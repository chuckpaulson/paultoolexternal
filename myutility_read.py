#module for utilities such as getting tokens and calling docebo api
import requests
import json 
import pandas as pd
import streamlit as st
import hashlib

@st.cache_data(ttl=3600)  # Cache data for 1 hour (=3600 seconds), also have @st.cache_data(show_spinner="Fetching data from API...")
def get_token():
    base_url = "https://paulsontraining.docebosaas.com/oauth2/token"
    data = {
        "client_id": "clientid1",
        "client_secret": st.secrets.client_secret,
        "grant_type": "password",
        "username": st.secrets.username,
        "password": st.secrets.password
    }
    response = requests.post(base_url, data=data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("token = ", token)
        return token
    else:
        print("Error getting token, response=", response)
        return None

def get_hash(name):
    name = name + st.secrets.salt
    nameb = name.encode('utf-8')
    myhash = hashlib.sha256(nameb).hexdigest()
    return myhash

def get_company_from_hash(hash_key):
    all_companies = do_get_companies()
    for index, row in all_companies.iterrows():
        #print(f'{row["title"]=} {get_hash(row["title"])=}')
        if hash_key == get_hash(row['title']):
            return row['id']
    return None

@st.cache_data(ttl=3600)  # Cache data for 1 hour (=3600 seconds)
def do_get_companies():
    get_companies = {
        'name': 'get_companies',
        'url': '/manage/v1/orgchart?flattened=true&page_size={page_size}&page={page}',
        'page_size': 200,
        'page': 1,
        'extract': 'items',
        'columns': ['id', 'title']
        #'columns': None
    }
    mycompanies = get_all_pages(get_companies)
    return mycompanies

@st.cache_data(ttl=3600)  # Cache data for 1 hour (=3600 seconds)
def do_get_users_by_company(company_id):
    get_users_by_company = {
        'name': 'get_users_by_company',
        'url': '/manage/v1/user?branch_id={branch_id}&page_size={page_size}&page={page}',
        'branch_id': 0,
        'page_size': 200,
        'page': 1,
        'extract': 'items',
        'columns': ['user_id', 'username', 'first_name', 'last_name', 'expiration_date']
        # 'columns': ['user_id','username','first_name','last_name','email','uuid','is_manager','fullname',
        #             'last_access_date','last_update','creation_date','status','avatar','language','lang_code',
        #             'expiration_date','level','email_validation_status','send_notification','newsletter_optout',
        #             'newsletter_optout_date','encoded_username','timezone','date_format','field_1','field_3',
        #             'multidomains','manager_names','managers','active_subordinates_count','actions,expired']
    }
    get_users_by_company['branch_id'] = company_id
    users_df = get_all_pages(get_users_by_company)
    return users_df

def split_into_courses_lessons(all_lessons):
    if all_lessons.empty:
        return (pd.DataFrame(), pd.DataFrame())
    # Separating lessons and courses
    courses = all_lessons[all_lessons['type'] == 'learning_plan']
    lessons = all_lessons[all_lessons['type'] == 'elearning']
    return (courses, lessons)

@st.cache_data(ttl=3600)  # Cache data for 1 hour (=3600 seconds)
def do_get_enrollments_by_user(user_id):
    get_user_lessons = {
    'name': 'get_user_enrollments',
    'url': '/learn/v1/enrollments?page_size={page_size}&page={page}&id_user={userid}',
    'userid': 19810,
    'page_size': 200,
    'page': 1,
    'extract': 'items',
    'columns': ['status', 'complete_percent', 'course_complete_date', 'score', 'name', 'type', 'url', 'code', 'id']
    }
    get_user_lessons['userid'] = user_id
    get_user_lessons['page'] = 1
    #make sure to return empty dataframe if no lessons
    lessons = get_all_pages(get_user_lessons)
    lessons.to_csv('columns_all.csv', index=False)
    return lessons

def calc_user_data_from_lessons(row):
    # Assuming 'user_id' is the unique identifier for each user
    user_id = row['user_id']
    user_lessons = do_get_enrollments_by_user(user_id)
    if user_lessons.empty:
        return 0,0,0,0,0,0
    mycourses_df, mylessons_df = split_into_courses_lessons(user_lessons)
    not_started_lessons = mylessons_df[mylessons_df['status'] == 'enrolled'].shape[0]
    in_progress_lessons = mylessons_df[mylessons_df['status'] == 'in_progress'].shape[0]
    completed_lessons = mylessons_df[mylessons_df['status'] == 'completed'].shape[0]
    total_lessons = mylessons_df.shape[0]

    # Counting the total number of courses and the number of completed courses
    completed_courses = mycourses_df[mycourses_df['status'] == 'completed'].shape[0]
    total_courses = mycourses_df.shape[0]
    return not_started_lessons, in_progress_lessons, completed_lessons, total_lessons, \
        completed_courses, total_courses

def add_lesson_data_to_users(users_df):
    users_df['not_started_lessons'], users_df['in_progress_lessons'], users_df['completed_lessons'], \
        users_df['total_lessons'], users_df['completed_courses'], users_df['total_courses']  = \
        zip(*users_df.apply(lambda row: calc_user_data_from_lessons(row), axis=1))
    return users_df

def get_all_pages(mydict):
    token = get_token()
    # Initialize an empty DataFrame to hold all the company data
    mydict_data = pd.DataFrame()
    mydict_copy = mydict.copy()
    # Get the data page by page
    while True:
        # Call the API to get the data for the current page
        mydict_json = docebo_api_get(mydict_copy, token)
        # Use the get_df function to convert the JSON data to a DataFrame
        df = get_df(mydict_copy, mydict_json)
        # Select only the 'id' and 'title' columns and append to the master DataFrame
        if not df.empty:
            mydict_data = pd.concat([mydict_data, df])
        # Check whether there is more data to fetch
        if not mydict_json['data']['has_more_data']:
            break
        # Move to the next page
        mydict_copy['page'] += 1
    # Save the data to a CSV file
    mydict_data.to_csv(mydict['name'] + '.csv', index=False)
    return mydict_data

def get_df(mydict, json_data):
    myindex = mydict.get('index', None)
    if myindex != None:
        df = pd.DataFrame(json_data['data'][mydict['extract']], myindex)
    else:
        df = pd.DataFrame(json_data['data'][mydict['extract']])
    if df.empty:
        return df
    mycolumns = mydict.get('columns',None)
    if mycolumns != None:
        df = df[mycolumns]
    mytranspose = mydict.get('transpose',None)
    if mytranspose != None:
        df = df.transpose()
    return df

def docebo_api_get(mydict, token):
    base_url = 'https://paulsontraining.docebosaas.com'
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
    }
    full_url = base_url + mydict['url'].format_map(mydict)
    response = requests.get(full_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        with open("result.json", "w") as f:
           json.dump(result, f)
        return result
    else:
        return None

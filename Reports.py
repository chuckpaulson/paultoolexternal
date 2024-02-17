import myutility_read
import pandas as pd
import streamlit as st

# Set the page configuration
st.set_page_config(
    page_title="ChuckTool",
    page_icon=":hammer_and_wrench:",
    layout="wide"
)
#this code reduces the white space at the top of the reports page
#the padding-top is set to 3rem to allow space for error messages
st.markdown("""
        <style>
               .block-container {
                    padding-top: 3rem;
                    padding-bottom: 0rem;
                    padding-left: 3rem;
                    padding-right: 3rem;
                }
        </style>
        """, unsafe_allow_html=True)
def dataframe_with_selections(df):
    df_with_selections = df.copy()
    df_with_selections.insert(0, "Select", False)

    # Get dataframe row-selections from user with st.data_editor
    edited_df = st.data_editor(
        df_with_selections,
        hide_index=True,
        use_container_width=True,
        column_config={"Select": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
        column_order=('Select', 'first_name','last_name','not_started_lessons', 'in_progress_lessons',
                          'completed_lessons', 'total_lessons', 'completed_courses', 'total_courses')
    )
    # Find the first selected row
    selections = edited_df[edited_df.Select]
    # drop the 'Select' column
    selections = selections.drop('Select', axis=1)
    # return the selected rows
    return selections
# get the hash key from the URL this app was called with
if 'key' not in st.query_params:
    st.error('''The URL must have a key parameter like this:,  
             https://paultoolexternal.streamlit.app/?key=<your key>''')
    st.stop()
company_key = st.query_params.key
if company_key == st.secrets.admin:
    all_companies = myutility_read.do_get_companies()
    # all_companies.to_csv('all_companies.csv', index=False)
    all_companies = all_companies[all_companies['title'].str.len() > 0]

    # Create a select box with the titles, putting default value first
    titles_list = all_companies['title'].tolist()
    DEFAULT = '<choose company>'
    titles_list.insert(0, DEFAULT)
    selected_title = st.selectbox('Choose a company:', titles_list)

    if selected_title == DEFAULT:
        st.write("Please select a company")
    else:
        # get the hash for the selected company
        hash = myutility_read.get_hash(selected_title)
        st.write(f'The link to the reports page for {selected_title} is:')
        st.write(f'https://paultoolexternal.streamlit.app/?key={hash}')
else:
    # get_hash('PaulsonTest5') = 04161345ee254a9badc06ec81045cc5ab7f61d0bcff0592b8d855f2845a6477f
    company_name, company_id = myutility_read.get_company_from_hash(company_key)
    if company_id is None:
        st.error(f'''The key={company_key} is not a valid key.  
                 Please check the URL and try a different key.''')
        st.stop()
    else:
        st.title(f"{company_name}")

        #after the comnpany id is chosen, then get all the users from the company and show them them
        users_df = myutility_read.do_get_users_by_company(company_id)
        users_df = myutility_read.add_lesson_data_to_users(users_df)

        #following displays the users in a dataframe and allows the user to select one
        selections = dataframe_with_selections(users_df)
        for selection in selections.iterrows():
            user_id = selection[1]['user_id']
            user_name = selection[1]['first_name'] + ' ' + selection[1]['last_name']
            st.subheader(f'{user_name}')
            user_lessons = myutility_read.do_get_enrollments_by_user(user_id)
            mycourses, mylessons = myutility_read.split_into_courses_lessons(user_lessons)
            if user_lessons.empty:
                st.write(f'User {user_name} has no enrollments')
            else:
                mycourses = mycourses[['code', 'status', 'complete_percent', 'score', 'name']]
                mylessons = mylessons[['code', 'status', 'course_complete_date', 'score', 'name']]
                st.write(f'Your courses are:')
                st.dataframe(mycourses, hide_index=True)
                st.write(f'Your lessons are:')
                st.dataframe(mylessons, hide_index=True)

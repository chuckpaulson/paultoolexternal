import myutility_read
import pandas as pd
import streamlit as st

# token = myutility.get_token()
# print("token = ", token)
# token =  '87392c2c4d819766bf912179f1c288eba30f1fc1'

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
company_key = st.query_params.key
st.write(f'{company_key=}')
# get_hash('PaulsonTest5') = 04161345ee254a9badc06ec81045cc5ab7f61d0bcff0592b8d855f2845a6477f
company_id = myutility_read.get_company_from_hash(company_key)
if company_id is not None:
    st.write(f'{company_id=}')
    st.title("Reports Page")
    st.write("Welcome to the Reports Page!")

    #after the comnpany id is chosen, then get all the users from the company and show them them
    users_df = myutility_read.do_get_users_by_company(company_id)
    users_df = myutility_read.add_lesson_data_to_users(users_df)

    #following displays the users in a dataframe and allows the user to select one
    selections = dataframe_with_selections(users_df)
    for selection in selections.iterrows():
        #user_id = selection.iloc[0]['user_id']
        print(f'{type(selection)=}')
        print(f'{selection=}')
        user_id = selection[1]['user_id']
        user_name = selection[1]['first_name'] + ' ' + selection[1]['last_name']
        st.write(f'{user_name=}, {user_id=}')
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

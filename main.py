import streamlit as st
from backend.utils import initialize_session
from pages.all_pages import all_pages as pages



initialize_session()

if st.session_state.logged_in: 
    # print(f"Answer Count for {user_id} --> {answered_count}")
    # If the user name is admin
    if st.session_state.user.email == st.secrets["admin_user"]["admin_user"]:
        # Normal experimental flow for admin user
        nav_list = [
                # Default page 
                pages["welcome"],
                # Access to the sign up page
                pages["signup"],
                pages["pre_treatment_survey"],
                pages["stage_1"],
                pages["stage_2_intro"],
                pages["stage_2_baseline"],
                pages["stage_2_static_explanation"],
                pages["stage_2_dialogue_based_explanation"],
                pages["stage_2_dialogue_based_explanation_2"],
                pages["stage_3_intro"],
                pages["stage_3"],
                pages["post_treatment_survey"],
                pages["completion"]
            ]
    else:
        hub = st.session_state.hub
        user_id = st.session_state.user_id
        answered_count = hub.response_service.get_answer_count(user_id) 
        is_completed = (answered_count == 28)
        #  Check if work is completed
        if is_completed:
            # Completion mode - only show thank you page
            nav_list = [pages["post_treatment_survey"], pages["completion"]]
        # If work is not completed
        elif not is_completed:
            nav_list = [
                # Default Page
                pages["welcome"],
                pages["pre_treatment_survey"],
                pages["stage_1"],
                pages["stage_2_intro"],
                pages["stage_2_baseline"],
                pages["stage_2_static_explanation"],
                pages["stage_2_dialogue_based_explanation"],
                pages["stage_2_dialogue_based_explanation_2"],
                pages["stage_3_intro"],
                pages["stage_3"],
                pages["post_treatment_survey"],
                pages["completion"]
            ]
else:
    # Not logged in is the default page
    nav_list = [pages["login"]]

page = st.navigation(nav_list)
page.run()
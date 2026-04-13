import streamlit as st
from backend.utils import initialize_session

# Specify the roles
ROLES = ["baseline", "static_exp", "static_with_dialogue", "dialogue_only"]

# TODO 1: Handling Login
##################################################################################################################
# Initialize Session Hub and Logged In
initialize_session()

def login():
    # This is the login function
    with st.container(border=True):
        # Fixed: st.title does NOT support text_alignment → use markdown instead
        st.markdown("<h1 style='text-align: center;'>Log in</h1>", unsafe_allow_html=True)
   
        # Your Email
        email = st.text_input(
            "Please enter your UNCG email",
            key="login_page_email"
        ).strip().lower()
   
        password = email
   
        _, col2, _ = st.columns(3)
        with col2:
            if st.button("Log in", use_container_width=True, key="login_page_button"):
                if not email or not password:
                    st.error("Please enter your UNCG Email")
                    st.stop()
   
                # Now safe to use st.session_state.hub (initialized in Main.py)
                user = st.session_state.hub.user_service.get_authenticated_user(email, password)
                if user:
                    # Get the user id
                    user_id = st.session_state.hub.user_service.get_user_id(email)
                    # Yes the user is logged in
                    st.session_state.logged_in = True
                    # User's session state
                    st.session_state.user = user
                    st.session_state.user_id = user_id
                    # Determining the user role
                    # if admin
                    if st.session_state.user.email == st.secrets["admin_user"]["admin_user"]:
                        st.session_state.role = "ADMIN"
                    else:
                        # Check if the User has answered all questions
                        answered_count = st.session_state.hub.response_service.get_answer_count(user_id)
                        is_completed = (answered_count == 28)
                        # Check if work is completed
                        if is_completed:
                            st.session_state.role = "DONE"
                        else:
                            role_pos = st.session_state.user_id % 4
                            st.session_state.role = ROLES[role_pos]
                    # Users DF
                    st.session_state.reviews_df = st.session_state.hub.reviews_service.get_reviews()
                    # print(st.session_state.user)
                    st.rerun()
   
                else:
                    st.error("Invalid UNCG email")

# ──────────────────────────────────────────────────────────────
# NAVIGATION (LOGIN KEPT EXACTLY AS st.Page LIKE YOU WANTED)
# ──────────────────────────────────────────────────────────────

# 1. Initialize the pages list
pages = []

# 2. Check if logged in. If not, ONLY show the login page.
if not st.session_state.get("logged_in", False):
    # This wraps your login function as a standalone page → exactly like you had
    pages = [st.Page(login, title="Log in", icon=":material/login:")]
else:
    # 3. Build the navigation based on roles
    #    → ALL heavy st.Page() definitions are now INSIDE this else block
    #    → This completely eliminates the lag on the login screen

    # Get the role
    role = st.session_state.role

    # Account Pages
    pre_treatment_survey_page = st.Page("pre_treatment_survey.py", title="Survey", icon=":material/quiz:")
    post_treatment_survey_page = st.Page("post_treatment_survey.py", title="Survey", icon=":material/quiz:")
    completion_page = st.Page("completion.py", title="Thank You", icon=":material/quiz:")
    welcome_page = st.Page("welcome.py", title="Welcome Page", icon=":material/quiz:", 
                           default=(role in ["ADMIN", "baseline", "static_exp", "static_with_dialogue", "dialogue_only"]))
    stage_1_page = st.Page("stage_1.py", title="Stage 1", icon=":material/quiz:")
    stage_3_intro_page = st.Page("stage_3_intro.py", title="Stage 3", icon=":material/quiz:")
    stage_3_page = st.Page("stage_3.py", title="Stage 3", icon=":material/quiz:")

    baseline_stage_2_intro_page = st.Page(
        "baseline_user/stage_2_baseline_intro.py",
        title="Welcome to Stage 2",
    )
    baseline_stage_2_page = st.Page(
        "baseline_user/stage_2_baseline.py",
        title="Stage 2",
        icon=":material/quiz:"
    )
    static_exp_stage_2_intro_page = st.Page(
        "static_exp_user/stage_2_static_exp_intro.py",
        title="Welcome to Stage 2",
    )
    static_exp_stage_2_page = st.Page(
        "static_exp_user/static_explanation.py",
        title="Stage 2",
        icon=":material/quiz:"
    )
    static_with_dialogue_stage_2_intro_page = st.Page(
        "static_with_dialogue_user/stage_2_stat_with_dialogue_intro.py",
        title="Welcome to Stage 2",
    )
    static_with_dialogue_stage_2_page = st.Page(
        "static_with_dialogue_user/dialogue_based_explanation.py",
        title="Stage 2",
        icon=":material/quiz:"
    )
    dialogue_stage_2_intro_page = st.Page(
        "dialogue_user/stage_2_dialogue_intro.py",
        title="Welcome to Stage 2",
    )
    dialogue_stage_2_page = st.Page(
        "dialogue_user/dialogue_based_explanation_2.py",
        title="Stage 2",
        icon=":material/quiz:"
    )
    done_post_treatment_page = st.Page(
        "survey_complete/done_post_treatment_survey.py",
        title="Thank You", 
        icon=":material/quiz:",
        default=(role == "DONE")
    )
    done_completion_page = st.Page(
        "survey_complete/done_completion.py",
        title="Thank You", 
        icon=":material/quiz:"
    )
    admin_signup_page = st.Page(
        "admin/signup.py",
        title="Sign Up Page",
        icon=":material/quiz:"
    )

    account_pages = [welcome_page, pre_treatment_survey_page, post_treatment_survey_page, stage_1_page,
                     stage_3_intro_page, stage_3_page, completion_page]
    admin_pages = [admin_signup_page]
    done_pages = [done_post_treatment_page, done_completion_page]
    baseline_pages = [baseline_stage_2_intro_page, baseline_stage_2_page]
    static_exp_pages = [static_exp_stage_2_intro_page, static_exp_stage_2_page]
    static_with_dialogue_pages = [static_with_dialogue_stage_2_intro_page, static_with_dialogue_stage_2_page]
    dialogue_pages = [dialogue_stage_2_intro_page, dialogue_stage_2_page]

    if st.session_state.role == "ADMIN":
        pages = account_pages + baseline_pages + static_exp_pages + static_with_dialogue_pages + dialogue_pages + admin_pages
    elif st.session_state.role == "DONE":
        pages = done_pages
    elif st.session_state.role == "baseline":
        pages = account_pages + baseline_pages
    elif st.session_state.role == "static_exp":
        pages = account_pages + static_exp_pages
    elif st.session_state.role == "static_with_dialogue":
        pages = account_pages + static_with_dialogue_pages
    else:
        pages = account_pages + dialogue_pages

# 4. Run the Navigation
if pages:
    pg = st.navigation(pages)
    pg.run()
####################################################################################################################
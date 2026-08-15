import streamlit as st
from backend.utils import initialize_session
from backend.filter_data import shuffle_stage_2
import re

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
        st.markdown("<h1 style='text-align: center;'>Study Registration</h1>", unsafe_allow_html=True)
   
        # Your Email
        email = st.text_input(
            "Please enter your email",
            key="login_page_email"
        ).strip().lower()
   
        password = email
   
        _, col2, _ = st.columns(3)
        with col2:
            if st.button("Register Here", use_container_width=True, key="login_page_button"):
                # Email Validation
                if not email:
                    st.error("Please enter your email address.")
                    st.stop()
                
                # Validate email format
                email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if not re.match(email_pattern, email):
                    st.error("Please enter a **valid** email address (e.g., name@example.com).")
                    st.stop()
                    
                # Check if user exists
                user = st.session_state.hub.user_service.get_authenticated_user(email, password)
                # Else create the user
                if not user:
                    # Create the new user
                    user = st.session_state.hub.user_service.create_user(email, password)
                # Get the user id
                user_id = st.session_state.hub.user_service.get_user_id(email)
                # Yes the user is logged in
                st.session_state.logged_in = True
                # User's session state
                st.session_state.user = user
                st.session_state.user_id = user_id
                # Determining the user role
                # Wave 1 = original collection (Stage-2 set 1, 75% accuracy).
                # Wave 2 = current collection (sets 2-4, 50%). Recorded for
                # the analysis; the app needs no branching on it.
                st.session_state.wave = st.session_state.user.wave
                # Stage-2 review set: 1 for wave-1 participants (the original
                # set, still present), 2-4 for wave 2. Assigned by the column
                # DEFAULT at registration, so it is simply read here.
                st.session_state.review_set = st.session_state.user.review_set
                is_admin = (st.session_state.user.email
                            == st.secrets["admin_user"]["admin_user"])

                # Reviews this participant will see: Stage 1 + their Stage-2
                # set + Stage 3. Admins get every set.
                #
                # Loaded before the role check so completion is judged
                # against the reviews actually assigned to this participant
                # rather than a hardcoded total.
                st.session_state.reviews_df = (
                    st.session_state.hub.reviews_service.get_reviews(
                        review_set=None if is_admin
                        else st.session_state.review_set
                    )
                )

                # Randomise this participant's Stage-2 trial order, once the
                # set is known. Seeded on user_id so a participant who
                # resumes gets the same sequence - resume matches saved
                # responses by review_id, so a fresh order would put them at
                # the right index but the wrong review. Admins keep the
                # database order.
                if not is_admin:
                    st.session_state.reviews_df = shuffle_stage_2(
                        st.session_state.reviews_df,
                        user_id=st.session_state.user_id,
                    )

                if is_admin:
                    st.session_state.role = "ADMIN"
                else:
                    answered_count = (
                        st.session_state.hub.response_service.get_answer_count(user_id)
                    )
                    # >= rather than ==: an extra or duplicated response would
                    # otherwise leave the participant permanently unfinished,
                    # unable to reach the post-treatment survey.
                    if answered_count >= len(st.session_state.reviews_df):
                        st.session_state.role = "DONE"
                    else:
                        role_pos = st.session_state.user_id % 4
                        st.session_state.role = ROLES[role_pos]
                st.rerun()
                    
                     

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
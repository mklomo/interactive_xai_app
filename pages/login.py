import streamlit as st
from pages.all_pages import all_pages as pages
from backend.utils import initialize_session



initialize_session()

with st.container(border=True):
    st.title("Log in", text_alignment="center")

    # Your Email
    email = st.text_input(
        "Please enter your UNCG email",
        key="login_email"
    ).strip().lower()

    password = email

    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("Log in", use_container_width=True):
            if not email or not password:
                st.error("Please enter your UNCG Email")
                st.stop()

            # Now safe to use st.session_state.hub (initialized in Main.py)
            user = st.session_state.hub.user_service.get_authenticated_user(email, password)

            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.user_id = st.session_state.hub.user_service.get_user_id(email)
                st.session_state.reviews_df = st.session_state.hub.reviews_service.get_reviews()

                # Check if user already completed the study
                answered_count = st.session_state.hub.response_service.get_answer_count(
                    st.session_state.user_id
                )
                st.rerun()   # Let Main.py handle the correct navigation

            else:
                st.error("Invalid UNCG email")

# Link to signup
# st.page_link(pages["signup"], label="Don't have an account? Please Signup!")
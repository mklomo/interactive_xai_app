import streamlit as st
from backend.hub import Hub
from pages.all_pages import all_pages as pages



# Instantiate Hub from user session state
hub = st.session_state.hub



with st.container(border=True):
    # Title of page
    st.title("Create Account")
    # User Email
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Create Account"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            user = hub.user_service.create_user(email, password)
            if user:
                st.success("Account Created Successfully")
                # Now navigate to login page
                st.switch_page(pages["login"])
            else:
                st.error("Please enter valid email or password")
            
# Link to the Login Page
st.page_link(pages["welcome"], label="Return to the Welcome page!")               
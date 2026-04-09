import streamlit as st
from backend.hub import Hub




# Instantiate Hub from user session state
hub = st.session_state.hub



with st.container(border=True):
    # Title of page
    st.title("Create Account")
    # User Email
    email = (st.text_input("Email")).strip().lower()
    password = email
    confirm_password = email
    if st.button("Create Account"):
        if password != confirm_password:
            st.error("Passwords do not match")
        else:
            user = hub.user_service.create_user(email, password)
            if user:
                st.success("Account Created Successfully")
            else:
                st.error("Please enter valid email or password")
            
# Link to the Login Page
st.page_link("welcome.py", label="Return to the Welcome page!")               
import streamlit as st
from backend.hub import Hub

def initialize_session():
    """Initialize all required session state variables safely."""
    if "hub" not in st.session_state:
        st.session_state.hub = Hub()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if "role" not in st.session_state:
        st.session_state.role = None



    
import streamlit as st
from pages.all_pages import all_pages as pages

def main():
    # === AGGRESSIVELY CLEAR ALL SESSION STATE (except the Hub if you still need it globally) ===
    keys_to_keep = ["hub"]  # keep this if your Hub object is used across the app
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    
    # Explicitly reset login flags
    st.session_state.logged_in = False
    st.session_state.user = None
    
    # === DIRECTLY SWITCH TO LOGIN PAGE ===
    # This bypasses the st.rerun() + main.py navigation gotcha that was sending you to "welcome"
    st.switch_page(pages["login"])

if __name__ == "__main__":
    main()
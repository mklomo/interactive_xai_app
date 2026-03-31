import streamlit as st
from pages.all_pages import all_pages as pages
import streamlit.components.v1 as components

def setup_page():
    st.set_page_config(
        page_title="Thank You - Review Hunters 🕵️‍♂️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
   
    st.markdown(
        """
        <style>
            [data-testid="stElementContainer"] {
                width: 100% !important;
            }
            .stButton > button {
                width: 100%;
                max-width: 460px;
                height: 3.6rem;
                font-size: 1.28rem !important;
                font-weight: 600;
                margin: 1.4rem auto;
                display: block;
            }
            h1, h2, h3 {
                text-align: center;
                margin-bottom: 1.2rem;
            }
            .main p {
                font-size: 1.18rem;
                line-height: 1.8;
                margin: 1.6rem auto;
                text-align: center;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

def main():
    setup_page() # Your existing CSS/Config

    st.markdown("<h1>Please Complete the Survey</h1>", unsafe_allow_html=True)

    # 1. The Survey Iframe (Clean and simple)
    _, center_content, _ = st.columns([1, 10, 1])
    with center_content:
        components.iframe(
            "https://uncg.qualtrics.com/jfe/form/SV_eUUKUUSlA5Cm086", 
            height=800, 
            scrolling=True
        )

    st.divider()

    # 2. The Verification Logic
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.subheader("Proceed To Stage 1")
        
        # User enters the code they saw at the end of Qualtrics
        st.markdown(
            "<p style='margin-bottom: 0rem;'>Please Complete the Survery and Enter the Completion Code Below</p>", 
            unsafe_allow_html=True
        )
        access_code = st.text_input(
            label="Enter the Completion Code from Survey", 
            placeholder="Completion Code", 
            label_visibility="collapsed" # Use 'collapsed' instead of 'hidden'
        )

        # Set Survey Complete to False
        st.session_state.survey_completed = False
        
        # Check if the code matches (Case-insensitive)
        if access_code.strip().upper() == "HUNTER-2026":
            st.session_state.survey_completed = True
            st.success("✅ Code Verified! You may now proceed.")
        elif access_code:
            st.error("❌ Incorrect code. Please finish the survey to see the code.")

        # The Proceed Button
        if st.button("Proceed to Stage 1", 
                     use_container_width=True, 
                     type="primary",
                     disabled=not st.session_state.get('survey_completed', False)):
            st.switch_page(pages["stage_1"])

        # Caption
        if not st.session_state.survey_completed:
            st.caption("🔒 Complete the survey to unlock", text_alignment="center")
        

if __name__ == "__main__":
    main()
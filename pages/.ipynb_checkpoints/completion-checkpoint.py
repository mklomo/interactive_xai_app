import streamlit as st
from pages.all_pages import all_pages as pages

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

def thank_you_content():
    st.markdown("<h1>Thank You, Review Hunter! 🎉</h1>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="max-width: 850px; margin: 0 auto; text-align: center;">
            <p style="font-size: 1.35rem; margin: 1.8rem 0 2.5rem;">
                <strong>Mission Accomplished!</strong><br>
                You have successfully completed all 28 reviews in <em>The Game: Review Hunters</em>.
            </p>
            <p>
                Thank you for your time and sharp detective work.
                Your decisions help researchers understand how people team up with AI to fight deceptive hotel reviews.
            </p>
            <p style="margin-top: 2.5rem; color: #2E8B57; font-size: 1.25rem;">
                You're now officially a certified Review Hunter 🕵️‍♂️<br>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

def main():
    setup_page()
    st.balloons()
    thank_you_content()

    # # Initialize flag
    # if "post_survey_completed" not in st.session_state:
    #     st.session_state.post_survey_completed = False

    # # Centered column for clean stacked buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
    #     # === 1. FINAL SURVEY SECTION ===
    #     if not st.session_state.post_survey_completed:
    #         # Step A: Click to reveal the actual link
    #         if st.button("Step 1: Start Final Survey", use_container_width=True):
    #             st.session_state.post_survey_completed = True
    #             st.rerun()
    #     else:
    #         # Step B: Show the actual Qualtrics link button
    #         st.info("Final Survey Link Active 👇")
    #         st.link_button(
    #             label="Open Final Survey 🔗",
    #             url="https://uncg.qualtrics.com/jfe/form/SV_5jLpOaEaNXiUr3w",
    #             width="stretch"
    #         )
    #         # st.success("✅ Survey opened! Please return here to log out after finishing.")

        # --- Log Out Section ---
        # st.markdown("---")

        # === 2. LOG OUT BUTTON ===
        if st.button(
            "🚪 Log Out & Finish",
            type="primary",
            width="stretch",
            # disabled=(not st.session_state.post_survey_completed)
        ):
            # Clear session state
            for key in list(st.session_state.keys()):
                if key != "hub": # Keep hub if necessary for your routing
                    del st.session_state[key]

            # Reset login flags explicitly
            st.session_state.logged_in = False
            
            # Go back to login
            st.switch_page(pages["login"])
        # # Dynamic Caption for the Log Out button
        # if not st.session_state.post_survey_completed:
        #     st.caption("🔒 Complete the final survey to unlock the Log Out button.", text_alignment="center")
        # else:
        #     st.caption("✅ Final mission step authorized. You may now log out.", text_alignment="center")

    # Footer note
    st.markdown(
        """
        <div style="text-align: center; margin-top: 4rem; font-size: 0.95rem; color: #666;">
            Your responses have been saved securely.<br>
            If you have any questions, please contact the research team.
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
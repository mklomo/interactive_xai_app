import streamlit as st
from pages.all_pages import all_pages as pages
from typing import Dict, Optional


def setup_page():
    st.set_page_config(
        page_title="The Game: Review Hunters 🕵️‍♂️",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    st.markdown(
        """
        <style>
            /* 1. FORCE the container to fill the full width of the column */
            /* This overrides the 'fit-content' you see in your HTML */
            [data-testid="stElementContainer"] {
                width: 100% !important;
            }

            /* 2. Center the radio widget itself */
            [data-testid="stRadio"] {
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                width: 100% !important;
            }

            /* 3. Center the 'Genuine' and 'Deceptive' buttons horizontally */
            [data-testid="stRadio"] > div[role="radiogroup"] {
                display: flex !important;
                justify-content: center !important;
                gap: 3rem !important;
                width: 100% !important;
            }

            /* 4. OVERRIDE your global 'justify' rule for the radio text */
            [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
                text-align: center !important;
                margin: 0 !important;
            }

            /* 5. Hide the 'Decision' label and its extra spacing */
            [data-testid="stWidgetLabel"] {
                display: none !important;
            }

            /* Slider Styling */
            div[data-testid="stSlider"] {
                margin: 1.5rem auto;
                width: 75%;
            }

            /* Button Styling */
            .stButton > button {
                width: 100%;
                max-width: 420px;
                height: 3.2rem;
                font-size: 1.25rem !important;
                font-weight: 600;
                margin: 1.2rem auto;
                display: block;
            }

            /* Headings and Paragraphs */
            h1, h2, h3, h4 {
                text-align: center;
                margin-bottom: 1.2rem;
            }
            .main p {
                font-size: 1.15rem;
                margin: 1.1rem auto;
                text-align: justify;
            }
        </style>
        """,
        unsafe_allow_html=True
    )


def explanation_condition():
    extra_item = ""
    if "user_id" in st.session_state:
        mod = st.session_state.user_id % 4
        # Recommendation + Static Feature Importance
        if mod == 1:
            extra_item = "<li>You will also receive a visual explanation of the review agent's recommendation. This visualisation depicts how the review agent arrives at its recommendations based on the features of the review (more on this at Stage 2)</li>"
        # Recommendation + Static Feature Importance + Dialogue
        elif mod == 2:
            extra_item = "<li>You will also receive a visual explanation of the review agent's recommendation. This visualisation depicts how the review agent arrives at its recommendations based on the review's features. In addition, you also have access to dialogue with the review agent through a chat interface to ask questions about the recommendation (more on this at Stage 2)</li>"
        # Recommendation + Dialogue
        elif mod == 3:
            extra_item = "<li>You you also have access to dialogue with the review agent through a chat interface to ask further questions about its recommendation (more on this at Stage 2)</li>"
        # # Recommendation + Dialogue
        # elif mod == 4:
        #     extra_item = "<li>You will also receive an explanation of the review agent's recommendation. This explanation reveals the rationale behind the review agent's recommendations based on the features of the review (more on this at Stage 2)</li>"
        # Baseline 
        else:
            extra_item = ""
    return extra_item


def page_text():
    st.markdown(
        "<h2>The Game: Review Hunters 🕵️‍♂️</h2>",
        unsafe_allow_html=True
    )

    intro_text = f"""
    <div style="max-width: 900px; margin: 0 auto;">
        <p>
            Welcome to <em>Review Hunters</em>! You’re teaming up with 🤖Review Agent, a machine learning agent, to bust deceptive hotel reviews (like those sneaky ones on Tripadvisor or Yelp). By a machine learning agent, we mean a system that utilises machine learning algorithms to provide recommendations.
        </p>
        <p>
            Imagine you were planning a trip and checking hotel reviews to decide where to stay. Your job? Spot whether a review is:
        </p>
        <ul>
            <li>✅Genuine—written by someone who actually stayed at the 🏨hotel orr</li>
            <li>❌Deceptive, a fake review crafted to trick you into thinking it’s legit.</li>
        </ul>
        <p>
            The task consists of three stages:
        </p>
        <h3>Stage 1: Solo Sleuthing 🔍</h3>
        <p>
            You will assess 8 hotel reviews without any assistance from the 🤖Review Agent. For each review, please:
        </p>
        <ul>
            <li>Decide if each review is ✅Genuine or ❌Deceptive</li>
            <li>Rate how confident you are in your decision</li>
            <li>State whether you would choose to book the hotel based solely on this review</li>
        </ul>
        <h3>Stage 2: Team-Up with 🤖Review Agent 🤝</h3>
        <p>
            You will evaluate 12 hotel reviews with access to 🤖Review Agent’s recommendations. For each review, you will see:
        </p>
        <ul>
            <li>The 🤖Review Agent recommendation</li>
            {explanation_condition()}</ul>
        <p>
            You are free to agree or disagree with the Agent when making your own judgment.
        </p>
        <h3>Stage 3: Back to Solo, But Stronger 💪</h3>
        <p>
            You will assess 8 final hotel reviews without Review Agent support — identical in format to Stage 1.
        </p>
        <h3>Purpose of the Study</h3>
        <p>
            This isn’t just a study—it’s a <em>game</em> where you’re the hero, sniffing out ❌Deceptive reviews and championing the ✅Genuine ones.
            So, grab your virtual magnifying glass, and let’s hunt some reviews! 🏨🔎
        </p>
        <p style="margin-top: 2.5rem; font-weight: 500;">
            Before beginning, please complete the pre-study survey by clicking the button below.
        </p>
    </div>
    """
    st.markdown(intro_text, unsafe_allow_html=True)



def main():
    if "hub" not in st.session_state:
        st.session_state.hub = Hub()
    setup_page()
    page_text()
    # Survey button – centered
    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("Open Pre-Study Survey", 
                  width="stretch", 
                ):
            st.switch_page(pages["pre_treatment_survey"])

        if st.session_state.user.email == st.secrets["admin_user"]["admin_user"]:
            if st.button("Create New User", 
                  width="stretch", 
                ):
                st.switch_page(pages["signup"])
            
        


if __name__ == "__main__":
    main()
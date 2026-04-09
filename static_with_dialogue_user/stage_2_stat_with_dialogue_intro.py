import streamlit as st



def setup_page():
    st.set_page_config(
        page_title="The Game: Review Hunters 🕵️‍♂️ – Stage 2",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    st.markdown(
        """
        <style>
            [data-testid="stElementContainer"] { width: 100% !important; }
            [data-testid="stRadio"] {
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                width: 100% !important;
                font-size: 1.5rem !important;
            }
            [data-testid="stRadio"] > div[role="radiogroup"] {
                display: flex !important;
                justify-content: center !important;
                gap: 3rem !important;
                width: 100% !important;
                font-size: 1.5rem !important;
            }
            [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
                text-align: center !important;
                margin: 0 !important;
            }
            [data-testid="stWidgetLabel"] { 
            display: none !important; 
            }
            div[data-testid="stSlider"] { 
                margin: 1.5rem auto; 
                width: 75%; 
                text-align: center;
                }
            [data-testid="stTickBar"] div {
                font-size: 1.5rem !important;  
            }
            [data-testid="stSliderThumbValue"] {
                font-size: 1.5rem !important;  /* Optional: Also increase thumb value size if desired */
            }
            .stButton > button {
                width: 100%;
                max-width: 420px;
                height: 3.2rem;
                font-size: 1.25rem !important;
                font-weight: 600;
                margin: 1.2rem auto;
                display: block;
            }
            h1, h2, h3, h4 { 
                text-align: center; 
                margin-bottom: 1.2rem; 
                }
            .main p {
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
            extra_item = "<li>You will also receive a visual explanation of the agent's recommendation. This visualisation depicts how the review agent arrives at its recommendations based on the features of the review (see tutorial below)</li>"
        # Recommendation + Static Feature Importance + Dialogue
        elif mod == 2:
            extra_item = "<li>You will also receive a visual explanation of the agent's recommendation. This visualisation depicts how the review agent arrives at its recommendations based on the review's features. In addition, you also have access to dialogue with the review agent through a chat interface to ask questions about the recommendation (see tutorial below)</li>"
        # Recommendation + Dialogue
        elif mod == 3:
            extra_item = "<li>You you also have access to dialogue with the review agent through a chat interface to ask further questions about its recommendation (see tutorial below)</li>"
        # # Recommendation + Dialogue
        # elif mod == 4:
        #     extra_item = "<li>You will also receive an explanation of the review agent's recommendation. This explanation reveals the rationale behind the review agent's recommendations based on the features of the review (more on this at Stage 2)</li>"
        # Baseline 
        else:
            extra_item = ""
    return extra_item


def tutorial_condition():
    if "user_id" in st.session_state:
        mod = st.session_state.user_id % 4
        if mod == 1:
            # Tutorial Link 1 - Static Feature Importance
            tutorial = "https://youtu.be/HKWiA3dbn5g"
        elif mod == 2:
            # Tutorial Link 2 - Static Feature Importance + Dialogue
            tutorial = "https://youtu.be/Ej076Pqaqvw"
        elif mod == 3:
            # Tutorial Link 3 - # Recommendation + Dialogue
            tutorial = "https://youtu.be/GPTYACS6gqk"
        # elif mod == 4:
        #     # Tutorial Link 4 - # NL Explanation
        #     tutorial = "https://youtu.be/GPTYACS6gqk"
        # Baseline
        else:
            # Tutorial Link 5
            tutorial = "https://youtu.be/AMPM-7yoyvs"
    return tutorial
        


def page_text():
    # Heading
    st.markdown("<h2 style='text-align: center;'>Stage 2: Team-Up with 🤖Review Agent 🤝</h2>", unsafe_allow_html=True)

    intro_text = f"""
                    <div>
                        <p class="intro-text">
                            Welcome to Stage 2 of <em>Review Hunters</em>! This time, you're teaming up with 🤖Review Agent to tackle 12 🏨hotel reviews. Your mission? Hunt down <span style="color: green;">Genuine</span> reviews and expose those sneaky <span style="color: red;">Deceptive</span> ones. Here's how you play:
                        </p>
                        <h3>Game Plan</h3>
                        <ul class="intro-text">
                            <li><strong>Step 1:</strong> You will make an initial decision and report your confidence scores and likelihood to stay in the hotel based on the review as you did in Stage 1.</li>
                            <li><strong>Step 2:</strong> You will then receive assistance from 🤖Review Agent and make a final decision. You can either change or maintain your initial decision, you have the final decision-making authority. This is followed by a brief set of questions regarding your decision-making process.</li>
                            {explanation_condition()}</ul>
                        <h3>How 🤖Review Agent Sniffs Out Clues</h3>
                        <p class="intro-text">
                            How does the 🤖Review Agent make its recommendations? It looks at clues in the hotel review. These clues include:
                        </p>
                        <ul class="clue-list">
                            <li><strong>Emotional Content in the Review:</strong> This is the number of emotional words, which show how much the review focuses on feelings. For example, positive feelings (like "happy" or "love") or negative ones (like "hate" or "disgust").</li>
                            <li><strong>Analytic Writing Style of the Review:</strong> This assesses the writing style of the review. High scores mean the review is formal, like a report. Low scores mean it's more like a story.</li>
                            <li><strong>Proportion of Adjectives in the Review:</strong> This assesses the share of descriptive words in the review (like "funny" or "quiet"), which tells us how much the writer describes things.</li>
                            <li><strong>Readability of the Review:</strong> How easy the review is to read. Reviews with long sentences and big words are harder to read (more complex), while short sentences and simple words make it easier.</li>
                        </ul>
                    </div>
    """

    st.markdown(f"<h4 style='text-align: justify;'>{intro_text}</h4>", unsafe_allow_html=True)

    # Display Decision Question
    st.markdown("<h3 style='text-align: center;'>A Short Tutotrial on How Review Agent Works</h3>", unsafe_allow_html=True)




def page_navigation():
    # Display tutorials
    tutorial_link = tutorial_condition()
    # print(f"Tutorial Link --> {tutorial_link}")
    # Set the pixel
    col_1, col_2, col_3 = st.columns([0.5,2,0.5])
    with col_2:
        st.video(tutorial_link, width="stretch")

    col_1, col_2, col_3 = st.columns([1, 1, 1])  # Adjust the ratios as needed
    with col_2:    
        if st.button("Proceed to Stage 2", width="stretch"):
            st.switch_page("static_with_dialogue_user/dialogue_based_explanation.py")
                

def main():
    # Set up Page
    setup_page()
    # Page text
    page_text()
    # Page Nav
    page_navigation()

if __name__ == "__main__":
    main()

            
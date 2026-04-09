import streamlit as st

def setup_page():
    st.set_page_config(
        page_title="The Game: Review Hunters 🕵️‍♂️ - Stage 3",
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



def page_text():
    st.markdown(""" <h2 style='text-align: center;'>The Game: Review Hunters 🕵️‍♂️ - Stage 3</h2> """, unsafe_allow_html=True)

    intro_text = """
    <div>
        <h3>Stage 3: Back to Solo, But Stronger 💪</h3>
        <p><strong>What’s the deal?</strong> You’re back on your own for 8 more 🏨hotel reviews, no 🤖Review Agent this time.</p>
        <p><strong>Your moves:</strong></p>
        <ul>
            <li>Just like Stage 1, decide if each review is ✅Genuine or ❌Deceptive.</li>
            <li>Rate your confidence and say whether you’d book the 🏨hotel based on the review.</li>
            </ul>
        <p><strong>Challenge:</strong> After teaming up with the Agent in Stage 2, have you leveled up your scam-spotting skills? Time to prove you’re a review-hunting legend!</p>
    </div>
    <div>
        <p>Ready to start Stage 3? Hit the button below! 😎</p>
    </div>
                """
    st.markdown(f"{intro_text}", unsafe_allow_html=True)



def main():
    # Run the page set up
    setup_page()
    # Get the page text
    page_text()
    col1, col2, col3 = st.columns([1, 1, 1]) # Adjust the ratios as needed
    with col2:
        if st.button("Start Stage 3", width="stretch"):
            st.switch_page("stage_3.py")


if __name__ == "__main__":
    main()           
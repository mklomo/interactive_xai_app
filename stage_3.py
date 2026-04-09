import streamlit as st
from streamlit_scroll_to_top import scroll_to_here
from typing import Dict, Optional
from backend.filter_data import filter_data
from backend.response import Response


def setup_page():
    st.set_page_config(
        page_title="The Game: Review Hunters 🕵️‍♂️ – Stage 3",
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


def scroll_to_top():
    if 'scroll_trigger' not in st.session_state:
        st.session_state.scroll_trigger = False
    if st.session_state.scroll_trigger:
        scroll_to_here(0, key="top_scroll")
        st.session_state.scroll_trigger = False


def scroll():
    st.session_state.scroll_to_top = True

    
def initialize_session_state(df):
    """Initialize session state for reviews and answers."""
    if "stage_3_current_review" not in st.session_state:
        st.session_state.stage_3_current_review = 0
    if "stage_3_answers" not in st.session_state:
        stage_3_df = filter_data(df=st.session_state.reviews_df, stage="stage_3")
        st.session_state.stage_3_answers = [{} for _ in range(len(df))]


def display_review(review_text: str, current: int, total: int):
    st.markdown(f"<h3>Review {current + 1} of {total}</h3>", unsafe_allow_html=True)
    st.progress((current + 1) / total)
    st.markdown(
        f"""
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #0E1117; font-size: 35px; color: white;">
            {review_text.replace('"', '')}
        </div>
        <div style="margin-bottom: 20px;"></div>
        """,
        unsafe_allow_html=True
    )


def render_questions(current: int, saved: dict):
    # Decision
    st.markdown(
        "<h3>Is this review ✅ Genuine or ❌ Deceptive?</h3>",
        unsafe_allow_html=True
    )
    col_left, col_center, col_right = st.columns([2, 1, 2])
    with col_center:
        decision_options = [":green[Genuine]", ":red[Deceptive]"]
        # Use saved value if exists
        preselected = None
        if saved.get("decision") == "Genuine":
            preselected = 0
        elif saved.get("decision") == "Deceptive":
            preselected = 1

        raw_decision = st.radio(
            label="Decision",
            options=decision_options,
            index=preselected,            
            horizontal=True,
            label_visibility="hidden",
            key=f"dec_{current}"
        )
        decision = raw_decision.split("[")[1].split("]")[0] if raw_decision else None

    # Certainty
    st.markdown("<h3>How certain are you in your decision? (1 = Very uncertain, 7 = Very certain)</h3>", unsafe_allow_html=True)
    certainty = st.slider(
        "Certainty",
        0, 7,
        value=saved.get("certainty", 0),  # default to 4 instead of 0 if nothing saved
        label_visibility="hidden",
        key=f"certainty_{current}"
    )

    # Likelihood
    st.markdown("<h3>If you were booking a trip right now, how likely would you choose this hotel? (1 = Not at all, 7 = Very likely)</h3>", unsafe_allow_html=True)
    likelihood = st.slider(
        "Likelihood",
        0, 7,
        value=saved.get("likelihood", 0),
        label_visibility="hidden",
        key=f"likelihood_{current}"
    )

    return decision, certainty, likelihood


def save_response(review_id: int, answers: dict, hub):
    user_id = st.session_state.user_id
    existing_id = hub.response_service.get_response_id(user_id=user_id, review_id=review_id)

    response_data = {
        "user_id": user_id,
        "review_id": review_id,
        "final_decision": answers["decision"],
        "final_certainty_rating": answers["certainty"],
        "final_persuasion_rating": answers["likelihood"],
        "initial_decision": None,
        "initial_certainty_rating": None,
        "initial_persuasion_rating": None,
        "influence_rating": None,
        "decision_making_description": None,
        "verification_queries_and_responses": None
    }

    response_obj = Response(**response_data)

    if existing_id:
        hub.response_service.update_response(existing_id, response_obj)
    else:
        hub.response_service.create_response(response_obj)

# Get Response
def get_response(
    user_id: str,
    review_id: int,
    response_service,  # your response_service from hub
) -> Optional[Dict[str, any]]:
    """
    Fetch previously saved response for this user + review.
    Returns a dict with the fields we care about for pre-filling Stage 3,
    or None if no saved response exists.
    """
    existing_id = response_service.get_response_id(
        user_id=user_id,
        review_id=review_id
    )
    
    if not existing_id:
        return None
        
    response_obj: Response = response_service.get_response(existing_id)
    if not response_obj:
        return None
        
    # Map the fields we actually use in Stage 3
    saved = {}
    
    if response_obj.final_decision:
        saved["decision"] = response_obj.final_decision
    
    if response_obj.final_certainty_rating is not None:
        saved["certainty"] = int(response_obj.final_certainty_rating)
        
    if response_obj.final_persuasion_rating is not None:
        saved["likelihood"] = response_obj.final_persuasion_rating
    return saved if saved else None



def handle_navigation(current: int, total: int, answers: dict, review_id: int, hub):
    col1, col2 = st.columns([1, 1])

    with col1:
        if current > 0:
            if st.button("← Previous", width="stretch"):
                st.session_state.stage_3_current_review -= 1
                st.session_state.scroll_trigger = True
                st.rerun()
        else:
            if st.button("Back to Stage 3 Intro", width="stretch"):
                st.switch_page("stage_3_intro.py")

    with col2:
        label = "Finish Stage 3 & Submit" if current == total - 1 else "Next Review →"
        if st.button(label, width="stretch"):
            if not answers["decision"]:
                st.error("Please indicate whether the review is Genuine or Deceptive.")
                return
            if answers["certainty"] < 1:
                st.error("Please select your certainty level (1–7).")
                return
            if answers["likelihood"] < 1:
                st.error("Please select how likely you would book the hotel (1–7).")
                return

            st.session_state.stage_3_answers[current] = answers.copy()
            save_response(review_id, answers, hub)
            st.session_state.stage_3_current_review += 1
            st.session_state.scroll_trigger = True
            st.rerun()


def main():
    """Main function to run Stage 1."""
    hub = st.session_state.hub
    setup_page()
    stage_3_df = filter_data(df=st.session_state.reviews_df, stage=3)
    initialize_session_state(stage_3_df)
    scroll_to_top()
    st.markdown(
        "<h1 style='text-align: center;'>Stage 3: Back to Solo, But Stronger 💪</h1>",
        unsafe_allow_html=True
    )

    total = len(stage_3_df)
    current = st.session_state.stage_3_current_review

    # Check if all reviews are done
    if current >= len(stage_3_df):
        st.success("Stage 3 completed! 🎉")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Proceed to Game Completion Page", width="stretch"):
                st.switch_page("post_treatment_survey.py")
        st.stop()

    # Display review and questions
    row = stage_3_df.iloc[current]
    review_text = row["review_text"]
    review_id = int(row["review_id"])

    saved_from_db = get_response(
        user_id=st.session_state.user_id,
        review_id=review_id,
        response_service=hub.response_service
    )

    # Fall back to session_state if nothing in DB, or use DB as priority
    saved_answers = saved_from_db or st.session_state.stage_3_answers[current]

    display_review(review_text, current, total)
    decision, certainty, likelihood = render_questions(current, saved_answers)

    current_answers = {
        "decision": decision,
        "certainty": certainty,
        "likelihood": likelihood
    }

    handle_navigation(current, total, current_answers, review_id, hub)


if __name__ == "__main__":
    main()
    
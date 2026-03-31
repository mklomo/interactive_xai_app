import streamlit as st
from streamlit_scroll_to_top import scroll_to_here
from typing import Dict, Optional
import altair as alt
import pandas as pd
from backend.filter_data import filter_data
from backend.static_exp import get_static_explanation_data, clean_feature_names, get_feature_df
from backend.response import Response

# ──────────────────────────────────────────────────────────────────────────────
#                           PAGE SETUP & SCROLL
# ──────────────────────────────────────────────────────────────────────────────

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

def scroll_to_top():
    if 'scroll_trigger' not in st.session_state:
        st.session_state.scroll_trigger = False
    if st.session_state.scroll_trigger:
        scroll_to_here(0, key="top_scroll")
        st.session_state.scroll_trigger = False

# ──────────────────────────────────────────────────────────────────────────────
#                        SESSION STATE & DATA
# ──────────────────────────────────────────────────────────────────────────────

def initialize_session_state(df):
    # Initialize the current session
    if "stage_2_current_review" not in st.session_state:
        st.session_state.stage_2_current_review = 0
    # Create answers 
    if "stage_2_answers" not in st.session_state:
        st.session_state.stage_2_answers = [{} for _ in range(len(df))]
    # Create the sub-step
    if "stage_2_sub_step" not in st.session_state:
        st.session_state.stage_2_sub_step = ["initial"] * len(df)

# ──────────────────────────────────────────────────────────────────────────────
#                               UI COMPONENTS
# ──────────────────────────────────────────────────────────────────────────────

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

def render_initial_questions(current: int, saved: dict):
    st.markdown("<h3>Is this review ✅ Genuine or ❌ Deceptive?</h3>", unsafe_allow_html=True)
    col_left, col_center, col_right = st.columns([2, 1, 2])
    with col_center:
        decision_options = [":green[Genuine]", ":red[Deceptive]"]
        preselected = None
        if saved.get("initial_decision") == "Genuine":
            preselected = 0
        elif saved.get("initial_decision") == "Deceptive":
            preselected = 1
        raw_decision = st.radio(
            label="Initial Decision",
            options=decision_options,
            index=preselected,
            horizontal=True,
            label_visibility="hidden",
            key=f"stage_2_init_dec_{current}"
        )
        decision = raw_decision.split("[")[1].split("]")[0] if raw_decision else None

    # Certainty
    st.markdown("<h3>How certain are you in your decision? (1 = Very uncertain, 7 = Very certain)</h3>", unsafe_allow_html=True)
    certainty = st.slider(
        "Certainty", 0, 7,
        # Default to 0
        value=saved.get("initial_certainty", 0),
        label_visibility="hidden",
        key=f"stage_2_init_cert_{current}"
    )

    st.markdown("<h3>If you were booking a trip right now, how likely would you choose this hotel? (1 = Not at all, 7 = Very likely)</h3>", unsafe_allow_html=True)
    likelihood = st.slider(
        "Likelihood", 0, 7,
        # Default 0
        value=saved.get("initial_likelihood", 0),
        label_visibility="hidden",
        key=f"stage_2_init_like_{current}"
    )

    return {
        "initial_decision": decision,
        "initial_certainty": certainty,
        "initial_likelihood": likelihood
    }



def render_agent_recommendation(current: int, stage_2_df):
    st.subheader("About Review")
    feature_imp_dict = get_static_explanation_data(df=stage_2_df.iloc[[current]])
    chart_data = clean_feature_names(feature_imp_dict)
    chart_data = chart_data.sort_values(by='score', ascending=False)
    full_features = chart_data["feature"].to_list()
    full_df = get_feature_df(stage_2_df)
    mins = full_df[full_features].min()
    maxs = full_df[full_features].max()
    means = full_df[full_features].mean().round(2)
    feature_values = [full_df.iloc[current][feat] for feat in full_features]

    label_dict = {
        "Analytic Writing Style of the Review": ["less formal and complex", "more formal and complex"],
        "Proportion of Adjectives in the Review": ["less descriptive and detailed", "more descriptive and detailed"],
        "Readability of the Review": ["less readable", "more readable"],
        "Emotional Content in the Review": ["low emotional content", "high emotional content"]
    }

    col1, col2 = st.columns(2)

    # ── Left column ── features 0 and 1
    left_charts = []
    for j in [0, 1]:
        feature_name = full_features[j]
        low_label, high_label = label_dict[feature_name]

        data = pd.DataFrame({
            'feature': [feature_name],
            'min_val': [0],
            'max_val': [maxs[feature_name]],
            'mean_val': [means[feature_name]],
            'value': [feature_values[j]],
            'global_min': [mins[feature_name]]
        })

        background = alt.Chart(data).mark_rect(
            opacity=0.3, color='#0E1117', stroke='#FAFAFA', strokeWidth=1
        ).encode(
            x=alt.X('min_val:Q', title='',
                    scale=alt.Scale(domain=[0, data['max_val'][0]], nice=False),
                    axis=alt.Axis(
                        values=[0, data['max_val'][0]],
                        labelExpr=f"datum.value === 0 ? '{low_label}' : '{high_label}'",
                        labelFontSize=18, tickSize=10, tickWidth=3, tickColor='#FAFAFA',
                        labelColor='#FAFAFA', domainColor='#FAFAFA', domainWidth=2,
                        labelLimit=0
                    )),
            x2='max_val:Q',
            y=alt.Y('feature:N', title=None, axis=None)
        )

        foreground = alt.Chart(data).mark_rect(
            color='white', stroke='#FAFAFA', strokeWidth=2
        ).encode(
            x='min_val:Q', x2='value:Q', y=alt.Y('feature:N', title=None, axis=None)
        )

        # Average line – Vivid Fuchsia, extended length
        avg_rule = alt.Chart(data).mark_rule(
            color='#FF00CC',  # Vivid Fuchsia
            size=3,
            strokeDash=[6, 3] # Slightly longer dashes for a bolder look
        ).encode(
            x='mean_val:Q',
            y=alt.value(-15), # Extends 15px ABOVE the bar area
            y2=alt.value(55)  # Extends 15px BELOW the bar area (40 + 15)
        )

        # Text label "avg" moved up to accommodate the longer line
        avg_label = alt.Chart(data).mark_text(
            align='center',
            baseline='bottom',
            dy=-35,                # Pushed slightly higher
            color='#FF00CC',
            fontSize=16,
            fontWeight='bold'
        ).encode(
            x='mean_val:Q',
            y=alt.Y('feature:N', title=None, axis=None),
            text=alt.value("avg")
        )

        # Layering order ensures the rule and label are on top
        layered_chart = (background + foreground + avg_rule + avg_label).properties(
            width='container',
            height=40,
            title=alt.TitleParams(text=feature_name, fontSize=24)
        )

        left_charts.append(layered_chart)

    left_vis = alt.vconcat(*left_charts, spacing=20).resolve_scale(x='independent')

    with col1:
        st.altair_chart(left_vis, use_container_width=True, theme='streamlit')

    # ── Right column ── features 2 and 3
    right_charts = []
    for j in [2, 3]:
        feature_name = full_features[j]
        low_label, high_label = label_dict[feature_name]

        data = pd.DataFrame({
            'feature': [feature_name],
            'min_val': [0],
            'max_val': [maxs[feature_name]],
            'mean_val': [means[feature_name]],
            'value': [feature_values[j]],
            'global_min': [mins[feature_name]]
        })

        background = alt.Chart(data).mark_rect(
            opacity=0.3, color='#0E1117', stroke='#FAFAFA', strokeWidth=1
        ).encode(
            x=alt.X('min_val:Q', title='',
                    scale=alt.Scale(domain=[0, data['max_val'][0]], nice=False),
                    axis=alt.Axis(
                        values=[0, data['max_val'][0]],
                        labelExpr=f"datum.value === 0 ? '{low_label}' : '{high_label}'",
                        labelFontSize=18, tickSize=10, tickWidth=3, tickColor='#FAFAFA',
                        labelColor='#FAFAFA', domainColor='#FAFAFA', domainWidth=2,
                        labelLimit=0
                    )),
            x2='max_val:Q',
            y=alt.Y('feature:N', title=None, axis=None)
        )

        foreground = alt.Chart(data).mark_rect(
            color='white', stroke='#FAFAFA', strokeWidth=2
        ).encode(
            x='min_val:Q', x2='value:Q', y=alt.Y('feature:N', title=None, axis=None)
        )

        # Average line – Vivid Fuchsia, extended length
        avg_rule = alt.Chart(data).mark_rule(
            color='#FF00CC',  # Vivid Fuchsia
            size=3,
            strokeDash=[6, 3] # Slightly longer dashes for a bolder look
        ).encode(
            x='mean_val:Q',
            y=alt.value(-15), # Extends 15px ABOVE the bar area
            y2=alt.value(55)  # Extends 15px BELOW the bar area (40 + 15)
        )

        # Text label "avg" moved up to accommodate the longer line
        avg_label = alt.Chart(data).mark_text(
            align='center',
            baseline='bottom',
            dy=-35,                # Pushed slightly higher
            color='#FF00CC',
            fontSize=16,
            fontWeight='bold'
        ).encode(
            x='mean_val:Q',
            y=alt.Y('feature:N', title=None, axis=None),
            text=alt.value("avg")
        )

        layered_chart = (background + foreground + avg_rule + avg_label).properties(
            width='container',
            height=40,
            title=alt.TitleParams(text=feature_name, fontSize=24)
        )

        right_charts.append(layered_chart)

    right_vis = alt.vconcat(*right_charts, spacing=20).resolve_scale(x='independent')

    with col2:
        st.altair_chart(right_vis, use_container_width=True, theme='streamlit')

    st.markdown("<h3>🤖 Review Agent’s Recommendation</h3>", unsafe_allow_html=True)
    agent_recommendation = stage_2_df.iloc[current]["ebm_prediction"]
    st.markdown(
        f"""
        <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background-color: #0E1117; font-size: 25px; text-align: center;">
            Based on the review features above, the 🤖Review Agent suggests this review is <strong>{agent_recommendation}</strong>.
        </div>
        <div style="margin-bottom: 20px;"></div>
        """,
        unsafe_allow_html=True
    )

    
def render_final_questions(current: int, saved: dict):
    st.markdown("<h3>What is your final decision?</h3>", unsafe_allow_html=True)
    col_left, col_center, col_right = st.columns([2, 1, 2])
    with col_center:
        decision_options = [":green[Genuine]", ":red[Deceptive]"]
        preselected = None
        if saved.get("final_decision") == "Genuine":
            preselected = 0
        elif saved.get("final_decision") == "Deceptive":
            preselected = 1
        raw_decision = st.radio(
            label="Final Decision",
            options=decision_options,
            index=preselected,
            horizontal=True,
            label_visibility="hidden",
            key=f"stage_2_final_dec_{current}"
        )
        decision = raw_decision.split("[")[1].split("]")[0] if raw_decision else None

    st.markdown("<h3>How certain are you in your final decision? (1 = Very uncertain, 7 = Very certain)</h3>", unsafe_allow_html=True)
    certainty = st.slider(
        "Final Certainty", 0, 7,
        value=saved.get("final_certainty", 0),
        label_visibility="hidden",
        key=f"stage_2_final_cert_{current}"
    )

    st.markdown("<h3>If you were booking a trip right now, how likely would you choose this hotel? (1 = Not at all, 7 = Very likely)</h3>", unsafe_allow_html=True)
    likelihood = st.slider(
        "Final Likelihood", 0, 7,
        value=saved.get("final_likelihood", 0),
        label_visibility="hidden",
        key=f"stage_2_final_like_{current}"
    )

    st.markdown("<h3>How much did the agent's recommendation influence your final decision? (1 = Not at all, 7 = Very much)</h3>", unsafe_allow_html=True)
    influence = st.slider(
        "Influence", 0, 7,
        value=saved.get("influence_rating", 0),
        label_visibility="hidden",
        key=f"stage_2_influence_{current}"
    )

    saved_initial = saved.get("initial_decision")
    if decision is None:
        label = "Please describe how the agent's recommendation informed your final decision [OPTIONAL]"
    elif decision != saved_initial:
        label = "Please describe how the agent's recommendation helped you change your initial decision [OPTIONAL]"
    else:
        label = "Please describe how the agent's recommendation helped you keep your initial decision [OPTIONAL]"

    st.markdown(f"<h4>{label}</h4>", unsafe_allow_html=True)
    comments = st.text_area(
        label=label,
        value=saved.get("decision_making_description", ""),
        height=120,
        label_visibility="hidden",
        key=f"stage_2_comments_{current}"
    )

    return {
        "final_decision": decision,
        "final_certainty": certainty,
        "final_likelihood": likelihood,
        "influence_rating": influence,
        "decision_making_description": comments
    }

# ──────────────────────────────────────────────────────────────────────────────
#                             DATABASE FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────

def get_response(user_id: str, review_id: int, response_service) -> Optional[Dict]:
    existing_id = response_service.get_response_id(user_id=user_id, review_id=review_id)
    if not existing_id:
        return None

    obj: Response = response_service.get_response(existing_id)
    if not obj:
        return None

    saved = {}
    if obj.initial_decision:
        saved["initial_decision"] = obj.initial_decision
    if obj.initial_certainty_rating is not None:
        saved["initial_certainty"] = obj.initial_certainty_rating
    if obj.initial_persuasion_rating is not None:
        saved["initial_likelihood"] = obj.initial_persuasion_rating

    if obj.final_decision:
        saved["final_decision"] = obj.final_decision
    if obj.final_certainty_rating is not None:
        saved["final_certainty"] = obj.final_certainty_rating
    if obj.final_persuasion_rating is not None:
        saved["final_likelihood"] = obj.final_persuasion_rating
    if obj.influence_rating is not None:
        saved["influence_rating"] = obj.influence_rating
    if obj.decision_making_description:
        saved["decision_making_description"] = obj.decision_making_description

    # print(f"Stage 2 - Loaded from DB: {saved}")
    return saved if saved else None


def save_response(review_id: int, answers: dict, hub, is_final: bool = False):
    user_id = st.session_state.user_id
    existing_id = hub.response_service.get_response_id(user_id=user_id, review_id=review_id)

    data = {
        "user_id": user_id,
        "review_id": review_id,
        "initial_decision": answers.get("initial_decision"),
        "initial_certainty_rating": answers.get("initial_certainty"),
        "initial_persuasion_rating": answers.get("initial_likelihood"),
    }

    if is_final:
        data.update({
            "final_decision": answers.get("final_decision"),
            "final_certainty_rating": answers.get("final_certainty"),
            "final_persuasion_rating": answers.get("final_likelihood"),
            "influence_rating": answers.get("influence_rating"),
            "decision_making_description": answers.get("decision_making_description"),
        })

    obj = Response(**data)

    if existing_id:
        hub.response_service.update_response(existing_id, obj)
    else:
        hub.response_service.create_response(obj)

# ──────────────────────────────────────────────────────────────────────────────
#                               NAVIGATION
# ──────────────────────────────────────────────────────────────────────────────

def handle_navigation(current: int, total: int, sub_step: str, answers: dict, review_id: int, hub):

    if sub_step == "initial":
        col1, col2, col3 = st.columns(3)
        with col1:
            if current > 0:
                if st.button("← Previous", width="stretch"):
                    st.session_state.stage_2_current_review -= 1
                    st.session_state.scroll_trigger = True
                    st.rerun()

        col = col3 if current > 0 else col2
        with col:
            if st.button("Submit Initial Decision → Agent", width="stretch"):
                if not answers.get("initial_decision"):
                    st.error("Please select Genuine or Deceptive.")
                    return
                if answers.get("initial_certainty", 0) < 1:
                    st.error("Please select certainty level (1–7).")
                    return
                if answers.get("initial_likelihood", 0) < 1:
                    st.error("Please select likelihood (1–7).")
                    return

                st.session_state.stage_2_answers[current].update(answers)
                save_response(review_id, answers, hub, is_final=False)
                st.session_state.stage_2_sub_step[current] = "agent"
                st.session_state.scroll_trigger = True
                st.rerun()

    elif sub_step == "agent":
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("Proceed to Final Decision →", width="stretch"):
                st.session_state.stage_2_sub_step[current] = "final"
                # st.session_state.scroll_trigger = True
                st.rerun()

    elif sub_step == "final":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Agent", width="stretch"):
                st.session_state.stage_2_sub_step[current] = "agent"
                st.session_state.scroll_trigger = True
                st.rerun()

        with col2:
            label = "Finish Stage 2 & Submit" if current == total - 1 else "Next Review →"
            if st.button(label, width="stretch"):
                if not answers.get("final_decision"):
                    st.error("Please select final decision.")
                    return
                if answers.get("final_certainty", 0) < 1:
                    st.error("Please select final certainty (1–7).")
                    return
                if answers.get("final_likelihood", 0) < 1:
                    st.error("Please select final likelihood (1–7).")
                    return
                if answers.get("influence_rating", 0) < 1:
                    st.error("Please select influence level (1–7).")
                    return

                st.session_state.stage_2_answers[current].update(answers)
                save_response(review_id, answers, hub, is_final=True)
                st.session_state.stage_2_current_review += 1
                st.session_state.scroll_trigger = True
                st.rerun()

# ──────────────────────────────────────────────────────────────────────────────
#                                 MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    hub = st.session_state.hub
    setup_page()
    scroll_to_top()
    stage_2_df = filter_data(df=st.session_state.reviews_df, stage=2)
    initialize_session_state(stage_2_df)
    
    st.markdown("<h1>Stage 2: Team-Up with 🤖Review Agent 🤝</h1>", unsafe_allow_html=True)

    total = len(stage_2_df)
    current = st.session_state.stage_2_current_review
    # print(f"This is the DF ---> {stage_2_df}")
    if current >= total:
        st.success("Stage 2 completed successfully! 🎉. Please proceed to Stage 3")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Proceed to Stage 3", width="stretch"):
                st.switch_page("pages/stage_3_intro.py")
        st.stop()

    row = stage_2_df.iloc[current]
    review_text = row["review_text"]
    review_id = int(row["review_id"])

    saved_from_db = get_response(
        user_id=st.session_state.user_id,
        review_id=review_id,
        response_service=hub.response_service
    )
    saved_answers = saved_from_db or st.session_state.stage_2_answers[current]

    display_review(review_text, current, total)

    sub_step = st.session_state.stage_2_sub_step[current]
    answers = {}

    if sub_step == "initial":
        answers = render_initial_questions(current, saved_answers)
    elif sub_step in ["agent", "final"]:
        render_agent_recommendation(current, stage_2_df)
        if sub_step == "final":
            answers = render_final_questions(current, saved_answers)

    handle_navigation(current, total, sub_step, answers, review_id, hub)

if __name__ == "__main__":
    main()
import streamlit as st


all_pages = {
    "welcome": st.Page("pages/welcome.py", title="Welcome", icon=":material/home:"),
    "login": st.Page("pages/login.py", title="Log in", icon=":material/login:"),
    "signup": st.Page("pages/signup.py", title="Sign up", icon=":material/login:"),
    "pre_treatment_survey": st.Page("pages/pre_treatment_survey.py", title="Survey", icon=":material/home:"),
    "post_treatment_survey": st.Page("pages/post_treatment_survey.py", title="Survey", icon=":material/home:"),
    "stage_1": st.Page("pages/stage_1.py", title="Stage 1", icon=":material/quiz:"),
    "stage_2_intro": st.Page("pages/stage_2_intro.py", title="Welcome to Stage 2", icon=":material/quiz:"),
    "stage_2_baseline": st.Page("pages/stage_2_baseline.py", title="Welcome to Stage 2", icon=":material/quiz:"),
    "stage_2_static_explanation": st.Page("pages/static_explanation.py", title="Welcome to Stage 2", icon=":material/quiz:"),
    "stage_2_nat_lang_explanation": st.Page("pages/nat_lang_exp.py", title="Welcome to Stage 2", icon=":material/quiz:"),
    "stage_2_dialogue_based_explanation": st.Page("pages/dialogue_based_explanation.py", title="Welcome to Stage 2", icon=":material/quiz:"),
    "stage_2_dialogue_based_explanation_2": st.Page("pages/dialogue_based_explanation_2.py", title="Welcome to Stage 2", icon=":material/quiz:"),
    "stage_3_intro": st.Page("pages/stage_3_intro.py", title="Welcome to Stage 3", icon=":material/home:"),
    "stage_3": st.Page("pages/stage_3.py", title="Stage 3", icon=":material/quiz:"),
    "logout": st.Page("pages/logout.py", title="Log out", icon=":material/logout:"),
    "completion": st.Page("pages/completion.py", title="Thank You Page", icon=":material/logout:")
}
import pandas as pd
from pathlib import Path
import streamlit as st

# Get the path for the current file
BASE_DIR = Path(__file__).resolve().parent

# Create the respective paths
STAGE_DATA_PATH= BASE_DIR / "data/stages_data/full_stage_df.csv" 


@st.cache_data(show_spinner="Reading review data",ttl="1d")
def load_data():
    """Load the Dataset for the study"""
    df = pd.read_csv(STAGE_DATA_PATH)
    # round all numeric data to 2dp
    numeric_cols = df.select_dtypes("number").columns
    df[numeric_cols] = df[numeric_cols].round(3)
    return df
    
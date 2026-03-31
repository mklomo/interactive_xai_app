import joblib
import pandas as pd
import numpy as np

features = ["proportion_of_emotional_content_in_review", "proportion_of_adjectives_in_review", "readability_of_review", "analytic_writing_style"]


remap_dict = {
    "proportion_of_emotional_content_in_review": "Emotional Content in the Review", 
    "proportion_of_adjectives_in_review": "Proportion of Adjectives in the Review", 
    "readability_of_review": "Readability of the Review", 
    "analytic_writing_style": "Analytic Writing Style of the Review",
}


# for app
ebm_model_path = "backend/ml_training/ebm_classifier_trained_on_09_12_2025.joblib"


# Load the model
ebm_model = joblib.load(ebm_model_path)

def get_static_explanation_data(df, feature_names=features):
    X = df[features]
    local_explanation = ebm_model.explain_local(X)
    feature_contributions = local_explanation.data(0)['scores']
    feature_contributions = [np.round(feat_cont, 3) for feat_cont in feature_contributions]
    feature_names = local_explanation.data(0)['names'] 
    static_exp = {}

    for idx in range(len(feature_names)):
        static_exp[feature_names[idx]] = feature_contributions[idx]
    return static_exp


def clean_feature_names(df_dict, remap_dict=remap_dict):
    # Convert the dictionary to a df
    chart_df = pd.DataFrame(list(df_dict.items()), columns=['feature', 'score'])
    # MAP the new feature names
    chart_df = (
        chart_df
        .assign(
            feature = lambda df_: df_["feature"].map(remap_dict)
        ))
    return chart_df


def get_feature_df(df):
    # Convert the dictionary to a df
    df = (
        df[features]
        # rename dict 
        .rename(columns=remap_dict)
    )
    return df




    
    
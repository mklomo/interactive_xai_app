import pandas as pd


def filter_data(stage:int, df):
    mask = df["stage"].eq(stage)
    return df.loc[mask]


def filter_explanations(df, review_id):
    mask = df["review_id"].eq(review_id)
    return df.loc[mask]["natural_language_explanation"].item()
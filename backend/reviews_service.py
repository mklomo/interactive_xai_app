from backend.reviews import Review
import pandas as pd


class ReviewService:
    def __init__(self, database):
        self.database = database

    def get_reviews(self):
        # Read all the records in the DB
        query = "SELECT * FROM reviews"
        results = self.database.execute_query(query)
        columns = [
            "review_id",
            "review_text",
            "proportion_of_emotional_content_in_review",
            "proportion_of_adjectives_in_review",
            "readability_of_review",
            "analytic_writing_style",
            "ebm_prediction",
            "mis_classified",
            "model_pred_confidence",
            "stage"
        ]
        raw_df = pd.DataFrame(results, columns=columns)
        app_df = (raw_df.drop(columns=["mis_classified", "model_pred_confidence"])).round(3)
        return app_df
        
        
        

        
        
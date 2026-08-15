from backend.reviews import Review
import pandas as pd


class ReviewService:
    def __init__(self, database):
        self.database = database

    # Columns are named explicitly rather than using SELECT *, so that adding
    # a column to the table cannot silently shift the DataFrame's columns.
    COLUMNS = [
        "review_id",
        "review_text",
        "proportion_of_emotional_content_in_review",
        "proportion_of_adjectives_in_review",
        "readability_of_review",
        "analytic_writing_style",
        "ebm_prediction",
        "mis_classified",
        "model_pred_confidence",
        "stage",
        "review_set",
    ]

    # Never sent to the participant-facing pages
    HIDDEN_COLUMNS = ["mis_classified", "model_pred_confidence"]

    def get_reviews(self, review_set=None):
        """Reviews for one participant: Stage 1 + their Stage-2 set + Stage 3.

        Stage 1 and Stage 3 rows carry review_set = 0 and are shared by
        everyone; Stage 2 rows carry the set they belong to. Filtering here
        rather than in each page means a participant's session only ever
        holds the 28 reviews they will actually see, so it is not possible
        for a page to display the wrong set.

        review_set=None returns every set - for admin views only.
        """
        query = f"SELECT {', '.join(self.COLUMNS)} FROM reviews"
        params = {}

        if review_set is None:
            # Admin view: every set. Wave-1 participants never reach here -
            # main.py routes them past Stage 2.
            pass
        else:
            query += " WHERE review_set IN (0, :review_set)"
            params = {"review_set": int(review_set)}

        results = self.database.execute_query(query, params)
        raw_df = pd.DataFrame(results, columns=self.COLUMNS)
        return raw_df.drop(columns=self.HIDDEN_COLUMNS).round(3)

    def get_reviews_full(self):
        """Includes ground-truth correctness and model confidence.

        For analysis and admin views only - never render this to participants.
        """
        query = f"SELECT {', '.join(self.COLUMNS)} FROM reviews"
        results = self.database.execute_query(query)
        return pd.DataFrame(results, columns=self.COLUMNS)

    def get_set_counts(self):
        """Sanity check: how many reviews are in each stage x set."""
        query = """
            SELECT stage, review_set, COUNT(*) AS n
            FROM reviews
            GROUP BY stage, review_set
            ORDER BY stage, review_set
        """
        results = self.database.execute_query(query)
        return pd.DataFrame(results, columns=["stage", "review_set", "n"])

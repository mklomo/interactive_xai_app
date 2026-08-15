import pandas as pd


class LanguageExplanationService:
    """Static natural-language explanations for Stage-2 reviews.

    Mirrors ReviewService: columns named explicitly, filtering done in SQL
    so a participant's session only holds what they will actually see.
    """

    def __init__(self, database):
        self.database = database

    # Named explicitly rather than SELECT *, so adding a column to the
    # table cannot shift the DataFrame's columns.
    COLUMNS = ["review_id", "natural_language_explanation"]

    def get_explanations(self, review_set=None):
        """Explanations for one participant's Stage-2 set.

        languageexplanations has no review_set column - an explanation
        inherits its set through review_id - so the filter joins `reviews`
        to reach it.

        Explanations exist only for stage 2, and only for sets still in
        collection. Set 0 (Stages 1 and 3) presents no AI advice and so
        has none; it is included in the IN clause purely to mirror
        ReviewService.get_reviews and stay correct if that ever changes.

        review_set=None returns every set, for admin views only.
        """
        cols = ", ".join(f"le.{c}" for c in self.COLUMNS)

        if review_set is None:
            query = f"SELECT {cols} FROM languageexplanations le"
            params = {}
        else:
            query = f"""
                SELECT {cols}
                FROM languageexplanations le
                JOIN reviews r ON r.review_id = le.review_id
                WHERE r.review_set IN (0, :review_set)
            """
            params = {"review_set": int(review_set)}

        results = self.database.execute_query(query, params)
        return pd.DataFrame(results, columns=self.COLUMNS)

    def get_coverage(self):
        """Which Stage-2 reviews still lack an explanation.

        filter_explanations() raises when a review has no explanation, so
        a gap here is a Stage-2 crash for whoever draws that set. Worth
        checking after loading a new set rather than discovering it live.
        """
        query = """
            SELECT r.review_set,
                   COUNT(*)            AS reviews,
                   COUNT(le.review_id) AS explanations
            FROM reviews r
            LEFT JOIN languageexplanations le ON le.review_id = r.review_id
            WHERE r.stage = 2
            GROUP BY r.review_set
            ORDER BY r.review_set
        """
        results = self.database.execute_query(query)
        return pd.DataFrame(results,
                            columns=["review_set", "reviews", "explanations"])

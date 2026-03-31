from backend.nat_lang_exp import LanguageExplanations   
import pandas as pd


class LanguageExplanationService:
    """
    Service for the natural language explanations (LanguageExplanations table).
    Mirrors the exact structure and style of your ReviewService.
    """

    def __init__(self, database):
        self.database = database

    def get_explanations(self):
        """
        Read all records from the LanguageExplanations table
        and return a cleaned pandas DataFrame ready for the app.
        """
        # Query the PostgreSQL table (quoted name to match your CREATE TABLE)
        query = "SELECT review_id, natural_language_explanation FROM LanguageExplanations"
        
        results = self.database.execute_query(query)
        
        # Columns exactly as defined in your dataclass + table
        columns = [
            "review_id",
            "natural_language_explanation",
        ]
        app_df = pd.DataFrame(results, columns=columns)
        return app_df
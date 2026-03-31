from dataclasses import dataclass
from typing import Optional

@dataclass
class LanguageExplanations:
    review_id: int                       # SERIAL PRIMARY KEY, auto-incremented
    review_text: str                                      # TEXT NOT NULL
    proportion_of_emotional_content_in_review: Optional[float] = None   # DOUBLE PRECISION
    proportion_of_adjectives_in_review: Optional[float] = None         # DOUBLE PRECISION
    readability_of_review: Optional[float] = None                      # DOUBLE PRECISION
    analytic_writing_style: Optional[float] = None                     # DOUBLE PRECISION
    ebm_prediction: Optional[str] = None                               # VARCHAR(10), e.g., 'Genuine' or 'Deceptive'
    model_prediction: Optional[str] = None                             # VARCHAR(10), actual EBM prediction
    natural_language_explanation: Optional[str] = None                 # TEXT
    feature_contributions: Optional[dict] = None                       # JSON
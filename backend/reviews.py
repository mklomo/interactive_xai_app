from dataclasses import dataclass
from typing import Optional

@dataclass
class Review:
    review_text: str  # TEXT NOT NULL
    review_id: Optional[int] = None  # SERIAL PRIMARY KEY, auto-incremented
    proportion_of_emotional_content_in_review: Optional[float] = None  # DOUBLE PRECISION
    proportion_of_adjectives_in_review: Optional[float] = None  # DOUBLE PRECISION
    readability_of_review: Optional[float] = None  # DOUBLE PRECISION
    analytic_writing_style: Optional[float] = None  # DOUBLE PRECISION
    ebm_prediction: Optional[str] = None  # VARCHAR(10), e.g., 'Genuine' or 'Deceptive'
    mis_classified: Optional[bool] = None  # BOOLEAN
    model_pred_confidence: Optional[float] = None  # DOUBLE PRECISION
    stage: Optional[int] = None  # INTEGER
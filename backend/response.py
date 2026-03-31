from dataclasses import dataclass
from typing import Optional

@dataclass
class Response:
    user_id: int  # INTEGER NOT NULL, FOREIGN KEY to Users
    review_id: int  # INTEGER NOT NULL, FOREIGN KEY to Reviews
    final_decision: Optional[str] = None # VARCHAR(10) NOT NULL, 'Genuine' or 'Deceptive'
    final_certainty_rating: Optional[int] = None  # INTEGER CHECK BETWEEN 0 AND 7
    final_persuasion_rating: Optional[int] = None  # INTEGER CHECK BETWEEN 0 AND 7
    initial_decision: Optional[str] = None # VARCHAR(10) NOT NULL, 'Genuine' or 'Deceptive'
    response_id: Optional[int] = None  # SERIAL PRIMARY KEY, auto-incremented
    initial_certainty_rating: Optional[int] = None  # INTEGER CHECK BETWEEN 0 AND 7
    initial_persuasion_rating: Optional[int] = None  # INTEGER CHECK BETWEEN 0 AND 7
    influence_rating: Optional[int] = None  # INTEGER CHECK BETWEEN 0 AND 7
    decision_making_description: Optional[str] = None  # TEXT
    verification_queries_and_responses: Optional[str] = None  # TEXT



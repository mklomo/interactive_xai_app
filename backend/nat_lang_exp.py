from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LanguageExplanations:
    """One static explanation, keyed to a review.

    Mirrors the table as rebuilt by migration 005. Note this class is not
    currently constructed anywhere - LanguageExplanationService returns a
    DataFrame - so it serves as schema documentation. Keep it accurate
    anyway: if anything ever does `LanguageExplanations(*row)`, a stale
    field order breaks it silently, which is exactly what happened to
    get_user() when a column was added to `users`.
    """

    # NOT a SERIAL. Always the review_id of an existing row in `reviews`,
    # never generated here. This is what ties an explanation to a
    # review_set - explanations carry no review_set of their own and
    # inherit it through this key. The old notebook assumed SERIAL and
    # renumbered rows 1..n, which would have mis-keyed every explanation.
    review_id: int                                       # BIGINT PK, FK -> reviews

    review_text: str                                     # TEXT NOT NULL

    proportion_of_emotional_content_in_review: Optional[float] = None  # DOUBLE PRECISION
    proportion_of_adjectives_in_review: Optional[float] = None         # DOUBLE PRECISION
    readability_of_review: Optional[float] = None                      # DOUBLE PRECISION
    analytic_writing_style: Optional[float] = None                     # DOUBLE PRECISION

    ebm_prediction: Optional[str] = None    # verdict stored on the review
    model_prediction: Optional[str] = None  # verdict recomputed at generation
    # A CHECK constraint requires these two to agree when both are present.

    natural_language_explanation: Optional[str] = None   # TEXT NOT NULL, non-blank

    # JSONB, not TEXT. Local feature contributions for THIS review -
    # feature effects specific to one observation, not global feature
    # importances. Worth keeping the distinction in the write-up.
    feature_contributions: Optional[dict] = None

    # Provenance. Wave 1 was written by an earlier EBM via Cohere; wave 2
    # by the deterministic template. Without this, which model produced
    # which explanation is unrecoverable after a regeneration.
    generator_model: Optional[str] = None                # TEXT
    generated_at: Optional[datetime] = None              # TIMESTAMPTZ NOT NULL

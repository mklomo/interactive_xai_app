import pandas as pd


SHARED_SET = 0  # Stage 1 and Stage 3 reviews are seen by every participant


def filter_data(stage: int, df, review_set: int | None = None):
    """Return the reviews for a stage, restricted to the participant's set.

    Stage 1 and Stage 3 rows carry review_set = 0 and are shared by everyone.
    Stage 2 rows carry review_set = 1..n; a participant sees only their own.

    Passing review_set=None returns every set for that stage, which is what
    the admin views want.
    """
    mask = df["stage"].eq(stage)

    if review_set is not None and "review_set" in df.columns:
        mask &= df["review_set"].isin([SHARED_SET, review_set])

    return df.loc[mask]


def filter_explanations(df, review_id):
    """The static explanation for one review.

    Explanations exist only for Stage-2 reviews in sets that are still in
    collection. Wave 1 is closed, so set 1 has none.

    A missing explanation is raised rather than returned as blank on
    purpose. Rendering an empty explanation would leave the participant in
    the explanation condition with no explanation, which silently corrupts
    that trial - far worse than a visible failure. .item() would also raise
    here, but with pandas' "array of size 1" message, which says nothing
    about which review or why.
    """
    matches = df.loc[df["review_id"].eq(review_id), "natural_language_explanation"]

    if len(matches) == 1:
        return matches.item()

    if matches.empty:
        raise LookupError(
            f"No explanation for review_id {review_id}. Stage 2 cannot be "
            f"shown without one. If this is a wave-1 participant, they should "
            f"not have reached Stage 2 - wave 1 is closed and set 1 has no "
            f"explanations. Otherwise run ml_training/generate_nl_explanations.py."
        )

    raise LookupError(
        f"{len(matches)} explanations for review_id {review_id}; expected 1. "
        f"Migration 005 makes review_id the primary key, so this means the "
        f"table predates it."
    )

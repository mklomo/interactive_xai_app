import numpy as np
import pandas as pd


SHARED_SET = 0  # Stage 1 and Stage 3 reviews are seen by every participant


def shuffle_stage_2(df, user_id, stage=2):
    """Randomise Stage-2 trial order for one participant.

    Applied once at login, after the review set is known, so the order is
    stable for the whole session.

    Why shuffle at all
    ------------------
    Without it every participant in a set sees the same twelve reviews in
    the same order, so each item sits at exactly one serial position and
    the two cannot be separated: an unusual result on review 9 could be
    the item or could be fatigue by trial 9. Randomising decorrelates
    them, which matters for the item random effect in the
    recommendation-direction analysis.

    Why the constraint is on DIRECTION only
    ---------------------------------------
    Participants receive no correctness feedback at any point -
    mis_classified is stripped in ReviewService.HIDDEN_COLUMNS and never
    reaches a page. So a run of AI errors is not observable AS errors;
    the participant simply sees recommendations. Balancing error
    placement across halves would guard against a trust trajectory the
    participant has no way to perceive, so it is not constrained here.

    Recommendation direction is different: every verdict is shown. Six
    consecutive 'Deceptive' verdicts is a visible pattern, and supports
    an inference like "this agent flags everything as fake" that can
    change how the remaining trials are weighed. That needs no feedback,
    so it is worth blocking.

    The whole block is permuted and kept only if each half holds half the
    Deceptive verdicts, so any review can land in either half - unlike
    permuting inside fixed halves, which leaves each item stuck where it
    was loaded and keeps item confounded with half.

    Rejection sampling rather than construction: uniform over the valid
    orders by definition, and easy to verify. Roughly 43% of the 12!
    permutations qualify, so it accepts within a couple of draws.

    Why seeded on user_id
    ---------------------
    Participants can resume. Resume looks responses up by review_id, so a
    fresh random order on a second login would put them at the right index
    but the wrong review. A seed fixed to the participant makes the order
    identical across logins, and reproducible at analysis time without
    storing anything.
    """
    mask = df["stage"].eq(stage)
    s2 = df[mask]
    if len(s2) < 2:
        return df

    rng = np.random.default_rng(int(user_id))
    order = _balanced_permutation(s2, rng)

    return pd.concat([
        df[df["stage"] < stage],
        s2.loc[order],
        df[df["stage"] > stage],
    ]).reset_index(drop=True)


def _balanced_permutation(s2, rng, max_attempts=500):
    """Permute the block, keeping recommendation direction even by half.

    Only direction is constrained - see shuffle_stage_2 for why error
    placement is not. Error position is left free, which also means an
    early run of AI errors remains possible and analysable rather than
    designed out.

    The target is derived from the block, not hardcoded, so this also
    works on set 1 (the 75% set, 7 Deceptive) where no even split exists;
    floor or ceil is accepted, the closest to even available.

    Falls back to a free permutation if nothing qualifies, which cannot
    happen for these sets but keeps the function total.
    """
    n = len(s2)
    half = n // 2

    if "ebm_prediction" not in s2.columns:
        return list(rng.permutation(s2.index))

    dec = (s2["ebm_prediction"].to_numpy() == "Deceptive")
    total = dec.sum()
    targets = (total // 2, (total + 1) // 2)

    idx = np.arange(n)
    for _ in range(max_attempts):
        perm = rng.permutation(idx)
        if dec[perm[:half]].sum() in targets:
            return list(s2.index[perm])

    return list(rng.permutation(s2.index))


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

"""Diagnose disagreement between stored ebm_prediction and the live model.

Read-only. Writes nothing.

The stored ebm_prediction is the stimulus - it is the verdict the
participant is shown, and mis_classified (and therefore the 3 TP / 3 FP /
3 TN / 3 FN balance of every set) is derived from it. So a disagreement is
not automatically a data error; it may just mean the stored features are
rounded relative to what the model was trained on.

What matters is how close to the decision boundary the review sits:

  * probability far from 0.5  -> the stored verdict is genuinely wrong,
                                 or the features in the DB are wrong
  * probability near 0.5      -> a rounding artifact; the review is a
                                 coin-flip for the model and is a weak
                                 stimulus regardless of which way it fell

Usage:
    export DATABASE_URL=postgresql://...
    python ml_training/diagnose_predictions.py
"""

import os
import sys

import joblib
import pandas as pd
from sqlalchemy import create_engine, text

MODEL_PATH = "./ml_training/ebm_classifier_trained_on_09_12_2025.joblib"
FEATURE_COLS = [
    "proportion_of_emotional_content_in_review",
    "proportion_of_adjectives_in_review",
    "readability_of_review",
    "analytic_writing_style",
]


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("Set DATABASE_URL.")

    engine = create_engine(db_url)
    q = text(f"""
        SELECT review_id, review_set, ebm_prediction, mis_classified,
               model_pred_confidence, review_text,
               {', '.join(FEATURE_COLS)}
        FROM reviews
        WHERE stage = 2
        ORDER BY review_set, review_id
    """)
    with engine.connect() as conn:
        df = pd.read_sql(q, conn)

    ebm = joblib.load(MODEL_PATH)
    X = df[FEATURE_COLS]
    preds = ebm.predict(X)
    proba = ebm.predict_proba(X)

    genuine_ix = list(ebm.classes_).index("Genuine")
    df["recomputed"] = preds
    df["p_genuine"] = proba[:, genuine_ix]
    # Distance from the decision boundary: 0 = coin flip, 0.5 = certain
    df["margin"] = (df["p_genuine"] - 0.5).abs()

    mismatch = df[df["ebm_prediction"] != df["recomputed"]]

    print("=" * 72)
    print(f"{len(df)} Stage-2 reviews, {len(mismatch)} disagreement(s)")
    print("=" * 72)

    if mismatch.empty:
        print("\nStored verdicts all reproduce. Nothing to fix.")
    for _, r in mismatch.iterrows():
        print(f"\nreview_id {r.review_id}  (set {r.review_set})")
        print(f"  stored ebm_prediction : {r.ebm_prediction}   <- what the "
              "participant sees")
        print(f"  recomputed            : {r.recomputed}")
        print(f"  P(Genuine)            : {r.p_genuine:.4f}")
        print(f"  margin from 0.5       : {r.margin:.4f}")
        print(f"  stored confidence     : {r.model_pred_confidence:.4f}")
        print(f"  mis_classified flag   : {r.mis_classified}")
        verdict = ("ROUNDING ARTIFACT - the model is near a coin flip here"
                   if r.margin < 0.05 else
                   "NOT a boundary case - investigate the stored features")
        print(f"  -> {verdict}")
        print(f"  text: {r.review_text[:140]}...")

    # How much slack is there? A set whose other reviews are all decisive
    # can absorb one swap; a set full of boundary cases cannot.
    print("\n" + "=" * 72)
    print("Margin distribution by set (low margin = weak stimulus)")
    print("=" * 72)
    summary = df.groupby("review_set")["margin"].agg(
        n="size", min="min", median="median")
    print(summary.round(4).to_string())

    weak = df[df["margin"] < 0.05]
    if len(weak):
        print(f"\n{len(weak)} review(s) within 0.05 of the boundary "
              "(coin flips for the model, regardless of stored verdict):")
        for _, r in weak.iterrows():
            print(f"  review_id {r.review_id} (set {r.review_set}): "
                  f"P(Genuine)={r.p_genuine:.4f}, stored={r.ebm_prediction}")

    # ------------------------------------------------------------------
    # Root cause: one bad row, or the wrong model?
    # ------------------------------------------------------------------
    # model_pred_confidence was written at the same time as ebm_prediction,
    # so it records what the model said THEN. Comparing it against what the
    # model says NOW separates two very different diagnoses:
    #
    #   one row off, rest exact  -> that row's stored features are corrupt
    #                               or misaligned with its text
    #   many rows drifting       -> the stored verdicts came from a
    #                               different model than this joblib, and
    #                               nothing here can be trusted to it
    print("\n" + "=" * 72)
    print("Stored confidence vs recomputed - is it one row, or the model?")
    print("=" * 72)

    # Confidence is for whichever class was stored as the prediction
    p_stored = df.apply(
        lambda r: r.p_genuine if r.ebm_prediction == "Genuine"
        else 1 - r.p_genuine, axis=1)
    drift = (p_stored - df["model_pred_confidence"]).abs()

    print(f"  max abs drift    : {drift.max():.4f}")
    print(f"  median abs drift : {drift.median():.4f}")
    print(f"  rows > 0.01      : {(drift > 0.01).sum()} of {len(df)}")
    print(f"  rows > 0.10      : {(drift > 0.10).sum()} of {len(df)}")

    worst = df.assign(drift=drift).nlargest(5, "drift")
    print("\n  Largest drifts:")
    for _, r in worst.iterrows():
        print(f"    review_id {r.review_id} (set {r.review_set}): "
              f"stored {r.model_pred_confidence:.4f} -> now {p_stored[r.name]:.4f} "
              f"(drift {r.drift:.4f})")

    if (drift > 0.01).sum() <= 2:
        print("\n  -> Only isolated rows drift. The model is the same one that "
              "wrote these verdicts;\n     the offending row's stored features "
              "are the problem.")
    else:
        print("\n  -> Widespread drift. These verdicts were NOT produced by this "
              "joblib.\n     Find the model that wrote them before generating "
              "any explanations.")

    # ------------------------------------------------------------------
    # Design cells
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("Design cells per set, from the STORED verdict + mis_classified")
    print("=" * 72)
    cells = (df.assign(cell=df["ebm_prediction"] + "/" +
                       df["mis_classified"].map({True: "wrong", False: "right"}))
               .groupby(["review_set", "cell"]).size().unstack(fill_value=0))
    print(cells.to_string())
    print("\nSets 2-4 should read 3 in all four cells (50% accuracy).")
    print("Set 1 is the original 75% set - 9 right, 3 wrong - so 5/2/4/1 is")
    print("correct for it, not a fault. If a swap is needed in sets 2-4, the")
    print("replacement must come from the same cell to preserve the balance.")


if __name__ == "__main__":
    main()

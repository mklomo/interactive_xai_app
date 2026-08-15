"""Restore the wave-1 (set 1) explanations from the original CSV.

These are the explanations wave-1 participants actually read, produced by
the earlier EBM. Restoring them is strictly better than regenerating:

  * the current model disagrees with the stored verdict on review 12, so a
    regenerated explanation would argue for a verdict no longer supported
    by its own contributions;
  * at temperature 0.7 regeneration would not reproduce the original text
    anyway, so the delivered stimulus would become unrecoverable.

The CSV has no review_id and no stage column - the notebook that wrote it
used a bare pandas index. Rows are therefore matched to the database on
full review text.

Matching is deliberately strict. Two reviews in this corpus both begin
"I recently stayed at the InterContinental Chicago" and carry OPPOSITE
verdicts, so a prefix or fuzzy match would silently attach the wrong
explanation to the wrong review - which would invert the stimulus for
those trials rather than fail loudly.

Usage:
    export DATABASE_URL=postgresql://...
    python ml_training/load_wave1_explanations.py \
        --csv /path/to/reviews_with_explanations.csv --dry-run
    python ml_training/load_wave1_explanations.py \
        --csv /path/to/reviews_with_explanations.csv
"""

import argparse
import ast
import json
import os
import re
import sys

import pandas as pd
from sqlalchemy import create_engine, text

FEATURE_COLS = [
    "proportion_of_emotional_content_in_review",
    "proportion_of_adjectives_in_review",
    "readability_of_review",
    "analytic_writing_style",
]

# The exact model that wrote these is not recorded. Naming it honestly is
# better than leaving the column NULL or guessing a version string.
WAVE1_MODEL = "wave-1 EBM (predates ebm_classifier_trained_on_09_12_2025)"


def norm(s):
    """Whitespace- and quote-insensitive text key.

    CSV round-tripping can alter line endings and runs of whitespace, and
    smart quotes differ between the source corpus and the database. Nothing
    else is touched - case and wording must match exactly.
    """
    s = str(s).strip()
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s)


def to_json(v):
    """feature_contributions is a Python dict repr, not JSON."""
    if pd.isna(v):
        return None
    if isinstance(v, dict):
        return json.dumps(v)
    try:
        return json.dumps(ast.literal_eval(str(v)))
    except (ValueError, SyntaxError):
        return json.dumps(json.loads(str(v)))   # already JSON


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--review-set", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("Set DATABASE_URL.")
    engine = create_engine(db_url)

    csv = pd.read_csv(args.csv)
    print(f"CSV: {len(csv)} row(s) - covers all three stages, "
          "only the Stage-2 ones are loaded")

    with engine.connect() as conn:
        db = pd.read_sql(text(f"""
            SELECT review_id, review_text, ebm_prediction,
                   {', '.join(FEATURE_COLS)}
            FROM reviews
            WHERE stage = 2 AND review_set = :rs
            ORDER BY review_id
        """), conn, params={"rs": args.review_set})
    print(f"DB : {len(db)} Stage-2 review(s) in set {args.review_set}")

    # ------------------------------------------------------------------
    # Strict 1:1 match on full text
    # ------------------------------------------------------------------
    csv["_k"] = csv["review_text"].map(norm)
    db["_k"] = db["review_text"].map(norm)

    for name, frame in (("CSV", csv), ("database", db)):
        dupes = frame["_k"].duplicated().sum()
        if dupes:
            sys.exit(f"STOP: {dupes} duplicate review text(s) in the {name}. "
                     "Matching on text cannot be unambiguous.")

    lookup = csv.set_index("_k")
    missing = [k for k in db["_k"] if k not in lookup.index]
    if missing:
        print(f"\nSTOP: {len(missing)} database review(s) have no CSV match:")
        for k in missing[:5]:
            print(f"  {k[:100]}...")
        sys.exit(1)

    print(f"\nMatched {len(db)}/{len(db)} on full text.")

    # ------------------------------------------------------------------
    # Integrity: the CSV must describe the verdict the DB stores
    # ------------------------------------------------------------------
    rows, mismatches = [], []
    for _, r in db.iterrows():
        c = lookup.loc[r["_k"]]
        if c["ebm_prediction"] != r["ebm_prediction"]:
            mismatches.append((r["review_id"], r["ebm_prediction"],
                               c["ebm_prediction"]))
        rows.append({
            "review_id": int(r["review_id"]),
            "review_text": r["review_text"],       # DB text is authoritative
            "emo": float(c[FEATURE_COLS[0]]),
            "adj": float(c[FEATURE_COLS[1]]),
            "read": float(c[FEATURE_COLS[2]]),
            "analytic": float(c[FEATURE_COLS[3]]),
            "ebm_prediction": r["ebm_prediction"],
            "model_prediction": c["model_prediction"],
            "explanation": c["natural_language_explanation"],
            "contributions": to_json(c["feature_contributions"]),
            "generator_model": WAVE1_MODEL,
        })

    if mismatches:
        print(f"\nSTOP: {len(mismatches)} review(s) where the CSV explains a "
              "different verdict than the database stores:")
        for rid, dbv, csvv in mismatches:
            print(f"  review_id {rid}: DB={dbv}, CSV={csvv}")
        print("Loading these would show participants an explanation arguing "
              "for the wrong verdict.")
        sys.exit(1)
    print("All CSV verdicts agree with the stored verdicts.")

    blank = [r for r in rows if not str(r["explanation"]).strip()]
    if blank:
        sys.exit(f"STOP: {len(blank)} blank explanation(s).")

    if args.dry_run:
        print("\nDry run - nothing written. Sample:")
        s = rows[0]
        print(f"  review_id {s['review_id']} ({s['ebm_prediction']})")
        print(f"  {str(s['explanation'])[:220]}...")
        return

    with engine.connect() as conn:
        clash = conn.execute(
            text("SELECT review_id FROM languageexplanations "
                 "WHERE review_id = ANY(:ids)"),
            {"ids": [r["review_id"] for r in rows]}).fetchall()
    if clash:
        sys.exit(f"STOP: {len(clash)} of these already have an explanation: "
                 f"{[c[0] for c in clash]}")

    q = text("""
        INSERT INTO languageexplanations (
            review_id, review_text,
            proportion_of_emotional_content_in_review,
            proportion_of_adjectives_in_review,
            readability_of_review, analytic_writing_style,
            ebm_prediction, model_prediction,
            natural_language_explanation, feature_contributions,
            generator_model
        ) VALUES (
            :review_id, :review_text, :emo, :adj, :read, :analytic,
            :ebm_prediction, :model_prediction, :explanation,
            CAST(:contributions AS JSONB), :generator_model
        )
    """)
    with engine.begin() as conn:
        for r in rows:
            conn.execute(q, r)

    print(f"\nAppended {len(rows)} wave-1 explanation(s) for set "
          f"{args.review_set}.")
    print(f"generator_model recorded as: {WAVE1_MODEL}")
    print("\nNow generate wave 2:")
    print("  python ml_training/generate_nl_explanations.py --sets 2 3 4")


if __name__ == "__main__":
    main()

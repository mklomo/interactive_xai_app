"""Deterministic natural-language explanations from local feature contributions.

No LLM. The explanation is a pure function of the EBM's local
contributions, so it is faithful by construction rather than by audit.

Why this replaces the Cohere path
---------------------------------
Once the explanation follows a rigid template, generation adds nothing but
risk. The wave-1 explanations, and the first wave-2 batch, repeatedly made
claims the contributions do not license:

  * causal reads - "typical of authentic feedback", "indicating potential
    exaggeration", "which could signal a crafted or insincere tone". A
    local contribution says how far a feature moved THIS prediction. It
    does not say why that feature is associated with deception.
  * false aggregation - "the adjective evidence outweighed the rest" on
    reviews where the contributions sum the other way.

Both classes of error vanish here, because nothing is generated: every
clause is derived from a number.

Terminology
-----------
These are LOCAL FEATURE CONTRIBUTIONS (local feature effects), not feature
importances. A feature importance is a global property of the model; a
contribution is specific to one observation. Worth using the precise term
in the write-up.

What the template deliberately does NOT say
-------------------------------------------
Why a feature points where it does. The EBM gives no basis for it, so any
sentence offering one is the explanation's author speaking, not the model.

Usage:
    python ml_training/render_explanations.py --demo
    export DATABASE_URL=...
    python ml_training/render_explanations.py --sets 2 3 4 --dry-run
    python ml_training/render_explanations.py --sets 2 3 4
"""

import argparse
import json
import os
import sys

import joblib
import pandas as pd
from sqlalchemy import create_engine, text

MODEL_PATH = "./ml_training/ebm_classifier_trained_on_09_12_2025.joblib"
GENERATOR = "deterministic-template-v1"

FEATURE_COLS = [
    "proportion_of_emotional_content_in_review",
    "proportion_of_adjectives_in_review",
    "readability_of_review",
    "analytic_writing_style",
]

# Participant-facing names. Wave 1 rendered these in prose, so they read
# the same way here.
READABLE = {
    "proportion_of_emotional_content_in_review": "proportion of emotional content",
    "proportion_of_adjectives_in_review": "proportion of adjectives",
    "readability_of_review": "readability score",
    "analytic_writing_style": "analytic writing style",
}

RANK = ["the strongest contributor", "the second strongest",
        "the third strongest", "the weakest"]


def _join(items):
    """a / a and b / a, b and c"""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def render(contributions, prediction):
    """Build the explanation. contributions: [(name, score, value), ...]

    Features are grouped by direction and ordered by ABSOLUTE
    contribution. Ranking by absolute value is the only ordering the
    numbers unambiguously support, and it is where the generated
    explanations went wrong most often - review 29 named emotional content
    (-1.3398) the largest when readability (-2.0557) was, because
    emotional content was the one that agreed with the verdict. Here the
    strongest contributor is named even when it points AWAY from the
    prediction.
    """
    ordered = sorted(contributions, key=lambda t: abs(t[1]), reverse=True)
    total = sum(s for _, s, _ in contributions)

    def label(name):
        return READABLE.get(name, name.replace("_", " "))

    lead_name, lead_score, lead_value = ordered[0]
    lead_dir = "Genuine" if lead_score >= 0 else "Deceptive"
    opp_dir = "Deceptive" if lead_dir == "Genuine" else "Genuine"

    same = [t for t in ordered[1:] if (t[1] >= 0) == (lead_score >= 0)]
    opp = [t for t in ordered[1:] if (t[1] >= 0) != (lead_score >= 0)]

    s = [f"The model predicted this review as **{prediction}**."]
    s.append(
        f"The **{label(lead_name)}** ({lead_value:.4f}) contributed "
        f"**{lead_score:+.4f}** toward **{lead_dir}**, making it the "
        f"strongest contributor."
    )

    if len(same) == 1:
        n, sc, v = same[0]
        s.append(f"The **{label(n)}** ({v:.4f}) also contributed "
                 f"**{sc:+.4f}** toward **{lead_dir}**.")
    elif same:
        parts = [f"the **{label(n)}** ({v:.4f}, **{sc:+.4f}**)"
                 for n, sc, v in same]
        s.append(f"{_join(parts).capitalize()} also contributed toward "
                 f"**{lead_dir}**.")

    if len(opp) == 1:
        n, sc, v = opp[0]
        s.append(f"In contrast, the **{label(n)}** ({v:.4f}) contributed "
                 f"**{sc:+.4f}** toward **{opp_dir}**.")
    elif opp:
        parts = [f"the **{label(n)}** ({v:.4f}, **{sc:+.4f}**)"
                 for n, sc, v in opp]
        s.append(f"In contrast, {_join(parts)} contributed toward "
                 f"**{opp_dir}**.")

    # Closing: the arithmetic, stated plainly. On reviews where the
    # contributions sum against the verdict, say so rather than inventing
    # a reason - the intercept is not shown to participants, so no honest
    # feature-level account of the gap exists.
    leans = "Genuine" if total >= 0 else "Deceptive"
    if leans == prediction:
        s.append(f"Together these four contributions sum to **{total:+.4f}**, "
                 f"favouring **{prediction}**.")
    else:
        s.append(f"Together these four contributions sum to **{total:+.4f}**, "
                 f"which leans toward **{leans}**, even though the model's "
                 f"prediction was **{prediction}**.")

    return " ".join(s)


def verify(explanation, contributions, prediction):
    """Every contribution quoted, correct direction, correct ranking."""
    problems = []
    for name, score, value in contributions:
        if f"{score:+.4f}" not in explanation:
            problems.append(f"missing contribution {score:+.4f} ({name})")
        if f"{value:.4f}" not in explanation:
            problems.append(f"missing value {value:.4f} ({name})")
    if f"**{prediction}**" not in explanation:
        problems.append("prediction not stated")

    # Features are grouped by direction, so the text is not globally sorted
    # by absolute contribution. Two things must still hold: the feature
    # named "strongest contributor" really is the largest in absolute
    # terms, and within each direction group the order descends.
    ordered = sorted(contributions, key=lambda t: abs(t[1]), reverse=True)
    lead = ordered[0]
    lead_at = explanation.find(f"{lead[1]:+.4f}")
    if lead_at == -1 or "strongest contributor" not in explanation:
        problems.append("strongest contributor not identified")
    else:
        before = explanation[:explanation.index("strongest contributor")]
        if f"{lead[1]:+.4f}" not in before:
            problems.append(
                f"wrong feature called strongest: largest is {lead[0]} "
                f"({lead[1]:+.4f})")

    for sign in (1, -1):
        group = [t for t in ordered if (t[1] >= 0) == (sign > 0)]
        pos = [explanation.index(f"{s:+.4f}") for _, s, _ in group
               if f"{s:+.4f}" in explanation]
        if pos != sorted(pos):
            problems.append(
                f"{'positive' if sign > 0 else 'negative'} contributions not "
                "in descending order of absolute value")

    total = sum(s for _, s, _ in contributions)
    if f"{total:+.4f}" not in explanation:
        problems.append(f"total {total:+.4f} not stated")
    return problems


DEMO = [
    ("Deceptive", [("proportion_of_emotional_content_in_review", -2.5676, 12.5000),
                   ("proportion_of_adjectives_in_review", -0.5294, 12.5000),
                   ("readability_of_review", -2.8126, 42.6330),
                   ("analytic_writing_style", -0.4065, 66.5100)]),
    ("Genuine",   [("proportion_of_emotional_content_in_review", 1.1651, 7.3200),
                   ("proportion_of_adjectives_in_review", 0.3642, 7.3200),
                   ("readability_of_review", 4.6325, 75.7920),
                   ("analytic_writing_style", 1.3593, 48.4400)]),
    ("Genuine",   [("proportion_of_emotional_content_in_review", -2.0154, 12.7700),
                   ("proportion_of_adjectives_in_review", 0.5340, 6.3800),
                   ("readability_of_review", 0.4393, 27.1333),
                   ("analytic_writing_style", 0.2462, 55.0100)]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", type=int, nargs="+", default=None)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.demo:
        import textwrap
        for i, (pred, contribs) in enumerate(DEMO, 1):
            total = sum(s for _, s, _ in contribs)
            mixed = ("MIXED - contributions sum against the verdict"
                     if (total >= 0) != (pred == "Genuine") else "")
            print("=" * 74)
            print(f"[{i}] prediction {pred} | sum {total:+.4f}  {mixed}")
            print("-" * 74)
            e = render(contribs, pred)
            print(textwrap.fill(e.replace("**", ""), 74))
            print(f"\n  verify: {verify(e, contribs, pred) or 'clean'}")
            print()
        return

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("Set DATABASE_URL.")
    engine = create_engine(db_url)

    where = "" if args.sets is None else "AND r.review_set = ANY(:sets)"
    q = text(f"""
        SELECT r.review_id, r.review_text, r.review_set, r.ebm_prediction,
               {', '.join('r.' + c for c in FEATURE_COLS)}
        FROM reviews r
        LEFT JOIN languageexplanations le ON le.review_id = r.review_id
        WHERE r.stage = 2 {where} AND le.review_id IS NULL
        ORDER BY r.review_set, r.review_id
    """)
    with engine.connect() as conn:
        df = pd.read_sql(q, conn,
                         params={} if args.sets is None else {"sets": args.sets})
    if df.empty:
        print("Nothing to do.")
        return
    print(f"{len(df)} review(s) to explain")

    ebm = joblib.load(MODEL_PATH)
    X = df[FEATURE_COLS]
    local = ebm.explain_local(X)
    recomputed = ebm.predict(X)
    if (recomputed != df["ebm_prediction"].values).any():
        n = (recomputed != df["ebm_prediction"].values).sum()
        sys.exit(f"STOP: {n} stored verdict(s) disagree with the model.")

    rows, faults = [], []
    for i in range(len(df)):
        d = local.data(i)
        contribs = [(n, float(s), float(v)) for n, s, v in
                    zip(d["names"], d["scores"], X.iloc[i].values)
                    if n.lower() != "intercept"]
        pred = df.iloc[i]["ebm_prediction"]
        e = render(contribs, pred)
        probs = verify(e, contribs, pred)
        if probs:
            faults.append((int(df.iloc[i]["review_id"]), probs))
        rows.append({
            "review_id": int(df.iloc[i]["review_id"]),
            "review_text": df.iloc[i]["review_text"],
            "emo": contribs[0][2], "adj": contribs[1][2],
            "read": contribs[2][2], "analytic": contribs[3][2],
            "ebm_prediction": pred, "model_prediction": str(recomputed[i]),
            "explanation": e,
            "contributions": json.dumps({n: round(s, 4) for n, s, _ in contribs}),
            "generator_model": GENERATOR,
        })

    if faults:
        print(f"\n{len(faults)} render fault(s) - this indicates a bug, not "
              "model behaviour:")
        for rid, p in faults:
            print(f"  review_id {rid}: {p}")
        sys.exit(1)
    print("All explanations verified: every value and contribution quoted, "
          "ranked correctly.")

    out = "./data/stages_data/nl_explanations_template.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Written to {out}")

    if args.dry_run:
        print("\nDry run - database untouched. Sample:\n")
        print(rows[0]["explanation"].replace("**", ""))
        return

    q = text("""
        INSERT INTO languageexplanations (
            review_id, review_text,
            proportion_of_emotional_content_in_review,
            proportion_of_adjectives_in_review,
            readability_of_review, analytic_writing_style,
            ebm_prediction, model_prediction,
            natural_language_explanation, feature_contributions, generator_model
        ) VALUES (
            :review_id, :review_text, :emo, :adj, :read, :analytic,
            :ebm_prediction, :model_prediction, :explanation,
            CAST(:contributions AS JSONB), :generator_model
        )
    """)
    with engine.begin() as conn:
        for r in rows:
            conn.execute(q, r)
    print(f"Appended {len(rows)} explanation(s).")


if __name__ == "__main__":
    main()

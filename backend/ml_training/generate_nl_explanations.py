"""Generate static natural-language explanations for Stage-2 reviews.

Replaces natural_language_exp.ipynb. Differences that matter:

  * review_id comes from the database, not range(1, n+1). The notebook's
    version would key explanations to the wrong reviews.
  * Appends only. The notebook used pandas to_sql(if_exists="replace"),
    which DROPS the table - that would destroy the explanations for the
    original 12 reviews. This script never updates or deletes an existing
    row, and aborts if any target review already has an explanation.
  * The API key is read from the environment, never hard-coded.
  * Idempotent: reviews that already have an explanation are skipped, so a
    failed run can be resumed without duplicating API calls.
  * Validates the EBM sign convention against the model's own predictions
    before spending any tokens.

Usage
-----
    export COHERE_API_KEY=...
    export DATABASE_URL=postgresql://...neon.tech/...

    python generate_nl_explanations.py --check-only      # validate, no API calls
    python generate_nl_explanations.py --sets 2 3 4 --dry-run   # show one prompt
    python generate_nl_explanations.py --sets 2 3 4
"""

import argparse
import json
import os
import sys
import time

import joblib
import pandas as pd
from sqlalchemy import create_engine, text

MODEL_PATH = "./ml_training/ebm_classifier_trained_on_09_12_2025.joblib"
COHERE_MODEL = "command-a-03-2025"   # keep: wave-1 explanations used this model

FEATURE_COLS = [
    "proportion_of_emotional_content_in_review",
    "proportion_of_adjectives_in_review",
    "readability_of_review",
    "analytic_writing_style",
]

READABLE = {
    "proportion_of_emotional_content_in_review": "proportion of emotional content in review",
    "proportion_of_adjectives_in_review": "proportion of adjectives in review",
    "readability_of_review": "readability of the review",
    "analytic_writing_style": "analytic writing style of the review",
}


# ----------------------------------------------------------------------
# Sign convention
# ----------------------------------------------------------------------
def get_intercept(local_data):
    """EBM puts the intercept in data['extra'], not in data['names'].

    Missing this makes the decision rule look wrong on rows near the
    boundary: the logit is intercept + sum(contributions), not the sum
    alone.
    """
    extra = local_data.get("extra") or {}
    scores = extra.get("scores") or [0.0]
    return float(scores[0])


def validate_sign_convention(ebm, X):
    """Confirm that positive contribution scores mean 'Genuine'.

    The prompt tells the model that negative scores are evidence for
    Deceptive and positive for Genuine. That holds only if the EBM's
    positive class is Genuine - i.e. classes_[1] == 'Genuine'.

    The check is that intercept + sum(contributions) reproduces the model's
    own predictions. Note this validates the DIRECTION convention only; it
    says nothing about whether the stored ebm_prediction is right, which is
    checked separately.
    """
    positive_class = ebm.classes_[1]
    local = ebm.explain_local(X)
    preds = ebm.predict(X)

    agree, disagreements = 0, []
    for i in range(len(X)):
        d = local.data(i)
        logit = get_intercept(d) + sum(d["scores"])
        implied = ebm.classes_[1] if logit >= 0 else ebm.classes_[0]
        if implied == preds[i]:
            agree += 1
        else:
            disagreements.append((i, logit, implied, preds[i]))

    pct = agree / len(X)
    print(f"  classes_          : {list(ebm.classes_)}")
    print(f"  positive class    : {positive_class}")
    print(f"  sign check        : {agree}/{len(X)} ({pct:.0%}) agree with predictions")

    if positive_class != "Genuine":
        sys.exit(
            f"\nSTOP: the positive class is '{positive_class}', not 'Genuine'.\n"
            "The prompt's interpretation rule is inverted. Flip it before generating."
        )
    if disagreements:
        print(f"\n  {len(disagreements)} row(s) where intercept + sum(scores) "
              "disagrees with predict():")
        for i, logit, implied, actual in disagreements[:10]:
            print(f"    row {i}: logit {logit:+.4f} -> {implied}, "
                  f"but predict() says {actual}")
        print("  These are boundary cases. The per-feature direction labels in "
              "the prompt are still correct.")
    return positive_class


# ----------------------------------------------------------------------
# Prompt
# ----------------------------------------------------------------------
def build_prompt(review_text, prediction, contributions, intercept=None):
    """Wave-1 prompt, plus one accuracy constraint. No baseline term.

    Kept from wave 1: the framing, the contribution block, the
    interpretation rule, the 3-5 sentence target, the requirement to quote
    every score, the tone instruction, and the exact glyphs (•, →, em
    dash). The explanation remains purely a FEATURE-IMPORTANCE
    explanation, which is what the study manipulates.

    Added: on reviews where the listed contributions sum against the
    verdict, Cohere is forbidden from claiming the supporting features
    outweighed the opposing ones. That claim is arithmetically false, and
    wave 1 made it on 4 of 28 reviews - all Genuine, because the model's
    starting point favours Genuine, so Genuine verdicts survive weak
    feature evidence more often than Deceptive ones do.

    The fix does NOT introduce the intercept. It only stops an unsupported
    aggregation claim, which a faithful feature-importance explanation
    should not make regardless. Cohere reports which features pointed
    which way and how strongly - all true - and states the verdict without
    inventing a mechanism for it.

    `intercept` is accepted for signature stability and unused.
    """
    lines = []
    for name, score, value in contributions:
        evidence_type = ("Evidence for DECEPTIVE" if score < 0
                         else "Evidence for GENUINE")
        toward = "Deceptive" if score < 0 else "Genuine"
        direction = f"pushed the prediction TOWARD '{toward}'"
        lines.append(
            f"- {name} (value: {value:.4f}) → contribution {score:.4f} "
            f"({evidence_type} / {direction})"
        )
    contribution_text = "\n".join(lines)

    contrib_sum = sum(s for _, s, _ in contributions)
    features_alone = "Genuine" if contrib_sum >= 0 else "Deceptive"

    if features_alone != prediction:
        accuracy_rule = f"""
ACCURACY REQUIREMENT — read the numbers before writing:
The contributions above sum to {contrib_sum:+.4f}. Taken together they lean toward
'{features_alone}', even though the model's prediction is '{prediction}'.
Therefore you must NOT write that the features supporting '{prediction}' outweighed,
overcame, dominated or tipped the balance against the others. That would be false.
Instead: state which features pointed which way and how strongly, say plainly that
the evidence from these features was mixed and on balance leaned toward
'{features_alone}', and report that the model's prediction was nonetheless
'{prediction}'. Do not invent a reason for this."""
    else:
        accuracy_rule = f"""
ACCURACY REQUIREMENT:
The contributions above sum to {contrib_sum:+.4f}, agreeing with the prediction of
'{prediction}'. You may say the features favouring '{prediction}' outweighed those
pointing the other way, because they do. Do not overstate any single feature —
name the one with the largest absolute contribution as the most influential."""

    return f"""You are an expert analyst explaining an EBM prediction for hotel review authenticity.

Review text:
"{review_text}"

Model Prediction: {prediction}

Feature Contributions (exact numerical scores from the model):
{contribution_text}

CRITICAL INTERPRETATION RULE (Positive class = Genuine):
• If the contribution score is **negative** → it is Evidence for DECEPTIVE (pushes toward 'Deceptive')
• If the contribution score is **positive** → it is Evidence for GENUINE (pushes toward 'Genuine')
{accuracy_rule}

Write a concise (3-5 sentences), natural, professional explanation of WHY the model predicted this review as '{prediction}'.
You MUST mention each feature's exact numerical score and whether it provided evidence for 'Deceptive' or 'Genuine'.
Tie the features directly to the review text.
Speak like a helpful human analyst — no jargon."""


# ----------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------
def fetch_reviews(engine, sets=None):
    """Stage-2 reviews with no explanation yet.

    Only stage = 2. Stages 1 and 3 present no AI advice, so they have
    nothing to explain and must not appear in this table.

    sets=None means every Stage-2 set, which is the case after a rebuild.
    """
    where_set = "" if sets is None else "AND r.review_set = ANY(:sets)"
    q = text(f"""
        SELECT r.review_id, r.review_text, r.review_set, r.ebm_prediction,
               {', '.join('r.' + c for c in FEATURE_COLS)}
        FROM reviews r
        LEFT JOIN languageexplanations le ON le.review_id = r.review_id
        WHERE r.stage = 2
          {where_set}
          AND le.review_id IS NULL
        ORDER BY r.review_set, r.review_id
    """)
    params = {} if sets is None else {"sets": list(sets)}
    with engine.connect() as conn:
        return pd.read_sql(q, conn, params=params)


OUTWEIGH_CLAIMS = ("outweigh", "outweighed", "overcame", "overrode",
                   "dominated", "stronger than", "won out", "tipped the")


# ----------------------------------------------------------------------
# Few-shot exemplars
# ----------------------------------------------------------------------
# Taken from the wave-1 Stage-2 explanations so that wave 2 matches their
# structure, register and length: the "primarily due to" opening, ordinal
# connectives, bolded feature names and figures, every value and
# contribution quoted, a tie to the review's wording, and a closing
# summary in roughly five sentences.
#
# The CONTENT is rewritten. All twelve wave-1 explanations end at what is
# really a causal claim - "typical of authentic feedback", "indicating
# potential exaggeration", "suggesting an overly enthusiastic sentiment".
# A local feature contribution does not license any of that. It says how
# far this feature moved THIS prediction, not why that feature is
# associated with deception. These four stop at describing what the model
# weighted, which is all the numbers support.
#
# The four cases are chosen to cover the range: all-agreeing in each
# direction, a narrowly balanced case, and - most importantly - a mixed
# case where the contributions sum against the verdict, which is where
# wave 1 confabulated.
EXEMPLARS = """
EXAMPLE 1 — all four features agree, prediction 'Deceptive'
Contributions: emotional content (12.5000) -2.5676 | adjectives (12.5000) -0.5294 |
readability (42.6330) -2.8126 | analytic writing style (66.5100) -0.4065
Explanation:
The model flagged this review as 'Deceptive', with all four features pointing that way. The **readability score** (**42.6330**) contributed **-2.8126**, the largest single contribution and the strongest evidence toward 'Deceptive'. The **proportion of emotional content** (**12.5000**) followed closely at **-2.5676**. The **proportion of adjectives** (**12.5000**), reflected in wording such as "great," "lovely" and "amazingly," added a smaller **-0.5294**, and the **analytic writing style** (**66.5100**) contributed **-0.4065**, both in the same direction. For this review the model weighted readability and emotional content far more heavily than the other two features.

EXAMPLE 2 — all four features agree, prediction 'Genuine'
Contributions: emotional content (7.3200) +1.1651 | adjectives (7.3200) +0.3642 |
readability (75.7920) +4.6325 | analytic writing style (48.4400) +1.3593
Explanation:
The model predicted this review as 'Genuine', with all four features pointing in that direction. The **readability score** (**75.7920**) contributed **4.6325**, by far the largest of the four and the strongest evidence toward 'Genuine'. The **analytic writing style** (**48.4400**) added **1.3593** and the **proportion of emotional content** (**7.3200**) added **1.1651**. The **proportion of adjectives** (**7.3200**), visible in the descriptive praise for the rooms, service and location, made the smallest contribution at **0.3642**. For this review the model weighted readability far more heavily than the other three features combined.

EXAMPLE 3 — features nearly cancel, prediction 'Genuine'
Contributions: emotional content (6.0800) +1.0836 | adjectives (4.9700) +0.4843 |
readability (63.5430) -1.0842 | analytic writing style (81.0100) -0.3942
Explanation:
The model predicted this review as 'Genuine', though the four features were closely balanced. The **proportion of emotional content** (**6.0800**) contributed **1.0836** toward 'Genuine' and the **proportion of adjectives** (**4.9700**) added **0.4843**, drawn from the specific praise for the hotel's amenities and staff. Pulling the other way, the **readability score** (**63.5430**) contributed **-1.0842** toward 'Deceptive' and the **analytic writing style** (**81.0100**) contributed **-0.3942**. The positive contributions only slightly exceeded the negative ones, so the evidence from these four features favoured 'Genuine' by a narrow margin.

EXAMPLE 4 — contributions sum AGAINST the prediction (handle it exactly like this)
Contributions: emotional content (12.7700) -2.0154 | adjectives (6.3800) +0.5340 |
readability (27.1333) +0.4393 | analytic writing style (55.0100) +0.2462
Explanation:
The model predicted this review as 'Genuine', but the four features did not point that way on balance. The **proportion of emotional content** (**12.7700**) contributed **-2.0154** toward 'Deceptive', the largest single contribution of the four. The remaining three pointed the other way: the **proportion of adjectives** (**6.3800**) contributed **0.5340** toward 'Genuine', reflected in descriptive wording such as "beautifully designed" and "impeccable service"; the **readability score** (**27.1333**) contributed **0.4393**; and the **analytic writing style** (**55.0100**) contributed **0.2462**. Taken together these four contributions sum to **-0.7959**, so the evidence from these features leaned toward 'Deceptive' even though the model's prediction was 'Genuine'.
"""


def is_hard(flag):
    """Hard faults fail the prompt's requirements and trigger regeneration.

    "soft:" flags are heuristics that fire on legitimate explanations - an
    explanation that discusses opposing evidence at length will mention the
    other verdict more often, which is fine.
    """
    return not flag.startswith("soft:")


def audit(explanation, prediction, contribs, intercept=0.0):
    """Flag explanations that may misstate the model.

    Cohere is asked to tie features to the review text, which is where it
    can assert an evidence direction the EBM did not produce. A wrong
    direction does not just read badly - it inverts the stimulus for every
    participant who draws that set. These checks catch the mechanical
    failures; they do not replace reading all 36.
    """
    problems = []
    low = explanation.lower()

    for name, score, _ in contribs:
        if f"{score:.4f}" not in explanation and f"{score:.3f}" not in explanation:
            problems.append(f"score {score:.4f} ({name}) not quoted")

    if prediction.lower() not in low:
        problems.append(f"never states the prediction '{prediction}'")

    # A false aggregation claim. This is the failure the word-count check
    # below missed entirely: on reviews where the intercept carries the
    # verdict, the contributions net the OTHER way, so any claim that a
    # feature outweighed the rest is arithmetically false - however fluent
    # the sentence reading it.
    contrib_sum = sum(s for _, s, _ in contribs)
    features_alone = "Genuine" if contrib_sum >= 0 else "Deceptive"
    if features_alone != prediction:
        claimed = [c for c in OUTWEIGH_CLAIMS if c in low]
        if claimed:
            # Blocking. This is the unfaithfulness the accuracy rule in the
            # prompt exists to prevent: the features sum against the
            # verdict, so nothing among them outweighed anything. Wave 1
            # made this claim on 4 of 28 reviews and those are already
            # delivered, but wave 2 is being held to a faithful standard.
            problems.append(
                f"FALSE AGGREGATION: says {claimed} but contributions sum to "
                f"{contrib_sum:+.4f}, favouring {features_alone}, not {prediction}. "
                f"Nothing outweighed anything here."
            )

    # Directional sanity. Note this fires on legitimate explanations that
    # discuss opposing evidence at length, so it is a prompt to look, not a
    # defect on its own.
    other = "genuine" if prediction.lower() == "deceptive" else "deceptive"
    if low.count(other) > low.count(prediction.lower()):
        problems.append(f"soft: mentions '{other}' more than '{prediction}' "
                        "- usually fine, verify direction")

    n_words = len(explanation.split())
    if n_words < 40 or n_words > 200:
        problems.append(f"length {n_words} words - outside the 3-5 sentence target")

    return problems


def preflight(engine, review_ids):
    """Refuse to run if appending could create a duplicate.

    filter_explanations() calls .item(), which raises unless a review has
    exactly one explanation. A duplicate would break Stage 2 at runtime for
    whichever participants drew that set, so it is checked before any rows
    are written rather than discovered in the field.
    """
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT review_id FROM languageexplanations "
                 "WHERE review_id = ANY(:ids)"),
            {"ids": list(review_ids)},
        ).fetchall()
        if existing:
            sys.exit(f"STOP: {len(existing)} of these reviews already have an "
                     f"explanation: {[r[0] for r in existing]}")

        dupes = conn.execute(text("""
            SELECT review_id, COUNT(*) FROM languageexplanations
            GROUP BY review_id HAVING COUNT(*) > 1
        """)).fetchall()
        if dupes:
            sys.exit(f"STOP: table already contains duplicate review_ids: {dupes}. "
                     "Stage 2 will crash for these. Resolve before appending.")

        total = conn.execute(
            text("SELECT COUNT(*) FROM languageexplanations")).scalar()
        print(f"  languageexplanations currently holds {total} row(s) - "
              "these will not be touched")


def insert_explanations(engine, rows):
    """Append only. Never UPDATE, never REPLACE, never DROP.

    The whole insert runs in one transaction, so a failure part-way through
    leaves the table exactly as it was rather than half-populated.
    """
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
            :review_id, :review_text,
            :emo, :adj, :read, :analytic,
            :ebm_prediction, :model_prediction,
            :explanation, CAST(:contributions AS JSONB),
            :generator_model
        )
    """)
    with engine.begin() as conn:
        for r in rows:
            conn.execute(q, r)


# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", type=int, nargs="+", default=None,
                    help="Stage-2 sets to generate for. Default: all of them, "
                         "which is what a full rebuild wants.")
    ap.add_argument("--check-only", action="store_true",
                    help="validate the sign convention and exit")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the first prompt and exit, no API calls")
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="seconds between API calls")
    ap.add_argument("--max-retries", type=int, default=4,
                    help="regeneration attempts per review when the audit "
                         "finds a fault (same prompt each time, new sample)")
    ap.add_argument("--use-stored-verdict", action="store_true",
                    help="proceed when the stored ebm_prediction disagrees with "
                         "the live model, explaining the stored verdict (which "
                         "is what participants actually see)")
    ap.add_argument("--force", action="store_true",
                    help="append even if the audit flagged explanations")
    ap.add_argument("--from-csv", metavar="PATH",
                    help="append previously generated (and possibly hand-edited) "
                         "explanations from CSV instead of calling the API")
    args = ap.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        sys.exit("Set DATABASE_URL (your Neon connection string).")

    engine = create_engine(db_url)

    # Hand-edited path: append text that already exists, no API calls.
    if args.from_csv:
        rows = pd.read_csv(args.from_csv).to_dict("records")
        preflight(engine, [int(r["review_id"]) for r in rows])
        print(f"Appending {len(rows)} explanation(s) from {args.from_csv}...")
        insert_explanations(engine, rows)
        print("Done - no existing rows were modified.")
        return

    print("Fetching Stage-2 reviews without explanations...")
    df = fetch_reviews(engine, args.sets)
    if df.empty:
        print("Nothing to do - every Stage-2 review already has an explanation.")
        return

    per_set = df.groupby("review_set").size().to_dict()
    print(f"  {len(df)} review(s) to explain")
    for s, n in sorted(per_set.items()):
        print(f"    set {s}: {n}")
    if any(n != 12 for n in per_set.values()):
        print("  NOTE: a set with other than 12 rows means either a partial "
              "run or a set that is not fully loaded. Check before spending.")

    preflight(engine, df["review_id"].tolist())

    print("\nLoading EBM and validating sign convention...")
    ebm = joblib.load(MODEL_PATH)
    X = df[FEATURE_COLS].copy()
    validate_sign_convention(ebm, X)

    # The explanation must justify the verdict the PARTICIPANT SEES, which is
    # the stored ebm_prediction - not whatever the model recomputes now.
    # mis_classified, and therefore each set's 3/3/3/3 balance, is derived
    # from the stored value too. So the stored verdict is authoritative and
    # is what gets passed to Cohere.
    recomputed = ebm.predict(X)
    stored = df["ebm_prediction"].values
    mismatched = (recomputed != stored).sum()
    print(f"  stored vs recomputed predictions: {len(df) - mismatched}/{len(df)} match")

    if mismatched:
        print(f"\n  {mismatched} review(s) where the stored verdict differs "
              "from the live model:")
        for i in range(len(df)):
            if recomputed[i] != stored[i]:
                print(f"    review_id {df.iloc[i]['review_id']} "
                      f"(set {df.iloc[i]['review_set']}): "
                      f"stored={stored[i]}, recomputed={recomputed[i]}")
        print("\n  Run diagnose_predictions.py to see how close these sit to "
              "the decision boundary.")
        if not args.use_stored_verdict:
            sys.exit(
                "\nSTOP: nothing generated.\n"
                "The stored verdict is what participants see, so it is the one\n"
                "the explanation must justify. But a mismatch means the feature\n"
                "contributions may argue toward the OTHER verdict, which would\n"
                "produce an incoherent explanation for that review.\n"
                "Diagnose first; then re-run with --use-stored-verdict."
            )
        print("\n  --use-stored-verdict given: explaining the stored verdicts.")

    # Authoritative from here on
    preds = stored

    if args.check_only:
        print("\nChecks passed. Re-run without --check-only to generate.")
        return

    local = ebm.explain_local(X)

    # How many verdicts does the baseline carry rather than the features?
    carried = []
    for i in range(len(df)):
        d = local.data(i)
        if (sum(d["scores"]) >= 0) != (preds[i] == "Genuine"):
            carried.append((int(df.iloc[i]["review_id"]), preds[i],
                            sum(d["scores"])))
    if carried:
        print(f"\n  {len(carried)} verdict(s) decided by the baseline, not the "
              "features:")
        for rid, p, s in carried:
            print(f"    review_id {rid}: shown {p}, features sum {s:+.4f}")
        by_verdict = {}
        for _, p, _ in carried:
            by_verdict[p] = by_verdict.get(p, 0) + 1
        print(f"    by verdict: {by_verdict}")
        if len(by_verdict) == 1:
            print("    NOTE: these fall entirely on one verdict. The prompt now "
                  "handles them\n    explicitly, so faithfulness will not covary "
                  "with recommendation direction.")

    if args.dry_run:
        # Show a baseline-carried prompt if one exists - that is the case
        # worth eyeballing, not the easy one.
        ix = 0
        for i in range(len(df)):
            d = local.data(i)
            if (sum(d["scores"]) >= 0) != (preds[i] == "Genuine"):
                ix = i
                break
        d = local.data(ix)
        contribs = [(n, s, v) for n, s, v in
                    zip(d["names"], d["scores"], X.iloc[ix].values)
                    if n.lower() != "intercept"]
        print("\n" + "=" * 70)
        print(f"Prompt for review_id {df.iloc[ix]['review_id']}:")
        print("=" * 70)
        print(build_prompt(df.iloc[ix]["review_text"], preds[ix], contribs,
                           get_intercept(d)))
        print("=" * 70)
        print("\nDry run - no API calls made.")
        return

    api_key = os.environ.get("COHERE_API_KEY")
    if not api_key:
        sys.exit("Set COHERE_API_KEY (and revoke the one committed in the notebook).")

    import cohere
    co = cohere.ClientV2(api_key=api_key)

    rows, flagged, attempts_used = [], [], []
    for i in range(len(df)):
        d = local.data(i)
        contribs = [(n, s, v) for n, s, v in
                    zip(d["names"], d["scores"], X.iloc[i].values)
                    if n.lower() != "intercept"]

        prompt = build_prompt(df.iloc[i]["review_text"], preds[i], contribs)
        mixed = ("Genuine" if sum(s for _, s, _ in contribs) >= 0
                 else "Deceptive") != preds[i]
        print(f"  [{i+1}/{len(df)}] review_id {df.iloc[i]['review_id']} "
              f"(set {df.iloc[i]['review_set']}, {preds[i]})"
              f"{'  [mixed evidence]' if mixed else ''}...")

        # Regenerate on a hard fault. The prompt is never altered between
        # attempts - every explanation in the study comes from the same
        # prompt, so retrying only draws a different sample at temperature
        # 0.7. Most faults are stochastic (a score left unquoted) and clear
        # within an attempt or two.
        best = None
        for attempt in range(1, args.max_retries + 1):
            resp = co.chat(
                model=COHERE_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300,
            )
            text_out = resp.message.content[0].text.strip()
            flags = audit(text_out, str(preds[i]), contribs)
            hard = [f for f in flags if is_hard(f)]

            # Keep the cleanest attempt in case none comes back perfect
            if best is None or len(hard) < len(best[1]):
                best = (text_out, hard, flags, attempt)

            if not hard:
                if attempt > 1:
                    print(f"        clean on attempt {attempt}")
                break

            for f in hard:
                print(f"        attempt {attempt} FAULT: {f}")
            if attempt < args.max_retries:
                print(f"        regenerating...")
                time.sleep(args.sleep)

        text_out, hard, flags, used_attempt = best
        attempts_used.append((int(df.iloc[i]["review_id"]), used_attempt,
                              len(hard)))
        if hard:
            print(f"        STILL FAULTY after {args.max_retries} attempts "
                  f"- kept the cleanest ({len(hard)} fault(s))")
        if flags:
            flagged.append((int(df.iloc[i]["review_id"]), flags))

        rows.append({
            "review_id": int(df.iloc[i]["review_id"]),
            "review_text": df.iloc[i]["review_text"],
            "emo": float(df.iloc[i][FEATURE_COLS[0]]),
            "adj": float(df.iloc[i][FEATURE_COLS[1]]),
            "read": float(df.iloc[i][FEATURE_COLS[2]]),
            "analytic": float(df.iloc[i][FEATURE_COLS[3]]),
            "ebm_prediction": df.iloc[i]["ebm_prediction"],
            "model_prediction": str(preds[i]),
            "explanation": text_out,
            "contributions": json.dumps({n: round(float(s), 4) for n, s, _ in contribs}),
            "generator_model": COHERE_MODEL,
        })
        time.sleep(args.sleep)

    # Save before inserting, so a database failure never costs the API spend
    backup = "./data/stages_data/nl_explanations_generated.csv"
    pd.DataFrame(rows).to_csv(backup, index=False)
    print(f"\nGenerated text saved to {backup}")

    retried = [(rid, a) for rid, a, _ in attempts_used if a > 1]
    print(f"\nGenerated on first attempt: {len(rows) - len(retried)}/{len(rows)}")
    if retried:
        print(f"Regenerated: {len(retried)} "
              f"({', '.join(f'id {r} x{a}' for r, a in retried)})")

    hard = [(rid, [f for f in fs if is_hard(f)]) for rid, fs in flagged]
    hard = [(rid, fs) for rid, fs in hard if fs]

    if flagged:
        print(f"\n{len(flagged)} of {len(rows)} explanation(s) carry a flag "
              f"({len(hard)} unresolved, {len(flagged) - len(hard)} soft):")
        for rid, fs in flagged:
            for f in fs:
                kind = "UNRESOLVED" if is_hard(f) else "soft"
                print(f"  [{kind}] review_id {rid}: {f}")

    if hard:
        if not args.force:
            print("\nNothing was written to the database.")
            print(f"These survived {args.max_retries} regeneration attempts, so "
                  "they are unlikely to\nclear on their own. Read them in the "
                  "CSV, edit if needed, then load with\n--from-csv - or accept "
                  "them with --force.")
            return
        print("\n--force given: appending despite unresolved faults.")

    print(f"\nAppending {len(rows)} explanation(s)...")
    insert_explanations(engine, rows)
    print("Done - no existing rows were modified.")
    print(f"Model: {COHERE_MODEL} - record this in the methods section.")
    print("\nBefore going live, read all 36 explanations yourself. The "
          "automated audit catches missing scores and inverted wording, not "
          "a fluent explanation that misreads the review.")


if __name__ == "__main__":
    main()

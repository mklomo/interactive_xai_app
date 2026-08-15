"""Build stratified Stage-2 review sets.

Each set of 12 reviews is stratified on three variables simultaneously:

    ground truth      6 genuine / 6 deceptive
    EBM verdict       6 genuine / 6 deceptive
    EBM correctness   9 correct / 3 incorrect

Those three constraints determine the four cells exactly:

                     verdict: deceptive   verdict: genuine
    truly deceptive        5 (correct)       1 (false negative)
    truly genuine          1 (false positive) 5 (correct)

  -> 6 deceptive verdicts, 6 genuine verdicts, 10 correct, 2 wrong

The 10/2 split gives 83% accuracy. To hit 75% (9 correct, 3 wrong) while
keeping verdicts at 6/6, one cell must be 4/2 instead of 5/1 -- see
TARGET_75 below. Pick whichever composition you intend and record it.

Usage
-----
    python build_stage2_sets.py pool.csv --sets 4 --seed 20260812 \
        --out ../data/stages_data/

`pool.csv` must contain, one row per candidate review:
    review_text, label, ebm_prediction, model_pred_confidence,
    proportion_of_emotional_content_in_review,
    proportion_of_adjectives_in_review,
    readability_of_review, analytic_writing_style

`label` and `ebm_prediction` take the values "Genuine" / "Deceptive".
Reviews already used in Stage 1 or Stage 3 must be excluded beforehand.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# (true label, ebm verdict) -> how many of that cell per set of 12.
#
# 50% is the only target that balances all three variables at once:
# 6/6 verdicts, 6/6 ground truth AND 6/6 correctness force 3 per cell.
# It also gives RAIR and RSR equal denominators of 6, which is the
# composition Schemmer et al. (2023) used for the same reason.
TARGET_50 = {
    ("Deceptive", "Deceptive"): 3,   # true positive
    ("Genuine", "Deceptive"): 3,     # false positive
    ("Genuine", "Genuine"): 3,       # true negative
    ("Deceptive", "Genuine"): 3,     # false negative
}

# 6/6 verdicts, 6/6 truth, 10 correct + 2 wrong  (83% accuracy)
TARGET_83 = {
    ("Deceptive", "Deceptive"): 5,
    ("Genuine", "Deceptive"): 1,
    ("Genuine", "Genuine"): 5,
    ("Deceptive", "Genuine"): 1,
}

# 6/6 verdicts, 9 correct + 3 wrong  (75% accuracy, truth 7/5)
TARGET_75 = {
    ("Deceptive", "Deceptive"): 5,
    ("Genuine", "Deceptive"): 1,
    ("Genuine", "Genuine"): 4,
    ("Deceptive", "Genuine"): 2,
}

TARGETS = {"50": TARGET_50, "83": TARGET_83, "75": TARGET_75}


def build_sets(pool: pd.DataFrame, n_sets: int, target: dict, seed: int):
    """Draw n_sets disjoint sets, each matching the target cell counts."""
    rng = pd.Series(range(len(pool))).sample(frac=1, random_state=seed).index
    pool = pool.iloc[rng].reset_index(drop=True)

    need = {cell: n * n_sets for cell, n in target.items()}
    have = (
        pool.groupby(["label", "ebm_prediction"]).size().to_dict()
    )

    shortfalls = {
        cell: (need[cell], have.get(cell, 0))
        for cell in need
        if have.get(cell, 0) < need[cell]
    }
    if shortfalls:
        for cell, (want, got) in shortfalls.items():
            print(f"  need {want:>3} of {cell}, pool has {got}", file=sys.stderr)
        raise SystemExit("Pool too small - add reviews or reduce --sets.")

    sets = {s: [] for s in range(1, n_sets + 1)}
    for (label, verdict), per_set in target.items():
        cell = pool[
            (pool["label"] == label) & (pool["ebm_prediction"] == verdict)
        ]
        cursor = 0
        for s in range(1, n_sets + 1):
            sets[s].append(cell.iloc[cursor : cursor + per_set])
            cursor += per_set

    return {s: pd.concat(rows).sample(frac=1, random_state=seed + s)
            for s, rows in sets.items()}


def report(sets: dict):
    print(f"\n{'set':>4} {'n':>3} {'verdict D/G':>12} {'truth D/G':>10} "
          f"{'correct':>8} {'accuracy':>9}")
    print("-" * 52)
    for s, df in sets.items():
        vd = (df["ebm_prediction"] == "Deceptive").sum()
        td = (df["label"] == "Deceptive").sum()
        correct = (df["label"] == df["ebm_prediction"]).sum()
        print(f"{s:>4} {len(df):>3} {f'{vd}/{len(df)-vd}':>12} "
              f"{f'{td}/{len(df)-td}':>10} {correct:>8} "
              f"{correct/len(df):>8.1%}")

    print("\nPrecision by verdict")
    for s, df in sets.items():
        line = [f"  set {s}:"]
        for verdict in ("Deceptive", "Genuine"):
            sub = df[df["ebm_prediction"] == verdict]
            if len(sub):
                p = (sub["label"] == verdict).mean()
                line.append(f"{verdict} {p:.0%} (n={len(sub)})")
        print("  ".join(line))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pool", type=Path, help="scored hold-out pool CSV")
    ap.add_argument("--sets", type=int, default=3)
    ap.add_argument("--accuracy", choices=TARGETS, default="50")
    ap.add_argument("--seed", type=int, default=20260812)
    ap.add_argument("--out", type=Path, default=Path("."))
    ap.add_argument("--exclude", type=Path, nargs="*", default=[],
                    help="CSVs whose review_text must be kept out of the pool")
    args = ap.parse_args()

    pool = pd.read_csv(args.pool)
    required = {"review_text", "label", "ebm_prediction"}
    missing = required - set(pool.columns)
    if missing:
        raise SystemExit(f"pool is missing columns: {sorted(missing)}")

    # Drop reviews already used elsewhere, then de-duplicate.
    def key(s):
        return s.str.strip().str.strip('"').str.replace(r"\s+", " ", regex=True)

    pool["_key"] = key(pool["review_text"])
    if "stage" in pool.columns:
        pool = pool[pool["stage"].isna()]
    for path in args.exclude:
        used = pd.read_csv(path)
        pool = pool[~pool["_key"].isin(set(key(used["review_text"])))]
    before = len(pool)
    pool = pool.drop_duplicates("_key").drop(columns="_key")
    if before != len(pool):
        print(f"removed {before - len(pool)} duplicate review(s)")
    print(f"pool available: {len(pool)} reviews")

    sets = build_sets(pool, args.sets, TARGETS[args.accuracy], args.seed)
    report(sets)

    args.out.mkdir(parents=True, exist_ok=True)
    combined = []
    for s, df in sets.items():
        df = df.copy()
        df["stage"] = 2
        df["review_set"] = s
        df.to_csv(args.out / f"stage_2_set_{s}.csv", index=False)
        combined.append(df)

    all_sets = pd.concat(combined)
    all_sets.to_csv(args.out / "stage_2_all_sets.csv", index=False)
    print(f"\nWrote {args.sets} sets ({len(all_sets)} reviews) to {args.out}")
    print(f"Seed {args.seed} - record this in the methods section.")


if __name__ == "__main__":
    main()

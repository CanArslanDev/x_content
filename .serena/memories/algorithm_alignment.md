# X Algorithm Alignment Status

## Verified Against
- `x-algorithm/home-mixer/scorers/weighted_scorer.rs` — WeightedScorer
- `x-algorithm/home-mixer/scorers/phoenix_scorer.rs` — PhoenixScorer  
- `x-algorithm/home-mixer/candidate_pipeline/candidate.rs` — PhoenixScores struct
- `x-algorithm/phoenix/runners.py` — ACTIONS list, RankingOutput

## Fully Aligned
- 19 signal names match Phoenix `runners.py:202-222` exactly
- Signal order matches PhoenixScores struct
- `repost_score` is correct (Phoenix name; home-mixer renames to `retweet_score`)
- VQV weight eligibility: no media → weight=0 (weighted_scorer.rs:72-81)
- `offset_score` 3-branch formula matches weighted_scorer.rs:83-91
- `compute_weighted_score` applies offset at the end (weighted_scorer.rs:69)
- No category system (was removed — never existed in algorithm)
- No SIGNAL_MAP (was removed — never existed in algorithm)

## Known Approximations (Cannot Control)
- Weight values are community estimates (real `params` module excluded)
- `NEGATIVE_SCORES_OFFSET` derived as `NEGATIVE_WEIGHTS_SUM / WEIGHTS_SUM`
- `normalize_score` is approximate (real `score_normalizer` excluded)
- `dwell_time` weight labeled `CONT_DWELL_TIME_WEIGHT` in source (continuous action)

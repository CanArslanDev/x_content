"""X algorithm knowledge base.

Derived from x-algorithm source: phoenix/runners.py:202-222 (19 ACTIONS)
and home-mixer scoring logic (weighted_scorer.rs).
"""

# The 19 engagement actions predicted by the Phoenix model.
# Each tweet gets a probability score [0, 1] for every action.
# Final ranking = weighted sum of these probabilities.
ACTIONS: list[str] = [
    "favorite_score",            # 0  - Like (PRIMARY ranking signal)
    "reply_score",               # 1  - Reply (deep engagement)
    "repost_score",              # 2  - Retweet (virality multiplier)
    "photo_expand_score",        # 3  - Photo expansion click
    "click_score",               # 4  - General click
    "profile_click_score",       # 5  - Profile click
    "vqv_score",                 # 6  - Video quality view
    "share_score",               # 7  - Share (general)
    "share_via_dm_score",        # 8  - DM share (VERY STRONG signal)
    "share_via_copy_link_score", # 9  - Copy link share
    "dwell_score",               # 10 - Dwell probability (started reading)
    "quote_score",               # 11 - Quote tweet
    "quoted_click_score",        # 12 - Clicked on quoted tweet
    "follow_author_score",       # 13 - Followed author after seeing tweet
    "not_interested_score",      # 14 - NEGATIVE: marked "not interested"
    "block_author_score",        # 15 - NEGATIVE: blocked author
    "mute_author_score",         # 16 - NEGATIVE: muted author
    "report_score",              # 17 - NEGATIVE: reported tweet
    "dwell_time",                # 18 - Read duration (continuous, not binary)
]

# Human-readable labels for display
ACTION_LABELS: dict[str, str] = {
    "favorite_score": "Like",
    "reply_score": "Reply",
    "repost_score": "Retweet",
    "photo_expand_score": "Photo Expand",
    "click_score": "Click",
    "profile_click_score": "Profile Click",
    "vqv_score": "Video View",
    "share_score": "Share",
    "share_via_dm_score": "DM Share",
    "share_via_copy_link_score": "Copy Link",
    "dwell_score": "Dwell",
    "quote_score": "Quote Tweet",
    "quoted_click_score": "Quoted Click",
    "follow_author_score": "Follow Author",
    "not_interested_score": "Not Interested",
    "block_author_score": "Block",
    "mute_author_score": "Mute",
    "report_score": "Report",
    "dwell_time": "Read Duration",
}

# Negative signals — higher = worse for ranking
NEGATIVE_ACTIONS = {
    "not_interested_score",
    "block_author_score",
    "mute_author_score",
    "report_score",
}

# Approximate weights derived from x-algorithm weighted_scorer logic.
# Positive signals get positive weights; negative signals get large negative weights.
# These reflect relative importance in the combined ranking score.
ACTION_WEIGHTS: dict[str, float] = {
    "favorite_score": 1.0,
    "reply_score": 27.0,
    "repost_score": 10.0,
    "photo_expand_score": 0.3,
    "click_score": 0.3,
    "profile_click_score": 2.0,
    "vqv_score": 0.2,
    "share_score": 1.0,
    "share_via_dm_score": 100.0,    # strongest positive signal
    "share_via_copy_link_score": 5.0,
    "dwell_score": 2.0,
    "quote_score": 40.0,
    "quoted_click_score": 0.5,
    "follow_author_score": 10.0,
    "not_interested_score": -74.0,
    "block_author_score": -371.0,
    "mute_author_score": -74.0,
    "report_score": -9209.0,        # strongest negative signal
    "dwell_time": 0.8,              # CONT_DWELL_TIME_WEIGHT (continuous action)
}

# Derived weight constants (weighted_scorer.rs:83-91)
WEIGHTS_SUM = sum(w for w in ACTION_WEIGHTS.values() if w > 0)
NEGATIVE_WEIGHTS_SUM = sum(abs(w) for w in ACTION_WEIGHTS.values() if w < 0)
NEGATIVE_SCORES_OFFSET = NEGATIVE_WEIGHTS_SUM / max(WEIGHTS_SUM, 1)


def compute_weighted_score(scores: dict[str, float],
                           has_media: bool = False) -> float:
    """Compute the weighted score from 19 dimension scores.

    Mirrors x-algorithm WeightedScorer (weighted_scorer.rs:44-70):
    1. combined = sum(score_i * weight_i)  (with VQV eligibility check)
    2. return offset_score(combined)

    VQV weight eligibility (weighted_scorer.rs:72-81):
    if no video/media, vqv_score weight is set to 0.
    """
    total = 0.0
    for action in ACTIONS:
        score = scores.get(action, 0.0)
        weight = ACTION_WEIGHTS.get(action, 0.0)
        # VQV weight eligibility: no media → vqv weight = 0
        if action == "vqv_score" and not has_media:
            weight = 0.0
        total += score * weight
    return offset_score(total)


def offset_score(raw_score: float) -> float:
    """Apply offset transformation to raw weighted score.

    From weighted_scorer.rs:83-91:
    - If WEIGHTS_SUM == 0: max(combined, 0)
    - If combined < 0: (combined + NEGATIVE_WEIGHTS_SUM) / WEIGHTS_SUM * NEGATIVE_SCORES_OFFSET
    - Else: combined + NEGATIVE_SCORES_OFFSET
    """
    if WEIGHTS_SUM == 0:
        return max(raw_score, 0.0)
    if raw_score < 0:
        return (raw_score + NEGATIVE_WEIGHTS_SUM) / WEIGHTS_SUM * NEGATIVE_SCORES_OFFSET
    return raw_score + NEGATIVE_SCORES_OFFSET


def normalize_score(raw_score: float, min_score: float = -100.0,
                    max_score: float = 300.0) -> float:
    """Normalize raw score to a 0-100 scale.

    Note: approximate — the actual score_normalizer implementation is
    excluded from x-algorithm open source. This uses offset + linear
    clamping as a reasonable approximation.
    """
    offset = offset_score(raw_score)
    clamped = max(min_score, min(max_score, offset))
    return ((clamped - min_score) / (max_score - min_score)) * 100.0

"""X algorithm knowledge base.

Derived from x-algorithm source: phoenix/runners.py:202-222 (19 ACTIONS)
and home-mixer scoring logic.
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
    "dwell_time": 0.8,
}


# Content-to-signal map: which tweet features influence which signals.
# Used by scorer.py to estimate per-signal scores from structural features.
SIGNAL_MAP: dict[str, dict] = {
    "favorite_score": {
        "drivers": ["emotional_resonance", "relatable_content", "strong_opinion",
                     "humor", "visual_appeal"],
        "description": "Probability user taps Like. Driven by emotional impact and relatability.",
    },
    "reply_score": {
        "drivers": ["question", "controversial_take", "incomplete_thought",
                     "call_to_action", "debate_trigger"],
        "description": "Probability user replies. Questions and debate-provoking content drive this.",
    },
    "repost_score": {
        "drivers": ["quotable_insight", "data_stat", "universal_truth",
                     "identity_signal", "useful_tip"],
        "description": "Probability user retweets. Shareable, identity-reinforcing content wins.",
    },
    "photo_expand_score": {
        "drivers": ["has_media", "intriguing_preview", "data_visualization"],
        "description": "Probability user expands attached photo.",
    },
    "click_score": {
        "drivers": ["has_url", "curiosity_gap", "teaser_text"],
        "description": "Probability user clicks a link in the tweet.",
    },
    "profile_click_score": {
        "drivers": ["authority_signal", "unique_perspective", "credibility_marker",
                     "curiosity_about_author"],
        "description": "Probability user clicks author profile. Expertise signals drive this.",
    },
    "vqv_score": {
        "drivers": ["has_video", "video_hook_text", "native_video"],
        "description": "Probability user watches video to quality threshold.",
    },
    "share_score": {
        "drivers": ["useful_content", "save_worthy", "reference_material",
                     "actionable_advice"],
        "description": "General share probability. Utility and reference value matter.",
    },
    "share_via_dm_score": {
        "drivers": ["personal_relevance", "conversation_starter", "niche_insight",
                     "surprising_fact", "emotionally_moving"],
        "description": "DM share probability. THE STRONGEST positive signal. Content people send to specific friends.",
    },
    "share_via_copy_link_score": {
        "drivers": ["cross_platform_value", "reference_material", "comprehensive_take"],
        "description": "Copy-link share probability. Content worth sharing outside X.",
    },
    "dwell_score": {
        "drivers": ["hook_first_line", "line_breaks", "storytelling",
                     "progressive_reveal"],
        "description": "Probability user pauses to read. Strong hooks and formatting matter.",
    },
    "quote_score": {
        "drivers": ["hot_take", "framework", "data_claim", "reaction_worthy",
                     "addable_context"],
        "description": "Probability user quote-tweets. Content that invites commentary.",
    },
    "quoted_click_score": {
        "drivers": ["embedded_quote_tweet", "referenced_content"],
        "description": "Probability user clicks on an embedded quote tweet.",
    },
    "follow_author_score": {
        "drivers": ["expertise_signal", "unique_niche", "consistent_value",
                     "personality_display"],
        "description": "Probability user follows after seeing tweet. Authority and uniqueness drive this.",
    },
    "not_interested_score": {
        "drivers": ["irrelevant_topic", "low_effort", "spam_signals",
                     "excessive_hashtags", "engagement_bait"],
        "description": "NEGATIVE. Probability user marks 'not interested'. Avoid spam patterns.",
    },
    "block_author_score": {
        "drivers": ["offensive_content", "harassment", "extreme_spam",
                     "misleading_content"],
        "description": "NEGATIVE. Probability user blocks. Extremely costly to ranking.",
    },
    "mute_author_score": {
        "drivers": ["repetitive_content", "excessive_posting", "mild_annoyance",
                     "off_topic"],
        "description": "NEGATIVE. Probability user mutes author.",
    },
    "report_score": {
        "drivers": ["policy_violation", "misinformation", "hate_speech",
                     "graphic_content"],
        "description": "NEGATIVE. THE STRONGEST negative signal. Content that violates platform rules.",
    },
    "dwell_time": {
        "drivers": ["long_form_content", "detailed_explanation", "storytelling",
                     "multi_line_format", "hook_then_payoff"],
        "description": "Expected read duration. Longer dwell = higher quality signal. Formatting matters.",
    },
}


def compute_weighted_score(scores: dict[str, float]) -> float:
    """Compute the combined weighted score from 19 dimension scores.

    Mirrors the x-algorithm WeightedScorer:
    combined = sum(score_i * weight_i)

    Negative actions contribute negatively via their negative weights.
    """
    total = 0.0
    for action in ACTIONS:
        score = scores.get(action, 0.0)
        weight = ACTION_WEIGHTS.get(action, 0.0)
        total += score * weight
    return total


def offset_score(raw_score: float) -> float:
    """Apply offset transformation to raw weighted score.

    From weighted_scorer.rs: negative scores are scaled differently
    to penalize bad content more harshly.
    """
    if raw_score >= 0:
        return raw_score
    return raw_score * 2.0  # negative scores weighted 2x


def normalize_score(raw_score: float, min_score: float = -100.0,
                    max_score: float = 300.0) -> float:
    """Normalize raw score to 0-100 percentage scale."""
    offset = offset_score(raw_score)
    clamped = max(min_score, min(max_score, offset))
    return ((clamped - min_score) / (max_score - min_score)) * 100.0

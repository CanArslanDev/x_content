"""Heuristic 19-dimension score estimator.

Estimates P(action) for each of the 19 signals based on structural
tweet features. Produces scores for both original and optimized tweets
to generate comparison reports.
"""

from x_content.algorithm import ACTIONS, NEGATIVE_ACTIONS, ACTION_WEIGHTS
from x_content import config


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def score_tweet(analysis: dict) -> dict[str, float]:
    """Estimate 0.0-1.0 heuristic score for each of the 19 signals.

    Uses structural features from analyzer.py and the content-to-signal
    map from algorithm.py to produce probability estimates.
    """
    s: dict[str, float] = {}
    a = analysis  # shorthand

    # --- POSITIVE SIGNALS ---

    # favorite_score: emotional resonance, power words, opinion strength
    base_fav = 0.20
    if a["power_word_count"] > 0:
        base_fav += min(a["power_word_count"] * 0.08, 0.25)
    if a["has_question"]:
        base_fav += 0.05
    if a["emoji_count"] > 0:
        base_fav += 0.05
    if a["char_utilization"] > 50:
        base_fav += 0.10
    if a["has_media"]:
        base_fav += 0.10
    s["favorite_score"] = _clamp(base_fav)

    # reply_score: questions, debate triggers, CTAs
    base_reply = 0.10
    if a["has_question"]:
        base_reply += 0.15 * min(a["question_count"], 3)
    if a["has_cta"]:
        base_reply += 0.10
    if a["power_word_count"] > 0:
        base_reply += 0.08
    if a["line_count"] >= 3:
        base_reply += 0.05
    s["reply_score"] = _clamp(base_reply)

    # repost_score: quotable insights, data, universal truths
    base_rt = 0.15
    if a["has_numbers"]:
        base_rt += 0.12
    if a["power_word_count"] >= 2:
        base_rt += 0.10
    if 100 < a["char_count"] < 200:
        base_rt += 0.08  # sweet spot for retweetability
    if a["has_list_format"]:
        base_rt += 0.05
    s["repost_score"] = _clamp(base_rt)

    # photo_expand_score
    base_photo = 0.05
    if a["has_media"]:
        base_photo += 0.50
    s["photo_expand_score"] = _clamp(base_photo)

    # click_score: URLs, curiosity gaps
    base_click = 0.05
    if a["has_url"]:
        base_click += 0.35
    if a["power_word_count"] > 0 and a["has_url"]:
        base_click += 0.10
    s["click_score"] = _clamp(base_click)

    # profile_click_score: authority, unique perspective
    base_profile = 0.10
    if a["power_word_count"] >= 2:
        base_profile += 0.10
    if a["has_numbers"]:
        base_profile += 0.08
    if a["char_utilization"] > 60:
        base_profile += 0.05
    s["profile_click_score"] = _clamp(base_profile)

    # vqv_score: video content
    base_vqv = 0.02
    if a["has_media"]:
        base_vqv += 0.15  # could be video
    s["vqv_score"] = _clamp(base_vqv)

    # share_score: useful, save-worthy content
    base_share = 0.10
    if a["has_list_format"]:
        base_share += 0.15
    if a["has_numbers"]:
        base_share += 0.10
    if a["power_word_count"] > 0:
        base_share += 0.05
    if a["char_utilization"] > 50:
        base_share += 0.05
    s["share_score"] = _clamp(base_share)

    # share_via_dm_score: personal relevance, surprising, niche
    base_dm = 0.05
    if a["power_word_count"] >= 2:
        base_dm += 0.12
    if a["has_numbers"]:
        base_dm += 0.08
    if a["has_question"] and a["power_word_count"] > 0:
        base_dm += 0.10
    if a["char_utilization"] > 60:
        base_dm += 0.05
    s["share_via_dm_score"] = _clamp(base_dm)

    # share_via_copy_link_score: cross-platform value
    base_copy = 0.05
    if a["has_list_format"]:
        base_copy += 0.12
    if a["has_numbers"]:
        base_copy += 0.08
    if a["char_utilization"] > 70:
        base_copy += 0.05
    s["share_via_copy_link_score"] = _clamp(base_copy)

    # dwell_score: hook + formatting
    base_dwell = 0.15
    if a["has_hook"]:
        base_dwell += 0.15
    if a["line_count"] >= 3:
        base_dwell += 0.10
    if a["char_utilization"] > 50:
        base_dwell += 0.10
    s["dwell_score"] = _clamp(base_dwell)

    # quote_score: hot takes, frameworks, reaction-worthy
    base_quote = 0.08
    if a["power_word_count"] >= 2:
        base_quote += 0.12
    if a["has_numbers"]:
        base_quote += 0.08
    if a["has_question"]:
        base_quote += 0.05
    s["quote_score"] = _clamp(base_quote)

    # quoted_click_score: low unless quoting
    s["quoted_click_score"] = 0.05

    # follow_author_score: expertise signals
    base_follow = 0.08
    if a["has_numbers"]:
        base_follow += 0.08
    if a["power_word_count"] >= 2:
        base_follow += 0.08
    if a["char_utilization"] > 60:
        base_follow += 0.05
    s["follow_author_score"] = _clamp(base_follow)

    # --- NEGATIVE SIGNALS (lower is better) ---

    # not_interested_score
    base_ni = 0.10
    if a["hashtag_count"] > 3:
        base_ni += 0.15
    if a["char_utilization"] < 15:
        base_ni += 0.10  # very short low-effort
    if a["cta_count"] > 2:
        base_ni += 0.08  # too pushy
    s["not_interested_score"] = _clamp(base_ni)

    # block_author_score
    base_block = 0.03
    if a["hashtag_count"] > 5:
        base_block += 0.05
    s["block_author_score"] = _clamp(base_block)

    # mute_author_score
    base_mute = 0.05
    if a["hashtag_count"] > 3:
        base_mute += 0.05
    s["mute_author_score"] = _clamp(base_mute)

    # report_score
    s["report_score"] = 0.02

    # dwell_time: reading duration
    base_dwell_t = 0.15
    if a["line_count"] >= 4:
        base_dwell_t += 0.15
    if a["char_utilization"] > 60:
        base_dwell_t += 0.15
    if a["has_hook"]:
        base_dwell_t += 0.10
    if a["has_list_format"]:
        base_dwell_t += 0.10
    s["dwell_time"] = _clamp(base_dwell_t)

    return s


def compute_delta(original: dict[str, float],
                  optimized: dict[str, float]) -> dict[str, dict]:
    """Compute per-signal percentage change between original and optimized scores.

    Returns dict mapping action -> {original, optimized, delta_pct, direction}.
    """
    result = {}
    for action in ACTIONS:
        orig = original.get(action, 0.0)
        opt = optimized.get(action, 0.0)
        delta_pct = ((opt - orig) / max(orig, 0.01)) * 100
        is_negative = action in NEGATIVE_ACTIONS
        # For negative signals, decrease is an improvement
        if is_negative:
            direction = "improved" if delta_pct < 0 else "worse"
        else:
            direction = "improved" if delta_pct > 0 else "worse"
        result[action] = {
            "original": orig,
            "optimized": opt,
            "delta_pct": round(delta_pct, 1),
            "direction": direction,
        }
    return result


def compute_category_scores(scores: dict[str, float]) -> dict[str, float]:
    """Compute 5 categorical metric scores (0.0-1.0) from 19 signal scores.

    Categories: engagement, discoverability, shareability, content_quality, safety.
    Safety is inverted (lower negative signals = higher safety score).
    """
    cfg = config.get("categories", {})

    categories = {}
    for cat_name, signals in cfg.items():
        if cat_name == "safety":
            # Invert: low negative scores = high safety
            raw = sum(scores.get(s, 0.0) for s in signals) / max(len(signals), 1)
            categories[cat_name] = _clamp(1.0 - raw)
        else:
            total = sum(scores.get(s, 0.0) for s in signals)
            categories[cat_name] = _clamp(total / max(len(signals), 1))
    return categories


def compute_overall_score(category_scores: dict[str, float]) -> float:
    """Compute weighted overall algorithm compatibility score (0-100).

    Overall = (0.35 * Engagement + 0.20 * Discoverability
             + 0.25 * Shareability + 0.15 * Content Quality
             + 0.05 * Safety) * 100
    """
    weights = config.get("category_weights", {
        "engagement": 0.35,
        "discoverability": 0.20,
        "shareability": 0.25,
        "content_quality": 0.15,
        "safety": 0.05,
    })
    total = sum(
        category_scores.get(cat, 0.0) * w
        for cat, w in weights.items()
    )
    return round(total * 100, 1)


def full_score_report(analysis: dict) -> dict:
    """Generate complete scoring report for a single tweet.

    Returns dict with: signals (19 scores), categories (5 scores), overall.
    """
    signals = score_tweet(analysis)
    categories = compute_category_scores(signals)
    overall = compute_overall_score(categories)
    return {
        "signals": signals,
        "categories": categories,
        "overall": overall,
    }


def comparison_report(original_analysis: dict,
                      optimized_scores: dict[str, float]) -> dict:
    """Generate full comparison between original tweet and optimized variation.

    Returns dict with: original (full report), optimized (scores + categories + overall),
    delta (per-signal changes), category_delta.
    """
    orig_report = full_score_report(original_analysis)

    opt_categories = compute_category_scores(optimized_scores)
    opt_overall = compute_overall_score(opt_categories)

    delta = compute_delta(orig_report["signals"], optimized_scores)

    category_delta = {}
    for cat in orig_report["categories"]:
        orig_val = orig_report["categories"][cat]
        opt_val = opt_categories.get(cat, 0.0)
        category_delta[cat] = {
            "original": round(orig_val * 100, 1),
            "optimized": round(opt_val * 100, 1),
            "change": round((opt_val - orig_val) * 100, 1),
        }

    return {
        "original": orig_report,
        "optimized": {
            "signals": optimized_scores,
            "categories": opt_categories,
            "overall": opt_overall,
        },
        "delta": delta,
        "category_delta": category_delta,
        "overall_change": round(opt_overall - orig_report["overall"], 1),
    }

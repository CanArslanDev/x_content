"""Terminal output formatting.

Renders signal comparisons, category bars, and summary tables.
"""

from x_content.algorithm import ACTIONS, ACTION_LABELS, NEGATIVE_ACTIONS
from x_content import config


# Box drawing characters
H_LINE = "\u2500"       # ─
D_LINE = "\u2550"       # ═
V_LINE = "\u2502"       # │
TL = "\u256d"           # ╭ (rounded) or \u2554 ╔
TR = "\u256e"           # ╮ or \u2557 ╗
BL = "\u2570"           # ╰ or \u255a ╚
BR = "\u256f"           # ╯ or \u255d ╝
BOX_TL = "\u2554"       # ╔
BOX_TR = "\u2557"       # ╗
BOX_BL = "\u255a"       # ╚
BOX_BR = "\u255d"       # ╝
BOX_H = "\u2550"        # ═
BOX_V = "\u2551"        # ║
BOX_T = "\u2566"        # ╦
BOX_B = "\u2569"        # ╩
BOX_L = "\u2560"        # ╠
BOX_R = "\u2563"        # ╣

BLOCK_FULL = "\u2588"   # █
BLOCK_EMPTY = "\u2591"  # ░

WIDTH = 68


def _bar(value: float, width: int = 24) -> str:
    """Render a progress bar."""
    cfg_width = config.get("display", {}).get("bar_width", width)
    filled = int(value * cfg_width)
    return BLOCK_FULL * filled + BLOCK_EMPTY * (cfg_width - filled)


def _change_arrows(delta_pct: float, is_negative: bool = False) -> str:
    """Render change arrows based on percentage change."""
    if is_negative:
        # For negative signals, decrease is good
        if delta_pct <= -50:
            return "\u25bc\u25bc (improved)"    # ▼▼
        elif delta_pct < 0:
            return "\u25bc (improved)"           # ▼
        elif delta_pct > 50:
            return "\u25b2\u25b2 (worse)"        # ▲▲
        elif delta_pct > 0:
            return "\u25b2 (worse)"              # ▲
        return ""
    else:
        abs_d = abs(delta_pct)
        if abs_d >= 300:
            arrows = "\u25b2\u25b2\u25b2\u25b2" if delta_pct > 0 else "\u25bc\u25bc\u25bc\u25bc"
        elif abs_d >= 100:
            arrows = "\u25b2\u25b2\u25b2" if delta_pct > 0 else "\u25bc\u25bc\u25bc"
        elif abs_d >= 50:
            arrows = "\u25b2\u25b2" if delta_pct > 0 else "\u25bc\u25bc"
        elif abs_d > 0:
            arrows = "\u25b2" if delta_pct > 0 else "\u25bc"
        else:
            return ""
        return arrows


def _box_line(text: str, width: int = WIDTH) -> str:
    """Render a line inside a box."""
    return f"{BOX_V}  {text:<{width - 4}}  {BOX_V}"


def _box_top(width: int = WIDTH) -> str:
    return BOX_TL + BOX_H * (width - 2) + BOX_TR


def _box_bottom(width: int = WIDTH) -> str:
    return BOX_BL + BOX_H * (width - 2) + BOX_BR


def _box_separator(width: int = WIDTH) -> str:
    return BOX_L + BOX_H * (width - 2) + BOX_R


def render_header() -> str:
    """Render the header box."""
    lines = [
        _box_top(),
        _box_line("X ALGORITHM TWEET OPTIMIZER"),
        _box_separator(),
    ]
    return "\n".join(lines)


def render_original(tweet: str, analysis: dict, report: dict) -> str:
    """Render original tweet section with signal profile."""
    overall = report["overall"]
    lang = analysis["lang"].upper()
    chars = analysis["char_count"]

    lines = [
        _box_line("Original Tweet"),
        _box_line(f'"{_truncate(tweet, WIDTH - 8)}"'),
        _box_line(f"Characters: {chars}/280 | Lang: {lang} | Algorithm Score: {overall:.0f}%"),
        _box_separator(),
    ]

    # Signal profile (top signals only)
    lines.append("")
    lines.append(f" Original Signal Profile:")
    lines.append(f" {H_LINE * 50}")

    display_cfg = config.get("display", {})
    show_all = display_cfg.get("show_all_signals", False)
    top_n = display_cfg.get("top_signals_count", 8)

    signals = report["signals"]
    if show_all:
        display_actions = ACTIONS
    else:
        # Show top N by weighted importance + all negatives
        scored = []
        for a in ACTIONS:
            if a in NEGATIVE_ACTIONS:
                scored.append((a, 999))  # always show
            else:
                scored.append((a, signals.get(a, 0.0)))
        scored.sort(key=lambda x: -x[1])
        display_actions = [a for a, _ in scored[:top_n]]

    for action in display_actions:
        val = signals.get(action, 0.0)
        label = ACTION_LABELS[action]
        bar = _bar(val, 20)
        risk = "  (risk)" if action in NEGATIVE_ACTIONS else ""
        padded_name = f"{action:<28}"
        lines.append(f" {padded_name} {bar} {val:>4.0%}{risk}")

    lines.append("")
    return "\n".join(lines)


def render_variation(
    index: int,
    variation: dict,
    comparison: dict | None,
    verbose: bool = False,
) -> str:
    """Render a single optimized variation with comparison data."""
    tweet = variation.get("tweet", "")
    strategy = variation.get("strategy", "")
    char_count = variation.get("char_count", len(tweet))
    media_sug = variation.get("media_suggestion", "")
    explanation = variation.get("explanation", "")

    opt_overall = 0.0
    overall_change = 0.0
    if comparison:
        opt_overall = comparison["optimized"]["overall"]
        overall_change = comparison["overall_change"]

    change_str = f"+{overall_change:.0f}pts" if overall_change >= 0 else f"{overall_change:.0f}pts"

    lines = [
        _box_separator(),
        _box_line(f'Variation {index}: "{strategy}"'),
        _box_line(f"Algorithm Compatibility: {opt_overall:.0f}% ({change_str})"),
        _box_separator(),
        _box_line(""),
    ]

    # Wrap tweet text
    for tweet_line in tweet.split("\n"):
        lines.append(_box_line(tweet_line))

    lines.append(_box_line(""))
    lines.append(_box_line(f"Characters: {char_count}/280"))
    lines.append(_box_line(""))

    # Signal changes
    if comparison:
        lines.append(_box_line("Signal Changes:"))
        lines.append(_box_line(H_LINE * 52))

        delta = comparison["delta"]
        display_cfg = config.get("display", {})
        show_all = display_cfg.get("show_all_signals", False)
        top_n = display_cfg.get("top_signals_count", 8)

        if show_all or verbose:
            display_actions = ACTIONS
        else:
            # Sort by absolute delta, show top N
            sorted_actions = sorted(
                ACTIONS,
                key=lambda a: abs(delta[a]["delta_pct"]),
                reverse=True,
            )
            display_actions = sorted_actions[:top_n]

        for action in display_actions:
            d = delta[action]
            is_neg = action in NEGATIVE_ACTIONS
            orig_pct = d["original"]
            opt_pct = d["optimized"]
            dpct = d["delta_pct"]
            arrows = _change_arrows(dpct, is_neg)
            sign = "+" if dpct >= 0 else ""
            name = f"{action:<28}"
            lines.append(
                _box_line(f"{name} {orig_pct:>3.0%} \u2192 {opt_pct:>3.0%}   {sign}{dpct:.1f}%   {arrows}")
            )

        lines.append(_box_line(""))

        # Category compatibility
        lines.append(_box_line("Category Compatibility:"))
        cat_delta = comparison["category_delta"]
        cat_order = ["engagement", "discoverability", "shareability",
                     "content_quality", "safety"]
        for cat in cat_order:
            if cat in cat_delta:
                cd = cat_delta[cat]
                opt_val = cd["optimized"]
                change = cd["change"]
                bar = _bar(opt_val / 100.0, 24)
                sign = "+" if change >= 0 else ""
                cat_label = cat.replace("_", " ").title()
                lines.append(
                    _box_line(f"{cat_label:<20} {bar} {opt_val:>3.0f}%  ({sign}{change:.0f}pts)")
                )

    lines.append(_box_line(""))

    if media_sug:
        lines.append(_box_line(f"Media Suggestion: {_truncate(media_sug, WIDTH - 22)}"))

    if explanation and verbose:
        lines.append(_box_line(f"Strategy: {_truncate(explanation, WIDTH - 14)}"))

    return "\n".join(lines)


def render_summary(
    original_overall: float,
    variations: list[dict],
    comparisons: list[dict | None],
) -> str:
    """Render summary comparison table."""
    lines = [
        _box_separator(),
        "",
        f" Summary Comparison:",
        f" {H_LINE * 56}",
        f" {'Variation':<12} {'Strategy':<24} {'Score':>6}   {'Change':>8}",
        f" {H_LINE * 56}",
        f" {'Original':<12} {'-':<24} {original_overall:>5.0f}%   {'-':>8}",
    ]

    for i, (var, comp) in enumerate(zip(variations, comparisons), 1):
        strategy = var.get("strategy", "")[:22]
        if comp:
            opt_score = comp["optimized"]["overall"]
            change = comp["overall_change"]
            sign = "+" if change >= 0 else ""
            lines.append(
                f" #{i:<11} {strategy:<24} {opt_score:>5.0f}%   {sign}{change:.0f}pts"
            )
        else:
            lines.append(f" #{i:<11} {strategy:<24}   {'N/A':>5}   {'N/A':>8}")

    lines.append(f" {H_LINE * 56}")
    lines.append("")
    return "\n".join(lines)


def render_full(result: dict, verbose: bool = False) -> str:
    """Render the complete optimization result."""
    parts = [
        render_header(),
        render_original(
            result["tweet"],
            result["analysis"],
            result["original_report"],
        ),
    ]

    for i, (var, comp) in enumerate(
        zip(result["variations"], result["comparisons"]), 1
    ):
        parts.append(render_variation(i, var, comp, verbose=verbose))

    parts.append(render_summary(
        result["original_report"]["overall"],
        result["variations"],
        result["comparisons"],
    ))

    if result.get("claude_analysis"):
        parts.append(f" Analysis: {result['claude_analysis']}")
        parts.append("")

    parts.append(_box_bottom())

    return "\n".join(parts)


def render_json(result: dict) -> str:
    """Render result as JSON string."""
    import json
    output = {
        "original": {
            "tweet": result["tweet"],
            "char_count": result["analysis"]["char_count"],
            "lang": result["lang"],
            "scores": result["original_report"]["signals"],
            "categories": result["original_report"]["categories"],
            "overall_score": result["original_report"]["overall"],
        },
        "variations": [],
        "analysis": result.get("claude_analysis", ""),
    }

    for var, comp in zip(result["variations"], result["comparisons"]):
        v = {
            "tweet": var.get("tweet", ""),
            "strategy": var.get("strategy", ""),
            "char_count": var.get("char_count", 0),
            "targeted_signals": var.get("targeted_signals", []),
            "scores": var.get("scores", {}),
            "media_suggestion": var.get("media_suggestion", ""),
            "explanation": var.get("explanation", ""),
        }
        if comp:
            v["overall_score"] = comp["optimized"]["overall"]
            v["overall_change"] = comp["overall_change"]
            v["category_scores"] = {
                k: round(v2 * 100, 1)
                for k, v2 in comp["optimized"]["categories"].items()
            }
        output["variations"].append(v)

    return json.dumps(output, indent=2, ensure_ascii=False)


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis if needed."""
    text = text.replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."

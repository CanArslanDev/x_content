"""Terminal output formatting.

Renders signal comparisons, score bars, and summary tables.
Uses ANSI colors, dynamic terminal width, and clean formatting
that makes tweet text easily copyable.
"""

import shutil
import textwrap

from x_content.algorithm import ACTIONS, ACTION_LABELS, NEGATIVE_ACTIONS
from x_content import config


# ── ANSI Color Codes ──────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

# Colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
WHITE = "\033[97m"
GRAY = "\033[90m"

# Bright variants
BRIGHT_CYAN = "\033[96m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_RED = "\033[91m"
BRIGHT_MAGENTA = "\033[95m"

# Background
BG_DARK = "\033[48;5;234m"
BG_DARKER = "\033[48;5;232m"

# ── Box Drawing Characters ────────────────────────────────────────
H_LINE = "\u2500"       # ─
BLOCK_FULL = "\u2588"   # █
BLOCK_MED = "\u2593"    # ▓
BLOCK_LIGHT = "\u2591"  # ░
ARROW_RIGHT = "\u2192"  # →
ARROW_UP = "\u25b2"     # ▲
ARROW_DOWN = "\u25bc"   # ▼
BULLET = "\u2022"       # •
CHECK = "\u2713"        # ✓
CROSS = "\u2717"        # ✗


def _get_width() -> int:
    """Get terminal width, with a sensible fallback."""
    try:
        cols = shutil.get_terminal_size().columns
        return min(max(cols, 60), 120)
    except Exception:
        return 80


def _bar(value: float, width: int = 20) -> str:
    """Render a colored progress bar."""
    cfg_width = config.get("display", {}).get("bar_width", width)
    filled = int(value * cfg_width)
    empty = cfg_width - filled

    if value >= 0.7:
        color = GREEN
    elif value >= 0.4:
        color = YELLOW
    else:
        color = DIM

    return f"{color}{BLOCK_FULL * filled}{GRAY}{BLOCK_LIGHT * empty}{RESET}"


def _bar_negative(value: float, width: int = 20) -> str:
    """Render a progress bar for negative signals (lower is better)."""
    cfg_width = config.get("display", {}).get("bar_width", width)
    filled = int(value * cfg_width)
    empty = cfg_width - filled

    if value <= 0.05:
        color = GREEN
    elif value <= 0.15:
        color = YELLOW
    else:
        color = RED

    return f"{color}{BLOCK_FULL * filled}{GRAY}{BLOCK_LIGHT * empty}{RESET}"


def _change_arrows(delta_pct: float, is_negative: bool = False) -> str:
    """Render colored change arrows."""
    if is_negative:
        if delta_pct <= -50:
            return f"{GREEN}{ARROW_DOWN}{ARROW_DOWN} improved{RESET}"
        elif delta_pct < 0:
            return f"{GREEN}{ARROW_DOWN} improved{RESET}"
        elif delta_pct > 50:
            return f"{RED}{ARROW_UP}{ARROW_UP} worse{RESET}"
        elif delta_pct > 0:
            return f"{RED}{ARROW_UP} worse{RESET}"
        return ""
    else:
        abs_d = abs(delta_pct)
        if abs_d >= 300:
            arrows = ARROW_UP * 4 if delta_pct > 0 else ARROW_DOWN * 4
        elif abs_d >= 100:
            arrows = ARROW_UP * 3 if delta_pct > 0 else ARROW_DOWN * 3
        elif abs_d >= 50:
            arrows = ARROW_UP * 2 if delta_pct > 0 else ARROW_DOWN * 2
        elif abs_d > 0:
            arrows = ARROW_UP if delta_pct > 0 else ARROW_DOWN
        else:
            return ""
        color = GREEN if delta_pct > 0 else RED
        return f"{color}{arrows}{RESET}"


def _header_line(text: str, width: int) -> str:
    """Create a styled header line."""
    pad = width - len(text) - 4
    return f"{BOLD}{CYAN}{'─' * 2} {text} {'─' * max(pad, 0)}{RESET}"


def _section_title(text: str) -> str:
    """Create a section title."""
    return f"\n  {BOLD}{WHITE}{text}{RESET}"


def _divider(width: int) -> str:
    """Create a subtle divider."""
    return f"  {GRAY}{'─' * (width - 4)}{RESET}"


def _wrap_text(text: str, width: int, indent: int = 4) -> list[str]:
    """Wrap text to fit terminal width."""
    lines = []
    for line in text.split("\n"):
        if len(line) + indent <= width:
            lines.append(line)
        else:
            wrapped = textwrap.wrap(line, width=width - indent - 2)
            lines.extend(wrapped)
    return lines


# ═══════════════════════════════════════════════════════════════════
#  PHASE 1: Preserve-style result display
# ═══════════════════════════════════════════════════════════════════

def render_preserve_style(result: dict) -> str:
    """Render Phase 1 result: original vs same-style optimized tweet."""
    w = _get_width()
    parts = []

    # Header
    parts.append("")
    parts.append(f"  {BOLD}{BRIGHT_CYAN}╔{'═' * (w - 6)}╗{RESET}")
    parts.append(f"  {BOLD}{BRIGHT_CYAN}║  {WHITE}X ALGORITHM TWEET OPTIMIZER{' ' * (w - 33)}║{RESET}")
    parts.append(f"  {BOLD}{BRIGHT_CYAN}╚{'═' * (w - 6)}╝{RESET}")
    parts.append("")

    tweet = result["tweet"]
    analysis = result["analysis"]
    report = result["original_report"]
    optimized = result["optimized"]
    comparison = result["comparison"]

    orig_ws = report["weighted_score"]
    opt_ws = comparison["weighted_score_optimized"] if comparison else 0
    ws_change = comparison["weighted_score_change"] if comparison else 0
    change_str = f"+{ws_change:.1f}" if ws_change >= 0 else f"{ws_change:.1f}"

    # ── Original Tweet ──
    parts.append(_header_line("ORIGINAL TWEET", w))
    parts.append("")

    # Show tweet text cleanly (no box decorations)
    parts.append(f"  {DIM}{ITALIC}")
    for line in _wrap_text(tweet, w):
        parts.append(f"    {line}")
    parts.append(f"  {RESET}")
    parts.append("")

    chars = analysis["char_count"]
    lang_str = analysis["lang"].upper()
    char_color = RED if chars > 280 else GREEN
    parts.append(f"  {GRAY}Characters: {char_color}{chars}/280{RESET}  {GRAY}│  Lang: {CYAN}{lang_str}{RESET}  {GRAY}│  Score: {YELLOW}{orig_ws:.1f}{RESET}")

    # ── Signal Profile (compact) ──
    parts.append("")
    parts.append(_section_title("Signal Profile"))
    parts.append(_divider(w))

    display_cfg = config.get("display", {})
    show_all = display_cfg.get("show_all_signals", False)
    top_n = display_cfg.get("top_signals_count", 8)

    signals = report["signals"]
    if show_all:
        display_actions = ACTIONS
    else:
        scored = []
        for a in ACTIONS:
            if a in NEGATIVE_ACTIONS:
                scored.append((a, 999))
            else:
                scored.append((a, signals.get(a, 0.0)))
        scored.sort(key=lambda x: -x[1])
        display_actions = [a for a, _ in scored[:top_n]]

    for action in display_actions:
        val = signals.get(action, 0.0)
        is_neg = action in NEGATIVE_ACTIONS
        bar = _bar_negative(val) if is_neg else _bar(val)
        risk_label = f"  {RED}risk{RESET}" if is_neg else ""
        name = ACTION_LABELS.get(action, action)
        parts.append(f"    {GRAY}{name:<22}{RESET} {bar} {val:>4.0%}{risk_label}")

    # ── Optimized Tweet ──
    parts.append("")
    parts.append("")
    score_color = GREEN if ws_change > 0 else RED if ws_change < 0 else YELLOW
    parts.append(_header_line(f"OPTIMIZED TWEET  {score_color}{orig_ws:.1f} {ARROW_RIGHT} {opt_ws:.1f} ({change_str}){RESET}", w + 20))
    parts.append("")

    opt_tweet = optimized.get("tweet", "")
    opt_chars = optimized.get("char_count", len(opt_tweet))

    # Show the optimized tweet in a clean, copyable format
    parts.append(f"  {BOLD}{WHITE}")
    for line in _wrap_text(opt_tweet, w):
        parts.append(f"    {line}")
    parts.append(f"  {RESET}")
    parts.append("")

    char_color = RED if opt_chars > 280 else GREEN
    parts.append(f"  {GRAY}Characters: {char_color}{opt_chars}/280{RESET}")

    # ── What Changed ──
    explanation = optimized.get("explanation", "")
    if explanation:
        parts.append("")
        parts.append(f"  {GRAY}{ITALIC}What changed: {explanation}{RESET}")

    # ── Signal Changes (top improvements) ──
    if comparison:
        parts.append("")
        parts.append(_section_title("Signal Changes"))
        parts.append(_divider(w))

        delta = comparison["delta"]
        sorted_actions = sorted(
            ACTIONS,
            key=lambda a: abs(delta[a]["delta_pct"]),
            reverse=True,
        )
        display_delta_actions = sorted_actions[:top_n]

        for action in display_delta_actions:
            d = delta[action]
            is_neg = action in NEGATIVE_ACTIONS
            orig_pct = d["original"]
            opt_pct = d["optimized"]
            dpct = d["delta_pct"]
            arrows = _change_arrows(dpct, is_neg)
            sign = "+" if dpct >= 0 else ""
            name = ACTION_LABELS.get(action, action)
            parts.append(
                f"    {GRAY}{name:<22}{RESET} {orig_pct:>3.0%} {ARROW_RIGHT} {opt_pct:>3.0%}  {sign}{dpct:.1f}%  {arrows}"
            )

    # Media suggestion
    media_sug = optimized.get("media_suggestion", "")
    if media_sug:
        parts.append("")
        parts.append(f"  {MAGENTA}{BULLET} Media tip:{RESET} {DIM}{media_sug}{RESET}")

    # Analysis
    claude_analysis = result.get("claude_analysis", "")
    if claude_analysis:
        parts.append("")
        parts.append(_section_title("Analysis"))
        parts.append(_divider(w))
        for line in _wrap_text(claude_analysis, w - 4):
            parts.append(f"    {DIM}{line}{RESET}")

    parts.append("")
    parts.append(f"  {GRAY}{'─' * (w - 4)}{RESET}")
    parts.append("")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════
#  PHASE 2: Different style variations display
# ═══════════════════════════════════════════════════════════════════

def render_variation_card(
    index: int,
    variation: dict,
    comparison: dict | None,
    verbose: bool = False,
) -> str:
    """Render a single variation as a clean card."""
    w = _get_width()
    parts = []

    tweet = variation.get("tweet", "")
    strategy = variation.get("strategy", "")
    char_count = variation.get("char_count", len(tweet))
    media_sug = variation.get("media_suggestion", "")
    explanation = variation.get("explanation", "")

    opt_ws = 0.0
    ws_change = 0.0
    if comparison:
        opt_ws = comparison["weighted_score_optimized"]
        ws_change = comparison["weighted_score_change"]

    change_str = f"+{ws_change:.1f}" if ws_change >= 0 else f"{ws_change:.1f}"
    change_color = GREEN if ws_change > 0 else RED if ws_change < 0 else GRAY

    # Card header
    parts.append("")
    parts.append(f"  {BOLD}{BRIGHT_MAGENTA}[{index}]{RESET} {BOLD}{WHITE}{strategy}{RESET}  {change_color}{opt_ws:.1f} ({change_str}){RESET}")
    parts.append(_divider(w))
    parts.append("")

    # Tweet text — clean and copyable
    parts.append(f"  {BOLD}{WHITE}")
    for line in _wrap_text(tweet, w):
        parts.append(f"    {line}")
    parts.append(f"  {RESET}")
    parts.append("")

    char_color = RED if char_count > 280 else GREEN
    parts.append(f"  {GRAY}Characters: {char_color}{char_count}/280{RESET}")

    if explanation:
        parts.append(f"  {GRAY}{ITALIC}{explanation}{RESET}")

    # Signal changes (compact - top 5)
    if comparison:
        parts.append("")
        delta = comparison["delta"]
        sorted_actions = sorted(
            ACTIONS,
            key=lambda a: abs(delta[a]["delta_pct"]),
            reverse=True,
        )

        for action in sorted_actions[:5]:
            d = delta[action]
            is_neg = action in NEGATIVE_ACTIONS
            orig_pct = d["original"]
            opt_pct = d["optimized"]
            dpct = d["delta_pct"]
            arrows = _change_arrows(dpct, is_neg)
            sign = "+" if dpct >= 0 else ""
            name = ACTION_LABELS.get(action, action)
            parts.append(
                f"    {GRAY}{name:<22}{RESET} {orig_pct:>3.0%} {ARROW_RIGHT} {opt_pct:>3.0%}  {sign}{dpct:.1f}%  {arrows}"
            )

    if media_sug:
        parts.append(f"    {MAGENTA}{BULLET} Media:{RESET} {DIM}{media_sug[:60]}{'...' if len(media_sug) > 60 else ''}{RESET}")

    parts.append("")
    return "\n".join(parts)


def render_variations(result: dict, verbose: bool = False) -> str:
    """Render Phase 2: all style variations."""
    w = _get_width()
    parts = []

    parts.append("")
    parts.append(f"  {BOLD}{BRIGHT_CYAN}╔{'═' * (w - 6)}╗{RESET}")
    parts.append(f"  {BOLD}{BRIGHT_CYAN}║  {WHITE}STYLE VARIATIONS{' ' * (w - 22)}║{RESET}")
    parts.append(f"  {BOLD}{BRIGHT_CYAN}╚{'═' * (w - 6)}╝{RESET}")

    for i, (var, comp) in enumerate(
        zip(result["variations"], result["comparisons"]), 1
    ):
        parts.append(render_variation_card(i, var, comp, verbose=verbose))

    # Summary comparison table
    parts.append(_header_line("SUMMARY", w))
    parts.append("")

    orig_ws = result["original_report"]["weighted_score"]
    parts.append(f"    {GRAY}{'Tweet':<8} {'Strategy':<28} {'Score':>8}  {'Change':>8}{RESET}")
    parts.append(f"    {GRAY}{'─' * 56}{RESET}")
    parts.append(f"    {DIM}{'Original':<8} {'-':<28} {orig_ws:>7.1f}  {'-':>8}{RESET}")

    for i, (var, comp) in enumerate(zip(result["variations"], result["comparisons"]), 1):
        strategy = var.get("strategy", "")[:26]
        if comp:
            opt_ws = comp["weighted_score_optimized"]
            ch = comp["weighted_score_change"]
            sign = "+" if ch >= 0 else ""
            ch_color = GREEN if ch > 0 else RED if ch < 0 else GRAY
            parts.append(
                f"    {BRIGHT_MAGENTA}#{i:<7}{RESET} {WHITE}{strategy:<28}{RESET} {opt_ws:>7.1f}  {ch_color}{sign}{ch:.1f}{RESET}"
            )
        else:
            parts.append(f"    {BRIGHT_MAGENTA}#{i:<7}{RESET} {strategy:<28}   {'N/A':>7}  {'N/A':>8}")

    # Analysis
    if result.get("claude_analysis"):
        parts.append("")
        parts.append(f"  {GRAY}{ITALIC}Analysis: {result['claude_analysis']}{RESET}")

    parts.append("")
    parts.append(f"  {GRAY}{'─' * (w - 4)}{RESET}")
    parts.append("")

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════
#  Legacy: Full render (backwards compatible for --json mode)
# ═══════════════════════════════════════════════════════════════════

def render_full(result: dict, verbose: bool = False) -> str:
    """Render the complete optimization result (legacy full output)."""
    return render_variations(result, verbose=verbose)


def render_json(result: dict) -> str:
    """Render result as JSON string."""
    import json
    output = {
        "original": {
            "tweet": result["tweet"],
            "char_count": result["analysis"]["char_count"],
            "lang": result["lang"],
            "scores": result["original_report"]["signals"],
            "weighted_score": result["original_report"]["weighted_score"],
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
            v["weighted_score"] = comp["weighted_score_optimized"]
            v["weighted_score_change"] = comp["weighted_score_change"]
        output["variations"].append(v)

    return json.dumps(output, indent=2, ensure_ascii=False)


def render_profile_summary(profile: dict) -> str:
    """Render a user profile summary for terminal display."""
    w = _get_width()
    parts = []

    username = profile.get("username", "unknown")
    followers = profile.get("followers", 0)
    following = profile.get("following", 0)
    tweet_count = profile.get("tweet_count", 0)
    verified = profile.get("verified", False)
    engagement = profile.get("engagement", {})
    style = profile.get("style", {})
    topics = profile.get("topics", [])

    # Format followers
    if followers >= 1_000_000:
        f_str = f"{followers / 1_000_000:.1f}M"
    elif followers >= 1_000:
        f_str = f"{followers / 1_000:.1f}K"
    else:
        f_str = str(followers)

    # Format tweet count
    if tweet_count >= 1_000:
        tc_str = f"{tweet_count:,}"
    else:
        tc_str = str(tweet_count)

    blue_str = f"{CYAN}Yes{RESET}" if verified else f"{GRAY}No{RESET}"

    parts.append("")
    parts.append(_header_line(f"PROFILE: @{username}", w))
    parts.append(
        f"  Followers: {BOLD}{WHITE}{f_str}{RESET}  "
        f"{GRAY}|{RESET}  Tweets: {WHITE}{tc_str}{RESET}  "
        f"{GRAY}|{RESET}  Blue: {blue_str}"
    )

    # Engagement metrics
    avg_likes = engagement.get("avg_likes", 0)
    avg_rts = engagement.get("avg_retweets", 0)
    avg_replies = engagement.get("avg_replies", 0)
    avg_quotes = engagement.get("avg_quotes", 0)
    er_likes = engagement.get("engagement_rate_likes", 0)
    er_rts = engagement.get("engagement_rate_retweets", 0)

    parts.append("")
    parts.append(_section_title("Engagement (per tweet)"))
    parts.append(_divider(w))
    parts.append(
        f"    {GRAY}Likes:{RESET} {GREEN}{avg_likes:.1f}{RESET}  "
        f"{GRAY}RTs:{RESET} {CYAN}{avg_rts:.1f}{RESET}  "
        f"{GRAY}Replies:{RESET} {YELLOW}{avg_replies:.1f}{RESET}  "
        f"{GRAY}Quotes:{RESET} {MAGENTA}{avg_quotes:.1f}{RESET}"
    )
    parts.append(
        f"    {GRAY}Like rate:{RESET} {er_likes:.2f}%  "
        f"{GRAY}RT rate:{RESET} {er_rts:.2f}%"
    )

    # Style info
    tone = style.get("typical_tone", "neutral")
    avg_len = style.get("avg_tweet_length", 0)
    avg_emoji = style.get("emoji_frequency", 0)

    parts.append("")
    parts.append(
        f"  {GRAY}Style:{RESET} {WHITE}{tone}{RESET}  "
        f"{GRAY}|{RESET}  {GRAY}Avg length:{RESET} {WHITE}{avg_len:.0f}{RESET} chars  "
        f"{GRAY}|{RESET}  {GRAY}Emojis:{RESET} {WHITE}{avg_emoji:.1f}{RESET}/tweet"
    )

    # Topics
    if topics:
        topic_str = ", ".join(topics[:6])
        parts.append(f"  {GRAY}Topics:{RESET} {CYAN}{topic_str}{RESET}")

    parts.append(f"  {GRAY}{'─' * (w - 4)}{RESET}")
    parts.append("")

    return "\n".join(parts)


def render_discovery_result(result: dict) -> str:
    """Render a discovery-generated tweet result.

    Unlike render_preserve_style, there is no 'original' tweet to compare
    against — this shows the generated tweet with its topic/angle context
    and signal scores.
    """
    w = _get_width()
    parts = []

    trending = result.get("trending_topic", {})
    angle = result.get("angle", "")
    optimized = result.get("optimized", {})
    report = result.get("generated_report", {})

    topic_name = trending.get("name", "Unknown topic")

    # Header
    parts.append("")
    parts.append(f"  {BOLD}{BRIGHT_CYAN}{'=' * (w - 4)}{RESET}")
    parts.append(f"  {BOLD}{WHITE}  TRENDING TOPIC TWEET{RESET}")
    parts.append(f"  {BOLD}{BRIGHT_CYAN}{'=' * (w - 4)}{RESET}")
    parts.append("")

    # Topic context
    parts.append(_header_line(f"TOPIC: {topic_name}", w))
    parts.append("")

    context = trending.get("context", "")
    if context:
        parts.append(f"    {GRAY}Context:{RESET} {DIM}{context}{RESET}")

    popular = trending.get("popular_take", "")
    if popular:
        parts.append(f"    {GRAY}Popular take:{RESET} {DIM}{popular}{RESET}")

    contrarian = trending.get("contrarian_angle", "")
    if contrarian:
        parts.append(f"    {GRAY}Contrarian:{RESET} {DIM}{contrarian}{RESET}")

    angle_display = angle.replace("_", " ").title() if angle else ""
    if angle_display:
        parts.append(f"    {GRAY}Your angle:{RESET} {CYAN}{angle_display}{RESET}")

    # Generated tweet
    parts.append("")
    opt_tweet = optimized.get("tweet", "")
    opt_chars = optimized.get("char_count", len(opt_tweet))

    ws = report.get("weighted_score", 0) if report else 0
    parts.append(_header_line(f"GENERATED TWEET  {YELLOW}Score: {ws:.1f}{RESET}", w + 15))
    parts.append("")

    parts.append(f"  {BOLD}{WHITE}")
    for line in _wrap_text(opt_tweet, w):
        parts.append(f"    {line}")
    parts.append(f"  {RESET}")
    parts.append("")

    char_color = RED if opt_chars > 280 else GREEN
    parts.append(f"  {GRAY}Characters: {char_color}{opt_chars}/280{RESET}")

    # Strategy and explanation
    strategy = optimized.get("strategy", "")
    if strategy:
        parts.append(f"  {GRAY}Strategy: {WHITE}{strategy}{RESET}")

    explanation = optimized.get("explanation", "")
    if explanation:
        parts.append(f"  {GRAY}{ITALIC}{explanation}{RESET}")

    # Signal scores (top signals)
    if "scores" in optimized:
        parts.append("")
        parts.append(_section_title("Signal Scores"))
        parts.append(_divider(w))

        display_cfg = config.get("display", {})
        top_n = display_cfg.get("top_signals_count", 8)

        scores = optimized["scores"]
        scored = []
        for a in ACTIONS:
            if a in NEGATIVE_ACTIONS:
                scored.append((a, 999))
            else:
                scored.append((a, scores.get(a, 0.0)))
        scored.sort(key=lambda x: -x[1])
        display_actions = [a for a, _ in scored[:top_n]]

        for action in display_actions:
            val = scores.get(action, 0.0)
            is_neg = action in NEGATIVE_ACTIONS
            bar = _bar_negative(val) if is_neg else _bar(val)
            risk_label = f"  {RED}risk{RESET}" if is_neg else ""
            name = ACTION_LABELS.get(action, action)
            parts.append(f"    {GRAY}{name:<22}{RESET} {bar} {val:>4.0%}{risk_label}")

    # Media suggestion
    media_sug = optimized.get("media_suggestion", "")
    if media_sug:
        parts.append("")
        parts.append(f"  {MAGENTA}{BULLET} Media tip:{RESET} {DIM}{media_sug}{RESET}")

    # Analysis
    claude_analysis = result.get("claude_analysis", "")
    if claude_analysis:
        parts.append("")
        parts.append(_section_title("Analysis"))
        parts.append(_divider(w))
        for line in _wrap_text(claude_analysis, w - 4):
            parts.append(f"    {DIM}{line}{RESET}")

    parts.append("")
    parts.append(f"  {GRAY}{'=' * (w - 4)}{RESET}")
    parts.append("")

    return "\n".join(parts)

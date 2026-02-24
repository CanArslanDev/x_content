#!/usr/bin/env python3
"""X Algorithm Tweet Optimizer - CLI Entry Point.

Interactive modes:
  python optimize.py                     -> Interactive welcome menu
  python optimize.py "Tweet text here"   -> Direct optimization
  python optimize.py --username canarslan -> Profile-aware optimization

Usage:
  python optimize.py
  python optimize.py "Tweet text here"
  python optimize.py "Tweet text" --topic "AI" --style provocative
  python optimize.py --file draft.txt --lang tr --thread
  python optimize.py "Tweet text" --no-interactive --variations 5
"""

import argparse
import platform
import shutil
import subprocess
import sys

from x_content.optimizer import (
    optimize, optimize_preserve_style, refine_tweet,
    generate_discovery_tweet, OptimizationError,
)
from x_content.display import (
    render_preserve_style, render_variations, render_json,
    render_profile_summary, render_discovery_result,
)


# ── ANSI helpers ─────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
WHITE = "\033[97m"
GRAY = "\033[90m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_GREEN = "\033[92m"


def _term_width() -> int:
    try:
        cols = shutil.get_terminal_size().columns
        return min(max(cols, 60), 120)
    except Exception:
        return 80


# ── Parser ───────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Optimize tweets for maximum X algorithm reach",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python optimize.py                                  (interactive)\n"
            '  python optimize.py "AI will replace 80%% of jobs"\n'
            '  python optimize.py "Test tweet" --topic "AI" --variations 5\n'
            '  python optimize.py --file draft.txt --lang tr --thread\n'
        ),
    )

    parser.add_argument(
        "tweet",
        nargs="?",
        help="Tweet text to optimize (omit for interactive mode)",
    )
    parser.add_argument(
        "--topic",
        help="Topic/niche context (e.g., 'AI', 'startups')",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "tr", "auto"],
        default="auto",
        help="Language: en, tr, or auto (default: auto)",
    )
    parser.add_argument(
        "--variations",
        type=int,
        default=3,
        help="Number of style variations for Phase 2 (default: 3)",
    )
    parser.add_argument(
        "--style",
        choices=["professional", "casual", "provocative", "educational"],
        default="professional",
        help="Tone style for Phase 2 variations (default: professional)",
    )
    parser.add_argument(
        "--media",
        action="store_true",
        help="Tweet will include media (photo/video)",
    )
    parser.add_argument(
        "--thread",
        action="store_true",
        help="Optimize for thread format",
    )
    parser.add_argument(
        "--file",
        help="Read tweet from file instead of positional arg",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output as JSON (non-interactive)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed algorithm analysis",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        dest="no_interactive",
        help="Skip interactive prompts, show all variations directly",
    )
    parser.add_argument(
        "--username",
        help="X username to fetch profile for personalized optimization",
    )
    parser.add_argument(
        "--refresh-profile",
        action="store_true",
        dest="refresh_profile",
        help="Force refresh profile cache",
    )

    return parser


# ── Clipboard ────────────────────────────────────────────────────

def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    system = platform.system()
    try:
        if system == "Darwin":
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"))
            return proc.returncode == 0
        elif system == "Linux":
            for cmd in [["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
                try:
                    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                    proc.communicate(text.encode("utf-8"))
                    if proc.returncode == 0:
                        return True
                except FileNotFoundError:
                    continue
            return False
        elif system == "Windows":
            proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-16le"))
            return proc.returncode == 0
    except Exception:
        return False
    return False


# ── Input helpers ────────────────────────────────────────────────

def prompt_choice(question: str, options: list[str]) -> str:
    """Show an interactive menu and return the chosen option key."""
    print(f"\n  {BOLD}{WHITE}{question}{RESET}")
    for i, opt in enumerate(options, 1):
        print(f"    {BRIGHT_CYAN}[{i}]{RESET} {opt}")
    print()

    while True:
        try:
            raw = input(f"  {GRAY}Select (1-{len(options)}): {RESET}").strip()
            if not raw:
                return "1"
            idx = int(raw)
            if 1 <= idx <= len(options):
                return str(idx)
        except (ValueError, EOFError):
            pass
        print(f"  {DIM}Please enter a number between 1 and {len(options)}{RESET}")


def _ask_input(prompt_text: str, required: bool = False) -> str:
    """Ask user for single-line input."""
    try:
        while True:
            value = input(f"  {GRAY}{prompt_text}{RESET}").strip()
            if value or not required:
                return value
            print(f"  {DIM}This field is required.{RESET}")
    except (EOFError, KeyboardInterrupt):
        print()
        if required:
            sys.exit(0)
        return ""


def _ask_multiline_input(prompt_text: str) -> str:
    """Ask user for multi-line input. Empty line finishes input."""
    print(f"  {GRAY}{prompt_text}{RESET}")
    print(f"  {DIM}(Paste text, then press Enter on an empty line to finish){RESET}\n")

    lines = []
    empty_count = 0
    try:
        while True:
            line = input(f"  {DIM}>{RESET} ")
            if line.strip() == "":
                empty_count += 1
                if empty_count >= 1 and lines:
                    break
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
    except (EOFError, KeyboardInterrupt):
        print()

    return "\n".join(lines).strip()


# ── Profile fetching ─────────────────────────────────────────────

def _fetch_profile(username: str, force_refresh: bool = False) -> dict | None:
    """Fetch user profile automatically, or fall back to Grok/manual entry."""
    from x_content.profile import fetch_profile, _load_cached_profile

    handle = username.lstrip("@").strip()

    # Check cache first
    if not force_refresh:
        cached = _load_cached_profile(handle)
        if cached is not None:
            print(f"\n  {BOLD}{BRIGHT_CYAN}Found cached profile @{handle}{RESET}")

            # Show age
            fetched_at = cached.get("fetched_at", "")
            if fetched_at:
                try:
                    from datetime import datetime, timezone
                    dt = datetime.fromisoformat(fetched_at)
                    hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                    if hours < 1:
                        age = f"{int(hours * 60)} min ago"
                    elif hours < 24:
                        age = f"{int(hours)}h ago"
                    else:
                        age = f"{int(hours / 24)}d ago"
                    print(f"  {DIM}(cached {age}){RESET}")
                except (ValueError, TypeError):
                    pass

            print()
            print(render_profile_summary(cached))

            choice = prompt_choice(
                "Use this profile or update?",
                [
                    f"{WHITE}Use cached profile{RESET}",
                    f"{CYAN}Update via Grok{RESET}",
                    f"{WHITE}Update manually{RESET}",
                ],
            )

            if choice == "1":
                return cached
            elif choice == "2":
                return _grok_profile_entry(handle)
            else:
                return _manual_profile_entry(handle)

    # Try automatic fetch
    try:
        print(f"\n  {BOLD}{BRIGHT_CYAN}Fetching profile @{handle}...{RESET}\n")
        profile = fetch_profile(handle, force_refresh=force_refresh)
        if profile:
            print(render_profile_summary(profile))
            return profile
    except Exception as e:
        err_str = str(e)
        first_line = err_str.split("\n")[0]
        print(f"  {YELLOW}{first_line}{RESET}")

    # Offer alternatives
    print()
    choice = prompt_choice(
        "Automatic fetch unavailable. How would you like to proceed?",
        [
            f"{WHITE}Ask Grok about this user (recommended){RESET}",
            f"{WHITE}Enter profile info manually{RESET}",
            f"{DIM}Continue without profile data{RESET}",
        ],
    )

    if choice == "1":
        return _grok_profile_entry(handle)
    elif choice == "2":
        return _manual_profile_entry(handle)
    return None



def _grok_profile_entry(username: str) -> dict | None:
    """Build profile by asking user to query Grok about the account."""
    from x_content.discovery import build_grok_profile_prompt, parse_grok_profile_response
    from x_content.profile import build_manual_profile

    handle = username.lstrip("@").strip()
    w = _term_width()

    # Detect preferred language
    lang = "en"
    print()
    lang_choice = prompt_choice(
        "Which language should the Grok prompt use?",
        [
            f"{WHITE}English{RESET}",
            f"{WHITE}Turkish{RESET}",
        ],
    )
    if lang_choice == "2":
        lang = "tr"

    grok_prompt = build_grok_profile_prompt(handle, lang)

    # Show prompt in a bordered box
    prompt_lines = grok_prompt.split("\n")
    max_line_len = max(len(l) for l in prompt_lines)
    box_w = min(max_line_len + 4, w - 6)

    print()
    print(f"  {BOLD}{WHITE}Copy this prompt and paste it into Grok (grok.com):{RESET}")
    print()
    print(f"    {CYAN}+{'─' * box_w}+{RESET}")
    for line in prompt_lines:
        padded = line + " " * max(box_w - 2 - len(line), 0)
        print(f"    {CYAN}|{RESET} {padded} {CYAN}|{RESET}")
    print(f"    {CYAN}+{'─' * box_w}+{RESET}")
    print()

    # Copy to clipboard
    if copy_to_clipboard(grok_prompt):
        print(f"  {GREEN}Copied to clipboard.{RESET}")
    print()

    print(f"  {BOLD}{WHITE}Paste Grok's response below{RESET}")
    grok_text = _ask_multiline_input("Grok's response:")

    if not grok_text:
        print(f"\n  {YELLOW}No response provided.{RESET}")
        fallback = prompt_choice(
            "How would you like to proceed?",
            [
                f"{WHITE}Enter profile info manually{RESET}",
                f"{DIM}Continue without profile data{RESET}",
            ],
        )
        if fallback == "1":
            return _manual_profile_entry(username)
        return None

    # Parse Grok's response
    parsed = parse_grok_profile_response(grok_text, handle)

    if not parsed:
        print(f"\n  {YELLOW}Could not parse Grok's response.{RESET}")
        fallback = prompt_choice(
            "How would you like to proceed?",
            [
                f"{WHITE}Enter profile info manually{RESET}",
                f"{DIM}Continue without profile data{RESET}",
            ],
        )
        if fallback == "1":
            return _manual_profile_entry(username)
        return None

    # Build profile from parsed data
    profile = build_manual_profile(
        username=parsed["username"],
        followers=parsed["followers"],
        avg_likes=parsed["avg_likes"],
        avg_retweets=parsed["avg_retweets"],
        avg_replies=parsed["avg_replies"],
        topics=parsed["topics"],
        sample_tweets=parsed["sample_tweets"],
    )

    # Enrich with extra fields from Grok that build_manual_profile doesn't set
    if parsed.get("following"):
        profile["following"] = parsed["following"]
    if parsed.get("tweet_count"):
        profile["tweet_count"] = parsed["tweet_count"]
    if parsed.get("verified"):
        profile["verified"] = parsed["verified"]
    if parsed.get("bio"):
        profile["description"] = parsed["bio"]
    if parsed.get("lang"):
        profile["lang"] = parsed["lang"]
    if parsed.get("tone"):
        profile["style"]["typical_tone"] = parsed["tone"]

    # Re-save with enriched data
    from x_content.profile import _save_cached_profile
    _save_cached_profile(handle, profile)

    print()
    print(render_profile_summary(profile))
    return profile

def _manual_profile_entry(username: str) -> dict | None:
    """Interactively collect profile data from the user."""
    from x_content.profile import build_manual_profile

    username = username.lstrip("@").strip()
    w = _term_width()

    print()
    print(f"  {BOLD}{WHITE}Manual Profile Entry{RESET}")
    print(f"  {GRAY}{'─' * (w - 4)}{RESET}")
    print(f"  {DIM}Check your X profile page for these numbers.{RESET}")
    print(f"  {DIM}Approximate values are fine.{RESET}")
    print()

    # Followers
    followers_str = _ask_input("Follower count: ", required=True)
    try:
        followers = int(followers_str.replace(",", "").replace(".", "").replace("K", "000").replace("k", "000"))
    except ValueError:
        followers = 0

    # Average engagement
    print()
    print(f"  {DIM}Average engagement per tweet (approximate):{RESET}")
    avg_likes = _parse_float(_ask_input("  Avg likes per tweet: "), 10)
    avg_rts = _parse_float(_ask_input("  Avg retweets per tweet: "), 2)
    avg_replies = _parse_float(_ask_input("  Avg replies per tweet: "), 1)

    # Topics
    print()
    topics_str = _ask_input("Your main topics (comma separated, e.g. AI, startup, tech): ", required=True)
    topics = [t.strip() for t in topics_str.split(",") if t.strip()]

    # Sample tweets
    print()
    print(f"  {BOLD}{WHITE}Sample tweets (optional but recommended){RESET}")
    print(f"  {DIM}Paste 2-3 of your best tweets for style analysis.{RESET}")
    print(f"  {DIM}Press Enter on an empty line between tweets. Enter twice to finish.{RESET}")
    print()

    sample_tweets = []
    consecutive_empty = 0
    current_tweet_lines = []

    try:
        while True:
            line = input(f"  {DIM}>{RESET} ")
            if line.strip() == "":
                consecutive_empty += 1
                if current_tweet_lines:
                    sample_tweets.append("\n".join(current_tweet_lines))
                    current_tweet_lines = []
                    consecutive_empty = 0
                    if len(sample_tweets) >= 5:
                        break
                    print(f"  {DIM}  (Tweet #{len(sample_tweets)} saved. Paste next or press Enter to finish){RESET}")
                elif consecutive_empty >= 1:
                    break
            else:
                consecutive_empty = 0
                current_tweet_lines.append(line)
    except (EOFError, KeyboardInterrupt):
        if current_tweet_lines:
            sample_tweets.append("\n".join(current_tweet_lines))
        print()

    profile = build_manual_profile(
        username=username,
        followers=followers,
        avg_likes=avg_likes,
        avg_retweets=avg_rts,
        avg_replies=avg_replies,
        topics=topics,
        sample_tweets=sample_tweets if sample_tweets else None,
    )

    print()
    print(render_profile_summary(profile))
    return profile


def _parse_float(value: str, default: float = 0.0) -> float:
    """Parse a float from user input, returning default on failure."""
    try:
        return float(value.replace(",", ".").strip())
    except (ValueError, AttributeError):
        return default


# ── Welcome banner ───────────────────────────────────────────────

def _show_welcome():
    """Display the welcome banner with recent session info."""
    from x_content.cache import load_session

    w = _term_width()
    inner = w - 6

    print()
    print(f"  {BOLD}{BRIGHT_CYAN}+{'=' * inner}+{RESET}")
    print(f"  {BOLD}{BRIGHT_CYAN}|{RESET}  {BOLD}{WHITE}X ALGORITHM TWEET OPTIMIZER{RESET}{' ' * (inner - 30)}{BOLD}{BRIGHT_CYAN}|{RESET}")
    print(f"  {BOLD}{BRIGHT_CYAN}+{'=' * inner}+{RESET}")

    # Show recent session info
    session = load_session()
    last_user = session.get("last_username")
    if last_user:
        updated = session.get("updated_at", "")
        time_str = ""
        if updated:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(updated)
                now = datetime.now(timezone.utc)
                delta = now - dt
                hours = delta.total_seconds() / 3600
                if hours < 1:
                    time_str = f" ({int(delta.total_seconds() / 60)} min ago)"
                elif hours < 24:
                    time_str = f" ({int(hours)}h ago)"
                else:
                    days = int(hours / 24)
                    time_str = f" ({days}d ago)"
            except (ValueError, TypeError):
                pass
        print(f"  {DIM}Last session: @{last_user}{time_str}{RESET}")

    print()


# ── Welcome flow (argless mode) ─────────────────────────────────

def _welcome_flow(args):
    """Interactive welcome when no arguments provided."""
    from x_content.cache import load_session, save_session

    _show_welcome()

    session = load_session()
    last_user = session.get("last_username")

    # Ask for username (optional), suggest last used
    print(f"  {BOLD}{WHITE}Setup{RESET}")
    print(f"  {GRAY}{'─' * (_term_width() - 4)}{RESET}")

    if last_user:
        username = _ask_input(
            f"X username (Enter for @{last_user}, or type new): ",
        )
        if not username:
            username = last_user
    else:
        username = _ask_input("X username (optional, press Enter to skip): ")

    user_profile = None
    if username:
        username = username.lstrip("@").strip()
        args.username = username
        args.refresh_profile = getattr(args, "refresh_profile", False)
        user_profile = _fetch_profile(username, force_refresh=args.refresh_profile)
        save_session(username=username)
    args.user_profile = user_profile

    # Main menu
    choice = prompt_choice(
        "What would you like to do?",
        [
            f"{WHITE}Optimize a tweet{RESET}",
            f"{CYAN}Discover trending topics & create content{RESET}",
            f"{DIM}Exit{RESET}",
        ],
    )

    if choice == "1":
        save_session(action="optimize")
        _optimize_tweet_interactive(args)
    elif choice == "2":
        save_session(action="discover")
        _discovery_flow(args)
    else:
        print(f"\n  {DIM}Done.{RESET}\n")


def _optimize_tweet_interactive(args):
    """Ask for tweet text and optional params, then optimize."""
    print(f"\n  {BOLD}{WHITE}Enter your tweet{RESET}")
    print(f"  {GRAY}{'─' * (_term_width() - 4)}{RESET}")

    tweet = _ask_input("Tweet text: ", required=True)
    args.tweet = tweet

    # Optional fields
    if not args.topic:
        topic = _ask_input("Topic/niche (optional): ")
        if topic:
            args.topic = topic

    # Set defaults for optional args if not set
    if not hasattr(args, "media"):
        args.media = False
    if not hasattr(args, "thread"):
        args.thread = False
    if not hasattr(args, "lang"):
        args.lang = "auto"
    if not hasattr(args, "variations"):
        args.variations = 3
    if not hasattr(args, "style"):
        args.style = "professional"
    if not hasattr(args, "verbose"):
        args.verbose = False

    interactive_flow(args)


# ── Discovery flow ───────────────────────────────────────────────


def _manual_trending_entry(lang: str = "en") -> list[dict]:
    """Manually enter trending topics when Grok is not available."""
    w = _term_width()

    print()
    print(f"  {BOLD}{WHITE}Manual Trending Topics Entry{RESET}")
    print(f"  {GRAY}{'─' * (w - 4)}{RESET}")

    if lang == "tr":
        print(f"  {DIM}Gundemdeki konulari tek tek girin.{RESET}")
        print(f"  {DIM}Her konu icin isim ve kisa aciklama girin.{RESET}")
        print(f"  {DIM}Bos birakip Enter'a basarak bitirin.{RESET}")
    else:
        print(f"  {DIM}Enter trending topics one by one.{RESET}")
        print(f"  {DIM}For each, provide a name and brief context.{RESET}")
        print(f"  {DIM}Press Enter on an empty name to finish.{RESET}")
    print()

    topics = []
    for i in range(1, 11):  # max 10 topics
        name = _ask_input(f"  Topic {i} name (Enter to finish): ")
        if not name:
            break

        context = _ask_input(f"  Context (optional): ")
        popular = _ask_input(f"  Popular opinion (optional): ")
        contrarian = _ask_input(f"  Contrarian angle (optional): ")
        print()

        topics.append({
            "name": name.strip(),
            "context": context.strip() if context else "",
            "popular_take": popular.strip() if popular else "",
            "contrarian_angle": contrarian.strip() if contrarian else "",
        })

    if topics:
        print(f"  {GREEN}{len(topics)} topic(s) entered.{RESET}")

    return topics

def _discovery_flow(args):
    """Three-stage discovery: topic selection, Grok research, tweet creation."""
    from x_content.cache import save_trending_topics, load_trending_topics

    user_profile = getattr(args, "user_profile", None)

    # Require a profile for discovery
    if not user_profile:
        print(f"\n  {YELLOW}Discovery mode requires a user profile.{RESET}")
        username = _ask_input("X username: ", required=True).lstrip("@").strip()
        args.username = username
        args.refresh_profile = getattr(args, "refresh_profile", False)
        user_profile = _fetch_profile(username, force_refresh=args.refresh_profile)
        args.user_profile = user_profile
        if not user_profile:
            print(f"  {RED}Cannot proceed without profile data.{RESET}\n")
            return

    lang = user_profile.get("lang", "en")

    from x_content.discovery import (
        rank_topics_by_engagement, build_grok_prompt,
        parse_grok_response, get_angle_instruction, get_angle_label,
        ANGLES,
    )

    # ── Stage 1: Topic Selection ─────────────────────────────────
    w = _term_width()
    print()
    print(f"  {BOLD}{BRIGHT_CYAN}{'─' * 2} STAGE 1: TOPIC SELECTION {'─' * max(w - 30, 0)}{RESET}")
    print()

    rankings = rank_topics_by_engagement(user_profile)

    if rankings:
        # Show ranked topics
        print(f"  {BOLD}{WHITE}Your strongest content areas (ranked by engagement):{RESET}")
        print()
        print(f"    {DIM}{'#':<4} {'Topic':<28} {'Avg Score':<14} {'Tweets'}{RESET}")
        print(f"    {DIM}{'─' * 56}{RESET}")

        topic_options = []
        for i, r in enumerate(rankings[:8], 1):
            score_str = f"{r['avg_engagement']:.0f}" if r["avg_engagement"] > 0 else "---"
            count_str = str(r["tweet_count"]) if r["tweet_count"] > 0 else "---"
            label = f"{r['topic']:<28} {score_str:<14} {count_str}"
            topic_options.append(label)

        topic_options.append(f"{DIM}Enter a custom topic{RESET}")

        for i, opt in enumerate(topic_options, 1):
            print(f"    {BRIGHT_CYAN}[{i}]{RESET} {opt}")
        print()

        while True:
            try:
                raw = input(f"  {GRAY}Select a topic (1-{len(topic_options)}): {RESET}").strip()
                if not raw:
                    idx = 1
                else:
                    idx = int(raw)
                if 1 <= idx <= len(topic_options):
                    break
            except (ValueError, EOFError):
                pass
            print(f"  {DIM}Please enter a number between 1 and {len(topic_options)}{RESET}")

        if idx == len(topic_options):
            selected_topic = _ask_input("Enter your topic: ", required=True)
        else:
            selected_topic = rankings[idx - 1]["topic"]
    else:
        print(f"  {DIM}No topic data from profile. Enter a topic manually.{RESET}")
        selected_topic = _ask_input("Topic: ", required=True)

    print(f"\n  {GREEN}Selected topic: {BOLD}{selected_topic}{RESET}")

    # ── Stage 2: Grok Research ───────────────────────────────────
    print()
    print(f"  {BOLD}{BRIGHT_CYAN}{'─' * 2} STAGE 2: GROK RESEARCH {'─' * max(w - 28, 0)}{RESET}")
    print()

    # Check trending topic cache first
    cached_trending = load_trending_topics(selected_topic, ttl_hours=2.0)
    use_cache = False
    use_manual_trending = False

    if cached_trending and cached_trending.get("parsed_topics"):
        cached_topics = cached_trending["parsed_topics"]
        cached_at = cached_trending.get("cached_at", "")

        # Calculate age
        age_str = ""
        if cached_at:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(cached_at)
                mins = int((datetime.now(timezone.utc) - dt).total_seconds() / 60)
                if mins < 60:
                    age_str = f"{mins} min ago"
                else:
                    age_str = f"{mins // 60}h ago"
            except (ValueError, TypeError):
                pass

        print(f"  {GREEN}Found cached trending topics for \"{selected_topic}\"{RESET}")
        if age_str:
            print(f"  {DIM}(cached {age_str}, {len(cached_topics)} topics){RESET}")

        # Preview cached topics
        for i, ct in enumerate(cached_topics[:5], 1):
            name = ct.get("name", "?")
            print(f"    {DIM}{i}. {name}{RESET}")
        print()

        cache_choice = prompt_choice(
            "Use cached results or enter new data?",
            [
                f"{WHITE}Use cached results{RESET}",
                f"{CYAN}Fetch fresh from Grok{RESET}",
                f"{WHITE}Enter trending topics manually{RESET}",
            ],
        )
        if cache_choice == "1":
            use_cache = True
        elif cache_choice == "3":
            use_cache = False
            use_manual_trending = True

    # Determine method: cache / grok / manual / skip
    trending_topics = []

    if use_cache and cached_trending:
        # User chose to use cache
        trending_topics = [dict(t) for t in cached_trending["parsed_topics"]]

    elif use_manual_trending:
        # User chose manual from the cache prompt
        trending_topics = _manual_trending_entry(lang)
        if trending_topics:
            save_trending_topics(selected_topic, "(manual entry)",
                                [dict(t) for t in trending_topics])

    else:
        # No usable cache — ask how to proceed
        if not cached_trending:
            method = prompt_choice(
                "How would you like to get trending topics?",
                [
                    f"{CYAN}Research via Grok (recommended){RESET}",
                    f"{WHITE}Enter trending topics manually{RESET}",
                    f"{DIM}Skip -- write about the topic directly{RESET}",
                ],
            )
        else:
            # Cache was found but user chose "Fetch fresh from Grok"
            method = "1"

        if method == "2":
            # Manual entry
            trending_topics = _manual_trending_entry(lang)
            if trending_topics:
                save_trending_topics(selected_topic, "(manual entry)",
                                    [dict(t) for t in trending_topics])

        elif method == "1":
            # Grok research flow
            grok_prompt = build_grok_prompt(selected_topic, lang)

            prompt_lines = grok_prompt.split("\n")
            max_line_len = max(len(l) for l in prompt_lines)
            box_w = min(max_line_len + 4, w - 6)

            print(f"  {BOLD}{WHITE}Copy this prompt and paste it into Grok (grok.com):{RESET}")
            print()
            print(f"    {CYAN}+{'─' * box_w}+{RESET}")
            for line in prompt_lines:
                padded = line + " " * max(box_w - 2 - len(line), 0)
                print(f"    {CYAN}|{RESET} {padded} {CYAN}|{RESET}")
            print(f"    {CYAN}+{'─' * box_w}+{RESET}")
            print()

            if copy_to_clipboard(grok_prompt):
                print(f"  {GREEN}Copied to clipboard.{RESET}")
            print()

            print(f"  {BOLD}{WHITE}Paste Grok's response below{RESET}")
            print(f"  {DIM}(Or press Enter to skip and write about the topic directly){RESET}")
            print()

            grok_text = _ask_multiline_input("Grok's response:")

            if grok_text:
                trending_topics = parse_grok_response(grok_text)
                if trending_topics:
                    save_trending_topics(selected_topic, grok_text,
                                        [dict(t) for t in trending_topics])

        # else: method == "3" — skip, trending_topics stays empty

    # ── Stage 3: Topic + Angle Selection ─────────────────────────
    trending_topic = None

    if trending_topics:
        print()
        print(f"  {BOLD}{BRIGHT_CYAN}{'─' * 2} STAGE 3: SELECT TOPIC & ANGLE {'─' * max(w - 35, 0)}{RESET}")
        print()
        print(f"  {BOLD}{WHITE}Trending topics found:{RESET}")
        print()

        for i, tt in enumerate(trending_topics, 1):
            print(f"    {BRIGHT_CYAN}[{i}]{RESET} {BOLD}{WHITE}{tt['name']}{RESET}")
            if tt.get("context"):
                print(f"        {GRAY}Context:{RESET} {DIM}{tt['context']}{RESET}")
            if tt.get("popular_take"):
                print(f"        {GRAY}Popular:{RESET} {DIM}{tt['popular_take']}{RESET}")
            if tt.get("contrarian_angle"):
                print(f"        {GRAY}Contrarian:{RESET} {DIM}{tt['contrarian_angle']}{RESET}")
            print()

        while True:
            try:
                raw = input(f"  {GRAY}Select a topic (1-{len(trending_topics)}): {RESET}").strip()
                if not raw:
                    tidx = 1
                else:
                    tidx = int(raw)
                if 1 <= tidx <= len(trending_topics):
                    break
            except (ValueError, EOFError):
                pass
            print(f"  {DIM}Please enter a number between 1 and {len(trending_topics)}{RESET}")

        trending_topic = trending_topics[tidx - 1]

    # If no trending topic from Grok, use the profile topic directly
    if not trending_topic:
        trending_topic = {
            "name": selected_topic,
            "context": "",
            "popular_take": "",
            "contrarian_angle": "",
        }

    print(f"\n  {GREEN}Topic: {BOLD}{trending_topic['name']}{RESET}")

    # Angle selection
    print()
    angle_keys = list(ANGLES.keys())
    angle_options = [get_angle_label(k, lang) for k in angle_keys]
    angle_options.append(f"{DIM}Write your own angle{RESET}")

    choice = prompt_choice("Choose your angle:", angle_options)
    choice_idx = int(choice) - 1

    if choice_idx < len(angle_keys):
        selected_angle = angle_keys[choice_idx]
        angle_instruction = get_angle_instruction(selected_angle, lang)
    else:
        # Custom angle
        selected_angle = "custom"
        custom_desc = _ask_input("Describe your angle: ", required=True)
        angle_instruction = (
            f"Write a tweet with this specific angle/perspective: {custom_desc}\n"
            f"Optimize for maximum algorithm engagement while staying true to "
            f"this angle."
        )

    # ── Generate tweet ───────────────────────────────────────────
    print(f"\n  {BOLD}{BRIGHT_CYAN}Generating tweet...{RESET}\n")

    try:
        result = generate_discovery_tweet(
            trending_topic=trending_topic,
            angle=selected_angle,
            angle_instruction=angle_instruction,
            user_profile=user_profile,
            lang=lang,
            has_media=getattr(args, "media", False),
            thread=getattr(args, "thread", False),
        )
    except OptimizationError as e:
        print(f"  {RED}Generation failed: {e}{RESET}\n")
        return

    # Show result
    print(render_discovery_result(result))

    # Enter interactive menu for copy/refine/phase2
    generated_tweet = result["optimized"].get("tweet", "")
    if generated_tweet:
        _interactive_menu(
            args,
            original_tweet=generated_tweet,
            current_tweet=generated_tweet,
            lang=lang,
            user_profile=user_profile,
        )


# ── Optimization flows (existing) ───────────────────────────────

def interactive_flow(args):
    """Run the two-phase interactive optimization flow."""
    original_tweet = args.tweet

    # Phase 1: Preserve-style optimization
    print(f"\n  {BOLD}{BRIGHT_CYAN}Optimizing tweet...{RESET}\n")

    try:
        result = optimize_preserve_style(
            tweet=original_tweet,
            topic=args.topic,
            lang=args.lang,
            has_media=args.media,
            thread=args.thread,
            user_profile=getattr(args, "user_profile", None),
        )
    except OptimizationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(render_preserve_style(result))

    optimized_tweet = result["optimized"].get("tweet", "")
    detected_lang = result.get("lang", args.lang)

    _interactive_menu(args, original_tweet, optimized_tweet, detected_lang,
                      user_profile=getattr(args, "user_profile", None))


def _interactive_menu(args, original_tweet: str, current_tweet: str, lang: str,
                      user_profile: dict | None = None):
    """Show the interactive menu in a loop. Supports refine iterations."""
    while True:
        choice = prompt_choice(
            "What would you like to do?",
            [
                f"{GREEN}Copy optimized tweet to clipboard{RESET}",
                f"{CYAN}Refine with AI (request changes){RESET}",
                f"{MAGENTA}Generate different style variations{RESET}",
                f"{YELLOW}Copy original tweet to clipboard{RESET}",
                f"{DIM}Exit{RESET}",
            ],
        )

        if choice == "1":
            if copy_to_clipboard(current_tweet):
                print(f"\n  {GREEN}{BOLD}Copied to clipboard!{RESET}\n")
            else:
                print(f"\n  {YELLOW}Could not access clipboard. Here's the tweet to copy:{RESET}\n")
                print(f"  {current_tweet}\n")

        elif choice == "2":
            current_tweet = _refine_loop(args, original_tweet, current_tweet, lang,
                                         user_profile=user_profile)

        elif choice == "3":
            _run_phase2(args, original_tweet, user_profile=user_profile)
            return

        elif choice == "4":
            if copy_to_clipboard(original_tweet):
                print(f"\n  {GREEN}{BOLD}Copied original to clipboard!{RESET}\n")
            else:
                print(f"\n  {YELLOW}Could not access clipboard.{RESET}\n")

        else:
            print(f"\n  {DIM}Done.{RESET}\n")
            return


def _refine_loop(args, original_tweet: str, current_tweet: str, lang: str,
                  user_profile: dict | None = None) -> str:
    """Ask user for feedback, send to AI, show result. Returns the latest tweet."""
    print(f"\n  {BOLD}{WHITE}What would you like to change?{RESET}")
    print(f"  {GRAY}(Type your instructions, e.g. 'make it shorter', 'keep the URL', 'add humor'){RESET}\n")

    try:
        feedback = input(f"  {BRIGHT_CYAN}> {RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return current_tweet

    if not feedback:
        print(f"  {DIM}No changes requested.{RESET}")
        return current_tweet

    print(f"\n  {BOLD}{BRIGHT_CYAN}Refining tweet...{RESET}\n")

    try:
        result = refine_tweet(
            original_tweet=original_tweet,
            current_tweet=current_tweet,
            user_feedback=feedback,
            lang=lang,
            has_media=getattr(args, "media", False),
            thread=getattr(args, "thread", False),
            user_profile=user_profile,
        )
    except OptimizationError as e:
        print(f"  {YELLOW}Refinement failed: {e}{RESET}\n")
        return current_tweet

    print(render_preserve_style(result))
    return result["optimized"].get("tweet", current_tweet)


def _run_phase2(args, tweet: str, user_profile: dict | None = None):
    """Run Phase 2: generate different style variations."""
    variations = getattr(args, "variations", 3)
    print(f"\n  {BOLD}{BRIGHT_CYAN}Generating {variations} style variations...{RESET}\n")

    try:
        result = optimize(
            tweet=tweet,
            topic=getattr(args, "topic", None),
            lang=getattr(args, "lang", "auto"),
            variations=variations,
            style=getattr(args, "style", "professional"),
            has_media=getattr(args, "media", False),
            thread=getattr(args, "thread", False),
            user_profile=user_profile,
        )
    except OptimizationError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    print(render_variations(result, verbose=getattr(args, "verbose", False)))

    num_vars = len(result["variations"])
    options = [
        f"Copy variation #{i+1} to clipboard"
        for i in range(num_vars)
    ]
    options.append(f"{DIM}Done{RESET}")

    choice = prompt_choice("Which tweet would you like to copy?", options)

    try:
        idx = int(choice) - 1
        if 0 <= idx < num_vars:
            var_tweet = result["variations"][idx].get("tweet", "")
            if copy_to_clipboard(var_tweet):
                print(f"\n  {GREEN}{BOLD}Variation #{idx+1} copied to clipboard!{RESET}\n")
            else:
                print(f"\n  {YELLOW}Could not access clipboard. Here's the tweet:{RESET}\n")
                print(f"  {var_tweet}\n")
        else:
            print(f"\n  {DIM}Done.{RESET}\n")
    except (ValueError, IndexError):
        print(f"\n  {DIM}Done.{RESET}\n")


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()

    # Get tweet text from args or file
    tweet = args.tweet
    if args.file:
        try:
            with open(args.file) as f:
                tweet = f.read().strip()
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

    # No tweet provided -> interactive welcome mode
    if not tweet:
        _welcome_flow(args)
        return

    args.tweet = tweet

    # Fetch user profile if --username provided
    user_profile = None
    if args.username:
        user_profile = _fetch_profile(args.username, force_refresh=args.refresh_profile)
    args.user_profile = user_profile

    # JSON output mode (non-interactive)
    if args.json_output:
        try:
            result = optimize(
                tweet=tweet,
                topic=args.topic,
                lang=args.lang,
                variations=args.variations,
                style=args.style,
                has_media=args.media,
                thread=args.thread,
                user_profile=user_profile,
            )
        except OptimizationError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(render_json(result))
        return

    # Non-interactive mode (legacy behavior)
    if args.no_interactive:
        try:
            result = optimize(
                tweet=tweet,
                topic=args.topic,
                lang=args.lang,
                variations=args.variations,
                style=args.style,
                has_media=args.media,
                thread=args.thread,
                user_profile=user_profile,
            )
        except OptimizationError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(render_variations(result, verbose=args.verbose))
        return

    # Interactive mode (default, with tweet provided)
    interactive_flow(args)


if __name__ == "__main__":
    main()

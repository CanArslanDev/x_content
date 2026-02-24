"""X user profile fetching, analysis, and caching.

Fetches a user's recent tweets via twscrape, analyzes writing style,
engagement patterns, and top-performing content. Results are cached
to avoid repeated API calls.

Dependencies:
  - twscrape (optional): pip install twscrape
  - Falls back gracefully if not installed or credentials unavailable.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from x_content import config


# ── Type definitions ─────────────────────────────────────────────

class StyleFingerprint(TypedDict):
    avg_tweet_length: float
    avg_line_count: float
    emoji_frequency: float
    hashtag_frequency: float
    question_frequency: float
    typical_tone: str
    uses_line_breaks: bool


class EngagementMetrics(TypedDict):
    avg_likes: float
    avg_retweets: float
    avg_replies: float
    avg_quotes: float
    avg_bookmarks: float
    avg_views: float
    engagement_rate_likes: float
    engagement_rate_retweets: float
    engagement_rate_total: float


class TopTweet(TypedDict):
    text: str
    likes: int
    retweets: int
    replies: int
    quotes: int
    views: int
    engagement_score: float
    structural_features: dict


class UserProfile(TypedDict):
    username: str
    followers: int
    following: int
    tweet_count: int
    verified: bool
    description: str
    engagement: EngagementMetrics
    style: StyleFingerprint
    top_tweets: list[TopTweet]
    topics: list[str]
    posting_frequency_hours: float
    lang: str
    fetched_at: str


# ── Stopwords for topic detection ────────────────────────────────

_STOPWORDS_EN = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "himself", "she", "her", "hers", "herself", "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves", "what", "which",
    "who", "whom", "this", "that", "these", "those", "am", "in", "on",
    "at", "by", "for", "with", "about", "between", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "don", "now", "also", "but", "and", "or", "if",
    "of", "as", "into", "because", "while", "until", "get", "got",
    "like", "really", "much", "many", "even", "still", "already",
    "going", "make", "think", "know", "want", "new", "one", "two",
    "every", "people", "thing", "things", "way", "good", "right",
})

_STOPWORDS_TR = frozenset({
    "bir", "bu", "ve", "de", "da", "ile", "için", "ama", "ya",
    "ne", "o", "ben", "sen", "biz", "siz", "onlar", "ki", "var",
    "yok", "çok", "daha", "en", "her", "gibi", "kadar", "sonra",
    "önce", "olan", "olarak", "bunu", "şu", "ise", "mi", "mu",
    "mı", "mü", "olan", "olur", "oldu", "olan", "ama", "fakat",
    "ancak", "lakin", "hem", "ya", "veya", "ile", "birlikte",
})


# ── Public API ───────────────────────────────────────────────────

def fetch_profile(
    username: str,
    force_refresh: bool = False,
) -> UserProfile | None:
    """Fetch and analyze an X user's profile.

    Main entry point. Returns a UserProfile dict or None on failure.
    Uses file-based caching with configurable TTL.

    Args:
        username: X username (without @).
        force_refresh: Skip cache and fetch fresh data.
    """
    username = username.lstrip("@").strip()
    if not username:
        return None

    # Try cache first
    if not force_refresh:
        cached = _load_cached_profile(username)
        if cached is not None:
            return cached

    # Fetch live data
    try:
        user_data, tweets = _fetch_user_data(username)
    except Exception as e:
        print(f"  \033[33mWarning: Could not fetch profile @{username}: {e}\033[0m")
        return None

    if user_data is None or not tweets:
        print(f"  \033[33mWarning: No data returned for @{username}\033[0m")
        return None

    # Analyze
    from x_content.analyzer import analyze, detect_language

    # Detect dominant language from tweets
    lang_counts: Counter = Counter()
    for t in tweets:
        lang_counts[detect_language(t["text"])] += 1
    dominant_lang = lang_counts.most_common(1)[0][0] if lang_counts else "en"

    style = _analyze_style(tweets, dominant_lang)
    engagement = _analyze_engagement(tweets, user_data.get("followers", 0))
    top_tweets = _find_top_tweets(tweets, analyze)
    topics = _detect_topics(tweets, dominant_lang)
    freq = _compute_posting_frequency(tweets)

    profile: UserProfile = {
        "username": username,
        "followers": user_data.get("followers", 0),
        "following": user_data.get("following", 0),
        "tweet_count": user_data.get("tweet_count", 0),
        "verified": user_data.get("verified", False),
        "description": user_data.get("description", ""),
        "engagement": engagement,
        "style": style,
        "top_tweets": top_tweets,
        "topics": topics,
        "posting_frequency_hours": freq,
        "lang": dominant_lang,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    _save_cached_profile(username, profile)
    return profile


def build_manual_profile(
    username: str,
    followers: int,
    avg_likes: float,
    avg_retweets: float,
    avg_replies: float,
    topics: list[str],
    sample_tweets: list[str] | None = None,
) -> UserProfile:
    """Build a UserProfile from manually entered data.

    Used when twscrape/credentials are not available. The user provides
    basic stats and optionally pastes a few sample tweets for style analysis.
    """
    from x_content.analyzer import analyze, detect_language

    # Detect language from topics or sample tweets
    lang = "en"
    if sample_tweets:
        lang_counts: Counter = Counter()
        for t in sample_tweets:
            lang_counts[detect_language(t)] += 1
        lang = lang_counts.most_common(1)[0][0] if lang_counts else "en"

    # Build tweet dicts from sample tweets
    tweet_dicts = []
    if sample_tweets:
        for text in sample_tweets:
            tweet_dicts.append({
                "text": text,
                "likes": int(avg_likes),
                "retweets": int(avg_retweets),
                "replies": int(avg_replies),
                "quotes": 0,
                "views": 0,
                "bookmarks": 0,
                "date": "",
            })

    # Analyze style from samples
    if tweet_dicts:
        style = _analyze_style(tweet_dicts, lang)
    else:
        style = StyleFingerprint(
            avg_tweet_length=140,
            avg_line_count=2.0,
            emoji_frequency=0.5,
            hashtag_frequency=0.3,
            question_frequency=0.2,
            typical_tone="professional",
            uses_line_breaks=True,
        )

    # Engagement metrics
    avg_quotes = 0.0
    er_likes = (avg_likes / max(followers, 1)) * 100
    er_rts = (avg_retweets / max(followers, 1)) * 100
    er_total = ((avg_likes + avg_retweets + avg_replies) / max(followers, 1)) * 100

    engagement = EngagementMetrics(
        avg_likes=round(avg_likes, 1),
        avg_retweets=round(avg_retweets, 1),
        avg_replies=round(avg_replies, 1),
        avg_quotes=0.0,
        avg_bookmarks=0.0,
        avg_views=0.0,
        engagement_rate_likes=round(er_likes, 2),
        engagement_rate_retweets=round(er_rts, 2),
        engagement_rate_total=round(er_total, 2),
    )

    # Top tweets from samples
    top_tweets: list[TopTweet] = []
    if sample_tweets:
        for text in sample_tweets:
            features = analyze(text)
            score = int(avg_likes) + 3 * int(avg_retweets) + 5 * int(avg_replies)
            top_tweets.append(TopTweet(
                text=text,
                likes=int(avg_likes),
                retweets=int(avg_retweets),
                replies=int(avg_replies),
                quotes=0,
                views=0,
                engagement_score=float(score),
                structural_features=features,
            ))

    profile: UserProfile = {
        "username": username,
        "followers": followers,
        "following": 0,
        "tweet_count": 0,
        "verified": False,
        "description": "",
        "engagement": engagement,
        "style": style,
        "top_tweets": top_tweets,
        "topics": topics,
        "posting_frequency_hours": 0.0,
        "lang": lang,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    _save_cached_profile(username, profile)
    return profile


# ── twscrape integration ─────────────────────────────────────────

def _fetch_user_data(username: str) -> tuple[dict | None, list[dict]]:
    """Fetch user info and recent tweets via twscrape.

    Returns (user_dict, tweets_list). Raises on failure.
    """
    try:
        import twscrape
    except ImportError:
        raise RuntimeError(
            "twscrape is not installed. Install with: pip install twscrape"
        )

    import asyncio

    creds = _load_auth_credentials()
    if not creds:
        raise RuntimeError(
            "X/Twitter credentials not configured.\n"
            "\n"
            "  twscrape requires an authenticated X account to fetch data.\n"
            "  Set up credentials using ONE of these methods:\n"
            "\n"
            "  1. Environment variables:\n"
            "     export TWITTER_USERNAME='your_x_username'\n"
            "     export TWITTER_PASSWORD='your_x_password'\n"
            "     export TWITTER_EMAIL='your_email'\n"
            "     export TWITTER_EMAIL_PASSWORD='your_email_password'\n"
            "\n"
            "  2. Create a .twitter_cookies file (JSON):\n"
            '     {"username": "...", "password": "...", "email": "...", "email_password": "..."}\n'
            "\n"
            "  3. Add to config.yaml:\n"
            "     profile:\n"
            "       credentials:\n"
            "         username: your_x_username\n"
            "         password: your_x_password\n"
            "         email: your_email\n"
            "         email_password: your_email_password\n"
            "\n"
            "  Note: Use a secondary account, not your main account."
        )

    async def _fetch():
        api = twscrape.API()

        await api.pool.add_account(
            creds["username"],
            creds["password"],
            creds.get("email", ""),
            creds.get("email_password", ""),
        )
        await api.pool.login_all()

        # Get user info
        user = await api.user_by_login(username)
        if user is None:
            return None, []

        user_dict = {
            "followers": user.followersCount,
            "following": user.friendsCount,
            "tweet_count": user.statusesCount,
            "verified": user.verified or user.blueVerified,
            "description": user.rawDescription or "",
        }

        # Get recent tweets
        max_tweets = config.get("profile", {}).get("max_tweets", 50)
        tweets_list = []
        async for tweet in api.user_tweets(user.id, limit=max_tweets):
            # Skip retweets
            if tweet.rawContent.startswith("RT @"):
                continue
            tweets_list.append({
                "text": tweet.rawContent,
                "likes": tweet.likeCount,
                "retweets": tweet.retweetCount,
                "replies": tweet.replyCount,
                "quotes": tweet.quoteCount,
                "views": tweet.viewCount or 0,
                "bookmarks": tweet.bookmarkCount or 0,
                "date": tweet.date.isoformat() if tweet.date else "",
            })

        return user_dict, tweets_list

    return asyncio.run(_fetch())


# ── Analysis helpers ─────────────────────────────────────────────

def _analyze_style(tweets: list[dict], lang: str) -> StyleFingerprint:
    """Compute writing style fingerprint from tweet texts."""
    if not tweets:
        return StyleFingerprint(
            avg_tweet_length=0, avg_line_count=0, emoji_frequency=0,
            hashtag_frequency=0, question_frequency=0,
            typical_tone="neutral", uses_line_breaks=False,
        )

    lengths = []
    line_counts = []
    emoji_counts = []
    hashtag_counts = []
    question_counts = []

    for t in tweets:
        text = t["text"]
        lengths.append(len(text))
        lines = [l for l in text.strip().split("\n") if l.strip()]
        line_counts.append(len(lines))
        emoji_counts.append(len(re.findall(
            r"[\U0001f300-\U0001f9ff\U00002600-\U000027bf\U0000fe00-\U0000feff]",
            text
        )))
        hashtag_counts.append(len(re.findall(r"#\w+", text)))
        question_counts.append(text.count("?"))

    n = len(tweets)
    avg_len = sum(lengths) / n
    avg_lines = sum(line_counts) / n
    avg_emoji = sum(emoji_counts) / n
    avg_hashtag = sum(hashtag_counts) / n
    avg_question = sum(question_counts) / n
    uses_breaks = avg_lines > 1.5

    # Determine tone heuristically
    if avg_emoji > 1.5:
        tone = "casual"
    elif avg_question > 0.5 and avg_len > 150:
        tone = "educational"
    elif avg_len < 100:
        tone = "punchy"
    else:
        tone = "professional"

    return StyleFingerprint(
        avg_tweet_length=round(avg_len, 1),
        avg_line_count=round(avg_lines, 1),
        emoji_frequency=round(avg_emoji, 2),
        hashtag_frequency=round(avg_hashtag, 2),
        question_frequency=round(avg_question, 2),
        typical_tone=tone,
        uses_line_breaks=uses_breaks,
    )


def _analyze_engagement(
    tweets: list[dict], followers_count: int,
) -> EngagementMetrics:
    """Compute average engagement metrics across tweets."""
    if not tweets:
        return EngagementMetrics(
            avg_likes=0, avg_retweets=0, avg_replies=0,
            avg_quotes=0, avg_bookmarks=0, avg_views=0,
            engagement_rate_likes=0, engagement_rate_retweets=0,
            engagement_rate_total=0,
        )

    n = len(tweets)
    total_likes = sum(t.get("likes", 0) for t in tweets)
    total_rts = sum(t.get("retweets", 0) for t in tweets)
    total_replies = sum(t.get("replies", 0) for t in tweets)
    total_quotes = sum(t.get("quotes", 0) for t in tweets)
    total_bookmarks = sum(t.get("bookmarks", 0) for t in tweets)
    total_views = sum(t.get("views", 0) for t in tweets)

    avg_likes = total_likes / n
    avg_rts = total_rts / n
    avg_replies = total_replies / n
    avg_quotes = total_quotes / n

    # Engagement rates (relative to followers)
    if followers_count > 0:
        er_likes = (avg_likes / followers_count) * 100
        er_rts = (avg_rts / followers_count) * 100
        er_total = ((avg_likes + avg_rts + avg_replies + avg_quotes) / followers_count) * 100
    else:
        er_likes = 0
        er_rts = 0
        er_total = 0

    return EngagementMetrics(
        avg_likes=round(avg_likes, 1),
        avg_retweets=round(avg_rts, 1),
        avg_replies=round(avg_replies, 1),
        avg_quotes=round(avg_quotes, 1),
        avg_bookmarks=round(total_bookmarks / n, 1),
        avg_views=round(total_views / n, 1),
        engagement_rate_likes=round(er_likes, 2),
        engagement_rate_retweets=round(er_rts, 2),
        engagement_rate_total=round(er_total, 2),
    )


def _find_top_tweets(
    tweets: list[dict],
    analyze_fn,
    n: int | None = None,
) -> list[TopTweet]:
    """Find top-performing tweets by composite engagement score.

    Score formula: likes + 3*RTs + 5*replies + 10*quotes
    """
    if n is None:
        n = config.get("profile", {}).get("top_tweets_count", 5)

    scored = []
    for t in tweets:
        score = (
            t.get("likes", 0)
            + 3 * t.get("retweets", 0)
            + 5 * t.get("replies", 0)
            + 10 * t.get("quotes", 0)
        )
        scored.append((score, t))

    scored.sort(key=lambda x: -x[0])

    top: list[TopTweet] = []
    for score, t in scored[:n]:
        features = analyze_fn(t["text"])
        top.append(TopTweet(
            text=t["text"],
            likes=t.get("likes", 0),
            retweets=t.get("retweets", 0),
            replies=t.get("replies", 0),
            quotes=t.get("quotes", 0),
            views=t.get("views", 0),
            engagement_score=score,
            structural_features=features,
        ))

    return top


def _detect_topics(tweets: list[dict], lang: str) -> list[str]:
    """Detect main topics from tweet content via word frequency."""
    stopwords = _STOPWORDS_TR if lang == "tr" else _STOPWORDS_EN

    word_counts: Counter = Counter()
    for t in tweets:
        text = t["text"].lower()
        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)
        # Remove mentions and hashtags
        text = re.sub(r"[@#]\w+", "", text)
        # Remove non-alphanumeric (keep Turkish chars)
        text = re.sub(r"[^\w\s]", "", text)

        words = text.split()
        for w in words:
            if len(w) > 2 and w not in stopwords:
                word_counts[w] += 1

    # Also extract hashtags as topics
    hashtag_counts: Counter = Counter()
    for t in tweets:
        for tag in re.findall(r"#(\w+)", t["text"]):
            hashtag_counts[tag.lower()] += 1

    # Combine: hashtags are strong topic signals
    combined: Counter = Counter()
    for word, count in word_counts.most_common(50):
        combined[word] += count
    for tag, count in hashtag_counts.items():
        combined[tag] += count * 3  # Hashtags weigh more

    return [word for word, _ in combined.most_common(10)]


def _compute_posting_frequency(tweets: list[dict]) -> float:
    """Compute average hours between tweets."""
    dates = []
    for t in tweets:
        date_str = t.get("date", "")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str)
                dates.append(dt)
            except (ValueError, TypeError):
                pass

    if len(dates) < 2:
        return 0.0

    dates.sort()
    total_hours = (dates[-1] - dates[0]).total_seconds() / 3600
    return round(total_hours / (len(dates) - 1), 1)


# ── Credentials ──────────────────────────────────────────────────

def _load_auth_credentials() -> dict | None:
    """Load Twitter auth credentials from config, cookie file, or env vars.

    Priority:
      1. config.yaml > profile > credentials
      2. .twitter_cookies JSON file
      3. Environment variables (TWITTER_USERNAME, TWITTER_PASSWORD)
    """
    # 1. config.yaml
    creds = config.get("profile", {}).get("credentials")
    if creds and creds.get("username") and creds.get("password"):
        return creds

    # 2. .twitter_cookies file
    cookie_path = Path(".twitter_cookies")
    if cookie_path.exists():
        try:
            data = json.loads(cookie_path.read_text("utf-8"))
            if data.get("username") and data.get("password"):
                return data
        except (json.JSONDecodeError, KeyError):
            pass

    # 3. Environment variables
    env_user = os.environ.get("TWITTER_USERNAME")
    env_pass = os.environ.get("TWITTER_PASSWORD")
    if env_user and env_pass:
        return {
            "username": env_user,
            "password": env_pass,
            "email": os.environ.get("TWITTER_EMAIL", ""),
            "email_password": os.environ.get("TWITTER_EMAIL_PASSWORD", ""),
        }

    return None


# ── Cache ────────────────────────────────────────────────────────

def _get_cache_dir() -> Path:
    """Get the profile cache directory, creating it if needed."""
    cache_dir = Path(config.get("profile", {}).get("cache_dir", ".cache/profiles"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _load_cached_profile(username: str) -> UserProfile | None:
    """Load a cached profile if it exists and hasn't expired."""
    cache_file = _get_cache_dir() / f"{username.lower()}.json"
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    # Check TTL
    ttl_hours = config.get("profile", {}).get("cache_ttl_hours", 24)
    fetched_at = data.get("fetched_at", "")
    if fetched_at:
        try:
            fetch_time = datetime.fromisoformat(fetched_at)
            age_hours = (datetime.now(timezone.utc) - fetch_time).total_seconds() / 3600
            if age_hours > ttl_hours:
                return None  # Expired
        except (ValueError, TypeError):
            return None

    return data


def _save_cached_profile(username: str, profile: UserProfile) -> None:
    """Save a profile to the cache directory."""
    cache_file = _get_cache_dir() / f"{username.lower()}.json"
    try:
        cache_file.write_text(json.dumps(profile, ensure_ascii=False, indent=2), "utf-8")
    except OSError:
        pass  # Silently fail on write errors

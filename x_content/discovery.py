"""Trending topic discovery and content creation.

Analyzes user profile to suggest strong topic areas,
generates structured Grok research prompts, and parses
Grok's responses into selectable trending topics.
"""

from __future__ import annotations

import re
from typing import TypedDict


# ── Types ────────────────────────────────────────────────────────

class TopicRanking(TypedDict):
    topic: str
    avg_engagement: float
    tweet_count: int


class TrendingTopic(TypedDict):
    name: str
    context: str
    popular_take: str
    contrarian_angle: str


# ── Angle definitions ────────────────────────────────────────────

ANGLES = {
    "dominant": {
        "label_en": "Align with the popular opinion",
        "label_tr": "Populer gorusle ayni yonde yaz",
        "instruction_en": (
            "Write a tweet that aligns with the dominant/popular opinion on this topic. "
            "Validate what most people are thinking. This builds relatability and "
            "boosts favorite_score and repost_score."
        ),
        "instruction_tr": (
            "Bu konuda populer gorusle ayni yonde bir tweet yaz. "
            "Cogunlugun dusundugunu dogrula. Bu yaklasim begeni ve "
            "retweet sinyallerini guclendirir."
        ),
    },
    "contrarian": {
        "label_en": "Take the contrarian angle (higher engagement potential)",
        "label_tr": "Karsi gorusle yaz (daha yuksek etkilesim potansiyeli)",
        "instruction_en": (
            "Write a tweet that presents a contrarian or opposing view on this topic. "
            "Challenge the mainstream narrative with a well-reasoned take. "
            "Contrarian tweets trigger significantly higher quote_score (weight=40) "
            "and reply_score (weight=27) because people feel compelled to respond. "
            "Be provocative but not offensive — avoid block/report triggers."
        ),
        "instruction_tr": (
            "Bu konuda karsi veya farkli bir bakis acisi sunan bir tweet yaz. "
            "Ana akim anlatiyi iyi gerekcelendirilmis bir gorusle sorgula. "
            "Karsi gorusler quote_score (agirlik=40) ve reply_score (agirlik=27) "
            "sinyallerini guclu sekilde tetikler. Provokatif ama saygili ol."
        ),
    },
    "personal": {
        "label_en": "Share personal insight / experience",
        "label_tr": "Kisisel deneyim / ozgun bakis acisi paylas",
        "instruction_en": (
            "Write a tweet sharing a personal experience, unique insight, or "
            "behind-the-scenes perspective related to this topic. "
            "Personal stories are the strongest driver of share_via_dm_score "
            "(weight=100 — the single most powerful signal) because people forward "
            "them to specific friends. Use first person, be authentic."
        ),
        "instruction_tr": (
            "Bu konuyla ilgili kisisel bir deneyim, ozgun bir bakis acisi veya "
            "perde arkasi bilgi paylasan bir tweet yaz. "
            "Kisisel hikayeler share_via_dm_score (agirlik=100 — en guclu sinyal) "
            "sinyalini en cok tetikleyen icerik turudur. Birinci tekil sahis kullan, "
            "samimi ol."
        ),
    },
}


def get_angle_label(angle: str, lang: str = "en") -> str:
    """Get the display label for an angle."""
    key = f"label_{lang}" if lang in ("en", "tr") else "label_en"
    return ANGLES.get(angle, ANGLES["dominant"]).get(key, "")


def get_angle_instruction(angle: str, lang: str = "en") -> str:
    """Get the prompt instruction for an angle."""
    key = f"instruction_{lang}" if lang in ("en", "tr") else "instruction_en"
    return ANGLES.get(angle, ANGLES["dominant"]).get(key, "")


# ── Topic ranking ────────────────────────────────────────────────

def rank_topics_by_engagement(user_profile: dict) -> list[TopicRanking]:
    """Rank user's topics by average engagement in their top tweets.

    Cross-references profile topics with top_tweets content to
    calculate which topics drive the most engagement for this user.
    """
    topics = user_profile.get("topics", [])
    top_tweets = user_profile.get("top_tweets", [])

    if not topics:
        return []

    rankings: list[TopicRanking] = []
    for topic in topics:
        topic_lower = topic.lower()
        matching_scores = []
        for tt in top_tweets:
            text_lower = tt.get("text", "").lower()
            if topic_lower in text_lower:
                matching_scores.append(tt.get("engagement_score", 0))

        # Also check across all engagement data
        avg = sum(matching_scores) / len(matching_scores) if matching_scores else 0
        rankings.append(TopicRanking(
            topic=topic,
            avg_engagement=round(avg, 1),
            tweet_count=len(matching_scores),
        ))

    # Sort by avg_engagement descending, then by tweet_count
    rankings.sort(key=lambda r: (-r["avg_engagement"], -r["tweet_count"]))
    return rankings


# ── Grok prompt builder ──────────────────────────────────────────

def build_grok_prompt(topic: str, lang: str = "en") -> str:
    """Build a structured Grok research prompt for the given topic.

    The prompt asks Grok for trending topics with structured fields
    that can be parsed back into TrendingTopic objects.
    """
    if lang == "tr":
        return (
            f"X/Twitter'da su anda \"{topic}\" hakkinda en cok konusulan "
            f"5 gundem maddesini listele.\n"
            f"\n"
            f"Her madde icin su formatta yaz:\n"
            f"1. Konu: [spesifik olay/konu adi]\n"
            f"   Neden gundemde: [1 cumle aciklama]\n"
            f"   Populer gorus: [X'te hakim olan gorus]\n"
            f"   Karsi gorus: [az temsil edilen veya farkli bir bakis acisi]\n"
            f"\n"
            f"Genel degil, spesifik ve guncel ol. "
            f"Bugun aktif olarak tartisilan konulara odaklan."
        )

    return (
        f"What are the top 5 trending topics, news, or discussions "
        f"about \"{topic}\" on X/Twitter right now?\n"
        f"\n"
        f"For each, use this exact format:\n"
        f"1. Topic: [specific event/topic name]\n"
        f"   Context: [why it's trending, 1 sentence]\n"
        f"   Popular take: [the dominant opinion on X]\n"
        f"   Contrarian angle: [an underrepresented or opposing perspective]\n"
        f"\n"
        f"Be specific and current. Focus on what's actively being "
        f"discussed today, not generic themes."
    )


# ── Grok response parser ────────────────────────────────────────

def parse_grok_response(text: str) -> list[TrendingTopic]:
    """Parse Grok's freeform response into structured trending topics.

    Attempts structured parsing first, falls back to extracting
    numbered items if the format doesn't match exactly.
    """
    if not text or not text.strip():
        return []

    # Strategy 1: Try structured field parsing
    topics = _parse_structured(text)
    if topics:
        return topics

    # Strategy 2: Split by numbered items and extract titles
    topics = _parse_numbered_items(text)
    if topics:
        return topics

    # Strategy 3: Fall back to paragraph splitting
    return _parse_paragraphs(text)


def _parse_structured(text: str) -> list[TrendingTopic]:
    """Try to parse response with structured fields (Topic/Context/Popular/Contrarian)."""
    # Match numbered items with sub-fields
    pattern = re.compile(
        r'\d+\.\s*'
        r'(?:Topic|Konu)\s*:\s*(.+?)(?:\n|$)'
        r'(?:.*?(?:Context|Neden\s+gundemde)\s*:\s*(.+?)(?:\n|$))?'
        r'(?:.*?(?:Popular\s+take|Populer\s+gorus)\s*:\s*(.+?)(?:\n|$))?'
        r'(?:.*?(?:Contrarian\s+angle|Karsi\s+gorus)\s*:\s*(.+?)(?:\n|$))?',
        re.IGNORECASE | re.DOTALL,
    )

    topics = []
    for m in pattern.finditer(text):
        name = m.group(1).strip().strip('"\'*[]')
        context = (m.group(2) or "").strip().strip('"\'*[]')
        popular = (m.group(3) or "").strip().strip('"\'*[]')
        contrarian = (m.group(4) or "").strip().strip('"\'*[]')

        if name:
            topics.append(TrendingTopic(
                name=name,
                context=context,
                popular_take=popular,
                contrarian_angle=contrarian,
            ))

    return topics


def _parse_numbered_items(text: str) -> list[TrendingTopic]:
    """Parse numbered list items, extracting the first line as topic name."""
    # Split by numbered items: "1.", "2.", etc.
    parts = re.split(r'\n(?=\d+[\.\)]\s)', text.strip())

    topics = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Remove leading number
        cleaned = re.sub(r'^\d+[\.\)]\s*', '', part)
        lines = [l.strip() for l in cleaned.split('\n') if l.strip()]

        if not lines:
            continue

        # First line is the topic name (strip markdown bold, etc.)
        name = re.sub(r'\*\*(.+?)\*\*', r'\1', lines[0])
        name = name.strip().strip(':').strip('"\'*[]')

        # Try to extract sub-fields from remaining lines
        context = ""
        popular = ""
        contrarian = ""

        rest = '\n'.join(lines[1:])
        for line in lines[1:]:
            lower = line.lower()
            if any(k in lower for k in ('context', 'neden', 'trending', 'gundem')):
                context = re.sub(r'^.*?:\s*', '', line).strip()
            elif any(k in lower for k in ('popular', 'populer', 'dominant', 'mainstream')):
                popular = re.sub(r'^.*?:\s*', '', line).strip()
            elif any(k in lower for k in ('contrarian', 'karsi', 'opposing', 'counter')):
                contrarian = re.sub(r'^.*?:\s*', '', line).strip()

        # If no structured fields found, use rest as context
        if not context and len(lines) > 1:
            # Take the first non-field line as context
            context = lines[1] if len(lines) > 1 else ""
            context = re.sub(r'^[-—:]\s*', '', context).strip()

        if name and len(name) > 2:
            topics.append(TrendingTopic(
                name=name[:120],
                context=context[:200],
                popular_take=popular[:200],
                contrarian_angle=contrarian[:200],
            ))

    return topics


def _parse_paragraphs(text: str) -> list[TrendingTopic]:
    """Last resort: split by double newlines and take first sentence."""
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    topics = []
    for para in paragraphs[:5]:
        first_line = para.split('\n')[0].strip()
        first_line = re.sub(r'^\d+[\.\)]\s*', '', first_line)
        first_line = re.sub(r'\*\*(.+?)\*\*', r'\1', first_line)
        first_line = first_line.strip().strip(':').strip('"\'*[]')

        if first_line and len(first_line) > 3:
            topics.append(TrendingTopic(
                name=first_line[:120],
                context="",
                popular_take="",
                contrarian_angle="",
            ))

    return topics


# ── Grok profile prompt + parser ──────────────────────────────

def build_grok_profile_prompt(username: str, lang: str = "en") -> str:
    """Build a Grok prompt that asks for a user's X profile analysis.

    Grok has access to X data, so it can provide follower count,
    engagement stats, writing style, and topic areas.
    """
    handle = username.lstrip("@").strip()

    if lang == "tr":
        return (
            f"X/Twitter'da @{handle} kullanicisini analiz et.\n"
            f"\n"
            f"Su bilgileri KESINLIKLE su formatta ver:\n"
            f"\n"
            f"Followers: [sayi]\n"
            f"Following: [sayi]\n"
            f"Tweet count: [sayi]\n"
            f"Verified: [Yes/No]\n"
            f"Bio: [profil aciklamasi]\n"
            f"Language: [en/tr/diger]\n"
            f"\n"
            f"Avg likes: [tweet basina ortalama begeni]\n"
            f"Avg retweets: [tweet basina ortalama RT]\n"
            f"Avg replies: [tweet basina ortalama yanit]\n"
            f"Avg quotes: [tweet basina ortalama alinti]\n"
            f"Avg views: [tweet basina ortalama goruntulenme]\n"
            f"\n"
            f"Style: [kisa/uzun/karma]\n"
            f"Tone: [professional/casual/provocative/humorous/analytical]\n"
            f"Uses emojis: [often/sometimes/rarely]\n"
            f"Uses hashtags: [often/sometimes/rarely]\n"
            f"Uses line breaks: [Yes/No]\n"
            f"\n"
            f"Topics: [virgulla ayrilmis ana konulari]\n"
            f"\n"
            f"Top 3 tweets (en cok etkilesim alan):\n"
            f"1. [tweet metni]\n"
            f"   Likes: [sayi] | RTs: [sayi] | Replies: [sayi]\n"
            f"2. [tweet metni]\n"
            f"   Likes: [sayi] | RTs: [sayi] | Replies: [sayi]\n"
            f"3. [tweet metni]\n"
            f"   Likes: [sayi] | RTs: [sayi] | Replies: [sayi]\n"
            f"\n"
            f"Formati degistirme, sadece [] icindeki yerleri doldur."
        )

    return (
        f"Analyze the X/Twitter user @{handle}.\n"
        f"\n"
        f"Provide the following information in EXACTLY this format:\n"
        f"\n"
        f"Followers: [number]\n"
        f"Following: [number]\n"
        f"Tweet count: [number]\n"
        f"Verified: [Yes/No]\n"
        f"Bio: [profile description]\n"
        f"Language: [en/tr/other]\n"
        f"\n"
        f"Avg likes: [average likes per tweet]\n"
        f"Avg retweets: [average retweets per tweet]\n"
        f"Avg replies: [average replies per tweet]\n"
        f"Avg quotes: [average quotes per tweet]\n"
        f"Avg views: [average views per tweet]\n"
        f"\n"
        f"Style: [short/long/mixed]\n"
        f"Tone: [professional/casual/provocative/humorous/analytical]\n"
        f"Uses emojis: [often/sometimes/rarely]\n"
        f"Uses hashtags: [often/sometimes/rarely]\n"
        f"Uses line breaks: [Yes/No]\n"
        f"\n"
        f"Topics: [comma-separated main topics]\n"
        f"\n"
        f"Top 3 tweets (highest engagement):\n"
        f"1. [tweet text]\n"
        f"   Likes: [number] | RTs: [number] | Replies: [number]\n"
        f"2. [tweet text]\n"
        f"   Likes: [number] | RTs: [number] | Replies: [number]\n"
        f"3. [tweet text]\n"
        f"   Likes: [number] | RTs: [number] | Replies: [number]\n"
        f"\n"
        f"Do not change the format. Only fill in the [] placeholders."
    )


def parse_grok_profile_response(text: str, username: str) -> dict | None:
    """Parse Grok's response about a user into profile-building data.

    Returns a dict with keys matching build_manual_profile args:
    username, followers, avg_likes, avg_retweets, avg_replies,
    topics, sample_tweets. Also includes extra fields that
    build_manual_profile doesn't use but enrich the profile.

    Returns None if parsing fails completely.
    """
    if not text or not text.strip():
        return None

    def _extract_number(pattern: str, default: float = 0) -> float:
        """Extract a number from a regex match in the text."""
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            return default
        raw = m.group(1).strip().replace(",", "").replace(" ", "")
        # Handle K/M suffixes
        multiplier = 1
        if raw.upper().endswith("K"):
            raw = raw[:-1]
            multiplier = 1000
        elif raw.upper().endswith("M"):
            raw = raw[:-1]
            multiplier = 1_000_000
        try:
            return float(raw) * multiplier
        except ValueError:
            return default

    def _extract_text(pattern: str, default: str = "") -> str:
        """Extract text from a regex match."""
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else default

    # Core stats
    followers = int(_extract_number(r'Followers?\s*:\s*([^\n]+)', 0))
    following = int(_extract_number(r'Following\s*:\s*([^\n]+)', 0))
    tweet_count = int(_extract_number(r'Tweet\s+count\s*:\s*([^\n]+)', 0))
    verified_str = _extract_text(r'Verified\s*:\s*([^\n]+)', 'No')
    verified = verified_str.lower().startswith('y')
    bio = _extract_text(r'Bio\s*:\s*([^\n]+)', '')
    lang = _extract_text(r'Language\s*:\s*([^\n]+)', 'en').lower().strip()
    # Normalize lang
    if lang not in ('en', 'tr'):
        if 'tr' in lang or 'turk' in lang:
            lang = 'tr'
        else:
            lang = 'en'

    # Engagement
    avg_likes = _extract_number(r'Avg\s+likes?\s*:\s*([^\n]+)', 0)
    avg_retweets = _extract_number(r'Avg\s+retweets?\s*:\s*([^\n]+)', 0)
    avg_replies = _extract_number(r'Avg\s+replies?\s*:\s*([^\n]+)', 0)
    avg_quotes = _extract_number(r'Avg\s+quotes?\s*:\s*([^\n]+)', 0)
    avg_views = _extract_number(r'Avg\s+views?\s*:\s*([^\n]+)', 0)

    # Style
    tone = _extract_text(r'Tone\s*:\s*([^\n]+)', 'professional').lower()
    emoji_str = _extract_text(r'Uses?\s+emojis?\s*:\s*([^\n]+)', 'sometimes').lower()
    hashtag_str = _extract_text(r'Uses?\s+hashtags?\s*:\s*([^\n]+)', 'sometimes').lower()
    line_breaks_str = _extract_text(r'Uses?\s+line\s*breaks?\s*:\s*([^\n]+)', 'No')

    # Topics
    topics_raw = _extract_text(r'Topics?\s*:\s*([^\n]+)', '')
    topics = [t.strip() for t in topics_raw.split(',') if t.strip()]

    # Top tweets — split by numbered items, take text before the stats line
    sample_tweets = []
    top_section = re.search(
        r'Top\s+\d+\s+tweets?.*?:\s*\n(.*)',
        text, re.IGNORECASE | re.DOTALL,
    )
    if top_section:
        section_text = top_section.group(1)
        # Split into numbered entries
        entries = re.split(r'\n(?=\d+\.)', section_text)
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            # Remove leading number: "1. "
            cleaned = re.sub(r'^\d+\.\s*', '', entry)
            lines = cleaned.split('\n')
            # First line is the tweet text; subsequent lines may be stats
            tweet_text = lines[0].strip().strip('"\'[]')
            if tweet_text and len(tweet_text) > 5:
                sample_tweets.append(tweet_text)

    # Validate: at minimum we need followers or topics
    if followers == 0 and not topics:
        return None

    return {
        "username": username.lstrip("@").strip(),
        "followers": followers,
        "following": following,
        "tweet_count": tweet_count,
        "verified": verified,
        "bio": bio,
        "lang": lang,
        "avg_likes": avg_likes,
        "avg_retweets": avg_retweets,
        "avg_replies": avg_replies,
        "avg_quotes": avg_quotes,
        "avg_views": avg_views,
        "tone": tone,
        "emoji_frequency": emoji_str,
        "hashtag_frequency": hashtag_str,
        "uses_line_breaks": line_breaks_str.lower().startswith('y'),
        "topics": topics,
        "sample_tweets": sample_tweets if sample_tweets else None,
    }

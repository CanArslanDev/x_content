"""Structural tweet analysis (pre-Claude).

Extracts measurable features from tweet text without LLM calls.
"""

import re

# Common Turkish characters for language detection
_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")

# CTA patterns
_CTA_PATTERNS_EN = [
    r"\bfollow\b", r"\bretweet\b", r"\bshare\b", r"\blike\b",
    r"\bcheck out\b", r"\bclick\b", r"\bsubscribe\b", r"\bjoin\b",
    r"\bsave this\b", r"\bbookmark\b", r"\btag\b", r"\bdrop\b",
    r"\bcomment\b", r"\btry\b", r"\bread\b",
]
_CTA_PATTERNS_TR = [
    r"\btakip\b", r"\bpaylaş\b", r"\bbeğen\b", r"\bbak\b",
    r"\btıkla\b", r"\babone\b", r"\bkatıl\b", r"\bkaydet\b",
    r"\byorum\b", r"\bdene\b", r"\boku\b", r"\byaz\b",
]

# Emotional/power words
_POWER_WORDS_EN = [
    "secret", "shocking", "truth", "mistake", "wrong", "never",
    "always", "must", "stop", "warning", "proven", "free",
    "exclusive", "breaking", "urgent", "finally", "revealed",
    "unpopular opinion", "hot take", "thread", "lesson",
]
_POWER_WORDS_TR = [
    "sır", "şok", "gerçek", "hata", "yanlış", "asla",
    "her zaman", "mutlaka", "dur", "uyarı", "kanıtlanmış",
    "ücretsiz", "özel", "son dakika", "acil", "sonunda",
]


def detect_language(text: str) -> str:
    """Simple language detection: 'tr', 'en', or 'auto'."""
    if any(c in _TR_CHARS for c in text):
        return "tr"
    # Check for common Turkish words
    lower = text.lower()
    tr_words = ["bir", "bu", "ve", "ile", "için", "olan", "var",
                "gibi", "ama", "çok", "daha", "ben", "sen", "biz"]
    tr_count = sum(1 for w in tr_words if f" {w} " in f" {lower} ")
    if tr_count >= 2:
        return "tr"
    return "en"


def analyze(text: str, has_media: bool = False) -> dict:
    """Analyze tweet structure and return feature dictionary.

    Returns:
        dict with keys: char_count, char_utilization, line_count,
        has_hook, has_question, question_count, hashtag_count,
        hashtags, has_url, has_media, lang, has_cta, cta_count,
        power_word_count, power_words_found, has_numbers,
        has_list_format, emoji_count, first_line, word_count
    """
    lines = [l for l in text.strip().split("\n") if l.strip()]
    first_line = lines[0].strip() if lines else ""

    # Basic metrics
    char_count = len(text)
    word_count = len(text.split())

    # Hashtags
    hashtags = re.findall(r"#\w+", text)

    # URLs
    has_url = bool(re.search(r"https?://\S+", text))

    # Questions
    questions = text.count("?")

    # Language
    lang = detect_language(text)

    # Hook detection: first line ends with strong punctuation or is a bold statement
    hook_indicators = [":", "?", "!", "...", "—", "👇", "🧵"]
    has_hook = any(first_line.endswith(h) for h in hook_indicators) or len(first_line) < 60

    # CTA detection
    lower_text = text.lower()
    cta_patterns = _CTA_PATTERNS_TR if lang == "tr" else _CTA_PATTERNS_EN
    cta_matches = [p for p in cta_patterns if re.search(p, lower_text)]

    # Power words
    power_words = _POWER_WORDS_TR if lang == "tr" else _POWER_WORDS_EN
    found_power = [w for w in power_words if w in lower_text]

    # Numbers / data
    has_numbers = bool(re.search(r"\d+%?", text))

    # List format (numbered or bulleted lines)
    list_lines = [l for l in lines if re.match(r"^\s*[\d•\-\*►▸→]\s*", l)]
    has_list = len(list_lines) >= 2

    # Emojis (rough count via Unicode range)
    emoji_count = len(re.findall(
        r"[\U0001f300-\U0001f9ff\U00002600-\U000027bf\U0000fe00-\U0000feff]",
        text
    ))

    return {
        "char_count": char_count,
        "char_utilization": round(char_count / 280 * 100, 1),
        "word_count": word_count,
        "line_count": len(lines),
        "first_line": first_line,
        "has_hook": has_hook,
        "has_question": questions > 0,
        "question_count": questions,
        "hashtag_count": len(hashtags),
        "hashtags": hashtags,
        "has_url": has_url,
        "has_media": has_media,
        "lang": lang,
        "has_cta": len(cta_matches) > 0,
        "cta_count": len(cta_matches),
        "power_word_count": len(found_power),
        "power_words_found": found_power,
        "has_numbers": has_numbers,
        "has_list_format": has_list,
        "emoji_count": emoji_count,
    }

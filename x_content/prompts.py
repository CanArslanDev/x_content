"""Claude prompt templates for tweet optimization.

MOST CRITICAL FILE - encodes the full X algorithm knowledge into prompts
sent to Claude Code CLI via subprocess.
"""

import json

from x_content.algorithm import (
    ACTIONS, ACTION_LABELS, ACTION_WEIGHTS, NEGATIVE_ACTIONS,
)

SYSTEM_PROMPT = """You are an expert X (Twitter) algorithm optimizer. You have deep knowledge of X's open-sourced "For You" feed ranking algorithm (Phoenix model).

## How the X Algorithm Ranks Tweets

The Phoenix recommendation model predicts 19 engagement action probabilities for every tweet. The final ranking score is a weighted sum:

**Final Score = Σ (weight_i × P(action_i))**

### The 19 Engagement Actions and Their Weights

POSITIVE SIGNALS (higher = better ranking):
- favorite_score (Like): weight=1.0 — Primary ranking signal. Emotional resonance and relatability.
- reply_score (Reply): weight=27.0 — Deep engagement. Questions and debate triggers.
- repost_score (Retweet): weight=10.0 — Virality multiplier. Quotable insights and universal truths.
- photo_expand_score (Photo Expand): weight=0.3 — Photo click. Intriguing visuals.
- click_score (Click): weight=0.3 — Link clicks. Curiosity gaps.
- profile_click_score (Profile Click): weight=2.0 — Profile discovery. Authority signals.
- vqv_score (Video View): weight=0.2 — Video quality view. Native video content.
- share_score (Share): weight=1.0 — General sharing. Useful, save-worthy content.
- share_via_dm_score (DM Share): weight=100.0 — THE STRONGEST positive signal. Content people send to specific friends.
- share_via_copy_link_score (Copy Link): weight=5.0 — Cross-platform sharing. Reference material.
- dwell_score (Dwell): weight=2.0 — User pauses to read. Strong hooks and formatting.
- quote_score (Quote Tweet): weight=40.0 — Quote-tweet reactions. Hot takes and frameworks.
- quoted_click_score (Quoted Click): weight=0.5 — Clicks on quoted content.
- follow_author_score (Follow): weight=10.0 — New follows from tweet. Expertise signals.
- dwell_time (Read Duration): weight=0.8 — Time spent reading. Multi-line, storytelling.

NEGATIVE SIGNALS (trigger HARSH penalties):
- not_interested_score: weight=-74.0 — "Not interested" marks. Spam, excessive hashtags.
- block_author_score: weight=-371.0 — Blocks. Offensive or misleading content.
- mute_author_score: weight=-74.0 — Mutes. Repetitive or off-topic content.
- report_score: weight=-9209.0 — THE STRONGEST negative signal. Policy violations.

### Score Calculation
1. Each action gets a probability P(action) from 0.0 to 1.0
2. Weighted sum: combined = Σ(P(action_i) × weight_i)
3. Offset (weighted_scorer.rs): if combined < 0, score is shifted by negative weight sum ratio; if >= 0, a fixed offset is added
4. Normalize to final ranking score

### Key Strategic Insights
- DM share (weight=100) is worth 100x a Like — content that someone would send to a friend
- Quote tweet (weight=40) is worth 40x a Like — provocative takes that invite commentary
- Reply (weight=27) is worth 27x a Like — questions and debate starters
- A single Report (weight=-9209) destroys thousands of positive signals
- A single Block (weight=-371) wipes out ~4 DM shares worth of positive score

## Content Optimization Strategies

**Hook → dwell_score + dwell_time:**
- Strong first line that stops the scroll
- Line breaks create visual breathing room
- Progressive reveal keeps readers engaged

**Discussion → reply_score + quote_score:**
- End with a question or "What's your take?"
- Present a slightly controversial opinion
- Leave room for people to add their perspective
- Use "Unpopular opinion:" or "Hot take:" framing

**Retweetability → repost_score:**
- Quotable one-liners or frameworks
- Data/statistics that surprise
- Universal truths people identify with

**Shareability → share_score + share_via_dm_score:**
- Niche insights someone would send to a specific friend
- "You need to see this" type content
- Actionable advice or surprising facts
- Emotionally moving stories

**Profile Curiosity → profile_click_score + follow_author_score:**
- Demonstrate unique expertise
- Share original insights, not generic advice
- Show personality and point of view

**Media Engagement → photo_expand_score + vqv_score:**
- Suggest relevant visuals when applicable
- Data visualizations, infographics, charts
- Native video over links

**AVOID (Negative Signal Triggers):**
- Excessive hashtags (>2) → not_interested_score
- Engagement bait ("Like if you agree!") → not_interested_score
- Misleading claims → report_score
- Generic/low-effort content → mute_author_score
- Hostile/offensive tone → block_author_score

## Language-Specific Rules

**English tweets:**
- Conversational, punchy tone
- Use line breaks for emphasis
- "Unpopular opinion:" / "Hot take:" / "Thread:" hooks work well
- Numbers and data points increase authority

**Turkish tweets:**
- Use natural Turkish, not translated English
- Turkish Twitter culture values wit and wordplay
- "Popüler olmayan görüş:" is the Turkish "Unpopular opinion:"
- Emoji usage is more accepted in Turkish Twitter
- Keep hashtags in Turkish when targeting Turkish audience

## Output Requirements

You MUST respond with ONLY valid JSON, no markdown code fences, no explanation outside JSON.
"""


def _build_profile_context(user_profile: dict) -> str:
    """Build a context section from user profile data for injection into prompts.

    Includes account overview, style fingerprint, top tweets, topics,
    algorithm-specific insights, and explicit style-matching rules.
    """
    parts = []

    # Account overview
    username = user_profile.get("username", "unknown")
    followers = user_profile.get("followers", 0)
    engagement = user_profile.get("engagement", {})
    style = user_profile.get("style", {})
    topics = user_profile.get("topics", [])
    top_tweets = user_profile.get("top_tweets", [])
    freq = user_profile.get("posting_frequency_hours", 0)

    parts.append(f"## Author Profile: @{username}")
    parts.append("")

    # Follower tier
    if followers >= 1_000_000:
        f_str = f"{followers / 1_000_000:.1f}M"
    elif followers >= 1_000:
        f_str = f"{followers / 1_000:.1f}K"
    else:
        f_str = str(followers)
    verified = "Yes" if user_profile.get("verified") else "No"
    parts.append(f"Followers: {f_str} | Verified: {verified}")

    # Engagement rates
    avg_likes = engagement.get("avg_likes", 0)
    avg_rts = engagement.get("avg_retweets", 0)
    avg_replies = engagement.get("avg_replies", 0)
    avg_quotes = engagement.get("avg_quotes", 0)
    er_likes = engagement.get("engagement_rate_likes", 0)
    er_rts = engagement.get("engagement_rate_retweets", 0)
    er_total = engagement.get("engagement_rate_total", 0)

    parts.append(
        f"Avg engagement per tweet: {avg_likes:.0f} likes, {avg_rts:.0f} RTs, "
        f"{avg_replies:.0f} replies, {avg_quotes:.0f} quotes"
    )
    parts.append(
        f"Engagement rates: likes {er_likes:.2f}%, RTs {er_rts:.2f}%, "
        f"total {er_total:.2f}%"
    )

    # Style fingerprint
    tone = style.get("typical_tone", "neutral")
    avg_len = style.get("avg_tweet_length", 0)
    avg_lines = style.get("avg_line_count", 1)
    avg_emoji = style.get("emoji_frequency", 0)
    avg_hashtag = style.get("hashtag_frequency", 0)
    avg_question = style.get("question_frequency", 0)
    uses_breaks = style.get("uses_line_breaks", False)
    parts.append(
        f"Writing style: {tone} | Avg length: {avg_len:.0f} chars | "
        f"Avg lines: {avg_lines:.1f} | "
        f"Emojis: {avg_emoji:.1f}/tweet | Hashtags: {avg_hashtag:.1f}/tweet | "
        f"Questions: {avg_question:.1f}/tweet | "
        f"Line breaks: {'yes' if uses_breaks else 'no'}"
    )

    # Topics
    if topics:
        parts.append(f"Topics/niche: {', '.join(topics[:8])}")

    # Posting frequency
    if freq > 0:
        parts.append(f"Posting frequency: ~{freq:.0f} hours between tweets")

    # Top tweets with FULL text for style reference
    if top_tweets:
        parts.append("")
        parts.append("### Top-Performing Tweets (STUDY THESE for style matching)")
        parts.append(
            "These are the author's best tweets. Analyze their structure, "
            "opening hooks, sentence rhythm, formatting, and tone — "
            "then replicate these patterns in the optimized tweet."
        )
        for i, tt in enumerate(top_tweets[:5], 1):
            # Show full text (up to 280 chars) to let Claude study the style
            tweet_text = tt["text"][:280].replace("\n", "\n   ")
            parts.append(
                f'{i}. """\n   {tweet_text}\n   """\n'
                f"   Likes: {tt['likes']} | RTs: {tt['retweets']} | "
                f"Replies: {tt['replies']} | Quotes: {tt['quotes']} | "
                f"Score: {tt['engagement_score']:.0f}"
            )

    # ── Style Matching Rules (explicit constraints) ──
    parts.append("")
    parts.append("### STYLE MATCHING RULES (MANDATORY)")
    parts.append(
        "The generated tweet MUST match the author's writing style. "
        "Specifically:"
    )

    # Tone rule
    parts.append(f"- TONE: Write in a {tone} tone. ", )
    if tone in ("professional", "analytical"):
        parts.append(
            "  Use measured, intelligent language. No slang, no hype words."
        )
    elif tone == "casual":
        parts.append(
            "  Use conversational, relaxed language. Can use informal phrasing."
        )
    elif tone == "provocative":
        parts.append(
            "  Be bold and direct. Challenge assumptions. Use punchy sentences."
        )
    elif tone == "punchy":
        parts.append(
            "  Keep sentences short and impactful. Get to the point fast."
        )
    elif tone == "humorous":
        parts.append(
            "  Use wit and humor. Can be sarcastic or playful."
        )

    # Length rule
    if avg_len > 0:
        len_min = max(int(avg_len * 0.7), 30)
        len_max = min(int(avg_len * 1.4), 280)
        parts.append(
            f"- LENGTH: Target {avg_len:.0f} characters "
            f"(acceptable range: {len_min}-{len_max}). "
            f"Do NOT write significantly shorter or longer than this."
        )

    # Line break / structure rule
    if uses_breaks and avg_lines > 1.5:
        parts.append(
            f"- STRUCTURE: Use line breaks. Author typically writes ~{avg_lines:.0f} lines. "
            "Break content into multiple lines for readability."
        )
    elif not uses_breaks or avg_lines <= 1.5:
        parts.append(
            "- STRUCTURE: Keep it as a single paragraph or minimal lines. "
            "The author does NOT use multi-line formatting."
        )

    # Emoji rule
    if avg_emoji < 0.2:
        parts.append("- EMOJIS: Do NOT use emojis. The author rarely/never uses them.")
    elif avg_emoji < 0.8:
        parts.append("- EMOJIS: Use emojis sparingly (0-1 per tweet). The author uses them occasionally.")
    else:
        parts.append(
            f"- EMOJIS: Use emojis ({avg_emoji:.0f}/tweet average). "
            "The author regularly includes them."
        )

    # Hashtag rule
    if avg_hashtag < 0.2:
        parts.append("- HASHTAGS: Do NOT use hashtags. The author rarely/never uses them.")
    elif avg_hashtag < 1.0:
        parts.append("- HASHTAGS: Use at most 1 hashtag. The author uses them sparingly.")
    else:
        parts.append(
            f"- HASHTAGS: Can use 1-2 hashtags. Author averages {avg_hashtag:.1f}/tweet."
        )

    # Question frequency
    if avg_question > 0.4:
        parts.append(
            "- QUESTIONS: The author frequently asks questions. "
            "Include a question in the tweet to match this pattern."
        )
    elif avg_question < 0.1:
        parts.append(
            "- QUESTIONS: The author rarely asks questions. "
            "Use declarative statements instead."
        )

    # Structural pattern analysis from top tweets
    if top_tweets:
        parts.append("- TWEET STRUCTURE PATTERNS from top tweets:")

        for i, tt in enumerate(top_tweets[:3], 1):
            text = tt["text"]
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            first_line = lines[0] if lines else ""

            # Detect patterns
            patterns = []

            # Hook type
            if "?" in first_line:
                patterns.append("rhetorical question hook")
            elif "ama" in first_line.lower() or "but" in first_line.lower():
                patterns.append("contrast/but hook")
            elif first_line.endswith(":"):
                patterns.append("setup-colon hook (builds anticipation)")
            elif len(first_line) < 50:
                patterns.append("short punchy opener")
            else:
                patterns.append("declarative statement hook")

            # Multi-line structure
            if len(lines) > 1:
                if any(l == "" for l in text.split("\n")):
                    patterns.append("uses blank line as pause/separator")
                if "?" in lines[-1]:
                    patterns.append("ends with a question")
                elif len(lines[-1]) < len(lines[0]):
                    patterns.append("short closing line (punchline effect)")

            # Contrast / opposition
            lower = text.lower()
            if any(w in lower for w in ["ama ", "but ", "fakat", "ancak", "however"]):
                patterns.append("uses contrast (X ama Y / X but Y)")
            if any(w in lower for w in ["herkes", "everyone", "kimse", "nobody", "no one"]):
                patterns.append("everyone/nobody framing")

            parts.append(f"  Tweet {i}: {', '.join(patterns)}")

        parts.append(
            "  REPLICATE these exact structural patterns. "
            "The new tweet should follow the same hook type, "
            "line break placement, and closing style."
        )

    # Algorithm-specific insights based on profile data
    parts.append("")
    parts.append("### Algorithm Insights for This Author")

    # OON Scorer insight
    if er_rts > 0.5:
        parts.append(
            "- OON (Out-of-Network) Scorer: This author has strong retweet engagement. "
            "Retweets/quotes are critical for reaching beyond followers — "
            "prioritize share_via_dm_score and repost_score signals."
        )
    else:
        parts.append(
            "- OON (Out-of-Network) Scorer: Retweet rate is moderate. "
            "To reach beyond followers, focus on creating quotable, "
            "shareable content that triggers repost_score and share_via_dm_score."
        )

    # Author Diversity Scorer
    if freq > 0 and freq < 2:
        parts.append(
            "- Author Diversity Scorer: HIGH RISK — This author tweets very frequently. "
            "X's diversity scorer applies exponential penalty to frequent posters "
            "to avoid timeline domination. Each tweet competes with the author's "
            "own recent tweets. Make every tweet count."
        )
    elif freq > 0 and freq < 6:
        parts.append(
            "- Author Diversity Scorer: Moderate posting frequency. "
            "Be aware that X applies diversity penalties — quality over quantity."
        )

    # Phoenix Retrieval / niche fit
    if topics:
        parts.append(
            f"- Phoenix Retrieval: Author's content clusters around [{', '.join(topics[:5])}]. "
            "Tweets that stay within this niche have better embedding similarity "
            "with the author's existing content graph, improving retrieval scores."
        )

    # Filter awareness
    if style.get("hashtag_frequency", 0) > 1.5:
        parts.append(
            "- Filter Awareness: This author uses hashtags frequently. "
            "X's filters downrank tweets with >2 hashtags. "
            "Reduce hashtag usage in optimized tweets."
        )

    # Follower size calibration
    if followers > 50_000:
        parts.append(
            "- Large account: Profile clicks are less likely (people already know this author). "
            "Focus on share/DM signals instead of profile_click_score."
        )
    elif followers < 1_000:
        parts.append(
            "- Small account: Profile clicks are a strong growth lever. "
            "Optimize for profile_click_score and follow_author_score to grow audience."
        )

    return "\n".join(parts)


def _get_system_prompt(has_profile: bool = False) -> str:
    """Get the system prompt, optionally with profile-aware instructions.

    When a user profile is available, adds instructions for Claude to
    match the author's style and leverage their engagement patterns.
    """
    if not has_profile:
        return SYSTEM_PROMPT

    profile_instructions = """

## Author-Aware Optimization

You have access to the author's profile data, engagement metrics, and top-performing tweets.
Use this information to:

1. **Match the author's voice**: Mirror their tone, emoji usage, line break style, and typical tweet length. The optimized tweet should sound like THEM, not like generic marketing copy.
2. **Reference top tweet patterns**: Study what made their top tweets successful. Apply similar structural patterns (hooks, questions, formatting) to the optimization.
3. **Niche alignment**: Stay within the author's established topics. Content that matches their existing content graph gets better Phoenix Retrieval scores.
4. **Audience calibration**: Adjust expectations based on follower count. A 500-follower account has different engagement dynamics than a 50K account.
5. **OON optimization**: For reaching beyond the author's followers, prioritize signals that trigger Out-of-Network distribution: repost_score, quote_score, share_via_dm_score.
6. **Diversity awareness**: If the author tweets frequently, each tweet must be exceptionally high-quality to overcome the Author Diversity Scorer's penalty."""

    return SYSTEM_PROMPT.rstrip() + profile_instructions + "\n"


def build_user_prompt(
    tweet: str,
    analysis: dict,
    scores: dict,
    num_variations: int = 3,
    style: str = "professional",
    topic: str | None = None,
    lang: str = "en",
    has_media: bool = False,
    thread: bool = False,
) -> str:
    """Build the user prompt with tweet analysis and scoring data."""

    # Format analysis summary
    analysis_summary = (
        f"Characters: {analysis['char_count']}/280 "
        f"({analysis['char_utilization']}% utilization)\n"
        f"Language: {lang.upper()}\n"
        f"Lines: {analysis['line_count']}\n"
        f"Has hook: {analysis['has_hook']}\n"
        f"Questions: {analysis['question_count']}\n"
        f"Hashtags: {analysis['hashtag_count']}\n"
        f"Power words: {analysis['power_word_count']} ({', '.join(analysis['power_words_found']) if analysis['power_words_found'] else 'none'})\n"
        f"Has CTA: {analysis['has_cta']}\n"
        f"Has numbers/data: {analysis['has_numbers']}\n"
        f"Has media: {has_media}\n"
        f"List format: {analysis['has_list_format']}"
    )

    # Format current scores
    score_lines = []
    for action in ACTIONS:
        val = scores.get(action, 0.0)
        label = ACTION_LABELS[action]
        weight = ACTION_WEIGHTS[action]
        neg = " (NEGATIVE)" if action in NEGATIVE_ACTIONS else ""
        score_lines.append(
            f"  {action} ({label}): {val:.0%} [weight: {weight}]{neg}"
        )
    scores_text = "\n".join(score_lines)

    # Build the output schema description
    schema_desc = _build_schema_description(num_variations, lang, thread)

    topic_context = f"\nTopic/Niche: {topic}" if topic else ""
    thread_instruction = (
        "\nOptimize as a THREAD: generate the hook tweet (first tweet) "
        "plus 2-3 follow-up tweets that maintain engagement."
    ) if thread else ""
    media_instruction = (
        "\nThis tweet WILL include media (photo/video). Optimize text to "
        "complement visuals and boost photo_expand_score / vqv_score."
    ) if has_media else ""

    return f"""## Original Tweet
"{tweet}"

## Structural Analysis
{analysis_summary}
{topic_context}

## Current Algorithm Scores (Heuristic Estimates)
{scores_text}

## Instructions
Generate exactly {num_variations} optimized variations of this tweet.
Style/Tone: {style}
Language: {lang.upper()} — write in {'Turkish' if lang == 'tr' else 'English'}
{thread_instruction}
{media_instruction}

Each variation should use a DIFFERENT optimization strategy targeting different signal combinations.

For each variation, estimate realistic scores (0.0-1.0) for ALL 19 signals based on the content you generate. Be honest — don't inflate scores unrealistically. Consider the actual content features that drive each signal.

{schema_desc}

RESPOND WITH ONLY VALID JSON. No markdown fences, no text outside JSON."""


def _build_schema_description(num_variations: int, lang: str, thread: bool) -> str:
    """Build JSON output schema description."""
    signals_obj = ", ".join(f'"{a}": <0.0-1.0>' for a in ACTIONS)

    thread_field = ""
    if thread:
        thread_field = ',\n      "thread_tweets": ["Follow-up tweet 1", "Follow-up tweet 2"]'

    return f"""## Required JSON Output Format
{{
  "variations": [
    {{
      "tweet": "<optimized tweet text, max 280 chars>",
      "strategy": "<strategy name, e.g. 'Reply Magnet', 'Share Magnet', 'Dwell Maximizer'>",
      "char_count": <integer>,
      "targeted_signals": ["<top 3-5 signals this variation targets>"],
      "scores": {{{signals_obj}}},
      "media_suggestion": "<optional media/visual suggestion>",
      "explanation": "<1-2 sentences why this ranks higher>"{thread_field}
    }}
    // ... exactly {num_variations} variations
  ],
  "analysis": "<2-3 sentence analysis of the original tweet's algorithmic weaknesses>"
}}"""


def build_preserve_style_prompt(
    tweet: str,
    analysis: dict,
    scores: dict,
    topic: str | None = None,
    lang: str = "en",
    has_media: bool = False,
    thread: bool = False,
    user_profile: dict | None = None,
) -> str:
    """Build a prompt that optimizes the tweet while preserving its original voice and structure.

    This is used for Phase 1: the user gets their own tweet back, optimized
    for the algorithm but keeping the same meaning, tone, and style.
    """
    # Format analysis summary
    analysis_summary = (
        f"Characters: {analysis['char_count']}/280 "
        f"({analysis['char_utilization']}% utilization)\n"
        f"Language: {lang.upper()}\n"
        f"Lines: {analysis['line_count']}\n"
        f"Has hook: {analysis['has_hook']}\n"
        f"Questions: {analysis['question_count']}\n"
        f"Hashtags: {analysis['hashtag_count']}\n"
        f"Power words: {analysis['power_word_count']} ({', '.join(analysis['power_words_found']) if analysis['power_words_found'] else 'none'})\n"
        f"Has CTA: {analysis['has_cta']}\n"
        f"Has numbers/data: {analysis['has_numbers']}\n"
        f"Has media: {has_media}\n"
        f"List format: {analysis['has_list_format']}"
    )

    # Format current scores
    score_lines = []
    for action in ACTIONS:
        val = scores.get(action, 0.0)
        label = ACTION_LABELS[action]
        weight = ACTION_WEIGHTS[action]
        neg = " (NEGATIVE)" if action in NEGATIVE_ACTIONS else ""
        score_lines.append(
            f"  {action} ({label}): {val:.0%} [weight: {weight}]{neg}"
        )
    scores_text = "\n".join(score_lines)

    topic_context = f"\nTopic/Niche: {topic}" if topic else ""
    thread_instruction = (
        "\nOptimize as a THREAD: generate the hook tweet (first tweet) "
        "plus 2-3 follow-up tweets that maintain engagement."
    ) if thread else ""
    media_instruction = (
        "\nThis tweet WILL include media (photo/video). Optimize text to "
        "complement visuals and boost photo_expand_score / vqv_score."
    ) if has_media else ""

    signals_obj = ", ".join(f'"{a}": <0.0-1.0>' for a in ACTIONS)

    thread_field = ""
    if thread:
        thread_field = ',\n    "thread_tweets": ["Follow-up tweet 1", "Follow-up tweet 2"]'

    profile_context = ""
    if user_profile:
        profile_context = "\n" + _build_profile_context(user_profile) + "\n"

    user_prompt = f"""## Original Tweet
"{tweet}"

## Structural Analysis
{analysis_summary}
{topic_context}
{profile_context}
## Current Algorithm Scores (Heuristic Estimates)
{scores_text}

## Instructions — PRESERVE STYLE OPTIMIZATION

Your task is to optimize this tweet for the X algorithm while PRESERVING the original tweet's:
- Voice and tone (if casual, keep casual; if formal, keep formal)
- Core message and meaning — do NOT change what the tweet is saying
- Structure and flow — keep the same narrative structure
- Author's personality — it should still sound like the same person wrote it

What you CAN change:
- Trim to fit within 280 characters if it exceeds the limit
- Improve formatting (add line breaks for readability/dwell time)
- Add a stronger hook at the beginning if the current hook is weak
- Add a question or CTA at the end to boost reply/quote signals
- Slightly reword for clarity and impact while keeping the same meaning
- Remove or reduce elements that trigger negative signals (excessive hashtags, etc.)

Language: {lang.upper()} — write in {'Turkish' if lang == 'tr' else 'English'}
{thread_instruction}
{media_instruction}

Generate EXACTLY 1 optimized version that maximizes the algorithm score while staying true to the original tweet.

Estimate realistic scores (0.0-1.0) for ALL 19 signals. Be honest — don't inflate scores.

## Required JSON Output Format
{{
  "variations": [
    {{
      "tweet": "<optimized tweet text, max 280 chars>",
      "strategy": "Preserve Style Optimization",
      "char_count": <integer>,
      "targeted_signals": ["<top 3-5 signals this targets>"],
      "scores": {{{signals_obj}}},
      "media_suggestion": "<optional media/visual suggestion>",
      "explanation": "<1-2 sentences explaining what was changed and why>"{thread_field}
    }}
  ],
  "analysis": "<2-3 sentence analysis of the original tweet's algorithmic weaknesses>"
}}

RESPOND WITH ONLY VALID JSON. No markdown fences, no text outside JSON."""

    system = _get_system_prompt(has_profile=user_profile is not None)
    return f"""{system}

---

{user_prompt}"""


def build_refine_prompt(
    original_tweet: str,
    current_tweet: str,
    user_feedback: str,
    lang: str = "en",
    has_media: bool = False,
    thread: bool = False,
    user_profile: dict | None = None,
) -> str:
    """Build a prompt to refine an already-optimized tweet based on user feedback.

    The user has seen the AI's optimization and wants specific changes.
    Claude gets the original tweet, the current optimized version,
    and the user's instructions for what to change.
    """
    signals_obj = ", ".join(f'"{a}": <0.0-1.0>' for a in ACTIONS)

    thread_field = ""
    if thread:
        thread_field = ',\n    "thread_tweets": ["Follow-up tweet 1", "Follow-up tweet 2"]'

    media_instruction = (
        "\nThis tweet WILL include media (photo/video). Keep text complementary to visuals."
    ) if has_media else ""

    profile_context = ""
    if user_profile:
        profile_context = "\n" + _build_profile_context(user_profile) + "\n"

    user_prompt = f"""## Original Tweet (user's first input)
"{original_tweet}"

## Current Optimized Version
"{current_tweet}"
{profile_context}
## User's Feedback
The user wants the following changes applied to the CURRENT optimized version:
"{user_feedback}"

## Instructions — REFINE BASED ON FEEDBACK

Apply the user's requested changes to the current optimized version.

Rules:
- Follow the user's feedback as closely as possible
- Keep the tweet within 280 characters
- Maintain algorithm optimization where possible, but USER'S WISHES take priority
- If the user asks to keep something, do NOT remove it
- If the user asks to change tone/style, follow that direction
- Language: {lang.upper()} — write in {'Turkish' if lang == 'tr' else 'English'}
{media_instruction}

Generate EXACTLY 1 refined version.

Estimate realistic scores (0.0-1.0) for ALL 19 signals. Be honest — don't inflate scores.

## Required JSON Output Format
{{
  "variations": [
    {{
      "tweet": "<refined tweet text, max 280 chars>",
      "strategy": "User Refinement",
      "char_count": <integer>,
      "targeted_signals": ["<top 3-5 signals this targets>"],
      "scores": {{{signals_obj}}},
      "media_suggestion": "<optional media/visual suggestion>",
      "explanation": "<1-2 sentences explaining what was changed based on user feedback>"{thread_field}
    }}
  ],
  "analysis": "<1-2 sentence note on how the changes affect algorithm performance>"
}}

RESPOND WITH ONLY VALID JSON. No markdown fences, no text outside JSON."""

    system = _get_system_prompt(has_profile=user_profile is not None)
    return f"""{system}

---

{user_prompt}"""


def build_full_prompt(
    tweet: str,
    analysis: dict,
    scores: dict,
    num_variations: int = 3,
    style: str = "professional",
    topic: str | None = None,
    lang: str = "en",
    has_media: bool = False,
    thread: bool = False,
    user_profile: dict | None = None,
) -> str:
    """Build complete prompt combining system + user prompts.

    Since we call `claude -p`, the system prompt is embedded in the
    single prompt string rather than sent separately.
    """
    user_prompt = build_user_prompt(
        tweet=tweet,
        analysis=analysis,
        scores=scores,
        num_variations=num_variations,
        style=style,
        topic=topic,
        lang=lang,
        has_media=has_media,
        thread=thread,
    )

    # Inject profile context between analysis and instructions
    if user_profile:
        profile_section = "\n" + _build_profile_context(user_profile) + "\n"
        # Add explicit style mandate in instructions
        style_mandate = (
            f"\n\nCRITICAL: Author profile is available above. "
            f"All variations MUST match @{user_profile.get('username', 'user')}'s "
            f"writing style. Follow the STYLE MATCHING RULES in the profile section. "
            f"Each variation should sound like the author wrote it."
        )
        user_prompt = user_prompt.replace(
            "\n## Current Algorithm Scores",
            f"{profile_section}\n## Current Algorithm Scores",
        )
        user_prompt = user_prompt.replace(
            "\nRESPOND WITH ONLY VALID JSON.",
            f"{style_mandate}\n\nRESPOND WITH ONLY VALID JSON.",
        )

    system = _get_system_prompt(has_profile=user_profile is not None)
    return f"""{system}

---

{user_prompt}"""


def build_discovery_tweet_prompt(
    trending_topic: dict,
    angle: str,
    angle_instruction: str,
    user_profile: dict | None = None,
    lang: str = "en",
    has_media: bool = False,
    thread: bool = False,
) -> str:
    """Build a prompt to generate an optimized tweet about a trending topic.

    Used by the discovery flow: user picked a trending topic and an angle,
    now Claude generates a tweet in the user's style about that topic.

    Args:
        trending_topic: dict with name, context, popular_take, contrarian_angle.
        angle: one of 'dominant', 'contrarian', 'personal', or custom text.
        angle_instruction: detailed instruction for the chosen angle.
        user_profile: optional user profile for style matching.
        lang: language code.
        has_media: whether tweet will include media.
        thread: whether to generate thread format.
    """
    signals_obj = ", ".join(f'"{a}": <0.0-1.0>' for a in ACTIONS)

    thread_field = ""
    if thread:
        thread_field = ',\n    "thread_tweets": ["Follow-up tweet 1", "Follow-up tweet 2"]'

    thread_instruction = (
        "\nGenerate as a THREAD: hook tweet (first tweet) "
        "plus 2-3 follow-up tweets that maintain engagement."
    ) if thread else ""
    media_instruction = (
        "\nThis tweet WILL include media (photo/video). Optimize text to "
        "complement visuals and boost photo_expand_score / vqv_score."
    ) if has_media else ""

    # Build topic context
    topic_name = trending_topic.get("name", "")
    topic_context = trending_topic.get("context", "")
    popular_take = trending_topic.get("popular_take", "")
    contrarian = trending_topic.get("contrarian_angle", "")

    topic_section = f'## Trending Topic\nTopic: {topic_name}'
    if topic_context:
        topic_section += f'\nContext: {topic_context}'
    if popular_take:
        topic_section += f'\nPopular opinion on X: {popular_take}'
    if contrarian:
        topic_section += f'\nContrarian angle: {contrarian}'

    # Build profile context
    profile_context = ""
    style_mandate = ""
    if user_profile:
        profile_context = "\n" + _build_profile_context(user_profile) + "\n"
        style_mandate = (
            "\n### CRITICAL: Author Style Matching\n"
            "You MUST write this tweet as if the author (@"
            f"{user_profile.get('username', 'user')}) wrote it themselves.\n"
            "- Study the top-performing tweets in the profile above\n"
            "- Replicate the author's sentence structure, rhythm, and vocabulary\n"
            "- Follow ALL style matching rules listed in the profile section "
            "(tone, length, emojis, hashtags, line breaks, hook pattern)\n"
            "- The tweet should be INDISTINGUISHABLE from the author's own writing\n"
            "- If you are unsure about the style, lean toward the patterns "
            "visible in the top tweets\n"
        )

    lang_name = 'Turkish' if lang == 'tr' else 'English'

    user_prompt = f"""{topic_section}
{profile_context}
## Instructions — TRENDING TOPIC TWEET CREATION

Create an original, high-quality tweet about the trending topic above.

### Angle
{angle_instruction}
{style_mandate}
### Rules
- Write in {lang_name} ({lang.upper()})
- Maximum 280 characters
- The tweet must be about the specific trending topic, not generic
- Apply all X algorithm optimization knowledge to maximize engagement signals
- Avoid excessive hashtags (max 1-2), avoid engagement bait
- Make it sound natural and authentic, not like AI-generated marketing copy
{thread_instruction}
{media_instruction}

Generate EXACTLY 1 optimized tweet.

Estimate realistic scores (0.0-1.0) for ALL 19 signals. Be honest.

## Required JSON Output Format
{{
  "variations": [
    {{
      "tweet": "<tweet text, max 280 chars>",
      "strategy": "Trending Topic — {angle.title()}",
      "char_count": <integer>,
      "targeted_signals": ["<top 3-5 signals this targets>"],
      "scores": {{{signals_obj}}},
      "media_suggestion": "<optional media/visual suggestion>",
      "explanation": "<1-2 sentences on why this tweet will perform well>"{thread_field}
    }}
  ],
  "analysis": "<1-2 sentence note on the angle chosen and engagement potential>"
}}

RESPOND WITH ONLY VALID JSON. No markdown fences, no text outside JSON."""

    system = _get_system_prompt(has_profile=user_profile is not None)
    return f"""{system}

---

{user_prompt}"""

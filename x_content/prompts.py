"""Claude prompt templates for tweet optimization.

MOST CRITICAL FILE - encodes the full X algorithm knowledge into prompts
sent to Claude Code CLI via subprocess.
"""

import json

from x_content.algorithm import (
    ACTIONS, ACTION_LABELS, ACTION_WEIGHTS, NEGATIVE_ACTIONS, SIGNAL_MAP,
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
3. Offset: negative combined scores are multiplied by 2x (harsher penalty)
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

    return f"""{SYSTEM_PROMPT}

---

{user_prompt}"""

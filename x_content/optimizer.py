"""Claude Code CLI integration.

Calls `claude -p` as subprocess to generate optimized tweet variations.
Parses JSON response and validates output.
"""

import json
import subprocess
import sys

from x_content.algorithm import ACTIONS
from x_content.analyzer import analyze
from x_content.prompts import build_full_prompt, build_preserve_style_prompt, build_refine_prompt
from x_content.scorer import score_tweet, comparison_report
from x_content import config


class OptimizationError(Exception):
    pass


def call_claude(prompt: str, timeout: int | None = None) -> str:
    """Call Claude Code CLI and return the response text.

    Uses: claude -p "<prompt>" --output-format json
    """
    if timeout is None:
        timeout = config.get("claude", {}).get("timeout", 120)

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise OptimizationError(
            "Claude Code CLI not found. Install it: https://docs.anthropic.com/en/docs/claude-code"
        )
    except subprocess.TimeoutExpired:
        raise OptimizationError(
            f"Claude Code CLI timed out after {timeout}s. "
            "Try again or increase timeout in config.yaml."
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise OptimizationError(f"Claude Code CLI error (exit {result.returncode}): {stderr}")

    if not result.stdout.strip():
        raise OptimizationError("Claude Code CLI returned empty response.")

    # Parse the CLI JSON wrapper
    try:
        cli_response = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise OptimizationError(
            f"Failed to parse CLI JSON response: {result.stdout[:200]}"
        )

    # Extract the text content from CLI response
    text = cli_response.get("result", "")
    if not text:
        raise OptimizationError("CLI response has no 'result' field.")

    return text


def parse_response(text: str) -> dict:
    """Parse Claude's response text as JSON.

    Handles potential markdown code fences or extra whitespace.
    """
    cleaned = text.strip()

    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json) and last line (```)
        start = 1
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        cleaned = "\n".join(lines[start:end])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise OptimizationError(f"Failed to parse Claude's response as JSON: {e}")


def validate_variation(variation: dict, max_chars: int = 280) -> list[str]:
    """Validate a single variation and return list of warnings."""
    warnings = []

    tweet = variation.get("tweet", "")
    if not tweet:
        warnings.append("Missing tweet text")
    elif len(tweet) > max_chars:
        warnings.append(f"Tweet exceeds {max_chars} chars: {len(tweet)}")

    scores = variation.get("scores", {})
    missing = [a for a in ACTIONS if a not in scores]
    if missing:
        warnings.append(f"Missing scores: {', '.join(missing)}")

    for action, val in scores.items():
        if not isinstance(val, (int, float)):
            warnings.append(f"Non-numeric score for {action}: {val}")
        elif not 0.0 <= val <= 1.0:
            warnings.append(f"Score out of range for {action}: {val}")

    return warnings


def optimize(
    tweet: str,
    topic: str | None = None,
    lang: str = "auto",
    variations: int = 3,
    style: str = "professional",
    has_media: bool = False,
    thread: bool = False,
) -> dict:
    """Run the full optimization pipeline.

    1. Analyze original tweet structure
    2. Score original tweet heuristically
    3. Build prompt with analysis + scores
    4. Call Claude Code CLI
    5. Parse and validate response
    6. Score each optimized variation for comparison

    Returns dict with: original, variations, analysis, comparisons.
    """
    # Step 1: Analyze original
    analysis = analyze(tweet, has_media=has_media)

    # Resolve language
    if lang == "auto":
        lang = analysis["lang"]

    # Step 2: Score original
    original_scores = score_tweet(analysis)

    # Step 3: Build prompt
    prompt = build_full_prompt(
        tweet=tweet,
        analysis=analysis,
        scores=original_scores,
        num_variations=variations,
        style=style,
        topic=topic,
        lang=lang,
        has_media=has_media,
        thread=thread,
    )

    # Step 4: Call Claude
    raw_response = call_claude(prompt)

    # Step 5: Parse and validate
    data = parse_response(raw_response)

    if "variations" not in data:
        raise OptimizationError("Response missing 'variations' key.")

    max_chars = config.get("optimization", {}).get("max_chars", 280)

    for i, var in enumerate(data["variations"]):
        warnings = validate_variation(var, max_chars)
        if warnings:
            print(f"  Warning (variation {i+1}): {'; '.join(warnings)}",
                  file=sys.stderr)
        # Fill in missing scores with 0.0
        if "scores" in var:
            for action in ACTIONS:
                var["scores"].setdefault(action, 0.0)

    # Step 6: Generate comparison reports
    comparisons = []
    for var in data["variations"]:
        if "scores" in var:
            comp = comparison_report(analysis, var["scores"], has_media=has_media)
            comparisons.append(comp)
        else:
            comparisons.append(None)

    # Build original report
    from x_content.scorer import full_score_report
    original_report = full_score_report(analysis, has_media=has_media)

    return {
        "tweet": tweet,
        "analysis": analysis,
        "original_report": original_report,
        "variations": data["variations"],
        "comparisons": comparisons,
        "claude_analysis": data.get("analysis", ""),
        "lang": lang,
    }


def optimize_preserve_style(
    tweet: str,
    topic: str | None = None,
    lang: str = "auto",
    has_media: bool = False,
    thread: bool = False,
) -> dict:
    """Run Phase 1: optimize while preserving original style/voice.

    Returns dict with: tweet, analysis, original_report,
    optimized (single variation), comparison, claude_analysis, lang.
    """
    # Step 1: Analyze original
    analysis = analyze(tweet, has_media=has_media)

    # Resolve language
    if lang == "auto":
        lang = analysis["lang"]

    # Step 2: Score original
    original_scores = score_tweet(analysis)

    # Step 3: Build preserve-style prompt
    prompt = build_preserve_style_prompt(
        tweet=tweet,
        analysis=analysis,
        scores=original_scores,
        topic=topic,
        lang=lang,
        has_media=has_media,
        thread=thread,
    )

    # Step 4: Call Claude
    raw_response = call_claude(prompt)

    # Step 5: Parse and validate
    data = parse_response(raw_response)

    if "variations" not in data or not data["variations"]:
        raise OptimizationError("Response missing 'variations' key.")

    max_chars = config.get("optimization", {}).get("max_chars", 280)
    var = data["variations"][0]

    warnings = validate_variation(var, max_chars)
    if warnings:
        print(f"  Warning: {'; '.join(warnings)}", file=sys.stderr)
    if "scores" in var:
        for action in ACTIONS:
            var["scores"].setdefault(action, 0.0)

    # Step 6: Generate comparison
    comp = None
    if "scores" in var:
        comp = comparison_report(analysis, var["scores"], has_media=has_media)

    from x_content.scorer import full_score_report
    original_report = full_score_report(analysis, has_media=has_media)

    return {
        "tweet": tweet,
        "analysis": analysis,
        "original_report": original_report,
        "optimized": var,
        "comparison": comp,
        "claude_analysis": data.get("analysis", ""),
        "lang": lang,
    }


def refine_tweet(
    original_tweet: str,
    current_tweet: str,
    user_feedback: str,
    lang: str = "auto",
    has_media: bool = False,
    thread: bool = False,
) -> dict:
    """Refine an optimized tweet based on user feedback.

    Takes the original tweet, current optimized version, and user's
    instructions for changes. Returns a new optimized version.
    """
    # Detect language from original if auto
    if lang == "auto":
        from x_content.analyzer import analyze as _analyze
        lang = _analyze(original_tweet, has_media=has_media)["lang"]

    # Build refine prompt
    prompt = build_refine_prompt(
        original_tweet=original_tweet,
        current_tweet=current_tweet,
        user_feedback=user_feedback,
        lang=lang,
        has_media=has_media,
        thread=thread,
    )

    # Call Claude
    raw_response = call_claude(prompt)

    # Parse and validate
    data = parse_response(raw_response)

    if "variations" not in data or not data["variations"]:
        raise OptimizationError("Response missing 'variations' key.")

    max_chars = config.get("optimization", {}).get("max_chars", 280)
    var = data["variations"][0]

    warnings = validate_variation(var, max_chars)
    if warnings:
        print(f"  Warning: {'; '.join(warnings)}", file=sys.stderr)
    if "scores" in var:
        for action in ACTIONS:
            var["scores"].setdefault(action, 0.0)

    # Generate comparison against original
    original_analysis = analyze(original_tweet, has_media=has_media)
    comp = None
    if "scores" in var:
        comp = comparison_report(original_analysis, var["scores"], has_media=has_media)

    from x_content.scorer import full_score_report
    original_report = full_score_report(original_analysis, has_media=has_media)

    return {
        "tweet": original_tweet,
        "analysis": original_analysis,
        "original_report": original_report,
        "optimized": var,
        "comparison": comp,
        "claude_analysis": data.get("analysis", ""),
        "lang": lang,
    }

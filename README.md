# X Algorithm Tweet Optimizer

A CLI tool that transforms any tweet into an algorithm-optimized viral tweet. Uses X's open-sourced "For You" feed algorithm (Phoenix model) to analyze and maximize the 19 engagement signals that determine tweet ranking.

## How It Works

X's recommendation algorithm predicts **19 engagement action probabilities** for each tweet and ranks them by weighted sum:

```
Final Score = Σ (weight_i × P(action_i))
```

This tool runs a **two-phase interactive flow**:

1. **Analyzes** your tweet's structural features (hooks, questions, hashtags, power words, etc.)
2. **Scores** it across all 19 algorithm dimensions using heuristic estimation
3. **Optimizes** the tweet while preserving your original voice and style
4. **Lets you refine** — chat with the AI to request specific changes
5. **Optionally generates** different style variations targeting different signal combinations
6. **Copies** the final tweet to your clipboard with one keypress

### The 19 Signals (and What Matters Most)

| Signal | Weight | What Drives It |
|--------|--------|---------------|
| `share_via_dm_score` | **100.0** | Content people DM to friends |
| `quote_score` | **40.0** | Hot takes that invite commentary |
| `reply_score` | **27.0** | Questions and debate triggers |
| `repost_score` | **10.0** | Quotable insights, universal truths |
| `follow_author_score` | **10.0** | Demonstrated expertise |
| `report_score` | **-9209.0** | Policy violations (avoid!) |
| `block_author_score` | **-371.0** | Offensive content (avoid!) |

A single DM share is worth **100 Likes**. A single report wipes out everything.

## Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- `pyyaml`

## Setup

```bash
pip install pyyaml
```

## Usage

```bash
# Basic optimization (interactive mode)
python optimize.py "AI will replace 80% of jobs in 5 years"

# Turkish tweet
python optimize.py "Yapay zeka işlerin %80'ini alacak" --lang tr

# With topic context
python optimize.py "AI will replace 80% of jobs" --topic "AI"

# Casual style for Phase 2 variations
python optimize.py "AI will replace 80% of jobs" --style casual

# From file, thread format
python optimize.py --file draft.txt --thread

# Tweet with media
python optimize.py "Check out this chart" --media --topic "data science"

# Non-interactive mode (legacy, shows all variations at once)
python optimize.py "AI will replace 80% of jobs" --no-interactive --variations 5

# JSON output for programmatic use
python optimize.py "Test tweet" --json
```

## Interactive Flow

By default, the tool runs interactively:

### Phase 1 — Same-Style Optimization

Your tweet is optimized while keeping your original voice, structure, and meaning:

```
  ╔══════════════════════════════════════════════════════════════╗
  ║  X ALGORITHM TWEET OPTIMIZER                                ║
  ╚══════════════════════════════════════════════════════════════╝

  ── ORIGINAL TWEET ────────────────────────────────────────────────

    AI will replace 80% of jobs in 5 years

  Characters: 38/280  │  Lang: EN  │  Score: 20%

  ── OPTIMIZED TWEET  20% → 35% (+15pts) ──────────────────────────

    AI will replace 80% of jobs in 5 years.

    But not the ones you think.

    The question isn't IF — it's which tasks disappear first.

  Characters: 112/280

  What would you like to do?
    [1] Copy optimized tweet to clipboard
    [2] Refine with AI (request changes)
    [3] Generate different style variations
    [4] Copy original tweet to clipboard
    [5] Exit
```

### Refine with AI

Select `[2]` to chat with the AI and request changes. You can iterate as many times as you want:

```
  What would you like to change?
  (Type your instructions, e.g. 'make it shorter', 'keep the URL', 'add humor')

  > add a question at the end to trigger replies

  Refining tweet...

  ── OPTIMIZED TWEET  20% → 42% (+22pts) ──────────────────────────

    AI will replace 80% of jobs in 5 years.

    But not the ones you think.

    The question isn't IF — it's which tasks disappear first.

    What job do you think goes first?

  Characters: 147/280
```

After each refinement, you return to the menu and can refine again, copy, or generate variations.

### Phase 2 — Style Variations

Select `[3]` to generate multiple variations with different strategies (Reply Magnet, DM Share Magnet, Quote Trigger, etc.), then pick one to copy.

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `tweet` | Tweet text (positional) | - |
| `--topic` | Topic/niche context | None |
| `--lang` | Language: `en`, `tr`, `auto` | `auto` |
| `--variations` | Number of style variations (Phase 2) | `3` |
| `--style` | Tone: `professional`, `casual`, `provocative`, `educational` | `professional` |
| `--media` | Tweet will include photo/video | `false` |
| `--thread` | Optimize for thread format | `false` |
| `--file` | Read tweet from file | None |
| `--json` | Output as JSON (non-interactive) | `false` |
| `--verbose` | Show all 19 signals in detail | `false` |
| `--no-interactive` | Skip interactive prompts, show all variations directly | `false` |

## Configuration

Edit `config.yaml` to customize:

- **Category weights** — adjust how Engagement, Discoverability, Shareability, Content Quality, and Safety contribute to the overall score
- **Display settings** — bar width, number of signals shown, show all vs top-N
- **Claude timeout** — increase for complex prompts

## Project Structure

```
x_content/
├── optimize.py          # CLI entry point (interactive flow)
├── config.yaml          # Settings
├── pyproject.toml       # Dependencies
└── x_content/
    ├── algorithm.py     # 19 actions, weights, signal map
    ├── analyzer.py      # Structural tweet feature extraction
    ├── scorer.py        # Heuristic scoring + comparison metrics
    ├── prompts.py       # Claude prompt templates (preserve-style, refine, variations)
    ├── optimizer.py     # Claude Code CLI subprocess integration
    ├── display.py       # Terminal output formatting (ANSI colors, dynamic width)
    └── config.py        # YAML config loader
```

## Algorithm Source

Based on X's open-sourced recommendation algorithm:
- `phoenix/runners.py` — 19 action definitions and ranking logic
- Scoring uses `jax.nn.sigmoid(logits)` to produce per-action probabilities
- Primary ranking by `favorite_score`, final ranking by weighted combination

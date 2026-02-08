# X Algorithm Tweet Optimizer

A CLI tool that transforms any tweet into an algorithm-optimized viral tweet. Uses X's open-sourced "For You" feed algorithm (Phoenix model) to analyze and maximize the 19 engagement signals that determine tweet ranking.

## How It Works

X's recommendation algorithm predicts **19 engagement action probabilities** for each tweet and ranks them by weighted sum:

```
Final Score = Σ (weight_i × P(action_i))
```

This tool:

1. **Analyzes** your tweet's structural features (hooks, questions, hashtags, power words, etc.)
2. **Scores** it across all 19 algorithm dimensions using heuristic estimation
3. **Sends** the analysis to Claude, which generates optimized variations targeting specific signal combinations
4. **Compares** original vs. optimized scores across 5 categories and 19 individual signals

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
# Basic optimization
python optimize.py "AI will replace 80% of jobs in 5 years"

# With topic context and more variations
python optimize.py "AI will replace 80% of jobs" --topic "AI" --variations 5

# Provocative style with verbose analysis
python optimize.py "AI will replace 80% of jobs" --style provocative --verbose

# Turkish tweet
python optimize.py "Yapay zeka işlerin %80'ini alacak" --lang tr

# From file, thread format
python optimize.py --file draft.txt --thread

# JSON output for programmatic use
python optimize.py "Test tweet" --json

# Tweet with media
python optimize.py "Check out this chart" --media --topic "data science"
```

### CLI Options

| Flag | Description | Default |
|------|-------------|---------|
| `tweet` | Tweet text (positional) | - |
| `--topic` | Topic/niche context | None |
| `--lang` | Language: `en`, `tr`, `auto` | `auto` |
| `--variations` | Number of optimized versions | `3` |
| `--style` | Tone: `professional`, `casual`, `provocative`, `educational` | `professional` |
| `--media` | Tweet will include photo/video | `false` |
| `--thread` | Optimize for thread format | `false` |
| `--file` | Read tweet from file | None |
| `--json` | Output as JSON | `false` |
| `--verbose` | Show all 19 signals in detail | `false` |

## Output

The tool displays a comparative analysis:

```
╔══════════════════════════════════════════════════════════════════╗
║  X ALGORITHM TWEET OPTIMIZER                                    ║
╠══════════════════════════════════════════════════════════════════╣
║  Original Tweet                                                 ║
║  "AI will replace 80% of jobs in 5 years"                       ║
║  Characters: 38/280 | Lang: EN | Algorithm Score: 20%           ║
╠══════════════════════════════════════════════════════════════════╣
║  Variation 1: "Reply Magnet"                                    ║
║  Algorithm Compatibility: 60% (+40pts)                          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  Unpopular opinion: AI won't replace 80% of jobs.              ║
║                                                                 ║
║  It'll replace 80% of TASKS within those jobs.                  ║
║                                                                 ║
║  The people who understand the difference will thrive.          ║
║  Which side are you on?                                         ║
║                                                                 ║
║  Signal Changes:                                                ║
║  favorite_score       20% → 72%   +260.0%   ▲▲▲                ║
║  reply_score          10% → 85%   +750.0%   ▲▲▲▲               ║
║  share_via_dm_score   13% → 45%   +246.2%   ▲▲▲                ║
║  not_interested       20% →  5%   -75.0%    ▼▼ (improved)      ║
║                                                                 ║
║  Category Compatibility:                                        ║
║  Engagement         █████████████████░░░░░░░  74%  (+56pts)    ║
║  Discoverability    █████████████░░░░░░░░░░░  55%  (+42pts)    ║
║  Shareability       ███████████░░░░░░░░░░░░░  48%  (+32pts)    ║
║  Content Quality    ██████████░░░░░░░░░░░░░░  42%  (+27pts)    ║
║  Safety             ███████████████████████░  97%  (+5pts)     ║
╚══════════════════════════════════════════════════════════════════╝
```

## Configuration

Edit `config.yaml` to customize:

- **Category weights** — adjust how Engagement, Discoverability, Shareability, Content Quality, and Safety contribute to the overall score
- **Display settings** — bar width, number of signals shown, show all vs top-N
- **Claude timeout** — increase for complex prompts

## Project Structure

```
x_content/
├── optimize.py          # CLI entry point
├── config.yaml          # Settings
├── pyproject.toml       # Dependencies
└── x_content/
    ├── algorithm.py     # 19 actions, weights, signal map
    ├── analyzer.py      # Structural tweet feature extraction
    ├── scorer.py        # Heuristic scoring + comparison metrics
    ├── prompts.py       # Claude prompt templates (algorithm-encoded)
    ├── optimizer.py     # Claude Code CLI subprocess integration
    ├── display.py       # Terminal output formatting
    └── config.py        # YAML config loader
```

## Algorithm Source

Based on X's open-sourced recommendation algorithm:
- `phoenix/runners.py` — 19 action definitions and ranking logic
- Scoring uses `jax.nn.sigmoid(logits)` to produce per-action probabilities
- Primary ranking by `favorite_score`, final ranking by weighted combination

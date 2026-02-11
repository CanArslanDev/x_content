# X Content Project Overview

## Purpose
CLI tool that optimizes tweets for X's "For You" feed ranking algorithm using Claude Code CLI as backend.

## Tech Stack
- Python 3.12+ (type hints, no external deps except PyYAML)
- Claude Code CLI (`claude -p` subprocess)
- YAML config

## Entry Point
- `python optimize.py "tweet text"` — interactive two-phase optimization

## Project Structure
- `optimize.py` — CLI entry point
- `x_content/algorithm.py` — X algorithm knowledge base (19 signals, weights, scoring)
- `x_content/scorer.py` — Heuristic signal scorer
- `x_content/analyzer.py` — Structural tweet feature extraction
- `x_content/optimizer.py` — Claude Code CLI integration pipeline
- `x_content/prompts.py` — Prompt templates
- `x_content/display.py` — Terminal UI with ANSI colors
- `x_content/config.py` — YAML config loader
- `config.yaml` — Configuration
- `x-algorithm/` — Reference X algorithm source code (Rust + Python)

## Key Architecture
- Two-phase: Phase 1 preserves style, Phase 2 generates variations
- Scoring pipeline: signals → weighted sum → offset → (normalize)
- 19 engagement signals from Phoenix model
- Weights are community estimates (real values excluded from x-algorithm open source)

## Code Style
- Google-style docstrings
- Type hints on all function signatures
- No external dependencies except PyYAML
- ANSI colors for terminal output (no rich/blessed)

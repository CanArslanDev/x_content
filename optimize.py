#!/usr/bin/env python3
"""X Algorithm Tweet Optimizer - CLI Entry Point.

Usage:
  python optimize.py "Tweet text here"
  python optimize.py "Tweet text" --topic "AI" --variations 5 --style provocative
  python optimize.py --file draft.txt --lang tr --thread
"""

import argparse
import sys

from x_content.optimizer import optimize, OptimizationError
from x_content.display import render_full, render_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Optimize tweets for maximum X algorithm reach",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python optimize.py "AI will replace 80%% of jobs"\n'
            '  python optimize.py "Test tweet" --topic "AI" --variations 5\n'
            '  python optimize.py --file draft.txt --lang tr --thread\n'
        ),
    )

    parser.add_argument(
        "tweet",
        nargs="?",
        help="Tweet text to optimize",
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
        help="Number of optimized variations (default: 3)",
    )
    parser.add_argument(
        "--style",
        choices=["professional", "casual", "provocative", "educational"],
        default="professional",
        help="Tone style (default: professional)",
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
        help="Output as JSON",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed algorithm analysis",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Get tweet text
    tweet = args.tweet
    if args.file:
        try:
            with open(args.file) as f:
                tweet = f.read().strip()
        except FileNotFoundError:
            print(f"Error: File not found: {args.file}", file=sys.stderr)
            sys.exit(1)

    if not tweet:
        parser.print_help()
        sys.exit(1)

    # Run optimization
    try:
        result = optimize(
            tweet=tweet,
            topic=args.topic,
            lang=args.lang,
            variations=args.variations,
            style=args.style,
            has_media=args.media,
            thread=args.thread,
        )
    except OptimizationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.json_output:
        print(render_json(result))
    else:
        print(render_full(result, verbose=args.verbose))


if __name__ == "__main__":
    main()

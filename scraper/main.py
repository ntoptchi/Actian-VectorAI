"""
CLI entrypoint for the nextup crash<->news linker.

Examples:
  python main.py candidates
  python main.py link --tier fatal --limit 20
  python main.py link
  python main.py link --threshold 60 --workers 10
  python main.py link --dry-run --limit 5
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def cmd_candidates(args: argparse.Namespace) -> int:
    from candidates import build_candidates
    out = build_candidates()
    print(f"wrote {out['count']} candidates")
    print(f"  tiers: fatal={out['stats']['fatal']} serious={out['stats']['serious']} "
          f"vulnerable={out['stats']['vulnerable']} wrongway={out['stats']['wrongway']}")
    return 0


def cmd_link(args: argparse.Namespace) -> int:
    from linker import run
    stats = run(
        limit=args.limit,
        tier=args.tier,
        threshold=args.threshold,
        workers=args.workers,
        dry_run=args.dry_run,
    )
    print(
        f"processed={stats['processed']} linked={stats['linked']} "
        f"unmatched={stats['unmatched']} errors={stats.get('errors', 0)}"
    )
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    from enrich import run

    stats = run(
        limit=args.limit,
        min_score=args.min_score,
        workers=args.workers,
        model=args.model,
        retry_failed=args.retry_failed,
        dry_run=args.dry_run,
    )
    print(
        f"processed={stats['processed']} enriched={stats['enriched']} "
        f"failed={stats['failed']} skipped_low_confidence={stats['skipped_low_confidence']} "
        f"already_done={stats['already_done']}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv(os.path.join(HERE, ".env"))

    parser = argparse.ArgumentParser(prog="nextup", description="Crash <-> news article linker")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cand = sub.add_parser("candidates", help="build the filtered candidates.json from data/raw")
    p_cand.set_defaults(func=cmd_candidates)

    p_link = sub.add_parser("link", help="run the Brave+scraper linker over candidates")
    p_link.add_argument("--limit", type=int, default=None, help="process at most N crashes")
    p_link.add_argument(
        "--tier",
        choices=["all", "fatal", "serious", "vulnerable", "wrongway"],
        default="all",
    )
    p_link.add_argument("--threshold", type=int, default=55, help="match score threshold (0-100)")
    p_link.add_argument("--workers", type=int, default=20, help="parallel article-fetch workers")
    p_link.add_argument("--dry-run", action="store_true", help="don't write output files")
    p_link.set_defaults(func=cmd_link)

    p_enrich = sub.add_parser("enrich", help="run OpenAI structured-output enrichment")
    p_enrich.add_argument("--limit", type=int, default=None, help="process at most N articles")
    p_enrich.add_argument("--min-score", type=int, default=None, help="optional matchScore floor")
    p_enrich.add_argument("--workers", type=int, default=10, help="parallel OpenAI worker count")
    p_enrich.add_argument("--model", type=str, default=None, help="OpenAI model override")
    p_enrich.add_argument("--retry-failed", action="store_true", help="retry entries with enrichment.error")
    p_enrich.add_argument("--dry-run", action="store_true", help="preview enrichment calls, write nothing")
    p_enrich.set_defaults(func=cmd_enrich)

    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

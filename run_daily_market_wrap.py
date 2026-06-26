from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import subprocess
import sys


UTC = dt.timezone.utc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-date")
    parser.add_argument("--market", choices=["all", "us", "europe"], default="all")
    parser.add_argument(
        "--output-dir",
        default=str(pathlib.Path(__file__).resolve().parent / "output"),
    )
    return parser.parse_args()


def resolve_target_date(raw: str | None) -> str:
    if raw:
        return dt.date.fromisoformat(raw).isoformat()
    return dt.datetime.now(UTC).date().isoformat()


def run_step(command: list[str]) -> None:
    subprocess.run(command, check=True)


def main() -> None:
    args = parse_args()
    target_date = resolve_target_date(args.target_date)
    root = pathlib.Path(__file__).resolve().parent

    print(f"Generating market wrap for {target_date}")
    run_step(
        [
            sys.executable,
            str(root / "generate_market_wrap_yahoo.py"),
            "--market",
            args.market,
            "--output-dir",
            args.output_dir,
            "--as-of-date",
            target_date,
        ]
    )
    run_step(
        [
            sys.executable,
            str(root / "generate_market_news_context.py"),
            "--market",
            args.market,
            "--output-dir",
            args.output_dir,
        ]
    )
    run_step(
        [
            sys.executable,
            str(root / "generate_market_commentary.py"),
            "--market",
            args.market,
            "--output-dir",
            args.output_dir,
        ]
    )


if __name__ == "__main__":
    main()

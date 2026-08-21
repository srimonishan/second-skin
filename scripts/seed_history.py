#!/usr/bin/env python3
"""
Backfill a few days of history so the gallery isn't empty at demo time.
Runs the same synchronous Step Functions execution as invoke_pipeline.sh,
once per backdated date.

Usage:
    python3 scripts/seed_history.py                # backfills the last 3 days (not including today)
    python3 scripts/seed_history.py --days 5
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone


def state_machine_arn(stack_name: str) -> str:
    result = subprocess.run(
        [
            "aws", "cloudformation", "describe-stacks",
            "--stack-name", stack_name,
            "--query", "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue",
            "--output", "text",
        ],
        capture_output=True, text=True, check=True,
    )
    arn = result.stdout.strip()
    if not arn or arn == "None":
        print(f"Could not find StateMachineArn output on stack '{stack_name}'. Is it deployed?", file=sys.stderr)
        sys.exit(1)
    return arn


def run_one(arn: str, date_str: str) -> None:
    print(f"--- seeding {date_str} ---")
    payload = json.dumps({"overrideDate": date_str})
    result = subprocess.run(
        ["aws", "stepfunctions", "start-sync-execution", "--state-machine-arn", arn, "--input", payload, "--output", "json"],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3, help="how many past days to backfill (default 3)")
    parser.add_argument("--stack-name", default="SecondSkinStack")
    args = parser.parse_args()

    arn = state_machine_arn(args.stack_name)
    today = datetime.now(timezone.utc).date()

    # Oldest first, so each day's "yesterday" image-conditioning reference
    # and style-memory read genuinely exist by the time the next date runs.
    for offset in range(args.days, 0, -1):
        date_str = (today - timedelta(days=offset)).isoformat()
        run_one(arn, date_str)


if __name__ == "__main__":
    main()

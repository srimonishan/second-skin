#!/usr/bin/env bash
# Manually trigger one full pipeline run synchronously -- for dev iteration
# and for a live demo during judging, without waiting on the daily schedule.
#
# Usage:
#   ./scripts/invoke_pipeline.sh                    # run for "today"
#   ./scripts/invoke_pipeline.sh 2026-08-19          # backfill a specific date
set -euo pipefail

STACK_NAME="${STACK_NAME:-SecondSkinStack}"
OVERRIDE_DATE="${1:-}"

STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" \
  --output text)

if [ -z "$STATE_MACHINE_ARN" ] || [ "$STATE_MACHINE_ARN" = "None" ]; then
  echo "Could not find the state machine ARN in stack outputs for '$STACK_NAME'. Is it deployed?" >&2
  exit 1
fi

if [ -n "$OVERRIDE_DATE" ]; then
  INPUT="{\"overrideDate\": \"$OVERRIDE_DATE\"}"
else
  INPUT="{}"
fi

echo "Starting synchronous execution of $STATE_MACHINE_ARN"
echo "Input: $INPUT"

aws stepfunctions start-sync-execution \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --input "$INPUT" \
  --output json

"""
API Gateway HTTP API handler for POST /submit. Accepts one visitor mood/word
submission at a time, runs it through a cheap Nova Micro moderation check,
and queues approved words in DynamoDB for the next pipeline run to consume.

This is invoked directly by API Gateway (Lambda proxy integration), not by
Step Functions, so its event/response shape is the API Gateway HTTP API
payload format rather than the pipeline's state-passing convention.
"""
import json
import os

from common import ddb, prompts
from common.bedrock_client import invoke_text

MAX_WORD_LENGTH = 40

_CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Content-Type": "application/json",
}


def _response(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": _CORS_HEADERS, "body": json.dumps(body)}


def handler(event: dict, context) -> dict:
    method = (event.get("requestContext", {}).get("http", {}) or {}).get("method", "POST")
    if method == "OPTIONS":
        return _response(200, {"ok": True})

    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "invalid JSON body"})

    word = str(payload.get("word", "")).strip()
    if not word:
        return _response(400, {"error": "word is required"})
    if len(word) > MAX_WORD_LENGTH:
        return _response(400, {"error": f"word must be {MAX_WORD_LENGTH} characters or fewer"})

    model_id = os.environ["MODERATION_MODEL_ID"]
    try:
        raw = invoke_text(
            model_id, prompts.MODERATION_SYSTEM_PROMPT, prompts.moderation_user_prompt(word),
            max_tokens=60, temperature=0.0,
        )
        decision = prompts.extract_json(raw)
        approved = bool(decision.get("approve"))
        reason = str(decision.get("reason", ""))
    except Exception:
        # Fail closed: if the moderation call itself breaks, reject rather
        # than silently letting unmoderated text into a public queue.
        approved = False
        reason = "moderation check unavailable"

    if approved:
        ddb.submit_word(word, status="pending")
        return _response(200, {"status": "accepted", "word": word})
    else:
        ddb.submit_word(word, status="rejected", reason=reason)
        return _response(200, {"status": "rejected", "reason": reason or "did not pass moderation"})

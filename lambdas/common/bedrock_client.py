"""
Thin wrappers around Amazon Bedrock Runtime calls used by Second Skin.

Model IDs are never hardcoded here -- each Lambda reads its model ID from an
environment variable wired in by CDK (see infra/.../constructs/lambdas.py),
so infra stays the single source of truth for which Nova model each function
calls, and swapping a model later is a one-line CDK change, not a code change.
"""
import base64
import json
import os

import boto3

_client = None


def _runtime():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION"))
    return _client


def invoke_text(model_id: str, system_prompt: str, user_prompt: str, *, max_tokens: int = 500, temperature: float = 0.9) -> str:
    """Call a Nova text model via the Converse API and return the plain text reply."""
    kwargs = {
        "modelId": model_id,
        "messages": [{"role": "user", "content": [{"text": user_prompt}]}],
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
    }
    if system_prompt:
        kwargs["system"] = [{"text": system_prompt}]
    response = _runtime().converse(**kwargs)
    return response["output"]["message"]["content"][0]["text"].strip()


def invoke_image(model_id: str, body: dict) -> bytes:
    """
    Call a Nova Canvas (or compatible) image model with a raw request body and
    return the decoded PNG bytes of the first generated image.

    NOTE: the exact `body` shape (taskType name, textToImageParams /
    imageVariationParams field names, imageGenerationConfig bounds) must be
    verified against the *current* Bedrock Nova Canvas API reference before
    this is trusted in production -- see the TODO at the top of
    lambdas/generate_image/handler.py. Do not assume this schema is still
    accurate without checking.
    """
    response = _runtime().invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(response["body"].read())
    images = payload.get("images") or []
    if not images:
        raise RuntimeError(f"Bedrock image model returned no images: {payload}")
    return base64.b64decode(images[0])

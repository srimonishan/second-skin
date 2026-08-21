"""
Step 3: generate today's pattern tile with Bedrock Nova Canvas.

Request body shape confirmed against docs.aws.amazon.com/nova/latest/userguide
(image-gen-req-resp-structure) at build time: taskType "TEXT_IMAGE" /
"IMAGE_VARIATION", textToImageParams / imageVariationParams /
imageGenerationConfig field names, and similarityStrength's valid range of
0.2-1.0 all check out. This is still exactly the kind of detail that can
shift between doc revisions, though -- if a deploy ever fails validation on
this call, re-check that page and `_build_body()` below before assuming the
bug is elsewhere.

For day-to-day visual continuity, when a previous day's tile exists we send
it as a reference image via the IMAGE_VARIATION task type with a moderate
similarityStrength, so today's tile is visibly derived from yesterday's
rather than unrelated. Day 1 (no previous tile) falls back to plain
TEXT_IMAGE.
"""
import base64
import hashlib
import os

from common import prompts, s3util
from common.bedrock_client import invoke_image

IMAGE_SIZE = 512  # px, square -- comfortably inside Nova Canvas's supported range
SIMILARITY_STRENGTH = 0.65  # 0=ignore reference, 1=near-copy; moderate so style evolves rather than repeats


def _seed_for(date: str) -> int:
    """Deterministic per-day seed so re-running the same date is reproducible."""
    digest = hashlib.sha256(date.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_147_483_647


def _build_body(prompt: str, seed: int, reference_image_b64: str | None) -> dict:
    generation_config = {
        "numberOfImages": 1,
        "height": IMAGE_SIZE,
        "width": IMAGE_SIZE,
        "cfgScale": 7.5,
        "seed": seed,
    }
    if reference_image_b64:
        return {
            "taskType": "IMAGE_VARIATION",
            "imageVariationParams": {
                "images": [reference_image_b64],
                "text": prompt,
                "negativeText": prompts.IMAGE_NEGATIVE_PROMPT,
                "similarityStrength": SIMILARITY_STRENGTH,
            },
            "imageGenerationConfig": generation_config,
        }
    return {
        "taskType": "TEXT_IMAGE",
        "textToImageParams": {
            "text": prompt,
            "negativeText": prompts.IMAGE_NEGATIVE_PROMPT,
        },
        "imageGenerationConfig": generation_config,
    }


def handler(event: dict, context) -> dict:
    state = dict(event or {})
    model_id = os.environ["IMAGE_MODEL_ID"]

    brief = state["brief"]
    prompt = prompts.image_prompt_from_brief(**brief)
    seed = _seed_for(state["date"])

    reference_b64 = None
    previous_key = state.get("previousImageKey")
    if previous_key:
        try:
            reference_bytes = s3util.get_bytes(previous_key)
            reference_b64 = base64.b64encode(reference_bytes).decode("utf-8")
        except Exception:
            # Missing/unreadable reference shouldn't block today's generation --
            # just fall back to a fresh text-to-image call.
            reference_b64 = None

    body = _build_body(prompt, seed, reference_b64)
    image_bytes = invoke_image(model_id, body)

    image_key = f"tiles/{state['date']}.png"
    s3util.put_bytes(image_key, image_bytes, "image/png")

    state["imageKey"] = image_key
    state["imageGenerated"] = True
    return state

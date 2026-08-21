"""
Step 4: persist today's result, self-critique into tomorrow's style memory,
mark any consumed community word as used, and regenerate manifest.json.

This is the one state in the pipeline that is allowed to hard-fail (see the
state machine's Catch on this task -> PersistFailed) -- if nothing could be
saved, the run genuinely produced nothing, so there's no meaningful fallback
to paper over.
"""
import os
from datetime import datetime, timezone

from common import ddb, prompts, s3util
from common.bedrock_client import invoke_text

PLACEHOLDER_IMAGE_KEY = "tiles/placeholder.png"


def handler(event: dict, context) -> dict:
    state = dict(event or {})
    model_id = os.environ["TEXT_MODEL_ID"]

    brief = state.get("brief") or {"palette": "unknown", "motif": "unknown", "mood": "unknown"}
    designer_note = state.get("designerNote") or "No note was recorded today."
    image_generated = bool(state.get("imageGenerated", False))
    image_key = state.get("imageKey") or PLACEHOLDER_IMAGE_KEY

    critique_prompt = prompts.critique_user_prompt(
        palette=brief["palette"], motif=brief["motif"], mood=brief["mood"],
        designer_note=designer_note, image_generated=image_generated,
    )
    try:
        style_note = invoke_text(model_id, prompts.CRITIQUE_SYSTEM_PROMPT, critique_prompt, max_tokens=120, temperature=0.8)
    except Exception:
        style_note = f"Tried a {brief['mood']} mood with {brief['motif']}; worth revisiting."

    community_word_id = state.get("communityWordId")
    if community_word_id:
        ddb.mark_word_used(community_word_id)

    status = "complete" if (image_generated and not state.get("briefFallbackUsed") and not state.get("contextFallbackUsed")) else "partial-fallback"

    design_item = {
        "date": state["date"],
        "dayOfWeek": state.get("dayOfWeek", ""),
        "weatherSummary": state.get("weatherSummary", "unknown"),
        "communityWordUsed": state.get("communityWord"),
        "communityWordId": community_word_id,
        "brief": brief,
        "designerNote": designer_note,
        "styleNote": style_note,
        "imageKey": image_key,
        "imageGenerated": image_generated,
        "status": status,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    ddb.put_design(design_item)

    _regenerate_manifest()

    state["styleNote"] = style_note
    state["status"] = status
    return state


def _regenerate_manifest() -> None:
    designs = ddb.all_designs()
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "designs": [
            {
                "date": d["date"],
                "dayOfWeek": d.get("dayOfWeek", ""),
                "weatherSummary": d.get("weatherSummary", ""),
                "communityWordUsed": d.get("communityWordUsed"),
                "brief": d.get("brief", {}),
                "designerNote": d.get("designerNote", ""),
                "styleNote": d.get("styleNote", ""),
                "imageUrl": s3util.public_url(d.get("imageKey", PLACEHOLDER_IMAGE_KEY)),
                "status": d.get("status", "complete"),
            }
            for d in designs
        ],
    }
    s3util.put_json("manifest.json", manifest)

"""Step 2: ask Nova Lite for today's design brief + designer's note."""
import os

from common import prompts
from common.bedrock_client import invoke_text


def handler(event: dict, context) -> dict:
    state = dict(event or {})
    model_id = os.environ["TEXT_MODEL_ID"]

    user_prompt = prompts.brief_user_prompt(
        date=state["date"],
        day_of_week=state["dayOfWeek"],
        weather_summary=state["weatherSummary"],
        community_word=state.get("communityWord"),
        style_memory=state.get("styleMemory", []),
    )
    raw = invoke_text(model_id, prompts.BRIEF_SYSTEM_PROMPT, user_prompt, max_tokens=400, temperature=0.9)
    parsed = prompts.extract_json(raw)

    state["brief"] = {
        "palette": parsed["palette"],
        "motif": parsed["motif"],
        "mood": parsed["mood"],
    }
    state["designerNote"] = parsed["designer_note"]
    state["briefFallbackUsed"] = False
    return state

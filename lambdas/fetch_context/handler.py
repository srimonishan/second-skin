"""
Step 1 of the Second Skin pipeline: gather today's context.

Convention used by all four pipeline Lambdas: each receives the running
Step Functions state as its event, copies it, adds its own fields, and
returns the merged dict. Combined with `output_path="$.Payload"` on every
LambdaInvoke task in the state machine, this means each state just sees the
accumulated state so far -- no ResultPath surgery needed in the ASL, and the
Catch fallback Pass states just need to produce a same-shaped dict.
"""
from datetime import datetime, timezone

from common import ddb, weather


def handler(event: dict, context) -> dict:
    state = dict(event or {})

    override_date = state.get("overrideDate")
    if override_date:
        date = override_date
        day_of_week = datetime.strptime(override_date, "%Y-%m-%d").strftime("%A")
    else:
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y-%m-%d")
        day_of_week = now.strftime("%A")

    weather_info = weather.fetch_weather()

    pending = ddb.oldest_pending_word()
    community_word = pending["word"] if pending else None
    community_word_id = pending["id"] if pending else None

    style_memory = ddb.recent_style_notes(limit=10)

    latest = ddb.latest_design()
    previous_image_key = None
    if latest and latest.get("imageGenerated") and latest.get("date") != date:
        previous_image_key = latest.get("imageKey")

    state.update({
        "date": date,
        "dayOfWeek": day_of_week,
        "weatherSummary": weather_info["summary"],
        "communityWord": community_word,
        "communityWordId": community_word_id,
        "styleMemory": style_memory,
        "previousImageKey": previous_image_key,
        "contextFallbackUsed": False,
    })
    return state

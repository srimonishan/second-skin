"""
Single source of truth for the Nova model IDs and default studio location.
Change values here, not in Lambda code -- every handler reads its model ID
from an env var that traces back to this file.

NOTE on model IDs: these are the on-demand foundation-model IDs as of this
build's writing. Before your first deploy, confirm in the Bedrock console
(Model access, in your target region) that Nova Micro / Nova Lite / Nova
Canvas are all listed as accessible for on-demand InvokeModel in that exact
region. Some Nova launches have required a cross-region *inference profile*
ARN instead of the bare foundation-model ARN in certain regions -- if
InvokeModel ever fails with an on-demand-throughput validation error, switch
the affected constant below to the inference profile ID shown under
Bedrock console -> Cross-region inference, and `model_arn()` will pick it up
automatically (it just interpolates whatever ID you give it).
"""

TEXT_MODEL_ID = "amazon.nova-lite-v1:0"
MODERATION_MODEL_ID = "amazon.nova-micro-v1:0"
IMAGE_MODEL_ID = "amazon.nova-canvas-v1:0"

# Default "studio" location used for weather theming (London -- genuinely
# variable weather, no API key required via Open-Meteo). Override via the
# WEATHER_LAT / WEATHER_LON / WEATHER_LOCATION_NAME env vars if you'd rather
# theme the agent to your own city.
DEFAULT_WEATHER_LAT = "51.5072"
DEFAULT_WEATHER_LON = "-0.1276"
DEFAULT_WEATHER_LOCATION_NAME = "London"

# Daily run time, UTC. 12:00 UTC lands early-to-mid morning across US time
# zones and early evening in Europe -- adjust to when you'd actually like
# a fresh tile "ready when you return".
SCHEDULE_CRON_HOUR_UTC = "12"
SCHEDULE_CRON_MINUTE_UTC = "0"


def model_arn(region: str, model_id: str) -> str:
    """
    Foundation-model ARNs have no account segment (they're AWS-owned),
    hence the double colon before the region-scoped resource path.
    """
    return f"arn:aws:bedrock:{region}::foundation-model/{model_id}"

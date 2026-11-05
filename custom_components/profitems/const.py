"""Constants for the ProfitEMS integration."""

from datetime import timedelta
from zoneinfo import ZoneInfo

DOMAIN = "profitems"
API_URL = "https://panel.profitems.pl/api/v1/instalacja"

# Prices, the plan and "today" all follow the Polish market day, whatever time zone Home Assistant uses.
MARKET_TZ = ZoneInfo("Europe/Warsaw")

# The server refreshes installation data every 5 minutes; its limit is 60 requests per 15 minutes.
# The coordinator asks shortly after the next reading is due, never more often than once a minute.
READING_INTERVAL = timedelta(minutes=5)
READING_GRACE = timedelta(seconds=20)
MIN_UPDATE_INTERVAL = timedelta(seconds=60)
MAX_UPDATE_INTERVAL = timedelta(minutes=5)
# Initial value; the coordinator adjusts it after every reading.
UPDATE_INTERVAL = MIN_UPDATE_INTERVAL

# Readings further apart than this are not integrated into the energy counters:
# the power between them is unknown (for example after an outage of the gateway or of Home Assistant).
MAX_INTEGRATION_GAP = timedelta(minutes=15)

# A repair issue is raised when the gateway stays offline this long.
OFFLINE_ISSUE_AFTER = timedelta(hours=1)

CARD_URL = "/profitems/profitems-card.js"

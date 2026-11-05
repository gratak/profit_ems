"""Services of the ProfitEMS integration. They only read data; nothing is sent to the installation."""

from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import ProfitEmsConfigEntry
from .prices import cheapest_window, day_start, market_today, price_slots

SERVICE_CHEAPEST_WINDOW = "cheapest_window"
ATTR_CONFIG_ENTRY = "config_entry_id"
ATTR_DURATION = "duration"
ATTR_DAY = "day"
DAYS = ("any", "today", "tomorrow")

_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
        vol.Required(ATTR_DURATION): vol.All(
            cv.positive_time_period, vol.Range(min=timedelta(minutes=1), max=timedelta(hours=24))
        ),
        vol.Optional(ATTR_DAY, default="any"): vol.In(DAYS),
    }
)


def _entry(hass: HomeAssistant, entry_id: str | None) -> ProfitEmsConfigEntry:
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
        and (entry_id is None or entry.entry_id == entry_id)
    ]
    if len(entries) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_found" if not entries else "entry_ambiguous",
        )
    return entries[0]


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the services."""

    async def cheapest(call: ServiceCall) -> ServiceResponse:
        entry = _entry(hass, call.data.get(ATTR_CONFIG_ENTRY))
        now = dt_util.utcnow()
        slots = price_slots(entry.runtime_data.data, now)
        today = market_today(now)
        not_after = None
        if call.data[ATTR_DAY] == "today":
            not_after = day_start(today + timedelta(days=1))
        elif call.data[ATTR_DAY] == "tomorrow":
            slots = [slot for slot in slots if slot.start >= day_start(today + timedelta(days=1))]
        window = cheapest_window(slots, call.data[ATTR_DURATION], now, not_after)
        if window is None:
            return {"found": False}
        return {
            "found": True,
            "start": window.start.isoformat(),
            "end": window.end.isoformat(),
            "average_price": window.average_price,
            "prices": [slot.as_dict() for slot in window.slots],
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHEAPEST_WINDOW,
        cheapest,
        schema=_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

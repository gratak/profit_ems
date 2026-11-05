"""Diagnostics of the ProfitEMS integration, for bug reports. The access key is never included."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import ProfitEmsConfigEntry

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ProfitEmsConfigEntry
) -> dict[str, Any]:
    """Return the entry, the last API response and the energy counters."""
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        "update_interval_seconds": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
        "data": coordinator.data,
        "energy": coordinator.energy.as_dict(),
    }

"""The ProfitEMS integration: read-only installation data for Home Assistant."""

import logging
from pathlib import Path

from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import ProfitEmsClient
from .const import CARD_URL, DOMAIN
from .coordinator import ProfitEmsConfigEntry, ProfitEmsCoordinator
from .energy import STORAGE_VERSION
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_FILE = Path(__file__).parent / "frontend" / "profitems-card.js"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services and the dashboard card."""
    async_setup_services(hass)
    await _async_register_card(hass)
    return True


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card and load it on every dashboard, so nothing has to be added by hand."""
    if hass.http is None or "frontend" not in hass.config.components:
        return
    # Imported here: both are optional (after_dependencies) and absent in a minimal setup.
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415
    from homeassistant.components.http import StaticPathConfig  # noqa: PLC0415

    version = (await async_get_integration(hass, DOMAIN)).version
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(CARD_FILE), cache_headers=False)]
    )
    # The version in the address makes browsers fetch the new card after an update.
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")


async def async_setup_entry(hass: HomeAssistant, entry: ProfitEmsConfigEntry) -> bool:
    """Set up ProfitEMS from a config entry."""
    client = ProfitEmsClient(async_get_clientsession(hass), entry.data[CONF_API_KEY])
    coordinator = ProfitEmsCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ProfitEmsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ProfitEmsConfigEntry) -> None:
    """Remove what the entry left behind: its saved counters and its repair issue."""
    ir.async_delete_issue(hass, DOMAIN, f"gateway_offline_{entry.entry_id}")
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}.energy").async_remove()

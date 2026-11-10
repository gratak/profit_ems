"""Data update coordinator for the ProfitEMS integration."""

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import InvalidAuth, ProfitEmsClient, ProfitEmsError, RateLimited
from .const import (
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    OFFLINE_ISSUE_AFTER,
    READING_GRACE,
    READING_INTERVAL,
    UPDATE_INTERVAL,
)
from .energy import EnergyCounters
from .history import BatteryHistory
from .prices import market_today

_LOGGER = logging.getLogger(__name__)

type ProfitEmsConfigEntry = ConfigEntry[ProfitEmsCoordinator]


def next_poll_delay(last_reading: datetime | None, now: datetime) -> timedelta:
    """Return how long to wait so the next request comes just after the next reading.

    The server takes a reading every 5 minutes. Asking more often returns the same data,
    so the request is timed for shortly after the next reading is due, and never earlier
    than a minute from now (a late reading is picked up a minute later).
    """
    if last_reading is None:
        return MAX_UPDATE_INTERVAL
    due = last_reading + READING_INTERVAL + READING_GRACE
    return min(max(due - now, MIN_UPDATE_INTERVAL), MAX_UPDATE_INTERVAL)


class ProfitEmsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the ProfitEMS API."""

    config_entry: ProfitEmsConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ProfitEmsConfigEntry,
        client: ProfitEmsClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.energy = EnergyCounters(hass, config_entry.entry_id)
        self.history = BatteryHistory(hass, config_entry.entry_id)
        # The API sends the plan for the rest of the day only; blocks that have passed are kept here.
        self.plan_today: list[dict[str, str]] = []
        self._plan_day: str | None = None

    async def _async_setup(self) -> None:
        await self.energy.async_load()
        await self.history.async_load()

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.async_get_installation()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("The access key is no longer valid") from err
        except RateLimited as err:
            raise UpdateFailed("Request limit exceeded", retry_after=err.retry_after) from err
        except ProfitEmsError as err:
            raise UpdateFailed(f"Could not read installation data: {err}") from err
        now = dt_util.utcnow()
        connection = data.get("polaczenie") or {}
        reading = connection.get("ostatniOdczyt")
        last_reading = dt_util.parse_datetime(reading) if reading else None
        self.update_interval = next_poll_delay(last_reading, now)
        self.energy.update(data)
        self.history.update(data)
        self._merge_plan(data.get("plan"), now)
        self._track_offline(data, connection.get("stan"), last_reading, now)
        return data

    def _merge_plan(self, plan: Any, now: datetime) -> None:
        """Keep today's earlier plan blocks in front of the plan the API sends now."""
        day = market_today(now).isoformat()
        if day != self._plan_day:
            self._plan_day = day
            self.plan_today = []
        current = [
            {"od": item["od"], "do": item["do"], "tryb": item["tryb"]}
            for item in plan or []
            if isinstance(item, dict)
            and all(isinstance(item.get(key), str) for key in ("od", "do", "tryb"))
        ]
        if not current:
            return
        # "HH:MM" strings with leading zeros sort in time order, "24:00" last.
        first = min(item["od"] for item in current)
        kept = []
        for item in self.plan_today:
            if item["od"] >= first:
                continue
            kept.append({**item, "do": min(item["do"], first)})
        self.plan_today = kept + sorted(current, key=lambda item: item["od"])

    def _track_offline(
        self, data: dict[str, Any], state: str | None, last_reading: datetime | None, now: datetime
    ) -> None:
        """Raise a repair issue while the gateway has sent nothing for a long time."""
        issue_id = f"gateway_offline_{self.config_entry.entry_id}"
        silent_long = last_reading is None or now - last_reading >= OFFLINE_ISSUE_AFTER
        if state == "offline" and silent_long:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="gateway_offline",
                translation_placeholders={"serial": str(data.get("numerBramki"))},
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)

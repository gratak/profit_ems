"""Energy and value counters built from the 5-minute power readings.

The API reports power only. These counters integrate it between consecutive readings
(trapezoidal rule), so the Energy dashboard can be used. They are an estimate: power
can change between two readings five minutes apart.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MARKET_TZ, MAX_INTEGRATION_GAP

STORAGE_VERSION = 1
SAVE_DELAY = 60

# Counter key -> function returning the power in W that feeds it (only positive values count).
_POWER_SOURCES = {
    "pv_energy": lambda now: now.get("pvW"),
    "home_energy": lambda now: now.get("domW"),
    "grid_import_energy": lambda now: _positive(now.get("siecW")),
    "grid_export_energy": lambda now: _positive(_negate(now.get("siecW"))),
    "battery_charge_energy": lambda now: _positive(_negate(now.get("bateriaW"))),
    "battery_discharge_energy": lambda now: _positive(now.get("bateriaW")),
}
# Value counters: energy counter they price, in PLN at the RCE price.
_VALUE_SOURCES = {
    "grid_export_value": "grid_export_energy",
    "grid_import_value": "grid_import_energy",
}
COUNTERS = (*_POWER_SOURCES, *_VALUE_SOURCES)


def _negate(value: Any) -> float | None:
    return -value if isinstance(value, (int, float)) else None


def _positive(value: Any) -> float | None:
    return max(value, 0) if isinstance(value, (int, float)) else None


@dataclass
class _Sample:
    time: datetime
    power: dict[str, float | None]
    price: float | None


class EnergyCounters:
    """Running totals since the integration was added, plus today's totals."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.energy"
        )
        self.total: dict[str, float] = dict.fromkeys(COUNTERS, 0.0)
        self.today: dict[str, float] = dict.fromkeys(COUNTERS, 0.0)
        self.day: str | None = None
        self._last: _Sample | None = None

    async def async_load(self) -> None:
        """Restore the counters saved before a restart."""
        stored = await self._store.async_load()
        if not stored:
            return
        for key in COUNTERS:
            self.total[key] = float(stored.get("total", {}).get(key, 0.0))
            self.today[key] = float(stored.get("today", {}).get(key, 0.0))
        self.day = stored.get("day")
        if (last := stored.get("last")) and (time := dt_util.parse_datetime(last["time"])):
            self._last = _Sample(time, last["power"], last.get("price"))

    def _data_to_save(self) -> dict[str, Any]:
        last = self._last
        return {
            "total": self.total,
            "today": self.today,
            "day": self.day,
            "last": last
            and {"time": last.time.isoformat(), "power": last.power, "price": last.price},
        }

    def update(self, data: dict[str, Any]) -> bool:
        """Add the energy since the previous reading. Return True when anything changed."""
        reading = (data.get("polaczenie") or {}).get("ostatniOdczyt")
        time = dt_util.parse_datetime(reading) if reading else None
        if time is None:
            return False
        last = self._last
        if last is not None and time <= last.time:
            return False  # the same reading again, or an older one
        now_values = data.get("teraz") or {}
        sample = _Sample(
            time,
            {key: _number(source(now_values)) for key, source in _POWER_SOURCES.items()},
            _number((data.get("ceny") or {}).get("teraz")),
        )
        day = time.astimezone(MARKET_TZ).date().isoformat()
        if day != self.day:
            self.today = dict.fromkeys(COUNTERS, 0.0)
            self.day = day
        if last is not None and time - last.time <= MAX_INTEGRATION_GAP:
            hours = (time - last.time).total_seconds() / 3600
            # The price of the earlier reading applies to the period that follows it.
            price = last.price
            for key in _POWER_SOURCES:
                before, after = last.power.get(key), sample.power.get(key)
                if before is None or after is None:
                    continue
                kwh = (before + after) / 2 * hours / 1000
                self._add(key, kwh)
                if price is not None:
                    for value_key, energy_key in _VALUE_SOURCES.items():
                        if energy_key == key:
                            self._add(value_key, kwh * price)
        self._last = sample
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
        return True

    def _add(self, key: str, amount: float) -> None:
        self.total[key] += amount
        self.today[key] += amount

    def today_for(self, key: str, now: datetime) -> float:
        """Return today's value, or 0 when no reading has come in yet today."""
        if self.day != now.astimezone(MARKET_TZ).date().isoformat():
            return 0.0
        return self.today[key]

    def as_dict(self) -> dict[str, Any]:
        return self._data_to_save()


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)

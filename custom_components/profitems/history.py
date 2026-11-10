"""What the battery did and when: hourly totals and sessions with the RCE price.

Built from the 5-minute power readings, like the energy estimates: the energy between two
readings is added to the hour it falls in. The last days are kept, so the card can show
when the battery charged or sold and at what price.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MARKET_TZ, MAX_INTEGRATION_GAP

STORAGE_VERSION = 1
SAVE_DELAY = 60
KEEP_DAYS = 7
# An hour counts as charging or discharging when the battery moved at least this much energy.
MIN_ACTIVITY_KWH = 0.05

CHARGING = "charging"
DISCHARGING = "discharging"
IDLE = "idle"


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _hour_start(moment: datetime) -> datetime:
    local = moment.astimezone(MARKET_TZ)
    return local.replace(minute=0, second=0, microsecond=0)


@dataclass
class _Reading:
    time: datetime
    battery_w: float | None
    grid_w: float | None
    price: float | None
    mode: str | None
    soc: float | None


def activity(hour: dict[str, Any]) -> str:
    """Whether the battery mostly charged, discharged or stayed idle in an hour."""
    charge, discharge = hour["charge_kwh"], hour["discharge_kwh"]
    if max(charge, discharge) < MIN_ACTIVITY_KWH:
        return IDLE
    return CHARGING if charge >= discharge else DISCHARGING


def sessions(hours: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group consecutive hours of the same activity and system mode into sessions.

    Each session has its start and end, the energy the battery took in or gave out, how much of
    it went through the grid, and the average RCE price weighted by that energy.
    """
    result: list[dict[str, Any]] = []
    for hour in hours:
        kind = activity(hour)
        if kind == IDLE:
            continue
        energy = hour["charge_kwh"] if kind == CHARGING else hour["discharge_kwh"]
        grid = hour["import_kwh"] if kind == CHARGING else hour["export_kwh"]
        last = result[-1] if result else None
        if (
            last is not None
            and last["activity"] == kind
            and last["mode"] == hour["mode"]
            and last["end"] == hour["start"]
        ):
            session = last
        else:
            session = {
                "activity": kind,
                "mode": hour["mode"],
                "start": hour["start"],
                "end": hour["end"],
                "energy_kwh": 0.0,
                "grid_kwh": 0.0,
                "_priced_kwh": 0.0,
                "_value": 0.0,
                "soc_start": hour["soc_start"],
            }
            result.append(session)
        session["end"] = hour["end"]
        session["energy_kwh"] += energy
        session["grid_kwh"] += grid
        session["soc_end"] = hour["soc_end"]
        if hour["price"] is not None:
            session["_priced_kwh"] += energy
            session["_value"] += energy * hour["price"]
    for session in result:
        priced = session.pop("_priced_kwh")
        value = session.pop("_value")
        session["average_price"] = round(value / priced, 4) if priced else None
        session["energy_kwh"] = round(session["energy_kwh"], 3)
        session["grid_kwh"] = round(session["grid_kwh"], 3)
        # Value of the energy at the RCE price: what charging from the grid cost or selling earned.
        session["value_pln"] = round(session["grid_kwh"] * session["average_price"], 2) if priced else None
    return result


class BatteryHistory:
    """Hourly battery totals for the last days, kept across restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.history"
        )
        self.hours: list[dict[str, Any]] = []
        self._last: _Reading | None = None

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if not stored:
            return
        self.hours = list(stored.get("hours", []))
        if (last := stored.get("last")) and (time := dt_util.parse_datetime(last["time"])):
            self._last = _Reading(
                time, last.get("battery_w"), last.get("grid_w"), last.get("price"), last.get("mode"), last.get("soc")
            )

    def _data_to_save(self) -> dict[str, Any]:
        last = self._last
        return {
            "hours": self.hours,
            "last": last
            and {
                "time": last.time.isoformat(),
                "battery_w": last.battery_w,
                "grid_w": last.grid_w,
                "price": last.price,
                "mode": last.mode,
                "soc": last.soc,
            },
        }

    def update(self, data: dict[str, Any]) -> bool:
        """Add the energy since the previous reading to its hour. Return True when anything changed."""
        reading_time = (data.get("polaczenie") or {}).get("ostatniOdczyt")
        time = dt_util.parse_datetime(reading_time) if reading_time else None
        if time is None:
            return False
        last = self._last
        if last is not None and time <= last.time:
            return False
        now_values = data.get("teraz") or {}
        reading = _Reading(
            time,
            _number(now_values.get("bateriaW")),
            _number(now_values.get("siecW")),
            _number((data.get("ceny") or {}).get("teraz")),
            (data.get("system") or {}).get("tryb"),
            _number(now_values.get("socPct")),
        )
        if (
            last is not None
            and time - last.time <= MAX_INTEGRATION_GAP
            and None not in (last.battery_w, reading.battery_w)
        ):
            hours = (time - last.time).total_seconds() / 3600
            battery_kwh = (last.battery_w + reading.battery_w) / 2 * hours / 1000
            grid_kwh = (
                (last.grid_w + reading.grid_w) / 2 * hours / 1000
                if None not in (last.grid_w, reading.grid_w)
                else 0.0
            )
            # The period belongs to the hour of the earlier reading, with its price and mode.
            hour = self._hour(_hour_start(last.time), last)
            if battery_kwh < 0:
                hour["charge_kwh"] += -battery_kwh
            else:
                hour["discharge_kwh"] += battery_kwh
            if grid_kwh > 0:
                hour["import_kwh"] += grid_kwh
            else:
                hour["export_kwh"] += -grid_kwh
            hour["soc_end"] = reading.soc
            for key in ("charge_kwh", "discharge_kwh", "import_kwh", "export_kwh"):
                hour[key] = round(hour[key], 4)
        self._last = reading
        self._prune(time)
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)
        return True

    def _hour(self, start: datetime, reading: _Reading) -> dict[str, Any]:
        key = start.isoformat()
        if self.hours and self.hours[-1]["start"] == key:
            hour = self.hours[-1]
        else:
            hour = {
                "start": key,
                # Elapsed time through UTC, so the hours around a DST change come out right.
                "end": (start.astimezone(UTC) + timedelta(hours=1)).astimezone(MARKET_TZ).isoformat(),
                "charge_kwh": 0.0,
                "discharge_kwh": 0.0,
                "import_kwh": 0.0,
                "export_kwh": 0.0,
                "price": reading.price,
                "mode": reading.mode,
                "soc_start": reading.soc,
                "soc_end": reading.soc,
            }
            self.hours.append(hour)
        if reading.mode:
            hour["mode"] = reading.mode
        return hour

    def _prune(self, now: datetime) -> None:
        oldest = now - timedelta(days=KEEP_DAYS)
        self.hours = [
            hour for hour in self.hours if (end := dt_util.parse_datetime(hour["end"])) and end > oldest
        ]

    def as_dict(self) -> dict[str, Any]:
        return self._data_to_save()

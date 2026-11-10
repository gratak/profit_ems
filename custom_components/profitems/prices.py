"""Price slots and the plan as points in time, independent of the API's list format."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from .const import MARKET_TZ


@dataclass(frozen=True)
class PriceSlot:
    """One price period: an hour or, on a quarter-hour market, 15 minutes."""

    start: datetime
    end: datetime
    price: float

    def as_dict(self) -> dict[str, Any]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat(), "price": self.price}


def market_today(now: datetime) -> date:
    """Return the market day (Polish local date) for a moment."""
    return now.astimezone(MARKET_TZ).date()


def day_start(day: date) -> datetime:
    """Return local midnight that starts a market day."""
    return datetime.combine(day, time(), MARKET_TZ)


def _day_length(day: date) -> timedelta:
    """Return the real length of a market day: 23, 24 or 25 hours."""
    return day_start(day + timedelta(days=1)).astimezone(UTC) - day_start(day).astimezone(UTC)


def _add_real(moment: datetime, delta: timedelta) -> datetime:
    """Add elapsed time, not wall-clock time, and express the result in market time.

    Arithmetic on datetimes that share a ZoneInfo is wall-clock arithmetic in Python,
    which is wrong across a DST change; going through UTC avoids that.
    """
    return (moment.astimezone(UTC) + delta).astimezone(MARKET_TZ)


def slots_for_day(values: list[Any] | None, day: date) -> list[PriceSlot]:
    """Turn the API's list of prices for a day into slots with start and end times.

    The list may hold hourly prices (23, 24 or 25 on DST days) or quarter-hour prices
    (92, 96 or 100). Slots are counted in real time from local midnight, so a 25 hour day
    gets two slots for the repeated hour. Missing values (None) are skipped.
    """
    if not values:
        return []
    count = len(values)
    if count in (23, 24, 25):
        step = timedelta(hours=1)
    elif count in (92, 96, 100):
        step = timedelta(minutes=15)
    else:
        step = _day_length(day) / count
    start = day_start(day)
    slots = []
    for index, value in enumerate(values):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        slot_start = _add_real(start, index * step)
        slots.append(PriceSlot(slot_start, _add_real(slot_start, step), float(value)))
    return slots


def slots_from_periods(periods: list[Any] | None) -> list[PriceSlot]:
    """Turn the API's prices with start and end (godzinyDzis, godzinyJutro) into slots."""
    slots = []
    for item in periods or []:
        if not isinstance(item, dict):
            continue
        start = _parse_utc(item.get("od"))
        end = _parse_utc(item.get("do"))
        price = item.get("cena")
        if start is None or end is None or end <= start:
            continue
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            continue
        slots.append(PriceSlot(start.astimezone(MARKET_TZ), end.astimezone(MARKET_TZ), float(price)))
    return slots


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else None


def price_slots(data: dict[str, Any], now: datetime) -> list[PriceSlot]:
    """Return today's and, when published, tomorrow's price slots.

    The prices with start and end from the API are used when present; otherwise the plain
    lists are given times here (older API responses).
    """
    prices = data.get("ceny") or {}
    today = market_today(now)
    result = []
    for periods, values, day in (
        ("godzinyDzis", "dzis", today),
        ("godzinyJutro", "jutro", today + timedelta(days=1)),
    ):
        slots = slots_from_periods(prices.get(periods))
        result += slots or slots_for_day(prices.get(values), day)
    return result


def cheapest_slot(slots: list[PriceSlot], day: date) -> PriceSlot | None:
    """Return the cheapest slot of a market day (the earliest one on a tie)."""
    of_day = [slot for slot in slots if slot.start.date() == day]
    return min(of_day, key=lambda slot: slot.price, default=None)


@dataclass(frozen=True)
class Window:
    """A run of consecutive slots."""

    start: datetime
    end: datetime
    average_price: float
    slots: list[PriceSlot]


def cheapest_window(
    slots: list[PriceSlot],
    duration: timedelta,
    not_before: datetime,
    not_after: datetime | None = None,
) -> Window | None:
    """Find the cheapest run of consecutive slots that covers the duration.

    Only slots starting at or after not_before are used, so the window can begin at
    once or later. A slot already in progress is skipped: it has partly passed.
    The average is weighted by time, so it stays correct when slot lengths differ.
    """
    usable = [slot for slot in slots if slot.start >= not_before]
    if not_after is not None:
        usable = [slot for slot in usable if slot.end <= not_after]
    best: Window | None = None
    for first in range(len(usable)):
        covered = timedelta()
        cost = 0.0
        for last in range(first, len(usable)):
            slot = usable[last]
            if last > first and slot.start != usable[last - 1].end:
                break  # a gap in the data
            length = slot.end - slot.start
            take = min(length, duration - covered)
            cost += slot.price * (take / timedelta(hours=1))
            covered += take
            if covered >= duration:
                average = cost / (duration / timedelta(hours=1))
                if best is None or average < best.average_price - 1e-9:
                    best = Window(
                        usable[first].start,
                        usable[first].start + duration,
                        round(average, 4),
                        usable[first : last + 1],
                    )
                break
    return best


def plan_blocks(
    plan: list[Any] | None, now: datetime, days_ahead: int = 0
) -> list[tuple[datetime, datetime, str]]:
    """Return a day's plan as (start, end, mode): today's, or with days_ahead=1 tomorrow's."""
    today = market_today(now) + timedelta(days=days_ahead)
    blocks = []
    for item in plan or []:
        try:
            start = _clock(today, item["od"])
            end = _clock(today, item["do"])
            mode = str(item["tryb"])
        except (KeyError, TypeError, ValueError):
            continue
        if end > start:
            blocks.append((start, end, mode))
    return blocks


def _clock(day: date, value: str) -> datetime:
    hours, minutes = (int(part) for part in value.split(":"))
    if hours == 24 and minutes == 0:
        return day_start(day + timedelta(days=1))
    return datetime.combine(day, time(hours, minutes), MARKET_TZ)

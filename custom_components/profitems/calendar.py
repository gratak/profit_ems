"""Calendar of the ProfitEMS integration: the system's plan for the rest of the day."""

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import ProfitEmsConfigEntry, ProfitEmsCoordinator
from .entity import ProfitEmsEntity
from .prices import plan_blocks

PARALLEL_UPDATES = 0

# Event titles; the API sends the mode as a key, and a calendar event has no translation of its own.
MODE_NAMES = {
    "pl": {
        "samokonsumpcja": "Samokonsumpcja",
        "ladowanie_ograniczone": "Ładowanie ograniczone",
        "ladowanie_z_sieci": "Ładowanie z sieci",
        "sprzedaz": "Sprzedaż do sieci",
        "rezerwa": "Rezerwa",
        "zasilanie_domu": "Zasilanie domu",
        "blokada_oddawania": "Blokada oddawania do sieci",
        "wstrzymany": "Wstrzymany",
        "obserwacja": "Obserwacja",
    },
    "en": {
        "samokonsumpcja": "Self-consumption",
        "ladowanie_ograniczone": "Limited charging",
        "ladowanie_z_sieci": "Charging from the grid",
        "sprzedaz": "Selling to the grid",
        "rezerwa": "Reserve",
        "zasilanie_domu": "Powering the home",
        "blokada_oddawania": "Export blocked",
        "wstrzymany": "Paused",
        "obserwacja": "Observation",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProfitEmsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the plan calendar."""
    async_add_entities([ProfitEmsPlanCalendar(entry.runtime_data)])


class ProfitEmsPlanCalendar(ProfitEmsEntity, CalendarEntity):
    """One event per block of today's plan; automations can trigger on an event's start."""

    def __init__(self, coordinator: ProfitEmsCoordinator) -> None:
        super().__init__(coordinator, EntityDescription(key="plan", translation_key="plan"))

    def _events(self) -> list[CalendarEvent]:
        language = "pl" if self.hass.config.language.startswith("pl") else "en"
        names = MODE_NAMES[language]
        return [
            CalendarEvent(
                start=start,
                end=end,
                summary=names.get(mode, mode),
                description=mode,
                uid=f"{self.unique_id}_{start.isoformat()}",
            )
            for start, end, mode in plan_blocks(self.coordinator.plan_today, dt_util.utcnow())
        ]

    @property
    def event(self) -> CalendarEvent | None:
        """Return the block in progress, or the next one."""
        now = dt_util.utcnow()
        upcoming = [event for event in self._events() if event.end > now]
        return min(upcoming, key=lambda event: event.start, default=None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the blocks that overlap the requested period."""
        return [
            event
            for event in self._events()
            if event.start < end_date and event.end > start_date
        ]

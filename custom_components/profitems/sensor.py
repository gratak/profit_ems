"""Sensors of the ProfitEMS integration."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import ProfitEmsConfigEntry
from .energy import COUNTERS
from .entity import ProfitEmsEntity, section
from .prices import cheapest_slot, market_today, price_slots

PARALLEL_UPDATES = 0

type Data = dict[str, Any]


def _timestamp(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


def _cheapest_start(data: Data) -> datetime | None:
    now = dt_util.utcnow()
    slot = cheapest_slot(price_slots(data, now), market_today(now))
    return slot.start if slot else None


@dataclass(frozen=True, kw_only=True)
class ProfitEmsSensorDescription(SensorEntityDescription):
    """Describes a sensor and where its value comes from."""

    value_fn: Callable[[Data], Any]
    attributes_fn: Callable[[Data], dict[str, Any]] | None = None


def _power(key: str, field: str, part: str = "teraz") -> ProfitEmsSensorDescription:
    return ProfitEmsSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: section(data, part).get(field),
    )


SENSORS = (
    ProfitEmsSensorDescription(
        key="battery_level",
        translation_key="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: section(data, "teraz").get("socPct"),
    ),
    _power("pv_power", "pvW"),
    _power("home_power", "domW"),
    _power("grid_power", "siecW"),
    _power("battery_power", "bateriaW"),
    _power("pv_surplus", "nadwyzkaPvW", "sygnaly"),
    # A plain text sensor, not an enum: API version 1 may add new modes without breaking the entity.
    ProfitEmsSensorDescription(
        key="mode",
        translation_key="mode",
        value_fn=lambda data: section(data, "system").get("tryb"),
        attributes_fn=lambda data: {
            "since": section(data, "system").get("trybOd"),
            "plan": data.get("plan", []),
        },
    ),
    ProfitEmsSensorDescription(
        key="rce_price",
        translation_key="rce_price",
        native_unit_of_measurement="PLN/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=4,
        value_fn=lambda data: section(data, "ceny").get("teraz"),
        attributes_fn=lambda data: {
            "today": section(data, "ceny").get("dzis"),
            "tomorrow": section(data, "ceny").get("jutro"),
            # The same prices with their start and end, whatever the API's resolution (hour or 15 minutes).
            "prices": [slot.as_dict() for slot in price_slots(data, dt_util.utcnow())],
        },
    ),
    ProfitEmsSensorDescription(
        key="cheapest_hour",
        translation_key="cheapest_hour",
        value_fn=lambda data: section(data, "sygnaly").get("najtanszaGodzina"),
    ),
    ProfitEmsSensorDescription(
        key="cheapest_slot_start",
        translation_key="cheapest_slot_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: _cheapest_start(data),
    ),
    ProfitEmsSensorDescription(
        key="connection",
        translation_key="connection",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: section(data, "polaczenie").get("stan"),
    ),
    ProfitEmsSensorDescription(
        key="last_reading",
        translation_key="last_reading",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp(section(data, "polaczenie").get("ostatniOdczyt")),
    ),
)


@dataclass(frozen=True, kw_only=True)
class ProfitEmsCounterDescription(SensorEntityDescription):
    """Describes an energy or value counter kept by the integration."""


ENERGY_COUNTERS = tuple(
    ProfitEmsCounterDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
    )
    for key in COUNTERS
    if key.endswith("_energy")
)
VALUE_COUNTERS = tuple(
    ProfitEmsCounterDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="PLN",
        suggested_display_precision=2,
    )
    for key in COUNTERS
    if key.endswith("_value")
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProfitEmsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            *(ProfitEmsSensor(coordinator, description) for description in SENSORS),
            *(
                ProfitEmsCounterSensor(coordinator, description)
                for description in (*ENERGY_COUNTERS, *VALUE_COUNTERS)
            ),
        ]
    )


class ProfitEmsSensor(ProfitEmsEntity, SensorEntity):
    """A value read from the installation data."""

    entity_description: ProfitEmsSensorDescription
    # Hourly prices and the plan change every day; keeping them out of the database saves space.
    _unrecorded_attributes = frozenset({"today", "tomorrow", "prices", "plan"})

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional data, such as the plan or hourly prices."""
        if (attributes_fn := self.entity_description.attributes_fn) is None:
            return None
        return attributes_fn(self.coordinator.data)


class ProfitEmsCounterSensor(ProfitEmsEntity, SensorEntity):
    """A running total since the integration was added, estimated from the power readings.

    The attribute today holds the total of the current market day, which the dashboard card shows.
    """

    entity_description: ProfitEmsCounterDescription

    @property
    def native_value(self) -> float:
        """Return the total."""
        return round(self.coordinator.energy.total[self.entity_description.key], 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return today's total."""
        today = self.coordinator.energy.today_for(self.entity_description.key, dt_util.utcnow())
        return {"today": round(today, 4)}

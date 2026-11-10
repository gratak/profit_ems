"""Sensors of the ProfitEMS integration."""

from collections.abc import Callable
from dataclasses import dataclass, replace
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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import ProfitEmsConfigEntry
from .energy import COUNTERS
from .entity import ProfitEmsEntity, section
from .prices import cheapest_slot, day_start, market_today, price_slots

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
    # Attributes kept by the coordinator rather than read from the last response.
    coordinator_attributes_fn: Callable[[Any], dict[str, Any]] | None = None
    # The value starts again from zero at Polish midnight (state_class TOTAL needs last_reset).
    resets_daily: bool = False


def _power(key: str, field: str, part: str = "teraz") -> ProfitEmsSensorDescription:
    return ProfitEmsSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: section(data, part).get(field),
    )


def _energy(key: str, field: str) -> ProfitEmsSensorDescription:
    # Inverter counters reset at the inverter's midnight; TOTAL_INCREASING handles the reset in the Energy panel.
    # Older API responses have no "energiaDzis", so the sensor stays unknown instead of failing.
    return ProfitEmsSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=1,
        value_fn=lambda data: section(data, "energiaDzis").get(field),
    )


# Daily counters reported by the inverter: sensor key -> API field.
ENERGY_FIELDS = {
    "pv_energy_today": "pvKwh",
    "home_energy_today": "domKwh",
    "grid_import_today": "poborKwh",
    "grid_export_today": "oddawanieKwh",
    "battery_charge_today": "ladowanieKwh",
    "battery_discharge_today": "rozladowanieKwh",
}
# The integration's own estimate that stands in for an inverter counter the brand does not report.
ESTIMATE_FOR_FIELD = {
    "pv_energy": "pvKwh",
    "home_energy": "domKwh",
    "grid_import_energy": "poborKwh",
    "grid_export_energy": "oddawanieKwh",
    "battery_charge_energy": "ladowanieKwh",
    "battery_discharge_energy": "rozladowanieKwh",
}


def _value_attributes(data: Data) -> dict[str, Any]:
    value = section(data, "wartoscDzis")
    return {
        "from_panels": value.get("zPaneliZl"),
        "from_system": value.get("zSystemuZl"),
        "export_revenue": value.get("sprzedazZl"),
        "data_coverage": value.get("pokrycieDanychPct"),
        "calculated_at": value.get("przeliczono"),
    }


def _plan_today(coordinator: Any) -> dict[str, Any]:
    # The API sends the whole day's plan; the plan kept by the coordinator covers older API versions.
    return {"plan_today": coordinator.data.get("planDoby") or coordinator.plan_today}


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
            "plan_tomorrow": data.get("planJutro"),
        },
        coordinator_attributes_fn=_plan_today,
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
            "prices_today": section(data, "ceny").get("godzinyDzis"),
            "prices_tomorrow": section(data, "ceny").get("godzinyJutro"),
            # Today's and tomorrow's prices in one list, whatever the API's resolution (hour or 15 minutes).
            "prices": [slot.as_dict() for slot in price_slots(data, dt_util.utcnow())],
        },
    ),
    *(_energy(key, field) for key, field in ENERGY_FIELDS.items()),
    ProfitEmsSensorDescription(
        key="value_today",
        translation_key="value_today",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        resets_daily=True,
        native_unit_of_measurement="PLN",
        suggested_display_precision=2,
        value_fn=lambda data: section(data, "wartoscDzis").get("razemZl"),
        attributes_fn=_value_attributes,
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


def _reports(data: Data, field: str) -> bool | None:
    """Whether the inverter reports a daily counter; None when the gateway is not online to tell."""
    if section(data, "polaczenie").get("stan") != "online":
        return None
    return section(data, "energiaDzis").get(field) is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ProfitEmsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    # Many inverter brands do not report some daily counters. Such sensors are created disabled,
    # so they do not clutter the device; the user can still enable them.
    descriptions = [
        replace(description, entity_registry_enabled_default=False)
        if description.key in ENERGY_FIELDS and not _reports(data, ENERGY_FIELDS[description.key])
        else description
        for description in SENSORS
    ]
    # The integration's estimates stand in only for counters the inverter does not report.
    # While the gateway is not online, nothing is decided and existing estimates stay.
    registry = er.async_get(hass)
    estimates = []
    for description in ENERGY_COUNTERS:
        if _reports(data, ESTIMATE_FOR_FIELD[description.key]):
            unique_id = f"{data.get('numerBramki')}_{description.key}"
            if entity_id := registry.async_get_entity_id("sensor", DOMAIN, unique_id):
                registry.async_remove(entity_id)
            continue
        estimates.append(description)
    async_add_entities(
        [
            *(ProfitEmsSensor(coordinator, description) for description in descriptions),
            *(
                ProfitEmsCounterSensor(coordinator, description)
                for description in (*estimates, *VALUE_COUNTERS)
            ),
        ]
    )


class ProfitEmsSensor(ProfitEmsEntity, SensorEntity):
    """A value read from the installation data."""

    entity_description: ProfitEmsSensorDescription
    # Hourly prices and the plan change every day; keeping them out of the database saves space.
    _unrecorded_attributes = frozenset(
        {"today", "tomorrow", "prices", "prices_today", "prices_tomorrow", "plan", "plan_today", "plan_tomorrow"}
    )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def last_reset(self) -> datetime | None:
        """Return Polish midnight for values that start again every day.

        The API counts the day's value from midnight in Poland, whatever time zone Home Assistant uses.
        """
        if not self.entity_description.resets_daily:
            return None
        return day_start(market_today(dt_util.utcnow()))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional data, such as the plan or hourly prices."""
        description = self.entity_description
        if description.attributes_fn is None:
            return None
        attributes = description.attributes_fn(self.coordinator.data)
        if description.coordinator_attributes_fn is not None:
            attributes |= description.coordinator_attributes_fn(self.coordinator)
        return attributes


class ProfitEmsCounterSensor(ProfitEmsEntity, SensorEntity):
    """A running total since the integration was added, estimated from the power readings.

    Energy estimates exist only for counters the inverter does not report. The attribute today
    holds the total of the current market day, which the dashboard card shows.
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

"""Tests of the features added on top of the read-only sensors."""

import copy
from datetime import UTC, date, datetime, timedelta

from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.profitems.const import API_URL, DOMAIN
from custom_components.profitems.coordinator import next_poll_delay
from custom_components.profitems.prices import cheapest_window, slots_for_day

from .conftest import INSTALLATION
from .test_integration import KEY, _setup, _state

READING = datetime(2026, 11, 2, 12, 5, 54, 400000, tzinfo=UTC)


def _body(**changes):
    body = copy.deepcopy(INSTALLATION)
    for path, value in changes.items():
        part, field = path.split("__")
        body[part][field] = value
    return body


# ---------------------------------------------------------------- prices


def test_hourly_prices_get_times_in_polish_time():
    slots = slots_for_day([0.5] * 24, date(2026, 11, 2))
    assert len(slots) == 24
    assert slots[0].start.isoformat() == "2026-11-02T00:00:00+01:00"
    assert slots[-1].end.isoformat() == "2026-11-03T00:00:00+01:00"


def test_quarter_hour_prices():
    slots = slots_for_day([float(i) for i in range(96)], date(2026, 11, 2))
    assert len(slots) == 96
    assert slots[5].start.isoformat() == "2026-11-02T01:15:00+01:00"
    assert slots[5].end - slots[5].start == timedelta(minutes=15)


def test_25_hour_day_repeats_the_hour_when_clocks_go_back():
    slots = slots_for_day([float(i) for i in range(25)], date(2026, 10, 25))
    assert [s.start.isoformat() for s in slots[1:4]] == [
        "2026-10-25T01:00:00+02:00",
        "2026-10-25T02:00:00+02:00",
        "2026-10-25T02:00:00+01:00",
    ]
    assert slots[-1].end.isoformat() == "2026-10-26T00:00:00+01:00"


def test_23_hour_day_skips_the_hour_when_clocks_go_forward():
    slots = slots_for_day([float(i) for i in range(23)], date(2026, 3, 29))
    assert slots[2].start.isoformat() == "2026-03-29T03:00:00+02:00"
    assert slots[-1].end.isoformat() == "2026-03-30T00:00:00+02:00"


def test_missing_prices_are_skipped():
    prices = [0.5] * 24
    prices[3] = None
    assert len(slots_for_day(prices, date(2026, 11, 2))) == 23
    assert slots_for_day(None, date(2026, 11, 2)) == []


def test_cheapest_window_spans_hours_and_starts_in_the_future():
    prices = [0.9] * 24
    prices[2], prices[3], prices[4] = 0.3, 0.2, 0.25
    slots = slots_for_day(prices, date(2026, 11, 2))
    start = datetime(2026, 11, 1, 23, 0, tzinfo=UTC)  # 00:00 Polish time
    window = cheapest_window(slots, timedelta(hours=2), start)
    assert window.start.isoformat() == "2026-11-02T03:00:00+01:00"
    assert window.average_price == 0.225
    # From 03:30 on, the slot in progress is skipped.
    later = datetime(2026, 11, 2, 2, 30, tzinfo=UTC)
    assert cheapest_window(slots, timedelta(hours=2), later).start.hour == 4


def test_cheapest_window_weights_a_partial_last_slot():
    slots = slots_for_day([0.2, 1.0] + [5.0] * 22, date(2026, 11, 2))
    window = cheapest_window(slots, timedelta(minutes=90), slots[0].start)
    assert window.average_price == round((0.2 + 0.5) / 1.5, 4)


def test_no_window_when_prices_run_out():
    slots = slots_for_day([0.5] * 24, date(2026, 11, 2))
    assert cheapest_window(slots, timedelta(hours=3), slots[-2].start) is None


# ---------------------------------------------------------------- polling


def test_poll_waits_for_the_next_reading():
    assert next_poll_delay(READING, READING + timedelta(seconds=10)) == timedelta(minutes=5)
    assert next_poll_delay(READING, READING + timedelta(minutes=3)) == timedelta(seconds=140)
    assert next_poll_delay(READING, READING + timedelta(minutes=20)) == timedelta(seconds=60)
    assert next_poll_delay(None, READING) == timedelta(minutes=5)


# ---------------------------------------------------------------- energy


async def test_energy_counters_integrate_power_between_readings(
    hass, aioclient_mock, freezer
):
    freezer.move_to(READING + timedelta(seconds=30))
    entry = await _setup(hass, aioclient_mock)
    assert float(_state(hass, "pv_energy").state) == 0

    later = READING + timedelta(minutes=5)
    body = _body(polaczenie__ostatniOdczyt=later.isoformat())
    body["teraz"] = {"socPct": 75, "pvW": 1418, "domW": 333, "siecW": -1000, "bateriaW": -100}
    aioclient_mock.clear_requests()
    aioclient_mock.get(API_URL, json=body)
    freezer.move_to(later + timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Trapezoid over 5 minutes: (582 + 1418) / 2 W * 1/12 h = 83.3 Wh.
    assert float(_state(hass, "pv_energy").state) == round(1000 / 12 / 1000, 4)
    export = _state(hass, "grid_export_energy")
    assert float(export.state) == round((11 + 1000) / 2 / 12 / 1000, 4)
    assert float(_state(hass, "grid_import_energy").state) == 0
    # Valued at the RCE price of the earlier reading.
    value = _state(hass, "grid_export_value")
    assert float(value.state) == round(float(export.state) * 2.1941, 4)
    assert value.attributes["today"] == float(value.state)
    assert value.attributes["unit_of_measurement"] == "PLN"

    # The same reading again adds nothing.
    aioclient_mock.clear_requests()
    aioclient_mock.get(API_URL, json=body)
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert float(_state(hass, "grid_export_energy").state) == float(export.state)
    assert entry.runtime_data.energy.day == "2026-11-02"


async def test_energy_skips_a_long_gap(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))
    await _setup(hass, aioclient_mock)
    later = READING + timedelta(hours=2)
    aioclient_mock.clear_requests()
    aioclient_mock.get(API_URL, json=_body(polaczenie__ostatniOdczyt=later.isoformat()))
    freezer.move_to(later + timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert float(_state(hass, "home_energy").state) == 0


async def test_energy_counters_survive_a_restart(hass, aioclient_mock, freezer, hass_storage):
    hass_storage[f"{DOMAIN}.test_entry.energy"] = {
        "version": 1,
        "key": f"{DOMAIN}.test_entry.energy",
        "data": {
            "total": {"pv_energy": 12.5},
            "today": {"pv_energy": 1.5},
            "day": "2026-11-02",
            "last": None,
        },
    }
    freezer.move_to(READING + timedelta(seconds=30))
    aioclient_mock.get(API_URL, json=INSTALLATION)
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry",
        unique_id=INSTALLATION["numerBramki"],
        data={"api_key": KEY},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = _state(hass, "pv_energy")
    assert float(state.state) == 12.5
    assert state.attributes["today"] == 1.5


# ---------------------------------------------------------------- entities


async def test_prices_attribute_and_cheapest_slot(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))
    prices = [0.6] * 24
    prices[13] = 0.1
    await _setup(hass, aioclient_mock, _body(ceny__dzis=prices, ceny__jutro=[0.4] * 24))
    attributes = _state(hass, "rce_price").attributes
    assert len(attributes["prices"]) == 48
    assert attributes["prices"][13] == {
        "start": "2026-11-02T13:00:00+01:00",
        "end": "2026-11-02T14:00:00+01:00",
        "price": 0.1,
    }
    assert _state(hass, "cheapest_slot_start").state == "2026-11-02T12:00:00+00:00"


async def test_plan_calendar(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))
    body = copy.deepcopy(INSTALLATION)
    body["plan"] = [
        {"od": "13:08", "do": "17:00", "tryb": "samokonsumpcja"},
        {"od": "17:00", "do": "24:00", "tryb": "sprzedaz"},
    ]
    await _setup(hass, aioclient_mock, body)
    state = _state(hass, "plan", "calendar")
    # 13:06 Polish time: the first block starts at 13:08, so it is shown as the next event.
    assert state.state == "off"
    assert state.attributes["message"] == "Self-consumption"

    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {"start_date_time": "2026-11-02T16:00:00+01:00", "duration": {"hours": 12}},
        target={"entity_id": state.entity_id},
        blocking=True,
        return_response=True,
    )
    events = result[state.entity_id]["events"]
    assert [e["summary"] for e in events] == ["Self-consumption", "Selling to the grid"]
    assert events[1]["end"] == "2026-11-03T00:00:00+01:00"


async def test_cheapest_window_service(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))  # 13:06 Polish time
    today = [0.9] * 24
    today[20], today[21] = 0.3, 0.35
    tomorrow = [0.9] * 24
    tomorrow[3], tomorrow[4] = 0.1, 0.1
    await _setup(hass, aioclient_mock, _body(ceny__dzis=today, ceny__jutro=tomorrow))

    async def call(**data):
        return await hass.services.async_call(
            DOMAIN, "cheapest_window", data, blocking=True, return_response=True
        )

    result = await call(duration={"hours": 2})
    assert result["start"] == "2026-11-03T03:00:00+01:00"
    assert result["average_price"] == 0.1
    result = await call(duration={"hours": 2}, day="today")
    assert result["start"] == "2026-11-02T20:00:00+01:00"
    assert result["end"] == "2026-11-02T22:00:00+01:00"
    assert (await call(duration={"hours": 12}, day="today")) == {"found": False}


async def test_diagnostics_hide_the_key(hass, aioclient_mock, hass_client):
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await _setup(hass, aioclient_mock)
    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert KEY not in str(diagnostics)
    assert diagnostics["data"]["numerBramki"] == INSTALLATION["numerBramki"]
    assert "total" in diagnostics["energy"]


async def test_offline_gateway_raises_and_clears_a_repair_issue(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(hours=2))
    offline = _body(polaczenie__stan="offline")
    entry = await _setup(hass, aioclient_mock, offline)
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, f"gateway_offline_{entry.entry_id}")

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        API_URL, json=_body(polaczenie__ostatniOdczyt=dt_util.utcnow().isoformat())
    )
    freezer.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert not issues.async_get_issue(DOMAIN, f"gateway_offline_{entry.entry_id}")


async def test_briefly_offline_gateway_raises_no_issue(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(minutes=20))
    entry = await _setup(hass, aioclient_mock, _body(polaczenie__stan="offline"))
    assert not ir.async_get(hass).async_get_issue(DOMAIN, f"gateway_offline_{entry.entry_id}")

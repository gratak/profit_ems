"""Tests of the features added on top of the read-only sensors."""

import copy
from datetime import UTC, date, datetime, timedelta

from homeassistant.helpers import entity_registry as er, issue_registry as ir
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
    """The fixture with changes; prices given as lists replace the API's prices with times."""
    body = copy.deepcopy(INSTALLATION)
    for path, value in changes.items():
        part, field = path.split("__")
        body[part][field] = value
        if part == "ceny" and field in ("dzis", "jutro"):
            body["ceny"]["godzinyDzis" if field == "dzis" else "godzinyJutro"] = None
    return body


def _without_inverter_counters(body):
    """An inverter brand that reports no daily counters, so the estimates are used."""
    body["energiaDzis"] = None
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
    entry = await _setup(hass, aioclient_mock, _without_inverter_counters(_body()))
    assert float(_state(hass, "pv_energy").state) == 0

    later = READING + timedelta(minutes=5)
    body = _without_inverter_counters(_body(polaczenie__ostatniOdczyt=later.isoformat()))
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
    await _setup(hass, aioclient_mock, _without_inverter_counters(_body()))
    later = READING + timedelta(hours=2)
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        API_URL, json=_without_inverter_counters(_body(polaczenie__ostatniOdczyt=later.isoformat()))
    )
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
    aioclient_mock.get(API_URL, json=_without_inverter_counters(_body()))
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
    body["planDoby"] = [{"od": "00:00", "do": "13:08", "tryb": "rezerwa"}, *body["plan"]]
    await _setup(hass, aioclient_mock, body)
    state = _state(hass, "plan", "calendar")
    # 13:06 Polish time: the morning block of the whole day's plan is still in progress.
    assert state.state == "on"
    assert state.attributes["message"] == "Reserve"

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


async def test_plan_keeps_earlier_blocks_of_the_day(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))
    body = copy.deepcopy(INSTALLATION)
    body["plan"] = [
        {"od": "13:00", "do": "17:00", "tryb": "samokonsumpcja"},
        {"od": "17:00", "do": "24:00", "tryb": "sprzedaz"},
    ]
    del body["planDoby"]  # an older API response: the integration keeps the plan itself
    entry = await _setup(hass, aioclient_mock, body)

    later = copy.deepcopy(body)
    later["polaczenie"]["ostatniOdczyt"] = (READING + timedelta(hours=5)).isoformat()
    later["plan"] = [{"od": "18:10", "do": "24:00", "tryb": "rezerwa"}]
    aioclient_mock.clear_requests()
    aioclient_mock.get(API_URL, json=later)
    freezer.move_to(READING + timedelta(hours=5, seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert entry.runtime_data.plan_today == [
        {"od": "13:00", "do": "17:00", "tryb": "samokonsumpcja"},
        {"od": "17:00", "do": "18:10", "tryb": "sprzedaz"},
        {"od": "18:10", "do": "24:00", "tryb": "rezerwa"},
    ]
    assert _state(hass, "mode").attributes["plan_today"][1]["do"] == "18:10"
    assert _state(hass, "mode").attributes["plan"] == later["plan"]


async def test_card_is_served_and_loaded_on_dashboards(hass):
    from unittest.mock import AsyncMock, MagicMock  # noqa: PLC0415

    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL  # noqa: PLC0415

    from custom_components.profitems import CARD_FILE, _async_register_card  # noqa: PLC0415

    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    hass.config.components.add("frontend")
    hass.data[DATA_EXTRA_MODULE_URL] = MagicMock()
    await _async_register_card(hass)
    (config,) = hass.http.async_register_static_paths.call_args.args[0]
    assert config.url_path == "/profitems/profitems-card.js"
    assert config.path == str(CARD_FILE)
    assert CARD_FILE.is_file()
    url = hass.data[DATA_EXTRA_MODULE_URL].add.call_args.args[0]
    assert url.startswith("/profitems/profitems-card.js?v=")


async def test_calendar_shows_tomorrows_plan(hass, aioclient_mock, freezer):
    freezer.move_to(datetime(2026, 11, 2, 21, 30, tzinfo=UTC))  # 22:30 Polish time
    body = _body(polaczenie__ostatniOdczyt=datetime(2026, 11, 2, 21, 28, tzinfo=UTC).isoformat())
    body["planJutro"] = [
        {"od": "00:00", "do": "05:00", "tryb": "ladowanie_z_sieci"},
        {"od": "05:00", "do": "24:00", "tryb": "samokonsumpcja"},
    ]
    await _setup(hass, aioclient_mock, body)
    state = _state(hass, "plan", "calendar")
    result = await hass.services.async_call(
        "calendar",
        "get_events",
        {"start_date_time": "2026-11-03T00:00:00+01:00", "duration": {"hours": 24}},
        target={"entity_id": state.entity_id},
        blocking=True,
        return_response=True,
    )
    events = result[state.entity_id]["events"]
    assert [e["summary"] for e in events] == ["Charging from the grid", "Self-consumption"]
    assert _state(hass, "mode").attributes["plan_tomorrow"] == body["planJutro"]


async def test_inverter_counters_replace_the_estimates(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))
    body = _body()
    body["energiaDzis"]["ladowanieKwh"] = None  # this brand does not report battery charging
    await _setup(hass, aioclient_mock, body)
    registry = er.async_get(hass)
    serial = INSTALLATION["numerBramki"]
    assert float(_state(hass, "pv_energy_today").state) == 14.2
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_pv_energy") is None
    # The missing inverter counter is disabled and the estimate stands in for it.
    charge = registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_battery_charge_today")
    assert registry.async_get(charge).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert _state(hass, "battery_charge_energy").state == "0.0"


async def test_estimates_are_removed_once_the_inverter_reports_counters(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))
    entry = await _setup(hass, aioclient_mock, _without_inverter_counters(_body()))
    registry = er.async_get(hass)
    serial = INSTALLATION["numerBramki"]
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_pv_energy")

    aioclient_mock.clear_requests()
    aioclient_mock.get(API_URL, json=INSTALLATION)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_pv_energy") is None


async def test_value_today_resets_at_polish_midnight(hass, aioclient_mock, freezer):
    await hass.config.async_set_time_zone("America/New_York")
    freezer.move_to(READING + timedelta(seconds=30))
    await _setup(hass, aioclient_mock)
    state = _state(hass, "value_today")
    assert float(state.state) == 6.42
    assert state.attributes["from_system"] == 2.32
    assert state.attributes["last_reset"] == "2026-11-02T00:00:00+01:00"  # Polish midnight


async def test_prices_with_times_from_the_api_are_used(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))
    body = _body()
    body["ceny"]["godzinyDzis"] = [
        {"od": "2026-11-02T11:00:00.000Z", "do": "2026-11-02T12:00:00.000Z", "cena": 0.2},
        {"od": "2026-11-02T12:00:00.000Z", "do": "2026-11-02T13:00:00.000Z", "cena": 0.9},
    ]
    await _setup(hass, aioclient_mock, body)
    prices = _state(hass, "rce_price").attributes["prices"]
    assert prices[0] == {
        "start": "2026-11-02T12:00:00+01:00",
        "end": "2026-11-02T13:00:00+01:00",
        "price": 0.2,
    }


# ---------------------------------------------------------------- battery history


def test_sessions_group_hours_and_weigh_the_price():
    from custom_components.profitems.history import sessions  # noqa: PLC0415

    def hour(h, charge=0.0, discharge=0.0, imp=0.0, exp=0.0, price=0.5, mode="samokonsumpcja"):
        return {
            "start": f"2026-11-02T{h:02d}:00:00+01:00", "end": f"2026-11-02T{h + 1:02d}:00:00+01:00",
            "charge_kwh": charge, "discharge_kwh": discharge, "import_kwh": imp, "export_kwh": exp,
            "price": price, "mode": mode, "soc_start": 10 * h, "soc_end": 10 * h + 10,
        }

    result = sessions([
        hour(1, charge=3.0, imp=3.2, price=0.3, mode="ladowanie_z_sieci"),
        hour(2, charge=1.0, imp=1.1, price=0.5, mode="ladowanie_z_sieci"),
        hour(3),  # idle
        hour(18, discharge=2.0, exp=1.8, price=1.6, mode="sprzedaz"),
    ])
    assert [s["activity"] for s in result] == ["charging", "discharging"]
    charge = result[0]
    assert (charge["start"], charge["end"]) == ("2026-11-02T01:00:00+01:00", "2026-11-02T03:00:00+01:00")
    assert charge["energy_kwh"] == 4.0
    assert charge["average_price"] == round((3 * 0.3 + 1 * 0.5) / 4, 4)
    assert charge["value_pln"] == round(4.3 * charge["average_price"], 2)
    assert (charge["soc_start"], charge["soc_end"]) == (10, 30)
    assert result[1]["mode"] == "sprzedaz"


async def test_battery_history_follows_the_readings(hass, aioclient_mock, freezer):
    freezer.move_to(READING + timedelta(seconds=30))
    body = _body()
    body["teraz"]["bateriaW"] = -3000
    body["teraz"]["siecW"] = 3200
    body["system"]["tryb"] = "ladowanie_z_sieci"
    await _setup(hass, aioclient_mock, body)
    assert _state(hass, "battery_activity").state == "charging"

    later = READING + timedelta(minutes=5)
    body = copy.deepcopy(body)
    body["polaczenie"]["ostatniOdczyt"] = later.isoformat()
    aioclient_mock.clear_requests()
    aioclient_mock.get(API_URL, json=body)
    freezer.move_to(later + timedelta(seconds=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    attributes = _state(hass, "battery_activity").attributes
    (hour,) = attributes["hours"]
    assert hour["start"] == "2026-11-02T13:00:00+01:00"
    assert hour["charge_kwh"] == 0.25  # 3 kW for 5 minutes
    assert hour["price"] == 2.1941
    (session,) = attributes["sessions"]
    assert session["activity"] == "charging"
    assert session["mode"] == "ladowanie_z_sieci"

// A stand-in for Home Assistant's hass object, so the card can be seen without an installation.
// Prices, plan and readings are examples.
const DEMO_PRICES = [0.42,0.38,0.31,0.29,0.30,0.36,0.48,0.62,0.66,0.58,0.49,0.41,0.37,0.39,0.46,0.58,0.74,0.92,0.98,0.89,0.71,0.58,0.50,0.45];
const DEMO_TOMORROW = [0.44,0.40,0.35,0.33,0.32,0.37,0.51,0.67,0.71,0.60,0.47,0.36,0.30,0.32,0.43,0.57,0.79,0.96,1.04,0.93,0.74,0.60,0.52,0.47];
const DEMO_PLAN = [
  { od: "00:00", do: "01:00", tryb: "samokonsumpcja" }, { od: "01:00", do: "05:00", tryb: "ladowanie_z_sieci" },
  { od: "05:00", do: "07:00", tryb: "rezerwa" }, { od: "07:00", do: "17:00", tryb: "samokonsumpcja" },
  { od: "17:00", do: "21:00", tryb: "sprzedaz" }, { od: "21:00", do: "24:00", tryb: "samokonsumpcja" },
];

const DEMO_PLAN_TOMORROW = [
  { od: "00:00", do: "05:00", tryb: "ladowanie_z_sieci" }, { od: "05:00", do: "08:00", tryb: "rezerwa" },
  { od: "08:00", do: "16:00", tryb: "samokonsumpcja" }, { od: "16:00", do: "20:00", tryb: "sprzedaz" },
  { od: "20:00", do: "24:00", tryb: "samokonsumpcja" },
];

const DEMO_SCENARIOS = {
  poludnie: { label: "Południe, nadwyżka", time: "12:40", soc: 78, pv: 4820, dom: 1150, bat: -2400, siec: -1270, tryb: "samokonsumpcja", od: "07:00", nadW: 3670, weather: "partlycloudy", temp: 9, elevation: 22 },
  pelny: { label: "Magazyn pełny", time: "13:30", soc: 100, pv: 5600, dom: 900, bat: 0, siec: -4700, tryb: "samokonsumpcja", od: "07:00", nadW: 4700, full: true, weather: "sunny", temp: 11, elevation: 20 },
  szczyt: { label: "Wieczór, sprzedaż, deszcz", time: "18:20", soc: 58, pv: 0, dom: 1900, bat: 4300, siec: -2400, tryb: "sprzedaz", od: "17:00", weather: "rainy", temp: 6, elevation: -14 },
  noc: { label: "Noc, ładowanie z sieci", time: "03:20", soc: 41, pv: 0, dom: 380, bat: -3600, siec: 3980, tryb: "ladowanie_z_sieci", od: "01:00", noTomorrow: true, weather: "clear-night", temp: 2, elevation: -40 },
  snieg: { label: "Śnieg, ceny co 15 minut", time: "10:50", soc: 63, pv: 640, dom: 1400, bat: 760, siec: 0, tryb: "samokonsumpcja", od: "07:00", weather: "snowy", temp: -3, elevation: 12, quarter: true },
  wyspa: { label: "Praca wyspowa, burza", time: "15:10", soc: 66, pv: 1200, dom: 1650, bat: 450, siec: 0, tryb: "samokonsumpcja", od: "07:00", island: true, conn: "opozniona", age: 9, weather: "lightning-rainy", temp: 14, elevation: 4 },
};

// Warsaw local time on 5 November 2026 (UTC+1) as a Date.
function demoDate(hm, dayOffset = 0) {
  const [h, m] = hm.split(":").map(Number);
  return new Date(Date.UTC(2026, 10, 5 + dayOffset, h - 1, m));
}

function demoSlots(values, dayOffset) {
  const step = values.length === 96 ? 15 : 60;
  return values.map((price, i) => {
    const start = new Date(demoDate("00:00", dayOffset).getTime() + i * step * 60000);
    return { start: start.toISOString(), end: new Date(start.getTime() + step * 60000).toISOString(), price };
  });
}

function demoHass(key, language = "pl") {
  const s = DEMO_SCENARIOS[key];
  const now = demoDate(s.time);
  const today = s.quarter ? DEMO_PRICES.flatMap((p, h) => [0, 1, 2, 3].map((q) => +(p + (q - 1.5) * 0.015 * (h % 3 ? 1 : -1)).toFixed(4))) : DEMO_PRICES;
  const slots = [...demoSlots(today, 0), ...(s.noTomorrow ? [] : demoSlots(DEMO_TOMORROW, 1))];
  const nowH = +s.time.slice(0, 2);
  const minH = DEMO_PRICES.indexOf(Math.min(...DEMO_PRICES));
  const plan = DEMO_PLAN.filter((p) => p.do > s.time);
  const exportKwh = { poludnie: 6.2, pelny: 9.4, szczyt: 14.1, noc: 0.0, snieg: 0.3, wyspa: 2.1 }[key];
  const importKwh = { poludnie: 9.8, pelny: 9.8, szczyt: 10.3, noc: 7.2, snieg: 12.0, wyspa: 9.9 }[key];
  const states = {};
  const entities = {};
  const add = (id, key, state, attributes = {}) => {
    states[id] = { entity_id: id, state: String(state), attributes, last_updated: now.toISOString() };
    if (key) entities[id] = { entity_id: id, device_id: "demo", platform: "profitems", translation_key: key };
  };
  const P = "sensor.profitems_pe_26_0142_";
  add(P + "battery", "battery_level", s.soc, { device_class: "battery" });
  add(P + "pv", "pv_power", s.pv); add(P + "home", "home_power", s.dom); add(P + "grid", "grid_power", s.siec);
  add(P + "battery_power", "battery_power", s.bat); add(P + "surplus", "pv_surplus", s.nadW ?? 0);
  const lateEvening = s.time >= "22:00";
  add(P + "mode", "mode", s.tryb, {
    since: demoDate(s.od).toISOString(), plan, plan_today: DEMO_PLAN,
    plan_tomorrow: lateEvening || key === "szczyt" ? DEMO_PLAN_TOMORROW : null,
  });
  add(P + "rce", "rce_price", DEMO_PRICES[nowH], { prices: slots });
  add(P + "connection", "connection", s.conn || "online");
  add(P + "last_reading", "last_reading", new Date(now.getTime() - (s.age ?? 2) * 60000).toISOString());
  add(P + "export_value", "grid_export_value", 812.4, { today: +(exportKwh * 0.71).toFixed(2) });
  add(P + "import_value", "grid_import_value", 455.1, { today: +(importKwh * 0.36).toFixed(2) });
  add(P + "export_energy", "grid_export_energy", 1520.2, { today: exportKwh });
  add(P + "import_energy", "grid_import_energy", 1210.7, { today: importKwh });
  const profit = { poludnie: [6.42, 4.10, 2.32, 1.85], pelny: [8.90, 5.60, 3.30, 4.20], szczyt: [14.75, 4.30, 10.45, 9.60], noc: [0.84, 0, 0.84, 0], snieg: [1.12, 0.40, 0.72, 0.15], wyspa: [3.05, 1.90, 1.15, 0.80] }[key];
  add(P + "value_today", "value_today", profit[0], { from_panels: profit[1], from_system: profit[2], export_revenue: profit[3], data_coverage: 98, calculated_at: new Date(now.getTime() - 25 * 60000).toISOString() });
  add(P + "export_today", "grid_export_today", exportKwh);
  add(P + "import_today", "grid_import_today", importKwh);
  add("binary_sensor.profitems_pe_26_0142_surplus", "pv_surplus_active", (s.nadW ?? 0) > 0 ? "on" : "off");
  add("binary_sensor.profitems_pe_26_0142_full", "battery_full", s.full ? "on" : "off");
  add("binary_sensor.profitems_pe_26_0142_cheapest", "cheapest_hour_now", nowH === minH ? "on" : "off");
  add("binary_sensor.profitems_pe_26_0142_island", "island_mode", s.island ? "on" : "off");
  add("weather.dom", null, s.weather, { temperature: s.temp, temperature_unit: "°C" });
  add("sun.sun", null, s.elevation > 0 ? "above_horizon" : "below_horizon", { elevation: s.elevation });
  return {
    states, entities, language, locale: { language },
    devices: { demo: { id: "demo", name: "ProfitEMS PE-26-0142", serial_number: "PE-26-0142" } },
    demoNow: now,
  };
}

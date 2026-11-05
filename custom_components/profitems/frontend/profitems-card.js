/*
 * ProfitEMS card for Home Assistant dashboards.
 * Served by the ProfitEMS integration and loaded on every dashboard; add it as
 * "type: custom:profitems-card". It reads only the integration's entities (and,
 * optionally, a weather entity and sun.sun), so it adds no requests to the ProfitEMS API.
 *
 * Copyright (c) 2026 gratak. PolyForm Noncommercial License 1.0.0, see LICENSE.
 */
(() => {
  const CARD_VERSION = "0.2.0";
  const TZ = "Europe/Warsaw";
  const SVG = "http://www.w3.org/2000/svg";

  // ------------------------------------------------------------------ texts
  const TEXTS = {
    pl: {
      home: "Dom", fromRoof: "z dachu", inHome: "w domu", import: "pobór", export: "oddawanie", gridIdle: "sieć",
      noGrid: "brak sieci", charging: "ładowanie", discharging: "rozładowanie", idle: "czuwa", full: "pełny",
      since: "od", reading: "odczyt", minAgo: (m) => (m < 1 ? "przed chwilą" : `${m} min temu`),
      conn: { online: "Połączono", opozniona: "Opóźnione", offline: "Brak połączenia" },
      island: "Praca wyspowa", pricesPlan: "Ceny i plan", rceNet: "RCE netto", today: "Dziś", tomorrow: "Jutro",
      tomorrowLater: "Ceny na jutro pojawiają się po południu", planTomorrow: "Plan na jutro system ułoży po północy",
      cheapest: "najtańsza", now: "teraz", surplus: "Nadwyżka z paneli", batteryFull: "Magazyn pełny",
      cheapestHour: "Najtańsza godzina", runningNow: "trwa teraz", none: "brak", yes: "tak", no: "nie",
      value: "Bilans dnia wg RCE", sold: "Sprzedaż", bought: "Zakup", balance: "Bilans",
      valueNote: "Szacunek z odczytów co 5 minut, po cenach RCE netto, bez opłat dystrybucyjnych.",
      forecast: "Prognoza", noData: "Brak danych z bramki", pickDevice: "Wybierz bramkę ProfitEMS w ustawieniach karty.",
      next: (mode, at) => `Dalej w planie: ${mode.toLowerCase()} od ${at}.`, noNext: "Do końca doby bez zmian w planie.",
      m: {
        island: "Brak zasilania z sieci. Dom pracuje na panelach i magazynie.",
        full: (p) => `Magazyn pełny, ${p} płynie do sieci. Dobry moment na grzałkę albo ładowanie auta.`,
        sell: (c) => `Magazyn sprzedaje energię do sieci przy cenie ${c}.`,
        charge: (c) => `Magazyn ładuje się z sieci w tanich godzinach, teraz ${c}.`,
        surplus: (p) => `Panele dają o ${p} więcej, niż zużywa dom.`,
        observe: "System uczy się instalacji i na razie tylko obserwuje.",
        plain: "Dom korzysta z energii z paneli i magazynu.",
        offline: "Bramka nie przesyła danych. Wartości wrócą po odzyskaniu połączenia.",
      },
      modes: {
        samokonsumpcja: "Samokonsumpcja", ladowanie_ograniczone: "Ładowanie ograniczone", ladowanie_z_sieci: "Ładowanie z sieci",
        sprzedaz: "Sprzedaż do sieci", rezerwa: "Rezerwa", zasilanie_domu: "Zasilanie domu", blokada_oddawania: "Blokada oddawania",
        wstrzymany: "Wstrzymany", obserwacja: "Obserwacja",
      },
      weather: {
        sunny: "słonecznie", "clear-night": "pogodnie", partlycloudy: "częściowe zachmurzenie", cloudy: "pochmurno",
        rainy: "deszcz", pouring: "ulewa", snowy: "śnieg", "snowy-rainy": "deszcz ze śniegiem", fog: "mgła",
        lightning: "burza", "lightning-rainy": "burza z deszczem", hail: "grad", windy: "wietrznie", "windy-variant": "wietrznie", exceptional: "niebezpieczna pogoda",
      },
      ed: {
        device: "Bramka ProfitEMS", theme: "Motyw", title: "Tytuł", weather_entity: "Encja pogody", show_weather: "Pogoda w motywie",
        price_resolution: "Ceny", show_status: "Status", show_moment: "Opis chwili", show_prices: "Ceny i plan",
        show_value: "Bilans dnia", show_signals: "Sygnały", load_fonts: "Czcionki motywu z Google Fonts",
        auto: "Jak w danych (godzina albo 15 minut)", hour: "Uśrednione do godzin",
      },
    },
    en: {
      home: "Home", fromRoof: "from the roof", inHome: "in the home", import: "import", export: "export", gridIdle: "grid",
      noGrid: "grid down", charging: "charging", discharging: "discharging", idle: "idle", full: "full",
      since: "since", reading: "reading", minAgo: (m) => (m < 1 ? "just now" : `${m} min ago`),
      conn: { online: "Connected", opozniona: "Delayed", offline: "Offline" },
      island: "Island mode", pricesPlan: "Prices and plan", rceNet: "RCE net", today: "Today", tomorrow: "Tomorrow",
      tomorrowLater: "Tomorrow's prices are published in the afternoon", planTomorrow: "The plan for tomorrow is made after midnight",
      cheapest: "cheapest", now: "now", surplus: "Solar surplus", batteryFull: "Battery full",
      cheapestHour: "Cheapest hour", runningNow: "now", none: "none", yes: "yes", no: "no",
      value: "Today at RCE prices", sold: "Sold", bought: "Bought", balance: "Balance",
      valueNote: "Estimated from 5-minute readings at net RCE prices, without distribution fees.",
      forecast: "Forecast", noData: "No data from the gateway", pickDevice: "Choose a ProfitEMS gateway in the card settings.",
      next: (mode, at) => `Next in the plan: ${mode.toLowerCase()} from ${at}.`, noNext: "No changes planned until midnight.",
      m: {
        island: "The grid is down. The home runs on solar and the battery.",
        full: (p) => `The battery is full and ${p} flows to the grid. A good moment for a water heater or the car.`,
        sell: (c) => `The battery sells energy to the grid at ${c}.`,
        charge: (c) => `The battery charges from the grid in cheap hours, now ${c}.`,
        surplus: (p) => `The panels produce ${p} more than the home uses.`,
        observe: "The system is learning the installation and only observes for now.",
        plain: "The home runs on solar and the battery.",
        offline: "The gateway sends no data. Values return once it reconnects.",
      },
      modes: {
        samokonsumpcja: "Self-consumption", ladowanie_ograniczone: "Limited charging", ladowanie_z_sieci: "Charging from the grid",
        sprzedaz: "Selling to the grid", rezerwa: "Reserve", zasilanie_domu: "Powering the home", blokada_oddawania: "Export blocked",
        wstrzymany: "Paused", obserwacja: "Observation",
      },
      weather: {
        sunny: "sunny", "clear-night": "clear", partlycloudy: "partly cloudy", cloudy: "cloudy", rainy: "rain", pouring: "pouring",
        snowy: "snow", "snowy-rainy": "sleet", fog: "fog", lightning: "thunderstorm", "lightning-rainy": "thunderstorm and rain",
        hail: "hail", windy: "windy", "windy-variant": "windy", exceptional: "severe weather",
      },
      ed: {
        device: "ProfitEMS gateway", theme: "Theme", title: "Title", weather_entity: "Weather entity", show_weather: "Weather in the theme",
        price_resolution: "Prices", show_status: "Status", show_moment: "Moment", show_prices: "Prices and plan",
        show_value: "Today's balance", show_signals: "Signals", load_fonts: "Theme fonts from Google Fonts",
        auto: "As in the data (hour or 15 minutes)", hour: "Averaged to hours",
      },
    },
  };

  // ------------------------------------------------------------------ themes
  const THEMES = {
    diorama: {
      name: "Diorama",
      vars: {
        bg: "#ffffff", surface: "#f3f7fb", border: "#e3eaf1", text: "#24364a", muted: "#6a7d92", accent: "#3b82f6",
        pv: "#f5a400", bat: "#1fbf86", grid: "#5b8def", home: "#f26b5b", track: "#e7eef4", "tab-on-bg": "#ffffff", "tab-on": "#24364a",
        warn: "#c96f1c", "warn-soft": "#fff1e2", bad: "#d64545", on: "#16865d", "on-bg": "#e3f7ee", "on-border": "#bfe9d6", plain: "#ffffff",
        good: "#1f9d55",
        font: '"Nunito", ui-rounded, "SF Pro Rounded", "Segoe UI", Roboto, system-ui, sans-serif',
        num: '"Nunito", ui-rounded, "SF Pro Rounded", "Segoe UI", Roboto, system-ui, sans-serif',
        head: '"Nunito", ui-rounded, "Segoe UI", Roboto, system-ui, sans-serif', "head-w": "800", "head-ls": "0",
        shadow: "0 18px 50px rgba(30,70,110,.16)", frame: "transparent", r: "28px", tr: "16px",
      },
      cheap: "#2bc48f", dear: "#f26b5b", gridline: "#e3eaf1", label: "#8697a8", past: 0.35, barR: 3,
      modes: { samokonsumpcja: "#ffc23d", ladowanie_z_sieci: "#7aa4f2", sprzedaz: "#f26b5b", rezerwa: "#2bc48f", ladowanie_ograniczone: "#f7d98a", zasilanie_domu: "#ff9d7a", blokada_oddawania: "#b6c3d1", wstrzymany: "#ccd5de", obserwacja: "#d9e1e8" },
      fonts: "family=Nunito:wght@500;700;800",
    },
    aurora: {
      name: "Aurora",
      vars: {
        bg: "radial-gradient(60% 40% at 15% 0%, rgba(0,255,200,.16), transparent 70%), radial-gradient(50% 40% at 100% 30%, rgba(140,80,255,.2), transparent 70%), radial-gradient(70% 50% at 50% 110%, rgba(255,60,160,.14), transparent 70%), #0a0d1a",
        surface: "rgba(255,255,255,.035)", border: "rgba(255,255,255,.09)", text: "#e9f1ff", muted: "#8390b8", accent: "#4dffd2",
        pv: "#ffd23f", bat: "#4dffd2", grid: "#a28bff", home: "#ff4fa3", track: "rgba(255,255,255,.07)", "tab-on-bg": "#4dffd2", "tab-on": "#0a0d1a",
        warn: "#ffb547", "warn-soft": "rgba(255,181,71,.1)", bad: "#ff6b6b", on: "#4dffd2", "on-bg": "rgba(77,255,210,.08)", "on-border": "rgba(77,255,210,.4)",
        plain: "#0f1324", good: "#4dffd2",
        font: '"Space Grotesk", "Segoe UI", Roboto, system-ui, sans-serif',
        num: '"JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace',
        head: '"Space Grotesk", "Segoe UI", Roboto, system-ui, sans-serif', "head-w": "700", "head-ls": "0",
        shadow: "0 30px 80px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.06)", frame: "rgba(255,255,255,.06)", r: "28px", tr: "14px",
      },
      cheap: "#4dffd2", dear: "#ff4fa3", gridline: "rgba(255,255,255,.07)", label: "#6c7799", past: 0.3, barR: 2, glow: true,
      modes: { samokonsumpcja: "#ffd23f", ladowanie_z_sieci: "#a28bff", sprzedaz: "#ff4fa3", rezerwa: "#4dffd2", ladowanie_ograniczone: "#c9b45a", zasilanie_domu: "#ff8fc6", blokada_oddawania: "#59607e", wstrzymany: "#3c425c", obserwacja: "#343a52" },
      fonts: "family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@500;700",
    },
    foundation: {
      name: "Foundation",
      vars: {
        bg: "radial-gradient(60% 40% at 50% 26%, rgba(232,196,122,.13), transparent 70%), radial-gradient(120% 80% at 50% 120%, #1a1408, transparent 60%), #07070a",
        surface: "rgba(232,196,122,.035)", border: "rgba(232,196,122,.2)", text: "#f1e6cf", muted: "#a8946c", accent: "#e8c47a",
        pv: "#f3cf7a", bat: "#c99a4a", grid: "#8fa6c8", home: "#f1e6cf", track: "rgba(232,196,122,.1)", "tab-on-bg": "rgba(232,196,122,.18)", "tab-on": "#f8edd4",
        warn: "#e8a35a", "warn-soft": "rgba(232,163,90,.08)", bad: "#e07a5f", on: "#f3cf7a", "on-bg": "rgba(232,196,122,.09)", "on-border": "rgba(232,196,122,.55)",
        plain: "#0c0b0c", good: "#f3cf7a",
        font: '"Cormorant Garamond", Garamond, "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif',
        num: '"Cinzel", "Trajan Pro", "Iowan Old Style", "Palatino Linotype", Georgia, serif',
        head: '"Cinzel", "Trajan Pro", "Iowan Old Style", Georgia, serif', "head-w": "400", "head-ls": ".18em",
        shadow: "none", frame: "rgba(232,196,122,.35)", r: "2px", tr: "0px",
      },
      cheap: "#8fa6c8", dear: "#f3cf7a", gridline: "rgba(232,196,122,.1)", label: "#7d6d4f", past: 0.3, barR: 0,
      modes: { samokonsumpcja: "#c99a4a", ladowanie_z_sieci: "#8fa6c8", sprzedaz: "#f3cf7a", rezerwa: "#6f5a33", ladowanie_ograniczone: "#a38755", zasilanie_domu: "#e0c9a0", blokada_oddawania: "#4a4335", wstrzymany: "#3a3428", obserwacja: "#2f2a20" },
      fonts: "family=Cinzel:wght@400;600&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500",
    },
  };

  // Entities of the integration, found by their translation key (battery level by device class).
  const KEYS = [
    "battery_level", "pv_power", "home_power", "grid_power", "battery_power", "pv_surplus", "mode", "rce_price",
    "connection", "last_reading", "grid_export_value", "grid_import_value", "grid_export_energy", "grid_import_energy",
    "pv_energy", "pv_surplus_active", "battery_full", "cheapest_hour_now", "island_mode",
  ];

  // ------------------------------------------------------------------ helpers
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const num = (v) => { const n = Number(v); return v === null || v === undefined || v === "" || Number.isNaN(n) ? null : n; };
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  function hex(c) { const n = parseInt(c.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; }
  function mix(a, b, t) { const A = hex(a), B = hex(b); return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(",")})`; }
  const warsaw = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  function wParts(d) {
    const p = Object.fromEntries(warsaw.formatToParts(d).map((x) => [x.type, x.value]));
    return { day: `${p.year}-${p.month}-${p.day}`, h: +p.hour, m: +p.minute, hm: `${p.hour}:${p.minute}` };
  }
  const durFor = (w) => Math.max(0.7, 3.2 - Math.abs(w) / 1000 * 0.45).toFixed(2) + "s";

  // Weather condition -> what the themes draw.
  function weatherLook(condition) {
    const c = condition || "";
    return {
      clouds: { sunny: 0, "clear-night": 0, partlycloudy: 1, windy: 1, "windy-variant": 2, cloudy: 3, fog: 2, rainy: 3, pouring: 3, snowy: 3, "snowy-rainy": 3, lightning: 3, "lightning-rainy": 3, hail: 3, exceptional: 3 }[c] ?? 0,
      rain: { rainy: 1, "lightning-rainy": 1, "snowy-rainy": 1, pouring: 2, hail: 2 }[c] ?? 0,
      snow: c === "snowy" || c === "snowy-rainy",
      fog: c === "fog",
      storm: c === "lightning" || c === "lightning-rainy",
    };
  }

  class ProfitEmsCard extends HTMLElement {
    static getConfigElement() { return document.createElement("profitems-card-editor"); }
    static getStubConfig() { return { theme: "diorama" }; }

    setConfig(config) {
      if (config.theme && !THEMES[config.theme]) throw new Error(`Unknown theme: ${config.theme}`);
      this._config = {
        theme: "diorama", show_weather: true, price_resolution: "auto", show_status: true, show_moment: true,
        show_prices: true, show_value: true, show_signals: true, load_fonts: false, ...config,
      };
      this._sel = null;
      this._day = "today";
      this._sig = null;
      if (this._config.load_fonts) loadFonts(this._config.theme);
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      const sig = this._signature();
      if (sig !== this._sig) { this._sig = sig; this._render(); }
    }

    connectedCallback() {
      // The "now" marker and the reading's age move even when no entity changes.
      this._tick = setInterval(() => { this._sig = null; this._render(); }, 60000);
    }
    disconnectedCallback() { clearInterval(this._tick); }

    getCardSize() { return 12; }
    getGridOptions() { return { columns: 12, min_columns: 6 }; }

    get _t() {
      const lang = (this._config?.language || this._hass?.locale?.language || this._hass?.language || "pl").slice(0, 2);
      return TEXTS[lang] || TEXTS.en;
    }

    // ---------------------------------------------------------- entities
    _entities() {
      const hass = this._hass;
      if (!hass?.entities) return {};
      let device = this._config.device;
      const mine = Object.values(hass.entities).filter((e) => e.platform === "profitems" && (!device || e.device_id === device));
      if (!device && mine.length) { device = mine[0].device_id; }
      const found = {};
      for (const e of mine) {
        if (e.device_id !== device) continue;
        let key = e.translation_key;
        if (!key && hass.states[e.entity_id]?.attributes?.device_class === "battery") key = "battery_level";
        if (key && !found[key]) found[key] = e.entity_id;
      }
      found._device = device;
      return found;
    }

    _weatherEntity() {
      if (!this._config.show_weather) return null;
      if (this._config.weather_entity) return this._config.weather_entity;
      return Object.keys(this._hass?.states || {}).find((id) => id.startsWith("weather.")) || null;
    }

    _signature() {
      const hass = this._hass;
      if (!hass) return "";
      const ids = Object.values(this._entities()).filter((v) => typeof v === "string" && v.includes("."));
      const w = this._weatherEntity();
      if (w) ids.push(w);
      ids.push("sun.sun");
      return ids.map((id) => hass.states[id]?.last_updated || "").join("|");
    }

    // ---------------------------------------------------------- data
    _data() {
      const hass = this._hass, ids = this._entities();
      const st = (k) => (ids[k] ? hass.states[ids[k]] : undefined);
      const val = (k) => num(st(k)?.state);
      const on = (k) => st(k)?.state === "on";
      const price = st("rce_price");
      const mode = st("mode");
      const wid = this._weatherEntity();
      const weather = wid ? hass.states[wid] : undefined;
      const sun = hass.states["sun.sun"];
      const lastReading = st("last_reading")?.state;
      const reading = lastReading && !["unknown", "unavailable"].includes(lastReading) ? new Date(lastReading) : null;
      const today = (k) => num(st(k)?.attributes?.today);
      return {
        found: Boolean(ids.mode || ids.pv_power),
        name: this._config.title || (ids._device && hass.devices?.[ids._device]?.name_by_user) || this._t.home,
        serial: ids._device && hass.devices?.[ids._device]?.serial_number,
        soc: val("battery_level"), pv: val("pv_power"), dom: val("home_power"), siec: val("grid_power"), bat: val("battery_power"),
        nadW: val("pv_surplus"), surplus: on("pv_surplus_active"), full: on("battery_full"), cheapNow: on("cheapest_hour_now"),
        island: on("island_mode"), conn: st("connection")?.state, reading,
        tryb: mode?.state, od: mode?.attributes?.since, plan: mode?.attributes?.plan_today || mode?.attributes?.plan || [],
        price: val("rce_price"), slots: price?.attributes?.prices || [],
        value: {
          sold: today("grid_export_value"), bought: today("grid_import_value"),
          soldKwh: today("grid_export_energy"), boughtKwh: today("grid_import_energy"), hasValue: Boolean(ids.grid_export_value),
        },
        weather: weather && { condition: weather.state, temp: num(weather.attributes?.temperature), unit: weather.attributes?.temperature_unit || "°C" },
        elevation: num(sun?.attributes?.elevation),
      };
    }

    // ---------------------------------------------------------- formatting
    _kw(w) {
      if (w === null) return "–";
      const a = Math.abs(w), loc = this._t === TEXTS.pl ? "pl-PL" : "en-GB";
      return a < 1000 ? `${Math.round(a)}\u00a0W` : `${(a / 1000).toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}\u00a0kW`;
    }
    _kwParts(w) { const s = this._kw(w); const i = s.lastIndexOf("\u00a0"); return [s.slice(0, i), s.slice(i + 1)]; }
    _n(v, d) { return v === null ? "–" : v.toLocaleString(this._t === TEXTS.pl ? "pl-PL" : "en-GB", { minimumFractionDigits: d, maximumFractionDigits: d }); }
    _zl(p) { return p === null ? "–" : `${this._n(p, 2)}\u00a0zł/kWh`; }
    _pln(v, sign) { if (v === null) return "–"; const s = sign ? (v > 0.004 ? "+" : v < -0.004 ? "−" : "") : ""; return `${s}${this._n(Math.abs(v), 2)}\u00a0zł`; }
    _mode(m) { return this._t.modes[m] || m || "–"; }
    _since(iso) { return iso ? wParts(new Date(iso)).hm : null; }

    _phase(d) {
      const e = d.elevation;
      if (e !== null) return e > 6 ? "day" : e > -6 ? "dusk" : "night";
      const h = wParts(new Date()).h;
      return h >= 8 && h < 16 ? "day" : (h >= 6 && h < 8) || (h >= 16 && h < 18) ? "dusk" : "night";
    }

    _moment(d) {
      const t = this._t, nowHm = wParts(new Date()).hm;
      let main;
      if (d.conn === "offline") main = t.m.offline;
      else if (d.island) main = t.m.island;
      else if (d.tryb === "obserwacja") main = t.m.observe;
      else if (d.full && (d.siec ?? 0) < -100) main = t.m.full(this._kw(d.siec));
      else if (d.tryb === "sprzedaz") main = t.m.sell(this._zl(d.price));
      else if (d.tryb === "ladowanie_z_sieci") main = t.m.charge(this._zl(d.price));
      else if (d.surplus && d.nadW) main = t.m.surplus(this._kw(d.nadW));
      else main = t.m.plain;
      const nb = d.plan.find((p) => p.od > nowHm && p.tryb !== d.tryb);
      return { main, next: nb ? t.next(this._mode(nb.tryb), nb.od) : d.plan.length ? t.noNext : "" };
    }

    // ---------------------------------------------------------- render
    _render() {
      if (!this._config) return;
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      const root = this.shadowRoot, theme = THEMES[this._config.theme], t = this._t;
      if (!this._hass) { root.innerHTML = ""; return; }
      const d = this._data();
      const vars = Object.entries(theme.vars).map(([k, v]) => `--c-${k}:${v}`).join(";");
      let inner;
      if (!d.found) {
        inner = `<div class="empty"><b>${esc(t.noData)}</b><span>${esc(t.pickDevice)}</span></div>`;
      } else {
        const c = this._config, m = this._moment(d);
        inner = `${this[`_hero_${c.theme}`](theme, d)}
          <div class="body">
            ${c.show_status ? this._status(theme, d) : ""}
            ${c.show_moment ? `<p class="moment" data-label="${esc(t.forecast)}">${esc(m.main)}${m.next ? `<small>${esc(m.next)}</small>` : ""}</p>` : ""}
            ${c.show_prices ? this._timeline(theme, d) : ""}
            ${c.show_value && d.value.hasValue ? this._value(d) : ""}
            ${c.show_signals ? this._signals(d) : ""}
          </div>`;
      }
      root.innerHTML = `<style>${STYLES}</style><ha-card class="card t-${this._config.theme}" style='${vars}'>${inner}</ha-card>`;
      this._bind();
    }

    _bind() {
      const root = this.shadowRoot;
      root.querySelectorAll(".hit").forEach((r) => {
        const pick = () => { const i = +r.dataset.i; if (this._sel !== i) { this._sel = i; this._render(); } };
        r.addEventListener("mouseenter", pick); r.addEventListener("click", pick);
      });
      const svg = root.querySelector(".tl svg");
      if (svg) svg.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        const n = root.querySelectorAll(".hit").length;
        this._sel = clamp((this._sel ?? this._defaultSel ?? 0) + (e.key === "ArrowRight" ? 1 : -1), 0, n - 1);
        this._render();
        this.shadowRoot.querySelector(".tl svg")?.focus();
      });
      root.querySelectorAll(".tl-toggle button").forEach((b) => b.addEventListener("click", () => {
        this._day = b.dataset.day; this._sel = null; this._render();
      }));
    }

    _status(T, d) {
      const t = this._t;
      const connColor = { online: T.vars.on, opozniona: T.vars.warn, offline: T.vars.bad }[d.conn] || T.vars.muted;
      const age = d.reading ? Math.max(0, Math.round((Date.now() - d.reading) / 60000)) : null;
      const since = this._since(d.od);
      return `<div class="status">
        <span class="pill mode" style="--dot:${T.modes[d.tryb] || T.vars.muted}"><i></i>${esc(this._mode(d.tryb))}${since ? ` <small>${t.since} ${since}</small>` : ""}</span>
        <span class="pill" style="--dot:${connColor}"><i></i>${esc(t.conn[d.conn] || "–")}${age !== null ? ` <small>${t.reading} ${t.minAgo(age)}</small>` : ""}</span>
        ${d.island ? `<span class="pill island">${t.island}</span>` : ""}
      </div>`;
    }

    _signals(d) {
      const t = this._t;
      const cheapest = d.slots.length ? this._cheapestOfDay(d.slots, wParts(new Date()).day) : null;
      return `<div class="signals">
        <div class="sig ${d.surplus ? "on" : ""}"><small>${t.surplus}</small><b>${d.surplus && d.nadW ? this._kw(d.nadW) : t.none}</b></div>
        <div class="sig ${d.full ? "on" : ""}"><small>${t.batteryFull}</small><b>${d.full ? t.yes : t.no}</b></div>
        <div class="sig ${d.cheapNow ? "on" : ""}"><small>${t.cheapestHour}</small><b>${d.cheapNow ? t.runningNow : cheapest ? wParts(new Date(cheapest.start)).hm : "–"}</b></div>
      </div>`;
    }

    _value(d) {
      const t = this._t, v = d.value;
      const bal = v.sold !== null && v.bought !== null ? v.sold - v.bought : null;
      const kwh = (x) => (x === null ? "" : `<small>${this._n(x, 1)} kWh</small>`);
      return `<section class="value">
        <h3>${t.value}</h3>
        <div class="value-row">
          <div><span>${t.sold}</span><b class="good">${this._pln(v.sold, false)}</b>${kwh(v.soldKwh)}</div>
          <div><span>${t.bought}</span><b>${this._pln(v.bought, false)}</b>${kwh(v.boughtKwh)}</div>
          <div class="bal"><span>${t.balance}</span><b class="${bal > 0 ? "good" : bal < 0 ? "bad" : ""}">${this._pln(bal, true)}</b></div>
        </div>
        <p>${t.valueNote}</p>
      </section>`;
    }

    _cheapestOfDay(slots, day) {
      let best = null;
      for (const s of slots) if (wParts(new Date(s.start)).day === day && (!best || s.price < best.price)) best = s;
      return best;
    }

    // Slots of the chosen day, averaged to hours when asked.
    _daySlots(d) {
      const todayKey = wParts(new Date()).day;
      const all = d.slots.map((s) => ({ start: new Date(s.start), end: new Date(s.end), price: num(s.price) })).filter((s) => s.price !== null);
      const byDay = { today: [], tomorrow: [] };
      for (const s of all) (wParts(s.start).day === todayKey ? byDay.today : byDay.tomorrow).push(s);
      const pick = (list) => {
        if (this._config.price_resolution !== "hour" || !list.length || list[0].end - list[0].start >= 3600000) return list;
        const hours = [];
        for (const s of list) {
          const h = hours[hours.length - 1];
          const hourStart = new Date(Math.floor(s.start / 3600000) * 3600000);
          if (h && +h.start === +hourStart) { h.sum += s.price * (s.end - s.start); h.len += s.end - s.start; h.end = s.end; }
          else hours.push({ start: hourStart, end: s.end, sum: s.price * (s.end - s.start), len: s.end - s.start });
        }
        return hours.map((h) => ({ start: h.start, end: h.end, price: h.sum / h.len }));
      };
      return { today: pick(byDay.today), tomorrow: pick(byDay.tomorrow) };
    }

    _timeline(T, d) {
      const t = this._t, days = this._daySlots(d);
      const hasTomorrow = days.tomorrow.length > 0;
      if (!hasTomorrow) this._day = "today";
      const isToday = this._day === "today";
      const slots = isToday ? days.today : days.tomorrow;
      const head = `<div class="tl-head"><h3>${t.pricesPlan}<small>${t.rceNet}</small></h3>
        <div class="tl-toggle" role="group">
          <button data-day="today" aria-pressed="${isToday}">${t.today}</button>
          <button data-day="tomorrow" aria-pressed="${!isToday}" ${hasTomorrow ? "" : `disabled title="${esc(t.tomorrowLater)}"`}>${t.tomorrow}</button>
        </div></div>`;
      if (!slots.length) return `<section class="tl">${head}<div class="tl-detail"><span>–</span></div></section>`;

      const W = 340, x0 = 30, x1 = 336, top = 16, base = 90, now = Date.now();
      const dayStart = +slots[0].start, dayEnd = +slots[slots.length - 1].end;
      const X = (ms) => x0 + ((ms - dayStart) / (dayEnd - dayStart)) * (x1 - x0);
      const prices = slots.map((s) => s.price);
      const lo = Math.min(...prices, 0), hi = Math.max(...prices);
      const maxP = Math.max(0.25, Math.ceil(hi * 4) / 4), minP = lo < 0 ? Math.floor(lo * 4) / 4 : 0;
      const Y = (p) => base - ((p - minP) / (maxP - minP)) * (base - top);
      const zeroY = Y(0);
      const minI = prices.indexOf(Math.min(...prices));
      const nowI = isToday ? slots.findIndex((s) => now >= s.start && now < s.end) : -1;
      this._defaultSel = nowI >= 0 ? nowI : minI;
      const sel = clamp(this._sel ?? this._defaultSel, 0, slots.length - 1);
      const narrow = (x1 - x0) / slots.length < 6;
      const gap = narrow ? 0.3 : 1.2;

      let g = "";
      for (let v = minP; v <= maxP + 1e-9; v += 0.25) {
        if (Math.abs(v) < 1e-9 && minP === 0) continue;
        g += `<line x1="${x0}" x2="${x1}" y1="${Y(v)}" y2="${Y(v)}" stroke="${T.gridline}"/>`;
        g += `<text x="${x0 - 5}" y="${Y(v) + 3}" text-anchor="end" class="lbl">${this._n(v, 2)}</text>`;
      }
      g += `<line x1="${x0}" x2="${x1}" y1="${zeroY}" y2="${zeroY}" stroke="${T.label}" stroke-opacity=".5"/>`;
      let bars = "";
      slots.forEach((s, i) => {
        const tt = (s.price - Math.min(...prices)) / ((hi - Math.min(...prices)) || 1);
        const past = isToday && +s.end <= now;
        const xa = X(+s.start) + gap, xb = X(+s.end) - gap;
        const y1 = Math.min(Y(s.price), zeroY), h = Math.abs(Y(s.price) - zeroY);
        const color = mix(T.cheap, T.dear, tt);
        bars += `<rect x="${xa.toFixed(2)}" y="${y1.toFixed(1)}" width="${Math.max(0.6, xb - xa).toFixed(2)}" height="${Math.max(0.8, h).toFixed(1)}" rx="${narrow ? 0 : T.barR}" fill="${color}" opacity="${past ? T.past : 1}"${T.glow && !past ? ` style="filter:drop-shadow(0 0 3px ${color})"` : ""}/>`;
      });
      const ss = slots[sel];
      bars += `<rect x="${X(+ss.start).toFixed(2)}" y="${top - 6}" width="${Math.max(2, X(+ss.end) - X(+ss.start)).toFixed(2)}" height="${base - top + 6 + (isToday ? 26 : 0)}" fill="none" stroke="var(--c-text)" stroke-opacity=".55" rx="${narrow ? 0 : T.barR}"/>`;
      const sm = slots[minI];
      bars += `<text x="${((X(+sm.start) + X(+sm.end)) / 2).toFixed(1)}" y="${Math.min(Y(sm.price), zeroY) - 4}" text-anchor="middle" class="min" fill="${T.cheap}">min</text>`;

      let plan = "";
      if (isToday) {
        const hm = (s) => { const [a, b] = s.split(":").map(Number); return dayStart + (a * 60 + b) * 60000; };
        for (const p of d.plan) {
          if (!p.od || !p.do) continue;
          const a = X(hm(p.od)), b = X(hm(p.do));
          if (b > a) plan += `<rect x="${a.toFixed(1)}" y="98" width="${Math.max(0.5, b - a - 1).toFixed(1)}" height="11" rx="${Math.min(T.barR, 3)}" fill="${T.modes[p.tryb] || T.vars.muted}"><title>${esc(this._mode(p.tryb))} ${esc(p.od)}–${esc(p.do)}</title></rect>`;
        }
        if (!d.plan.length) plan += `<text x="${(x0 + x1) / 2}" y="107" text-anchor="middle" class="note">–</text>`;
        const nx = X(now);
        if (nx >= x0 && nx <= x1) {
          plan += `<rect x="${x0}" y="97" width="${(nx - x0).toFixed(1)}" height="13" fill="var(--c-plain)" opacity=".6"/>`;
          plan += `<line x1="${nx}" x2="${nx}" y1="${top - 8}" y2="113" stroke="var(--c-text)" stroke-width="1.5" stroke-dasharray="3 2"/>`;
          plan += `<text x="${clamp(nx, x0 + 12, x1 - 12)}" y="${top - 10}" text-anchor="middle" class="nowlbl">${wParts(new Date(now)).hm}</text>`;
        }
      } else {
        plan += `<text x="${(x0 + x1) / 2}" y="107" text-anchor="middle" class="note">${esc(t.planTomorrow)}</text>`;
      }
      let ax = "";
      for (const h of [0, 6, 12, 18, 24]) {
        const x = x0 + (h / 24) * (x1 - x0);
        ax += `<text x="${x}" y="126" text-anchor="${h === 0 ? "start" : h === 24 ? "end" : "middle"}" class="lbl">${String(h).padStart(2, "0")}</text>`;
      }
      let hits = "";
      slots.forEach((s, i) => { hits += `<rect class="hit" data-i="${i}" x="${X(+s.start)}" y="0" width="${Math.max(1, X(+s.end) - X(+s.start))}" height="130" fill="transparent"/>`; });

      const atSel = isToday ? d.plan.find((p) => p.od <= wParts(ss.start).hm && wParts(ss.start).hm < p.do) : null;
      const detail = `<b>${wParts(ss.start).hm}–${wParts(ss.end).hm === "00:00" ? "24:00" : wParts(ss.end).hm}</b><b>${this._zl(ss.price)}</b>${atSel ? `<span>${esc(this._mode(atSel.tryb))}</span>` : ""}${sel === minI ? `<span>${t.cheapest}</span>` : ""}`;
      const used = [...new Set(d.plan.map((p) => p.tryb))];
      return `<section class="tl">${head}
        <svg viewBox="0 0 ${W} 130" tabindex="0" role="img" aria-label="${esc(t.pricesPlan)}">${g}${bars}${plan}${ax}${hits}</svg>
        <div class="tl-detail" aria-live="polite">${detail}</div>
        ${isToday && used.length ? `<div class="legend">${used.map((k) => `<span style="--m:${T.modes[k] || T.vars.muted}">${esc(this._mode(k))}</span>`).join("")}</div>` : ""}
      </section>`;
    }

    // ---------------------------------------------------------- weather layers
    _weatherSvg(d, w, h, colors, seedY = 0) {
      if (!d.weather || !this._config.show_weather) return "";
      const look = weatherLook(d.weather.condition);
      let s = "";
      if (look.rain) {
        const n = look.rain === 2 ? 46 : 24;
        s += `<g class="rain ${look.rain === 2 ? "heavy" : ""}" stroke="${colors.rain}" stroke-width="1.2" stroke-linecap="round">`;
        for (let i = 0; i < n; i++) { const x = (i * 97) % w, y = seedY + ((i * 53) % (h * 0.8)); s += `<line style="--d:-${(i % 12) * 0.1}s" x1="${x}" y1="${y}" x2="${x - 4}" y2="${y + 11}"/>`; }
        s += `</g>`;
      }
      if (look.snow) {
        s += `<g class="snow" fill="${colors.snow}">`;
        for (let i = 0; i < 34; i++) { const x = (i * 83) % w, y = seedY + ((i * 41) % (h * 0.8)); s += `<circle style="--d:-${(i % 10) * 0.6}s" cx="${x}" cy="${y}" r="${1.2 + (i % 3) * 0.5}"/>`; }
        s += `</g>`;
      }
      if (look.fog) {
        s += `<g class="fog" fill="${colors.fog}">`;
        for (let i = 0; i < 4; i++) s += `<rect style="--d:-${i * 4}s" x="${-120 + i * 40}" y="${h * (0.35 + i * 0.14)}" width="${w * 0.9}" height="${h * 0.08}" rx="${h * 0.04}"/>`;
        s += `</g>`;
      }
      if (look.storm) s += `<rect class="flash" x="0" y="0" width="${w}" height="${h}" fill="#fff"/>`;
      return s;
    }

    _weatherText(d) {
      if (!d.weather || !this._config.show_weather) return "";
      const label = this._t.weather[d.weather.condition] || "";
      const temp = d.weather.temp !== null ? `${Math.round(d.weather.temp)}${d.weather.unit}` : "";
      return [label, temp].filter(Boolean).join(" · ");
    }

    // ---------------------------------------------------------- Diorama
    _hero_diorama(T, d) {
      const t = this._t, V = T.vars, phase = this._phase(d);
      const look = d.weather && this._config.show_weather ? weatherLook(d.weather.condition) : weatherLook("");
      const grey = look.clouds >= 3 || look.rain || look.fog;
      const sky = phase === "night" ? ["#0f1c3a", "#2a3d6b"] : phase === "dusk" ? (grey ? ["#8f8fa8", "#d8c9c0"] : ["#f0a875", "#fbe0c4"]) : grey ? ["#9fb1c2", "#dfe7ee"] : ["#79c3f2", "#d9f0fb"];
      const roof = [[220, 92], [300, 132], [260, 190], [180, 150]];
      const q = (u, v) => { const [a, b, c, e] = roof; return [(1 - v) * ((1 - u) * a[0] + u * b[0]) + v * ((1 - u) * e[0] + u * c[0]), (1 - v) * ((1 - u) * a[1] + u * b[1]) + v * ((1 - u) * e[1] + u * c[1])]; };
      let panels = "";
      for (let r = 0; r < 2; r++) for (let c = 0; c < 4; c++) {
        const u0 = 0.08 + c * 0.215, u1 = u0 + 0.19, v0 = 0.12 + r * 0.4, v1 = v0 + 0.34;
        const pts = [q(u0, v0), q(u1, v0), q(u1, v1), q(u0, v1)].map((p) => p.map((n) => n.toFixed(1)).join(",")).join(" ");
        panels += `<polygon points="${pts}" fill="${(d.pv ?? 0) > 50 ? "#2b4374" : "#22324f"}" stroke="#9fb7e0" stroke-width=".8"/>`;
      }
      const win = phase === "night" ? "#ffd77a" : phase === "dusk" ? "#ffe2a8" : "#a9d4f5";
      const stars = phase === "night" && look.clouds < 2 ? [[60, 40], [120, 70], [390, 50], [470, 90], [300, 30], [210, 55], [440, 30]].map(([x, y], i) => `<circle class="twinkle" style="--d:${i * 0.7}s" cx="${x}" cy="${y}" r="1.4" fill="#fff"/>`).join("") : "";
      const sunY = phase === "dusk" ? 96 : 58;
      const sun = look.clouds >= 3 ? "" : phase === "night"
        ? `<circle cx="410" cy="62" r="16" fill="#f2f4ff"/><circle cx="417" cy="57" r="14" fill="${sky[0]}"/>`
        : `<circle class="glow" cx="410" cy="${sunY}" r="34" fill="#ffe28a" opacity=".35"/><circle cx="410" cy="${sunY}" r="22" fill="#ffd34d"/>`;
      let clouds = "";
      const nClouds = [0, 2, 3, 5][look.clouds];
      const cloudFill = phase === "night" ? "#5d6b8a" : grey ? "#f3f5f8" : "#ffffff";
      for (let i = 0; i < nClouds; i++) {
        const y = 62 + (i * 29) % 56, s = 0.6 + (i % 3) * 0.2;
        clouds += `<g class="cloud" style="--t:${60 + i * 17}s;--d:-${i * 13}s" opacity="${grey ? 0.95 : 0.85}"><g transform="translate(0 ${y}) scale(${s})"><ellipse cx="40" cy="20" rx="34" ry="14" fill="${cloudFill}"/><ellipse cx="62" cy="12" rx="22" ry="14" fill="${cloudFill}"/><ellipse cx="24" cy="12" rx="16" ry="11" fill="${cloudFill}"/></g></g>`;
      }
      const bat = d.bat ?? 0, siec = d.siec ?? 0, pv = d.pv ?? 0;
      const fl = (path, w, color, rev) => `<path class="flow${Math.abs(w) > 30 ? " run" : ""}${rev ? " rev" : ""}" style="--t:${durFor(w)}" d="${path}" stroke="${color}" stroke-width="3.2" stroke-dasharray="1 8" opacity="${Math.abs(w) > 30 ? 1 : 0.25}"/>`;
      const lvl = (() => { const h = 36 * clamp(d.soc ?? 0, 0, 100) / 100, yb = (x) => 202 - (x - 92) * 0.5; return [[98, yb(98)], [116, yb(116)], [116, yb(116) - h], [98, yb(98) - h]].map((p) => p.map((n) => n.toFixed(1)).join(",")).join(" "); })();
      const night = phase === "night";
      const wx = this._weatherSvg(d, 520, 340, { rain: "rgba(255,255,255,.75)", snow: "#ffffff", fog: "rgba(255,255,255,.45)" });
      const svg = `<svg viewBox="0 0 520 340" aria-hidden="true">
        ${stars}${sun}${clouds}
        <polygon points="40,238 260,128 480,238 260,348" fill="${night ? "#3f6b48" : look.snow ? "#eef3f7" : "#8fd07a"}"/>
        <polygon points="40,238 260,348 260,360 40,250" fill="${night ? "#2f5236" : look.snow ? "#d5dee6" : "#6fb45c"}"/>
        <polygon points="480,238 260,348 260,360 480,250" fill="${night ? "#28472f" : look.snow ? "#c8d3dd" : "#5fa14d"}"/>
        <polygon points="92,206 122,191 122,145 92,160" fill="#e8eef4"/><polygon points="122,191 142,201 142,155 122,145" fill="#cfd9e3"/>
        <polygon points="92,160 122,145 142,155 112,170" fill="#f7fafc"/><polygon points="${lvl}" fill="${V.bat}" opacity=".9"/>
        <polygon points="180,210 260,250 260,190 180,150" fill="#fbf6ef"/><polygon points="260,250 340,210 340,150 260,190" fill="#e9dfd2"/>
        <polygon points="196,190 214,199 214,182 196,173" fill="${win}"/><polygon points="226,205 244,214 244,197 226,188" fill="${win}"/>
        <polygon points="290,226 306,218 306,190 290,198" fill="#c8794a"/><polygon points="314,208 330,200 330,184 314,192" fill="${win}"/>
        <polygon points="220,92 300,132 340,150 260,110" fill="#c94f3d"/><polygon points="260,190 340,150 300,132" fill="#f3ebe0"/>
        <polygon points="${roof.map((p) => p.join(",")).join(" ")}" fill="${look.snow ? "#f4f7fa" : "#de5f45"}"/>${look.snow ? "" : panels}
        <polygon points="164,206 174,211 174,196 164,191" fill="#ffffff" stroke="#b9c7d6" stroke-width=".8"/>
        <circle cx="169" cy="198" r="1.6" fill="${d.conn === "online" ? V.on : V.warn}"/>
        <g stroke="${d.island ? "#9aa6b2" : "#5d6e80"}" stroke-width="2.2" fill="none" opacity="${d.island ? 0.55 : 1}">
          <path d="M418 262 L438 140 L458 262"/><path d="M424 226 L452 226 M428 196 L448 196 M432 166 L444 166"/><path d="M412 150 L464 150"/><path d="M424 226 L448 196 L428 196 L444 166"/>
        </g>
        <circle cx="276" cy="282" r="13" fill="${night ? "#2f6b3f" : look.snow ? "#dfe8ee" : "#57b86a"}"/><rect x="274" y="290" width="4" height="12" fill="#8a5a3c"/>
        ${fl("M236,150 C226,170 190,178 172,196", pv, V.pv, false)}
        ${fl("M142,182 C150,190 156,196 164,200", bat, V.bat, bat < 0)}
        ${d.island ? `<path d="M414 150 C390 152 360 156 338 166" stroke="${V.bad}" stroke-width="2" stroke-dasharray="4 5" fill="none" opacity=".7"/>` : fl("M414,150 C390,152 360,156 338,166", siec, V.grid, siec < 0)}
        ${wx}
      </svg>`;
      const batText = d.full ? t.full : bat < -30 ? `${t.charging} ${this._kw(bat)}` : bat > 30 ? `${t.discharging} ${this._kw(bat)}` : t.idle;
      const wtext = this._weatherText(d);
      return `<div class="dio-scene" style="--sky-a:${sky[0]};--sky-b:${sky[1]}">${svg}
        <div class="dio-title"><h2>${esc(d.name)}</h2><span>ProfitEMS${d.serial ? ` · ${esc(d.serial)}` : ""}</span></div>
        <div class="dio-clock">${wParts(new Date()).hm}${wtext ? `<span>${esc(wtext)}</span>` : ""}</div>
        <div class="dio-tag" style="left:47%;top:17%;--dot:${V.pv}"><i></i>${this._kw(d.pv)} <small>${t.fromRoof}</small></div>
        <div class="dio-tag" style="left:3%;top:63%;--dot:${V.bat}"><i></i>${d.soc ?? "–"}% <small>${batText}</small></div>
        <div class="dio-tag" style="right:3%;top:80%;--dot:${d.island ? V.bad : V.grid}"><i></i>${d.island ? t.noGrid : `${this._kw(d.siec)} <small>${siec > 30 ? t.import : siec < -30 ? t.export : t.gridIdle}</small>`}</div>
        <div class="dio-tag" style="left:28%;bottom:4%;--dot:${V.home}"><i></i>${this._kw(d.dom)} <small>${t.inHome}</small></div>
      </div>`;
    }

    // ---------------------------------------------------------- Aurora
    _hero_aurora(T, d) {
      const t = this._t, V = T.vars, bat = d.bat ?? 0, siec = d.siec ?? 0;
      const look = d.weather && this._config.show_weather ? weatherLook(d.weather.condition) : weatherLook("");
      const node = (cx, cy, color, label, parts, sub, extra = "") => `
        <circle class="ring" style="--glow:${color}" cx="${cx}" cy="${cy}" r="36" fill="rgba(10,13,26,.78)" stroke="${color}" stroke-width="2"/>${extra}
        <text x="${cx}" y="${cy - 12}" text-anchor="middle" class="nl">${label}</text>
        <text x="${cx}" y="${cy + 6}" text-anchor="middle" class="nv">${parts[0]}</text>
        <text x="${cx}" y="${cy + 19}" text-anchor="middle" class="nu">${parts[1]}</text>
        ${sub ? `<text x="${cx}" y="${cy + 52}" text-anchor="middle" class="ns">${sub}</text>` : ""}`;
      const C = 2 * Math.PI * 41;
      const socArc = `<circle cx="70" cy="140" r="41" fill="none" stroke="${V.bat}" stroke-width="3" stroke-dasharray="${(C * clamp(d.soc ?? 0, 0, 100) / 100).toFixed(1)} ${C.toFixed(1)}" transform="rotate(-90 70 140)" style="filter:drop-shadow(0 0 4px ${V.bat})"/>`;
      const fl = (path, w, color, out) => `<path d="${path}" stroke="rgba(255,255,255,.07)" stroke-width="3" fill="none"/><path class="flow${Math.abs(w) > 30 ? " run" : ""}${out ? "" : " rev"}" style="--t:${durFor(w)};filter:drop-shadow(0 0 3px ${color})" d="${path}" stroke="${color}" stroke-width="3" stroke-dasharray="2 10" opacity="${Math.abs(w) > 30 ? 1 : 0}"/>`;
      const lbl = (x, y, w, color, anchor = "middle") => (Math.abs(w) > 30 ? `<text x="${x}" y="${y}" text-anchor="${anchor}" class="fv" fill="${color}">${this._kw(w)}</text>` : "");
      const up = (s) => s.toUpperCase();
      const gridSub = d.island ? up(t.noGrid) : siec > 30 ? up(t.import) : siec < -30 ? up(t.export) : "";
      const batSub = d.full ? up(t.full) : bat < -30 ? up(t.charging) : bat > 30 ? up(t.discharging) : up(t.idle);
      const wx = this._weatherSvg(d, 360, 290, { rain: "rgba(162,139,255,.55)", snow: "rgba(233,241,255,.8)", fog: "rgba(162,139,255,.12)" });
      // Cloud cover dims the solar ring a little; the sky does not lie about the sun.
      const pvColor = look.clouds >= 3 ? mix(V.pv, "#8390b8", 0.35) : V.pv;
      const svg = `<svg class="aur-svg" viewBox="0 0 360 290" aria-hidden="true">
        ${wx}
        ${fl("M180 128 L180 92", d.pv ?? 0, pvColor, false)}
        ${fl("M168 140 C140 140 132 152 106 146", bat, V.bat, bat < 0)}
        ${d.island ? `<path d="M192 140 C220 140 228 152 254 146" stroke="${V.warn}" stroke-width="2" stroke-dasharray="3 6" fill="none" opacity=".6"/>` : fl("M192 140 C220 140 228 152 254 146", siec, V.grid, siec < 0)}
        ${fl("M180 152 L180 188", d.dom ?? 0, V.home, true)}
        ${lbl(186, 114, d.pv ?? 0, pvColor, "start")}${lbl(136, 132, bat, V.bat)}${lbl(224, 132, siec, V.grid)}
        <circle cx="180" cy="140" r="13" fill="#0a0d1a" stroke="${V.text}" stroke-opacity=".5" stroke-width="1.5"/>
        <text x="180" y="143" text-anchor="middle" class="hub">EMS</text>
        ${node(180, 54, pvColor, "PV", this._kwParts(d.pv), "")}
        ${node(70, 140, V.bat, "SOC", [`${d.soc ?? "–"}%`, (bat < -30 ? "+" : bat > 30 ? "−" : "") + this._kw(bat)], batSub, socArc)}
        ${node(290, 140, d.island ? "#5a5f78" : V.grid, up(t === TEXTS.pl ? "sieć" : "grid"), d.island ? ["—", ""] : this._kwParts(d.siec), gridSub)}
        ${node(180, 226, V.home, up(t.home), this._kwParts(d.dom), "")}
      </svg>`;
      const late = d.conn !== "online";
      const wtext = this._weatherText(d);
      return `<div class="grain"></div>
        <div class="aur-head"><div><h2>${esc(d.name)}</h2><small>${d.serial ? esc(d.serial) + " · " : ""}EMS Connect</small>${wtext ? `<small class="wx">${esc(wtext)}</small>` : ""}</div>
        <div class="aur-live ${late ? "late" : ""}"><i></i>${esc(up(t.conn[d.conn] || "–"))} ${wParts(new Date()).hm}</div></div>${svg}`;
    }

    // ---------------------------------------------------------- Foundation
    _hero_foundation(T, d) {
      const t = this._t, V = T.vars, bat = d.bat ?? 0, siec = d.siec ?? 0;
      const look = d.weather && this._config.show_weather ? weatherLook(d.weather.condition) : weatherLook("");
      const orbit = (rx, ry, ang, sec, rev, r, color) => `<g class="spin${rev ? " rev" : ""}" style="--t:${sec}s"><g transform="rotate(${ang} 180 150)">
        <ellipse cx="180" cy="150" rx="${rx}" ry="${ry}" fill="none" stroke="${V.accent}" stroke-opacity=".28" stroke-width=".8"/><circle cx="${180 + rx}" cy="150" r="${r}" fill="${color}"/></g></g>`;
      const ray = (path, w, color, rev) => `<path class="flow${Math.abs(w) > 30 ? " run" : ""}${rev ? " rev" : ""}" style="--t:${(parseFloat(durFor(w)) * 2).toFixed(2)}s" d="${path}" stroke="${color}" stroke-width="1.6" stroke-dasharray="1 5" opacity="${Math.abs(w) > 30 ? 1 : 0.18}"/>`;
      const dust = look.rain || look.snow ? "" : [[70, 70], [300, 60], [60, 230], [310, 240], [120, 40], [250, 262], [330, 150], [30, 150]].map(([x, y], i) => `<circle class="twinkle" style="--d:${i * 0.6}s" cx="${x}" cy="${y}" r="1" fill="${V.accent}"/>`).join("");
      const label = (x, y, anchor, title, value, sub, color) => `
        <text x="${x}" y="${y}" text-anchor="${anchor}" class="ft">${title}</text>
        <text x="${x}" y="${y + 21}" text-anchor="${anchor}" class="fval" fill="${color}">${value}</text>
        ${sub ? `<text x="${x}" y="${y + 36}" text-anchor="${anchor}" class="fsub">${sub}</text>` : ""}`;
      const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
      const batSub = d.full ? cap(t.full) : bat < -30 ? cap(t.charging) : bat > 30 ? cap(t.discharging) : cap(t.idle);
      const gridSub = d.island ? cap(t.noGrid) : siec > 30 ? cap(t.import) : siec < -30 ? cap(t.export) : "";
      const halo = look.clouds >= 3 ? 0.45 : look.clouds ? 0.75 : 1;
      const wx = this._weatherSvg(d, 360, 300, { rain: "rgba(232,196,122,.45)", snow: "rgba(241,230,207,.8)", fog: "rgba(232,196,122,.08)" });
      const U = (s) => s.toUpperCase();
      const svg = `<svg class="fnd-svg" viewBox="0 0 360 300" aria-hidden="true">
        <defs><radialGradient id="fsph" cx="45%" cy="40%" r="60%"><stop offset="0" stop-color="#fff3cf"/><stop offset=".35" stop-color="#e8c47a"/><stop offset="1" stop-color="#5a4318"/></radialGradient>
        <radialGradient id="fhalo"><stop offset="0" stop-color="#e8c47a" stop-opacity=".35"/><stop offset="1" stop-color="#e8c47a" stop-opacity="0"/></radialGradient></defs>
        ${dust}${wx}
        <circle cx="180" cy="150" r="78" fill="url(#fhalo)" opacity="${halo}"/>
        ${orbit(132, 52, 0, 60, false, 2.4, V.pv)}${orbit(112, 66, 34, 85, true, 2, V.bat)}${orbit(112, 66, -34, 110, false, 2, V.grid)}
        ${ray("M180 72 L180 112", d.pv ?? 0, V.pv, false)}
        ${ray("M180 188 L180 226", d.dom ?? 0, V.home, false)}
        ${ray("M92 150 L142 150", bat, V.bat, bat < 0)}
        ${d.island ? `<path d="M218 150 L268 150" stroke="${V.warn}" stroke-width="1" stroke-dasharray="2 4" opacity=".6"/>` : ray("M218 150 L268 150", siec, V.grid, siec < 0)}
        <circle cx="180" cy="150" r="34" fill="url(#fsph)" opacity=".92"/>
        <text x="180" y="154" text-anchor="middle" class="fcore">EMS</text>
        ${label(180, 20, "middle", t === TEXTS.pl ? "SŁOŃCE" : "SUN", this._kw(d.pv), "", V.pv)}
        ${label(16, 128, "start", `${t === TEXTS.pl ? "MAGAZYN" : "BATTERY"} ${d.soc ?? "–"}%`, this._kw(bat), batSub, V.text)}
        ${label(344, 128, "end", t === TEXTS.pl ? "SIEĆ" : "GRID", d.island ? "—" : this._kw(siec), gridSub, V.grid)}
        ${label(180, 246, "middle", U(t.home), this._kw(d.dom), "", V.text)}
      </svg>`;
      const date = new Intl.DateTimeFormat(t === TEXTS.pl ? "pl-PL" : "en-GB", { timeZone: TZ, day: "numeric", month: "long" }).format(new Date());
      const wtext = this._weatherText(d);
      return `<div class="fnd-head"><small>PROFITEMS</small><h2>${esc(U(d.name))}</h2><em>${esc(date)} · ${wParts(new Date()).hm}${wtext ? ` · ${esc(wtext)}` : ""}</em></div>${svg}`;
    }
  }

  function loadFonts(theme) {
    const id = `profitems-fonts-${theme}`;
    if (document.getElementById(id) || !THEMES[theme]) return;
    const link = document.createElement("link");
    link.id = id; link.rel = "stylesheet";
    link.href = `https://fonts.googleapis.com/css2?${THEMES[theme].fonts}&display=swap`;
    document.head.appendChild(link);
  }

  const STYLES = `
    :host { display: block; }
    ha-card.card { display: block; }
    .card { position: relative; overflow: hidden; border-radius: var(--c-r); background: var(--c-bg); color: var(--c-text);
      font-family: var(--c-font); box-shadow: var(--c-shadow); border: 1px solid var(--c-frame); container-type: inline-size; }
    .empty { padding: 24px; display: grid; gap: 6px; }
    .empty span { color: var(--c-muted); font-size: 13px; }
    .body { display: grid; gap: 14px; padding: 16px; position: relative; }
    .status { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px 8px; align-items: center; font-size: 12.5px; }
    .pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 999px; background: var(--c-surface);
      border: 1px solid var(--c-border); white-space: nowrap; }
    .pill i { width: 8px; height: 8px; border-radius: 50%; background: var(--dot, var(--c-muted)); flex: none; }
    .pill small { color: var(--c-muted); font-size: 11.5px; }
    .pill.mode { font-weight: 700; }
    .pill.island { background: var(--c-warn-soft); border-color: var(--c-warn); color: var(--c-warn); font-weight: 700; }
    .moment { margin: 0; font-size: 14px; line-height: 1.45; text-align: center; text-wrap: balance; }
    .moment small { display: block; margin-top: 3px; color: var(--c-muted); font-size: 12px; }
    .tl, .value { padding: 12px 12px 10px; border-radius: var(--c-tr); background: var(--c-surface); border: 1px solid var(--c-border); display: grid; gap: 6px; }
    .tl-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    h3 { margin: 0; font-size: 14px; font-family: var(--c-head); font-weight: var(--c-head-w); letter-spacing: var(--c-head-ls); }
    h3 small { color: var(--c-muted); font-weight: 500; font-size: 11px; font-family: var(--c-font); letter-spacing: 0; margin-left: 4px; }
    .tl-toggle { display: inline-flex; padding: 2px; border-radius: 999px; background: var(--c-track); }
    .tl-toggle button { border: 0; background: transparent; color: var(--c-muted); font: 600 12px var(--c-font); padding: 4px 10px; border-radius: 999px; cursor: pointer; }
    .tl-toggle button[aria-pressed="true"] { background: var(--c-tab-on-bg); color: var(--c-tab-on); }
    .tl-toggle button:disabled { opacity: .45; cursor: not-allowed; }
    .tl-toggle button:focus-visible, .tl svg:focus-visible { outline: 2px solid var(--c-accent); outline-offset: 2px; }
    .tl svg { display: block; width: 100%; height: auto; overflow: visible; touch-action: pan-y; }
    .tl .lbl { font-size: 8.5px; fill: var(--c-muted); font-family: var(--c-num); }
    .tl .min { font-size: 8px; font-weight: 700; font-family: var(--c-font); }
    .tl .note { font-size: 9.5px; fill: var(--c-muted); font-family: var(--c-font); }
    .tl .nowlbl { font-size: 8.5px; font-weight: 700; fill: var(--c-text); font-family: var(--c-font); }
    .tl-detail { font-size: 12.5px; min-height: 1.4em; display: flex; flex-wrap: wrap; gap: 2px 10px; }
    .tl-detail b { font-family: var(--c-num); }
    .tl-detail span { color: var(--c-muted); }
    .legend { display: flex; flex-wrap: wrap; gap: 3px 12px; font-size: 11px; color: var(--c-muted); }
    .legend span::before { content: ""; display: inline-block; width: 9px; height: 9px; margin-right: 5px; border-radius: 2px; background: var(--m); vertical-align: -1px; }
    .value-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
    .value-row div { display: grid; gap: 1px; min-width: 0; }
    .value-row span { font-size: 11px; color: var(--c-muted); }
    .value-row b { font-family: var(--c-num); font-size: 16px; white-space: nowrap; }
    .value-row small { font-size: 11px; color: var(--c-muted); font-family: var(--c-num); }
    .value-row .bal { padding-left: 10px; border-left: 1px solid var(--c-border); }
    .value .good { color: var(--c-good); } .value .bad { color: var(--c-bad); }
    .value p { margin: 0; font-size: 11px; color: var(--c-muted); line-height: 1.35; }
    .signals { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
    .sig { min-width: 0; padding: 9px 10px; border-radius: var(--c-tr); background: var(--c-surface); border: 1px solid var(--c-border); display: grid; gap: 2px; }
    .sig small { font-size: 10.5px; color: var(--c-muted); line-height: 1.2; }
    .sig b { font-size: 14px; font-family: var(--c-num); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .sig.on { border-color: var(--c-on-border); background: var(--c-on-bg); }
    .sig.on b { color: var(--c-on); }
    .flow { fill: none; stroke-linecap: round; }
    .flow.run { animation: dash var(--t, 3s) linear infinite; }
    .flow.rev { animation-direction: reverse; }
    @keyframes dash { to { stroke-dashoffset: -36; } }
    .cloud { animation: drift var(--t) linear infinite; animation-delay: var(--d); }
    @keyframes drift { from { transform: translateX(-120px); } to { transform: translateX(560px); } }
    .rain line { animation: fall 1.1s linear infinite; animation-delay: var(--d); }
    .rain.heavy line { animation-duration: .65s; }
    @keyframes fall { from { transform: translate(0, -40px); opacity: 0; } 15% { opacity: 1; } to { transform: translate(-14px, 70px); opacity: 0; } }
    .snow circle { animation: flake 6s linear infinite; animation-delay: var(--d); }
    @keyframes flake { from { transform: translate(0, -30px); opacity: 0; } 15% { opacity: .9; } to { transform: translate(14px, 90px); opacity: 0; } }
    .fog rect { animation: fog 22s ease-in-out infinite alternate; animation-delay: var(--d); }
    @keyframes fog { to { transform: translateX(110px); } }
    .flash { opacity: 0; pointer-events: none; animation: flash 9s linear infinite; }
    @keyframes flash { 0%, 92%, 95%, 100% { opacity: 0; } 93%, 96% { opacity: .5; } }
    .twinkle { animation: tw 5s ease-in-out infinite; animation-delay: var(--d); }
    @keyframes tw { 50% { opacity: .15; } }
    .glow { transform-box: fill-box; transform-origin: center; animation: glow 6s ease-in-out infinite; }
    @keyframes glow { 50% { transform: scale(1.18); opacity: .12; } }
    .spin { transform-box: view-box; transform-origin: 180px 150px; animation: spin var(--t) linear infinite; }
    .spin.rev { animation-direction: reverse; }
    @keyframes spin { to { transform: rotate(360deg); } }
    @media (prefers-reduced-motion: reduce) { .flow.run, .cloud, .rain line, .snow circle, .fog rect, .flash, .twinkle, .glow, .spin { animation: none !important; } }

    .dio-scene { position: relative; aspect-ratio: 520 / 340; background: linear-gradient(180deg, var(--sky-a), var(--sky-b) 72%); }
    .dio-scene svg { position: absolute; inset: 0; width: 100%; height: 100%; }
    .dio-title { position: absolute; left: 4.5%; top: 5%; color: #fff; text-shadow: 0 1px 8px rgba(20,60,100,.35); }
    .dio-title h2 { margin: 0 0 5px; font-size: clamp(18px, 5.4cqw, 26px); font-weight: 800; }
    .dio-title span { display: inline-block; font-size: 11px; font-weight: 700; padding: 3px 9px; border-radius: 999px; background: rgba(255,255,255,.28); text-shadow: none; }
    .dio-clock { position: absolute; right: 4%; top: 6%; padding: 5px 10px; border-radius: 999px; background: rgba(255,255,255,.3); color: #fff; font-size: 12px; font-weight: 800; display: flex; gap: 6px; }
    .dio-clock span { font-weight: 700; padding-left: 6px; border-left: 1px solid rgba(255,255,255,.5); }
    .dio-tag { position: absolute; display: flex; align-items: center; gap: 6px; padding: 5px 10px 5px 8px; border-radius: 999px; background: #fff;
      box-shadow: 0 6px 18px rgba(30,70,110,.16); font-size: clamp(11px, 3.4cqw, 14px); font-weight: 800; color: #24364a; white-space: nowrap; }
    .dio-tag i { width: 10px; height: 10px; border-radius: 50%; background: var(--dot); }
    .dio-tag small { font-weight: 700; color: #6a7d92; font-size: .85em; }
    .t-diorama .status .pill { background: #fff; }
    .t-diorama .moment { padding: 12px 14px; border-radius: 16px; background: var(--c-surface); }

    .t-aurora .grain { position: absolute; inset: 0; pointer-events: none; background-image: radial-gradient(rgba(255,255,255,.05) 1px, transparent 1px); background-size: 4px 4px; }
    .aur-head { position: relative; display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; padding: 18px 18px 0; }
    .aur-head h2 { margin: 0; font-size: 22px; letter-spacing: -.02em; font-weight: 700; }
    .aur-head small { display: block; color: var(--c-muted); font-size: 12px; }
    .aur-head small.wx { color: var(--c-grid); }
    .aur-live { font-family: var(--c-num); font-size: 11.5px; color: var(--c-accent); display: flex; align-items: center; gap: 6px; white-space: nowrap; }
    .aur-live i { width: 7px; height: 7px; border-radius: 50%; background: currentColor; box-shadow: 0 0 8px currentColor; }
    .aur-live.late { color: var(--c-warn); }
    .aur-svg { position: relative; display: block; width: 100%; height: auto; }
    .aur-svg .ring { filter: drop-shadow(0 0 6px var(--glow)); }
    .aur-svg .nl { font-size: 8px; letter-spacing: 1.5px; fill: var(--c-muted); font-family: var(--c-num); }
    .aur-svg .nv { font-size: 17px; font-weight: 700; fill: var(--c-text); font-family: var(--c-num); }
    .aur-svg .nu { font-size: 8px; fill: var(--c-muted); font-family: var(--c-num); }
    .aur-svg .ns { font-size: 8.5px; letter-spacing: 1.2px; fill: var(--c-muted); font-family: var(--c-font); }
    .aur-svg .fv { font-size: 9px; font-family: var(--c-num); }
    .aur-svg .hub { font-size: 7px; font-weight: 700; fill: var(--c-text); font-family: var(--c-num); }
    .t-aurora .moment { font-size: 13.5px; }
    .t-aurora .pill.mode { color: var(--c-accent); }

    .t-foundation .fnd-head { text-align: center; padding: 22px 16px 0; display: grid; gap: 4px; }
    .fnd-head small { font-family: var(--c-head); letter-spacing: .42em; font-size: 10.5px; color: var(--c-accent); }
    .fnd-head h2 { margin: 0; font-family: var(--c-head); font-weight: 400; font-size: 30px; letter-spacing: .14em; }
    .fnd-head em { color: var(--c-muted); font-size: 15px; }
    .fnd-svg { display: block; width: 100%; height: auto; }
    .fnd-svg .ft { font-size: 8.5px; letter-spacing: 3px; fill: var(--c-muted); font-family: var(--c-head); }
    .fnd-svg .fval { font-size: 19px; font-weight: 500; font-family: var(--c-font); }
    .fnd-svg .fsub { font-size: 12px; font-style: italic; fill: var(--c-muted); font-family: var(--c-font); }
    .fnd-svg .fcore { font-size: 13px; font-weight: 600; letter-spacing: 2px; fill: #2a1f0a; font-family: var(--c-head); }
    .t-foundation .moment { text-align: center; font-style: italic; font-size: 18px; padding: 12px 6px 14px; border-top: 1px solid var(--c-border); border-bottom: 1px solid var(--c-border); }
    .t-foundation .moment::before { content: attr(data-label); display: block; font: 400 10.5px var(--c-head); letter-spacing: .4em; text-transform: uppercase; color: var(--c-accent); margin-bottom: 6px; font-style: normal; }
    .t-foundation .moment small { font-size: 14px; }
    .t-foundation .pill { border-radius: 0; font-size: 13.5px; }
    .t-foundation .sig small, .t-foundation .value-row span { font-family: var(--c-head); letter-spacing: .12em; font-size: 9.5px; text-transform: uppercase; }
    .t-foundation .tl-toggle, .t-foundation .tl-toggle button { border-radius: 0; }
    .t-foundation .tl-toggle button { font-size: 13.5px; }
    .t-foundation .tl-detail, .t-foundation .legend, .t-foundation .value p { font-size: 13px; }
  `;

  // ------------------------------------------------------------------ editor
  class ProfitEmsCardEditor extends HTMLElement {
    setConfig(config) { this._config = config; this._render(); }
    set hass(hass) { this._hass = hass; if (this._form) this._form.hass = hass; else this._render(); }

    _render() {
      if (!this._hass || !this._config) return;
      const lang = (this._hass.locale?.language || this._hass.language || "pl").slice(0, 2);
      const ed = (TEXTS[lang] || TEXTS.en).ed;
      if (!this._form) {
        this._form = document.createElement("ha-form");
        this._form.computeLabel = (s) => ed[s.name] || s.name;
        this._form.addEventListener("value-changed", (e) => {
          this._config = e.detail.value;
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
        });
        this.appendChild(this._form);
      }
      this._form.hass = this._hass;
      this._form.schema = [
        { name: "device", selector: { device: { integration: "profitems" } } },
        { name: "theme", selector: { select: { mode: "dropdown", options: Object.entries(THEMES).map(([value, th]) => ({ value, label: th.name })) } } },
        { name: "title", selector: { text: {} } },
        { name: "weather_entity", selector: { entity: { domain: "weather" } } },
        { name: "price_resolution", selector: { select: { options: [{ value: "auto", label: ed.auto }, { value: "hour", label: ed.hour }] } } },
        { type: "grid", name: "", schema: ["show_weather", "show_status", "show_moment", "show_prices", "show_value", "show_signals", "load_fonts"].map((name) => ({ name, selector: { boolean: {} } })) },
      ];
      this._form.data = {
        theme: "diorama", show_weather: true, price_resolution: "auto", show_status: true, show_moment: true,
        show_prices: true, show_value: true, show_signals: true, load_fonts: false, ...this._config,
      };
    }
  }

  if (!customElements.get("profitems-card")) customElements.define("profitems-card", ProfitEmsCard);
  if (!customElements.get("profitems-card-editor")) customElements.define("profitems-card-editor", ProfitEmsCardEditor);
  window.customCards = window.customCards || [];
  if (!window.customCards.some((c) => c.type === "profitems-card")) {
    window.customCards.push({
      type: "profitems-card", name: "ProfitEMS", preview: true,
      description: "Przepływ energii, ceny RCE z planem pracy i bilans dnia w motywach Diorama, Aurora i Foundation.",
      documentationURL: "https://github.com/gratak/profit_ems",
    });
  }
  console.info(`%c PROFITEMS-CARD %c ${CARD_VERSION} `, "background:#1fbf86;color:#fff;font-weight:700", "background:#24364a;color:#fff");
})();

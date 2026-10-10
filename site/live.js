// The live half of the page. It recomputes this week's plan in the browser from Bitget's public
// candle API, prices the Monday list against the public order books, and draws the planting calendar.
// Nothing here needs a key, and if Bitget does not answer the page keeps the plan it shipped with.

(() => {
  const API = "https://api.bitget.com/api/v2/spot/market";
  const DAY = 86_400_000;
  const LOOKBACKS = [21, 63, 126, 252];
  const VOL_WINDOW = 60;
  const VOL_FLOOR = 0.03;
  const CRYPTO = new Set(["BTCUSDT", "ETHUSDT"]);

  let F;             // helpers and data handed over by app.js
  let panel = null;  // live closes on bitcoin's calendar, once fetched
  let books = {};    // symbol -> order book
  let booksAt = null;

  const pause = (ms) => new Promise((done) => setTimeout(done, ms));

  // Bitget's public API allows a handful of requests a second per visitor, so calls are spaced and a refusal is retried once.
  async function getJSON(url, attempt = 0) {
    const res = await fetch(url);
    if (res.status === 429 && attempt < 2) {
      await pause(1200 * (attempt + 1));
      return getJSON(url, attempt + 1);
    }
    if (!res.ok) throw new Error("HTTP " + res.status);
    const body = await res.json();
    if (body.code && body.code !== "00000") throw new Error(body.msg || body.code);
    return body.data;
  }

  // Closed daily bars for one symbol, as a map of open time to close.
  async function closes(symbol) {
    const out = new Map();
    let end = Date.now();
    for (let page = 0; page < 2; page++) {
      const rows = await getJSON(`${API}/history-candles?symbol=${symbol}&granularity=1day&endTime=${end}&limit=200`);
      if (!rows || !rows.length) break;
      for (const r of rows) out.set(Number(r[0]), Number(r[4]));
      end = Number(rows[0][0]) - 1;
      await pause(320);
    }
    const now = Date.now();
    for (const t of [...out.keys()]) if (t + DAY > now) out.delete(t);  // drop the bar still forming
    return out;
  }

  // Bitcoin trades every day, so its bars are the calendar. A day another market was shut carries its last close forward.
  async function fetchPanel(symbols) {
    const maps = [];
    for (const s of symbols) maps.push(await closes(s));
    const days = [...maps[0].keys()].sort((a, b) => a - b);
    const cols = maps.map((m) => {
      let last = null;
      return days.map((d) => (m.has(d) ? (last = m.get(d)) : last));
    });
    const start = Math.max(...cols.map((c) => c.findIndex((v) => v !== null)));
    if (days.length - start <= Math.max(...LOOKBACKS) + 1) throw new Error("not enough history");
    return { days: days.slice(start), prices: Object.fromEntries(symbols.map((s, k) => [s, cols[k].slice(start)])) };
  }

  function stdev(xs) {
    const mean = xs.reduce((a, b) => a + b, 0) / xs.length;
    return Math.sqrt(xs.reduce((a, b) => a + (b - mean) ** 2, 0) / xs.length);
  }

  // The plan is set once a week, on the bar that opens Sunday 16:00 UTC and closes at midday on Monday in New York.
  function signalBar() {
    for (let i = panel.days.length - 1; i > 0; i--) if (new Date(panel.days[i]).getUTCDay() === 0) return i;
    return panel.days.length - 1;
  }

  // The same rule as fallow/rule.py, on the latest weekly signal bar.
  function plan(budget) {
    const symbols = Object.keys(panel.prices), i = signalBar();
    const weights = {}, trend = {};
    for (const s of symbols) {
      const p = panel.prices[s];
      trend[s] = LOOKBACKS.filter((n) => p[i] > p[i - n]).length;
      const moved = [];
      for (let k = i - VOL_WINDOW + 1; k <= i; k++) {
        const r = p[k] / p[k - 1] - 1;
        if (r !== 0) moved.push(r);
      }
      const vol = moved.length < 2 ? null : stdev(moved) * Math.sqrt(CRYPTO.has(s) ? 365 : 252);
      weights[s] = vol === null || !trend[s] ? 0 : (trend[s] / LOOKBACKS.length) * (budget / symbols.length) / Math.max(vol, VOL_FLOOR);
    }
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    if (total > 1) for (const s of symbols) weights[s] /= total;
    const planted = Object.values(weights).reduce((a, b) => a + b, 0);
    return { as_of: new Date(panel.days[i] + DAY).toISOString().slice(0, 10), weights, usdt: 1 - planted, trend };
  }

  // Cost in basis points, against the mid price, of a market order for `usd`. Null when the book cannot fill it.
  function costBp(book, side, usd) {
    const levels = book && book[side];
    if (!levels || !levels.length || !book.asks.length || !book.bids.length || usd <= 0) return null;
    const best = (Number(book.asks[0][0]) + Number(book.bids[0][0])) / 2;
    let left = usd, qty = 0;
    for (const [price, size] of levels) {
      const take = Math.min(left, price * size);
      qty += take / price;
      left -= take;
      if (left <= 1e-9) return Math.abs(usd / qty / best - 1) * 1e4;
    }
    return null;
  }

  async function fetchBooks(symbols) {
    books = {};
    for (const s of symbols) {
      books[s] = await getJSON(`${API}/orderbook?symbol=${s}&type=step0&limit=150`).catch(() => null);
      await pause(320);
    }
    booksAt = new Date();
  }

  function setupList() {
    const { report, pct, num, html, list, longDate } = F;
    const symbols = report.fields.map((f) => f.symbol);
    const name = Object.fromEntries(report.fields.map((f) => [f.symbol, f.name]));
    const account = document.getElementById("account"), dial = document.getElementById("dial");
    const body = document.querySelector("#list tbody");
    const money = (x) => Math.round(x).toLocaleString("en-GB") + " USDT";

    const grid = document.getElementById("holding-grid");
    for (const s of symbols) {
      const label = html("label", "", `${name[s]}<input type="number" inputmode="decimal" min="0" step="10" placeholder="0" data-hold="${s}">`);
      grid.append(label);
    }
    const held = () => Object.fromEntries(symbols.map((s) => [s, Math.max(0, Number(grid.querySelector(`[data-hold="${s}"]`).value) || 0)]));

    let lines = [];
    const draw = () => {
      const size = Math.max(0, Number(account.value) || 0);
      const stats = report.dial[dial.value];
      const setting = panel ? plan(Number(dial.value) / 100) : stats;
      const holding = held(), using = Object.values(holding).some((v) => v > 0);
      document.getElementById("dial-value").textContent = dial.value + "%";
      body.innerHTML = "";
      lines = [];
      let cost = 0, unpriced = [];
      const rows = symbols.map((s) => [s, setting.weights[s]]).sort((a, b) => b[1] - a[1]);
      for (const [s, w] of rows) {
        const target = w * size, trade = target - (using ? holding[s] : 0);
        if (w < 0.0005 && Math.abs(trade) < 1) continue;
        const book = books[s], side = trade >= 0 ? "asks" : "bids";
        let costCell = "", cls = "";
        if (Math.abs(trade) >= 1) {
          const bp = costBp(book, side, Math.abs(trade));
          if (bp === null) { costCell = booksAt ? "book too thin now" : ""; cls = "thin"; if (booksAt) unpriced.push(name[s]); }
          else { costCell = `${num(bp, 1)} bp`; cost += Math.abs(trade) * bp / 1e4; }
        }
        const word = Math.abs(trade) < 1 ? "nothing" : (trade > 0 ? "buy " : "sell ") + money(Math.abs(trade));
        body.append(html("tr", "",
          `<td>${name[s]}<small>${s}</small></td><td>${pct(w)}</td><td>${money(target)}</td>` +
          `<td class="${trade < -1 ? "sell" : "buy"}">${word}</td><td class="${cls}">${costCell}</td>`));
        lines.push(`${s}  hold ${money(target)}  (${pct(w)})  ${word}`);
      }
      const resting = rows.filter(([, w]) => w < 0.0005).map(([s]) => name[s]);
      body.append(html("tr", "rest",
        `<td>USDT${resting.length ? `<small>${list(resting)} not held this week</small>` : ""}</td>` +
        `<td>${pct(setting.usdt)}</td><td>${money(setting.usdt * size)}</td><td></td><td></td>`));
      lines.push(`USDT  hold ${money(setting.usdt * size)}  (${pct(setting.usdt)})`);

      const line = document.getElementById("cost-line");
      if (!booksAt) line.textContent = "Reading Bitget's order books…";
      else {
        const at = booksAt.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
        line.textContent =
          `Getting there would cost about ${num(cost, 2)} USDT in spread and depth, read from the order books at ${at}.` +
          (unpriced.length ? ` ${list(unpriced)} cannot be filled at this size right now. Wait for New York to open.` : "");
      }
      document.getElementById("dial-record").textContent =
        `At this setting, the ${num(report.fallow.full.years, 1)}-year record is ${pct(stats.cagr)} growth a year, ` +
        `a max drawdown of ${pct(-stats.max_drawdown)} and a Sharpe of ${num(stats.sharpe)}, with ${pct(stats.avg_exposure, 0)} of the account invested on average.`;
      document.getElementById("copied").textContent = "";
    };

    account.addEventListener("input", draw);
    dial.addEventListener("input", draw);
    grid.addEventListener("input", draw);
    document.getElementById("copy").addEventListener("click", async () => {
      const text = `Fallow, week of ${longDate(report.plan.as_of)}, volatility target ${dial.value}%\n` + lines.join("\n");
      try { await navigator.clipboard.writeText(text); document.getElementById("copied").textContent = "Copied."; }
      catch (e) { document.getElementById("copied").textContent = "Your browser blocked the copy. Select the table instead."; }
    });
    const reprice = async () => { await fetchBooks(symbols); draw(); };
    document.getElementById("reprice").addEventListener("click", reprice);
    draw();
    return { draw, reprice };
  }

  // Seven and a half years in one picture: a row per field, a column per week.
  function drawCalendar() {
    const { report, curves, el, pct, list, longDate } = F;
    const weeks = curves.weights, symbols = report.fields.map((f) => f.symbol);
    const name = Object.fromEntries(report.fields.map((f) => [f.symbol, f.name]));
    const svg = document.getElementById("chart-calendar"), detail = document.getElementById("calendar-detail");
    const W = 760, LEFT = 112, ROW = 24, GAP = 5, top = 6, rows = [...symbols, "USDT"];
    const H = top + rows.length * (ROW + GAP) + 26;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    const cw = (W - LEFT - 4) / weeks.length;
    const usdt = (w) => 1 - symbols.reduce((a, s) => a + w[s], 0);
    const peak = Object.fromEntries(symbols.map((s) => [s, Math.max(...weeks.map((w) => w[s]))]));
    rows.forEach((s, r) => {
      const y = top + r * (ROW + GAP);
      svg.append(el("text", { x: LEFT - 10, y: y + ROW / 2 + 4, "text-anchor": "end", class: "rowname" }, s === "USDT" ? "USDT" : name[s]));
      weeks.forEach((w, k) => {
        const v = s === "USDT" ? usdt(w) * 0.55 : (w[s] > 0 ? 0.18 + 0.82 * w[s] / peak[s] : 0);
        if (v <= 0.01) return;
        svg.append(el("rect", { x: LEFT + k * cw, y, width: cw + 0.25, height: ROW, class: s === "USDT" ? "rest" : "cell", opacity: v.toFixed(2) }));
      });
    });
    let year = "";
    weeks.forEach((w, k) => {
      const y = w.date.slice(0, 4);
      if (y !== year && k > 0) svg.append(el("text", { x: LEFT + k * cw, y: H - 6, "text-anchor": "middle" }, y));
      year = y;
    });
    const cursor = el("line", { y1: top - 2, y2: H - 24, class: "cursor" });
    svg.append(cursor);

    const levelOn = (key, date) => {
      const i = curves.dates.findIndex((d) => d >= date);
      return i < 0 ? null : curves[key][i];
    };
    const ahead = (date) => new Date(Date.parse(date) + 91 * DAY).toISOString().slice(0, 10);
    const show = (k) => {
      k = Math.max(0, Math.min(weeks.length - 1, k));
      const w = weeks[k], x = LEFT + (k + 0.5) * cw;
      cursor.setAttribute("x1", x); cursor.setAttribute("x2", x);
      const planted = symbols.filter((s) => w[s] > 0.005).sort((a, b) => w[b] - w[a]).map((s) => `${name[s]} ${pct(w[s], 0)}`);
      let text = `Week of ${longDate(w.date)}: ` + (planted.length ? `${list(planted)}, with ${pct(usdt(w), 0)} in USDT.` : "everything in USDT.");
      const a = levelOn("fallow", w.date), b = levelOn("fallow", ahead(w.date));
      const c = levelOn("btc_hold", w.date), d = levelOn("btc_hold", ahead(w.date));
      if (a && b && c && d && ahead(w.date) <= curves.dates[curves.dates.length - 1]) {
        text += ` Over the next three months bitcoin went ${pct(d / c - 1, 0)} and Fallow ${pct(b / a - 1)}.`;
      }
      detail.textContent = text;
    };
    const at = (ev) => {
      const box = svg.getBoundingClientRect();
      show(Math.floor(((ev.clientX - box.left) / box.width * W - LEFT) / cw));
    };
    svg.addEventListener("pointermove", at);
    svg.addEventListener("pointerdown", at);
    show(weeks.length - 1);
  }

  document.addEventListener("fallow-ready", async () => {
    F = window.Fallow;
    const symbols = F.report.fields.map((f) => f.symbol);
    drawCalendar();
    const listUi = setupList();
    const shipped = `Set from the midday price in New York on Monday ${F.longDate(F.report.plan.as_of)}.`;
    try {
      panel = await fetchPanel(symbols);
      const live = plan(0.15);
      const at = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
      F.redrawPlan(live, "");
      document.getElementById("plan-date").innerHTML =
        `<span class="live-dot"></span>Set from the midday price in New York on Monday ${F.longDate(live.as_of)}. Worked out in your browser at ${at} from Bitget's public candles.`;
    } catch (err) {
      document.getElementById("plan-date").textContent = shipped + " Bitget's live prices did not load, so this is the plan the page shipped with.";
    }
    await listUi.reprice().catch(() => listUi.draw());
  });
})();

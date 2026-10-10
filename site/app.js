// Draws the page from data/fallow.json, which `python3 -m fallow site` writes.

const SVG = "http://www.w3.org/2000/svg";
const pct = (x, places = 1) => (x * 100).toFixed(places) + "%";
const num = (x, places = 2) => x.toFixed(places);
const el = (tag, attrs = {}, text) => {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
};
const html = (tag, cls, inner) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (inner !== undefined) node.innerHTML = inner;
  return node;
};
const longDate = (iso) =>
  new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const monthYear = (iso) =>
  new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
const list = (items) =>
  items.length < 2 ? items.join("") : items.slice(0, -1).join(", ") + " and " + items[items.length - 1];

function fill(key, text) {
  document.querySelectorAll(`[data-fill="${key}"]`).forEach((n) => (n.textContent = text));
}

function weeklyNote(report) {
  const { weights, usdt, as_of } = report.plan;
  const name = Object.fromEntries(report.fields.map((f) => [f.symbol, f.name]));
  const planted = Object.entries(weights).filter(([, w]) => w > 0.005).sort((a, b) => b[1] - a[1]);
  const resting = Object.entries(weights).filter(([, w]) => w <= 0.005).map(([s]) => name[s]);
  const parts = [`Week of ${longDate(as_of).replace(/ \d{4}$/, "")}.`];
  if (planted.length) parts.push(`${name[planted[0][0]]} gets the most ground.`);
  else parts.push("Nothing is worth planting.");
  if (resting.length) parts.push(`${list(resting)} ${resting.length > 1 || resting[0].endsWith("s") ? "are" : "is"} resting.`);
  parts.push(usdt > 0.5 ? `More than half the farm waits in USDT.` : `${pct(usdt, 0)} waits in USDT.`);
  return parts.join(" ");
}

function drawFields(report) {
  const box = document.getElementById("fields");
  box.innerHTML = document.getElementById("allocation").innerHTML = document.getElementById("allocation-key").innerHTML = "";
  const lookbacks = 4;
  for (const f of report.fields) {
    const trend = report.plan.trend[f.symbol];
    const weight = report.plan.weights[f.symbol];
    const state =
      trend === lookbacks ? "Up over all 4 lookbacks"
      : trend === 0 ? "Down over all 4. Not held"
      : `Up over ${trend} of 4 lookbacks`;
    const field = html("div", "field");
    field.setAttribute("role", "listitem");
    field.append(
      html("div", "plot", `<div class="crop-fill" style="height:0"></div>`),
      html("h4", "", `${f.name}<small>${f.symbol}</small>`),
      html("p", "weight", pct(weight)),
      html("p", "state", state)
    );
    box.append(field);
    requestAnimationFrame(() => (field.querySelector(".crop-fill").style.height = (trend / lookbacks) * 100 + "%"));
  }

  const bar = document.getElementById("allocation");
  const key = document.getElementById("allocation-key");
  const name = Object.fromEntries(report.fields.map((f) => [f.symbol, f.name]));
  const planted = Object.entries(report.plan.weights).filter(([, w]) => w > 0.0005);
  for (const [s, w] of planted) {
    const seg = html("span", "planted");
    seg.style.width = w * 100 + "%";
    seg.title = `${name[s]} ${pct(w)}`;
    bar.append(seg);
    key.append(html("li", "", `${name[s]} <b>${pct(w)}</b>`));
  }
  const rest = html("span", "resting");
  rest.style.width = report.plan.usdt * 100 + "%";
  rest.title = `USDT ${pct(report.plan.usdt)}`;
  bar.append(rest);
  key.append(html("li", "", `In USDT <b>${pct(report.plan.usdt)}</b>`));
  bar.setAttribute("aria-label", key.textContent);
}

// Shared chart frame: 720 wide, left gutter for the y labels, right gutter for line labels.
const W = 720, LEFT = 44, RIGHT = 118, TOP = 12;

function yearTicks(svg, dates, x, bottom) {
  let last = "";
  dates.forEach((d, i) => {
    const y = d.slice(0, 4);
    if (y !== last && i > 0) {
      svg.append(el("line", { x1: x(i), x2: x(i), y1: bottom, y2: bottom + 5, class: "axis" }));
      svg.append(el("text", { x: x(i), y: bottom + 18, "text-anchor": "middle" }, y));
    }
    last = y;
  });
}

function hatch(svg) {
  const defs = el("defs");
  const p = el("pattern", { id: "hatch", width: 7, height: 7, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" });
  p.append(el("line", { x1: 0, y1: 0, x2: 0, y2: 7, stroke: "currentColor", "stroke-width": 1, opacity: 0.35 }));
  defs.append(p);
  svg.append(defs);
}

function drawdowns(curve) {
  let peak = 0;
  return curve.map((v) => ((peak = Math.max(peak, v)), v / peak - 1));
}

function drawDrawdown(curves, report) {
  const svg = document.getElementById("chart-drawdown");
  const H = 300, bottom = H - 30;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.style.color = "var(--ink)";
  hatch(svg);
  const n = curves.dates.length;
  const x = (i) => LEFT + (i / (n - 1)) * (W - LEFT - RIGHT);
  const y = (v) => TOP + (-v / 0.8) * (bottom - TOP);
  for (const v of [0, -0.2, -0.4, -0.6, -0.8]) {
    svg.append(el("line", { x1: LEFT, x2: W - RIGHT, y1: y(v), y2: y(v), class: "axis" }));
    svg.append(el("text", { x: LEFT - 8, y: y(v) + 4, "text-anchor": "end" }, v === 0 ? "High" : pct(v, 0)));
  }
  yearTicks(svg, curves.dates, x, bottom);
  // The curves are thinned for the page, so the worst fall is read from the full-resolution report.
  const series = [
    ["btc", drawdowns(curves.btc_hold), "Holding bitcoin", report.benchmarks.btc_hold.full.max_drawdown],
    ["fallow", drawdowns(curves.fallow), "Fallow", report.fallow.full.max_drawdown],
  ];
  for (const [cls, dd, label, worst] of series) {
    const pts = dd.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    svg.append(el("path", { d: `M${x(0)},${y(0)}L${pts.join("L")}L${x(n - 1)},${y(0)}Z`, class: `area ${cls}` }));
    svg.append(el("path", { d: `M${pts.join("L")}`, class: `line ${cls}` }));
    // Label each line in the right gutter, where nothing else is drawn.
    const ly = Math.max(y(dd[n - 1]), TOP + 10) + (cls === "btc" ? 4 : -6);
    const t = el("text", { x: x(n - 1) + 8, y: ly, class: "label" }, label);
    const sub = el("text", { x: x(n - 1) + 8, y: ly + 15 }, `max drawdown ${pct(worst, 0)}`);
    t.style.fill = sub.style.fill = cls === "btc" ? "var(--ink)" : "var(--wheat-ink)";
    svg.append(sub);
    svg.append(t);
  }
}

function drawGrowth(curves, report) {
  const svg = document.getElementById("chart-growth");
  const H = 300, bottom = H - 30;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const n = curves.dates.length;
  const lo = Math.log10(0.5), hi = Math.log10(Math.max(...curves.btc_hold) * 1.15);
  const x = (i) => LEFT + (i / (n - 1)) * (W - LEFT - RIGHT);
  const y = (v) => bottom - ((Math.log10(v) - lo) / (hi - lo)) * (bottom - TOP);
  for (const v of [1, 10]) {
    svg.append(el("line", { x1: LEFT, x2: W - RIGHT, y1: y(v), y2: y(v), class: "axis" }));
    svg.append(el("text", { x: LEFT - 8, y: y(v) + 4, "text-anchor": "end" }, v + "×"));
  }
  yearTicks(svg, curves.dates, x, bottom);
  const marks = [[report.holdout_start, "out of sample from here"], [report.rtoken_listing, "rTokens live"]];
  for (const [date, label] of marks) {
    const i = curves.dates.findIndex((d) => d >= date);
    if (i < 0) continue;
    svg.append(el("line", { x1: x(i), x2: x(i), y1: TOP, y2: bottom, class: "axis", "stroke-dasharray": "3 4" }));
    svg.append(el("text", { x: x(i) - 5, y: TOP + 10, "text-anchor": "end" }, label));
  }
  for (const [cls, key, label] of [["btc", "btc_hold", "Holding bitcoin"], ["fallow", "fallow", "Fallow"]]) {
    const pts = curves[key].map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
    svg.append(el("path", { d: `M${pts.join("L")}`, class: `line ${cls}` }));
    const end = curves[key][n - 1];
    const t = el("text", { x: x(n - 1) + 8, y: y(end) + 4, class: "label" }, `${label} ${end.toFixed(1)}×`);
    t.style.fill = cls === "btc" ? "var(--ink)" : "var(--wheat-ink)";
    svg.append(t);
  }
}

function drawGrid(values, ours) {
  const svg = document.getElementById("chart-grid");
  const H = 150, base = H - 34;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  const lo = Math.floor(Math.min(...values, ours) * 10 - 1) / 10;
  const hi = Math.ceil(Math.max(...values, ours) * 10 + 1) / 10;
  const x = (v) => LEFT + ((v - lo) / (hi - lo)) * (W - LEFT - 24);
  svg.append(el("line", { x1: LEFT, x2: W - 24, y1: base, y2: base, class: "axis" }));
  for (let v = lo; v <= hi + 1e-9; v += 0.1) {
    svg.append(el("text", { x: x(v), y: base + 18, "text-anchor": "middle" }, v.toFixed(1)));
  }
  svg.append(el("text", { x: W - 24, y: base + 32, "text-anchor": "end" }, "Out-of-sample Sharpe"));
  for (const v of values) svg.append(el("line", { x1: x(v), x2: x(v), y1: base - 26, y2: base, class: "tick" }));
  svg.append(el("line", { x1: x(ours), x2: x(ours), y1: base - 72, y2: base, class: "tick ours" }));
  const t = el("text", { x: x(ours) + 8, y: base - 62, class: "label" }, `This page, ${num(ours)}`);
  t.style.fill = "var(--wheat-ink)";
  svg.append(t);
}

function drawMetrics(report) {
  const body = document.querySelector("#metrics tbody");
  const groups = [
    ["full", `Whole period, ${monthYear(report.fallow_first)} to ${monthYear(report.last_day)}`],
    ["in_sample", "In sample, to December 2023"],
    ["held_out", "Out of sample, January 2024 on"],
    ["rtoken_era", `Since rTokens went live, ${monthYear(report.rtoken_listing)} on`],
  ];
  for (const [key, title] of groups) {
    body.append(html("tr", "group", `<td colspan="6">${title}</td>`));
    for (const [label, m, cls] of [["Fallow", report.fallow[key], "ours"], ["Holding bitcoin", report.benchmarks.btc_hold[key], ""]]) {
      body.append(html("tr", cls,
        `<td>${label}</td><td>${num(m.sharpe)}</td><td>${num(m.sortino)}</td><td>${pct(m.max_drawdown)}</td>` +
        `<td>${pct(m.cagr)}</td><td>${num(m.turnover_per_year, 1)}×</td>`));
    }
  }
  const years = Object.keys(report.yearly.fallow);
  document.querySelector("#years thead tr").innerHTML = "<th></th>" + years.map((y) => `<th>${y}</th>`).join("");
  const yb = document.querySelector("#years tbody");
  for (const [label, row, cls] of [["Fallow", report.yearly.fallow, "ours"], ["Holding bitcoin", report.yearly.btc_hold, ""]]) {
    yb.append(html("tr", cls, `<td>${label}</td>` + years.map((y) => `<td>${pct(row[y], 0)}</td>`).join("")));
  }
}

function drawScorecard(report) {
  const f = report.fallow, body = document.querySelector("#scorecard tbody");
  const rows = [
    [`Whole period, ${num(f.full.years, 1)} years`, f.full],
    [`In sample, ${num(f.in_sample.years, 1)} years`, f.in_sample],
    [`Out of sample, ${num(f.held_out.years, 1)} years`, f.held_out],
    ["Last 365 days", f.last_year],
  ];
  for (const [label, m] of rows) {
    body.append(html("tr", "",
      `<td>${label}</td><td>${num(m.sharpe)}</td><td>${num(m.sortino)}</td><td>${pct(m.max_drawdown)}</td>` +
      `<td>${pct(m.cagr)}</td><td>${num(m.turnover_per_year, 1)}\u00d7</td>`));
  }
  document.getElementById("scorecard-note").innerHTML =
    `Out-of-sample Sharpe is ${num(f.decay_ratio)} of in-sample. Rolling 30-day Sharpe is positive in ` +
    `${pct(f.full.rolling30_share_positive, 0)} of windows. Holding bitcoin over the whole period scored ` +
    `${num(report.benchmarks.btc_hold.full.sharpe)} with a ${pct(-report.benchmarks.btc_hold.full.max_drawdown, 0)} max drawdown. ` +
    `The last year lost money, and <a href="#loses">the section on where it loses</a> says why.`;
}

function drawAdds(report) {
  const rows = [
    ["Crypto and USDT only", report.ablations.crypto_only_trend.held_out.sharpe, ""],
    ["Holding bitcoin", report.benchmarks.btc_hold.held_out.sharpe, ""],
    ["Everything in the one strongest asset", report.ablations.one_field_at_a_time.held_out.sharpe, ""],
    ["All five assets", report.fallow.held_out.sharpe, "ours"],
  ];
  const max = Math.max(...rows.map((r) => r[1]));
  const one = report.ablations.one_field_at_a_time.full;
  document.getElementById("one-field").textContent =
    `We also tried putting everything in the single strongest asset each week. Over the whole period that grew ` +
    `${pct(one.cagr, 0)} a year, fell ${pct(-one.max_drawdown, 0)} at its worst and traded ${num(one.turnover_per_year, 0)} times the account a year. ` +
    `Its Sharpe was ${num(one.sharpe)} against ${num(report.fallow.full.sharpe)} for five assets sharing the risk.`;
  const box = document.getElementById("adds-bars");
  for (const [label, v, cls] of rows) {
    box.append(html("div", `bar ${cls}`,
      `<span class="name">${label}</span><div class="track"><div class="fill" style="width:${(v / max) * 100}%"></div></div>` +
      `<span class="value">${num(v)}</span>`));
  }
}

function drawLosses(report) {
  const f = report.fallow, a = report.ablations, c = report.cost_sensitivity;
  const worst = report.worst_drawdowns.fallow[0];
  const items = [
    `It has lost money since rTokens went live. From ${longDate(report.rtoken_listing)} it is down ${pct(-f.rtoken_era.total_return)} ` +
      `while bitcoin rose ${pct(report.benchmarks.btc_hold.rtoken_era.total_return, 0)}. That is ${f.rtoken_era.days} days, which is short. ` +
      `It is also the only stretch that used real rToken prices.`,
    `Its last year was a losing one. Over the most recent 365 days it is down ${pct(-f.last_year.total_return)}, with a Sharpe of ${num(f.last_year.sharpe)}. ` +
      `A one-year backtest, which is what most strategy listings show, would make Fallow look bad. Holding bitcoin lost ` +
      `${pct(-report.benchmarks.btc_hold.last_year.total_return, 0)} over the same year, and Bitget's own official cross-asset rotation Playbook ` +
      `was flat over its first 82 live days.`,
    `It leans on gold. Take gold out and the out-of-sample Sharpe falls from ${num(f.held_out.sharpe)} to ` +
      `${num(a.without_RGLDUSDT.held_out.sharpe)}. Much of 2024 and 2025 was a gold story.`,
    `Five assets flatter it. We fixed the five before looking, following Harry Browne's old portfolio of stocks, bonds, gold and cash, ` +
      `plus two coins. A nine-asset version with foreign shares, mid Treasuries and oil scores ${num(a.nine_fields.held_out.sharpe)} out of sample.`,
    `It trails bitcoin badly in a bull run. On average ${pct(f.full.avg_exposure, 0)} of the account is invested. ` +
      `Bitcoin grew ${pct(report.benchmarks.btc_hold.full.cagr, 0)} a year over the whole period and Fallow grew ${pct(f.full.cagr, 0)}.`,
    `The result depends on costs. We assume 15 bp a trade. At 30 bp the out-of-sample Sharpe is ${num(c["30bp"].held_out.sharpe)}, and at 60 bp it is ${num(c["60bp"].held_out.sharpe)}.`,
    `The Sharpe is a rough figure. On ${num(f.held_out.years, 1)} out-of-sample years its standard error is ${num(f.held_out.sharpe_stderr)}, ` +
      `so the true number could sit anywhere from about ${num(f.held_out.sharpe - f.held_out.sharpe_stderr, 1)} to ${num(f.held_out.sharpe + f.held_out.sharpe_stderr, 1)}.`,
    `Its losing stretches are long. The worst ran from ${monthYear(worst.from)} to ${monthYear(worst.to)}, a fall of ${pct(-worst.depth)} ` +
      `that took most of two years. Short stretches are unreliable: ${pct(f.full.rolling30_share_positive, 0)} of 30-day windows had a positive Sharpe.`,
  ];
  const ol = document.getElementById("losses");
  for (const item of items) ol.append(html("li", "", item));
}

function drawRobustness(report) {
  const h = report.one_year_holds, hb = document.querySelector("#holds tbody");
  for (const [label, m, cls] of [["Fallow", h.fallow, "ours"], ["Holding bitcoin", h.btc_hold, ""]]) {
    hb.append(html("tr", cls,
      `<td>${label}</td><td>${pct(m.share_positive, 0)} of periods</td><td>${pct(m.worst)}</td><td>${pct(m.tenth_percentile)}</td>` +
      `<td>${pct(m.median)}</td><td>${pct(m.best, 0)}</td>`));
  }
  fill("hold-n", h.fallow.periods.toLocaleString("en-GB"));
  const sb = document.querySelector("#storms tbody");
  for (const s of report.storms) {
    sb.append(html("tr", "", `<td>${monthYear(s.from)}</td><td>${monthYear(s.to)}</td><td>${pct(s.btc)}</td><td><b>${pct(s.fallow)}</b></td>`));
  }
}

async function main() {
  const { report, curves, grid_held_out } = await (await fetch("data/fallow.json")).json();
  report.fallow_first = curves.dates[0];

  document.getElementById("weekly-note").textContent = weeklyNote(report);
  document.getElementById("plan-date").textContent = `Set from the midday price in New York on Monday ${longDate(report.plan.as_of)}.`;
  drawFields(report);
  drawScorecard(report);
  drawRobustness(report);
  drawDrawdown(curves, report);
  drawGrowth(curves, report);
  drawMetrics(report);
  drawAdds(report);
  drawLosses(report);
  drawGrid(grid_held_out, report.fallow.held_out.sharpe);

  fill("btc-dd", pct(-report.benchmarks.btc_hold.full.max_drawdown, 0));
  fill("fallow-dd", pct(-report.fallow.full.max_drawdown, 0));
  fill("decay", num(report.fallow.decay_ratio));
  fill("grid-n", report.grid.variants);
  fill("span", `${monthYear(curves.dates[0])} to ${monthYear(report.last_day)}`);
  fill("listing", longDate(report.rtoken_listing));
  const g = report.grid;
  document.getElementById("grid-note").textContent =
    `Every version stayed above ${num(g.held_out_sharpe.min, 1)}. The one on this page sits at the ` +
    `${Math.round(g.default_percentile_held_out * 100)}th percentile, so about three in four of the alternatives did better. ` +
    `We kept the textbook settings, because choosing the best of ${g.variants} after seeing the results would overstate what the rule can do.`;
  document.getElementById("built").textContent = `Numbers built ${report.built} from candles to ${longDate(report.last_day)}.`;
  // live.js takes it from here: it recomputes the plan from Bitget's public API and runs the Monday list.
  window.Fallow = {
    report, curves, pct, num, html, el, longDate, monthYear, list,
    redrawPlan(plan, status) {
      report.plan = plan;
      document.getElementById("weekly-note").textContent = weeklyNote(report);
      document.getElementById("plan-date").textContent = status;
      drawFields(report);
    },
  };
  document.dispatchEvent(new Event("fallow-ready"));
}

// The switch in the nav flips between light and dark and remembers the choice.
document.getElementById("theme").addEventListener("click", () => {
  const root = document.documentElement;
  const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
  try { localStorage.setItem("fallow-theme", root.dataset.theme); } catch (e) {}
});

main().catch((err) => {
  document.getElementById("weekly-note").textContent = "The field book did not load. Try again in a minute.";
  console.error(err);
});

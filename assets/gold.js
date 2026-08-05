// ── Gold rates page - live rates, history chart, forecast calculator ──
const TOLA_G = 11.6638;
let GDATA = null;
let gCharts = {};

document.addEventListener("DOMContentLoaded", () => {
  fetch("/data.json?v=" + Date.now())
    .then(r => r.json())
    .then(d => { GDATA = d; initGold(); })
    .catch(() => {
      const el = document.getElementById("gr-source");
      if (el) el.textContent = "Live rate unavailable right now - please refresh.";
    });
});

// Pakistani comma formatting: X,XX,XXX
function fmtPKR(n) {
  if (n == null || isNaN(n)) return "-";
  n = Math.round(n);
  const s = String(Math.abs(n));
  let out;
  if (s.length <= 3) out = s;
  else {
    let r = s.slice(-3), rest = s.slice(0, -3);
    while (rest.length > 2) { r = rest.slice(-2) + "," + r; rest = rest.slice(0, -2); }
    out = rest + "," + r;
  }
  return (n < 0 ? "-" : "") + out;
}
function rs(n) { return "₨" + fmtPKR(n); }

// Parse "Jun'26" → Date
function parseLbl(lbl) {
  const M = { Jan:0, Feb:1, Mar:2, Apr:3, May:4, Jun:5, Jul:6, Aug:7, Sep:8, Oct:9, Nov:10, Dec:11 };
  const m = /^([A-Za-z]{3})'(\d{2})$/.exec(lbl || "");
  if (!m) return null;
  return new Date(2000 + parseInt(m[2], 10), M[m[1]] ?? 0, 1);
}

function setT(id, v) { const el = document.getElementById(id); if (el) el.textContent = v; }

function initGold() {
  const g = GDATA.gold;
  if (!g) { setT("gr-source", "Gold data unavailable."); return; }

  // ── Live rate grid ──
  setT("gr-tola24", rs(g.tola_24k));
  setT("gr-tola22", rs(g.tola_22k));
  setT("gr-10g24",  rs(g.g10_24k));
  setT("gr-gram24", rs(g.gram_24k));
  setT("gr-10g22",  rs(g.g10_22k));
  setT("gr-gram22", rs(g.gram_22k));
  setT("gr-tola24-m", rs(g.tola_24k));
  // 21K and 18K are estimated off the 24K rate; a tola is 11.6638 g.
  [21, 18].forEach(k => {
    const tola = Math.round(g.tola_24k * k / 24);
    setT("gr-tola" + k, rs(tola));
    setT("gr-10g" + k,  rs(Math.round(tola / 11.6638 * 10)));
    setT("gr-gram" + k, rs(Math.round(tola / 11.6638)));
  });

  // Change badge
  const chg = document.getElementById("gr-chg");
  if (chg && g.chg1y_pct != null) {
    const up = g.chg1y_pct >= 0;
    chg.textContent = (up ? "▲ " : "▼ ") + Math.abs(g.chg1y_pct) + "% over 1 year";
    chg.style.background = up ? "var(--green-light)" : "var(--red-light)";
    chg.style.color = up ? "var(--green)" : "var(--red)";
    chg.style.borderColor = "transparent";
  }

  // Source + date
  const when = new Date(GDATA.updated).toLocaleDateString("en-PK", { day: "numeric", month: "long", year: "numeric" });
  const note = g.source_type === "local"
    ? "Source: local Sarafa rate via gold.pk."
    : "Source: international spot (gold futures × PKR/USD).";
  setT("gr-source", `As of ${when}. ${note} 21K and 18K are estimated from the 24K rate (×87.5% and ×75%). Local shop prices add making charges.`);
  setT("gold-asof", "Updated " + when);

  // ── History chart + CAGR ──
  renderHistory();
  const cagr = computeCAGR();

  // ── Calculator ──
  // Default growth stays at a defensible long-run assumption (~15% in PKR =
  // long-run gold in USD + expected rupee depreciation), NOT the raw historical
  // CAGR, which is depreciation-inflated and unlikely to repeat. We surface the
  // historical figure as context and let the user edit.
  if (cagr != null) {
    setT("gc-rate-help", `Default 15%/yr ≈ long-run gold + expected rupee depreciation. For reference, gold averaged ~${cagr.toFixed(0)}%/yr over the last ${cagrYears.toFixed(1)} years (CPI inflation: ${GDATA.macro.inflation_cpi}%). Edit to your own view.`);
  } else {
    setT("gc-rate-help", `Default 15%/yr is a long-run assumption. CPI inflation is ${GDATA.macro.inflation_cpi}%. Edit to your own view.`);
  }

  const amt = document.getElementById("gc-amount");
  amt.addEventListener("input", () => {
    const raw = amt.value.replace(/[^0-9]/g, "");
    amt.value = raw ? fmtPKR(parseInt(raw, 10)) : "";
    calcGold();
  });
  ["gc-years", "gc-rate"].forEach(id => document.getElementById(id).addEventListener("input", calcGold));
  document.querySelectorAll('input[name="gc-karat"]').forEach(r => r.addEventListener("change", calcGold));
  calcGold();
}

let cagrYears = 0;
function computeCAGR() {
  const h = GDATA.gold.history;
  if (!h || !h.values || h.values.length < 2) return null;
  const first = h.values[0], last = h.values[h.values.length - 1];
  const d0 = parseLbl(h.labels[0]), d1 = parseLbl(h.labels[h.labels.length - 1]);
  if (!first || !last || !d0 || !d1) return null;
  cagrYears = (d1 - d0) / (365.25 * 24 * 3600 * 1000);
  if (cagrYears < 0.5) return null;
  const cagr = (Math.pow(last / first, 1 / cagrYears) - 1) * 100;
  setT("gr-cagr", `Over the last ${cagrYears.toFixed(1)} years, 24K gold rose from ${rs(first)} to ${rs(last)} per tola - a compound average of about ${cagr.toFixed(1)}% per year (in rupee terms, currency depreciation included).`);
  return Math.max(0, cagr);
}

function renderHistory() {
  const ctx = document.getElementById("gr-history");
  if (!ctx || typeof Chart === "undefined" || !GDATA.gold.history) return;
  if (gCharts.hist) gCharts.hist.destroy();
  gCharts.hist = new Chart(ctx.getContext("2d"), {
    type: "line",
    data: {
      labels: GDATA.gold.history.labels,
      datasets: [{
        label: "24K gold (PKR/tola)",
        data: GDATA.gold.history.values,
        borderColor: "#B7791F",
        backgroundColor: "rgba(242,185,75,.18)",
        borderWidth: 3, pointRadius: 0, fill: true, tension: .35,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: c => " " + rs(c.parsed.y) + " / tola" } } },
      scales: {
        y: { ticks: { callback: v => (v / 1000).toFixed(0) + "K" }, grid: { color: "#E6EBF1" } },
        x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 9 }, grid: { display: false } }
      }
    }
  });
}

function calcGold() {
  const g = GDATA.gold;
  const amount = parseInt((document.getElementById("gc-amount").value || "").replace(/[^0-9]/g, ""), 10) || 0;
  const years = Math.min(30, Math.max(1, parseInt(document.getElementById("gc-years").value, 10) || 1));
  const rate = Math.max(0, parseFloat(document.getElementById("gc-rate").value) || 0);
  const karat = (document.querySelector('input[name="gc-karat"]:checked') || {}).value || "24";
  const tolaRate = karat === "22" ? g.tola_22k : g.tola_24k;
  const infl = GDATA.macro.inflation_cpi || 0;

  const resEl = document.getElementById("gc-result");
  if (!amount) { resEl.innerHTML = '<div style="color:#8a887d">Enter an amount to see the projection.</div>'; drawProjection([], []); return; }

  const tolas = amount / tolaRate;
  const grams = tolas * TOLA_G;
  const future = amount * Math.pow(1 + rate / 100, years);
  const gain = future - amount;
  const gainPct = (gain / amount) * 100;
  const real = future / Math.pow(1 + infl / 100, years);

  // National Savings comparison (best rate open to all Pakistanis)
  const pub = (GDATA.national_savings || []).filter(s => s.eligible === "All Pakistanis");
  const nsRate = pub.length ? Math.max(...pub.map(s => s.rate)) : 11.5;
  const nsFuture = amount * Math.pow(1 + nsRate / 100, years);

  resEl.innerHTML = `
    <div class="gold-stat-grid">
      <div class="gold-stat"><div class="v">${tolas.toFixed(2)} tola</div><div class="l">Gold bought now (${grams.toFixed(1)} g, ${karat}K)</div></div>
      <div class="gold-stat"><div class="v">${rs(future)}</div><div class="l">Value after ${years} yr @ ${rate}%/yr</div></div>
      <div class="gold-stat"><div class="v" style="color:${gain >= 0 ? "#0E3B2E" : "#C24132"}">${gain >= 0 ? "+" : ""}${rs(gain)}</div><div class="l">Total gain (${gainPct >= 0 ? "+" : ""}${gainPct.toFixed(0)}%)</div></div>
      <div class="gold-stat"><div class="v">${rs(real)}</div><div class="l">Real value (today's rupees)</div></div>
    </div>
    <p style="font-size:.86rem;color:var(--ink2);margin:14px 0 0;line-height:1.6">
      At the current ${karat}K rate of <strong>${rs(tolaRate)}/tola</strong>, <strong>${rs(amount)}</strong> buys about <strong>${tolas.toFixed(2)} tola</strong>.
      At ${rate}%/yr it could be worth <strong>${rs(future)}</strong> in ${years} years.
      The same amount in a National Savings certificate at <strong>${nsRate}%</strong> would reach <strong>${rs(nsFuture)}</strong> -
      ${future >= nsFuture ? "gold ahead by " + rs(future - nsFuture) : "savings ahead by " + rs(nsFuture - future)}, before tax, charges and zakat.
      Unlike savings, gold pays no income while you hold it.
    </p>`;

  // Projection series
  const labels = [], goldS = [], nsS = [], cashS = [];
  for (let y = 0; y <= years; y++) {
    labels.push(y === 0 ? "Now" : "Yr " + y);
    goldS.push(Math.round(amount * Math.pow(1 + rate / 100, y)));
    nsS.push(Math.round(amount * Math.pow(1 + nsRate / 100, y)));
    cashS.push(Math.round(amount / Math.pow(1 + infl / 100, y)));
  }
  drawProjection(labels, [
    { label: "Gold @ " + rate + "%", data: goldS, color: "#B7791F" },
    { label: "National Savings @ " + nsRate + "%", data: nsS, color: "#075E4B" },
    { label: "If kept as cash (real)", data: cashS, color: "#C24132" },
  ]);
}

function drawProjection(labels, sets) {
  const ctx = document.getElementById("gc-chart");
  if (!ctx || typeof Chart === "undefined") return;
  if (gCharts.proj) gCharts.proj.destroy();
  gCharts.proj = new Chart(ctx.getContext("2d"), {
    type: "line",
    data: {
      labels,
      datasets: sets.map(s => ({
        label: s.label, data: s.data,
        borderColor: s.color, backgroundColor: s.color + "22",
        borderWidth: 2.5, pointRadius: 0, tension: .25,
        fill: false, borderDash: s.color === "#C24132" ? [5, 4] : [],
      }))
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { font: { size: 11 }, usePointStyle: true, boxWidth: 8 } },
        tooltip: { callbacks: { label: c => " " + c.dataset.label + ": " + rs(c.parsed.y) } }
      },
      scales: {
        y: { ticks: { callback: v => "₨" + (v / 1000).toFixed(0) + "K" }, grid: { color: "#E6EBF1" } },
        x: { grid: { display: false } }
      }
    }
  });
}

// Pakistan investment education interface.

let DATA = null;
let AMOUNT = 0;
let currentPage = 0;
let selectedProfile = "balanced";

const PROFILE_MIXES = {
  balanced: [30, 25, 20, 20, 5],
  income: [45, 30, 10, 10, 5],
  growth: [15, 20, 35, 25, 5],
};

const PROFILE_LABELS = {
  balanced: "Mixed example",
  income: "Income tilt",
  growth: "Equity tilt",
};

const PORTFOLIO_ALLOC = [
  { label: "Government savings", pct: 30, color: "#075E4B",
    type: "National Savings or government securities", where: "Compare current rates, access rules and eligibility" },
  { label: "Income or money-market funds", pct: 25, color: "#2854C5",
    type: "Lower-volatility mutual fund category", where: "Compare MUFAP returns, fees and risk profiles" },
  { label: "Diversified equity funds", pct: 20, color: "#F2B94B",
    type: "Market-linked mutual fund category", where: "Review the fund manager, holdings and benchmark" },
  { label: "PSX equity basket", pct: 20, color: "#C24132",
    type: "Diversified listed shares", where: "Use a PSX-recognized, SECP-licensed broker" },
  { label: "Liquid reserve", pct: 5, color: "#667085",
    type: "Cash or accessible savings", where: "Keep access, fees and withdrawal time in view" },
];

// ── Load data.json on startup ─────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  formatAmountInput();
  initProfileToggle();
  fetch("data.json?v=" + Date.now())
    .then(r => r.json())
    .then(d => {
      DATA = d;
      applyData();
    })
    .catch(() => {
      document.getElementById("data-age").textContent = "Data unavailable - retrying…";
      // Retry once after 3 s (handles transient network hiccup on page load)
      setTimeout(() => {
        fetch("data.json?v=" + Date.now())
          .then(r => r.json())
          .then(d => { DATA = d; applyData(); })
          .catch(() => {
            document.getElementById("data-age").textContent = "Data unavailable";
            if (currentPage === 4) renderPortfolio();
          });
      }, 3000);
    });
});

function applyData() {
  if (!DATA) return;

  // Header age
  const updated = new Date(DATA.updated);
  const staleSources = Object.entries(DATA.data_health || {})
    .filter(([, health]) => health && health.stale)
    .map(([name]) => name);
  const ageEl = document.getElementById("data-age");
  const cutoff = updated.toLocaleDateString("en-PK", { day: "numeric", month: "long", year: "numeric" });
  ageEl.textContent = `Data cutoff: ${cutoff}` +
    (staleSources.length ? ` · ${staleSources.length} source group${staleSources.length === 1 ? "" : "s"} stale` : "");
  if (staleSources.length) ageEl.title = `Stale source groups: ${staleSources.join(", ")}`;
  setText("hero-data-age", `Dataset: ${cutoff}`);

  // Macro pills
  const m = DATA.macro;
  document.getElementById("m-kse").textContent = (m.kse100_level / 1000).toFixed(0) + "K";
  document.getElementById("m-sbp").textContent = m.sbp_rate + "%";
  document.getElementById("m-pkr").textContent = "₨" + m.pkr_usd;
  document.getElementById("m-inf").textContent = m.inflation_cpi + "%";
  setText("h-kse", (m.kse100_level / 1000).toFixed(0) + "K");
  setText("h-sbp", m.sbp_rate + "%");
  setText("h-pkr", "₨" + m.pkr_usd);
  setText("h-inf", m.inflation_cpi + "%");

  // Per-metric provenance on hover (source + the data's own 'as of' date), so a
  // Readers can inspect the source and the data's own cutoff on hover.
  const setTitle = (id, t) => { const e = document.getElementById(id); if (e && t) e.title = t; };
  const prov = {
    "inf": "CPI inflation YoY · PBS" + (m.inflation_cpi_asof ? " · " + m.inflation_cpi_asof : ""),
    "kse": "KSE-100 close · PSX" + (m.kse100_asof ? " · " + m.kse100_asof : ""),
    // When the SBP interbank M2M rate is unreachable, forex fails over to a
    // third-party reference rate (m.pkr_usd_approx) — label it honestly rather
    // than attributing a non-SBP number to SBP interbank.
    "pkr": (m.pkr_usd_approx
              ? "USD/PKR reference rate (SBP unavailable) · " + (m.pkr_usd_source || "fallback")
              : "Interbank USD/PKR · SBP")
           + (m.pkr_usd_asof ? " · " + m.pkr_usd_asof : ""),
    "sbp": "SBP policy rate" + (m.sbp_direction ? " · " + m.sbp_direction : ""),
  };
  Object.entries(prov).forEach(([k, t]) => { setTitle("m-" + k, t); setTitle("h-" + k, t); });

  const snap = document.getElementById("snapshot-date");
  if (snap) {
    const d = new Date(DATA.updated);
    snap.textContent =
      "As of " + d.toLocaleDateString("en-PK", { day: "numeric", month: "long", year: "numeric" }) +
      " · Sources: PBS, SBP, PSX, MUFAP, National Savings";
  }

  // Dated ticker tape, best-effort and only if present.
  renderTicker();

  // Charts (page 0)
  renderKSEChart();
  renderSBPChart();

  // Dated gold-rate card
  renderGold();

  // Dated fuel-price card
  renderFuel();

  // Re-render whichever page is already visible so data arrives even if
  // the user navigated before the fetch completed.
  if (currentPage === 1) renderNationalSavings();
  else if (currentPage === 2) renderMutualFunds();
  else if (currentPage === 3) renderStocks();
  else if (currentPage === 4) renderPortfolio();
}

// ── Amount input - Pakistani comma formatting ─────────────────────
function formatAmountInput() {
  const inp = document.getElementById("amount-input");
  inp.addEventListener("input", () => {
    let raw = inp.value.replace(/[^0-9]/g, "");
    if (raw) inp.value = formatPKR(parseInt(raw, 10));
    else inp.value = "";
    clearAmountError();
    updateScenarioSummary();
  });
  inp.addEventListener("keydown", e => {
    if (e.key === "Enter") startComparison();
  });
}

function initProfileToggle() {
  document.querySelectorAll(".profile-option").forEach(btn => {
    btn.addEventListener("click", () => {
      selectedProfile = btn.dataset.profile || "balanced";
      document.querySelectorAll(".profile-option").forEach(el => {
        el.classList.toggle("active", el === btn);
      });
      applyProfileAllocation();
      updateScenarioSummary();
      if (currentPage === 2) renderMutualFunds();
      if (currentPage === 4) renderPortfolio();
    });
  });
  updateScenarioSummary();
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function applyProfileAllocation() {
  const mix = PROFILE_MIXES[selectedProfile] || PROFILE_MIXES.balanced;
  PORTFOLIO_ALLOC.forEach((a, i) => { a.pct = mix[i]; });
}

function updateScenarioSummary() {
  const el = document.getElementById("hero-score");
  if (!el) return;
  const amount = parseAmount();
  el.innerHTML = amount
    ? `<span>Illustrative scenario</span><strong>${PROFILE_LABELS[selectedProfile]} mix · PKR ${formatPKR(amount)}</strong>`
    : "<span>Illustrative scenario</span><strong>Enter an amount</strong>";
}

function formatPKR(n) {
  // Pakistani numbering: X,XX,XXX - group the integer part only, keep decimals.
  if (isNaN(n)) return "0";
  const neg = Number(n) < 0;
  const [intRaw, decPart] = String(Math.abs(Number(n))).split(".");
  let result = intRaw;
  if (intRaw.length > 3) {
    let tail = intRaw.slice(-3);
    let rest = intRaw.slice(0, -3);
    while (rest.length > 2) {
      tail = rest.slice(-2) + "," + tail;
      rest = rest.slice(0, -2);
    }
    result = rest + "," + tail;
  }
  return (neg ? "-" : "") + result + (decPart ? "." + decPart : "");
}

function parseAmount() {
  const raw = document.getElementById("amount-input").value.replace(/[^0-9]/g, "");
  return parseInt(raw, 10) || 0;
}

// ── Navigation ────────────────────────────────────────────────────
function goPage(n) {
  if (n < 0 || n > 4) return;

  // Mark step pills
  document.querySelectorAll(".step-pill").forEach((el, i) => {
    el.classList.remove("active", "done");
    if (i === n) el.classList.add("active");
    else if (i < n) el.classList.add("done");
  });

  // Show/hide pages
  document.querySelectorAll(".page").forEach((el, i) => {
    el.classList.toggle("active", i === n);
  });

  // Progress bar (optional - removed from homepage)
  const _pb = document.getElementById("progress-bar");
  if (_pb) _pb.style.width = ((n + 1) / 5 * 100) + "%";

  currentPage = n;
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Lazy-render page content
  if (n === 1) renderNationalSavings();
  if (n === 2) renderMutualFunds();
  if (n === 3) renderStocks();
  if (n === 4) {
    renderPortfolio();
    if (!goPage._completed && window.pkTrack) {
      goPage._completed = true;   // fire once per session
      window.pkTrack("calculator_complete", { amount_band: amountBand(AMOUNT) });
    }
  }
}

function amountBand(n) {
  if (n < 50000) return "under_50k";
  if (n < 200000) return "50k_200k";
  if (n < 1000000) return "200k_1m";
  return "1m_plus";
}

function startComparison() {
  AMOUNT = parseAmount();
  if (AMOUNT < 1000) {
    showAmountError("Enter at least PKR 1,000 to compare.");
    return;
  }
  clearAmountError();
  if (window.pkTrack) window.pkTrack("calculator_use", { amount_band: amountBand(AMOUNT) });
  goPage(1);
}

function showAmountError(message) {
  const el = document.getElementById("amount-error");
  if (!el) return;
  el.textContent = message;
  el.classList.add("visible");
}

function clearAmountError() {
  const el = document.getElementById("amount-error");
  if (!el) return;
  el.textContent = "";
  el.classList.remove("visible");
}

// Step pill click (step-nav removed from homepage - guard if absent)
const _stepNav = document.getElementById("step-nav");
if (_stepNav) _stepNav.addEventListener("click", e => {
  const pill = e.target.closest(".step-pill");
  if (!pill) return;
  const step = parseInt(pill.dataset.step, 10);
  if (step === 0) { goPage(0); return; }
  if (!AMOUNT) { startComparison(); return; }
  goPage(step);
});

// ── PAGE 1 - National Savings ─────────────────────────────────────
function renderNationalSavings() {
  if (!DATA) return;
  const tbody = document.getElementById("ns-tbody");
  tbody.innerHTML = "";

  DATA.national_savings.forEach(s => {
    const earn = AMOUNT > 0 ? Math.round(AMOUNT * s.rate / 100) : null;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <strong>${s.name}</strong>
        ${s.shariah ? '<span class="badge badge-green" style="margin-left:4px">Shariah</span>' : ""}
      </td>
      <td class="num yield-hi">${s.rate}%</td>
      <td>${s.tenure}</td>
      <td>${s.payout}</td>
      <td class="num" style="color:#23415E;font-weight:700">
        ${earn ? "PKR " + formatPKR(earn) + "/yr" : "-"}
      </td>
      <td>${s.eligible}</td>
      <td style="font-size:.8rem;color:#555">Rate effective ${s.rate_effective || "date not supplied"}; check tax and encashment terms.</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── PAGE 2 - Mutual Funds ─────────────────────────────────────────
function renderMutualFunds() {
  if (!DATA) return;
  const grid = document.getElementById("funds-grid");
  grid.innerHTML = "";
  const fundHealth = DATA.data_health && DATA.data_health.funds;
  if (fundHealth && fundHealth.stale) {
    const asOf = fundHealth.as_of ? ` Last successful source date: ${fundHealth.as_of}.` : "";
    grid.insertAdjacentHTML("beforeend", `<div role="status" style="grid-column:1/-1;border:1px solid #D6A84B;background:#FFF8E6;padding:12px 14px;font-size:.82rem;color:#614A14"><strong>Stale fund data.</strong>${asOf} MUFAP refresh did not complete; use the linked MUFAP table for current figures.</div>`);
  }

  DATA.mutual_funds.forEach(f => {
    const full = AMOUNT > 0 ? Math.round(AMOUNT * f.ret_1y / 100) : null;

    const card = document.createElement("div");
    card.className = "fund-card";
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">
        <div class="fund-name">${f.name}</div>
      </div>
      <div class="fund-mgr">${f.manager} &nbsp;·&nbsp; ${f.type}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">
        ${f.shariah ? '<span class="badge badge-green">Shariah</span>' : '<span class="badge badge-grey">Conventional</span>'}
        <span class="badge badge-${riskBadge(f.risk)}">${f.risk} Risk</span>
      </div>
      <div class="fund-returns">
        <div class="ret-box"><div class="ret-val">${f.ret_1y}%</div><div class="ret-lbl">1-Year</div></div>
        <div class="ret-box"><div class="ret-val">${f.ret_3y}%</div><div class="ret-lbl">3-Year</div></div>
        <div class="ret-box best"><div class="ret-val">${f.ret_5y}%</div><div class="ret-lbl">5-Year</div></div>
      </div>
      <div style="font-size:.78rem;color:var(--muted)">Min: PKR ${formatPKR(f.min_pkr)}</div>
      <div class="fund-verdict">Reported as a ${f.return_type || "historical"} return; compare only with the same period and category.</div>
      ${full ? `<div class="fund-earn">A ${f.ret_1y}% historical return on PKR ${formatPKR(AMOUNT)} equals PKR ${formatPKR(full)} <span style="color:var(--muted);font-weight:400">for comparison only; it is not a forecast</span></div>` : ""}
    `;
    grid.appendChild(card);
  });
  grid.insertAdjacentHTML("beforeend", '<p style="grid-column:1/-1;font-size:.74rem;color:var(--muted);margin:6px 0 0">Return periods are not directly comparable across every fund category. Confirm the latest NAV, calculation basis, risk profile and fees on the <a href="https://www.mufap.com.pk/Industry/IndustryStatDaily?tab=1" target="_blank" rel="noopener">MUFAP daily performance table</a> before making a decision.</p>');
}

function riskBadge(risk) {
  if (risk === "Low") return "green";
  if (risk === "Medium") return "blue";
  return "red";
}

// ── PAGE 3 - Stocks ───────────────────────────────────────────────
function renderStocks() {
  if (!DATA) return;
  const tbody = document.getElementById("stocks-tbody");
  tbody.innerHTML = "";

  const stockHealth = DATA.data_health && DATA.data_health.stocks;
  const dividendHealth = DATA.data_health && DATA.data_health.dividends;
  const staleParts = [stockHealth && stockHealth.stale ? "prices" : "", dividendHealth && dividendHealth.stale ? "dividends" : ""].filter(Boolean);
  if (staleParts.length) {
    const sourceDates = [stockHealth, dividendHealth]
      .filter(health => health && health.as_of)
      .map(health => health.as_of)
      .join(" / ");
    tbody.insertAdjacentHTML("beforeend", `<tr><td colspan="8" style="background:#FFF8E6;color:#614A14;font-size:.8rem"><strong>Stale ${staleParts.join(" and ")} data.</strong>${sourceDates ? ` Last successful source date: ${sourceDates}.` : ""} Verify company payouts and prices on the PSX Data Portal.</td></tr>`);
  }

  // Universe is comprehensive (~100+ names); show only priced stocks and cap
  // the homepage table to the top 15 by dividend yield to keep it readable.
  const sorted = [...DATA.stocks]
    .filter(s => s.price > 0)
    .sort((a, b) => b.yield - a.yield)
    .slice(0, 15);
  sorted.forEach(s => {
    const up = s.chg1y >= 0;
    tbody.innerHTML += `
      <tr>
        <td><strong>${s.ticker}</strong></td>
        <td>${s.name}</td>
        <td><span class="badge badge-grey">${s.sector}</span></td>
        <td class="num">${formatPKR(s.price)}</td>
        <td class="num ${up ? "chg-up" : "chg-dn"}">${up ? "▲" : "▼"} ${Math.abs(s.chg1y)}%</td>
        <td class="num yield-hi">${s.yield}%</td>
        <td class="num">${s.div}</td>
        <td class="num">${s.pe || "-"}</td>
      </tr>
    `;
  });

  renderStocksChart(sorted.slice(0, 8));
}

// ── PAGE 4 - Portfolio ────────────────────────────────────────────
function renderPortfolio() {
  if (!DATA) {
    document.getElementById("alloc-grid").innerHTML =
      '<div style="text-align:center;padding:32px;color:#888">Loading investment data...</div>';
    document.getElementById("action-steps").innerHTML = "";
    return;
  }
  applyProfileAllocation();

  document.getElementById("port-subtitle").textContent =
    `${PROFILE_LABELS[selectedProfile]} educational scenario for PKR ${formatPKR(AMOUNT)}. Percentages are examples, not advice.`;

  const grid = document.getElementById("alloc-grid");
  grid.innerHTML = "";
  PORTFOLIO_ALLOC.forEach(a => {
    const amt = Math.round(AMOUNT * a.pct / 100);
    grid.innerHTML += `
      <div class="alloc-item">
        <div class="alloc-dot" style="background:${a.color}"></div>
        <div>
          <div class="alloc-label">${a.label}</div>
          <div class="alloc-sub">${a.type}</div>
          <div style="font-size:.75rem;color:var(--muted);margin-top:2px">${a.where}</div>
        </div>
        <div class="alloc-amount">
          <div>PKR ${formatPKR(amt)}</div>
          <div class="alloc-pct">${a.pct}% of this scenario</div>
        </div>
      </div>
    `;
  });

  const steps = [
    { n: 1, title: "Define the job of each bucket", body: "Separate money needed soon from long-term capital. A category can be unsuitable even when its recent return looks attractive.", color: "#0E3B2E" },
    { n: 2, title: "Verify current primary-source data", body: "Check National Savings rates, MUFAP fund performance and PSX disclosures on their official websites. Do not treat the figures on this page as a quote or offer.", color: "#23415E" },
    { n: 3, title: "Compare costs and access", body: "Record management fees, taxes, lock-ins, withdrawal time, account requirements and the possibility of loss before choosing an instrument.", color: "#A4452F" },
    { n: 4, title: "Use regulated providers", body: "Confirm a fund manager or broker in the relevant SECP or PSX directory, and seek regulated advice where a decision depends on your personal circumstances.", color: "#5E5C52" },
  ];
  const stepsEl = document.getElementById("action-steps");
  stepsEl.innerHTML = steps.map(s => `
    <div style="display:flex;gap:14px;margin-bottom:16px">
      <div style="width:32px;height:32px;border-radius:50%;background:${s.color};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.9rem;flex-shrink:0">${s.n}</div>
      <div>
        <div style="font-weight:700;margin-bottom:4px">${s.title}</div>
        <div style="font-size:.84rem;color:#444">${s.body}</div>
      </div>
    </div>
  `).join("") + '<p style="font-size:.78rem;color:var(--muted);margin:4px 0 0"><strong>This is an illustration, not a recommendation or suitability assessment.</strong> It does not account for your income, debts, time horizon, tax status, risk capacity or goals.</p>';

  setTimeout(renderDonutChart, 50);
}

// ── Charts ────────────────────────────────────────────────────────
let chartInstances = {};

function destroyChart(id) {
  if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; }
}

function renderKSEChart() {
  if (!DATA) return;
  const ctx = document.getElementById("chart-kse").getContext("2d");
  destroyChart("kse");
  chartInstances["kse"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: DATA.kse100_history.labels,
      datasets: [{
        label: "KSE-100",
        data: DATA.kse100_history.values,
        borderColor: "#12A87D",
        backgroundColor: "rgba(18,168,125,.12)",
        borderWidth: 3,
        pointRadius: 3,
        fill: true,
        tension: .35,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => (v/1000).toFixed(0) + "K" }, grid: { color: "#E6EBF1" } },
        x: { ticks: { maxRotation: 0 }, grid: { display: false } }
      }
    }
  });
}

function renderSBPChart() {
  if (!DATA) return;
  const ctx = document.getElementById("chart-sbp").getContext("2d");
  destroyChart("sbp");
  chartInstances["sbp"] = new Chart(ctx, {
    type: "line",
    data: {
      labels: DATA.sbp_history.labels,
      datasets: [{
        label: "SBP Rate %",
        data: DATA.sbp_history.values,
        borderColor: "#2854C5",
        backgroundColor: "rgba(40,84,197,.1)",
        borderWidth: 3,
        fill: true,
        tension: .35,
        pointRadius: 3,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => v + "%" }, min: 0, grid: { color: "#E6EBF1" } },
        x: { ticks: { maxRotation: 0 }, grid: { display: false } }
      }
    }
  });
}

function renderStocksChart(stocks) {
  const ctx = document.getElementById("chart-stocks").getContext("2d");
  destroyChart("stocks");
  chartInstances["stocks"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: stocks.map(s => s.ticker),
      datasets: [{
        label: "Dividend Yield %",
        data: stocks.map(s => s.yield),
        backgroundColor: stocks.map(s => s.yield >= 6 ? "#075E4B" : s.yield >= 4 ? "#12A87D" : "#F2B94B"),
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => v + "%" }, beginAtZero: true, grid: { color: "#E6EBF1" } },
        x: { grid: { display: false } }
      }
    }
  });
}

function renderDonutChart() {
  const ctx = document.getElementById("chart-donut").getContext("2d");
  destroyChart("donut");
  chartInstances["donut"] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: PORTFOLIO_ALLOC.map(a => a.label),
      datasets: [{
        data: PORTFOLIO_ALLOC.map(a => a.pct),
        backgroundColor: PORTFOLIO_ALLOC.map(a => a.color),
        borderWidth: 2,
        borderColor: "#FFFFFF",
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: "58%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { font: { size: 11 }, boxWidth: 12, padding: 12, usePointStyle: true }
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.label}: ${ctx.parsed}%  (PKR ${formatPKR(Math.round(AMOUNT * ctx.parsed / 100))})`
          }
        }
      }
    }
  });
}

function renderProjectionChart(projVals) {
  const ctx = document.getElementById("chart-proj").getContext("2d");
  destroyChart("proj");
  chartInstances["proj"] = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
      datasets: [
        {
          label: "Portfolio Value",
          data: projVals,
          backgroundColor: ["#F8D98A","#F2B94B","#12A87D","#2854C5","#075E4B"],
          borderRadius: 8,
        },
        {
          label: "Starting Amount",
          data: Array(5).fill(AMOUNT),
          type: "line",
          borderColor: "#C24132",
          borderDash: [5, 4],
          borderWidth: 1.5,
          pointRadius: 0,
          fill: false,
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { font: { size: 11 } } },
        tooltip: {
          callbacks: { label: ctx => ` PKR ${formatPKR(ctx.parsed.y)}` }
        }
      },
      scales: {
        y: { ticks: { callback: v => "₨" + (v/1000).toFixed(0) + "K" }, grid: { color: "#E6EBF1" } },
        x: { grid: { display: false } }
      }
    }
  });
}

function renderRiskChart() {
  const ctx = document.getElementById("chart-risk");
  if (!ctx || typeof Chart === "undefined") return;
  destroyChart("risk");
  const profiles = {
    balanced: [78, 70, 70, 72, 55],
    income: [90, 76, 44, 88, 48],
    growth: [54, 64, 92, 58, 62],
  };
  chartInstances["risk"] = new Chart(ctx, {
    type: "radar",
    data: {
      labels: ["Stability", "Liquidity", "Growth", "Income", "Shariah sleeve"],
      datasets: [{
        label: PROFILE_LABELS[selectedProfile],
        data: profiles[selectedProfile] || profiles.balanced,
        borderColor: "#075E4B",
        backgroundColor: "rgba(18,168,125,.16)",
        pointBackgroundColor: "#F2B94B",
        pointBorderColor: "#075E4B",
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: { display: false, stepSize: 20 },
          grid: { color: "#DDE3EA" },
          angleLines: { color: "#DDE3EA" },
          pointLabels: { font: { size: 11 }, color: "#374151" },
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => `${ctx.label}: ${ctx.raw}/100` } }
      }
    }
  });
}

// ── Homepage dashboard (static section) ──────────────────────────
const LEDGER = { green:"#075E4B", green3:"#12A87D", gold:"#F2B94B", goldPale:"#F8D98A",
                 navy:"#2854C5", red:"#C24132", ink:"#111827", muted:"#667085", paper:"#FFFFFF" };
const MONO_FONT = { family:"'IBM Plex Mono', monospace", size: 11 };

// Dated ticker tape
function renderTicker() {
  if (!DATA) return;
  const m = DATA.macro, g = DATA.gold;
  setText("tk-kse", m.kse100_level ? formatPKR(m.kse100_level) : "-");
  setText("tk-sbp", m.sbp_rate + "%");
  setText("tk-pkr", "₨" + m.pkr_usd);
  setText("tk-inf", m.inflation_cpi + "%");
  if (g) {
    setText("tk-gold", "₨" + formatPKR(g.tola_24k));
    const chg = document.getElementById("tkc-gold");
    if (chg && g.chg1y_pct != null) {
      const up = g.chg1y_pct >= 0;
      chg.textContent = (up ? "▲" : "▼") + Math.abs(g.chg1y_pct) + "%";
      chg.className = up ? "up" : "dn";
    }
  }
  // duplicate the feed once so the marquee (-50%) loops seamlessly
  const feed = document.querySelector(".ticker-feed");
  if (feed && !feed.dataset.looped) {
    feed.dataset.looped = "1";
    feed.insertAdjacentHTML("beforeend", feed.innerHTML.replace(/\sid="[^"]*"/g, ""));
  }
}

// Dated gold rates (homepage card)
function renderGold() {
  const g = DATA && DATA.gold;
  if (!g) return;
  setText("g-tola24", "₨" + formatPKR(g.tola_24k));
  setText("g-tola22", "₨" + formatPKR(g.tola_22k));
  setText("g-10g24",  "₨" + formatPKR(g.g10_24k));
  setText("g-gram24", "₨" + formatPKR(g.gram_24k));

  const chgEl = document.getElementById("gold-chg");
  if (chgEl && g.chg1y_pct != null) {
    const up = g.chg1y_pct >= 0;
    chgEl.textContent = (up ? "▲ " : "▼ ") + Math.abs(g.chg1y_pct) + "% / 1yr";
    chgEl.style.background = up ? "var(--green-light)" : "var(--red-light)";
    chgEl.style.color = up ? "var(--green)" : "var(--red)";
    chgEl.style.borderColor = "transparent";
  }

  const srcEl = document.getElementById("gold-src");
  if (srcEl) {
    const d = new Date(DATA.updated);
    const when = d.toLocaleDateString("en-PK", { day: "numeric", month: "long", year: "numeric" });
    const note = g.source_type === "local"
      ? "third-party local-rate reference via gold.pk"
      : "derived international futures and PKR/USD fallback";
    srcEl.textContent = `Collected ${when} · ${note}`;
  }

  renderGoldChart();
}

// Dated fuel prices (homepage card)
function renderFuel() {
  const f = DATA && DATA.fuel;
  if (!f) return;
  const px = v => (v == null ? "-" : "₨" + Number(v).toFixed(2));
  setText("f-petrol", px(f.petrol));
  setText("f-hsd",    px(f.hsd));
  setText("f-kero",   px(f.kerosene));
  setText("f-ldo",    px(f.ldo));
  const badge = document.getElementById("fuel-asof");
  if (badge && f.asof) badge.textContent = "w.e.f " + f.asof;
  const srcEl = document.getElementById("fuel-src");
  if (srcEl) {
    srcEl.textContent = (f.source || "Public source reporting notified retail rates") +
      (f.asof ? " · effective " + f.asof : "");
  }
}

function renderGoldChart() {
  const ctx = document.getElementById("chart-gold");
  if (!ctx || typeof Chart === "undefined" || !DATA.gold || !DATA.gold.history) return;
  destroyChart("gold");
  chartInstances["gold"] = new Chart(ctx.getContext("2d"), {
    type: "line",
    data: {
      labels: DATA.gold.history.labels,
      datasets: [{
        label: "24K gold (PKR/tola)",
        data: DATA.gold.history.values,
        borderColor: "#B7791F",
        backgroundColor: "rgba(242,185,75,.16)",
        borderWidth: 3,
        pointRadius: 0,
        fill: true,
        tension: .35,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: c => " ₨" + formatPKR(c.parsed.y) + " / tola" } }
      },
      scales: {
        y: { ticks: { callback: v => (v / 1000).toFixed(0) + "K" }, grid: { color: "#E6EBF1" } },
        x: { ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }, grid: { display: false } }
      }
    }
  });
}

function renderMixChart() {
  const ctx = document.getElementById("chart-mix");
  if (!ctx || typeof Chart === "undefined") return;
  destroyChart("chart-mix");
  chartInstances["chart-mix"] = new Chart(ctx, {
    type: "doughnut",
    data: { labels: ["National Savings 30%", "Islamic income fund 25%", "Equity fund 20%", "PSX dividend stocks 20%", "Emergency buffer 5%"],
      datasets: [{ data: [30, 25, 20, 20, 5],
        backgroundColor: [LEDGER.green, LEDGER.navy, LEDGER.gold, LEDGER.red, LEDGER.muted],
        borderColor: LEDGER.paper, borderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: "62%",
      plugins: { legend: { position: "right", labels: { font: { ...MONO_FONT, size: 10 }, boxWidth: 12, color: LEDGER.ink } } } }
  });
}

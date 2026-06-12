// ── Pakistan Investment Advisor — app.js ──────────────────────────

let DATA = null;
let AMOUNT = 0;
let currentPage = 0;

const PORTFOLIO_ALLOC = [
  { label: "National Savings Certificate", pct: 30, ret: null, color: "#0E3B2E", shariah: false,
    type: "Government-backed Fixed Income", where: "Pakistan Post Office / CDNS branch" },
  { label: "Meezan Islamic Income Fund",   pct: 25, ret: null, color: "#23415E", shariah: true,
    type: "Islamic Money Market Fund",     where: "almeezangroup.com" },
  { label: "Al Meezan Mutual Fund",        pct: 20, ret: null, color: "#7A5A1F", shariah: true,
    type: "Islamic Equity Fund",           where: "almeezangroup.com" },
  { label: "PSX Blue Chips (FFC + MCB)",   pct: 20, ret: 6.5,  color: "#A4452F", shariah: false,
    type: "Dividend Stocks",               where: "CDC account via PSX broker" },
  { label: "Emergency Buffer (CDNS)",      pct: 5,  ret: null, color: "#5E5C52", shariah: false,
    type: "CDNS Savings Account",          where: "Pakistan Post Office / CDNS branch" },
];

// ── Load data.json on startup ─────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  formatAmountInput();
  fetch("data.json?v=" + Date.now())
    .then(r => r.json())
    .then(d => {
      DATA = d;
      applyData();
    })
    .catch(() => {
      document.getElementById("data-age").textContent = "Data unavailable — retrying…";
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
  const age = Math.round((Date.now() - updated) / 3600000);
  document.getElementById("data-age").textContent =
    age < 2 ? "Data: fresh today" : `Data: updated ${age}h ago`;

  // Macro pills
  const m = DATA.macro;
  document.getElementById("m-kse").textContent = (m.kse100_level / 1000).toFixed(0) + "K";
  document.getElementById("m-sbp").textContent = m.sbp_rate + "%";
  document.getElementById("m-pkr").textContent = "₨" + m.pkr_usd;
  document.getElementById("m-inf").textContent = m.inflation_cpi + "%";

  const d = new Date(DATA.updated);
  document.getElementById("snapshot-date").textContent =
    "As of " + d.toLocaleDateString("en-PK", { day: "numeric", month: "long", year: "numeric" });

  // Charts (page 0)
  renderKSEChart();
  renderSBPChart();

  // Re-render whichever page is already visible so data arrives even if
  // the user navigated before the fetch completed.
  if (currentPage === 1) renderNationalSavings();
  else if (currentPage === 2) renderMutualFunds();
  else if (currentPage === 3) renderStocks();
  else if (currentPage === 4) renderPortfolio();
}

// ── Amount input — Pakistani comma formatting ─────────────────────
function formatAmountInput() {
  const inp = document.getElementById("amount-input");
  inp.addEventListener("input", () => {
    let raw = inp.value.replace(/[^0-9]/g, "");
    if (raw) inp.value = formatPKR(parseInt(raw, 10));
    else inp.value = "";
  });
  inp.addEventListener("keydown", e => {
    if (e.key === "Enter") startAnalysis();
  });
}

function formatPKR(n) {
  // Pakistani numbering: X,XX,XXX
  if (isNaN(n)) return "0";
  const s = String(n);
  if (s.length <= 3) return s;
  let result = s.slice(-3);
  let rest = s.slice(0, -3);
  while (rest.length > 2) {
    result = rest.slice(-2) + "," + result;
    rest = rest.slice(0, -2);
  }
  return rest + "," + result;
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

  // Progress bar
  document.getElementById("progress-bar").style.width = ((n + 1) / 5 * 100) + "%";

  currentPage = n;
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Lazy-init AdSense for the newly visible page (pages 1–4 only)
  if (n > 0) initPageAd(n);

  // Lazy-render page content
  if (n === 1) renderNationalSavings();
  if (n === 2) renderMutualFunds();
  if (n === 3) renderStocks();
  if (n === 4) renderPortfolio();
}

function startAnalysis() {
  AMOUNT = parseAmount();
  if (AMOUNT < 1000) {
    alert("Please enter at least PKR 1,000 to analyze.");
    return;
  }
  goPage(1);
}

// Step pill click
document.getElementById("step-nav").addEventListener("click", e => {
  const pill = e.target.closest(".step-pill");
  if (!pill) return;
  const step = parseInt(pill.dataset.step, 10);
  if (step === 0) { goPage(0); return; }
  if (!AMOUNT) { startAnalysis(); return; }
  goPage(step);
});

// ── PAGE 1 — National Savings ─────────────────────────────────────
function renderNationalSavings() {
  if (!DATA) return;
  const tbody = document.getElementById("ns-tbody");
  tbody.innerHTML = "";

  DATA.national_savings.forEach(s => {
    const earn = AMOUNT > 0 ? Math.round(AMOUNT * s.rate / 100) : null;
    const rec = s.recommended;
    const minOk = AMOUNT === 0 || AMOUNT >= s.min_pkr;
    const tr = document.createElement("tr");
    if (rec) tr.className = "rec-row";
    tr.innerHTML = `
      <td>
        <strong>${s.name}</strong>
        ${rec ? '<span class="badge badge-gold" style="margin-left:6px">⭐ Rec</span>' : ""}
        ${s.shariah ? '<span class="badge badge-green" style="margin-left:4px">☪ Islamic</span>' : ""}
      </td>
      <td class="num yield-hi">${s.rate}%</td>
      <td>${s.tenure}</td>
      <td>${s.payout}</td>
      <td class="num" style="color:#23415E;font-weight:700">
        ${earn ? "PKR " + formatPKR(earn) + "/yr" : "—"}
      </td>
      <td>${s.eligible}</td>
      <td style="font-size:.8rem;color:#555">${s.verdict}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── PAGE 2 — Mutual Funds ─────────────────────────────────────────
function renderMutualFunds() {
  if (!DATA) return;
  const grid = document.getElementById("funds-grid");
  grid.innerHTML = "";

  // Resolve portfolio returns from data
  wirePortfolioReturns();

  DATA.mutual_funds.forEach(f => {
    const alloc = AMOUNT > 0 ? getPortfolioAlloc(f.name) : null;
    const earn = alloc ? Math.round(alloc * f.ret_1y / 100) : null;

    const card = document.createElement("div");
    card.className = "fund-card" + (f.recommended ? " rec" : "");
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">
        <div class="fund-name">${f.name}</div>
        ${f.recommended ? '<span class="badge badge-gold">⭐ Rec</span>' : ""}
      </div>
      <div class="fund-mgr">📁 ${f.manager} &nbsp;·&nbsp; ${f.type}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px">
        ${f.shariah ? '<span class="badge badge-green">☪ Shariah</span>' : '<span class="badge badge-grey">Conventional</span>'}
        <span class="badge badge-${riskBadge(f.risk)}">${f.risk} Risk</span>
      </div>
      <div class="fund-returns">
        <div class="ret-box"><div class="ret-val">${f.ret_1y}%</div><div class="ret-lbl">1-Year</div></div>
        <div class="ret-box"><div class="ret-val">${f.ret_3y}%</div><div class="ret-lbl">3-Year</div></div>
        <div class="ret-box best"><div class="ret-val">${f.ret_5y}%</div><div class="ret-lbl">5-Year</div></div>
      </div>
      <div style="font-size:.78rem;color:var(--muted)">Min: PKR ${formatPKR(f.min_pkr)}</div>
      <div class="fund-verdict">${f.verdict}</div>
      ${earn ? `<div class="fund-earn">Your ${alloc ? "PKR " + formatPKR(alloc) : ""} could earn ~PKR ${formatPKR(earn)}/yr</div>` : ""}
      <a href="${f.url}" target="_blank" rel="noopener" class="btn-cta btn-primary" style="margin-top:12px;font-size:.78rem;display:inline-flex">Invest Now →</a>
    `;
    grid.appendChild(card);
  });
}

function riskBadge(risk) {
  if (risk === "Low") return "green";
  if (risk === "Medium") return "blue";
  return "red";
}

function getPortfolioAlloc(fundName) {
  const name = fundName.toLowerCase();
  if (name.includes("meezan islamic income")) return Math.round(AMOUNT * 0.25);
  if (name.includes("al meezan mutual"))      return Math.round(AMOUNT * 0.20);
  return null;
}

// ── PAGE 3 — Stocks ───────────────────────────────────────────────
function renderStocks() {
  if (!DATA) return;
  const tbody = document.getElementById("stocks-tbody");
  tbody.innerHTML = "";

  const sorted = [...DATA.stocks].sort((a, b) => b.yield - a.yield);
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
        <td class="num">${s.pe || "—"}</td>
      </tr>
    `;
  });

  renderStocksChart(sorted.slice(0, 8));
}

// ── PAGE 4 — Portfolio ────────────────────────────────────────────
function renderPortfolio() {
  if (!DATA) {
    document.getElementById("alloc-grid").innerHTML =
      '<div style="text-align:center;padding:32px;color:#888">⏳ Loading investment data…</div>';
    document.getElementById("action-steps").innerHTML = "";
    return;
  }
  document.getElementById("alloc-grid").innerHTML = "";
  wirePortfolioReturns();

  document.getElementById("port-subtitle").textContent =
    `Conservative, dividend-focused allocation for PKR ${formatPKR(AMOUNT)}`;

  let totalIncome = 0;
  PORTFOLIO_ALLOC.forEach(a => {
    const amt = Math.round(AMOUNT * a.pct / 100);
    const income = Math.round(amt * (a.ret || 0) / 100);
    totalIncome += income;
  });

  const blended = AMOUNT > 0 ? ((totalIncome / AMOUNT) * 100).toFixed(1) : 0;
  const monthly = Math.round(totalIncome / 12);

  // 5-year projection
  let bal = AMOUNT;
  const projVals = [];
  for (let i = 0; i < 5; i++) {
    bal *= (1 + parseFloat(blended) / 100);
    projVals.push(Math.round(bal));
  }

  document.getElementById("s-annual").textContent  = "PKR " + formatPKR(totalIncome);
  document.getElementById("s-monthly").textContent = "PKR " + formatPKR(monthly);
  document.getElementById("s-yield").textContent   = blended + "%";
  document.getElementById("s-5y").textContent      = "PKR " + formatPKR(projVals[4]);

  // Allocation grid
  const grid = document.getElementById("alloc-grid");
  grid.innerHTML = "";
  PORTFOLIO_ALLOC.forEach(a => {
    const amt = Math.round(AMOUNT * a.pct / 100);
    const income = Math.round(amt * (a.ret || 0) / 100);
    grid.innerHTML += `
      <div class="alloc-item">
        <div class="alloc-dot" style="background:${a.color}"></div>
        <div>
          <div class="alloc-label">${a.label}</div>
          <div class="alloc-sub">${a.type} &nbsp;·&nbsp; ${a.shariah ? "☪ Shariah" : "🏦 Conv."}</div>
          <div style="font-size:.75rem;color:var(--muted);margin-top:2px">${a.where}</div>
        </div>
        <div class="alloc-amount">
          <div>PKR ${formatPKR(amt)}</div>
          <div class="alloc-pct">${a.pct}% &nbsp;·&nbsp; ${a.ret ? a.ret + "% ret" : "—"}</div>
          ${income ? `<div style="font-size:.75rem;color:var(--navy)">~PKR ${formatPKR(income)}/yr</div>` : ""}
        </div>
      </div>
    `;
  });

  // Action steps
  const steps = [
    { n: 1, title: "Open CDNS / National Savings Account", body: `Visit any Pakistan Post Office with your CNIC. Deposit PKR ${formatPKR(Math.round(AMOUNT * 0.30))} into a Special Savings Certificate.`, color: "#0E3B2E" },
    { n: 2, title: "Register on Al Meezan Online Portal",  body: `Go to almeezangroup.com → Register → upload CNIC → KYC online (~15 mins). Invest PKR ${formatPKR(Math.round(AMOUNT * 0.25))} in Meezan Islamic Income Fund and PKR ${formatPKR(Math.round(AMOUNT * 0.20))} in Al Meezan Mutual Fund.`, color: "#23415E" },
    { n: 3, title: "Open a PSX Brokerage + CDC Account",   body: `Choose a broker (Arif Habib, MCB FSL, or Akseer). Register online. Transfer PKR ${formatPKR(Math.round(AMOUNT * 0.20))} and split: 60% into FFC, 40% into MCB Bank shares.`, color: "#A4452F" },
    { n: 4, title: "Keep Emergency Buffer Liquid",          body: `At the same CDNS visit, open a Savings Account with PKR ${formatPKR(Math.round(AMOUNT * 0.05))}. No lock-in — withdraw anytime.`, color: "#5E5C52" },
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
  `).join("");

  // Render charts after a tick so canvas is visible
  setTimeout(() => {
    renderDonutChart();
    renderProjectionChart(projVals);
  }, 50);
}

function wirePortfolioReturns() {
  if (!DATA) return;
  // Pull live rates from data.json into PORTFOLIO_ALLOC
  const nsSSC = DATA.national_savings.find(n => n.name.includes("Special Savings"));
  const nsCDNS = DATA.national_savings.find(n => n.name.includes("CDNS Savings"));
  const fMIIF = DATA.mutual_funds.find(f => f.name.includes("Meezan Islamic Income"));
  const fAMMF = DATA.mutual_funds.find(f => f.name.includes("Al Meezan Mutual"));

  if (nsSSC)  PORTFOLIO_ALLOC[0].ret = nsSSC.rate;
  if (fMIIF)  PORTFOLIO_ALLOC[1].ret = fMIIF.ret_1y;
  if (fAMMF)  PORTFOLIO_ALLOC[2].ret = fAMMF.ret_1y;
  // Stocks: fixed 6.5% dividend yield estimate
  PORTFOLIO_ALLOC[3].ret = 6.5;
  if (nsCDNS) PORTFOLIO_ALLOC[4].ret = nsCDNS.rate;
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
        borderColor: "#0E3B2E",
        backgroundColor: "rgba(14,59,46,.08)",
        borderWidth: 2.5,
        pointRadius: 3,
        fill: true,
        tension: .35,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => (v/1000).toFixed(0) + "K" } },
        x: { ticks: { maxRotation: 45 } }
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
        borderColor: "#A4452F",
        backgroundColor: "rgba(164,69,47,.07)",
        borderWidth: 2.5,
        fill: true,
        tension: .35,
        pointRadius: 3,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => v + "%" }, min: 0 },
        x: { ticks: { maxRotation: 45 } }
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
        backgroundColor: stocks.map(s => s.yield >= 6 ? "#0E3B2E" : s.yield >= 4 ? "#1F7A53" : "#C9B27B"),
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => v + "%" }, beginAtZero: true }
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
        borderColor: "#F6F1E6",
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: "58%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { font: { size: 11 }, boxWidth: 12, padding: 12 }
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
          backgroundColor: ["#D9B86A","#B98A2F","#1F7A53","#23415E","#0E3B2E"],
          borderRadius: 8,
        },
        {
          label: "Starting Amount",
          data: Array(5).fill(AMOUNT),
          type: "line",
          borderColor: "#A4452F",
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
        y: { ticks: { callback: v => "₨" + (v/1000).toFixed(0) + "K" } }
      }
    }
  });
}

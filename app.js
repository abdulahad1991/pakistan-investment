// ── Pakistan Investment Advisor - app.js ──────────────────────────

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
  balanced: "Balanced",
  income: "Income",
  growth: "Growth",
};

const PORTFOLIO_ALLOC = [
  { label: "National Savings Certificate", pct: 30, ret: null, color: "#075E4B", shariah: false,
    type: "Government-backed Fixed Income", where: "Pakistan Post Office / CDNS branch" },
  { label: "Meezan Islamic Income Fund",   pct: 25, ret: null, color: "#2854C5", shariah: true,
    type: "Islamic Money Market Fund",     where: "almeezangroup.com" },
  { label: "Al Meezan Mutual Fund",        pct: 20, ret: null, color: "#F2B94B", shariah: true,
    type: "Islamic Equity Fund",           where: "almeezangroup.com" },
  { label: "PSX Blue Chips (FFC + MCB)",   pct: 20, ret: 6.5,  color: "#C24132", shariah: false,
    type: "Dividend Stocks",               where: "CDC account via PSX broker" },
  { label: "Emergency Buffer (CDNS)",      pct: 5,  ret: null, color: "#667085", shariah: false,
    type: "CDNS Savings Account",          where: "Pakistan Post Office / CDNS branch" },
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
  const age = Math.round((Date.now() - updated) / 3600000);
  document.getElementById("data-age").textContent =
    age < 2 ? "Data: fresh today" : `Data: updated ${age}h ago`;

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

  const snap = document.getElementById("snapshot-date");
  if (snap) {
    const d = new Date(DATA.updated);
    snap.textContent =
      "As of " + d.toLocaleDateString("en-PK", { day: "numeric", month: "long", year: "numeric" });
  }

  // Live ticker tape (v2 masthead) - best-effort, only if present
  renderTicker();

  // Charts (page 0)
  renderKSEChart();
  renderSBPChart();

  // Live gold rates card
  renderGold();

  // Dashboard section (below the tool)
  renderInsightStrip();
  renderGrowChart();
  renderRealChart();
  renderMixChart();

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
    updateHeroScore();
  });
  inp.addEventListener("keydown", e => {
    if (e.key === "Enter") startAnalysis();
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
      updateHeroScore();
      if (currentPage === 2) renderMutualFunds();
      if (currentPage === 4) renderPortfolio();
    });
  });
  updateHeroScore();
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function applyProfileAllocation() {
  const mix = PROFILE_MIXES[selectedProfile] || PROFILE_MIXES.balanced;
  PORTFOLIO_ALLOC.forEach((a, i) => { a.pct = mix[i]; });
}

function calculateReadinessScore(amount) {
  if (!amount) return null;
  const amountScore = amount >= 1000000 ? 30 : amount >= 500000 ? 24 : amount >= 100000 ? 18 : amount >= 25000 ? 12 : 7;
  const diversificationScore = 36;
  const emergencyScore = 14;
  const dataScore = DATA ? 12 : 6;
  const profileBonus = selectedProfile === "balanced" ? 8 : 6;
  return Math.min(100, amountScore + diversificationScore + emergencyScore + dataScore + profileBonus);
}

function updateHeroScore() {
  const el = document.getElementById("hero-score");
  if (!el) return;
  const amount = parseAmount();
  const score = calculateReadinessScore(amount);
  el.innerHTML = score
    ? `<span>${PROFILE_LABELS[selectedProfile]} readiness</span><strong>${score}/100</strong>`
    : "<span>Readiness score</span><strong>Enter amount</strong>";
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

  // Progress bar
  document.getElementById("progress-bar").style.width = ((n + 1) / 5 * 100) + "%";

  currentPage = n;
  window.scrollTo({ top: 0, behavior: "smooth" });

  // Lazy-init AdSense for the newly visible page (pages 1-4 only)
  if (n > 0) initPageAd(n);

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

function startAnalysis() {
  AMOUNT = parseAmount();
  if (AMOUNT < 1000) {
    showAmountError("Enter at least PKR 1,000 to analyze.");
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

// Step pill click
document.getElementById("step-nav").addEventListener("click", e => {
  const pill = e.target.closest(".step-pill");
  if (!pill) return;
  const step = parseInt(pill.dataset.step, 10);
  if (step === 0) { goPage(0); return; }
  if (!AMOUNT) { startAnalysis(); return; }
  goPage(step);
});

// ── PAGE 1 - National Savings ─────────────────────────────────────
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
        ${rec ? '<span class="badge badge-gold" style="margin-left:6px">Recommended</span>' : ""}
        ${s.shariah ? '<span class="badge badge-green" style="margin-left:4px">Shariah</span>' : ""}
      </td>
      <td class="num yield-hi">${s.rate}%</td>
      <td>${s.tenure}</td>
      <td>${s.payout}</td>
      <td class="num" style="color:#23415E;font-weight:700">
        ${earn ? "PKR " + formatPKR(earn) + "/yr" : "-"}
      </td>
      <td>${s.eligible}</td>
      <td style="font-size:.8rem;color:#555">${s.verdict}</td>
    `;
    tbody.appendChild(tr);
  });
}

// ── PAGE 2 - Mutual Funds ─────────────────────────────────────────
function renderMutualFunds() {
  if (!DATA) return;
  const grid = document.getElementById("funds-grid");
  grid.innerHTML = "";

  // Resolve portfolio returns from data
  wirePortfolioReturns();
  applyProfileAllocation();

  DATA.mutual_funds.forEach(f => {
    const full = AMOUNT > 0 ? Math.round(AMOUNT * f.ret_1y / 100) : null;
    const alloc = AMOUNT > 0 ? getPortfolioAlloc(f.name) : null;
    const allocPct = alloc ? Math.round(alloc / AMOUNT * 100) : null;
    const allocEarn = alloc ? Math.round(alloc * f.ret_1y / 100) : null;

    const card = document.createElement("div");
    card.className = "fund-card" + (f.recommended ? " rec" : "");
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px">
        <div class="fund-name">${f.name}</div>
        ${f.recommended ? '<span class="badge badge-gold">Recommended</span>' : ""}
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
      <div class="fund-verdict">${f.verdict}</div>
      ${full ? `<div class="fund-earn">Your PKR ${formatPKR(AMOUNT)} in this fund ≈ ~PKR ${formatPKR(full)}/yr <span style="color:var(--muted);font-weight:400">based on its ${f.ret_1y}% 1-year return</span></div>` : ""}
      ${alloc ? `<div style="font-size:.75rem;color:var(--muted);margin-top:2px">Suggested portfolio slice: PKR ${formatPKR(alloc)} (${allocPct}%) &rarr; ~PKR ${formatPKR(allocEarn)}/yr</div>` : ""}
      <a href="${f.url}" target="_blank" rel="noopener" class="btn-cta btn-primary" style="margin-top:12px;font-size:.78rem;display:inline-flex">Invest Now →</a>
    `;
    grid.appendChild(card);
  });
  grid.insertAdjacentHTML("beforeend", '<p style="grid-column:1/-1;font-size:.74rem;color:var(--muted);margin:6px 0 0">Fund returns are annualized and refreshed with the daily data update. Confirm the latest NAV and returns with the AMC or MUFAP before investing.</p>');
}

function riskBadge(risk) {
  if (risk === "Low") return "green";
  if (risk === "Medium") return "blue";
  return "red";
}

function getPortfolioAlloc(fundName) {
  const name = fundName.toLowerCase();
  if (name.includes("meezan islamic income")) return Math.round(AMOUNT * PORTFOLIO_ALLOC[1].pct / 100);
  if (name.includes("al meezan mutual"))      return Math.round(AMOUNT * PORTFOLIO_ALLOC[2].pct / 100);
  return null;
}

// ── PAGE 3 - Stocks ───────────────────────────────────────────────
function renderStocks() {
  if (!DATA) return;
  const tbody = document.getElementById("stocks-tbody");
  tbody.innerHTML = "";

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
      '<div style="text-align:center;padding:32px;color:#888">⏳ Loading investment data…</div>';
    document.getElementById("action-steps").innerHTML = "";
    return;
  }
  document.getElementById("alloc-grid").innerHTML = "";
  wirePortfolioReturns();
  applyProfileAllocation();

  document.getElementById("port-subtitle").textContent =
    `${PROFILE_LABELS[selectedProfile]} allocation for PKR ${formatPKR(AMOUNT)} across savings, funds and PSX dividends.`;

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
  renderPortfolioGamification(totalIncome, blended, monthly);

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
          <div class="alloc-sub">${a.type} &nbsp;·&nbsp; ${a.shariah ? "Shariah" : "Conventional"}</div>
          <div style="font-size:.75rem;color:var(--muted);margin-top:2px">${a.where}</div>
        </div>
        <div class="alloc-amount">
          <div>PKR ${formatPKR(amt)}</div>
          <div class="alloc-pct">${a.pct}% &nbsp;·&nbsp; ${a.ret ? a.ret + "% ret" : "-"}</div>
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
    { n: 4, title: "Keep Emergency Buffer Liquid",          body: `At the same CDNS visit, open a Savings Account with PKR ${formatPKR(Math.round(AMOUNT * 0.05))}. No lock-in - withdraw anytime.`, color: "#5E5C52" },
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
    renderRiskChart();
  }, 50);
}

function renderPortfolioGamification(totalIncome, blended, monthly) {
  const score = calculateReadinessScore(AMOUNT) || 0;
  setText("portfolio-score", score);
  setText("portfolio-score-copy",
    `${PROFILE_LABELS[selectedProfile]} profile: estimated ${blended}% blended return and PKR ${formatPKR(monthly)} monthly income.`
  );
  const badges = [
    { label: "Diversified", unlocked: true },
    { label: "Inflation-aware", unlocked: DATA ? parseFloat(blended) > DATA.macro.inflation_cpi : false },
    { label: "Emergency buffer", unlocked: true },
    { label: totalIncome > 0 ? "Income mapped" : "Income pending", unlocked: totalIncome > 0 },
  ];
  const badgeEl = document.getElementById("portfolio-badges");
  if (!badgeEl) return;
  badgeEl.innerHTML = badges.map(b =>
    `<span class="score-badge ${b.unlocked ? "unlocked" : ""}">${b.label}</span>`
  ).join("");
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

function bestOf(arr, key) {
  return arr.reduce((a, b) => (b[key] > a[key] ? b : a), arr[0]);
}
function dashboardInputs() {
  const m = DATA.macro;
  const nssPublic = DATA.national_savings.filter(s => s.eligible === "All Pakistanis");
  const ssc = bestOf(nssPublic, "rate");
  const nssMax = bestOf(DATA.national_savings, "rate");           // e.g. Behbood
  const mmf = bestOf(DATA.mutual_funds.filter(f => /money|income/i.test(f.type)), "ret_1y");
  const eq  = bestOf(DATA.mutual_funds.filter(f => /equity|stock|mutual/i.test(f.type) || f.ret_5y > 14), "ret_5y");
  const topStock = bestOf(DATA.stocks, "yield");
  return { m, ssc, nssMax, mmf, eq, topStock };
}

function renderInsightStrip() {
  const el = document.getElementById("insight-strip");
  if (!el) return;
  const { m, ssc, eq, topStock } = dashboardInputs();
  const real = (ssc.rate - m.inflation_cpi).toFixed(1);
  el.innerHTML = `
    <div class="insight-cell"><div class="insight-num">+${real} pts</div>
      <div class="insight-lbl">Real return on ${ssc.name} (${ssc.rate}%) after ${m.inflation_cpi}% inflation - savers are beating inflation</div></div>
    <div class="insight-cell"><div class="insight-num">${topStock.yield}%</div>
      <div class="insight-lbl">${topStock.name} dividend yield vs ${m.sbp_rate}% policy rate - but dividends carry market risk</div></div>
    <div class="insight-cell"><div class="insight-num">${eq.ret_5y}%/yr</div>
      <div class="insight-lbl">${eq.name} 5-year average vs ${ssc.rate}% on certificates - the reward for taking equity risk</div></div>`;
}

function renderGrowChart() {
  const ctx = document.getElementById("chart-grow");
  if (!ctx || typeof Chart === "undefined") return;
  destroyChart("chart-grow");
  const { m, ssc, mmf, eq } = dashboardInputs();
  const fv = r => Math.round(100000 * Math.pow(1 + r / 100, 5));
  const rows = [
    { lbl: "Kept as cash (inflation-adjusted)", val: Math.round(100000 / Math.pow(1 + m.inflation_cpi / 100, 5)), col: LEDGER.red },
    { lbl: ssc.name + " " + ssc.rate + "%", val: fv(ssc.rate), col: LEDGER.green },
    { lbl: mmf.name + " " + mmf.ret_1y + "%", val: fv(mmf.ret_1y), col: LEDGER.navy },
    { lbl: eq.name + " " + eq.ret_5y + "% (5y avg)", val: fv(eq.ret_5y), col: LEDGER.gold },
  ];
  chartInstances["chart-grow"] = new Chart(ctx, {
    type: "bar",
    data: { labels: rows.map(r => r.lbl),
      datasets: [{ data: rows.map(r => r.val), backgroundColor: rows.map(r => r.col), borderRadius: 3 }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: "y",
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: c => "PKR " + c.raw.toLocaleString() } } },
      scales: { x: { ticks: { font: MONO_FONT, callback: v => (v / 1000) + "K" }, grid: { color: "#EFE8D8" } },
                y: { ticks: { font: { ...MONO_FONT, size: 10 } }, grid: { display: false } } } }
  });
}

function renderRealChart() {
  const ctx = document.getElementById("chart-real");
  if (!ctx || typeof Chart === "undefined") return;
  destroyChart("chart-real");
  const { m, ssc, nssMax, mmf, eq, topStock } = dashboardInputs();
  const rows = [
    { lbl: "Bank current account (0%)", r: 0 },
    { lbl: topStock.ticker + " dividend yield", r: topStock.yield },
    { lbl: ssc.name, r: ssc.rate },
    { lbl: nssMax.name + " (restricted)", r: nssMax.rate },
    { lbl: mmf.name, r: mmf.ret_1y },
    { lbl: eq.name + " (5y avg)", r: eq.ret_5y },
  ].map(x => ({ ...x, real: +(x.r - m.inflation_cpi).toFixed(2) }))
   .sort((a, b) => a.real - b.real);
  chartInstances["chart-real"] = new Chart(ctx, {
    type: "bar",
    data: { labels: rows.map(x => x.lbl),
      datasets: [{ data: rows.map(x => x.real),
        backgroundColor: rows.map(x => x.real >= 0 ? LEDGER.green3 : LEDGER.red), borderRadius: 3 }] },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: "y",
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: c => (c.raw > 0 ? "+" : "") + c.raw + " pts vs inflation" } } },
      scales: { x: { ticks: { font: MONO_FONT, callback: v => v + "%" }, grid: { color: "#EFE8D8" } },
                y: { ticks: { font: { ...MONO_FONT, size: 10 } }, grid: { display: false } } } }
  });
}

// ── Live ticker tape (v2 masthead) ───────────────────────────────
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

// ── Live gold rates (homepage card) ──────────────────────────────
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
      ? "local Sarafa rate via gold.pk"
      : "international spot (gold futures × PKR/USD)";
    srcEl.textContent = `As of ${when} · ${note}`;
  }

  renderGoldChart();
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

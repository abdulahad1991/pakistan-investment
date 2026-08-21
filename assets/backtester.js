/* Investment backtester: "what if I'd invested?" Uses dated data.json (gold + macro)
   and data/stock_history.json (monthly closes). No backend, no key. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  function fmtPKR(n) {
    if (!isFinite(n)) return "-";
    n = Math.round(n); var neg = n < 0; var s = String(Math.abs(n));
    if (s.length > 3) { var h = s.slice(0, -3), t = s.slice(-3); h = h.replace(/\B(?=(\d\d)+(?!\d))/g, ","); s = h + "," + t; }
    return (neg ? "-" : "") + "₨ " + s;
  }
  function groupPK(s) { s = s.replace(/\D/g, ""); if (s.length <= 3) return s; var h = s.slice(0, -3), t = s.slice(-3); return h.replace(/\B(?=(\d\d)+(?!\d))/g, ",") + "," + t; }
  function num(id) { return Number(String($(id).value).replace(/[^0-9.-]/g, "")) || 0; }

  var DATA = null, HIST = null, ASSETS = [], chart = null, periodM = 36;

  Promise.all([
    fetch("/data.json?v=" + Date.now()).then(function (r) { return r.json(); }),
    fetch("/data/stock_history.json?v=" + Date.now()).then(function (r) { return r.json(); }).catch(function () { return {}; })
  ]).then(function (res) {
    DATA = res[0]; HIST = res[1] || {};
    fillTicker();
    buildAssets();
    wire();
    compute();
  }).catch(function () { $("bt-note").textContent = "Could not load the dated observations. Try again shortly."; });

  function fillTicker() {
    var m = DATA.macro || {};
    var set = function (id, v) { var e = $(id); if (e) e.textContent = v; };
    if (m.kse100_level) set("tk-kse", m.kse100_level.toLocaleString());
    if (m.sbp_rate != null) set("tk-sbp", m.sbp_rate + "%");
    if (m.pkr_usd) set("tk-pkr", m.pkr_usd);
    if (m.inflation_cpi != null) set("tk-inf", m.inflation_cpi + "%");
    if (DATA.gold && DATA.gold.tola_24k) set("tk-gold", "₨" + DATA.gold.tola_24k.toLocaleString());
  }

  function buildAssets() {
    ASSETS = [];
    if (DATA.gold && DATA.gold.history && DATA.gold.history.values.length > 3) {
      ASSETS.push({ key: "GOLD", name: "Gold (24K, per tola)", labels: DATA.gold.history.labels, values: DATA.gold.history.values });
    }
    var names = {}; (DATA.stocks || []).forEach(function (s) { names[s.ticker] = s.name; });
    Object.keys(HIST).sort().forEach(function (tk) {
      var h = HIST[tk];
      if (h && h.values && h.values.length > 3) ASSETS.push({ key: tk, name: (names[tk] || tk) + " (" + tk + ")", labels: h.labels, values: h.values });
    });
    var sel = $("bt-asset");
    sel.innerHTML = ASSETS.map(function (a, i) { return '<option value="' + i + '">' + a.name + "</option>"; }).join("");
  }

  function wire() {
    var amt = $("bt-amount");
    amt.addEventListener("input", function () {
      var pos = amt.value.length - amt.selectionStart;
      amt.value = groupPK(amt.value);
      try { amt.selectionStart = amt.selectionEnd = amt.value.length - pos; } catch (e) {}
      compute();
    });
    $("bt-asset").addEventListener("change", compute);
    $("bt-ns").addEventListener("input", compute);
    $("bt-period").querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        $("bt-period").querySelectorAll("button").forEach(function (x) { x.classList.remove("on"); });
        b.classList.add("on"); periodM = +b.getAttribute("data-m"); compute();
      });
    });
    document.querySelectorAll(".ip input,.ip select").forEach(function (i) {
      i.addEventListener("focus", function () { i.parentElement.classList.add("focus"); });
      i.addEventListener("blur", function () { i.parentElement.classList.remove("focus"); });
    });
  }

  function compute() {
    if (!ASSETS.length) { $("bt-note").textContent = "No price history available yet."; return; }
    var amount = num("bt-amount");
    var a = ASSETS[Math.max(0, Math.min(ASSETS.length - 1, +$("bt-asset").value))];
    var scenarioRate = Math.max(-1, Math.min(1, num("bt-ns") / 100));
    var labels = a.labels, vals = a.values, N = vals.length;
    var span = periodM > 0 ? Math.min(periodM + 1, N) : N;
    var start = N - span;
    var L = labels.slice(start), V = vals.slice(start);
    if (amount <= 0 || V.length < 2 || !V[0]) { $("bt-note").textContent = "Enter an amount to see the result."; return; }

    var units = amount / V[0];
    var series = V.map(function (p) { return units * p; });
    var scenario = L.map(function (_, i) { return amount * Math.pow(1 + scenarioRate, i / 12); });
    var final = series[series.length - 1];
    var ret = (final - amount) / amount * 100;
    var years = (V.length - 1) / 12;
    var cagr = years > 0 ? (Math.pow(final / amount, 1 / years) - 1) * 100 : 0;

    $("o-final").textContent = fmtPKR(final);
    var rv = $("o-ret"); rv.textContent = (ret >= 0 ? "+" : "") + ret.toFixed(1) + "%"; rv.className = "rv " + (ret >= 0 ? "pos" : "neg");
    var pv = $("o-profit"); pv.textContent = (final - amount >= 0 ? "+" : "") + fmtPKR(final - amount); pv.className = "rv " + (final >= amount ? "pos" : "neg");
    var cv = $("o-cagr"); cv.textContent = (cagr >= 0 ? "+" : "") + cagr.toFixed(1) + "%"; cv.className = "rv " + (cagr >= 0 ? "pos" : "neg");

    $("bt-note").textContent = "From " + L[0] + " to " + L[L.length - 1] + ", ₨ " + groupPK(String(Math.round(amount))) + " applied to " + a.name + " becomes " + fmtPKR(final) + " (" +
      (ret >= 0 ? "+" : "") + ret.toFixed(0) + "% price-only). The dashed line applies your " + (scenarioRate * 100).toFixed(1) + "% constant-rate assumption. Dividends, costs and tax are excluded.";

    draw(L, series, scenario, a.name);
    if (window.pkTrack) window.pkTrack("backtest_run", { asset: a.key });
  }

  function draw(labels, series, scenario, name) {
    if (typeof Chart === "undefined") return;
    var ctx = $("bt-chart").getContext("2d");
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          { label: name, data: series, borderColor: "#075E4B", backgroundColor: "rgba(7,94,75,.08)", borderWidth: 2.4, fill: true, tension: .25, pointRadius: 0, pointHoverRadius: 4 },
          { label: "User-set annual-rate scenario", data: scenario, borderColor: "#B98A2F", borderWidth: 1.6, borderDash: [5, 4], fill: false, tension: .1, pointRadius: 0, pointHoverRadius: 3 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { font: { family: "Poppins" }, boxWidth: 12 } },
          tooltip: { callbacks: { label: function (c) { return c.dataset.label + ": " + fmtPKR(c.parsed.y); } } }
        },
        scales: {
          x: { ticks: { maxTicksLimit: 7, font: { family: "IBM Plex Mono", size: 10 } }, grid: { display: false } },
          y: { ticks: { font: { family: "IBM Plex Mono", size: 10 }, callback: function (v) { return "₨" + (v >= 1e6 ? (v / 1e6).toFixed(1) + "m" : (v / 1e3).toFixed(0) + "k"); } }, grid: { color: "rgba(7,94,75,.08)" } }
        }
      }
    });
  }
})();

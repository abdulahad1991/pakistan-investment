/* SIP / monthly-investment growth calculator. Pure math + Chart.js. No backend. */
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
  var chart = null;

  // Dated ticker, best-effort.
  fetch("/data.json?v=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
    var m = d.macro || {}, set = function (id, v) { var e = $(id); if (e) e.textContent = v; };
    if (m.kse100_level) set("tk-kse", m.kse100_level.toLocaleString());
    if (m.sbp_rate != null) set("tk-sbp", m.sbp_rate + "%");
    if (m.pkr_usd) set("tk-pkr", m.pkr_usd);
    if (m.inflation_cpi != null) set("tk-inf", m.inflation_cpi + "%");
    if (d.gold && d.gold.tola_24k) set("tk-gold", "₨" + d.gold.tola_24k.toLocaleString());
  }).catch(function () {});

  function compute() {
    var P = num("sip-amount");
    var years = Math.max(1, Math.min(40, Math.round(num("sip-years")) || 1));
    var r = Math.max(-1, Math.min(1, num("sip-return") / 100));
    var step = num("sip-stepup") / 100;
    var i = r / 12;
    var bal = 0, invested = 0, contrib = P;
    var labels = ["0"], valSeries = [0], invSeries = [0];
    for (var y = 1; y <= years; y++) {
      for (var m = 0; m < 12; m++) { bal = bal * (1 + i) + contrib; invested += contrib; }
      labels.push("Yr " + y); valSeries.push(bal); invSeries.push(invested);
      contrib = contrib * (1 + step);
    }
    var gains = bal - invested;
    var mult = invested > 0 ? bal / invested : 0;

    $("o-fv").textContent = fmtPKR(bal);
    $("o-inv").textContent = fmtPKR(invested);
    var gainEl = $("o-gain");
    gainEl.textContent = (gains > 0 ? "+" : "") + fmtPKR(gains);
    gainEl.className = "rv " + (gains >= 0 ? "pos" : "neg");
    $("o-mult").textContent = mult.toFixed(2) + "x";
    $("sip-note").textContent = fmtPKR(P) + " contributed at each month-end" + (step > 0 ? ", with a " + (step * 100).toFixed(0) + "% yearly contribution step-up," : "") +
      " for " + years + " years under a " + (r * 100).toFixed(1) + "% constant nominal annual-rate scenario produces " + fmtPKR(bal) +
      ". Total contributions are " + fmtPKR(invested) + "; costs, tax and variable returns are excluded.";

    draw(labels, invSeries, valSeries);
    if (window.pkTrack) window.pkTrack("sip_calc", {});
  }

  function draw(labels, inv, val) {
    if (typeof Chart === "undefined") return;
    var ctx = $("sip-chart").getContext("2d");
    if (chart) chart.destroy();
    chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [
          { label: "Scenario value", data: val, borderColor: "#075E4B", backgroundColor: "rgba(7,94,75,.10)", borderWidth: 2.4, fill: true, tension: .25, pointRadius: 0, pointHoverRadius: 4 },
          { label: "Total contributions", data: inv, borderColor: "#B98A2F", borderWidth: 1.6, borderDash: [5, 4], fill: false, tension: .1, pointRadius: 0, pointHoverRadius: 3 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { font: { family: "Poppins" }, boxWidth: 12 } },
          tooltip: { callbacks: { label: function (c) { return c.dataset.label + ": " + fmtPKR(c.parsed.y); } } }
        },
        scales: {
          x: { ticks: { maxTicksLimit: 8, font: { family: "IBM Plex Mono", size: 10 } }, grid: { display: false } },
          y: { ticks: { font: { family: "IBM Plex Mono", size: 10 }, callback: function (v) { return "₨" + (v >= 1e6 ? (v / 1e6).toFixed(1) + "m" : (v / 1e3).toFixed(0) + "k"); } }, grid: { color: "rgba(7,94,75,.08)" } }
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var amt = $("sip-amount");
    amt.addEventListener("input", function () {
      var pos = amt.value.length - amt.selectionStart;
      amt.value = groupPK(amt.value);
      try { amt.selectionStart = amt.selectionEnd = amt.value.length - pos; } catch (e) {}
      compute();
    });
    ["sip-years", "sip-return", "sip-stepup"].forEach(function (id) { $(id).addEventListener("input", compute); });
    document.querySelectorAll(".ip input").forEach(function (i) {
      i.addEventListener("focus", function () { i.parentElement.classList.add("focus"); });
      i.addEventListener("blur", function () { i.parentElement.classList.remove("focus"); });
    });
    compute();
  });
})();

/* Portfolio tracker: holdings in localStorage, valued from live data.json.
   No login, nothing leaves the browser. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var KEY = "pk_portfolio_v1";
  var DATA = null, STK = {}, chart = null;
  var PAL = ["#075E4B", "#0B7C5E", "#2854C5", "#B98A2F", "#0E2A22", "#0B755F", "#8A6512", "#436055", "#C24132"];

  function fmtPKR(n) {
    if (!isFinite(n)) return "₨ 0";
    n = Math.round(n); var neg = n < 0; var s = String(Math.abs(n));
    if (s.length > 3) { var h = s.slice(0, -3), t = s.slice(-3); h = h.replace(/\B(?=(\d\d)+(?!\d))/g, ","); s = h + "," + t; }
    return (neg ? "-" : "") + "₨ " + s;
  }
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; } }
  function save(h) { try { localStorage.setItem(KEY, JSON.stringify(h)); } catch (e) {} }

  fetch("/data.json?v=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
    DATA = d;
    (d.stocks || []).forEach(function (s) { if (s.price > 0) STK[s.ticker] = s; });
    var m = d.macro || {}, set = function (id, v) { var e = $(id); if (e) e.textContent = v; };
    if (m.kse100_level) set("tk-kse", m.kse100_level.toLocaleString());
    if (m.sbp_rate != null) set("tk-sbp", m.sbp_rate + "%");
    if (m.pkr_usd) set("tk-pkr", m.pkr_usd);
    if (m.inflation_cpi != null) set("tk-inf", m.inflation_cpi + "%");
    if (d.gold && d.gold.tola_24k) set("tk-gold", "₨" + d.gold.tola_24k.toLocaleString());
    var sel = $("pf-ticker");
    sel.innerHTML = Object.keys(STK).sort(function (a, b) { return STK[a].name.localeCompare(STK[b].name); })
      .map(function (t) { return '<option value="' + t + '">' + STK[t].name + " (" + t + ")</option>"; }).join("");
    render();
  }).catch(function () { $("pf-emptymsg").textContent = "Could not load live prices. Try again shortly."; });

  function priceOf(h) {
    if (h.type === "stock") return (STK[h.ticker] || {}).price || 0;
    if (h.type === "gold") return (DATA.gold && DATA.gold.gram_24k) || 0;
    return 1; // cash
  }
  function chgOf(h) {
    if (h.type === "stock") return (STK[h.ticker] || {}).chg1y || 0;
    if (h.type === "gold") return (DATA.gold && DATA.gold.chg1y_pct) || 0;
    return 0;
  }
  function labelOf(h) {
    if (h.type === "stock") return (STK[h.ticker] || {}).name || h.ticker;
    if (h.type === "gold") return "Gold (24K)";
    return "Cash / Savings";
  }
  function unit(h) { return h.type === "stock" ? "sh" : h.type === "gold" ? "g" : ""; }

  function render() {
    var hs = load();
    var rows = $("pf-rows"); rows.innerHTML = "";
    var total = 0, weighted = 0, slices = [], labels = [], colors = [];
    hs.forEach(function (h, i) {
      var price = priceOf(h), val = h.qty * (h.type === "cash" ? 1 : price), chg = chgOf(h);
      total += val; weighted += val * chg;
      slices.push(val); labels.push(labelOf(h)); colors.push(PAL[i % PAL.length]);
      var tr = document.createElement("tr");
      tr.innerHTML = "<td><b>" + labelOf(h) + "</b></td>"
        + "<td>" + (h.qty % 1 === 0 ? h.qty : h.qty.toFixed(2)) + " " + unit(h) + "</td>"
        + "<td>" + (h.type === "cash" ? "-" : fmtPKR(price)) + "</td>"
        + "<td>" + fmtPKR(val) + "</td>"
        + '<td class="' + (chg >= 0 ? "pos" : "neg") + '">' + (h.type === "cash" ? "-" : (chg >= 0 ? "+" : "") + chg.toFixed(1) + "%") + "</td>"
        + '<td><button class="pf-del" data-i="' + i + '" aria-label="Remove">&times;</button></td>';
      rows.appendChild(tr);
    });
    $("pf-emptymsg").style.display = hs.length ? "none" : "block";
    $("pf-table").style.display = hs.length ? "" : "none";

    $("pf-total").textContent = fmtPKR(total);
    $("pf-count").textContent = hs.length;
    var pc = total > 0 ? weighted / total : 0;
    var chgEl = $("pf-chg"); chgEl.textContent = hs.length ? (pc >= 0 ? "+" : "") + pc.toFixed(1) + "%" : "-";
    chgEl.className = "rv " + (pc >= 0 ? "pos" : "neg");
    var top = "-";
    if (slices.length) { var mi = slices.indexOf(Math.max.apply(null, slices)); top = labels[mi] + " " + Math.round(slices[mi] / total * 100) + "%"; }
    $("pf-top").textContent = top;

    rows.querySelectorAll(".pf-del").forEach(function (b) {
      b.addEventListener("click", function () { var arr = load(); arr.splice(+b.getAttribute("data-i"), 1); save(arr); render(); });
    });
    drawDonut(labels, slices, colors);
  }

  function drawDonut(labels, data, colors) {
    if (typeof Chart === "undefined") return;
    var ctx = $("pf-donut").getContext("2d");
    if (chart) chart.destroy();
    if (!data.length) { return; }
    chart = new Chart(ctx, {
      type: "doughnut",
      data: { labels: labels, datasets: [{ data: data, backgroundColor: colors, borderColor: "#fff", borderWidth: 2 }] },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: "60%",
        plugins: {
          legend: { position: "right", labels: { font: { family: "Nunito", size: 11 }, boxWidth: 12 } },
          tooltip: { callbacks: { label: function (c) { return c.label + ": " + fmtPKR(c.parsed); } } }
        }
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    function syncType() {
      var t = $("pf-type").value;
      $("pf-tickwrap").style.display = t === "stock" ? "" : "none";
      $("pf-qtylabel").textContent = t === "stock" ? "Shares" : t === "gold" ? "Grams (24K)" : "Amount (₨)";
    }
    $("pf-type").addEventListener("change", syncType); syncType();
    $("pf-add").addEventListener("click", function () {
      var t = $("pf-type").value;
      var qty = Number(String($("pf-qty").value).replace(/[^0-9.]/g, "")) || 0;
      if (qty <= 0) { $("pf-qty").focus(); return; }
      var h = { type: t, qty: qty };
      if (t === "stock") { h.ticker = $("pf-ticker").value; if (!h.ticker) return; }
      var arr = load(); arr.push(h); save(arr);
      $("pf-qty").value = "";
      render();
      if (window.pkTrack) window.pkTrack("portfolio_add", { type: t });
    });
    document.querySelectorAll(".ip input,.ip select").forEach(function (i) {
      i.addEventListener("focus", function () { i.parentElement.classList.add("focus"); });
      i.addEventListener("blur", function () { i.parentElement.classList.remove("focus"); });
    });
  });
})();

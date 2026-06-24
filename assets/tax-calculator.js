/* Pakistan Tax Calculator - interactive engine.
   Educational only; not tax advice. Rates are as reported for FY2026-27
   (salaried slabs reflect the Budget 2026-27 cuts, effective 1 July 2026
   pending the Finance Act); non-salaried/AOP and sales-tax rates reflect the
   current published position. Verify the enacted figures on fbr.gov.pk and the
   relevant provincial revenue authority before relying on any result. */
(function () {
  'use strict';

  /* ── Rate tables ─────────────────────────────────────────── */

  // Salaried - annual taxable income (FY2026-27, post-budget cuts, surcharge abolished)
  var SALARIED = [
    { upTo: 600000, from: 0, base: 0, rate: 0 },
    { upTo: 1200000, from: 600000, base: 0, rate: 0.01 },
    { upTo: 2200000, from: 1200000, base: 6000, rate: 0.11 },
    { upTo: 3200000, from: 2200000, base: 116000, rate: 0.20 },
    { upTo: 4100000, from: 3200000, base: 316000, rate: 0.25 },
    { upTo: 5600000, from: 4100000, base: 541000, rate: 0.29 },
    { upTo: 7000000, from: 5600000, base: 976000, rate: 0.32 },
    { upTo: Infinity, from: 7000000, base: 1424000, rate: 0.35 }
  ];

  // Salaried - PREVIOUS year (FY2025-26, pre-budget) for comparison. 9% surcharge over Rs 10m.
  var SALARIED_OLD = [
    { upTo: 600000, from: 0, base: 0, rate: 0 },
    { upTo: 1200000, from: 600000, base: 0, rate: 0.01 },
    { upTo: 2200000, from: 1200000, base: 6000, rate: 0.11 },
    { upTo: 3200000, from: 2200000, base: 116000, rate: 0.23 },
    { upTo: 4100000, from: 3200000, base: 346000, rate: 0.30 },
    { upTo: Infinity, from: 4100000, base: 616000, rate: 0.35 }
  ];

  // Non-salaried individual & AOP - annual taxable income (current published slabs)
  var NONSAL = [
    { upTo: 600000, from: 0, base: 0, rate: 0 },
    { upTo: 1200000, from: 600000, base: 0, rate: 0.15 },
    { upTo: 1600000, from: 1200000, base: 90000, rate: 0.20 },
    { upTo: 3200000, from: 1600000, base: 170000, rate: 0.30 },
    { upTo: 5600000, from: 3200000, base: 650000, rate: 0.40 },
    { upTo: Infinity, from: 5600000, base: 1610000, rate: 0.45 }
  ];

  // GST on goods (federal). Standard 18%.
  var GST_STANDARD = 18;

  // Provincial sales tax on services - standard rates (%)
  var SERVICE_RATES = { Punjab: 16, Sindh: 15, KPK: 15, Balochistan: 15, Islamabad: 15 };

  // Restaurant sales tax (%) - cash vs card/digital. Punjab & Islamabad give a
  // large reduced rate for digital payments; other provinces verify with their board.
  var RESTAURANT_RATES = {
    Punjab: { cash: 16, card: 5 },
    Islamabad: { cash: 16, card: 5 },
    Sindh: { cash: 15, card: 15 },
    KPK: { cash: 15, card: 15 },
    Balochistan: { cash: 15, card: 15 }
  };

  /* ── Pure compute functions (exposed for testing) ────────── */

  function computeIncomeTax(income, type, year) {
    income = Math.max(0, Number(income) || 0);
    year = year || 'fy27';
    var slabs = type === 'nonsalaried' ? NONSAL : (year === 'fy26' ? SALARIED_OLD : SALARIED);
    var slab = slabs[slabs.length - 1];
    for (var i = 0; i < slabs.length; i++) {
      if (income <= slabs[i].upTo) { slab = slabs[i]; break; }
    }
    var tax = slab.base + slab.rate * (income - slab.from);
    // Surcharge over Rs 10m: non-salaried/AOP 10% (both years); salaried 9% in FY2025-26,
    // abolished in FY2026-27.
    var surcharge = 0;
    if (income > 10000000) {
      if (type === 'nonsalaried') surcharge = tax * 0.10;
      else if (year === 'fy26') surcharge = tax * 0.09;
    }
    var total = tax + surcharge;
    return {
      income: income,
      tax: tax,
      surcharge: surcharge,
      total: total,
      afterTax: income - total,
      monthlyTakeHome: (income - total) / 12,
      effective: income > 0 ? total / income * 100 : 0,
      marginalRate: Math.round(slab.rate * 100),
      slabFrom: slab.from,
      slabBase: slab.base
    };
  }

  function computeGst(amount, ratePct, mode) {
    amount = Math.max(0, Number(amount) || 0);
    var r = (Number(ratePct) || 0) / 100;
    var net, tax, gross;
    if (mode === 'extract') { gross = amount; net = amount / (1 + r); tax = gross - net; }
    else { net = amount; tax = amount * r; gross = net + tax; }
    return { net: net, tax: tax, gross: gross, rate: Number(ratePct) || 0 };
  }

  // expose for tests / verification
  var API = {
    computeIncomeTax: computeIncomeTax, computeGst: computeGst,
    SALARIED: SALARIED, SALARIED_OLD: SALARIED_OLD, NONSAL: NONSAL,
    SERVICE_RATES: SERVICE_RATES, RESTAURANT_RATES: RESTAURANT_RATES
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  if (typeof window !== 'undefined') window.PakTax = API;

  /* ── Formatting helpers ──────────────────────────────────── */
  function rs(n) {
    return 'Rs ' + Math.round(n).toLocaleString('en-PK');
  }
  function pct(n) { return n.toFixed(2) + '%'; }
  function parseAmount(el) {
    if (!el) return 0;
    return Number(String(el.value).replace(/[, ]/g, '')) || 0;
  }

  /* ── DOM wiring (browser only) ───────────────────────────── */
  if (typeof document === 'undefined') return;

  document.addEventListener('DOMContentLoaded', function () {

    /* Tabs */
    var tabs = Array.prototype.slice.call(document.querySelectorAll('[data-tax-tab]'));
    var panels = Array.prototype.slice.call(document.querySelectorAll('[data-tax-panel]'));
    function activate(id) {
      tabs.forEach(function (t) {
        var on = t.getAttribute('data-tax-tab') === id;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.classList.toggle('tax-tab-active', on);
      });
      panels.forEach(function (p) { p.hidden = p.getAttribute('data-tax-panel') !== id; });
      if (window.gtag) try { gtag('event', 'tax_tab', { tab: id }); } catch (e) {}
    }
    tabs.forEach(function (t) { t.addEventListener('click', function () { activate(t.getAttribute('data-tax-tab')); }); });

    /* Income tax */
    var incAmt = document.getElementById('inc-amount');
    var incPeriod = document.getElementById('inc-period');
    var incTypeEls = Array.prototype.slice.call(document.querySelectorAll('input[name="inc-type"]'));
    var incOut = document.getElementById('inc-result');
    function incType() { var c = incTypeEls.filter(function (e) { return e.checked; })[0]; return c ? c.value : 'salaried'; }
    function runIncome() {
      if (!incAmt || !incOut) return;
      var raw = parseAmount(incAmt);
      var annual = (incPeriod && incPeriod.value === 'monthly') ? raw * 12 : raw;
      if (annual <= 0) { incOut.innerHTML = '<p class="tax-hint">Enter your taxable income to see the breakdown.</p>'; return; }
      var type = incType();
      var r = computeIncomeTax(annual, type, 'fy27');
      var compare = '';
      if (type === 'salaried') {
        var old = computeIncomeTax(annual, 'salaried', 'fy26');
        var saving = old.total - r.total;
        if (saving > 0.5) {
          compare = '<p class="tax-note" style="border-left:4px solid #175A41;background:#E9EFE6;padding:10px 14px;border-radius:0 6px 6px 0">' +
            'Under the previous FY2025-26 slabs you would have paid <strong>' + rs(old.total) + '</strong> - the Budget 2026-27 cut saves you about <strong>' + rs(saving) + '</strong> a year (' + rs(saving / 12) + '/month).</p>';
        }
      }
      incOut.innerHTML =
        resultGrid([
          ['Annual income tax', rs(r.tax), '#0E3B2E'],
          r.surcharge > 0 ? ['+ Surcharge', rs(r.surcharge), '#A4452F'] : null,
          ['Total tax / year', rs(r.total), '#A4452F'],
          ['Take-home / year', rs(r.afterTax), '#175A41'],
          ['Take-home / month', rs(r.monthlyTakeHome), '#175A41'],
          ['Effective tax rate', pct(r.effective), '#7A5A1F']
        ]) + compare +
        '<p class="tax-note">Marginal rate on the top slice of your income: <strong>' + r.marginalRate + '%</strong>. ' +
        (type === 'salaried'
          ? 'Salaried slabs shown are the Budget 2026-27 rates (effective 1 July 2026, pending the Finance Act).'
          : 'Non-salaried / business individual &amp; AOP slabs; a 10% surcharge applies on tax where annual income exceeds Rs 10 million.') +
        ' Verify the enacted slabs on <a href="https://www.fbr.gov.pk" target="_blank" rel="noopener">fbr.gov.pk</a>.</p>';
      if (window.gtag) try { gtag('event', 'tax_calc', { kind: 'income', type: type }); } catch (e) {}
    }
    [incAmt, incPeriod].forEach(function (el) { if (el) el.addEventListener('input', runIncome); });
    incTypeEls.forEach(function (el) { el.addEventListener('change', runIncome); });

    /* GST / sales tax */
    var gAmt = document.getElementById('gst-amount');
    var gRate = document.getElementById('gst-rate');
    var gMode = document.getElementById('gst-mode');
    var gKind = document.getElementById('gst-kind');
    var gProv = document.getElementById('gst-province');
    var gOut = document.getElementById('gst-result');
    var gProvWrap = document.getElementById('gst-province-wrap');
    function syncGstRate() {
      if (!gKind || !gRate) return;
      if (gKind.value === 'goods') {
        if (gProvWrap) gProvWrap.style.display = 'none';
        gRate.value = GST_STANDARD;
      } else {
        if (gProvWrap) gProvWrap.style.display = '';
        gRate.value = SERVICE_RATES[gProv ? gProv.value : 'Punjab'];
      }
      runGst();
    }
    function runGst() {
      if (!gAmt || !gOut) return;
      var amt = parseAmount(gAmt);
      if (amt <= 0) { gOut.innerHTML = '<p class="tax-hint">Enter an amount to split out the sales tax.</p>'; return; }
      var r = computeGst(amt, gRate ? gRate.value : GST_STANDARD, gMode ? gMode.value : 'add');
      gOut.innerHTML = resultGrid([
        ['Price before tax', rs(r.net), '#0E3B2E'],
        ['Sales tax (' + r.rate + '%)', rs(r.tax), '#A4452F'],
        ['Total price', rs(r.gross), '#175A41']
      ]);
      if (window.gtag) try { gtag('event', 'tax_calc', { kind: 'gst' }); } catch (e) {}
    }
    if (gKind) gKind.addEventListener('change', syncGstRate);
    if (gProv) gProv.addEventListener('change', syncGstRate);
    [gAmt, gRate, gMode].forEach(function (el) { if (el) el.addEventListener('input', runGst); });

    /* Restaurant */
    var rAmt = document.getElementById('rest-amount');
    var rProv = document.getElementById('rest-province');
    var rPayEls = Array.prototype.slice.call(document.querySelectorAll('input[name="rest-pay"]'));
    var rOut = document.getElementById('rest-result');
    function restPay() { var c = rPayEls.filter(function (e) { return e.checked; })[0]; return c ? c.value : 'card'; }
    function runRest() {
      if (!rAmt || !rOut) return;
      var bill = parseAmount(rAmt);
      var prov = rProv ? rProv.value : 'Punjab';
      var rates = RESTAURANT_RATES[prov] || RESTAURANT_RATES.Punjab;
      if (bill <= 0) { rOut.innerHTML = '<p class="tax-hint">Enter your food bill to see the sales tax.</p>'; return; }
      var pay = restPay();
      var rate = rates[pay];
      var tax = bill * rate / 100;
      var saving = (rates.cash - rates.card) / 100 * bill;
      var html = resultGrid([
        ['Food bill', rs(bill), '#0E3B2E'],
        ['Sales tax (' + rate + '%)', rs(tax), '#A4452F'],
        ['Total to pay', rs(bill + tax), '#175A41']
      ]);
      if (saving > 0) {
        html += '<p class="tax-note">' + (pay === 'card'
          ? 'Paying by card/digital here saves <strong>' + rs(saving) + '</strong> versus cash (' + rates.cash + '%) on this bill.'
          : 'Paying by <strong>card/digital</strong> instead would cost only ' + rates.card + '% - a saving of <strong>' + rs(saving) + '</strong> on this bill.');
        html += '</p>';
      } else {
        html += '<p class="tax-note">In ' + prov + ', the documented rate is ' + rate + '%. A reduced card/digital rate may apply - verify with the provincial revenue authority.</p>';
      }
      rOut.innerHTML = html;
      if (window.gtag) try { gtag('event', 'tax_calc', { kind: 'restaurant', province: prov, pay: pay }); } catch (e) {}
    }
    if (rProv) rProv.addEventListener('change', runRest);
    rPayEls.forEach(function (el) { el.addEventListener('change', runRest); });
    if (rAmt) rAmt.addEventListener('input', runRest);

    function resultGrid(rows) {
      return '<div class="tax-result-grid">' + rows.filter(Boolean).map(function (r) {
        return '<div class="tax-cell"><div class="tax-cell-val" style="color:' + r[2] + '">' + r[1] + '</div><div class="tax-cell-lbl">' + r[0] + '</div></div>';
      }).join('') + '</div>';
    }

    /* History comparison chart - salaried tax: FY2025-26 (old) vs FY2026-27 (new) */
    function rsShort(n) {
      n = Math.round(n);
      if (n >= 1000000) return (n / 1000000).toFixed(n >= 10000000 ? 1 : 2) + 'm';
      if (n >= 1000) return Math.round(n / 1000) + 'k';
      return '' + n;
    }
    function renderHistoryChart() {
      var host = document.getElementById('tax-history-chart');
      if (!host) return;
      var incomes = [1500000, 2500000, 3500000, 5000000, 7000000, 10000000];
      var labels = ['1.5m', '2.5m', '3.5m', '5m', '7m', '10m'];
      var data = incomes.map(function (inc) {
        return { old: computeIncomeTax(inc, 'salaried', 'fy26').total, neu: computeIncomeTax(inc, 'salaried', 'fy27').total };
      });
      var max = 0; data.forEach(function (d) { max = Math.max(max, d.old, d.neu); });
      var W = 720, H = 380, padL = 56, padR = 16, padT = 22, padB = 72;
      var plotH = H - padT - padB, plotW = W - padL - padR;
      var gw = plotW / incomes.length, bw = gw * 0.30;
      function y(v) { return padT + plotH - (v / max) * plotH; }
      var grid = '', bars = '', xl = '';
      for (var g = 0; g <= 4; g++) {
        var gv = max * g / 4, gy = y(gv);
        grid += '<line x1="' + padL + '" y1="' + gy + '" x2="' + (W - padR) + '" y2="' + gy + '" stroke="#EFE8D8" stroke-width="1"></line>';
        grid += '<text x="' + (padL - 8) + '" y="' + (gy + 3) + '" text-anchor="end" font-family="\'IBM Plex Mono\',monospace" font-size="9" fill="#8a887d">' + (gv > 0 ? rsShort(gv) : '0') + '</text>';
      }
      data.forEach(function (d, i) {
        var gx = padL + i * gw + gw / 2, x1 = gx - bw - 3, x2 = gx + 3;
        bars += '<rect x="' + x1 + '" y="' + y(d.old) + '" width="' + bw + '" height="' + (padT + plotH - y(d.old)) + '" rx="2" fill="#B98A2F"></rect>';
        bars += '<rect x="' + x2 + '" y="' + y(d.neu) + '" width="' + bw + '" height="' + (padT + plotH - y(d.neu)) + '" rx="2" fill="#0E3B2E"></rect>';
        bars += '<text x="' + (x1 + bw / 2) + '" y="' + (y(d.old) - 5) + '" text-anchor="middle" font-family="\'IBM Plex Mono\',monospace" font-size="9" fill="#7A5A1F">' + rsShort(d.old) + '</text>';
        bars += '<text x="' + (x2 + bw / 2) + '" y="' + (y(d.neu) - 5) + '" text-anchor="middle" font-family="\'IBM Plex Mono\',monospace" font-size="9" fill="#0E3B2E">' + rsShort(d.neu) + '</text>';
        xl += '<text x="' + gx + '" y="' + (padT + plotH + 18) + '" text-anchor="middle" font-family="\'IBM Plex Mono\',monospace" font-size="11" fill="#6B6A60">Rs ' + labels[i] + '</text>';
      });
      host.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" style="height:auto" role="img" aria-label="Grouped bar chart comparing annual salaried income tax under FY2025-26 versus FY2026-27 slabs, at taxable incomes from Rs 1.5 million to Rs 10 million">' +
        grid + bars + xl +
        '<rect x="' + padL + '" y="' + (H - 30) + '" width="12" height="12" fill="#B98A2F"></rect><text x="' + (padL + 18) + '" y="' + (H - 20) + '" font-family="\'IBM Plex Mono\',monospace" font-size="11" fill="#6B6A60">FY2025-26 (old)</text>' +
        '<rect x="' + (padL + 160) + '" y="' + (H - 30) + '" width="12" height="12" fill="#0E3B2E"></rect><text x="' + (padL + 178) + '" y="' + (H - 20) + '" font-family="\'IBM Plex Mono\',monospace" font-size="11" fill="#6B6A60">FY2026-27 (new)</text>' +
        '</svg>';
    }

    // initial render
    runIncome(); syncGstRate(); runRest(); renderHistoryChart();
  });
})();

/* Zakat Calculator — interactive engine.
   Educational only; not a religious ruling. Zakat is 2.5% of zakatable net
   wealth held for one lunar year (hawl), payable if that wealth is at or above
   the nisab. Nisab = value of 87.48g (7.5 tola) of gold OR 612.36g (52.5 tola)
   of silver; many scholars recommend the lower (silver) nisab. Rulings on what
   is zakatable vary — consult a scholar you trust. */
(function () {
  'use strict';

  var TOLA_G = 11.6638;
  var GOLD_NISAB_TOLA = 7.5;     // 87.48 g
  var SILVER_NISAB_TOLA = 52.5;  // 612.36 g
  var ZAKAT_RATE = 0.025;

  function nisabValue(basis, pricePerTola) {
    pricePerTola = Math.max(0, Number(pricePerTola) || 0);
    var tolas = basis === 'gold' ? GOLD_NISAB_TOLA : SILVER_NISAB_TOLA;
    return tolas * pricePerTola;
  }

  function computeZakat(a) {
    var n = function (x) { return Math.max(0, Number(x) || 0); };
    var assets = n(a.cash) + n(a.gold) + n(a.silver) + n(a.investments) + n(a.business) + n(a.receivables);
    var net = Math.max(0, assets - n(a.liabilities));
    var nisab = n(a.nisab);
    var due = nisab > 0 && net >= nisab;
    var zakat = due ? net * ZAKAT_RATE : 0;
    return { assets: assets, net: net, nisab: nisab, due: due, zakat: zakat, belowNisab: nisab > 0 && net < nisab };
  }

  var API = { computeZakat: computeZakat, nisabValue: nisabValue,
    GOLD_NISAB_TOLA: GOLD_NISAB_TOLA, SILVER_NISAB_TOLA: SILVER_NISAB_TOLA, ZAKAT_RATE: ZAKAT_RATE, TOLA_G: TOLA_G };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  if (typeof window !== 'undefined') window.PakZakat = API;

  if (typeof document === 'undefined') return;

  function rs(n) { return 'Rs ' + Math.round(n).toLocaleString('en-PK'); }
  function val(id) { var el = document.getElementById(id); return el ? Number(String(el.value).replace(/[, ]/g, '')) || 0 : 0; }

  document.addEventListener('DOMContentLoaded', function () {
    var basisEl = document.getElementById('zk-basis');
    var priceEl = document.getElementById('zk-price');
    var priceLbl = document.getElementById('zk-price-label');
    var out = document.getElementById('zk-result');
    if (!out) return;

    var INPUTS = ['zk-cash', 'zk-gold', 'zk-silver', 'zk-invest', 'zk-business', 'zk-receivable', 'zk-liabilities', 'zk-price'];

    function syncLabel() {
      if (!priceLbl || !basisEl) return;
      var b = basisEl.value;
      priceLbl.textContent = (b === 'gold' ? 'Gold' : 'Silver') + ' price per tola (Rs)';
    }

    function run() {
      var basis = basisEl ? basisEl.value : 'silver';
      var nisab = nisabValue(basis, val('zk-price'));
      var r = computeZakat({
        cash: val('zk-cash'), gold: val('zk-gold'), silver: val('zk-silver'),
        investments: val('zk-invest'), business: val('zk-business'), receivables: val('zk-receivable'),
        liabilities: val('zk-liabilities'), nisab: nisab
      });
      if (r.assets <= 0 && nisab <= 0) {
        out.innerHTML = '<p class="tax-hint">Enter your assets and the current ' + basis + ' price to calculate your Zakat.</p>';
        return;
      }
      var rows = [
        ['Total zakatable assets', rs(r.assets), '#0E3B2E'],
        ['Net after liabilities', rs(r.net), '#0E3B2E'],
        ['Nisab threshold', nisab > 0 ? rs(nisab) : '—', '#7A5A1F']
      ];
      var html = '<div class="tax-result-grid">' + rows.map(function (x) {
        return '<div class="tax-cell"><div class="tax-cell-val" style="color:' + x[2] + '">' + x[1] + '</div><div class="tax-cell-lbl">' + x[0] + '</div></div>';
      }).join('') + '</div>';

      if (nisab <= 0) {
        html += '<p class="tax-note">Enter the current ' + basis + ' price per tola to see whether your wealth reaches the nisab and what Zakat is due.</p>';
      } else if (r.due) {
        html += '<div class="zk-due" style="margin-top:14px;background:#E9EFE6;border:1px solid #C9D6C0;border-left:4px solid #175A41;border-radius:0 8px 8px 0;padding:14px 18px">' +
          '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;color:#6B6A60">Zakat payable (2.5%)</div>' +
          '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:1.7rem;font-weight:700;color:#0E3B2E;margin-top:2px">' + rs(r.zakat) + '</div>' +
          '<div style="font-size:.82rem;color:#5E5C52;margin-top:4px">Your net wealth is at or above the nisab, so Zakat is due at 2.5% (about ' + rs(r.zakat / 12) + '/month if you set it aside monthly).</div></div>';
      } else {
        html += '<div class="zk-due" style="margin-top:14px;background:#F4E7D4;border:1px solid #E4D3B0;border-left:4px solid #B98A2F;border-radius:0 8px 8px 0;padding:14px 18px">' +
          '<div style="font-weight:700;color:#7A5A1F">No Zakat due on these figures</div>' +
          '<div style="font-size:.82rem;color:#5E5C52;margin-top:3px">Your net zakatable wealth (' + rs(r.net) + ') is below the nisab (' + rs(nisab) + '). Zakat becomes due once it reaches the nisab and a lunar year passes.</div></div>';
      }
      html += '<p class="tax-note">Estimate only, based on the figures and metal price you entered — not a religious ruling. What counts as zakatable, and which nisab to use, can vary by scholar. Verify with a scholar you trust.</p>';
      out.innerHTML = html;
      if (window.gtag) try { gtag('event', 'zakat_calc', { basis: basis, due: r.due }); } catch (e) {}
    }

    if (basisEl) basisEl.addEventListener('change', function () { syncLabel(); run(); });
    INPUTS.forEach(function (id) { var el = document.getElementById(id); if (el) el.addEventListener('input', run); });
    syncLabel(); run();
  });
})();

/* Standalone live ticker filler for the v2 masthead tape.
   Used on pages that do NOT load app.js (calculators, guides, content).
   Fetches data.json and fills #tk-* spans; silently no-ops if absent. */
(function () {
  'use strict';
  function pkr(n) {
    if (n == null || isNaN(n)) return '-';
    var s = String(Math.round(Math.abs(n))), out = s;
    if (s.length > 3) {
      var tail = s.slice(-3), rest = s.slice(0, -3);
      while (rest.length > 2) { tail = rest.slice(-2) + ',' + tail; rest = rest.slice(0, -2); }
      out = rest + ',' + tail;
    }
    return out;
  }
  function set(id, v) { var el = document.getElementById(id); if (el) el.textContent = v; }
  function fill(d) {
    if (!d) return;
    var m = d.macro || {}, g = d.gold || {};
    if (m.kse100_level != null) set('tk-kse', pkr(m.kse100_level));
    if (m.sbp_rate != null) set('tk-sbp', m.sbp_rate + '%');
    if (m.pkr_usd != null) set('tk-pkr', '₨' + m.pkr_usd);
    if (m.inflation_cpi != null) set('tk-inf', m.inflation_cpi + '%');
    if (g.tola_24k != null) set('tk-gold', '₨' + pkr(g.tola_24k));
    var chg = document.getElementById('tkc-gold');
    if (chg && g.chg1y_pct != null) {
      var up = g.chg1y_pct >= 0;
      chg.textContent = (up ? '▲' : '▼') + Math.abs(g.chg1y_pct) + '%';
      chg.className = up ? 'up' : 'dn';
    }
  }
  // duplicate the feed once so the marquee (-50%) loops seamlessly
  var feed = document.querySelector('.ticker-feed');
  if (feed && !feed.dataset.looped) {
    feed.dataset.looped = '1';
    feed.insertAdjacentHTML('beforeend', feed.innerHTML.replace(/\sid="[^"]*"/g, ''));
  }
  function go() {
    if (!document.getElementById('tk-kse')) return; // no ticker on this page
    fetch('/data.json?v=' + Date.now()).then(function (r) { return r.json(); }).then(fill).catch(function () {});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', go);
  else go();
})();

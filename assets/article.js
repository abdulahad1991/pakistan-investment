/* Article enhancements: collapsible table of contents + daily live-data
   snapshot. Figures come from /data.json, refreshed every morning by the
   GitHub Actions scraper, so article numbers stay current without edits. */
document.addEventListener('DOMContentLoaded', function () {

  /* ── Live snapshot widget ─────────────────────────────── */
  var slot = document.getElementById('live-snap');
  if (slot) {
    fetch('/data.json').then(function (r) { return r.json(); }).then(function (d) {
      var m = d.macro;
      var ssc = null;
      (d.national_savings || []).forEach(function (s) {
        if (s.eligible === 'All Pakistanis' && (!ssc || s.rate > ssc.rate)) ssc = s;
      });
      var updated = (d.updated || '').slice(0, 10);
      function cell(val, lbl, sub, bg, color) {
        return '<div style="background:' + bg + ';border:1px solid #D9D1BE;border-radius:6px;padding:13px 8px;text-align:center">' +
          '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:1.25rem;font-weight:600;color:' + color + '">' + val + '</div>' +
          '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:.6rem;letter-spacing:.06em;text-transform:uppercase;color:#6B6A60;margin-top:4px">' + lbl + '</div>' +
          (sub ? '<div style="font-size:.7rem;color:#8a887d;margin-top:2px">' + sub + '</div>' : '') + '</div>';
      }
      slot.innerHTML =
        '<div style="display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:6px;margin-bottom:10px">' +
        '<div style="font-family:Fraunces,serif;font-weight:600;font-size:1.05rem;color:#0E3B2E">Today’s Market Numbers</div>' +
        '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;background:#B98A2F;color:#191D1A;padding:3px 9px;border-radius:3px">Updated ' + updated + '</span></div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px">' +
        cell(m.sbp_rate + '%', 'SBP Policy Rate', m.sbp_direction, '#E9EFE6', '#0E3B2E') +
        cell(m.inflation_cpi + '%', 'CPI Inflation', 'Real rate +' + (m.sbp_rate - m.inflation_cpi).toFixed(1) + '%', '#F4E7D4', '#A4452F') +
        cell(m.kse100_level.toLocaleString(), 'KSE-100', 'Index level', '#E8EDF3', '#23415E') +
        cell(m.pkr_usd, 'PKR / USD', 'Interbank', '#F6EFDA', '#7A5A1F') +
        (ssc ? cell(ssc.rate + '%', 'Top NSS Rate', ssc.name.replace(' Certificate', ''), '#E9EFE6', '#175A41') : '') +
        '</div>';
    }).catch(function () { slot.style.display = 'none'; });
  }

  /* ── Collapsible table of contents ────────────────────── */
  var byline = document.querySelector('.byline');
  var heads = Array.prototype.slice.call(document.querySelectorAll('.container h2'));
  if (byline && heads.length >= 4) {
    var toc = document.createElement('details');
    toc.style.cssText = 'border:1px solid #D9D1BE;border-left:4px solid #B98A2F;border-radius:6px;background:#FDFBF4;padding:0;margin:0 0 24px';
    var items = '';
    heads.forEach(function (h, i) {
      if (!h.id) h.id = 'sec-' + (i + 1) + '-' + h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);
      items += '<a href="#' + h.id + '" style="display:block;padding:7px 0;border-bottom:1px solid #EFE8D8;font-size:.92rem;color:#0E3B2E">' + h.textContent + '</a>';
    });
    toc.innerHTML =
      '<summary style="cursor:pointer;list-style:none;padding:13px 18px;font-family:\'IBM Plex Mono\',monospace;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:#6B6A60">☰ On this page • ' + heads.length + ' sections</summary>' +
      '<div style="padding:4px 18px 14px">' + items + '</div>';
    byline.parentNode.insertBefore(toc, byline.nextSibling);
  }
});

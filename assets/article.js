/* Article enhancements: collapsible table of contents + dated data snapshot.
   Each partition in /data.json has its own source date and health status. */
document.addEventListener('DOMContentLoaded', function () {

  /* ── Live snapshot widget ─────────────────────────────── */
  var slot = document.getElementById('live-snap');
  if (slot) {
    fetch('/data.json').then(function (r) { return r.json(); }).then(function (d) {
      var m = d.macro;
      var updated = (d.updated || '').slice(0, 10);
      var health = d.data_health || {};
      function sourceNote(key) {
        var h = health[key] || {};
        var date = h.as_of || 'date not supplied';
        return (h.stale || h.ok === false ? 'Stale / failed · ' : 'As of ') + date;
      }
      // v2 token palette for the injected widget
      function cell(val, lbl, sub, accent) {
        return '<div style="background:#FFFFFF;border:1px solid rgba(7,94,75,.22);border-top:3px solid ' + (accent || '#075E4B') + ';border-radius:4px;padding:13px 8px;text-align:center">' +
          '<div style="font-family:\'Poppins\',sans-serif;font-size:1.25rem;font-weight:800;color:#053C30;font-variant-numeric:tabular-nums">' + val + '</div>' +
          '<div style="font-family:\'IBM Plex Mono\',monospace;font-size:.6rem;letter-spacing:.06em;text-transform:uppercase;color:#436055;margin-top:4px">' + lbl + '</div>' +
          (sub ? '<div style="font-size:.7rem;color:#436055;margin-top:2px">' + sub + '</div>' : '') + '</div>';
      }
      slot.innerHTML =
        '<div style="display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:6px;margin-bottom:10px">' +
        '<div style="font-family:\'Poppins\',sans-serif;font-weight:800;font-size:1.05rem;color:#053C30">Published data snapshot</div>' +
        '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;background:#EDF804;color:#053C30;padding:3px 9px;border-radius:3px">Dataset built ' + updated + '</span></div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px">' +
        cell(m.sbp_rate + '%', 'SBP Policy Rate', sourceNote('policy'), '#075E4B') +
        cell(m.inflation_cpi + '%', 'CPI Inflation', sourceNote('inflation'), '#075E4B') +
        cell(m.kse100_level.toLocaleString(), 'KSE-100', sourceNote('kse'), '#075E4B') +
        cell(m.pkr_usd, 'PKR / USD', sourceNote('forex'), '#075E4B') +
        '</div>';
    }).catch(function () { slot.style.display = 'none'; });
  }

  /* ── Collapsible table of contents ────────────────────── */
  var byline = document.querySelector('.byline');
  var heads = Array.prototype.slice.call(document.querySelectorAll('.container h2'));
  if (byline && heads.length >= 4) {
    var toc = document.createElement('details');
    toc.style.cssText = 'border:1px solid rgba(7,94,75,.22);border-left:4px solid #EDF804;border-radius:4px;background:#F0FFFA;padding:0;margin:0 0 24px';
    var items = '';
    heads.forEach(function (h, i) {
      if (!h.id) h.id = 'sec-' + (i + 1) + '-' + h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50);
      items += '<a href="#' + h.id + '" style="display:block;padding:7px 0;border-bottom:1px solid rgba(7,94,75,.14);font-size:.92rem;color:#053C30">' + h.textContent + '</a>';
    });
    toc.innerHTML =
      '<summary style="cursor:pointer;list-style:none;padding:13px 18px;font-family:\'IBM Plex Mono\',monospace;font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;color:#436055">On this page • ' + heads.length + ' sections</summary>' +
      '<div style="padding:4px 18px 14px">' + items + '</div>';
    byline.parentNode.insertBefore(toc, byline.nextSibling);
  }
});

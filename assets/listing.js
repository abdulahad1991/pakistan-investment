/* Listing pages (guides/blog): live ticker, manifest-driven auto-listing,
   topic filters. manifest.json + data.json are rebuilt by the scheduled
   GitHub Action, so new guides appear here without editing this page. */
document.addEventListener('DOMContentLoaded', function () {

  /* ── Live ticker ──────────────────────────────────────── */
  fetch('/data.json').then(function (r) { return r.json(); }).then(function (d) {
    var m = d.macro;
    var set = function (id, v) { var e = document.getElementById(id); if (e) e.textContent = v; };
    set('t-kse', m.kse100_level.toLocaleString());
    set('t-sbp', m.sbp_rate + '%');
    set('t-inf', m.inflation_cpi + '%');
    set('t-pkr', m.pkr_usd);
    set('t-date', (d.updated || '').slice(0, 10));
  }).catch(function () {});

  /* ── Manifest: auto-append new pages, badge the newest ── */
  var grid = document.querySelector('.guides-grid');
  var kind = document.body.getAttribute('data-listing'); /* 'guides' | 'posts' */
  if (grid && kind) {
    fetch('/manifest.json').then(function (r) { return r.json(); }).then(function (man) {
      var items = man[kind] || [];
      items.forEach(function (it, i) {
        var link = grid.querySelector('a[href="' + it.url + '"]');
        if (!link) {
          var card = document.createElement('div');
          card.className = 'guide-card';
          card.setAttribute('data-cat', 'all');
          card.innerHTML =
            '<div class="guide-title">' + it.title + '</div>' +
            '<div class="guide-desc">' + it.description + '</div>' +
            '<div class="guide-meta"><span class="topic-tag tag-new">New</span>' +
            (it.modified ? '<span class="read-time">Updated ' + it.modified + '</span>' : '') + '</div>' +
            '<a href="' + it.url + '" class="guide-link">Read →</a>';
          grid.insertBefore(card, grid.firstElementChild);
        } else if (i === 0) {
          var meta = link.closest('.guide-card').querySelector('.guide-meta');
          if (meta && !meta.querySelector('.tag-new')) {
            var s = document.createElement('span');
            s.className = 'topic-tag tag-new';
            s.textContent = 'Newest';
            meta.insertBefore(s, meta.firstChild);
          }
        }
      });
      var stamp = document.getElementById('manifest-stamp');
      if (stamp && man.generated) {
        stamp.textContent = 'Library checked ' + man.generated.slice(0, 10) + ' · ' + items.length + ' published';
      }
    }).catch(function () {});
  }

  /* ── Topic filter chips ───────────────────────────────── */
  var chips = document.querySelectorAll('.chip[data-filter]');
  chips.forEach(function (ch) {
    ch.addEventListener('click', function () {
      chips.forEach(function (c) { c.classList.remove('active'); });
      ch.classList.add('active');
      var f = ch.getAttribute('data-filter');
      document.querySelectorAll('.guides-grid .guide-card').forEach(function (card) {
        var cats = card.getAttribute('data-cat') || 'all';
        card.style.display = (f === 'all' || cats.indexOf(f) >= 0) ? '' : 'none';
      });
    });
  });

  /* ── Inline text filter (live search within this listing) ── */
  var lf = document.getElementById('card-filter');
  if (lf) {
    var emptyMsg = document.getElementById('filter-empty');
    lf.addEventListener('input', function () {
      var q = lf.value.trim().toLowerCase();
      var shown = 0;
      document.querySelectorAll('.guides-grid .guide-card').forEach(function (card) {
        var hit = !q || card.textContent.toLowerCase().indexOf(q) >= 0;
        card.style.display = hit ? '' : 'none';
        if (hit) shown++;
      });
      /* typing in the text box overrides any active topic chip */
      if (q) {
        document.querySelectorAll('.chip[data-filter]').forEach(function (c) {
          c.classList.toggle('active', c.getAttribute('data-filter') === 'all');
        });
      }
      if (emptyMsg) emptyMsg.style.display = shown ? 'none' : 'block';
    });
  }
});

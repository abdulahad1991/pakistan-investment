/* Global site search - command palette.
   Index is built from manifest.json (guides + posts, rebuilt every morning
   by the GitHub Action) plus a small static list of top-level pages, so new
   guides and blog posts become searchable automatically without editing this
   file. Open with the header Search button, the "/" key, or Ctrl/Cmd-K. */
(function () {
  'use strict';

  var STATIC = [
    { url: '/',                    title: 'Investment Comparison Tool',  description: 'Compare National Savings, mutual funds and PSX stocks side by side with live daily data.', type: 'Tool' },
    { url: '/tax-calculator.html', title: 'Pakistan Tax Calculator 2026-27', description: 'Calculate income tax (salaried & business), GST, sales tax on services and restaurant tax, with a year-on-year comparison.', type: 'Tool' },
    { url: '/zakat-calculator.html', title: 'Zakat Calculator Pakistan 2026', description: 'Work out your 2.5% Zakat from cash, gold, silver, investments and business assets, with the nisab from gold or silver.', type: 'Tool' },
    { url: '/faq.html', title: 'FAQ - Pakistan Investing & Tax', description: '223 answered questions on tax, mutual funds, stocks, savings, prize bonds and Zakat, searchable and filterable by topic.', type: 'Page' },
    { url: '/guides/',             title: 'All Investment Guides',       description: 'Step-by-step guides to every major investment route in Pakistan.', type: 'Guide' },
    { url: '/blog/',               title: 'Analysis & Blog',             description: 'Budget breakdowns, policy-rate analysis and salaried-class money moves.', type: 'Blog' },
    { url: '/about.html',          title: 'About',                       description: 'Who runs Pakistan Investment Advisor and why.', type: 'Page' },
    { url: '/methodology.html',    title: 'Methodology',                 description: 'How the figures, returns and rankings on this site are produced.', type: 'Page' },
    { url: '/contact.html',        title: 'Contact',                     description: 'Get in touch with Pakistan Investment Advisor.', type: 'Page' },
    { url: '/privacy-policy.html', title: 'Privacy Policy',              description: 'How this site handles your data (it does not store any).', type: 'Page' }
  ];

  var index = STATIC.slice();
  var decoder = document.createElement('textarea');
  function decode(s) { decoder.innerHTML = s || ''; return decoder.value; }

  fetch('/manifest.json').then(function (r) { return r.json(); }).then(function (m) {
    (m.guides || []).forEach(function (g) { index.push({ url: g.url, title: decode(g.title), description: decode(g.description), type: 'Guide' }); });
    (m.posts  || []).forEach(function (p) { index.push({ url: p.url, title: decode(p.title), description: decode(p.description), type: 'Blog'  }); });
  }).catch(function () { /* static list still works */ });

  /* ── Overlay DOM ──────────────────────────────────────── */
  var ov = document.createElement('div');
  ov.className = 'search-overlay';
  ov.innerHTML =
    '<div class="search-modal" role="dialog" aria-modal="true" aria-label="Search the site">' +
      '<div class="search-box">' +
        '<span class="s-ic" aria-hidden="true"></span>' +
        '<input type="text" id="gs-input" placeholder="Search guides, blog posts, tools…" autocomplete="off" spellcheck="false" aria-label="Search">' +
        '<span class="s-esc">ESC</span>' +
      '</div>' +
      '<div class="search-results" id="gs-results"></div>' +
      '<div class="search-foot"><span><b>↑↓</b> navigate</span><span><b>↵</b> open</span><span><b>esc</b> close</span></div>' +
    '</div>';

  var input, results, active = -1, current = [];

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function hl(text, tokens) {
    var out = esc(text);
    tokens.filter(Boolean).sort(function (a, b) { return b.length - a.length; }).forEach(function (tok) {
      var re = new RegExp('(' + tok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig');
      out = out.replace(re, '<mark>$1</mark>');
    });
    return out;
  }

  function score(item, q, tokens) {
    var t = item.title.toLowerCase(), d = (item.description || '').toLowerCase(), u = item.url.toLowerCase();
    var s = 0;
    if (t === q) s += 100;
    if (t.indexOf(q) === 0) s += 50;
    if (t.indexOf(q) >= 0) s += 30;
    if (u.indexOf(q) >= 0) s += 15;
    if (d.indexOf(q) >= 0) s += 10;
    tokens.forEach(function (tok) {
      if (!tok) return;
      if (t.indexOf(tok) >= 0) s += 8;
      if (d.indexOf(tok) >= 0) s += 3;
      if (u.indexOf(tok) >= 0) s += 2;
    });
    if (item.type === 'Guide' || item.type === 'Blog') s += 1;
    return s;
  }

  function render(q) {
    q = (q || '').trim().toLowerCase();
    var tokens = q.split(/\s+/).filter(Boolean);
    var list;
    if (!q) {
      list = index.filter(function (i) { return i.type === 'Guide' || i.type === 'Blog'; }).slice(0, 7);
    } else {
      list = index.map(function (i) { return { i: i, s: score(i, q, tokens) }; })
                  .filter(function (x) { return x.s > 0; })
                  .sort(function (a, b) { return b.s - a.s; })
                  .slice(0, 8)
                  .map(function (x) { return x.i; });
    }
    current = list;
    active = list.length ? 0 : -1;

    if (!list.length) {
      results.innerHTML = '<div class="search-empty">No matches for “' + esc(q) + '”.<br><br>Browse <a href="/guides/">all guides</a> or <a href="/blog/">the blog</a> instead.</div>';
      return;
    }
    results.innerHTML = list.map(function (it, idx) {
      return '<a class="search-item' + (idx === active ? ' active' : '') + '" href="' + it.url + '" data-idx="' + idx + '">' +
        '<span class="si-body">' +
          '<span class="si-title">' + hl(it.title, tokens) + '</span>' +
          '<span class="si-desc">' + hl(it.description || '', tokens) + '</span>' +
        '</span>' +
        '<span class="s-badge ' + it.type + '">' + it.type + '</span>' +
      '</a>';
    }).join('');
    Array.prototype.forEach.call(results.querySelectorAll('.search-item'), function (el) {
      el.addEventListener('mousemove', function () { setActive(+el.getAttribute('data-idx')); });
    });
  }

  function setActive(i) {
    active = i;
    Array.prototype.forEach.call(results.querySelectorAll('.search-item'), function (el) {
      el.classList.toggle('active', +el.getAttribute('data-idx') === active);
    });
  }

  function scrollActive() { var el = results.querySelector('.search-item.active'); if (el) el.scrollIntoView({ block: 'nearest' }); }
  function go() { if (active >= 0 && current[active]) window.location.href = current[active].url; }

  function open(prefill) {
    if (!ov.parentNode) document.body.appendChild(ov);
    input = document.getElementById('gs-input');
    results = document.getElementById('gs-results');
    ov.classList.add('open');
    document.body.style.overflow = 'hidden';
    input.value = prefill || '';
    render(input.value);
    setTimeout(function () { input.focus(); }, 0);
  }
  function close() { ov.classList.remove('open'); document.body.style.overflow = ''; }

  ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
  ov.addEventListener('input', function (e) { if (e.target.id === 'gs-input') render(e.target.value); });

  document.addEventListener('keydown', function (e) {
    if (!ov.classList.contains('open')) {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) { e.preventDefault(); open(); }
      else if (e.key === '/' && !/^(input|textarea|select)$/i.test(e.target.tagName || '') && !e.target.isContentEditable) { e.preventDefault(); open(); }
      return;
    }
    if (e.key === 'Escape') { close(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); if (current.length) { setActive((active + 1) % current.length); scrollActive(); } }
    else if (e.key === 'ArrowUp') { e.preventDefault(); if (current.length) { setActive((active - 1 + current.length) % current.length); scrollActive(); } }
    else if (e.key === 'Enter') { e.preventDefault(); go(); }
  });

  function makeBtn() {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'nav-search';
    btn.setAttribute('data-search-open', '');
    btn.setAttribute('aria-label', 'Search the site');
    btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><line x1="20" y1="20" x2="16.65" y2="16.65"></line></svg><span>Search</span><kbd>/</kbd>';
    btn.addEventListener('click', function () { open(); });
    return btn;
  }

  function markActiveNav() {
    var path = location.pathname.replace(/index\.html$/, '') || '/';
    var best = null, bestLen = -1;
    Array.prototype.forEach.call(document.querySelectorAll('.site-nav a'), function (a) {
      var hp = (a.getAttribute('href') || '').replace(/index\.html$/, '');
      if (hp === '/') { if (path === '/') a.classList.add('active'); return; }
      if (path === hp || path.indexOf(hp) === 0) { if (hp.length > bestLen) { best = a; bestLen = hp.length; } }
    });
    if (best) best.classList.add('active');
  }

  function init() {
    document.body.appendChild(ov);

    /* Search triggers declared in the header markup take priority. */
    var nav = document.querySelector('.site-header nav') || document.querySelector('header nav');
    var host = nav || document.querySelector('.site-header .header-inner') || document.querySelector('header .header-inner') || document.querySelector('.site-header') || document.querySelector('header');
    var triggers = Array.prototype.slice.call(document.querySelectorAll('[data-search-open]'));

    if (!triggers.length && host) {
      var existing = host.querySelector('.nav-search, .nav-search-btn');
      if (existing) {
        existing.setAttribute('data-search-open', '');
        triggers = [existing];
      } else {
        var fallback = makeBtn();
        host.appendChild(fallback);
        triggers = [fallback];
      }
    }

    if (triggers.some(function (el) { return el.classList && el.classList.contains('nav-search'); })) {
      Array.prototype.forEach.call(document.querySelectorAll('.site-header .nav-search-btn, header .nav-search-btn'), function (el) {
        if (el.parentNode) el.parentNode.removeChild(el);
      });
    }

    triggers.forEach(function (el) {
      el.addEventListener('click', function (e) { e.preventDefault(); open(el.getAttribute('data-search-prefill') || ''); });
    });

    /* Mobile menu toggle. */
    var toggle = document.querySelector('.nav-toggle');
    var snav = document.getElementById('site-nav');
    if (toggle && snav) {
      toggle.addEventListener('click', function () {
        var on = snav.classList.toggle('open');
        toggle.setAttribute('aria-expanded', on ? 'true' : 'false');
      });
      Array.prototype.forEach.call(snav.querySelectorAll('a'), function (a) {
        a.addEventListener('click', function () { snav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); });
      });
    }

    markActiveNav();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

/* ── Ad-slot reveal ─────────────────────────────────────────────────
   .ad-slot is display:none by default (v2.css) so unapproved/unfilled
   AdSense units never render as empty dashed "Advertisement" boxes.
   Reveal a slot only when its <ins.adsbygoogle> actually fills. */
(function () {
  'use strict';
  function revealFilledAds() {
    try {
      var units = document.querySelectorAll('ins.adsbygoogle');
      Array.prototype.forEach.call(units, function (ins) {
        var filled = ins.getAttribute('data-ad-status') === 'filled' || !!ins.querySelector('iframe');
        if (!filled) return;
        var slot = ins.closest ? ins.closest('.ad-slot') : null;
        if (slot) slot.classList.add('ad-filled');
      });
    } catch (e) { /* ads must never break the page */ }
  }
  function schedule() { revealFilledAds(); setTimeout(revealFilledAds, 3500); }
  if (document.readyState === 'complete') schedule();
  else window.addEventListener('load', schedule);
})();

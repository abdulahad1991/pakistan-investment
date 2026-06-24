/* Lightweight social share bar. Self-injects after the byline (or first H1)
   using the page's canonical URL + title. No dependencies, no tracking beyond
   an optional GA4 event. WhatsApp is first - it's how most of Pakistan shares. */
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    var canon = document.querySelector('link[rel="canonical"]');
    var url = (canon && canon.href) || location.href;
    var ogt = document.querySelector('meta[property="og:title"]');
    var title = (ogt && ogt.content) || document.title;
    var anchor = document.querySelector('.container .byline') || document.querySelector('.container h1');
    if (!anchor) return;

    var u = encodeURIComponent(url), t = encodeURIComponent(title);
    var links = [
      { k: 'WhatsApp', c: '#25D366', h: 'https://wa.me/?text=' + t + '%20' + u },
      { k: 'Facebook', c: '#1877F2', h: 'https://www.facebook.com/sharer/sharer.php?u=' + u },
      { k: 'LinkedIn', c: '#0A66C2', h: 'https://www.linkedin.com/sharing/share-offsite/?url=' + u },
      { k: 'X', c: '#111111', h: 'https://twitter.com/intent/tweet?text=' + t + '&url=' + u }
    ];

    if (!document.getElementById('share-bar-css')) {
      var st = document.createElement('style');
      st.id = 'share-bar-css';
      st.textContent =
        '.share-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin:0 0 22px}' +
        '.share-bar .sb-lbl{font-family:"IBM Plex Mono",monospace;font-size:.64rem;letter-spacing:.08em;text-transform:uppercase;color:#8a887d;margin-right:2px}' +
        '.share-bar a,.share-bar button{display:inline-flex;align-items:center;gap:6px;font-family:"IBM Plex Mono",monospace;font-size:.72rem;font-weight:600;color:#fff;border:0;border-radius:8px;padding:7px 12px;cursor:pointer;text-decoration:none;line-height:1}' +
        '.share-bar a:hover,.share-bar button:hover{opacity:.9}' +
        '.share-bar .sb-copy{background:#B98A2F}';
      document.head.appendChild(st);
    }

    var bar = document.createElement('div');
    bar.className = 'share-bar';
    bar.innerHTML = '<span class="sb-lbl">Share</span>' +
      links.map(function (l) { return '<a href="' + l.h + '" target="_blank" rel="noopener" style="background:' + l.c + '" data-net="' + l.k + '">' + l.k + '</a>'; }).join('') +
      '<button type="button" class="sb-copy">Copy link</button>';
    anchor.parentNode.insertBefore(bar, anchor.nextSibling);

    bar.addEventListener('click', function (e) {
      var a = e.target.closest('a'); if (a && window.gtag) try { gtag('event', 'share', { method: a.getAttribute('data-net') }); } catch (x) {}
    });
    var copyBtn = bar.querySelector('.sb-copy');
    copyBtn.addEventListener('click', function () {
      var done = function () { copyBtn.textContent = 'Copied!'; setTimeout(function () { copyBtn.textContent = 'Copy link'; }, 1800); if (window.gtag) try { gtag('event', 'share', { method: 'copy' }); } catch (x) {} };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, done); else done();
    });
  });
})();

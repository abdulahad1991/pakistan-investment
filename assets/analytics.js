/* Site-wide GA4 engagement tracking (loaded on every page).
   Sends custom events to the existing gtag (G-4T2H0KH9H7) so we can mark
   them as Key Events in GA4 and see what visitors actually DO — not just
   that they showed up. Calculator-specific events live in app.js. */
(function () {
  "use strict";

  // gtag is defined in the <head> on every page; fall back to a no-op so a
  // blocked analytics script never throws.
  function track(name, params) {
    try {
      if (typeof window.gtag === "function") window.gtag("event", name, params || {});
    } catch (e) { /* never break the page for analytics */ }
  }
  // Expose for app.js and inline handlers.
  window.pkTrack = track;

  var HOST = location.hostname.replace(/^www\./, "");

  function isExternal(a) {
    if (!a || !a.href) return false;
    var proto = (a.protocol || "").toLowerCase();
    if (proto !== "http:" && proto !== "https:") return false;       // skip mailto:, tel:, #, javascript:
    return a.hostname.replace(/^www\./, "") !== HOST;
  }

  /* ── Outbound + CTA clicks ──────────────────────────────────
     Delegated so it covers links rendered later by app.js (broker /
     fund / CDNS buttons on the calculator result pages). */
  document.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a[href]") : null;
    if (!a || !isExternal(a)) return;

    var domain = a.hostname.replace(/^www\./, "");
    var text = (a.textContent || "").trim().replace(/\s+/g, " ").slice(0, 80);

    track("outbound_click", {
      link_domain: domain,
      link_url: a.href,
      link_text: text
    });

    // .btn-cta = the money buttons (open broker / CDNS / fund account).
    // Fire a second, higher-intent event so it can be its own Key Event.
    if (a.classList && a.classList.contains("btn-cta")) {
      track("cta_click", { cta_domain: domain, cta_text: text });
    }
  }, true);

  /* ── Scroll depth milestones ────────────────────────────────
     GA4's default `scroll` event only fires once at 90%. These give
     25/50/75/100 granularity to gauge how far articles are read. */
  var marks = [25, 50, 75, 100];
  var fired = {};
  var ticking = false;

  function checkDepth() {
    ticking = false;
    var doc = document.documentElement;
    var scrollable = doc.scrollHeight - window.innerHeight;
    if (scrollable <= 0) return;                       // page shorter than viewport
    var pct = Math.min(100, Math.round(((window.scrollY || doc.scrollTop) / scrollable) * 100));
    for (var i = 0; i < marks.length; i++) {
      var m = marks[i];
      if (pct >= m && !fired[m]) {
        fired[m] = true;
        track("scroll_depth", { percent: m, page_path: location.pathname });
      }
    }
  }

  window.addEventListener("scroll", function () {
    if (!ticking) { ticking = true; window.requestAnimationFrame(checkDepth); }
  }, { passive: true });
})();

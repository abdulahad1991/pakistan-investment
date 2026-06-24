/* FAQ hub - live search + topic filter over server-rendered FAQ accordions.
   Filters the existing DOM (.faq-item with data-topic) so all content stays
   crawlable without JS. */
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    var list = document.getElementById('faq-list');
    if (!list) return;
    var chipsEl = document.getElementById('faq-chips');
    var input = document.getElementById('faq-search');
    var countEl = document.getElementById('faq-count');
    var emptyEl = document.getElementById('faq-empty');
    var items = Array.prototype.slice.call(list.querySelectorAll('.faq-item'));

    var topics = [];
    items.forEach(function (it) {
      var t = it.getAttribute('data-topic');
      if (t && topics.indexOf(t) < 0) topics.push(t);
    });
    topics.sort();
    var active = 'All', query = '';

    function apply() {
      var q = query.trim().toLowerCase(), n = 0;
      items.forEach(function (it) {
        var okT = active === 'All' || it.getAttribute('data-topic') === active;
        var okQ = !q || it.textContent.toLowerCase().indexOf(q) >= 0;
        var show = okT && okQ;
        it.style.display = show ? '' : 'none';
        if (show) n++;
      });
      if (countEl) countEl.textContent = n + (n === 1 ? ' question' : ' questions');
      if (emptyEl) emptyEl.style.display = n ? 'none' : '';
    }

    function chips() {
      if (!chipsEl) return;
      chipsEl.innerHTML = ['All'].concat(topics).map(function (t) {
        var on = t === active;
        return '<button type="button" class="faq-chip' + (on ? ' faq-chip-on' : '') + '" data-topic="' + t + '" aria-pressed="' + on + '">' + t + '</button>';
      }).join('');
      Array.prototype.forEach.call(chipsEl.querySelectorAll('.faq-chip'), function (b) {
        b.addEventListener('click', function () { active = b.getAttribute('data-topic'); chips(); apply(); });
      });
    }

    if (input) input.addEventListener('input', function () { query = input.value; apply(); });
    chips();
    apply();

    if (location.hash && location.hash.indexOf('#faq-') === 0) {
      var el = document.getElementById(location.hash.slice(1));
      if (el) { el.open = true; el.scrollIntoView(); }
    }
  });
})();

/* Daily-brief video: play only when scrolled into view, with sound.
   Browsers block unmuted autoplay until the user has interacted with the page,
   so we unmute once any real gesture (pointer/key/touch) has happened; until
   then we fall back to muted playback. Pauses when scrolled out of view. */
(function () {
  'use strict';
  var v = document.getElementById('brief-video');
  if (!v) return;
  var gestured = false, inView = false;

  // Play a touch slower than rendered - easier for viewers to follow.
  var RATE = 0.8;
  function applyRate() { try { v.defaultPlaybackRate = RATE; v.playbackRate = RATE; } catch (e) {} }
  applyRate();
  v.addEventListener('loadedmetadata', applyRate);
  v.addEventListener('play', applyRate);   // some browsers reset rate on play

  // Cross-browser fullscreen (Chrome/Firefox/Edge, desktop Safari, iOS Safari).
  function goFull() {
    if (v.requestFullscreen) v.requestFullscreen();
    else if (v.webkitRequestFullscreen) v.webkitRequestFullscreen();   // older desktop Safari
    else if (v.webkitEnterFullscreen) v.webkitEnterFullscreen();       // iOS Safari (video only)
    else if (v.msRequestFullscreen) v.msRequestFullscreen();
  }
  var fsBtn = document.getElementById('brief-fs');
  if (fsBtn) fsBtn.addEventListener('click', function (e) { e.preventDefault(); goFull(); });

  function tryPlay() {
    if (!inView) return;
    if (gestured) v.muted = false;
    var p = v.play();
    if (p && p.catch) p.catch(function () { v.muted = true; v.play().catch(function () {}); });
    applyRate();
  }
  function onGesture() { gestured = true; tryPlay(); }
  ['pointerdown', 'keydown', 'touchstart'].forEach(function (e) {
    document.addEventListener(e, onGesture, { passive: true });
  });

  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        inView = en.isIntersecting && en.intersectionRatio >= 0.6;
        if (inView) tryPlay(); else v.pause();
      });
    }, { threshold: [0, 0.6] });
    io.observe(v);
  }
})();

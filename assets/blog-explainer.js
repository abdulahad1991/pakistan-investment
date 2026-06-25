/* Interactive 60-second Urdu blog explainer player.
   Drop <div class="blog-explainer" data-explainer="<slug>"></div> in a page and
   load this file. Reads /assets/blog-audio/<slug>.json (chapters+timings) and
   /assets/blog-audio/<slug>.mp3. No dependency. Self-injects its CSS. */
(function () {
  "use strict";
  var mounts = document.querySelectorAll(".blog-explainer[data-explainer]");
  if (!mounts.length) return;

  // ── load a proper Urdu (Nastaliq) webfont once ────────────
  var fl = document.createElement("link");
  fl.rel = "stylesheet";
  fl.href = "https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@500;600&display=swap";
  document.head.appendChild(fl);

  // ── inject CSS once ───────────────────────────────────────
  var css = ""
    + ".bx{border:1px solid var(--line);border-top:3px solid var(--acid);background:var(--green-d);color:#fff;margin:0 0 28px;overflow:hidden}"
    + ".bx-head{display:flex;justify-content:space-between;align-items:center;padding:12px 18px;border-bottom:1px solid rgba(255,255,255,.12)}"
    + ".bx-k{font-family:var(--display);font-size:.66rem;font-weight:700;letter-spacing:.14em;color:var(--acid);text-transform:uppercase}"
    + ".bx-lang{font-family:var(--display);font-size:.7rem;font-weight:600;color:rgba(204,223,211,.85)}"
    + ".bx-stage{padding:26px 22px;min-height:132px;display:flex;flex-direction:column;justify-content:center;text-align:center}"
    + ".bx-cap{font-family:'Noto Nastaliq Urdu','Jameel Noori Nastaleeq',var(--body);font-size:1.4rem;line-height:2.1;font-weight:600;color:#fff;opacity:0;transform:translateY(6px);transition:opacity .35s ease,transform .35s ease}"
    + ".bx-cap.on{opacity:1;transform:none}"
    + ".bx-sub{font-family:var(--body);font-size:.82rem;color:rgba(204,223,211,.7);margin-top:10px;min-height:1em}"
    + ".bx-bar{position:relative;height:6px;background:rgba(255,255,255,.14);cursor:pointer}"
    + ".bx-fill{position:absolute;left:0;top:0;height:100%;width:0;background:var(--acid);transition:width .12s linear}"
    + ".bx-tick{position:absolute;top:0;width:2px;height:100%;background:var(--green-d)}"
    + ".bx-ctrl{display:flex;align-items:center;gap:12px;padding:12px 16px;flex-wrap:wrap}"
    + ".bx-play{flex:none;width:42px;height:42px;border:none;border-radius:50%;background:var(--acid);color:var(--green-d);font-size:1.05rem;cursor:pointer;display:flex;align-items:center;justify-content:center;font-weight:800}"
    + ".bx-play:hover{filter:brightness(1.08)}"
    + ".bx-time{font-family:var(--mono);font-size:.82rem;color:rgba(204,223,211,.85);min-width:84px}"
    + ".bx-chips{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}"
    + ".bx-chip{font-family:var(--display);font-size:.74rem;font-weight:600;color:rgba(255,255,255,.8);background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);padding:4px 10px;cursor:pointer;direction:rtl}"
    + ".bx-chip:hover{background:rgba(255,255,255,.16)}"
    + ".bx-chip.on{background:var(--acid);color:var(--green-d);border-color:var(--acid)}"
    + "@media(max-width:560px){.bx-cap{font-size:1.25rem}.bx-chips{margin-left:0;width:100%}}";
  var st = document.createElement("style"); st.textContent = css; document.head.appendChild(st);

  function fmt(t) { t = Math.max(0, t | 0); return (t / 60 | 0) + ":" + ("0" + (t % 60)).slice(-2); }

  function build(el) {
    var slug = el.getAttribute("data-explainer");
    fetch("/assets/blog-audio/" + slug + ".json")
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (m) { render(el, slug, m); })
      .catch(function () { el.style.display = "none"; });   // no audio yet -> hide silently
  }

  function render(el, slug, m) {
    var ch = m.chapters || [];
    if (!ch.length) { el.style.display = "none"; return; }
    var total = m.total || (ch[ch.length - 1].start + ch[ch.length - 1].dur);

    var wrap = document.createElement("div");
    wrap.className = "bx";
    wrap.innerHTML =
      '<div class="bx-head"><span class="bx-k">&#9654; 60-second explainer</span>'
      + '<span class="bx-lang">&#1575;&#1585;&#1583;&#1608; &middot; Urdu voice</span></div>'
      + '<div class="bx-stage"><div class="bx-cap" dir="rtl"></div><div class="bx-sub"></div></div>'
      + '<div class="bx-bar"><div class="bx-fill"></div></div>'
      + '<div class="bx-ctrl"><button class="bx-play" aria-label="Play">&#9654;</button>'
      + '<span class="bx-time">0:00 / ' + fmt(total) + '</span>'
      + '<div class="bx-chips"></div></div>';
    el.innerHTML = ""; el.appendChild(wrap);

    var audio = new Audio("/assets/blog-audio/" + slug + ".mp3");
    audio.preload = "metadata";
    var cap = wrap.querySelector(".bx-cap"), sub = wrap.querySelector(".bx-sub");
    var fill = wrap.querySelector(".bx-fill"), bar = wrap.querySelector(".bx-bar");
    var play = wrap.querySelector(".bx-play"), time = wrap.querySelector(".bx-time");
    var chips = wrap.querySelector(".bx-chips");
    var cur = -1;

    ch.forEach(function (c, i) {
      var tick = document.createElement("div");
      tick.className = "bx-tick"; tick.style.left = (c.start / total * 100) + "%";
      bar.appendChild(tick);
      var b = document.createElement("button");
      b.className = "bx-chip"; b.textContent = c.label || (i + 1);
      b.addEventListener("click", function () { audio.currentTime = c.start + 0.01; audio.play(); });
      chips.appendChild(b);
    });
    var chipEls = chips.querySelectorAll(".bx-chip");

    function setChapter(i) {
      if (i === cur) return; cur = i;
      var c = ch[i];
      cap.classList.remove("on");
      setTimeout(function () { cap.textContent = c.ur; sub.textContent = c.en; cap.classList.add("on"); }, 60);
      for (var k = 0; k < chipEls.length; k++) chipEls[k].classList.toggle("on", k === i);
    }
    function chapterAt(t) {
      var idx = 0;
      for (var i = 0; i < ch.length; i++) if (t >= ch[i].start - 0.05) idx = i;
      return idx;
    }
    setChapter(0);

    audio.addEventListener("timeupdate", function () {
      fill.style.width = (audio.currentTime / total * 100) + "%";
      time.textContent = fmt(audio.currentTime) + " / " + fmt(total);
      setChapter(chapterAt(audio.currentTime));
    });
    audio.addEventListener("play", function () { play.innerHTML = "&#10073;&#10073;"; play.setAttribute("aria-label", "Pause"); });
    audio.addEventListener("pause", function () { play.innerHTML = "&#9654;"; play.setAttribute("aria-label", "Play"); });
    audio.addEventListener("ended", function () { play.innerHTML = "&#9654;"; fill.style.width = "100%"; });
    play.addEventListener("click", function () { audio.paused ? audio.play() : audio.pause(); });
    bar.addEventListener("click", function (e) {
      var r = bar.getBoundingClientRect();
      audio.currentTime = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * total;
    });
    if (window.pkTrack) play.addEventListener("click", function () { window.pkTrack("explainer_play", { slug: slug }); }, { once: true });
  }

  mounts.forEach(build);
})();

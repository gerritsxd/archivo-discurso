// ¿Quién lo dijo? Daily game: 5 quotes, guess the candidate.
// Talks to api/daily and api/guess. Progress and stats live in localStorage (optional).
// Quote text comes from transcripts: inserted with textContent only.
(function () {
  "use strict";
  function tfetch(url, opts, ms) {
    // fetch with a timeout, so a hanging API falls back instead of spinning
    opts = opts || {};
    if (typeof AbortController === "function") {
      var ac = new AbortController();
      opts.signal = ac.signal;
      setTimeout(function () { ac.abort(); }, ms || 6000);
    }
    return fetch(url, opts);
  }
  var KEY = "quienlodijo:v1";
  var SHARE_URL = document.body.getAttribute("data-share-url") || "";
  var MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var root = document.getElementById("game");
  var puzzle = null, state = null, busy = false, timer = null;

  // ---------- storage (never required)
  function load() {
    try { var s = JSON.parse(localStorage.getItem(KEY) || "{}"); return s && typeof s === "object" ? s : {}; }
    catch (e) { return {}; }
  }
  function save(all) { try { localStorage.setItem(KEY, JSON.stringify(all)); } catch (e) { /* private mode */ } }
  function dayState(date) {
    var all = load();
    all.days = all.days || {};
    var d = all.days[date];
    if (!d || !Array.isArray(d.answers)) d = { answers: [] };
    return d;
  }
  function storeDay(date, d) {
    var all = load();
    all.days = all.days || {};
    all.days[date] = d;
    save(all);
  }
  function stats() {
    var days = load().days || {}, done = [], right = 0, total = 0;
    Object.keys(days).forEach(function (k) {
      var d = days[k];
      if (d && d.done && Array.isArray(d.answers)) {
        done.push(k);
        d.answers.forEach(function (a) { total++; if (a.correct) right++; });
      }
    });
    done.sort();
    // streak = consecutive days played, ending today (or yesterday if today isn't finished)
    var best = 0, run = 0, prev = null;
    done.forEach(function (k) {
      run = prev && dayDiff(prev, k) === 1 ? run + 1 : 1;
      best = Math.max(best, run);
      prev = k;
    });
    var cur = 0;
    if (done.length) {
      var last = done[done.length - 1], gap = dayDiff(last, puzzle.date);
      if (gap <= 1) cur = run;
    }
    return { played: done.length, pct: total ? Math.round(100 * right / total) : 0, cur: cur, best: best };
  }
  function dayDiff(a, b) { return Math.round((Date.parse(b + "T12:00:00Z") - Date.parse(a + "T12:00:00Z")) / 864e5); }

  // ---------- helpers
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function clock(t) {
    t = Math.max(0, Math.floor(t || 0));
    var h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = t % 60;
    var p = function (n) { return (n < 10 ? "0" : "") + n; };
    return h ? h + ":" + p(m) + ":" + p(s) : m + ":" + p(s);
  }
  function dateEs(d) {
    var p = (d || "").split("-");
    if (p.length !== 3) return d || "";
    return parseInt(p[2], 10) + " de " + MONTHS[parseInt(p[1], 10) - 1] + " de " + p[0];
  }
  function safeHref(u) { return /^https?:\/\//i.test(u || "") ? u : ""; }
  function squares(answers) { return answers.map(function (a) { return a.correct ? "■" : "□"; }).join(""); }
  function score(answers) { return answers.filter(function (a) { return a.correct; }).length; }
  function message(text, retry) {
    root.textContent = "";
    var box = el("div", "g-msg");
    box.appendChild(el("p", null, text));
    if (retry) {
      var b = el("button", "g-next", "Reintentar");
      b.type = "button";
      b.addEventListener("click", start);
      box.appendChild(b);
    }
    root.appendChild(box);
    root.setAttribute("aria-busy", "false");
  }
  function cand(id) {
    for (var i = 0; i < puzzle.candidates.length; i++) if (puzzle.candidates[i].id === id) return puzzle.candidates[i];
    return { id: id, name: id, role: "" };
  }

  // ---------- flow
  function start() {
    root.setAttribute("aria-busy", "true");
    root.textContent = "";
    root.appendChild(el("p", "g-loading", "Cargando las frases de hoy…"));
    tfetch("api/daily", { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        if (!d || d.error || !Array.isArray(d.rounds) || !Array.isArray(d.candidates)) throw new Error("bad");
        puzzle = d;
        var num = document.getElementById("g-num");
        if (num) num.textContent = "nº " + d.number + " · " + dateEs(d.date);
        if (!d.rounds.length) return message("Hoy todavía no hay frases suficientes para el juego. Vuelve más tarde.");
        state = dayState(d.date);
        if (state.done || state.answers.length >= d.rounds.length) { state.done = true; return finish(); }
        state.revealed = false;
        render();
      })
      .catch(function () {
        message("El juego no está disponible ahora mismo. Vuelve a intentarlo en unos minutos.", true);
      });
  }

  function current() { return state.answers.length - (state.revealed ? 1 : 0); }

  function render() {
    root.setAttribute("aria-busy", "false");
    root.textContent = "";
    var n = current(), round = puzzle.rounds[n], total = puzzle.rounds.length;
    var head = el("div", "g-head");
    head.appendChild(el("p", "g-count", "Frase " + (n + 1) + " de " + total));
    var pips = el("p", "g-pips");
    pips.setAttribute("aria-hidden", "true");
    for (var i = 0; i < total; i++) {
      var a = state.answers[i];
      pips.appendChild(el("span", "sq" + (a ? (a.correct ? " ok" : "") : (i === n ? " now" : " todo"))));
    }
    head.appendChild(pips);
    root.appendChild(head);

    var q = el("blockquote", "g-quote", round.text);
    q.id = "g-quote";
    root.appendChild(q);

    var ans = state.revealed ? state.answers[n] : null;
    var grid = el("div", "g-choices");
    grid.setAttribute("role", "group");
    grid.setAttribute("aria-label", "¿Quién lo dijo?");
    puzzle.candidates.forEach(function (c, i) {
      var b = el("button", "g-choice");
      b.type = "button";
      b.setAttribute("data-id", c.id);
      b.appendChild(el("span", "k", String(i + 1)));
      var nm = el("span", "nm", c.name);
      b.appendChild(nm);
      if (c.role) b.appendChild(el("span", "rl", c.role));
      if (ans) {
        b.disabled = true;
        if (c.id === ans.answer.id) { b.classList.add("is-answer"); b.setAttribute("aria-label", c.name + ": lo dijo"); }
        else if (c.id === ans.guess) { b.classList.add("is-wrong"); b.setAttribute("aria-label", c.name + ": tu respuesta, incorrecta"); }
      } else {
        b.addEventListener("click", function () { guess(c.id); });
      }
      grid.appendChild(b);
    });
    root.appendChild(grid);

    var live = el("div", "g-reveal");
    live.setAttribute("aria-live", "polite");
    if (ans) {
      live.appendChild(el("p", "g-verdict", ans.correct ? "Correcto." : "No."));
      var who = el("p", "g-who");
      who.appendChild(document.createTextNode("Lo dijo "));
      who.appendChild(el("strong", null, ans.answer.name));
      if (ans.answer.role) who.appendChild(document.createTextNode(" (" + ans.answer.role + ")"));
      who.appendChild(document.createTextNode("."));
      live.appendChild(who);
      live.appendChild(sourceLine(ans.source));
      var next = el("button", "g-next", n + 1 < total ? "Siguiente frase" : "Ver el resultado");
      next.type = "button";
      next.id = "g-next";
      next.addEventListener("click", advance);
      live.appendChild(next);
    } else {
      live.appendChild(el("p", "g-hint", "Elige un nombre. En un teclado, pulsa del 1 al " + puzzle.candidates.length + "."));
    }
    root.appendChild(live);
    if (ans) { var nb = document.getElementById("g-next"); if (nb) nb.focus({ preventScroll: true }); }
  }

  function sourceLine(src) {
    var p = el("p", "g-src");
    src = src || {};
    var bits = [src.outlet, dateEs(src.date)].filter(Boolean).join(" · ");
    p.appendChild(document.createTextNode(bits));
    var href = safeHref(src.link);
    if (href) {
      p.appendChild(document.createTextNode(" · "));
      var a = el("a", null, "Escuchar en la fuente (min " + clock(src.start) + ")");
      a.href = href; a.target = "_blank"; a.rel = "noopener noreferrer";
      p.appendChild(a);
    }
    if (src.item_id && /^[A-Za-z0-9_-]+$/.test(src.item_id)) {
      p.appendChild(document.createTextNode(" · "));
      var t = el("a", null, "transcripción");
      t.href = "a/" + src.item_id + ".html";
      p.appendChild(t);
    }
    return p;
  }

  function guess(id) {
    if (busy || state.revealed) return;
    busy = true;
    var n = state.answers.length;
    var btns = root.querySelectorAll(".g-choice");
    Array.prototype.forEach.call(btns, function (b) { b.disabled = true; if (b.getAttribute("data-id") === id) b.classList.add("is-picked"); });
    tfetch("api/guess", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date: puzzle.date, n: puzzle.rounds[n].n, guess: id })
    }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (res) {
        if (!res || !res.answer) throw new Error("bad");
        state.answers.push({ guess: id, correct: !!res.correct, answer: res.answer, source: res.source || {}, text: puzzle.rounds[n].text });
        state.revealed = true;
        storeDay(puzzle.date, { answers: state.answers, done: false });
        busy = false;
        render();
      })
      .catch(function () {
        busy = false;
        Array.prototype.forEach.call(btns, function (b) { b.disabled = false; b.classList.remove("is-picked"); });
        var live = root.querySelector(".g-reveal");
        if (live) { live.textContent = ""; live.appendChild(el("p", "g-hint", "No se ha podido comprobar la respuesta. Inténtalo otra vez.")); }
      });
  }

  function advance() {
    state.revealed = false;
    if (state.answers.length >= puzzle.rounds.length) {
      state.done = true;
      storeDay(puzzle.date, { answers: state.answers, done: true });
      return finish();
    }
    render();
    var q = document.getElementById("g-quote");
    if (q) q.scrollIntoView({ block: "nearest" });
  }

  function finish() {
    root.setAttribute("aria-busy", "false");
    root.textContent = "";
    var a = state.answers, total = puzzle.rounds.length;
    var box = el("div", "g-end");
    box.appendChild(el("p", "g-count", "Resultado de hoy"));
    box.appendChild(el("p", "g-score", score(a) + "/" + total));
    var sq = el("p", "g-squares");
    a.forEach(function (x) { sq.appendChild(el("span", "sq" + (x.correct ? " ok" : ""))); });
    sq.setAttribute("aria-label", score(a) + " aciertos de " + total);
    box.appendChild(sq);

    var shareText = "¿Quién lo dijo? #" + puzzle.number + " " + score(a) + "/" + total + " " + squares(a) + (SHARE_URL ? " " + SHARE_URL : "");
    var row = el("div", "g-actions");
    var sb = el("button", "g-next", "Compartir");
    sb.type = "button";
    var note = el("p", "g-copied");
    note.setAttribute("aria-live", "polite");
    sb.addEventListener("click", function () { copy(shareText, note, row); });
    row.appendChild(sb);
    box.appendChild(row);
    box.appendChild(note);

    var st = stats();
    var dl = el("dl", "counts small g-stats");
    [["jugados", st.played], ["% aciertos", st.pct], ["racha", st.cur], ["mejor racha", st.best]].forEach(function (x) {
      var d = el("div");
      d.appendChild(el("dt", null, x[0]));
      d.appendChild(el("dd", null, String(x[1])));
      dl.appendChild(d);
    });
    box.appendChild(dl);
    var cd = el("p", "g-next-day");
    box.appendChild(cd);
    root.appendChild(box);
    tick(cd);

    root.appendChild(el("h2", "sect", "Las frases de hoy"));
    var ol = el("ol", "g-review");
    a.forEach(function (x, i) {
      var li = el("li");
      var mk = el("span", "g-mark");
      mk.appendChild(el("span", "sq" + (x.correct ? " ok" : "")));
      mk.setAttribute("aria-label", x.correct ? "Acierto" : "Fallo");
      li.appendChild(mk);
      var body = el("div");
      body.appendChild(el("blockquote", null, x.text || (puzzle.rounds[i] && puzzle.rounds[i].text) || ""));
      var who = el("p", "g-who");
      who.appendChild(el("strong", null, x.answer.name));
      if (!x.correct) who.appendChild(document.createTextNode(" · respondiste " + cand(x.guess).name));
      body.appendChild(who);
      body.appendChild(sourceLine(x.source));
      li.appendChild(body);
      ol.appendChild(li);
    });
    root.appendChild(ol);
  }

  function tick(node) {
    function upd() {
      var parts = {};
      try {
        new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Madrid", hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })
          .formatToParts(new Date()).forEach(function (p) { parts[p.type] = p.value; });
      } catch (e) { var d = new Date(); parts = { hour: d.getHours(), minute: d.getMinutes(), second: d.getSeconds() }; }
      var secs = 86400 - ((+parts.hour % 24) * 3600 + (+parts.minute) * 60 + (+parts.second));
      var h = Math.floor(secs / 3600), m = Math.floor(secs % 3600 / 60), s = secs % 60;
      var p2 = function (n) { return (n < 10 ? "0" : "") + n; };
      node.textContent = "Vuelve mañana: nuevas frases en " + h + ":" + p2(m) + ":" + p2(s) + ".";
    }
    upd();
    if (timer) clearInterval(timer);
    timer = setInterval(upd, 1000);
  }

  function copy(text, note, row) {
    function ok() { note.textContent = "Copiado: " + text; }
    function manual() {
      note.textContent = "Copia este texto:";
      var ta = document.getElementById("g-share-text") || el("textarea", "g-share");
      ta.id = "g-share-text"; ta.readOnly = true; ta.value = text; ta.rows = 2;
      if (!ta.parentNode) note.parentNode.insertBefore(ta, note.nextSibling);
      ta.focus(); ta.select();
    }
    function legacy() {
      try {
        var ta = el("textarea");
        ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select();
        var done = document.execCommand && document.execCommand("copy");
        document.body.removeChild(ta);
        if (done) ok(); else manual();
      } catch (e) { manual(); }
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(ok, legacy);
    else legacy();
  }

  document.addEventListener("keydown", function (e) {
    if (!puzzle || !state || state.done || e.altKey || e.ctrlKey || e.metaKey) return;
    var tag = (e.target && e.target.tagName) || "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (!state.revealed && /^[1-9]$/.test(e.key)) {
      var c = puzzle.candidates[parseInt(e.key, 10) - 1];
      if (c) { e.preventDefault(); guess(c.id); }
    } else if (state.revealed && (e.key === "Enter" || e.key === " ") && tag !== "BUTTON" && tag !== "A") {
      e.preventDefault(); advance();
    }
  });

  start();
})();

// Inicio: refresh counts and candidate figures from api/stats; the static numbers stay if the API is down.
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
  function set(id, v) { var e = document.getElementById(id); if (e) e.textContent = v; }
  function num(n) { return Number(n || 0).toLocaleString("es-ES"); }
  function dur(min) {
    min = Number(min || 0);
    if (min < 60) return Math.round(min) + " min";
    return (min / 60).toLocaleString("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " h";
  }
  tfetch("api/stats", { cache: "no-store" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (s) {
      if (!s || typeof s.items !== "number") return;
      set("n-items", num(s.items));
      set("l-items", s.items === 1 ? "aparición" : "apariciones");
      set("n-hours", Number(s.hours || 0).toLocaleString("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 }));
      set("n-quotes", num(s.quotes));
      var per = s.per_person || {};
      Array.prototype.forEach.call(document.querySelectorAll("[data-person]"), function (card) {
        var p = per[card.getAttribute("data-person")] || { items: 0, minutes: 0 };
        var t = card.querySelector(".f-time"), i = card.querySelector(".f-items"), l = card.querySelector(".f-items-l");
        if (t) t.textContent = dur(p.minutes);
        if (i) i.textContent = num(p.items);
        if (l) l.textContent = p.items === 1 ? "aparición" : "apariciones";
      });
    })
    .catch(function () { /* keep the static figures */ });

  // Analysis: counts per type, a line per candidate card, one featured possible contradiction
  var MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  function dateEs(d) { var p = (d || "").split("-"); return p.length === 3 ? (+p[2]) + " de " + MONTHS[+p[1] - 1] : d; }
  function j(url) { return tfetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }); }
  Promise.all([j("api/analysis"), j("api/tone").catch(function () { return {}; }),
               j("api/claims?insult=1&limit=1")]).then(function (res) {
    var a = res[0], tone = (res[1] && res[1].per_person) || {}, tot = {};
    Object.keys(a.per_person || {}).forEach(function (pid) {
      var t = a.per_person[pid].types || {};
      Object.keys(t).forEach(function (k) { tot[k] = (tot[k] || 0) + t[k]; });
    });
    ["promesa", "dato", "ataque"].forEach(function (k) { set("an-" + k, num(tot[k])); });
    set("an-insulto", num(res[2].total));
    set("an-contradiccion", num(a.contradictions));
    Array.prototype.forEach.call(document.querySelectorAll("[data-person]"), function (card) {
      var pid = card.getAttribute("data-person"), p = (a.per_person || {})[pid], line = card.querySelector(".f-an");
      if (!p || !line) return;
      var t = p.types || {}, parts = [num(t.promesa) + " promesas", num(t.ataque) + " ataques", num(p.insults) + " descalificaciones"];
      if (tone[pid]) parts.push("tono " + tone[pid].tone.toLocaleString("es-ES"));
      line.textContent = "";
      var link = document.createElement("a");
      link.href = "analisis.html?c=" + encodeURIComponent(pid) + "#promesa";
      link.textContent = parts.join(" · ");
      line.appendChild(link);
      line.hidden = false;
    });
  }).catch(function () { /* analysis not available: tiles keep their dash */ });
  j("api/contradictions").then(function (d) {
    var r = d.results || [];
    if (!r.length) return;
    var x = r[Math.floor(Math.random() * r.length)];
    var names = {};
    Array.prototype.forEach.call(document.querySelectorAll("[data-person] h3 a"), function (e) {
      names[e.closest("[data-person]").getAttribute("data-person")] = e.textContent;
    });
    set("an-f-who", (names[x.person] || x.person) + " · " + x.topic + " · " +
        (x.kind === "cifras" ? "cifras que no cuadran" : "posturas opuestas"));
    set("an-f-exp", x.explanation);
    set("an-f-a", x.a.quote); set("an-f-am", dateEs(x.a.date) + " · " + x.a.outlet);
    set("an-f-b", x.b.quote); set("an-f-bm", dateEs(x.b.date) + " · " + x.b.outlet);
    [["an-f-am", x.a], ["an-f-bm", x.b]].forEach(function (m) {
      if (!m[1].link) return;
      var e = document.getElementById(m[0]), l = document.createElement("a");
      l.href = m[1].link; l.rel = "noopener noreferrer"; l.target = "_blank"; l.textContent = "fuente";
      e.appendChild(document.createTextNode(" · ")); e.appendChild(l);
    });
    document.getElementById("an-feature").hidden = false;
  }).catch(function () {});

  // Daily game: say if today's puzzle is already done (localStorage is optional)
  try {
    var days = (JSON.parse(localStorage.getItem("quienlodijo:v1") || "{}").days) || {};
    var keys = Object.keys(days).sort(), last = keys[keys.length - 1], d = last && days[last];
    var today = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Madrid" }).format(new Date());
    if (d && d.done && last === today && Array.isArray(d.answers)) {
      var ok = d.answers.filter(function (a) { return a.correct; }).length;
      set("game-status", "Hoy: " + ok + "/" + d.answers.length + ". Vuelve mañana para el siguiente.");
      set("game-cta", "Ver tu resultado");
    }
  } catch (e) { /* no storage */ }
})();

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

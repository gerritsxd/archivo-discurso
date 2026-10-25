// Buscar: search over identified candidates' words.
// Uses the server API (api/search, full-text index) when it answers. Falls back to
// data/index.json + static quote shards when the API is down, or when filtering by
// medium/type (the API has no such filters).
// All transcript text is inserted with textContent, never innerHTML.
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
  var PAGE = 40, API_PAGE = 20;
  var MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var $ = function (id) { return document.getElementById(id); };
  var form = $("sf"), status = $("status"), list = $("results"), moreBtn = $("more");
  var idx = null, idxP = null, cache = {}, hits = [], shown = 0, terms = [], runId = 0;
  var apiDown = false, api = null; // api = {f, offset, total} while paging server results
  var names = {};
  Array.prototype.forEach.call($("c").options, function (o) { if (o.value) names[o.value] = o.textContent; });

  function norm(s) {
    // one output char per input char, so match positions map back onto the original text
    var out = "";
    s = s.normalize("NFC");
    for (var i = 0; i < s.length; i++) {
      var c = s[i].toLowerCase().normalize("NFD")[0] || s[i];
      out += c;
    }
    return out;
  }
  function parseQuery(q) {
    var t = [], re = /"([^"]+)"|(\S+)/g, m;
    while ((m = re.exec(q))) {
      var v = norm((m[1] || m[2]).trim());
      if (v.length) t.push(v);
    }
    return t;
  }
  function clock(t) {
    t = Math.max(0, Math.floor(t || 0));
    var h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = t % 60;
    var p = function (n) { return (n < 10 ? "0" : "") + n; };
    return h ? h + ":" + p(m) + ":" + p(s) : m + ":" + p(s);
  }
  function dateEs(d) {
    var p = (d || "").split("-");
    if (p.length !== 3) return d || "fecha desconocida";
    return parseInt(p[2], 10) + " de " + MONTHS[parseInt(p[1], 10) - 1] + " de " + p[0];
  }
  function atTime(it, t) {
    t = Math.max(0, Math.floor(t));
    if (!it.u) return "";
    if (it.s === "youtube") return it.u + (it.u.indexOf("?") >= 0 ? "&" : "?") + "t=" + t + "s";
    if (it.s === "audio") return it.u.split("#")[0] + "#t=" + t;
    return it.u;
  }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function highlight(node, text) {
    // wrap every term occurrence in <mark>, built from text nodes only
    var n = norm(text), ranges = [];
    terms.forEach(function (t) {
      var from = 0, i;
      while ((i = n.indexOf(t, from)) >= 0) { ranges.push([i, i + t.length]); from = i + t.length; }
    });
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    var pos = 0;
    ranges.forEach(function (r) {
      if (r[0] < pos) { if (r[1] > pos) r[0] = pos; else return; }
      node.appendChild(document.createTextNode(text.slice(pos, r[0])));
      node.appendChild(el("mark", null, text.slice(r[0], r[1])));
      pos = r[1];
    });
    node.appendChild(document.createTextNode(text.slice(pos)));
  }

  function readForm() {
    return {
      q: $("q").value.trim(), c: $("c").value, desde: $("desde").value, hasta: $("hasta").value,
      medio: $("medio").value, tipo: $("tipo").value, todo: $("todo") && $("todo").checked ? "1" : ""
    };
  }
  function writeUrl(f) {
    var p = new URLSearchParams();
    Object.keys(f).forEach(function (k) { if (f[k]) p.set(k, f[k]); });
    var qs = p.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
  }
  function fromUrl() {
    var p = new URLSearchParams(location.search);
    if ($("todo")) $("todo").checked = p.get("todo") === "1";
    ["q", "c", "desde", "hasta", "medio", "tipo"].forEach(function (k) {
      var v = p.get(k);
      if (v != null && $(k)) $(k).value = v;
    });
  }

  function run() {
    var f = readForm();
    writeUrl(f);
    terms = parseQuery(f.q);
    list.textContent = "";
    moreBtn.hidden = true;
    api = null;
    if (!terms.length && !f.c) {
      status.textContent = "Escribe una palabra o elige un candidato.";
      return;
    }
    var my = ++runId;
    status.textContent = "Buscando…";
    if (f.todo && apiDown) { status.textContent = "Buscar en todas las intervenciones necesita el servidor, que no responde ahora."; return; }
    if (f.todo || (!apiDown && !f.medio && !f.tipo)) runApi(f, 0, my);
    else runStatic(f, my);
  }

  // ---------- server search
  function apiUrl(f, offset) {
    var p = new URLSearchParams();
    if (f.q) p.set("q", f.q);
    if (f.c) p.set("person", f.c);
    if (f.todo) p.set("all", "1");
    if (f.desde) p.set("from", f.desde);
    if (f.hasta) p.set("to", f.hasta);
    p.set("limit", API_PAGE);
    p.set("offset", offset);
    return "api/search?" + p.toString();
  }

  function runApi(f, offset, my) {
    tfetch(apiUrl(f, offset), { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        if (my !== runId) return;
        if (!d || typeof d.total !== "number" || !Array.isArray(d.results)) throw new Error("bad");
        api = { f: f, offset: offset + d.results.length, total: d.total };
        if (offset === 0) {
          var n = d.total;
          status.textContent = n === 0 ? "Sin resultados." :
            (n === 1 ? "1 intervención" : n.toLocaleString("es-ES") + " intervenciones") + ", de la más reciente a la más antigua.";
        }
        d.results.forEach(function (r) { list.appendChild(apiCard(r)); });
        moreBtn.hidden = api.offset >= d.total || !d.results.length;
      })
      .catch(function () {
        if (my !== runId) return;
        if (offset > 0) { status.textContent = "No se han podido cargar más resultados."; moreBtn.hidden = false; return; }
        apiDown = true; // static fallback for the rest of this visit
        runStatic(f, my);
      });
  }

  function snippet(text) {
    // long turns: show a window around the first match
    if (text.length <= 480) return { text: text, cut: false };
    var n = norm(text), at = -1;
    // the whole query first, then the longest words ("autónomos" before "que"), like the server's link time
    [terms.join(" ")].concat(terms.slice().sort(function (x, y) { return y.length - x.length; }))
      .some(function (t) { at = n.indexOf(t); return at >= 0; });
    if (at < 0) at = 0;
    var a = Math.max(0, at - 180), b = Math.min(text.length, at + 300);
    if (a > 0) { var sp = text.indexOf(" ", a); if (sp > 0 && sp < at) a = sp + 1; }
    if (b < text.length) { var sp2 = text.lastIndexOf(" ", b); if (sp2 > at) b = sp2; }
    return { text: (a > 0 ? "… " : "") + text.slice(a, b) + (b < text.length ? " …" : ""), cut: a > 0 };
  }

  function apiCard(r) {
    var li = el("li", "res");
    var sn = snippet(String(r.text || ""));
    // what was said just before (usually the interviewer's question), for context
    var pid0 = String(r.person || "");
    if (r.context && r.context.text) {
      // shown as a two-line dialogue: who asked, then who answers
      var ctx = el("div", "ctx");
      ctx.appendChild(el("p", "ctx-who", "Pregunta · " + String(r.context.name || "Entrevistador")));
      ctx.appendChild(el("p", "ctx-q", "«" + String(r.context.text) + "»"));
      li.appendChild(ctx);
      li.appendChild(el("p", "ans-who", "Responde · " + (names[pid0] || pid0)));
    }
    var bq = el("blockquote");
    highlight(bq, sn.text);
    li.appendChild(bq);
    var who = el("p", "who");
    var pid = String(r.person || "");
    var a = el(pid ? "a" : "span", null, names[pid] || String(r.name || "Hablante sin identificar"));
    if (pid) a.href = "c/" + encodeURIComponent(pid) + ".html";
    who.appendChild(a);
    li.appendChild(who);
    li.appendChild(el("p", "src", [dateEs(r.date), r.outlet].filter(Boolean).join(" · ")));
    var links = el("p", "links");
    var href = /^https?:\/\//i.test(r.link || "") ? r.link : "";
    var exact = href && /([?&]|#)t=\d/.test(href);
    if (href) {
      var s = el("a", null, exact
        ? "Escuchar en la fuente (min " + clock(r.start) + ")"
        : "Abrir la fuente y buscar el min " + clock(r.start));
      s.href = href; s.rel = "noopener noreferrer"; s.target = "_blank";
      links.appendChild(s);
    }
    if (/^[A-Za-z0-9_-]+$/.test(r.item_id || "")) {
      var t = el("a", null, "Ver en la transcripción");
      t.href = "a/" + r.item_id + ".html#t-" + Math.floor(r.start || 0);
      links.appendChild(t);
    }
    li.appendChild(links);
    return li;
  }

  // ---------- static fallback
  function ensureIdx() {
    if (!idxP) {
      idxP = fetch("data/index.json", { cache: "no-cache" })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(function (d) { idx = d; return d; });
      idxP.catch(function () { idxP = null; });
    }
    return idxP;
  }
  function getShard(s) {
    if (!cache[s.f]) {
      cache[s.f] = fetch("data/q/" + encodeURIComponent(s.f) + "?v=" + s.v)
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    }
    return cache[s.f];
  }

  function runStatic(f, my) {
    ensureIdx().then(function () {
      var shards = idx.shards.filter(function (s) {
        if (f.c && s.p !== f.c) return false;
        if (f.desde && s.m !== "sin-fecha" && s.m < f.desde.slice(0, 7)) return false;
        if (f.hasta && s.m !== "sin-fecha" && s.m > f.hasta.slice(0, 7)) return false;
        return true;
      });
      return Promise.all(shards.map(function (s) {
        return getShard(s).then(function (rows) { return { p: s.p, rows: rows }; });
      }));
    }).then(function (parts) {
      if (my !== runId) return;
      hits = [];
      parts.forEach(function (part) {
        part.rows.forEach(function (r) {
          var it = idx.items[r[0]];
          if (!it) return;
          if (f.desde && it.d < f.desde) return;
          if (f.hasta && it.d > f.hasta) return;
          if (f.medio && it.m !== f.medio) return;
          if (f.tipo && it.k !== f.tipo) return;
          if (terms.length) {
            var n = r[5] || (r[5] = norm(r[3]));
            for (var i = 0; i < terms.length; i++) if (n.indexOf(terms[i]) < 0) return;
          }
          hits.push({ p: part.p, r: r, it: it });
        });
      });
      hits.sort(function (a, b) {
        if (a.it.d !== b.it.d) return a.it.d < b.it.d ? 1 : -1;
        if (a.r[0] !== b.r[0]) return a.r[0] - b.r[0];
        return a.r[1] - b.r[1];
      });
      shown = 0;
      var n = hits.length;
      status.textContent = n === 0 ? "Sin resultados." :
        (n === 1 ? "1 fragmento" : n.toLocaleString("es-ES") + " fragmentos") + ", del más reciente al más antiguo.";
      more();
    }).catch(function () {
      if (my === runId) status.textContent = "No se han podido cargar los datos. Vuelve a intentarlo.";
    });
  }

  function more() {
    if (api) { moreBtn.hidden = true; return runApi(api.f, api.offset, runId); }
    var end = Math.min(hits.length, shown + PAGE);
    for (; shown < end; shown++) list.appendChild(card(hits[shown]));
    moreBtn.hidden = shown >= hits.length;
  }

  function card(h) {
    var r = h.r, it = h.it, person = idx.people[h.p] || { name: h.p, role: "" };
    var li = el("li", "res");
    var bq = el("blockquote");
    highlight(bq, r[3]);
    li.appendChild(bq);
    var who = el("p", "who");
    var a = el("a", null, person.name);
    a.href = "c/" + encodeURIComponent(h.p) + ".html";
    who.appendChild(a);
    li.appendChild(who);
    var kind = idx.kinds[it.k] || it.k;
    li.appendChild(el("p", "src", dateEs(it.d) + " · " + it.o + " · " + kind));
    var links = el("p", "links");
    var href = atTime(it, r[1]);
    var approx = r[2] ? "≈ " : "";
    if (href) {
      var s = el("a", null, (it.s === "youtube" || it.s === "audio")
        ? "Escuchar en la fuente (" + approx + "min " + clock(r[1]) + ")"
        : "Abrir la fuente y buscar el min " + clock(r[1]));
      s.href = href; s.rel = "noopener noreferrer"; s.target = "_blank";
      links.appendChild(s);
    }
    var t = el("a", null, "Ver en la transcripción");
    t.href = "a/" + encodeURIComponent(it.id) + ".html#t-" + r[4];
    links.appendChild(t);
    li.appendChild(links);
    return li;
  }

  form.addEventListener("submit", function (e) { e.preventDefault(); run(); });
  ["c", "desde", "hasta", "medio", "tipo"].forEach(function (k) { $(k).addEventListener("change", run); });
  moreBtn.addEventListener("click", more);
  fromUrl();
  run();
})();

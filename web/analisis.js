// Análisis: promises, figures, attacks, insults, positions and possible contradictions,
// from the API (api/claims, api/contradictions). All text is inserted with textContent.
(function () {
  "use strict";
  var PAGE = 40;
  var MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var $ = function (id) { return document.getElementById(id); };
  var status = $("status"), list = $("results"), moreBtn = $("more");
  var names = {}, view = "promesa", offset = 0, runId = 0, timer = null;
  Array.prototype.forEach.call($("c").options, function (o) { if (o.value) names[o.value] = o.textContent; });

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function dateEs(d) {
    var p = (d || "").split("-");
    return p.length === 3 ? (+p[2]) + " de " + MONTHS[+p[1] - 1] : d;
  }
  function clock(t) {
    t = Math.floor(t || 0);
    var h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = t % 60;
    return (h ? h + ":" + (m < 10 ? "0" : "") : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }
  function claimBlock(c, showWho) {
    var box = el("div");
    if (showWho !== false) box.appendChild(el("p", "who", names[c.person] || c.person));
    var bq = el("blockquote", "pull", c.quote);
    box.appendChild(bq);
    var tags = [c.topic];
    if (c.target) tags.push("contra: " + c.target);
    if (c.insult && c.insult_words) tags.push("descalificación: «" + c.insult_words + "»");
    box.appendChild(el("p", "src", c.summary));
    box.appendChild(el("p", "src", tags.join(" · ")));
    var links = el("p", "links");
    var src = el("span", null, dateEs(c.date) + " · " + c.outlet + " · ");
    links.appendChild(src);
    var a = el("a", null, "transcripción (" + clock(c.start) + ")");
    a.href = "a/" + encodeURIComponent(c.item_id) + ".html";
    links.appendChild(a);
    if (c.link) {
      var o = el("a", null, "fuente original");
      o.href = c.link; o.rel = "noopener noreferrer"; o.target = "_blank";
      links.appendChild(o);
    }
    box.appendChild(links);
    return box;
  }
  function params() {
    var p = [];
    if ($("c").value) p.push("person=" + encodeURIComponent($("c").value));
    if ($("t").value && view !== "contradiccion") p.push("topic=" + encodeURIComponent($("t").value));
    if ($("q").value.trim() && view !== "contradiccion") p.push("q=" + encodeURIComponent($("q").value.trim()));
    if (view === "insulto") p.push("insult=1");
    else if (view !== "contradiccion") p.push("type=" + view);
    return p.join("&");
  }
  function load(reset) {
    var my = ++runId;
    if (reset) { offset = 0; list.textContent = ""; }
    status.textContent = "Cargando…";
    var url = view === "contradiccion" ? "api/contradictions?" + params()
      : "api/claims?" + params() + "&limit=" + PAGE + "&offset=" + offset;
    fetch(url).then(function (r) { return r.json(); }).then(function (d) {
      if (my !== runId) return;
      (d.results || []).forEach(function (x) {
        var li = el("li", "res");
        if (view === "contradiccion") {
          li.appendChild(el("p", "who", (names[x.person] || x.person) + " · " + x.topic + " · " +
            (x.kind === "cifras" ? "cifras que no cuadran" : "posturas opuestas")));
          li.appendChild(el("p", "ctx-q", x.explanation));
          var a = el("div", "ctx"); a.appendChild(claimBlock(x.a, false)); li.appendChild(a);
          var b = el("div", "ctx"); b.appendChild(claimBlock(x.b, false)); li.appendChild(b);
        } else {
          li.appendChild(claimBlock(x));
        }
        list.appendChild(li);
      });
      offset += (d.results || []).length;
      var total = d.total || 0;
      status.textContent = total ? total.toLocaleString("es-ES") + " resultados" : "Sin resultados.";
      moreBtn.hidden = view === "contradiccion" || offset >= total;
    }).catch(function () {
      if (my === runId) status.textContent = "El servidor no responde. Prueba en un momento.";
    });
  }
  Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (b) {
    b.addEventListener("click", function () {
      Array.prototype.forEach.call(document.querySelectorAll(".tab"), function (x) { x.removeAttribute("aria-pressed"); });
      b.setAttribute("aria-pressed", "true");
      view = b.getAttribute("data-v");
      load(true);
    });
  });
  $("c").addEventListener("change", function () { load(true); });
  $("t").addEventListener("change", function () { load(true); });
  $("q").addEventListener("input", function () { clearTimeout(timer); timer = setTimeout(function () { load(true); }, 350); });
  moreBtn.addEventListener("click", function () { load(false); });
  var h = (location.hash || "").replace("#", "");
  if (h) {
    var b = document.querySelector('.tab[data-v="' + h + '"]');
    if (b) { b.click(); return; }
  }
  load(true);
})();

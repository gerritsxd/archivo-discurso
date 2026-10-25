# M0 tier-1 (already-text) sources: notes

Checked 2026-10-25, covering 5 Oct to 25 Oct 2026. The data is in `text_sources.csv`, with 36 rows, one row per source item. Two rows can describe the same real event. For example, the Moncloa transcript and the Moncloa press note for 5 Oct are the same event, so dedup them into `appearance` later.

| Person | Rows | Where |
|---|---|---|
| Feijóo | 17 | pp.es |
| Abascal | 11 | voxespana.es |
| Sánchez | 6 | Moncloa: 1 full transcript + 5 press notes |
| Ione Belarra (Podemos) | 1 | Congreso, Diputación Permanente 16 Oct |
| Ada Colau (Frente Amplio) | 1 | comuns.cat |
| Irene Montero | 0 | podemos.info blocked, see below |

Leads as the press reports them: Frente Amplio named **Ada Colau** as its candidate for Presidencia on 12 Oct. Emilio Delgado heads the Madrid list. Podemos runs separately; the press expects Montero to lead it, and Belarra is its parliamentary voice. Confirm both against the BOE candidaturas.

---

## 1. La Moncloa

- **Transcripts index:** `https://www.lamoncloa.gob.es/presidente/intervenciones/Paginas/index.aspx`. This is SharePoint. The page shows the current month only (`hdnFilterDate=YYYYMM`). Earlier months are an ASP.NET postback on `ddlMonth`/`ddlYear`, which needs the `__VIEWSTATE`. Each item is an `li.advanced-new` with `a[href]`, `title="D/M/YYYY. Título"` and `span.date`.
- **Detail page:** `/presidente/intervenciones/Paginas/YYYY/<slug>.aspx`. The full text is inside `<main>`, and a PDF sits at `/presidente/intervenciones/Documents/YYYY/<NAME>.pdf`, found by regex on `href=".*\.pdf"`. **Slugs are not reliable dates.** The 5 Oct transcript has slug `20260905-…`, so always take the date from `span.date`.
- **Press notes ("Actividad del presidente"):** `/presidente/actividades/Paginas/index.aspx`. Same layout, 5 items per page. Slug pattern is `DDMMYY-sanchez-….aspx`. These notes carry partial quotes. Mostly they work as **discovery** for appearances whose full transcript comes later or never.
- **RSS:** `https://www.lamoncloa.gob.es/Paginas/rss.aspx` gives "Noticias destacadas del Presidente" (activities), in clean RSS 2.0 with pubDate. **This is the simplest daily trigger.** No feed for intervenciones alone was found.
- **Council press conferences:** `/consejodeministros/ruedas/Paginas/YYYY/YYYYMMDD-transcripcion-rueda-de-prensa*.aspx` holds the portavoz's transcripts. None are listed for October yet.
- **robots/terms:** `robots.txt` is empty, so nothing is disallowed. The Aviso legal allows reuse of government content with attribution (standard for gob.es; still check the text). Crawl politely.
- **Gaps:** Only **one** full transcript exists since 5 Oct, the 5 Oct declaración institucional. The 6 Oct comparecencia after the Consejo de Ministros and the 16 Oct comparecencia after the Consejo Europeo show up only as press notes, with no transcript as of today. Transcripts may lag or may not be published during the caretaker period. Re-check weekly. Sánchez's campaign speech as PSOE leader is never on Moncloa.

## 2. Congreso: Diputación Permanente

- Diputación Permanente sessions are **in the same series as Pleno**: `https://www.congreso.es/public_oficiales/L15/CONG/DS/PL/DSCD-15-PL-{N}.PDF`. The masthead reads "PLENO Y DIPUTACIÓN PERMANENTE"; the DP series `/DS/DP/` returns 404. Numbers are sequential:
  - 210 = Pleno 2 Oct (before our window)
  - **211 = Diputación Permanente núm. 8, 16 Oct**
  - 212 = 404 so far
- **Crawler:** probe N+1 daily (HEAD, 404 until it is published). Parse page 1 with `pdftotext` for "Diputación permanente núm." and "celebrada el …". Speaker turns appear as `La señora BELARRA URTEAGA:` or `El señor …:`, in uppercase surnames, so attribution is easy.
- **Agendas:** `https://www.congreso.es/backoffice_doc/atp/orden_dia/DP_{NNN}_{MMYYYY}.pdf`, for example `DP_008_102026.pdf`. The page `https://www.congreso.es/es/sesiones-de-la-diputacion-permanente` shows the next call ("No hay convocada sesión" today).
- **16 Oct content:** RDL 24/2026 (DANA) and RDL 25/2026 (Oriente Medio). **Belarra** spoke in both debates. Feijóo and Abascal sit on the body but did not speak, and Sánchez and Colau did not take part.
- **robots.txt:** it only disallows a few old BOCG PDFs. DS PDFs are allowed.
- **Gaps:** Press reports conflict on whether the re-approved housing decrees will go to another DP session. If one happens, it will be DSCD-15-PL-212.

## 3. Party press rooms

### pp.es (works well)
- WordPress with an open REST API: `https://www.pp.es/wp-json/wp/v2/posts?after=2026-10-05T00:00:00&per_page=100&page=N&_fields=id,date,link,title,content`. The header `X-WP-Total` gives the total; it was 62 posts since 5 Oct.
- Articles live at `/actualidad/articulos/<slug>/`. The `evento` custom post type (`/wp-json/wp/v2/evento`) looks like the **PP agenda**, which helps discovery. `/feed/` exists too.
- **Rule used:** keep posts whose title starts with "Feijóo"/"Feijoo". That gave 17. The first line of each body names the setting, such as "En la clausura de un mitin en Vigo…" or "En una entrevista en Hoy por hoy…", and kind was taken from that. Posts by Tellado, Muñoz, Gamarra and others can also quote Feijóo; those were not included.
- **robots.txt:** `Disallow:` is empty, so everything is allowed. Mark as `party_edited`.

### voxespana.es (Cloudflare)
- Plain curl and WebFetch get **403 (Cloudflare challenge)**. Inside a real browser session, the same-origin WP REST API works: `/wp-json/wp/v2/posts?after=…&per_page=100&page=N`. That returned 287 posts since 5 Oct.
- Item URL: `https://www.voxespana.es/{category}/{slug}-{YYYYMMDD}`. The category `abascal` holds most items; one was under `actualidad`. Filter on "abascal" in link or title.
- 23 hits: 11 text articles (in the CSV) and 12 `videos-vox-nacional` posts. The video posts have **empty content** (an embed only), so they belong in tier 2 and are not in the CSV.
- **robots.txt:** disallows only `/gestion/`, `/wp-admin/`, `/sn-login/` and a pdf folder. The Cloudflare bot wall is the practical barrier. A VPS crawler will need a headless browser, or another route such as their YouTube/Telegram.

### psoe.es (blocked)
- Imperva/Incapsula answers every URL with a JS challenge page, including `robots.txt`, `/feed/` and `/sitemap.xml`. The page stayed empty in the browser too, so it is probably an interactive challenge. **Nothing collected.** Sánchez is partly covered by Moncloa, but his PSOE rallies are not. Use PSOE YouTube (tier 2) and Google News for discovery.

### podemos.info (blocked)
- A Cloudflare "Un momento…" challenge appears for curl, WebFetch **and** the real browser. It did not clear after waiting, so it looks like an interactive Turnstile/CAPTCHA. It was **not bypassed** (CAPTCHAs are off-limits).
- `site:podemos.info` web search returned nothing. **Montero: 0 rows.** Use Podemos YouTube or Canal Red (tier 2) and Montero's EP pages instead.

### Frente Amplio / Sumar
- **No official Frente Amplio website was found.** sumar.info is an unrelated supplier portal.
- The member parties' WordPress RSS feeds work:
  - `https://comuns.cat/feed/` (in Catalan; 1 Colau item, 17 Oct)
  - `https://masmadrid.org/feed/` (no Colau or Delgado items in the window)
  - `https://movimientosumar.es/feed/` (nothing since 1 Oct)
  - iu.es did not resolve from here.
- Paginate feeds with `/feed/?paged=N`, or use `/wp-json/wp/v2/posts`.

## Problems / caveats
- Party press rooms are `party_edited`: summaries plus selected quotes, never full speeches. They are good for discovery and dating, weak as text.
- Interview items (SER, COPE, esRadio) are only party summaries. The full audio is tier 2.
- Nothing read on any page was addressed to an AI or tried to give instructions.
- PDFs were fetched only to read headers and turns. No media was downloaded.

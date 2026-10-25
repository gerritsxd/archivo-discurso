# M1 results: one Moncloa appearance, end to end

*Run 2026-10-25 on Windows 10, RTX 3060 Ti 8 GB, driver 596.49, Python 3.13.*

## Test item

- **Declaración institucional del presidente del Gobierno**, Palacio de La Moncloa, 5 Oct 2026 (Sánchez calls the 29N election). One speaker, a lectern, no questions.
- Audio: La Moncloa's own HLS stream (480p rendition, audio only kept), 16 kHz mono WAV, **558.95 s** (page says 09:18).
- Official text: the HTML transcript on the intervenciones page ("Transcripción editada por la Secretaría de Estado de Comunicación"). Sources and hashes: `data/raw/2026-10-05-decl-inst-convocatoria/SOURCE.txt`, `SHA256SUMS`.

## Numbers

| Metric | Value |
|---|---|
| Model | faster-whisper 1.2.1, large-v3, CUDA, float16, beam 5, VAD on, `condition_on_previous_text=False` |
| Processing time | 52.9 s (+2.7 s model load, model already cached) |
| **Real-time factor** | **10.6×** (558.95 s audio / 52.85 s) |
| **GPU memory** | **~4.2 GB** for the process (whole-GPU peak 5,626 MiB, 1,394 MiB used before start). float16 fits; int8_float16 not needed |
| **WER vs official** | **11.4 %** (1,214 reference words; 38 substitutions, 12 deletions, 88 insertions) |
| Mean word confidence | 0.989; only 7 of 1,290 words below 0.6 |

**What was compared.** The official text has no Q&A, and neither does this event. I cut the official text from "Queridos ciudadanos" to "Muchas gracias." and compared it with our whole transcript. Normalisation on both sides: lowercase, remove punctuation, keep accents, numbers as-is (here both sides wrote "5%" and "29" as digits, so no number errors).

**I used the HTML, not the PDF.** pypdf splits words in the Moncloa PDF ("sab en", "h ace", "un ilaterales"), which would add errors that aren't ours.

## Reading the 11.4 %

Most of the difference is **the official text being edited**, not transcription errors. The published text is closer to the prepared speech than to what he said. 88 of the 138 errors are insertions: words he says that the official text leaves out (extra "también", "de las españolas", whole clauses). Model confidence on those words is high (mean 0.989), and the inserted phrases are fluent and in context. That is not what Whisper hallucinations over silence look like.

Three examples:

1. **Official edit.** Our transcript opens at 0:11 with *"Buenos días y gracias a los medios de comunicación por atender esta declaración institucional."* The official text starts at "Queridos ciudadanos". The greeting was cut from the official version.
2. **Official edit (rewording).** Official: *"para que construyeran vivienda e invirtieran en sanidad, para que construyeran viviendas"*. Ours (2:02): *"para que invirtieran en sanidad, en educación, para que construyeran vivienda"*. The official sentence even repeats itself, so it looks like it was written from the prepared text, not from the audio. The same happens with *"el triple que en Francia y en Alemania"* vs ours *"el triple que grandes economías europeas como la francesa o la alemana"*.
3. **Probably our error.** Official: *"También ha sido posible gracias a la generosidad…"*. Ours (5:24): *"También ha sido posible a la generosidad…"*. "Gracias" is missing, which makes the sentence ungrammatical. More likely a dropped word than a slip by the speaker. Spelling and format also cost a few points: official "tecno-oligarcas" vs ours "tecnoligarcas" (2 errors), and a typo in the official text, "aqradecérselo" (1 error).

**Caveat:** I didn't listen to the audio, so examples 1–2 are judged from text and confidence, not by ear. A human check of ~20 diff spots (timestamps are in `ours.json`) would give the true ASR error rate. My guess is that it's well under 5 %.

## Problems hit (fixed)

- **PyAV 19 breaks faster-whisper 1.2.1** (`open() got an unexpected keyword argument 'metadata_errors'`). Fix: `pip install "av<16"` (15.1.0).
- **ffmpeg reading the HLS stream directly lost ~14 s** to TLS drops without failing. yt-dlp with fragment retries got the full 558.95 s. Always check the duration against the page.
- **`python -I` ignores PYTHONIOENCODING**, so the scripts set stdout to UTF-8 themselves.
- CUDA itself worked first time with the pip packages `nvidia-cublas-cu12` 12.9 and `nvidia-cudnn-cu12` 9.27 (DLL folders added in `transcribe.py`).

## Files

- `m1/ours.json`: segments, word timestamps and probabilities, run metadata
- `m1/official_speech.txt`: official text, cut to the speech
- `m1/official_raw.txt`: raw PDF extraction, kept to show the split-word problem
- `m1/wer_report.json`, `m1/wer_output.txt`: WER and every diff chunk with context

## Next

WER here is an upper bound because the official text is edited. For M2 and later: (a) hand-check the diff spots, (b) try WhisperX alignment for better word timestamps, (c) measure on a harder item (press conference with Q&A, or a rally).

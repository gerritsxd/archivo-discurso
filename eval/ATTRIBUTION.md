# Attribution accuracy: does the name on a quote belong to the person who said it?

*Review of 25 October 2026. Sample and verdicts: `attribution_sample.jsonl`, `attribution_review.jsonl`. Reproduce: `python src/attribution_sample.py --per 15 --seed 29`, score: `--score`.*

## Result

A fixed random sample of **102 named turns**: 15 per candidate and every host turn drawn by the same rule (7 Herrera, 5 Bustos). Only turns of 15+ words whose speaker the voiceprints named with a clear match are included.

| Verdict | Turns | Share of the 100 that could be judged |
|---|---|---|
| Right person, clean turn (correcto 85 + probable 10) | 95 | **95 %** |
| Right person, but the turn also contains a few words of someone else (mixto) | 5 | 5 % |
| **Wrong person** | **0** | **0 %** (95 % upper bound ≈ 3 %) |
| Could not be decided from the text | 2 | (excluded) |

Per candidate: no wrong attributions for any of them (see `--score` output).

## How it was judged, and the limits

- The reviewer read each turn with the turn before it (usually the question), the appearance and its title, and decided from content and context: who is being asked, who answers, what they say about themselves ("yo, como presidente del Gobierno…"), how the host addresses them. **Nobody listened to the audio.** A turn whose content fits but cannot be confirmed is "probable"; a turn that could be someone else is "indeterminable".
- The reviewer was Claude (the assistant that built the pipeline), not an independent human. The verdicts and the evidence for each are in the review file, so anyone can check or overrule them.
- The sample was drawn **after** the voiceprint threshold was raised from 0.55 to 0.65. Before that, an automatic content check had found two real errors: two other voices at PSOE rallies named as Ada Colau (similarity 0.58 and 0.59). With the old threshold, the turn-level error rate would not have been 0.
- The sample covers turns the system named. It says nothing about turns it left unnamed ("hablante sin identificar"), which is where the system puts anything it is unsure about.

## What the review found besides attribution

- **Speaker boundaries (5 %).** The most common defect: a turn starts with the end of the interviewer's question or ends with the host's goodbye. The quote is still the candidate's, with a few extra words at an edge.
- **Whisper artefacts.** 4 of the 102 turns contained the list of names given to Whisper as hints ("Yolanda Díaz, Alberto Núñez Feijóo, Santiago Abascal, Federico Jiménez…") inserted into the text, plus stock subtitle phrases ("¡Suscríbete al canal!") and a repetition loop. `src/clean_words.py` now removes these before turns are assembled; all items were rebuilt with it.
- **The automatic content check over-flags.** Of the 16 speakers it marked "dudoso", the review found several were correct: a clip of Colau played on RNE, Sánchez thanking the Valencian president, Belarra introducing Montero, Montero speaking about her alliance with Rufián. The check is useful for finding candidates for review, not as a verdict.

## Next

- An independent check against official transcripts with speaker labels: the Congreso's *Diario de Sesiones* and the Moncloa press-conference transcripts, once those appearances are processed.
- A human listening pass over the "mixto" and "indeterminable" turns.

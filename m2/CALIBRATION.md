# Voiceprint calibration, first data (2026-10-25)

Embeddings: pyannote speaker-diarization-community-1 (256-dim, per diarized speaker). Cosine similarity.

Enrolled: Feijóo, Herrera, Bustos (COPE 20 Oct, human-confirmed labels), Sánchez (Moncloa 5 Oct, single speaker).

| Pair | Similarity |
|---|---|
| Feijóo COPE vs Feijóo SER (different studio, station, day) | **0.96** |
| Different people, all pairs seen so far | 0.14 – 0.40 |
| Aimar Bretos (not enrolled) vs best voiceprint (Sánchez) | 0.40 → correctly "unknown" |

Rule in `src/voiceprints.py`: accept if sim ≥ 0.55 and ≥ 0.10 above the next best, and ≥ 20 s of speech. Big gap between 0.40 and 0.96, but only 2 recordings: re-check with rallies (crowd noise), phone interviews and TV before trusting the threshold.

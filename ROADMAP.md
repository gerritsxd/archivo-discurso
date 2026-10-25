# Plan

*Actualizado: 25 de octubre de 2026. Elecciones: 29 de noviembre. Campaña: 13–27 de noviembre.*

## Hecho (MVP)

- [x] Inventario de fuentes desde el 5 de octubre: 121 apariciones encontradas ([m0/SUMMARY.md](m0/SUMMARY.md))
- [x] Transcripción local en GPU: Whisper large-v3, 10,6× tiempo real, 11,4 % frente a texto oficial editado ([m1/RESULTS.md](m1/RESULTS.md))
- [x] Quién habla: pyannote + huellas de voz de los 6 candidatos ([m2/CALIBRATION.md](m2/CALIBRATION.md))
- [x] Descubrimiento automático cada 2 h en el servidor: 59 feeds (partidos, radio nacional y regional, TV) ([m0/GEO_TEST.md](m0/GEO_TEST.md))
- [x] Base de datos SQLite con búsqueda de texto completo + API de solo lectura
- [x] Web: buscador con contexto de la pregunta, transcripciones, fichas de candidato, página de método y de privacidad
- [x] Juego diario ¿Quién lo dijo?, con frases filtradas por contenido
- [x] Fuentes fuera de YouTube que el servidor descarga solo: Congreso, La Moncloa, RTVE Play, 3Cat ([m0/NON_YOUTUBE.md](m0/NON_YOUTUBE.md))

## Ahora: completar el archivo (hasta el 5 de noviembre)

- [ ] Procesar todo lo descargado desde el 5 de octubre (72 apariciones, ~55 h)
- [ ] Integrar las fuentes no-YouTube en el descubrimiento diario
- [ ] Segunda huella de voz por candidato en otro contexto (radio, mitin), para reconocerlos en cualquier sala
- [ ] Huellas de voz de los periodistas habituales, para que las preguntas salgan con nombre
- [ ] Mejorar los cortes entre hablantes cuando se pisan
- [ ] Listas oficiales de candidaturas del BOE (principios de noviembre)

## Siguiente: la capa de análisis (antes del 13 de noviembre)

Un modelo etiqueta cada frase de los candidatos (las frases van al modelo como datos, nunca como instrucciones):

| Etiqueta | Ejemplo |
|---|---|
| **promesa** | «Habría aproximadamente un 50 % menos de altos cargos» |
| **dato** (afirmación con cifra) | «Estamos creciendo tres veces más que la zona euro» |
| **ataque** (a quién) | «…el candidato de Marruecos» |
| **postura** (tema) | vivienda, economía, inmigración, Cataluña, corrupción, pensiones, Europa, igualdad… |

Con esas etiquetas:

1. **Promesómetro**: todas las promesas por candidato y tema, con fecha, lugar y enlace. Después del 29N, seguimiento de las del ganador.
2. **Comparador por tema**: qué ha dicho cada candidato sobre vivienda (o cualquier tema), en columnas, con la fuente.
3. **Mismo candidato, distinto discurso**: lo que dice cada uno según la ciudad, el medio y el público.
4. **Las cifras de la semana**: temas más y menos tratados, menciones a rivales, minutos de voz. Con gráficos y texto para compartir.
5. **Frases para verificar**: afirmaciones con cifras, exportables para los verificadores (Newtral, Maldita, EFE Verifica).

## Campaña (13–27 de noviembre)

- [ ] Grabación de los debates: cara a cara Sánchez–Feijóo (16 nov), portavoces (23 nov), a cuatro (26 nov). Transcritos y buscables a la mañana siguiente
- [ ] Entrevistas en The Wild Project (los cuatro candidatos principales, ~9–13 nov)
- [ ] Ritmo diario: lo de cada día publicado al día siguiente
- [ ] Más capacidad: servidor de 8 GB en cuanto haya stock; GPU de alquiler si la campaña desborda el PC

## Después del 29N

- [ ] Seguimiento de promesas del gobierno resultante
- [ ] Ampliar hacia atrás: campaña de 2023 (GPU de alquiler, ~50–150 $)
- [ ] Revisión humana de frases y correcciones públicas con registro
- [ ] Unir con un grafo de la política española (personas, partidos, votaciones, contratos, sentencias), con cada enlace documentado

## Usuarios y difusión

- Verificadores y periodistas políticos: buscador, API y datos abiertos
- Votantes: juego diario, comparador por tema, promesómetro
- Investigadores: el corpus completo en CC BY 4.0

## Riesgos y cómo se gestionan

| Riesgo | Medida |
|---|---|
| Atribuir una frase a quien no la dijo | Umbral de identificación estricto, «sin identificar» antes que adivinar, enlace a la fuente en cada frase, correcciones públicas |
| Derechos de autor de las cadenas | Solo texto, marcas de tiempo y enlaces; nunca audio ni vídeo |
| YouTube bloquea las descargas | Diversificar fuentes (radio, RTVE, Congreso, Moncloa, TV3); YouTube despacio y desde una conexión doméstica; nunca saltarse sus controles |
| Datos biométricos (huellas de voz) | Privados, solo para candidatos y figuras públicas en su papel público, nunca publicados |

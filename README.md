# Archivo del discurso político

**Todo lo que dicen en público los candidatos a las elecciones generales del 29 de noviembre de 2026, transcrito, con quién lo dijo y enlace al segundo exacto de la fuente.** Desde el día de la convocatoria (5 de octubre de 2026).

🔗 **Web:** https://gerritsxd.com/discurso/ · **Juego diario:** [¿Quién lo dijo?](https://gerritsxd.com/discurso/juego.html) · **Plan:** [ROADMAP.md](ROADMAP.md)

> Transcripción automática, sin revisar. Comprueba siempre la fuente: cada frase enlaza al original.

## Por qué

El discurso político llega troceado: un corte de 20 segundos en el telediario, un titular, un clip en redes. Casi nadie transcribe los mítines, las entrevistas de radio de las 8 de la mañana ni las ruedas de prensa completas, y lo que existe está repartido entre cadenas y partidos. Este proyecto es un archivo abierto de **lo que se dijo de verdad**, verificable por cualquiera, para el derecho a la información y para que nadie tenga el monopolio de lo que se recuerda.

## Qué ofrece hoy

- **Buscador** de todo lo dicho por los candidatos, con la pregunta del entrevistador como contexto y enlace al minuto exacto de la fuente.
- **Transcripciones completas** de cada aparición, con cada intervención atribuida a quien habla.
- **¿Quién lo dijo?**: 5 frases reales al día, adivina el candidato. Solo frases con contenido (cada una puntuada por un editor automático).
- **Datos abiertos**: un JSON por aparición y una API de solo lectura (`/discurso/api/search`, `/stats`, `/item/<id>`, `/daily`).

Cobertura a 25 de octubre de 2026: **72 apariciones, ~55 h de audio** (5–24 oct) de Pedro Sánchez, Alberto Núñez Feijóo, Santiago Abascal, Ada Colau, Irene Montero e Ione Belarra: mítines, declaraciones, entrevistas de radio y televisión.

## Lo que viene

El valor está en lo que se puede sacar del archivo (detalle en [ROADMAP.md](ROADMAP.md)):

1. **Promesómetro**: cada promesa, por candidato y tema, con la fuente. Durante la campaña, el mapa de lo que se promete; después del 29N, la lista con la que pedir cuentas.
2. **Mismo candidato, distinto discurso**: qué dice cada uno según dónde y ante quién habla.
3. **Las cifras de la semana**: de qué hablan, de qué no, y a quién atacan.
4. **Frases para verificar**: afirmaciones con datos, listas para los verificadores.
5. **Los debates** (16, 23 y 26 de noviembre), transcritos a la mañana siguiente.

## Cómo funciona

```
descubrir apariciones → descargar audio → Whisper large-v3 → pyannote (quién habla cuándo)
  → huellas de voz (qué candidato es) → base de datos SQLite + búsqueda → web y API
```

- **Fuentes**: canales oficiales de los partidos y de La Moncloa, RTVE Play, radio (SER, COPE, Onda Cero, RNE, esRadio y emisoras regionales), Congreso, TV3. Solo fuentes oficiales o de medios, nunca subidas anónimas (los imitadores también suenan como el original).
- **Quién habla**: la voz de cada candidato se compara con su huella de voz. Solo se atribuye una frase si la coincidencia es clara; si no, aparece como «hablante sin identificar». Una cita mal atribuida es el peor error posible, así que el sistema prefiere no poner nombre a equivocarse.
- **Precisión medida**: Whisper sobre una declaración oficial de La Moncloa, 11,4 % de diferencia con la transcripción oficial (que está editada: la diferencia real es menor). Huellas de voz: el mismo candidato en otro estudio y otra emisora da una similitud de 0,96; personas distintas, como mucho 0,40.

Detalles técnicos: [ARCHITECTURE.md](ARCHITECTURE.md) · Cómo ejecutarlo: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

## Principios

- **Se publica texto, marcas de tiempo y enlaces a la fuente.** Nunca audio ni vídeo.
- **Neutralidad**: mismo trato para todos los candidatos, orden alfabético, sin colores de partido.
- **Privacidad**: sin cookies, sin analítica, sin registros de visitas. Las huellas de voz son datos biométricos y nunca se publican.
- **Correcciones públicas**: cualquier error se corrige y queda registrado.

## Licencias

Código: [MIT](LICENSE). Transcripciones y datos: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es). Las fuentes originales pertenecen a sus autores; aquí solo se cita y se enlaza.

---

*English: an open archive of everything Spain's 2026 general-election candidates say in public, transcribed with speaker attribution and second-precise links to the original source. Whisper + pyannote + voiceprints, SQLite full-text search, static site and read-only API. See [ROADMAP.md](ROADMAP.md) and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).*

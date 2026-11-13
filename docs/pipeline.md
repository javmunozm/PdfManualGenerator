# Pipeline de trabajo

Cómo pasa un documento desde el original hasta el PDF verificado, con qué herramienta
se hace cada etapa, qué bibliotecas usa y cómo se controla el costo en tokens.

Detalle de cada etapa: [extractor.md](extractor.md) y [generator.md](generator.md).
Errores conocidos y pendientes: [auditoria.md](auditoria.md).

---

## 1. Flujo

```
sources/            original del usuario (no se toca sin permiso; no se versiona)
   |  /extraer  ->  tools/extraer.py
extracted/<n>/      <n>.md + assets/ + reporte.md + fuente.json     registro fiel del original
   |  tools/costo.py            cuánto cuesta lo que sigue
   |  tools/preparar.py         ajustes sin criterio + lista de pendientes
documentos/<n>/     <n>.md + assets/                                 la fuente del PDF
   |  (manuales técnicos) tools/capitulos.py + subagente traductor + tools/comparar_traduccion.py
   |  tools/validar.py          errores y sintaxis no admitida, antes de generar
   |  manual.py
output/<n>.pdf      resultado
   |  tools/comparar.py         faltantes, cifras, portada, sobrantes, orden
   |  subagente revisor-visual  una imagen de control
terminado           comparar.py con código 0
```

Tres casos: **A** documento nuevo (empieza en `documentos/`), **B** regenerar un
documento existente (todo el flujo), **C** actualizar uno ya generado (editar el `.md`,
validar, generar, comparar).

---

## 2. Etapas

| # | Etapa | Comando | Entra | Sale | Código de salida |
|---|---|---|---|---|---|
| 1 | Extraer | `python tools/extraer.py sources/<archivo>` | PDF, Word, PowerPoint, Excel, JSON, CSV, MD, TXT | `extracted/<n>/` | 0 extraído o sin cambios · 2 se niega (pisaría trabajo manual) o error |
| 2 | Estimar | `python tools/costo.py <n>` | un `.md` | tamaño, pendientes, plan por tandas | 0 |
| 3 | Resolver pendientes | subagente `describir-figuras` + ediciones | `reporte.md`, `assets/` | `.md` sin `FIGURA: describir` ni `TRANSCRIBIR` | — |
| 4 | Preparar | `python tools/preparar.py extracted/<n>` | `extracted/<n>/` | `documentos/<n>/` | 0 listo · 1 quedan pendientes · 2 ya existe o error |
| 5 | Traducir (manuales técnicos) | `python tools/capitulos.py partir\|unir ...` + subagente `traductor` | `.md` en español | `.md` en inglés + `<n>.anterior.md` | 0 · 2 error |
| 6 | Verificar la traducción | `python tools/comparar_traduccion.py <n>.anterior.md <n>.md` | los dos `.md` | diferencias de estructura | 0 coincide · 1 difiere |
| 7 | Validar | `python tools/validar.py documentos/<n>/<n>.md` | `.md` | errores y avisos con línea | 0 sin errores · 1 con errores |
| 8 | Generar | `python manual.py documentos/<n>/<n>.md -o output/<n>.pdf` | `.md` | PDF | 0 · distinto de 0 si falla |
| 9 | Comparar | `python tools/comparar.py <origen> output/<n>.pdf` | origen (`.md` o PDF) y PDF | resultado | 0 correcto · 1 falla · 2 error |
| 10 | Revisión visual | comando de `generator.md` (sección 8) + subagente `revisor-visual` | PDF | `output/revision.png` y observaciones | — |

Origen para la etapa 9: `extracted/<n>/<n>.md` si se regeneró sin traducir;
`documentos/<n>/<n>.md --estricto` si el documento es nuevo, actualizado o traducido.
Ninguno necesita abrir `sources/`.

---

## 3. Bibliotecas instaladas

Python 3.14.10 en Windows 11. Versiones instaladas al 12/11/2026, tras reinstalar el
sistema (`pip install -r requirements.txt` instala las seis primeras; las 58 pruebas
pasan con estas versiones):

| Biblioteca | Instalada | Mínima (`requirements.txt`) | La usa | Para qué |
|---|---|---|---|---|
| `reportlab` | 5.1.0 | 4.0 | `manual.py`, `tools/validar.py`, `tests/` | Construir el PDF: portada, índice, marcadores, tablas, recuadros. En `validar.py`, saber qué caracteres tienen glifo. |
| `pillow` | 13.0.0 | 10.0 | `manual.py`, `tools/costo.py` | Reducir el peso de las imágenes; medir las de `assets/`. Opcional para generar. |
| `pymupdf` | 2.1 | 1.24 | `tools/extraer.py`, `tools/comparar.py`, `tests/`, revisión visual | Leer PDF: texto con posición, tablas, imágenes, enlaces, marcadores; renderizar páginas. |
| `python-docx` | 1.2.0 | 1.1 | `tools/extraer.py` | Leer Word (`.docx`). |
| `python-pptx` | 1.0.2 | 0.6.23 | `tools/extraer.py` | Leer PowerPoint (`.pptx`): diapositivas, notas, datos de gráficos. |
| `openpyxl` | 3.1.5 | 3.1 | `tools/extraer.py` | Leer Excel (`.xlsx`, `.xlsm`). |
| `lxml` | 6.1.3 | — | (dependencia de `python-docx` y `python-pptx`) | Se instala sola. |
| `pymupdf_layout`, `pymupdf4llm`, `onnxruntime`, `tabulate` | 2.1 · 2.1 · 1.31.1 · 0.10.0 | — | nadie | Las trae PyMuPDF 2.x como dependencias; el flujo no las usa. |
| `pytest` | no instalada | — | opcional | Las pruebas usan `unittest`; `pytest` también las ejecuta. |

De la biblioteca estándar: `argparse`, `re`, `json`, `hashlib`, `zipfile`,
`xml.etree.ElementTree` (lectura directa de los paquetes de Office para la cobertura),
`csv`, `shutil`, `unicodedata`, `collections`, `pathlib`, `tempfile`, `unittest`.

No se usan y conviene saberlo: no hay OCR (Tesseract) ni LibreOffice. Un PDF escaneado se
transcribe mirando la imagen; un `.doc`, `.ppt` o `.xls` antiguo se convierte antes a mano.

---

## 4. Skills y subagentes

Skills (`.claude/skills/<nombre>/SKILL.md`); se invocan con `/<nombre>`:

| Skill | Caso | Quién la invoca | Qué hace |
|---|---|---|---|
| `/extraer <archivo>` | B | **Solo el usuario.** Invocarla es el permiso para ese archivo de `sources/`. | Etapas 1 a 3. |
| `/costo <n>` | todos | Usuario o Claude | Etapa 2: tamaño, etapas caras y plan por tandas. |
| `/regenerar-manual <n>` | B | Usuario o Claude | Etapas 2, 4, 7, 8 y llama a `traducir-manual` y `verificar-pdf`. |
| `/traducir-manual <n>` | B, A | Usuario o Claude | Etapas 5 y 6. No se usa con `Manual_Curso_IA_Python_v2`. |
| `/nuevo-manual <n>` | A | Usuario o Claude | Acordar índice, escribir, validar, generar, verificar. |
| `/actualizar-manual <n> <cambio>` | C | Usuario o Claude | Edición puntual, versión, validar, generar, comparar. |
| `/verificar-pdf <n>` | todos | Usuario o Claude | Etapas 9 y 10. |

Subagentes (`.claude/agents/<nombre>.md`); trabajan en su propio contexto y devuelven
un resumen de pocas líneas:

| Subagente | Modelo | Herramientas | Tarea |
|---|---|---|---|
| `describir-figuras` | `sonnet` | Read, Edit, Grep | Describir figuras, pasar gráficos a tablas, transcribir páginas escaneadas. |
| `traductor` | `sonnet` | Read, Write | Traducir una parte del manual (un archivo de `partes/`). |
| `revisor-visual` | `haiku` | Read | Mirar la imagen de control y listar problemas visuales. |

---

## 5. Control de costo

Lo que cuesta son los tokens que entran a la conversación (y vuelven a entrar en cada
turno) y los que se escriben. El flujo está armado para que el contenido del manual casi
nunca pase por la conversación principal.

| Qué gasta | Cuánto | Cómo se evita |
|---|---|---|
| Leer el original como imagen | Lo más caro; además es impreciso. | Prohibido. Se extrae con script; el hook `guardia.py` deniega leer PDF y Office. |
| Describir figuras y transcribir escaneados | Caro por imagen. | Subagente `describir-figuras`: otro modelo, y las imágenes no quedan en la conversación. |
| Leer el `.md` completo | Su tamaño, en cada turno que siga. | `tools/costo.py` da el mapa; se lee por rangos de líneas (`grep -n "^#"`). |
| Traducir | El documento entero como salida, que es lo más caro por token. | `capitulos.py` lo parte; cada parte la traduce un `traductor` y se escribe con `Write` (sin repetir el texto viejo); la verificación la hace un script. |
| Arranque de cada subagente | Unos 7.000 tokens por lanzamiento, tenga la parte 40 tokens o 7.000. En un manual de 87.000 tokens fueron 29 lanzamientos y ~473.000 tokens: cerca del 40% fue arranque. | Partes de menos de ~300 tokens se traducen en la conversación; `--tanda 10000` para la mitad de las partes. |
| Avisos de los subagentes en segundo plano | Cada subagente despierta dos veces a la conversación principal, con todo el historial. | No resumir en cada aviso: solo lanzar la parte siguiente. Modelo intermedio en la conversación principal (auditoría, 12.3). |
| Reescribir el `.md` para un cambio | Todo el documento como salida. | `Edit` puntual; si el cambio se repite muchas veces, un script en archivo. |
| Verificar leyendo el PDF | Todo el documento otra vez. | `comparar.py`: unas líneas y un código de salida. |
| Revisión visual página por página | Una imagen por página. | Una imagen con 4 páginas a baja escala, vista por `revisor-visual`. |
| Volver a extraer | Repite todo lo anterior. | `extraer.py` no lo hace si el original no cambió. |
| Sesiones largas | Cada turno reenvía el historial. | Un documento por sesión; `/clear` al cambiar de documento. |
| Esfuerzo alto en tareas mecánicas | Más razonamiento del necesario. | Las skills fijan `effort: medium` o `low` para su turno. |

Ajustes que se pueden cambiar:

- **Modelo de los subagentes**: campo `model` de `.claude/agents/*.md`. Si las
  descripciones de figuras salen pobres, subir `describir-figuras`; si la revisión visual
  se queda corta, subir `revisor-visual` a `sonnet`.
- **Esfuerzo de las skills**: campo `effort` de cada `SKILL.md`.
- **Tamaño de la tanda**: `--tanda` en `costo.py` y `capitulos.py` (6.000 tokens).

Los tokens que muestran las herramientas son aproximados (caracteres / 3,5).

---

## 6. Protecciones

| Qué | Dónde | Efecto |
|---|---|---|
| Hook `guardia.py` (PreToolUse) | `.claude/hooks/`, `.claude/settings.json` | Deniega editar `sources/`; pide confirmación para leerlo o nombrarlo en un comando; deniega leer PDF y Office directamente. También pide confirmación si se llega a `sources/` sin nombrarlo: `Glob` de `**/*`, listado recursivo desde la raíz, comodines, o un encargo a un subagente (H6). |
| Reglas de permiso | `.claude/settings.json` | `deny` editar `sources/`, `ask` leerlo. |
| No pisar trabajo manual | `extraer.py`, `preparar.py`, `capitulos.py` | Se niegan si el destino ya existe; con `--forzar` guardan `<n>.anterior.md`. |
| Pruebas | `tests/` (`python -m unittest discover tests`) | Una por cada error corregido. Crean sus propios archivos. |
| Qué se versiona | `.gitignore` | Solo el flujo de trabajo; nunca `sources/`, `extracted/`, `documentos/` ni `output/`. |

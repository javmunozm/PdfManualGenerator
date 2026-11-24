# Registro de trabajos (regla 10 de `CLAUDE.md`)

Índice de lo que se hizo con archivos temporales, para entender un resultado o un error
después de que los temporales se borraron. Cada entrada: qué se hizo, con qué scripts
(qué hacía cada uno) y qué falló o quedó dudoso. Los scripts no se guardan: si hace falta
uno, se rehace desde esta descripción.

---

## 16/11/2026 · Manual 2 (Manual_2_DotNet10_React19_SQLServer_Mediator_Mapperly)

Regenerado en español, comparado con el original, traducido al inglés (detalle en
`docs/auditoria.md`, sección 14). Scripts de esa sesión (borrados el 17/11/2026):

| Script | Qué hacía |
|---|---|
| `arreglar_m2.py`, `_b`, `_c` | Portada (etiquetas y viñetas desde el renglón aplanado), índice p.2-5 a comentarios, `### PARTE X · CAPÍTULO N` → `# N.`, `### N.N` → `##`, capítulos fundidos con su párrafo; identificadores partidos en celdas y la fila suelta; el recuadro «El camino de una petición» de tabla de una celda a bloque de código con la disposición leída del original; dos celdas con dos comandos. |
| `unir_renglones.py` | Une renglones de código cortados por ancho; exige que el siguiente tenga 4 espacios más de sangría. Uso: `<md> <línea>[:s] ...` (`:s` = con espacio). |
| `pares.py` | Ubica en el `.md` los «renglones que podrían estar partidos» del reporte, con largo y sangría. |
| `unir_codigo_en_linea.py`, `codigo_en_linea.py` | Une `` `a` `b` `` partido; devuelve a su original el código en línea que el traductor cambió. |
| `traducir_titulos_codigo.py`, `ver_titulos.py`, `traducir_06.py` | Títulos de bloque en inglés; comprobar que el código no cambió; una parte chica traducida con reemplazos exactos. |
| `unir_negritas.py`, `palabras_partidas.py`, `compactar_tablas.py`, `unir_tabla_p42.py`, `separar_fragmento.py` | Negritas partidas por el renglón, palabras partidas en celdas, tablas rehechas, una tabla con su continuación, un recuadro pegado al de TERMINAL. |
| `region.py`, `rotulos_codigo.py`, `patch_preparar.py` | Primeras versiones de lo que pasó a `tools/region.py`, `tools/rotulos_codigo.py` y `tools/preparar.py`. |
| `docs_al_dia.py`, `docs_flujo.py`, `skill_regenerar.py`, `coherencia.py`, `migrar_output.py`, `rutas_output.py` | Cambios a las guías y skills; `output/<n>/<n>.pdf` por documento. |

Quedó a medias: el PDF quedó viejo tras separar el recuadro `API/Program.cs (fragment)`
(se regeneró el 17/11).

---

## 17/11/2026 · Manual 2, pruebas, guías y manual 4

- **Manual 2:** regenerado; validar 0/0, `comparar_traduccion` correcto, `comparar --estricto`
  código 0, revisor-visual sin problemas.
- **Pruebas:** 124 → 134 (10 nuevas en `tests/test_mejoras.py`), todas OK. La skill `traducir-manual` se acortó a 79 renglones.
- **`tools/rotulos_codigo.py`:** un «… X» en **otro** bloque confirma que «X» es un rótulo
  si lleva una línea vacía después (caso del manual 4: un TERMINAL de una línea con el
  rótulo `ci.yml` pegado debajo). Con prueba.
- **Manual 4** (en copias del scratchpad, luego instalado): `rotulos_codigo.py --todos` en el
  `.md` y el `.anterior.md` (172 títulos, 54 «… rótulo» quitados, 41 recuadros separados,
  17 unidos entre páginas); 30 códigos en línea partidos unidos (`codigo_partido.py`: la
  regla de `preparar.inline_code` renglón por renglón); 21 títulos de bloque traducidos
  (`titulos_m4.py`); dos celdas git con un comando por renglón (`celdas_git.py`).
  Comprobado con `codigo_igual.py` (el código no cambió: solo se quitaron 243 rótulos).
  Resultado: validar 0/0, `comparar_traduccion` correcto, `comparar --estricto` código 0.
  Revisor: «TXT» en p.124 es el fin de un heredoc (`cat <<'TXT'`), no un rótulo.

---

## 17/11/2026 · Manual 1 (Manual_1_DotNet10_Vue3_SQLServer_Mediator_Mapperly)

Rehecho como el manual 2 sin tocar la fuente: el original de `sources/` no se consultó
(permiso denegado) y `extracted/` solo se leyó.

1. `preparar.py extracted/<M1> --salida <temp>` (no `--forzar`): 91 bloques de código
   unidos, 48 cuadros, 61 códigos en línea, 10 tablas.
2. `arreglar_m1.py` (el de manual 2 adaptado): portada, índice p.2-5 a comentarios,
   4 partes, 16 capítulos (4 fundidos), 110 secciones.
3. `rotulos_codigo.py --todos`: 212 títulos, 82 «… rótulo», 57 recuadros separados.
4. `arreglar_m1_b.py`: fila «Vue / Vite / TypeScript» a su tabla; `OpenIdConnect` x2;
   negrita cruzada; diagrama 3.1 a tablas de componentes y conexiones; flujo 8.1 a bloque
   de código; dos celdas git. **Dudoso:** el diagrama 3.1 y la disposición del flujo 8.1 se
   tomaron del manual 2, porque el original no se pudo mirar. Se comprobó que las palabras
   son exactamente las mismas (salvo «Vue 3» por «React 19»), no la posición de cada flecha.
5. `unir_renglones.py`: 12 renglones cortados por ancho (de 16 con sangría +4; quedaron
   4 que son formato del autor: parámetros, un `if` y su cuerpo, argumentos de una lambda).
6. Verificación en español contra un origen armado en el scratchpad: el `.md` de
   `extracted/` con solo los cambios de estructura (`arreglar_m1.py`) y sin los «… rótulo»
   (lo mismo que `comparar.py` hace con un PDF de origen). `comparar.py` código 0, 100%,
   con 7 `--ignorar` para los encabezados que el original repite al seguir una tabla en
   otra página (los quita `preparar.py`, N10). Las palabras quitadas se revisaron una a una
   (`palabras_quitadas.py`): encabezados repetidos, tablas reordenadas, identificadores unidos.
7. Instalado en `documentos/` (el anterior era la salida del `preparar.py` viejo, sin
   trabajo a mano). Traducido con `traducir-manual`: `capitulos.py partir --tanda 10000`
   (13 partes, todas a `traductor`, ~524.000 tokens de subagente, entre 35.000 y 48.000 por
   parte, 50-74 s cada una) y glosario de 160 pares sacado del manual 2 (`glosario.py`:
   títulos y títulos de bloque ES = EN emparejados por orden). Desvíos: 4 códigos en línea
   traducidos (`Metodo`, `<fecha>`, `nombre`, `opciones`) y un título de bloque en español,
   corregidos con `arreglar_m1_en.py`.
8. Resultado: `comparar_traduccion` correcto (99%), validar 0/0, PDF de 176 páginas y 130
   marcadores, `comparar --estricto` código 0 (100%). Revisor: sin problemas (p.7 es la
   apertura de una parte; p.54, continuación de un recuadro).

Temporales borrados al terminar: las copias y scripts de este trabajo y la carpeta de la
sesión del 16/11.

---

## 17/11/2026 · Extractor: E20 a E24 (`tools/extraer.py`)

Commit `79fea4f` en `main` antes de empezar (todo lo anterior). Cambios y cómo se probaron
(detalle en `docs/auditoria.md`, 14.6):

- E20 `bookmark_head`, `toc_by_page`, `mark_key`; E21 en `page_to_md` (puntos sueltos);
  E22 `wrapped` en `rebuild_code` (con `counts`, cuántas veces aparece cada palabra);
  E23 `open_last_row` en `ruled_tables` y `cut_word` en `cell_md` (con `cuts`: conteos y
  trozos unidos, para que `build_table` y la cobertura no los den por faltantes); E24
  `mono_box`.
- Pruebas nuevas en `tests/test_mejoras.py` (143 en total, todas OK).
- Regresión sin la fuente: se extrajeron con la versión anterior (`git show HEAD:`) y con
  la nueva los PDF de `output/` de los manuales 1, 2 y 4, y se comparó con su `.md`
  (`verdad.py`: cada renglón unido está tal cual en el `.md`; `dudosos.py`: cuántos cortes
  reales quedaron sin unir; `reglas2.py`: aciertos y errores de cada regla candidata).
- **Falló y se corrigió:** la primera versión de `open_last_row` metía el pie de página en
  la última fila; esas tablas no se armaban y `find_tables` las partía en 14 columnas
  (manual 2, p.11 y p.16). Ahora el renglón debe empezar en una columna, no se mira la
  zona del pie y, si la tabla ampliada no se arma, queda la original.
- **Falló y se corrigió:** el cierre `}` se unía sin espacio; el `.md` mostró que `}` lleva
  espacio y `)` no.
- La regla de E22 se ajustó con el manual 2 y se comprobó con el 1 y el 4 (no usados para
  ajustarla): 52 de 52 y 17 de 17 uniones correctas.
- **Visto, no resuelto (N17):** un párrafo que toca la línea de cierre de una tabla se
  pierde; la cobertura lo marca.
- Los originales de la serie no se usaron: E20, E21 y E24 se probaron con PDF que imitan
  lo que mostraba su extracción, no con el original.

## 17/11/2026 · Manual 3 (Manual_3_Node_Vue3_MongoDB) y regla 1

Primer original de la serie extraído con E20 a E24. El original se usó solo como fuente
(extraer, `region.py`, un script de lectura de glifos y `comparar.py`); no se alteró.

- `extraer.py`: 149 p., cobertura 100%, 111 marcadores. Reunido 1 renglón de código
  (correcto); los 47 dudosos eran instrucciones aparte (no se unió ninguno).
- `describir-figuras`: portada y diagrama p.11 (6 componentes, 6 conexiones). Símbolos:
  p.147, 11 casillas → `[ ]`. **Dudoso:** p.103, el glifo no tiene mapa de caracteres
  (código 0) y el original lo muestra como caja vacía; se puso `↔` por contexto.
- `preparar.py` + `rotulos_codigo.py --todos` (17 bloques con rótulo no reconocido, todos
  rótulos): `validar.py` 0/0. Portada armada como la del manual 4.
- **Falló, no lo detectó `validar.py`:** el extractor dejó los capítulos en `##` con el
  antetítulo («PARTE I · CAPÍTULO 1 …») y las secciones en `###` con el nivel en mayúsculas
  («AVANZADO»). Se corrigió con un script: partes y capítulos en `#`, secciones en `##`,
  «(avanzado)» como en el índice; 4 + 16 + 91 = 111 marcadores. Falta que `validar.py`
  avise de capítulos con antetítulo en un nivel inferior.
- Español contra el original: `comparar.py --ignorar "PARTE I · CAPÍTULO"` (una por parte):
  CORRECTO, 0 de 35.956 palabras faltan.
- Traducción: 11 partes (`--tanda 10000`), glosario sacado del manual 4 (123 de 126 títulos
  en común). `comparar_traduccion.py`: 3 fragmentos de código en línea traducidos
  (`?v=<fecha>`, `v-model:nombre`, `ask(opciones)`), devueltos por script; luego CORRECTO.
  El cap. 14 queda «Dockerization and building images» (el manual 4 usa «Building Images»).
- PDF en inglés: 149 p., 516 KB; `validar.py` 0/0; `comparar.py --estricto` CORRECTO;
  `revisor-visual` sin observaciones. Temporales y `partes/` borrados.
- Regla 1 de `CLAUDE.md` reescrita por pedido del usuario: `sources/` se usa como fuente
  (ubicar, extraer, recortar, comparar) sin pedir `/extraer`; solo se prohíbe alterar el
  original. Ajustados `extraer`, `regenerar-manual`, `verificar-pdf`, `docs/pipeline.md` y
  los mensajes de `guardia.py` (18 pruebas del hook OK).

## 17/11/2026 · Manuales 1 a 4: texto en español dentro del código

El usuario vio español en los PDF en inglés de los manuales 1 y 4: todo estaba dentro de los
bloques de código (comentarios, árboles, CLAUDE.md, mensajes de la interfaz, `echo`), que la
regla 2 dejaba sin tocar. Decisión del usuario: se traduce todo lo que no es código, en los
cuatro manuales. Regla 2 de `CLAUDE.md`, `traductor.md` y `traducir-manual` al día.

- `tools/comparar_traduccion.py`: los bloques ya no se exigen idénticos sino con el mismo
  código: `esqueleto` (sin comentarios, cadenas de texto vacías, en plantillas solo etiquetas e
  interpolaciones; los atributos ligados `:x`/`@x`/`v-x` y `class`/`href`… cuentan como código),
  comentarios de varios renglones, y `solo_texto` para prosa o diagramas dentro del código
  (mismos identificadores, cifras, símbolos y sin palabras clave cambiadas). El código en línea
  de la prosa puede cambiar solo si cita un texto de la app traducido con ella. Pruebas nuevas
  en `tests/test_costo.py` (145 en total, todas OK).
- Trabajo en copias del scratchpad (respaldo de los cuatro `.md` antes de instalar):
  `codigo_es.py` sacó los renglones de código con español (2.692, 14 tandas a subagentes
  Sonnet de ~55.000 tokens cada una) y los volvió a poner por número de renglón, comprobando
  que el renglón no hubiera cambiado. Citas de la prosa a mensajes de la app (403/409/sin
  conexión, «Register user», «Invalid configuration», «Categories») cambiadas para que digan
  lo mismo que el código.
- **Falló y se corrigió:** el primer detector de español (tildes o varias palabras comunes)
  dejó pasar mensajes cortos (`echo "Activado: $1"`, `'Tu perfil fue actualizado.'`); lo vio
  el revisor visual. Se rehízo con el vocabulario de cada manual (palabras de la prosa en
  español que nunca aparecen en la prosa en inglés): segunda vuelta de ~130 renglones por
  manual y 10 reemplazos exactos al final. Un error del propio detector (palabra seguida de
  `:`) se corrigió en la tercera vuelta.
- Resultado: los cuatro con `comparar_traduccion` correcto, validar 0/0, `comparar --estricto`
  código 0. Queda en español solo lo que es código o marcador: identificadores (`guardar`,
  `Ejemplo`), archivos (`crear-solucion.sh`, `usuarios.csv`), marcadores (`<tema>`,
  `<paquete>`, `ask(opciones)`), valores de ejemplo (`rrhh`, `Equipo-Marketing`, `temporal`,
  `/no-existe`), nombres de personas, `<html lang="es">`, y la salida de `dotnet` en español
  citada junto a la inglesa («Compilación correcta» / «Build succeeded»).
- Revisión visual de los cuatro antes de la segunda vuelta: sin problemas de formato.

## 2026-11-18 · MongoDB (manual nuevo, skill `nuevo-manual`)

- Manual de preparación para el examen MongoDB Associate Developer (C#), en inglés, sin
  archivo en `sources/`: contenido investigado en la web (documentación oficial del driver
  C# 3.x, manual del servidor, Atlas Search). Notas y URL en
  `documentos/MongoDB/investigacion.md`.
- Escrito por partes en `documentos/MongoDB/partes/` (10 archivos) y unido en
  `MongoDB.md`; las partes se borraron al terminar. Teoría por dominio del examen,
  glosario, 14 ejercicios, 3 exámenes de práctica de 60 preguntas originales con
  explicación de cada opción, resumen final y referencias.
- **No se pudo:** leer las páginas de MongoDB University (guía oficial del examen, cursos
  y quizzes): se generan con JavaScript y WebFetch solo recibe el título. Los objetivos
  salen de dos repositorios que dicen seguir la guía oficial. Sin confirmar: número de
  preguntas (~53) y nota de aprobación.
- **Falló y se corrigió:** `validar.py` marcó `[!IMPORTANT]` (el tipo es `[!IMPORTANTE]`)
  y una negrita con código; `comparar.py` marcó «question's» y «`$inc`s» (se reescribieron).
  Un heredoc de Bash con el texto de las notas falló por las comillas: se usó Edit.
- Resultado: validar 0/0, `comparar --estricto` código 0, 176 páginas, 572 KB; revisor
  visual sin observaciones.
- v1.1 (mismo día, skill `actualizar-manual`): comprobado que no hay cambios de temario en
  2026 (notas en `investigacion.md`). Se agregó el apéndice «Beyond the Blueprint» con los
  temas extra de una guía no oficial (Certsqill): validación de esquema, change streams,
  transacciones, Atlas Charts y Data Federation, con código C#, y 5 preguntas extra. API C#
  comprobada en la referencia 3.13.0. validar 0/0, `comparar --estricto` código 0,
  185 páginas, 608 KB.
- v1.2 (a pedido del usuario): sección de `$out` a S3 verificada completa contra
  docs/atlas/data-federation/supported-unsupported/pipeline/out (campos, obligatorios,
  valores por defecto, `errorMode`, nombres de archivo, privilegios) y reescrita; ejemplo C#
  propio con esos campos. El formato exacto de la cadena de conexión de una instancia
  federada no aparece en la documentación: el texto dice copiarla del diálogo Connect.
  Revisión visual de las páginas 174-183 del apéndice (dos hojas a 80 dpi).
- **Falló y se corrigió (revisión visual de v1.2):**
  - Las viñetas dentro de los cuadros `> [!...]` salían como un solo párrafo, porque
    `manual.py` une los renglones de cada párrafo de un cuadro. Se separó cada viñeta con
    `>` vacío y `•` (63 viñetas en 15 cuadros).
  - El código en celdas de encabezado de tabla salía como un recuadro blanco sobre el verde:
    se quitaron las comillas invertidas en 7 encabezados.
  - Había 21 páginas en blanco, porque cada `#` ya empieza página y el `\salto` previo
    agregaba otra: se quitaron los 21 `\salto` antes de capítulo.
  - La tabla de conteo era demasiado angosta: se rehízo en 4 columnas más una lista.
  - Las tres primeras correcciones se hicieron con scripts sobre una copia en el scratchpad.
    La primera versión del script cambió los fines de línea (escritura en modo texto en
    Windows); se vio en el diff de la copia y se corrigió con `newline=""`. El `.md` real
    no se tocó hasta que el diff fue el esperado.
  - Un `sed` por número de línea apuntó a la línea equivocada (corrida de una); se usó Edit.
- Resultado v1.2: validar 0/0, `comparar --estricto` código 0, 165 páginas, 598 KB, sin
  páginas vacías (barrido de todas las páginas con PyMuPDF). El revisor visual confirmó las
  correcciones en 155-164 y 33.

## 2026-11-18 · Lecciones del manual MongoDB a herramientas, guías y skills

- `tools/validar.py`: tres avisos nuevos (salto antes de capítulo, lista dentro de un
  cuadro, código en el encabezado de una tabla). `tools/revisar.py`: lista las páginas casi
  vacías. Seis pruebas nuevas en `tests/test_mejoras.py` (`FormatoDeManualNuevo`); 151
  pruebas OK.
- `docs/generator.md` (sintaxis, problemas frecuentes, verificación final),
  `docs/auditoria.md` (sección 15) y las skills `nuevo-manual`, `verificar-pdf` y
  `actualizar-manual`.
- **Efecto en manuales terminados:** los manuales 1 a 4 pasan a 0 errores y 2 avisos (G12:
  código en dos encabezados de tabla cada uno). No se tocaron: queda a decisión del usuario.
- Las pruebas se corren con `python -m unittest discover tests`; `python -m unittest
  tests.test_mejoras` falla al importar `test_pipeline` (no es un error del código).

## 2026-11-18 · Manuales 1 a 4: encabezados de tabla con código (G12)

- A pedido del usuario. En cada manual, dos encabezados: `usermanager-bff` y
  `<script setup>` en código. Pasaron a «Client setting usermanager-bff» y «Vue 3 (script
  setup)» (sin `<>`: validar lo tomaría como etiqueta HTML). Script sobre copias del
  scratchpad, diff de 4 renglones por manual, validar 0/0 en las copias, luego instalado.
- Sin línea `version` en la cabecera de estos manuales (vienen de un original de
  `sources/`): no se agregó, para no cambiar la portada.
- Resultado: los cuatro con validar 0/0 y `comparar --estricto` código 0; revisor visual
  confirmó los encabezados en las 8 páginas.
- **Falló y se corrigió:** la primera versión de la lista de páginas vacías de `revisar.py`
  (5 renglones o menos) marcó como vacías las 3 portadillas de parte de cada manual. Se
  cambió a «sin texto entre encabezado y pie», con prueba nueva (152 OK). Un `rm` con una
  variable de shell lo bloqueó el control de seguridad; se repitió con rutas literales.

## 2026-11-19 · Manual 1: capítulo 9 «Backend tests» (versión 2.0)

- A pedido del usuario: las pruebas van **después del backend terminado** (no repartidas en
  los capítulos ni como apéndice). Capítulo nuevo 9 en la Parte II; los capítulos 9-16 pasan
  a 10-17 (58 títulos; el texto no tenía referencias numéricas a esos capítulos).
- **Verificación real, no por lectura:** el código del capítulo 8 se extrajo del `.md` a una
  solución temporal con los `.csproj` de 7.8 y compiló (SDK 10.0.404). Se creó la migración,
  se escribieron las pruebas y se ejecutaron con Docker: 57 pasan (38 unitarias, 19 contra
  `mssql/server:2022-latest`). El capítulo incluye esos mismos archivos (sustitución
  automática, no copia a mano). Fuentes y hallazgos en
  `documentos/Manual_1_…/investigacion-pruebas.md`.
- Otros cambios: 1.4 (versiones), 1.5, 1.7 (backend «compilado», proyecciones probadas contra
  SQL Server; se arregló una fila partida de la extracción), 4.2 y 4.5 (árboles con `Tests/`
  y `global.json`), 4.7 (`CLAUDE.md` del proyecto), 7.14, 14.2 (paso 8 de Category), 16.5 (CI
  con `dotnet test`), 17.1 y 17.3. Cabecera `version: 2.0`.
- Scripts (scratchpad; borrados el 19/11/2026 al terminar los cuatro manuales, con las
  soluciones temporales `um/`, `um2/`, `un/`, `un4/` y las plantillas `cap9.md`, `cap9n.md`):

| Script | Qué hacía |
|---|---|
| `extract_backend.py` | Extrae los bloques de código con título `Domain/…`, `API/…`, etc. de un rango de líneas del `.md`, separando los títulos pegados dentro de un bloque. |
| `reflow_tests.py` | Acorta a ≤ 102 caracteres los renglones largos del código de pruebas (reemplazos exactos). |
| `build_manual1.py` | Renumera títulos 9-16 fuera de bloques de código, inserta el capítulo (los `@@FILE` se reemplazan por los archivos ejecutados) y aplica los ajustes con conteo exacto. |

- **Falló y se corrigió:** NuGet sin orígenes configurados en la máquina (se usó un
  `nuget.config` solo en la carpeta temporal); `Mvc.Testing` sin versión instala 11.0.0
  (NU1202, quedó como advertencia en el capítulo); dos pruebas de validadores fallaron por el
  nombre de propiedad que da el `selector` (quedó como nota); Docker Desktop estaba detenido.
- Resultado: validar 0/0, `comparar --estricto` código 0 (100%), revisión visual de las
  páginas 10, 11, 20, 87-110 y 195 sin observaciones; «Sin páginas vacías».
- Pendiente para el usuario: advertencias NU1902/NU1903 por paquetes transitivos de las
  versiones fijadas (`System.Security.Cryptography.Pkcs` 9.0.4, `Microsoft.OpenApi` 2.0.0).
  Manuales 2-4 sin cambios.

## 2026-11-19 · Manuales 2, 3 y 4: capítulo 9 «Backend tests» (versión 2.0)

- Hay dos backends: .NET (manuales 1 y 2) y Node + MongoDB (3 y 4). Cada par recibe el mismo
  capítulo; cada manual se verificó contra **su propio** código del capítulo 8.
- **Manual 2:** su backend (55 archivos) compila, el modelo coincide con la migración y las 57
  pruebas del manual 1 pasan. Capítulo de `cap9.md`; ajustes como en el manual 1 con las frases
  propias del manual 2 (`build_manual2.py`, derivado de `build_manual1.py` por `derive_manual2.py`).
- **Manuales 3 y 4:** capítulo nuevo con Vitest 5, supertest 7 y @testcontainers/mongodb 12.
  Sin Node en la máquina: todo en el contenedor `node:24` con el socket de Docker. El workspace
  y el código de cada manual compilan (`tsc -b`, TypeScript 7.0.2); 55 pruebas (36 unitarias, 19
  contra `mongo:8`) pasan en cada uno; `npm run test:types` sin errores. Detalle y hallazgos en
  `documentos/Manual_3_…/investigacion-pruebas.md` (copia en el manual 4).
- La tabla de proyectos de 9.2 (.NET) pasó de 4 a 3 columnas en los manuales 1 y 2 (una columna
  quedaba angosta); en 3 y 4, salto de página antes de 9.7 (la p.83 quedaba con solo el commit).
- Scripts (scratchpad): `extract_node.py` (archivos del workspace Node desde el `.md`, incluidos
  `package.json`, `tsconfig` y títulos pegados dentro de un bloque), `reflow_node.py`,
  `build_node.py` (como `build_manual1.py`, con las frases de cada manual Node y los árboles
  `+-` del manual 4), `fix_table_9_2.py`, `salto_9_7.py`.
- **Falló y se corrigió:** la terminal alteró las barras invertidas de un script en línea (se
  pasó a archivo, como dice la memoria); una copia de seguridad fue a `/tmp` por error (se
  recuperó); las primeras pruebas de `resolve.conditions` no eran concluyentes porque existía
  `dist/` (se repitieron sin `dist/`).
- Resultado en los tres: validar 0/0, `comparar --estricto` código 0 (100%), «Sin páginas
  vacías», revisión visual de las páginas cambiadas y del capítulo entero.
- Temporales borrados al terminar (scripts, soluciones de prueba, copias v1 de los `.md`, hojas de
  revisión). Quedan en Docker las imágenes `node:24`, `mongo:8` y `mssql/server:2022-latest`.

## 2026-11-19 · Correcciones: versiones .NET (manuales 1 y 2) y syncSession (3 y 4)

- A pedido del usuario («correct them»), los dos pendientes del informe anterior.
- **Manuales 1 y 2:** el script de 7.11, corrido tal cual, falla en el paso 5: sin `--version`
  se instala EF Core 11.0.0 (solo net11.0, NU1202). Todos los paquetes Microsoft.* pasan a
  `--version 10.0.15` (7.7, 7.11 y el paquete de Redis en 14.6); 7.8 muestra 10.0.15 y
  FluentValidation 12.2.0; advertencia nueva en 7.7; `--highest-minor` en 7.14; 1.4 y 1.7 al
  día. Verificado: el script corregido corre entero, sin NU190x; las 57 pruebas pasan;
  `--vulnerable` vacío en los 7 proyectos.
- **Manuales 3 y 4:** `syncSession` rechaza el perfil desactivado antes de guardar
  (`ensureActive`); dos pruebas nuevas, primero en rojo con el código viejo, después en verde.
  `tsconfig.test.json` ya no toma `Client/src`. Conteos del capítulo al día (56 pruebas).
  Verificado desde el `.md` corregido de cada manual, con `Client/` presente: build, 56
  pruebas, `test:types` y `npm audit` (0).
- Scripts (scratchpad, borrados al terminar): `extract.py` (genérico, con regex de rutas),
  `fix_net_versions.py`, `new_tests.py`, `fix_sync.py`, `fix_tsconfig_test.py`, `notes_update.py`.
- **Falló y se corrigió:** un `rm` con variable lo bloqueó el control de seguridad (se rehízo
  sin borrar); un patrón de nombre de archivo no coincidía (mayúscula final); extraer hasta el
  final del manual trajo los archivos del ejemplo Category (14.2), que no compila solo porque su
  registro se da como fragmentos: ya figuraba como «no compilado» en 1.6/1.7.
- Resultado: validar 0/0 y `comparar --estricto` correcto en los cuatro; revisión visual de las
  páginas cambiadas.


## 2026-11-19 · Compendium CCAR-F (diagnóstico) y manual nuevo CCAR-F_Lab_Manual

- Extraído `sources/Claude_Compendium-CCAR-F/The-Architects-Compendium-CCAR-F.pdf` (113 p.,
  100%) solo para diagnosticarlo contra la guía oficial v1.0; no se regeneró. Quedan sin
  resolver sus pendientes de código (1 reunido, 16 dudosos).
- Manual nuevo (skill `nuevo-manual`, inglés, Python): `documentos/CCAR-F_Lab_Manual/`
  (investigación en `investigacion.md`). 196 páginas, 30 laboratorios, 4 capstones, 69
  preguntas de capítulo, 2 exámenes de 60 ítems (12 de respuesta múltiple cada uno).
- Verificado: todo el código titulado `ccarf-labs/...` se extrajo del manual y corrió en un venv
  (anthropic 2.11.0, claude-agent-sdk 0.2.185, mcp 2.3.0): 43 pruebas sin API pasan, todos los
  módulos importan; el servidor MCP probado con el cliente en memoria. Las partes que llaman a
  la API **no se ejecutaron** (costo): están marcadas «calls the API».
- Scripts (scratchpad, borrados): `pdftxt.py`, `extract_labs.py`, `shuffle_options.py`
  (repartió la letra correcta, antes casi siempre A), `check_keys.py` (claves vs opciones: 0
  errores).
- Falló y se corrigió: tool_choice forzado en `run_batch` (nombre fijo → 400), documentos
  «grandes» que no se achicaban, líneas mal numeradas en `sample_code.py`, ``` dentro de un
  string de Python, negrita alrededor de código, código en encabezado de tabla.
- Resultado: validar 0/0; `comparar --estricto` CORRECTO; sin páginas vacías.


## 2026-11-21/22 · Manual nuevo Manual_Curso_IA_Python_v3 (inglés, plataforma RAG en Docker)

- Manual nuevo en inglés a partir de la v2 (`sources/Manual_Python_RAG/`, solo leída):
  `documentos/Manual_Curso_IA_Python_v3/` (22 partes en `partes/`, unidas por `build_manual.py`,
  que inserta el código probado byte a byte). 189 páginas, 973 KB, 7 capturas en `imagenes/`.
- Proyecto probado en `_trabajo/rag-platform` (fuera de Git): 87 pruebas; `check_stages.py`
  verifica cada punto de control (15/22/32/44/53/53/53/53/85/87). Pruebas reales contra Gemini
  (`gemini-3.5-flash-lite`, `gemini-embedding-001`) con la clave del usuario, solo en un `.env`
  temporal: nunca en el manual ni en el repo.
- Mediciones reales insertadas (caps. 9, 10, 12, 13, 14, 16, 18, 19): PDF propio de 400 p. en
  la capa gratuita (1.200 trozos en 3 tandas, aparcado por la cuota diaria y reanudado solo),
  respuestas con citas, tickets, diagnóstico, chat del widget en Edge sin interfaz, evaluación
  (1.0 / 1.0), capturas del panel revisadas por `revisor-visual`.
- Scripts: en `_trabajo/tools` (se conservan, ver abajo) `build_manual.py`, `check_stages.py`,
  `env_names.py`, `watch_job.py`, `shoot.py`, `make_big_pdf.py`, `capture_429.py`,
  `capture_daily.py`; en el scratchpad (temporales) `watch_big.py`, `shoot_panel.py`,
  `shoot_chat.py`, `cut_pdf.py`, `timeline*.py`, `reset_tickets.py`, `interrupt_test.sh`.
- `_trabajo/` (proyecto de 87 pruebas y scripts) **se conserva por decisión del usuario**, como
  excepción a la regla 10. Borrados: el `.env` con la clave y los volúmenes Docker.
- **Falló y se corrigió (errores del código que enseña el manual, hallados al probar de verdad):**
  - Un 429 por minuto de Gemini dice «billing»: se tomaba por cuota diaria y aparcaba el trabajo.
  - redis-py 8 espera 5 s por defecto, igual que el `BLPOP`: el worker caía en bucle
    (`socket_timeout=30`).
  - En Gemini cada texto de un lote es una petición; la cuota diaria es de 1.000.
  - `gemini-3.5-flash` tardó 266 s contra 1,6 s de `flash-lite`.
  - La lámpara rota se clasificaba como `billing` (faltaba la categoría `orders`).
  - Orden de capítulos y `TENANTS` anidado corregidos.
  - Hoy: el chat inventó `support@acme-home.example` al no poder abrir un ticket → campo
    `support_contact` del tenant y `handover_fallback`.
  - El worker fuera de Docker no indexaba nada (`relative_to` con bandeja relativa contra las
    rutas absolutas de `watchfiles`) → `resolve()`.
  - Un trabajo cortado por `docker stop` quedaba `indexing` para siempre y el worker moría con
    137 → cola confiable (`BLMOVE` + `ragkit:processing` + `recover()`) y SIGTERM como Ctrl+C;
    probado: parada en 0,9 s con código 0, `"recovered": 1`, saltó 60 trozos y terminó.
  - Pasos del diagnóstico en un solo párrafo en el panel (`white-space: pre-line`).
  - El aviso «Below the threshold» era falso dentro de los 30 min.
  - Una tabla de 4 columnas partía un nombre de prueba de 53 caracteres (comparar falló) →
    3 columnas y lista.
  - `python -c` desde PowerShell rompió las comillas (se rehízo con script en archivo).
- Pendiente conocido, documentado en el cap. 13: «similar» devuelve el ticket resuelto más
  cercano aunque no se parezca (sin umbral de distancia).
- Resultado: validar 0/0; `comparar --estricto` CORRECTO (48.816 palabras, 100%); sin páginas
  vacías; revisión visual de portada, índice, figuras y páginas cambiadas.
- Herramienta: `tools/estado.py` daba «traducción en curso» a todo documento con `partes/`,
  también a un manual nuevo escrito por partes (skill `nuevo-manual`) y ya unido; el hook de
  cierre lo excluía de la revisión de PDF desactualizado. Ahora dice «partes sin unir» solo si
  una parte es más nueva que el `.md`. Prueba ampliada en `tests/test_costo.py`; 152 pruebas OK.

## 2026-11-22 · Manual v3: bloques de código para escribirlos a mano (pedido del usuario)

- Pedido: un solo PDF (sin zip) en el que el código se pueda escribir sin dudas: letra y
  tamaño claros, saltos de renglón naturales, sangría visible. Medido antes: Courier, 77 de
  155 bloques achicados a 7,3–8,4 pt (renglones de hasta 100 caracteres); continuaciones
  ambiguas escritas a mano (bloque de carpetas en PowerShell del cap. 2).
- Copiar: PDFium (Chrome, Edge) reduce a un espacio toda sangría al copiar; 8 variantes
  probadas con pypdfium2 (espacios, `ActualText` por renglón y por bloque, NBSP, tabuladores,
  espacios sueltos): ninguna la conserva; MuPDF sí. No hay arreglo dentro del PDF: la regla 4
  del cap. 0 ahora lo dice y pide rehacer la sangría con las guías. No se pudo copiar desde
  el Edge del usuario por automatización (no acepta teclas simuladas).
- `manual.py`: código en DejaVu Sans Mono 9 pt, tinta más oscura, interlineado 1,35, guías de
  sangría por nivel (dibujo, no texto); un párrafo que presenta lo que sigue («…:» o rótulo
  corto) no queda solo al pie (`CondPageBreak(3.5 cm)`; `keepWithNext` dejaba 29 páginas a
  medias). Prueba nueva `test_G17_*`; 153 pruebas OK. `docs/generator.md` actualizado.
- Proyecto (`_trabajo/rag-platform`): ruff `line-length = 80`. Scripts del scratchpad
  (borrados), en este orden desde una copia de respaldo (`run_all.ps1`, `check_all.ps1`):
  `pre_fixes.py` (los comandos de los docstrings a su propio renglón), `reflow_py2.py`
  (comentarios y docstrings por párrafo, con `tokenize`), `rewrap_strings.py` (cadenas
  contiguas, AST idéntico), `ruff format`, `hand_fixes*.py`, `reflow_hash.py`, `reflow_web.py`
  (JS con esprima; CSS: una declaración por renglón si la regla no cabe), `reflow_md.py`,
  `fix_parts.py`; todos con `wraputil.balanced` (mismos renglones, el ancho más angosto: sin
  pedazos de frase al final; sin cortar `código` corto). Verificado: AST igual salvo
  `common.py`, `jobs.py` y `tickets_db.py` (cambios a propósito); tokens JS iguales salvo los
  cambios a propósito; CSS, HTML, Markdown, `.env`, TOML, JSON y Dockerfile iguales en
  contenido; `docker compose config` idéntico; 87 pruebas y todas las etapas OK.
- **Falló y se corrigió:** `ruff format` sin mover antes los comentarios partía el código
  (`settings.tenants[\n tenant\n]`); el primer `rewrap_strings.py` partió la clave
  `"message"` letra por letra (AST igual, ilegible); la primera pasada de CSS perdió un
  comentario después de `}`; `comparar.py` quitó el encabezado equivocado de una tabla que
  empezaba arriba de una página (lo arregló el `CondPageBreak`). La primera pasada partía cada
  renglón largo por separado y dejaba pedazos sueltos («from the», «own variable.») y un
  comando partido en un docstring: se rehízo por párrafos y con reparto parejo. La revisión
  visual lo encontró, no los scripts. En PowerShell `$py` y `$PY` son la misma variable;
  `pyproject.toml` debe pasar a 80 antes del primer `ruff format`.
- Manual: reglas 4 y 5 del cap. 0 sin el «kit» ni la «versión en línea» (no existen);
  63 «Copy the whole block» → «Type or paste»; comandos con estructura de renglones completos
  (splatting en PowerShell, `-d @-` con heredoc en curl), probados contra un servidor de eco.
- Resultado: 0 renglones de código de más de 80; los 156 bloques a 9 pt; validar 0/0;
  `comparar --estricto` CORRECTO (49.082 palabras); 235 páginas, sin páginas vacías;
  revisión visual de portada, índice, figuras y las páginas de código cambiadas.
## 2026-11-23 · Manual v3 3.1: archivos grandes que no son PDF y HTML rediseñados (pedido del usuario)

- Pedido: «el PDF no tiene vectorstore, indexación ni chunkado para archivos grandes y evitar que
  el servicio muera»; «los html están muy feos». Diagnóstico: Qdrant (cap. 7), la indexación
  (cap. 9) y el troceo ya estaban; lo que faltaba era que solo el PDF se leía por partes.
- Medido (memoria máxima del proceso, Windows; archivos propios en el scratchpad, `make_big.py`,
  `make_office.py`, `measure.py`): `.xlsx` de 300.000 filas (8,8 MB) 2.098 MB y 108 s con
  MarkItDown → 166 MB y 20 s; `.log` de 300 MB 731 → 133 MB; PDF de 150 MB con imágenes
  432 → 158 MB; `.docx` de 4,2 MB (33 MB de XML) 486 MB → rechazado por el tope.
- Proyecto (`_trabajo/rag-platform`): `loaders.py` (texto en partes de 20.000 caracteres que
  terminan en fin de línea y CSV con su encabezado; `.xlsx` con openpyxl `read_only` en tablas
  de 200 filas; tope de 20 MB de XML para `.docx`/`.pptx`/`.html`; `PdfReader` con el archivo
  abierto y un lector nuevo + `gc.collect()` cada 10 páginas), `pipeline.py` (id por posición:
  sin eso las partes sin número de página se pisaban), `jobs.py` (`release` en parada limpia,
  `crashes`/`MAX_CRASHES=3` en `recover`), `worker.py` (`MAX_INDEX_MB`, también para la bandeja),
  `config.py`, `.env.example`, `compose.yaml` (`mem_limit` 512m y 1g el worker),
  `pyproject.toml` + `uv.lock` (`openpyxl==3.1.5` declarado). 8 pruebas nuevas: 95;
  `check_stages.py` con los conteos nuevos (36/52/61/93/95), todas las etapas OK; ruff limpio.
- Probado en Docker con Gemini real (clave en `.env` temporal): parada limpia → `queued`, sin
  contar; tres `docker compose kill -s KILL worker` → `crashes` 1, 2 y `failed` («the worker died
  3 times…»). Con 350 y 280 MB el `.html` de 19 MB no se cayó en Linux (cupo); el presupuesto de
  5 embeddings de la prueba lo frenó. En reposo: APIs ~200 MiB, worker 228 MiB.
- HTML: panel (`index.html`, `panel.css`, `panel.js`) con menú lateral, tarjetas, filas con
  etiquetas, avisos en vez de `alert`, sugerencia y resolución en la fila, modo oscuro; widget
  con el mismo estilo y `data-color`; tienda «Acme Home». Borradas `web/dashboard` y
  `web/demo-site` (vacías). 5 capturas del cap. 19 rehechas (scratchpad `shoot2.py`, `crop.py`), un `salto` antes del paso 19.2 (título huérfano),
  revisadas tres veces por `revisor-visual`. La del cap. 9 (`panel-knowledge-waiting.png`) se
  conserva: es la medición del 22/11 con la cuota diaria agotada; el pie lo dice.
- **Falló y se corrigió:** un lector nuevo de pypdf sin `gc.collect()` no liberaba nada (ciclos);
  el tope por tamaño en disco no servía para `.docx` (comprimido); las primeras capturas salieron
  vacías y los chats con 429: el tiempo virtual de Edge sin interfaz adelanta el `setInterval` y
  supera `REQUESTS_PER_MINUTE=30` (subido solo en el `.env` temporal); el revisor encontró el
  subtítulo del widget ilegible, etiquetas que bajaban bajo títulos largos, «1 parts» y el campo
  de la clave cortado: corregidos.
- Quedó: los tickets #5 a #7 en `data/tickets.db` (creados por el diagnóstico y los chats de las
  capturas). **Pendiente del usuario:** borrar `_trabajo/rag-platform/.env` (tiene la clave) y los
  volúmenes `ragkit_qdrant_data` y `ragkit_redis_data`: el modo automático no dejó borrarlos.

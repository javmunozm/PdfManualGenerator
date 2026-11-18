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

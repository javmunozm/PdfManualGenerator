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

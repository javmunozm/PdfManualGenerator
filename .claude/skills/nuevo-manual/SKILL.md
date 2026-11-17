---
name: nuevo-manual
description: Crea un manual PDF nuevo cuando no hay un archivo de origen en sources/. El contenido se investiga en la web según lo que el lector necesita aprender. Usar cuando se pide escribir o armar un manual, guía o apunte nuevo.
argument-hint: <nombre> [tema]
effort: medium
allowed-tools:
  - Bash(python tools/validar.py *)
  - Bash(python manual.py *)
  - Bash(python tools/comparar.py documentos/*)
  - PowerShell(python tools/validar.py *)
  - PowerShell(python manual.py *)
  - PowerShell(python tools/comparar.py documentos/*)
---

# Manual nuevo

Nombre de carpeta y archivo: primer argumento (`$0`), sin espacios ni tildes.

## Pasos

1. Acordar con el usuario, en un solo mensaje, lo que no esté dicho:
   - **el lector**: para quién es (el usuario u otra persona) y desde qué nivel parte;
   - **qué necesita saber** o poder hacer al terminar el manual;
   - título, capítulos y extensión aproximada.
   No empezar a investigar ni a escribir sin el lector y el índice aprobados.
2. Investigar en la web antes de escribir. El contenido de un manual sale de `sources/`;
   esta skill es para cuando no hay un archivo de origen (si lo hay, es el caso B:
   `/extraer` y `/regenerar-manual`). No se escribe de memoria.
   - Buscar por capítulo del índice, usando como pregunta lo que el lector necesita saber.
   - Preferir fuentes primarias: documentación oficial, normas, el autor original.
     Comprobar que versiones, cifras y fechas estén vigentes.
   - Anotar en `documentos/$0/investigacion.md`, por capítulo: el dato, su URL y la fecha
     de consulta. Comandos, cifras y versiones se anotan tal como están en la página.
   - Lo que no se pudo confirmar en ninguna fuente se informa al usuario; no se rellena.
3. Idioma: los manuales de programación, ingeniería, física y matemática se escriben
   **en inglés** (excepción: `Manual_Curso_IA_Python_v2`). El resto, en el idioma del lector.
4. Crear `documentos/$0/$0.md` con la cabecera de `ejemplo.md` (titulo, subtitulo, autor,
   curso, institucion, version, color, numerar, e `idioma: en` si va en inglés) y los capítulos. Se redacta desde las
   notas de `investigacion.md`, con palabras propias (sin copiar párrafos de las páginas)
   y al nivel del lector acordado. El último capítulo es «Referencias» («References»),
   con los enlaces usados. Las imágenes van en `documentos/$0/imagenes/`.
5. Si parte de la información viene de archivos, se extrae primero (`/extraer`) y se copia
   desde `extracted/`, nunca desde el original. Lo que dice el archivo manda sobre la web.
6. `python tools/validar.py documentos/$0/$0.md --estricto` hasta que no muestre nada.
7. `python manual.py documentos/$0/$0.md -o output/$0/$0.pdf`
8. `python tools/comparar.py documentos/$0/$0.md output/$0/$0.pdf --estricto`
9. Skill `verificar-pdf` para la revisión visual.

## Sintaxis admitida

`#` `##` `###`, `**negrita**`, `*cursiva*`, `` `código` ``, `[texto](https://...)`, listas
(anidadas con 2 espacios o más de sangría), tablas (`<br>` para un salto dentro de una
celda), bloques de código (con título: ```` ```API/Program.cs ````),
`> [!NOTA|CONSEJO|ADVERTENCIA|IMPORTANTE|EJERCICIO] título`, `![pie](ruta)` sola en la
línea, `\salto`. Sin HTML ni notas al pie.
Detalle: `docs/generator.md`, sección 7.

## Presupuesto

- Un documento largo se escribe por capítulos en mensajes separados, no en una sola
  respuesta gigante: si se corta, se pierde todo.
- No releer lo ya escrito para "revisarlo": lo revisan `validar.py` y `comparar.py`.
- La web también cuesta: abrir solo las páginas que responden una pregunta del índice y
  dejar lo útil en `investigacion.md`; no pegar páginas enteras en la conversación.
- `comparar.py` comprueba que el PDF dice lo que dice el `.md`, no que el `.md` sea
  cierto: la exactitud depende de las notas y sus URL.

---
name: nuevo-manual
description: Crea un manual PDF nuevo desde ideas, apuntes o información suelta (no desde un documento existente). Usar cuando se pide escribir o armar un manual, guía o apunte nuevo.
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

1. Acordar con el usuario, en un solo mensaje, lo que no esté dicho: título, público,
   capítulos y extensión aproximada. No empezar a escribir sin el índice aprobado.
2. Idioma: los manuales de programación, ingeniería, física y matemática se escriben
   **en inglés** (excepción: `Manual_Curso_IA_Python_v2`). El resto, en el idioma del usuario.
3. Crear `documentos/$0/$0.md` con la cabecera de `ejemplo.md` (titulo, subtitulo, autor,
   curso, institucion, version, color, numerar) y los capítulos. Escribirlo de una vez,
   no por parches; las imágenes van en `documentos/$0/imagenes/`.
4. Si parte de la información viene de archivos, se extrae primero (`/extraer`) y se copia
   desde `extracted/`, nunca desde el original.
5. `python tools/validar.py documentos/$0/$0.md --estricto` hasta que no muestre nada.
6. `python manual.py documentos/$0/$0.md -o output/$0.pdf`
7. `python tools/comparar.py documentos/$0/$0.md output/$0.pdf --estricto`
8. Skill `verificar-pdf` para la revisión visual.

## Sintaxis admitida

`#` `##` `###`, `**negrita**`, `*cursiva*`, `` `código` ``, `[texto](https://...)`, listas
simples, tablas, bloques de código, `> [!NOTA|CONSEJO|ADVERTENCIA|IMPORTANTE|EJERCICIO] título`,
`![pie](ruta)` sola en la línea, `\salto`. Sin listas anidadas, HTML ni notas al pie.
Detalle: `docs/generator.md`, sección 7.

## Presupuesto

- Un documento largo se escribe por capítulos en mensajes separados, no en una sola
  respuesta gigante: si se corta, se pierde todo.
- No releer lo ya escrito para "revisarlo": lo revisan `validar.py` y `comparar.py`.

---
name: actualizar-manual
description: Aplica cambios a un manual que ya tiene su .md en documentos/ y vuelve a generar el PDF. Usar cuando se pide corregir, agregar o cambiar algo en un manual ya generado.
argument-hint: <nombre> <cambio pedido>
effort: medium
allowed-tools:
  - Bash(python tools/validar.py *)
  - Bash(python manual.py *)
  - Bash(python tools/comparar.py documentos/*)
  - PowerShell(python tools/validar.py *)
  - PowerShell(python manual.py *)
  - PowerShell(python tools/comparar.py documentos/*)
---

# Actualizar un manual

Documento: `documentos/$0/$0.md`. El PDF nunca se edita: se cambia el `.md` y se regenera.

## Pasos

1. Ubicar el lugar del cambio sin leer el documento: `grep -n "^#" documentos/$0/$0.md`
   para el mapa de títulos, `grep -n "<palabra>"` para el punto exacto, y leer solo ese
   rango de líneas.
2. Hacer el cambio con `Edit` puntual. No reescribir secciones que no cambian.
3. En la cabecera: subir `version` (1.0 → 1.1 correcciones, 2.0 cambios grandes) y
   actualizar `fecha`, o borrar la línea `fecha` para que use la de hoy.
4. `python tools/validar.py documentos/$0/$0.md`
5. `python manual.py documentos/$0/$0.md -o output/$0.pdf`
6. `python tools/comparar.py documentos/$0/$0.md output/$0.pdf --estricto`
   Debe terminar en `RESULTADO: CORRECTO`.
7. Revisión visual solo si el cambio toca tablas, figuras, código largo o la portada
   (skill `verificar-pdf`).
8. Informar: qué cambió, versión nueva, resultado de la verificación.

## Presupuesto

- Entrada típica de esta tarea: el mapa de títulos más 20-60 líneas. Si se está leyendo
  más que eso, parar y acotar.
- Si el manual está en inglés (regla 2 de `CLAUDE.md`), el cambio se escribe en inglés.

---
name: costo
description: Estima cuántos tokens cuesta trabajar un documento y propone un plan por tandas. Usar antes de leer, regenerar o traducir un documento largo, o cuando el usuario pregunta cuánto va a costar.
argument-hint: <nombre o ruta del .md>
effort: low
allowed-tools:
  - Bash(python tools/costo.py *)
  - PowerShell(python tools/costo.py *)
---

# Costo de `$ARGUMENTS`

1. `python tools/costo.py $ARGUMENTS`
2. Con esa salida, decir al usuario en 5 líneas o menos:
   - tamaño del documento en tokens;
   - qué etapas son caras **en este documento** (visión si hay figuras por describir,
     traducción si corresponde por la regla 2 de `CLAUDE.md`);
   - el plan: cuántas tandas y cuántos subagentes.
3. Si la traducción o las figuras superan ~40.000 tokens, preguntar antes de empezar.

## Qué cuesta y qué no

| Etapa | Costo | Cómo se controla |
|---|---|---|
| Scripts (`extraer`, `preparar`, `validar`, `manual`, `comparar`) | Casi nada: unas líneas de terminal. | Se usan siempre en vez de leer. |
| Leer el documento completo | Todo su tamaño, cada vez. | `grep -n "^#"` y rangos de líneas. |
| Describir figuras y páginas escaneadas | Lo más caro por unidad. | Subagente `describir-figuras` (modelo más barato; las imágenes no quedan en la conversación). |
| Traducir | Tamaño del documento en entrada y otra vez en salida. | `capitulos.py` + subagente `traductor`, por partes. |
| Revisión visual | Una o dos imágenes. | Subagente `revisor-visual`. |
| Conversación larga | Cada turno vuelve a enviar lo anterior. | Un documento por sesión; `/clear` entre documentos. |

Los números de `costo.py` son aproximados (caracteres / 3,5). No dar precios en dinero:
dependen del plan y del modelo.

---
name: verificar-pdf
description: Verifica un PDF generado antes de darlo por terminado (contenido contra su origen y revisión visual mínima). Usar al final de cualquier generación de manual.
argument-hint: <nombre>
effort: low
allowed-tools:
  - Bash(python tools/comparar.py documentos/*)
  - Bash(python tools/comparar.py extracted/*)
  - PowerShell(python tools/comparar.py documentos/*)
  - PowerShell(python tools/comparar.py extracted/*)
---

# Verificar `output/$ARGUMENTS.pdf`

Un PDF no está terminado hasta que `comparar.py` termina con código 0.

## 1. Contenido

Elegir el origen según el caso; ninguno necesita tocar `sources/`:

| Caso | Comando |
|---|---|
| Regenerado sin traducir | `python tools/comparar.py extracted/$ARGUMENTS/$ARGUMENTS.md output/$ARGUMENTS.pdf` |
| Nuevo, actualizado o traducido | `python tools/comparar.py documentos/$ARGUMENTS/$ARGUMENTS.md output/$ARGUMENTS.pdf --estricto` |

- `Faltan`, `Cifras`, `Portada`: corregir el `.md`, regenerar, repetir.
- `Aviso: sobran`: aceptable solo si es texto agregado a propósito (pies de figura,
  tablas de datos). Decirlo en el informe.
- Una falta aceptada se declara con `--ignorar "texto"`; no se calla.

## 2. Vista (una sola imagen)

```
python -c "import pymupdf; s=pymupdf.open('output/$ARGUMENTS.pdf'); n=min(4,len(s)); r=s[0].rect; o=pymupdf.open(); p=o.new_page(width=r.width*n,height=r.height); [p.show_pdf_page(pymupdf.Rect(i*r.width,0,(i+1)*r.width,r.height),s,i) for i in range(n)]; p.get_pixmap(dpi=58).save('output/revision.png')"
```

Pasar `output/revision.png` al subagente `revisor-visual`. Si el documento tiene tablas,
figuras o código largo, generar una segunda imagen con esas páginas (cambiar `range(n)`
por los índices) y pasársela también. No abrir las imágenes en esta conversación.

## 3. Informe

Tres líneas: resultado de `comparar.py`, observaciones del revisor, peso del PDF.

## Presupuesto

- Nunca leer el PDF ni revisar página por página.
- Máximo dos imágenes por verificación.

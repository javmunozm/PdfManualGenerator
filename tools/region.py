#!/usr/bin/env python3
"""Mira una franja de una página de un PDF sin abrirlo en la conversación.

Uso:
    python tools/region.py <pdf> <página> texto  "<desde>" "<hasta>"
    python tools/region.py <pdf> <página> imagen "<desde>" "<hasta>" <salida.png>

`<desde>` y `<hasta>` son textos de esa página que delimitan la franja: empieza en el
renglón de `<desde>` y termina justo antes del de `<hasta>`.

    texto    un renglón por línea, con su columna de inicio (en letras de ancho fijo), la
             fuente y el tamaño. Sirve para rehacer un recuadro de código o un diagrama de
             texto que la extracción aplanó: la sangría sale de la columna.
    imagen   recorte de la franja a 130 dpi, para pasarlo al subagente `describir-figuras`
             (un diagrama que quedó como texto suelto). No se abre en la conversación.

El PDF puede ser un original de `sources/`: usar solo el archivo que el usuario autorizó
(el hook pedirá confirmación). Código de salida: 0; 2 si no encuentra los textos o hay
un error.
"""
import argparse
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def band(page, start, end):
    """Rectángulo entre el renglón de `start` y el de `end` (excluido)."""
    import pymupdf
    a, b = page.search_for(start), page.search_for(end)
    if not a or not b:
        raise ValueError(f"no se encontró en la página: «{start if not a else end}»")
    y0 = a[0].y0 - 2
    y1 = next((r.y0 for r in b if r.y0 > y0 + 5), page.rect.height) - 2
    return pymupdf.Rect(0, y0, page.rect.width, y1)


def rows(page, clip):
    """[(y, columna, texto, fuente, tamaño)] de los renglones de la franja."""
    out = []
    for blk in page.get_text("dict", clip=clip)["blocks"]:
        for ln in blk.get("lines", []):
            text = "".join(s["text"] for s in ln["spans"])
            if text.strip():
                s0 = ln["spans"][0]
                out.append((ln["bbox"][1], ln["bbox"][0], ln["bbox"][2], text, s0["font"], s0["size"]))
    out.sort()
    if not out:
        return [], 0
    mono = sorted((x1 - x0) / len(t) for _, x0, x1, t, f, _ in out
                  if len(t) > 5 and ("ono" in f or "ourier" in f))
    cw = mono[len(mono) // 2] if mono else 0.55 * out[0][5]
    left = min(r[1] for r in out)
    return [(y, round((x0 - left) / cw), t, f, size) for y, x0, _, t, f, size in out], cw


def main():
    ap = argparse.ArgumentParser(description="Texto con posiciones o recorte de una franja de un PDF.")
    ap.add_argument("pdf")
    ap.add_argument("pagina", type=int)
    ap.add_argument("modo", choices=("texto", "imagen"))
    ap.add_argument("desde")
    ap.add_argument("hasta")
    ap.add_argument("salida", nargs="?", help="archivo .png (solo con «imagen»)")
    a = ap.parse_args()
    try:
        import pymupdf
        doc = pymupdf.open(a.pdf)
        if not 1 <= a.pagina <= doc.page_count:
            raise ValueError(f"el PDF tiene {doc.page_count} páginas")
        page = doc[a.pagina - 1]
        clip = band(page, a.desde, a.hasta)
    except Exception as e:                       # archivo inexistente, protegido, texto ausente
        print(f"No se pudo: {e}")
        return 2
    if a.modo == "imagen":
        if not a.salida:
            print("Falta la ruta del .png de salida.")
            return 2
        Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(clip=clip, dpi=130).save(a.salida)
        print(f"{a.salida}: p.{a.pagina}, franja de {round(clip.height)} pt de alto")
        return 0
    found, cw = rows(page, clip)
    for y, col, text, font, size in found:
        print(f"col {col:3d} · {font[:16]:16s} {size:4.1f} | {' ' * col}{text.strip() if col else text}")
    print(f"{len(found)} renglones · ancho de letra {cw:.2f} pt")
    return 0


if __name__ == "__main__":
    sys.exit(main())

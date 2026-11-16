#!/usr/bin/env python3
"""Arma las hojas de revisión visual de un PDF generado (ver docs/generator.md, sección 8).

Uso:
    python tools/revisar.py output/<nombre>.pdf
    python tools/revisar.py output/<nombre>.pdf --paginas 12,40 --dpi 110

Sin --paginas crea dos imágenes, cada una con hasta 4 páginas una al lado de otra:

    output/revision.png     portada, índice, primera página de contenido y última página
    output/revision2.png    las páginas con más riesgo: la tabla más cargada, la última
                            tabla, una figura y el bloque de código más largo

Con --paginas crea solo output/revision.png con esas páginas (para ver de cerca una que
el revisor marcó). Las imágenes no se abren en la conversación principal: se pasan al
subagente revisor-visual, junto con la lista de páginas que imprime este script.

Código de salida: 0 correcto, 2 error.
"""
import argparse
import sys
from pathlib import Path

import pymupdf

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def sheet(doc, pages, path, dpi):
    """Una imagen con esas páginas (números desde 1) una al lado de otra."""
    r = doc[0].rect
    out = pymupdf.open()
    page = out.new_page(width=r.width * len(pages), height=r.height)
    for i, n in enumerate(pages):
        page.show_pdf_page(pymupdf.Rect(i * r.width, 0, (i + 1) * r.width, r.height), doc, n - 1)
    page.get_pixmap(dpi=dpi).save(str(path))


def risky(doc, skip):
    """Páginas donde más se puede romper el formato: [(número, motivo)], sin repetir."""
    rules, images, code = {}, [], {}
    for page in doc:
        n = page.number + 1
        if n in skip:
            continue
        try:                          # filas de tabla: líneas horizontales finas
            lines = sum(1 for d in page.get_drawings()
                        if d["rect"].height < 1.5 and d["rect"].width > 100)
        except Exception:
            lines = 0
        if lines >= 4:
            rules[n] = lines
        if page.get_images():
            images.append(n)
        chars = sum(len(s["text"]) for b in page.get_text("dict")["blocks"]
                    for ln in b.get("lines", []) for s in ln["spans"]
                    if "Courier" in s["font"] or "Mono" in s["font"])
        if chars > 200:
            code[n] = chars
    picks = []
    if rules:
        picks.append((max(rules, key=rules.get), "la tabla con más filas"))
        picks.append((max(rules), "la última tabla"))
    if images:
        picks.append((images[0], "la primera figura"))
    if code:
        picks.append((max(code, key=code.get), "la página con más código"))
    seen, out = set(), []
    for n, why in picks:
        if n not in seen:
            seen.add(n)
            out.append((n, why))
    return out[:4]


def main():
    ap = argparse.ArgumentParser(description="Arma las hojas de revisión visual de un PDF.")
    ap.add_argument("pdf")
    ap.add_argument("--paginas", default="", help="páginas a mostrar, separadas por coma (máximo 4)")
    ap.add_argument("--dpi", type=int, default=58, help="resolución (58; 110 para ver de cerca)")
    ap.add_argument("--salida", help="carpeta de las imágenes (la del PDF)")
    a = ap.parse_args()
    pdf = Path(a.pdf)
    if not pdf.is_file():
        print(f"No existe el archivo: {pdf}")
        return 2
    folder = Path(a.salida) if a.salida else pdf.parent
    folder.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(pdf)
    total = doc.page_count
    first, second = folder / "revision.png", folder / "revision2.png"
    if a.paginas:
        try:
            pages = [int(x) for x in a.paginas.split(",") if x.strip()][:4]
        except ValueError:
            print("--paginas espera números separados por coma, por ejemplo 12,40")
            return 2
        pages = [n for n in pages if 1 <= n <= total]
        if not pages:
            print(f"Ninguna de esas páginas existe: el PDF tiene {total}")
            return 2
        sheet(doc, pages, first, a.dpi)
        print(f"{first}: páginas {', '.join(map(str, pages))} a {a.dpi} dpi")
        return 0
    toc = doc.get_toc()
    start = toc[0][2] if toc else min(2, total)           # primera página de contenido
    base = list(dict.fromkeys(n for n in (1, 2 if start > 2 else None, start, total) if n and n <= total))
    sheet(doc, base, first, a.dpi)
    names = {1: "portada", 2: "índice" if start > 2 else "contenido", start: "primera página de contenido",
             total: "última página"}
    names[1] = "portada"
    print(f"{first}: " + "; ".join(f"p.{n} {names[n]}" for n in base))
    extra = risky(doc, set(base))
    if second.exists():
        second.unlink()                                   # no dejar la de otro documento
    if extra:
        sheet(doc, [n for n, _ in extra], second, a.dpi)
        print(f"{second}: " + "; ".join(f"p.{n} {why}" for n, why in extra))
    else:
        print("Sin tablas, figuras ni código largo: no hace falta una segunda imagen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

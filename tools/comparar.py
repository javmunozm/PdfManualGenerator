#!/usr/bin/env python3
"""Compara un documento generado con su origen (ver docs/generator.md).

Uso:
    python tools/comparar.py ORIGEN GENERADO.pdf
    ORIGEN puede ser el PDF original o el .md usado para generar.

Muestra páginas, marcadores y las palabras del origen que faltan en el PDF.
"""
import re
import sys
from pathlib import Path

import pymupdf

WORD = re.compile(r"[\wáéíóúüñ]+", re.I)


def text_of(path):
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        doc = pymupdf.open(path)
        return "\n".join(p.get_text() for p in doc), doc
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)       # comentarios no se imprimen
    text = re.sub(r"\]\([^)]*\)", "]", text)                   # rutas de imágenes y URL
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)   # cabecera
    return text, None


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src_text, src_doc = text_of(sys.argv[1])
    out_doc = pymupdf.open(sys.argv[2])
    out_text = "\n".join(p.get_text() for p in out_doc)
    src = {w.lower() for w in WORD.findall(src_text)}
    out = {w.lower() for w in WORD.findall(out_text)}
    miss = sorted(src - out)
    if src_doc:
        print(f"Páginas: {src_doc.page_count} -> {out_doc.page_count} | "
              f"Marcadores: {len(src_doc.get_toc())} -> {len(out_doc.get_toc())}")
    else:
        print(f"Páginas generadas: {out_doc.page_count} | Marcadores: {len(out_doc.get_toc())}")
    print(f"Palabras distintas del origen: {len(src)} | faltan: {len(miss)} "
          f"({1 - len(miss) / (len(src) or 1):.1%} cubierto)")
    if miss:
        print("Faltan:", " ".join(miss[:60]))
    print(f"Tamaño: {Path(sys.argv[2]).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()

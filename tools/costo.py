#!/usr/bin/env python3
"""Estima cuánto cuesta trabajar un documento antes de empezar (ver docs/pipeline.md).

Uso:
    python tools/costo.py <nombre>            busca documentos/<nombre>/ y, si no, extracted/<nombre>/
    python tools/costo.py ruta/al/archivo.md [--tanda 6000]

Muestra el tamaño en tokens, lo que requiere visión (lo más caro), los pendientes y un
plan por tandas de capítulos con sus rangos de líneas, para leer o traducir por partes.

Los tokens son una aproximación (caracteres / 3,5). No lee el contenido en la terminal.
"""
import argparse
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

IMAGES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}


def tokens(text):
    return round(len(text) / 3.5)


def locate(arg):
    p = Path(arg)
    if p.is_file():
        return p
    if p.is_dir():
        return p / f"{p.name}.md"
    for base in ("documentos", "extracted"):
        cand = Path(base) / arg / f"{arg}.md"
        if cand.is_file():
            return cand
    return p


def chapters(lines):
    """[(título, primera línea, última línea, tokens)] cortando en los capítulos "#"."""
    starts, fence = [], False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            fence = not fence
        elif not fence and re.match(r"#\s", line):
            starts.append(i)
    if not starts or starts[0] != 0:
        starts.insert(0, 0)
    out = []
    for a, b in zip(starts, starts[1:] + [len(lines)]):
        title = lines[a].lstrip("# ").strip() if re.match(r"#\s", lines[a]) else "(cabecera e inicio)"
        out.append((title, a + 1, b, tokens("\n".join(lines[a:b]))))
    return out


def megapixels(folder):
    files = [f for f in folder.iterdir() if f.suffix.lower() in IMAGES] if folder.is_dir() else []
    try:
        from PIL import Image
        total = 0.0
        for f in files:
            with Image.open(f) as im:
                total += im.width * im.height / 1e6
        return len(files), total
    except Exception:
        return len(files), None


def main():
    ap = argparse.ArgumentParser(description="Estima el costo de trabajar un documento.")
    ap.add_argument("documento", help="nombre, carpeta o archivo .md")
    ap.add_argument("--tanda", type=int, default=6000, help="tokens por tanda (6000)")
    a = ap.parse_args()
    md = locate(a.documento)
    if not md.is_file():
        print(f"No se encontró el documento: {a.documento}")
        return 2
    text = md.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    total = tokens(text)
    caps = chapters(lines)
    print(f"Documento: {md} · {len(text):,} caracteres · ~{total:,} tokens · {len(caps)} partes")

    n_fig, n_scan = text.count("FIGURA: describir"), text.count("TRANSCRIBIR")
    n_img, mp = megapixels(md.parent / "assets")
    size = f" ({mp:.1f} megapíxeles)" if mp is not None else ""
    print(f"Imágenes en assets/: {n_img}{size} · por describir: {n_fig} · páginas por transcribir: {n_scan}")
    if n_fig or n_scan:
        print("  -> lo más caro del flujo. Delegar en el subagente describir-figuras: las imágenes "
              "no entran a la conversación principal.")
    n_links = len(re.findall(r"^Enlaces:", text, re.M))
    n_bold = len(re.findall(r"^\*\*[^*\n]+\*\*$", text, re.M))
    print(f"Otros pendientes probables: líneas «Enlaces:» {n_links} · rótulos en negrita sola {n_bold}")

    print("Costo aproximado por etapa (tokens):")
    print("  scripts (extraer, preparar, validar, generar, comparar)   ~300 de salida de terminal cada uno")
    print(f"  leer el documento completo                                ~{total:,} de entrada (evitar)")
    print(f"  traducir al inglés                                        ~{total:,} de entrada + "
          f"~{round(total * 0.95):,} de salida")
    print(f"Plan por tandas de hasta ~{a.tanda:,} tokens (leer o traducir una tanda por vez):")
    batch, size_b, first = [], 0, None
    rows = []
    for title, l0, l1, t in caps:
        if batch and size_b + t > a.tanda:
            rows.append((first, batch[-1][2], size_b, batch))
            batch, size_b, first = [], 0, None
        first = l0 if first is None else first
        batch.append((title, l0, l1, t))
        size_b += t
    if batch:
        rows.append((first, batch[-1][2], size_b, batch))
    for i, (l0, l1, t, items) in enumerate(rows[:20], 1):
        names = "; ".join(x[0][:28] for x in items[:3]) + (f" (+{len(items) - 3})" if len(items) > 3 else "")
        flag = "  <- parte más grande que la tanda" if t > a.tanda * 1.2 else ""
        print(f"  {i:>2}. l.{l0}-{l1}  ~{t:,}  {names}{flag}")
    if len(rows) > 20:
        print(f"  ... y {len(rows) - 20} tandas más")
    return 0


if __name__ == "__main__":
    sys.exit(main())

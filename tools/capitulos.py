#!/usr/bin/env python3
"""Parte un .md en archivos por capítulo y los vuelve a unir (ver docs/pipeline.md).

Uso:
    python tools/capitulos.py partir documentos/<n>/<n>.md [--tanda 6000]
    python tools/capitulos.py unir   documentos/<n>/<n>.md

`partir` crea documentos/<n>/partes/00.md, 01.md... (00 trae la cabecera). Sirve para
trabajar un documento largo por partes: cada parte se lee y se reescribe completa, sin
cargar el resto. Un capítulo más grande que la tanda se divide en sus secciones "##".

`unir` reconstruye el .md con las partes en orden. El anterior queda como
<n>.anterior.md (es el original para tools/comparar_traduccion.py).

Código de salida: 0 correcto, 2 error.
"""
import argparse
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def cut_points(lines, level):
    """Índices de las líneas que abren un título de ese nivel (fuera de código)."""
    out, fence = [], False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            fence = not fence
        elif not fence and re.match(r"#{%d}\s" % level, line):
            out.append(i)
    return out


def split(lines, limit):
    """[(primera línea, última línea)] por capítulo; los grandes, por sección."""
    def ranges(cuts, a, b):
        cuts = [a] + [c for c in cuts if c > a]
        return list(zip(cuts, cuts[1:] + [b]))
    def size(a, b):
        return len("\n".join(lines[a:b])) / 3.5
    parts = []
    for a, b in ranges(cut_points(lines, 1), 0, len(lines)):
        if size(a, b) <= limit:
            parts.append((a, b))
            continue
        group = None                                  # secciones seguidas, hasta llenar la tanda
        for x, y in ranges([a + i for i in cut_points(lines[a:b], 2)], a, b):
            if group and size(group[0], y) <= limit:
                group = (group[0], y)
            else:
                if group:
                    parts.append(group)
                group = (x, y)
        parts.append(group)
    return parts


def main():
    ap = argparse.ArgumentParser(description="Parte un .md por capítulos y lo vuelve a unir.")
    ap.add_argument("accion", choices=("partir", "unir"))
    ap.add_argument("archivo")
    ap.add_argument("--tanda", type=int, default=6000, help="tokens máximos por parte (6000)")
    ap.add_argument("--forzar", action="store_true", help="partir aunque ya exista partes/")
    a = ap.parse_args()
    md = Path(a.archivo)
    folder = md.parent / "partes"
    if a.accion == "partir":
        if not md.is_file():
            print(f"No existe el archivo: {md}")
            return 2
        if folder.is_dir() and any(folder.glob("*.md")) and not a.forzar:
            print(f"Ya existe {folder} con partes (puede haber trabajo hecho). Usa --forzar para rehacerlas.")
            return 2
        lines = md.read_text(encoding="utf-8-sig").splitlines()
        folder.mkdir(exist_ok=True)
        for old in folder.glob("*.md"):
            old.unlink()
        parts = split(lines, a.tanda)
        for n, (x, y) in enumerate(parts):
            body = "\n".join(lines[x:y]).strip("\n") + "\n"
            (folder / f"{n:02d}.md").write_text(body, encoding="utf-8", newline="\n")
            title = next((ln.lstrip("# ").strip() for ln in lines[x:y] if re.match(r"#{1,2}\s", ln)), "(cabecera)")
            print(f"  {n:02d}.md  l.{x + 1}-{y}  ~{round(len(body) / 3.5):,} tokens  {title[:50]}")
        print(f"{len(parts)} partes en {folder}")
        return 0
    files = sorted(folder.glob("*.md")) if folder.is_dir() else []
    if not files:
        print(f"No hay partes en {folder}")
        return 2
    text = "\n\n".join(f.read_text(encoding="utf-8-sig").strip("\n") for f in files) + "\n"
    if md.exists():
        backup = md.with_name(md.stem + ".anterior.md")
        backup.write_bytes(md.read_bytes())
        print(f"Anterior guardado como {backup}")
    md.write_text(text, encoding="utf-8", newline="\n")
    print(f"{md}: {len(files)} partes unidas, ~{round(len(text) / 3.5):,} tokens. "
          "Borrar partes/ cuando la verificación pase.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

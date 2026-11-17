#!/usr/bin/env python3
"""Resume en pocas líneas en qué está cada documento del flujo (ver docs/pipeline.md).

Uso:
    python tools/estado.py            una línea por documento que tiene algo pendiente
    python tools/estado.py --todo     también los que están terminados

Mira solo extracted/, documentos/ y output/ (nunca sources/) y dice, por documento
(cada uno con su carpeta en las tres: extracted/<n>/, documentos/<n>/ y output/<n>/):

    extraído, sin preparar          hay extracted/<n>/ y no documentos/<n>/
    pendientes en la extracción     quedan figuras por describir, páginas por transcribir
                                    o símbolos sin identificar
    traducción en curso             existe documentos/<n>/partes/
    sin PDF                         hay documentos/<n>/<n>.md y no output/<n>/<n>.pdf
    PDF desactualizado              el .md es más nuevo que su PDF
    sin verificar / verificación fallida   según el registro que deja tools/comparar.py

Lo usan los hooks de inicio y de cierre de sesión (.claude/hooks/). Código de salida: 0.
"""
import argparse
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

MARKS = (("![FIGURA: describir]", "figuras por describir"), ("TRANSCRIBIR]", "páginas por transcribir"),
         ("[SIMBOLO?]", "símbolos sin identificar"))
RECORD = ".comparar.json"            # lo escribe tools/comparar.py junto al PDF


def read_record(folder):
    try:
        return json.loads((Path(folder) / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def status(root="."):
    """[(nombre, [problemas])] de cada documento; lista vacía = terminado."""
    root = Path(root)
    ext, docs, out = root / "extracted", root / "documentos", root / "output"
    names = sorted({p.name for base in (ext, docs) if base.is_dir() for p in base.iterdir() if p.is_dir()})
    result = []
    for n in names:
        todo = []
        # cada documento tiene su carpeta en output/, con su PDF, su registro y sus hojas
        src_md, md, pdf = ext / n / f"{n}.md", docs / n / f"{n}.md", out / n / f"{n}.pdf"
        record = read_record(pdf.parent)
        if src_md.is_file():
            try:
                text = src_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            marks = [f"{text.count(k)} {what}" for k, what in MARKS if text.count(k)]
            if marks:
                todo.append("pendientes en la extracción: " + ", ".join(marks))
            if not md.is_file():
                todo.append("extraído, sin preparar")
        if md.is_file():
            parts = docs / n / "partes"
            if parts.is_dir() and any(parts.glob("*.md")):
                todo.append(f"traducción en curso ({len(list(parts.glob('*.md')))} partes)")
            if not pdf.is_file():
                todo.append("sin PDF")
            elif md.stat().st_mtime > pdf.stat().st_mtime + 1:
                todo.append("PDF desactualizado (el .md es más nuevo)")
            else:
                rec = record.get(pdf.name)
                if not rec or abs(rec.get("mtime", 0) - pdf.stat().st_mtime) > 1:
                    todo.append("PDF sin verificar con tools/comparar.py")
                elif rec.get("resultado") != "CORRECTO":
                    todo.append("la última verificación falló")
        result.append((n, todo))
    return result


def stale(root="."):
    """Documentos cuyo PDF no refleja su .md o cuya verificación falló (hook de cierre).
    Un documento sin PDF todavía, o con la traducción en curso, está en trabajo: no cuenta."""
    out = []
    for n, todo in status(root):
        if any(t.startswith("traducción en curso") or t == "sin PDF" for t in todo):
            continue
        bad = [t for t in todo if t.startswith(("PDF desactualizado", "la última verificación"))]
        if bad:
            out.append((n, bad))
    return out


def main():
    ap = argparse.ArgumentParser(description="Estado de los documentos del flujo.")
    ap.add_argument("--todo", action="store_true", help="mostrar también los terminados")
    ap.add_argument("--raiz", default=".")
    a = ap.parse_args()
    rows = status(a.raiz)
    if not rows:
        print("Sin documentos en extracted/ ni en documentos/.")
        return 0
    open_ = [(n, t) for n, t in rows if t]
    for n, todo in (rows if a.todo else open_)[:15]:
        print(f"{n}: " + ("; ".join(todo) if todo else "terminado (PDF al día y verificado)"))
    if len(open_) > 15 and not a.todo:
        print(f"... y {len(open_) - 15} más")
    print(f"estado: {len(rows)} documentos, {len(open_)} con algo pendiente")
    return 0


if __name__ == "__main__":
    sys.exit(main())

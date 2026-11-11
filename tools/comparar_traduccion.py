#!/usr/bin/env python3
"""Verifica una traducción sin leerla: compara lo que no debe cambiar al traducir.

Uso:
    python tools/comparar_traduccion.py ORIGINAL.md TRADUCIDO.md

tools/comparar.py compara palabras y no sirve entre dos idiomas. Aquí se compara la
estructura: títulos (niveles y orden), bloques de código y código en línea (idénticos),
imágenes, enlaces, tablas, cuadros, listas y cifras. Si el texto traducido es mucho más
corto que el original, avisa: puede haberse resumido.

Código de salida: 0 coincide, 1 hay diferencias, 2 error.
"""
import re
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def features(text):
    lines = text.splitlines()
    i = 0
    if lines and lines[0].strip() == "---":                # la cabecera se compara aparte
        i = next((j for j in range(1, len(lines)) if lines[j].strip() == "---"), 0) + 1
    f = {"títulos": [], "bloques de código": [], "código en línea": Counter(), "imágenes": [],
         "enlaces": Counter(), "tablas": [], "cuadros": [], "ítems de lista": 0, "cifras": Counter()}
    keys = sorted(ln.split(":", 1)[0].strip() for ln in lines[1:max(i - 1, 0)] if ":" in ln)
    prose = []
    while i < len(lines):
        st = lines[i].strip()
        if st.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            f["bloques de código"].append("\n".join(lines[i + 1:j]))
            i = j + 1
            continue
        if st.startswith("<!--"):                          # los comentarios no se traducen ni comparan
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if re.match(r"#{1,6}\s", st):
            f["títulos"].append(len(st) - len(st.lstrip("#")))
        elif st.startswith("|"):
            rows = 0
            cols = st.count("|")
            while i < len(lines) and lines[i].strip().startswith("|"):
                prose.append(lines[i])
                rows += 1
                i += 1
            f["tablas"].append((rows, cols))
            continue
        elif re.match(r"\s*([-*+]|\d+[.)])\s", lines[i]):
            f["ítems de lista"] += 1
        m = re.match(r">\s*\[!(\w+)\]", st)
        if m:
            f["cuadros"].append(m.group(1).upper())
        prose.append(lines[i])
        i += 1
    body = "\n".join(prose)
    f["código en línea"].update(re.findall(r"`([^`\n]+)`", body))
    f["imágenes"] = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
    f["enlaces"].update(re.findall(r"(?<!!)\[[^\]]+\]\(([^)\s]+)\)", body))
    plain = re.sub(r"`[^`\n]+`|\]\([^)]*\)", " ", body)    # sin código ni rutas
    f["cifras"].update(re.sub(r"[.,]", "", n) for n in re.findall(r"\d+(?:[.,]\d+)*", plain))
    return f, keys, len(re.sub(r"\s+", " ", plain))


def show(x):
    s = repr(x) if not isinstance(x, str) else x.replace("\n", " ⏎ ")
    return s if len(s) <= 70 else s[:67] + "..."


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    for p in (a, b):
        if not p.is_file():
            print(f"No existe el archivo: {p}")
            return 2
    fa, ka, la = features(a.read_text(encoding="utf-8-sig"))
    fb, kb, lb = features(b.read_text(encoding="utf-8-sig"))
    bad = 0
    if ka != kb:
        bad += 1
        print(f"cabecera: cambian las claves · solo en el original: {sorted(set(ka) - set(kb))} · "
              f"solo en la traducción: {sorted(set(kb) - set(ka))}")
    for name in fa:
        x, y = fa[name], fb[name]
        if x == y:
            continue
        bad += 1
        if isinstance(x, Counter):
            gone, new = x - y, y - x
            print(f"{name}: faltan {sum(gone.values())} · sobran {sum(new.values())}"
                  + (f" · falta: {', '.join(show(k) for k in list(gone)[:5])}" if gone else "")
                  + (f" · sobra: {', '.join(show(k) for k in list(new)[:5])}" if new else ""))
        elif isinstance(x, list):
            k = next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
            p, q = (x[k] if k < len(x) else "(no hay)"), (y[k] if k < len(y) else "(no hay)")
            if isinstance(p, str) and isinstance(q, str) and "\n" in p + q:   # el renglón que cambió
                pl, ql = p.split("\n"), q.split("\n")
                j = next((i for i, (u, v) in enumerate(zip(pl, ql)) if u != v), min(len(pl), len(ql)) - 1)
                p, q = pl[min(j, len(pl) - 1)].strip(), ql[min(j, len(ql) - 1)].strip()
            print(f"{name}: {len(x)} en el original, {len(y)} en la traducción · primera diferencia "
                  f"en el n.º {k + 1}: {show(p)} -> {show(q)}")
        else:
            print(f"{name}: {x} en el original, {y} en la traducción")
    ratio = lb / (la or 1)
    note = ""
    if not 0.65 <= ratio <= 1.35:
        note = " · AVISO: tamaño muy distinto; revisar que no se haya resumido ni duplicado"
    print(f"Texto: {la:,} caracteres -> {lb:,} ({ratio:.0%}){note}")
    print("RESULTADO: " + ("FALLA (" + str(bad) + " diferencias de estructura)" if bad else "CORRECTO"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

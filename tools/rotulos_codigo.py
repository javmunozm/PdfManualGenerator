#!/usr/bin/env python3
"""Saca del código los rótulos de recuadro que la extracción dejó dentro.

Uso:
    python tools/rotulos_codigo.py documentos/<n>/<n>.md --ver     solo cuenta, no escribe
    python tools/rotulos_codigo.py documentos/<n>/<n>.md           aplica
    python tools/rotulos_codigo.py documentos/<n>/<n>.md --todos   todo bloque empieza con rótulo

En muchos manuales cada recuadro de código lleva arriba un rótulo: el nombre del archivo
(`API/Program.cs`) o «TERMINAL». Al extraer, ese rótulo queda como primera línea del
código, y dos cosas más se cuelan dentro del bloque:

    … API/Program.cs      el rótulo que el original repite cuando el recuadro sigue en
                          la página siguiente: queda en medio del código
    otro rótulo           el de un segundo recuadro pegado al anterior: dos archivos
                          distintos en un mismo bloque

Quien copia el código se lleva esas líneas. Este script:

1. une el bloque que empieza con «… rótulo» al bloque anterior del mismo rótulo (un
   recuadro de tres páginas o más; los marcadores `<!-- p.N -->` quedan después);
2. quita los «… rótulo» de continuación (y la línea vacía que les sigue);
3. separa los recuadros pegados, cada uno en su bloque;
4. pasa el rótulo a la línea que abre el bloque (```API/Program.cs), que manual.py
   dibuja como título del recuadro y no como código.

Un rótulo es la primera línea de un recuadro, sin sangría y seguida de una línea vacía.
Con --todos también vale sin la línea vacía: usarlo solo si en --ver se ve que todos los
bloques «sin rótulo» empiezan en realidad con uno. No se pierde ni se cambia código.
Código de salida: 0; 2 si hay un error.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

CONT = re.compile(r"…\s*(\S.*)")
MARKER = re.compile(r"<!-- p\.\d+ -->")


def segments(lines):
    """[["text", líneas] | ["code", líneas del cuerpo]]. Un bloque sin cerrar, o que ya
    tiene algo tras ``` en la línea que lo abre, queda como texto: no se toca."""
    out, i = [], 0
    while i < len(lines):
        j = i + 1
        if lines[i].startswith("```"):
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            if j < len(lines) and lines[i].strip() == "```":
                out.append(["code", lines[i + 1:j]])
                i = j + 1
                continue
            j = min(j + 1, len(lines))
        if out and out[-1][0] == "text":
            out[-1][1].extend(lines[i:j])
        else:
            out.append(["text", lines[i:j]])
        i = j
    return out


def continuation(line):
    m = CONT.fullmatch(line.strip()) if line and not line.startswith((" ", "\t")) else None
    return m.group(1) if m else None


def first_label(body, every):
    """Rótulo con que empieza el recuadro, o None."""
    if not body or not body[0].strip() or body[0].startswith((" ", "\t")) or len(body[0]) > 90:
        return None
    return body[0] if every or (len(body) > 2 and body[1] == "") else None


def name_of(label):
    """El rótulo sin la marca de continuación («… API/Program.cs» -> «API/Program.cs»)."""
    return continuation(label) or label


def join_across_pages(segs, done):
    """Un bloque que empieza con «… rótulo» sigue al último recuadro del bloque anterior,
    si es de ese rótulo y entre los dos solo hay marcadores de página. `segs` trae los
    bloques ya separados en recuadros: ["code", [[rótulo, código], ...]]."""
    k = 2
    while k < len(segs):
        prev, mid, cur = segs[k - 2], segs[k - 1], segs[k]
        label = continuation(cur[1][0][0]) if cur[0] == "code" else None
        if label and prev[0] == "code" and mid[0] == "text" \
                and all(not l.strip() or MARKER.fullmatch(l.strip()) for l in mid[1]) \
                and label == name_of(prev[1][-1][0]):
            prev[1][-1][1].extend(cur[1][0][1])
            prev[1].extend(cur[1][1:])
            del segs[k]
            done["bloques unidos (recuadro que sigue en otra página)"] += 1
            done["rótulos pasados al título del bloque"] -= 1
            if k < len(segs) and segs[k][0] == "text":       # los marcadores, después
                mid[1].extend(segs.pop(k)[1])
        else:
            k += 1
    return segs


def split_block(body, every, done, elsewhere=frozenset()):
    """[[rótulo, código]] de un bloque: sin continuaciones y con cada recuadro aparte.
    `elsewhere`: rótulos que tienen un «… X» en otro bloque del documento."""
    label = first_label(body, every)
    if label is None:
        done["bloques sin rótulo (no se tocaron)"] += 1
        return [["", body]]
    boxes, k = [[label, []]], 2 if len(body) > 1 and body[1] == "" else 1
    # Un «… X» más abajo confirma que la línea «X» de este bloque es un rótulo, aunque no
    # tenga líneas vacías alrededor (dos recuadros pegados sin separación). Si el «… X»
    # está en otro bloque (el recuadro sigue en la página siguiente), «X» además tiene que
    # llevar una línea vacía después, como todo rótulo: así no se parte una lista de rutas.
    confirmed = {continuation(l) for l in body} - {None}
    while k < len(body):
        line = body[k]
        if continuation(line) == name_of(boxes[-1][0]):
            done["rótulos «… nombre» de cambio de página quitados"] += 1
            k += 2 if k + 1 < len(body) and body[k + 1] == "" else 1
            continue
        if line != name_of(boxes[-1][0]) and (line in confirmed or (
                line in elsewhere and k + 1 < len(body) and body[k + 1] == "")):
            while boxes[-1][1] and boxes[-1][1][-1] == "":
                boxes[-1][1].pop()
            boxes.append([line, []])
            done["recuadros pegados separados"] += 1
            k += 2 if k + 1 < len(body) and body[k + 1] == "" else 1
            continue
        # otro recuadro: tras dos líneas vacías, un rótulo con su línea vacía y código
        if boxes[-1][1][-2:] == ["", ""] and first_label(body[k:], False) and body[k + 2].strip():
            while boxes[-1][1] and boxes[-1][1][-1] == "":
                boxes[-1][1].pop()
            boxes.append([line, []])
            done["recuadros pegados separados"] += 1
            k += 2
            continue
        boxes[-1][1].append(line)
        k += 1
    while boxes[-1][1] and boxes[-1][1][-1] == "":
        boxes[-1][1].pop()
    done["rótulos pasados al título del bloque"] += len(boxes)
    return boxes


def convert(text, every=False):
    done = Counter()
    raw = segments(text.split("\n"))
    elsewhere = frozenset(continuation(l) for kind, body in raw if kind == "code" for l in body) - {None}
    segs = [[kind, split_block(body, every, done, elsewhere) if kind == "code" else body]
            for kind, body in raw]
    out = []
    for kind, body in join_across_pages(segs, done):
        if kind == "text":
            out.extend(body)
            continue
        for n, (label, code) in enumerate(body):
            if n:
                out.append("")
            out.extend(["```" + label.replace("`", "'"), *code, "```"])
    return "\n".join(out), +done


def main():
    ap = argparse.ArgumentParser(description="Pasa los rótulos de los recuadros de código al título del bloque.")
    ap.add_argument("md")
    ap.add_argument("--ver", action="store_true", help="solo contar; no escribe")
    ap.add_argument("--todos", action="store_true",
                    help="la primera línea de todo bloque es su rótulo, tenga o no una línea vacía después")
    a = ap.parse_args()
    path = Path(a.md)
    if not path.is_file():
        print(f"No existe el archivo: {path}")
        return 2
    text = path.read_text(encoding="utf-8")
    new, done = convert(text, a.todos)
    print(" · ".join(f"{k}: {v}" for k, v in done.items()) or "Sin bloques de código.")
    if a.ver:
        shown = 0
        for kind, body in segments(text.split("\n")):
            if kind == "code" and first_label(body, False) is None and shown < 30:
                print(f"  sin rótulo reconocido: {body[0][:80] if body else ''}")
                shown += 1
    elif new != text:
        path.write_text(new, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

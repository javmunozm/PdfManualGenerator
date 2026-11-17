#!/usr/bin/env python3
"""Extrae un documento de sources/ a Markdown compacto y completo.

Formatos: pdf, docx, pptx, xlsx, json, md, txt, csv/tsv.

Uso:
    python tools/extraer.py sources/archivo.pdf
    python tools/extraer.py sources/datos.json --salida extracted

Genera, en extracted/<nombre>/:
    <nombre>.md   contenido en Markdown compatible con manual.py
    assets/       imágenes, gráficos vectoriales y páginas escaneadas
    reporte.md    resumen corto: qué se extrajo y qué falta revisar

Método y reglas: docs/extractor.md
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import pymupdf

for _s in (sys.stdout, sys.stderr):   # la consola de Windows (cp1252) no admite todo Unicode
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

MONO = re.compile(r"mono|courier|consol|code|menlo", re.I)
BULLET = re.compile(r"^\s*[•●▪◦‣∙·–]\s*")
LEADER = re.compile(r"(?:\.\s*){5,}")
CAPTION = re.compile(r"^(figura|fig\.|imagen|gr[aá]fico|diagrama|esquema)\b", re.I)
NUM_HEAD = re.compile(r"^\d+(\.\d+)*\.?\s+\S")
PAGE_NUM = re.compile(r"^(p[aá]g(ina|e)?\.?\s*)?\d+(\s*(de|/|of)\s*\d+)?$", re.I)
WORD = re.compile(r"[\wáéíóúüñ]+", re.I)
MARGIN = 0.065  # franja superior/inferior donde viven encabezados y pies
BAND = 0.15     # franja donde se busca texto repetido en la misma posición
COL_GAP = 9     # hueco mínimo (pt) entre columnas; un espacio normal mide menos
MARK = "[SIMBOLO?]"   # símbolo sin mapa de caracteres en el original (era NUL en el texto)
MAX_ROWS = 2000       # filas por hoja o CSV; 0 = todas (opción --filas)
JUNK_TITLE = re.compile(r"^(\(?anonymous\)?|untitled|\(?unspecified\)?|sin t[ií]tulo|microsoft word - .*|"
                        r"document\d*|documento\d*|presentaci[oó]n\d*|presentation\d*|"
                        r".*\.(docx?|pptx?|xlsx?|pdf|indd|tex|dvi|odt))$", re.I)
# Superíndices y subíndices que existen como caracteres propios
SUP = str.maketrans("0123456789+-=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ")
SUB = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")


class ExtractError(Exception):
    """El archivo no se puede extraer; el mensaje dice por qué."""


def norm(s):
    return re.sub(r"\s+", " ", s.replace("­", "")).strip()


def key(s):
    return re.sub(r"\d+", "#", norm(s).lower())


def words(s):
    """Palabras con repetición. NFKC: «10³» y «103» cuentan como la misma palabra, porque
    el texto plano del PDF trae el superíndice aplanado y el Markdown no."""
    return Counter(w.lower() for w in WORD.findall(unicodedata.normalize("NFKC", s)))


def fix_scripts(spans, lost=None):
    """Superíndices y subíndices como caracteres propios (10³, H₂O): el texto plano los
    aplana y cambia el significado (E4). Un tramo es superíndice o subíndice si es corto,
    de letra más chica que el resto del renglón y está más arriba o más abajo. Si alguno
    de sus caracteres no existe como superíndice, queda igual y se anota en `lost`."""
    real = [s for s in spans if s["text"].strip()]
    if len(real) < 2:
        return spans
    main = max(real, key=lambda s: s["size"] * len(s["text"].strip()))
    out = []
    for s in spans:
        t, table = s["text"].strip(), None
        if t and s is not main and len(t) <= 6 and s["size"] <= 0.85 * main["size"]:
            dy = s.get("origin", (0, 0))[1] - main.get("origin", (0, 0))[1]
            if s["flags"] & 1 or dy < -0.15 * main["size"]:
                table = SUP
            elif dy > 0.08 * main["size"]:
                table = SUB
        if table:
            if all(ord(c) in table for c in t):
                s = dict(s, text=s["text"].translate(table))
            elif lost is not None:
                lost.append(t)
        out.append(s)
    return out


# ---------------------------------------------------------------------------
def span_md(spans):
    """Une los fragmentos de una línea conservando negrita, cursiva y código."""
    out = []
    for sp in spans:
        t = sp["text"]
        core = t.strip()
        if not core:
            out.append(t)
            continue
        lead, trail = t[: len(t) - len(t.lstrip())], t[len(t.rstrip()):]
        font = sp["font"].lower()
        if MONO.search(font):
            core = f"`{core}`"
        else:
            if sp["flags"] & 16 or "bold" in font:
                core = f"**{core}**"
            if sp["flags"] & 2 or "italic" in font or "oblique" in font:
                core = f"*{core}*"
        out.append(lead + core + trail)
    s = "".join(out)
    s = s.replace("****", "").replace("``", "")
    s = re.sub(r"\*\*(\s+)\*\*", r"\1", s)
    s = re.sub(r"`(\s+)`", r"\1", s)
    s = re.sub(r"(?<![\*\s])\*(\s+)\*(?![\*\s])", r"\1", s)
    return s


def block_lines(b, lost=None):
    """Devuelve líneas (texto plano, texto md, bbox) y rasgos del bloque."""
    lines, sizes, mono, bold = [], [], True, True
    for ln in b["lines"]:
        spans = fix_scripts(ln["spans"], lost)
        plain = "".join(s["text"] for s in spans)
        if not plain.strip():
            continue
        lines.append((plain, span_md(spans), ln["bbox"]))
        for s in ln["spans"]:
            if s["text"].strip():
                sizes.append(s["size"])
                mono &= bool(MONO.search(s["font"]))
                bold &= bool(s["flags"] & 16 or "bold" in s["font"].lower())
    return lines, (max(sizes) if sizes else 0), mono and bool(sizes), bold and bool(sizes)


def body_size(doc):
    c = Counter()
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for s in ln["spans"]:
                    if not MONO.search(s["font"]):  # el código no define el tamaño normal
                        c[round(s["size"], 1)] += len(s["text"].strip())
    return c.most_common(1)[0][0] if c else 10


def zone_of(y0, y1, h):
    return "top" if y1 < h * MARGIN else "bot" if y0 > h * (1 - MARGIN) else None


def band_of(y0, y1, h):
    return "top" if y1 < h * BAND else "bot" if y0 > h * (1 - BAND) else None


def slot_key(text):
    """Identidad de un renglón repetido: su texto exacto, o "contador de páginas".
    No se enmascaran cifras: "Ejercicio 3" y "Ejercicio 4" son renglones distintos."""
    return "\x00pagina" if PAGE_NUM.match(text) else text.lower()


def find_boilerplate(doc, body, toc=()):
    """Reúne lo necesario para reconocer encabezados y pies repetidos.

    Una línea de la franja de encabezado/pie se elimina solo si se repite en otra
    página, si es un número de página o si repite un título o una línea del cuerpo.
    El texto que aparece una sola vez (una nota al pie) se conserva en el cuerpo.
    Más adentro de esa franja se elimina además el renglón que está en el extremo de la
    página y aparece idéntico (o es el contador de páginas) en la misma posición en la
    mitad de las páginas o más: un pie colocado lejos del borde. Los títulos, de letra
    más grande, no entran en esa regla.
    """
    seen, texts, slots, right = Counter(), set(), {}, 0
    for page in doc:
        h = page.rect.height
        page_keys, inner = set(), []
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                text = norm("".join(s["text"] for s in ln["spans"]))
                if not text:
                    continue
                y0, y1 = ln["bbox"][1], ln["bbox"][3]
                if zone_of(y0, y1, h):
                    page_keys.add((zone_of(y0, y1, h), key(text)))
                else:
                    texts.add(text.lower())
                    if not all(MONO.search(s["font"]) for s in ln["spans"] if s["text"].strip()):
                        right = max(right, ln["bbox"][2])   # borde del texto normal
                    inner.append(((y0 + y1) / 2, band_of(y0, y1, h), text,
                                  max(s["size"] for s in ln["spans"])))
        inner.sort()
        for y, band, text, size in inner[:2] + inner[-2:]:   # solo los renglones extremos
            if band:
                slots.setdefault((band, slot_key(text)), {})[page.number] = (y, size)
        seen.update(page_keys)
    need = max(3, 0.5 * doc.page_count)
    fixed = {}
    for k, per_page in slots.items():
        ys = sorted(v[0] for v in per_page.values())
        small = max(v[1] for v in per_page.values()) <= body * 1.05
        if len(ys) >= need and ys[-1] - ys[0] <= 4 and small:
            fixed[k] = ys[len(ys) // 2]      # los títulos (letra grande) no entran
    return dict(seen=seen, texts=texts, fixed=fixed, right=right,
                titles={norm(x[1]).lower() for x in toc})


def is_boiler(line_text, bbox, page_h, bp):
    """¿Es un encabezado o pie repetido? (criterio en find_boilerplate)"""
    t = norm(line_text)
    k, y0, y1 = key(t), bbox[1], bbox[3]
    zone = zone_of(y0, y1, page_h)
    if zone and (PAGE_NUM.match(t) or bp["seen"][(zone, k)] >= 2
                 or t.lower() in bp["titles"] or t.lower() in bp["texts"]):
        return True
    band = band_of(y0, y1, page_h)
    y = bp["fixed"].get((band, slot_key(t))) if band else None
    return y is not None and abs((y0 + y1) / 2 - y) <= 4


# ---------------------------------------------------------------------------
def heading_level(text, size, bold, nlines, body, toc_levels):
    k = key(text)
    if k in toc_levels:
        return min(toc_levels[k], 3)
    if nlines > 2 or len(text) > 140:
        return 0
    r = size / body
    if len(toc_levels) >= 5:
        # Con marcadores, solo se agregan títulos extra muy claros (negrita y grandes)
        return 3 if bold and r >= 1.25 else 0
    if r >= 1.6:
        return 1
    if r >= 1.25:
        return 2
    if r >= 1.1 and (bold or len(text) < 90):
        return 3
    return 0


def mark_key(s):
    """Clave para comparar un título con un marcador: sin mayúsculas ni puntuación y con
    las cifras como «#» («PARTE I · CAPÍTULO 1» -> «parte i capítulo #»)."""
    return re.sub(r"[^\w#]+", " ", key(s)).strip()


BOLD_LINE = re.compile(r"\*\*[^*]+\*\*(?:\s+\*\*[^*]+\*\*)*")


def toc_by_page(toc):
    """{página: [(clave, nivel)]} de los marcadores del PDF, con el nivel desde 1."""
    out = {}
    if toc:
        top = min(x[0] for x in toc)
        for lvl, title, page in toc:
            out.setdefault(page, []).append((mark_key(title), lvl - top + 1))
    return out


def bookmark_head(kept, size, body, marks):
    """Título que coincide con un marcador del PDF en su misma página (E20): los primeros
    renglones del bloque terminan con el texto del marcador. Así se reconoce «PARTE I ·
    CAPÍTULO 1 Introducción» con el marcador «1. Introducción», y el título de dos
    renglones que quedó en el mismo bloque que su párrafo. Los renglones del título van
    en negrita (o el bloque entero es de letra más grande) y lo que sobra antes del texto
    del marcador es corto (un antetítulo). Devuelve (renglones del título, nivel) o None."""
    for j in range(1, min(4, len(kept)) + 1):
        bold = all(BOLD_LINE.fullmatch(md.strip()) for _, md, _ in kept[:j])
        if not bold and not (j == len(kept) and size >= 1.1 * body):
            break
        k = mark_key(" ".join(p for p, _, _ in kept[:j]))
        for m, lvl in marks:
            if m and (k == m or (k.endswith(" " + m) and len(k) - len(m) <= 30)):
                marks.remove((m, lvl))
                return j, lvl
    return None


def glue(out, ln, vocab=None, kept=None):
    """Agrega un renglón al texto anterior. Si el anterior termina en guion y este sigue
    en minúscula, puede ser un corte de renglón (docu-/mentación) o un guion de verdad
    (físico-/químico). Se une sin guion solo si la palabra unida existe en otra parte del
    documento (`vocab`); si no, el guion se conserva y la palabra se anota en `kept` (E8).
    Sin `vocab` se une siempre."""
    if out.endswith("-") and ln[:1].islower():
        a, b = re.search(r"[^\W\d_]+(?=-$)", out), re.match(r"[^\W\d_]+", ln)
        whole = (a.group(0) + b.group(0)).lower() if a and b else ""
        if vocab is None or not whole or whole in vocab:
            return out[:-1] + ln
        if kept is not None:
            kept.append(f"{a.group(0)}-{b.group(0)}")
        return out + ln
    return f"{out} {ln}" if out else ln


def join_lines(md_lines, vocab=None, kept=None):
    """Une las líneas de un párrafo y corrige guiones de corte."""
    out = ""
    for ln in md_lines:
        out = glue(out, ln.strip(), vocab, kept)
    return norm(out)


def save_image(doc, xref, assets, stem, page, bb):
    """Guarda una imagen del PDF y devuelve el nombre del archivo (E10). Un JPEG se guarda
    tal cual (pesa menos que su PNG); una imagen con transparencia conserva su canal alfa
    en vez de quedar con fondo negro."""
    try:
        info = doc.extract_image(xref) if xref else None
        if info and not info.get("smask") and info.get("ext") in ("jpeg", "jpg") \
                and info.get("colorspace") in (1, 3):
            (assets / f"{stem}.jpg").write_bytes(info["image"])
            return f"{stem}.jpg"
        pix = pymupdf.Pixmap(doc, xref)
        if pix.colorspace and pix.colorspace.n > 3:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        if info and info.get("smask"):
            if pix.alpha:
                pix = pymupdf.Pixmap(pix, 0)
            pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, info["smask"]))
        pix.save(str(assets / f"{stem}.png"))
    except Exception:
        page.get_pixmap(clip=bb, dpi=150).save(str(assets / f"{stem}.png"))
    return f"{stem}.png"


# ---------------------------------------------------------------------------
# Bloques de código
# ---------------------------------------------------------------------------
CODE_COMMENT = re.compile(r"\s*(#|//|/\*|\*|--|<!--|rem\b)", re.I)


def unfinished(line):
    """¿Un renglón de código quedó a medias? Comillas sin cerrar, más paréntesis abiertos
    que cerrados, o termina en una coma o un operador. Un comentario nunca cuenta: lo que
    sigue puede ser código, y unirlo lo dejaría dentro del comentario."""
    if CODE_COMMENT.match(line):
        return False
    s = re.sub(r"(?<=\w)'(?=\w)", "", line.rstrip())      # apóstrofos dentro de una palabra
    if s.count('"') % 2 or s.count("'") % 2:
        return True
    if sum(s.count(c) for c in "([{") > sum(s.count(c) for c in ")]}"):
        return True
    return s.endswith((",", "&&", "||", "|", "+", "="))


# Finales con los que un autor sigue a propósito en el renglón de abajo (argumentos,
# operadores, una lambda): una continuación +4 después de ellos es formato, no un corte.
AUTHOR_BREAK = (",", "(", "{", "[", "=", "=>", "+", "-", "*", "&&", "||", "|", "\\", ":", ";",
                "?", "->", "<", ">", "&")
CONTROL = re.compile(r"\s*(}\s*)?(if|else if|while|for|foreach|using|catch|lock|switch|fixed)\b")


def wrapped(prev, nxt, counts):
    """¿El renglón siguiente, que el original corrió 4 letras más adentro, es la
    continuación de un renglón que no cabía (E22)? Devuelve el separador para unirlos
    ("" o " ") o None. La sangría +4 sola no alcanza: un autor también la usa para los
    parámetros, el cuerpo de un `if` o los argumentos de una llamada. Se une solo si:
    - el corte cayó a media palabra: los dos trozos juntos son una palabra que el
      documento usa y alguno de los trozos aparece una sola vez (`API.csp` + `roj`);
    - el anterior es un comentario y el siguiente no repite la marca (`///`, `#`);
    - el anterior dejó unas comillas abiertas;
    - el siguiente es solo un cierre (`);`, `};`, `/>`);
    - el anterior dejó un paréntesis abierto que el siguiente cierra;
    - el corte cayó entre dos palabras y el anterior no termina como termina un renglón
      que el autor sigue abajo (`AUTHOR_BREAK`, `do`/`then`, la cabecera de un `if`).
    Una continuación tras una coma no se une: no se distingue de un argumento por renglón.
    Comprobado con el manual 2 generado por manual.py, que corta igual: cada renglón unido
    está tal cual en su `.md` (docs/registro.md)."""
    a, b = prev.rstrip(), nxt.strip()
    tail, head = re.search(r"[^\W\d_]+$", a), re.match(r"[^\W\d_]+", b)
    if tail and head and counts:
        t, h = tail.group(0).lower(), head.group(0).lower()
        if counts[t + h] >= 1 and (counts[t] <= 1 or counts[h] <= 1):
            return ""
    if CODE_COMMENT.match(a) and not CODE_COMMENT.match(b):
        return " "
    s = re.sub(r"(?<=\w)'(?=\w)", "", a)
    if not CODE_COMMENT.match(a) and (s.count('"') % 2 or s.count("'") % 2):
        return " "
    if re.fullmatch(r"[)\]}]+[;,]?", b):
        return " " if b.startswith("}") else ""   # `{ X = 1 }` lleva espacio; `f(x)` no
    if CODE_COMMENT.match(b):
        return None
    if b == "/>":
        return " "
    depth = lambda x: sum(x.count(c) for c in "([{") - sum(x.count(c) for c in ")]}")   # noqa: E731
    if depth(a) > 0 and depth(b) < 0 and re.search(r"[\w.\"'>\]]$", a) and not a.endswith("=>"):
        return " "                                # «(Ctrl+C para» + «salir)»
    if re.search(r"[\w\"'.)]$", a) and not a.endswith(AUTHOR_BREAK) and re.match(r"[\w./<\"'-]", b) \
            and not re.search(r"(?<![\w-])(do|then|else|in)$", a) \
            and not (a.endswith(")") and depth(a) == 0 and CONTROL.match(a)):
        return " "                                # el corte cayó entre dos palabras
    return None


def rebuild_code(lines, right, log=None, skipped=None, counts=None):
    """Reconstruye el código tal como se escribió. Devuelve (texto, renglones reunidos).
    Si se pasan `log` y `skipped` (listas), anota como (final del renglón, renglón
    siguiente) cada reunión y cada caso dudoso que no se unió, para el reporte.

    `lines` son renglones (texto, x0, x1, y0, y1, tamaño de letra).
    - Sangría: si el PDF la da por posición (sin espacios), se calcula con el ancho de letra.
    - Renglones vacíos: solo donde hay una separación vertical real.
    - Renglones partidos: cuando el original cortó un renglón porque no cabía en el
      recuadro, las partes se reúnen. Tienen que darse tres cosas: la primera palabra del
      renglón siguiente no habría cabido al final del anterior; el siguiente empieza en el
      borde izquierdo (quien parte por ancho no respeta la sangría); y el anterior quedó a
      medias (`unfinished`). Solo con la primera, la regla unía instrucciones distintas
      (E17): un renglón con sangría propia es un renglón del autor. `right` es el borde
      útil (el del recuadro o el del texto normal); sin ese dato no se reúne nada.
      Algunos originales corren la continuación 4 letras más adentro en vez de dejarla
      en el borde (E22): esa se une solo en los casos de `wrapped` (`counts`: cuántas
      veces aparece cada palabra en el documento).
    """
    per_char = sorted((x1 - x0) / len(t) for t, x0, x1, *_ in lines
                      if len(t) >= 8 and t == t.strip())
    cw = per_char[len(per_char) // 2] if per_char else 0.6 * lines[0][5]
    rows = []                                   # une fragmentos de un mismo renglón
    for text, x0, x1, y0, y1, _ in sorted(lines, key=lambda l: (round(l[3]), l[1])):
        if rows and abs(rows[-1][2] - y0) < 2:
            gap = max(1, round((x0 - rows[-1][1]) / cw) - len(rows[-1][0]))
            rows[-1][0] += " " * gap + text
        else:
            rows.append([text, x0, y0])
    left = min(r[1] for r in rows)
    steps = sorted(b[2] - a[2] for a, b in zip(rows, rows[1:]) if b[2] - a[2] > 1)
    step = steps[len(steps) // 2] if steps else 1.2 * lines[0][5]
    cols = int((right - left) / cw + 0.05) if right else 0   # letras que caben por renglón
    out, joined, prev, indent = [], 0, None, 0
    for text, x0, y0 in rows:
        text = text.rstrip()
        lead = max(0, round((x0 - left) / cw))
        gap_rows = round((y0 - prev[1]) / step) - 1 if prev else 0
        first = text.strip().split(" ")[0]
        no_cabia = bool(prev and cols and gap_rows <= 0 and prev[0] >= 0.6 * cols
                        and prev[0] + 1 + len(first) > cols)
        own = lead + len(text) - len(text.lstrip())        # sangría de este renglón
        sep = wrapped(out[-1], text, counts) if no_cabia and own == indent + 4 else None
        if no_cabia and own == 0 and unfinished(out[-1]):
            sep = " "
        if sep is not None:
            if log is not None:
                log.append((out[-1].strip()[-40:], text.strip()[:40]))
            out[-1] += sep + text.strip()
            joined += 1
            prev = (own + len(text.strip()), y0)    # fin del renglón visible, no del unido
            continue
        if no_cabia and skipped is not None:
            skipped.append((out[-1].strip()[-40:], text.strip()[:40]))
        out += [""] * max(0, min(gap_rows, 3))
        out.append(" " * lead + text)
        indent = own
        prev = (lead + len(text), y0)             # columna donde termina el renglón visible
    return "\n".join(out), joined


def code_right(boxes, lines, fallback):
    """Borde derecho útil del recuadro que contiene el código (o el del texto normal)."""
    x = min(l[1] for l in lines)
    y = (lines[0][3] + lines[0][4]) / 2
    inside = [r for r in boxes if r.x0 <= x <= r.x1 and r.y0 <= y <= r.y1]
    if not inside:
        return fallback
    r = min(inside, key=lambda r: r.get_area())
    return r.x1 - (x - r.x0)                    # mismo margen interior a ambos lados


# ---------------------------------------------------------------------------
# Tablas dibujadas solo con líneas horizontales (y franjas de color)
# ---------------------------------------------------------------------------
def ruled_tables(page, drawings, cuts=None):
    """Devuelve ([(rect, markdown)], [rect sin reconstruir])."""
    H = page.rect.height
    lines, fills = [], []
    for d in drawings:
        r = d["rect"]
        if r.width < 20 or not (H * MARGIN < r.y0 < H * (1 - MARGIN)):
            continue
        if r.height < 1.5 and len(d["items"]) <= 2:
            lines.append(pymupdf.Rect(r))
        elif (d.get("fill") is not None and len(d["items"]) == 1
              and d["items"][0][0] == "re" and r.height < 60):
            fills.append(pymupdf.Rect(r))

    def merge(rects, same):
        """Une tramos contiguos a la misma altura (una línea dibujada por columnas)."""
        out = []
        for r in sorted(rects, key=lambda r: (round(r.y0), round(r.y1), r.x0)):
            if out and same(out[-1], r) and r.x0 <= out[-1].x1 + 3:
                out[-1].x1 = max(out[-1].x1, r.x1)
            else:
                out.append(pymupdf.Rect(r))
        return out

    lines = merge(lines, lambda a, b: abs(a.y0 - b.y0) < 1.5)
    fills = merge(fills, lambda a, b: abs(a.y0 - b.y0) < 1.5 and abs(a.y1 - b.y1) < 1.5)
    groups = {}
    for kind, rects in (("l", lines), ("f", fills)):
        for r in rects:
            if r.width < 150:
                continue
            g = groups.setdefault((round(r.x0 / 4), round(r.x1 / 4)),
                                  {"ys": [], "fills": [], "lines": 0, "x0": r.x0, "x1": r.x1})
            if kind == "l":
                g["ys"].append(r.y0)
                g["lines"] += 1
            else:
                g["fills"].append(r)  # franjas: encabezado o filas alternas
    done, failed = [], []
    for g in groups.values():
        if g["lines"] < 2:
            continue
        ys = []
        for y in sorted(g["ys"]):
            if not ys or y - ys[-1] > 2:
                ys.append(y)
        segs, cur = [], [ys[0]]
        for a, b in zip(ys, ys[1:]):
            covered = any(f.y0 <= a + 2 and f.y1 >= b - 2 for f in g["fills"])
            if b - a > 36 and not covered:
                segs.append(cur)
                cur = [b]
            else:
                cur.append(b)
        segs.append(cur)
        # Una franja pegada al borde superior o inferior es una fila más (p. ej. el encabezado)
        for seg in segs:
            for f in g["fills"]:
                if abs(f.y1 - seg[0]) < 2:
                    seg.insert(0, f.y0)
                elif abs(f.y0 - seg[-1]) < 2 and any(
                        abs(l - f.y1) < 2 for l in g["ys"]):  # cerrada por una línea
                    seg.append(f.y1)
        segs = join_tall_rows(page, segs, g["x0"], g["x1"])
        for seg in segs:
            if len(seg) < 3:
                continue
            end = open_last_row(page, seg, g["x0"], g["x1"])
            md = None
            if end:                                  # con la fila sin línea de cierre (E23)
                rect = pymupdf.Rect(g["x0"], seg[0], g["x1"], end)
                md = build_table(page, rect, seg + [end], cuts)
                if md in (None, "NO_ES_TABLA"):
                    md = None                        # no resultó: la tabla, como estaba
            if md is None:
                rect = pymupdf.Rect(g["x0"], seg[0], g["x1"], seg[-1])
                md = build_table(page, rect, seg, cuts)
            if md == "NO_ES_TABLA":
                continue  # cuadro o franja de una sola columna: se extrae como texto
            if md:
                done.append((rect, md))
            elif page.get_text(clip=rect).strip():
                failed.append(rect)
    return done, failed


def col_starts(page, rect):
    """Inicio (x) de cada columna, según los huecos verticales sin texto."""
    cols = []
    for a, b in sorted((w[0], w[2]) for w in page.get_text("words", clip=rect)):
        if cols and a - cols[-1][1] < COL_GAP:
            cols[-1][1] = max(cols[-1][1], b)
        else:
            cols.append([a, b])
    return [c[0] for c in cols]


def open_last_row(page, seg, x0, x1):
    """Borde inferior de una fila que quedó debajo de la última línea de la tabla, o None
    (E23). Antes de un cambio de página el original no dibuja la línea de cierre y la
    última fila quedaba como un párrafo suelto. Es una fila si su texto está a menos de una
    fila y media de la última línea, ocupa dos columnas o más, cada renglón empieza donde
    empieza una columna de la tabla (un pie de página centrado no) y ningún renglón cruza
    el límite entre columnas (un párrafo sí lo cruza)."""
    steps = sorted(b - a for a, b in zip(seg, seg[1:]))
    row_h = steps[len(steps) // 2]
    floor = page.rect.height * (1 - MARGIN)              # no entra en la zona del pie
    band = pymupdf.Rect(x0, seg[-1] + 1, x1, min(seg[-1] + 1.5 * row_h, floor))
    if band.height < 4:
        return None
    starts = col_starts(page, pymupdf.Rect(x0, seg[0], x1, seg[-1]))
    if len(starts) < 2:
        return None
    bounds = [s - 4 for s in starts[1:]]
    used, bottom = set(), None
    for b in page.get_text("dict", clip=band)["blocks"]:
        for ln in b.get("lines", []):
            lb = pymupdf.Rect(ln["bbox"])
            if not "".join(s["text"] for s in ln["spans"]).strip():
                continue
            if lb.y0 < seg[-1] - 1 or lb.y1 > band.y1 + row_h:
                return None                       # sigue más allá de una fila
            if any(lb.x0 < x < lb.x1 for x in bounds) or lb.x0 < x0 - 4 or lb.x1 > x1 + 4:
                return None                       # cruza columnas: es un párrafo
            if not any(abs(lb.x0 - s) <= 6 for s in starts):
                return None                       # no empieza en una columna de la tabla
            used.add(sum(1 for s in starts if s - 4 <= lb.x0))
            bottom = max(bottom or 0, lb.y1)
    return bottom + 2 if bottom and len(used) >= 2 else None


def join_tall_rows(page, segs, x0, x1):
    """Une tramos separados por una fila alta (celdas de varios renglones).

    Se unen si el texto entre ambos respeta las columnas de la tabla; si hay un
    renglón que cruza columnas (un título o un párrafo), son dos tablas distintas.
    """
    out = [segs[0]]
    for seg in segs[1:]:
        prev = out[-1]
        top, bot = prev[-1], seg[0]
        known = [(a, b) for s in (prev, seg) for a, b in zip(s, s[1:])]
        if bot - top > 90 or not known:
            out.append(seg)
            continue
        # Inicios de columna que se repiten en la mayoría de las filas conocidas
        votes = Counter()
        for a, b in known:
            for x in {round(x / 4) for x in col_starts(page, pymupdf.Rect(x0, a, x1, b))}:
                votes[x] += 1
        starts = sorted(x * 4 for x, v in votes.items() if v >= max(1, len(known) / 2))
        bounds = [s - 4 for s in starts[1:]]
        crosses = False
        for b in page.get_text("dict", clip=pymupdf.Rect(x0, top, x1, bot))["blocks"]:
            for ln in b.get("lines", []):
                lb = pymupdf.Rect(ln["bbox"])
                if any(lb.x0 < x < lb.x1 for x in bounds) or lb.x0 < x0 - 4 or lb.x1 > x1 + 4:
                    crosses = True
        if crosses:
            out.append(seg)
        else:
            prev.extend(seg)
    return out


def cut_word(prev, nxt, counts):
    """¿Una celda angosta partió un identificador entre dos renglones (E23:
    «Authentication.Op» / «enIdConnect»)? Sí, si los dos trozos juntos son una palabra
    que el documento usa, el trozo más raro no aparece más veces que la palabra entera,
    y lo partido parece un identificador (punto, guion bajo o mayúscula en medio)."""
    a, b = re.sub(r"[`*]+$", "", prev), re.sub(r"^[`*]+", "", nxt)
    tail, head = re.search(r"[^\W\d_]+$", a), re.match(r"[^\W\d_]+", b)
    if not (tail and head and counts):
        return False
    t, h = tail.group(0), head.group(0)
    whole = counts[(t + h).lower()]
    token = re.search(r"\S+$", a).group(0) + re.match(r"\S+", b).group(0)
    return whole >= 1 and min(counts[t.lower()], counts[h.lower()]) <= whole \
        and bool(re.search(r"[._]|[a-z][A-Z]", token))


def cell_md(page, rect, lost=None, cuts=None):
    parts = []
    for b in page.get_text("dict", clip=rect)["blocks"]:
        for ln in b.get("lines", []):
            spans = [s for s in ln["spans"] if rect.contains(pymupdf.Point(
                (s["bbox"][0] + s["bbox"][2]) / 2, (s["bbox"][1] + s["bbox"][3]) / 2))]
            if spans:
                part = span_md(fix_scripts(spans, lost)).strip()
                if parts and part and cuts and cut_word(parts[-1], part, cuts["counts"]):
                    end = re.search(r"[`*]*$", parts[-1]).group(0)
                    start = re.match(r"[`*]*", part).group(0)
                    if end == start:                   # misma marca a los dos lados: una sola
                        cuts["parts"] += [re.search(r"\S+$", parts[-1]).group(0), part.split()[0]]
                        parts[-1] = parts[-1][:len(parts[-1]) - len(end)] + part[len(start):]
                        continue
                parts.append(part)
    return norm(" ".join(parts))


def build_table(page, rect, ys, cuts=None):
    """Filas = franjas entre líneas; columnas = huecos verticales sin texto."""
    words_ = [w for w in page.get_text("words", clip=rect)
              if rect.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
    if not words_:
        return None
    for b in page.get_text("dict")["blocks"]:  # un renglón que la atraviesa: no es tabla
        for ln in b.get("lines", []):
            lb = pymupdf.Rect(ln["bbox"])
            if lb.intersects(rect) and lb.height < rect.height and \
                    (lb.x0 < rect.x0 - 4 or lb.x1 > rect.x1 + 4):
                return "NO_ES_TABLA"
    cols = []
    for a, b in sorted((w[0], w[2]) for w in words_):
        if cols and a - cols[-1][1] < COL_GAP:
            cols[-1][1] = max(cols[-1][1], b)
        else:
            cols.append([a, b])
    if len(cols) < 2:
        return "NO_ES_TABLA"
    xb = [rect.x0] + [(cols[i][1] + cols[i + 1][0]) / 2 for i in range(len(cols) - 1)] + [rect.x1]
    rows = []
    for y0, y1 in zip(ys, ys[1:]):
        row = [cell_md(page, pymupdf.Rect(c0, y0, c1, y1), cuts=cuts) for c0, c1 in zip(xb, xb[1:])]
        if any(row):
            rows.append(row)
    if len(rows) < 2:
        return "NO_ES_TABLA"
    md = md_table(rows)
    joined = set(words(" ".join(cuts["parts"]))) if cuts else set()   # trozos unidos (E23)
    if set(words(" ".join(w[4] for w in words_))) - set(words(md)) - joined:
        return None  # alguna palabra no quedó en la tabla
    return md


# ---------------------------------------------------------------------------
def diagram_like(page, r, rects):
    """¿Un grupo de dibujos con texto es un diagrama de cajas y flechas? Tiene que haber
    al menos tres cajas que no se contienen entre sí, dos conectores (trazos finos fuera
    de las cajas) y texto en renglones cortos: rótulos, no párrafos ni código."""
    boxes = [b for b in rects if b.width > 40 and b.height > 14
             and b.get_area() < 0.5 * r.get_area()]
    boxes = [b for k, b in enumerate(boxes)
             if not any(o.contains(b) and o != b for o in boxes[:k] + boxes[k + 1:])]
    lines = [b for b in rects if (b.width < 3 or b.height < 3) and max(b.width, b.height) > 8
             and not any(o.contains(b) for o in boxes)]
    texts = [l.strip() for l in page.get_text(clip=r).splitlines() if l.strip()]
    if len(boxes) < 3 or len(lines) < 2 or len(texts) < 4:
        return False
    return sorted(len(t) for t in texts)[len(texts) // 2] <= 45


def page_to_md(doc, page, ctx):
    n = page.number + 1
    W, H = page.rect.width, page.rect.height
    body, assets = ctx["body"], ctx["assets"]
    marks = list(ctx.get("toc_pages", {}).get(n, []))     # marcadores de esta página (E20)
    items, notes, removed = [], [], []

    raw_lines = [norm(l) for l in page.get_text().splitlines() if l.strip()]

    # Página de índice: se guarda comprimida en un comentario (se regenera)
    leaders = [l for l in raw_lines if LEADER.search(l)]
    # Algunos originales dan título, puntos y número en tres renglones (E21): los puntos
    # son un tercio de los renglones, pero casi todas las «palabras» de la página.
    tokens_ = [t for l in raw_lines for t in l.split()]
    dots = sum(1 for t in tokens_ if re.fullmatch(r"\.+", t))
    if (len(leaders) >= 5 and len(leaders) >= 0.4 * len(raw_lines)) or \
            (dots >= 50 and dots >= 0.6 * len(tokens_)):
        parts = []
        for l in raw_lines:
            x = norm(re.sub(r"(?<!\S)\.+(?!\S)", " ", LEADER.sub(" ", l)))
            if x and x.isdigit() and parts:
                parts[-1] += " " + x                  # el número de página, con su título
            elif x:
                parts.append(x)
        entries = " | ".join(parts)
        notes.append("índice original (omitido del cuerpo)")
        return f"<!-- p.{n} ÍNDICE ORIGINAL: {entries} -->", notes, [], raw_lines

    try:
        drawings = page.get_drawings()
        clusters = page.cluster_drawings(drawings=drawings)
    except Exception:
        drawings, clusters = [], []
    boxes = [pymupdf.Rect(d["rect"]) for d in drawings   # recuadros con fondo (código, cuadros)
             if d.get("fill") is not None and d["rect"].width > 100 and d["rect"].height > 8]
    unique = []

    # Tablas con solo líneas horizontales (muy comunes en manuales)
    ctx["cuts"] = {"counts": ctx["counts"], "parts": []}
    ruled, failed = ruled_tables(page, drawings, ctx["cuts"])
    t_rects = [r for r, _ in ruled]
    for r, md in ruled:
        items.append((r.y0, r.x0, md))
    for r in failed:
        name = f"p{n}-tabla{len(notes) + 1}.png"
        page.get_pixmap(clip=r, dpi=100).save(str(assets / name))
        notes.append(f"posible tabla sin reconstruir (ver assets/{name})")

    # Tablas con bordes completos; se descartan detecciones que cortan palabras
    # (por ejemplo, el fondo de color del código en línea)
    tables = []
    for t in page.find_tables().tables:
        if any(pymupdf.Rect(t.bbox).intersects(r) for r in t_rects):
            continue
        rows = table_rows(page, t, ctx["scripts_lost"], ctx["cuts"])
        if clean_table(page, t, rows) and \
                (t.row_count >= 2 or (t.col_count == 1 and t.bbox[3] - t.bbox[1] > 30)):
            tables.append((t, rows))
    t_rects += [pymupdf.Rect(t.bbox) for t, _ in tables]
    for t, rows in tables:
        code = mono_box(page, t) if t.col_count == 1 else None
        if code:                                  # recuadro de código con borde (E24)
            items.append((t.bbox[1], t.bbox[0], ("CODE", code)))
        elif len(rows) == 1 and len(rows[0]) == 1:  # caja de un solo cuadro
            if rows[0][0]:
                items.append((t.bbox[1], t.bbox[0], "> " + rows[0][0]))
        else:
            items.append((t.bbox[1], t.bbox[0], md_table(rows)))

    def in_table(r):
        c = pymupdf.Rect(r)
        return any(tr.contains(pymupdf.Point((c.x0 + c.x1) / 2, (c.y0 + c.y1) / 2))
                   for tr in t_rects)

    # Imágenes
    img_rects = []
    for info in page.get_image_info(xrefs=True):
        xref, bb = info["xref"], pymupdf.Rect(info["bbox"])
        if info["width"] < 48 or info["height"] < 48 or bb.get_area() < 0.01 * W * H:
            continue
        img_rects.append(bb)
        name = ctx["img_names"].get(xref) if xref else None
        if name and ctx["img_pages"][xref] >= ctx["img_repeat"]:
            continue                  # la misma imagen en muchas páginas (un logo): una vez
        if not name:
            stem = f"p{n}-img{xref}" if xref else f"p{n}-img0-{len(ctx['figures']) + 1}"
            name = save_image(doc, xref, assets, stem, page, bb)
            ctx["figures"].append(f"assets/{name}")
            if xref:
                ctx["img_names"][xref] = name
        items.append((bb.y0, bb.x0, ("IMG", name, bb)))   # si se repite, se vuelve a nombrar

    # Gráficos vectoriales grandes con poco texto (diagramas, gráficos)
    for i, r in enumerate(clusters):
        if r.width < 120 or r.height < 80 or any(r.intersects(t) for t in t_rects):
            continue
        inside = [d["rect"] for d in drawings if r.contains(d["rect"])]
        if len(inside) < 6:
            continue  # caja o fondo simple, no es un gráfico
        if len(page.get_text(clip=r).strip()) > r.get_area() / 400:
            # Cuadro con texto: el texto ya se extrae. Pero si son varias cajas unidas
            # por flechas es un diagrama: sus rótulos quedan como texto suelto, sin decir
            # qué se conecta con qué (E24). Se guarda el recorte y queda como pendiente.
            if diagram_like(page, r, inside):
                name = f"p{n}-diagrama{i + 1}.png"
                page.get_pixmap(clip=r, dpi=130).save(str(assets / name))
                items.append((r.y0, r.x0, ("IMG", name, r)))
                ctx["figures"].append(f"assets/{name}")
                ctx.setdefault("diagrams", []).append((n, name))
            continue
        name = f"p{n}-vec{i + 1}.png"
        page.get_pixmap(clip=r, dpi=110).save(str(assets / name))
        items.append((r.y0, r.x0, ("IMG", name, r)))
        ctx["figures"].append(f"assets/{name}")

    # Página escaneada (casi sin texto y cubierta por una imagen)
    text_chars = sum(len(l) for l in raw_lines)
    if text_chars < 30 and any(r.get_area() > 0.5 * W * H for r in img_rects):
        name = f"p{n}-escaneada.png"
        page.get_pixmap(dpi=150).save(str(assets / name))
        ctx["scanned"].append(n)
        notes.append("ESCANEADA: transcribir")
        return (f"<!-- p.{n} -->\n\n![PÁGINA ESCANEADA p.{n}: TRANSCRIBIR](assets/{name})",
                notes, [], raw_lines)

    # Texto
    blocks = [b for b in page.get_text("dict")["blocks"] if b["type"] == 0]
    # Dos columnas: bloques anchos de texto, uno a cada lado, a la misma altura
    wide = [pymupdf.Rect(b["bbox"]) for b in blocks if not in_table(b["bbox"])
            and 0.25 * W < b["bbox"][2] - b["bbox"][0] < 0.5 * W]
    left = [r for r in wide if r.x1 < W / 2 + 10]
    right = [r for r in wide if r.x0 > W / 2 - 10]
    two_cols = sum(1 for a in left for b in right
                   if min(a.y1, b.y1) - max(a.y0, b.y0) > 0.5 * min(a.height, b.height)) >= 3
    for b in blocks:
        if in_table(b["bbox"]):
            continue
        lines, size, mono, bold = block_lines(b, ctx["scripts_lost"])
        kept = []
        for plain, md, bb in lines:
            if is_boiler(plain, bb, H, ctx["bp"]):
                removed.append(norm(plain))
            else:
                if zone_of(bb[1], bb[3], H):     # aparece una sola vez: es contenido
                    unique.append(norm(plain))
                kept.append((plain, md, bb))
        if not kept:
            continue
        x0, y0 = b["bbox"][0], b["bbox"][1]
        if mono:
            items.append((y0, x0, ("CODE", [(p, bb[0], bb[2], bb[1], bb[3], size)
                                            for p, _, bb in kept if p.strip()])))
            continue
        head = bookmark_head(kept, size, body, marks) if marks else None
        if head:                                 # título con su marcador en esta página
            j, lvl = head
            title = norm(" ".join(p for p, _, _ in kept[:j]))
            items.append((y0, x0, "#" * min(lvl, 3) + " " + title))
            ctx["headings"].append(title)
            kept = kept[j:]
            if not kept:
                continue
            y0 = kept[0][2][1]                    # el párrafo que venía en el mismo bloque
        plain_all = norm(" ".join(p for p, _, _ in kept))
        lvl = 0 if head else heading_level(plain_all, size, bold, len(kept), body, ctx["toc_levels"])
        if lvl:
            items.append((y0, x0, "#" * lvl + " " + plain_all))
            ctx["headings"].append(plain_all)
            continue
        # Agrupa en párrafos o ítems de lista
        paras, cur = [], []
        for plain, md, _ in kept:
            if BULLET.match(plain):
                if cur:
                    paras.append(cur)
                cur = ["- " + BULLET.sub("", md.replace("**•**", "•"))]
            else:
                cur.append(md)
        if cur:
            paras.append(cur)
        vocab, hyph = ctx["vocab"], ctx["hyphens"]
        text = "\n".join(join_lines(p, vocab, hyph) if not p[0].startswith("- ")
                         else "- " + join_lines([p[0][2:]] + p[1:], vocab, hyph) for p in paras)
        if ctx["pending_bullet"] and len(kept) and not text.startswith("- "):
            text = "- " + text
        ctx["pending_bullet"] = norm(plain_all) in ("•", "●", "▪", "-")
        if ctx["pending_bullet"]:
            continue
        items.append((y0, x0, text))

    # Orden de lectura (por columnas si la página tiene dos)
    def order(it):
        y, x, _ = it
        if not two_cols:
            return (0, y, x)
        return (0 if x < W / 2 else 1, y, x)
    items.sort(key=order)

    # Imagen + pie de figura inmediato
    out, skip = [], set()
    for i, (y, x, it) in enumerate(items):
        if i in skip:
            continue
        if isinstance(it, tuple) and it[0] == "CODE":
            lines, j = list(it[1]), i + 1       # un recuadro puede venir en varios bloques
            while j < len(items) and isinstance(items[j][2], tuple) and items[j][2][0] == "CODE":
                lines += items[j][2][1]
                skip.add(j)
                j += 1
            joins, doubts = [], []
            code, n_joined = rebuild_code(lines, code_right(boxes, lines, ctx["bp"]["right"]),
                                          joins, doubts, ctx["counts"])
            ctx["code_joined"] += n_joined
            ctx.setdefault("code_joins", []).extend((page.number + 1, a, b) for a, b in joins)
            ctx.setdefault("code_doubts", []).extend((page.number + 1, a, b) for a, b in doubts)
            out.append(f"```\n{code}\n```")
        elif isinstance(it, tuple):
            _, name, r = it
            alt = "FIGURA: describir"
            if i + 1 not in skip and i + 1 < len(items) and isinstance(items[i + 1][2], str):
                nxt = items[i + 1]
                cap = nxt[2].strip("*").strip()
                looks_caption = (nxt[2].startswith("*") and not nxt[2].startswith("**")) \
                    or CAPTION.match(cap)
                if nxt[0] - r.y1 < 25 and len(cap) < 200 and looks_caption:
                    alt, _ = cap, skip.add(i + 1)
            out.append(f"![{alt}](assets/{name})")
        else:
            out.append(it)
    if two_cols:
        notes.append("dos columnas: verificar orden")
    if unique:
        notes.append("texto único en la zona de encabezado/pie, conservado en el cuerpo "
                     "(verificar): " + " / ".join(u[:70] for u in unique[:3]))
    body_md = add_links(page, merge_blocks(out))
    return f"<!-- p.{n} -->\n\n" + body_md, notes, removed, raw_lines


def kind(b):
    if b.startswith("```"):
        return "code"
    if b.startswith("- ") or re.match(r"\d+[.)] ", b):
        return "list"
    if b.startswith(("#", "|", "!", "<!--", ">")):
        return "other"
    return "para"


def merge_blocks(blocks):
    """Une listas, código y párrafos que el PDF partió en varios bloques."""
    out = []
    for b in blocks:
        b = re.sub(r"^\*\*(\d+[.)])\*\*\s*", r"\1 ", b)       # **1.** texto
        b = re.sub(r"^\*\*(\d+[.)])\s+(?=\S)", r"\1 **", b)   # **1. texto**
        if out:
            prev, kp, kb = out[-1], kind(out[-1]), kind(b)
            if kp == kb == "list":
                out[-1] = prev + "\n" + b
                continue
            if kp == kb == "code":
                out[-1] = prev[:-3].rstrip("\n") + "\n\n" + b[4:]
                continue
            if kp == kb == "para" and not re.search(r"[.!?:;)»\"”]$", prev) \
                    and not re.fullmatch(r"\*\*[^*]+\*\*", prev):
                out[-1] = prev + " " + b
                continue
        out.append(b)
    return "\n\n".join(out)


def mono_box(page, t):
    """Renglones de un recuadro de una columna cuyo texto es todo de letra de código (un
    diagrama de flujo con flechas de texto, o código con borde), con su posición, para
    reconstruirlo como bloque de código; None si no lo es (E24). Como tabla de una celda
    perdía los saltos de renglón y la sangría."""
    lines = []
    for b in page.get_text("dict", clip=pymupdf.Rect(t.bbox))["blocks"]:
        for ln in b.get("lines", []):
            spans = [s for s in ln["spans"] if s["text"].strip()]
            if not spans:
                continue
            if not all(MONO.search(s["font"]) for s in spans):
                return None
            bb = ln["bbox"]
            text = "".join(s["text"] for s in ln["spans"]).rstrip()   # como en block_lines
            lines.append((text, bb[0], bb[2], bb[1], bb[3], spans[0]["size"]))
    return lines if len(lines) >= 2 else None


def table_rows(page, t, lost=None, cuts=None):
    """Texto de cada celda de una tabla con bordes, leído de sus tramos. `Table.extract()`
    de PyMuPDF pega las palabras cuando el espacio mide menos de 3 pt (letra de 10 pt o
    menos: «sin cambios» queda «sincambios») y aplana superíndices y subíndices (E4)."""
    return [[cell_md(page, pymupdf.Rect(c), lost, cuts) if c else "" for c in row.cells]
            for row in t.rows]


def clean_table(page, t, rows):
    """Una tabla es válida si no corta palabras y contiene todo el texto de su zona."""
    r = pymupdf.Rect(t.bbox)
    real = set(words(" ".join(  # palabras completas cuyo centro cae en la tabla
        w[4] for w in page.get_text("words")
        if r.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)))))
    cells = set(words(" ".join(c for row in rows for c in row)))
    if cells != real or t.row_count == 0:
        return False
    # En una tabla real el texto queda dentro; si un renglón la atraviesa, es un
    # párrafo con fragmentos de código resaltados, no una tabla. El renglón de arriba o de
    # abajo, que apenas roza el borde (su caja incluye el espacio bajo las letras), no cuenta.
    for b in page.get_text("dict")["blocks"]:  # sin recorte: renglones completos
        for ln in b.get("lines", []):
            lb = pymupdf.Rect(ln["bbox"])
            inside = min(lb.y1, r.y1) - max(lb.y0, r.y0)
            if inside > 0.3 * lb.height and (lb.x0 < r.x0 - 4 or lb.x1 > r.x1 + 4):
                return False
    return True


def add_links(page, md):
    """Recupera las URL de los enlaces (el texto extraído no las trae) (E11).

    - La puntuación final queda fuera del enlace.
    - El texto se busca aunque en el Markdown tenga marcas de formato entre palabras.
    - Si el texto aparece varias veces en la página, se elige la aparición que corresponde
      a la posición del enlace, no la primera.
    - Dos enlaces a la misma dirección son dos enlaces; un enlace que sigue en el renglón
      siguiente es uno solo.
    """
    page_words = page.get_text("words")
    centers = [pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page_words]
    found = []
    for ln in page.get_links():
        if ln.get("uri"):
            idx = [i for i, c in enumerate(centers) if ln["from"].contains(c)]
            found.append((idx[0] if idx else len(centers), ln["uri"], idx))
    links = []
    for _, uri, idx in sorted(found, key=lambda f: f[0]):
        if links and links[-1][0] == uri and idx and links[-1][1] and idx[0] == links[-1][1][-1] + 1:
            links[-1][1].extend(idx)
        else:
            links.append([uri, list(idx)])
    missing = []
    for uri, idx in links:
        safe = uri.replace("(", "%28").replace(")", "%29").replace(" ", "%20")
        core = norm(" ".join(page_words[i][4] for i in idx)).rstrip(".,;:")
        placed = False
        if core:
            nth = " ".join(w[4] for w in page_words[:idx[0]]).count(core)
            pat = re.compile(r"(?<![\w\[])" + r"[*]*\s+[*]*".join(re.escape(w) for w in core.split())
                             + r"(?!\w)(?!\]\()")
            taken = [m.span() for m in re.finditer(r"\[[^\]\n]*\]\([^)\n]*\)|```.*?```|`[^`\n]*`", md, re.S)]
            hits = [m for m in pat.finditer(md)
                    if not any(a <= m.start() < b for a, b in taken)]   # ni en otro enlace ni en código
            if hits:
                m = hits[min(nth, len(hits) - 1)]
                md = md[:m.start()] + f"[{m.group(0)}]({safe})" + md[m.end():]
                placed = True
        if not placed:
            missing.append(f"[{core or uri}]({safe})")
    if missing:
        md += "\n\nEnlaces: " + ", ".join(missing)
    return md


# ---------------------------------------------------------------------------
def coverage(raw_lines, md, removed, vocab=None):
    """Palabras del original que no aparecen en el Markdown de esa página. Los renglones
    del original se unen con la misma regla de guiones que el Markdown (E8): una palabra
    cortada al final del renglón no cuenta como faltante."""
    text = ""
    for line in raw_lines:
        text = glue(text, line, vocab)
    src = words(text) - words("\n".join(removed))
    miss = src - words(md)
    total = sum(src.values()) or 1
    return 1 - sum(miss.values()) / total, list(miss)[:10]


def mark_unmapped(md_text):
    """Reemplaza por una marca visible y buscable los símbolos cuya fuente no dice qué
    carácter son (llegan como NUL o U+FFFD) (E18). Devuelve (texto, {página: cuántos})."""
    unmapped, page_now = {}, 0
    for ln in md_text.split("\n"):
        m = re.match(r"<!-- p\.(\d+)", ln)
        page_now = int(m.group(1)) if m else page_now
        n_bad = ln.count("\x00") + ln.count("�")
        if n_bad:
            unmapped[page_now] = unmapped.get(page_now, 0) + n_bad
    return md_text.replace("\x00", MARK).replace("�", MARK), unmapped


def extract(pdf_path, out_dir):
    pdf_path, out_dir = Path(pdf_path), Path(out_dir)
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        raise ExtractError(f"el PDF no se puede abrir ({type(e).__name__}): está dañado o no es un PDF")
    if doc.needs_pass:
        raise ExtractError("el PDF está protegido con contraseña: guardar una copia sin protección")
    name = out_dir.name
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    toc = doc.get_toc()
    body = body_size(doc)
    vocab, img_pages = set(), Counter()         # palabras del documento; páginas de cada imagen
    counts = Counter()                          # y cuántas veces aparece cada una
    for page in doc:
        page_words = re.findall(r"[^\W\d_]+", page.get_text().lower())
        vocab.update(page_words)
        counts.update(page_words)
        img_pages.update({info["xref"] for info in page.get_image_info(xrefs=True) if info["xref"]})
    ctx = dict(body=body, assets=assets, bp=find_boilerplate(doc, body, toc), code_joined=0,
               toc_levels={key(t): lvl - min(x[0] for x in toc) + 1 for lvl, t, _ in toc},
               toc_pages=toc_by_page(toc),
               img_names={}, img_pages=img_pages, img_repeat=max(3, 0.3 * doc.page_count),
               vocab=vocab, counts=counts, hyphens=[], scripts_lost=[],
               figures=[], scanned=[], headings=[], pending_bullet=False)

    pages_md, report_rows, info_rows, all_removed, cover_lines = [], [], [], set(), []
    cover_title = ""
    for page in doc:
        md, notes, removed, raw = page_to_md(doc, page, ctx)
        all_removed.update(removed)
        cov, miss = coverage(raw, md, removed + ctx.get("cuts", {}).get("parts", []), vocab)
        # Portada: poco texto y con letra grande -> comentario
        biggest = max((s["size"] for b in page.get_text("dict")["blocks"]
                       for ln in b.get("lines", []) for s in ln["spans"]), default=0)
        if page.number == 0 and doc.page_count > 2 and sum(len(l) for l in raw) < 400 \
                and biggest >= 1.6 * ctx["body"]:
            cover_lines = raw
            spans = [s for b in page.get_text("dict")["blocks"] for ln in b.get("lines", [])
                     for s in ln["spans"] if s["text"].strip()]
            cover_title = norm(" ".join(s["text"] for s in spans if s["size"] >= biggest - 0.5))
            labels = {"curso": "curso", "autor": "autor", "autora": "autor",
                      "versión": "version", "version": "version", "fecha": "fecha",
                      "institución": "institucion", "institucion": "institucion"}
            for a, b in zip(raw, raw[1:]):
                lab = a.lower().rstrip(":")
                if lab in labels:
                    ctx.setdefault("cover", {})[labels[lab]] = b
            md = "<!-- p.1 PORTADA ORIGINAL: " + " | ".join(raw) + " -->"
            ctx["headings"] = [h for h in ctx["headings"] if h not in raw]
            notes.append("portada: datos en la cabecera")
        pages_md.append(md)
        # Solo va a "requieren revisión" lo que pide hacer algo (E13); lo demás es informativo
        todo = [x for x in notes if not x.startswith(("índice original", "portada:"))]
        if cov < 0.98 or todo:
            report_rows.append(f"| {page.number + 1} | {cov:.0%} | {'; '.join(todo)} "
                               f"| {' '.join(miss)} |")
        if len(todo) < len(notes):
            info_rows.append(f"p.{page.number + 1}: " + "; ".join(x for x in notes if x not in todo))

    meta = doc.metadata or {}
    titulo = (meta.get("title") or "").strip()
    if not titulo or JUNK_TITLE.match(titulo):      # título de metadatos sin valor (E14)
        titulo = cover_title or (cover_lines[0] if cover_lines else name)
    numbered = sum(bool(NUM_HEAD.match(h)) for h in ctx["headings"])
    front = {
        "titulo": titulo,
        # «(unspecified)» y «(anonymous)» son relleno del programa que creó el PDF (E14)
        **{k: v for k, v in (("subtitulo", (meta.get("subject") or "").strip()),
                             ("autor", (meta.get("author") or "").strip()),
                             ("palabras_clave", (meta.get("keywords") or "").strip()))
           if not JUNK_TITLE.match(v)},
        "tamano": "carta" if abs(doc[0].rect.width - 612) < 5 else "A4",
        "numerar": "no" if numbered > len(ctx["headings"]) / 2 else "si",
        "fuente": pdf_path.name,
        **ctx.get("cover", {}),
    }
    head = "---\n" + "\n".join(f"{k}: {v}" for k, v in front.items() if v) + "\n---\n"
    if all_removed:
        uniq = sorted({re.sub(r"\d+", "#", r) for r in all_removed})
        head += "\n<!-- ENCABEZADOS/PIES REPETIDOS (omitidos): " + " | ".join(uniq) + " -->\n"
    md_text = head + "\n" + "\n\n".join(pages_md) + "\n"
    md_text, unmapped = mark_unmapped(md_text)
    md_file = out_dir / f"{name}.md"
    md_file.write_text(md_text, encoding="utf-8")
    pending_figs = re.findall(r"!\[FIGURA: describir\]\(([^)]+)\)", md_text)

    rep = [
        f"# Reporte de extracción: {pdf_path.name}",
        "",
        f"- Páginas: {doc.page_count} | Títulos detectados: {len(ctx['headings'])} "
        f"| Marcadores del PDF: {len(toc)}",
        f"- Markdown: `{md_file.name}` ({len(md_text):,} caracteres, ~{round(len(md_text) / 3.5):,} tokens)",
        f"- Figuras guardadas: {len(ctx['figures'])} | por describir: {len(set(pending_figs))}",
        f"- Páginas escaneadas (transcribir): {ctx['scanned'] or 'ninguna'}",
    ]
    if ctx["hyphens"]:
        rep.append(f"- Guiones conservados al final de un renglón: {len(ctx['hyphens'])} "
                   f"({', '.join(dict.fromkeys(ctx['hyphens']))[:300]}). La palabra unida no aparece "
                   "en otra parte del documento: si era un corte de renglón, quitar el guion.")
    if ctx["scripts_lost"]:
        rep.append(f"- Superíndices o subíndices sin carácter propio (quedaron en línea): "
                   f"{', '.join(dict.fromkeys(ctx['scripts_lost']))[:200]}. Revisar el sentido.")
    if ctx["code_joined"]:
        rep.append(f"- Renglones de código reunidos (el original los partió por ancho): "
                   f"{ctx['code_joined']}. Revisar todos: lista al final.")
    if ctx.get("code_doubts"):
        rep.append(f"- Renglones de código que podrían estar partidos y no se unieron: "
                   f"{len(ctx['code_doubts'])}. Lista al final.")
    if unmapped:
        rep.append(f"- Símbolos sin mapa de caracteres (quedaron como `{MARK}` en el .md): "
                   f"{sum(unmapped.values())}, en p. "
                   + ", ".join(f"{p} ({n})" for p, n in sorted(unmapped.items()))
                   + ". Reemplazar cada uno por el símbolo que se ve en el original.")
    rep.append("")
    if report_rows:
        rep += ["## Páginas que requieren revisión", "",
                "| Pág. | Cobertura | Notas | Palabras faltantes |", "|---|---|---|---|",
                *report_rows]
    else:
        rep.append("Cobertura 100% en todas las páginas; sin observaciones.")
    if info_rows:
        rep += ["", "## Notas (no requieren acción)", "", *[f"- {r}" for r in info_rows]]
    if pending_figs:
        rep += ["", "## Figuras pendientes de describir", "",
                *[f"- `{f}`" for f in dict.fromkeys(pending_figs)]]
    if ctx.get("diagrams"):
        rep += ["", "## Diagramas con texto", "",
                "Cajas unidas por flechas: los rótulos están en el `.md` como texto suelto, sin "
                "decir qué se conecta con qué. Pasar cada uno a `describir-figuras`, que reemplaza "
                "ese texto por una tabla de componentes y otra de conexiones.", "",
                *[f"- p.{p}: `assets/{name}`" for p, name in ctx["diagrams"]]]
    if ctx.get("code_joins"):
        rep += ["", "## Renglones de código reunidos", "",
                "Cada línea: página, final del renglón y lo que se le unió. Es correcto solo si "
                "lo unido continúa la misma instrucción; si es otra instrucción (otra variable, "
                "otra sentencia, texto tras un comentario), separarlos en el `.md`.", "",
                *[f"- p.{p}: `…{a}` + `{b}…`" for p, a, b in ctx["code_joins"]]]
    if ctx.get("code_doubts"):
        rep += ["", "## Renglones de código que podrían estar partidos (no se unieron)", "",
                "El segundo renglón no habría cabido al final del primero, pero tiene sangría "
                "propia o el primero está completo, así que quedaron separados, como en el "
                "original. Unirlos a mano solo si el segundo continúa la misma instrucción.", "",
                *[f"- p.{p}: `…{a}` / `{b}…`" for p, a, b in ctx["code_doubts"]]]
    (out_dir / "reporte.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    return md_file, out_dir / "reporte.md"


# ---------------------------------------------------------------------------
# Otros formatos: JSON, Markdown/texto, CSV, Word, Excel, PowerPoint
# ---------------------------------------------------------------------------
def esc_cell(v):
    s = "" if v is None else str(v)
    return s.replace("|", "\\|").replace("\r", "").replace("\n", "<br>").strip()


def md_table(rows):
    rows = [[esc_cell(c) for c in r] for r in rows]
    if not rows:
        return ""
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * n]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def finish(src, out_dir, front, body, figures=(), notes=(), src_words=None, ref=None):
    """Escribe <nombre>.md y reporte.md (formato común a todos los tipos).

    La cobertura cuenta apariciones (no solo palabras distintas). `ref` es el texto de
    referencia leído directo del archivo, por partes: {"parte": Counter de palabras}.
    """
    src, out_dir = Path(src), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    front = {"fuente": src.name, **{k: v for k, v in front.items() if v}}
    head = "---\n" + "\n".join(f"{k}: {v}" for k, v in front.items()) + "\n---\n\n"
    md_text = head + body.strip() + "\n"
    md_file = out_dir / f"{out_dir.name}.md"
    md_file.write_text(md_text, encoding="utf-8")
    rep = [f"# Reporte de extracción: {src.name}", "",
           f"- Markdown: `{md_file.name}` ({len(md_text):,} caracteres, "
           f"~{round(len(md_text) / 3.5):,} tokens)",
           f"- Figuras guardadas: {len(figures)} | por describir: "
           f"{md_text.count('![FIGURA: describir]')}"]
    parts = ref if ref is not None else ({"": src_words} if src_words is not None else {})
    if parts:
        total = Counter()
        for c in parts.values():
            total += c
        miss = total - words(md_text)
        n_total, n_miss = sum(total.values()) or 1, sum(miss.values())
        rep.append(f"- Cobertura de palabras: {1 - n_miss / n_total:.1%}"
                   + (f" | faltan {n_miss} de {n_total}" if n_miss else ""))
        for label, c in parts.items():           # dónde está lo que falta
            here = c & miss
            miss -= here
            if here:
                rep.append(f"- **Faltan{' en ' + label if label else ''}:** "
                           + " ".join(list(here)[:25]))
    rep += [f"- {n}" for n in notes]
    if figures:
        rep += ["", "## Figuras pendientes de describir", "", *[f"- `{f}`" for f in figures]]
    (out_dir / "reporte.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    return md_file, out_dir / "reporte.md"


# ---------------------------------------------------------------------------
# Texto de referencia leído directo del paquete (ZIP + XML) de Word, PowerPoint y Excel.
# No pasa por python-docx / python-pptx / openpyxl: sirve para detectar lo que el
# recorrido de esas bibliotecas no visita (pies, cuadros de texto, notas, SmartArt...).
# ---------------------------------------------------------------------------
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
NS_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def xml_text(data, ns, skip=()):
    """Texto de un XML de Office: une los fragmentos de cada párrafo y separa párrafos."""
    import xml.etree.ElementTree as ET
    out, hidden = [], 0
    skip = {MC_FALLBACK, *skip}                  # Fallback repite el contenido de Choice
    for ev, el in ET.iterparse(io.BytesIO(data), events=("start", "end")):
        if el.tag in skip:
            hidden += 1 if ev == "start" else -1
        elif ev == "end" and not hidden:
            if el.tag == ns + "t":
                out.append(el.text or "")
            elif el.tag == ns + "p":
                out.append("\n")
            elif el.tag in (ns + "br", ns + "tab", ns + "cr"):
                out.append(" ")
    return "".join(out)


def package_reference(src, rules, ns, skip=()):
    """{parte: Counter} con el texto de las partes del paquete que calzan con `rules`."""
    parts = {}
    with zipfile.ZipFile(src) as z:
        for name in sorted(z.namelist()):
            for pattern, label in rules:
                if re.fullmatch(pattern, name):
                    parts.setdefault(label, Counter()).update(words(xml_text(z.read(name), ns, skip)))
    return parts


def package_count(src, pattern, needle):
    """Cuántas veces aparece `needle` (bytes) en las partes cuyo nombre calza con `pattern`."""
    with zipfile.ZipFile(src) as z:
        return sum(z.read(n).count(needle) for n in z.namelist() if re.fullmatch(pattern, n))


DOCX_PARTS = [(r"word/document\.xml", "el cuerpo"), (r"word/header\d*\.xml", "encabezados"),
              (r"word/footer\d*\.xml", "pies de página"), (r"word/footnotes\.xml", "notas al pie"),
              (r"word/endnotes\.xml", "notas finales"), (r"word/comments\.xml", "comentarios")]
PPTX_PARTS = [(r"ppt/slides/slide\d+\.xml", "las diapositivas"),
              (r"ppt/notesSlides/notesSlide\d+\.xml", "las notas del orador"),
              (r"ppt/diagrams/data\d+\.xml", "SmartArt"), (r"ppt/charts/chart\d+\.xml", "gráficos")]


def xlsx_reference(src):
    """Texto de las celdas y cantidad de celdas con contenido, leídos del XML."""
    import xml.etree.ElementTree as ET
    parts, cells = {"las celdas": Counter()}, 0
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS_S + "si"):
                shared.append("".join(x.text or "" for x in si.iter(NS_S + "t")))
        for name in sorted(names):
            if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name):
                for c in ET.fromstring(z.read(name)).iter(NS_S + "c"):
                    v, f, kind = c.find(NS_S + "v"), c.find(NS_S + "f"), c.get("t")
                    text = None
                    if kind == "s" and v is not None and (v.text or "").isdigit():
                        text = shared[int(v.text)] if int(v.text) < len(shared) else ""
                    elif kind == "inlineStr":
                        text = "".join(x.text or "" for x in c.iter(NS_S + "t"))
                    elif kind == "str" and v is not None:
                        text = v.text or ""
                    if text is not None:
                        if text.strip():
                            cells += 1
                            parts["las celdas"].update(words(text))
                    elif (v is not None and (v.text or "").strip()) or f is not None:
                        cells += 1
            elif re.fullmatch(r"xl/comments\d+\.xml", name):
                parts.setdefault("comentarios de celda", Counter()).update(
                    words(" ".join(x.text or "" for x in ET.fromstring(z.read(name)).iter(NS_S + "t"))))
            elif re.fullmatch(r"xl/drawings/drawing\d+\.xml", name):
                parts.setdefault("cuadros de texto", Counter()).update(words(xml_text(z.read(name), NS_A)))
    return parts, cells


def json_to_md(data, level=0):
    """JSON a Markdown compacto: listas de objetos planos -> tabla; resto -> lista."""
    pad = "  " * level
    if isinstance(data, list) and data and all(isinstance(x, dict) for x in data) \
            and all(not isinstance(v, (dict, list)) for x in data for v in x.values()):
        cols = list(dict.fromkeys(k for x in data for k in x))
        return md_table([cols] + [[x.get(c, "") for c in cols] for x in data])
    if isinstance(data, dict):
        out = []
        for k, v in data.items():
            if isinstance(v, (dict, list)) and v:
                inner = json_to_md(v, level + 1)
                if inner.startswith("|"):
                    out.append(f"{pad}- **{k}:**\n\n{inner}\n")
                else:
                    out.append(f"{pad}- **{k}:**\n{inner}")
            else:
                out.append(f"{pad}- **{k}:** {json_scalar(v)}")
        return "\n".join(out)
    if isinstance(data, list):
        out = []
        for i, v in enumerate(data, 1):
            if isinstance(v, (dict, list)) and v:
                out.append(f"{pad}- [{i}]\n{json_to_md(v, level + 1)}")
            else:
                out.append(f"{pad}- {json_scalar(v)}")
        return "\n".join(out)
    return pad + json_scalar(data)


def json_scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if v == [] or v == {}:
        return str(v)
    return str(v)


def json_words(data):
    """Palabras de los valores (con repetición) y de las claves (una vez cada clave:
    en una tabla la clave se escribe solo en el encabezado)."""
    values, keys = Counter(), set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                keys.add(str(k))
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        else:
            values.update(words(json_scalar(x)))
    walk(data)
    for k in keys:
        values.update(words(k))
    return values


def read_text(src):
    """Texto de un archivo en UTF-8 (con o sin BOM), UTF-16 o, si no, cp1252: lo que
    exportan Excel y el Bloc de notas de Windows en español (E6)."""
    data = Path(src).read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("latin-1")


def extract_json(src, out_dir):
    try:
        data = json.loads(read_text(src))
    except ValueError as e:
        raise ExtractError(f"el JSON no es válido: {e}")
    body = json_to_md(data)
    notes = ["JSON convertido: listas de objetos -> tablas; objetos -> listas `clave: valor`.",
             "Los tipos (número/texto) no se distinguen en el Markdown; el original sigue en sources/."]
    return finish(src, out_dir, {"titulo": Path(src).stem}, body, notes=notes,
                  src_words=json_words(data))


def extract_text(src, out_dir):
    text = read_text(src).replace("\r\n", "\n").replace("\r", "\n")
    front = {"titulo": Path(src).stem}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:  # conserva la cabecera existente
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                front[k.strip()] = v.strip()
        text = text[m.end():]
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return finish(src, out_dir, front, text, src_words=words(text),
                  notes=["Texto ya optimizado: solo se limpiaron espacios y líneas vacías."])


def limit_rows(rows, label, notes):
    """Recorta una tabla enorme a MAX_ROWS filas y lo deja escrito en el reporte (E12)."""
    if MAX_ROWS and len(rows) > MAX_ROWS + 1:
        notes.append(f"**{label}: {len(rows) - 1:,} filas; se extrajeron las primeras {MAX_ROWS:,}** "
                     "(revisar: `--filas 0` extrae todas)")
        return rows[:MAX_ROWS + 1]
    return rows


def extract_csv(src, out_dir):
    raw = read_text(src)
    try:
        dialect = csv.Sniffer().sniff(raw[:4096], delimiters=",;\t|")
    except csv.Error:                # una sola columna, o no se distingue: el más frecuente
        first = raw.split("\n", 1)[0]
        dialect = csv.excel_tab if Path(src).suffix.lower() == ".tsv" or "\t" in first else csv.excel
        if dialect is csv.excel and first.count(";") > first.count(","):
            class dialect(csv.excel):
                delimiter = ";"
    # newline="": un salto de renglón dentro de un campo entre comillas es parte del campo
    rows = [r for r in csv.reader(io.StringIO(raw, newline=""), dialect) if any(c.strip() for c in r)]
    notes = [f"{len(rows)} filas x {max(map(len, rows), default=0)} columnas"]
    rows = limit_rows(rows, "CSV", notes)
    return finish(src, out_dir, {"titulo": Path(src).stem}, md_table(rows),
                  src_words=words(raw), notes=notes)


def extract_docx(src, out_dir):
    import docx
    from docx.table import Table as DTable
    from docx.text.paragraph import Paragraph as DPara
    try:
        d = docx.Document(src)
    except Exception as e:
        raise ExtractError(f"el Word no se puede abrir ({type(e).__name__}): está dañado, protegido "
                           "o es un .doc antiguo renombrado")
    out_dir = Path(out_dir)
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    figures, parts = [], []

    def run_md(r):
        t = r.text
        if not t.strip():
            return t
        lead, trail, core = t[: len(t) - len(t.lstrip())], t[len(t.rstrip()):], t.strip()
        if r.font.name and MONO.search(r.font.name):
            core = f"`{core}`"
        else:
            if r.bold:
                core = f"**{core}**"
            if r.italic:
                core = f"*{core}*"
        return lead + core + trail

    def clean(s):
        return re.sub(r"\*\*(\s+)\*\*", r"\1", s.replace("****", ""))

    def runs_md(p):
        """Texto del párrafo con formato. Los hipervínculos no están en `p.runs`: hay que
        recorrer el contenido en orden para no perder su texto ni su dirección (E5)."""
        out = []
        for item in p.iter_inner_content():
            if hasattr(item, "runs"):                         # hipervínculo
                t = clean("".join(run_md(r) for r in item.runs))
                url = getattr(item, "url", "") or getattr(item, "address", "") or ""
                if t.strip() and url.startswith(("http://", "https://", "mailto:")):
                    lead, trail = t[: len(t) - len(t.lstrip())], t[len(t.rstrip()):]
                    safe = url.replace("(", "%28").replace(")", "%29").replace(" ", "%20")
                    t = f"{lead}[{t.strip()}]({safe}){trail}"
                out.append(t)
            else:
                out.append(run_md(item))
        return clean("".join(out))

    # Formato de cada lista (viñeta o número), leído de la numeración del documento
    num_formats = {}
    try:
        root = d.part.numbering_part.element
        abstract = {a.get(NS_W + "abstractNumId"): {
            lvl.get(NS_W + "ilvl"): (lvl.find(NS_W + "numFmt").get(NS_W + "val")
                                     if lvl.find(NS_W + "numFmt") is not None else "bullet")
            for lvl in a.iter(NS_W + "lvl")} for a in root.iter(NS_W + "abstractNum")}
        for num in root.iter(NS_W + "num"):
            ref = num.find(NS_W + "abstractNumId")
            for ilvl, fmt in abstract.get(ref.get(NS_W + "val") if ref is not None else None, {}).items():
                num_formats[(int(num.get(NS_W + "numId")), int(ilvl))] = fmt
    except Exception:
        pass                                                  # documento sin listas numeradas
    counters = {}

    def list_item(p, style):
        """None si el párrafo no es de lista; si lo es, su prefijo («- », «3. », con sangría)."""
        num = p._p.pPr.numPr if p._p.pPr is not None else None
        if num is None and not ("list" in style or "lista" in style):
            return None
        level = int(num.ilvl.val) if num is not None and num.ilvl is not None else 0
        num_id = int(num.numId.val) if num is not None and num.numId is not None else style
        fmt = num_formats.get((num_id, level))
        if fmt is None:
            fmt = "decimal" if re.search(r"number|n[uú]mero", style) else "bullet"
        for k in [k for k in counters if k[0] == num_id and k[1] > level]:
            del counters[k]                                   # una lista hija vuelve a empezar
        if fmt in ("bullet", "none"):
            return "   " * level + "- "
        counters[(num_id, level)] = counters.get((num_id, level), 0) + 1
        return "   " * level + f"{counters[(num_id, level)]}. "

    def images_in(p):
        names = []
        for blip in p._p.xpath(".//a:blip"):
            rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            part = d.part.related_parts.get(rid)
            if part is None:
                continue
            name = f"img{len(figures) + 1}{Path(part.partname).suffix}"
            (assets / name).write_bytes(part.blob)
            figures.append(f"assets/{name}")
            names.append(name)
        return names

    for child in d.element.body.iterchildren():
        tag = child.tag.split("}")[1]
        if tag == "p":
            p = DPara(child, d)
            for name in images_in(p):
                parts.append(f"![FIGURA: describir](assets/{name})")
            text = runs_md(p).strip()
            if not text:
                continue
            style = (p.style.name or "").lower() if p.style is not None else ""
            m = re.search(r"(heading|título|titulo)\s*(\d)", style)
            prefix = None if m or style in ("title", "título", "titulo") else list_item(p, style)
            if style in ("title", "título", "titulo"):
                parts.append("# " + p.text.strip())
            elif m:
                parts.append("#" * min(int(m.group(2)), 3) + " " + p.text.strip())
            elif prefix is not None:
                parts.append(prefix + text)
            else:
                parts.append(text)
                for k in [k for k in counters if isinstance(k[0], str)]:
                    del counters[k]                           # lista por estilo: se interrumpió
        elif tag == "tbl":
            t = DTable(child, d)
            seen, rows = set(), []
            for r in t.rows:                                  # una celda combinada: una sola vez
                row = []
                for c in r.cells:
                    where = c._tc.getroottree().getpath(c._tc)
                    row.append("" if where in seen else c.text)
                    seen.add(where)
                rows.append(row)
            parts.append(md_table(rows))
    # juntar ítems de lista consecutivos
    body, item = "", re.compile(r"\s*(- |\d+\. )")
    for prev, cur in zip([""] + parts, parts):
        sep = "\n" if item.match(prev) and item.match(cur) else "\n\n"
        body += (sep if body else "") + cur
    cp = d.core_properties
    title = (cp.title or "").strip()
    front = {"titulo": Path(src).stem if not title or JUNK_TITLE.match(title) else title,
             "autor": cp.author, "subtitulo": cp.subject, "palabras_clave": cp.keywords}
    notes = []
    if d.sections and any(s.header and s.header.paragraphs and any(p.text.strip() for p in s.header.paragraphs)
                          for s in d.sections):
        hdr = " | ".join(p.text.strip() for s in d.sections for p in s.header.paragraphs if p.text.strip())
        body = f"<!-- ENCABEZADO ORIGINAL: {hdr} -->\n\n" + body
        notes.append("Encabezado del Word guardado como comentario.")
    n_img = package_count(src, r"word/document\.xml", b"<pic:pic")
    if n_img != len(figures):
        notes.append(f"**Imágenes en el original: {n_img} | extraídas: {len(figures)}** (revisar)")
    return finish(src, out_dir, front, body, figures, notes,
                  ref=package_reference(src, DOCX_PARTS, NS_W))


def extract_xlsx(src, out_dir):
    import openpyxl
    try:
        wb = openpyxl.load_workbook(src, data_only=True, read_only=True)
        wf = openpyxl.load_workbook(src, read_only=True)  # fórmulas, por si no hay valor guardado
    except Exception as e:
        raise ExtractError(f"el Excel no se puede abrir ({type(e).__name__}): está dañado, protegido "
                           "o es un .xls antiguo renombrado")
    parts, notes, n_cells = [], [], 0

    def shown(c):
        """El valor como se ve en la hoja: porcentaje con su signo, fecha sin hora (E12)."""
        v, fmt = c.value, getattr(c, "number_format", None) or ""
        if isinstance(v, (int, float)) and not isinstance(v, bool) and "%" in fmt:
            m = re.search(r"\.(0+)", fmt)
            return f"{v * 100:.{len(m.group(1)) if m else 0}f}%"
        if isinstance(v, dt.datetime) and v.time() == dt.time(0):
            return v.date().isoformat()
        return v

    for ws in wb.worksheets:
        frows = list(wf[ws.title].iter_rows(values_only=True))
        rows = [[shown(c) if c.value is not None or i >= len(frows) or j >= len(frows[i]) else frows[i][j]
                 for j, c in enumerate(r)]
                for i, r in enumerate(ws.iter_rows())]
        rows = [r for r in rows if any(v not in (None, "") for v in r)]
        if not rows:
            continue
        keep = [j for j in range(max(map(len, rows))) if any(j < len(r) and r[j] not in (None, "") for r in rows)]
        rows = [[r[j] if j < len(r) else "" for j in keep] for r in rows]
        hidden = " (oculta)" if getattr(ws, "sheet_state", "visible") != "visible" else ""
        rows = limit_rows(rows, f"Hoja '{ws.title}'", notes)
        parts.append(f"## Hoja: {ws.title}{hidden}\n\n{md_table(rows)}")
        n_cells += sum(1 for r in rows for v in r if str(v if v is not None else "").strip())
        notes.append(f"Hoja '{ws.title}'{hidden}: {len(rows)} filas x {len(keep)} columnas")
    notes.append("Se extraen valores calculados; las fórmulas no se copian.")
    ref, ref_cells = xlsx_reference(src)
    if ref_cells != n_cells:
        notes.append(f"**Celdas con contenido en el original: {ref_cells} | extraídas: {n_cells}** (revisar)")
    return finish(src, out_dir, {"titulo": Path(src).stem}, "\n\n".join(parts), notes=notes, ref=ref)


def extract_pptx(src, out_dir):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    try:
        prs = Presentation(src)
    except Exception as e:
        raise ExtractError(f"el PowerPoint no se puede abrir ({type(e).__name__}): está dañado, "
                           "protegido o es un .ppt antiguo renombrado")
    out_dir = Path(out_dir)
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    parts, figures = [], []

    def walk(shapes):
        for sh in shapes:
            if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                yield from walk(sh.shapes)
            else:
                yield sh

    for i, slide in enumerate(prs.slides, 1):
        title = slide.shapes.title.text.strip() if slide.shapes.title is not None and slide.shapes.title.has_text_frame else ""
        hidden = " (oculta)" if slide._element.get("show") in ("0", "false") else ""
        sec = [f"## Diapositiva {i}{hidden}" + (f": {title}" if title else "")]
        for sh in sorted(walk(slide.shapes), key=lambda s: (s.top or 0, s.left or 0)):
            if slide.shapes.title is not None and sh.shape_id == slide.shapes.title.shape_id:
                continue
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    t = "".join(r.text for r in p.runs).strip()
                    if t:
                        sec.append("  " * p.level + "- " + t)
            elif getattr(sh, "has_table", False) and sh.has_table:
                rows = [[c.text for c in r.cells] for r in sh.table.rows]
                sec.append("\n" + md_table(rows) + "\n")
            elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                name = f"d{i}-img{len(figures) + 1}.{sh.image.ext}"
                (assets / name).write_bytes(sh.image.blob)
                figures.append(f"assets/{name}")
                sec.append(f"\n![FIGURA: describir](assets/{name})\n")
            elif getattr(sh, "has_chart", False) and sh.has_chart:
                ch = sh.chart
                rows = [["Serie"] + [str(c) for c in ch.plots[0].categories]] if ch.plots else []
                for plot in ch.plots:
                    for s in plot.series:
                        rows.append([s.name] + list(s.values))
                sec.append("\n**Gráfico (datos):**\n\n" + md_table(rows) + "\n")
        if slide.has_notes_slide:
            notes_t = slide.notes_slide.notes_text_frame.text.strip()
            if notes_t:
                sec.append("\n> **Notas del orador:** " + norm(notes_t))
        parts.append("\n".join(sec))
    cp = prs.core_properties
    notes = [f"{len(prs.slides)} diapositivas"]
    n_img = package_count(src, r"ppt/slides/slide\d+\.xml", b"<p:pic>")
    if n_img != len(figures):
        notes.append(f"**Imágenes en el original: {n_img} | extraídas: {len(figures)}** (revisar)")
    title = (cp.title or "").strip()
    return finish(src, out_dir, {"titulo": Path(src).stem if not title or JUNK_TITLE.match(title) else title,
                                 "autor": cp.author},
                  "\n\n".join(parts), figures, notes,
                  ref=package_reference(src, PPTX_PARTS, NS_A, skip=(NS_A + "fld",)))


EXTRACTORS = {
    ".pdf": extract,
    ".json": extract_json,
    ".md": extract_text, ".markdown": extract_text, ".txt": extract_text,
    ".csv": extract_csv, ".tsv": extract_csv,
    ".docx": extract_docx,
    ".xlsx": extract_xlsx, ".xlsm": extract_xlsx,
    ".pptx": extract_pptx,
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_manifest(out_dir):
    try:
        return json.loads((Path(out_dir) / "fuente.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def plan(src, out_root, forzar):
    """Decide dónde extraer y si corresponde. Devuelve (carpeta, acción, motivo).

    Acciones: extraer | omitir (ya extraído, original sin cambios) |
    abortar (se perdería trabajo manual) | respaldar (con --forzar: guarda el .md y extrae).
    """
    out_dir = Path(out_root) / src.stem
    man = read_manifest(out_dir)
    if man and man.get("archivo") != src.name:      # otro original con el mismo nombre
        out_dir = Path(out_root) / f"{src.stem}-{src.suffix.lstrip('.').lower()}"
        man = read_manifest(out_dir)
    md = out_dir / f"{out_dir.name}.md"
    if not md.exists():
        return out_dir, "extraer", ""
    if man is None:
        why = "existe una extracción anterior sin registro de su original (fuente.json)"
    else:
        edited = sha256(md) != man.get("md_sha256")
        same = man.get("sha256") == sha256(src)
        if same and not forzar:
            return out_dir, "omitir", ("ya extraído y el original no cambió"
                                       + ("; el .md tiene trabajo manual" if edited else ""))
        if not edited:
            return out_dir, "extraer", ""
        why = "el .md fue editado a mano" + ("" if same else " y el original cambió")
    return out_dir, ("respaldar" if forzar else "abortar"), why


def pending(md, rep):
    """Lo que el reporte pide resolver antes de dar la extracción por terminada (E13)."""
    md_text = Path(md).read_text(encoding="utf-8", errors="replace")
    rep_text = Path(rep).read_text(encoding="utf-8", errors="replace")
    out = []
    for needle, what in (("![FIGURA: describir]", "figuras por describir"),
                         ("TRANSCRIBIR]", "páginas por transcribir"),
                         (MARK, "símbolos sin identificar")):
        if md_text.count(needle):
            out.append(f"{md_text.count(needle)} {what}")
    for needle, what in (("## Páginas que requieren revisión", "páginas que requieren revisión"),
                         ("**Faltan", "texto del original que no se extrajo"),
                         ("(revisar", "diferencias de cantidad con el original"),
                         ("## Renglones de código reunidos", "renglones de código reunidos"),
                         ("## Renglones de código que podrían", "renglones de código dudosos"),
                         ("Guiones conservados", "guiones por confirmar"),
                         ("sin carácter propio", "superíndices por revisar")):
        if needle in rep_text:
            out.append(what)
    return out


def main():
    global MAX_ROWS
    ap = argparse.ArgumentParser(
        description="Extrae un documento a Markdown compacto.",
        epilog="Código de salida: 0 extraído sin pendientes; 1 extraído con pendientes "
               "(ver reporte.md); 2 no se extrajo.")
    ap.add_argument("archivo", help="archivo a extraer (pdf, docx, pptx, xlsx, json, md, txt, csv)")
    ap.add_argument("--salida", default="extracted")
    ap.add_argument("--forzar", action="store_true",
                    help="volver a extraer aunque exista; el .md anterior se guarda como respaldo")
    ap.add_argument("--filas", type=int, default=MAX_ROWS,
                    help=f"filas máximas por hoja de Excel o CSV ({MAX_ROWS}); 0 = todas")
    a = ap.parse_args()
    MAX_ROWS = max(0, a.filas)
    src = Path(a.archivo)
    if not src.is_file():
        print(f"No existe el archivo: {src}")
        return 2
    fn = EXTRACTORS.get(src.suffix.lower())
    if fn is None:
        print(f"Formato {src.suffix} no soportado directamente. "
              "Conviértelo a PDF o DOCX primero (ver docs/extractor.md, paso 0).")
        return 2
    out_dir, action, why = plan(src, a.salida, a.forzar)
    md = out_dir / f"{out_dir.name}.md"
    def result(md, rep):
        todo = pending(md, rep) if Path(rep).is_file() else []
        print("Pendientes: " + ("; ".join(todo) if todo else "ninguno"))
        return 1 if todo else 0

    if action == "omitir":
        print(f"Sin cambios: {why}.\nMarkdown: {md}\nReporte:  {out_dir / 'reporte.md'}")
        return result(md, out_dir / "reporte.md")
    if action == "abortar":
        print(f"No se extrajo: {why}.\nMarkdown existente: {md}\n"
              "Usa --forzar para volver a extraer (el .md actual se guarda como respaldo).")
        return 2
    if action == "respaldar":
        backup = md.with_name(f"{out_dir.name}.anterior.md")
        backup.write_bytes(md.read_bytes())
        print(f"Respaldo del .md anterior ({why}): {backup}")
    try:
        md, rep = fn(src, out_dir)
    except (ExtractError, zipfile.BadZipFile) as e:
        why = str(e) if isinstance(e, ExtractError) else \
            "el archivo no es un documento de Office válido (dañado, o es un formato antiguo renombrado)"
        print(f"No se extrajo: {why}.")
        return 2
    (out_dir / "fuente.json").write_text(json.dumps({
        "archivo": src.name, "sha256": sha256(src), "md_sha256": sha256(md),
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Markdown: {md}\nReporte:  {rep}")
    return result(md, rep)


if __name__ == "__main__":
    sys.exit(main())

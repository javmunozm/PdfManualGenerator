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
import re
from collections import Counter
from pathlib import Path

import pymupdf

MONO = re.compile(r"mono|courier|consol|code|menlo", re.I)
BULLET = re.compile(r"^\s*[•●▪◦‣∙·–]\s*")
LEADER = re.compile(r"(?:\.\s*){5,}")
CAPTION = re.compile(r"^(figura|fig\.|imagen|gr[aá]fico|diagrama|esquema)\b", re.I)
NUM_HEAD = re.compile(r"^\d+(\.\d+)*\.?\s+\S")
PAGE_NUM = re.compile(r"^(p[aá]g(ina)?\.?\s*)?\d+(\s*(de|/|of)\s*\d+)?$", re.I)
WORD = re.compile(r"[\wáéíóúüñ]+", re.I)
MARGIN = 0.065  # franja superior/inferior donde viven encabezados y pies
COL_GAP = 9     # hueco mínimo (pt) entre columnas; un espacio normal mide menos


def norm(s):
    return re.sub(r"\s+", " ", s.replace("­", "")).strip()


def key(s):
    return re.sub(r"\d+", "#", norm(s).lower())


def words(s):
    return Counter(w.lower() for w in WORD.findall(s))


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


def block_lines(b):
    """Devuelve líneas (texto plano, texto md, bbox) y rasgos del bloque."""
    lines, sizes, mono, bold = [], [], True, True
    for ln in b["lines"]:
        plain = "".join(s["text"] for s in ln["spans"])
        if not plain.strip():
            continue
        lines.append((plain, span_md(ln["spans"]), ln["bbox"]))
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


def find_boilerplate(doc):
    """Líneas repetidas en la franja de encabezado/pie (o con número de página)."""
    seen, zone_pages = Counter(), Counter()
    for page in doc:
        h = page.rect.height
        found = {"top": False, "bot": False}
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                y0, y1 = ln["bbox"][1], ln["bbox"][3]
                zone = "top" if y1 < h * MARGIN else "bot" if y0 > h * (1 - MARGIN) else None
                if zone:
                    found[zone] = True
                    seen[(zone, key("".join(s["text"] for s in ln["spans"])))] += 1
        for z, v in found.items():
            zone_pages[z] += v
    n = doc.page_count
    running = {z for z, c in zone_pages.items() if n >= 3 and c >= 0.6 * n}
    return seen, running


def is_boiler(line_text, bbox, page_h, seen, running):
    y0, y1 = bbox[1], bbox[3]
    zone = "top" if y1 < page_h * MARGIN else "bot" if y0 > page_h * (1 - MARGIN) else None
    if not zone:
        return False
    return (zone in running or seen[(zone, key(line_text))] >= 2
            or bool(PAGE_NUM.match(norm(line_text))))


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


def join_lines(md_lines):
    """Une las líneas de un párrafo y corrige guiones de corte."""
    out = ""
    for ln in md_lines:
        ln = ln.strip()
        if out.endswith("-") and ln[:1].islower():
            out = out[:-1] + ln
        else:
            out = f"{out} {ln}" if out else ln
    return norm(out)


def save_pixmap(pix, path):
    if pix.colorspace and pix.colorspace.n > 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    pix.save(str(path))


# ---------------------------------------------------------------------------
# Tablas dibujadas solo con líneas horizontales (y franjas de color)
# ---------------------------------------------------------------------------
def ruled_tables(page, drawings):
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
            rect = pymupdf.Rect(g["x0"], seg[0], g["x1"], seg[-1])
            md = build_table(page, rect, seg)
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


def cell_md(page, rect):
    parts = []
    for b in page.get_text("dict", clip=rect)["blocks"]:
        for ln in b.get("lines", []):
            spans = [s for s in ln["spans"] if rect.contains(pymupdf.Point(
                (s["bbox"][0] + s["bbox"][2]) / 2, (s["bbox"][1] + s["bbox"][3]) / 2))]
            if spans:
                parts.append(span_md(spans).strip())
    return norm(" ".join(parts))


def build_table(page, rect, ys):
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
        row = [cell_md(page, pymupdf.Rect(c0, y0, c1, y1)) for c0, c1 in zip(xb, xb[1:])]
        if any(row):
            rows.append(row)
    if len(rows) < 2:
        return "NO_ES_TABLA"
    md = md_table(rows)
    if set(words(" ".join(w[4] for w in words_))) - set(words(md)):
        return None  # alguna palabra no quedó en la tabla
    return md


# ---------------------------------------------------------------------------
def page_to_md(doc, page, ctx):
    n = page.number + 1
    W, H = page.rect.width, page.rect.height
    body, assets = ctx["body"], ctx["assets"]
    items, notes, removed = [], [], []

    raw_lines = [norm(l) for l in page.get_text().splitlines() if l.strip()]

    # Página de índice: se guarda comprimida en un comentario (se regenera)
    leaders = [l for l in raw_lines if LEADER.search(l)]
    if len(leaders) >= 5 and len(leaders) >= 0.4 * len(raw_lines):
        entries = " | ".join(x for x in (norm(LEADER.sub(" ", l)) for l in raw_lines) if x)
        notes.append("índice original (omitido del cuerpo)")
        return f"<!-- p.{n} ÍNDICE ORIGINAL: {entries} -->", notes, [], raw_lines

    try:
        drawings = page.get_drawings()
        clusters = page.cluster_drawings(drawings=drawings)
    except Exception:
        drawings, clusters = [], []

    # Tablas con solo líneas horizontales (muy comunes en manuales)
    ruled, failed = ruled_tables(page, drawings)
    t_rects = [r for r, _ in ruled]
    for r, md in ruled:
        items.append((r.y0, r.x0, md))
    for r in failed:
        name = f"p{n}-tabla{len(notes) + 1}.png"
        page.get_pixmap(clip=r, dpi=100).save(str(assets / name))
        notes.append(f"posible tabla sin reconstruir (ver assets/{name})")

    # Tablas con bordes completos; se descartan detecciones que cortan palabras
    # (por ejemplo, el fondo de color del código en línea)
    tables = [t for t in page.find_tables().tables
              if not any(pymupdf.Rect(t.bbox).intersects(r) for r in t_rects)
              and clean_table(page, t)
              and (t.row_count >= 2 or (t.col_count == 1 and t.bbox[3] - t.bbox[1] > 30))]
    t_rects += [pymupdf.Rect(t.bbox) for t in tables]
    for t in tables:
        rows = t.extract()
        if len(rows) == 1 and len(rows[0]) == 1:  # caja de un solo cuadro
            txt = norm(rows[0][0] or "")
            if txt:
                items.append((t.bbox[1], t.bbox[0], "> " + txt))
        else:
            items.append((t.bbox[1], t.bbox[0], t.to_markdown().strip()))

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
        if xref in ctx["seen_imgs"]:
            continue
        ctx["seen_imgs"].add(xref)
        name = f"p{n}-img{xref}.png"
        try:
            save_pixmap(pymupdf.Pixmap(doc, xref), assets / name)
        except Exception:
            page.get_pixmap(clip=bb, dpi=150).save(str(assets / name))
        items.append((bb.y0, bb.x0, ("IMG", name, bb)))
        ctx["figures"].append(f"assets/{name}")

    # Gráficos vectoriales grandes con poco texto (diagramas, gráficos)
    for i, r in enumerate(clusters):
        if r.width < 120 or r.height < 80 or any(r.intersects(t) for t in t_rects):
            continue
        if sum(1 for d in drawings if r.contains(d["rect"])) < 6:
            continue  # caja o fondo simple, no es un gráfico
        if len(page.get_text(clip=r).strip()) > r.get_area() / 400:
            continue  # cuadro con texto: el texto ya se extrae
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
        lines, size, mono, bold = block_lines(b)
        kept = []
        for plain, md, bb in lines:
            if is_boiler(plain, bb, H, ctx["seen"], ctx["running"]):
                removed.append(norm(plain))
            else:
                kept.append((plain, md, bb))
        if not kept:
            continue
        x0, y0 = b["bbox"][0], b["bbox"][1]
        if mono:
            code = "\n".join(p.rstrip() for p, _, _ in kept)
            items.append((y0, x0, f"```\n{code}\n```"))
            continue
        plain_all = norm(" ".join(p for p, _, _ in kept))
        lvl = heading_level(plain_all, size, bold, len(kept), body, ctx["toc_levels"])
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
        text = "\n".join(join_lines(p) if not p[0].startswith("- ")
                         else "- " + join_lines([p[0][2:]] + p[1:]) for p in paras)
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
        if isinstance(it, tuple):
            _, name, r = it
            alt = "FIGURA: describir"
            if i + 1 < len(items) and isinstance(items[i + 1][2], str):
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


def clean_table(page, t):
    """Una tabla es válida si no corta palabras y contiene todo el texto de su zona."""
    r = pymupdf.Rect(t.bbox)
    real = set(words(" ".join(  # palabras completas cuyo centro cae en la tabla
        w[4] for w in page.get_text("words")
        if r.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)))))
    cells = set(words(" ".join(c or "" for row in t.extract() for c in row)))
    if cells != real or t.row_count == 0:
        return False
    # En una tabla real el texto queda dentro; si un renglón la atraviesa, es un
    # párrafo con fragmentos de código resaltados, no una tabla.
    for b in page.get_text("dict")["blocks"]:  # sin recorte: renglones completos
        for ln in b.get("lines", []):
            lb = pymupdf.Rect(ln["bbox"])
            if lb.intersects(r) and (lb.x0 < r.x0 - 4 or lb.x1 > r.x1 + 4):
                return False
    return True


def add_links(page, md):
    """Recupera las URL de los enlaces (el texto extraído no las trae)."""
    by_uri, page_words = {}, page.get_text("words")
    for ln in page.get_links():
        if ln.get("uri"):
            r = ln["from"]
            txt = " ".join(w[4] for w in page_words
                           if r.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)))
            by_uri.setdefault(ln["uri"], []).append(txt)
    missing = []
    for uri, parts in by_uri.items():
        text = norm(" ".join(parts))
        if text and text in md:
            md = md.replace(text, f"[{text}]({uri})", 1)
        else:
            missing.append(f"[{text or uri}]({uri})")
    if missing:
        md += "\n\nEnlaces: " + ", ".join(missing)
    return md


# ---------------------------------------------------------------------------
def coverage(raw_lines, md, removed):
    """Palabras del original que no aparecen en el Markdown de esa página."""
    src = words("\n".join(raw_lines)) - words("\n".join(removed))
    miss = src - words(md)
    total = sum(src.values()) or 1
    return 1 - sum(miss.values()) / total, list(miss)[:10]


def extract(pdf_path, out_root):
    pdf_path = Path(pdf_path)
    doc = pymupdf.open(pdf_path)
    name = pdf_path.stem
    out_dir = Path(out_root) / name
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    seen, running = find_boilerplate(doc)
    toc = doc.get_toc()
    ctx = dict(body=body_size(doc), assets=assets, seen=seen, running=running,
               toc_levels={key(t): lvl - min(x[0] for x in toc) + 1 for lvl, t, _ in toc},
               seen_imgs=set(),
               figures=[], scanned=[], headings=[], pending_bullet=False)

    pages_md, report_rows, all_removed, cover_lines = [], [], set(), []
    for page in doc:
        md, notes, removed, raw = page_to_md(doc, page, ctx)
        all_removed.update(removed)
        cov, miss = coverage(raw, md, removed)
        # Portada: poco texto y con letra grande -> comentario
        biggest = max((s["size"] for b in page.get_text("dict")["blocks"]
                       for ln in b.get("lines", []) for s in ln["spans"]), default=0)
        if page.number == 0 and doc.page_count > 2 and sum(len(l) for l in raw) < 400 \
                and biggest >= 1.6 * ctx["body"]:
            cover_lines = raw
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
        if cov < 0.98 or notes:
            report_rows.append(f"| {page.number + 1} | {cov:.0%} | {'; '.join(notes)} "
                               f"| {' '.join(miss)} |")

    meta = doc.metadata or {}
    titulo = meta.get("title") or (cover_lines[0] if cover_lines else name)
    numbered = sum(bool(NUM_HEAD.match(h)) for h in ctx["headings"])
    front = {
        "titulo": titulo,
        "subtitulo": meta.get("subject", ""),
        "autor": meta.get("author", ""),
        "palabras_clave": meta.get("keywords", ""),
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
    md_file = out_dir / f"{name}.md"
    md_file.write_text(md_text, encoding="utf-8")

    rep = [
        f"# Reporte de extracción: {pdf_path.name}",
        "",
        f"- Páginas: {doc.page_count} | Títulos detectados: {len(ctx['headings'])} "
        f"| Marcadores del PDF: {len(toc)}",
        f"- Markdown: `{md_file.name}` ({len(md_text):,} caracteres, ~{len(md_text) // 4:,} tokens)",
        f"- Figuras guardadas (describir): {len(ctx['figures'])}",
        f"- Páginas escaneadas (transcribir): {ctx['scanned'] or 'ninguna'}",
        "",
    ]
    if report_rows:
        rep += ["## Páginas que requieren revisión", "",
                "| Pág. | Cobertura | Notas | Palabras faltantes |", "|---|---|---|---|",
                *report_rows]
    else:
        rep.append("Cobertura 100% en todas las páginas; sin observaciones.")
    if ctx["figures"]:
        rep += ["", "## Figuras pendientes de describir", "",
                *[f"- `{f}`" for f in ctx["figures"]]]
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


def finish(src, out_root, front, body, figures=(), notes=(), src_words=None):
    """Escribe <nombre>.md y reporte.md (formato común a todos los tipos)."""
    src = Path(src)
    out_dir = Path(out_root) / src.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    front = {"fuente": src.name, **{k: v for k, v in front.items() if v}}
    head = "---\n" + "\n".join(f"{k}: {v}" for k, v in front.items()) + "\n---\n\n"
    md_text = head + body.strip() + "\n"
    md_file = out_dir / f"{src.stem}.md"
    md_file.write_text(md_text, encoding="utf-8")
    rep = [f"# Reporte de extracción: {src.name}", "",
           f"- Markdown: `{md_file.name}` ({len(md_text):,} caracteres, "
           f"~{len(md_text) // 4:,} tokens)",
           f"- Figuras guardadas (describir): {len(figures)}"]
    if src_words is not None:  # cada palabra distinta del original debe aparecer
        miss = set(src_words) - set(words(md_text))
        cov = 1 - len(miss) / (len(src_words) or 1)
        rep.append(f"- Cobertura de palabras: {cov:.1%}"
                   + (f" | faltan: {' '.join(list(miss)[:15])}" if miss else ""))
    rep += [f"- {n}" for n in notes]
    if figures:
        rep += ["", "## Figuras pendientes de describir", "", *[f"- `{f}`" for f in figures]]
    (out_dir / "reporte.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    return md_file, out_dir / "reporte.md"


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
    c = Counter()
    if isinstance(data, dict):
        for k, v in data.items():
            c += words(str(k)) + json_words(v)
    elif isinstance(data, list):
        for v in data:
            c += json_words(v)
    else:
        c += words(json_scalar(data))
    return c


def extract_json(src, out_root):
    import json
    data = json.loads(Path(src).read_text(encoding="utf-8-sig"))
    body = json_to_md(data)
    notes = ["JSON convertido: listas de objetos -> tablas; objetos -> listas `clave: valor`.",
             "Los tipos (número/texto) no se distinguen en el Markdown; el original sigue en sources/."]
    return finish(src, out_root, {"titulo": Path(src).stem}, body, notes=notes,
                  src_words=json_words(data))


def extract_text(src, out_root):
    text = Path(src).read_text(encoding="utf-8-sig")
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
    return finish(src, out_root, front, text, src_words=words(text),
                  notes=["Texto ya optimizado: solo se limpiaron espacios y líneas vacías."])


def extract_csv(src, out_root):
    import csv
    raw = Path(src).read_text(encoding="utf-8-sig")
    dialect = csv.Sniffer().sniff(raw[:4096], delimiters=",;\t|")
    rows = list(csv.reader(raw.splitlines(), dialect))
    return finish(src, out_root, {"titulo": Path(src).stem}, md_table(rows),
                  src_words=words(raw), notes=[f"{len(rows)} filas x {max(map(len, rows), default=0)} columnas"])


def extract_docx(src, out_root):
    import docx
    from docx.table import Table as DTable
    from docx.text.paragraph import Paragraph as DPara
    d = docx.Document(src)
    out_dir = Path(out_root) / Path(src).stem
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    figures, parts, all_text = [], [], []

    def runs_md(p):
        out = []
        for r in p.runs:
            t = r.text
            if not t.strip():
                out.append(t)
                continue
            lead, trail, core = t[: len(t) - len(t.lstrip())], t[len(t.rstrip()):], t.strip()
            if r.font.name and MONO.search(r.font.name):
                core = f"`{core}`"
            else:
                if r.bold:
                    core = f"**{core}**"
                if r.italic:
                    core = f"*{core}*"
            out.append(lead + core + trail)
            # imágenes dentro del párrafo
        s = "".join(out).replace("****", "")
        return re.sub(r"\*\*(\s+)\*\*", r"\1", s)

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
            all_text.append(p.text)
            for name in images_in(p):
                parts.append(f"![FIGURA: describir](assets/{name})")
            text = runs_md(p).strip()
            if not text:
                continue
            style = (p.style.name or "").lower() if p.style is not None else ""
            m = re.search(r"(heading|título|titulo)\s*(\d)", style)
            if style in ("title", "título", "titulo"):
                parts.append("# " + p.text.strip())
            elif m:
                parts.append("#" * min(int(m.group(2)), 3) + " " + p.text.strip())
            elif "list" in style or "lista" in style or p._p.pPr is not None and p._p.pPr.numPr is not None:
                parts.append("- " + text)
            else:
                parts.append(text)
        elif tag == "tbl":
            t = DTable(child, d)
            rows = [[c.text for c in r.cells] for r in t.rows]
            all_text += [c for r in rows for c in r]
            parts.append(md_table(rows))
    # juntar ítems de lista consecutivos
    body = ""
    for prev, cur in zip([""] + parts, parts):
        sep = "\n" if prev.startswith("- ") and cur.startswith("- ") else "\n\n"
        body += (sep if body else "") + cur
    cp = d.core_properties
    front = {"titulo": cp.title or Path(src).stem, "autor": cp.author, "subtitulo": cp.subject,
             "palabras_clave": cp.keywords}
    notes = []
    if d.sections and any(s.header and s.header.paragraphs and any(p.text.strip() for p in s.header.paragraphs)
                          for s in d.sections):
        hdr = " | ".join(p.text.strip() for s in d.sections for p in s.header.paragraphs if p.text.strip())
        body = f"<!-- ENCABEZADO ORIGINAL: {hdr} -->\n\n" + body
        notes.append("Encabezado del Word guardado como comentario.")
    return finish(src, out_root, front, body, figures, notes, words("\n".join(all_text)))


def extract_xlsx(src, out_root):
    import openpyxl
    wb = openpyxl.load_workbook(src, data_only=True, read_only=True)
    wf = openpyxl.load_workbook(src, read_only=True)  # fórmulas, por si no hay valor guardado
    parts, all_words, notes = [], Counter(), []
    for ws in wb.worksheets:
        frows = list(wf[ws.title].iter_rows(values_only=True))
        rows = [[v if v is not None or i >= len(frows) or j >= len(frows[i]) else frows[i][j]
                 for j, v in enumerate(r)]
                for i, r in enumerate(ws.iter_rows(values_only=True))]
        rows = [r for r in rows if any(v not in (None, "") for v in r)]
        if not rows:
            continue
        keep = [j for j in range(max(map(len, rows))) if any(j < len(r) and r[j] not in (None, "") for r in rows)]
        rows = [[r[j] if j < len(r) else "" for j in keep] for r in rows]
        parts.append(f"## Hoja: {ws.title}\n\n{md_table(rows)}")
        all_words += words(" ".join(esc_cell(v) for r in rows for v in r))
        notes.append(f"Hoja '{ws.title}': {len(rows)} filas x {len(keep)} columnas")
    notes.append("Se extraen valores calculados; las fórmulas no se copian.")
    return finish(src, out_root, {"titulo": Path(src).stem}, "\n\n".join(parts), notes=notes,
                  src_words=all_words)


def extract_pptx(src, out_root):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    prs = Presentation(src)
    out_dir = Path(out_root) / Path(src).stem
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    parts, figures, all_text = [], [], []

    def walk(shapes):
        for sh in shapes:
            if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                yield from walk(sh.shapes)
            else:
                yield sh

    for i, slide in enumerate(prs.slides, 1):
        title = slide.shapes.title.text.strip() if slide.shapes.title is not None and slide.shapes.title.has_text_frame else ""
        all_text.append(title)
        sec = [f"## Diapositiva {i}" + (f": {title}" if title else "")]
        for sh in sorted(walk(slide.shapes), key=lambda s: (s.top or 0, s.left or 0)):
            if slide.shapes.title is not None and sh.shape_id == slide.shapes.title.shape_id:
                continue
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    t = "".join(r.text for r in p.runs).strip()
                    if t:
                        all_text.append(t)
                        sec.append("  " * p.level + "- " + t)
            elif getattr(sh, "has_table", False) and sh.has_table:
                rows = [[c.text for c in r.cells] for r in sh.table.rows]
                all_text += [c for r in rows for c in r]
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
                all_text.append(notes_t)
                sec.append("\n> **Notas del orador:** " + norm(notes_t))
        parts.append("\n".join(sec))
    cp = prs.core_properties
    return finish(src, out_root, {"titulo": cp.title or Path(src).stem, "autor": cp.author},
                  "\n\n".join(parts), figures, [f"{len(prs.slides)} diapositivas"],
                  words("\n".join(all_text)))


EXTRACTORS = {
    ".pdf": extract,
    ".json": extract_json,
    ".md": extract_text, ".markdown": extract_text, ".txt": extract_text,
    ".csv": extract_csv, ".tsv": extract_csv,
    ".docx": extract_docx,
    ".xlsx": extract_xlsx, ".xlsm": extract_xlsx,
    ".pptx": extract_pptx,
}


def main():
    ap = argparse.ArgumentParser(description="Extrae un documento a Markdown compacto.")
    ap.add_argument("archivo", help="archivo en sources/ (pdf, docx, pptx, xlsx, json, md, txt, csv)")
    ap.add_argument("--salida", default="extracted")
    a = ap.parse_args()
    ext = Path(a.archivo).suffix.lower()
    fn = EXTRACTORS.get(ext)
    if fn is None:
        raise SystemExit(f"Formato {ext} no soportado directamente. "
                         "Conviértelo a PDF o DOCX primero (ver docs/extractor.md, paso 0).")
    md, rep = fn(a.archivo, a.salida)
    print(f"Markdown: {md}\nReporte:  {rep}")


if __name__ == "__main__":
    main()

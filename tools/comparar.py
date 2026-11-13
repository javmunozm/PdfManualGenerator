#!/usr/bin/env python3
"""Compara un PDF generado con su origen (ver docs/generator.md).

Uso:
    python tools/comparar.py ORIGEN GENERADO.pdf [opciones]

ORIGEN es el PDF original o un .md (el de documentos/ o el de extracted/).

Qué comprueba, contando repeticiones y no solo palabras distintas:
    Faltantes   palabras y cifras del origen que no están en el PDF           falla
    Cifras      una cifra que está, pero entre otras palabras                 falla
    Portada     datos de la cabecera (o de la portada original) ausentes      falla
    Sobrantes   texto del PDF que no está en el origen                        aviso
    Orden       pares de palabras seguidas del origen que no aparecen         aviso

Opciones:
    --ignorar "texto"        frase del origen que se reemplazó a propósito (repetible)
    --ignorar-paginas 2,3    páginas del PDF de origen que no se comparan (un índice)
    --estricto               los avisos también cuentan como falla
    --max N                  cuántos ejemplos mostrar por sección (12)

Código de salida: 0 correcto, 1 hay fallas, 2 error de uso.
"""
import argparse
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extraer  # noqa: E402  (mismas reglas de encabezados, pies e índice que el extractor)

for _s in (sys.stdout, sys.stderr):   # la consola de Windows (cp1252) no admite todo Unicode
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

TOKEN = re.compile(r"\d+(?:[.,]\d+)*|\w+")      # una cifra con separadores es una unidad
HEAD_NUM = re.compile(r"^\d+(\.\d+)*\.?\s+")
LINK = re.compile(r"\[([^\]]+)\]\((?:https?://|mailto:)[^)\s]+\)")
CALLOUTS = {"NOTA": "Nota", "CONSEJO": "Consejo", "ADVERTENCIA": "Advertencia",
            "IMPORTANTE": "Importante", "EJERCICIO": "Ejercicio"}
COVER_KEYS = ("titulo", "subtitulo", "autor", "curso", "institucion", "version", "fecha")


def clean(s):
    return unicodedata.normalize("NFKC", s).replace("­", "").lower()


def tokens(s):
    return TOKEN.findall(clean(s))


# ---------------------------------------------------------------------------
# Lectura del origen y del PDF generado: renglones (texto, ubicación)
# ---------------------------------------------------------------------------
def md_lines(text):
    """Cabecera y renglones visibles de un .md, con las reglas de manual.py."""
    lines = text.splitlines()
    cfg, i = {}, 0
    if lines and lines[0].strip() == "---":
        for j in range(1, len(lines)):
            if lines[j].strip() == "---":
                for raw in lines[1:j]:
                    if ":" in raw and not raw.lstrip().startswith("#"):
                        k, v = raw.split(":", 1)
                        cfg[k.strip().lower()] = v.strip().strip('"').strip("'")
                i = j + 1
                break
    out, in_quote = [], False
    while i < len(lines):
        st, where = lines[i].strip(), f"l.{i + 1}"
        quote = st.startswith(">")
        if st.startswith("```"):                         # código: se imprime tal cual
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                out.append((lines[i], f"l.{i + 1}"))
                i += 1
        elif st in ("\\newpage", "\\salto", "<!-- salto -->"):
            pass
        elif st.startswith("<!--"):                      # comentario: no se imprime
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            if i < len(lines) and lines[i].split("-->", 1)[1].strip():
                out.append((lines[i].split("-->", 1)[1], f"l.{i + 1}"))  # texto tras el cierre
        elif re.match(r"#{1,3}\s+", st):
            out.append((LINK.sub(r"\1", re.sub(r"^#{1,3}\s+", "", st)), where))
        elif re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", st):
            out.append((re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", st).group(1), where))
        elif st.startswith("|"):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", st.strip("|"))]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                row = re.sub(r"<br\s*/?>", " ", " ".join(cells), flags=re.I)   # salto en la celda
                out.append((LINK.sub(r"\1", row), where))
        elif quote:
            q = re.sub(r"^\s*>\s?", "", lines[i])
            m = None if in_quote else re.match(r"\[!(\w+)\]\s*(.*)", q.strip())
            if m and m.group(1).upper() in CALLOUTS:     # el tipo no se imprime si hay título
                q = m.group(2) or CALLOUTS[m.group(1).upper()]
            out.append((LINK.sub(r"\1", q), where))
        elif st:
            out.append((LINK.sub(r"\1", lines[i]), where))
        in_quote = quote
        i += 1
    return cfg, out


def pdf_lines(doc, skip_pages=()):
    """Renglones de un PDF separados en cuerpo, portada y auxiliares (índice, pies...)."""
    generated = "manual.py" in ((doc.metadata or {}).get("creator") or "")
    body_size = extraer.body_size(doc)
    bp = extraer.find_boilerplate(doc, body_size, doc.get_toc())
    body, cover, aux = [], [], 0
    for page in doc:
        n, H = page.number + 1, page.rect.height
        rows = []
        for b in page.get_text("dict")["blocks"]:
            last = None                                   # une los tramos de un mismo renglón
            for ln in b.get("lines", []):
                # ZapfDingbats solo dibuja símbolos (flechas, viñetas): su texto son letras
                # sin relación con lo que se ve, así que no cuenta como palabras.
                text = extraer.norm("".join(s["text"] for s in ln["spans"]
                                            if "Dingbats" not in s["font"]))
                if not text:
                    continue
                size = max(s["size"] for s in ln["spans"])
                if last is not None and abs(rows[last][1][1] - ln["bbox"][1]) < 2:
                    rows[last] = (rows[last][0] + " " + text, rows[last][1], max(size, rows[last][2]))
                else:
                    rows.append((text, ln["bbox"], size))
                    last = len(rows) - 1
        if n in skip_pages:
            aux += len(rows)
            continue
        if page.number == 0 and (generated or (
                doc.page_count > 2 and sum(len(r[0]) for r in rows) < 400
                and max((r[2] for r in rows), default=0) >= 1.6 * body_size)):
            cover += [r[0] for r in rows]
            continue
        leaders = sum(1 for r in rows if extraer.LEADER.search(r[0]))
        inner = [r[0] for r in rows if not extraer.zone_of(r[1][1], r[1][3], H)]
        own_index = generated and leaders and inner[:1] == ["Índice"]
        if own_index or (leaders >= (1 if generated else 5) and leaders >= 0.4 * len(rows)):
            aux += len(rows)                              # página de índice
            continue
        for text, bb, _ in rows:
            # En un PDF de manual.py el encabezado y el pie están siempre en la franja;
            # en otros PDF se aplican las reglas del extractor.
            if (extraer.zone_of(bb[1], bb[3], H) if generated
                    else extraer.is_boiler(text, bb, H, bp)):
                aux += 1
            else:
                body.append((text, f"p.{n}"))
    return body, cover, aux


def strip_heading_numbers(body, doc):
    """Quita la numeración automática de los títulos del PDF generado (numerar: si)."""
    titles = [extraer.norm(title) for _, title, _ in doc.get_toc()]
    out = []
    for text, where in body:
        if HEAD_NUM.match(text) and any(t == text or t.startswith(text + " ") for t in titles):
            text = HEAD_NUM.sub("", text)
        out.append((text, where))
    return out


def to_tokens(lines, other_vocab, soft=False):
    """Tokens con su ubicación. Une las palabras cortadas con guion al final del renglón
    cuando la palabra completa existe en el otro documento.

    Con soft=True (PDF generado) también une una palabra partida sin guion porque no
    cabía en su celda: solo si la palabra completa existe en el otro documento y alguno
    de los dos trozos no existe allí. Una palabra muy larga puede quedar en tres o más
    trozos: los intermedios se unen mientras formen el comienzo de una palabra larga."""
    starts = ({w[:k] for w in other_vocab if len(w) >= 16 for k in range(8, len(w))}
              if soft else set())
    toks, locs, cut = [], [], False              # cut: el renglón anterior terminó en guion
    for text, where in lines:
        row = tokens(text)
        if cut and row and toks and text.lstrip()[:1].islower() and toks[-1] + row[0] in other_vocab:
            toks[-1] += row[0]
            row = row[1:]
        elif soft and row and toks and (
                (toks[-1] + row[0] in other_vocab
                 and (toks[-1] not in other_vocab or row[0] not in other_vocab))
                or (toks[-1] + row[0] in starts and toks[-1] not in other_vocab)):
            toks[-1] += row[0]
            row = row[1:]
        toks += row
        locs += [where] * len(row)
        end = text.rstrip()
        cut = bool(tokens(text)) and end.endswith("-") and end[-2:-1].isalpha()
    return toks, locs


def table_headers(text):
    """Encabezados de las tablas de un .md (la fila anterior a |---|), como tokens."""
    heads, fence, lines = set(), False, text.splitlines()
    for a, b in zip(lines, lines[1:]):
        a, b = a.strip(), b.strip()
        if a.startswith("```"):
            fence = not fence
        if fence or not (a.startswith("|") and b.startswith("|")):
            continue
        if all(re.fullmatch(r":?-{2,}:?", c.strip()) for c in re.split(r"(?<!\\)\|", b.strip("|"))):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", a.strip("|"))]
            head = tuple(tokens(LINK.sub(r"\1", re.sub(r"<br\s*/?>", " ", " ".join(cells), flags=re.I))))
            if head:
                heads.add(head)
    return heads


def drop_repeated_headers(toks, locs, heads, src_t):
    """Quita del PDF generado los encabezados de tabla que manual.py repite cuando la tabla
    sigue en otra página: solo apariciones al inicio de una página, y solo las que el
    origen no tiene."""
    def count(ts, h):
        n = len(h)
        return sum(1 for i in range(len(ts) - n + 1) if ts[i] == h[0] and tuple(ts[i:i + n]) == h)

    for h in sorted(heads, key=len, reverse=True):
        surplus, n = count(toks, h) - count(src_t, h), len(h)
        i = len(toks) - n
        while surplus > 0 and i > 0:
            if toks[i] == h[0] and tuple(toks[i:i + n]) == h and locs[i] != locs[i - 1]:
                del toks[i:i + n], locs[i:i + n]
                surplus -= 1
            i -= 1
    return toks, locs


def drop_phrases(toks, locs, phrases):
    for phrase in phrases:
        p = tokens(phrase)
        if not p:
            continue
        i, keep_t, keep_l = 0, [], []
        while i < len(toks):
            if toks[i:i + len(p)] == p:
                i += len(p)
            else:
                keep_t.append(toks[i])
                keep_l.append(locs[i])
                i += 1
        toks, locs = keep_t, keep_l
    return toks, locs


# ---------------------------------------------------------------------------
def context(toks, i, span=3):
    return "«…" + " ".join(toks[max(0, i - span): i + span + 1]) + "…»"


def compare(src_t, src_l, out_t, credit):
    """Faltantes, cifras fuera de lugar, sobrantes y pares de palabras ausentes."""
    have = Counter(out_t)
    budget = have + credit                                # la portada también cuenta
    missing, left = [], Counter(budget)
    for i, t in enumerate(src_t):
        if left[t] > 0:
            left[t] -= 1
        else:
            missing.append(i)
    gone = {src_t[i] for i in missing}
    extra = Counter(out_t) - Counter(src_t)

    def pairs(ts):
        return Counter(zip(ts, ts[1:]))
    out_pairs = pairs(out_t)
    lp, rp = Counter(out_pairs), Counter(out_pairs)
    numbers = []
    for i, t in enumerate(src_t):
        if not t[0].isdigit() or t in gone:
            continue
        a = (src_t[i - 1], t) if i else None
        b = (t, src_t[i + 1]) if i + 1 < len(src_t) else None
        ok_a = a is None or lp[a] > 0
        ok_b = b is None or rp[b] > 0
        if a and ok_a:
            lp[a] -= 1
        if b and ok_b:
            rp[b] -= 1
        if not ok_a and not ok_b:                         # ningún vecino coincide
            numbers.append(i)
    order, left_pairs = [], Counter(out_pairs)
    for i in range(len(src_t) - 1):
        pair = (src_t[i], src_t[i + 1])
        if pair[0] in gone or pair[1] in gone:
            continue
        if left_pairs[pair] > 0:
            left_pairs[pair] -= 1
        else:
            order.append(i)
    return missing, numbers, extra, order


def main():
    ap = argparse.ArgumentParser(description="Compara un PDF generado con su origen.",
                                 epilog="Código de salida: 0 correcto, 1 hay fallas, 2 error.")
    ap.add_argument("origen", help="PDF original o .md")
    ap.add_argument("generado", help="PDF generado por manual.py")
    ap.add_argument("--ignorar", action="append", default=[], metavar="TEXTO")
    ap.add_argument("--ignorar-paginas", default="", metavar="N,N")
    ap.add_argument("--estricto", action="store_true")
    ap.add_argument("--max", type=int, default=12)
    a = ap.parse_args()

    src_path, out_path = Path(a.origen), Path(a.generado)
    for f in (src_path, out_path):
        if not f.is_file():
            print(f"No existe el archivo: {f}")
            return 2
    kind = src_path.suffix.lower()
    if kind not in (".pdf", ".md", ".markdown", ".txt"):
        print(f"ORIGEN debe ser PDF o Markdown, no {kind}. Para Word, PowerPoint, Excel, JSON o "
              "CSV usa el .md de extracted/<nombre>/ (su cobertura está en reporte.md).")
        return 2
    try:
        skip = {int(x) for x in a.ignorar_paginas.split(",") if x.strip()}
    except ValueError:
        print("--ignorar-paginas espera números separados por coma, por ejemplo 2,3")
        return 2

    out_doc = pymupdf.open(out_path)
    out_body, out_cover, _ = pdf_lines(out_doc)
    cfg, src_cover, src_doc = {}, [], None
    if kind == ".pdf":
        src_doc = pymupdf.open(src_path)
        src_body, src_cover, src_aux = pdf_lines(src_doc, skip)
    else:
        cfg, src_body = md_lines(src_path.read_text(encoding="utf-8-sig"))
        if cfg.get("numerar", "si").lower() in ("si", "sí", "yes", "true", "1"):
            out_body = strip_heading_numbers(out_body, out_doc)

    raw_src = {t for line, _ in src_body for t in tokens(line)}
    raw_out = {t for line, _ in out_body for t in tokens(line)}
    src_t, src_l = to_tokens(src_body, raw_out)
    out_t, out_l = to_tokens(out_body, raw_src, soft=True)
    src_t, src_l = drop_phrases(src_t, src_l, a.ignorar)
    if kind != ".pdf":
        heads = table_headers(src_path.read_text(encoding="utf-8-sig"))
        out_t, out_l = drop_repeated_headers(out_t, out_l, heads, src_t)
    cover_t = Counter(t for line in out_cover for t in tokens(line))
    missing, numbers, extra, order = compare(src_t, src_l, out_t, cover_t)

    # Portada: datos de la cabecera del .md, o texto de la portada original
    everything = set(out_t) | set(cover_t)
    ignored = {t for p in a.ignorar for t in tokens(p)}
    if kind == ".pdf":
        cover_miss = sorted({t for line in src_cover for t in tokens(line)} - everything - ignored)
    else:
        cover_miss = sorted({t for k in COVER_KEYS for t in tokens(cfg.get(k, ""))} - set(cover_t))

    size = f"Tamaño: {out_path.stat().st_size / 1024:.0f} KB"
    if src_doc:
        print(f"Páginas: {src_doc.page_count} -> {out_doc.page_count} | "
              f"Marcadores: {len(src_doc.get_toc())} -> {len(out_doc.get_toc())} | {size}")
    else:
        print(f"Páginas generadas: {out_doc.page_count} | Marcadores: {len(out_doc.get_toc())} | {size}")
    total = len(src_t) or 1
    print(f"Palabras del origen: {len(src_t)} | faltan: {len(missing)} "
          f"({1 - len(missing) / total:.1%} cubierto)")
    if missing:
        runs = []                                         # tramos de palabras seguidas
        for i in missing:
            if runs and i - runs[-1][-1] <= 2:
                runs[-1].append(i)
            else:
                runs.append([i])
        print("Faltan (dónde está en el origen · cuántas palabras · texto):")
        for run in runs[:a.max]:
            words_ = " ".join(src_t[run[0]:run[-1] + 1][:14]) + ("…" if run[-1] - run[0] >= 14 else "")
            around = context(src_t, run[0]) if len(run) == 1 else f"«{words_}»"
            print(f"  {src_l[run[0]]} · {len(run)} · {src_t[run[0]] + ' ' if len(run) == 1 else ''}{around}")
        if len(runs) > a.max:
            print(f"  ... y {len(runs) - a.max} tramos más")
    if numbers:
        print(f"Cifras con otras palabras alrededor: {len(numbers)}")
        for i in numbers[:a.max]:
            print(f"  {src_t[i]} · {src_l[i]} {context(src_t, i)}")
    if cover_miss:
        print("Portada: faltan " + " ".join(cover_miss[:a.max * 2]))
    n_extra = sum(extra.values())
    if n_extra:
        print(f"Aviso: sobran {n_extra} palabras que no están en el origen: "
              + " ".join(f"{t} x{c}" if c > 1 else t for t, c in extra.most_common(a.max)))
    if order:
        print(f"Aviso: {len(order)} pares de palabras seguidas del origen no aparecen así "
              f"(orden o contexto distinto), por ejemplo: "
              + "; ".join(f"{src_l[i]} {context(src_t, i, 2)}" for i in order[:3]))
    fails = []
    if missing:
        fails.append("faltan palabras")
    if numbers:
        fails.append("cifras fuera de lugar")
    if cover_miss:
        fails.append("portada incompleta")
    if a.estricto and n_extra:
        fails.append("sobra texto")
    if a.estricto and order:
        fails.append("orden distinto")
    print("RESULTADO: " + ("FALLA (" + ", ".join(fails) + ")" if fails else "CORRECTO"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Prepara una extracción para generar: extracted/<nombre>/ -> documentos/<nombre>/.

Uso:
    python tools/preparar.py extracted/<nombre>          (o la ruta de su .md)
    python tools/preparar.py extracted/<nombre> --forzar

Copia el .md y assets/ y aplica los ajustes que no requieren criterio
(docs/generator.md, sección 4):

    - une bloques de código, párrafos, listas y tablas partidos por un cambio de página
    - convierte "**Nota**" + párrafo en un cuadro "> [!NOTA]"
    - pasa a la cabecera los datos de la portada original que faltan
    - mueve cada enlace de la línea "Enlaces:" a su frase y saca la puntuación del enlace
    - agrega un capítulo "#" si el documento solo tiene secciones "##"

Lo que sí requiere criterio queda en una lista corta al final.

Código de salida: 0 listo para validar, 1 quedan pendientes, 2 error.
"""
import argparse
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

MARKER = re.compile(r"<!-- p\.(\d+) -->")
URL = r"(?:https?://|mailto:)[^)\s]+"
# Primera palabra del rótulo -> tipo de cuadro (español e inglés)
LABELS = {
    "nota": "NOTA", "note": "NOTA",
    "consejo": "CONSEJO", "sugerencia": "CONSEJO", "tip": "CONSEJO", "hint": "CONSEJO",
    "advertencia": "ADVERTENCIA", "precaución": "ADVERTENCIA", "atención": "ADVERTENCIA",
    "cuidado": "ADVERTENCIA", "warning": "ADVERTENCIA", "caution": "ADVERTENCIA",
    "importante": "IMPORTANTE", "important": "IMPORTANTE",
    "ejercicio": "EJERCICIO", "exercise": "EJERCICIO", "actividad": "EJERCICIO",
}
COVER_LABELS = {"curso", "autor", "autora", "versión", "version", "fecha", "institución",
                "institucion", "course", "author", "date"}
JUNK_TITLES = re.compile(r"^(\(?anonymous\)?|untitled|unspecified|sin t[ií]tulo|"
                         r"microsoft word - .*|document\d*|presentaci[oó]n\d*)$", re.I)


# ---------------------------------------------------------------------------
def split_front(text):
    """(pares clave-valor de la cabecera, cuerpo)."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                pairs = [tuple(x.strip() for x in ln.split(":", 1)) for ln in lines[1:i] if ":" in ln]
                return dict(pairs), "\n".join(lines[i + 1:])
    return {}, text


def split_blocks(body):
    """Bloques separados por líneas vacías. Un bloque de código o un comentario de
    varias líneas es un solo bloque aunque tenga líneas vacías dentro."""
    blocks, cur, inside = [], [], None
    for line in body.splitlines():
        st = line.strip()
        if inside:
            cur.append(line)
            if (inside == "code" and st.startswith("```")) or (inside == "comment" and "-->" in line):
                blocks.append("\n".join(cur))
                cur, inside = [], None
        elif st.startswith("```"):
            if cur:
                blocks.append("\n".join(cur))
            cur, inside = [line], "code"
        elif st.startswith("<!--") and not cur and "-->" not in line:
            cur, inside = [line], "comment"
        elif not st:
            if cur:
                blocks.append("\n".join(cur))
            cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def kind(b):
    first = b.lstrip().split("\n", 1)[0]
    if first.startswith("```"):
        return "code"
    if MARKER.fullmatch(b.strip()):
        return "marker"
    if first.startswith("<!--"):
        return "comment"
    if re.match(r"#{1,6}\s", first):
        return "heading"
    if first.startswith("|"):
        return "table"
    if first.startswith(">"):
        return "quote"
    if first.startswith("!["):
        return "image"
    if re.match(r"\d+[.)]\s", first):
        return "ol"
    if re.match(r"[-*+]\s", first):
        return "ul"
    if re.fullmatch(r"\*\*[^*\n]+\*\*", b.strip()):
        return "label"
    return "para"


def open_end(b):
    """¿El bloque termina sin puntuación de cierre (la frase sigue)?"""
    return not re.search(r"[.!?:;)»\"”…]$", b.rstrip().rstrip("*`_"))


def starts_lower(b):
    return b.lstrip("*_`( ")[:1].islower()


def table_head(b):
    return re.sub(r"[*\s]", "", b.split("\n", 1)[0]).lower()


# ---------------------------------------------------------------------------
def join_pages(blocks, done, pending):
    """Une lo que un cambio de página partió en dos. El marcador queda después."""
    i = 1
    while i < len(blocks) - 1:
        if kind(blocks[i]) != "marker":
            i += 1
            continue
        a, b = blocks[i - 1], blocks[i + 1]
        ka, kb, merged = kind(a), kind(b), None
        if ka == kb == "code":
            merged = a[:a.rstrip().rfind("```")].rstrip("\n") + "\n" + b.split("\n", 1)[1]
            done["bloques de código unidos"] += 1
        elif ka in ("para", "ol", "ul") and kb == "para" and open_end(a) and starts_lower(b):
            merged = a + " " + b
            done["párrafos unidos"] += 1
        elif ka == kb and ka in ("ol", "ul"):
            merged = a + "\n" + b
            done["listas unidas"] += 1
        elif ka == kb == "table":
            if table_head(a) == table_head(b):
                merged = a + "\n" + "\n".join(b.split("\n")[2:])
                done["tablas unidas"] += 1
            elif a.split("\n", 1)[0].count("|") == b.split("\n", 1)[0].count("|"):
                pending.append(f"p.{MARKER.fullmatch(blocks[i].strip()).group(1)}: una tabla sigue a otra "
                               "con las mismas columnas tras el cambio de página; si es la misma, unirlas")
        if merged is not None:
            blocks[i - 1:i + 2] = [merged, blocks[i]]
        i += 1
    return blocks


def callouts(blocks, done, pending):
    """**Nota** + párrafo -> cuadro. Un rótulo desconocido queda como pendiente."""
    out, i, unknown = [], 0, []
    while i < len(blocks):
        b = blocks[i]
        if kind(b) == "label" and i + 1 < len(blocks) and kind(blocks[i + 1]) == "para":
            label = b.strip().strip("*").strip().rstrip(":")
            word = re.match(r"[^\W\d_]+", label.lower())
            tipo = LABELS.get(word.group(0)) if word else None
            if tipo:
                title = "" if label.lower() == tipo.lower() else " " + label
                out.append(f"> [!{tipo}]{title}\n> " + blocks[i + 1].replace("\n", "\n> "))
                done["cuadros reconstruidos"] += 1
                i += 2
                continue
            if len(label) <= 60:
                unknown.append(label)
        out.append(b)
        i += 1
    for label in unknown[:4]:
        pending.append(f"«{label}» está en negrita y solo en su línea: si era un cuadro, "
                       f"escribir `> [!TIPO] {label}` y el texto con `> `")
    if len(unknown) > 4:
        pending.append(f"y {len(unknown) - 4} rótulos más en negrita sola (buscar líneas `**...**`)")
    return out


def links(blocks, done, pending):
    """Saca la puntuación de los enlaces y reubica los de las líneas "Enlaces:"."""
    fix = re.compile(r"\[([^\]\n]+?)([.,;:]+)\]\((" + URL + r")\)")
    for i, b in enumerate(blocks):
        if kind(b) not in ("code", "comment", "marker"):
            blocks[i], n = fix.subn(r"[\1](\3)\2", b)
            done["enlaces sin puntuación dentro"] += n
    out, start, left = [], 0, 0
    for b in blocks:
        if kind(b) == "marker":
            start = len(out) + 1
        if not b.startswith("Enlaces:"):
            out.append(b)
            continue
        rest = []
        for text, url in re.findall(r"\[([^\]]+)\]\((" + URL + r")\)", b):
            clean = text.strip().rstrip(".,;:").strip()
            pat = re.compile(r"(?<![\w\[])(\*{0,3})" + re.escape(clean) + r"\1(?![\w])(?!\]\()")
            hits = [(j, m) for j in range(start, len(out))
                    if kind(out[j]) in ("para", "ol", "ul", "quote", "table")
                    for m in pat.finditer(out[j])]
            if clean and len(hits) == 1:
                j, m = hits[0]
                out[j] = out[j][:m.start()] + f"[{m.group(0)}]({url})" + out[j][m.end():]
                done["enlaces reubicados"] += 1
            else:
                rest.append(f"[{text}]({url})")
        if rest:
            out.append("Enlaces: " + ", ".join(rest))
            left += len(rest)
    if left:
        pending.append(f"{left} enlaces siguen en líneas «Enlaces:» (su texto no aparece o aparece "
                       "varias veces en la página): ubicarlos a mano")
    return out


def cover(front, blocks, done, pending):
    """Datos de la portada original que no llegaron a la cabecera."""
    for b in blocks:
        m = re.match(r"<!-- p\.1 PORTADA ORIGINAL: (.*) -->$", b.strip(), re.S)
        if not m:
            continue
        lines = [x.strip() for x in m.group(1).split(" | ") if x.strip()]
        known = {v.lower() for v in front.values()}
        free = [x for x in lines if x.lower() not in known and x.lower().rstrip(":") not in COVER_LABELS]
        if free and "institucion" not in front and free[0] == lines[0]:
            front["institucion"] = free.pop(0)        # lo primero de la portada
            done["portada: institucion"] += 1
        title = front.get("titulo", "").lower()
        for x in list(free):
            pos = lines.index(x)
            if "subtitulo" not in front and pos and lines[pos - 1].lower() == title:
                front["subtitulo"] = x
                free.remove(x)
                done["portada: subtitulo"] += 1
        if free:
            pending.append("portada: datos sin ubicar en la cabecera: " + " | ".join(free)[:150])
    if JUNK_TITLES.match(front.get("titulo", "")):
        pending.append(f"cabecera: `titulo: {front['titulo']}` viene de los metadatos y no sirve; "
                       "escribir el título real")
    return front


def chapters(front, blocks, done):
    """Sin ningún capítulo "#" (PowerPoint, Excel) la numeración saldría 0.1, 0.2..."""
    levels = [len(re.match(r"#+", b).group(0)) for b in blocks if kind(b) == "heading"]
    if levels and 1 not in levels:
        first = next(i for i, b in enumerate(blocks) if kind(b) == "heading")
        blocks.insert(first, "# " + (front.get("titulo") or "Contenido"))
        done["capítulo agregado"] += 1
    return blocks


# ---------------------------------------------------------------------------
def prepare(text):
    done, pending = Counter(), []
    front, body = split_front(text)
    blocks = split_blocks(body)
    blocks = join_pages(blocks, done, pending)
    blocks = callouts(blocks, done, pending)
    blocks = links(blocks, done, pending)
    front = cover(front, blocks, done, pending)
    blocks = chapters(front, blocks, done)
    out = "---\n" + "\n".join(f"{k}: {v}" for k, v in front.items()) + "\n---\n\n" + "\n\n".join(blocks) + "\n"
    for needle, what in (("FIGURA: describir", "figuras sin describir"),
                         ("TRANSCRIBIR", "páginas escaneadas sin transcribir")):
        if out.count(needle):
            pending.append(f"{out.count(needle)} {what}: resolver en extracted/ (docs/extractor.md, "
                           "paso 3) y volver a preparar con --forzar")
    return out, done, pending


def main():
    ap = argparse.ArgumentParser(description="Prepara una extracción para generar el PDF.")
    ap.add_argument("extraccion", help="carpeta extracted/<nombre> o su archivo .md")
    ap.add_argument("--salida", default="documentos")
    ap.add_argument("--forzar", action="store_true",
                    help="reemplazar un documento ya preparado (el anterior queda como respaldo)")
    a = ap.parse_args()
    src = Path(a.extraccion)
    src_dir = src if src.is_dir() else src.parent
    md = src_dir / f"{src_dir.name}.md" if src.is_dir() else src
    if not md.is_file():
        print(f"No existe la extracción: {md}")
        return 2
    out_dir = Path(a.salida) / src_dir.name
    out_md = out_dir / f"{src_dir.name}.md"
    if out_md.exists():
        if not a.forzar:
            print(f"No se preparó: ya existe {out_md} (es la fuente del PDF y puede tener trabajo "
                  "manual).\nUsa --forzar para rehacerlo; el actual se guarda como respaldo.")
            return 2
        backup = out_md.with_name(f"{src_dir.name}.anterior.md")
        backup.write_bytes(out_md.read_bytes())
        print(f"Respaldo del documento anterior: {backup}")
    text, done, pending = prepare(md.read_text(encoding="utf-8-sig"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md.write_text(text, encoding="utf-8", newline="\n")
    n_assets = 0
    if (src_dir / "assets").is_dir():
        shutil.copytree(src_dir / "assets", out_dir / "assets", dirs_exist_ok=True)
        n_assets = sum(1 for f in (out_dir / "assets").iterdir() if f.is_file())
    print(f"Documento: {out_md} ({n_assets} archivos en assets/)")
    print("Ajustes: " + (" · ".join(f"{k} {v}" for k, v in done.items() if v) or "ninguno"))
    if pending:
        print(f"Pendientes ({len(pending)}):")
        for p in pending[:12]:
            print(f"  - {p}")
    print(f"Siguiente: python tools/validar.py {out_md}")
    return 1 if pending else 0


if __name__ == "__main__":
    sys.exit(main())

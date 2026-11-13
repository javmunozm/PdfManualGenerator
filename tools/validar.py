#!/usr/bin/env python3
"""Revisa un .md antes de generar el PDF (sin generarlo).

Uso:
    python tools/validar.py documentos/<nombre>/<nombre>.md [--estricto] [--max 15]

    error   se perdería contenido, quedaría trabajo sin terminar o el PDF saldría dañado
    aviso   sintaxis que manual.py no admite y que se imprimiría tal cual

Código de salida: 0 sin errores, 1 hay errores (con --estricto, también si hay avisos),
2 no se pudo leer el archivo.
"""
import argparse
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import manual  # noqa: E402  (mismas reglas que el generador)
from reportlab.pdfbase import pdfmetrics  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMG_OK = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
YES_NO = {"si", "sí", "yes", "true", "1", "no", "false", "0"}
BULLET = re.compile(r"(\s*)[-*+]\s+(.*)")
NUMBER = re.compile(r"(\s*)(\d+)[.)]\s+(.*)")


def encodings():
    font = pdfmetrics.getFont("Helvetica")
    return [font.encName] + [s.encName for s in font.substitutionFonts]


def has_glyph(ch, encs, cache={}):
    if ch not in cache:
        cache[ch] = False
        for enc in encs:
            try:
                ch.encode(enc)
                cache[ch] = True
                break
            except (UnicodeError, LookupError):
                pass
    return cache[ch]


class Checker:
    def __init__(self, path):
        self.path, self.found, self.no_glyph = Path(path), [], {}
        self.encs = encodings()

    def error(self, n, msg):
        self.found.append((0, n, "error", msg))

    def aviso(self, n, msg):
        self.found.append((1, n, "aviso", msg))

    def glyphs(self, text, n):
        for ch in text:
            if ord(ch) > 126 and not ch.isspace() and ch not in self.no_glyph \
                    and not has_glyph(ch, self.encs):
                self.no_glyph[ch] = n

    def inline(self, text, n, in_table=False):
        self.glyphs(text, n)
        t = re.sub(r"`[^`]+`", "", text)                       # el código en línea es literal
        if not manual.emphasis(escape(t))[1]:
            self.aviso(n, "negrita o cursiva mal cerrada o cruzada: se imprimen los asteriscos")
        if "<!--" in t:
            self.aviso(n, "comentario dentro de un renglón: se imprime; debe ir en su propia línea")
        tags = set(re.findall(r"</?([a-zA-Z]+)\b[^>]*>", t)) - ({"br"} if in_table else set())
        if tags:
            self.aviso(n, f"etiqueta HTML <{'>, <'.join(sorted(tags))}>: se imprime tal cual")
        if re.search(r"(?<!\w)_{1,2}[^\s_][^_]*_{1,2}(?!\w)", t):
            self.aviso(n, "cursiva o negrita con guion bajo: no se admite; usar asteriscos")
        if "~~" in t:
            self.aviso(n, "tachado (~~): no se admite; se imprime tal cual")
        if re.search(r"(?<!!)\[[^\]]+\]\((?!https?://|mailto:)[^)]*\)", t):
            self.aviso(n, "enlace interno o relativo: solo se admiten http(s) y mailto; queda escrito tal cual")
        if IMG.search(t) and not IMG.fullmatch(t.strip()):
            self.aviso(n, "imagen dentro de un renglón: debe ir sola en su línea")

    # ------------------------------------------------------------------
    def header(self, cfg):
        if not cfg:
            self.aviso(1, "sin cabecera (---): el título será «Manual»")
        if "color" in cfg and not re.fullmatch(r"#[0-9A-Fa-f]{6}", cfg["color"]):
            self.error(1, f"cabecera: color «{cfg['color']}» no es #RRGGBB (el generador falla)")
        if "dpi_imagenes" in cfg and not cfg["dpi_imagenes"].isdigit():
            self.error(1, f"cabecera: dpi_imagenes «{cfg['dpi_imagenes']}» no es un número")
        if cfg.get("tamano", "a4").lower() not in ("a4", "carta", "letter"):
            self.aviso(1, f"cabecera: tamano «{cfg['tamano']}» desconocido; se usará A4")
        for k in ("indice", "numerar"):
            if k in cfg and cfg[k].lower() not in YES_NO:
                self.aviso(1, f"cabecera: {k} «{cfg[k]}» debe ser si o no")
        if cfg.get("logo") and not (self.path.parent / cfg["logo"]).is_file():
            self.aviso(1, f"cabecera: no existe el logo {cfg['logo']}")
        for k in ("titulo", "subtitulo", "autor", "curso", "institucion"):
            self.glyphs(cfg.get(k, ""), 1)

    def image(self, caption, src, n):
        if "FIGURA: describir" in caption:
            self.error(n, "figura sin describir: el pie diría «FIGURA: describir»")
        if "TRANSCRIBIR" in caption:
            self.error(n, "página escaneada sin transcribir")
        self.inline(caption, n)
        src = src.strip()
        if re.match(r"https?://", src):
            self.error(n, f"imagen remota ({src[:50]}): debe ser un archivo local")
        elif not (self.path.parent / src).is_file():
            self.error(n, f"imagen no encontrada: {src} (la ruta es relativa al .md)")
        elif Path(src).suffix.lower() not in IMG_OK:
            self.error(n, f"formato de imagen no admitido: {src} (convertir a PNG o JPG)")

    def run(self):
        try:
            text = self.path.read_bytes().decode("utf-8-sig")
        except UnicodeDecodeError:
            self.error(1, "el archivo no está en UTF-8: guardarlo como UTF-8")
            return
        for n, ln in enumerate(text.split("\n"), 1):      # NUL y similares: símbolos sin mapa
            raros = sorted({c for c in ln if c == "�" or (ord(c) < 32 and c not in "\t\r")})
            if raros:
                self.error(n, "carácter de control o ilegible ("
                           + ", ".join(f"U+{ord(c):04X}" for c in raros)
                           + "): era un símbolo sin mapa de caracteres en el original; "
                             "reemplazarlo por el símbolo real")
        cfg, _ = manual.parse_front_matter(text)
        start = cfg.pop("_body_line", 0)
        written = {ln.split(":", 1)[0].strip().lower()        # lo que la cabecera trae escrito
                   for ln in text.splitlines()[1:max(start - 1, 0)] if ":" in ln}
        self.header({k: v for k, v in cfg.items() if k in written})
        numerar = cfg.get("numerar", "si").lower() in ("si", "sí", "yes", "true", "1")
        lines = text.splitlines()
        i, seen_h1, warned0 = start, False, False
        while i < len(lines):
            line, st, n = lines[i], lines[i].strip(), i + 1
            if not st or st in ("\\newpage", "\\salto", "<!-- salto -->"):
                i += 1
            elif st.startswith("```"):
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    self.glyphs(lines[j], j + 1)
                    j += 1
                if j >= len(lines):
                    self.error(n, "bloque de código sin cerrar: el resto del documento saldría como código")
                i = j + 1
            elif st.startswith("<!--"):
                j = i
                while j < len(lines) and "-->" not in lines[j]:
                    j += 1
                if j >= len(lines):
                    self.error(n, "comentario sin cerrar: el resto del documento no se imprimiría")
                elif lines[j].split("-->", 1)[1].strip():
                    self.error(j + 1, "hay texto después de --> en la misma línea: no se imprime")
                i = j + 1
            elif re.match(r"#+\s", st):
                level, title = len(st) - len(st.lstrip("#")), st.lstrip("#").strip()
                if level > 3:
                    self.aviso(n, f"título de nivel {level}: solo hay 3 niveles; sale como texto")
                elif level == 1:
                    seen_h1 = True
                elif not seen_h1 and numerar and not warned0:
                    self.aviso(n, "sección antes del primer capítulo (#): se numerará 0.1")
                    warned0 = True
                if re.search(r"\]\(", title):
                    self.aviso(n, "enlace en un título: queda escrito tal cual en el índice y el marcador")
                self.inline(title, n)
                i += 1
            elif IMG.fullmatch(st):
                m = IMG.fullmatch(st)
                self.image(m.group(1), m.group(2), n)
                i += 1
            elif st.startswith("|"):
                widths = set()
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = manual.split_row(lines[i])
                    if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                        widths.add(len(cells))
                        self.inline(lines[i], i + 1, in_table=True)
                        if max(map(len, cells)) > 2500:
                            self.aviso(i + 1, "celda muy larga: una fila no puede ocupar más de una página")
                    i += 1
                if len(widths) > 1:
                    self.aviso(n, "tabla con filas de distinta cantidad de celdas")
            elif st.startswith(">"):
                size, first = 0, re.sub(r"^\s*>\s?", "", line).strip()
                m = re.match(r"\[!(\w+)\]", first)
                if m and m.group(1).upper() not in manual.CALLOUTS:
                    self.aviso(n, f"tipo de cuadro [!{m.group(1)}] desconocido: sale como cita gris")
                while i < len(lines) and lines[i].strip().startswith(">"):
                    size += len(lines[i])
                    self.inline(re.sub(r"^\s*>\s?(\[!\w+\])?", "", lines[i]), i + 1)
                    i += 1
                if size > 3500:
                    self.aviso(n, "cuadro o cita muy largo: no puede ocupar más de una página")
            elif BULLET.match(line) or NUMBER.match(line):
                ordered = bool(NUMBER.match(line))
                pat = NUMBER if ordered else BULLET
                if ordered and int(NUMBER.match(line).group(2)) != 1:
                    self.aviso(n, f"lista numerada que empieza en {NUMBER.match(line).group(2)}: se imprime "
                                  "desde 1 (quitar líneas vacías entre ítems o lo que la interrumpe)")
                nested = False
                while i < len(lines):
                    m = pat.match(lines[i])
                    if m:
                        nested |= len(m.group(1)) >= 2
                        self.inline(m.group(m.lastindex), i + 1)
                    elif not (lines[i].strip() and lines[i].startswith("  ")):
                        break
                    else:
                        nested |= bool(BULLET.match(lines[i]) or NUMBER.match(lines[i]))
                        self.inline(lines[i], i + 1)
                    i += 1
                if nested:
                    self.aviso(n, "lista anidada: se imprime como lista simple (se pierde la jerarquía)")
            else:
                if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", st):
                    self.aviso(n, "línea horizontal: no se admite; se imprime tal cual")
                elif st.startswith("Enlaces:"):
                    self.aviso(n, "línea «Enlaces:» de la extracción: mover cada enlace a su frase")
                else:
                    self.inline(line, n)
                i += 1
        if self.no_glyph:
            chars = " ".join(f"{c} (l.{n})" for c, n in list(self.no_glyph.items())[:12])
            self.error(min(self.no_glyph.values()),
                       f"caracteres sin glifo en las fuentes del PDF (saldrían como ■): {chars}")


def main():
    ap = argparse.ArgumentParser(description="Revisa un .md antes de generar el PDF.")
    ap.add_argument("archivo")
    ap.add_argument("--estricto", action="store_true", help="los avisos también fallan")
    ap.add_argument("--max", type=int, default=15)
    a = ap.parse_args()
    if not Path(a.archivo).is_file():
        print(f"No existe el archivo: {a.archivo}")
        return 2
    c = Checker(a.archivo)
    c.run()
    found = sorted(c.found)
    for _, n, level, msg in found[:a.max]:
        print(f"l.{n} {level}: {msg}")
    if len(found) > a.max:
        print(f"... y {len(found) - a.max} más (usa --max)")
    errors = sum(1 for f in found if f[2] == "error")
    print(f"validar: {errors} errores, {len(found) - errors} avisos · {a.archivo}")
    return 1 if errors or (a.estricto and found) else 0


if __name__ == "__main__":
    sys.exit(main())

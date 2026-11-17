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

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
IMG_OK = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
YES_NO = {"si", "sí", "yes", "true", "1", "no", "false", "0"}


class Checker:
    def __init__(self, path):
        self.path, self.found, self.no_glyph = Path(path), [], {}

    def error(self, n, msg):
        self.found.append((0, n, "error", msg))

    def aviso(self, n, msg):
        self.found.append((1, n, "aviso", msg))

    def glyphs(self, text, n):
        for ch in text:
            if ord(ch) > 126 and not ch.isspace() and ch not in self.no_glyph \
                    and not manual.has_glyph(ch):      # ni en la fuente normal ni en fonts/
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
        if "idioma" in cfg and cfg["idioma"].strip().lower() not in manual.IDIOMAS:
            self.aviso(1, f"cabecera: idioma «{cfg['idioma']}» desconocido (es o en); el índice, "
                          "el pie y los rótulos saldrán en español")
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
            if "[SIMBOLO?]" in ln:
                self.error(n, "«[SIMBOLO?]»: símbolo que la extracción no pudo identificar; "
                              "reemplazarlo por el que se ve en el original (una casilla: [ ])")
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
                    self.aviso(n, "sección antes del primer capítulo (#): saldrá sin número")
                    warned0 = True
                self.inline(title, n)
                i += 1
            elif IMG.fullmatch(st):
                m = IMG.fullmatch(st)
                self.image(m.group(1), m.group(2), n)
                i += 1
            elif st.startswith("|"):
                widths, total, empty = set(), 0, 0
                while i < len(lines) and lines[i].strip().startswith("|"):
                    cells = manual.split_row(lines[i])
                    if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                        widths.add(len(cells))
                        total += len(cells)
                        empty += sum(1 for c in cells if not c.strip())
                        self.inline(lines[i], i + 1, in_table=True)
                    i += 1
                if len(widths) > 1:
                    self.aviso(n, "tabla con filas de distinta cantidad de celdas")
                caben = manual.max_table_cols(cfg.get("tamano", "A4"))
                if widths and max(widths) > caben:
                    self.error(n, f"tabla de {max(widths)} columnas: en la página caben {caben} y "
                                  "manual.py no la puede dibujar. Si viene de una extracción, es una "
                                  "tabla mal reconstruida: rehacerla con sus columnas reales")
                elif widths and max(widths) >= 4 and empty > 0.6 * total:
                    self.aviso(n, f"tabla con {round(100 * empty / total)}% de celdas vacías: "
                                  "probablemente la extracción la partió en columnas o filas de más")
            elif st.startswith(">"):
                first = re.sub(r"^\s*>\s?", "", line).strip()
                m = re.match(r"\[!(\w+)\]", first)
                if m and m.group(1).upper() not in manual.CALLOUTS:
                    self.aviso(n, f"tipo de cuadro [!{m.group(1)}] desconocido: sale como cita gris")
                while i < len(lines) and lines[i].strip().startswith(">"):
                    self.inline(re.sub(r"^\s*>\s?(\[!\w+\])?", "", lines[i]), i + 1)
                    i += 1
            elif manual.ITEM.match(line):
                while i < len(lines):                     # ítems y sus renglones de continuación
                    m = manual.ITEM.match(lines[i])
                    if m:
                        self.inline(m.group(3), i + 1)
                    elif lines[i].strip() and lines[i].startswith("  "):
                        self.inline(lines[i], i + 1)
                    else:
                        break
                    i += 1
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
        if "fuente" in cfg:                       # el documento viene de una extracción
            self.conversion(lines, start)

    # ------------------------------------------------------------------
    CODE_LABEL = re.compile(r"[\w.\-/\[\]{}@]*[\w\]}]\.[A-Za-z]{1,6}(?: \(.*\))?"      # un archivo
                            r"|[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 ·().]+")                       # TERMINAL
    SPLIT_CODE = re.compile(r"`[^`\n]+` `[^`\n]+`")
    LEADERS = re.compile(r"(?:\s\.){8,}|(?:\*\*\.\*\*\s*){5,}")
    BOLD_ROW = re.compile(r"(?:\*\*[^*\n]+\*\*\s*){2,}")

    def conversion(self, lines, start):
        """Defectos que deja una extracción y que no cambian la cuenta de palabras: la
        cobertura da 100% y `comparar.py` da correcto con todos ellos dentro. Solo se
        revisan en un documento que viene de `extraer.py` (cabecera con `fuente:`).
        Son avisos: ninguno impide generar, pero el manual no está bien convertido."""
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from preparar import label_type
        except ImportError:                       # sin preparar.py no se revisan los cuadros
            label_type = lambda _label: None      # noqa: E731
        levels, first_head, i = {}, 0, start
        while i < len(lines):
            st, n = lines[i].strip(), i + 1
            if st.startswith("```"):
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    j += 1
                body = lines[i + 1:j]
                cont = next((k for k, b in enumerate(body) if re.match(r"…\s*\S", b)), None)
                if cont is not None:
                    self.aviso(i + 2 + cont, "«… rótulo» en medio del código: es el rótulo que el original "
                                             "repite cuando el recuadro sigue en otra página "
                                             "(tools/rotulos_codigo.py)")
                if st == "```" and len(body) > 2 and body[1] == "" and self.CODE_LABEL.fullmatch(body[0]):
                    self.aviso(i + 2, f"la primera línea del bloque («{body[0][:40]}») es el rótulo del "
                                      "recuadro, no código (tools/rotulos_codigo.py)")
                i = j + 1
                continue
            if st.startswith("<!--"):
                while i < len(lines) and "-->" not in lines[i]:
                    i += 1
                i += 1
                continue
            head = re.match(r"(#+)\s", st)
            if head:
                levels[len(head.group(1))] = levels.get(len(head.group(1)), 0) + 1
                first_head = first_head or n
            elif st:
                if self.SPLIT_CODE.search(st):
                    self.aviso(n, "código en línea partido en dos por el renglón del original "
                                  "(`a` `b`): unirlo (lo hace preparar.py)")
                if self.LEADERS.search(st):
                    self.aviso(n, "renglón con puntos guía: es el índice del original dentro del "
                                  "cuerpo; pasarlo a un comentario (el índice se genera solo)")
                elif st.startswith("|"):
                    cells = manual.split_row(st)
                    if cells and not any(c.strip() for c in cells):
                        self.aviso(n, "fila de tabla vacía: la extracción partió una fila en varias")
                elif not st.startswith((">", "- ", "!")):
                    nxt = next((l.strip() for l in lines[i + 1:i + 6]
                                if l.strip() and not l.strip().startswith("<!--")), "")
                    label = re.match(r"\*\*([^*\n]{2,30})\*\*(?:[ \t]+\S|$)", st)
                    if label and label.group(1) == label.group(1).upper() \
                            and label_type(label.group(1).strip().rstrip(":")):
                        self.aviso(n, f"«{label.group(1)}» es el rótulo de un cuadro sin armar: "
                                      "escribirlo como `> [!TIPO]` (lo hace preparar.py)")
                    elif self.BOLD_ROW.fullmatch(st) and nxt.startswith("|"):
                        self.aviso(n, "encabezado de tabla suelto: la tabla sigue de la página "
                                      "anterior y repite su encabezado; unir las dos partes")
                    elif re.match(r"\*\*[^*a-zñáéíóú]{6,}\*\* \*\*[^*\n]+\*\*", st):
                        self.aviso(n, "parece un título fundido con su párrafo "
                                      "(antetítulo en mayúsculas y título, en negrita)")
            i += 1
        if sum(levels.values()) >= 10 and len(levels) == 1:
            level = next(iter(levels))
            self.aviso(first_head, f"los {levels[level]} títulos están en un mismo nivel ({'#' * level}): "
                                   "revisar la jerarquía contra los marcadores del original "
                                   "(capítulos en #, secciones en ##)")


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

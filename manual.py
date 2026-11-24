#!/usr/bin/env python3
"""Plantilla de manual en PDF.

Convierte un archivo Markdown sencillo en un manual con portada, índice,
encabezados, pies de página, marcadores (bookmarks) y estilos consistentes.

Uso:
    python manual.py ejemplo.md                 -> ejemplo.pdf
    python manual.py ejemplo.md -o salida.pdf

Requiere: reportlab (pip install reportlab). Pillow es opcional y sirve
para reducir el peso de las imágenes.
"""
import argparse
import io
import re
import sys
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Flowable, Frame, Image, KeepTogether,
    ListFlowable, ListItem, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.doctemplate import LayoutError
from reportlab.platypus.tableofcontents import TableOfContents

for _s in (sys.stdout, sys.stderr):   # la consola de Windows (cp1252) no admite todo Unicode
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Configuración por defecto (se puede cambiar en la cabecera del .md)
# ---------------------------------------------------------------------------
DEFAULTS = {
    "titulo": "Manual",
    "subtitulo": "",
    "autor": "",
    "curso": "",
    "institucion": "",
    "version": "1.0",
    "fecha": date.today().strftime("%d/%m/%Y"),
    "color": "#1F4E79",       # color principal (hex)
    "tamano": "A4",           # A4 o carta
    "indice": "si",           # si / no
    "numerar": "si",          # numerar títulos (1, 1.1, 1.1.1)
    "logo": "",               # ruta a una imagen para la portada
    "palabras_clave": "",
    "dpi_imagenes": "150",    # resolución máxima de las imágenes
    "idioma": "es",           # es / en: idioma de los textos que pone la plantilla
}

# Textos fijos que pone la plantilla, por idioma (campo `idioma` de la cabecera).
# tools/comparar.py y tools/validar.py leen esta misma tabla.
TEXTOS = {
    "es": {"indice": "Índice", "pagina": "Página {page} de {total}",
           "curso": "Curso", "autor": "Autor", "version": "Versión", "fecha": "Fecha",
           "sin_imagen": "Imagen no encontrada",
           "NOTA": "Nota", "CONSEJO": "Consejo", "ADVERTENCIA": "Advertencia",
           "IMPORTANTE": "Importante", "EJERCICIO": "Ejercicio"},
    "en": {"indice": "Contents", "pagina": "Page {page} of {total}",
           "curso": "Course", "autor": "Author", "version": "Version", "fecha": "Date",
           "sin_imagen": "Image not found",
           "NOTA": "Note", "CONSEJO": "Tip", "ADVERTENCIA": "Warning",
           "IMPORTANTE": "Important", "EJERCICIO": "Exercise"},
}
IDIOMAS = {"es": "es", "español": "es", "espanol": "es", "spanish": "es",
           "en": "en", "english": "en", "inglés": "en", "ingles": "en"}


def idioma(cfg):
    """Código del idioma del documento (es o en); un valor desconocido cuenta como es."""
    return IDIOMAS.get(str(cfg.get("idioma", "es")).strip().lower(), "es")


def textos(cfg):
    return TEXTOS[idioma(cfg)]

CALLOUTS = {
    "NOTA":        ("Nota",        "#2E75B6", "#EAF2FB"),
    "CONSEJO":     ("Consejo",     "#2E8B57", "#EAF6EF"),
    "ADVERTENCIA": ("Advertencia", "#C55A11", "#FDF1E7"),
    "IMPORTANTE":  ("Importante",  "#C00000", "#FBEAEA"),
    "EJERCICIO":   ("Ejercicio",   "#7030A0", "#F3ECF8"),
}

GRIS = colors.HexColor("#595959")
GRIS_CLARO = colors.HexColor("#D9D9D9")


# ---------------------------------------------------------------------------
# Fuentes de respaldo (G4). Helvetica y Courier solo traen los caracteres de Windows
# (cp1252). Lo demás (subíndices, flechas, griego, casillas, cirílico) se escribe con
# DejaVu Sans, que está en fonts/. Si esa carpeta falta, queda como antes: esos caracteres
# salen como ■ y tools/validar.py los informa.
# ---------------------------------------------------------------------------
FONT_DIR = Path(__file__).resolve().parent / "fonts"
RESPALDO = {}                         # nombre de la fuente -> códigos que tiene


def _registrar_fuentes():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for name in ("DejaVuSans", "DejaVuSansMono"):
        path = FONT_DIR / f"{name}.ttf"
        if path.is_file():
            try:
                font = TTFont(name, str(path))
                pdfmetrics.registerFont(font)
                RESPALDO[name] = font.face.charToGlyph
            except Exception:
                pass                  # archivo dañado: se sigue sin respaldo


_registrar_fuentes()


def _encodable(ch, enc, cache={}):
    if (ch, enc) not in cache:
        try:
            ch.encode(enc)
            cache[ch, enc] = True
        except (UnicodeError, LookupError):
            cache[ch, enc] = False
    return cache[ch, enc]


def font_for(ch, mono=False):
    """Fuente con la que se escribe un carácter: None = la normal del texto; un nombre =
    fuente de respaldo; "" = no hay glifo (sale como ■)."""
    if ord(ch) < 127 or ch.isspace() or _encodable(ch, "WinAnsiEncoding"):
        return None
    order = ("DejaVuSansMono", "DejaVuSans") if mono else ("DejaVuSans", "DejaVuSansMono")
    for name in order:
        if ord(ch) in RESPALDO.get(name, ()):
            return name
    if _encodable(ch, "SymbolEncoding") or _encodable(ch, "ZapfDingbatsEncoding"):
        return None                   # ReportLab lo sustituye solo (sin respaldo instalado)
    return ""


def has_glyph(ch):
    return font_for(ch) != ""


def runs(text, mono=False):
    """Parte un texto en tramos [(fuente de respaldo o None, texto)]."""
    out = []
    for ch in text:
        f = font_for(ch, mono) or None
        if out and out[-1][0] == f:
            out[-1][1] += ch
        else:
            out.append([f, ch])
    return out


def with_fallback(markup, mono=False):
    """Marca con <font> los caracteres que la fuente normal no tiene. `markup` ya está
    escapado; las etiquetas no se tocan."""
    if markup.isascii():
        return markup
    parts = re.split(r"(<[^>]*>)", markup)
    for i in range(0, len(parts), 2):
        parts[i] = "".join(f'<font face="{f}">{t}</font>' if f else t
                           for f, t in runs(parts[i], mono))
    return "".join(parts)


def text_width(text, font, size):
    return sum(stringWidth(t, f or font, size) for f, t in runs(text, "Courier" in font))


def draw_text(c, x, y, text, font, size, right=False):
    """drawString que cambia a la fuente de respaldo donde hace falta."""
    if right:
        x -= text_width(text, font, size)
    for f, t in runs(text, "Courier" in font):
        c.setFont(f or font, size)
        c.drawString(x, y, t)
        x += stringWidth(t, f or font, size)
    c.setFont(font, size)


# ---------------------------------------------------------------------------
# Estilos
# ---------------------------------------------------------------------------
def build_styles(primary):
    s = {}
    s["body"] = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5,
                               leading=15, alignment=TA_JUSTIFY, spaceAfter=7)
    s["h1"] = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=22,
                             leading=27, textColor=primary, spaceBefore=4,
                             spaceAfter=14)
    s["h2"] = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15,
                             leading=19, textColor=primary, spaceBefore=14,
                             spaceAfter=7)
    s["h3"] = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=12,
                             leading=15, textColor=colors.HexColor("#262626"),
                             spaceBefore=10, spaceAfter=5)
    s["list"] = ParagraphStyle("list", parent=s["body"], alignment=TA_LEFT,
                               spaceAfter=2)
    s["quote"] = ParagraphStyle("quote", parent=s["body"],
                                fontName="Helvetica-Oblique", textColor=GRIS,
                                spaceAfter=3)
    s["callout_title"] = ParagraphStyle("callout_title", fontName="Helvetica-Bold",
                                        fontSize=10.5, leading=14, spaceAfter=3)
    s["callout"] = ParagraphStyle("callout", parent=s["body"], spaceAfter=3)
    s["cell"] = ParagraphStyle("cell", fontName="Helvetica", fontSize=9.5,
                               leading=12.5)
    s["cell_head"] = ParagraphStyle("cell_head", parent=s["cell"],
                                    fontName="Helvetica-Bold",
                                    textColor=colors.white)
    s["caption"] = ParagraphStyle("caption", fontName="Helvetica-Oblique",
                                  fontSize=9, leading=12, textColor=GRIS,
                                  alignment=TA_CENTER, spaceBefore=4,
                                  spaceAfter=10)
    s["toc_title"] = ParagraphStyle("toc_title", parent=s["h1"])
    s["toc"] = [
        ParagraphStyle("toc0", fontName="Helvetica-Bold", fontSize=11,
                       leading=16, leftIndent=0, spaceBefore=6),
        ParagraphStyle("toc1", fontName="Helvetica", fontSize=10,
                       leading=14, leftIndent=16),
        ParagraphStyle("toc2", fontName="Helvetica", fontSize=9.5,
                       leading=13, leftIndent=32, textColor=GRIS),
    ]
    return s


# ---------------------------------------------------------------------------
# Formato en línea: **negrita**, *cursiva*, `código`, [enlace](url)
# ---------------------------------------------------------------------------
TAG = re.compile(r"<(/?)(b|i|u|link)\b[^>]*>")


def balanced(markup):
    """¿Las etiquetas de formato abren y cierran en orden?"""
    stack = []
    for m in TAG.finditer(markup):
        if not m.group(1):
            stack.append(m.group(2))
        elif not stack or stack.pop() != m.group(2):
            return False
    return not stack


def emphasis(text):
    """Convierte ***x***, **x** y *x*. Devuelve (texto, correcto). Si las marcas quedan
    cruzadas (**a *b** c*) no se convierte nada: se imprimen tal cual."""
    out = re.sub(r"\*\*\*(?!\s)(.+?)(?<!\s)\*\*\*", r"<b><i>\1</i></b>", text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", out)
    return (out, True) if balanced(out) else (text, False)


def inline(text, link_color="#1F4E79", br=False):
    """Formato en línea. Con br=True (celdas de tabla), <br> es un salto de renglón."""
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = escape(text)
    if br:
        text = re.sub(r"&lt;br\s*/?&gt;", "<br/>", text, flags=re.I)
    text, _ = emphasis(text)
    linked = re.sub(r"\[([^\]]+)\]\(((?:https?://|mailto:)[^)\s]+)\)",
                    rf'<link href="\2" color="{link_color}"><u>\1</u></link>', text)
    if balanced(linked):
        text = linked
    text = with_fallback(text)
    text = re.sub(
        "\x00(\\d+)\x00",
        lambda m: ('<font face="Courier" size="9.5" backColor="#EFEFEF">'
                   f"{with_fallback(escape(codes[int(m.group(1))]), mono=True)}</font>"),
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Bloque de código con fondo, que se puede dividir entre páginas
# ---------------------------------------------------------------------------
def code_title(fence):
    """Título de un bloque de código: lo que sigue a ``` en la línea que lo abre
    (```API/Program.cs, ```TERMINAL). Un nombre de lenguaje (```python, ```bash: una
    palabra corta en minúsculas) no es un título y se ignora, como siempre."""
    info = fence.strip().lstrip("`").strip()
    return "" if re.fullmatch(r"[a-z][a-z0-9+#-]{0,11}", info) else info


class CodeBlock(Flowable):
    """Recuadro de código en el que cada renglón del código ocupa un renglón.

    Letra monoespaciada clara (DejaVu Sans Mono, de fonts/; Courier si falta) a 9 pt: unos
    80 caracteres por renglón en carta. Si algún renglón no cabe, primero se reduce la
    letra de todo el bloque (hasta MIN_SIZE). Solo si aun así no cabe se parte: en un
    espacio, con sangría mayor que la del renglón y una marca gris al inicio, para que se
    vea que es continuación. Las guías de sangría (una raya fina por nivel, como en un
    editor) son dibujo, no texto: no entran al copiar ni a tools/comparar.py.
    """
    FONT = "DejaVuSansMono" if "DejaVuSansMono" in RESPALDO else "Courier"
    GLYPH = stringWidth("M", FONT, 1)          # ancho de un carácter / tamaño de la letra
    SIZE, MIN_SIZE, PAD, LINE = 9.0, 7.0, 6, 1.35   # LINE: interlineado / tamaño
    HEAD = 15                     # alto de la franja del título (nombre del archivo, «TERMINAL»)
    INK, GUIDE = colors.HexColor("#1A1A1A"), colors.HexColor("#CFCFCF")

    def __init__(self, lines, accent, rows=None, size=None, title=""):
        super().__init__()
        self.raw_lines = [ln.expandtabs(4) for ln in lines]
        self.accent = accent
        self.rows = rows          # [(texto, es_continuación)], ya calculado al dividir
        self.size = size
        self.title = title        # va en una franja arriba: no es parte del código
        self.head = self.HEAD if title else 0

    def _layout(self, width):
        avail = width - 2 * (self.PAD + 4)        # mismo margen interior a ambos lados
        longest = max((len(ln.rstrip()) for ln in self.raw_lines), default=1) or 1
        size = self.SIZE
        if longest * self.GLYPH * size > avail:
            size = max(self.MIN_SIZE, int(avail / (self.GLYPH * longest) * 10) / 10)
        max_chars = max(20, int(avail / (self.GLYPH * size)))
        rows = []
        for line in self.raw_lines:
            line = line.rstrip()
            indent = len(line) - len(line.lstrip(" "))
            hang = " " * min(indent + 4, max_chars // 2)
            cont = False
            while len(line) > max_chars:
                lead = len(line) - len(line.lstrip(" "))
                cut = line.rfind(" ", max(lead + 1, max_chars // 2), max_chars + 1)
                if cut < 0:
                    cut = max_chars               # sin espacios: corte forzado
                rows.append((line[:cut].rstrip(), cont))
                line = hang + line[cut:].lstrip(" ")
                cont = True
            rows.append((line, cont))
        return size, rows

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        if self.rows is None:
            self.size, self.rows = self._layout(availWidth)
        self.leading = round(self.size * self.LINE, 2)
        self.height = len(self.rows) * self.leading + 2 * self.PAD + self.head
        return self.width, self.height

    def split(self, availWidth, availHeight):
        self.wrap(availWidth, availHeight)
        fit = int((availHeight - 2 * self.PAD - self.head) / self.leading)
        while 0 < fit < len(self.rows) and self.rows[fit][1]:
            fit -= 1                              # no separar un renglón de su continuación
        if fit < 3 or fit >= len(self.rows):
            return []
        # El título va solo en la primera parte: repetirlo metería texto que no está en el .md
        return [CodeBlock([], self.accent, self.rows[:fit], self.size, self.title),
                CodeBlock([], self.accent, self.rows[fit:], self.size)]

    def guides(self):
        """(unidad, [(nivel, primer renglón, último renglón)]): guías de sangría, como en
        un editor.
        La unidad es la menor sangría del bloque (4 en Python, 2 en YAML o JS); con menos
        de 2 (alineaciones de un espacio) no hay guías. Una continuación de renglón partido
        y un renglón vacío no abren ni cortan niveles."""
        indents, last = [], 0
        for text, cont in self.rows:
            if cont:
                indents.append(last)
            elif not text.strip():
                indents.append(None)
            else:
                last = len(text) - len(text.lstrip(" "))
                indents.append(last)
        unit = min((i for i in indents if i), default=0)
        if unit < 2:
            return unit, []
        levels = [None if i is None else i // unit for i in indents]
        for k, lv in enumerate(levels):              # un vacío toma el menor de sus vecinos
            if lv is None:
                before = next((x for x in reversed(levels[:k]) if x is not None), 0)
                after = next((x for x in levels[k + 1:] if x is not None), 0)
                levels[k] = min(before, after)
        out = []
        for level in range(1, max(levels, default=0) + 1):
            start = None
            for k, lv in enumerate(levels + [0]):
                if lv >= level and start is None:
                    start = k
                elif lv < level and start is not None:
                    out.append((level, start, k - 1))
                    start = None
        return unit, out

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#F5F5F5"))
        c.setStrokeColor(GRIS_CLARO)
        c.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=1)
        if self.title:
            top = self.height - self.head
            c.setFillColor(colors.HexColor("#E4E4E4"))
            c.roundRect(0, top, self.width, self.head, 3, fill=1, stroke=0)
            c.rect(0, top, self.width, 3, fill=1, stroke=0)       # esquinas rectas abajo
            c.setFillColor(colors.HexColor("#4D4D4D"))
            x = self.PAD + 4
            for f, t in runs(self.title):
                font = f or "Helvetica-Bold"
                c.setFont(font, 7.5)
                c.drawString(x, top + 4.6, t)
                x += stringWidth(t, font, 7.5)
        c.setFillColor(self.accent)
        c.rect(0, 0, 2.5, self.height, fill=1, stroke=0)
        x0, cw = self.PAD + 4, self.GLYPH * self.size
        y = self.height - self.PAD - self.size - self.head
        c.setStrokeColor(colors.HexColor("#8C8C8C"))
        c.setLineWidth(0.7)
        for text, cont in self.rows:               # marca de continuación (dibujo, no texto)
            if cont:
                x = x0 + (len(text) - len(text.lstrip(" ")) - 2.2) * cw
                c.lines([(x, y + self.size * 0.75, x, y + self.size * 0.25),
                         (x, y + self.size * 0.25, x + 1.3 * cw, y + self.size * 0.25)])
            y -= self.leading
        top = self.height - self.PAD - self.size - self.head      # base del primer renglón
        c.setStrokeColor(self.GUIDE)
        c.setLineWidth(0.6)
        unit, segments = self.guides()
        for level, first, last in segments:
            x = x0 + (level - 1) * unit * cw + 0.35 * cw
            y1 = top - first * self.leading + self.size * 0.85
            y2 = top - last * self.leading - self.size * 0.35
            c.line(x, y1, x, y2)
        c.setFillColor(self.INK)
        y = top
        for text, _ in self.rows:
            if text.isascii():
                c.setFont(self.FONT, self.size)
                c.drawString(x0, y, text)
            else:                     # cada tramo en su columna: el diagrama no se desalinea
                col = 0
                for f, t in runs(text, mono=True):
                    c.setFont(f or self.FONT, self.size)
                    c.drawString(x0 + col * cw, y, t)
                    col += len(t)
            y -= self.leading


# ---------------------------------------------------------------------------
# Imágenes (con reducción opcional de peso usando Pillow)
# ---------------------------------------------------------------------------
def load_image(path, max_width, max_height, dpi):
    try:
        from PIL import Image as PILImage
    except ImportError:
        PILImage = None

    if PILImage is None:
        img = Image(str(path))
        iw, ih = img.imageWidth, img.imageHeight
        ratio = min(max_width / iw, max_height / ih, 1.0)
        img.drawWidth, img.drawHeight = iw * ratio, ih * ratio
        return img

    with PILImage.open(path) as im:
        iw, ih = im.size
        ratio = min(max_width / iw, max_height / ih, 1.0)
        draw_w, draw_h = iw * ratio, ih * ratio
        # Píxeles necesarios a la resolución elegida
        target_w = int(draw_w / 72 * dpi)
        im = im.copy()
        if iw > target_w:
            im = im.resize((target_w, int(ih * target_w / iw)), PILImage.LANCZOS)
        buf = io.BytesIO()
        if im.mode in ("RGBA", "LA", "P"):
            im.save(buf, format="PNG", optimize=True)
        else:
            im.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
        buf.seek(0)
    return Image(buf, width=draw_w, height=draw_h)


# ---------------------------------------------------------------------------
# Lectura del Markdown
# ---------------------------------------------------------------------------
def parse_front_matter(text):
    cfg = dict(DEFAULTS)
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for raw in lines[1:i]:
                    if ":" in raw and not raw.lstrip().startswith("#"):
                        k, v = raw.split(":", 1)
                        k, v = k.strip().lower(), v.strip().strip('"').strip("'")
                        if v or k not in SIN_VACIO:   # `fecha:` vacía = la de hoy (G13)
                            cfg[k] = v
                cfg["_body_line"] = i + 1         # líneas que ocupa la cabecera
                return cfg, "\n".join(lines[i + 1:])
    return cfg, text


# Campos que, escritos sin valor, conservan su valor por defecto
SIN_VACIO = {"titulo", "fecha", "color", "tamano", "indice", "numerar", "dpi_imagenes", "idioma"}


class ConfigError(Exception):
    """La cabecera tiene un valor con el que no se puede generar el PDF."""


class TableError(Exception):
    """Una tabla del .md no se puede dibujar (más columnas de las que caben)."""


MIN_COL = 30          # pt: ancho mínimo útil de una columna (12 de relleno + unas letras)


def max_table_cols(tamano="A4"):
    """Cuántas columnas caben en una tabla a lo ancho de la página (N9). Lo usan el
    generador y tools/validar.py, para que el validador rechace lo que no se dibuja."""
    width = (LETTER if str(tamano).lower() in ("carta", "letter") else A4)[0]
    return int((width - 5 * cm - 12) // MIN_COL)


def check_config(cfg):
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", cfg["color"]):
        raise ConfigError(f"cabecera: color «{cfg['color']}» no es un color #RRGGBB (ejemplo: #1F4E79)")
    if not cfg["dpi_imagenes"].isdigit() or int(cfg["dpi_imagenes"]) < 1:
        raise ConfigError(f"cabecera: dpi_imagenes «{cfg['dpi_imagenes']}» no es un número (ejemplo: 150)")


def fit(text, font, size, width):
    """El texto, recortado con «…» si no cabe en ese ancho (encabezado, pie, portada)."""
    if text_width(text, font, size) <= width:
        return text
    while text and text_width(text + "…", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


class SplitTable(Table):
    """Tabla que parte una fila por dentro solo cuando esa fila no cabe en una página
    entera (G2). En los demás casos la fila pasa completa a la página siguiente."""
    FULL = 0                      # alto útil de una página; lo fija build_pdf

    def split(self, availWidth, availHeight):
        self.splitInRow = 0
        parts = super().split(availWidth, availHeight)
        if not parts and availHeight >= 0.85 * self.FULL:
            self.splitInRow = 1
            parts = super().split(availWidth, availHeight)
        return parts


def split_row(row):
    """Celdas de una fila de tabla. Una barra escrita como \\| o dentro de `código` es
    texto de la celda, no un separador."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    cells, cur, in_code, i = [], "", False, 0
    while i < len(row):
        ch = row[i]
        if ch == "\\" and row[i + 1:i + 2] == "|":
            cur += "|"
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    cells.append(cur.strip())
    return cells


ITEM = re.compile(r"(\s*)([-*+]|\d+[.)])\s+(.*)")       # ítem de lista: sangría, marca, texto
LEAD_LABEL = re.compile(r"\*\*\[[A-ZÁÉÍÓÚÑ ]+\]\*\*")    # rótulo al inicio: **[READ ONLY]**


class Builder:
    def __init__(self, cfg, styles, base_dir, frame_w, frame_h):
        self.cfg = cfg
        self.s = styles
        self.base = base_dir
        self.fw, self.fh = frame_w, frame_h
        self.primary = colors.HexColor(cfg["color"])
        self.t = textos(cfg)
        self.link = cfg["color"]
        self.numerar = cfg["numerar"].lower() in ("si", "sí", "yes", "true", "1")
        self.counters = [0, 0, 0]
        self.story = []
        self.first_h1 = True
        self.bm = 0
        self.line = 0             # línea del .md que se está leyendo
        self.first_line = 0       # líneas que ocupa la cabecera
        self.warnings = []
        self.no_glyph = set()

    def para(self, text, style, link=None, br=False):
        """Párrafo con formato en línea. Si no se puede interpretar, se imprime literal."""
        self.glyphs(text)
        try:
            return Paragraph(inline(text, link or self.link, br), style)
        except ValueError:
            self.warnings.append(f"l.{self.line}: formato en línea no reconocido; se imprimió tal cual")
            return Paragraph(escape(text), style)

    def p(self, text, style="body"):
        return self.para(text, self.s[style])

    # --- títulos -----------------------------------------------------------
    def heading(self, level, text):
        lvl = level - 1
        self.counters[lvl] += 1
        for j in range(lvl + 1, 3):
            self.counters[j] = 0
        label = text
        if self.numerar and self.counters[0]:     # una sección sin capítulo no se numera (0.1)
            num = ".".join(str(n) for n in self.counters[:lvl + 1])
            label = f"{num}{'.' if lvl == 0 else ''}  {text}"
        if lvl == 0:
            if not self.first_h1:
                self.story.append(PageBreak())
            self.first_h1 = False
        else:
            self.story.append(CondPageBreak(3 * cm))
        para = self.para(label, self.s[f"h{level}"])
        self.bm += 1
        para._toc_level = lvl
        plain = re.sub(r"\[([^\]]+)\]\((?:https?://|mailto:)[^)\s]+\)", r"\1", label)
        para._toc_text = re.sub(r"[`*]", "", plain.replace("  ", " "))   # sin formato ni enlaces
        para._bm_key = f"h{self.bm}"
        self.story.append(para)
        if lvl == 0:
            self.story.append(_Rule(self.primary))

    # --- bloques -----------------------------------------------------------
    def col_widths(self, cells):
        """Ancho de cada columna según su contenido, sobre el ancho total de la página.

        Cada columna recibe al menos el ancho de su palabra más larga (un comando en
        `código` cuenta entero), para que no se parta por la mitad; lo que sobra se
        reparte según cuánto texto tiene cada una. Si ni las palabras caben, el ancho se
        reparte en proporción a ellas.
        """
        ncols, size, pad = len(cells[0]), self.s["cell"].fontSize, 14
        need, want, words = [0.0] * ncols, [0.0] * ncols, [0.0] * ncols
        for row in cells:
            for c, cell in enumerate(row):
                for part in re.split(r"<br\s*/?>", cell, flags=re.I):
                    line = 0.0
                    for i, piece in enumerate(re.split(r"`([^`]+)`", part)):
                        font = "Courier" if i % 2 else "Helvetica-Bold"   # negrita: cota superior
                        if not i % 2:
                            piece = re.sub(r"\[([^\]]+)\]\([^)\s]+\)", r"\1", piece)
                            piece = piece.replace("*", "").replace("\\|", "|")
                        for word in piece.split():
                            need[c] = max(need[c], stringWidth(word, font, size))
                            if not i % 2:
                                words[c] = max(words[c], stringWidth(word, font, size))
                        line += stringWidth(piece, font, size)
                    want[c] = max(want[c], line)
        cap = 0.6 * self.fw if ncols > 1 else self.fw
        need = [min(n + pad, cap) for n in need]
        want = [max(min(w + pad, cap), n) for w, n in zip(want, need)]
        if sum(need) >= self.fw:
            # No cabe todo. Antes de repartir en proporción (que parte palabras normales:
            # «component-es»), se deja a cada columna el ancho de su palabra más larga y
            # lo que falta lo ceden las columnas con código largo, que sí se puede partir.
            words = [max(MIN_COL, min(w + pad, n)) for w, n in zip(words, need)]
            extra = [n - w for n, w in zip(need, words)]
            if sum(words) < self.fw and sum(extra) > 0:
                # Lo que queda se reparte de menor a mayor: un código corto
                # (`ValidationBehavior`) recibe todo lo que pide y queda entero; solo las
                # columnas con el código más largo se quedan cortas y lo parten.
                widths, left = list(words), self.fw - sum(words)
                order = sorted(range(ncols), key=lambda c: extra[c])
                for pos, c in enumerate(order):
                    give = min(extra[c], left / (ncols - pos))
                    widths[c] += give
                    left -= give
                return widths
            # Ninguna columna baja de MIN_COL: una columna vacía entre otras muy anchas
            # quedaba con menos ancho que su relleno y ReportLab no la podía dibujar (N9)
            widths = [self.fw * n / sum(need) for n in need]
            low = [i for i, w in enumerate(widths) if w < MIN_COL]
            if low:
                deficit = sum(MIN_COL - widths[i] for i in low)
                spare = sum(w - MIN_COL for w in widths if w >= MIN_COL)
                widths = [MIN_COL if w < MIN_COL else w - deficit * (w - MIN_COL) / spare
                          for w in widths]
            return widths
        if sum(want) <= self.fw:
            return [self.fw * w / sum(want) for w in want]
        spare, flex = self.fw - sum(need), [w - n for w, n in zip(want, need)]
        return [n + spare * f / sum(flex) for n, f in zip(need, flex)]

    def table(self, rows):
        cells = [split_row(r) for r in rows]
        cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
        if not cells:
            return
        ncols = max(len(r) for r in cells)
        if ncols * MIN_COL > self.fw:
            # ReportLab fallaría con «negative availWidth» y sin decir dónde (N9)
            raise TableError(f"l.{self.line}: la tabla tiene {ncols} columnas y en la página caben "
                             f"{int(self.fw // MIN_COL)}. Si viene de una extracción, es una tabla "
                             "mal reconstruida (celdas vacías de más): rehacerla con sus columnas reales")
        cells = [r + [""] * (ncols - len(r)) for r in cells]
        data = [[self.para(c, self.s["cell_head"], "#FFFFFF", br=True) for c in cells[0]]]
        data += [[self.para(c, self.s["cell"], br=True) for c in r] for r in cells[1:]]
        t = SplitTable(data, colWidths=self.col_widths(cells), repeatRows=1, hAlign="LEFT")
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), self.primary),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRIS_CLARO),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
        for i in range(2, len(data), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F2F2F2")))
        t.setStyle(TableStyle(style))
        self.story += [t, Spacer(1, 10)]

    def lst(self, entries):
        """Listas a partir de [(sangría, numerada, número escrito, texto)]. Una lista
        numerada empieza en el número que trae escrito (G3) y un ítem con más sangría
        que el anterior abre una lista dentro de ese ítem (G17)."""
        def make(k, depth):
            indent, ordered, first = entries[k][0], entries[k][1], entries[k][2]
            items = []
            while k < len(entries) and entries[k][0] >= indent:
                if entries[k][0] >= indent + 2 and items:      # más adentro: lista hija
                    sub, k = make(k, depth + 1)
                    items[-1].append(sub)
                elif entries[k][1] != ordered:                 # cambia de tipo: otra lista
                    break
                else:
                    items.append([self.p(entries[k][3], "list")])
                    k += 1
            flow = ListFlowable(
                [ListItem(parts, leftIndent=16) for parts in items],
                bulletType="1" if ordered else "bullet",
                start=str(first) if ordered else ("•", "–")[depth % 2],
                bulletFormat="%s." if ordered else None,
                bulletColor=self.primary,
                bulletFontName="Helvetica-Bold",
                bulletFontSize=10 if ordered else 11,
                leftIndent=16,
            )
            return flow, k

        k = 0
        while k < len(entries):
            flow, k = make(k, 0)
            self.story.append(flow)
        self.story.append(Spacer(1, 6))

    def quote(self, lines):
        m = re.match(r"\[!(\w+)\]\s*(.*)", lines[0].strip()) if lines else None
        if m and m.group(1).upper() in CALLOUTS:
            name, border, bg = CALLOUTS[m.group(1).upper()]
            title = m.group(2) or self.t[m.group(1).upper()]
            body_lines = lines[1:]
        else:
            name, border, bg, title, body_lines = None, "#A6A6A6", None, None, lines

        # Una fila por párrafo: así un cuadro largo puede seguir en la página siguiente (G2)
        content, sizes = [], []
        if title:
            ts = ParagraphStyle("ct", parent=self.s["callout_title"],
                                textColor=colors.HexColor(border))
            content.append([self.para(title, ts)])
        for para in "\n".join(body_lines).split("\n\n"):
            para = " ".join(x.strip() for x in para.splitlines()).strip()
            if para:
                content.append([self.p(para, "callout" if name else "quote")])
                sizes.append(len(para))
        if not content:
            return

        t = SplitTable(content, colWidths=[self.fw])
        style = [
            ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(border)),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, 0), 7),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 5),
        ]
        # El título no queda solo al final de una página. Solo con un primer párrafo
        # corto: si título y párrafo no caben juntos en una página, ReportLab no termina.
        if title and sizes and sizes[0] < 1200:
            style.append(("NOSPLIT", (0, 0), (-1, 1)))
        if bg:
            style.append(("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)))
        t.setStyle(TableStyle(style))
        self.story += [t, Spacer(1, 10)]

    def image(self, caption, src):
        path = (self.base / src).resolve()
        if "FIGURA: describir" in caption or "TRANSCRIBIR" in caption:
            self.warn("figura sin describir o página sin transcribir: el pie se imprimió tal cual")
        if not path.is_file():
            self.warn(f"imagen no encontrada: {src}")
            self.story.append(self.p(f"**[{self.t['sin_imagen']}: {src}]**"))
            return
        img = load_image(path, self.fw, self.fh * 0.6, int(self.cfg["dpi_imagenes"]))
        parts = [img]
        if caption:
            parts.append(self.p(caption, "caption"))
        # Un título seguido de una figura no queda solo al final de la página (G12)
        if len(self.story) > 1 and getattr(self.story[-1], "_toc_level", 0) \
                and isinstance(self.story[-2], CondPageBreak):
            self.story[-2] = CondPageBreak(img.drawHeight + 80)
        self.story.append(KeepTogether(parts))

    def warn(self, msg):
        self.warnings.append(f"l.{self.line}: {msg}")

    def glyphs(self, text):
        """Avisa, una vez por carácter, de los que ninguna fuente tiene (salen como ■)."""
        if text.isascii():
            return
        missing = sorted({ch for ch in text if font_for(ch) == ""} - self.no_glyph)
        if missing:
            self.no_glyph.update(missing)
            self.warn("caracteres sin glifo en las fuentes del PDF (salen como ■): " + " ".join(missing))

    # --- recorrido línea por línea -----------------------------------------
    def build(self, text):
        lines = text.splitlines()
        i, para = 0, []

        def flush():
            if para:
                text = " ".join(x.strip() for x in para)
                # Un párrafo que presenta lo que sigue («...:» o un rótulo corto como
                # «**[RUN]** Windows:») no queda solo al pie de la página: si no queda lugar
                # para él y unos renglones de lo siguiente, empieza en la página siguiente.
                # (keepWithNext movería entero un bloque largo y dejaría páginas a medias.)
                if text.rstrip().endswith(":") or (LEAD_LABEL.match(text) and len(text) <= 200):
                    self.story.append(CondPageBreak(3.5 * cm))
                self.story.append(self.p(text))
                para.clear()

        while i < len(lines):
            line = lines[i]
            st = line.strip()
            if not para:
                self.line = i + 1 + self.first_line

            if not st:
                flush(); i += 1; continue

            if st.startswith("```"):
                flush()
                code = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code.append(lines[i]); i += 1
                if i >= len(lines):
                    self.warn("bloque de código sin cerrar: el resto del documento salió como código")
                title = code_title(st)
                self.glyphs("".join(code) + title)
                self.story += [CodeBlock(code or [""], self.primary, title=title), Spacer(1, 10)]
                i += 1; continue

            if st in ("\\newpage", "\\salto", "<!-- salto -->"):
                flush(); self.story.append(PageBreak()); i += 1; continue

            if st.startswith("<!--"):  # comentarios: no se imprimen
                flush()
                while i < len(lines) and "-->" not in lines[i]:
                    i += 1
                if i >= len(lines):
                    self.warn("comentario sin cerrar: el resto del documento no se imprimió")
                elif lines[i].split("-->", 1)[1].strip():
                    self.warn("hay texto después de --> en la misma línea: no se imprimió")
                i += 1; continue

            if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", st):
                self.warn("línea horizontal: no se admite; se imprimió tal cual")
            elif re.match(r"#{4,}\s", st):
                self.warn("título de nivel 4 o más: solo hay 3 niveles; salió como texto")

            m = re.match(r"(#{1,3})\s+(.*)", st)
            if m:
                flush(); self.heading(len(m.group(1)), m.group(2).strip()); i += 1; continue

            m = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", st)
            if m:
                flush(); self.image(m.group(1), m.group(2)); i += 1; continue

            if st.startswith("|"):
                flush()
                rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    rows.append(lines[i]); i += 1
                self.table(rows); continue

            if st.startswith(">"):
                flush()
                q = []
                while i < len(lines) and lines[i].strip().startswith(">"):
                    q.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
                self.quote(q); continue

            if ITEM.match(line) and not re.fullmatch(r"(\*{3,}|-{3,})", st):
                flush()
                entries = []                # (sangría, numerada, número escrito, texto)
                while i < len(lines):
                    mm = ITEM.match(lines[i])
                    if mm:
                        mark = mm.group(2)
                        entries.append([len(mm.group(1).expandtabs(4)), mark[0].isdigit(),
                                        int(mark[:-1]) if mark[0].isdigit() else 0, mm.group(3)])
                        i += 1
                    elif lines[i].strip() and lines[i].startswith("  "):
                        entries[-1][3] += " " + lines[i].strip(); i += 1
                    elif not lines[i].strip() and i + 1 < len(lines) and (
                            lambda nx: nx and (nx.group(2)[0].isdigit() == entries[0][1]
                                               or len(nx.group(1)) >= 2))(ITEM.match(lines[i + 1])):
                        i += 1              # línea vacía entre ítems: la lista sigue (G3)
                    else:
                        break
                self.lst(entries); continue

            para.append(line); i += 1

        flush()
        return self.story


class _Rule(Flowable):
    """Línea de color bajo los títulos de capítulo."""
    def __init__(self, color):
        super().__init__()
        self.color = color

    def wrap(self, w, h):
        self.width = w
        return w, 14

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(2)
        self.canv.line(0, 12, 60, 12)


# ---------------------------------------------------------------------------
# Documento: portada, encabezado, pie, índice y marcadores
# ---------------------------------------------------------------------------
COVER_CUT = ("portada: el título y el subtítulo no caben ni con la letra más chica; "
             "se recortaron con «…». Acortarlos en la cabecera.")



class ManualDoc(BaseDocTemplate):
    def __init__(self, filename, cfg, **kw):
        super().__init__(filename, **kw)
        self.cfg = cfg
        self.primary = colors.HexColor(cfg["color"])
        self.t = textos(cfg)
        self.warnings = []
        self.page_chapters = {}
        self._last_level = -1
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([
            PageTemplate(id="portada", frames=[frame], onPage=self.draw_cover),
            PageTemplate(id="contenido", frames=[frame]),
        ])

    def afterFlowable(self, f):
        level = getattr(f, "_toc_level", None)
        if level is None:
            return
        level = min(level, self._last_level + 1)   # el árbol no puede saltar niveles
        self._last_level = level
        self.canv.bookmarkPage(f._bm_key)
        self.canv.addOutlineEntry(f._toc_text, f._bm_key, level=level, closed=level > 0)
        self.notify("TOCEntry", (level, with_fallback(escape(f._toc_text)), self.page, f._bm_key))
        if level == 0:
            self.page_chapters[self.page] = f._toc_text

    def handle_documentBegin(self):
        # multiBuild arma el documento varias veces (el índice cambia la paginación).
        # Lo anotado en una pasada no sirve para la siguiente: sin vaciarlo, el pie
        # mezclaba las páginas de la primera pasada con las de la última (G5).
        self._last_level = -1
        self.page_chapters = {}
        super().handle_documentBegin()

    # --- portada -----------------------------------------------------------
    def draw_cover(self, c, doc):
        cfg, W, H = self.cfg, self.pagesize[0], self.pagesize[1]
        c.saveState()
        c.showOutline()  # abre el panel de marcadores al abrir el PDF
        band_h = H * 0.45
        c.setFillColor(self.primary)
        c.rect(0, H - band_h, W, band_h, fill=1, stroke=0)
        c.setFillColor(colors.Color(1, 1, 1, alpha=0.08))
        c.circle(W * 0.92, H - band_h * 0.25, band_h * 0.55, fill=1, stroke=0)

        x, w = 2.5 * cm, W - 5 * cm
        y = H - band_h + 2.2 * cm
        top = H - 2.5 * cm
        if cfg["institucion"]:
            st = ParagraphStyle("ins", fontName="Helvetica-Bold", fontSize=10,
                                leading=13, textColor=colors.HexColor("#D6E4F0"))
            p = Paragraph(with_fallback(escape(cfg["institucion"].upper())), st)
            _, ph = p.wrap(w, H)
            p.drawOn(c, x, top - ph)
            top -= ph + 0.5 * cm

        # Título y subtítulo ocupan la banda, entre su base y la institución. Si no caben,
        # se achica la letra (hasta la mitad); si ni así, se recortan con aviso (G11):
        # antes subían sin límite y lo que pasaba el borde de la página se perdía.
        def cover_blocks(scale, title, sub):
            out = [Paragraph(with_fallback(escape(title)), ParagraphStyle(
                "ct", fontName="Helvetica-Bold", fontSize=32 * scale, leading=38 * scale,
                textColor=colors.white))]
            if sub:
                size = max(15 * scale, 10)
                out.append(Paragraph(with_fallback(escape(sub)), ParagraphStyle(
                    "cs", fontName="Helvetica", fontSize=size, leading=size * 4 / 3,
                    textColor=colors.HexColor("#E8EEF4"))))
            return out

        def fits(blocks):
            return sum(p.wrap(w, H)[1] + 10 for p in blocks) - 10 <= top - y

        title, sub, scale = cfg["titulo"], cfg["subtitulo"], 1.0
        blocks = cover_blocks(scale, title, sub)
        while not fits(blocks) and scale > 0.5:
            scale = max(0.5, scale - 0.05)
            blocks = cover_blocks(scale, title, sub)
        cut = False
        while not fits(blocks) and (" " in title or " " in sub):
            if len(sub) > len(title) and " " in sub or " " not in title:   # se recorta el más largo
                sub = sub.rstrip("…").rsplit(" ", 1)[0] + "…"
            else:
                title = title.rstrip("…").rsplit(" ", 1)[0] + "…"
            cut = True
            blocks = cover_blocks(scale, title, sub)
        if cut and COVER_CUT not in self.warnings:
            self.warnings.append(COVER_CUT)
        for p in reversed(blocks):
            _, ph = p.wrap(w, H)
            p.drawOn(c, x, y)
            y += ph + 10

        # Datos bajo la banda
        info = [(self.t[k], cfg[k]) for k in ("curso", "autor", "version", "fecha") if cfg[k]]
        y = H - band_h - 2.2 * cm
        for label, value in info:
            c.setFillColor(GRIS)
            c.setFont("Helvetica", 9)
            c.drawString(x, y, label.upper())
            c.setFillColor(colors.HexColor("#262626"))
            draw_text(c, x, y - 15, fit(value, "Helvetica-Bold", 12, w), "Helvetica-Bold", 12)
            y -= 1.4 * cm

        if cfg["logo"]:
            logo = (Path(doc.filename).parent / cfg["logo"])
            src = Path(cfg["_base"]) / cfg["logo"]
            logo = src if src.exists() else logo
            if logo.exists():
                c.drawImage(str(logo), W - 2.5 * cm - 4 * cm, 2.2 * cm, 4 * cm, 2.5 * cm,
                            preserveAspectRatio=True, mask="auto", anchor="se")

        c.setFillColor(self.primary)
        c.rect(0, 0, W, 0.5 * cm, fill=1, stroke=0)
        c.restoreState()


def header_footer(c, doc, page, total):
    cfg, W, H = doc.cfg, doc.pagesize[0], doc.pagesize[1]
    lm, rm = doc.leftMargin, W - doc.rightMargin
    chapter = ""
    for p in sorted(doc.page_chapters):
        if p <= page:
            chapter = doc.page_chapters[p]
    c.saveState()
    # Encabezado
    c.setStrokeColor(doc.primary)
    c.setLineWidth(0.8)
    c.line(lm, H - 1.6 * cm, rm, H - 1.6 * cm)
    c.setFont("Helvetica", 8.5)
    c.setFillColor(GRIS)
    # Los textos largos se recortan: no se montan uno sobre otro ni pasan el margen (G11)
    full, gap = rm - lm, 14
    curso = fit(cfg["curso"], "Helvetica", 8.5, 0.4 * full)
    draw_text(c, lm, H - 1.6 * cm + 5, fit(cfg["titulo"], "Helvetica", 8.5, full - gap
                                           - text_width(curso, "Helvetica", 8.5)), "Helvetica", 8.5)
    if curso:
        draw_text(c, rm, H - 1.6 * cm + 5, curso, "Helvetica", 8.5, right=True)
    # Pie
    label = doc.t["pagina"].format(page=page, total=total)
    c.setStrokeColor(GRIS_CLARO)
    c.line(lm, 1.6 * cm, rm, 1.6 * cm)
    draw_text(c, lm, 1.6 * cm - 12, fit(chapter, "Helvetica", 8.5, full - gap
                                        - stringWidth(label, "Helvetica-Bold", 8.5)), "Helvetica", 8.5)
    c.setFillColor(doc.primary)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawRightString(rm, 1.6 * cm - 12, label)
    c.restoreState()


def make_canvas(doc):
    class NumberedCanvas(rl_canvas.Canvas):
        """Guarda las páginas para poder escribir 'Página X de Y'."""
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()
            # Las páginas se escriben recién en save(). El contador debe avanzar aquí para
            # que cada marcador y cada enlace del índice apunte a su página y no a la primera.
            self._doc.pageCounter += 1

        def save(self):
            total = len(self._pages)
            self._doc.pageCounter = 1
            for state in self._pages:
                self.__dict__.update(state)
                if self._pageNumber > 1:
                    header_footer(self, doc, self._pageNumber, total)
                super().showPage()
            super().save()
    return NumberedCanvas


# ---------------------------------------------------------------------------
def build_pdf(md_path, out_path):
    md_path = Path(md_path)
    cfg, body = parse_front_matter(md_path.read_text(encoding="utf-8-sig"))  # con o sin BOM
    cfg["_base"] = str(md_path.parent)
    check_config(cfg)
    size = LETTER if cfg["tamano"].lower() in ("carta", "letter") else A4
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)     # crea la carpeta de salida

    doc = ManualDoc(
        str(out_path), cfg, pagesize=size,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.4 * cm, bottomMargin=2.4 * cm,
        title=cfg["titulo"], author=cfg["autor"], subject=cfg["subtitulo"],
        keywords=cfg["palabras_clave"], creator="Plantilla de manual (manual.py)",
        lang=idioma(cfg), pageCompression=1,
    )
    styles = build_styles(doc.primary)
    # El marco tiene 6 pt de relleno por lado
    builder = Builder(cfg, styles, md_path.parent, doc.width - 12, doc.height - 12)
    builder.first_line = cfg.get("_body_line", 0)
    SplitTable.FULL = doc.height - 12

    content = builder.build(body)
    story = [Spacer(1, 1), NextPageTemplate("contenido"), PageBreak()]
    # Sin títulos no hay índice: ReportLab imprimiría un texto de relleno en su lugar.
    if cfg["indice"].lower() in ("si", "sí", "yes", "true", "1") and builder.bm:
        toc = TableOfContents(levelStyles=styles["toc"], dotsMinLevel=0)
        story += [Paragraph(doc.t["indice"], styles["toc_title"]), _Rule(doc.primary),
                  toc, PageBreak()]
    story += content

    doc.multiBuild(story, canvasmaker=make_canvas(doc))
    build_pdf.warnings = list(builder.warnings) + doc.warnings
    for w in build_pdf.warnings:
        print(f"Aviso {w}", file=sys.stderr)
    return out_path


def main():
    ap = argparse.ArgumentParser(
        description="Genera un manual PDF desde Markdown.",
        epilog="Código de salida: 0 generado; 1 generado con avisos (solo con --estricto); "
               "2 no se pudo generar.")
    ap.add_argument("entrada", help="archivo .md con el contenido")
    ap.add_argument("-o", "--salida", help="archivo PDF de salida")
    ap.add_argument("--estricto", action="store_true",
                    help="terminar con código 1 si hubo avisos (el PDF se genera igual)")
    args = ap.parse_args()
    src = Path(args.entrada)
    if not src.is_file():
        print(f"No existe el archivo: {src}", file=sys.stderr)
        return 2
    out = Path(args.salida) if args.salida else src.with_suffix(".pdf")
    try:
        build_pdf(src, out)
    except (ConfigError, TableError) as e:
        print(f"No se generó: {e}", file=sys.stderr)
        return 2
    except LayoutError as e:
        # Un elemento que no se puede dividir y no cabe en una página
        what = re.sub(r"\s+", " ", str(e))[:160]
        print(f"No se generó: hay un elemento más alto que una página y no se pudo dividir "
              f"({what}). Revisar con tools/validar.py.", file=sys.stderr)
        return 2
    print(f"Manual generado: {out}  ({out.stat().st_size / 1024:.0f} KB)")
    n = len(build_pdf.warnings)
    if n:
        print(f"{n} avisos: lo indicado se imprimió tal cual o no se imprimió; corregir el .md.",
              file=sys.stderr)
    return 1 if n and args.estricto else 0


if __name__ == "__main__":
    sys.exit(main())

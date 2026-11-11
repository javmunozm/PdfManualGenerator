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
}

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
def inline(text, link_color="#1F4E79"):
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])", r"<i>\1</i>", text)
    text = re.sub(r"\[([^\]]+)\]\(((?:https?://|mailto:)[^)\s]+)\)",
                  rf'<link href="\2" color="{link_color}"><u>\1</u></link>', text)
    text = re.sub(
        "\x00(\\d+)\x00",
        lambda m: ('<font face="Courier" size="9.5" backColor="#EFEFEF">'
                   f"{escape(codes[int(m.group(1))])}</font>"),
        text,
    )
    return text


# ---------------------------------------------------------------------------
# Bloque de código con fondo, que se puede dividir entre páginas
# ---------------------------------------------------------------------------
class CodeBlock(Flowable):
    """Recuadro de código en el que cada renglón del código ocupa un renglón.

    Si algún renglón no cabe, primero se reduce la letra de todo el bloque (hasta
    MIN_SIZE). Solo si aun así no cabe se parte: en un espacio, con sangría mayor que la
    del renglón y una marca gris al inicio, para que se vea que es continuación.
    """
    FONT, SIZE, MIN_SIZE, PAD, GLYPH = "Courier", 8.5, 7.0, 6, 0.6   # GLYPH: ancho / tamaño

    def __init__(self, lines, accent, rows=None, size=None):
        super().__init__()
        self.raw_lines = [ln.expandtabs(4) for ln in lines]
        self.accent = accent
        self.rows = rows          # [(texto, es_continuación)], ya calculado al dividir
        self.size = size

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
        self.leading = round(self.size * 1.3, 2)
        self.height = len(self.rows) * self.leading + 2 * self.PAD
        return self.width, self.height

    def split(self, availWidth, availHeight):
        self.wrap(availWidth, availHeight)
        fit = int((availHeight - 2 * self.PAD) / self.leading)
        while 0 < fit < len(self.rows) and self.rows[fit][1]:
            fit -= 1                              # no separar un renglón de su continuación
        if fit < 3 or fit >= len(self.rows):
            return []
        return [CodeBlock([], self.accent, self.rows[:fit], self.size),
                CodeBlock([], self.accent, self.rows[fit:], self.size)]

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#F5F5F5"))
        c.setStrokeColor(GRIS_CLARO)
        c.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=1)
        c.setFillColor(self.accent)
        c.rect(0, 0, 2.5, self.height, fill=1, stroke=0)
        x0, cw = self.PAD + 4, self.GLYPH * self.size
        y = self.height - self.PAD - self.size
        c.setStrokeColor(colors.HexColor("#8C8C8C"))
        c.setLineWidth(0.7)
        for text, cont in self.rows:               # marca de continuación (dibujo, no texto)
            if cont:
                x = x0 + (len(text) - len(text.lstrip(" ")) - 2.2) * cw
                c.lines([(x, y + self.size * 0.75, x, y + self.size * 0.25),
                         (x, y + self.size * 0.25, x + 1.3 * cw, y + self.size * 0.25)])
            y -= self.leading
        c.setFillColor(colors.HexColor("#262626"))
        tx = c.beginText(x0, self.height - self.PAD - self.size)
        tx.setFont(self.FONT, self.size, self.leading)
        for text, _ in self.rows:
            tx.textLine(text)
        c.drawText(tx)


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
                        cfg[k.strip().lower()] = v.strip().strip('"').strip("'")
                return cfg, "\n".join(lines[i + 1:])
    return cfg, text


class Builder:
    def __init__(self, cfg, styles, base_dir, frame_w, frame_h):
        self.cfg = cfg
        self.s = styles
        self.base = base_dir
        self.fw, self.fh = frame_w, frame_h
        self.primary = colors.HexColor(cfg["color"])
        self.link = cfg["color"]
        self.numerar = cfg["numerar"].lower() in ("si", "sí", "yes", "true", "1")
        self.counters = [0, 0, 0]
        self.story = []
        self.first_h1 = True
        self.bm = 0

    def p(self, text, style="body"):
        return Paragraph(inline(text, self.link), self.s[style])

    # --- títulos -----------------------------------------------------------
    def heading(self, level, text):
        lvl = level - 1
        self.counters[lvl] += 1
        for j in range(lvl + 1, 3):
            self.counters[j] = 0
        label = text
        if self.numerar:
            num = ".".join(str(n) for n in self.counters[:lvl + 1])
            label = f"{num}{'.' if lvl == 0 else ''}  {text}"
        if lvl == 0:
            if not self.first_h1:
                self.story.append(PageBreak())
            self.first_h1 = False
        else:
            self.story.append(CondPageBreak(3 * cm))
        para = Paragraph(inline(label, self.link), self.s[f"h{level}"])
        self.bm += 1
        para._toc_level = lvl
        para._toc_text = re.sub(r"[`*]", "", label.replace("  ", " "))
        para._bm_key = f"h{self.bm}"
        self.story.append(para)
        if lvl == 0:
            self.story.append(_Rule(self.primary))

    # --- bloques -----------------------------------------------------------
    def table(self, rows):
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
        if not cells:
            return
        ncols = max(len(r) for r in cells)
        cells = [r + [""] * (ncols - len(r)) for r in cells]
        data = [[Paragraph(inline(c, "#FFFFFF"), self.s["cell_head"]) for c in cells[0]]]
        data += [[Paragraph(inline(c, self.link), self.s["cell"]) for c in r] for r in cells[1:]]
        t = Table(data, colWidths=[self.fw / ncols] * ncols, repeatRows=1, hAlign="LEFT")
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

    def lst(self, items, ordered):
        flow = ListFlowable(
            [ListItem(self.p(it, "list"), leftIndent=16) for it in items],
            bulletType="1" if ordered else "bullet",
            start="1" if ordered else "•",
            bulletFormat="%s." if ordered else None,
            bulletColor=self.primary,
            bulletFontName="Helvetica-Bold",
            bulletFontSize=10 if ordered else 11,
            leftIndent=16,
        )
        self.story += [flow, Spacer(1, 6)]

    def quote(self, lines):
        m = re.match(r"\[!(\w+)\]\s*(.*)", lines[0].strip()) if lines else None
        if m and m.group(1).upper() in CALLOUTS:
            name, border, bg = CALLOUTS[m.group(1).upper()]
            title = m.group(2) or name
            body_lines = lines[1:]
        else:
            name, border, bg, title, body_lines = None, "#A6A6A6", None, None, lines

        content = []
        if title:
            ts = ParagraphStyle("ct", parent=self.s["callout_title"],
                                textColor=colors.HexColor(border))
            content.append(Paragraph(inline(title, self.link), ts))
        for para in "\n".join(body_lines).split("\n\n"):
            para = " ".join(x.strip() for x in para.splitlines()).strip()
            if para:
                content.append(self.p(para, "callout" if name else "quote"))

        t = Table([[content]], colWidths=[self.fw])
        style = [
            ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(border)),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        if bg:
            style.append(("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)))
        t.setStyle(TableStyle(style))
        self.story += [t, Spacer(1, 10)]

    def image(self, caption, src):
        path = (self.base / src).resolve()
        if not path.exists():
            self.story.append(self.p(f"**[Imagen no encontrada: {src}]**"))
            return
        img = load_image(path, self.fw, self.fh * 0.6, int(self.cfg["dpi_imagenes"]))
        parts = [img]
        if caption:
            parts.append(self.p(caption, "caption"))
        self.story.append(KeepTogether(parts))

    # --- recorrido línea por línea -----------------------------------------
    def build(self, text):
        lines = text.splitlines()
        i, para = 0, []

        def flush():
            if para:
                self.story.append(self.p(" ".join(x.strip() for x in para)))
                para.clear()

        while i < len(lines):
            line = lines[i]
            st = line.strip()

            if not st:
                flush(); i += 1; continue

            if st.startswith("```"):
                flush()
                code = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code.append(lines[i]); i += 1
                self.story += [CodeBlock(code or [""], self.primary), Spacer(1, 10)]
                i += 1; continue

            if st in ("\\newpage", "\\salto", "<!-- salto -->"):
                flush(); self.story.append(PageBreak()); i += 1; continue

            if st.startswith("<!--"):  # comentarios: no se imprimen
                flush()
                while i < len(lines) and "-->" not in lines[i]:
                    i += 1
                i += 1; continue

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

            bullet = re.match(r"\s*[-*+]\s+(.*)", line)
            number = re.match(r"\s*\d+[.)]\s+(.*)", line)
            if bullet or number:
                flush()
                ordered = bool(number)
                pat = r"\s*\d+[.)]\s+(.*)" if ordered else r"\s*[-*+]\s+(.*)"
                items = []
                while i < len(lines):
                    mm = re.match(pat, lines[i])
                    if mm:
                        items.append(mm.group(1)); i += 1
                    elif lines[i].strip() and lines[i].startswith("  ") and items:
                        items[-1] += " " + lines[i].strip(); i += 1
                    else:
                        break
                self.lst(items, ordered); continue

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
class ManualDoc(BaseDocTemplate):
    def __init__(self, filename, cfg, **kw):
        super().__init__(filename, **kw)
        self.cfg = cfg
        self.primary = colors.HexColor(cfg["color"])
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
        self.notify("TOCEntry", (level, f._toc_text, self.page, f._bm_key))
        if level == 0:
            self.page_chapters[self.page] = f._toc_text

    def handle_documentBegin(self):
        self._last_level = -1
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
        if cfg["institucion"]:
            st = ParagraphStyle("ins", fontName="Helvetica-Bold", fontSize=10,
                                leading=13, textColor=colors.HexColor("#D6E4F0"))
            p = Paragraph(escape(cfg["institucion"].upper()), st)
            _, ph = p.wrap(w, H)
            p.drawOn(c, x, H - 2.5 * cm - ph)

        blocks = []
        blocks.append(Paragraph(escape(cfg["titulo"]), ParagraphStyle(
            "ct", fontName="Helvetica-Bold", fontSize=32, leading=38,
            textColor=colors.white)))
        if cfg["subtitulo"]:
            blocks.append(Paragraph(escape(cfg["subtitulo"]), ParagraphStyle(
                "cs", fontName="Helvetica", fontSize=15, leading=20,
                textColor=colors.HexColor("#E8EEF4"))))
        for p in reversed(blocks):
            _, ph = p.wrap(w, H)
            p.drawOn(c, x, y)
            y += ph + 10

        # Datos bajo la banda
        info = [(k, cfg[v]) for k, v in (("Curso", "curso"), ("Autor", "autor"),
                ("Versión", "version"), ("Fecha", "fecha")) if cfg[v]]
        y = H - band_h - 2.2 * cm
        for label, value in info:
            c.setFillColor(GRIS)
            c.setFont("Helvetica", 9)
            c.drawString(x, y, label.upper())
            c.setFillColor(colors.HexColor("#262626"))
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x, y - 15, value)
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
    c.drawString(lm, H - 1.6 * cm + 5, cfg["titulo"])
    if cfg["curso"]:
        c.drawRightString(rm, H - 1.6 * cm + 5, cfg["curso"])
    # Pie
    c.setStrokeColor(GRIS_CLARO)
    c.line(lm, 1.6 * cm, rm, 1.6 * cm)
    c.drawString(lm, 1.6 * cm - 12, chapter)
    c.setFillColor(doc.primary)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawRightString(rm, 1.6 * cm - 12, f"Página {page} de {total}")
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
    cfg, body = parse_front_matter(md_path.read_text(encoding="utf-8"))
    cfg["_base"] = str(md_path.parent)
    size = LETTER if cfg["tamano"].lower() in ("carta", "letter") else A4

    doc = ManualDoc(
        str(out_path), cfg, pagesize=size,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.4 * cm, bottomMargin=2.4 * cm,
        title=cfg["titulo"], author=cfg["autor"], subject=cfg["subtitulo"],
        keywords=cfg["palabras_clave"], creator="Plantilla de manual (manual.py)",
        lang="es", pageCompression=1,
    )
    styles = build_styles(doc.primary)
    # El marco tiene 6 pt de relleno por lado
    builder = Builder(cfg, styles, md_path.parent, doc.width - 12, doc.height - 12)

    story = [Spacer(1, 1), NextPageTemplate("contenido"), PageBreak()]
    if cfg["indice"].lower() in ("si", "sí", "yes", "true", "1"):
        toc = TableOfContents(levelStyles=styles["toc"], dotsMinLevel=0)
        story += [Paragraph("Índice", styles["toc_title"]), _Rule(doc.primary),
                  toc, PageBreak()]
    story += builder.build(body)

    doc.multiBuild(story, canvasmaker=make_canvas(doc))
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Genera un manual PDF desde Markdown.")
    ap.add_argument("entrada", help="archivo .md con el contenido")
    ap.add_argument("-o", "--salida", help="archivo PDF de salida")
    args = ap.parse_args()
    src = Path(args.entrada)
    if not src.exists():
        sys.exit(f"No existe el archivo: {src}")
    out = Path(args.salida) if args.salida else src.with_suffix(".pdf")
    build_pdf(src, out)
    print(f"Manual generado: {out}  ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()

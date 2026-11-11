"""Pruebas del flujo: manual.py, tools/extraer.py y tools/comparar.py.

Cada prueba corresponde a un error de docs/auditoria.md (su código va en el nombre o en
el comentario). Todos los archivos se crean aquí, en una carpeta temporal: no se usa
sources/.

    python -m unittest discover tests
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

RAIZ = Path(__file__).resolve().parent.parent
W, H = A4
CABECERA = "---\ntitulo: Prueba\nnumerar: no\n---\n\n"


def run(script, *args, utf8=True):
    """Ejecuta un script del proyecto. Devuelve (código de salida, salida completa)."""
    env = dict(os.environ)
    env.pop("PYTHONUTF8", None)
    if utf8:
        env["PYTHONIOENCODING"] = "utf-8"
    else:
        env.pop("PYTHONIOENCODING", None)      # consola de Windows: cp1252
    r = subprocess.run([sys.executable, "-B", str(RAIZ / script), *map(str, args)],
                       capture_output=True, env=env)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", "replace")


class Caso(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def md(self, nombre, cuerpo, cabecera=CABECERA):
        ruta = self.tmp / f"{nombre}.md"
        ruta.write_text(cabecera + cuerpo, encoding="utf-8")
        return ruta

    def generar(self, nombre, cuerpo, cabecera=CABECERA):
        md = self.md(nombre, cuerpo, cabecera)
        pdf = self.tmp / f"{nombre}.pdf"
        rc, out = run("manual.py", md, "-o", pdf)
        self.assertEqual(rc, 0, out)
        return md, pdf

    def extraer(self, archivo, *extra):
        rc, out = run("tools/extraer.py", archivo, "--salida", self.tmp / "ext", *extra)
        carpeta = self.tmp / "ext" / Path(archivo).stem
        return rc, out, carpeta

    def leer(self, carpeta, archivo=None):
        return (carpeta / (archivo or f"{carpeta.name}.md")).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
class Comparar(Caso):
    def test_ejemplo_completo_en_modo_estricto(self):
        pdf = self.tmp / "ejemplo.pdf"
        self.assertEqual(run("manual.py", RAIZ / "ejemplo.md", "-o", pdf)[0], 0)
        rc, out = run("tools/comparar.py", RAIZ / "ejemplo.md", pdf, "--estricto")
        self.assertEqual(rc, 0, out)
        self.assertIn("RESULTADO: CORRECTO", out)

    def test_C1_contenido_borrado_aunque_sus_palabras_esten_en_otra_parte(self):
        resumen = "# Resumen\n\nUsar guantes y lentes. Encender, calibrar y medir el equipo.\n"
        completo = self.md("completo", "# Seguridad\n\nUsar guantes y lentes.\n\n# Pasos\n\n"
                                       "Encender el equipo. Calibrar el equipo. Medir.\n\n" + resumen)
        _, pdf = self.generar("recortado", resumen)
        rc, out = run("tools/comparar.py", completo, pdf)
        self.assertEqual(rc, 1, out)
        self.assertIn("faltan palabras", out)

    def test_C1_cifras_intercambiadas(self):
        origen = self.md("origen", "# Dosis\n\nAdministrar 250 mg cada 8 horas.\n")
        _, pdf = self.generar("alterado", "# Dosis\n\nAdministrar 8 mg cada 250 horas.\n")
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 1, out)
        self.assertIn("cifras fuera de lugar", out)

    def test_C1_cifra_con_separador_es_una_unidad(self):
        origen = self.md("origen", "# Total\n\nSon 1.250 unidades.\n")
        _, pdf = self.generar("alterado", "# Total\n\nSon 250.1 unidades.\n")
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 1, out)
        self.assertIn("1.250", out)

    def test_C1_texto_agregado_es_aviso_y_falla_en_estricto(self):
        origen = self.md("origen", "# Uno\n\nTexto original.\n")
        _, pdf = self.generar("mas", "# Uno\n\nTexto original. Frase inventada.\n")
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 0, out)
        self.assertIn("sobran", out)
        self.assertEqual(run("tools/comparar.py", origen, pdf, "--estricto")[0], 1)

    def test_C2_sintaxis_de_la_plantilla_no_da_faltantes(self):
        md, pdf = self.generar("sintaxis", "# Uno\n\nTexto.\n\n\\salto\n\n"
                               "> [!IMPORTANTE] Antes de entregar\n> Revisar todo.\n\n"
                               "```python\nprint(1)\n```\n\n| A | B |\n|:--|--:|\n| x | y |\n",
                               cabecera="---\ntitulo: Prueba\n---\n\n")   # numerar: si
        rc, out = run("tools/comparar.py", md, pdf, "--estricto")
        self.assertEqual(rc, 0, out)

    def test_C2_palabra_cortada_con_guion_en_el_pdf_de_origen(self):
        origen = self.tmp / "origen.pdf"
        c = canvas.Canvas(str(origen), pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 100, "Este parrafo tiene una palabra cortada al final del renglon: docu-")
        c.drawString(70, H - 116, "mentacion del sistema.")
        c.save()
        _, pdf = self.generar("nuevo", "Este parrafo tiene una palabra cortada al final del "
                                       "renglon: documentacion del sistema.\n")
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 0, out)

    def test_C3_ignorar_acepta_una_falta_declarada(self):
        origen = self.md("origen", "# Uno\n\nTexto.\n\nEncabezado antiguo de la facultad.\n")
        _, pdf = self.generar("nuevo", "# Uno\n\nTexto.\n")
        self.assertEqual(run("tools/comparar.py", origen, pdf)[0], 1)
        rc, out = run("tools/comparar.py", origen, pdf, "--ignorar", "Encabezado antiguo de la facultad")
        self.assertEqual(rc, 0, out)

    def test_C3_portada_incompleta(self):
        origen = self.md("origen", "# Uno\n\nTexto.\n",
                         cabecera="---\ntitulo: Prueba\nautor: Ada Lovelace\nnumerar: no\n---\n\n")
        _, pdf = self.generar("nuevo", "# Uno\n\nTexto.\n")
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 1, out)
        self.assertIn("Portada: faltan", out)

    def test_C4_consola_de_windows_no_falla_con_otros_alfabetos(self):
        origen = self.md("origen", "# T\n\nLa proteina \u03b1\u03b2\u03b3 y el simbolo \u03c9mega.\n")
        _, pdf = self.generar("vacio", "# T\n\nNada.\n")
        rc, out = run("tools/comparar.py", origen, pdf, utf8=False)
        self.assertEqual(rc, 1, out)
        self.assertNotIn("Traceback", out)

    def test_C5_origen_no_admitido_da_mensaje_y_codigo_2(self):
        otro = self.tmp / "x.docx"
        otro.write_bytes(b"PK")
        _, pdf = self.generar("nuevo", "# Uno\n\nTexto.\n")
        rc, out = run("tools/comparar.py", otro, pdf)
        self.assertEqual(rc, 2, out)
        self.assertNotIn("Traceback", out)


# ---------------------------------------------------------------------------
class Generador(Caso):
    def test_G14_marcadores_y_enlaces_del_indice_apuntan_a_su_pagina(self):
        _, pdf = self.generar("tres", "# Uno\n\nA.\n\n# Dos\n\nB.\n\n# Tres\n\nC.\n")
        with pymupdf.open(pdf) as doc:
            self.assertEqual([p for _, _, p in doc.get_toc()], [3, 4, 5])
            self.assertEqual(sorted({ln["page"] for ln in doc[1].get_links()}), [2, 3, 4])

    def test_G15_un_renglon_de_codigo_largo_no_se_parte_si_cabe_con_letra_menor(self):
        largo = '    """' + "palabra " * 10 + 'fin."""'                 # 94 caracteres
        self.assertTrue(83 < len(largo) <= 100)                          # no cabe a 8,5 pt; sí a 7
        _, pdf = self.generar("codigo", "# C\n\n```\ndef f():\n" + largo + "\n    return 1\n```\n")
        with pymupdf.open(pdf) as doc:
            renglones = [ln.strip() for ln in doc[2].get_text().splitlines()]
        self.assertIn(largo.strip(), renglones)

    def test_G15_un_renglon_que_no_cabe_se_parte_en_un_espacio_sin_perder_texto(self):
        largo = "x = " + " + ".join(f"valor_{i:02d}" for i in range(20))  # 220 caracteres
        md, pdf = self.generar("codigo", "# C\n\n```\n" + largo + "\n```\n")
        with pymupdf.open(pdf) as doc:
            texto = doc[2].get_text()
        self.assertNotRegex(texto, r"valor_\d?\n\s*\d")                 # ningún nombre cortado
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)


    def test_G1_negrita_y_cursiva_juntas(self):
        _, pdf = self.generar("bi", "# T\n\nEsto es ***muy importante*** aqui.\n")
        with pymupdf.open(pdf) as doc:
            self.assertIn("Esto es muy importante aqui.", doc[2].get_text())

    def test_G1_marcas_cruzadas_se_imprimen_tal_cual(self):
        _, pdf = self.generar("cruzado", "# T\n\nEsto **a *b** c* fin.\n")
        with pymupdf.open(pdf) as doc:
            self.assertIn("Esto **a *b** c* fin.", doc[2].get_text())

    def test_G6_barra_y_salto_dentro_de_una_celda(self):
        md, pdf = self.generar("tabla", "# T\n\n| Expr | Nota |\n|---|---|\n"
                               "| a \\| b | linea1<br>linea2 |\n| `x|y` | ok |\n")
        with pymupdf.open(pdf) as doc:
            renglones = [ln.strip() for ln in doc[2].get_text().splitlines()]
        for esperado in ("a | b", "linea1", "linea2", "x|y", "ok"):
            self.assertIn(esperado, renglones)
        self.assertNotIn("<br>", " ".join(renglones))
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)

    def test_G7_archivo_con_bom_conserva_la_cabecera(self):
        md = self.tmp / "bom.md"
        md.write_bytes(("\ufeff---\ntitulo: Con BOM\nautor: Ada\n---\n\n# Uno\n\nTexto.\n").encode("utf-8"))
        pdf = self.tmp / "bom.pdf"
        self.assertEqual(run("manual.py", md, "-o", pdf)[0], 0)
        with pymupdf.open(pdf) as doc:
            self.assertIn("Con BOM", doc[0].get_text())

    def test_G9_titulo_con_signos_de_etiqueta_no_rompe_el_indice(self):
        _, pdf = self.generar("angulos", "# Etiqueta <b> y a < b\n\nTexto.\n")
        with pymupdf.open(pdf) as doc:
            self.assertEqual(doc.get_toc()[0][1], "Etiqueta <b> y a < b")


# ---------------------------------------------------------------------------
class Validar(Caso):
    def test_documento_limpio(self):
        rc, out = run("tools/validar.py", RAIZ / "ejemplo.md", "--estricto")
        self.assertEqual(rc, 0, out)
        self.assertIn("0 errores, 0 avisos", out)

    def test_errores(self):
        md = self.md("malo", "# Uno\n\nAgua H\u2082O.\n\n![FIGURA: describir](assets/no.png)\n\n"
                             "<!-- nota --> texto perdido\n\n```\nsin cerrar\n",
                     cabecera="---\ntitulo: P\ncolor: azul\n---\n\n")
        rc, out = run("tools/validar.py", md, "--max", "30")
        self.assertEqual(rc, 1, out)
        for esperado in ("color «azul»", "sin glifo", "figura sin describir", "imagen no encontrada",
                         "después de -->", "sin cerrar"):
            self.assertIn(esperado, out)

    def test_avisos_no_fallan_salvo_en_estricto(self):
        md = self.md("avisos", "## Sin capitulo\n\n#### Nivel 4\n\nTexto _asi_ y **a *b** c*.\n\n"
                               "1. Uno\n\n2. Dos\n\n- a\n  - b\n\n---\n",
                     cabecera="---\ntitulo: P\n---\n\n")
        rc, out = run("tools/validar.py", md, "--max", "30")
        self.assertEqual(rc, 0, out)
        for esperado in ("0.1", "nivel 4", "guion bajo", "mal cerrada", "empieza en 2",
                         "lista anidada", "línea horizontal"):
            self.assertIn(esperado, out)
        self.assertEqual(run("tools/validar.py", md, "--estricto")[0], 1)


EXTRAIDO = """---
titulo: Manual de prueba
fuente: manual.pdf
curso: QUI-101
---

<!-- p.1 PORTADA ORIGINAL: FACULTAD DE CIENCIAS | Manual de prueba | Guia de laboratorio | CURSO | QUI-101 -->

<!-- p.2 -->

# 1. Uso

Este parrafo empieza en una pagina y

<!-- p.3 -->

termina en la siguiente.

```
linea uno
```

<!-- p.4 -->

```
linea dos
```

1. Primer paso.

<!-- p.5 -->

2. Segundo paso.

**Nota**

Texto de la nota.

**Warning**

Do not open the lid.

**Antes de empezar**

Leer todo.

Consulta la norma vigente, por favor. Ver [el sitio.](https://ejemplo.org/sitio)

Enlaces: [la norma vigente,](https://ejemplo.org/norma)
"""


class Preparar(Caso):
    def preparar(self, texto, *extra, nombre="manual"):
        carpeta = self.tmp / "ext" / nombre
        (carpeta / "assets").mkdir(parents=True, exist_ok=True)
        (carpeta / "assets" / "fig.png").write_bytes(b"png")
        (carpeta / f"{nombre}.md").write_text(texto, encoding="utf-8")
        rc, out = run("tools/preparar.py", carpeta, "--salida", self.tmp / "doc", *extra)
        return rc, out, self.tmp / "doc" / nombre / f"{nombre}.md"

    def test_ajustes_automaticos(self):
        rc, out, md = self.preparar(EXTRAIDO)
        self.assertEqual(rc, 1, out)                                    # queda un rótulo por decidir
        t = md.read_text(encoding="utf-8")
        self.assertIn("empieza en una pagina y termina en la siguiente.", t)
        self.assertIn("```\nlinea uno\nlinea dos\n```", t)
        self.assertIn("1. Primer paso.\n2. Segundo paso.", t)
        self.assertIn("> [!NOTA]\n> Texto de la nota.", t)
        self.assertIn("> [!ADVERTENCIA] Warning\n> Do not open the lid.", t)
        self.assertIn("**Antes de empezar**", t)                        # no se adivina el tipo
        self.assertIn("Antes de empezar", out)
        self.assertIn("institucion: FACULTAD DE CIENCIAS", t)
        self.assertIn("subtitulo: Guia de laboratorio", t)
        self.assertIn("Consulta [la norma vigente](https://ejemplo.org/norma), por favor.", t)
        self.assertIn("[el sitio](https://ejemplo.org/sitio).", t)
        self.assertNotIn("Enlaces:", t)
        self.assertTrue((md.parent / "assets" / "fig.png").is_file())

    def test_no_pisa_un_documento_ya_preparado(self):
        rc, out, md = self.preparar("---\ntitulo: P\n---\n\n# Uno\n\nTexto.\n")
        self.assertEqual(rc, 0, out)
        md.write_text(md.read_text(encoding="utf-8") + "\nTrabajo manual.\n", encoding="utf-8")
        rc, out, _ = self.preparar("---\ntitulo: P\n---\n\n# Uno\n\nTexto.\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("Trabajo manual.", md.read_text(encoding="utf-8"))
        rc, out, _ = self.preparar("---\ntitulo: P\n---\n\n# Uno\n\nTexto.\n", "--forzar")
        self.assertEqual(rc, 0, out)
        self.assertIn("Trabajo manual.", md.with_name("manual.anterior.md").read_text(encoding="utf-8"))

    def test_presentacion_sin_capitulos_recibe_uno(self):
        rc, out, md = self.preparar("---\ntitulo: Clase 1\n---\n\n## Diapositiva 1: Hola\n\n- a\n\n"
                                    "## Diapositiva 2\n\n- b\n", nombre="clase")
        self.assertEqual(rc, 0, out)
        self.assertIn("# Clase 1\n\n## Diapositiva 1: Hola", md.read_text(encoding="utf-8"))
        pdf = self.tmp / "clase.pdf"
        self.assertEqual(run("manual.py", md, "-o", pdf)[0], 0)
        with pymupdf.open(pdf) as doc:
            self.assertEqual(doc.get_toc()[1][1], "1.1 Diapositiva 1: Hola")

    def test_pendientes_de_la_extraccion_se_avisan(self):
        rc, out, _ = self.preparar("---\ntitulo: P\n---\n\n# Uno\n\n![FIGURA: describir](assets/fig.png)\n")
        self.assertEqual(rc, 1, out)
        self.assertIn("figuras sin describir", out)


# ---------------------------------------------------------------------------
def pdf_con_pie_y_nota(ruta):
    c = canvas.Canvas(str(ruta), pagesize=A4)
    for n in range(1, 5):
        c.setFont("Helvetica", 9)
        c.drawString(70, H - 35, "Manual de Seguridad")
        c.drawRightString(W - 70, 30, f"Pagina {n}")
        c.setFont("Helvetica-Bold", 20)
        c.drawString(70, H - 110, f"{n}. Capitulo numero {n}")
        c.setFont("Helvetica", 11)
        for i in range(6):
            c.drawString(70, H - 150 - i * 16, f"Texto normal de la pagina {n}, renglon {i} con relleno.")
        if n == 2:
            c.setFont("Helvetica", 8)
            c.drawString(70, 44, "1 Nota al pie: la dosis maxima es 250 mg cada 8 horas segun la norma 4471.")
        c.showPage()
    c.save()


CODIGO = '''RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un asistente que responde SOLO con la informacion que viene entre "
            "<documentos> y </documentos> en el mensaje del usuario.",
        ),
    ]
)'''


def pdf_con_codigo_partido(ruta):
    """Como un manual real: recuadro de código con letra grande, renglones partidos por
    ancho que siguen en el borde izquierdo, sangría por posición y un pie de dos líneas
    lejos del borde de la página."""
    c = canvas.Canvas(str(ruta), pagesize=A4)
    size, x0, x1, pad = 11, 70, 525, 8
    cw = 0.6 * size
    ancho = int((x1 - x0 - 2 * pad) / cw)
    for n in range(1, 5):
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 90, f"Explicacion de la pagina {n} con un texto normal de relleno suficiente.")
        if n == 2:
            filas = []
            for linea in CODIGO.splitlines():
                sangria = len(linea) - len(linea.lstrip())
                resto, primera = linea.strip(), True
                while resto:
                    tope = ancho - (sangria if primera else 0)
                    corte = len(resto) if len(resto) <= tope else resto.rfind(" ", 0, tope + 1)
                    filas.append((sangria if primera else 0, resto[:corte]))
                    resto, primera = resto[corte:].strip(), False
            alto = len(filas) * 14 + 2 * pad
            c.setFillGray(0.95)
            c.rect(x0, H - 120 - alto, x1 - x0, alto, fill=1, stroke=0)
            c.setFillGray(0)
            c.setFont("Courier", size)
            for i, (sangria, texto) in enumerate(filas):
                c.drawString(x0 + pad + sangria * cw, H - 120 - pad - size - i * 14, texto)
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, 84, f"Page {n} of 4")
        c.drawCentredString(W / 2, 72, "Manual paso a paso - Curso de prueba (v2)")
        c.showPage()
    c.save()


def sin_comentarios(md):
    return re.sub(r"<!--.*?-->", "", md, flags=re.S)


class Extractor(Caso):
    def test_E1_nota_al_pie_unica_queda_en_el_cuerpo_con_sus_cifras(self):
        pdf = self.tmp / "notapie.pdf"
        pdf_con_pie_y_nota(pdf)
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 0, out)
        cuerpo = sin_comentarios(self.leer(carpeta))
        self.assertIn("250 mg cada 8 horas segun la norma 4471", cuerpo)
        self.assertNotIn("Manual de Seguridad", cuerpo)                # el encabezado repetido sí se omite
        self.assertIn("conservado en el cuerpo", self.leer(carpeta, "reporte.md"))

    def test_E2_no_vuelve_a_extraer_ni_pisa_trabajo_manual(self):
        origen = self.tmp / "apuntes.txt"
        origen.write_text("Primera version.\n", encoding="utf-8")
        rc, out, carpeta = self.extraer(origen)
        self.assertEqual(rc, 0, out)
        md = carpeta / "apuntes.md"
        self.assertIn("Sin cambios", self.extraer(origen)[1])
        md.write_text(md.read_text(encoding="utf-8") + "\n<!-- DESCRIPCION hecha a mano -->\n", encoding="utf-8")
        origen.write_text("Segunda version.\n", encoding="utf-8")
        rc, out, _ = self.extraer(origen)
        self.assertEqual(rc, 2, out)                                   # se niega
        self.assertIn("hecha a mano", md.read_text(encoding="utf-8"))
        rc, out, _ = self.extraer(origen, "--forzar")
        self.assertEqual(rc, 0, out)
        self.assertIn("Segunda version", md.read_text(encoding="utf-8"))
        self.assertIn("hecha a mano", (carpeta / "apuntes.anterior.md").read_text(encoding="utf-8"))

    def test_E2_mismo_nombre_y_otro_formato_van_a_carpetas_distintas(self):
        a, b = self.tmp / "datos.txt", self.tmp / "datos.json"
        a.write_text("Contenido del texto.\n", encoding="utf-8")
        b.write_text('{"clave": "valor"}', encoding="utf-8")
        self.assertEqual(self.extraer(a)[0], 0)
        self.assertEqual(self.extraer(b)[0], 0)
        self.assertIn("Contenido del texto", (self.tmp / "ext/datos/datos.md").read_text(encoding="utf-8"))
        self.assertIn("valor", (self.tmp / "ext/datos-json/datos-json.md").read_text(encoding="utf-8"))

    def test_E3_word_avisa_lo_que_el_recorrido_no_extrae(self):
        import docx
        d = docx.Document()
        d.add_heading("Guia", 1)
        d.add_paragraph("Texto del cuerpo.")
        d.sections[0].footer.paragraphs[0].text = "Documento confidencial ZETA"
        origen = self.tmp / "guia.docx"
        d.save(origen)
        rc, out, carpeta = self.extraer(origen)
        self.assertEqual(rc, 0, out)
        reporte = self.leer(carpeta, "reporte.md")
        self.assertRegex(reporte, r"Faltan en pies de página:\*\* .*zeta")

    def test_E3_powerpoint_avisa_imagenes_y_renglones_pegados(self):
        from PIL import Image
        from pptx import Presentation
        img = self.tmp / "foto.png"
        Image.new("RGB", (200, 120), (200, 30, 30)).save(img)
        prs = Presentation()
        s = prs.slides.add_slide(prs.slide_layouts[1])
        s.shapes.title.text = "Seguridad"
        p = s.placeholders[1].text_frame.paragraphs[0]
        p.add_run().text = "Usar guantes"
        p.add_line_break()
        p.add_run().text = "Usar lentes"
        s2 = prs.slides.add_slide(prs.slide_layouts[8])
        s2.shapes.title.text = "Foto"
        next(ph for ph in s2.placeholders if "PICTURE" in str(ph.placeholder_format.type)).insert_picture(str(img))
        origen = self.tmp / "clase.pptx"
        prs.save(origen)
        rc, out, carpeta = self.extraer(origen)
        self.assertEqual(rc, 0, out)
        reporte = self.leer(carpeta, "reporte.md")
        self.assertIn("Imágenes en el original: 1 | extraídas: 0", reporte)
        self.assertIn("Faltan en las diapositivas", reporte)

    def test_E3_excel_completo_no_da_avisos(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Alumno", "Nota"])
        ws.append(["Ana", 6.5])
        ws.append(["Luis", 5.8])
        origen = self.tmp / "notas.xlsx"
        wb.save(origen)
        rc, out, carpeta = self.extraer(origen)
        self.assertEqual(rc, 0, out)
        reporte = self.leer(carpeta, "reporte.md")
        self.assertIn("Cobertura de palabras: 100.0%", reporte)
        self.assertNotIn("revisar", reporte)

    def test_E9_codigo_conserva_sangria_dada_por_posicion(self):
        pdf = self.tmp / "codigo.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Courier", 10)
        for i, (x, t) in enumerate([(70, "def f(x):"), (94, "if x:"), (118, "return 1"), (94, "return 0")]):
            c.drawString(x, H - 100 - i * 13, t)
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 0, out)
        self.assertIn("```\ndef f(x):\n    if x:\n        return 1\n    return 0\n```", self.leer(carpeta))

    def test_E16_codigo_partido_por_ancho_se_reune_y_el_pie_no_entra(self):
        pdf = self.tmp / "manual.pdf"
        pdf_con_codigo_partido(pdf)
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 0, out)
        md = self.leer(carpeta)
        self.assertIn("```\n" + CODIGO + "\n```", md)
        cuerpo = sin_comentarios(md)
        self.assertNotIn("Page 2 of 4", cuerpo)
        self.assertNotIn("Manual paso a paso", cuerpo)

    def test_ejemplo_ida_y_vuelta(self):
        pdf = self.tmp / "ejemplo.pdf"
        self.assertEqual(run("manual.py", RAIZ / "ejemplo.md", "-o", pdf)[0], 0)
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 0, out)
        reporte = self.leer(carpeta, "reporte.md")
        self.assertIn("Títulos detectados: 21 | Marcadores del PDF: 21", reporte)
        md = self.leer(carpeta)
        self.assertIn('    """Calcula el promedio de una lista de notas."""', md)
        rc, out = run("tools/preparar.py", carpeta, "--salida", self.tmp / "doc")
        self.assertEqual(rc, 1, out)                                    # queda un rótulo por decidir
        self.assertIn("Antes de entregar", out)
        listo = self.tmp / "doc" / "ejemplo" / "ejemplo.md"
        texto = listo.read_text(encoding="utf-8")
        self.assertIn("institucion: MATERIAL DE CLASE", texto)
        self.assertEqual(len(re.findall(r"^> \[!", texto, re.M)), 5)    # 5 de los 6 cuadros
        self.assertIn("version: 2.0\nfecha: 10/11/2026", texto)        # bloque partido por página
        self.assertEqual(run("tools/validar.py", listo)[0], 0)
        regenerado = self.tmp / "regenerado.pdf"
        self.assertEqual(run("manual.py", listo, "-o", regenerado)[0], 0)
        rc, out = run("tools/comparar.py", pdf, regenerado)
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()

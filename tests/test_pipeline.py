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

    def test_C6_encabezado_de_tabla_repetido_en_otra_pagina_no_es_texto_sobrante(self):
        filas = "".join(f"| Concepto {i} | Detalle de la fila {i} |\n" for i in range(1, 121))
        md, pdf = self.generar("larga", "# T\n\n| Nombre | Explicación |\n|---|---|\n" + filas)
        with pymupdf.open(pdf) as doc:
            self.assertGreater(doc.page_count, 4)                # la tabla ocupa varias páginas
            self.assertGreater(sum("Explicación" in p.get_text() for p in doc), 1)
        rc, out = run("tools/comparar.py", md, pdf, "--estricto")
        self.assertEqual(rc, 0, out)

    def test_C6_un_encabezado_repetido_no_tapa_una_fila_duplicada(self):
        filas = "".join(f"| Concepto {i} | Detalle de la fila {i} |\n" for i in range(1, 121))
        origen = self.md("origen", "# T\n\n| Nombre | Explicación |\n|---|---|\n" + filas)
        _, pdf = self.generar("doble", "# T\n\n| Nombre | Explicación |\n|---|---|\n" + filas
                              + "| Concepto 7 | Detalle de la fila 7 |\n")
        rc, out = run("tools/comparar.py", origen, pdf, "--estricto")
        self.assertEqual(rc, 1, out)
        self.assertIn("sobra texto", out)

    def test_C7_simbolos_dibujados_con_fuente_de_simbolos_no_son_palabras(self):
        md, pdf = self.generar("flechas", "# T\n\n```\nCliente\n   ▼\nServidor\n   ▲\nBase\n```\n")
        rc, out = run("tools/comparar.py", md, pdf, "--estricto")
        self.assertEqual(rc, 0, out)

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

    def test_C9_encabezado_del_original_en_dos_textos_a_la_misma_altura_no_es_falta(self):
        # Encabezado con un texto a la izquierda y otro a la derecha, en el mismo renglón:
        # comparar.py los unía antes de ver si se repetían y, unidos, no los reconocía.
        origen = self.tmp / "origen.pdf"
        c = canvas.Canvas(str(origen), pagesize=A4)
        cuerpo = []
        for n in range(1, 5):
            c.setFont("Helvetica", 9)
            c.drawString(70, H - 35, "Guia 4 · Redes y servicios")
            c.drawRightString(W - 70, H - 35, "Proyecto Faro")
            c.drawCentredString(W / 2, 30, str(n))
            c.setFont("Helvetica", 11)
            for i in range(6):
                renglon = f"Texto normal de la hoja {n}, renglon {i} con relleno."
                cuerpo.append(renglon)
                c.drawString(70, H - 150 - i * 16, renglon)
            c.showPage()
        c.save()
        with pymupdf.open(origen) as doc:                              # el caso que se quiere probar
            arriba = [ln["bbox"][1] for b in doc[1].get_text("dict")["blocks"][:1] for ln in b["lines"]]
        self.assertEqual(len(arriba), 2, "los dos textos del encabezado deben quedar en un bloque")
        _, pdf = self.generar("nuevo", "\n\n".join(cuerpo) + "\n")
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 0, out)

    FILAS = [("codigo", "texto", "Identificador unico del registro"),
             ("nombre", "texto", "Nombre visible de la persona"),
             ("activo", "logico", "Indica si la cuenta sigue vigente"),
             ("origen", "texto", "Sistema desde donde llego el dato")]

    def pdf_con_tabla_en_dos_paginas(self, ruta, duplicada=False):
        """Original (no de manual.py) con una tabla que sigue en la página 2 y repite ahí
        su encabezado."""
        c = canvas.Canvas(str(ruta), pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 100, "La tabla siguiente describe cada campo del registro.")
        y = H - 130
        for fila in [("Campo", "Tipo", "Descripcion")] + self.FILAS[:2] + (self.FILAS[1:2] if duplicada else []):
            for x, celda in zip((70, 170, 270), fila):
                c.drawString(x, y, celda)
            y -= 18
        c.showPage()
        c.setFont("Helvetica", 11)
        y = H - 100
        for fila in [("Campo", "Tipo", "Descripcion")] + self.FILAS[2:]:
            for x, celda in zip((70, 170, 270), fila):
                c.drawString(x, y, celda)
            y -= 18
        c.drawString(70, y - 20, "Fin de la descripcion de los campos.")
        c.save()

    def test_C10_encabezado_de_tabla_repetido_en_el_original_no_es_falta(self):
        tabla = "| Campo | Tipo | Descripcion |\n|---|---|---|\n" + "".join(
            f"| {a} | {b} | {d} |\n" for a, b, d in self.FILAS)
        _, pdf = self.generar("nuevo", "La tabla siguiente describe cada campo del registro.\n\n"
                              + tabla + "\nFin de la descripcion de los campos.\n")
        origen = self.tmp / "origen.pdf"
        self.pdf_con_tabla_en_dos_paginas(origen)
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 0, out)
        self.pdf_con_tabla_en_dos_paginas(origen, duplicada=True)     # una fila de más: sí falta
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 1, out)
        self.assertIn("nombre", out)

    def test_C10_una_cifra_del_original_que_quedo_en_la_portada_no_esta_fuera_de_lugar(self):
        renglones = [f"Renglon {letra} del contenido con texto suficiente para llenar la hoja inicial."
                     for letra in "abcdefgh"]
        origen = self.tmp / "origen.pdf"
        c = canvas.Canvas(str(origen), pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 80, "Curso Faro")
        c.drawString(70, H - 100, "Guia 4 de 4")
        for i, r in enumerate(renglones):
            c.drawString(70, H - 140 - i * 16, r)
        c.save()
        _, pdf = self.generar("nuevo", "\n\n".join(renglones) + "\n", cabecera=(
            "---\ntitulo: Curso Faro\nsubtitulo: Guia 4 de 4\nindice: no\nnumerar: no\n---\n\n"))
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

    def test_N3_el_pie_y_el_indice_se_revisan_contra_los_marcadores(self):
        sys.path.insert(0, str(RAIZ / "tools"))
        import comparar
        _, pdf = self.generar("tres", "# Uno\n\nA.\n\n# Dos\n\nB.\n\n# Tres\n\nC.\n")
        with pymupdf.open(pdf) as doc:
            chrome = comparar.pdf_lines(doc)[3]
            self.assertEqual(comparar.check_template(doc, chrome, "es"), [])
            malo = dict(chrome, foot={**chrome["foot"], 4: "Uno Página 4 de 5"})
            self.assertIn("capítulo equivocado en 1", " ".join(comparar.check_template(doc, malo, "es")))
            malo = dict(chrome, foot={**chrome["foot"], 4: "Dos Página 3 de 5"})
            self.assertIn("numeración", " ".join(comparar.check_template(doc, malo, "es")))
            malo = dict(chrome, index=[x.replace("Dos", "Otro") for x in chrome["index"]])
            self.assertIn("índice", " ".join(comparar.check_template(doc, malo, "es")))

    def test_C5_titulos_figuras_y_enlaces_del_md_contra_el_pdf(self):
        cuerpo = "# Uno\n\nVer [la guia](https://ejemplo.org/guia).\n\n## Detalle\n\nTexto.\n"
        md, pdf = self.generar("base", cuerpo)
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)
        otro = self.md("otro", cuerpo.replace("## Detalle", "## Resumen").replace("guia)", "otra)"))
        rc, out = run("tools/comparar.py", otro, pdf)
        self.assertEqual(rc, 1, out)
        self.assertIn("Estructura: títulos", out)
        self.assertIn("Aviso: enlaces", out)


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

    def test_G16_un_comando_largo_en_una_celda_no_se_parte(self):
        comando = "./scripts/keycloak-admin.sh"                          # no cabe en 1/3 del ancho
        md, pdf = self.generar("ancho", "# T\n\n| Paso | Comando | Nota |\n|---|---|---|\n"
                               f"| 1 | `{comando} add-role maria` | Asigna el rol a la persona "
                               "indicada en el comando y lo confirma. |\n")
        with pymupdf.open(pdf) as doc:
            renglones = [ln.strip() for ln in doc[2].get_text().splitlines()]
        self.assertTrue(any(comando in r for r in renglones), renglones)
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)

    def test_C8_palabras_que_no_caben_en_ninguna_columna_no_son_faltantes(self):
        a, b = "identificador_muy_largo_" * 3 + "a", "otro_nombre_extenso_" * 4 + "b"
        md, pdf = self.generar("partida", f"# T\n\n| Uno | Dos |\n|---|---|\n| `{a}` | `{b}` |\n")
        rc, out = run("tools/comparar.py", md, pdf, "--estricto")
        self.assertEqual(rc, 0, out)

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

    def test_G5_el_pie_muestra_el_capitulo_de_cada_pagina_aunque_el_indice_ocupe_varias(self):
        cuerpo = "".join(f"# Capitulo {c}\n\n" + "".join(
            f"## Seccion {c}.{s}\n\nTexto.\n\n" for s in range(1, 9)) for c in range(1, 9))
        md, pdf = self.generar("largo", cuerpo)
        with pymupdf.open(pdf) as doc:
            caps = [(p, t) for nivel, t, p in doc.get_toc() if nivel == 1]
            self.assertGreater(caps[0][0], 3)                        # índice de 2 páginas o más
            for page in list(doc)[1:]:
                n = page.number + 1
                pie = " ".join(b[4] for b in page.get_text("blocks") if b[1] > page.rect.height * 0.93)
                real = [t for p, t in caps if p <= n][-1:]
                if real:
                    self.assertIn(real[0], pie, f"p.{n}")
                else:
                    self.assertNotIn("Capitulo", pie, f"p.{n} (índice)")
        rc, out = run("tools/comparar.py", md, pdf, "--estricto")
        self.assertEqual(rc, 0, out)

    def texto(self, pdf, desde=1):
        with pymupdf.open(pdf) as doc:
            return "\n".join(p.get_text() for p in list(doc)[desde:])

    def test_G2_cuadro_celda_y_cita_mas_altos_que_una_pagina_se_dividen(self):
        largo = " ".join(f"palabra{i}" for i in range(1500))
        relleno = "\n\n".join(["Texto de relleno para bajar en la pagina."] * 21)
        casos = {"cuadro": f"> [!NOTA]\n> {largo}\n",
                 "cuadro con titulo": f"{relleno}\n\n> [!NOTA] Titulo\n> Parrafo corto.\n>\n> {largo}\n",
                 "celda": f"{relleno}\n\n| A | B |\n|---|---|\n| uno | corto |\n| x | {largo} |\n",
                 "cita": f"> {largo}\n"}
        for nombre, cuerpo in casos.items():
            with self.subTest(nombre):
                md, pdf = self.generar("alto", "# Cap\n\n" + cuerpo)
                palabras = re.findall(r"palabra\d+", self.texto(pdf))
                self.assertEqual(palabras, [f"palabra{i}" for i in range(1500)])
                self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)

    def test_G4_simbolos_fuera_de_la_fuente_normal_salen_como_texto(self):
        md, pdf = self.generar("simbolos", "# Agua H₂O y x²\n\nEl ángulo α ≥ β, hecho ✓, "
                               "**masa Ω₁** y `a → b`.\n\n| S | Uso |\n|---|---|\n| ↔ | ida |\n\n"
                               "```\nA ──▶ B\n│\n▼\n```\n",
                               cabecera="---\ntitulo: Química ΔT\nnumerar: no\n---\n\n")
        texto = self.texto(pdf, 0)
        for esperado in ("H₂O", "α ≥ β", "✓", "Ω₁", "a → b", "↔",
                         "A ──▶ B", "▼", "Química ΔT"):
            self.assertIn(esperado, texto)
        self.assertNotIn("■", texto)
        self.assertEqual(run("tools/validar.py", md, "--estricto")[0], 0)
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)

    def test_G4_un_caracter_que_ninguna_fuente_tiene_se_avisa(self):
        md = self.md("cjk", "# T\n\nTexto 日本 fin.\n")
        rc, out = run("manual.py", md, "-o", self.tmp / "cjk.pdf", "--estricto")
        self.assertEqual(rc, 1, out)
        self.assertIn("sin glifo", out)
        self.assertEqual(run("tools/validar.py", md)[0], 1)

    def test_G3_lista_numerada_respeta_su_numero_y_las_lineas_vacias(self):
        md, pdf = self.generar("listas", "# Cap\n\n5. cinco\n6. seis\n\nTexto.\n\n1. uno\n\n2. dos\n\n"
                                         "3. tres\n\n```\nx\n```\n\n4. cuatro\n")
        renglones = [r.strip() for r in self.texto(pdf, 2).splitlines()]
        for esperado in ("5. cinco", "6. seis", "1. uno", "2. dos", "3. tres", "4. cuatro"):
            self.assertIn(esperado, renglones)
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)

    def test_G17_listas_anidadas_conservan_la_jerarquia(self):
        md, pdf = self.generar("anidada", "# Cap\n\n- fruta\n  - manzana\n  - pera\n- verdura\n\n"
                                          "1. abrir\n   1. tapa\n   2. sello\n2. cerrar\n")
        with pymupdf.open(pdf) as doc:
            x = {w[4]: w[0] for w in doc[2].get_text("words")}
        self.assertGreater(x["manzana"], x["fruta"] + 8)             # más adentro que su padre
        self.assertAlmostEqual(x["fruta"], x["verdura"], delta=1)
        self.assertGreater(x["tapa"], x["abrir"] + 8)
        renglones = [r.strip() for r in self.texto(pdf, 2).splitlines()]
        for esperado in ("1. abrir", "1. tapa", "2. sello", "2. cerrar"):
            self.assertIn(esperado, renglones)
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)

    def test_G8_lo_que_no_se_pudo_imprimir_se_avisa_y_falla_en_estricto(self):
        md = self.md("avisos", "# Uno\n\n![pie](no_existe.png)\n\n<!-- nota --> texto perdido\n\n"
                               "```\nx = 1\n\n# Dos\n")
        pdf = self.tmp / "avisos.pdf"
        rc, out = run("manual.py", md, "-o", pdf)
        self.assertEqual(rc, 0, out)
        for esperado in ("imagen no encontrada", "después de -->", "sin cerrar"):
            self.assertIn(esperado, out)
        self.assertRegex(out, r"Aviso l\.8: imagen")                 # con la línea del .md
        self.assertEqual(run("manual.py", md, "-o", pdf, "--estricto")[0], 1)
        self.assertEqual(run("manual.py", RAIZ / "ejemplo.md", "-o", pdf, "--estricto")[0], 0)

    def test_G9_enlace_en_un_titulo_no_queda_crudo_en_el_marcador(self):
        md, pdf = self.generar("enlace", "# Ver [la guia](https://ejemplo.org) hoy\n\nTexto.\n")
        with pymupdf.open(pdf) as doc:
            self.assertEqual(doc.get_toc()[0][1], "Ver la guia hoy")
            self.assertNotIn("https://", doc[1].get_text())           # el índice
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)

    def test_G10_crea_la_carpeta_de_salida_y_explica_una_cabecera_invalida(self):
        md = self.md("ok", "# Uno\n\nTexto.\n")
        pdf = self.tmp / "no" / "existe" / "ok.pdf"
        self.assertEqual(run("manual.py", md, "-o", pdf)[0], 0)
        self.assertTrue(pdf.is_file())
        for cabecera, esperado in (("color: azul", "color «azul»"), ("dpi_imagenes: alta", "dpi_imagenes")):
            malo = self.md("malo", "# Uno\n\nTexto.\n", cabecera=f"---\ntitulo: P\n{cabecera}\n---\n\n")
            rc, out = run("manual.py", malo, "-o", self.tmp / "malo.pdf")
            self.assertEqual(rc, 2, out)
            self.assertIn(esperado, out)
            self.assertNotIn("Traceback", out)
        rc, out = run("manual.py", self.tmp / "no_hay.md")
        self.assertEqual(rc, 2, out)

    def test_G11_textos_largos_del_encabezado_y_del_pie_se_recortan(self):
        cabecera = ("---\ntitulo: " + "Titulo muy largo " * 8 + "\ncurso: " + "Curso largo " * 8
                    + "\nautor: " + "Nombre Apellido " * 9 + "\nindice: no\nnumerar: no\n---\n\n")
        md, pdf = self.generar("largo", "# " + "Capitulo largo " * 9 + "\n\nTexto.\n", cabecera=cabecera)
        with pymupdf.open(pdf) as doc:
            for page in doc:
                W = page.rect.width
                for b in page.get_text("blocks"):
                    self.assertLess(b[2], W - 60, b[4][:40])           # nada pasa el margen derecho
            alto = doc[1].rect.height
            zonas = [sorted((w[0], w[2], w[4]) for w in doc[1].get_text("words") if cond(w))
                     for cond in (lambda w: w[3] < alto * 0.08, lambda w: w[1] > alto * 0.92)]
        for palabras in zonas:                                         # encabezado y pie
            self.assertIn("…", " ".join(p[2] for p in palabras))
            for a, b in zip(palabras, palabras[1:]):
                self.assertLessEqual(a[1], b[0] + 0.5, (a, b))         # ningún texto sobre otro
        rc, out = run("tools/comparar.py", md, pdf)
        self.assertNotIn("Plantilla", out)                             # el pie recortado se reconoce

    def portada(self, nombre, veces, *extra):
        """Genera un manual con un título de `veces` repeticiones; devuelve (rc, salida, tramos
        de la portada como (tamaño, y0, y1, texto))."""
        md = self.md(nombre, "# Uno\n\nTexto.\n", cabecera=(
            "---\ntitulo: " + "Titulo largo de prueba " * veces + "\nsubtitulo: "
            + "Subtitulo tambien largo " * min(veces, 12)
            + "\ninstitucion: Instituto de prueba\nautor: Ada\nindice: no\n---\n\n"))
        pdf = self.tmp / f"{nombre}.pdf"
        rc, out = run("manual.py", md, "-o", pdf, *extra)
        with pymupdf.open(pdf) as doc:
            tramos = [(s["size"], s["bbox"][1], s["bbox"][3], s["text"])
                      for b in doc[0].get_text("dict")["blocks"] for ln in b.get("lines", [])
                      for s in ln["spans"] if s["text"].strip()]
            alto = doc[0].rect.height
        return rc, out, tramos, alto

    def test_G11_un_titulo_largo_en_la_portada_se_achica_y_no_sale_de_su_zona(self):
        rc, out, tramos, alto = self.portada("portada", 14, "--estricto")
        self.assertEqual(rc, 0, out)                                   # cabe entero: sin avisos
        texto = " ".join(t[3] for t in tramos)
        self.assertEqual(texto.count("Titulo"), 14)
        self.assertEqual(texto.count("Subtitulo"), 12)
        institucion = next(t for t in tramos if "INSTITUTO" in t[3])
        for size, y0, y1, t in tramos:
            self.assertGreaterEqual(y0, 0, t)                          # nada sale de la página
            if t is not institucion[3] and y1 < alto * 0.45:           # título y subtítulo
                self.assertGreater(y0, institucion[2], t)              # no se montan sobre la institución
        self.assertLess(max(t[0] for t in tramos), 32)                 # la letra se achicó

    def test_G11_un_titulo_que_no_cabe_en_la_portada_se_recorta_con_aviso(self):
        rc, out, tramos, alto = self.portada("enorme", 80, "--estricto")
        self.assertEqual(rc, 1, out)
        self.assertIn("portada", out)
        self.assertIn("…", " ".join(t[3] for t in tramos))
        institucion = next(t for t in tramos if "INSTITUTO" in t[3])
        for size, y0, y1, t in tramos:
            if t is not institucion[3] and y1 < alto * 0.45:
                self.assertGreater(y0, institucion[2], t)

    def test_G13_fecha_vacia_usa_la_de_hoy_y_una_seccion_sin_capitulo_no_se_numera(self):
        _, pdf = self.generar("g13", "## Seccion suelta\n\nTexto.\n\n# Capitulo\n\n## Otra\n\nMas.\n",
                              cabecera="---\ntitulo: P\nfecha:\n---\n\n")
        with pymupdf.open(pdf) as doc:
            self.assertIn("FECHA", doc[0].get_text())
            self.assertEqual([t for _, t, _ in doc.get_toc()], ["Seccion suelta", "1. Capitulo", "1.1 Otra"])

    EN = "---\ntitulo: Guide\nautor: Ada\nnumerar: no\nidioma: en\n---\n\n"

    def test_N2_un_manual_en_ingles_no_lleva_rotulos_en_espanol(self):
        md, pdf = self.generar("ingles", "# One\n\n> [!NOTA]\n> Keep it.\n\n> [!CONSEJO]\n> Try it.\n",
                               cabecera=self.EN)
        with pymupdf.open(pdf) as doc:
            texto = "\n".join(p.get_text() for p in doc)
            self.assertEqual(doc.xref_get_key(doc.pdf_catalog(), "Lang")[1], "en")
        for esperado in ("Contents", "Page 2 of 3", "AUTHOR", "DATE", "Note", "Tip"):
            self.assertIn(esperado, texto)
        for sobra in ("Índice", "Página", "AUTOR", "FECHA", "Nota", "Consejo"):
            self.assertNotIn(sobra, texto)
        rc, out = run("tools/comparar.py", md, pdf, "--estricto")
        self.assertEqual(rc, 0, out)

    def test_N2_comparar_falla_si_el_pdf_tiene_los_rotulos_en_otro_idioma(self):
        cuerpo = "# One\n\nSome text here.\n"
        _, pdf = self.generar("es", cuerpo, cabecera=self.EN.replace("idioma: en\n", ""))
        rc, out = run("tools/comparar.py", self.md("en", cuerpo, cabecera=self.EN), pdf)
        self.assertEqual(rc, 1, out)
        self.assertIn("idioma", out)


# ---------------------------------------------------------------------------
class Validar(Caso):
    def test_documento_limpio(self):
        rc, out = run("tools/validar.py", RAIZ / "ejemplo.md", "--estricto")
        self.assertEqual(rc, 0, out)
        self.assertIn("0 errores, 0 avisos", out)

    def test_errores(self):
        md = self.md("malo", "# Uno\n\nTexto \u65e5\u672c.\n\n![FIGURA: describir](assets/no.png)\n\n"
                             "<!-- nota --> texto perdido\n\n```\nsin cerrar\n",
                     cabecera="---\ntitulo: P\ncolor: azul\n---\n\n")
        rc, out = run("tools/validar.py", md, "--max", "30")
        self.assertEqual(rc, 1, out)
        for esperado in ("color «azul»", "sin glifo", "figura sin describir", "imagen no encontrada",
                         "después de -->", "sin cerrar"):
            self.assertIn(esperado, out)

    def test_E18_un_caracter_nul_es_error(self):
        md = self.md("nul", "# T\n\n| Paso | Hecho |\n|---|---|\n| Revisar | \x00 |\n")
        rc, out = run("tools/validar.py", md)
        self.assertEqual(rc, 1, out)
        self.assertIn("U+0000", out)

    def test_avisos_no_fallan_salvo_en_estricto(self):
        md = self.md("avisos", "## Sin capitulo\n\n#### Nivel 4\n\nTexto _asi_ y **a *b** c*.\n\n"
                               "1. Uno\n\n2. Dos\n\n- a\n  - b\n\n---\n",
                     cabecera="---\ntitulo: P\n---\n\n")
        rc, out = run("tools/validar.py", md, "--max", "30")
        self.assertEqual(rc, 0, out)
        for esperado in ("sin número", "nivel 4", "guion bajo", "mal cerrada", "línea horizontal"):
            self.assertIn(esperado, out)
        for resuelto in ("empieza en", "lista anidada"):            # G3 y G17: ya se admiten
            self.assertNotIn(resuelto, out)
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


ANCHO_RECUADRO = int((525 - 70 - 2 * 8) / (0.6 * 11))      # letras por renglón: 66


def pdf_con_codigo_partido(ruta):
    """Como un manual real: recuadro de código con letra grande, renglones partidos por
    ancho que siguen en el borde izquierdo, sangría por posición y un pie de dos líneas
    lejos del borde de la página."""
    filas = []
    for linea in CODIGO.splitlines():
        sangria = len(linea) - len(linea.lstrip())
        resto, primera = linea.strip(), True
        while resto:
            tope = ANCHO_RECUADRO - (sangria if primera else 0)
            corte = len(resto) if len(resto) <= tope else resto.rfind(" ", 0, tope + 1)
            filas.append((sangria if primera else 0, resto[:corte]))
            resto, primera = resto[corte:].strip(), False
    pdf_con_recuadro_de_codigo(ruta, filas)


def pdf_con_recuadro_de_codigo(ruta, filas):
    """Cuatro páginas; en la 2, un recuadro gris con `filas` = [(sangría, texto)] en
    Courier 11, con la sangría dada por posición."""
    c = canvas.Canvas(str(ruta), pagesize=A4)
    size, x0, x1, pad = 11, 70, 525, 8
    cw = 0.6 * size
    for n in range(1, 5):
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 90, f"Explicacion de la pagina {n} con un texto normal de relleno suficiente.")
        if n == 2:
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
        self.assertEqual(rc, 1, out)                                   # extraído, con pendientes
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
        self.assertEqual(rc, 1, out)                                   # extraído, con pendientes
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
        self.assertEqual(rc, 1, out)                                   # extraído, con pendientes
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
        self.assertEqual(rc, 1, out)                                   # extraído, con pendientes
        md = self.leer(carpeta)
        self.assertIn("```\n" + CODIGO + "\n```", md)
        cuerpo = sin_comentarios(md)
        self.assertNotIn("Page 2 of 4", cuerpo)
        self.assertNotIn("Manual paso a paso", cuerpo)

    def test_E17_el_reporte_lista_cada_renglon_de_codigo_reunido(self):
        pdf = self.tmp / "manual.pdf"
        pdf_con_codigo_partido(pdf)
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 1, out)                                   # extraído, con pendientes
        reporte = self.leer(carpeta, "reporte.md")
        total = int(re.search(r"Renglones de código reunidos \([^)]*\): (\d+)", reporte).group(1))
        lista = reporte.split("## Renglones de código reunidos")[1]
        self.assertEqual(len(re.findall(r"^- p\.2: `…", lista, flags=re.M)), total)

    def test_E17_instrucciones_distintas_no_se_unen_aunque_no_quepan_juntas(self):
        # Casos reales: en todos, la primera palabra del segundo renglón no cabe al final
        # del primero, pero son renglones del autor y deben quedar separados.
        filas = [
            (0, "# Usa solo letras y numeros: van dentro de MONGO_URI"),         # comentario...
            (0, "MONGO_ROOT_USER=root_de_prueba_para_el_manual"),                 # ...y variable
            (0, "MONGO_URI=mongodb://app:clave@localhost:27017/base?authSource=base"),
            (0, "SESSION_SECRET=reemplaza-esto-por-64-caracteres"),               # otra variable
            (4, "const dto = await service.create(body, currentUser(req))"),
            (4, "res.status(201).location(`/api/users/${dto.id}`).json(dto)"),    # misma sangría
            (6, 'className="rounded-full bg-amber-100 px-2 text-xs font-bold'),
            (8, 'text-amber-700-con-un-nombre-de-clase-largo">'),                 # sangría propia
        ]
        for (s1, a), (_, b) in zip(filas[::2], filas[1::2]):                      # no cabían juntos
            self.assertGreater(s1 + len(a) + 1 + len(b.split(" ")[0]), ANCHO_RECUADRO)
        pdf = self.tmp / "manual.pdf"
        pdf_con_recuadro_de_codigo(pdf, filas)
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 1, out)                                   # extraído, con pendientes
        codigo = "\n".join(" " * s + t for s, t in filas)
        self.assertIn("```\n" + codigo + "\n```", self.leer(carpeta))
        reporte = self.leer(carpeta, "reporte.md")
        self.assertNotIn("## Renglones de código reunidos", reporte)
        dudosos = reporte.split("## Renglones de código que podrían estar partidos")[1]
        # los cuatro pares de arriba, más los vecinos que tampoco cabían juntos
        self.assertGreaterEqual(len(re.findall(r"^- p\.2: `…", dudosos, flags=re.M)), 4)

    def test_E4_superindices_y_subindices_no_se_aplanan(self):
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate
        pdf = self.tmp / "ciencia.pdf"
        SimpleDocTemplate(str(pdf)).build([Paragraph(
            "El volumen es 10<super>3</super> m<super>2</super> de H<sub>2</sub>O segun la "
            "nota<super>1</super> del texto y la cota x<sub>crit</sub> del equipo.",
            getSampleStyleSheet()["Normal"])])
        rc, out, carpeta = self.extraer(pdf)
        md, reporte = self.leer(carpeta), self.leer(carpeta, "reporte.md")
        self.assertIn("10³ m² de H₂O segun la nota¹", md)
        self.assertIn("Cobertura 100%", reporte)                       # 10³ cuenta como 103
        self.assertIn("sin carácter propio", reporte)                  # «crit» no existe como subíndice
        self.assertEqual(rc, 1, out)

    def test_E4_tabla_con_bordes_completos_conserva_sus_celdas_y_los_indices(self):
        # Letra de 10 pt: el espacio mide menos de 3 pt y Table.extract() de PyMuPDF pega las
        # palabras («sincambios»); la tabla se descartaba y quedaba como un párrafo.
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
        st = getSampleStyleSheet()["Normal"]
        filas = (("Magnitud", "Valor medido"),
                 ("Volumen", "10<super>3</super> m<super>2</super>"),
                 ("Agua", "H<sub>2</sub>O"),
                 ("Texto", "sin cambios | con barra"))
        tabla = Table([[Paragraph(x, st) for x in f] for f in filas], colWidths=[150, 200])
        tabla.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
        pdf = self.tmp / "bordes.pdf"
        SimpleDocTemplate(str(pdf)).build([Paragraph("Tabla con bordes completos.", st), tabla])
        rc, out, carpeta = self.extraer(pdf)
        md = self.leer(carpeta)
        for fila in ("| Magnitud | Valor medido |", "| Volumen | 10³ m² |", "| Agua | H₂O |",
                     "| Texto | sin cambios \\| con barra |"):
            self.assertIn(fila, md)
        for relleno in ("unspecified", "anonymous"):                   # E14: metadatos sin valor
            self.assertNotIn(relleno, md)
        self.assertIn("Cobertura 100%", self.leer(carpeta, "reporte.md"))
        self.assertEqual(rc, 0, out)

    def test_E5_word_conserva_enlaces_numeracion_y_celdas_combinadas(self):
        import docx
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        d = docx.Document()
        p = d.add_paragraph("Consulta ")
        rid = d.part.relate_to("https://ejemplo.org/norma", "http://schemas.openxmlformats.org/"
                               "officeDocument/2006/relationships/hyperlink", is_external=True)
        h, r, t = OxmlElement("w:hyperlink"), OxmlElement("w:r"), OxmlElement("w:t")
        h.set(qn("r:id"), rid)
        t.text = "la norma vigente"
        r.append(t)
        h.append(r)
        p._p.append(h)
        p.add_run(" antes de empezar.")
        for paso in ("Abrir", "Medir", "Cerrar"):
            d.add_paragraph(paso, style="List Number")
        d.add_paragraph("Suelto", style="List Bullet")
        tabla = d.add_table(rows=2, cols=3)
        tabla.cell(0, 0).merge(tabla.cell(0, 2)).text = "Encabezado combinado"
        for j, v in enumerate(("uno", "dos", "tres")):
            tabla.cell(1, j).text = v
        origen = self.tmp / "norma.docx"
        d.save(origen)
        rc, out, carpeta = self.extraer(origen)
        self.assertEqual(rc, 0, out)
        md = self.leer(carpeta)
        self.assertIn("Consulta [la norma vigente](https://ejemplo.org/norma) antes de empezar.", md)
        self.assertIn("1. Abrir\n2. Medir\n3. Cerrar\n- Suelto", md)
        self.assertEqual(md.count("Encabezado combinado"), 1)
        self.assertIn("| uno | dos | tres |", md)

    def test_E6_texto_y_csv_guardados_por_windows(self):
        txt = self.tmp / "nota.txt"
        txt.write_bytes("Medición de presión: año 2026.\n".encode("cp1252"))
        rc, out, carpeta = self.extraer(txt)
        self.assertEqual(rc, 0, out)
        self.assertIn("Medición de presión: año 2026.", self.leer(carpeta))
        una = self.tmp / "lista.csv"                                   # una sola columna
        una.write_bytes("Nombre\nAna Muñoz\nLuis\n".encode("cp1252"))
        rc, out, carpeta = self.extraer(una)
        self.assertEqual(rc, 0, out)
        self.assertIn("| Ana Muñoz |", self.leer(carpeta))
        campo = self.tmp / "campos.csv"                                # salto dentro de un campo
        campo.write_text('Paso;Detalle\n1;"linea uno\nlinea dos"\n', encoding="utf-8")
        rc, out, carpeta = self.extraer(campo)
        self.assertEqual(rc, 0, out)
        self.assertIn("| 1 | linea uno<br>linea dos |", self.leer(carpeta))

    def test_E8_guion_al_final_del_renglon_corte_o_guion_real(self):
        pdf = self.tmp / "guiones.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Helvetica", 11)
        for i, t in enumerate(["La docu-", "mentacion del equipo es de tipo fisico-",
                               "quimico y esa documentacion sirve de respaldo."]):
            c.drawString(70, H - 100 - i * 14, t)
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        md, reporte = self.leer(carpeta), self.leer(carpeta, "reporte.md")
        self.assertIn("La documentacion del equipo es de tipo fisico-quimico y esa", md)
        self.assertIn("Guiones conservados al final de un renglón: 1 (fisico-quimico)", reporte)
        self.assertNotIn("Páginas que requieren revisión", reporte)     # sin faltantes falsos
        self.assertEqual(rc, 1, out)

    def test_E10_imagenes_transparencia_repeticion_y_jpeg(self):
        from PIL import Image
        png, jpg = self.tmp / "logo.png", self.tmp / "foto.jpg"
        im = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
        im.paste((200, 30, 30, 255), (30, 30, 90, 90))
        im.save(png)
        Image.effect_noise((300, 200), 60).convert("RGB").save(jpg, quality=80)
        pdf = self.tmp / "imagenes.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        for n in range(1, 5):
            c.setFont("Helvetica", 11)
            c.drawString(70, H - 90, f"Texto de la pagina {n} con relleno suficiente para leer.")
            if n in (1, 2):
                c.drawImage(str(png), 70, 400, 200, 200, mask="auto")
            if n == 3:
                c.drawImage(str(jpg), 70, 400, 300, 200)
            c.showPage()
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        md = self.leer(carpeta)
        nombres = re.findall(r"\]\(assets/([^)]+)\)", md)
        self.assertEqual(len(nombres), 3, md)                           # la repetida se nombra dos veces
        self.assertEqual(nombres[0], nombres[1])
        with Image.open(carpeta / "assets" / nombres[0]) as extraida:
            self.assertEqual(extraida.convert("RGBA").getpixel((0, 0))[3], 0)   # sigue transparente
        self.assertTrue(nombres[2].endswith(".jpg"))
        self.assertLess((carpeta / "assets" / nombres[2]).stat().st_size, jpg.stat().st_size * 1.5)
        self.assertIn("por describir: 2", self.leer(carpeta, "reporte.md"))
        self.assertEqual(rc, 1, out)

    def test_E11_enlace_en_su_aparicion_y_sin_la_puntuacion(self):
        pdf = self.tmp / "enlaces.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Helvetica", 11)

        def linea(y, antes, enlace, despues, url):
            c.drawString(70, y, antes + enlace + despues)
            x0 = 70 + c.stringWidth(antes, "Helvetica", 11)
            c.linkURL(url, (x0, y - 2, x0 + c.stringWidth(enlace, "Helvetica", 11), y + 10))
        linea(H - 100, "Ver la guia rapida. Despues consulta ", "la guia", " completa del curso.",
              "https://ejemplo.org/guia")
        linea(H - 140, "Mas datos del tema estan ", "aqui.", "", "https://ejemplo.org/datos")
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 0, out)
        md = self.leer(carpeta)
        self.assertIn("Ver la guia rapida. Despues consulta [la guia](https://ejemplo.org/guia) completa", md)
        self.assertIn("estan [aqui](https://ejemplo.org/datos).", md)
        self.assertNotIn("Enlaces:", md)

    def test_E12_excel_y_powerpoint_formato_ocultos_y_limite_de_filas(self):
        import datetime
        import openpyxl
        from pptx import Presentation
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Obra", "Avance", "Fecha"])
        ws.append(["Puente", 0.15, datetime.datetime(2026, 11, 10)])
        ws["B2"].number_format = "0%"
        ws["C2"].number_format = "dd/mm/yyyy"
        oculta = wb.create_sheet("Reserva")
        oculta.append(["Clave", "Valor"])
        oculta.append(["tope", 7])
        oculta.sheet_state = "hidden"
        larga = wb.create_sheet("Larga")
        larga.append(["N", "Dato"])
        for i in range(30):
            larga.append([i, f"dato {i}"])
        origen = self.tmp / "obra.xlsx"
        wb.save(origen)
        rc, out, carpeta = self.extraer(origen, "--filas", "10")
        md, reporte = self.leer(carpeta), self.leer(carpeta, "reporte.md")
        self.assertIn("| Puente | 15% | 2026-11-10 |", md)
        self.assertIn("## Hoja: Reserva (oculta)", md)
        self.assertIn("| 9 | dato 9 |", md)
        self.assertNotIn("dato 10 ", md)
        self.assertIn("Hoja 'Larga': 30 filas; se extrajeron las primeras 10", reporte)
        self.assertEqual(rc, 1, out)
        prs = Presentation()
        for titulo in ("Visible", "Reservada"):
            prs.slides.add_slide(prs.slide_layouts[5]).shapes.title.text = titulo
        prs.slides[1]._element.set("show", "0")
        clase = self.tmp / "clase.pptx"
        prs.save(clase)
        rc, out, carpeta = self.extraer(clase)
        self.assertIn("## Diapositiva 2 (oculta): Reservada", self.leer(carpeta))

    def test_E14_un_titulo_de_metadatos_sin_valor_se_reemplaza_por_el_de_la_portada(self):
        pdf = self.tmp / "informe.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setTitle("Microsoft Word - informe_final_v3.docx")
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 100, "FACULTAD DE INGENIERIA")
        c.setFont("Helvetica-Bold", 28)
        c.drawString(70, H - 200, "Manual de Bombas")
        c.showPage()
        for n in (2, 3):
            c.setFont("Helvetica", 11)
            for i in range(5):
                c.drawString(70, H - 100 - i * 16, f"Contenido de la pagina {n}, renglon {i} del texto.")
            c.showPage()
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 0, out)
        self.assertIn("titulo: Manual de Bombas\n", self.leer(carpeta))

    def test_E15_archivo_protegido_o_danado_da_un_mensaje_y_codigo_2(self):
        limpio, protegido = self.tmp / "limpio.pdf", self.tmp / "protegido.pdf"
        c = canvas.Canvas(str(limpio), pagesize=A4)
        c.drawString(70, H - 100, "Texto.")
        c.save()
        with pymupdf.open(limpio) as doc:
            doc.save(protegido, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="a", owner_pw="b")
        roto = self.tmp / "roto.docx"
        roto.write_bytes(b"esto no es un documento de Word")
        for archivo, esperado in ((protegido, "contraseña"), (roto, "no se puede abrir")):
            rc, out, _ = self.extraer(archivo)
            self.assertEqual(rc, 2, out)
            self.assertIn(esperado, out)
            self.assertNotIn("Traceback", out)

    def test_E18_un_simbolo_sin_mapa_queda_como_marca_visible(self):
        sys.path.insert(0, str(RAIZ / "tools"))
        import extraer
        texto, cuantos = extraer.mark_unmapped("<!-- p.3 -->\n\n| Revisar | \x00 |\n\n<!-- p.4 -->\n\nFin �.\n")
        self.assertEqual(cuantos, {3: 1, 4: 1})
        self.assertNotIn("\x00", texto)
        self.assertEqual(texto.count(extraer.MARK), 2)
        md = self.md("marca", "# T\n\n" + texto)
        rc, out = run("tools/validar.py", md)
        self.assertEqual(rc, 1, out)
        self.assertIn("[SIMBOLO?]", out)

    def test_ejemplo_ida_y_vuelta(self):
        pdf = self.tmp / "ejemplo.pdf"
        self.assertEqual(run("manual.py", RAIZ / "ejemplo.md", "-o", pdf)[0], 0)
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 0, out)
        self.assertIn("Pendientes: ninguno", out)                       # E13: la figura ya tiene pie
        reporte = self.leer(carpeta, "reporte.md")
        self.assertNotIn("Figuras pendientes de describir", reporte)
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

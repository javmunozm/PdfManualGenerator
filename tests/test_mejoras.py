"""Pruebas de las mejoras del 16/11/2026 (manual 2 de la serie UserManager):

    N9   tabla con columnas y filas vacías de más: se rehace, se valida y no rompe al generar
    N10  tabla que sigue en otra página con el encabezado repetido como texto
    N11  cuadro con el rótulo en el mismo párrafo; rótulos SEGURIDAD y ¿POR QUÉ?
    N12  palabras cortadas al final del renglón en uno de los dos PDF (comparar.py)
    N13  rótulos de los recuadros de código (tools/rotulos_codigo.py) y título del bloque
    N14  una palabra normal no se parte en una celda por culpa de un código largo

Y del 17/11/2026: los avisos de conversión de validar.py, tools/region.py, la detección
de diagramas de extraer.py (E24), recuadros pegados en rotulos_codigo.py y que las
opciones citadas en skills y guías existan en su script.

Todo se crea en una carpeta temporal: no se usa sources/.
"""
import re
import unittest

import pymupdf
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from test_pipeline import RAIZ, Caso, pdf_con_recuadro_de_codigo, run

W, H = A4
CAB = "---\ntitulo: P\n---\n\n"


def renglones(pdf, pagina=2):
    with pymupdf.open(pdf) as doc:
        return [ln.strip() for ln in doc[pagina].get_text().splitlines()]


class Preparar(Caso):
    def preparar(self, texto, nombre="manual"):
        carpeta = self.tmp / "ext" / nombre
        (carpeta / "assets").mkdir(parents=True, exist_ok=True)
        (carpeta / f"{nombre}.md").write_text(texto, encoding="utf-8")
        rc, out = run("tools/preparar.py", carpeta, "--salida", self.tmp / "doc")
        return rc, out, (self.tmp / "doc" / nombre / f"{nombre}.md").read_text(encoding="utf-8")

    def test_N9_tabla_con_columnas_y_filas_vacias_de_mas_se_rehace(self):
        tabla = ("| **DTO** |  |  |  |  |  | **Dirección** | **Para qué** |  |  |  |\n"
                 "|---|---|---|---|---|---|---|---|---|---|---|\n"
                 "|  |  |  |  |  |  |  |  |  |  |  |\n"
                 "| `BaseUserDto` |  |  |  |  |  | entrada | Campos comunes (como `BaseActivityDto` |  |  | en |\n"
                 "|  |  |  |  |  |  |  | Reactivities). |  |  |  |\n"
                 "|  |  |  |  |  |  |  |  |  |  |  |\n"
                 "| `PhotoUploadResult`, |  |  |  |  |  | interno | Lo que devuelve el servicio. |  |  |  |\n"
                 "| `PhotoFileDto` |  |  |  |  |  |  |  |  |  |  |\n")
        rc, out, t = self.preparar(CAB + "# Uno\n\n" + tabla)
        self.assertEqual(rc, 0, out)
        self.assertIn("tablas rehechas", out)
        self.assertIn("| **DTO** | **Dirección** | **Para qué** |\n|---|---|---|\n"
                      "| `BaseUserDto` | entrada | Campos comunes (como `BaseActivityDto` en Reactivities). |\n"
                      "| `PhotoUploadResult`, `PhotoFileDto` | interno | Lo que devuelve el servicio. |", t)

    def test_N9_una_tabla_normal_con_celdas_vacias_no_se_toca(self):
        tabla = "| A | B | C | D |\n|---|---|---|---|\n| 1 |  | 3 |  |\n| 5 | 6 |  | 8 |\n"
        rc, out, t = self.preparar(CAB + "# Uno\n\n" + tabla)
        self.assertEqual(rc, 0, out)
        self.assertIn(tabla, t)

    def test_N9_columna_vacia_y_fila_partida_de_una_tabla_que_sigue(self):
        texto = (CAB + "# Uno\n\n| **Pieza** | **Dónde** | **Qué hace** |\n|---|---|---|\n"
                 "| `A` | `x` | Primero. |\n\n<!-- p.2 -->\n\n"
                 "| **Pieza** |  | **Dónde** | **Qué hace** |\n|---|---|---|---|\n|  |  |  |  |\n"
                 "| `B` |  | `y` | Lo inesperado: el |\n|  |  |  | resto sale igual. |\n")
        rc, out, t = self.preparar(texto)
        self.assertEqual(rc, 0, out)
        self.assertIn("| `A` | `x` | Primero. |\n| `B` | `y` | Lo inesperado: el resto sale igual. |", t)
        self.assertEqual(t.count("**Pieza**"), 1)

    def test_N10_tabla_que_sigue_con_el_encabezado_repetido_como_texto(self):
        texto = (CAB + "# Uno\n\n| **Pieza** | **Versión** | **Función** |\n|---|---|---|\n"
                 "| Keycloak | 26.7 | Identidad |\n\n<!-- p.2 -->\n\n"
                 "**Pieza** **Versión** **Función**\n\n"
                 "| axios | 1.20 | Cliente HTTP |\n|---|---|---|\n| Docker | 27+ | Contenedores |\n")
        rc, out, t = self.preparar(texto)
        self.assertEqual(rc, 0, out)
        self.assertIn("| Keycloak | 26.7 | Identidad |\n| axios | 1.20 | Cliente HTTP |\n"
                      "| Docker | 27+ | Contenedores |", t)
        self.assertNotIn("**Pieza** **Versión** **Función**", t)

    def test_N10_la_ultima_fila_que_quedo_como_parrafo_se_avisa(self):
        texto = (CAB + "# Uno\n\n| **Pieza** | **Versión** |\n|---|---|\n| Keycloak | 26.7 |\n\n"
                 "React / Vite 19.2 / 8\n\n<!-- p.2 -->\n\n**Pieza** **Versión**\n\n"
                 "| axios | 1.20 |\n|---|---|\n| Docker | 27+ |\n")
        rc, out, t = self.preparar(texto)
        self.assertEqual(rc, 1, out)                                   # queda una fila por armar
        self.assertIn("quedó debajo de su tabla", out)
        self.assertIn("| Keycloak | 26.7 |\n| axios | 1.20 |\n| Docker | 27+ |", t)
        self.assertIn("React / Vite 19.2 / 8", t)

    def test_N15_un_bloque_de_codigo_de_tres_paginas_queda_en_uno(self):
        texto = (CAB + "# Uno\n\n```\nuno\n```\n\n<!-- p.2 -->\n\n```\ndos\n```\n\n<!-- p.3 -->\n\n"
                 "```\ntres\n```\n\nFin.\n")
        rc, out, t = self.preparar(texto)
        self.assertEqual(rc, 0, out)
        self.assertIn("```\nuno\ndos\ntres\n```\n\n<!-- p.2 -->\n\n<!-- p.3 -->\n\nFin.", t)

    def test_N16_codigo_en_linea_partido_por_el_renglon_se_une(self):
        texto = (CAB + "# Uno\n\nSe instala con `dotnet` `package add` y el proveedor "
                 "`Microsoft.EntityFrameworkCore.SqlServe` `r` de siempre.\n\n"
                 "```\ndotnet package add Microsoft.EntityFrameworkCore.SqlServer\n```\n")
        rc, out, t = self.preparar(texto)
        self.assertEqual(rc, 0, out)
        self.assertIn("con `dotnet package add` y el proveedor `Microsoft.EntityFrameworkCore.SqlServer` de", t)

    def test_N11_cuadros_con_el_rotulo_en_el_mismo_parrafo(self):
        texto = (CAB + "# Uno\n\n**NOTA** **UserManager** es un nombre de ejemplo.\n\n"
                 "**SEGURIDAD**\n\nEl archivo `.env` no se sube.\n\n"
                 "**¿POR QUÉ?** Es la recomendación vigente.\n\n"
                 "**ATENCIÓN** Verifica las versiones.\n\n"
                 "**API** es la capa que expone HTTP.\n\n"
                 "**Seguridad**\n\nUn subtítulo, no un cuadro.\n")
        rc, out, t = self.preparar(texto)
        self.assertIn("> [!NOTA]\n> **UserManager** es un nombre de ejemplo.", t)
        self.assertIn("> [!ADVERTENCIA] SEGURIDAD\n> El archivo `.env` no se sube.", t)
        self.assertIn("> [!NOTA] ¿POR QUÉ?\n> Es la recomendación vigente.", t)
        self.assertIn("> [!ADVERTENCIA] ATENCIÓN\n> Verifica las versiones.", t)
        self.assertIn("\n**API** es la capa que expone HTTP.", t)        # una sigla no es un rótulo
        self.assertIn("\n**Seguridad**\n\nUn subtítulo, no un cuadro.", t)
        self.assertIn("Seguridad", out)                                  # queda como pendiente


class TablasQueNoCaben(Caso):
    ANCHA = "# T\n\n|" + " c |" * 16 + "\n|" + "---|" * 16 + "\n|" + " x |" * 16 + "\n"

    def test_N9_validar_da_error_con_la_linea_y_manual_no_termina_en_traza(self):
        md = self.md("ancha", self.ANCHA)
        rc, out = run("tools/validar.py", md)
        self.assertEqual(rc, 1, out)
        self.assertRegex(out, r"l\.8 error: tabla de 16 columnas")
        rc, out = run("manual.py", md, "-o", self.tmp / "ancha.pdf")
        self.assertEqual(rc, 2, out)
        self.assertRegex(out, r"No se generó: l\.8: la tabla tiene 16 columnas")
        self.assertNotIn("Traceback", out)

    def test_N9_aviso_si_casi_todas_las_celdas_estan_vacias(self):
        md = self.md("rala", "# T\n\n| A |  |  | B |  |\n|---|---|---|---|---|\n"
                             "|  |  |  |  |  |\n| x |  |  | y |  |\n")
        rc, out = run("tools/validar.py", md)
        self.assertEqual(rc, 0, out)
        self.assertIn("de celdas vacías", out)

    def test_N9_una_columna_vacia_entre_otras_muy_anchas_se_dibuja(self):
        largo = "palabra_larguisima_sin_espacios_" * 3
        _, pdf = self.generar("vacia", f"# T\n\n| A | B | C |\n|---|---|---|\n| {largo} |  | {largo} |\n")
        self.assertTrue(pdf.is_file())

    def test_N14_un_codigo_largo_no_parte_las_palabras_de_otra_columna(self):
        md, pdf = self.generar(
            "ancho", "# T\n\n| Necesidad | Vue 3 | React 19 |\n|---|---|---|\n"
            "| Comunicar componentes lejanos | `provide` / `inject` (con `InjectionKey_tipada_y_muy_larga_para_la_columna`) "
            "| Context + `use(Context_con_un_nombre_larguisimo_que_no_cabe_entero)` |\n")
        texto = renglones(pdf)
        self.assertIn("componentes", " ".join(texto).split())
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)


class Comparar(Caso):
    def origen(self, *lineas):
        ruta = self.tmp / "origen.pdf"
        c = canvas.Canvas(str(ruta), pagesize=A4)
        c.setFont("Courier", 10)
        for i, linea in enumerate(lineas):
            c.drawString(70, H - 100 - 14 * i, linea)
        c.save()
        return ruta

    def test_N12_palabra_cortada_sin_guion_en_el_origen_y_entera_en_el_generado(self):
        origen = self.origen("var upload = await photoService.UploadPhoto(request.File, cancellationTo",
                             "    ken);")
        _, pdf = self.generar("nuevo", "```\nvar upload = await photoService.UploadPhoto(request.File, "
                                       "cancellationToken);\n```\n")
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 0, out)
        self.assertIn("cancellationto|ken", out)

    def test_N12_dos_palabras_que_faltan_no_se_perdonan_por_parecer_un_corte(self):
        origen = self.origen("El servicio guarda la foto y devuelve su nombre final.")
        _, pdf = self.generar("nuevo", "El servicio guarda y devuelve su nombre final.\n")
        rc, out = run("tools/comparar.py", origen, pdf)
        self.assertEqual(rc, 1, out)
        self.assertIn("foto", out)

    def test_N13_el_rotulo_que_el_original_repite_al_cambiar_de_pagina_no_es_falta(self):
        ruta = self.tmp / "origen.pdf"
        c = canvas.Canvas(str(ruta), pagesize=A4)
        c.setFont("Courier", 10)
        c.drawString(70, H - 100, "API/Program.cs")
        c.drawString(70, H - 120, "var builder = WebApplication.CreateBuilder(args);")
        c.showPage()
        c.setFont("Courier", 10)
        c.drawString(70, H - 100, "… API/Program.cs")
        c.drawString(70, H - 120, "app.Run();")
        c.save()
        _, pdf = self.generar("nuevo", "```API/Program.cs\nvar builder = WebApplication.CreateBuilder(args);\n"
                                       "app.Run();\n```\n")
        rc, out = run("tools/comparar.py", ruta, pdf)
        self.assertEqual(rc, 0, out)


class RotulosDeCodigo(Caso):
    DOC = (CAB + "# Uno\n\n```\nAPI/Program.cs\n\nvar a = 1;\n… API/Program.cs\n\nvar b = 2;\n\n\n"
           "TERMINAL\n\ndotnet run\n```\n\n<!-- p.2 -->\n\n<!-- p.3 -->\n\n```\n… TERMINAL\n\ndotnet test\n```\n\n"
           "```\n  diagrama ──► sin rótulo\n```\n")

    def test_N13_los_rotulos_pasan_al_titulo_y_el_codigo_queda_limpio(self):
        md = self.tmp / "d.md"
        md.write_text(self.DOC, encoding="utf-8")
        rc, out = run("tools/rotulos_codigo.py", md, "--ver")
        self.assertEqual(rc, 0, out)
        self.assertEqual(md.read_text(encoding="utf-8"), self.DOC)        # --ver no escribe
        rc, out = run("tools/rotulos_codigo.py", md)
        self.assertEqual(rc, 0, out)
        t = md.read_text(encoding="utf-8")
        self.assertIn("```API/Program.cs\nvar a = 1;\nvar b = 2;\n```\n\n"
                      "```TERMINAL\ndotnet run\ndotnet test\n```\n\n<!-- p.2 -->\n\n<!-- p.3 -->", t)
        self.assertIn("```\n  diagrama ──► sin rótulo\n```", t)           # sin rótulo: no se toca
        self.assertNotIn("… ", t)
        self.assertEqual(run("tools/rotulos_codigo.py", md)[0], 0)        # aplicarlo dos veces no cambia nada
        self.assertEqual(md.read_text(encoding="utf-8"), t)

    def test_N13_sin_linea_vacia_tras_el_rotulo_solo_con_todos(self):
        md = self.tmp / "e.md"
        md.write_text(CAB + "# Uno\n\n```\nTERMINAL\nmkdir keycloak\n```\n", encoding="utf-8")
        run("tools/rotulos_codigo.py", md)
        self.assertIn("```\nTERMINAL\nmkdir keycloak\n```", md.read_text(encoding="utf-8"))
        run("tools/rotulos_codigo.py", md, "--todos")
        self.assertIn("```TERMINAL\nmkdir keycloak\n```", md.read_text(encoding="utf-8"))

    def test_N13_el_titulo_del_bloque_se_imprime_y_no_cuenta_como_codigo(self):
        md, pdf = self.generar("titulo", "# T\n\n```API/Program.cs\nvar a = 1;\n```\n\n"
                                         "```python\nx = 1\n```\n\n```TERMINAL · SQL SERVER\ndocker ps\n```\n")
        texto = renglones(pdf)
        self.assertIn("API/Program.cs", texto)
        self.assertIn("TERMINAL · SQL SERVER", texto)
        self.assertNotIn("python", texto)                                 # un lenguaje no es un título
        rc, out = run("tools/comparar.py", md, pdf, "--estricto")
        self.assertEqual(rc, 0, out)
        self.assertEqual(run("tools/validar.py", md)[0], 0)

    def test_N13_un_bloque_con_titulo_que_ocupa_varias_paginas(self):
        codigo = "\n".join(f"linea_{i} = {i}" for i in range(150))
        md, pdf = self.generar("largo", f"# T\n\n```Largo/Archivo.cs\n{codigo}\n```\n")
        with pymupdf.open(pdf) as doc:
            todo = "\n".join(p.get_text() for p in doc)
        self.assertEqual(todo.count("Largo/Archivo.cs"), 1)               # el título no se repite
        self.assertIn("linea_149 = 149", todo)
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)

    def test_N13_recuadros_pegados_sin_linea_vacia_confirmados_por_su_continuacion(self):
        md = self.tmp / "f.md"
        md.write_text(CAB + "# Uno\n\n```\nAPI/A.cs\n\nvar a = 1;\nAPI/B.cs\nvar b = 2;\n"
                            "… API/B.cs\n\nvar c = 3;\n```\n", encoding="utf-8")
        rc, out = run("tools/rotulos_codigo.py", md)
        self.assertEqual(rc, 0, out)
        self.assertIn("recuadros pegados separados: 1", out)
        self.assertIn("```API/A.cs\nvar a = 1;\n```\n\n```API/B.cs\nvar b = 2;\nvar c = 3;\n```",
                      md.read_text(encoding="utf-8"))

    def test_N13_la_continuacion_en_la_pagina_siguiente_confirma_el_rotulo_pegado(self):
        # Caso del manual 4: un TERMINAL de una línea con el rótulo del recuadro siguiente
        # pegado debajo; el «… ci.yml» que lo confirma está en el bloque de la otra página.
        md = self.tmp / "g.md"
        md.write_text(CAB + "# Uno\n\n```\nTERMINAL\n\nmkdir -p .github/workflows\n"
                            ".github/workflows/ci.yml\n\nname: CI\n```\n\n<!-- p.2 -->\n\n"
                            "```\n… .github/workflows/ci.yml\n\non: push\n```\n\n"
                            "```\n.gitignore\n\nnode_modules\n.github/workflows/ci.yml\ndist\n```\n",
                      encoding="utf-8")
        rc, out = run("tools/rotulos_codigo.py", md)
        self.assertEqual(rc, 0, out)
        t = md.read_text(encoding="utf-8")
        self.assertIn("```TERMINAL\nmkdir -p .github/workflows\n```\n\n"
                      "```.github/workflows/ci.yml\nname: CI\non: push\n```\n\n<!-- p.2 -->", t)
        self.assertIn("```.gitignore\nnode_modules\n.github/workflows/ci.yml\ndist\n```", t)  # una lista no se parte


class AvisosDeConversion(Caso):
    """validar.py: defectos de una extracción que no cambian la cuenta de palabras. Solo
    se revisan en un documento con `fuente:` en la cabecera."""
    CON_FUENTE = "---\ntitulo: Prueba\nnumerar: no\nfuente: original.pdf\n---\n\n"
    CASOS = {
        "rótulo en la primera línea": ("```\nAPI/Program.cs\n\nvar a = 1;\n```\n",
                                        "es el rótulo del recuadro, no código"),
        "«… rótulo» en medio": ("```API/Program.cs\nvar a = 1;\n… API/Program.cs\nvar b = 2;\n```\n",
                                "«… rótulo» en medio del código"),
        "código en línea partido": ("Se compila con `dotnet` `run` desde la carpeta.\n",
                                    "código en línea partido en dos"),
        "puntos guía": ("Introducción . . . . . . . . . . 5\n", "renglón con puntos guía"),
        "fila vacía": ("| A | B |\n|---|---|\n|  |  |\n| 1 | 2 |\n", "fila de tabla vacía"),
        "cuadro sin armar": ("**NOTA** El archivo se guarda en la carpeta del proyecto.\n",
                             "es el rótulo de un cuadro sin armar"),
        "encabezado de tabla suelto": ("**Pieza** **Versión**\n\n| axios | 1.20 |\n|---|---|\n"
                                       "| Docker | 27+ |\n", "encabezado de tabla suelto"),
        "título fundido": ("**CAPÍTULO 3** **Configurar la base de datos** El texto sigue aquí.\n",
                           "título fundido con su párrafo"),
        "todos los títulos en un nivel": ("".join(f"## Sección {k}\n\nTexto.\n\n" for k in range(10)),
                                          "los 10 títulos están en un mismo nivel"),
    }

    def test_cada_defecto_da_su_aviso_y_solo_si_el_documento_viene_de_una_extraccion(self):
        for nombre, (cuerpo, aviso) in self.CASOS.items():
            with self.subTest(nombre):
                rc, out = run("tools/validar.py", self.md("con", cuerpo, self.CON_FUENTE))
                self.assertEqual(rc, 0, out)                          # avisos: no impiden generar
                self.assertIn(aviso, out)
                self.assertIn("0 errores, 1 avisos", out)             # cada caso, un solo defecto
                self.assertEqual(run("tools/validar.py", self.md("con", cuerpo, self.CON_FUENTE),
                                     "--estricto")[0], 1)
                rc, out = run("tools/validar.py", self.md("sin", cuerpo))
                self.assertIn("0 errores, 0 avisos", out)             # sin `fuente:`, ninguno

    def test_lo_bien_convertido_no_da_avisos(self):
        cuerpo = ("# Capítulo\n\n" + "".join(f"## Sección {k}\n\nTexto.\n\n" for k in range(10))
                  + "```API/Program.cs\nvar a = 1;\n```\n\nSe compila con `dotnet run`.\n\n"
                  "> [!NOTA]\n> El archivo se guarda.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
        rc, out = run("tools/validar.py", self.md("bien", cuerpo, self.CON_FUENTE), "--estricto")
        self.assertEqual(rc, 0, out)
        self.assertIn("0 errores, 0 avisos", out)


class Region(Caso):
    """tools/region.py: una franja de una página, como texto con columnas o como imagen."""

    def pdf(self):
        ruta = self.tmp / "region.pdf"
        c = canvas.Canvas(str(ruta), pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 80, "Antes del recuadro")
        c.setFont("Courier", 10)
        for i, (sangria, texto) in enumerate([(0, "INICIO del recuadro"), (0, "def f(x):"),
                                              (4, "return x + 1"), (0, "FIN del recuadro")]):
            c.drawString(70 + sangria * 6, H - 110 - 14 * i, texto)
        c.save()
        return ruta

    def test_texto_con_la_sangria_en_columnas(self):
        rc, out = run("tools/region.py", self.pdf(), 1, "texto", "INICIO", "FIN")
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r"col +0 .*\| def f\(x\):")
        self.assertRegex(out, r"col +4 .*\|     return x \+ 1")
        self.assertIn("3 renglones", out)                             # hasta antes de «FIN»
        self.assertNotIn("Antes del recuadro", out)

    def test_imagen_de_la_franja(self):
        png = self.tmp / "sub" / "franja.png"
        rc, out = run("tools/region.py", self.pdf(), 1, "imagen", "INICIO", "FIN", png)
        self.assertEqual(rc, 0, out)
        pix = pymupdf.Pixmap(str(png))
        self.assertGreater(pix.width, pix.height)                     # una franja, no la página
        self.assertEqual(run("tools/region.py", self.pdf(), 1, "imagen", "INICIO", "FIN")[0], 2)

    def test_codigo_2_si_no_encuentra_el_texto_o_la_pagina(self):
        rc, out = run("tools/region.py", self.pdf(), 1, "texto", "NO EXISTE", "FIN")
        self.assertEqual(rc, 2, out)
        self.assertIn("no se encontró", out)
        self.assertEqual(run("tools/region.py", self.pdf(), 3, "texto", "INICIO", "FIN")[0], 2)
        self.assertNotIn("Traceback", out)


class Diagramas(Caso):
    """extraer.py (E24): cajas unidas por flechas se guardan como diagrama pendiente."""

    def test_tres_cajas_con_flechas_y_rotulos_cortos_son_un_diagrama(self):
        pdf = self.tmp / "diagrama.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 80, "La arquitectura tiene tres piezas que se comunican en orden.")
        top, alto, ancho, hueco = H - 120, 80, 110, 40
        xs = [70 + k * (ancho + hueco) for k in range(3)]
        for x, rotulos in zip(xs, [("Cliente Vue", "navegador", "puerto 5173"),
                                   ("API .NET", "controladores", "puerto 5000"),
                                   ("SQL Server", "base de datos", "puerto 1433")]):
            c.rect(x, top - alto, ancho, alto, stroke=1, fill=0)
            for j, t in enumerate(rotulos):
                c.drawString(x + 10, top - 22 - 16 * j, t)
        for x in xs[:2]:                                              # conector y punta de flecha
            y, fin = top - alto / 2, x + ancho + hueco
            c.line(x + ancho, y, fin, y)
            p = c.beginPath()
            p.moveTo(fin, y)
            p.lineTo(fin - 7, y + 4)
            p.lineTo(fin - 7, y - 4)
            p.close()
            c.drawPath(p, stroke=1, fill=1)
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        self.assertEqual(rc, 1, out)                                   # queda por describir
        self.assertEqual([p.name for p in (carpeta / "assets").glob("*.png")], ["p1-diagrama1.png"])
        reporte = self.leer(carpeta, "reporte.md")
        self.assertIn("## Diagramas con texto", reporte)
        self.assertIn("- p.1: `assets/p1-diagrama1.png`", reporte)
        self.assertIn("![FIGURA: describir](assets/p1-diagrama1.png)", self.leer(carpeta))

    def test_un_recuadro_de_codigo_no_es_un_diagrama(self):
        pdf = self.tmp / "codigo.pdf"
        pdf_con_recuadro_de_codigo(pdf, [(0, "def f(x):"), (4, "if x:"), (8, "return 1"),
                                         (4, "return 0")])
        rc, out, carpeta = self.extraer(pdf)
        self.assertNotIn("diagrama", " ".join(p.name for p in (carpeta / "assets").glob("*")))
        self.assertNotIn("## Diagramas con texto", self.leer(carpeta, "reporte.md"))


def pdf_con_codigo(ruta, filas, texto):
    """Una página: un párrafo normal y un recuadro gris con `filas` = [(sangría, texto)]
    en Courier 11 (66 letras por renglón), con la sangría dada por posición."""
    c = canvas.Canvas(str(ruta), pagesize=A4)
    c.setFont("Helvetica", 11)
    c.drawString(70, H - 90, texto)
    x0, x1, pad, size = 70, 525, 8, 11
    alto = len(filas) * 14 + 2 * pad
    c.setFillGray(0.95)
    c.rect(x0, H - 120 - alto, x1 - x0, alto, fill=1, stroke=0)
    c.setFillGray(0)
    c.setFont("Courier", size)
    for i, (sangria, t) in enumerate(filas):
        c.drawString(x0 + pad + sangria * 0.6 * size, H - 120 - pad - size - i * 14, t)
    c.save()


class CodigoCortadoConSangria(Caso):
    """E22: el original corre la continuación 4 letras más adentro. Se une solo si el corte
    cayó a media palabra, en un comentario, con comillas abiertas o antes de un cierre."""
    FILAS = [(0, "dotnet add package Mediator.Abstractions --project src/API/API.csp"),
             (4, "roj"),
             (0, "/// Una fila de la tabla de usuarios. Se llena con proyección SQL"),
             (4, "devuelve solo estas columnas."),
             (4, "protected override async Task HandleAsync(AuthContext context,"),
             (8, "IsSelfRequirement requirement)"),
             (4, "public static partial IQueryable<User> ToItems(this IQueryable"),
             (8, ");"),
             (0, 'git commit -m "feat(api): usuarios, patrón (Mediator, Result,'),
             (4, 'FluentValidation)"')]

    def test_E22_continuaciones_con_sangria_mas_4(self):
        for sangria, t in self.FILAS[0::2]:
            self.assertLessEqual(sangria + len(t), 66, t)               # cabe en el recuadro
        pdf = self.tmp / "manual.pdf"
        pdf_con_codigo(pdf, self.FILAS, "El proyecto API.csproj lista los paquetes de la capa.")
        rc, out, carpeta = self.extraer(pdf)
        md = self.leer(carpeta)
        self.assertIn("```\ndotnet add package Mediator.Abstractions --project src/API/API.csproj\n"
                      "/// Una fila de la tabla de usuarios. Se llena con proyección SQL devuelve "
                      "solo estas columnas.\n"
                      "    protected override async Task HandleAsync(AuthContext context,\n"
                      "        IsSelfRequirement requirement)\n"             # formato del autor
                      "    public static partial IQueryable<User> ToItems(this IQueryable);\n"
                      'git commit -m "feat(api): usuarios, patrón (Mediator, Result, '
                      'FluentValidation)"\n```', md)
        reporte = self.leer(carpeta, "reporte.md")
        reunidos, dudosos = reporte.split("## Renglones de código reunidos")[1].split("\n## ", 1)
        self.assertEqual(len(re.findall(r"^- p\.1: `…", reunidos, flags=re.M)), 4)
        self.assertIn("IsSelfRequirement requirement)", dudosos)           # formato del autor: dudoso

    MAS = [(0, "dotnet watch run --project API/API.csproj --urls http://0.0.0.0 (o"),
           (4, "cualquier puerto libre)"),                                  # paréntesis abierto
           (0, '<PackageReference Include="FluentValidation" Version="12.1.10.0"'),
           (4, "/>"),
           (0, "dotnet add Persistence/Persistence.csproj reference --project"),
           (4, "Application/Application.csproj"),                           # corte entre palabras
           (4, "if (h[0] == 0xFF && h[1] == 0xD8 && h[2] == 0xFF && valid)"),
           (8, 'return ("image/jpeg", ".jpg");')]                          # cabecera de un if

    def test_E22_parentesis_cierre_xml_y_corte_entre_palabras(self):
        for sangria, t in self.MAS[0::2]:
            self.assertLessEqual(sangria + len(t), 66, t)
        pdf = self.tmp / "manual.pdf"
        pdf_con_codigo(pdf, self.MAS, "Comandos de la capa de datos.")
        rc, out, carpeta = self.extraer(pdf)
        self.assertIn("```\ndotnet watch run --project API/API.csproj --urls http://0.0.0.0 (o "
                      "cualquier puerto libre)\n"
                      '<PackageReference Include="FluentValidation" Version="12.1.10.0" />\n'
                      "dotnet add Persistence/Persistence.csproj reference --project "
                      "Application/Application.csproj\n"
                      "    if (h[0] == 0xFF && h[1] == 0xD8 && h[2] == 0xFF && valid)\n"
                      '        return ("image/jpeg", ".jpg");\n```', self.leer(carpeta))


class IdentificadorPartidoEnCelda(Caso):
    """E23: una celda angosta parte un identificador en dos renglones; al extraer quedaba
    con un espacio en medio («Authentication.Op enIdConnect»)."""

    def test_E23_el_identificador_se_une_y_dos_palabras_no(self):
        pdf = self.tmp / "tabla.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 80, "Paquetes que usa la capa API del proyecto.")
        for y in (H - 100, H - 120, H - 155):                       # solo líneas horizontales
            c.line(70, y, 520, y)
        c.setFont("Helvetica", 10)
        c.drawString(75, H - 114, "Paquete")
        c.drawString(295, H - 114, "Uso")
        c.drawString(75, H - 133, "Microsoft.AspNetCore.Authentication.Op")
        c.drawString(75, H - 146, "enIdConnect")
        c.drawString(295, H - 133, "Cliente OIDC del")
        c.drawString(295, H - 146, "backend BFF")
        c.setFont("Courier", 10)
        c.drawString(70, H - 200, "dotnet add package Microsoft.AspNetCore.Authentication.OpenIdConnect")
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        md = self.leer(carpeta)
        self.assertIn("| Microsoft.AspNetCore.Authentication.OpenIdConnect | Cliente OIDC del backend BFF |", md)


class RecuadroDeCodigoConBorde(Caso):
    """E24: un recuadro con borde, de una columna y con todo el texto en letra de código
    (un flujo dibujado con flechas de texto) salía como tabla de una celda con los
    renglones en línea. Debe salir como bloque de código con su sangría."""

    def test_E24_flujo_con_letra_de_codigo_es_un_bloque_de_codigo(self):
        pdf = self.tmp / "flujo.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 80, "Cada peticion recorre siempre el mismo camino.")
        top, bottom = H - 100, H - 200
        c.rect(70, bottom, 450, top - bottom, stroke=1, fill=0)
        c.line(70, top - 20, 520, top - 20)                         # franja del título
        c.setFont("Courier", 10)
        c.drawString(78, top - 14, "El camino de una peticion")
        for i, (sangria, t) in enumerate([(2, "Navegador --HTTP--> UsersController"),
                                          (12, "|"), (12, "v"),
                                          (8, "Mediator --> ValidationBehavior")]):
            c.drawString(78 + 6 * sangria, top - 38 - 14 * i, t)
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        md = self.leer(carpeta)
        self.assertNotIn("| ", md)                                    # no es una tabla
        self.assertIn("  Navegador --HTTP--> UsersController\n            |\n            v\n"
                      "        Mediator --> ValidationBehavior\n```", md)
        self.assertIn("```\nEl camino de una peticion\n", md)           # el rótulo, primera línea

    def test_E24_mono_box_da_los_renglones_con_su_posicion(self):
        # find_tables no detecta un recuadro de una columna dibujado con reportlab; en el
        # original sí lo detectaba (salía como tabla de una celda). Se prueba la función
        # con la tabla simulada: solo hace falta su rectángulo.
        import sys
        from types import SimpleNamespace
        sys.path.insert(0, str(RAIZ / "tools"))
        import extraer
        pdf = self.tmp / "flujo.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Courier", 10)
        for i, (sangria, t) in enumerate([(0, "El camino de una peticion"), (2, "Navegador --> API"),
                                          (6, "|"), (4, "Mediator")]):
            c.drawString(78 + 6 * sangria, H - 120 - 14 * i, t)
        c.setFont("Helvetica", 10)
        c.drawString(78, H - 300, "Texto normal fuera del recuadro.")
        c.save()
        with pymupdf.open(pdf) as doc:
            page = doc[0]
            caja = SimpleNamespace(bbox=(70, 100, 520, 190), col_count=1)
            lines = extraer.mono_box(page, caja)
            self.assertEqual(len(lines), 4)
            code, _ = extraer.rebuild_code(lines, 0)
            self.assertEqual(code, "El camino de una peticion\n  Navegador --> API\n      |\n    Mediator")
            mixta = SimpleNamespace(bbox=(70, 100, 520, 310), col_count=1)
            self.assertIsNone(extraer.mono_box(page, mixta))              # hay texto normal

    def test_E24_una_caja_de_texto_normal_sigue_siendo_un_cuadro(self):
        pdf = self.tmp / "caja.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.rect(70, H - 160, 450, 60, stroke=1, fill=0)
        c.setFont("Helvetica", 11)
        c.drawString(78, H - 120, "Nota: el archivo .env no se sube al repositorio.")
        c.drawString(78, H - 136, "Cada desarrollador crea el suyo a partir del ejemplo.")
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        self.assertNotIn("```", self.leer(carpeta))


class IndiceConPuntosSueltos(Caso):
    """E21: el índice del original da título, puntos guía y número en renglones separados;
    los renglones con puntos eran un tercio y la página no se reconocía como índice."""
    ENTRADAS = [("Parte I · Fundamentos", "5"), ("1. Introduccion: que vas a construir", "6"),
                ("1.1 Esta edicion: variante Mediator", "6"), ("1.2 Que incluye el sistema", "6"),
                ("1.3 Roles y atribuciones", "7"), ("1.4 Stack y versiones", "7"),
                ("2. Requisitos previos", "10"), ("2.1 Verificar la instalacion", "10")]

    def test_E21_la_pagina_de_indice_va_a_un_comentario(self):
        pdf = self.tmp / "indice.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Helvetica", 10)
        for i, (t, p) in enumerate(self.ENTRADAS):
            y = H - 100 - 16 * i
            c.drawString(70, y, t)
            for x in range(300, 500, 5):
                c.drawString(x, y, ".")
            c.drawRightString(520, y, p)
        c.showPage()
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 100, "Introduccion: que vas a construir. Este manual arma el sistema completo.")
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        md = self.leer(carpeta)
        self.assertIn("<!-- p.1 ÍNDICE ORIGINAL: Parte I · Fundamentos 5 | 1. Introduccion: que vas a "
                      "construir 6 | 1.1 Esta edicion: variante Mediator 6 |", md)
        self.assertNotIn(". . . .", md)
        self.assertIn("índice original", self.leer(carpeta, "reporte.md"))


class TitulosDesdeMarcadores(Caso):
    """E20: el título de la página («PARTE I · CAPÍTULO 1 Introducción») no es igual al del
    marcador («1. Introducción»): con cinco marcadores o más, todo salía en ###."""
    RELLENO = ("Este parrafo explica el tema con texto normal de relleno suficiente para que "
               "el cuerpo tenga su tamano de letra.")

    def pdf(self, ruta):
        c = canvas.Canvas(str(ruta), pagesize=A4)

        def titulo(renglones, y, size, clave, texto, nivel):
            c.bookmarkPage(clave, top=H - y + 20)
            c.addOutlineEntry(texto, clave, level=nivel)
            c.setFont("Helvetica-Bold", size)
            for i, r in enumerate(renglones):
                c.drawString(70, H - y - i * (size + 3), r)

        def parrafos(y, n=3):
            c.setFont("Helvetica", 11)
            for i in range(n):
                c.drawString(70, H - y - 16 * i, self.RELLENO[:95])

        c.setFont("Helvetica-Bold", 28)                              # portada (va a la cabecera)
        c.drawString(70, H - 200, "Manual de prueba")
        c.showPage()
        titulo(["PARTE I", "Fundamentos"], 100, 20, "p1", "Parte I · Fundamentos", 0)
        parrafos(170)
        c.showPage()
        titulo(["PARTE I · CAPÍTULO 1", "Introducción: qué vas a construir"], 100, 16, "c1",
               "1. Introducción: qué vas a construir", 1)
        parrafos(160)
        titulo(["1.1 Esta edición: variante"], 240, 13, "s11", "1.1 Esta edición: variante", 2)
        parrafos(270)
        c.showPage()
        titulo(["PARTE II · CAPÍTULO 2", "Infraestructura y", "base de datos"], 100, 13, "c2",
               "2. Infraestructura y base de datos", 1)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 100 - 3 * 16, "En este capitulo levantamos la base y el proveedor.")
        parrafos(200)
        titulo(["2.1 Variables de entorno"], 280, 13, "s21", "2.1 Variables de entorno", 2)
        parrafos(310)
        c.save()

    def test_E20_niveles_del_marcador_y_titulo_fundido_separado(self):
        pdf = self.tmp / "marcadores.pdf"
        self.pdf(pdf)
        rc, out, carpeta = self.extraer(pdf)
        md = self.leer(carpeta)
        heads = [l for l in md.splitlines() if l.startswith("#")]
        self.assertEqual(heads, ["# PARTE I Fundamentos",
                                 "## PARTE I · CAPÍTULO 1 Introducción: qué vas a construir",
                                 "### 1.1 Esta edición: variante",
                                 "## PARTE II · CAPÍTULO 2 Infraestructura y base de datos",
                                 "### 2.1 Variables de entorno"], md)
        self.assertIn("En este capitulo levantamos la base y el proveedor.", md)


class UltimaFilaSinLinea(Caso):
    """E23: antes del cambio de página el original no dibuja la línea de cierre de la tabla
    y la última fila quedaba como un párrafo debajo de ella."""

    def tabla(self, c, filas, top, cerrar):
        c.setFont("Helvetica", 10)
        ys = [top - 18 * i for i in range(len(filas) + 1)]
        for y in ys[:len(filas) + (1 if cerrar else 0)]:
            c.line(70, y, 520, y)
        for (a, b, d), y in zip(filas, ys):
            for x, t in zip((75, 230, 330), (a, b, d)):
                c.drawString(x, y - 13, t)

    def test_E23_la_fila_sin_linea_de_cierre_entra_en_la_tabla(self):
        pdf = self.tmp / "versiones.pdf"
        c = canvas.Canvas(str(pdf), pagesize=A4)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 80, "Versiones de referencia de cada pieza del sistema.")
        self.tabla(c, [("Pieza", "Version", "Funcion"), ("Keycloak", "26.7", "Identidad OIDC"),
                       ("PostgreSQL", "17", "Base de Keycloak"),
                       ("Vue / Vite", "3.5 / 8", "SPA con script setup")], H - 100, cerrar=False)
        c.showPage()
        self.tabla(c, [("Pieza", "Version", "Funcion"), ("Pinia", "4", "Sesion y rutas"),
                       ("Tailwind CSS", "4.3", "Estilos")], H - 100, cerrar=True)
        c.setFont("Helvetica", 11)
        c.drawString(70, H - 100 - 18 * 3 - 22, "Estas versiones se verificaron en octubre de 2026 con el repositorio.")
        c.save()
        rc, out, carpeta = self.extraer(pdf)
        md = self.leer(carpeta)
        self.assertIn("| PostgreSQL | 17 | Base de Keycloak |\n| Vue / Vite | 3.5 / 8 | SPA con script setup |", md)
        self.assertNotIn("\nVue / Vite 3.5 / 8 SPA con script setup", md)        # no quedó suelta
        self.assertIn("| Tailwind CSS | 4.3 | Estilos |\n\n", md)                # tabla cerrada:
        self.assertIn("Estas versiones se verificaron en octubre", md)            # el párrafo, aparte


class Coherencia(unittest.TestCase):
    """Toda opción `--algo` que citan las skills y las guías existe en su script."""
    DOCS = [*RAIZ.glob(".claude/skills/*/SKILL.md"), *RAIZ.glob(".claude/agents/*.md"),
            RAIZ / "CLAUDE.md", RAIZ / "README.md",
            *(RAIZ / "docs" / g for g in ("pipeline.md", "extractor.md", "generator.md"))]
    CITA = re.compile(r"\b(\w+)\.py\b([^`\n#|]*)")               # script y lo que le sigue
    OPCION = re.compile(r"(?<![\w-])--[a-z][\w-]*(?![\w.>-])")   # no la flecha --x.py-->

    @staticmethod
    def define(texto, opcion):
        return f'"{opcion}"' in texto or f"'{opcion}'" in texto

    def test_las_opciones_citadas_existen(self):
        scripts = [*RAIZ.glob("tools/*.py"), RAIZ / "manual.py", *RAIZ.glob(".claude/hooks/*.py")]
        fuentes = {s.name: s.read_text(encoding="utf-8") for s in scripts}
        todas, revisadas = "\n".join(fuentes.values()), 0
        for doc in self.DOCS:
            for n, linea in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
                for m in self.CITA.finditer(linea):              # `python tools/x.py ... --opción`
                    for opcion in self.OPCION.findall(m.group(2)):
                        revisadas += 1
                        with self.subTest(f"{doc.name}:{n} {m.group(1)}.py {opcion}"):
                            self.assertIn(f"{m.group(1)}.py", fuentes)
                            self.assertTrue(self.define(fuentes[f"{m.group(1)}.py"], opcion))
                for cita in re.findall(r"`(--[^`\n]+)`", linea):  # `--tanda 10000` suelto
                    for opcion in self.OPCION.findall(cita):
                        with self.subTest(f"{doc.name}:{n} {opcion}"):
                            self.assertTrue(self.define(todas, opcion))
        self.assertGreater(revisadas, 20)                        # la búsqueda encontró las citas


class FormatoDeManualNuevo(Caso):
    """Defectos de formato vistos en el manual MongoDB (18/11/2026), que validar.py no avisaba
    y el muestreo de revisar.py no mostraba."""

    def test_salto_antes_de_capitulo_se_avisa(self):
        md = self.md("salto", "# Uno\n\nTexto.\n\n\\salto\n\n# Dos\n\nMás.\n")
        rc, out = run("tools/validar.py", md, "--estricto")
        self.assertEqual(rc, 1, out)
        self.assertIn("salto de página antes de un capítulo", out)

    def test_salto_antes_de_una_seccion_no_se_avisa(self):
        md = self.md("salto2", "# Uno\n\nTexto.\n\n\\salto\n\n## Sección\n\nMás.\n")
        self.assertNotIn("salto de página", run("tools/validar.py", md)[1])

    def test_lista_dentro_de_un_cuadro_se_avisa(self):
        md = self.md("cuadro", "# T\n\n> [!NOTA] Título\n> - uno\n> - dos\n")
        rc, out = run("tools/validar.py", md, "--estricto")
        self.assertEqual(rc, 1, out)
        self.assertIn("lista dentro de un cuadro", out)

    def test_items_separados_por_renglon_vacio_no_se_avisan(self):
        md = self.md("cuadro2", "# T\n\n> [!NOTA] Título\n> • uno\n>\n> • dos\n\n> [!NOTA] Otro\n> - solo uno\n")
        self.assertNotIn("lista dentro de un cuadro", run("tools/validar.py", md)[1])

    def test_codigo_en_el_encabezado_de_una_tabla_se_avisa(self):
        md = self.md("tabla", "# T\n\n| `campo` | Valor |\n|---|---|\n| `a` | 1 |\n")
        rc, out = run("tools/validar.py", md, "--estricto")
        self.assertEqual(rc, 1, out)
        self.assertIn("encabezado de una tabla", out)
        md2 = self.md("tabla2", "# T\n\n| Campo | Valor |\n|---|---|\n| `a` | 1 |\n")
        self.assertNotIn("encabezado de una tabla", run("tools/validar.py", md2)[1])

    def test_revisar_lista_la_pagina_en_blanco(self):
        md = self.md("blanco", "# Uno\n\nTexto.\n\n\\salto\n\n# Dos\n\nMás.\n")
        pdf = self.tmp / "blanco.pdf"
        rc, out = run("manual.py", md, "-o", pdf)
        self.assertEqual(rc, 0, out)
        rc, out = run("tools/revisar.py", pdf)
        self.assertEqual(rc, 0, out)
        self.assertIn("Páginas casi vacías", out)

    def test_revisar_no_cuenta_una_portadilla_como_vacia(self):
        md = self.md("parte", "# Parte I\n\nUna línea que presenta la parte.\n\n# Uno\n\nTexto.\n")
        pdf = self.tmp / "parte.pdf"
        self.assertEqual(run("manual.py", md, "-o", pdf)[0], 0)
        rc, out = run("tools/revisar.py", pdf)
        self.assertEqual(rc, 0, out)
        self.assertIn("Sin páginas vacías", out)


if __name__ == "__main__":
    unittest.main()

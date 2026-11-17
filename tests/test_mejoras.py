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


if __name__ == "__main__":
    unittest.main()

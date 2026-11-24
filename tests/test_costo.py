"""Pruebas de las herramientas de control de costo y de las skills y subagentes.

    tools/costo.py, tools/capitulos.py, tools/comparar_traduccion.py
    .claude/skills/*/SKILL.md, .claude/agents/*.md

Todo se crea en una carpeta temporal: no se usa sources/.
"""
import re
import unittest

from test_pipeline import RAIZ, Caso, run

EJEMPLO = (RAIZ / "ejemplo.md").read_text(encoding="utf-8")


def normal(s):
    return re.sub(r"\n{3,}", "\n\n", s).strip()


class Capitulos(Caso):
    def copia(self):
        carpeta = self.tmp / "doc"
        carpeta.mkdir()
        md = carpeta / "doc.md"
        md.write_text(EJEMPLO, encoding="utf-8")
        return md

    def test_partir_y_unir_devuelve_el_mismo_documento(self):
        md = self.copia()
        rc, out = run("tools/capitulos.py", "partir", md, "--tanda", "500")
        self.assertEqual(rc, 0, out)
        partes = sorted((md.parent / "partes").glob("*.md"))
        self.assertGreater(len(partes), 4)                    # el capítulo 3 se divide en secciones
        self.assertTrue(partes[0].read_text(encoding="utf-8").startswith("---"))
        rc, out = run("tools/capitulos.py", "unir", md)
        self.assertEqual(rc, 0, out)
        self.assertEqual(normal(md.read_text(encoding="utf-8")), normal(EJEMPLO))
        self.assertTrue((md.parent / "doc.anterior.md").is_file())

    def test_no_parte_dentro_de_un_bloque_de_codigo(self):
        md = self.tmp / "c.md"
        md.write_text("# Uno\n\n```\n# esto es un comentario, no un titulo\nx = 1\n```\n\n# Dos\n\nFin.\n",
                      encoding="utf-8")
        self.assertEqual(run("tools/capitulos.py", "partir", md, "--tanda", "5")[0], 0)
        self.assertEqual(len(list((self.tmp / "partes").glob("*.md"))), 2)

    def test_P1_los_capitulos_chicos_van_juntos_en_una_parte(self):
        md = self.tmp / "d.md"
        original = "---\ntitulo: T\n---\n\n" + "".join(f"# Cap {i}\n\nTexto corto {i}.\n\n" for i in range(1, 9))
        md.write_text(original, encoding="utf-8")
        self.assertEqual(run("tools/capitulos.py", "partir", md)[0], 0)
        self.assertEqual(len(list((self.tmp / "partes").glob("*.md"))), 1)     # todo cabe en una tanda
        self.assertEqual(run("tools/capitulos.py", "partir", md, "--forzar", "--tanda", "20")[0], 0)
        partes = len(list((self.tmp / "partes").glob("*.md")))
        self.assertTrue(1 < partes < 9, partes)                                # varias por parte
        self.assertEqual(run("tools/capitulos.py", "unir", md)[0], 0)
        self.assertEqual(normal(md.read_text(encoding="utf-8")), normal(original))

    def test_no_pisa_partes_ya_trabajadas(self):
        md = self.copia()
        self.assertEqual(run("tools/capitulos.py", "partir", md)[0], 0)
        rc, out = run("tools/capitulos.py", "partir", md)
        self.assertEqual(rc, 2, out)
        self.assertEqual(run("tools/capitulos.py", "partir", md, "--forzar")[0], 0)


class Traduccion(Caso):
    ORIGINAL = ("---\ntitulo: Guia\nnumerar: si\n---\n\n# Uso\n\nEjecuta `python a.py` 3 veces. "
                "Ver [la guia](https://ejemplo.org).\n\n```\nprint('hola')  # saludo\n```\n\n"
                "| Paso | Tiempo |\n|---|---|\n| Uno | 2,5 s |\n\n> [!NOTA] Ojo\n> Son 1.250 unidades.\n\n"
                "- primero\n- segundo\n\n![Esquema del flujo](imagenes/flujo.png)\n")

    def comparar(self, traducido):
        a, b = self.tmp / "es.md", self.tmp / "en.md"
        a.write_text(self.ORIGINAL, encoding="utf-8")
        b.write_text(traducido, encoding="utf-8")
        return run("tools/comparar_traduccion.py", a, b)

    BIEN = ("---\ntitulo: Guide\nnumerar: si\nidioma: en\n---\n\n# Usage\n\nRun `python a.py` 3 times. "
            "See [the guide](https://ejemplo.org).\n\n```\nprint('hola')  # saludo\n```\n\n"
            "| Step | Time |\n|---|---|\n| One | 2.5 s |\n\n> [!NOTA] Note\n> There are 1,250 units.\n\n"
            "- first\n- second\n\n![Flow diagram](imagenes/flujo.png)\n")

    def test_traduccion_fiel_pasa_aunque_cambie_el_separador_decimal(self):
        rc, out = self.comparar(self.BIEN)
        self.assertEqual(rc, 0, out)
        self.assertIn("RESULTADO: CORRECTO", out)

    def test_detecta_lo_que_no_debia_cambiar(self):
        casos = {
            "bloques de código": self.BIEN.replace("print('hola')  # saludo", "echo('hola')  # saludo"),
            "código en línea": self.BIEN.replace("`python a.py`", "`python b.py`"),
            "cifras": self.BIEN.replace("1,250", "1,520"),
            "enlaces": self.BIEN.replace("https://ejemplo.org", "https://example.org"),
            "ítems de lista": self.BIEN.replace("- second\n", ""),
            "tablas": self.BIEN.replace("| One | 2.5 s |\n", ""),
            "cuadros": self.BIEN.replace("[!NOTA]", "[!NOTE]"),
            "títulos": self.BIEN.replace("# Usage", "## Usage"),
            "imágenes": self.BIEN.replace("imagenes/flujo.png", "images/flow.png"),
            "cabecera": self.BIEN.replace("titulo: Guide", "title: Guide"),
            "idioma: en": self.BIEN.replace("idioma: en\n", ""),      # N2: rótulos en español
        }
        for nombre, texto in casos.items():
            with self.subTest(nombre):
                rc, out = self.comparar(texto)
                self.assertEqual(rc, 1, out)
                self.assertIn(nombre, out)

    def test_comentarios_y_textos_del_codigo_se_traducen_el_codigo_no(self):
        bloque = ("```\nconst msg = 'Usuario eliminado.' // aviso al usuario\n"
                  "├─ Domain/   # Entidades y reglas (UserProfile)\n"
                  "- Domain: entidades y reglas. Depende de IUserAccessor.\n"
                  "return res.status(403)  -- sin permiso\n"
                  '<button :disabled="saving" title="Guardar">Guardar {{ n }} cambios</button>\n```\n')
        bien = ("```\nconst msg = 'User deleted.' // notice to the user\n"
                "├─ Domain/   # Entities and rules (UserProfile)\n"
                "- Domain: entities and rules. Depends on IUserAccessor.\n"
                "return res.status(403)  -- no permission\n"
                '<button :disabled="saving" title="Save">Save {{ n }} changes</button>\n```\n')
        a, b = self.tmp / "es.md", self.tmp / "en.md"
        a.write_text(self.ORIGINAL + "\n" + bloque, encoding="utf-8")
        cambios = {
            "comentarios y cadenas": (bien, 0),
            "palabra clave": (bien.replace("const msg", "constante msg"), 1),
            "identificador en texto suelto": (bien.replace("IUserAccessor", "IUserService"), 1),
            "un renglón menos": (bien.replace("- Domain: entities and rules. Depends on IUserAccessor.\n", ""), 1),
            "cifra en el código": (bien.replace("status(403)", "status(401)"), 1),
            "atributo de plantilla": (bien.replace(':disabled="saving"', ':disabled="busy"'), 1),
            "interpolación": (bien.replace("{{ n }}", "{{ count }}"), 1),
        }
        for nombre, (texto, esperado) in cambios.items():
            with self.subTest(nombre):
                b.write_text(self.BIEN + "\n" + texto, encoding="utf-8")
                rc, out = run("tools/comparar_traduccion.py", a, b)
                self.assertEqual(rc, esperado, out)
        b.write_text(self.BIEN + "\n" + bien, encoding="utf-8")
        self.assertIn("5 renglones con comentarios o textos traducidos", run("tools/comparar_traduccion.py", a, b)[1])

    def test_cita_de_un_mensaje_de_la_app_se_traduce_con_el_codigo(self):
        es = "```\nthrow new Error('Configuración inválida')\n```\n\nSi ves `Configuración inválida`, revisa.\n"
        en = "```\nthrow new Error('Invalid configuration')\n```\n\nIf you see `Invalid configuration`, check.\n"
        a, b = self.tmp / "es.md", self.tmp / "en.md"
        a.write_text(self.ORIGINAL + "\n" + es, encoding="utf-8")
        for texto, esperado in ((en, 0), (en.replace("If you see `Invalid configuration`", "If you see `Bad config`"), 1)):
            with self.subTest(texto[-40:]):
                b.write_text(self.BIEN + "\n" + texto, encoding="utf-8")
                rc, out = run("tools/comparar_traduccion.py", a, b)
                self.assertEqual(rc, esperado, out)

    def test_avisa_si_la_traduccion_es_un_resumen(self):
        largo = self.ORIGINAL.replace("Ejecuta", "Texto de relleno. " * 40 + "Ejecuta")
        a, b = self.tmp / "es.md", self.tmp / "en.md"
        a.write_text(largo, encoding="utf-8")
        b.write_text(self.BIEN, encoding="utf-8")
        rc, out = run("tools/comparar_traduccion.py", a, b)
        self.assertIn("AVISO", out)


class Costo(Caso):
    def test_estima_y_propone_tandas_sin_imprimir_el_contenido(self):
        carpeta = self.tmp / "extracted" / "doc"
        carpeta.mkdir(parents=True)
        md = carpeta / "doc.md"
        md.write_text(EJEMPLO + "\n![FIGURA: describir](assets/x.png)\n", encoding="utf-8")
        rc, out = run("tools/costo.py", md, "--tanda", "800")
        self.assertEqual(rc, 0, out)
        self.assertIn("por describir: 1", out)
        self.assertRegex(out, r"1\. l\.1-\d+")
        self.assertLess(len(out.splitlines()), 20)
        self.assertNotIn("Esta plantilla convierte", out)

    def test_documento_inexistente(self):
        rc, out = run("tools/costo.py", "no-existe")
        self.assertEqual(rc, 2, out)


class EstadoYRevision(Caso):
    DOC = "---\ntitulo: Doc\nnumerar: no\n---\n\n# Uno\n\nTexto.\n"

    def documento(self, nombre, cuerpo=DOC):
        md = self.tmp / "documentos" / nombre / f"{nombre}.md"
        md.parent.mkdir(parents=True)
        md.write_text(cuerpo, encoding="utf-8")
        return md, self.tmp / "output" / nombre / f"{nombre}.pdf"       # una carpeta por documento

    def test_estado_dice_que_falta_en_cada_documento(self):
        import os
        ext = self.tmp / "extracted" / "nuevo"
        ext.mkdir(parents=True)
        (ext / "nuevo.md").write_text("# T\n\n![FIGURA: describir](assets/a.png)\n", encoding="utf-8")
        md, pdf = self.documento("viejo")
        self.assertEqual(run("manual.py", md, "-o", pdf)[0], 0)
        os.utime(md, (pdf.stat().st_mtime + 60, pdf.stat().st_mtime + 60))      # editado después
        md, pdf = self.documento("sinver")
        self.assertEqual(run("manual.py", md, "-o", pdf)[0], 0)
        md, pdf = self.documento("listo")
        self.assertEqual(run("manual.py", md, "-o", pdf)[0], 0)
        self.assertEqual(run("tools/comparar.py", md, pdf, "--estricto")[0], 0)  # deja su registro
        unida = md.parent / "partes" / "00.md"                  # escrito por partes y ya unido
        unida.parent.mkdir()
        unida.write_text("# T\n", encoding="utf-8")
        os.utime(unida, (md.stat().st_mtime - 60, md.stat().st_mtime - 60))
        md, _ = self.documento("borrador")
        sin_unir = md.parent / "partes" / "01.md"                 # una parte cambiada después
        sin_unir.parent.mkdir()
        sin_unir.write_text("# T\n", encoding="utf-8")
        os.utime(sin_unir, (md.stat().st_mtime + 60, md.stat().st_mtime + 60))
        rc, out = run("tools/estado.py", "--raiz", self.tmp, "--todo")
        self.assertEqual(rc, 0, out)
        for esperado in ("nuevo: pendientes en la extracción: 1 figuras por describir; extraído, sin preparar",
                         "viejo: PDF desactualizado", "sinver: PDF sin verificar",
                         "borrador: partes sin unir (1 de 1 más nuevas que el .md); sin PDF",
                         "listo: terminado", "5 documentos, 4 con algo pendiente"):
            self.assertIn(esperado, out)
        self.assertNotIn("listo", run("tools/estado.py", "--raiz", self.tmp)[1])

    def test_revisar_arma_las_hojas_y_dice_que_paginas_muestra(self):
        filas = "".join(f"| Concepto {i} | Detalle {i} |\n" for i in range(1, 9))
        codigo = "\n".join(f"linea_{i} = calcular(valor_{i}, otro_valor_{i})" for i in range(12))
        md, pdf = self.documento("visual", self.DOC + f"\n# Dos\n\n| A | B |\n|---|---|\n{filas}\n"
                                                      f"# Tres\n\n```\n{codigo}\n```\n\n# Cuatro\n\nFin.\n")
        self.assertEqual(run("manual.py", md, "-o", pdf)[0], 0)
        rc, out = run("tools/revisar.py", pdf)
        self.assertEqual(rc, 0, out)
        self.assertRegex(out, r"revision\.png: p\.1 portada; p\.2 índice; p\.3 primera página")
        self.assertRegex(out, r"revision2\.png: p\.4 la tabla con más filas; p\.5 la página con más código")
        for nombre in ("revision.png", "revision2.png"):
            self.assertGreater((pdf.parent / nombre).stat().st_size, 2000)
        rc, out = run("tools/revisar.py", pdf, "--paginas", "4", "--dpi", "110")
        self.assertEqual(rc, 0, out)
        self.assertIn("páginas 4 a 110 dpi", out)
        self.assertEqual(run("tools/revisar.py", pdf, "--paginas", "99")[0], 2)


class SkillsYAgentes(unittest.TestCase):
    """Los archivos de .claude/ tienen la cabecera que Claude Code espera y solo nombran
    herramientas, skills y subagentes que existen."""

    def cabecera(self, ruta):
        texto = ruta.read_text(encoding="utf-8")
        self.assertTrue(texto.startswith("---\n"), ruta)
        front = texto.split("\n---\n", 1)[0]
        campos = dict(re.findall(r"^([\w-]+):\s*(.*)$", front, re.M))
        return campos, texto

    def test_skills(self):
        skills = sorted((RAIZ / ".claude" / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 7)
        nombres = {s.parent.name for s in skills}
        agentes = {a.stem for a in (RAIZ / ".claude" / "agents").glob("*.md")}
        for s in skills:
            with self.subTest(s.parent.name):
                campos, texto = self.cabecera(s)
                self.assertEqual(campos.get("name"), s.parent.name)
                self.assertTrue(20 < len(campos.get("description", "")) < 400)
                self.assertIn(campos.get("effort"), ("low", "medium", "high"))
                self.assertLess(len(texto.splitlines()), 80)             # cortas: se cargan enteras
                for script in re.findall(r"python (tools/\w+\.py|manual\.py)", texto):
                    self.assertTrue((RAIZ / script).is_file(), script)
                for otro in re.findall(r"[Ss]kill `([\w-]+)`", texto):
                    self.assertIn(otro, nombres)
                for agente in re.findall(r"subagente `([\w-]+)`", texto):
                    self.assertIn(agente, agentes)
        _, extraer = self.cabecera(RAIZ / ".claude" / "skills" / "extraer" / "SKILL.md")
        # Regla 1: pedir un manual autoriza extraer su original; lo prohibido es alterarlo
        self.assertNotIn("disable-model-invocation: true", extraer)
        self.assertIn("nunca se altera", extraer)

    def test_agentes(self):
        for a in sorted((RAIZ / ".claude" / "agents").glob("*.md")):
            with self.subTest(a.stem):
                campos, _ = self.cabecera(a)
                self.assertEqual(campos.get("name"), a.stem)
                self.assertIn(campos.get("model"), ("haiku", "sonnet", "opus", "inherit"))
                self.assertTrue(campos.get("tools"))
                self.assertNotIn("Bash", campos["tools"])                # no ejecutan comandos


if __name__ == "__main__":
    unittest.main()

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
        self.assertEqual(run("tools/capitulos.py", "partir", md)[0], 0)
        self.assertEqual(len(list((self.tmp / "partes").glob("*.md"))), 2)

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

    BIEN = ("---\ntitulo: Guide\nnumerar: si\n---\n\n# Usage\n\nRun `python a.py` 3 times. "
            "See [the guide](https://ejemplo.org).\n\n```\nprint('hola')  # saludo\n```\n\n"
            "| Step | Time |\n|---|---|\n| One | 2.5 s |\n\n> [!NOTA] Note\n> There are 1,250 units.\n\n"
            "- first\n- second\n\n![Flow diagram](imagenes/flujo.png)\n")

    def test_traduccion_fiel_pasa_aunque_cambie_el_separador_decimal(self):
        rc, out = self.comparar(self.BIEN)
        self.assertEqual(rc, 0, out)
        self.assertIn("RESULTADO: CORRECTO", out)

    def test_detecta_lo_que_no_debia_cambiar(self):
        casos = {
            "bloques de código": self.BIEN.replace("print('hola')  # saludo", "print('hello')  # greeting"),
            "código en línea": self.BIEN.replace("`python a.py`", "`python b.py`"),
            "cifras": self.BIEN.replace("1,250", "1,520"),
            "enlaces": self.BIEN.replace("https://ejemplo.org", "https://example.org"),
            "ítems de lista": self.BIEN.replace("- second\n", ""),
            "tablas": self.BIEN.replace("| One | 2.5 s |\n", ""),
            "cuadros": self.BIEN.replace("[!NOTA]", "[!NOTE]"),
            "títulos": self.BIEN.replace("# Usage", "## Usage"),
            "imágenes": self.BIEN.replace("imagenes/flujo.png", "images/flow.png"),
            "cabecera": self.BIEN.replace("titulo: Guide", "title: Guide"),
        }
        for nombre, texto in casos.items():
            with self.subTest(nombre):
                rc, out = self.comparar(texto)
                self.assertEqual(rc, 1, out)
                self.assertIn(nombre, out)

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
        self.assertIn("disable-model-invocation: true", extraer)         # solo la invoca el usuario

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

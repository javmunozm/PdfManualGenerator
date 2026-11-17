"""Pruebas del hook .claude/hooks/guardia.py (reglas de sources/ y de originales).

Se le entrega al hook el mismo JSON que le pasa Claude Code. No se abre ningún archivo.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HOOK = RAIZ / ".claude" / "hooks" / "guardia.py"
SRC = RAIZ / "sources"


def decision(tool, tool_input):
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(RAIZ))
    r = subprocess.run([sys.executable, "-B", str(HOOK)],
                       input=json.dumps({"tool_name": tool, "tool_input": tool_input,
                                         "cwd": str(RAIZ)}),
                       capture_output=True, text=True, encoding="utf-8", env=env)
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return None
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]


class Sources(unittest.TestCase):
    def test_editar_sources_se_deniega(self):
        self.assertEqual(decision("Edit", {"file_path": "sources/x.md"}), "deny")
        self.assertEqual(decision("Write", {"file_path": str(SRC / "nuevo.txt")}), "deny")

    def test_leer_sources_pide_permiso(self):
        self.assertEqual(decision("Read", {"file_path": str(SRC / "apuntes.md")}), "ask")
        self.assertEqual(decision("Grep", {"pattern": "hola", "path": str(SRC)}), "ask")
        self.assertEqual(decision("Glob", {"pattern": "sources/*"}), "ask")

    def test_comandos_que_nombran_sources_piden_permiso(self):
        self.assertEqual(decision("Bash", {"command": "python tools/extraer.py sources/m.pdf"}), "ask")
        self.assertEqual(decision("Bash", {"command": "ls /e/proyecto/sources"}), "ask")
        self.assertEqual(decision("PowerShell", {"command": "Get-ChildItem .\\sources"}), "ask")

    def test_lo_demas_no_se_toca(self):
        self.assertIsNone(decision("Read", {"file_path": str(RAIZ / "ejemplo.md")}))
        self.assertIsNone(decision("Write", {"file_path": str(RAIZ / "documentos" / "x" / "x.md")}))
        self.assertIsNone(decision("Glob", {"pattern": "docs/**/*.md"}))   # **/*.md: ver H6
        self.assertIsNone(decision("Bash", {"command": "python manual.py ejemplo.md"}))
        self.assertIsNone(decision("Bash", {"command": "pip install resources open-sources"}))


class SinNombrarlo(unittest.TestCase):
    """H6: lo que llega a sources/ sin escribir su nombre."""

    def test_glob_que_puede_entrar_a_sources_pide_permiso(self):
        for patron in ("**/*.pdf", "**/*", "**", "s*/*.md", "*/*", "sourc*/**"):
            self.assertEqual(decision("Glob", {"pattern": patron}), "ask", patron)
        self.assertEqual(decision("Glob", {"pattern": "**/*.md", "path": str(RAIZ)}), "ask")
        self.assertEqual(decision("Glob", {"pattern": "**/*.md", "path": str(RAIZ.parent)}), "ask")

    def test_glob_acotado_a_otra_carpeta_no_se_toca(self):
        for patron in ("docs/**/*.md", "tools/*.py", "*.md", ".claude/**/*", "tests/**"):
            self.assertIsNone(decision("Glob", {"pattern": patron}), patron)
        self.assertIsNone(decision("Glob", {"pattern": "**/*.md", "path": str(RAIZ / "docs")}))

    def test_listado_o_busqueda_recursiva_desde_la_raiz_pide_permiso(self):
        for tool, cmd in [("PowerShell", "Get-ChildItem -Recurse -Name"),
                          ("PowerShell", "gci . -r | Select-Object FullName"),
                          ("PowerShell", f'Get-ChildItem -Path "{RAIZ}" -Recurse -Filter *.pdf'),
                          ("PowerShell", "cd ..; ls -Recurse"),
                          ("PowerShell", "tree /f"),
                          ("Bash", "ls -R ."), ("Bash", "ls -laR"), ("Bash", "find . -name '*.pdf'"),
                          ("Bash", "grep -rn MongoDB ."), ("Bash", "rg --no-ignore MongoDB"),
                          ("Bash", "cd docs && cd .. && find . -type f")]:
            self.assertEqual(decision(tool, {"command": cmd}), "ask", cmd)

    def test_comodin_que_alcanza_sources_pide_permiso(self):
        self.assertEqual(decision("Bash", {"command": "cat sourc*/*/*.md"}), "ask")
        self.assertEqual(decision("PowerShell", {"command": "Get-Content s*\\*.md"}), "ask")
        self.assertEqual(decision("Bash", {"command": "head -5 */*.md"}), "ask")

    def test_encargo_a_un_subagente_que_nombra_sources_pide_permiso(self):
        self.assertEqual(decision("Agent", {"prompt": "lee sources/manual.pdf"}), "ask")
        self.assertIsNone(decision("Agent", {"prompt": "traduce documentos/x/partes/01.md"}))

    def test_comandos_habituales_no_se_tocan(self):
        for tool, cmd in [("PowerShell", "Get-ChildItem -Name"),
                          ("PowerShell", "Get-ChildItem .claude -Recurse -Name"),
                          ("PowerShell", "Get-ChildItem extracted, documentos, output -ErrorAction SilentlyContinue"),
                          ("PowerShell", "cd tools; Get-ChildItem -Recurse"),
                          ("PowerShell", "Remove-Item output\\*.png"),
                          ("PowerShell", "python -m unittest discover tests 2>&1 | Select-Object -Last 3"),
                          ("PowerShell", "git status --short --ignored"),
                          ("Bash", "ls -R tools"), ("Bash", "ls -r"), ("Bash", "find tests -name '*.py'"),
                          ("Bash", "grep -rn TODO tools docs"), ("Bash", "rg MongoDB"),
                          ("Bash", "grep -n '^#' documentos/x/x.md"),
                          ("Bash", "python tools/costo.py documentos/x/x.md")]:
            self.assertIsNone(decision(tool, {"command": cmd}), cmd)

    def test_grep_sin_ruta_depende_de_que_sources_este_en_gitignore(self):
        # ripgrep (la herramienta Grep) no entra a carpetas ignoradas: por eso el hook no
        # objeta un Grep sin ruta. Si sources/ sale de .gitignore, esa protección se pierde.
        ignorados = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("sources/", [ln.strip() for ln in ignorados])


class SiElGuardiaFalla(unittest.TestCase):
    def test_N7_una_llamada_ilegible_pide_confirmacion(self):
        r = subprocess.run([sys.executable, "-B", str(HOOK)], input="esto no es JSON",
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")


class Flujo(unittest.TestCase):
    """H3, H4 y H5 (.claude/hooks/flujo.py), con documentos creados en una carpeta temporal."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def hook(self, evento, **datos):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.raiz))
        r = subprocess.run([sys.executable, "-B", str(RAIZ / ".claude" / "hooks" / "flujo.py")],
                           input=json.dumps({"hook_event_name": evento, **datos}),
                           capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def md(self, carpeta, nombre, texto):
        ruta = self.raiz / carpeta / nombre / f"{nombre}.md"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    def editar(self, ruta):
        return self.hook("PostToolUse", tool_name="Edit", tool_input={"file_path": str(ruta)})

    def test_H3_al_editar_un_documento_devuelve_los_errores(self):
        malo = self.md("documentos", "a", "---\ntitulo: A\n---\n\n# Uno\n\n```\nsin cerrar\n")
        salida = self.editar(malo)
        self.assertEqual(salida["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("sin cerrar", salida["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(self.editar(self.md("documentos", "b", "---\ntitulo: B\n---\n\n# Uno\n\nTexto.\n")))
        self.assertIsNone(self.editar(self.raiz / "README.md"))            # fuera del flujo

    def test_H3_en_extracted_no_repite_lo_que_ya_lleva_el_reporte(self):
        figura = "# T\n\n![FIGURA: describir](assets/a.png)\n"
        self.assertIsNone(self.editar(self.md("extracted", "c", figura)))
        salida = self.editar(self.md("extracted", "d", figura + "\nCasilla [SIMBOLO?] pendiente.\n"))
        self.assertIn("[SIMBOLO?]", salida["hookSpecificOutput"]["additionalContext"])

    def test_H4_no_deja_cerrar_con_un_pdf_mas_viejo_que_su_md_y_no_insiste(self):
        md = self.md("documentos", "e", "---\ntitulo: E\n---\n\n# Uno\n\nTexto.\n")
        self.assertIsNone(self.hook("Stop"))                              # sin PDF: en trabajo
        pdf = self.raiz / "output" / "e" / "e.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"%PDF-1.4")
        os.utime(md, (pdf.stat().st_mtime + 60, pdf.stat().st_mtime + 60))
        salida = self.hook("Stop")
        self.assertEqual(salida["decision"], "block")
        self.assertIn("PDF desactualizado", salida["reason"])
        self.assertIsNone(self.hook("Stop", stop_hook_active=True))

    def test_H5_al_empezar_resume_lo_pendiente(self):
        self.assertIsNone(self.hook("SessionStart"))                      # nada que decir
        self.md("documentos", "f", "---\ntitulo: F\n---\n\n# Uno\n\nTexto.\n")
        salida = self.hook("SessionStart")
        self.assertIn("f: sin PDF", salida["hookSpecificOutput"]["additionalContext"])


class Originales(unittest.TestCase):
    def test_no_se_leen_binarios_del_proyecto(self):
        self.assertEqual(decision("Read", {"file_path": str(RAIZ / "ejemplo.pdf")}), "deny")
        self.assertEqual(decision("Read", {"file_path": str(SRC / "manual.docx")}), "deny")

    def test_imagenes_y_archivos_externos_si(self):
        img = RAIZ / "extracted" / "ejemplo" / "assets" / "p4-img47.png"
        self.assertIsNone(decision("Read", {"file_path": str(img)}))
        self.assertIsNone(decision("Read", {"file_path": str(Path.home() / "otro.pdf")}))


if __name__ == "__main__":
    unittest.main()

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
        self.assertIsNone(decision("Glob", {"pattern": "**/*.md"}))
        self.assertIsNone(decision("Bash", {"command": "python manual.py ejemplo.md"}))
        self.assertIsNone(decision("Bash", {"command": "pip install resources open-sources"}))


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

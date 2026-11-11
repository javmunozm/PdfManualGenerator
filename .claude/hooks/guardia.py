#!/usr/bin/env python3
"""Hook PreToolUse: protege sources/ y evita leer originales binarios.

H1  sources/ es del usuario: editar ahí se deniega; leer, buscar o ejecutar
    comandos que lo nombren pide confirmación.
H2  No se leen PDF ni documentos de Office directamente: se extraen.

Entrada: JSON del hook por stdin. Salida: JSON con la decisión, o nada (sin objeción).
"""
import json
import os
import re
import sys
from pathlib import Path

BINARIOS = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xlsm", ".xls"}
EDITAN = {"Edit", "Write", "NotebookEdit"}
# "sources" como nombre de carpeta: no precedido ni seguido de letras, dígitos, _ o -
NOMBRA_SOURCES = re.compile(r"(?<![\w-])sources(?![\w-])", re.I)


def decidir(decision, motivo):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": motivo,
    }}))  # ASCII con escapes \u: no depende de la codificación de la consola
    sys.exit(0)


def absoluta(ruta, cwd):
    ruta = str(ruta).strip().strip('"').strip("'")
    m = re.match(r"^/([a-zA-Z])/(.*)", ruta)        # /e/carpeta -> E:/carpeta (Git Bash)
    if m:
        ruta = f"{m.group(1)}:/{m.group(2)}"
    p = Path(ruta)
    if not p.is_absolute():
        p = Path(cwd) / p
    return Path(os.path.normcase(os.path.abspath(p)))


def dentro(ruta, carpeta):
    try:
        ruta.relative_to(carpeta)
        return True
    except ValueError:
        return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    raiz = absoluta(os.environ.get("CLAUDE_PROJECT_DIR") or cwd, cwd)
    sources = raiz / "sources"

    pide = ("sources/ contiene los documentos del usuario. Solo se usa un archivo de ahí "
            "si el usuario lo autorizó explícitamente para esta tarea.")

    if tool in EDITAN | {"Read"}:
        ruta = ti.get("file_path") or ti.get("notebook_path")
        if not ruta:
            return
        ruta = absoluta(ruta, cwd)
        en_sources = dentro(ruta, sources)
        if tool in EDITAN:
            if en_sources:
                decidir("deny", "Los originales de sources/ no se modifican nunca. "
                                "Los cambios se hacen en documentos/<nombre>/<nombre>.md.")
            return
        if ruta.suffix.lower() in BINARIOS and dentro(ruta, raiz):
            decidir("deny", "No se leen originales directamente (cuesta muchos tokens y "
                            "es impreciso). Usa: python tools/extraer.py <archivo> y lee "
                            "reporte.md; python tools/comparar.py para verificar un PDF; para "
                            "ver una página, renderízala a PNG a baja escala.")
        if en_sources:
            decidir("ask", pide)
        return

    if tool in ("Glob", "Grep"):
        ruta = ti.get("path")
        if ruta and dentro(absoluta(ruta, cwd), sources):
            decidir("ask", pide)
        if any(NOMBRA_SOURCES.search(str(ti.get(k) or "")) for k in ("pattern", "glob")):
            decidir("ask", pide)
        return

    if tool in ("Bash", "PowerShell"):
        if NOMBRA_SOURCES.search(str(ti.get("command") or "")):
            decidir("ask", pide + " El comando nombra sources/.")
        return


if __name__ == "__main__":
    main()

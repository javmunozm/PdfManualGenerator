#!/usr/bin/env python3
"""Hooks del flujo de manuales (un solo script; decide por el evento que recibe).

H3  PostToolUse (Edit, Write): si se editó el .md de un documento (documentos/<n>/<n>.md
    o extracted/<n>/<n>.md), lo revisa con tools/validar.py y devuelve los errores a
    Claude. Así un bloque sin cerrar o un símbolo ilegible se ve al escribirlo y no al
    generar. Sin errores no dice nada.
H4  Stop: si el PDF de un documento quedó más viejo que su .md, o su última verificación
    falló, lo dice una vez antes de cerrar el turno (regla: el .md es la fuente y un PDF
    no está terminado hasta que comparar.py da 0). No insiste: si Claude ya fue avisado
    en este cierre (`stop_hook_active`), deja terminar.
H5  SessionStart: agrega al contexto el resumen de tools/estado.py (documentos con algo
    pendiente), para no explorar carpetas al empezar.

Ninguno bloquea una herramienta ni toca sources/. Si algo falla aquí, el hook calla:
es una ayuda, no un control. Entrada: JSON del hook por stdin. Salida: JSON o nada.
"""
import json
import os
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parents[2]                    # donde están las herramientas
RAIZ = Path(os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or AQUI))   # los documentos
sys.path.insert(0, str(AQUI / "tools"))
# En extracted/ esto es trabajo en curso que ya lleva la cuenta reporte.md: no se repite
EN_CURSO = ("figura sin describir", "sin transcribir", "imagen no encontrada")


def emit(data):
    print(json.dumps(data))           # ASCII con escapes: no depende de la consola
    sys.exit(0)


def documento(ruta):
    """("documentos" | "extracted", ruta) si es el .md principal de un documento."""
    try:
        rel = Path(os.path.abspath(ruta)).relative_to(RAIZ)
    except ValueError:
        return None
    p = rel.parts
    if len(p) == 3 and p[0] in ("documentos", "extracted") and p[2] == f"{p[1]}.md":
        return p[0], RAIZ / rel
    return None


def al_editar(data):
    ti, tr = data.get("tool_input") or {}, data.get("tool_response")
    ruta = ti.get("file_path") or (tr.get("filePath") if isinstance(tr, dict) else None)
    doc = documento(ruta) if ruta else None
    if not doc or not doc[1].is_file():
        return
    import validar
    c = validar.Checker(doc[1])
    c.run()
    errores = sorted(f for f in c.found if f[2] == "error"
                     and not (doc[0] == "extracted" and any(x in f[3] for x in EN_CURSO)))
    if not errores:
        return
    lineas = [f"l.{n}: {msg}" for _, n, _, msg in errores[:5]]
    if len(errores) > 5:
        lineas.append(f"... y {len(errores) - 5} más (python tools/validar.py)")
    emit({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": f"tools/validar.py: {len(errores)} errores en "
                             f"{doc[1].relative_to(RAIZ).as_posix()} tras esta edición:\n"
                             + "\n".join(lineas)}})


def al_terminar(data):
    if data.get("stop_hook_active"):
        return
    import estado
    viejos = estado.stale(RAIZ)
    if not viejos:
        return
    detalle = "; ".join(f"{n}: {', '.join(t)}" for n, t in viejos[:4])
    emit({"decision": "block",
          "reason": f"Antes de terminar: {detalle}. El .md es la fuente y el PDF debe reflejarlo: "
                    "validar, generar y comparar (skill actualizar-manual o verificar-pdf). Si "
                    "queda así a propósito, decirle al usuario qué PDF está desactualizado y por qué."})


def al_empezar(_):
    import estado
    abiertos = [(n, t) for n, t in estado.status(RAIZ) if t]
    if not abiertos:
        return
    lineas = [f"- {n}: {'; '.join(t)}" for n, t in abiertos[:8]]
    if len(abiertos) > 8:
        lineas.append(f"- ... y {len(abiertos) - 8} más (python tools/estado.py)")
    emit({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "Estado de los documentos del flujo (tools/estado.py):\n" + "\n".join(lineas)}})


def main():
    data = json.load(sys.stdin)
    {"PostToolUse": al_editar, "Stop": al_terminar, "SessionStart": al_empezar}.get(
        data.get("hook_event_name"), lambda _: None)(data)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass                          # una ayuda que falla no debe estorbar

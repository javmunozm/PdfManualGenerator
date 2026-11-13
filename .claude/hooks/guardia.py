#!/usr/bin/env python3
"""Hook PreToolUse: protege sources/ y evita leer originales binarios.

H1  sources/ es del usuario: editar ahí se deniega; leer, buscar o ejecutar
    comandos que lo nombren pide confirmación.
H2  No se leen PDF ni documentos de Office directamente: se extraen.
H6  También pide confirmación lo que llega a sources/ sin nombrarlo: un Glob que
    puede entrar ahí (`**/*.pdf`, `s*/*`), un listado o búsqueda recursiva desde la
    raíz (`ls -R`, `Get-ChildItem -Recurse`, `find .`, `tree`, `grep -r`,
    `rg --no-ignore`), una ruta con comodines que alcanza la carpeta (`sourc*/*`) y
    un encargo a un subagente que la nombra. Grep sin ruta no entra a sources/
    mientras esté en .gitignore (ripgrep lo respeta; lo comprueba tests/test_hooks.py).
    Es una barrera contra descuidos, no un aislamiento: un script propio puede
    recorrer carpetas sin que el hook lo vea.

Entrada: JSON del hook por stdin. Salida: JSON con la decisión, o nada (sin objeción).
"""
import fnmatch
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


def alcanza(patron, base, sources, descender=True):
    """¿Una ruta con comodines, relativa a `base`, puede entrar a sources/?

    Con descender=True (Glob, argumentos sueltos) un comodín que solo coincide con el
    nombre de la carpeta no cuenta: hace falta que el patrón siga hacia adentro.
    """
    partes = [p for p in re.split(r"[\\/]+", patron.strip()) if p not in ("", ".")]
    i = next((k for k, p in enumerate(partes) if re.search(r"[*?\[]", p)), None)
    if i is None:
        return False
    prefijo = "/".join(partes[:i])
    if re.match(r"^[\\/]", patron.strip()) and prefijo and not re.match(r"^[a-zA-Z]:", prefijo):
        prefijo = "/" + prefijo
    carpeta = absoluta(prefijo or ".", base)
    if partes[i] == "**":
        return dentro(sources, carpeta)                 # carpeta es sources o está sobre ella
    return (carpeta == sources.parent and fnmatch.fnmatchcase("sources", partes[i].lower())
            and (not descender or len(partes) > i + 1))


CON_VALOR = {"-filter", "-include", "-exclude", "-depth", "-erroraction", "-ea", "-attributes"}


def rutas(args):
    """Argumentos que son rutas: sin banderas ni los valores de las banderas con valor."""
    out, salta = [], False
    for a in args:
        if salta:
            salta = False
        elif a.lower() in CON_VALOR:
            salta = True
        elif not (a.startswith("-") or re.fullmatch(r"/[a-zA-Z]{1,2}", a)):
            out.append(a)
    return out


def objetivos_recursivos(nombre, args, tool):
    """Carpetas que un comando recorre entera, o None si no es un listado recursivo."""
    bajos = [a.lower() for a in args]
    if nombre in ("get-childitem", "gci", "dir", "ls"):
        ps = tool == "PowerShell" and any(re.fullmatch(r"-(r|rec\w*|s|depth)", a) for a in bajos)
        sh = any(re.fullmatch(r"-[a-zA-Z]*R[a-zA-Z]*", a) for a in args) or \
            "--recursive" in bajos or "/s" in bajos
        return rutas(args) if ps or sh else None
    if nombre == "tree":
        return rutas(args)
    if nombre == "find":
        corte = next((k for k, a in enumerate(args) if a[:1] in "-(!"), len(args))
        return args[:corte]
    if nombre in ("grep", "egrep", "fgrep"):
        if any(re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", a) for a in args) or "--recursive" in bajos:
            return rutas(args)[1:]
        return None
    if nombre == "rg":
        if any(a.startswith("--no-ignore") or re.fullmatch(r"-u+", a) for a in bajos):
            return rutas(args)[1:]
        return None                                     # sin eso, ripgrep respeta .gitignore
    if nombre == "findstr" and "/s" in bajos:
        return [a for a in args[1:] if not a.startswith("/")]
    return None


def comando_alcanza(cmd, tool, cwd, sources):
    """¿Un comando puede listar o leer sources/ sin nombrarlo?"""
    aqui = absoluta(".", cwd)
    for simple in re.split(r"&&|\|\||[;|&\n]", cmd):
        crudos = simple.split()
        toks = [t.strip("\"'(){},") for t in crudos]
        pares = [(c, t) for c, t in zip(crudos, toks) if t]
        if not pares:
            continue
        nombre = re.split(r"[\\/]", pares[0][1].lower())[-1].removesuffix(".exe")
        args = [t for _, t in pares[1:]]
        if nombre in ("cd", "chdir", "pushd", "set-location", "sl") and args:
            aqui = absoluta(args[-1], aqui)
            continue
        for crudo, t in pares[1:]:                      # rutas con comodines: sourc*/*
            t = t.replace("\\", "/")
            if "/" in t.strip("/") and not re.search(r"[\^$()|+{}]", crudo) and alcanza(t, aqui, sources):
                return True
        objetivos = objetivos_recursivos(nombre, args, tool)
        if objetivos is None:
            continue
        for o in objetivos or ["."]:
            if re.search(r"[*?\[]", o):
                if alcanza(o, aqui, sources, descender=False):
                    return True
            elif dentro(sources, absoluta(o, aqui)):    # la raíz o una carpeta sobre sources
                return True
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
        if tool == "Glob" and alcanza(str(ti.get("pattern") or ""), absoluta(ruta or ".", cwd), sources):
            decidir("ask", pide + " Este patrón también recorre sources/: acota la búsqueda "
                                  "a una carpeta (docs/**, tools/**) o usa el campo path.")
        return

    if tool in ("Bash", "PowerShell"):
        cmd = str(ti.get("command") or "")
        if NOMBRA_SOURCES.search(cmd):
            decidir("ask", pide + " El comando nombra sources/.")
        if comando_alcanza(cmd, tool, cwd, sources):
            decidir("ask", pide + " El comando recorre la carpeta del proyecto y eso incluye "
                                  "sources/: indica una carpeta concreta.")
        return

    if tool in ("Agent", "Task"):
        if any(NOMBRA_SOURCES.search(str(ti.get(k) or "")) for k in ("prompt", "description")):
            decidir("ask", pide + " El encargo al subagente nombra sources/.")
        return


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Verifica una traducción sin leerla: compara lo que no debe cambiar al traducir.

Uso:
    python tools/comparar_traduccion.py ORIGINAL.md TRADUCIDO.md

tools/comparar.py compara palabras y no sirve entre dos idiomas. Aquí se compara la
estructura: títulos (niveles y orden), código en línea (idéntico), bloques de código
(mismo código: solo pueden cambiar los comentarios y el texto de las cadenas, ver
`esqueleto`), imágenes, enlaces, tablas, cuadros, listas y cifras. Si el texto traducido es mucho más
corto que el original, avisa: puede haberse resumido. La traducción debe declarar
`idioma: en` en la cabecera, para que manual.py ponga sus textos fijos en inglés.

Código de salida: 0 coincide, 1 hay diferencias, 2 error.
"""
import re
import sys
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")


def features(text):
    lines = text.splitlines()
    i = 0
    if lines and lines[0].strip() == "---":                # la cabecera se compara aparte
        i = next((j for j in range(1, len(lines)) if lines[j].strip() == "---"), 0) + 1
    f = {"títulos": [], "bloques de código": [], "código en línea": Counter(), "imágenes": [],
         "enlaces": Counter(), "tablas": [], "cuadros": [], "ítems de lista": 0, "cifras": Counter()}
    front = dict((k.strip(), v.strip()) for k, v in
                 (ln.split(":", 1) for ln in lines[1:max(i - 1, 0)] if ":" in ln))
    lang = front.pop("idioma", "").lower()                 # cambia a propósito al traducir
    keys = sorted(front)
    prose = []
    while i < len(lines):
        st = lines[i].strip()
        if st.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            f["bloques de código"].append("\n".join(lines[i + 1:j]))
            i = j + 1
            continue
        if st.startswith("<!--"):                          # los comentarios no se traducen ni comparan
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if re.match(r"#{1,6}\s", st):
            f["títulos"].append(len(st) - len(st.lstrip("#")))
        elif st.startswith("|"):
            rows = 0
            cols = st.count("|")
            while i < len(lines) and lines[i].strip().startswith("|"):
                prose.append(lines[i])
                rows += 1
                i += 1
            f["tablas"].append((rows, cols))
            continue
        elif re.match(r"\s*([-*+]|\d+[.)])\s", lines[i]):
            f["ítems de lista"] += 1
        m = re.match(r">\s*\[!(\w+)\]", st)
        if m:
            f["cuadros"].append(m.group(1).upper())
        prose.append(lines[i])
        i += 1
    body = "\n".join(prose)
    f["código en línea"].update(re.findall(r"`([^`\n]+)`", body))
    f["imágenes"] = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", body)
    f["enlaces"].update(re.findall(r"(?<!!)\[[^\]]+\]\(([^)\s]+)\)", body))
    plain = re.sub(r"`[^`\n]+`|\]\([^)]*\)", " ", body)    # sin código ni rutas
    f["cifras"].update(re.sub(r"[.,]", "", n) for n in re.findall(r"\d+(?:[.,]\d+)*", plain))
    return f, keys, len(re.sub(r"\s+", " ", plain)), lang


MARCADO = re.compile(r"</?[A-Za-z][^<>]*>|\{\{.*?\}\}|\{[^{}]*\}")


def esqueleto(linea):
    """El renglón sin comentario y con las cadenas vacías: lo que no puede cambiar al traducir.

    Al traducir se traducen los comentarios y el texto de las cadenas, nunca el código:
    `x = 'Hola' // saluda` y `x = 'Hello' // greets` tienen el mismo esqueleto `x = ''`.
    En un renglón de plantilla (Vue, JSX, HTML) el texto visible entre etiquetas también
    se traduce: quedan las etiquetas y las interpolaciones `{{ … }}` / `{ … }`.
    """
    if re.search(r"</[A-Za-z]|<[A-Za-z][^<>]*>\s*[^\s<]", linea) and not re.match(r"\s*(//|#|\*|/\*)", linea):
        partes = MARCADO.findall(linea.split("<!--")[0])
        return " ".join(_etiqueta(p) if p.startswith("<") else _esqueleto(p) for p in partes)
    return _esqueleto(linea)


FIJOS = {"class", "id", "to", "href", "src", "type", "name", "key", "ref", "for", "role",
         "method", "action", "lang", "rel", "target", "accept", "autocomplete", "variant", "size"}


def _etiqueta(tag):
    """Una etiqueta: se traduce el valor de un atributo de texto (title, placeholder, label…);
    los ligados (`:x`, `@x`, `v-x`, `#x`) son código y los estructurales (class, href…) no cambian."""
    def valor(m):
        nombre = m.group(1)
        if nombre[0] in ":@#" or nombre.startswith("v-") or nombre.lower() in FIJOS:
            return m.group(0)
        return f'{nombre}={m.group(2)}{m.group(2)}'
    return re.sub(r"""([:@#]?[\w.:-]+)=(["'])(.*?)\2""", valor, tag)


LIGADO = re.compile(r"(?:(?<![\w-])[:@#][\w.:-]+|(?<![\w-])v-[\w.:-]+|\b(?:%s))\s*=\s*$" % "|".join(sorted(FIJOS)))


def _esqueleto(linea):
    out, q, i, guarda = [], None, 0, False
    while i < len(linea):
        c = linea[i]
        if q:
            if c == "\\":
                if guarda:
                    buf.append(linea[i:i + 2])
                i += 2
                continue
            if c == q:
                q = None
                if guarda:                                # :x="expr": código, con sus cadenas vacías
                    out.append(_esqueleto("".join(buf)))
                out.append(c)
            elif guarda:
                buf.append(c)
            i += 1
            continue
        prev = linea[i - 1] if i else " "
        if (linea.startswith("//", i) and prev != ":") or linea.startswith("/*", i) \
                or linea.startswith("<!--", i) or (c == "#" and prev in " \t") \
                or (linea.startswith("-- ", i) and prev in " \t"):
            break
        if c in "'\"`" and not (c == "'" and prev.isalpha()):   # don't, it's: no abren cadena
            q, buf = c, []
            guarda = bool(LIGADO.search(linea[:i]))
        out.append(c)
        i += 1
    return "".join(out).rstrip()


CODIGO = re.compile(r"[\w$@-]*[A-Za-z_$@][\w$@-]*(?:[./:\\][\w$@*{}<>-]+)+"   # rutas, a.b, users:read
                    r"|\b(?=\w*[a-z])\w+[A-Z]\w*|\b\w+_\w+"       # camelCase, PascalCase, IUser, snake (no USUARIO)
                    r"|\d+(?:\.\d+)*")


def en_comentario(lineas):
    """Para cada renglón, si está dentro de un comentario de varios renglones (/* */, <!-- -->,
    docstring) o es un renglón `* …` de JSDoc. El renglón que abre no cuenta: lo ve esqueleto."""
    res, abierto = [], None
    for l in lineas:
        s = l.strip()
        if abierto:
            res.append(True)
            if abierto in l:
                abierto = None
            continue
        res.append(bool(re.match(r"\*(\s|/|$)", s)))
        for a, c in (("/*", "*/"), ("<!--", "-->"), ('"""', '"""')):
            k = l.find(a)
            if a == '"""' and not (s.startswith(a) or s.endswith(a)):
                continue
            if k >= 0 and c not in l[k + len(a):]:
                abierto = c
                break
    return res


def mismo_codigo(a, b):
    """¿Dos bloques tienen el mismo código, aunque cambien comentarios y textos?

    Devuelve (iguales, renglones con texto traducido, primer renglón distinto o None).
    """
    la, lb = a.split("\n"), b.split("\n")
    if len(la) != len(lb):
        return False, 0, (f"{len(la)} renglones", f"{len(lb)} renglones")
    cambiados = 0
    for x, y, dentro in zip(la, lb, en_comentario(la)):
        if x == y:
            continue
        cambiados += 1
        if dentro:
            continue                                      # renglón interior de un comentario largo
        if esqueleto(x) == esqueleto(y):
            continue
        if solo_texto(x, y):
            continue
        return False, cambiados, (x.strip(), y.strip())
    return True, cambiados, None


CLAVE = set("""return const let var function async await if else elif for foreach while do new class
public private protected internal static void import export from default select where insert
update delete join into values true false null none undefined this self string int bool get set
echo cd ls git npm npx docker dotnet node run then fi esac case in is not and or try catch
finally throw using namespace interface type enum readonly yield lambda def print""".split())
SIMBOLOS = re.compile(r"[{}\[\]=;<>|&$]")
INTERPOLA = re.compile(r"\{\{.*?\}\}|\$\{[^}]*\}")
ATRIB_LIGADO = re.compile(r"""(?<![\w-])(?:[:@#][\w.:-]+|v-[\w.:-]+)=(["'])(.*?)\1""")


def _palabras(s):
    return re.findall(r"[^\W\d_]+|\S", s)


def solo_texto(x, y):
    """Un renglón que no es código puro (prosa, diagrama, ayuda de un script, texto de una
    plantilla) puede cambiar sus palabras, pero no: los identificadores y rutas, las cifras,
    los símbolos de código, las interpolaciones, los atributos ligados ni una palabra clave."""
    sx, sy = esqueleto(x), esqueleto(y)
    clave = lambda s: Counter(_esqueleto(m.group(2)) for m in ATRIB_LIGADO.finditer(s))
    if Counter(CODIGO.findall(sx)) != Counter(CODIGO.findall(sy)) \
            or Counter(SIMBOLOS.findall(sx)) != Counter(SIMBOLOS.findall(sy)) \
            or Counter(INTERPOLA.findall(x)) != Counter(INTERPOLA.findall(y)) \
            or clave(x) != clave(y):
        return False
    import difflib
    a, b = _palabras(sx), _palabras(sy)
    for op, i1, i2, _, _ in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op in ("replace", "delete") and any(w.lower() in CLAVE for w in a[i1:i2]):
            return False                                  # una palabra clave traducida o quitada
    return True


def textos_de_codigo(bloques):
    """Textos para personas dentro de los bloques: contenido de cadenas y texto entre etiquetas."""
    res = set()
    for b in bloques:
        for t in re.findall(r"""'([^'\n]+)'|"([^"\n]+)"|`([^`\n]+)`|>([^<>{}\n]+)<""", b):
            s = "".join(t).strip()
            if s:
                res.add(s)
    return res


def show(x):
    s = repr(x) if not isinstance(x, str) else x.replace("\n", " ⏎ ")
    return s if len(s) <= 70 else s[:67] + "..."


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    for p in (a, b):
        if not p.is_file():
            print(f"No existe el archivo: {p}")
            return 2
    fa, ka, la, _ = features(a.read_text(encoding="utf-8-sig"))
    fb, kb, lb, lang = features(b.read_text(encoding="utf-8-sig"))
    bad = 0
    if lang not in ("en", "english", "inglés", "ingles"):
        bad += 1
        print("cabecera: la traducción debe declarar `idioma: en`; sin eso el índice, el pie "
              "y los rótulos de la portada y de los cuadros salen en español")
    if ka != kb:
        bad += 1
        print(f"cabecera: cambian las claves · solo en el original: {sorted(set(ka) - set(kb))} · "
              f"solo en la traducción: {sorted(set(kb) - set(ka))}")
    traducidos = 0
    for name in fa:
        x, y = fa[name], fb[name]
        if x == y:
            continue
        if name == "bloques de código" and len(x) == len(y):
            malos = []
            for k, (p, q) in enumerate(zip(x, y)):
                ok, n, dif = mismo_codigo(p, q)
                traducidos += n
                if not ok:
                    malos.append((k, dif))
            if not malos:
                continue
            bad += 1
            k, (p, q) = malos[0]
            print(f"{name}: {len(malos)} con el código cambiado (se traducen solo comentarios y "
                  f"textos) · primero, el n.º {k + 1}: {show(p)} -> {show(q)}")
            continue
        bad += 1
        if isinstance(x, Counter):
            gone, new = x - y, y - x
            if name == "código en línea":                 # cita de un texto de la app, traducido con él
                ca, cb = textos_de_codigo(fa["bloques de código"]), textos_de_codigo(fb["bloques de código"])
                for g in list(gone):
                    par = next((n for n in new if any(g in s for s in ca) and any(n in s for s in cb)
                                and not any(g in s for s in cb)), None)
                    if par:
                        gone[g] -= 1
                        new[par] -= 1
                gone, new = +gone, +new
                if not gone and not new:
                    bad -= 1
                    continue
            print(f"{name}: faltan {sum(gone.values())} · sobran {sum(new.values())}"
                  + (f" · falta: {', '.join(show(k) for k in list(gone)[:5])}" if gone else "")
                  + (f" · sobra: {', '.join(show(k) for k in list(new)[:5])}" if new else ""))
        elif isinstance(x, list):
            k = next((i for i, (p, q) in enumerate(zip(x, y)) if p != q), min(len(x), len(y)))
            p, q = (x[k] if k < len(x) else "(no hay)"), (y[k] if k < len(y) else "(no hay)")
            if isinstance(p, str) and isinstance(q, str) and "\n" in p + q:   # el renglón que cambió
                pl, ql = p.split("\n"), q.split("\n")
                j = next((i for i, (u, v) in enumerate(zip(pl, ql)) if u != v), min(len(pl), len(ql)) - 1)
                p, q = pl[min(j, len(pl) - 1)].strip(), ql[min(j, len(ql) - 1)].strip()
            print(f"{name}: {len(x)} en el original, {len(y)} en la traducción · primera diferencia "
                  f"en el n.º {k + 1}: {show(p)} -> {show(q)}")
        else:
            print(f"{name}: {x} en el original, {y} en la traducción")
    ratio = lb / (la or 1)
    note = ""
    if not 0.65 <= ratio <= 1.35:
        note = " · AVISO: tamaño muy distinto; revisar que no se haya resumido ni duplicado"
    print(f"Texto: {la:,} caracteres -> {lb:,} ({ratio:.0%}){note}")
    if traducidos:
        print(f"Código: {traducidos} renglones con comentarios o textos traducidos; el código, igual")
    print("RESULTADO: " + ("FALLA (" + str(bad) + " diferencias de estructura)" if bad else "CORRECTO"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

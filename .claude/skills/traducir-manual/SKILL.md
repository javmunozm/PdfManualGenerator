---
name: traducir-manual
description: Traduce al inglés el .md de un manual técnico (programación, ingeniería, física, matemática) por capítulos y verifica que no se perdió nada. No se usa con Manual_Curso_IA_Python_v2.
argument-hint: <nombre>
effort: medium
allowed-tools:
  - Bash(python tools/costo.py *)
  - Bash(python tools/capitulos.py *)
  - Bash(python tools/comparar_traduccion.py *)
  - Bash(python tools/validar.py *)
  - PowerShell(python tools/costo.py *)
  - PowerShell(python tools/capitulos.py *)
  - PowerShell(python tools/comparar_traduccion.py *)
  - PowerShell(python tools/validar.py *)
---

# Traducir `$ARGUMENTS` al inglés

Si `$ARGUMENTS` es `Manual_Curso_IA_Python_v2`, no traducir: ese manual queda en español.

Traducir es la etapa más cara: todo el documento sale como texto nuevo. Por eso se hace
por partes, en subagentes, y se verifica con un script en vez de releer.

## Pasos

1. `python tools/costo.py $ARGUMENTS`: mirar el tamaño. Avisar al usuario el costo
   aproximado antes de empezar si pasa de ~40.000 tokens. Si el usuario ya pidió el
   proceso completo, avisar y seguir; si solo pidió extraer o regenerar, preguntar.
   Antes de partir: `validar.py` sin errores (un NUL impide guardar la parte).
2. `python tools/capitulos.py partir documentos/$ARGUMENTS/$ARGUMENTS.md`
3. Por cada archivo de `documentos/$ARGUMENTS/partes/`, lanzar el subagente `traductor`
   con la ruta de esa parte. Hasta 3 en paralelo, reponiendo una por cada una que
   termina. No leer las partes aquí, con estas dos salvedades:
   - **Partes de menos de ~300 tokens** (portadillas, checklists): traducirlas aquí con
     `Edit`. Cada subagente cuesta unos 7.000 tokens de arranque aunque la parte tenga
     40; en un manual de 87.000 tokens ese arranque fue el 40% del gasto de traducir.
     Con `--tanda 10000` en el paso 2 salen la mitad de las partes.
   - **Glosario**: traducir primero la parte del capítulo 1, mirar con `grep` cómo quedó
     el término propio del manual (el que no tiene traducción obvia) y pasar a las
     demás partes una línea de glosario después de la ruta. Sin eso, 28 traductores
     independientes eligen términos distintos.
   No responder a cada aviso de término con un resumen: solo lanzar la siguiente.
4. `python tools/capitulos.py unir documentos/$ARGUMENTS/$ARGUMENTS.md`
   (el español queda en `$ARGUMENTS.anterior.md`).
5. `python tools/comparar_traduccion.py documentos/$ARGUMENTS/$ARGUMENTS.anterior.md documentos/$ARGUMENTS/$ARGUMENTS.md`
   - Cada diferencia nombra qué cambió (un bloque de código, una cifra, una tabla).
     Corregir solo eso con `Edit` puntual y repetir hasta `RESULTADO: CORRECTO`.
   - Aviso de tamaño (menos de 65%): una parte se resumió. Volver a traducir esa parte.
   - «código en línea: faltan/sobran»: el traductor tradujo marcadores como `<usuario>`.
     Devolverlos al original con un script de reemplazos exactos por línea.
   - Si `fecha` de la cabecera tiene un mes escrito («Octubre 2026»), traducirlo a mano.
6. `python tools/validar.py documentos/$ARGUMENTS/$ARGUMENTS.md`
7. Cuando el PDF esté verificado, borrar `documentos/$ARGUMENTS/partes/`.

## Qué no se traduce (lo comprueba el paso 5)

Bloques de código y código en línea, comandos, nombres de archivo, rutas de imágenes,
URL, fórmulas, cifras, claves de la cabecera, marcas `[!NOTA]`, `\salto` y comentarios
`<!-- -->`. Sí se traducen: títulos, texto, celdas, pies de figura, títulos de cuadros y
los valores `titulo` y `subtitulo` de la cabecera.

## Presupuesto

- La conversación principal nunca ve el texto del manual: solo rutas y resultados.
- No "revisar la calidad" releyendo todo: muestrear una parte si el usuario lo pide.

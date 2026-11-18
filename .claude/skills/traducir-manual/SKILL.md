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
   Traducir no se omite por costo: un manual de ~108.000 tokens costó ~445.000 tokens de
   subagente (Sonnet) y unos minutos (`docs/auditoria.md`, 14.3).
   Antes de partir: `validar.py` con 0 errores y 0 avisos (los avisos de conversión se
   corrigen en español, una sola vez) y el PDF en español verificado contra el original
   (skill `regenerar-manual`, pasos 3 y 4).
2. `python tools/capitulos.py partir documentos/$ARGUMENTS/$ARGUMENTS.md`
   (los capítulos chicos seguidos van juntos en una parte, hasta llenar la tanda).
3. Por cada archivo de `documentos/$ARGUMENTS/partes/`, lanzar el subagente `traductor`
   con la ruta de esa parte. Hasta 3 en paralelo, reponiendo una por cada una que
   termina. No leer las partes aquí, con estas dos salvedades:
   - **Partes de menos de ~1.000 tokens** (portadillas, checklists, una sección corta):
     traducirlas aquí, con `Edit` o con un script de reemplazos exactos por renglón.
     Un subagente cuesta unos 30.000 tokens por parte aunque la parte sea chica.
     Usar `--tanda 10000` en el paso 2: salen la mitad de las partes.
   - **Glosario**, en la misma línea del encargo, después de la ruta, y **desde la primera
     parte**. Si ya hay un manual de la misma serie traducido en `documentos/`, sacarlo de
     ahí con `grep` (títulos de partes y capítulos, términos propios, títulos de cuadros):
     así los manuales de la serie dicen lo mismo. Si no lo hay, traducir primero la parte
     del capítulo 1, mirar cómo quedaron los términos sin traducción obvia y pasarlos a
     las demás. Sin glosario, cada traductor elige términos distintos. Incluir el estilo
     de los títulos (mayúscula solo en la primera palabra).
   No responder a cada aviso de término con un resumen: solo lanzar la siguiente.
4. `python tools/capitulos.py unir documentos/$ARGUMENTS/$ARGUMENTS.md`
   (el español queda en `$ARGUMENTS.anterior.md`).
5. `python tools/comparar_traduccion.py documentos/$ARGUMENTS/$ARGUMENTS.anterior.md documentos/$ARGUMENTS/$ARGUMENTS.md`
   - Cada diferencia nombra qué cambió (un bloque de código, una cifra, una tabla).
     Corregir solo eso con `Edit` puntual y repetir hasta `RESULTADO: CORRECTO`.
   - Aviso de tamaño (menos de 65%): una parte se resumió. Volver a traducir esa parte.
   - «código en línea: faltan/sobran»: el traductor tradujo marcadores como `<usuario>`.
     Devolverlos al original con un script de reemplazos exactos por línea.
   - Si `fecha` de la cabecera quedó con el mes en español («Octubre 2026»), traducirlo.
   - Títulos de bloques de código que son frases (```` ```Raíz del proyecto ````): el
     traductor los traduce; `comparar_traduccion.py` no los compara. Comprobar que no
     quedó ninguno en español: `grep -n '^```.*[áéíóúñ]' <md>`.
   - «cabecera: la traducción debe declarar `idioma: en`»: agregar esa línea a la cabecera.
6. `python tools/validar.py documentos/$ARGUMENTS/$ARGUMENTS.md`: 0 errores y 0 avisos.
   Una corrección de estructura que aparezca aquí se hace en los dos archivos (el `.md`
   y `$ARGUMENTS.anterior.md`), para que el paso 5 siga dando correcto.
7. Cuando el PDF esté verificado, borrar `documentos/$ARGUMENTS/partes/`.

## Qué no se traduce (lo comprueba el paso 5)
El código (en bloques y en línea), comandos, archivos, claves, URL, fórmulas, cifras, la
cabecera salvo `titulo`/`subtitulo`, `[!NOTA]`, `\salto` y los `<!-- -->` del `.md`. Dentro
de los bloques sí se traduce lo que no es código (comentarios, árboles, mensajes y textos
de la interfaz); `comparar_traduccion.py` exige el mismo código renglón por renglón, y el
párrafo o la tabla que cita un mensaje debe decir lo mismo que el código.

## Presupuesto

- La conversación principal nunca ve el texto del manual: solo rutas y resultados.
- No "revisar la calidad" releyendo todo: muestrear una parte si el usuario lo pide.

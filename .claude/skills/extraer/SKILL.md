---
name: extraer
description: Extrae un archivo de sources/ a Markdown completo en extracted/. Solo la invoca el usuario; invocarla autoriza el uso de ese archivo y de ningún otro.
argument-hint: <archivo de sources/>
disable-model-invocation: true
effort: medium
---

# Extraer `$ARGUMENTS`

El usuario autorizó **solo** `sources/$ARGUMENTS`. No listar la carpeta ni abrir otros
archivos de `sources/`. Si el archivo no existe, decirlo y parar.

## Pasos

1. `python tools/extraer.py "sources/$ARGUMENTS"`
   - Código 0: sin pendientes. Código 1: extraído, con los pendientes que lista la línea
     «Pendientes:». Código 2: no se extrajo (el mensaje dice por qué).
   - "Sin cambios": ya está extraído; seguir con lo que hay.
   - "No se extrajo: ... editado a mano": hay trabajo manual. No usar `--forzar` sin preguntar.
2. Leer **solo** `extracted/<nombre>/reporte.md`.
3. `python tools/costo.py <nombre>` para saber el tamaño y cuánto requiere visión.
4. Resolver los pendientes del reporte (tabla del paso 3 de `docs/extractor.md`):
   - Figuras, gráficos y páginas escaneadas: subagente `describir-figuras`, con la ruta
     del `.md` y la lista de imágenes, en tandas de hasta 8.
   - Tabla sin reconstruir: abrir solo su recorte de `assets/`.
   - "Faltan en ...": ubicar ese texto con un script sobre el original y agregarlo.
   - "Renglones de código reunidos: N": revisar **todos** con la lista del final del
     reporte (no una muestra). Si lo unido es otra instrucción (otra variable, otra
     sentencia, texto detrás de un comentario), separarlo en el `.md` con su sangría.
   - "Renglones de código que podrían estar partidos y no se unieron: N": quedaron como
     en el original. Leer la lista; unir a mano solo los que continúan la misma
     instrucción (un texto o un comando cortado a la mitad). Si ninguno, no hacer nada.
     Señal de un corte por ancho: el primero termina a media palabra (`cancellationTo` /
     `ken);`, `API.csp` / `roj`) o a media frase de un comentario, y el segundo trae una
     sangría fija mayor que la del primero (4 espacios más) en todos los casos. Ubicarlos
     con un script que muestre el largo del primero y la sangría de ambos, y unirlos por
     número de línea; a media palabra se unen sin espacio.
   - "Diagramas con texto" (`assets/p<N>-diagrama<M>.png`): cajas y flechas cuyos rótulos
     quedaron como texto suelto. Pasarlos a `describir-figuras` igual que las figuras: los
     deja como tabla de componentes y tabla de conexiones.
   - "Símbolos sin mapa de caracteres": quedan como `[SIMBOLO?]` en el `.md`.
     Reemplazarlos aquí por el símbolo que se ve en el original (una casilla es `[ ]`);
     `validar.py` no deja generar mientras quede alguno.
   - "Guiones conservados": la palabra unida no aparece en otra parte del documento.
     Si era un corte de renglón (`docu-mentación`), quitar el guion; si es un guion
     real (`físico-químico`), dejarlo.
   - "Superíndices o subíndices sin carácter propio": quedaron en línea (`xcrit`).
     Revisar que no cambie el sentido; si cambia, escribirlo de otra forma (`x (crit)`).
   - Diagrama o recuadro de texto que el extractor no marcó y quedó aplanado (rótulos en
     negrita solos, sin frases; un flujo con flechas `──►` metido en una celda):
     `python tools/region.py "sources/<archivo>" <página> imagen "<desde>" "<hasta>" extracted/<nombre>/assets/p<N>-diagrama.png`
     y pasar ese recorte a `describir-figuras`. Si es texto en letra de código, usar el
     modo `texto` (da la columna de cada renglón) y rehacerlo como bloque de código.
5. Comprobar que no queda nada:
   `grep -n "describir\|TRANSCRIBIR\|SIMBOLO?\|^Enlaces:" extracted/<nombre>/<nombre>.md`
6. Mirar la estructura, que la cobertura no ve (100% de palabras no es una extracción
   correcta): en `reporte.md`, «Títulos detectados» contra «Marcadores del PDF»; en el
   `.md`, `grep -c "^# "`, `"^## "` y `"^### "`. Si todos los títulos están en un nivel, o
   el índice del original quedó en el cuerpo (renglones con `. . . .`), decirlo en el
   informe: se corrige al regenerar (`validar.py` lo avisa en `documentos/`).
7. Informar en 6 líneas o menos: páginas, cobertura, pendientes resueltos, qué quedó.

## Presupuesto

- Nunca leer el original ni renderizar sus páginas: el texto ya está en el `.md`.
- No leer el `.md` completo si pasa de ~6.000 tokens: mapa con `grep -n "^#"` y luego
  rangos de líneas.
- Ninguna imagen se abre en esta conversación: van al subagente.
- No imprimir el `.md` en la terminal.

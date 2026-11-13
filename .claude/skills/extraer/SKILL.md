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
   - "Sin cambios": ya está extraído; seguir con lo que hay.
   - "No se extrajo": hay trabajo manual. No usar `--forzar` sin preguntar.
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
   - "Símbolos sin mapa de caracteres": son NUL en el `.md`. Reemplazarlos aquí por el
     símbolo que se ve en el original (una casilla es `[ ]`); con NUL el subagente
     `traductor` no puede guardar esa parte.
   - Diagrama que quedó como texto suelto (rótulos en negrita solos, sin frases):
     renderizar **solo esa región** a `assets/` y pasarla a `describir-figuras` para que
     lo deje como tabla de componentes y tabla de conexiones.
5. Comprobar que no queda nada:
   `grep -n "describir\|TRANSCRIBIR\|^Enlaces:" extracted/<nombre>/<nombre>.md`
6. Informar en 6 líneas o menos: páginas, cobertura, pendientes resueltos, qué quedó.

## Presupuesto

- Nunca leer el original ni renderizar sus páginas: el texto ya está en el `.md`.
- No leer el `.md` completo si pasa de ~6.000 tokens: mapa con `grep -n "^#"` y luego
  rangos de líneas.
- Ninguna imagen se abre en esta conversación: van al subagente.
- No imprimir el `.md` en la terminal.

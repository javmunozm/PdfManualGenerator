# Guía para continuar (estado al 17/11/2026)

Lo hecho está en `docs/registro.md` (qué, con qué scripts, qué quedó dudoso) y en
`docs/auditoria.md`, sección 14.5.

## Hecho el 17/11/2026
- Manual 2: PDF regenerado y verificado.
- Pruebas: 134, todas OK (avisos de conversión, `region.py`, diagramas, recuadros pegados,
  coherencia de opciones citadas).
- Guías y skills al día; `CLAUDE.md`: regla 8 (validar 0/0 obligatorio en todo documento)
  y regla 10 (trabajo sobre temporales, índice en `docs/registro.md`).
- Manual 4: rótulos de código, código en línea partido, títulos de bloque, celdas git.
- Manual 1: rehecho y traducido al inglés.
- Los cuatro documentos: `estado.py` sin pendientes.

## Decisiones del usuario
- `rotulos_codigo.py` y `region.py` no van en `allowed-tools` de ninguna skill ni
  `region.py` en los comandos de `CLAUDE.md`.
- La fuente no se toca: el original de `sources/` del manual 1 no se consultó
  (permiso denegado) y `extracted/` solo se lee.

## Pendiente
1. **Extractor (auditoría 14.2):** E20 (títulos y niveles desde los marcadores), E21 (índice
   con puntos guía de a uno), E22 (código cortado por ancho con +4 de sangría), E23 (última
   fila fuera de la tabla; identificador partido en una celda), y la parte de E24 que falta
   (recuadro con letra de código y flechas que sale como tabla de una celda). En los
   manuales 1 y 2 se corrigieron a mano; el manual 3 los va a traer.
2. **Manual 1, dudoso:** el diagrama 3.1 y la disposición del flujo 8.1 se tomaron del
   manual 2 (mismas palabras). Confirmarlos contra el original solo si el usuario lo autoriza.
3. **Git:** nada confirmado. Hacer commit solo cuando el usuario lo pida.

## Cuidados
- Scripts con Write a un archivo; nunca heredoc ni `python -c` para tocar un `.md`.
- Tras traducir, toda corrección de estructura va en el `.md` y en el `.anterior.md`.
- Ejecutar desde la raíz del proyecto.

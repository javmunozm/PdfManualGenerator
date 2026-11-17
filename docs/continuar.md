# Guía para continuar (estado al 17/11/2026)

Lo hecho está en `docs/registro.md` (qué, con qué scripts, qué quedó dudoso) y en
`docs/auditoria.md`, sección 14.5.

## Hecho el 17/11/2026
- Manual 2: PDF regenerado y verificado.
- Pruebas: 143, todas OK (avisos de conversión, `region.py`, diagramas, recuadros pegados,
  coherencia de opciones citadas, extractor E20 a E24).
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
1. **Extractor:** E20 a E24 resueltos (auditoría 14.6), probados con PDF propios y con los
   PDF generados, no con los originales de la serie. Con el manual 3 se verá si alcanzan.
   Quedan: los cortes de código tras una coma (lista de dudosos) y N17 (párrafo pegado a
   la línea de cierre de una tabla).
2. **Manual 1, dudoso:** el diagrama 3.1 y la disposición del flujo 8.1 se tomaron del
   manual 2 (mismas palabras). Confirmarlos contra el original solo si el usuario lo autoriza.
3. **Git:** todo está en `main` y en GitHub (`79fea4f` manuales y verificación,
   `8f9634b` extractor E20 a E24). No hay otras ramas.

## Cuidados
- Scripts con Write a un archivo; nunca heredoc ni `python -c` para tocar un `.md`.
- Tras traducir, toda corrección de estructura va en el `.md` y en el `.anterior.md`.
- Ejecutar desde la raíz del proyecto.

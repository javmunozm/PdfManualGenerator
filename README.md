# Plantilla de manual en PDF

Extrae información de documentos (PDF, Word, PowerPoint, Excel, JSON, CSV, Markdown) y
genera manuales PDF con portada, índice, encabezados, pie "Página X de Y", marcadores y
estilos uniformes.

## Flujo

```
sources/  --tools/extraer.py-->  extracted/  --preparar-->  documentos/  --manual.py-->  output/
```

| Guía | Para qué |
|---|---|
| [docs/extractor.md](docs/extractor.md) | Extraer el 100% de la información con pocos tokens. |
| [docs/generator.md](docs/generator.md) | Crear, regenerar o actualizar un documento. |

## Uso rápido

```
pip install reportlab pillow pymupdf python-docx python-pptx openpyxl

python tools/extraer.py sources/archivo.pdf          # -> extracted/archivo/
python manual.py documentos/x/x.md -o output/x.pdf   # genera el PDF
python tools/comparar.py sources/archivo.pdf output/x.pdf   # verifica cobertura
```

Para un manual nuevo, copia `ejemplo.md` y reemplaza el contenido. `ejemplo.pdf`
explica toda la sintaxis.

## Archivos

| Ruta | Contenido |
|---|---|
| `manual.py` | Generador de PDF (no hace falta editarlo). |
| `tools/extraer.py` | Extractor multiformato a Markdown + reporte de cobertura. |
| `tools/comparar.py` | Compara origen y PDF generado (páginas, marcadores, palabras faltantes). |
| `ejemplo.md` / `ejemplo.pdf` | Ejemplo y guía de sintaxis. |
| `sources/` | Originales (no se modifican). Contiene `ejemplo.pdf` como demostración. |
| `extracted/` | Resultados de extracción. Contiene la extracción de demostración. |
| `documentos/` | Fuentes `.md` listas para generar. |
| `output/` | PDFs generados. Contiene `ejemplo_regenerado.pdf` (prueba de ida y vuelta). |
| `imagenes/` | Imágenes del ejemplo. |

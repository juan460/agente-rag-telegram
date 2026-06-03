import os
from ingest import ingest

# Ruta de la carpeta docs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
carpeta = os.path.join(BASE_DIR, "data", "docs")

archivos = os.listdir(carpeta)
pdfs = [os.path.join(carpeta, archivo) for archivo in archivos if archivo.endswith(".pdf")]

print(f"PDFs encontrados: {len(pdfs)}")
for pdf in pdfs:
    print(f"\nCargando: {pdf}")
    ingest(pdf)

print("\n✅ Todos los PDFs cargados.")
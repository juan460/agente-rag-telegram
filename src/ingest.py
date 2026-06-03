"""
Flujo:
  1. extract_pages  — extrae texto por página con PyMuPDF
  2. chunk_pages    — fragmenta preservando solapamiento semántico
  3. ingest         — orquesta embeddings + upsert en lotes
"""

import os
import uuid
import hashlib

import fitz 
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

import config


# ─────────────────────────────────────────────────────────────
# 1. EXTRACCIÓN
# ─────────────────────────────────────────────────────────────

def extract_pages(pdf_path: str) -> list[dict]:
    """
    Abre el PDF y extrae el texto de cada página.
    Retorna: [{"page": 1, "text": "..."}, ...]
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")
    doc = fitz.open(pdf_path)
    return [{"page": i + 1, "text": page.get_text()} for i, page in enumerate(doc)]


def pdf_hash(pdf_path: str) -> str:
    """
    Genera un SHA-256 del archivo binario.
    Útil como identificador estable del documento.
    """
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────
# 2. CHUNKING
# ─────────────────────────────────────────────────────────────

def chunk_pages(pages: list[dict]) -> list[dict]:
    """
    Divide cada página en fragmentos de tamaño controlado.

    El solapamiento (chunk_overlap) preserva contexto entre chunks
    consecutivos, evitando que una idea quede truncada en el borde.
    Retorna: [{"page": 1, "chunk_index": 0, "content": "..."}, ...]
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = []
    for page in pages:
        for idx, text in enumerate(splitter.split_text(page["text"])):
            chunks.append({
                "page":        page["page"],
                "chunk_index": idx,
                "content":     text,
            })
    return chunks


# ─────────────────────────────────────────────────────────────
# 3. QDRANT — COLECCIÓN
# ─────────────────────────────────────────────────────────────

def ensure_collection(client: QdrantClient, name: str) -> None:
    """Crea la colección si no existe. No hace nada si ya está creada."""
    if not client.collection_exists(name):
        print(f"  → Creando colección '{name}'...")
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=config.VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )


# ─────────────────────────────────────────────────────────────
# 4. PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────

def ingest(pdf_path: str, collection: str = config.COLLECTION_NAME, batch_size: int = 50) -> None:
    """
    Pipeline completo de ingesta para un único PDF.

    El upsert en lotes (batch_size) evita timeouts y exceso de memoria
    en documentos grandes. uuid.NAMESPACE_URL genera IDs determinísticos
    y semánticamente correctos para contenido no-DNS.
    """
    filename = os.path.basename(pdf_path)
    doc_hash = pdf_hash(pdf_path)
    print(f"\n[INGEST] {filename}  (hash: {doc_hash[:12]}...)")

    candidate_name = filename.replace(".pdf", "")

    # Paso 1 — Extracción
    pages  = extract_pages(pdf_path)
    print(f"  → {len(pages)} páginas extraídas")

    # Paso 2 — Chunking semántico
    chunks = chunk_pages(pages)
    print(f"  → {len(chunks)} chunks generados")

    # Paso 3 — Conexión y colección
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    ensure_collection(client, collection)

    # Paso 4 — Embeddings → PointStruct
    # El prefijo "search_document:" es el prompt instructivo de nomic-embed-text
    print(f"  → Generando embeddings con '{config.EMBED_MODEL}'...")
    points = []
    for chunk in chunks:
        resp = ollama.embeddings(
            model=config.EMBED_MODEL,
            prompt=f"search_document: {chunk['content']}"
        )
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, filename + chunk["content"]))
        points.append(PointStruct(
            id=point_id,
            vector=resp["embedding"],
            payload={
                "candidate":     candidate_name,
                "source":        filename,
                "document_hash": doc_hash,
                "page":          chunk["page"],
                "chunk_index":   chunk["chunk_index"],
                "content":       chunk["content"],
            }
        ))

    # Paso 5 — Upsert en lotes
    for start in range(0, len(points), batch_size):
        batch = points[start: start + batch_size]
        client.upsert(collection_name=collection, points=batch)
        print(f"  → Subidos puntos {start + 1}–{start + len(batch)}")

    print(f"[INGEST] ✓ {len(points)} puntos indexados en '{collection}'\n")


# ─────────────────────────────────────────────────────────────
# HEALTH CHECKS Y PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

def health_checks() -> None:
    """Verifica que Qdrant y Ollama respondan antes de arrancar."""
    print("[CHECK] Qdrant... ", end="", flush=True)
    QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT, timeout=2).get_collections()
    print("OK")

    print("[CHECK] Ollama...  ", end="", flush=True)
    ollama.list()
    print("OK\n")


if __name__ == "__main__":
    PDF_PATH = "./data/docs/programa-gobierno-2026-2030.pdf"

    try:
        health_checks()
        ingest(pdf_path=PDF_PATH)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("Asegúrate de que Docker y Ollama estén corriendo.")
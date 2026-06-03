"""
Flujo:
  1. retrieve  — embed query + búsqueda Qdrant + reranking híbrido + filtro
  2. generate  — construye prompt con contexto e invoca el LLM
  3. ask       — orquesta ambas fases y devuelve la respuesta final
"""

import re
import time

import ollama
from qdrant_client import QdrantClient

import config


# ─────────────────────────────────────────────────────────────
# 1. RETRIEVAL
# ─────────────────────────────────────────────────────────────

def embed_query(query: str) -> list[float]:
    """
    Vectoriza la pregunta con el prefijo instructivo correcto.
    nomic-embed-text distingue entre "search_query" (consulta)
    y "search_document" (ingesta) para mejorar la similitud.
    """
    resp = ollama.embeddings(model=config.EMBED_MODEL, prompt=f"search_query: {query}")
    return resp["embedding"]


def search_qdrant(vector: list[float], collection: str) -> list:
    """Búsqueda semántica: devuelve los N hits más similares de Qdrant."""
    client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
    result = client.query_points(
        collection_name=collection,
        query=vector,
        limit=config.RETRIEVAL_LIMIT
    )
    return result.points


def hybrid_rerank(hits: list, query: str) -> list[dict]:
    """
    Reranking híbrido = score semántico (Qdrant) + bonus lexical.

    El bonus premia chunks que contienen los mismos términos de la pregunta,
    compensando casos donde la similitud semántica no captura palabras clave exactas.
    El filtro por SCORE_THRESHOLD se aplica aquí, antes de cualquier salida.
    """
    terms = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 3]

    scored = []
    for hit in hits:
        content = hit.payload.get("content", "")
        bonus   = sum(config.LEXICAL_BONUS for t in terms if t in content.lower())
        scored.append({
            "source":     hit.payload.get("source", "?"),
            "page":       hit.payload.get("page"),
            "content":    content,
            "similarity": hit.score + bonus,
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return [c for c in scored if c["similarity"] >= config.SCORE_THRESHOLD]


def retrieve(query: str, collection: str = config.COLLECTION_NAME) -> list[dict]:
    """
    Orquesta el proceso completo de recuperación:
      embed → search → rerank → filter
    Devuelve los chunks relevantes listos para el generador.
    """
    t0     = time.perf_counter()
    vector = embed_query(query)
    hits   = search_qdrant(vector, collection)
    chunks = hybrid_rerank(hits, query)
    print(f"[RETRIEVAL] {len(chunks)} chunks relevantes  ({time.perf_counter() - t0:.2f}s)")
    return chunks


# ─────────────────────────────────────────────────────────────
# 2. GENERATION
# ─────────────────────────────────────────────────────────────

def build_context(chunks: list[dict]) -> str:
    """
    Ensambla los chunks recuperados en un bloque de texto estructurado.
    La fuente y página dan trazabilidad al LLM sobre el origen del contexto.
    """
    lines = []
    for i, c in enumerate(chunks, 1):
        lines.append(f"--- Fragmento {i} (fuente: {c['source']}, p.{c['page']}) ---")
        lines.append(c["content"])
    return "\n".join(lines)


def generate(query: str, chunks: list[dict]) -> str:
    """
    Construye el prompt RAG e invoca el LLM.
    El prompt es dinámico: detecta automáticamente los documentos disponibles.
    """
    # Detecta los nombres de los documentos desde los chunks
    sources = list(set(c["source"].replace(".pdf", "") for c in chunks))
    sources_text = ", ".join(sources)

    system = (
        f"Eres un asistente experto en programas de gobierno colombianos. "
        f"Tienes acceso a los siguientes documentos: {sources_text}. "
        "Responde en español basándote en el contexto recuperado. "
        "Responde utilizando principalmente la información que responda directamente la pregunta. "
        "Puedes complementar con información relacionada solo si ayuda a comprender la respuesta principal. "
        "Solo di que no encontraste información si el contexto es completamente irrelevante. "
    )

    user = (
        f"Contexto recuperado:\n{build_context(chunks)}\n\n"
        f"Pregunta: {query}\n\nRespuesta:"
    )

    t0 = time.perf_counter()
    resp = ollama.chat(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ]
    )
    print(f"[GENERATION] LLM respondió en {time.perf_counter() - t0:.2f}s")
    return resp["message"]["content"]

# ─────────────────────────────────────────────────────────────
# 3. PIPELINE COMPLETO
# ─────────────────────────────────────────────────────────────

def ask(query: str, collection: str = config.COLLECTION_NAME) -> str:
    """
    Función principal del sistema RAG.
    Recibe una pregunta y devuelve la respuesta generada.
    """
    chunks = retrieve(query, collection)
    if not chunks:
        return "No se encontraron fragmentos relevantes para esa pregunta."
    for i, c in enumerate(chunks, 1):
        print(f"\n--- Chunk (página {c['page']}) ---")
        print(f"Score: {c['similarity']}")
        print(c['content'])

    return generate(query, chunks)


# ─────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pregunta = "¿Cuál es la propuesta de Cepeda respecto a la salud?"

    print(f"Pregunta: {pregunta}\n")
    respuesta = ask(pregunta)
    print("\n" + "=" * 60)
    print(respuesta)
    print("=" * 60)
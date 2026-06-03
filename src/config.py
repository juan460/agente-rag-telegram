# Configuración general del agente RAG
# Modelos: llama3.2:3b (LLM) + nomic-embed-text (embeddings)
# Base de datos vectorial: Qdrant
# ── Base de datos vectorial ──────────────────────────────────
QDRANT_HOST     = "localhost"
QDRANT_PORT     = 6333
COLLECTION_NAME = "rag_collection"
VECTOR_SIZE     = 768         

# ── Modelos Ollama ───────────────────────────────────────────
EMBED_MODEL     = "nomic-embed-text"
LLM_MODEL       = "llama3.2:3b"  

# ── Chunking ─────────────────────────────────────────────────
CHUNK_SIZE      = 1200
CHUNK_OVERLAP   = 300

# ── Recuperación ─────────────────────────────────────────────
RETRIEVAL_LIMIT = 6       
SCORE_THRESHOLD = 0.30   
LEXICAL_BONUS   = 0.03   
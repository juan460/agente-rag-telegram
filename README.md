# Agente RAG - Planes de Gobierno 2026-2030

Bot de Telegram basado en arquitectura RAG (Retrieval-Augmented Generation) 
que responde preguntas sobre documentos de programas de gobierno colombianos.

## ¿Qué es RAG?
RAG (Retrieval-Augmented Generation) es una arquitectura que combina:
1. **Recuperación**: busca fragmentos relevantes en una base de datos vectorial
2. **Generación**: usa un LLM para generar una respuesta basada en ese contexto

Esto permite que el modelo responda con información real de los documentos 
sin alucinar ni inventar datos.

## Arquitectura del proyecto

```
Usuario → Telegram → Bot Python → Qdrant (búsqueda vectorial)
                               → Ollama (embeddings + LLM)
                               → Respuesta → Telegram → Usuario
```

## Tecnologías usadas

- **Docker** — contenedores para Qdrant y Ollama
- **Qdrant** — base de datos vectorial con interfaz gráfica
- **Ollama** — modelos de IA locales (llama3.2:3b + nomic-embed-text)
- **python-telegram-bot** — bot de Telegram
- **ngrok** — túnel HTTPS para el webhook de Telegram
- **PyMuPDF** — extracción de texto de PDFs
- **LangChain** — chunking de documentos

## Modelos utilizados

- **LLM**: `llama3.2:3b` — modelo cuantizado de 2GB, responde preguntas
- **Embeddings**: `nomic-embed-text` — convierte texto en vectores de 768 dimensiones

## Estructura del proyecto

```
agente-rag-telegram/
├── docker-compose.yml   # Servicios Docker (Qdrant + Ollama)
├── .gitignore
├── README.md
├── requirements.txt     # Dependencias Python
├── data/
│   └── docs/            # PDFs cargados al sistema
└── src/
    ├── bot.py           # Bot de Telegram
    ├── config.py        # Configuración general
    ├── rag.py           # Lógica RAG (recuperación + generación)
    ├── ingest.py        # Carga un PDF a Qdrant
    └── ingest_all.py    # Carga todos los PDFs de data/docs
```

## Requisitos previos

- Docker Desktop instalado
- Python 3.11 o superior
- Cuenta en ngrok (gratuita)
- Bot de Telegram creado con @BotFather

## Instalación paso a paso

### 1. Clonar el repositorio
```bash
git clone https://github.com/juan460/agente-rag-telegram.git
cd agente-rag-telegram
```

### 2. Crear entorno virtual
```bash
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crea un archivo `.env` con:
```env
TELEGRAM_TOKEN=tu_token_de_botfather
WEBHOOK_URL=https://tu-url.ngrok-free.app
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3.2:3b
EMBED_MODEL=nomic-embed-text
QDRANT_HOST=localhost
QDRANT_PORT=6333
COLLECTION_NAME=rag_collection
```

### 5. Levantar Docker
```bash
docker compose up -d
```

### 6. Descargar modelos en Ollama
```bash
docker exec -it ollama ollama pull llama3.2:3b
docker exec -it ollama ollama pull nomic-embed-text
```

### 7. Cargar documentos a Qdrant
Coloca tus PDFs en `data/docs/` y ejecuta:
```bash
python src/ingest_all.py
```

### 8. Iniciar ngrok
```bash
.\ngrok.exe http 8444
# Copia la URL y pégala en WEBHOOK_URL del .env
```

### 9. Iniciar el bot
```bash
python src/bot.py
```

## Uso

Abre Telegram, busca tu bot y escribe `/start`.
Luego hazle preguntas sobre los documentos cargados.

## Documentos cargados

- **programa-gobierno-2026-2030.pdf** — Plan de gobierno de Iván Cepeda Castro
- **PROPUESTAS-DEL-TIGRE.pdf** — Propuestas políticas adicionales

## Ejemplo de preguntas

- ¿Cuáles son las propuestas de salud?
- ¿Qué propone Cepeda para la educación?
- ¿Cuáles son las propuestas económicas?

## Integrantes

- Juan Stevan Castro Miranda
- Diego Alexander Aristizabal Salazar
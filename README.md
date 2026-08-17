# 🧠 RAG Studio

A modern conversational Retrieval-Augmented Generation (RAG) application built with **Streamlit, LangChain, ChromaDB, OpenAI and Google Gemini**.

The application lets you upload PDF, TXT, DOCX and CSV files, build a persistent vector knowledge base, and chat with your documents using conversational retrieval and source-aware answers.

## ✨ What changed

The original project used a heavily pinned 2024 dependency stack and an older LangChain architecture. This version simplifies and modernizes the application around a stable LangChain 0.3 stack.

Key improvements:

- Modern LangChain retrieval architecture
- No dependency on the deprecated `ConversationalRetrievalChain`
- OpenAI and Google Gemini providers
- Persistent Chroma vector stores
- Conversation-aware question rewriting
- Similarity retrieval with configurable top-k
- PDF, TXT, DOCX and CSV ingestion
- Source document display with page information when available
- Cleaner Streamlit UI
- Vector-store metadata to prevent embedding-provider mismatches
- Session-based API key handling
- Structure prepared for future multimodal / Computer Vision RAG

## 🔄 Architecture

```text
                         RAG STUDIO
                             │
              ┌──────────────┴──────────────┐
              │                             │
         DOCUMENT INGESTION              CHAT
              │                             │
       File Upload / Loaders        Question + History
              │                             │
         Text Chunking             History-aware Retriever
              │                             │
          Embeddings                    ChromaDB
              │                             │
           ChromaDB                 Relevant Chunks
                                            │
                                            ▼
                                     Stuff Documents
                                            │
                                            ▼
                                           LLM
                                            │
                                            ▼
                                  Answer + Source Docs
```

## 🧰 Tech stack

| Component | Technology |
|---|---|
| UI | Streamlit |
| Orchestration | LangChain |
| Vector database | ChromaDB |
| LLM provider 1 | OpenAI |
| LLM provider 2 | Google Gemini |
| Embeddings | OpenAI / Google |
| PDF | PyPDF |
| DOCX | docx2txt |
| CSV | LangChain CSVLoader |
| Deployment | Docker-compatible |

## 📁 Project structure

```text
RAG/
├── RAG_app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── RAG_notebook.ipynb
├── data/
│   ├── tmp/
│   └── vector_stores/
└── README.md
```

## 🚀 Local setup

### 1. Create a virtual environment

Python 3.10 or 3.11 is recommended.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure an API key

You can enter the key directly in the Streamlit sidebar, or create a `.env` file:

```env
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
```

Do **not** commit real API keys to GitHub.

### 4. Start the application

```bash
streamlit run RAG_app.py
```

Then open the local Streamlit URL, normally `http://localhost:8501`.

## 💬 How to use

1. Select **OpenAI** or **Google**.
2. Enter the API key.
3. Upload PDF/TXT/DOCX/CSV documents.
4. Give the knowledge base a name.
5. Click **Build Knowledge Base**.
6. Wait for chunking, embedding and indexing to finish.
7. Ask questions in the chat box.
8. Inspect the source cards under each answer.
9. Later, load the saved knowledge base from the sidebar without re-uploading the documents.

## 🧠 RAG workflow

### Indexing

```text
Documents
   ↓
LangChain loaders
   ↓
RecursiveCharacterTextSplitter
   ↓
Embedding model
   ↓
ChromaDB
```

### Querying

```text
Question + conversation history
              ↓
History-aware question rewriting
              ↓
Chroma similarity retrieval
              ↓
Relevant document chunks
              ↓
Stuff-document answer chain
              ↓
LLM
              ↓
Grounded answer + sources
```

## ⚠️ Important compatibility rule

A vector store must be loaded with the same embedding provider used when it was created. For example, a store created using OpenAI embeddings should be loaded with OpenAI selected in the UI. The app records this information in `rag_metadata.json` and blocks incompatible loads.

## 🔐 API key safety

Use environment variables or the Streamlit UI. Never hard-code keys in `RAG_app.py`, commit them to Git, or paste them into public files.

If a key has ever been committed to a public repository, revoke it and create a new one.

## 🔭 Next stage: Computer Vision RAG

The current architecture is intentionally suitable for a future multimodal extension:

```text
Text query ────────┐
                   ├──→ Multimodal retrieval → Chroma → Multimodal LLM
Image ─→ Vision ───┘
```

The next version can support image understanding, image-to-text retrieval, multimodal document ingestion, and image + text questions without throwing away the current RAG foundation.

import json
import os
import re
import shutil
from pathlib import Path
from typing import List

import streamlit as st
from dotenv import load_dotenv

from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.document_loaders import CSVLoader, Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TMP_DIR = DATA_DIR / "tmp"
VECTOR_DIR = DATA_DIR / "vector_stores"
TMP_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Page / theme
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="RAG Studio",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
/* DARK RAG STUDIO */

.stApp {
    background: #0b1120;
    color: #e5e7eb;
}

[data-testid="stAppViewContainer"] {
    background: #0b1120;
}

[data-testid="stHeader"] {
    background: rgba(11, 17, 32, 0.95);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #263244;
}

[data-testid="stSidebar"] * {
    color: #e5e7eb !important;
}

[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #1f2937 !important;
    color: #f9fafb !important;
    border-color: #374151 !important;
}

/* Hero */
.hero {
    padding: 1.4rem 1.5rem;
    border: 1px solid #293548;
    border-radius: 18px;
    background: linear-gradient(
        135deg,
        #111827 0%,
        #172554 100%
    );
    color: #f9fafb;
    margin-bottom: 1rem;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
}

.hero h1 {
    margin: 0;
    font-size: 2rem;
    color: #ffffff;
}

.hero p {
    margin: 0.4rem 0 0;
    color: #cbd5e1;
}

/* Metric cards */
.metric-card {
    padding: 1rem;
    border: 1px solid #293548;
    border-radius: 14px;
    background: #111827;
    color: #f9fafb;
    text-align: center;
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}

.metric-card b {
    color: #f8fafc;
}

.small-muted {
    color: #94a3b8;
    font-size: 0.85rem;
}

/* Chat */
[data-testid="stChatMessage"] {
    background: #111827;
    border: 1px solid #263244;
    border-radius: 14px;
    margin-bottom: 0.7rem;
}

[data-testid="stChatInput"] {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 14px;
}

[data-testid="stChatInput"] textarea {
    color: #f9fafb !important;
    background: #111827 !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
}

/* Inputs */
.stTextInput input,
.stNumberInput input {
    color: #f9fafb !important;
    background: #111827 !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 12px;
}

/* Expanders */
[data-testid="stExpander"] {
    background: #111827;
    border: 1px solid #293548;
    border-radius: 12px;
}

/* Source cards */
.source-card {
    padding: 0.75rem 1rem;
    border-left: 4px solid #818cf8;
    background: #111827;
    color: #e5e7eb;
    border-radius: 8px;
    margin: 0.4rem 0;
}

/* Alerts */
[data-testid="stAlert"] {
    background: #111827;
    color: #e5e7eb;
}

/* Dividers */
hr {
    border-color: #263244 !important;
}

/* Code */
code {
    color: #c4b5fd !important;
    background: #111827 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
def init_state():
    defaults = {
        "messages": [],
        "chat_history": [],
        "chain": None,
        "retriever": None,
        "vectorstore": None,
        "vectorstore_name": None,
        "last_sources": [],
        "provider": "OpenAI",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "top_k": 6,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    return value.strip("_")[:80] or "my_knowledge_base"


def get_key(provider: str) -> str:
    if provider == "OpenAI":
        return st.session_state.get("openai_key", "") or os.getenv("OPENAI_API_KEY", "")
    return st.session_state.get("google_key", "") or os.getenv("GOOGLE_API_KEY", "")


def get_llm():
    provider = st.session_state.provider
    model = st.session_state.model
    temperature = st.session_state.temperature
    key = get_key(provider)

    if not key:
        raise ValueError(f"Add your {provider} API key in the sidebar or .env file.")

    if provider == "OpenAI":
        return ChatOpenAI(model=model, temperature=temperature, api_key=key)
    return ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=key)


def get_embeddings():
    provider = st.session_state.provider
    key = get_key(provider)

    if not key:
        raise ValueError(f"Add your {provider} API key before creating/loading a vector store.")

    if provider == "OpenAI":
        return OpenAIEmbeddings(model="text-embedding-3-small", api_key=key)
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=key)


def load_file(path: Path) -> List[Document]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    if suffix == ".txt":
        return TextLoader(str(path), encoding="utf-8").load()
    if suffix == ".csv":
        return CSVLoader(str(path), encoding="utf-8").load()
    if suffix == ".docx":
        return Docx2txtLoader(str(path)).load()
    raise ValueError(f"Unsupported file type: {suffix}")


def save_uploaded_files(uploaded_files):
    for old_file in TMP_DIR.iterdir():
        if old_file.is_file():
            old_file.unlink()
    paths = []
    for uploaded in uploaded_files:
        path = TMP_DIR / uploaded.name
        path.write_bytes(uploaded.getbuffer())
        paths.append(path)
    return paths


def build_vectorstore(uploaded_files, name: str):
    paths = save_uploaded_files(uploaded_files)
    documents: List[Document] = []

    for path in paths:
        documents.extend(load_file(path))

    if not documents:
        raise ValueError("No readable content was found in the uploaded files.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=180,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    # Add stable source metadata for the UI.
    for chunk in chunks:
        source = Path(str(chunk.metadata.get("source", "unknown"))).name
        chunk.metadata["source_name"] = source

    safe_name = slugify(name)
    persist_dir = VECTOR_DIR / safe_name
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    embeddings = get_embeddings()
    vectorstore = Chroma(
        collection_name="documents",
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
    )
    vectorstore.add_documents(chunks)

    metadata = {
        "name": safe_name,
        "provider": st.session_state.provider,
        "embedding_model": "text-embedding-3-small" if st.session_state.provider == "OpenAI" else "models/gemini-embedding-001",
        "document_count": len(paths),
        "chunk_count": len(chunks),
    }
    (persist_dir / "rag_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return vectorstore, safe_name, len(paths), len(chunks)


def available_vectorstores():
    stores = []
    for directory in VECTOR_DIR.iterdir():
        if directory.is_dir() and (directory / "rag_metadata.json").exists():
            try:
                stores.append(json.loads((directory / "rag_metadata.json").read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    return sorted(stores, key=lambda item: item.get("name", ""))


def load_vectorstore(name: str):
    persist_dir = VECTOR_DIR / name
    metadata_path = persist_dir / "rag_metadata.json"
    if not persist_dir.exists() or not metadata_path.exists():
        raise ValueError("The selected vector store is incomplete or missing metadata.")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("provider") != st.session_state.provider:
        raise ValueError(
            f"This vector store was created with {metadata.get('provider')} embeddings. "
            f"Select {metadata.get('provider')} as the provider before loading it."
        )

    vectorstore = Chroma(
        collection_name="documents",
        embedding_function=get_embeddings(),
        persist_directory=str(persist_dir),
    )
    return vectorstore, metadata


def create_rag_chain(vectorstore):
    llm = get_llm()
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": st.session_state.top_k},
    )

    contextualize_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Given the chat history and the latest user question, rewrite the latest question as a standalone search query. "
                "Do not answer the question. Preserve important names, terms, dates, and constraints.",
            ),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful document-grounded assistant. Answer using the provided context whenever possible. "
                "If the answer is not supported by the context, say that the information was not found in the uploaded documents. "
                "Do not invent citations or facts. Keep answers clear and practical.\n\nCONTEXT:\n{context}",
            ),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_prompt
    )
    answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, answer_chain)
    return rag_chain, retriever


def reset_chat():
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.session_state.last_sources = []


def render_sources(sources):
    if not sources:
        return
    st.markdown("#### Sources")
    seen = set()
    for doc in sources:
        source = doc.metadata.get("source_name") or Path(str(doc.metadata.get("source", "unknown"))).name
        page = doc.metadata.get("page")
        key = (source, page)
        if key in seen:
            continue
        seen.add(key)
        page_text = f" · Page {int(page) + 1}" if isinstance(page, (int, float)) else ""
        with st.container(border=True):
            st.markdown(f"**📄 {source}**{page_text}")
            preview = doc.page_content.replace("\n", " ")
            st.caption(preview[:420] + ("…" if len(preview) > 420 else ""))

# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("# 🧠 RAG Studio")
    st.caption("Modern conversational Retrieval-Augmented Generation")
    st.divider()

    st.markdown("### 1. AI Provider")
    st.session_state.provider = st.radio("Provider", ["OpenAI", "Google"], horizontal=True)

    if st.session_state.provider == "OpenAI":
        st.session_state.openai_key = st.text_input(
            "OpenAI API key", value=os.getenv("OPENAI_API_KEY", ""), type="password"
        )
        st.session_state.model = st.selectbox(
            "Chat model", ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"], index=0
        )
    else:
        st.session_state.google_key = st.text_input(
            "Google API key", value=os.getenv("GOOGLE_API_KEY", ""), type="password"
        )
        st.session_state.model = st.selectbox(
            "Chat model", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0
        )

    st.session_state.temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1)
    st.session_state.top_k = st.slider("Retrieved chunks", 2, 12, 6, 1)

    st.divider()
    st.markdown("### 2. Knowledge Base")
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "txt", "docx", "csv"],
        accept_multiple_files=True,
        help="PDF, TXT, DOCX and CSV are supported.",
    )
    vector_name = st.text_input("Vector store name", placeholder="e.g. machine_learning_notes")

    if st.button("🚀 Build Knowledge Base", use_container_width=True, type="primary"):
        if not uploaded_files:
            st.error("Upload at least one document first.")
        elif not vector_name.strip():
            st.error("Enter a vector store name.")
        else:
            with st.spinner("Loading, chunking, embedding and indexing documents..."):
                try:
                    vs, name, doc_count, chunk_count = build_vectorstore(uploaded_files, vector_name)
                    st.session_state.vectorstore = vs
                    st.session_state.vectorstore_name = name
                    st.session_state.chain, st.session_state.retriever = create_rag_chain(vs)
                    reset_chat()
                    st.success(f"Indexed {doc_count} document(s) into {chunk_count} chunks.")
                except Exception as exc:
                    st.error(str(exc))

    stores = available_vectorstores()
    if stores:
        selected = st.selectbox("Saved vector stores", [item["name"] for item in stores])
        if st.button("📂 Load Selected Store", use_container_width=True):
            with st.spinner("Loading knowledge base..."):
                try:
                    vs, metadata = load_vectorstore(selected)
                    st.session_state.vectorstore = vs
                    st.session_state.vectorstore_name = selected
                    st.session_state.chain, st.session_state.retriever = create_rag_chain(vs)
                    reset_chat()
                    st.success(f"Loaded {metadata.get('chunk_count', 0)} chunks.")
                except Exception as exc:
                    st.error(str(exc))

    st.divider()
    if st.button("🧹 Clear Conversation", use_container_width=True):
        reset_chat()
        st.rerun()

    st.caption("API keys are used only for the current app session unless supplied through your environment.")

# -----------------------------------------------------------------------------
# Main UI
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
      <h1>🧠 RAG Studio</h1>
      <p>Upload your knowledge. Build a vector index. Ask grounded questions with conversational context.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="metric-card"><b>📚 Knowledge Base</b><br><span class="small-muted">{}</span></div>'.format(st.session_state.vectorstore_name or "Not loaded"), unsafe_allow_html=True)
with c2:
    st.markdown('<div class="metric-card"><b>⚡ Retrieval</b><br><span class="small-muted">Top {} chunks</span></div>'.format(st.session_state.top_k), unsafe_allow_html=True)
with c3:
    st.markdown('<div class="metric-card"><b>🤖 Model</b><br><span class="small-muted">{} · {}</span></div>'.format(st.session_state.provider, st.session_state.model), unsafe_allow_html=True)

st.divider()

if st.session_state.vectorstore is None:
    st.info("👈 Start by entering an API key, uploading documents, and clicking **Build Knowledge Base**. You can also load an existing vector store.")
    with st.expander("How this RAG works"):
        st.markdown(
            """
            **Ingestion:** documents → loaders → chunks → embeddings → ChromaDB\n\n
            **Query:** question + chat history → standalone query → similarity retrieval → relevant context → LLM → answer + sources
            """
        )
else:
    if not st.session_state.messages:
        st.markdown("### 💬 Chat with your data")
        st.caption("Ask questions about the documents in the active knowledge base.")
        examples = [
            "Summarize the main ideas in the documents.",
            "What are the most important concepts I should learn?",
            "Compare the key approaches discussed in the documents.",
        ]
        cols = st.columns(3)
        for i, example in enumerate(examples):
            with cols[i]:
                st.markdown(f"`{example}`")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and message.get("sources"):
                render_sources(message["sources"])

    prompt = st.chat_input("Ask something about your documents…")
    if prompt:
        if st.session_state.chain is None:
            st.error("Load or build a knowledge base first.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching your knowledge base…"):
                try:
                    result = st.session_state.chain.invoke(
                        {"input": prompt, "chat_history": st.session_state.chat_history}
                    )
                    answer = result.get("answer", "I could not generate an answer.")
                    sources = result.get("context", [])
                    st.markdown(answer)
                    render_sources(sources)

                    st.session_state.chat_history.extend(
                        [HumanMessage(content=prompt), AIMessage(content=answer)]
                    )
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer, "sources": sources}
                    )
                    st.session_state.last_sources = sources
                except Exception as exc:
                    error_text = str(exc)
                    st.error(f"RAG request failed: {error_text}")

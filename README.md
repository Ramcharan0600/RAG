# RAG Chatbot with LangChain

A Retrieval-Augmented Generation (RAG) chatbot built with Python, Streamlit, LangChain, ChromaDB, and multiple LLM providers. The app lets you upload documents, convert them into embeddings, store them in a vector database, and ask questions about your content using conversational AI.

## Overview

This project is designed to help you chat with your own data instead of relying only on a model’s general knowledge. It follows the standard RAG flow:

1. Upload local documents (.txt, .pdf, .csv, .docx)
2. Load and split them into chunks
3. Generate embeddings with the selected provider
4. Store them in a Chroma vector database
5. Retrieve the most relevant chunks for a question
6. Send the context and question to an LLM for a grounded answer
7. Keep the conversation memory for follow-up questions

The app supports:

- OpenAI models
- Google Generative AI models
- Hugging Face models
- Multiple retriever strategies:
  - vectorstore-backed retriever
  - contextual compression retriever
  - Cohere reranker (optional)

## How the project works

The application flow in this repo is:

- The user selects an LLM provider and API key in the sidebar.
- The user uploads documents in the Streamlit UI.
- Files are stored in the temporary data directory.
- LangChain loaders read the uploaded files.
- A text splitter breaks the documents into smaller chunks.
- Embeddings are created with the selected provider.
- ChromaDB creates or loads a persistent vector store.
- A retriever fetches the most relevant document chunks for each question.
- A `ConversationalRetrievalChain` combines chat memory, retrieved context, and the LLM response.
- The app displays the answer and the source documents used.

This behavior is implemented in [RAG_app.py](RAG_app.py) and the application is run through Streamlit.

## Repository structure

- [RAG_app.py](RAG_app.py) — main Streamlit chatbot application
- [requirements.txt](requirements.txt) — Python dependencies
- [docker-compose.yml](docker-compose.yml) — Docker Compose setup
- [Dockerfile](Dockerfile) — container image for the app
- [RAG_notebook.ipynb](RAG_notebook.ipynb) — notebook version of the project workflow
- [data/](data/) — uploaded files and persisted Chroma vector stores

## Prerequisites

- Python 3.10+
- A valid API key for one of the supported providers:
  - OpenAI
  - Google Generative AI
  - Hugging Face
- Optional: Cohere API key if you want the reranker retriever

## Local setup

From the project root:

```bash
python -m venv langchain_env
```

On Windows PowerShell:

```powershell
.\langchain_env\Scripts\Activate.ps1
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run RAG_app.py
```

Open the local URL shown by Streamlit in the browser.

## Using the app

1. Choose the LLM provider from the sidebar.
2. Paste the required API key.
3. Select a model and adjust temperature/top_p.
4. Choose a retriever type.
5. Upload one or more documents.
6. Create a vectorstore.
7. Ask a question about the uploaded content.
8. Review the answer along with the source documents that were retrieved.

## Docker setup

This project includes a Docker configuration for running the app in a container.

Build and run:

```bash
docker-compose up --build
```

The app is exposed on:

```text
http://localhost:8501
```

## Environment notes

- The app stores vector stores under the `data/vector_stores` folder.
- Temporary uploaded files are processed from the `data/tmp` folder.
- If you upload a new dataset, the app creates a new Chroma database for it.
- You can also reopen an existing stored vector database from the UI.

## Dependencies

The project uses libraries such as:

- LangChain
- ChromaDB
- Streamlit
- OpenAI SDK
- Google Generative AI SDK
- Hugging Face integrations
- pypdf / docx2txt / CSV loaders

See [requirements.txt](requirements.txt) for the full dependency list.

## Notes

This repo is a practical implementation of a document-based conversational assistant using retrieval augmentation. It is useful for:

- internal knowledge base assistants
- document Q&A bots
- private data chat interfaces
- prototype RAG systems for product demos and learning

## License

This project is provided as-is for educational and development use.

## Repository

https://github.com/Ramcharan0600/RAG.git

# BRANCH: feature/m1-rag-core
import os
import json
import tiktoken
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import logger centralisé
try:
    from logger import log_info, log_warn, log_error
except ImportError:
    def log_info(m): pass
    def log_warn(m): print(m)
    def log_error(m): print(m)

# Suppress ChromaDB telemetry
os.environ["CHROMA_TELEMETRY_IMPL"] = "0"

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

def get_token_count(text, model="cl100k_base"):
    enc = tiktoken.get_encoding(model)
    return len(enc.encode(text))

def split_text(text, max_tokens=512, overlap_tokens=102):
    """
    Iterative text splitting logic with overlap.
    Directly uses tokens for precise boundary management.
    """
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)

    if not tokens:
        return []

    if len(tokens) <= max_tokens:
        return [text]

    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunks.append(enc.decode(chunk_tokens))

        if end >= len(tokens):
            break

        # Standard overlap: the next chunk starts 'overlap_tokens' before the current one ends
        start = end - overlap_tokens

        # Safety: if overlap >= max_tokens, we would loop.
        # But here overlap_tokens is 20% of max_tokens.
        if start >= end: # Should not happen with 20%
            start = end

    return chunks

def index_documents(json_file, rebuild=False):
    if not os.path.exists(json_file):
        log_error(f"Error: {json_file} not found.")
        return 0

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    os.makedirs(CHROMA_PATH, exist_ok=True)
    client_chroma = chromadb.PersistentClient(path=CHROMA_PATH)

    if rebuild:
        try:
            client_chroma.delete_collection("imt_docs")
        except:
            pass

    collection = client_chroma.get_or_create_collection(name="imt_docs")

    all_chunks = []
    all_metadatas = []
    all_ids = []

    # Flexible chunking parameters via ENV
    max_tokens = int(os.getenv("RAG_CHUNK_SIZE", 512))
    overlap_ratio = float(os.getenv("RAG_CHUNK_OVERLAP_RATIO", 0.2))
    overlap_tokens = int(max_tokens * overlap_ratio)

    for doc in data:
        content = doc.get("content", "")
        url = doc.get("url", "")
        title = doc.get("title", "")

        chunks = split_text(content, max_tokens, overlap_tokens)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{url}_{i}"
            all_chunks.append(chunk)
            all_metadatas.append({"url": url, "title": title, "chunk_id": i})
            all_ids.append(chunk_id)

    if not all_chunks:
        log_warn("No chunks to index.")
        return 0

    # Gemini Embeddings
    if not GEMINI_API_KEY:
        log_error("GEMINI_API_KEY not set. Cannot index embeddings.")
        return 0

    client_genai = genai.Client(api_key=GEMINI_API_KEY)

    # Chroma can take a list of embeddings. We'll generate them in batches.
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i+batch_size]
        batch_metadatas = all_metadatas[i:i+batch_size]
        batch_ids = all_ids[i:i+batch_size]

        try:
            result = client_genai.models.embed_content(
                model="embedding-001",
                contents=batch_chunks,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            embeddings = [e.values for e in result.embeddings]

            collection.add(
                embeddings=embeddings,
                documents=batch_chunks,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
        except Exception as e:
            print(f"Error indexing batch starting at {i}: {e}")
            continue

    log_info(f"Indexed {len(all_chunks)} chunks in ChromaDB")
    return len(all_chunks)

def imt_rag_search(query: str):
    client_chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client_chroma.get_collection(name="imt_docs")

    # Gemini Embeddings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set.")
        return []

    client_genai = genai.Client(api_key=GEMINI_API_KEY)

    # Embed the query
    result = client_genai.models.embed_content(
        model="embedding-001",
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    )
    query_embedding = result.embeddings[0].values

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    formatted_results = []
    if results['documents']:
        for i in range(len(results['documents'][0])):
            formatted_results.append({
                "content": results['documents'][0][i],
                "score": 1 - results['distances'][0][i], # Approximate score
                "source": results['metadatas'][0][i]['url']
            })

    return formatted_results

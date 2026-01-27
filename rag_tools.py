# BRANCH: feature/m1-rag-core
import os
import json
import tiktoken
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

def get_token_count(text, model="cl100k_base"):
    enc = tiktoken.get_encoding(model)
    return len(enc.encode(text))

def recursive_split(text, max_tokens, overlap_tokens):
    """Recursive splitting logic with overlap."""
    if get_token_count(text) <= max_tokens:
        return [text]

    separators = ["\n\n", "\n", ". ", " ", ""]
    final_chunks = []

    # Try splitting by separators
    selected_sep = ""
    for sep in separators:
        if sep in text:
            selected_sep = sep
            break

    if selected_sep != "":
        parts = text.split(selected_sep)
        current_parts = []
        current_tokens = 0

        for part in parts:
            part_tokens = get_token_count(part)
            if current_tokens + part_tokens > max_tokens and current_parts:
                # Store current chunk
                chunk_text = selected_sep.join(current_parts)
                final_chunks.append(chunk_text)

                # Handle overlap: keep parts that fit in overlap_tokens
                new_parts = []
                new_tokens = 0
                for p in reversed(current_parts):
                    p_tok = get_token_count(p)
                    if new_tokens + p_tok <= overlap_tokens:
                        new_parts.insert(0, p)
                        new_tokens += p_tok
                    else:
                        break
                current_parts = new_parts
                current_tokens = new_tokens

            current_parts.append(part)
            current_tokens += part_tokens

        if current_parts:
            final_chunks.append(selected_sep.join(current_parts))
    else:
        # No separator found, hard cut by tokens (not ideal but fallback)
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        for i in range(0, len(tokens), max_tokens - overlap_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            final_chunks.append(enc.decode(chunk_tokens))

    # Recurse on chunks that are still too large
    resolved_chunks = []
    for chunk in final_chunks:
        if get_token_count(chunk) > max_tokens:
            resolved_chunks.extend(recursive_split(chunk, max_tokens, overlap_tokens))
        else:
            resolved_chunks.append(chunk)

    return resolved_chunks

def index_documents(json_file, rebuild=False):
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found.")
        return

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    os.makedirs(CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    if rebuild:
        try:
            client.delete_collection("imt_docs")
        except:
            pass

    collection = client.get_or_create_collection(name="imt_docs")

    all_chunks = []
    all_metadatas = []
    all_ids = []

    max_tokens = 512
    overlap_tokens = int(max_tokens * 0.2)

    for doc in data:
        content = doc.get("content", "")
        url = doc.get("url", "")
        title = doc.get("title", "")

        chunks = recursive_split(content, max_tokens, overlap_tokens)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{url}_{i}"
            all_chunks.append(chunk)
            all_metadatas.append({"url": url, "title": title, "chunk_id": i})
            all_ids.append(chunk_id)

    # Gemini Embeddings
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set. Cannot index embeddings.")
        return

    # Chroma can take a list of embeddings. We'll generate them in batches.
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i:i+batch_size]
        batch_metadatas = all_metadatas[i:i+batch_size]
        batch_ids = all_ids[i:i+batch_size]

        result = genai.embed_content(
            model="models/text-embedding-004",
            content=batch_chunks,
            task_type="retrieval_document"
        )
        embeddings = result['embedding']

        collection.add(
            embeddings=embeddings,
            documents=batch_chunks,
            metadatas=batch_metadatas,
            ids=batch_ids
        )

    print(f"Indexed {len(all_chunks)} chunks in ChromaDB")
    return len(all_chunks)

def imt_rag_search(query: str):
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(name="imt_docs")

    # Embed the query
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )
    query_embedding = result['embedding']

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    formatted_results = []
    for i in range(len(results['documents'][0])):
        formatted_results.append({
            "content": results['documents'][0][i],
            "score": 1 - results['distances'][0][i], # Approximate score
            "source": results['metadatas'][0][i]['url']
        })

    return formatted_results

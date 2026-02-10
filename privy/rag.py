#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) Module for Privy.
Uses ChromaDB for vector storage and efficient searching.
"""

import os
import sys
import hashlib
import chromadb
from chromadb.config import Settings

try:
    from . import ai
except ImportError:
    import ai

DOCS_DIR = "docs" if os.path.exists("docs") else "/usr/local/share/privy/docs"
CHROMA_PATH = os.path.expanduser("~/.local/share/privy/chroma_db")

def get_client():
    """Returns a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_collection(provider=None):
    """
    Returns (or creates) a collection for the current AI provider.
    Since different providers use different embedding models, we separate them.
    """
    client = get_client()
    prov = provider or ai.PROVIDER
    collection_name = f"privy_docs_{prov.replace('-', '_')}"
    return client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

def index_docs():
    """Scans DOCS_DIR, chunks files, generates embeddings, and saves to ChromaDB."""
    if not os.path.exists(DOCS_DIR):
        print(f"[RAG] Docs directory {DOCS_DIR} not found.")
        return

    print(f"[RAG] Indexing documentation from {DOCS_DIR} using {ai.PROVIDER} embeddings...")
    collection = get_collection()
    
    # Simple strategy: Clear and re-index for now to keep it simple
    # In a larger app, we'd check hashes to only update changed files
    
    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".md") or filename.endswith(".txt"):
            filepath = os.path.join(DOCS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                chunks = [c.strip() for c in content.split('\n\n') if c.strip()]
                
                ids = []
                vectors = []
                metadatas = []
                documents = []

                print(f"  - Processing {filename} ({len(chunks)} chunks)...")
                for i, chunk in enumerate(chunks):
                    vector = ai.get_embedding(chunk)
                    if vector:
                        chunk_id = hashlib.md5(f"{filename}_{i}".encode()).hexdigest()
                        ids.append(chunk_id)
                        vectors.append(vector)
                        metadatas.append({"source": filename, "chunk": i})
                        documents.append(chunk)

                if ids:
                    collection.upsert(
                        ids=ids,
                        embeddings=vectors,
                        metadatas=metadatas,
                        documents=documents
                    )
            except Exception as e:
                print(f"  ! Error processing {filename}: {e}")
    
    print(f"[RAG] Indexing complete.")

def search_docs(query: str, top_k: int = 3) -> str:
    """Searches ChromaDB for the most relevant document chunks."""
    try:
        query_vector = ai.get_embedding(query)
        if not query_vector:
            return ""

        collection = get_collection()
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k
        )

        context_parts = []
        # Chroma returns results in a nested list format
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                doc = results['documents'][0][i]
                meta = results['metadatas'][0][i]
                # Distance in Chroma (cosine) is 1 - similarity, so lower is better
                # But here we just take what it gives us as they are the top-K
                context_parts.append(f"--- SOURCE: {meta['source']} ---\n{doc}\n")
                
        return "\n".join(context_parts)
    except Exception as e:
        # If collection doesn't exist yet or other Chroma error
        return ""

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "index":
            index_docs()
        else:
            query_arg = " ".join(sys.argv[1:])
            print(search_docs(query_arg))
    else:
        print("Usage: python -m privy.rag [index | <query string>]")
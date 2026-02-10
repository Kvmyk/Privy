#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) Module for Privy.

This module handles searching local documentation using vector embeddings
via the local Ollama instance.
"""

import os
import sys
import json
import math
import requests
import hashlib

# Configuration
DOCS_DIR = "docs" if os.path.exists("docs") else "/usr/local/share/privy/docs"
INDEX_FILE = os.path.expanduser("~/.local/share/privy/index.json")
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_EMBED_API = "http://localhost:11434/api/embeddings"

def get_embedding(text: str) -> list:
    """Fetches the vector embedding for a given text from Ollama."""
    try:
        response = requests.post(OLLAMA_EMBED_API, json={
            "model": EMBEDDING_MODEL,
            "prompt": text
        }, timeout=10)
        if response.status_code == 200:
            return response.json().get('embedding', [])
    except Exception as e:
        print(f"[RAG] Error getting embedding: {e}", file=sys.stderr)
    return []

def cosine_similarity(v1: list, v2: list) -> float:
    """Calculates the cosine similarity between two vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude_v1 = math.sqrt(sum(a * a for a in v1))
    magnitude_v2 = math.sqrt(sum(b * b for b in v2))
    if magnitude_v1 == 0 or magnitude_v2 == 0:
        return 0.0
    return dot_product / (magnitude_v1 * magnitude_v2)

def index_docs():
    """Scans DOCS_DIR, chunks files, generates embeddings, and saves to INDEX_FILE."""
    if not os.path.exists(DOCS_DIR):
        print(f"[RAG] Docs directory {DOCS_DIR} not found.")
        return

    print(f"[RAG] Indexing documentation from {DOCS_DIR}...")
    index_data = []
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)

    for filename in os.listdir(DOCS_DIR):
        if filename.endswith(".md") or filename.endswith(".txt"):
            filepath = os.path.join(DOCS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Simple Chunking: Split by double newlines (paragraphs)
                chunks = [c.strip() for c in content.split('\n\n') if c.strip()]
                
                print(f"  - Processing {filename} ({len(chunks)} chunks)...")
                for chunk in chunks:
                    vector = get_embedding(chunk)
                    if vector:
                        index_data.append({
                            "source": filename,
                            "content": chunk,
                            "vector": vector,
                            "hash": hashlib.md5(chunk.encode()).hexdigest()
                        })
            except Exception as e:
                print(f"  ! Error processing {filename}: {e}")

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index_data, f)
    
    print(f"[RAG] Indexing complete. Saved {len(index_data)} chunks to {INDEX_FILE}.")

def search_docs(query: str, top_k: int = 3) -> str:
    """
    Searches the index for the most relevant document chunks.
    
    Args:
        query (str): The user's question.
        top_k (int): Number of chunks to return.
        
    Returns:
        str: Context string for the AI.
    """
    if not os.path.exists(INDEX_FILE):
        return "" # No index, no context

    query_vector = get_embedding(query)
    if not query_vector:
        return ""

    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    except Exception:
        return ""

    results = []
    for item in index_data:
        score = cosine_similarity(query_vector, item.get('vector', []))
        results.append((score, item))

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)

    # Build context string
    context_parts = []
    for score, item in results[:top_k]:
        # Filter low relevance matches if needed (e.g., score > 0.4)
        if score > 0.3:
            context_parts.append(f"--- SOURCE: {item['source']} (Score: {score:.2f}) ---\n{item['content']}\n")
            
    return "\n".join(context_parts)

if __name__ == "__main__":
    # CLI utility for testing/indexing
    if len(sys.argv) > 1:
        if sys.argv[1] == "index":
            index_docs()
        else:
            query_arg = " ".join(sys.argv[1:])
            print(search_docs(query_arg))
    else:
        print("Usage: python -m privy.rag [index | <query string>]")
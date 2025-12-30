#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) Module for Privy.

This module handles searching local documentation to provide context
for the AI assistant.
"""

import os
import sys

# Default documentation directory
DOCS_DIR = "/usr/local/share/privy/docs"

def search_docs(query: str) -> str:
    """
    Searches for keywords in local text/markdown files.

    Args:
        query (str): The search query string.

    Returns:
        str: A formatted string containing the content of matching documents,
             or an empty string if no matches or if the directory doesn't exist.
    """
    if not os.path.exists(DOCS_DIR):
        return ""
    
    context = []
    query_words = query.lower().split()
    
    try:
        for filename in os.listdir(DOCS_DIR):
            if filename.endswith(".md") or filename.endswith(".txt"):
                path = os.path.join(DOCS_DIR, filename)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Simple keyword match: check if ANY word from query is in content
                        if any(word in content.lower() for word in query_words):
                            context.append(f"--- DOCUMENT: {filename} ---\n{content}\n")
                except Exception as e:
                    print(f"Error reading {filename}: {e}", file=sys.stderr)
    except OSError as e:
        print(f"Error accessing docs directory: {e}", file=sys.stderr)
    
    return "\n".join(context)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("")
        sys.exit(0)
    
    query_arg = " ".join(sys.argv[1:])
    print(search_docs(query_arg))

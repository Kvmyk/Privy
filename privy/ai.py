import os
import requests
import json
from dotenv import load_dotenv

# Load configuration: local .env first, then global ~/.privy/.env (global takes precedence)
load_dotenv(override=True)
load_dotenv(os.path.expanduser("~/.privy/.env"), override=True)

def update_config(new_provider, api_key=None):
    """Updates the provider and optional API key both in memory and in the user's .env file."""
    global PROVIDER, GEMINI_API_KEY
    PROVIDER = new_provider.lower()
    if api_key:
        GEMINI_API_KEY = api_key

    config_path = os.path.expanduser("~/.privy/.env")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    lines = []
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            lines = f.readlines()
            
    # Update or add PRIVY_PROVIDER
    provider_found = False
    for i, line in enumerate(lines):
        if line.startswith("PRIVY_PROVIDER="):
            lines[i] = f"PRIVY_PROVIDER={PROVIDER}\n"
            provider_found = True
            break
    if not provider_found:
        lines.append(f"PRIVY_PROVIDER={PROVIDER}\n")
        
    # Update or add GEMINI_API_KEY if provided
    if api_key:
        key_name = "GEMINI_API_KEY"
        key_found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key_name}="):
                lines[i] = f"{key_name}={api_key}\n"
                key_found = True
                break
        if not key_found:
            lines.append(f"{key_name}={api_key}\n")
            
    with open(config_path, "w") as f:
        f.writelines(lines)

PROVIDER = os.getenv("PRIVY_PROVIDER", "gemini").lower()

# Ollama Settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

def generate(prompt, system_instruction=""):
    if PROVIDER == "ollama":
        return _generate_ollama(prompt, system_instruction)
    elif PROVIDER == "gemini":
        return _generate_gemini(prompt, system_instruction)
    else:
        raise ValueError(f"Unsupported provider: {PROVIDER}")

def get_embedding(text):
    if PROVIDER == "ollama":
        return _get_embedding_ollama(text)
    elif PROVIDER == "gemini":
        return _get_embedding_gemini(text)
    else:
        # Fallback to Ollama or return empty if not configured
        return _get_embedding_ollama(text)

def _generate_ollama(prompt, system_instruction):
    url = f"{OLLAMA_BASE_URL}/api/generate"
    # Simplified raw prompt for Ollama which works well with many models
    full_prompt = f"SYSTEM: {system_instruction}\nUSER: {prompt}\nASSISTANT:"
    
    response = requests.post(url, json={
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_ctx": 4096}
    }, timeout=120)
    
    if response.status_code == 200:
        return response.json().get('response', '').strip()
    return f"Error: {response.status_code} - {response.text}"

def _generate_gemini(prompt, system_instruction):
    if not GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY not set in environment."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": f"System Instruction: {system_instruction}\n\nUser Question: {prompt}"}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
        }
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        try:
            return result['candidates'][0]['content']['parts'][0]['text'].strip()
        except (KeyError, IndexError):
            return "Error: Unexpected response format from Gemini."
    return f"Error: {response.status_code} - {response.text}"

def _get_embedding_ollama(text):
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    try:
        response = requests.post(url, json={
            "model": OLLAMA_EMBED_MODEL,
            "prompt": text
        }, timeout=10)
        if response.status_code == 200:
            return response.json().get('embedding', [])
    except:
        pass
    return []

def _get_embedding_gemini(text):
    if not GEMINI_API_KEY:
        return []
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": text}]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json().get('embedding', {}).get('values', [])
    except:
        pass
    return []

def check_ready():
    """Checks if the configured provider is available."""
    if PROVIDER == "ollama":
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
            if r.status_code == 200:
                models = [m['name'] for m in r.json().get('models', [])]
                # Check both main and embedding models
                main_ok = any(OLLAMA_MODEL in m for m in models)
                embed_ok = any(OLLAMA_EMBED_MODEL in m for m in models)
                return main_ok and embed_ok
            return False
        except:
            return False
    elif PROVIDER == "gemini":
        return bool(GEMINI_API_KEY)
    return False

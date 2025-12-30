#!/usr/bin/env python3
"""
Privy Main Application Module.

This is the entry point for the Privy Local AI Terminal.
It handles user input, executes native shell commands, and manages
interactions with the local AI model (Ollama).
"""

import sys
import os
import subprocess
import requests
import json
import time
import re

# Import local modules
try:
    from . import rag
    from . import status
except ImportError:
    # Fallback for running directly (development)
    import rag
    import status

# Try importing rich for UI Polish
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.style import Style
    from rich.text import Text
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Configuration
MODEL = "qwen2.5-coder:1.5b"
OLLAMA_API = "http://localhost:11434/api/generate"
OLLAMA_CHECK = "http://localhost:11434/api/tags"
HISTORY_LIMIT = 5

# Fallback Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_styled(text: str, style: str = "white"):
    """
    Prints text with color/style using Rich if available, else ANSI codes.

    Args:
        text (str): The text to print.
        style (str): The color/style name (e.g., 'red', 'bold cyan').
    """
    if HAS_RICH:
        console.print(text, style=style)
    else:
        # Basic mapping
        color = RESET
        if style == "cyan": color = CYAN
        elif style == "green": color = GREEN
        elif style == "red": color = RED
        elif style == "yellow": color = YELLOW
        print(f"{color}{text}{RESET}")

def check_ollama_ready() -> bool:
    """
    Checks if Ollama is running and if the required model is available.
    Pulls the model if missing.

    Returns:
        bool: True if ready, False otherwise.
    """
    print_styled(f"[System] Inicjalizacja silnika AI...", "yellow")
    max_retries = 30
    for _ in range(max_retries):
        try:
            r = requests.get(OLLAMA_CHECK)
            if r.status_code == 200:
                models = [m['name'] for m in r.json()['models']]
                if MODEL not in models and f"{MODEL}:latest" not in models:
                    print_styled(f"[System] Model {MODEL} nie znaleziony. Pobieranie...", "red")
                    subprocess.run(f"ollama pull {MODEL}", shell=True)
                return True
        except:
            time.sleep(2)
    return False

def detect_intent(query: str) -> str:
    """
    Simple keyword routing to decide between System Admin and Coder mode.
    
    Args:
        query (str): The user's input.

    Returns:
        str: 'coder' or 'admin'.
    """
    code_keywords = [
        "write code", "create script", "generate file", "napisz kod", "stwórz plik", 
        "napisz skrypt", "program in", "python script", "bash script", "html file"
    ]
    query_lower = query.lower()
    for kw in code_keywords:
        if kw in query_lower:
            return "coder"
    return "admin"

def process_ai_interaction(user_query: str, history: list) -> dict:
    """
    Processes the user query via the AI model, including RAG and tool use.

    Args:
        user_query (str): The user's text input.
        history (list): List of previous interactions.

    Returns:
        dict: A dictionary with 'type' ('message', 'suggestion', 'error') and 'content'.
    """
    intent = detect_intent(user_query)
    
    # RAG: Search local documentation
    local_context = ""
    try:
        rag_text = rag.search_docs(user_query)
        if rag_text.strip():
            local_context = f"\nLOCAL SYSTEM DOCUMENTATION:\n{rag_text}\n"
    except Exception as e:
        print_styled(f"RAG Error: {e}", "red")

    # Build Context History
    context_str = ""
    if history:
        context_str = "PREVIOUS CONTEXT:\n"
        for item in history:
            context_str += f"User: {item['user']}\nLast Command: {item['cmd']}\nResult: {item['status']}\n---\n"

    # Base System Prompts
    if intent == "coder":
        system_instruction = f"You are a Coding Assistant. Generate BASH commands to CREATE files using 'cat << EOF'.\n{local_context}\nOUTPUT ONLY THE BASH COMMAND. No explanations."
    else:
        system_instruction = f"""
You are Privy System Assistant.
        {local_context}
        MODES:
        1. **QUERY/INFO** (User asks "What is...", "Check...", "Show me..."):
           - You can run read-only commands silently to get info.
           - FORMAT: `[[CHECK: command]]`
           - IMPORTANT: After receiving "TOOL OUTPUT", you MUST provide a human-readable summary. DO NOT loop unless the previous command failed.

        2. **ACTION** (User asks "Create...", "Delete...", "Move...", "Install..."):
           - Output the BASH command directly.
           - Do NOT use markdown.

        EXAMPLE FLOW:
        User: "How much RAM is free?"
        Assistant: [[CHECK: free -h]]
        System: TOOL OUTPUT: Mem: 16Gi 8Gi 8Gi ...
        Assistant: You have 8Gi of free RAM.

        3. **CHAT**:
           - Just reply nicely.
        """

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": f"{context_str}\nUser Request: {user_query}"}
    ]

    # Tool Use Loop (Increased to 4 to allow retry)
    for _ in range(4):
        try:
            # Prepare prompt for non-chat API (using raw prompt mode for simplicity with this model)
            conversation = ""
            for m in messages:
                conversation += f"{m['role'].upper()}: {m['content']}\n"
            conversation += "ASSISTANT:"

            response = requests.post(OLLAMA_API, json={
                "model": MODEL,
                "prompt": conversation,
                "stream": False,
                "options": {"temperature": 0.1, "num_ctx": 4096}
            })
            if response.status_code != 200:
                return {"type": "error", "content": f"API Error: {response.status_code}"}
            
            raw_output = response.json()['response'].strip()
            
            # 1. Check for Tool Use ([[CHECK: ...]])
            check_match = re.search(r"\\\[\[CHECK:\s*(.*?)\\\]\]", raw_output, re.IGNORECASE)
            if check_match:
                cmd_to_run = check_match.group(1).strip()
                print_styled(f"[Agent] Sprawdzam: {cmd_to_run}...", "yellow")
                
                # Execute silently
                try:
                    # Timeout to prevent hanging
                    proc = subprocess.run(cmd_to_run, shell=True, capture_output=True, text=True, timeout=5)
                    tool_output = proc.stdout[:2000] + proc.stderr[:500] # Limit output size
                    if not tool_output.strip(): tool_output = "(No output)"
                except subprocess.TimeoutExpired:
                    tool_output = "Error: Command timed out."
                except Exception as e:
                    tool_output = f"Error executing check: {e}"

                # Add result to conversation and loop again
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({"role": "system", "content": f"TOOL OUTPUT for '{cmd_to_run}':\n{tool_output}\n\nNow answer the user's question based on this info."
})
                continue
            
            final_cmd = raw_output
            if final_cmd.startswith("```"):
                lines = final_cmd.splitlines()
                if len(lines) >= 3:
                    final_cmd = "\n".join(lines[1:-1])
                else:
                    final_cmd = final_cmd.replace("```bash", "").replace("```", "")
            final_cmd = final_cmd.strip()

            is_command = False
            if intent == "coder":
                is_command = True
            else:
                common_bins = ["ls", "cd", "cat", "grep", "find", "mkdir", "rm", "mv", "cp", "git", "apt", "nano", "vim", "python", "curl", "wget", "ip", "ping", "systemctl", "sudo"]
                first_word = final_cmd.split()[0] if final_cmd else ""
                if first_word in common_bins or "&&" in final_cmd or "|" in final_cmd:
                    is_command = True
                if "\n" in final_cmd and not ("&&" in final_cmd or ";" in final_cmd):
                     is_command = False

            if is_command:
                return {"type": "suggestion", "content": final_cmd}
            else:
                return {"type": "message", "content": raw_output.replace("[[CHECK:", "").strip()}

        except Exception as e:
            return {"type": "error", "content": f"Logic Error: {e}"}

    return {"type": "error", "content": "Agent loop limit reached."}

def print_banner():
    """Prints the Privy banner with ASCII art."""
    ascii_art = """
  _____       _                
 |  __ \     (_)               
 | |__) | __ _ __   _ _   _ 
 |  ___/ '__| | \ \ / / | | |
 | |   | |  | |  \ V /| |_| |
 |_|   |_|  |_|   \_/  \__, |
                        __/ |
                       |___/ 
"""
    if HAS_RICH:
        panel = Panel(
            Text(ascii_art, style="cyan bold") + Text("\nPrivy v1.4 - Local AI Terminal", style="white"),
            border_style="cyan"
        )
        console.print(panel)
    else:
        print(f"{CYAN}{ascii_art}{RESET}")
        print(f"{CYAN}Privy v1.4{RESET}")

def main():
    """Main application loop."""
    os.system('clear')
    print_banner()

    ai_enabled = check_ollama_ready()
    NATIVE_COMMANDS = ['ls', 'cd', 'pwd', 'cat', 'grep', 'cp', 'mv', 'rm', 'mkdir', 'touch', 'clear', 'exit', 'privypm']
    history = []

    while True:
        try:
            cwd = os.getcwd()
            prompt = f"Privy {cwd} > "
            user_input = input(prompt)
            
            if not user_input.strip(): continue
            if user_input.lower() in ['exit', 'logout']: break
            
            cmd_root = user_input.split()[0]

            if cmd_root == 'privy-status':
                status.show_dashboard()
                continue
            
            if cmd_root in NATIVE_COMMANDS:
                if cmd_root == 'cd':
                    path = user_input[3:].strip() or os.path.expanduser('~')
                    try: os.chdir(os.path.expanduser(path))
                    except Exception as e: print(e)
                else:
                    os.system(user_input)
                continue

            if not ai_enabled:
                print("AI disabled.")
                continue

            print("Thinking...", end="\r")
            result = process_ai_interaction(user_input, history)
            print(" " * 20, end="\r")
            
            if result['type'] == 'message':
                print(result['content'])
            elif result['type'] == 'suggestion':
                print(f"Sugestia: {result['content']}")
                if input("Wykonać? [Y/n]: ").lower() in ['y', '']:
                    os.system(result['content'])
            elif result['type'] == 'error':
                 print(f"Error: {result['content']}")

        except KeyboardInterrupt:
            print("\nExit with 'exit'")

if __name__ == "__main__":
    main()
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


try:
    from . import rag
    from . import status
    from . import ai
except ImportError:
    import rag
    import status
    import ai


try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.style import Style
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    console = Console(force_terminal=True)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False




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

def run_setup_wizard():
    """Interactive wizard to configure the AI provider."""
    console.print(Panel("[bold cyan]Privy Setup Wizard[/bold cyan]", border_style="cyan"))
    console.print("Wybierz dostawcę AI (BYOK):")
    console.print("1. [bold white]Ollama[/bold white] (Lokalny, darmowy)")
    console.print("2. [bold white]Google Gemini[/bold white] (Chmura, wymaga klucza)")
    console.print("3. [italic grey]OpenAI (Wkrótce...)[/italic grey]")
    console.print("4. [italic grey]Claude (Wkrótce...)[/italic grey]")
    
    choice = Prompt.ask("Twój wybór", choices=["1", "2"], default="2")
    
    if choice == "1":
        ai.update_config("ollama")
        console.print("[yellow]Sprawdzanie modeli Ollama...[/yellow]")
        
        # Simple auto-pull for convenience
        import subprocess
        try:
            console.print(f"[cyan]Pobieranie modelu {ai.OLLAMA_MODEL}... (może to zająć chwilę)[/cyan]")
            subprocess.run(["ollama", "pull", ai.OLLAMA_MODEL], check=True)
            console.print(f"[cyan]Pobieranie modelu embeddingów {ai.OLLAMA_EMBED_MODEL}...[/cyan]")
            subprocess.run(["ollama", "pull", ai.OLLAMA_EMBED_MODEL], check=True)
            console.print("[green]Modele pobrane pomyślnie.[/green]")
        except Exception as e:
            console.print(f"[red]Błąd podczas pobierania modeli: {e}[/red]")
            console.print("[yellow]Upewnij się, że polecenie 'ollama' jest dostępne w systemie.[/yellow]")
            
        console.print("[green]Skonfigurowano Ollama.[/green]")
    elif choice == "2":
        key = Prompt.ask("Wprowadź swój Gemini API Key", password=True)
        ai.update_config("gemini", key)
        console.print("[green]Skonfigurowano Google Gemini.[/green]")
    
    return ai.check_ready()

def check_ai_ready() -> bool:
    """Checks if the configured AI provider is available."""
    if ai.check_ready():
        return True
    
    print_styled(f"[System] AI ({ai.PROVIDER}) nie jest gotowe.", "yellow")
    if Confirm.ask("Czy chcesz uruchomić instalator (Setup Wizard)?"):
        return run_setup_wizard()
    
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
    

    local_context = ""
    try:
        rag_text = rag.search_docs(user_query)
        if rag_text.strip():
            local_context = f"\nLOCAL SYSTEM DOCUMENTATION:\n{rag_text}\n"
    except Exception as e:
        print_styled(f"RAG Error: {e}", "red")


    context_str = ""
    if history:
        context_str = "PREVIOUS CONTEXT:\n"
        for item in history:
            context_str += f"User: {item['user']}\nLast Command: {item['cmd']}\nResult: {item['status']}\n---\n"


    if intent == "coder":
        system_instruction = f"You are a Coding Assistant. First explain what you are going to do, then generate BASH commands to CREATE files using 'cat << EOF' inside a markdown code block (```bash ... ```).\n{local_context}"
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
           - First, explain briefly what the command will do.
           - Then, output the BASH command inside a markdown code block (```bash ... ```).

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


    for _ in range(4):
        try:
            raw_output = ai.generate(f"{context_str}\nUser Request: {user_query}", system_instruction)
            
            if raw_output.startswith("Error:"):
                return {"type": "error", "content": raw_output}
            
            check_match = re.search(r"\[\[CHECK:\s*(.*?)\]\]", raw_output, re.IGNORECASE)
            if check_match:
                cmd_to_run = check_match.group(1).strip()
                print_styled(f"[Agent] Sprawdzam: {cmd_to_run}...", "yellow")
                
                try:
                    proc = subprocess.run(cmd_to_run, shell=True, capture_output=True, text=True, timeout=5)
                    tool_output = proc.stdout[:2000] + proc.stderr[:500] 
                    if not tool_output.strip(): tool_output = "(No output)"
                except subprocess.TimeoutExpired:
                    tool_output = "Error: Command timed out."
                except Exception as e:
                    tool_output = f"Error executing check: {e}"

                messages.append({"role": "assistant", "content": raw_output})
                messages.append({"role": "system", "content": f"TOOL OUTPUT for '{cmd_to_run}':\n{tool_output}\n\nNow answer the user's question based on this info."})
                # Re-build prompt with tool output for the next iteration
                user_query = f"{user_query}\nTOOL OUTPUT for '{cmd_to_run}':\n{tool_output}"
                continue
            
            cmd_match = re.search(r"```(?:bash)?\s*(.*?)\s*```", raw_output, re.DOTALL)
            explanation = ""
            final_cmd = ""

            if cmd_match:
                final_cmd = cmd_match.group(1).strip()
                explanation = raw_output.replace(cmd_match.group(0), "").strip()
            else:
                final_cmd = raw_output.strip()
                if final_cmd.startswith("```"):
                    lines = final_cmd.splitlines()
                    if len(lines) >= 3:
                        final_cmd = "\n".join(lines[1:-1])

            is_command = False
            if intent == "coder" and cmd_match:
                is_command = True
            else:
                common_bins = ["ls", "cd", "cat", "grep", "find", "mkdir", "rm", "mv", "cp", "git", "apt", "nano", "vim", "python", "curl", "wget", "ip", "ping", "systemctl", "sudo"]
                first_word = final_cmd.split()[0] if final_cmd else ""
                if first_word in common_bins or "&&" in final_cmd or "|" in final_cmd:
                    is_command = True
                if "\n" in final_cmd and not ("&&" in final_cmd or ";" in final_cmd) and not cmd_match:
                     is_command = False

            if is_command:
                return {"type": "suggestion", "content": final_cmd, "explanation": explanation}
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

    ai_enabled = check_ai_ready()
    NATIVE_COMMANDS = ['ls', 'cd', 'pwd', 'cat', 'grep', 'cp', 'mv', 'rm', 'mkdir', 'touch', 'clear', 'exit', 'privypm']
    history = []

    while True:
        try:
            cwd = os.getcwd()
            if HAS_RICH:
                prompt_text = f"[bold cyan]Privy[/bold cyan] [bold bright_blue]{cwd}[/bold bright_blue] > "
                user_input = console.input(prompt_text)
            else:
                prompt = f"Privy {cwd} > "
                user_input = input(prompt)
            if not user_input.strip(): continue
            if user_input.lower() in ['exit', 'logout']: break
            
            if user_input.lower() == 'privy-setup':
                ai_enabled = run_setup_wizard()
                continue

            cmd_root = user_input.split()[0]

            if cmd_root == 'privy-status':
                status.show_dashboard()
                continue
            
            if cmd_root == 'privy-index':
                print_styled("[System] Uruchamianie indeksowania bazy wiedzy...", "cyan")
                rag.index_docs()
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
                if result.get('explanation'):
                    print_styled(f"[Wyjaśnienie] {result['explanation']}", "yellow")
                
                print(f"Sugestia: {result['content']}")
                if input("Wykonać? [Y/n]: ").lower() in ['y', '']:
                    os.system(result['content'])
            elif result['type'] == 'error':
                 print(f"Error: {result['content']}")

        except KeyboardInterrupt:
            print("\nExit with 'exit'")

if __name__ == "__main__":
    main()
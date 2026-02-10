#!/usr/bin/env python3
"""
Privy Package Manager (PrivyPM).

This module handles package installation via apt-get and generates
cheat sheets for installed tools using the local AI model.
"""

import sys
import subprocess
import requests
import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
try:
    from . import ai
except ImportError:
    import ai

console = Console(force_terminal=True)


def get_cheat_sheet(pkg):
    prompt = f"Provide a concise cheat sheet for the linux command '{pkg}'. List top 5 most useful examples. Output in Markdown. Keep it under 200 words."
    res = ai.generate(prompt, "You are a helpful Linux assistant.")
    if res.startswith("Error:"):
        return f"Could not generate cheat sheet ({res})."
    return res

def main():
    if len(sys.argv) < 2:
        console.print("[red]Usage: privypm <package_name>[/red]")
        return

    pkg = sys.argv[1]
    console.print(f"[bold green]PrivyPM:[/bold green] Installing [cyan]{pkg}[/cyan]...")
    
    res = subprocess.run(["sudo", "apt-get", "install", "-y", pkg])
    
    if res.returncode == 0:
        console.print(f"[bold green]Success![/bold green] Generating cheat sheet for [cyan]{pkg}[/cyan]...")
        cheat = get_cheat_sheet(pkg)
        console.print(Panel(Markdown(cheat), title=f"Cheat Sheet: {pkg}", border_style="blue"))
    else:
        console.print(f"[bold red]Failed to install {pkg}.[/bold red]")

if __name__ == "__main__":
    main()
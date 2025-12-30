#!/usr/bin/env python3
"""
System Status Module for Privy.

This module provides a dashboard view of system resources including
CPU, Memory, Disk usage, and Ollama AI status using the 'rich' library.
"""

import psutil
import requests
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# Initialize console instance
console = Console()

def get_cpu_info() -> str:
    """Returns the current CPU usage percentage."""
    return f"{psutil.cpu_percent()}%"

def get_mem_info() -> str:
    """Returns the current memory usage (Used / Total)."""
    mem = psutil.virtual_memory()
    return f"{mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB"

def get_disk_info() -> str:
    """Returns the free disk space on the root partition."""
    try:
        du = psutil.disk_usage('/')
        return f"{du.free // (1024**3)}GB Free"
    except Exception:
        return "N/A"

def get_ollama_status() -> str:
    """
    Checks the status of the local Ollama instance.

    Returns:
        str: A rich-formatted string indicating Online/Offline status.
    """
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=0.5)
        if r.status_code == 200:
            models = len(r.json().get('models', []))
            return f"[green]Online ({models} models)[/green]"
    except Exception:
        pass
    return "[red]Offline[/red]"

def generate_layout() -> Layout:
    """
    Generates the UI layout for the dashboard.

    Returns:
        Layout: A configured rich Layout object.
    """
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1)
    )
    
    layout["header"].update(Panel(Text("Privy Dashboard", justify="center", style="bold cyan"), box=box.ROUNDED))
    
    table = Table(box=box.SIMPLE, expand=True)
    table.add_column("System Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("CPU Usage", get_cpu_info())
    table.add_row("Memory (Used/Total)", get_mem_info())
    table.add_row("Disk Space (Free)", get_disk_info())
    table.add_row("Ollama AI Engine", get_ollama_status())
    
    layout["body"].update(Panel(table, title="Resource Monitor", border_style="blue"))
    return layout

def show_dashboard():
    """Renders and prints the dashboard to the console."""
    console.print(generate_layout())

if __name__ == "__main__":
    show_dashboard()

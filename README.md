# Privy

**Privy** is a Local AI Terminal Assistant Wrapper. It integrates with your local Ollama instance to provide intelligent suggestions, command explanations, and system status checks directly within your terminal workflow.

## Features

- **Natural Language Commands**: Ask for tasks in English (e.g., "Find all large files in /var").
- **System Dashboard**: View CPU, Memory, and Disk usage with `privy-status`.
- **PrivyPM**: Install packages and automatically generate cheat sheets with `privypm <package>`.
- **RAG Support**: Searches local documentation to provide context-aware answers.
- **Privacy Focused**: Runs entirely locally using Ollama.

## Installation

### From .deb (Debian/Ubuntu/Kali)
```bash
sudo dpkg -i privy_1.4.0-1_amd64.deb
sudo apt-get install -f  # To fix any missing dependencies
```

### Manual Installation
```bash
pip install -r requirements.txt
python3 -m privy.main
```

## Usage

Simply type `privy` to start the interactive session.
```bash
privy
```

Inside Privy:
- Type standard shell commands (`ls`, `cd`, `grep`...) normally.
- Type questions or requests for the AI.
- Use `privy-status` to see the dashboard.
- Use `privypm <package>` to install a tool and get a cheat sheet (e.g., `privypm htop`).

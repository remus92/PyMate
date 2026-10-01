# PyMate — Local AI Coding Assistant

Local AI assistant powered by [Ollama](https://ollama.com/). Writes and tests Python, manages files in a sandboxed workspace, searches the web, shows weather, installs pip packages, and fetches web pages.

Default model: `qwen2.5-coder:14b` (optimized for RTX 3060 12GB). Change it in `config.py`.

## Features
- Interactive CLI with `rich` and `prompt_toolkit`
- Tool-calling loop with JSON fallback
- Local Python execution with timeout
- Sandboxed workspace: `./workspace`
- Web search via DuckDuckGo, weather via `wttr.in`
- Install pip packages, fetch and extract web pages
- In-memory history; commands: `/help`, `/reset`, `/model`, `/exit`

## Requirements
- Python 3.10+
- [Ollama](https://ollama.com/) installed and running
- Model pulled: `ollama pull qwen2.5-coder:14b`
- Recommended GPU: RTX 3060 12GB. If low VRAM, reduce `NUM_CTX` or use a smaller model.

## Create a virtual environment
python -m venv .venv

## Create a virtual environment
Open a separate terminal and run:
ollama serve
Then pull the model:
ollama pull qwen2.5-coder:14b

## Installation

```bash
git clone https://github.com/remus92/PyMate.git
cd PyMate
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
ollama pull qwen2.5-coder:14b
python main.py
```

## Usage 
python main.py

## Configuration

All settings live in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL` | `qwen2.5-coder:14b` | Ollama model to use |
| `THINKING` | `False` | Thinking mode (not supported by qwen2.5-coder) |
| `MAX_ITERATIONS` | `10` | Max tool-calling loops per message |
| `TEMPERATURE` | `0.2` | Lower = more deterministic code |
| `NUM_CTX` | `8192` | Context size in tokens |
| `NUM_PREDICT` | `2048` | Max tokens per response |
| `NUM_GPU` | `99` | GPU layers (99 = all) |
| `TOP_P` | `0.9` | Nucleus sampling |
| `TOP_K` | `40` | Top-K sampling |
| `REPEAT_PENALTY` | `1.05` | Penalize repetition |
| `NUM_BATCH` | `512` | Batch size |
| `WORKSPACE_DIR` | `./workspace` | Sandbox folder for files |

> **Tip:** If you get a VRAM out-of-memory error, lower `NUM_CTX` to `6144` or `4096`, or switch to `qwen2.5-coder:7b`.

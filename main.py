"""
CLI interactiv pentru PyMate.
"""

import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from agent import chat
from config import MODEL, THINKING, WORKSPACE_DIR


console = Console()

PROMPT_STYLE = Style.from_dict({
    "prompt": "bold #00d787",
})

session = PromptSession(
    history=InMemoryHistory(),
    style=PROMPT_STYLE,
)

HIDDEN_TOOLS = {"web_search", "get_weather", "get_news", "fetch_url"}


def _print_tool_call(name: str, args: dict, result: str) -> None:
    if name in HIDDEN_TOOLS:
        return

    preview = result if len(result) <= 400 else result[:400] + "…"

    if name == "run_python" and "code" in args:
        console.print(Panel(
            Syntax(args["code"], "python", theme="monokai", line_numbers=False),
            title=f"[yellow]tool → {name}[/yellow]",
            border_style="yellow",
        ))
        console.print(f"[dim]↳ {preview}[/dim]\n")
    else:
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        console.print(
            f"[yellow]tool → {name}({args_str[:120]})[/yellow]\n"
            f"[dim]↳ {preview}[/dim]\n"
        )


def _print_help() -> None:
    console.print(Panel.fit(
        "[bold]Comenzi disponibile:[/bold]\n"
        "  [cyan]/help[/cyan]      afișează acest mesaj\n"
        "  [cyan]/reset[/cyan]     șterge istoricul conversației\n"
        "  [cyan]/model[/cyan]     afișează modelul curent\n"
        "  [cyan]/exit[/cyan]      ieși din asistent\n\n"
        "Scrie orice întrebare sau cere cod direct.",
        title="[bold cyan]Ajutor[/bold cyan]",
        border_style="cyan",
    ))


def main() -> None:
    console.print(Panel.fit(
        f"[bold cyan]PyMate — Asistent AI Coding[/bold cyan]\n"
        f"Model: [green]{MODEL}[/green]  |  "
        f"Thinking: [green]{'ON' if THINKING else 'OFF'}[/green]  |  "
        f"Workspace: [green]{WORKSPACE_DIR}[/green]\n"
        f"Scrie [yellow]/help[/yellow] pentru comenzi.",
        border_style="cyan",
    ))

    messages: list[dict] = []

    while True:
        try:
            user_input = session.prompt("\ntu › ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]La revedere![/dim]")
            sys.exit(0)

        if not user_input:
            continue

        if user_input in ("/exit", "/quit"):
            console.print("[dim]La revedere![/dim]")
            break
        if user_input == "/help":
            _print_help()
            continue
        if user_input == "/reset":
            messages = []
            console.print("[dim]Istoric resetat.[/dim]")
            continue
        if user_input == "/model":
            console.print(f"[green]Model curent:[/green] {MODEL}")
            continue

        messages.append({"role": "user", "content": user_input})

        console.print("[dim]gândesc...[/dim]")
        try:
            answer = chat(messages, on_tool_call=_print_tool_call)
        except KeyboardInterrupt:
            console.print("\n[red]Întrerupt.[/red]")
            continue
        except Exception as e:
            console.print(f"[red]Eroare: {type(e).__name__}: {e}[/red]")
            continue

        messages.append({"role": "assistant", "content": answer})

        console.print(Panel(
            Markdown(answer),
            title="[bold cyan]asistent[/bold cyan]",
            border_style="cyan",
        ))


if __name__ == "__main__":
    main()

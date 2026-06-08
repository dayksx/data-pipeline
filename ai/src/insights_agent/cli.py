import json

import typer
from rich.console import Console
from rich.table import Table

from insights_agent.graph import run_question

app = typer.Typer(no_args_is_help=True, name="insights")
console = Console()


def _simplify_messages(messages) -> list[dict]:
    simplified: list[dict] = []
    for msg in messages or []:
        entry: dict = {"type": getattr(msg, "type", type(msg).__name__)}
        name = getattr(msg, "name", None)
        if name:
            entry["name"] = name
        content = getattr(msg, "content", "")
        if isinstance(content, str):
            try:
                entry["content"] = json.loads(content)
            except json.JSONDecodeError:
                entry["content"] = content
        else:
            entry["content"] = content
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            entry["tool_calls"] = tool_calls
        simplified.append(entry)
    return simplified


def _print_tool_trace(messages, verbose: bool) -> None:
    if not verbose:
        return
    for msg in messages:
        if getattr(msg, "type", None) != "tool":
            continue
        console.print(f"[dim]tool[/dim] {msg.name}")
        try:
            data = json.loads(msg.content)
        except (TypeError, json.JSONDecodeError):
            console.print(msg.content[:500])
            continue
        sql = data.get("sql")
        if sql:
            console.print(f"  SQL: {sql}")
        if data.get("error"):
            detail = data.get("message") or data.get("errors")
            console.print(f"  [red]error:[/red] {data['error']} {detail or ''}")
        if data.get("rows"):
            result_table = Table(show_header=True)
            columns = data.get("columns") or list(data["rows"][0].keys())
            for col in columns:
                result_table.add_column(str(col))
            for row in data["rows"][:10]:
                result_table.add_row(*[str(row.get(c, "")) for c in columns])
            console.print(result_table)


@app.callback()
def main() -> None:
    """LangGraph insights agent over the retail pipeline warehouse."""


@app.command()
def ask(
    question: str,
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Ask the agent a question."""
    state = run_question(question)
    payload = {
        "question": question,
        "final_answer": state.get("final_answer"),
        "messages": _simplify_messages(state.get("messages", [])),
    }

    if as_json:
        console.print_json(json.dumps(payload, default=str))
        return

    _print_tool_trace(state.get("messages", []), verbose=verbose)
    console.print(state.get("final_answer") or "(no answer)")


if __name__ == "__main__":
    app()

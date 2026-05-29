"""agentrr CLI."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from agentrr_core.log.reader import LogReader
from agentrr_core.validate import validate_log
from agentrr_core.version import __version__
from agentrr_sdk.record import record as sdk_record
from agentrr_sdk.replay import replay as replay_fn
from agentrr_sdk.replay import resolve_log_path
from rich.console import Console
from rich.json import JSON
from rich.table import Table

app = typer.Typer(name="agentrr", help="Record and replay AI agent runs.")
console = Console()


def _resolve(run_id: str) -> Path:
    return resolve_log_path(run_id)


@app.command()
def version() -> None:
    typer.echo(__version__)


@app.command()
def validate(
    run_id: str = typer.Argument(..., help="Run id or path to .jsonl"),
) -> None:
    path = _resolve(run_id) if not Path(run_id).is_file() else Path(run_id)
    result = validate_log(path)
    if result.ok:
        typer.secho(
            f"OK (last_valid_seq={result.last_valid_seq}, truncated={result.truncated})",
            fg=typer.colors.GREEN,
        )
    else:
        for err in result.errors:
            typer.secho(err, fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def inspect(
    run_id: str = typer.Argument(...),
    seq: int = typer.Option(..., "--seq", help="Event sequence number"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    reader = LogReader(_resolve(run_id))
    ev = reader.get_event(seq)
    if ev is None:
        typer.secho(f"No event at seq {seq}", fg=typer.colors.RED)
        raise typer.Exit(1)
    if as_json:
        console.print(JSON(ev.model_dump_json()))
    else:
        table = Table(title=f"Event seq={seq}")
        table.add_column("field")
        table.add_column("value")
        table.add_row("type", ev.type.value)
        table.add_row("status", ev.status.value)
        table.add_row("request_sig", ev.meta.get("request_sig", ""))
        console.print(table)
        console.print(JSON(json.dumps(ev.request, indent=2)[:2000]))


@app.command()
def record_cmd(
    module: str = typer.Argument(..., help="module.path:callable"),
    run_name: str = typer.Option("run", "--name"),
) -> None:
    import importlib

    mod_name, _, fn_name = module.partition(":")
    mod = importlib.import_module(mod_name)
    entry = getattr(mod, fn_name)
    path_out = sdk_record(run_name, entry)[1]
    typer.echo(str(path_out))


@app.command("replay")
def replay_cmd(
    run_id: str = typer.Argument(...),
    module: str | None = typer.Argument(
        None,
        help="module.path:callable (optional if stored in log header)",
    ),
    strict: bool = typer.Option(True, "--strict/--observe"),
    until_seq: int | None = typer.Option(None, "--until-seq"),
) -> None:
    import importlib

    mode = "strict" if strict else "observe"
    entry = None
    if module is not None:
        mod_name, _, fn_name = module.partition(":")
        entry = getattr(importlib.import_module(mod_name), fn_name)
    if until_seq is not None:
        if entry is None:
            typer.secho("module required with --until-seq", fg=typer.colors.RED)
            raise typer.Exit(1)
        from agentrr_cli.session import ReplaySession

        session = ReplaySession(_resolve(run_id), mode=mode)
        session.run_until_seq(entry, until_seq)
    else:
        replay_fn(run_id, entry, mode=mode)
        typer.secho("Replay complete", fg=typer.colors.GREEN)


@app.command()
def steps(
    run_id: str = typer.Argument(...),
    module: str = typer.Argument(...),
) -> None:
    import importlib

    mod_name, _, fn_name = module.partition(":")
    entry = getattr(importlib.import_module(mod_name), fn_name)
    from agentrr_cli.session import ReplaySession

    session = ReplaySession(_resolve(run_id))
    typer.echo("Commands: n=next boundary, p=step back (re-run-to-seq), q=quit")
    while True:
        cmd = typer.prompt("step").strip().lower()
        if cmd == "q":
            break
        if cmd == "n":
            seq = session.step_forward(entry)
            typer.echo(f"paused after seq {seq}")
        elif cmd == "p":
            seq = session.step_back(entry)
            typer.echo(f"re-run-to-seq {seq}")
        else:
            typer.echo("unknown command")


if __name__ == "__main__":
    app()

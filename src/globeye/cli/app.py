"""Typer + Rich command-line interface."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import Session

from globeye import __version__
from globeye.config import get_settings
from globeye.core.db import make_engine
from globeye.core.models import ScanResult
from globeye.core.orchestrator import Orchestrator
from globeye.core.target import TargetDetectionError, detect
from globeye.db.models import Case
from globeye.report.html_writer import write_html
from globeye.report.json_writer import write_json
from globeye.services.scan_service import run_cli_case_scan
from globeye.services.source_status import describe_source_status

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="GLOBEYE — strictly passive OSINT. Never contacts the target.",
)
console = Console()

_CONF_STYLE = {"high": "red", "medium": "yellow", "low": "cyan"}

_STATUS_STYLE = {
    "ok": "green",
    "keyless": "green",
    "missing_key": "yellow",
    "invalid_key": "red",
    "rate_limited": "yellow",
    "network_error": "red",
    "config_error": "red",
    "unknown": "red",
    "not_applicable": "dim",
}


def _render(result: ScanResult) -> None:
    s = result.summary()
    console.print(
        f"[bold]Target[/] {result.target.type.value} "
        f"[bold cyan]{result.target.value}[/]  "
        f"([green]{s['total']}[/] findings in "
        f"{result.duration_seconds:.2f}s)"
    )
    console.print(
        f"[dim]sources:[/] used={','.join(result.sources_used) or '-'} "
        f"skipped={','.join(result.sources_skipped) or '-'}"
    )
    if not result.findings:
        console.print("[yellow]No findings.[/]")
        return
    table = Table(show_lines=False, expand=True)
    table.add_column("source", style="magenta", no_wrap=True)
    table.add_column("kind", no_wrap=True)
    table.add_column("value")
    table.add_column("conf", no_wrap=True)
    for f in sorted(result.findings, key=lambda x: (x.source, x.kind, x.value)):
        table.add_row(
            f.source,
            f.kind,
            f.value,
            f"[{_CONF_STYLE.get(f.confidence.value, 'white')}]{f.confidence.value}[/]",
        )
    console.print(table)


@app.command()
def scan(
    target: Annotated[str, typer.Argument(help="domain, IP, email, ...")],
    json_out: Annotated[Path | None, typer.Option("--json", "-j", help="write JSON report")] = None,
    html_out: Annotated[
        Path | None, typer.Option("--html", help="write interactive HTML report")
    ] = None,
    pivot: Annotated[bool, typer.Option("--pivot", help="pivot into discovered entities")] = False,
    depth: Annotated[
        str,
        typer.Option("--depth", help="quick | standard | deep (case scans only)"),
    ] = "standard",
    case_id: Annotated[
        int | None,
        typer.Option("--case-id", help="associate scan with an investigation case"),
    ] = None,
    no_cache: Annotated[bool, typer.Option("--no-cache", help="bypass the disk cache")] = False,
    proxy: Annotated[str | None, typer.Option("--proxy", help="SOCKS5/HTTP proxy URL")] = None,
) -> None:
    """Run a passive scan against TARGET."""
    settings = get_settings()
    overrides: dict[str, object] = {}
    if no_cache:
        overrides["cache_enabled"] = False
    if proxy:
        overrides["proxy_url"] = proxy
    if overrides:
        settings = settings.model_copy(update=overrides)

    try:
        tgt = detect(target)
    except TargetDetectionError as exc:
        console.print(f"[red]invalid target:[/] {exc}")
        raise typer.Exit(2) from exc

    try:
        if case_id is not None:
            engine = make_engine(settings.db_url)
            with Session(engine) as session:
                if session.get(Case, case_id) is None:
                    console.print(f"[red]case not found:[/] {case_id}")
                    raise typer.Exit(2)
            result = asyncio.run(
                run_cli_case_scan(
                    engine,
                    settings,
                    case_id=case_id,
                    target=tgt,
                    pivot=pivot,
                    depth=depth,
                )
            )
            console.print(f"[dim]case:[/] {case_id}")
        else:
            result = asyncio.run(Orchestrator(settings).scan(tgt, pivot=pivot))
    except Exception as exc:
        console.print(f"[red]scan failed:[/] {exc}")
        raise typer.Exit(1) from exc

    _render(result)
    if json_out is not None:
        write_json(result, json_out)
        console.print(f"[green]JSON report written:[/] {json_out}")
    if html_out is not None:
        write_html(result, html_out)
        console.print(f"[green]HTML report written:[/] {html_out}")


@app.command()
def sources(
    check: Annotated[
        bool,
        typer.Option("--check", help="light probe per source (uses a small amount of API quota)"),
    ] = False,
    health: Annotated[
        bool,
        typer.Option("--health", help="alias for --check (deprecated)", hidden=True),
    ] = False,
) -> None:
    """List passive sources and their configuration status."""
    probe = check or health
    settings = get_settings()
    rows = asyncio.run(describe_source_status(settings, probe=probe))
    table = Table(title="Passive sources" + (" (checked)" if probe else ""))
    table.add_column("source", style="magenta")
    table.add_column("configured")
    table.add_column("status")
    table.add_column("message")
    for row in rows:
        status = str(row["status"])
        style = _STATUS_STYLE.get(status, "white")
        configured = "yes" if row["configured"] else "no"
        if not row["requires_api_key"]:
            configured = "n/a"
        table.add_row(
            row["name"],
            configured,
            f"[{style}]{status}[/]",
            str(row["message"]),
        )
    console.print(table)


@app.command()
def version() -> None:
    """Print the GLOBEYE version."""
    console.print(f"globeye {__version__}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()

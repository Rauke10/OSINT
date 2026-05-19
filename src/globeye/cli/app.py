"""Typer + Rich command-line interface."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from globeye import __version__
from globeye.config import get_settings
from globeye.core.models import ScanResult
from globeye.core.orchestrator import Orchestrator
from globeye.core.target import TargetDetectionError, detect
from globeye.report.json_writer import write_json

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="GLOBEYE — strictly passive OSINT. Never contacts the target.",
)
console = Console()

_CONF_STYLE = {"high": "red", "medium": "yellow", "low": "cyan"}


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
    pivot: Annotated[bool, typer.Option("--pivot", help="pivot into discovered entities")] = False,
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
        result = asyncio.run(Orchestrator(settings).scan(tgt, pivot=pivot))
    except Exception as exc:
        console.print(f"[red]scan failed:[/] {exc}")
        raise typer.Exit(1) from exc

    _render(result)
    if json_out is not None:
        write_json(result, json_out)
        console.print(f"[green]JSON report written:[/] {json_out}")


@app.command()
def sources(
    health: Annotated[bool, typer.Option("--health", help="run passive health checks")] = False,
) -> None:
    """List registered passive sources (optionally with health)."""
    orch = Orchestrator(get_settings())
    table = Table(title="Passive sources")
    table.add_column("name", style="magenta")
    table.add_column("targets")
    table.add_column("API key")
    table.add_column("available" if health else "")
    statuses = asyncio.run(orch.health_check()) if health else []
    by_name = {s.name: s for s in statuses}
    for cls in orch.source_classes:
        st = by_name.get(cls.name)
        table.add_row(
            cls.name,
            ",".join(sorted(t.value for t in cls.supported_target_types)),
            "required" if cls.requires_api_key else "no",
            ("[green]yes[/]" if st and st.available else "[red]no[/]") if health else "",
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

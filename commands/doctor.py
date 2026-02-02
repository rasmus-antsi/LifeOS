import argparse
import sys
from rich.console import Console

from commands._folders import build_folder_checks
from commands._hygiene import build_hygiene_checks

console = Console()

def run(context, args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="life-os doctor",
        description="Check system health against the LifeOS spec",
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Run a single check by name",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reserved for future cleanup actions (doctor is report-only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable output (not implemented yet)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include per-path details in report output",
    )
    parsed = parser.parse_args(args)

    if parsed.json:
        console.print("[yellow]JSON output is not implemented yet.[/yellow]")
        sys.exit(2)

    if parsed.verbose:
        context.verbose = True

    target = parsed.target.lower() if parsed.target else None

    console.print("[bold]life-os doctor[/bold]")
    console.print("[dim]Hygiene checks are report-only; no files are deleted.[/dim]")

    issues_found = False

    if parsed.dry_run:
        console.print("[cyan]↷ Doctor is report-only; no changes will be made.[/cyan]")

    checks = build_folder_checks(context) + build_hygiene_checks(context)
    for name, fn in checks:
        if target and name.lower() != target:
            continue

        result = fn(context)

        if result["ok"]:
            console.print(f"[green]✔ {name}[/green]")
        else:
            issues_found = True
            console.print(f"[yellow]⚠ {name}[/yellow]")
            for item in result["issues"]:
                console.print(f"  - {item}")
            for note in result.get("notes", []):
                console.print(f"  [dim]- {note}[/dim]")

    if not issues_found:
        console.print("[green]✔ System health: OK[/green]")
        sys.exit(0)

    console.print("\n[yellow]⚠ Issues found[/yellow]")
    sys.exit(1)

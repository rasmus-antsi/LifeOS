import argparse
import sys
from pathlib import Path
from rich.console import Console

from commands._cleanup import (
    caches_candidates,
    desktop_candidates,
    downloads_candidates,
    format_top_items,
    large_files_candidates,
    move_to_trash,
    summarize,
    _human_bytes,
)


console = Console()


def _prompt_step(label: str) -> str:
    while True:
        response = input(f"Proceed with {label}? (y/n/s=safe-only) ").strip().lower()
        if response in {"y", "n", "t"}:
            return response
        if response in {"s"}:
            return "t"
        print("Please enter y, n, or s.")


def _run_step(
    label: str,
    items: list,
    trash_dir: Path,
    dry_run: bool,
    assume_yes: bool,
    verbose: bool,
) -> bool:
    if not items:
        console.print(f"[green]{label}: no items[/green]")
        return True

    summary = summarize(items)
    console.print(
        f"{label}: {summary['count']} items ({_human_bytes(summary['size'])}) "
        f"[trash: {summary['trash']}, might-need: {summary['might']}]"
    )

    top_items = format_top_items(summary["top"])
    if top_items:
        if verbose:
            for item in items:
                console.print(f"  - {item.path} ({_human_bytes(item.size)}) [{item.classification}]")
        else:
            console.print(f"  Top: {', '.join(top_items)}")

    choice = "y" if assume_yes else _prompt_step(label)
    if choice == "n":
        console.print("[cyan]↷ Skipped.[/cyan]")
        return False

    trash_only = choice == "t"
    moved = move_to_trash(items, trash_dir, dry_run=dry_run, trash_only=trash_only)

    if dry_run:
        console.print("[cyan]↷ Dry run: no changes made.[/cyan]")
        return True

    if not moved:
        console.print("[cyan]↷ No changes made.[/cyan]")
        return True

    console.print(f"[green]✔ Moved to Trash: {len(moved)} item(s)[/green]")
    return True


def run(context, args: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="life-os cleanup",
        description="Step-by-step cleanup with confirmations",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without making changes",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmations and run all steps",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed item lists",
    )
    parsed = parser.parse_args(args)

    if parsed.verbose:
        context.verbose = True

    cleanup_config = context.cleanup
    actions = cleanup_config.get("actions", {})
    trash_dir = Path(actions.get("trash_dir", "~/.Trash")).expanduser()

    console.print("[bold]life-os cleanup[/bold]")
    console.print("[dim]Cleanup uses Trash by default; no permanent delete.[/dim]")

    if parsed.dry_run:
        console.print("[cyan]↷ Dry run: no changes will be made.[/cyan]")

    steps = [
        ("Desktop", desktop_candidates),
        ("Downloads", downloads_candidates),
        ("Caches", caches_candidates),
        ("Large Files", large_files_candidates),
    ]

    for label, fn in steps:
        items = fn(context)
        _run_step(
            label=label,
            items=items,
            trash_dir=trash_dir,
            dry_run=parsed.dry_run,
            assume_yes=parsed.yes,
            verbose=parsed.verbose,
        )

    sys.exit(0)

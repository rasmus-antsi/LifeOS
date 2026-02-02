import sys
from rich.console import Console

from commands._folders import build_folder_checks

console = Console()

def run(context, args: list[str]) -> None:
    target = args[0].lower() if args else None

    console.print("[bold]life-os doctor[/bold]")

    issues_found = False

    for name, fn in build_folder_checks(context):
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

    if not issues_found:
        console.print("[green]✔ System health: OK[/green]")
        sys.exit(0)

    console.print("\n[yellow]⚠ Issues found[/yellow]")
    sys.exit(1)

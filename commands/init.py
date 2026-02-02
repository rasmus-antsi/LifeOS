import sys
from rich.console import Console

from commands._folders import build_folder_checks

console = Console()

def run(context, args: list[str]) -> None:
    target = args[0].lower() if args else None

    console.print("[bold]life-os init[/bold]")

    created_any = False
    unresolved = False

    for name, fn in build_folder_checks(context):
        if target and name.lower() != target:
            continue

        result = fn(context)

        if result["ok"]:
            console.print(f"[green]✔ {name}[/green]")
            continue

        console.print(f"[yellow]⚠ {name}[/yellow]")

        issues = result["issues"]
        fix = result["fix"]

        for item in issues:
            console.print(f"  - {item}")

        if fix is None:
            unresolved = True
            continue

        created = fix()
        if created:
            created_any = True
            for created_item in created:
                console.print(f"[green]✔ Created[/green] {created_item}")
        else:
            console.print("[cyan]↷ No changes needed[/cyan]")

    if unresolved:
        console.print("\n[yellow]⚠ Some issues could not be fixed[/yellow]")
        sys.exit(1)

    if created_any:
        console.print("\n[green]✔ Initialization complete[/green]")
    else:
        console.print("[green]✔ Nothing to initialize[/green]")

    sys.exit(0)

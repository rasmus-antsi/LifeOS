from pathlib import Path

from life_os.context import Context


def test_context_expands_paths(tmp_path: Path) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "version: 0.3",
                "filesystem:",
                "  workspace:",
                "    path: ~/Workspace",
                "  system:",
                "    path: ~/System",
                "  documents:",
                "    path: ~/Documents",
                "  desktop:",
                "    path: ~/Desktop",
                "  downloads:",
                "    path: ~/Downloads",
                "hygiene:",
                "  downloads:",
                "    age_days: 7",
            ]
        ),
        encoding="utf-8",
    )

    context = Context(spec_path=spec_path)
    home = Path.home()

    assert context.desktop == home / "Desktop"
    assert context.downloads == home / "Downloads"
    assert context.hygiene["downloads"]["age_days"] == 7

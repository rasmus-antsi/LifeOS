import os
import time
from pathlib import Path

from commands._cleanup import CleanupItem, downloads_candidates, move_to_trash
from life_os.context import Context


def _make_context(tmp_path: Path) -> Context:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "version: 0.4",
                "filesystem:",
                "  workspace:",
                "    path: " + str(tmp_path / "Workspace"),
                "  system:",
                "    path: " + str(tmp_path / "System"),
                "  documents:",
                "    path: " + str(tmp_path / "Documents"),
                "  desktop:",
                "    path: " + str(tmp_path / "Desktop"),
                "  downloads:",
                "    path: " + str(tmp_path / "Downloads"),
                "cleanup:",
                "  actions:",
                "    trash_dir: " + str(tmp_path / ".Trash"),
                "  downloads:",
                "    allowlist:",
                "      names:",
                "        - .DS_Store",
                "    rules:",
                "      trash_extensions:",
                "        - .dmg",
                "      max_age_days: 7",
                "      large_min_size_mb: 1",
            ]
        ),
        encoding="utf-8",
    )
    return Context(spec_path=spec_path)


def test_downloads_candidates_classification(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    context.downloads.mkdir(parents=True)

    old_dmg = context.downloads / "old.dmg"
    old_iso = context.downloads / "old.iso"
    new_iso = context.downloads / "new.iso"

    old_dmg.write_bytes(b"a" * 1024)
    old_iso.write_bytes(b"b" * 1024)
    new_iso.write_bytes(b"c" * 2 * 1024 * 1024)

    old_time = time.time() - (10 * 24 * 60 * 60)
    for path in (old_dmg, old_iso):
        os.utime(path, (old_time, old_time))

    items = downloads_candidates(context)
    by_name = {item.path.name: item.classification for item in items}

    assert by_name["old.dmg"] == "trash"
    assert by_name["old.iso"] == "might-need"
    assert by_name["new.iso"] == "might-need"


def test_move_to_trash_dry_run(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.txt"
    file_path.write_text("hello", encoding="utf-8")

    item = CleanupItem(path=file_path, size=5, classification="trash")
    trash_dir = tmp_path / ".Trash"

    moved = move_to_trash([item], trash_dir, dry_run=True)

    assert moved == []
    assert file_path.exists()

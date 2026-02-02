import os
import time
from pathlib import Path

from life_os.context import Context
from commands._hygiene import (
    check_caches_reporting,
    check_desktop_cleanliness,
    check_downloads_aging,
    check_large_files,
)


def _make_context(tmp_path: Path) -> Context:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        "\n".join(
            [
                "version: 0.3",
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
                "hygiene:",
                "  desktop:",
                "    allowlist:",
                "      names:",
                "        - .DS_Store",
                "  downloads:",
                "    age_days: 7",
                "    top_n: 3",
                "  caches:",
                "    warn_over_mb: 1",
                "    paths:",
                "      - " + str(tmp_path / "Caches"),
                "  large_files:",
                "    min_size_mb: 1",
                "    top_n: 5",
                "    roots:",
                "      - " + str(tmp_path / "Downloads"),
            ]
        ),
        encoding="utf-8",
    )
    return Context(spec_path=spec_path)


def test_desktop_cleanliness_detects_items(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    context.desktop.mkdir(parents=True)
    (context.desktop / "note.txt").write_text("hi", encoding="utf-8")

    result = check_desktop_cleanliness(context)

    assert result["ok"] is False
    assert "Desktop has 1" in result["issues"][0]


def test_downloads_aging_groups_old_items(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    context.downloads.mkdir(parents=True)
    old_dmg = context.downloads / "old.dmg"
    old_zip = context.downloads / "old.zip"
    new_file = context.downloads / "new.txt"

    old_dmg.write_bytes(b"a" * 1024)
    old_zip.write_bytes(b"b" * 2048)
    new_file.write_bytes(b"c" * 1024)

    old_time = time.time() - (10 * 24 * 60 * 60)
    for path in (old_dmg, old_zip):
        path.chmod(0o644)
        os.utime(path, (old_time, old_time))

    result = check_downloads_aging(context)

    assert result["ok"] is False
    assert any("dmg:" in line for line in result["issues"])
    assert any("zip:" in line for line in result["issues"])


def test_caches_reporting_flags_large_entries(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    cache_dir = tmp_path / "Caches"
    cache_dir.mkdir(parents=True)
    (cache_dir / "big.cache").write_bytes(b"x" * 2 * 1024 * 1024)

    result = check_caches_reporting(context)

    assert result["ok"] is False
    assert any("Caches" in line for line in result["issues"])


def test_large_files_reports_top_items(tmp_path: Path) -> None:
    context = _make_context(tmp_path)
    context.downloads.mkdir(parents=True)
    big_file = context.downloads / "big.bin"
    big_file.write_bytes(b"x" * 2 * 1024 * 1024)

    result = check_large_files(context)

    assert result["ok"] is False
    assert any("file:" in line for line in result["issues"])

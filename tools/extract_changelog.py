#!/usr/bin/env python3
"""Extract one released section from CHANGELOG.md (Keep a Changelog format)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def extract(version: str, changelog: Path | None = None) -> str:
    text = (changelog or ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = version.lstrip("v")
    pattern = re.compile(
        rf"^##\s*\[?{re.escape(version)}\]?.*?$(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"version {version} not found in CHANGELOG.md")
    return f"## {version}\n" + match.group(1).strip() + "\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: extract_changelog.py <version>")
    sys.stdout.write(extract(sys.argv[1]))

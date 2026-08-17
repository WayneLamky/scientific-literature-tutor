#!/usr/bin/env python3
"""Validate the required structure and assets of an interactive reader spec."""

from __future__ import annotations

import json
import sys
from pathlib import Path


TOP = ("paper", "thesis", "logic_chain", "sample_audit", "figures", "validation", "takeaways", "questions", "glossary")
FIG = ("number", "title_zh", "title_en", "image", "question", "takeaway", "provenance", "reading", "observations", "claim", "limitation", "glossary")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_spec.py SPEC.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1]).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for key in TOP:
        if key not in data or data[key] in (None, "", []):
            errors.append(f"missing or empty top-level field: {key}")
    seen: set[str] = set()
    for index, figure in enumerate(data.get("figures", []), 1):
        for key in FIG:
            if key not in figure or figure[key] in (None, "", []):
                errors.append(f"figure {index}: missing or empty {key}")
        number = figure.get("number", "")
        if number in seen:
            errors.append(f"duplicate figure number: {number}")
        seen.add(number)
        image = figure.get("image")
        if image and not (path.parent / image).exists():
            errors.append(f"figure {index}: image not found: {image}")
    if errors:
        print("SPEC INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"SPEC OK: {len(data['figures'])} figures, {len(data['logic_chain'])} logic steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

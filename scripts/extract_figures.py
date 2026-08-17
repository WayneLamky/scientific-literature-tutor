#!/usr/bin/env python3
"""Crop paper figures from rendered page images using a JSON manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: extract_figures.py MANIFEST.json", file=sys.stderr)
        return 2
    manifest_path = Path(sys.argv[1]).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    for item in data["crops"]:
        source = (base / item["source"]).resolve()
        output = (base / item["output"]).resolve()
        box = tuple(item["box"])
        with Image.open(source) as image:
            width, height = image.size
            left, top, right, bottom = box
            if not (0 <= left < right <= width and 0 <= top < bottom <= height):
                raise ValueError(f"Invalid crop {box} for {source} ({width}x{height})")
            cropped = image.crop(box)
            output.parent.mkdir(parents=True, exist_ok=True)
            cropped.save(output, optimize=True)
            print(f"{item.get('name', output.stem)}: {cropped.width}x{cropped.height} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

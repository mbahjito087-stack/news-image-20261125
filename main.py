#!/usr/bin/env python3
"""Publish the front page for Wednesday 25 November 2026.

The finished page ships next to this file as ``asset.jpg``. It is a
broadsheet front page for 25 November 2026 whose lead is Zelenskiy's
confirmation that Ukraine struck a Russian ship in the Gulf of
Finland. Five further stories share the page: a Houthi drone hitting
Riyadh's tallest tower and wounding eleven people, Donald Trump
presenting Rudy Giuliani with the Medal of Freedom, Huawei's
conviction in an American criminal trial, NATO moving early-warning
aircraft to Poland, and the two Thanksgiving turkeys, Freedom and
Feathers, being spared.

The script itself draws nothing. It proves the picture is a whole
JPEG inside the contest limits, copies its bytes to the output
directory under the name ``entry.png`` (the contest reads the format
from the first bytes, so JPEG bytes under that name are fine), and
then checks the copy by size, digest and dimensions. Nothing here
touches the network, the clock or any random source, so two runs
always write the same bytes.
"""

from __future__ import annotations

import hashlib
import os
import struct
import sys
from pathlib import Path

ASSET_NAME = "asset.jpg"
OUT_NAME = "entry.png"
MAX_BYTES = 1_048_576
MAX_SIDE = 1_024


class EntryError(Exception):
    """A problem with the picture or the output that must stop the run."""


def digest(blob: bytes) -> str:
    """Hex SHA-256 of a byte string."""
    return hashlib.sha256(blob).hexdigest()


def jpeg_dimensions(blob: bytes) -> tuple[int, int]:
    """Pull (width, height) out of a JPEG's first frame segment.

    Walks the marker segments with struct instead of manual index
    arithmetic: each segment is 0xFF, a marker byte and a big-endian
    length, and the frame markers 0xC0-0xC3 carry height then width.
    Raises EntryError when no frame segment turns up.
    """
    if blob[:2] != b"\xff\xd8":
        raise EntryError("asset does not start with a JPEG SOI marker")
    pos = 2
    while pos + 4 <= len(blob):
        if blob[pos] != 0xFF:
            raise EntryError("asset has a broken JPEG marker chain")
        marker = blob[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        (length,) = struct.unpack_from(">H", blob, pos + 2)
        if 0xC0 <= marker <= 0xC3:
            height, width = struct.unpack_from(">HH", blob, pos + 5)
            return width, height
        pos += 2 + length
    raise EntryError("asset has no JPEG frame segment")


def check_picture(blob: bytes) -> tuple[int, int]:
    """Confirm the picture obeys the contest limits; return its size."""
    if not blob:
        raise EntryError("asset is empty")
    if len(blob) > MAX_BYTES:
        raise EntryError(
            f"asset is {len(blob)} bytes, over the {MAX_BYTES} limit"
        )
    if blob[:3] != b"\xff\xd8\xff":
        raise EntryError("asset does not open with the JPEG start marker")
    if blob[-2:] != b"\xff\xd9":
        raise EntryError("asset does not end with the JPEG end marker")
    width, height = jpeg_dimensions(blob)
    if width <= 0 or height <= 0:
        raise EntryError("asset reports zero width or height")
    if width > MAX_SIDE or height > MAX_SIDE:
        raise EntryError(
            f"asset is {width}x{height}, over the {MAX_SIDE}x{MAX_SIDE} limit"
        )
    return width, height


def publish() -> int:
    """Validate asset.jpg and write it out as entry.png, verified."""
    here = Path(__file__).resolve().parent
    source = here / ASSET_NAME
    if not source.is_file():
        print(f"error: no {ASSET_NAME} beside main.py", file=sys.stderr)
        return 1
    blob = source.read_bytes()
    try:
        width, height = check_picture(blob)
    except EntryError as problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1
    print(
        f"{ASSET_NAME} is {width}x{height} and {len(blob)} bytes, "
        "within the limits"
    )

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / OUT_NAME
    target.write_bytes(blob)

    written = target.read_bytes()
    if len(written) != len(blob):
        print("error: output size differs from the source", file=sys.stderr)
        return 1
    if digest(written) != digest(blob):
        print("error: output SHA-256 differs from the source", file=sys.stderr)
        return 1
    if jpeg_dimensions(written) != (width, height):
        print("error: output dimensions differ from the source", file=sys.stderr)
        return 1

    print(f"wrote {target} ({len(blob)} bytes, sha256 {digest(blob)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(publish())

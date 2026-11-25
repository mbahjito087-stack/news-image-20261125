#!/usr/bin/env python3
"""Copy the finished front page for Wednesday 25 November 2026 to the output.

The picture already exists beside this file as asset.jpg: a newspaper
front page for 25 November 2026. Its lead is Zelenskiy confirming
Ukraine's drone strike on a Russian ship in the Gulf of Finland, with
Norway urging caution, and the rest of the page carries five more
stories from the same day: a Houthi drone hitting Riyadh's tallest
tower and wounding 11, Trump awarding Rudy Giuliani the Medal of
Freedom, Huawei convicted in a sprawling US criminal trial, NATO
sending early-warning jets to Poland, and the Thanksgiving turkeys
Freedom and Feathers being spared.

This program draws nothing and changes nothing. It checks that the
image is a complete JPEG within the contest limits, copies it
byte-for-byte to the output directory as entry.png (the rules accept
JPEG bytes under that name, told apart by the file's first bytes),
and then proves the copy is exact by comparing file size and
SHA-256 digest. No network, no clock, no randomness: the same input
always produces the same output.
"""

import hashlib
import os
import shutil
import sys

ASSET = "asset.jpg"
OUTPUT_NAME = "entry.png"
FALLBACK_OUTPUT_DIR = "/output"
BYTE_LIMIT = 1048576
PIXEL_LIMIT = 1024
SOI = b"\xff\xd8\xff"
EOI = b"\xff\xd9"


def digest_file(path):
    """SHA-256 hex digest of a file, read in 1 MiB chunks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def is_complete_jpeg(path):
    """True when a file opens with the JPEG start marker and ends with EOI."""
    with open(path, "rb") as stream:
        opening = stream.read(3)
        stream.seek(-2, os.SEEK_END)
        closing = stream.read(2)
    return opening == SOI and closing == EOI


def read_jpeg_size(path):
    """Return (width, height) from the first JPEG frame marker, else None.

    Scans the marker segments with the standard library only. A segment
    begins with 0xFF, a marker byte and a 2-byte big-endian length; the
    frame markers 0xC0-0xC3 store height then width as 2-byte values.
    """
    with open(path, "rb") as stream:
        blob = stream.read()
    if blob[:2] != b"\xff\xd8":
        return None
    offset = 2
    while offset + 4 <= len(blob):
        if blob[offset] != 0xFF:
            return None
        marker = blob[offset + 1]
        if marker == 0xD8 or marker == 0xD9 or 0xD0 <= marker <= 0xD7:
            offset += 2
            continue
        length = int.from_bytes(blob[offset + 2:offset + 4], "big")
        if 0xC0 <= marker <= 0xC3:
            height = int.from_bytes(blob[offset + 5:offset + 7], "big")
            width = int.from_bytes(blob[offset + 7:offset + 9], "big")
            return width, height
        offset += 2 + length
    return None


def abort(message):
    """Report a failure on stderr and return the failing exit code."""
    print("error: " + message, file=sys.stderr)
    return 1


def run():
    base = os.path.dirname(os.path.abspath(__file__))
    asset = os.path.join(base, ASSET)

    if not os.path.isfile(asset):
        return abort("missing " + ASSET + " next to main.py: " + asset)

    size = os.path.getsize(asset)
    if size == 0:
        return abort(ASSET + " is empty: " + asset)
    if size > BYTE_LIMIT:
        return abort(
            "%s is %d bytes, over the %d-byte limit" % (ASSET, size, BYTE_LIMIT)
        )
    if not is_complete_jpeg(asset):
        return abort(ASSET + " is not a complete JPEG file: " + asset)

    dimensions = read_jpeg_size(asset)
    if dimensions is None:
        return abort("could not read the JPEG dimensions of " + ASSET)
    width, height = dimensions
    if width > PIXEL_LIMIT or height > PIXEL_LIMIT:
        return abort(
            "%s is %dx%d, over the %dx%d limit"
            % (ASSET, width, height, PIXEL_LIMIT, PIXEL_LIMIT)
        )
    print("%s is %dx%d and %d bytes, within the limits" % (ASSET, width, height, size))

    target_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or FALLBACK_OUTPUT_DIR
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, OUTPUT_NAME)

    shutil.copyfile(asset, target)

    if os.path.getsize(target) != size:
        return abort(
            "size mismatch after copy: %s is %d bytes, expected %d"
            % (target, os.path.getsize(target), size)
        )
    source_digest = digest_file(asset)
    if digest_file(target) != source_digest:
        return abort("SHA-256 mismatch after copy: " + target)

    target_dimensions = read_jpeg_size(target)
    if target_dimensions != (width, height):
        return abort(
            "output dimensions %s differ from the source %dx%d"
            % (target_dimensions, width, height)
        )

    print("wrote %s (%d bytes, sha256 %s)" % (target, size, source_digest))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

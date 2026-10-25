#!/usr/bin/env python3
"""Verify every plugin's vendored _common.py is byte-identical to the master.

Master: tools/common/_common.py
Vendored copies: plugins/*/lib/*/<pkg>/_common.py

Exit 0 when all copies match; exit 1 (listing the drifted files) otherwise.
Run directly, or via pytest (test_copies_match_master below).

To fix drift: edit the master, then re-vendor:
    for f in $(python3 tools/check_common_sync.py --list); do
        cp tools/common/_common.py "$f"
    done
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER = REPO_ROOT / "tools" / "common" / "_common.py"


def find_vendored() -> list[Path]:
    return sorted(REPO_ROOT.glob("plugins/*/lib/*/*/_common.py"))


def check() -> tuple[list[Path], list[Path]]:
    """Return (ok, drifted) vendored copies."""
    master_bytes = MASTER.read_bytes()
    ok, drifted = [], []
    for copy in find_vendored():
        (ok if copy.read_bytes() == master_bytes else drifted).append(copy)
    return ok, drifted


def main() -> int:
    if "--list" in sys.argv:
        for copy in find_vendored():
            print(copy)
        return 0

    if not MASTER.exists():
        print(f"master missing: {MASTER}")
        return 1

    ok, drifted = check()
    if not ok and not drifted:
        print("no vendored _common.py copies found under plugins/*/lib/")
        return 1

    for copy in ok:
        print(f"  in sync: {copy.relative_to(REPO_ROOT)}")
    for copy in drifted:
        print(f"  DRIFTED: {copy.relative_to(REPO_ROOT)}")

    if drifted:
        print("\nvendored copies have drifted from tools/common/_common.py —")
        print("edit the master, then: cp tools/common/_common.py <each drifted path>")
        return 1
    print(f"\nall {len(ok)} vendored copies match the master")
    return 0


# pytest entry point — lets any plugin's CI catch drift
def test_copies_match_master():
    _, drifted = check()
    assert not drifted, f"vendored _common.py drifted from master: {drifted}"


if __name__ == "__main__":
    sys.exit(main())

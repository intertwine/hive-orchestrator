#!/usr/bin/env python3
"""Build the reusable Hive 2.2 launch demo workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from src.hive.demo_fixture import build_north_star_demo, write_demo_manifest


def parse_args() -> argparse.Namespace:
    """Parse CLI args for the demo builder."""
    parser = argparse.ArgumentParser(description="Build the Hive 2.2 launch demo workspace.")
    parser.add_argument("path", help="Directory where the demo workspace should be created.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete the target directory first if it already exists.",
    )
    return parser.parse_args()


def main() -> int:
    """Build the launch fixture and print its manifest."""
    args = parse_args()
    root = Path(args.path).resolve()
    if root.exists():
        if not args.force:
            raise SystemExit(f"{root} already exists. Re-run with --force to replace it.")
        shutil.rmtree(root)
    manifest = build_north_star_demo(root)
    manifest_path = write_demo_manifest(root, manifest)
    payload = manifest | {"manifest_path": str(manifest_path)}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

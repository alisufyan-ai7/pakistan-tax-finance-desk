"""Internal stdin-to-summary synthetic worker, run only within deny-network container.

No environment secrets, no original files persisted, no external transport.
"""
from __future__ import annotations

import base64
import json
import os
import sys

from .source_contracts import inspect_synthetic_source


def main() -> None:
    if os.getenv("APP_DATA_MODE") != "synthetic":
        raise RuntimeError("Synthetic-only worker is required")
    source = sys.stdin.buffer.read(1024 * 1024 + 1)
    if len(source) > 1024 * 1024:
        raise RuntimeError("Source IPC size limit exceeded")
    item = json.loads(source)
    if not isinstance(item, dict) or set(item) != {
        "synthetic_fixture", "raw_b64", "adapter_key", "kind", "tax_year",
    } or item["synthetic_fixture"] is not True:
        raise RuntimeError("Invalid synthetic converter protocol")
    raw = base64.b64decode(item["raw_b64"], validate=True)
    result = inspect_synthetic_source(
        raw, adapter_key=item["adapter_key"], extension=".pdf",
        kind=item["kind"], synthetic_fixture=True, tax_year=item["tax_year"])
    output = json.dumps(result, separators=(",", ":"), sort_keys=True)
    if len(output.encode("utf-8")) > 4096:
        raise RuntimeError("Oversize synthetic metadata response")
    sys.stdout.write(output)


if __name__ == "__main__":
    main()

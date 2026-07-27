#!/usr/bin/env python3
"""Kopieer de protocollaag en de CLI naar de add-onmap.

Docker kan tijdens een build niet buiten zijn context kijken, dus de add-on kan
`custom_components/moma/protocol` niet rechtstreeks aanspreken. Dit script zet
er een kopie neer. Die kopieën staan in .gitignore -- de bron blijft
`custom_components/moma/`.

Draaien voor je de add-on naar /addons kopieert:

    python tools/sync_addon.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADDON = ROOT / "addon" / "moma-recorder"


def main() -> int:
    source = ROOT / "custom_components" / "moma" / "protocol"
    target = ADDON / "protocol"

    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "tools" / "moma_record.py", ADDON / "moma_record.py")

    print(f"protocol/ en moma_record.py gekopieerd naar {ADDON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

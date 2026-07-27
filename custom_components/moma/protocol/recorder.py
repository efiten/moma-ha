"""Pakketten wegschrijven als JSONL en weer terugspelen.

Formaat: één JSON-object per regel. De payload staat als leesbare tekst onder
`raw` wanneer het geldige UTF-8 is, en anders hexadecimaal onder `hex`. Zo is
een capture met een gewone editor te lezen zonder dat byte-getrouwheid
verloren gaat.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType


@dataclass(frozen=True)
class RecordedPacket:
    """Eén teruggespeeld pakket."""

    received_at: float
    source: str
    payload: bytes


class JsonlRecorder:
    """Schrijft ruwe pakketten weg, direct doorgespoeld naar schijf."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._handle = None

    def __enter__(self) -> JsonlRecorder:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Append: een herstart van de add-on mag een lopend corpus niet wissen.
        self._handle = self._path.open("a", encoding="utf-8", newline="\n")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def record(self, payload: bytes, *, source: str, received_at: float) -> None:
        """Leg één datagram vast."""
        if self._handle is None:
            raise RuntimeError("recorder is niet geopend; gebruik hem als context manager")

        entry: dict[str, object] = {"received_at": received_at, "source": source}
        try:
            entry["raw"] = payload.decode("utf-8")
        except UnicodeDecodeError:
            entry["hex"] = payload.hex()

        self._handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        # Onbewaakt draaien betekent dat een crash niet de laatste -- en meest
        # interessante -- pakketten mag kosten.
        self._handle.flush()

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def replay(path: Path | str) -> Iterator[RecordedPacket]:
    """Lees een capture terug in opnamevolgorde."""
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue

            entry = json.loads(line)
            if "raw" in entry:
                payload = entry["raw"].encode("utf-8")
            else:
                payload = bytes.fromhex(entry["hex"])

            yield RecordedPacket(
                received_at=entry["received_at"],
                source=entry["source"],
                payload=payload,
            )

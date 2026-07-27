"""Detecteren dat de stroom pakketten stilvalt.

UDP meldt niet dat een bron verdwenen is. Zonder detectie blijft een listener
tevreden luisteren naar niets: er crasht niets, Supervisor herstart niets, en de
opname stopt in stilte.

De klok komt van buiten. Dat maakt de detector zuiver testbaar en houdt de
tijdsbron bij de aanroeper, waar hij hoort.
"""

from __future__ import annotations


class StallDetector:
    """Houdt bij hoe lang er geen pakket meer binnenkwam."""

    def __init__(self, *, timeout: float, now: float) -> None:
        """`timeout` in seconden; 0 schakelt detectie uit."""
        self._timeout = timeout
        self._last_seen = now

    def packet_received(self, *, now: float) -> None:
        self._last_seen = now

    def quiet_for(self, *, now: float) -> float:
        """Aantal seconden sinds het laatste pakket."""
        return now - self._last_seen

    def is_stalled(self, *, now: float) -> bool:
        if not self._timeout:
            return False
        return self.quiet_for(now=now) > self._timeout

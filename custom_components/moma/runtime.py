"""De runtime: één socket per config entry, gedeeld door alle apparaten erop.

Bezit de UDP-listener, de toestand per apparaat en de stilstandsdetectie. Alles
wat hierboven zit -- sensoren, diagnostics -- leest hier alleen uit.

Deze module is de enige plek waar de protocollaag en Home Assistant elkaar
raken.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import (
    CONF_SHOW_ALL_FIELDS,
    DOMAIN,
    ISSUE_ALL_FIELDS_ZERO,
    MAX_DIAGNOSTIC_PAYLOADS,
    SIGNAL_DEVICE_UPDATE,
    SIGNAL_NEW_FIELDS,
    STALL_CHECK_INTERVAL,
    STALL_TIMEOUT,
    STORAGE_VERSION,
)
from .protocol.activation import FieldActivation
from .protocol.devices import DeviceTracker
from .protocol.listener import MomaListener, open_listener
from .protocol.watchdog import StallDetector

_LOGGER = logging.getLogger(__name__)


class MomaRuntime:
    """Houdt de listener en de apparaattoestand voor één config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.port: int = entry.data[CONF_PORT]
        self.tracker = DeviceTracker()

        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._listener: MomaListener | None = None
        self._detector = StallDetector(timeout=STALL_TIMEOUT, now=time.monotonic())
        self._recent: deque[dict[str, Any]] = deque(maxlen=MAX_DIAGNOSTIC_PAYLOADS)
        self._unsub_periodic_check: Any = None
        self._was_stalled = False
        self._zero_issue_open = False

    @property
    def show_all_fields(self) -> bool:
        return bool(self.entry.options.get(CONF_SHOW_ALL_FIELDS, False))

    async def async_start(self) -> None:
        """Herstel de activeringsstatus en open de socket."""
        stored = await self._store.async_load() or {}

        # Zonder herstel zou een herstart 's nachts de PV-sensor laten
        # verdwijnen tot zonsopgang: het veld staat dan op nul en zou opnieuw
        # als niet-geactiveerd gelden (ontwerpbeslissing 13).
        show_all = self.show_all_fields
        self.tracker = DeviceTracker(
            show_all_fields=show_all,
            activation=FieldActivation(
                active=stored.get("active", {}),
                require_value=not show_all,
            ),
        )

        self._listener = await open_listener(on_packet=self.handle_packet, port=self.port)
        self._unsub_periodic_check = async_track_time_interval(
            self.hass,
            self._async_periodic_check,
            timedelta(seconds=STALL_CHECK_INTERVAL),
        )

    async def async_stop(self) -> None:
        """Sluit de socket en bewaar de activeringsstatus.

        De socket moet hier werkelijk vrijkomen: blijft hij open, dan faalt de
        volgende reload met EADDRINUSE, en SO_REUSEPORT verdoezelt dat deels.
        """
        if self._unsub_periodic_check is not None:
            self._unsub_periodic_check()
            self._unsub_periodic_check = None

        if self._listener is not None:
            self._listener.close()
            self._listener = None

        await self._store.async_save({"active": self.tracker.activation_state()})

    @callback
    def handle_packet(self, payload: bytes, source: str) -> None:
        """Verwerk één datagram. Wordt door de listener in de event loop geroepen."""
        self._detector.packet_received(now=time.monotonic())

        # Vastleggen voor diagnostics gebeurt voor het interpreteren, zodat ook
        # onbegrepen verkeer terugkomt in een rapport.
        self._recent.append(
            {"source": source, "payload": payload.decode("utf-8", errors="replace")}
        )

        update = self.tracker.handle(payload)
        if update is None:
            return

        if update.activated_fields:
            _LOGGER.debug(
                "Nieuwe velden voor %s: %s", update.device, ", ".join(update.activated_fields)
            )
            async_dispatcher_send(self.hass, f"{SIGNAL_NEW_FIELDS}_{self.entry.entry_id}")
            self._store.async_delay_save(
                lambda: {"active": self.tracker.activation_state()}, 5
            )

        async_dispatcher_send(
            self.hass, f"{SIGNAL_DEVICE_UPDATE}_{self.entry.entry_id}_{update.device}"
        )

    @property
    def available(self) -> bool:
        """Of er recent nog pakketten binnenkwamen."""
        return not self._detector.is_stalled(now=time.monotonic())

    @property
    def active_entities(self) -> list[tuple[str, str]]:
        """Alle (apparaat, veld)-paren die een entiteit horen te hebben."""
        return [
            (device, field)
            for device, fields in self.tracker.activation_state().items()
            for field in fields
        ]

    @property
    def recent_payloads(self) -> list[dict[str, Any]]:
        return list(self._recent)

    @callback
    def _async_periodic_check(self, _now: Any) -> None:
        """De enige terugkerende taak: beschikbaarheid en de nul-melding."""
        self._async_update_availability()
        self._async_update_zero_issue()

    @callback
    def _async_update_zero_issue(self) -> None:
        """Meld het geval waarin alles binnenkomt maar niets een sensor wordt.

        Een apparaat waarvan elk veld op nul staat activeert geen enkel veld, en
        zonder entiteiten komt er ook geen device. De integratie werkt dan
        volledig correct terwijl er in de interface letterlijk niets staat -- niet
        te onderscheiden van een kapotte installatie. Zonder deze melding is de
        enige aanwijzing een alinea in de documentatie.

        Alleen bij `show_all_fields` uit: staat die aan, dan bestaan de
        entiteiten wel en valt er niets te melden.
        """
        issue_id = f"{ISSUE_ALL_FIELDS_ZERO}_{self.entry.entry_id}"
        stil = (
            bool(self.tracker.devices)
            and not self.active_entities
            and not self.show_all_fields
        )

        if stil == self._zero_issue_open:
            return

        self._zero_issue_open = stil

        if not stil:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return

        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_ALL_FIELDS_ZERO,
            translation_placeholders={
                "devices": ", ".join(sorted(self.tracker.devices)),
                "port": str(self.port),
            },
        )

    @callback
    def _async_update_availability(self) -> None:
        """Werk de beschikbaarheid bij wanneer de stroom stilvalt of terugkomt.

        UDP meldt niet dat een bron verdwenen is. Zonder deze controle blijven
        entiteiten hun laatste waarde tonen alsof er niets aan de hand is.
        """
        stalled = not self.available
        if stalled == self._was_stalled:
            return

        self._was_stalled = stalled
        if stalled:
            _LOGGER.warning(
                "Geen moma-pakketten meer op poort %s; entiteiten worden onbeschikbaar",
                self.port,
            )

        for device in self.tracker.devices:
            async_dispatcher_send(
                self.hass, f"{SIGNAL_DEVICE_UPDATE}_{self.entry.entry_id}_{device}"
            )

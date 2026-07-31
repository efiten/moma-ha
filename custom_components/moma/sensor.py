"""Sensoren voor moma-velden.

Entiteiten ontstaan pas wanneer een veld activeert (ontwerpbeslissing 13), en de
naamgeving volgt het protocolveld letterlijk (ontwerpbeslissing 11): een veld
`grid_power_w` van apparaat `Moma005000` wordt
`sensor.moma005000_grid_power_w`.

Dat levert een minder mooie weergavenaam op dan "Grid power", maar voor een
monitoring-integratie weegt een voorspelbare entity_id zwaarder: gebruikers
schrijven er templates, automatiseringen en dashboards tegenaan.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from . import MomaConfigEntry
from .const import SIGNAL_DEVICE_UPDATE, SIGNAL_NEW_FIELDS
from .device import device_details
from .fields import describe, display_name
from .runtime import MomaRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MomaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Maak sensoren aan, nu en zodra er velden bijkomen."""
    runtime = entry.runtime_data
    known: set[tuple[str, str]] = set()

    @callback
    def _add_activated_fields() -> None:
        new = [
            MomaSensor(runtime, device, field)
            for device, field in runtime.active_entities
            if (device, field) not in known
        ]
        if not new:
            return

        known.update((sensor.device, sensor.field) for sensor in new)
        async_add_entities(new)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{SIGNAL_NEW_FIELDS}_{entry.entry_id}", _add_activated_fields
        )
    )

    # Na een herstart zijn de velden al bekend uit de bewaarde activeringsstatus;
    # dan moeten de entiteiten er meteen zijn en niet pas bij het eerste pakket.
    _add_activated_fields()


class MomaSensor(SensorEntity):
    """Eén veld van één moma-apparaat."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, runtime: MomaRuntime, device: str, field: str) -> None:
        self._runtime = runtime
        self.device = device
        self.field = field

        spec = describe(field)
        self._attr_unique_id = f"{device}_{field}"
        self._attr_name = display_name(field)

        # Home Assistant leidt de entity_id normaal af uit de weergavenaam, wat
        # van "Battery SOC" `..._battery_soc` zou maken maar van "Grid power"
        # `..._grid_power` -- het eenheidstoken zou wegvallen. Een entiteit mag
        # zijn entity_id echter zelf voorstellen, en dat houdt hem gelijk aan het
        # protocolveld (ontwerpbeslissing 11). Bij een bestaande registratie
        # wint het register, dus hernoemen door de gebruiker blijft werken.
        self.entity_id = f"{Platform.SENSOR.value}.{slugify(f'{device}_{field}')}"
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_device_info = DeviceInfo(**device_details(device))

    @property
    def native_value(self) -> Any:
        return self._runtime.tracker.values_for(self.device).get(self.field)

    @property
    def available(self) -> bool:
        return self._runtime.available and self.native_value is not None

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{SIGNAL_DEVICE_UPDATE}_{self._runtime.entry.entry_id}_{self.device}",
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

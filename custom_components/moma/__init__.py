"""De moma-integratie voor Home Assistant.

Leest energiedata van apparaten die het moma-protocol via UDP broadcasten.

De integratie is configuratieloos: de identiteit komt uit de broadcast zelf, dus
er is geen IP-adres of naam nodig. Apparaten verschijnen binnen één interval na
installatie.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, ISSUE_ALL_FIELDS_ZERO, PLATFORMS
from .runtime import MomaRuntime

type MomaConfigEntry = ConfigEntry[MomaRuntime]

__all__ = ["DOMAIN"]


async def async_setup_entry(hass: HomeAssistant, entry: MomaConfigEntry) -> bool:
    """Open de socket en zet de platforms op."""
    runtime = MomaRuntime(hass, entry)

    try:
        await runtime.async_start()
    except OSError as err:
        # Meestal EADDRINUSE: iets anders houdt de poort al vast. Als
        # ConfigEntryNotReady probeert Home Assistant het later opnieuw, in
        # plaats van de integratie definitief kapot te melden.
        raise ConfigEntryNotReady(
            f"Kan niet luisteren op UDP-poort {runtime.port}: {err}"
        ) from err

    entry.runtime_data = runtime
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_change))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: MomaConfigEntry) -> bool:
    """Breek af en geef de socket vrij."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()

    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: MomaConfigEntry) -> None:
    """Ruim de nul-melding op als de integratie verwijderd wordt.

    Meldingen in het reparatieregister overleven het verwijderen van de invoer.
    Zonder dit blijft er een waarschuwing staan over een integratie die niet
    meer bestaat, en dan is er ook niets meer dat hem kan intrekken.
    """
    ir.async_delete_issue(hass, DOMAIN, f"{ISSUE_ALL_FIELDS_ZERO}_{entry.entry_id}")


async def _async_reload_on_options_change(
    hass: HomeAssistant, entry: MomaConfigEntry
) -> None:
    """Herlaad wanneer de opties wijzigen.

    "Alle velden tonen" verandert welke entiteiten er horen te bestaan, en dat
    is alleen bij het opzetten te bepalen.
    """
    await hass.config_entries.async_reload(entry.entry_id)

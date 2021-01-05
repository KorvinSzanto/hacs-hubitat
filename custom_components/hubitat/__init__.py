"""The Hubitat integration."""
from asyncio import gather
from logging import getLogger
import re
from typing import Any, Dict

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant

from .const import CONF_HUBITAT_EVENT, DOMAIN, PLATFORMS
from .device import Hub, get_hub

_LOGGER = getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Legacy setup -- not implemented."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hubitat from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hub = Hub(hass, config_entry, len(hass.data[DOMAIN]) + 1)

    if not await hub.async_setup():
        return False

    hass.data[DOMAIN][config_entry.entry_id] = hub

    await hub.async_update_device_registry()

    def stop_hub(event: Event) -> None:
        hub.stop()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_hub)

    # If this config entry's title uses a MAC address, rename it to use the hub
    # ID
    if re.match(r"Hubitat \(\w{2}(:\w{2}){5}\)", config_entry.title):
        hass.config_entries.async_update_entry(
            config_entry, title=f"Hubitat ({hub.id})"
        )

    hass.bus.fire(CONF_HUBITAT_EVENT, {"name": "ready"})
    _LOGGER.info("Hubitat is ready")

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = all(
        await gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, component)
                for component in PLATFORMS
            ]
        )
    )

    await get_hub(hass, config_entry.entry_id).unload()

    _LOGGER.debug(f"Unloaded all components for {config_entry.entry_id}")

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok

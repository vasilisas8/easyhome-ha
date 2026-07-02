"""Platform for EasyHome binary_sensors."""

import logging

from pymodbus.exceptions import ModbusException

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device_types import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up EasyHome binary_sensors."""
    coordinator = entry.runtime_data
    devices = entry.options.get("devices", [])
    binary_sensors = [EasyHomeBinarySensor(coordinator, entry, dev) for dev in devices if dev.get("device_type") == "switch"]
    async_add_entities(binary_sensors)


class EasyHomeBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """EasyHome binary_sensor."""

    def __init__(self, coordinator, entry, device_config) -> None:
        """EasyHome binary_sensor."""

        super().__init__(coordinator)
        self._api = coordinator.api
        self._device_number = int(device_config["device_number"])
        self._device_type = device_config["device_type"]
        info = DEVICE_TYPES[self._device_type]
        self._register_address = int(info["register"] + (self._device_number - 1) * info["step"])
        self._register_byte, self._register_bit = self._api.get_bit_info(self._device_number)
        if self._device_type == "switch":
            self._register_bit += 1
        self._attr_unique_id = f"{entry.entry_id}_{device_config['device_id']}"
        self._attr_name = device_config["name"]
        self._attr_is_on = False

        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_config["device_id"])},
            "name": self._attr_name,
            "manufacturer": "EasyHome",
            "model": info["name"],
            "via_device": (DOMAIN, entry.entry_id),
        }

    def _handle_coordinator_update(self) -> None:
        """Read binary_sensor state."""

        try:
            self._attr_is_on = self._api.read_bit(self._register_address, self._register_byte, self._register_bit)

        except ModbusException as err:
            _LOGGER.error(
                "Failed to read binary_sensor %s: %s",
                self.name,
                err,
            )
        finally:
            self.async_write_ha_state()

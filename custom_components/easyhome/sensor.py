"""Platform for EasyHome sensors."""

import logging

from pymodbus.exceptions import ModbusException

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device_types import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up sensor platform."""
    coordinator = entry.runtime_data
    devices = entry.options.get("devices", [])
    sensors = [EasyHomeSensor(coordinator, entry, dev) for dev in devices if dev.get("device_type") in ["temperature", "humidity", "illuminance"]]
    if sensors:
        async_add_entities(sensors)


class EasyHomeSensor(CoordinatorEntity, SensorEntity):
    """EasyHome Sensor."""

    def __init__(self, coordinator, entry, device_config) -> None:
        """EasyHome Sensor init."""
        super().__init__(coordinator)
        self._api = coordinator.api
        self._device_number = int(device_config["device_number"])
        self._device_type = device_config["device_type"]
        info = DEVICE_TYPES[self._device_type]
        self._attr_device_class = info["device_class"]
        self._attr_native_unit_of_measurement = info["unit"]
        self._attr_state_class = info["state_class"]
        self._register_address = info["register"] + (self._device_number - 1) * info["step"]
        self._register_byte = self._api.get_byte_info(self._register_address)
        self._register_address = int(self._register_address)
        self._max = info["max"]
        self._attr_unique_id = f"{entry.entry_id}_{device_config['device_id']}"
        self._attr_name = device_config["name"]
        self._attr_suggested_area = device_config.get("suggested_area")
        self._attr_native_value = None

        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_config["device_id"])},
            "name": self._attr_name,  # Название устройства = название сенсора
            "manufacturer": "EasyHome",
            "model": info["name"],
            "via_device": (DOMAIN, entry.entry_id),
        }

    def _handle_coordinator_update(self) -> None:
        """Обновление значения из регистра."""
        try:
            value = self._api.read_byte(self._register_address, self._register_byte)
            self._attr_native_value = value * self._max / 250

        except (ModbusException, TypeError, ZeroDivisionError) as e:
            _LOGGER.error(
                "Failed to read register %s (%s): %s",
                self._register_address,
                self.name,
                e,
            )
            self._attr_native_value = None
        finally:
            self.async_write_ha_state()

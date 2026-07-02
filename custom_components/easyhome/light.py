"""Platform for EasyHome lights."""

import logging

from pymodbus.exceptions import ModbusException

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .device_types import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up EasyHome light platform."""
    coordinator = entry.runtime_data
    devices = entry.options.get("devices", [])
    lights = [EasyHomeLight(coordinator, entry, dev) for dev in devices if dev.get("device_type") == "light"]
    async_add_entities(lights)


class EasyHomeLight(CoordinatorEntity, LightEntity):
    """EasyHome light."""

    def __init__(self, coordinator, entry, device_config) -> None:
        """EasyHome light."""
        super().__init__(coordinator)
        self._api = coordinator.api
        self._device_number = int(device_config["device_number"])
        self._device_type = device_config["device_type"]
        info = DEVICE_TYPES[self._device_type]
        self._onoff_register_address = info["onoff_register"] + (self._device_number - 1) * info["onoff_step"]
        self._onoff_register_byte = self._api.get_byte_info(self._onoff_register_address)
        self._onoff_register_address = int(self._onoff_register_address)
        self._brightness_register_address = info["dimmer_register"] + (self._device_number - 1) * info["dimmer_step"]
        self._brightness_register_byte = self._api.get_byte_info(self._brightness_register_address)
        self._brightness_register_address = int(self._brightness_register_address)
        self._dimmable = device_config.get("dimmable", False)
        self._attr_unique_id = f"{entry.entry_id}_{device_config['device_id']}"
        self._attr_name = device_config["name"]
        self._attr_is_on = False
        self._attr_brightness = None

        if self._dimmable:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_brightness = 255
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF

        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_config["device_id"])},
            "name": self._attr_name,
            "manufacturer": "EasyHome",
            "model": info["name"],
            "via_device": (DOMAIN, entry.entry_id),
        }

    def _handle_coordinator_update(self) -> None:
        """Считываем состояние лампы вкл/выкл."""
        try:
            # ON/OFF bit
            self._attr_is_on = self._api.read_bit(self._onoff_register_address, self._onoff_register_byte, 0)
            # brightness only for dimmer
            if self._dimmable:
                self._attr_brightness = self._api.read_byte(self._brightness_register_address, self._brightness_register_byte)
        except ModbusException as err:
            _LOGGER.error("Failed to read light %s: %s", self.name, err)
        finally:
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Вкл лампу."""
        try:
            # dimmer brightness
            if self._dimmable:
                brightness = kwargs.get("brightness", self._attr_brightness)
                if brightness is not None:
                    await self._api.write_byte(self._brightness_register_address, self._brightness_register_byte, brightness)

            await self._api.write_bit(self._onoff_register_address, self._onoff_register_byte, 0, True)
            self._attr_is_on = True
            if self._dimmable and brightness is not None:
                self._attr_brightness = brightness

        except ModbusException as err:
            _LOGGER.error("Failed to turn on %s: %s", self.name, err)
        finally:
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Выкл лампу."""
        try:
            await self._api.write_bit(self._onoff_register_address, self._onoff_register_byte, 0, False)
            self._attr_is_on = False
        except ModbusException as err:
            _LOGGER.error("Failed to turn off %s: %s", self.name, err)
        finally:
            self.async_write_ha_state()

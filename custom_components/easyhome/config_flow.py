"""Config flow for the EasyHome integration."""

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.selector import selector

from .api import EasyHomeApi
from .const import DOMAIN
from .device_types import DEVICE_TYPES

_LOGGER = logging.getLogger(__name__)

# Форма заполнения при добавлении ПЛК
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT): str,
    }
)


async def validate_input(hass: HomeAssistant, data):
    """Validate the user input allows us to connect.Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user."""

    api = EasyHomeApi(data[CONF_HOST], data[CONF_PORT])

    try:
        await api.connect()
    except (TimeoutError, aiohttp.ClientError) as err:
        raise ConfigEntryNotReady(f"Failed to connect to EasyHome at {CONF_HOST}:{CONF_PORT}") from err
    finally:
        await api.close()

    return {"title": f"EasyHome PLC ({data[CONF_HOST]})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # noqa: F811
    """Handle a config flow for EasyHome."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> EasyHomeOptionsFlow:
        """Get the options flow for this handler."""
        return EasyHomeOptionsFlow(config_entry)


class EasyHomeOptionsFlow(ConfigFlow):
    """Handle options flow for EasyHome."""

    def __init__(self, config_entry: ConfigEntry) -> None:  # noqa: D107
        self.config_entry = config_entry
        self._device_type = None

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Show main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options={
                "add_device": "Добавьте новое устройство",
                "remove_device": "Удалить устройство",
            },
            description_placeholders={"name": self.config_entry.title},
        )

    async def async_step_add_device(self, user_input: dict | None = None) -> FlowResult:
        """Выбор типа устройства."""

        if user_input is not None:
            self._device_type = user_input["device_type"]
            return await self.async_step_add_device_details()

        return self.async_show_form(
            step_id="add_device",
            data_schema=vol.Schema(
                {
                    vol.Required("device_type"): selector(
                        {
                            "select": {
                                "options": [
                                    {
                                        "value": key,
                                        "label": value["name"],
                                    }
                                    for key, value in DEVICE_TYPES.items()
                                ]
                            }
                        }
                    )
                }
            ),
        )

    async def async_step_add_device_details(self, user_input: dict | None = None) -> FlowResult:
        """Добавление устройства."""

        errors = {}

        # Общие поля
        schema = {
            vol.Required("device_number"): int,
            vol.Required("name"): str,
            vol.Optional("suggested_area"): str,
        }

        # Дополнительные поля
        if self._device_type == "light":
            schema[vol.Required("dimmable", default=False)] = bool

        if user_input is not None:
            user_input["device_type"] = self._device_type
            device_id = f"{self._device_type}_{user_input['device_number']}"
            devices = list(self.config_entry.options.get("devices", []))

            if any(dev["device_id"] == device_id for dev in devices):
                errors["base"] = "device_exists"
            else:
                user_input["device_id"] = device_id

                devices.append(user_input)

                return self.async_create_entry(
                    title="",
                    data={"devices": devices},
                )

        return self.async_show_form(
            step_id="add_device_details",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_remove_device(self, user_input: dict | None = None) -> FlowResult:
        """Удаление устройства."""

        devices = list(self.config_entry.options.get("devices", []))

        if not devices:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            device_id = user_input["device"]

            devices = [dev for dev in devices if dev["device_id"] != device_id]

            return self.async_create_entry(
                title="",
                data={"devices": devices},
            )

        return self.async_show_form(
            step_id="remove_device",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): selector(
                        {
                            "select": {
                                "options": [
                                    {
                                        "value": dev["device_id"],
                                        "label": (f"{dev['name']} ({dev['device_type']} №{dev['device_number']})"),
                                    }
                                    for dev in devices
                                ]
                            }
                        }
                    )
                }
            ),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

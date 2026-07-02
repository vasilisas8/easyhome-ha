"""The EasyHome integration."""

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .api import EasyHomeApi
from .const import DOMAIN
from .coordinator import EasyHomeCoordinator

_PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.LIGHT, Platform.SENSOR]

type EasyHomeConfigEntry = ConfigEntry[EasyHomeApi]


async def async_setup_entry(hass: HomeAssistant, entry: EasyHomeConfigEntry) -> bool:
    """Set up EasyHome from a config entry."""

    host = entry.data["host"]
    port = entry.data["port"]

    api = EasyHomeApi(host, port)

    try:
        await api.connect()
    except (TimeoutError, aiohttp.ClientError) as err:
        raise ConfigEntryNotReady(f"Failed to connect to EasyHome at {host}:{port}") from err

    coordinator = EasyHomeCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Создаем в реестре Главный Контроллер (Хаб)
    dev_registry = dr.async_get(hass)
    dev_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},  # ID главного хаба
        name=entry.title,
        manufacturer="EasyHome",
        model="Центральный Контроллер",
    )

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    # Подписываемся на события subentries
    entry.async_on_unload(entry.add_update_listener(async_entry_updated))

    return True


async def async_entry_updated(hass: HomeAssistant, entry: EasyHomeConfigEntry) -> bool:
    """Обработчик обновления entry (включая subentries)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(hass: HomeAssistant, entry: EasyHomeConfigEntry, device_entry) -> bool:
    """Определяем, можно ли удалять устройство."""
    # Разрешаем удаление только если устройство принадлежит этому config entry
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EasyHomeConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
    if unload_ok:
        await entry.runtime_data.api.close()
    return unload_ok

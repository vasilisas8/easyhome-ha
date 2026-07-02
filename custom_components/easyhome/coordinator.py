"""DataUpdateCoordinator for EasyHome."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EasyHomeApi

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


class EasyHomeCoordinator(DataUpdateCoordinator):
    """Coordinator for EasyHome."""

    def __init__(self, hass: HomeAssistant, api: EasyHomeApi) -> None:
        """Coordinator for EasyHome."""
        super().__init__(hass, _LOGGER, name="EasyHome", update_interval=SCAN_INTERVAL)
        self.api = api

    async def _async_update_data(self):
        """Read all registers."""

        try:
            #
            # TODO Здесь позже будет формироваться список автоматически
            #

            await self.api.read_registers(150, 120)
            await self.api.read_registers(310, 320)
            await self.api.read_registers(953, 32)
            await self.api.read_registers(730, 70)
            await self.api.read_registers(850, 16)

        except Exception as err:
            raise UpdateFailed(err) from err

"""Описание возможных типов устройств."""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature

DEVICE_TYPES = {
    "temperature": {
        "platform": "sensor",
        "name": "Датчик температуры",
        "register": 150,  # %MB/2
        "step": 4,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "max": 50,
    },
    "humidity": {
        "platform": "sensor",
        "name": "Датчик влажности",
        "register": 953,
        "step": 0.5,
        "device_class": SensorDeviceClass.HUMIDITY,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT,
        "max": 100,
    },
    "illuminance": {
        "platform": "sensor",
        "name": "Датчик освещенности",
        "register": 978.5,
        "step": 1,
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "unit": "%",
        "state_class": SensorStateClass.MEASUREMENT,
        "max": 100,
    },
    "light": {
        "platform": "light",
        "name": "Лампа",
        "onoff_register": 310,
        "dimmer_register": 730,
        "onoff_step": 4,
        "dimmer_step": 0.5,
    },
    "switch": {
        "platform": "switch",
        "name": "Выключатель",
        "register": 850,
        "step": 1 / 16,
    },
}

"""Coordinator for EasyHome."""

import asyncio
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)

MAX_REGISTERS = 125


class EasyHomeApi:
    """Централизованное подключение к контроллеру. Через него проходят все Modbus запросы."""

    def __init__(self, host: str, port: str) -> None:
        """Init."""
        self._host = host
        self._port = port
        self.client = AsyncModbusTcpClient(host, port=port)
        self._lock = asyncio.Lock()
        self._register_cache: dict[int, int] = {}

    async def connect(self) -> None:
        """Connect to Modbus device."""
        await self.client.connect()
        if not self.client.connected:
            raise ConnectionError("Cannot connect to Modbus device")

    async def close(self):
        """Close connection."""
        if self.client:
            try:
                self.client.close()
            except ModbusException as e:
                _LOGGER.warning("Error while closing Modbus client: %s", e)

    def get_bit_info(self, device_number: int):
        """Возвращает байт и бит."""
        bit = (device_number - 1) % 16
        if bit < 8:
            byte = "low"
        else:
            byte = "high"
            bit -= 8
        return byte, bit

    def get_byte_info(self, register_address: float):
        """Возвращает байт."""
        if register_address % 1 == 0:
            byte = "low"
        elif register_address % 1 == 0.5:
            byte = "high"
        return byte

    async def read_registers(self, start: int, count: int) -> None:
        """Считываем блок значений регистров."""
        while count > 0:
            block = min(count, MAX_REGISTERS)

            async with self._lock:
                rr = await self.client.read_holding_registers(
                    address=start,
                    count=block,
                )

            if rr.isError():
                raise RuntimeError(f"Modbus read error: {rr}")

            for i, value in enumerate(rr.registers):
                self._register_cache[start + i] = value

            start += block
            count -= block

    def read_register(self, address: int) -> int:
        """Считываем значение одного регистра."""
        if address not in self._register_cache:
            raise RuntimeError(f"Register {address} not found in cache")
        return self._register_cache[address]

    def read_byte(self, register: int, byte: str) -> int:
        """Read high or low byte from holding register."""
        value = self.read_register(register)
        if byte == "low":
            return value & 0xFF
        if byte == "high":
            return (value >> 8) & 0xFF
        raise ValueError(f"Unknown byte: {byte}")

    def read_bit(self, register: int, byte: str, bit: int) -> bool:
        """Read one bit from selected byte."""
        byte_value = self.read_byte(register, byte)
        return bool(byte_value & (1 << bit))

    async def write_register(self, address: int, value: int):
        """Write one register."""
        async with self._lock:
            wr = await self.client.write_register(address, value)
        if wr.isError():
            raise RuntimeError(f"Modbus write error: {wr}")
        self._register_cache[address] = value

    async def write_byte(self, register: int, byte: str, value: int) -> None:
        """Write high or low byte of holding register."""
        # Ограничиваем значение одним байтом
        value &= 0xFF
        # Читаем текущий регистр
        register_value = self.read_register(register)
        if byte == "low":
            # Сохраняем старший байт, заменяем младший
            register_value = (register_value & 0xFF00) | value
        elif byte == "high":
            # Сохраняем младший байт, заменяем старший
            register_value = (register_value & 0x00FF) | (value << 8)
        else:
            raise ValueError(f"Unknown byte: {byte}")
        await self.write_register(register, register_value)

    async def write_bit(self, register: int, byte: str, bit: int, state: bool) -> None:
        """Write one bit in selected byte."""
        byte_value = self.read_byte(register, byte)
        if state:
            byte_value |= 1 << bit
        else:
            byte_value &= ~(1 << bit)
        await self.write_byte(register, byte, byte_value)

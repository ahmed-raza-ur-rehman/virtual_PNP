"""Hardware Abstraction Layer (HAL) for multi-MCU targets."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class PinConfig:
    port: str
    pin: int
    mode: str = "input"  # input, output, analog, alternate
    pull: str = "none"  # none, up, down
    speed: str = "low"  # low, medium, high, very_high
    af: int = 0


class HALBase:
    def __init__(self, target: str):
        self.target = target
        self.clock_hz = 168_000_000
        self.pins: dict[tuple[str, int], PinConfig] = {}

    def init_clock(self, freq: int):
        self.clock_hz = freq

    def gpio_init(self, cfg: PinConfig):
        self.pins[(cfg.port, cfg.pin)] = cfg

    def gpio_write(self, port: str, pin: int, state: int):
        pass

    def gpio_read(self, port: str, pin: int) -> int:
        return 0

    def gpio_toggle(self, port: str, pin: int):
        pass

    def delay_ms(self, ms: int):
        pass

    def delay_us(self, us: int):
        pass


class STM32HAL(HALBase):
    def __init__(self, variant: str = "F4"):
        super().__init__(f"STM32{variant}")
        self.variant = variant
        self.registers: dict[int, int] = {}
        self.peripherals: dict[str, Any] = {}
        self.interrupts_enabled = True
        self.clock_tree = {"HSI": 16_000_000, "HSE": 8_000_000, "PLL": 168_000_000}

    def init_clock(self, freq: int):
        self.clock_hz = freq
        self.clock_tree["SYSCLK"] = freq

    def enable_peripheral_clock(self, periph: str):
        self.peripherals.setdefault(periph, True)

    def gpio_init(self, cfg: PinConfig):
        super().gpio_init(cfg)
        # configure MODER, OTYPER, OSPEEDR, PUPDR
        self.registers.setdefault(0x40020000 + 0x00, 0)  # MODER
        self.registers.setdefault(0x40020000 + 0x04, 0)  # OTYPER
        self.registers.setdefault(0x40020000 + 0x08, 0)  # OSPEEDR
        self.registers.setdefault(0x40020000 + 0x0C, 0)  # PUPDR

    def uart_init(self, uart_id: int, baud: int):
        self.peripherals[f"UART{uart_id}"] = {"baud": baud, "enabled": True}

    def uart_transmit(self, uart_id: int, data: bytes):
        pass

    def uart_receive(self, uart_id: int, timeout: int = 1000) -> bytes:
        return b""

    def spi_init(self, spi_id: int, mode: int, speed: int):
        self.peripherals[f"SPI{spi_id}"] = {"mode": mode, "speed": speed, "enabled": True}

    def i2c_init(self, i2c_id: int, speed: int):
        self.peripherals[f"I2C{i2c_id}"] = {"speed": speed, "enabled": True}

    def adc_init(self, adc_id: int, channels: list[int]):
        self.peripherals[f"ADC{adc_id}"] = {"channels": channels, "enabled": True}

    def adc_read(self, adc_id: int, channel: int) -> int:
        return 0

    def timer_init(self, tim_id: int, prescaler: int, period: int):
        self.peripherals[f"TIM{tim_id}"] = {"prescaler": prescaler, "period": period, "enabled": True}

    def pwm_set_duty(self, tim_id: int, channel: int, duty: float):
        pass

    def dma_init(self, dma_id: int, channel: int, src: int, dst: int, length: int):
        self.peripherals.setdefault(f"DMA{dma_id}", {})["ch" + str(channel)] = {"src": src, "dst": dst, "len": length}

    def flash_unlock(self):
        pass

    def flash_program(self, addr: int, data: bytes):
        pass

    def flash_erase_sector(self, sector: int):
        pass

    def enter_sleep(self):
        pass

    def enter_stop(self):
        pass

    def enter_standby(self):
        pass

    def get_uid(self) -> str:
        return "0123456789ABCDEF"


class ESP32HAL(HALBase):
    def __init__(self):
        super().__init__("ESP32")
        self.wifi_enabled = False
        self.bt_enabled = False
        self.free_heap = 320 * 1024

    def wifi_init(self, ssid: str, password: str):
        self.wifi_enabled = True

    def wifi_connect(self) -> bool:
        return True

    def bt_init(self):
        self.bt_enabled = True

    def deep_sleep(self, us: int):
        pass

    def get_chip_id(self) -> int:
        return 0x12345678

    def temperature_read(self) -> float:
        return 25.0

    def hall_sensor_read(self) -> int:
        return 0

    def touch_read(self, pin: int) -> int:
        return 0

    def dac_write(self, channel: int, value: int):
        pass

    def ledc_setup(self, channel: int, freq: int, resolution: int):
        pass

    def ledc_write(self, channel: int, duty: int):
        pass


class RP2040HAL(HALBase):
    def __init__(self):
        super().__init__("RP2040")
        self.cores = 2
        self.pio_state_machines = 8

    def pio_init(self, sm: int, program: bytes):
        pass

    def pio_exec(self, sm: int, instr: int):
        pass

    def multicore_launch(self, core: int, entry: Callable):
        pass

    def watchdog_enable(self, timeout_ms: int):
        pass

    def watchdog_feed(self):
        pass

    def flash_range_erase(self, addr: int, length: int):
        pass

    def flash_range_program(self, addr: int, data: bytes):
        pass


class AVRHAL(HALBase):
    def __init__(self, variant: str = "ATmega328P"):
        super().__init__(variant)
        self.variant = variant
        self.eeprom_size = 1024

    def eeprom_read(self, addr: int) -> int:
        return 0

    def eeprom_write(self, addr: int, val: int):
        pass

    def adc_init(self, ref: str = "AVCC"):
        pass

    def adc_read(self, channel: int) -> int:
        return 0

    def pwm_init(self, timer: int, mode: int):
        pass

    def pwm_set(self, timer: int, channel: int, duty: int):
        pass

    def sleep_mode(self, mode: str):
        pass

    def wdt_enable(self, timeout: int):
        pass

    def wdt_reset(self):
        pass


def get_hal(target: str) -> HALBase:
    t = target.lower()
    if "stm32" in t:
        return STM32HAL()
    if "esp32" in t:
        return ESP32HAL()
    if "rp2040" in t or "pico" in t:
        return RP2040HAL()
    if "avr" in t or "atmega" in t or "arduino" in t:
        return AVRHAL()
    return HALBase(target)

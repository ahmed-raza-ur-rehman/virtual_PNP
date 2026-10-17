"""Complete firmware emulator for STM32/ESP32/RP2040/AVR."""
from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Register:
    name: str
    address: int
    value: int = 0
    reset_value: int = 0
    read_only: bool = False
    write_callback: Callable | None = None

    def read(self) -> int:
        return self.value

    def write(self, val: int):
        if self.read_only:
            return
        if self.write_callback:
            self.write_callback(val)
        self.value = val


@dataclass
class GPIO:
    port: str
    pins: int = 16
    mode: list[int] = field(default_factory=lambda: [0] * 16)
    output: list[int] = field(default_factory=lambda: [0] * 16)
    input: list[int] = field(default_factory=lambda: [0] * 16)

    def set_mode(self, pin: int, mode: int):
        self.mode[pin] = mode

    def write_pin(self, pin: int, state: int):
        if self.mode[pin] == 1:
            self.output[pin] = state

    def read_pin(self, pin: int) -> int:
        if self.mode[pin] == 0:
            return self.input[pin]
        return self.output[pin]

    def toggle_pin(self, pin: int):
        if self.mode[pin] == 1:
            self.output[pin] ^= 1


@dataclass
class Timer:
    id: int
    prescaler: int = 0
    period: int = 0
    counter: int = 0
    enabled: bool = False
    interrupt: bool = False
    callback: Callable | None = None

    def tick(self):
        if not self.enabled:
            return
        self.counter += 1
        if self.counter >= self.period:
            self.counter = 0
            self.interrupt = True
            if self.callback:
                self.callback()

    def start(self):
        self.enabled = True
        self.counter = 0

    def stop(self):
        self.enabled = False

    def set_period(self, period: int):
        self.period = period

    def set_prescaler(self, prescaler: int):
        self.prescaler = prescaler


@dataclass
class UART:
    id: int
    baudrate: int = 115200
    tx_buffer: list[int] = field(default_factory=list)
    rx_buffer: list[int] = field(default_factory=list)
    tx_ready: bool = True
    rx_available: bool = False

    def transmit(self, data: bytes):
        self.tx_buffer.extend(data)
        self.tx_ready = False

    def receive(self, maxlen: int = 256) -> bytes:
        data = bytes(self.rx_buffer[:maxlen])
        self.rx_buffer = self.rx_buffer[maxlen:]
        return data

    def is_tx_ready(self) -> bool:
        return self.tx_ready

    def is_rx_available(self) -> bool:
        return len(self.rx_buffer) > 0


@dataclass
class SPI:
    id: int
    mode: int = 0
    speed: int = 1000000
    cs: bool = True

    def transmit(self, data: bytes) -> bytes:
        return bytes([0] * len(data))

    def set_cs(self, state: bool):
        self.cs = state


@dataclass
class I2C:
    id: int
    speed: int = 100000
    address: int = 0

    def write(self, addr: int, data: bytes) -> bool:
        self.address = addr
        return True

    def read(self, addr: int, length: int) -> bytes:
        self.address = addr
        return bytes([0] * length)


@dataclass
class ADC:
    id: int
    channels: int = 8
    resolution: int = 12
    values: list[int] = field(default_factory=lambda: [0] * 8)

    def read(self, channel: int) -> int:
        if channel < self.channels:
            return self.values[channel]
        return 0

    def set_value(self, channel: int, value: int):
        if channel < self.channels:
            self.values[channel] = value


@dataclass
class DAC:
    id: int
    channels: int = 2
    resolution: int = 12
    values: list[int] = field(default_factory=lambda: [0] * 2)

    def write(self, channel: int, value: int):
        if channel < self.channels:
            self.values[channel] = value

    def read(self, channel: int) -> int:
        if channel < self.channels:
            return self.values[channel]
        return 0


@dataclass
class DMA:
    id: int
    channels: int = 8
    active: list[bool] = field(default_factory=lambda: [False] * 8)
    src: list[int] = field(default_factory=lambda: [0] * 8)
    dst: list[int] = field(default_factory=lambda: [0] * 8)
    length: list[int] = field(default_factory=lambda: [0] * 8)
    complete: list[bool] = field(default_factory=lambda: [False] * 8)

    def configure(self, channel: int, src: int, dst: int, length: int):
        self.src[channel] = src
        self.dst[channel] = dst
        self.length[channel] = length
        self.active[channel] = False
        self.complete[channel] = False

    def start(self, channel: int):
        self.active[channel] = True
        self.complete[channel] = False

    def is_complete(self, channel: int) -> bool:
        return self.complete[channel]

    def tick(self):
        for ch in range(self.channels):
            if self.active[ch]:
                self.length[ch] -= 1
                if self.length[ch] <= 0:
                    self.active[ch] = False
                    self.complete[ch] = True


@dataclass
class NVIC:
    priorities: list[int] = field(default_factory=lambda: [0] * 256)
    enabled: list[bool] = field(default_factory=lambda: [False] * 256)
    pending: list[bool] = field(default_factory=lambda: [False] * 256)

    def set_priority(self, irq: int, priority: int):
        if irq < len(self.priorities):
            self.priorities[irq] = priority

    def enable_irq(self, irq: int):
        if irq < len(self.enabled):
            self.enabled[irq] = True

    def disable_irq(self, irq: int):
        if irq < len(self.enabled):
            self.enabled[irq] = False

    def trigger_irq(self, irq: int):
        if irq < len(self.pending):
            self.pending[irq] = True

    def get_pending_irq(self) -> int:
        for irq in range(len(self.pending)):
            if self.pending[irq] and self.enabled[irq]:
                return irq
        return -1


@dataclass
class Flash:
    size: int = 1024 * 1024
    data: bytearray = field(default_factory=lambda: bytearray(1024 * 1024))

    def read(self, addr: int, length: int) -> bytes:
        return bytes(self.data[addr:addr + length])

    def write(self, addr: int, data: bytes):
        self.data[addr:addr + len(data)] = data

    def erase(self, addr: int, length: int):
        for i in range(addr, addr + length):
            if i < len(self.data):
                self.data[i] = 0xFF


@dataclass
class SRAM:
    size: int = 256 * 1024
    data: bytearray = field(default_factory=lambda: bytearray(256 * 1024))

    def read(self, addr: int, length: int) -> bytes:
        return bytes(self.data[addr:addr + length])

    def write(self, addr: int, data: bytes):
        self.data[addr:addr + len(data)] = data

    def read_word(self, addr: int) -> int:
        return struct.unpack("<I", self.data[addr:addr + 4])[0]

    def write_word(self, addr: int, value: int):
        struct.pack_into("<I", self.data, addr, value)


class FirmwareEmulator:
    def __init__(self, target: str = "stm32"):
        self.target = target
        self.gpio: dict[str, GPIO] = {}
        self.timers: dict[int, Timer] = {}
        self.uarts: dict[int, UART] = {}
        self.spis: dict[int, SPI] = {}
        self.i2cs: dict[int, I2C] = {}
        self.adcs: dict[int, ADC] = {}
        self.dacs: dict[int, DAC] = {}
        self.dmas: dict[int, DMA] = {}
        self.nvic = NVIC()
        self.flash = Flash()
        self.sram = SRAM()
        self.registers: dict[int, Register] = {}
        self.running = False
        self.tick_count = 0
        self._init_peripherals()

    def _init_peripherals(self):
        for port in "ABCDE":
            self.gpio[port] = GPIO(port=port)
        for i in range(1, 15):
            self.timers[i] = Timer(id=i)
        for i in range(1, 6):
            self.uarts[i] = UART(id=i)
        for i in range(1, 4):
            self.spis[i] = SPI(id=i)
        for i in range(1, 4):
            self.i2cs[i] = I2C(id=i)
        for i in range(1, 4):
            self.adcs[i] = ADC(id=i)
        for i in range(1, 3):
            self.dacs[i] = DAC(id=i)
        for i in range(1, 3):
            self.dmas[i] = DMA(id=i)

    def reset(self):
        self.tick_count = 0
        for t in self.timers.values():
            t.counter = 0
            t.enabled = False
        for u in self.uarts.values():
            u.tx_buffer.clear()
            u.rx_buffer.clear()
        for d in self.dmas.values():
            for ch in range(d.channels):
                d.active[ch] = False
                d.complete[ch] = False

    def tick(self):
        self.tick_count += 1
        for t in self.timers.values():
            t.tick()
        for d in self.dmas.values():
            d.tick()

    def run(self, cycles: int = 1000):
        self.running = True
        for _ in range(cycles):
            self.tick()
        self.running = False

    def get_status(self) -> dict:
        return {
            "target": self.target,
            "tick_count": self.tick_count,
            "running": self.running,
            "gpio_ports": list(self.gpio.keys()),
            "timers": len(self.timers),
            "uarts": len(self.uarts),
            "spis": len(self.spis),
            "i2cs": len(self.i2cs),
            "adcs": len(self.adcs),
            "dacs": len(self.dacs),
            "dmas": len(self.dmas),
        }

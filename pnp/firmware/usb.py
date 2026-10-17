"""USB device/host emulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class USBDescriptor:
    bLength: int = 18
    bDescriptorType: int = 1
    bcdUSB: int = 0x0200
    bDeviceClass: int = 0
    bDeviceSubClass: int = 0
    bDeviceProtocol: int = 0
    bMaxPacketSize0: int = 64
    idVendor: int = 0x1234
    idProduct: int = 0x5678
    bcdDevice: int = 0x0100
    iManufacturer: int = 0
    iProduct: int = 0
    iSerialNumber: int = 0
    bNumConfigurations: int = 1


class USBDevice:
    def __init__(self, vid: int = 0x1234, pid: int = 0x5678):
        self.vid = vid
        self.pid = pid
        self.state = "disconnected"  # disconnected, attached, powered, default, addressed, configured
        self.address = 0
        self.configured = False
        self.endpoints: dict[int, dict[str, Any]] = {}
        self.rx_buffers: dict[int, bytearray] = {}
        self.tx_buffers: dict[int, bytearray] = {}
        self.descriptor = USBDescriptor(idVendor=vid, idProduct=pid)
        self.suspended = False
        self.remote_wakeup = False

    def connect(self):
        self.state = "attached"

    def disconnect(self):
        self.state = "disconnected"
        self.configured = False

    def set_address(self, addr: int):
        self.address = addr
        self.state = "addressed"

    def set_configuration(self, config: int):
        self.configured = True
        self.state = "configured"

    def add_endpoint(self, ep: int, direction: str, transfer_type: str, max_packet: int):
        self.endpoints[ep] = {"direction": direction, "type": transfer_type, "max_packet": max_packet}
        self.rx_buffers[ep] = bytearray()
        self.tx_buffers[ep] = bytearray()

    def endpoint_write(self, ep: int, data: bytes):
        if ep in self.tx_buffers:
            self.tx_buffers[ep].extend(data)

    def endpoint_read(self, ep: int, length: int) -> bytes:
        if ep in self.rx_buffers:
            buf = self.rx_buffers[ep]
            data = bytes(buf[:length])
            del buf[:length]
            return data
        return b""

    def endpoint_inject(self, ep: int, data: bytes):
        if ep in self.rx_buffers:
            self.rx_buffers[ep].extend(data)

    def suspend(self):
        self.suspended = True

    def resume(self):
        self.suspended = False

    def get_status(self) -> dict[str, Any]:
        return {
            "vid": self.vid, "pid": self.pid, "state": self.state,
            "address": self.address, "configured": self.configured,
            "endpoints": len(self.endpoints), "suspended": self.suspended,
        }


class USBHost:
    def __init__(self):
        self.devices: list[USBDevice] = []
        self.port_status: dict[int, bool] = {}

    def enumerate(self) -> list[dict[str, Any]]:
        return [d.get_status() for d in self.devices]

    def attach(self, device: USBDevice):
        device.connect()
        self.devices.append(device)

    def detach(self, device: USBDevice):
        device.disconnect()
        if device in self.devices:
            self.devices.remove(device)

    def control_transfer(self, device: USBDevice, request: bytes) -> bytes:
        return b""

    def bulk_transfer(self, device: USBDevice, ep: int, data: bytes, timeout: int = 1000) -> int:
        device.endpoint_write(ep, data)
        return len(data)

    def interrupt_transfer(self, device: USBDevice, ep: int, length: int, timeout: int = 1000) -> bytes:
        return device.endpoint_read(ep, length)

"""CAN bus controller emulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CANFrame:
    id: int
    dlc: int = 0
    data: bytes = b""
    extended: bool = False
    rtr: bool = False
    timestamp: int = 0


class CANController:
    def __init__(self, id: int = 1, bitrate: int = 500000):
        self.id = id
        self.bitrate = bitrate
        self.rx_fifo: list[CANFrame] = []
        self.tx_mailbox: list[CANFrame] = []
        self.filters: list[tuple[int, int]] = []
        self.error_count = 0
        self.state = "active"  # active, error_passive, bus_off
        self.loopback = False
        self.silent = False

    def set_bitrate(self, bitrate: int):
        self.bitrate = bitrate

    def add_filter(self, mask: int, id: int):
        self.filters.append((mask, id))

    def transmit(self, frame: CANFrame) -> bool:
        if self.state == "bus_off":
            return False
        self.tx_mailbox.append(frame)
        if self.loopback:
            self.rx_fifo.append(frame)
        return True

    def receive(self) -> CANFrame | None:
        if self.rx_fifo:
            return self.rx_fifo.pop(0)
        return None

    def rx_available(self) -> bool:
        return len(self.rx_fifo) > 0

    def tx_ready(self) -> bool:
        return len(self.tx_mailbox) < 3

    def inject_frame(self, frame: CANFrame):
        # check filters
        accepted = True
        if self.filters:
            accepted = False
            for mask, fid in self.filters:
                if (frame.id & mask) == (fid & mask):
                    accepted = True
                    break
        if accepted:
            self.rx_fifo.append(frame)

    def error_increment(self, count: int = 1):
        self.error_count += count
        if self.error_count > 255:
            self.state = "bus_off"
        elif self.error_count > 127:
            self.state = "error_passive"

    def error_decrement(self, count: int = 1):
        self.error_count = max(0, self.error_count - count)
        if self.error_count <= 127:
            self.state = "active"

    def reset(self):
        self.rx_fifo.clear()
        self.tx_mailbox.clear()
        self.error_count = 0
        self.state = "active"

    def get_status(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "bitrate": self.bitrate,
            "state": self.state,
            "error_count": self.error_count,
            "rx_pending": len(self.rx_fifo),
            "tx_pending": len(self.tx_mailbox),
            "filters": len(self.filters),
        }


class CANBus:
    """Multi-node CAN bus simulator."""
    def __init__(self):
        self.nodes: list[CANController] = []
        self.message_log: list[CANFrame] = []

    def add_node(self, node: CANController):
        self.nodes.append(node)

    def broadcast(self, sender: CANController, frame: CANFrame):
        self.message_log.append(frame)
        for node in self.nodes:
            if node is not sender:
                node.inject_frame(frame)

    def send(self, sender: CANController, frame: CANFrame) -> bool:
        ok = sender.transmit(frame)
        if ok:
            self.broadcast(sender, frame)
        return ok

    def get_log(self) -> list[CANFrame]:
        return list(self.message_log)

    def clear_log(self):
        self.message_log.clear()

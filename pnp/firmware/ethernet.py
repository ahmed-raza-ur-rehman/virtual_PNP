"""Ethernet MAC/PHY emulation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EthernetFrame:
    dst_mac: bytes
    src_mac: bytes
    ethertype: int
    payload: bytes
    fcs: int = 0

    def to_bytes(self) -> bytes:
        return self.dst_mac + self.src_mac + self.ethertype.to_bytes(2, "big") + self.payload

    @staticmethod
    def from_bytes(data: bytes) -> EthernetFrame:
        dst = data[0:6]
        src = data[6:12]
        et = int.from_bytes(data[12:14], "big")
        payload = data[14:]
        return EthernetFrame(dst_mac=dst, src_mac=src, ethertype=et, payload=payload)


class EthernetMAC:
    def __init__(self, mac: bytes = b"\x00\x11\x22\x33\x44\x55"):
        self.mac = mac
        self.rx_queue: list[EthernetFrame] = []
        self.tx_queue: list[EthernetFrame] = []
        self.promiscuous = False
        self.multicast_filter: list[bytes] = []
        self.link_up = True
        self.speed = 100  # Mbps
        self.duplex = "full"
        self.stats = {"rx_packets": 0, "tx_packets": 0, "rx_bytes": 0, "tx_bytes": 0,
                      "rx_errors": 0, "tx_errors": 0, "collisions": 0}

    def set_mac(self, mac: bytes):
        self.mac = mac

    def transmit(self, frame: EthernetFrame) -> bool:
        if not self.link_up:
            return False
        self.tx_queue.append(frame)
        self.stats["tx_packets"] += 1
        self.stats["tx_bytes"] += len(frame.to_bytes())
        return True

    def receive(self) -> EthernetFrame | None:
        if self.rx_queue:
            f = self.rx_queue.pop(0)
            self.stats["rx_packets"] += 1
            self.stats["rx_bytes"] += len(f.to_bytes())
            return f
        return None

    def inject_frame(self, frame: EthernetFrame):
        if self._accept(frame):
            self.rx_queue.append(frame)

    def _accept(self, frame: EthernetFrame) -> bool:
        if self.promiscuous:
            return True
        if frame.dst_mac == self.mac:
            return True
        if frame.dst_mac == b"\xff\xff\xff\xff\xff\xff":
            return True
        if frame.dst_mac[0] & 0x01:
            return frame.dst_mac in self.multicast_filter
        return False

    def set_link(self, up: bool):
        self.link_up = up

    def set_speed(self, speed: int):
        self.speed = speed

    def add_multicast(self, mac: bytes):
        self.multicast_filter.append(mac)

    def get_stats(self) -> dict[str, Any]:
        return dict(self.stats)

    def reset_stats(self):
        for k in self.stats:
            self.stats[k] = 0


class IPPacket:
    def __init__(self, src: str, dst: str, protocol: int, payload: bytes, ttl: int = 64):
        self.src = src
        self.dst = dst
        self.protocol = protocol
        self.payload = payload
        self.ttl = ttl
        self.id = 0
        self.flags = 0
        self.fragment_offset = 0

    def to_bytes(self) -> bytes:
        import struct
        header = struct.pack("!BBHHHBBH4s4s", 4 << 4 | 5, 0, 20 + len(self.payload),
                            self.id, self.flags << 13 | self.fragment_offset,
                            self.ttl, self.protocol, 0,
                            bytes(map(int, self.src.split("."))),
                            bytes(map(int, self.dst.split("."))))
        return header + self.payload

    @staticmethod
    def from_bytes(data: bytes) -> IPPacket:
        import struct
        _ver_ihl, _tos, total_len, ident, flags_frag, ttl, proto, _checksum, src, dst = struct.unpack("!BBHHHBBH4s4s", data[:20])
        payload = data[20:total_len]
        src_str = ".".join(str(b) for b in src)
        dst_str = ".".join(str(b) for b in dst)
        p = IPPacket(src_str, dst_str, proto, payload, ttl)
        p.id = ident
        p.flags = flags_frag >> 13
        p.fragment_offset = flags_frag & 0x1fff
        return p


class UDPSocket:
    def __init__(self, port: int):
        self.port = port
        self.rx_queue: list[tuple[str, int, bytes]] = []
        self.bound = False

    def bind(self, port: int):
        self.port = port
        self.bound = True

    def send_to(self, data: bytes, dst_ip: str, dst_port: int):
        pass

    def recv_from(self, bufsize: int = 1024) -> tuple[bytes, str, int] | None:
        if self.rx_queue:
            data, ip, port = self.rx_queue.pop(0)
            return data[:bufsize], ip, port
        return None

    def inject(self, data: bytes, src_ip: str, src_port: int):
        self.rx_queue.append((src_ip, src_port, data))


class TCPSocket:
    def __init__(self):
        self.state = "CLOSED"
        self.local_port = 0
        self.remote_ip = ""
        self.remote_port = 0
        self.seq = 0
        self.ack = 0
        self.rx_buffer = bytearray()
        self.tx_buffer = bytearray()
        self.window = 65535

    def connect(self, ip: str, port: int) -> bool:
        self.remote_ip = ip
        self.remote_port = port
        self.state = "ESTABLISHED"
        return True

    def listen(self, port: int, backlog: int = 5):
        self.local_port = port
        self.state = "LISTEN"

    def accept(self) -> TCPSocket | None:
        if self.state == "LISTEN":
            s = TCPSocket()
            s.state = "ESTABLISHED"
            s.local_port = self.local_port
            return s
        return None

    def send(self, data: bytes) -> int:
        if self.state == "ESTABLISHED":
            self.tx_buffer.extend(data)
            return len(data)
        return 0

    def recv(self, bufsize: int = 1024) -> bytes:
        data = bytes(self.rx_buffer[:bufsize])
        self.rx_buffer = self.rx_buffer[bufsize:]
        return data

    def close(self):
        self.state = "CLOSED"

    def inject_data(self, data: bytes):
        self.rx_buffer.extend(data)

"""WebSocket server simulation (stdlib-based)."""
from __future__ import annotations

import json
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WebSocketClient:
    id: str
    connected: bool = True
    subscriptions: set[str] = field(default_factory=set)
    last_ping: float = 0.0


class WebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: dict[str, WebSocketClient] = {}
        self.handlers: dict[str, Callable] = {}
        self.broadcast_queue: list[dict[str, Any]] = []
        self.running = False
        self._lock = threading.Lock()

    def register_handler(self, msg_type: str, handler: Callable):
        self.handlers[msg_type] = handler

    def connect(self, client_id: str) -> WebSocketClient:
        c = WebSocketClient(id=client_id, connected=True, last_ping=time.time())
        self.clients[client_id] = c
        return c

    def disconnect(self, client_id: str):
        if client_id in self.clients:
            self.clients[client_id].connected = False
            del self.clients[client_id]

    def subscribe(self, client_id: str, topic: str):
        if client_id in self.clients:
            self.clients[client_id].subscriptions.add(topic)

    def unsubscribe(self, client_id: str, topic: str):
        if client_id in self.clients:
            self.clients[client_id].subscriptions.discard(topic)

    def handle_message(self, client_id: str, raw: str) -> dict[str, Any] | None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "invalid json"}
        msg_type = msg.get("type", "")
        handler = self.handlers.get(msg_type)
        if handler:
            return handler(client_id, msg)
        return {"type": "ack", "original": msg_type}

    def broadcast(self, topic: str, data: dict[str, Any]):
        msg = {"type": "broadcast", "topic": topic, "data": data, "timestamp": time.time()}
        self.broadcast_queue.append(msg)
        for cid, client in list(self.clients.items()):
            if topic in client.subscriptions or topic == "*":
                pass  # would send over socket

    def send_to(self, client_id: str, data: dict[str, Any]):
        if client_id in self.clients:
            pass  # would send over socket

    def ping_all(self):
        now = time.time()
        for cid, client in list(self.clients.items()):
            if now - client.last_ping > 30:
                self.disconnect(cid)
            else:
                client.last_ping = now

    def get_stats(self) -> dict[str, Any]:
        return {
            "clients": len(self.clients),
            "topics": len(set().union(*[c.subscriptions for c in self.clients.values()])) if self.clients else 0,
            "queued_messages": len(self.broadcast_queue),
            "handlers": list(self.handlers.keys()),
        }

    def encode_frame(self, data: str) -> bytes:
        # WebSocket frame encoding (text)
        payload = data.encode()
        frame = bytearray()
        frame.append(0x81)  # FIN + text
        if len(payload) < 126:
            frame.append(len(payload))
        elif len(payload) < 65536:
            frame.append(126)
            frame.extend(struct.pack(">H", len(payload)))
        else:
            frame.append(127)
            frame.extend(struct.pack(">Q", len(payload)))
        frame.extend(payload)
        return bytes(frame)

    def decode_frame(self, data: bytes) -> str:
        if len(data) < 2:
            return ""
        # simplified: assume no masking, text frame
        length = data[1] & 0x7F
        offset = 2
        if length == 126:
            length = struct.unpack(">H", data[2:4])[0]
            offset = 4
        elif length == 127:
            length = struct.unpack(">Q", data[2:10])[0]
            offset = 10
        return data[offset:offset+length].decode(errors="replace")


class RealTimeDataStreamer:
    def __init__(self, ws: WebSocketServer):
        self.ws = ws
        self.streams: dict[str, Callable] = {}
        self.running = False
        self.thread = None

    def add_stream(self, topic: str, source: Callable):
        self.streams[topic] = source

    def start(self, interval: float = 0.1):
        self.running = True
        def loop():
            while self.running:
                for topic, source in self.streams.items():
                    try:
                        data = source()
                        self.ws.broadcast(topic, data)
                    except (ValueError, RuntimeError):
                        pass
                time.sleep(interval)
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

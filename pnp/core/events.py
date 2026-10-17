"""Event system for decoupled communication."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    source: str = ""
    priority: int = 0


class EventBus:
    def __init__(self):
        self.subscribers: dict[str, list[Callable]] = defaultdict(list)
        self.queue: deque[Event] = deque()
        self.history: deque[Event] = deque(maxlen=10000)
        self._lock = threading.Lock()

    def subscribe(self, event_name: str, handler: Callable):
        self.subscribers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable):
        if handler in self.subscribers[event_name]:
            self.subscribers[event_name].remove(handler)

    def publish(self, event: Event):
        event.timestamp = time.time()
        with self._lock:
            self.queue.append(event)
            self.history.append(event)

    def dispatch(self, event: Event):
        handlers = self.subscribers.get(event.name, [])
        for h in handlers:
            try:
                h(event)
            except (ValueError, RuntimeError):
                pass
        # wildcard subscribers
        for h in self.subscribers.get("*", []):
            try:
                h(event)
            except (ValueError, RuntimeError):
                pass

    def process_queue(self):
        while self.queue:
            event = self.queue.popleft()
            self.dispatch(event)

    def publish_and_dispatch(self, event: Event):
        event.timestamp = time.time()
        self.dispatch(event)
        self.history.append(event)

    def get_history(self, event_name: str | None = None, n: int = 100) -> list[Event]:
        if event_name:
            return [e for e in self.history if e.name == event_name][-n:]
        return list(self.history)[-n:]

    def clear(self):
        self.queue.clear()
        self.subscribers.clear()


class EventScheduler:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.scheduled: list[tuple[float, Event]] = []
        self.time = 0.0

    def schedule(self, event: Event, delay: float):
        self.scheduled.append((self.time + delay, event))
        self.scheduled.sort(key=lambda x: x[0])

    def schedule_at(self, event: Event, time: float):
        self.scheduled.append((time, event))
        self.scheduled.sort(key=lambda x: x[0])

    def tick(self, dt: float):
        self.time += dt
        while self.scheduled and self.scheduled[0][0] <= self.time:
            _, event = self.scheduled.pop(0)
            self.bus.publish(event)

    def cancel(self, event_name: str):
        self.scheduled = [(t, e) for t, e in self.scheduled if e.name != event_name]


class EventLogger:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.log: list[Event] = []
        bus.subscribe("*", self._on_event)

    def _on_event(self, event: Event):
        self.log.append(event)

    def get_log(self, n: int = 100) -> list[Event]:
        return self.log[-n:]

    def clear(self):
        self.log.clear()

    def export(self) -> str:
        import json
        return json.dumps([{"name": e.name, "payload": e.payload, "timestamp": e.timestamp, "source": e.source} for e in self.log], indent=2)

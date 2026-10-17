"""Real-time operating system (RTOS) kernel for embedded firmware."""
from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    name: str
    priority: int
    stack_size: int = 256
    state: str = "ready"  # ready, running, blocked, suspended
    period_ms: int = 0
    deadline_ms: int = 0
    cpu_time: int = 0
    entry: Callable | None = None
    stack: list[int] = field(default_factory=list)
    tid: int = 0


class RTOSKernel:
    def __init__(self, tick_rate_hz: int = 1000):
        self.tick_rate_hz = tick_rate_hz
        self.tasks: list[Task] = []
        self.current_task: Task | None = None
        self.ready_queue: list[Task] = []
        self.blocked_list: list[Task] = []
        self.delayed_list: list[tuple[int, Task]] = []
        self.mutexes: dict[str, Mutex] = {}
        self.semaphores: dict[str, Semaphore] = {}
        self.queues: dict[str, MessageQueue] = {}
        self.tick_count = 0
        self.context_switches = 0
        self.idle_hooks: list[Callable] = []
        self.tick_hooks: list[Callable] = []

    def create_task(self, task: Task) -> int:
        task.tid = len(self.tasks)
        self.tasks.append(task)
        self.ready_queue.append(task)
        return task.tid

    def delete_task(self, tid: int):
        self.tasks = [t for t in self.tasks if t.tid != tid]
        self.ready_queue = [t for t in self.ready_queue if t.tid != tid]

    def suspend_task(self, tid: int):
        for t in self.tasks:
            if t.tid == tid:
                t.state = "suspended"
                self.ready_queue = [x for x in self.ready_queue if x.tid != tid]

    def resume_task(self, tid: int):
        for t in self.tasks:
            if t.tid == tid:
                t.state = "ready"
                if t not in self.ready_queue:
                    self.ready_queue.append(t)

    def delay_task(self, tid: int, ticks: int):
        for t in self.tasks:
            if t.tid == tid:
                t.state = "blocked"
                self.ready_queue = [x for x in self.ready_queue if x.tid != tid]
                heapq.heappush(self.delayed_list, (self.tick_count + ticks, t))

    def schedule(self):
        if not self.ready_queue:
            # run idle
            for h in self.idle_hooks:
                h()
            return None
        # highest priority (lower number = higher priority)
        self.ready_queue.sort(key=lambda t: t.priority)
        next_task = self.ready_queue.pop(0)
        if self.current_task is not None and self.current_task.state == "running":
            self.current_task.state = "ready"
            self.ready_queue.append(self.current_task)
        next_task.state = "running"
        self.current_task = next_task
        self.context_switches += 1
        return next_task

    def tick(self):
        self.tick_count += 1
        # wake delayed tasks
        while self.delayed_list and self.delayed_list[0][0] <= self.tick_count:
            _, t = heapq.heappop(self.delayed_list)
            t.state = "ready"
            if t not in self.ready_queue:
                self.ready_queue.append(t)
        for h in self.tick_hooks:
            h()
        self.schedule()

    def run(self, ticks: int = 1000):
        for _ in range(ticks):
            self.tick()

    def create_mutex(self, name: str):
        self.mutexes[name] = Mutex(name)

    def create_semaphore(self, name: str, initial: int = 1, max_count: int = 1):
        self.semaphores[name] = Semaphore(name, initial, max_count)

    def create_queue(self, name: str, size: int = 16):
        self.queues[name] = MessageQueue(name, size)

    def mutex_lock(self, name: str, timeout: int = -1) -> bool:
        m = self.mutexes.get(name)
        if m is None:
            return False
        return m.lock(self.current_task, timeout)

    def mutex_unlock(self, name: str):
        m = self.mutexes.get(name)
        if m is not None:
            m.unlock(self.current_task)

    def sem_take(self, name: str, timeout: int = -1) -> bool:
        s = self.semaphores.get(name)
        if s is None:
            return False
        return s.take(self.current_task, timeout)

    def sem_give(self, name: str):
        s = self.semaphores.get(name)
        if s is not None:
            s.give()

    def queue_send(self, name: str, msg: Any, timeout: int = -1) -> bool:
        q = self.queues.get(name)
        if q is None:
            return False
        return q.send(msg, timeout)

    def queue_receive(self, name: str, timeout: int = -1) -> Any:
        q = self.queues.get(name)
        if q is None:
            return None
        return q.receive(timeout)

    def get_stats(self) -> dict[str, Any]:
        return {
            "tick_count": self.tick_count,
            "num_tasks": len(self.tasks),
            "context_switches": self.context_switches,
            "ready": len(self.ready_queue),
            "blocked": len(self.blocked_list),
            "delayed": len(self.delayed_list),
        }


@dataclass
class Mutex:
    name: str
    owner: Task | None = None
    locked: bool = False
    waiters: list[Task] = field(default_factory=list)
    priority_ceiling: int = 0

    def lock(self, task: Task | None, timeout: int = -1) -> bool:
        if not self.locked:
            self.locked = True
            self.owner = task
            return True
        if task is not None and task in self.waiters:
            return False
        if task is not None:
            self.waiters.append(task)
            if task is not None:
                task.state = "blocked"
        return False

    def unlock(self, task: Task | None):
        if self.owner is task or self.owner is None:
            self.locked = False
            self.owner = None
            if self.waiters:
                w = self.waiters.pop(0)
                w.state = "ready"
                self.locked = True
                self.owner = w

    def is_locked(self) -> bool:
        return self.locked


@dataclass
class Semaphore:
    name: str
    count: int = 1
    max_count: int = 1
    waiters: list[Task] = field(default_factory=list)

    def take(self, task: Task | None, timeout: int = -1) -> bool:
        if self.count > 0:
            self.count -= 1
            return True
        if task is not None:
            self.waiters.append(task)
            if task is not None:
                task.state = "blocked"
        return False

    def give(self):
        if self.waiters:
            w = self.waiters.pop(0)
            w.state = "ready"
        else:
            if self.count < self.max_count:
                self.count += 1

    def get_count(self) -> int:
        return self.count


@dataclass
class MessageQueue:
    name: str
    size: int = 16
    buffer: list[Any] = field(default_factory=list)
    send_waiters: list[Task] = field(default_factory=list)
    recv_waiters: list[Task] = field(default_factory=list)

    def send(self, msg: Any, timeout: int = -1) -> bool:
        if len(self.buffer) < self.size:
            self.buffer.append(msg)
            if self.recv_waiters:
                w = self.recv_waiters.pop(0)
                w.state = "ready"
            return True
        return False

    def receive(self, timeout: int = -1) -> Any:
        if self.buffer:
            msg = self.buffer.pop(0)
            if self.send_waiters:
                w = self.send_waiters.pop(0)
                w.state = "ready"
            return msg
        return None

    def is_empty(self) -> bool:
        return len(self.buffer) == 0

    def is_full(self) -> bool:
        return len(self.buffer) >= self.size

    def count(self) -> int:
        return len(self.buffer)


class MemoryManager:
    """Simple heap allocator for RTOS."""
    def __init__(self, size: int = 65536):
        self.size = size
        self.memory = bytearray(size)
        self.free_list: list[tuple[int, int]] = [(0, size)]
        self.allocated: dict[int, int] = {}

    def malloc(self, size: int) -> int | None:
        for i, (start, length) in enumerate(self.free_list):
            if length >= size:
                self.free_list.pop(i)
                if length > size:
                    self.free_list.append((start + size, length - size))
                self.allocated[start] = size
                return start
        return None

    def free(self, ptr: int):
        size = self.allocated.pop(ptr, 0)
        if size:
            self.free_list.append((ptr, size))
            self._coalesce()

    def _coalesce(self):
        self.free_list.sort()
        merged = []
        for start, length in self.free_list:
            if merged and merged[-1][0] + merged[-1][1] == start:
                merged[-1] = (merged[-1][0], merged[-1][1] + length)
            else:
                merged.append((start, length))
        self.free_list = merged

    def usage(self) -> dict[str, int]:
        used = sum(self.allocated.values())
        return {"total": self.size, "used": used, "free": self.size - used, "blocks": len(self.allocated)}

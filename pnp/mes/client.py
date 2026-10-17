"""Manufacturing Execution System (MES) client."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkOrder:
    id: str
    product: str
    quantity: int
    priority: int = 0
    status: str = "pending"  # pending, in_progress, completed, cancelled
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    components: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceRecord:
    serial_number: str
    work_order: str
    timestamp: float
    event: str
    data: dict[str, Any] = field(default_factory=dict)


class MESClient:
    def __init__(self, endpoint: str = "http://localhost:8080"):
        self.endpoint = endpoint
        self.work_orders: dict[str, WorkOrder] = {}
        self.trace_records: list[TraceRecord] = []
        self.inventory: dict[str, int] = {}
        self.quality_records: list[dict[str, Any]] = []

    def create_work_order(self, wo: WorkOrder) -> str:
        if wo.created_at == 0:
            wo.created_at = time.time()
        self.work_orders[wo.id] = wo
        return wo.id

    def get_work_order(self, wo_id: str) -> WorkOrder | None:
        return self.work_orders.get(wo_id)

    def start_work_order(self, wo_id: str) -> bool:
        wo = self.work_orders.get(wo_id)
        if wo is None or wo.status != "pending":
            return False
        wo.status = "in_progress"
        wo.started_at = time.time()
        return True

    def complete_work_order(self, wo_id: str) -> bool:
        wo = self.work_orders.get(wo_id)
        if wo is None or wo.status != "in_progress":
            return False
        wo.status = "completed"
        wo.completed_at = time.time()
        return True

    def cancel_work_order(self, wo_id: str) -> bool:
        wo = self.work_orders.get(wo_id)
        if wo is None:
            return False
        wo.status = "cancelled"
        return True

    def list_work_orders(self, status: str | None = None) -> list[WorkOrder]:
        out = list(self.work_orders.values())
        if status:
            out = [w for w in out if w.status == status]
        return out

    def trace(self, serial_number: str, work_order: str, event: str, data: dict[str, Any] | None = None):
        rec = TraceRecord(serial_number=serial_number, work_order=work_order, timestamp=time.time(), event=event, data=data or {})
        self.trace_records.append(rec)

    def get_trace(self, serial_number: str) -> list[TraceRecord]:
        return [r for r in self.trace_records if r.serial_number == serial_number]

    def update_inventory(self, part: str, quantity: int):
        self.inventory[part] = self.inventory.get(part, 0) + quantity

    def get_inventory(self, part: str) -> int:
        return self.inventory.get(part, 0)

    def check_inventory(self, parts: dict[str, int]) -> bool:
        for part, qty in parts.items():
            if self.inventory.get(part, 0) < qty:
                return False
        return True

    def consume_inventory(self, parts: dict[str, int]) -> bool:
        if not self.check_inventory(parts):
            return False
        for part, qty in parts.items():
            self.inventory[part] -= qty
        return True

    def record_quality(self, serial_number: str, test: str, result: str, value: float | None = None):
        self.quality_records.append({
            "serial_number": serial_number, "test": test, "result": result,
            "value": value, "timestamp": time.time(),
        })

    def get_quality_records(self, serial_number: str) -> list[dict[str, Any]]:
        return [r for r in self.quality_records if r["serial_number"] == serial_number]

    def get_yield(self, product: str) -> float:
        records = [r for r in self.quality_records]
        if not records:
            return 1.0
        passed = sum(1 for r in records if r["result"] == "pass")
        return passed / len(records)

    def report(self) -> str:
        lines = ["MES Report"]
        lines.append(f"  Work orders: {len(self.work_orders)}")
        lines.append(f"  Pending: {sum(1 for w in self.work_orders.values() if w.status=='pending')}")
        lines.append(f"  In progress: {sum(1 for w in self.work_orders.values() if w.status=='in_progress')}")
        lines.append(f"  Completed: {sum(1 for w in self.work_orders.values() if w.status=='completed')}")
        lines.append(f"  Trace records: {len(self.trace_records)}")
        lines.append(f"  Quality records: {len(self.quality_records)}")
        lines.append(f"  Inventory items: {len(self.inventory)}")
        return "\n".join(lines)

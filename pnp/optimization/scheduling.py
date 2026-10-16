"""Multi-head placement scheduling."""
from __future__ import annotations


def schedule_multihead(tasks: list[dict], heads: int = 4) -> list[list[dict]]:
    """Greedy multi-head scheduling: assign each task to the head that becomes free earliest."""
    # tasks: list of {id, duration, ready_time}
    # returns list per head of ordered tasks
    head_free = [0.0] * heads
    head_tasks: list[list[dict]] = [[] for _ in range(heads)]
    # sort tasks by ready_time then duration desc
    ordered = sorted(tasks, key=lambda t: (t.get("ready_time", 0.0), -t.get("duration", 1.0)))
    for t in ordered:
        # pick head with earliest free time >= ready_time
        h = min(range(heads), key=lambda i: max(head_free[i], t.get("ready_time", 0.0)))
        start = max(head_free[h], t.get("ready_time", 0.0))
        t = dict(t)
        t["start"] = start
        t["end"] = start + t.get("duration", 1.0)
        t["head"] = h
        head_tasks[h].append(t)
        head_free[h] = t["end"]
    return head_tasks


def makespan(schedule: list[list[dict]]) -> float:
    return max((t["end"] for head in schedule for t in head), default=0.0)

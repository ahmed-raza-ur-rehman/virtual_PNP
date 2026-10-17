"""State machine framework."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class State:
    name: str
    on_enter: Callable | None = None
    on_exit: Callable | None = None
    on_update: Callable | None = None


@dataclass
class Transition:
    from_state: str
    to_state: str
    condition: Callable | None = None
    action: Callable | None = None


class StateMachine:
    def __init__(self, initial: str):
        self.states: dict[str, State] = {}
        self.transitions: list[Transition] = []
        self.current_state = initial
        self.previous_state = ""
        self.history: list[str] = [initial]
        self.context: dict[str, Any] = {}

    def add_state(self, state: State):
        self.states[state.name] = state

    def add_transition(self, t: Transition):
        self.transitions.append(t)

    def can_transition(self, to_state: str) -> bool:
        for t in self.transitions:
            if t.from_state == self.current_state and t.to_state == to_state and (t.condition is None or t.condition(self.context)):
                    return True
        return False

    def transition(self, to_state: str) -> bool:
        for t in self.transitions:
            if t.from_state == self.current_state and t.to_state == to_state and (t.condition is None or t.condition(self.context)):
                    # exit current
                    cur = self.states.get(self.current_state)
                    if cur and cur.on_exit:
                        cur.on_exit(self.context)
                    # action
                    if t.action:
                        t.action(self.context)
                    # enter new
                    self.previous_state = self.current_state
                    self.current_state = to_state
                    new = self.states.get(to_state)
                    if new and new.on_enter:
                        new.on_enter(self.context)
                    self.history.append(to_state)
                    return True
        return False

    def update(self, dt: float = 0.0):
        s = self.states.get(self.current_state)
        if s and s.on_update:
            s.on_update(self.context, dt)

    def get_current(self) -> str:
        return self.current_state

    def get_history(self) -> list[str]:
        return list(self.history)

    def reset(self, initial: str):
        self.current_state = initial
        self.previous_state = ""
        self.history = [initial]
        self.context.clear()

    def is_in_state(self, state: str) -> bool:
        return self.current_state == state


class HierarchicalStateMachine(StateMachine):
    def __init__(self, initial: str):
        super().__init__(initial)
        self.sub_machines: dict[str, StateMachine] = {}
        self.active_sub = ""

    def add_sub_machine(self, parent_state: str, sm: StateMachine):
        self.sub_machines[parent_state] = sm

    def transition(self, to_state: str) -> bool:
        ok = super().transition(to_state)
        if ok and to_state in self.sub_machines:
            self.active_sub = to_state
        return ok

    def update(self, dt: float = 0.0):
        super().update(dt)
        if self.active_sub and self.active_sub in self.sub_machines:
            self.sub_machines[self.active_sub].update(dt)

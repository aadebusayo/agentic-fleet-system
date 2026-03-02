from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Any


@dataclass
class Checkpoint:
    trace_id: str
    task_id: str
    agent_id: str
    status: str
    timestamp: datetime
    payload: dict[str, Any]


class StateStore(Protocol):
    def put_context(self, session_id: str, context: dict[str, Any]) -> None: ...

    def get_context(self, session_id: str) -> dict[str, Any] | None: ...

    def put_checkpoint(self, checkpoint: Checkpoint) -> None: ...

    def list_checkpoints(self, trace_id: str) -> list[Checkpoint]: ...


class InMemoryStateStore:
    def __init__(self) -> None:
        self._context: dict[str, dict[str, Any]] = {}
        self._checkpoints: dict[str, list[Checkpoint]] = {}

    def put_context(self, session_id: str, context: dict[str, Any]) -> None:
        self._context[session_id] = context

    def get_context(self, session_id: str) -> dict[str, Any] | None:
        return self._context.get(session_id)

    def put_checkpoint(self, checkpoint: Checkpoint) -> None:
        items = self._checkpoints.setdefault(checkpoint.trace_id, [])
        items.append(checkpoint)

    def list_checkpoints(self, trace_id: str) -> list[Checkpoint]:
        return self._checkpoints.get(trace_id, [])

from __future__ import annotations

import threading
from collections import deque

from .schemas import DiagnosticEvent


class EventStore:
    def __init__(self, maxlen: int = 200) -> None:
        self._lock = threading.Lock()
        self._items: deque[DiagnosticEvent] = deque(maxlen=maxlen)

    def add(self, event: DiagnosticEvent) -> None:
        with self._lock:
            self._items.appendleft(event)

    def list(self) -> list[DiagnosticEvent]:
        with self._lock:
            return list(self._items)

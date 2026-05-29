"""Error taxonomy for halt-and-report semantics."""


class AgentRrError(Exception):
    """Base error for agentrr."""


class CorruptEventError(AgentRrError):
    def __init__(self, seq: int, detail: str = "") -> None:
        self.seq = seq
        super().__init__(f"corrupt event at seq {seq}: {detail}")


class IntegrityMismatchError(AgentRrError):
    def __init__(self, seq: int) -> None:
        self.seq = seq
        super().__init__(f"integrity mismatch at seq {seq}")


class UnsupportedLogVersionError(AgentRrError):
    def __init__(self, found: str, supported: str) -> None:
        self.found = found
        self.supported = supported
        super().__init__(f"unsupported log format {found!r} (supported {supported!r})")


class LogExhaustedError(AgentRrError):
    def __init__(self, seq: int) -> None:
        self.seq = seq
        super().__init__(f"log exhausted at seq {seq}")


class DivergenceError(AgentRrError):
    """Strict-mode halt on boundary mismatch."""


class PauseAtBoundary(AgentRrError):
    """Step replay paused after serving a boundary (worker IPC)."""

    def __init__(
        self,
        seq: int,
        event_type: str,
        request: dict,
        response: dict | None,
    ) -> None:
        self.seq = seq
        self.event_type = event_type
        self.request = request
        self.response = response
        super().__init__(f"pause at seq {seq} ({event_type})")

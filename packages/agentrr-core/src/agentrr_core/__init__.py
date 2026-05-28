"""agentrr-core: schemas, log I/O, durability."""

from agentrr_core.durability.gate import persist_before_return
from agentrr_core.errors import AgentRrError
from agentrr_core.log.writer import LogWriter, LogWriterConfig
from agentrr_core.schema.events import Event, EventType, RunHeader
from agentrr_core.version import __version__

__all__ = [
    "__version__",
    "AgentRrError",
    "Event",
    "EventType",
    "LogWriter",
    "LogWriterConfig",
    "RunHeader",
    "persist_before_return",
]

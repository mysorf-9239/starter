"""Schema owned by the logging subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoggingConfig:
    backend: str = "console"
    enabled: bool = True
    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    path: str | None = None
    json: bool = False
    context: dict[str, str] = field(default_factory=dict)
    rich_tracebacks: bool = False
    show_path: bool = True

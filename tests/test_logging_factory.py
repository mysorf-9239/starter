from pathlib import Path

from starter.config import compose_typed_config
from starter.logging import NullLogger, build_logger, parse_logging_config


def test_config_compose_includes_logging_section() -> None:
    cfg = compose_typed_config()

    assert cfg.logging["backend"] == "console"
    assert cfg.logging["enabled"] is True


def test_build_console_logger_from_composed_section() -> None:
    cfg = compose_typed_config()
    logger = build_logger(cfg.logging, name="starter.test")

    logger.info("hello")
    assert logger.__class__.__name__ == "Logger"


def test_build_disabled_logger_returns_null_logger() -> None:
    cfg = compose_typed_config(["logging=disabled"])
    logger = build_logger(cfg.logging)

    assert isinstance(logger, NullLogger)


def test_build_file_logger_creates_log_file(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "starter.log"
    cfg = parse_logging_config(
        {
            "backend": "file",
            "enabled": True,
            "level": "INFO",
            "format": "%(message)s",
            "path": str(path),
        }
    )

    logger = build_logger(cfg, name="starter.file")
    logger.info("written")

    assert path.exists()


def test_parse_structlog_config_section() -> None:
    cfg = parse_logging_config(
        {
            "backend": "structlog",
            "enabled": True,
            "level": "INFO",
            "format": "%(message)s",
            "path": None,
            "json": False,
            "context": {"component": "test"},
        }
    )

    assert cfg.backend == "structlog"
    assert cfg.context["component"] == "test"


def test_parse_rich_config_section() -> None:
    cfg = parse_logging_config(
        {
            "backend": "rich",
            "enabled": True,
            "level": "INFO",
            "format": "%(message)s",
            "path": None,
            "json": False,
            "context": {},
            "rich_tracebacks": True,
            "show_path": True,
        }
    )

    assert cfg.backend == "rich"
    assert cfg.rich_tracebacks is True

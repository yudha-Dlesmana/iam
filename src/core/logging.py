import logging
import sys

from src.core.config import settings


class _HealthFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args and len(record.args) >= 5:
            path, status = record.args[2], record.args[4]
            if (
                isinstance(path, str)
                and "/v1/health" in path
                and isinstance(status, int)
                and status < 400
            ):
                return False
        return True


def setup_logging() -> None:
    level = logging.INFO if settings.is_production else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("uvicorn.access").addFilter(_HealthFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

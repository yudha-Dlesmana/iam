import logging
import sys

from src.core.config import settings


def setup_logging() -> None:
    level = logging.INFO if settings.is_production else logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

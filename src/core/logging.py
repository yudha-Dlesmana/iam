import json
import logging
import sys

from src.core.config import settings
from src.core.context import request_id_var


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


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = request_id_var.get()
        if rid:
            data["request_id"] = rid

        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def setup_logging() -> None:
    level = logging.INFO if settings.is_production else logging.DEBUG
    handler = logging.StreamHandler(sys.stdout)
    if settings.is_production:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s | %(message)s")
        )
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(handler)
    logging.getLogger("uvicorn.access").addFilter(_HealthFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

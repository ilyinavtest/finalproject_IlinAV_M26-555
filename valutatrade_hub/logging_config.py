"""Настройка логирования: формат, уровень, ротация.

Формат берётся из SettingsLoader (log_format, log_level, log_file).
Поддерживаются text и json форматы. Ротация — по размеру файла.
"""

import json
import logging
from logging.handlers import RotatingFileHandler

from valutatrade_hub.infra.settings import get_settings

_FORMATTER_TEXT = logging.Formatter(
    fmt="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

_LOGGER_NAME = "valutatrade"


class JsonFormatter(logging.Formatter):
    """Форматтер, сериализующий запись лога в JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    """Настраивает и возвращает логгер 'valutatrade'.

    Повторный вызов не добавляет дублирующие хендлеры.
    """
    settings = get_settings()
    logger = logging.getLogger(_LOGGER_NAME)

    if logger.handlers:
        return logger  # уже настроен

    log_format = str(settings.get("log_format", "text")).lower()
    log_level = str(settings.get("log_level", "INFO")).upper()
    log_file = settings.get("log_file_abs")

    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.propagate = False

    log_max_bytes = int(settings.get("log_max_bytes", 1_000_000))
    log_backup_count = int(settings.get("log_backup_count", 3))

    handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )

    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(_FORMATTER_TEXT)

    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    """Возвращает настроенный логгер (при необходимости инициализирует)."""
    return setup_logging()

_PARSER_LOGGER_NAME = "valutatrade.parser"


def get_parser_logger() -> logging.Logger:
    """Возвращает логгер Parser Service (пишет в logs/parser.log).

    Отдельный от 'valutatrade' (actions.log), чтобы разделить логи
    бизнес-операций и парсера (по ТЗ п.4.4: 'Check logs/parser.log').
    """
    settings = get_settings()
    logger = logging.getLogger(_PARSER_LOGGER_NAME)

    if logger.handlers:
        return logger

    log_level = str(settings.get("log_level", "INFO")).upper()
    logs_dir = settings.get("log_file_abs").parent
    parser_log_file = logs_dir / "parser.log"

    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.propagate = False

    log_max_bytes = int(settings.get("log_max_bytes", 1_000_000))
    log_backup_count = int(settings.get("log_backup_count", 3))

    handler = RotatingFileHandler(
        filename=str(parser_log_file),
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(_FORMATTER_TEXT)
    logger.addHandler(handler)
    return logger

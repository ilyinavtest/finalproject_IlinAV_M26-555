"""Singleton SettingsLoader для конфигурации проекта

Источник конфигурации: pyproject.toml -> секция [tool.valutatrade]
Singleton реализован через __new__: не требует
отдельного метакласса и гарантирует единственный экземпляр при импортах
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

_DEFAULTS: dict[str, Any] = {
    "data_dir": "data",
    "rates_ttl_seconds": 300,
    "default_base_currency": "USD",
    "log_format": "text",
    "log_level": "INFO",
    "log_file": "logs/actions.log",
}


class SettingsLoader:
    """Синглтон-загрузчик конфигурации из pyproject.toml -> [tool.valutatrade]

    Выбран __new__ (а не метакласс), потому что:
    - проще и читабельнее;
    - достаточно для проекта такого масштаба;
    - не усложняет наследование
    """

    _instance: SettingsLoader | None = None

    def __new__(cls) -> SettingsLoader:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._load()  # type: ignore[attr-defined]
            cls._instance = instance
        return cls._instance

    def _load(self) -> None:
        """Загружает секцию [tool.valutatrade] из pyproject.toml

        Отсутствующие ключи берутся из _DEFAULTS
        """
        config: dict[str, Any] = {}
        if PYPROJECT_PATH.exists():
            with PYPROJECT_PATH.open("rb") as f:
                pyproject = tomllib.load(f)
            config = pyproject.get("tool", {}).get("valutatrade", {})

        self._config: dict[str, Any] = {**_DEFAULTS, **config}

        # Приводим data_dir к абсолютному пути и создаём директорию
        data_dir = Path(str(self._config["data_dir"]))
        if not data_dir.is_absolute():
            data_dir = (PROJECT_ROOT / data_dir).resolve()
        self._config["data_dir_abs"] = data_dir
        data_dir.mkdir(parents=True, exist_ok=True)

        # Создаём директорию для логов (если путь относительный)
        log_file = Path(str(self._config["log_file"]))
        if not log_file.is_absolute():
            log_file = (PROJECT_ROOT / log_file).resolve()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        self._config["log_file_abs"] = log_file

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение по ключу (или default, если ключа нет)"""
        return self._config.get(key, default)

    def reload(self) -> None:
        """Перезагружает конфигурацию (например, если pyproject.toml изменился)"""
        self._load()


def get_settings() -> SettingsLoader:
    """Удобный хелпер для получения синглтона"""
    return SettingsLoader()

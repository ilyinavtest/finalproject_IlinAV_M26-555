"""Singleton DatabaseManager — абстракция над JSON-хранилищем.

Единая точка доступа к файлам data/*.json (users, portfolios, rates,
exchange_rates). Singleton через __new__ — для единообразия с SettingsLoader.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import get_settings


class DatabaseManager:
    """Синглтон-обёртка над JSON-файлами в data/.

    Не заменяет usecases.load_json/save_json (они продолжают работать),
    но предоставляет единый API для новых модулей и замыкает критерий
    «Singleton DatabaseManager» из ТЗ.
    """

    _instance: DatabaseManager | None = None

    def __new__(cls) -> DatabaseManager:
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._data_dir = get_settings().get("data_dir_abs")
            cls._instance = instance
        return cls._instance

    @property
    def data_dir(self) -> Path:
        """Путь к директории с JSON-файлами (data/)."""
        return self._data_dir

    def path_for(self, filename: str) -> Path:
        """Возвращает полный путь к файлу внутри data/."""
        return self._data_dir / filename

    def load(self, filename: str, default: Any = None) -> Any:
        """Читает JSON из data/<filename>.

        Защита: отсутствие файла, пустой файл, битый JSON, кодировка.
        Возвращает default, если прочитать не удалось.
        """
        if default is None:
            default = [] if filename.endswith("s.json") else {}

        path = self.path_for(filename)
        if not path.exists():
            return default

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback для UTF-16 (например, файлы, созданные через PowerShell echo).
            try:
                content = path.read_text(encoding="utf-16")
            except UnicodeDecodeError:
                return default

        if not content.strip():
            return default

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return default

    def save(self, filename: str, data: Any) -> None:
        """Сохраняет data в data/<filename> как JSON (UTF-8, indent=2)."""
        path = self.path_for(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def get_database() -> DatabaseManager:
    """Удобный хелпер для получения синглтона DatabaseManager."""
    return DatabaseManager()

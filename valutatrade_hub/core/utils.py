"""Вспомогательные функции и валидаторы."""

import json
from pathlib import Path

DATA_DIR = Path("data")


def ensure_data_files() -> None:
    """Создает папку data и пустые JSON-файлы, если их нет."""
    DATA_DIR.mkdir(exist_ok=True)

    files = {
        "users.json": [],
        "portfolios.json": [],
        "rates.json": {},
    }

    for filename, default_data in files.items():
        file_path = DATA_DIR / filename
        if not file_path.exists():
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)


def load_json(filename: str) -> list | dict:
    """Загружает данные из JSON-файла с защитой от пустых и битых файлов."""
    file_path = DATA_DIR / filename
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return [] if filename.endswith("s.json") else {}
            return json.loads(content)
    except json.JSONDecodeError:
        return [] if filename.endswith("s.json") else {}


def save_json(filename: str, data: list | dict) -> None:
    """Сохраняет данные в JSON-файл."""
    file_path = DATA_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def validate_currency(currency_code: str) -> str:
    """Проверяет и нормализует код валюты."""
    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Код валюты не может быть пустым.")
    return currency_code.strip().upper()


def validate_amount(amount: float) -> float:
    """Проверяет, что сумма является положительным числом."""
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        raise ValueError("Сумма должна быть числом.")
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом.")
    return float(amount)

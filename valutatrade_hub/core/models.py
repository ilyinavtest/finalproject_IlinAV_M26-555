"""Реализация доменных классов приложения"""

import hashlib
from datetime import datetime


class User:
    """Пользователь системы"""

    def __init__(
            self,
            user_id: int,
            username: str,
            hashed_password: str,
            salt: str,
            registration_date: datetime,
    ) -> None:
        """Инициализация пользователя"""
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

        if not self._username.strip():
            raise ValueError("Имя пользователя не может быть пустым.")

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым.")
        self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    def get_user_info(self) -> dict[str, str | int]:
        """Выводит информацию о пользователе (без пароля и соли)"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль пользователя, хешируя его с текущей солью"""
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов.")

        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode("utf-8")
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли введённый пароль с сохранённым хешем"""
        check_hash = hashlib.sha256(
            (password + self._salt).encode("utf-8")
        ).hexdigest()
        return self._hashed_password == check_hash

    def to_dict(self) -> dict:
        """Сериализует объект в словарь для users.json"""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }


    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Создает пользователя из словаря (при чтении users.json)"""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )

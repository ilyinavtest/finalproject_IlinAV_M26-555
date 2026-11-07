"""Реализация доменных классов приложения"""

import hashlib
from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError


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


class Wallet:
    """Кошелёк пользователя для одной конкретной валюты"""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        """Инициализация кошелька
        По умолчанию баланс равен 0.0. Проверка на отрицательный баланс
        произойдет автоматически через сеттер свойства balance
        """
        self.currency_code = currency_code
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        """Геттер для получения текущего баланса"""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Сеттер с защитой от отрицательных значений и некорректных типов"""
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("Баланс должен быть числом")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополнение баланса на указанную сумму"""
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("Сумма пополнения должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом")

        self.balance = self._balance + amount

    def withdraw(self, amount: float) -> None:
        """Снятие средств с проверкой достаточности баланса"""
        if not isinstance(amount, (int, float)) or isinstance(amount, bool):
            raise ValueError("Сумма снятия должна быть числом")
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом")
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=amount,
                code=self.currency_code,
            )

        self.balance = self._balance - amount

    def get_balance_info(self) -> dict[str, str | float]:
        """Вывод информации о текущем балансе"""
        return {
            "currency_code": self.currency_code,
            "balance": self._balance
        }

    def to_dict(self) -> dict:
        """Сериализация кошелька для сохранения в JSON"""
        return {
            "currency_code": self.currency_code,
            "balance": self._balance
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        """Создание кошелька из словаря (при чтении из JSON)"""
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"]
        )


class Portfolio:
    """Управление всеми кошельками одного пользователя"""

    def __init__(self, user: User) -> None:
        """Инициализация портфеля для конкретного пользователя
        Сохраняем ссылку на пользователя и создаем пустой словарь кошельков
        """
        self._user = user
        self._user_id = user.user_id
        self._wallets: dict[str, Wallet] = {}

    @property
    def user(self) -> User:
        """Геттер, возвращающий объект пользователя (без возможности перезаписи)"""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Геттер, возвращающий копию словаря кошельков"""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый кошелёк в портфель (если его ещё нет)
        Возвращает созданный (или уже существующий) объект Wallet
        """
        currency_code = currency_code.upper()
        if currency_code in self._wallets:
            return self._wallets[currency_code]

        new_wallet = Wallet(currency_code=currency_code, balance=0.0)
        self._wallets[currency_code] = new_wallet
        return new_wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Возвращает объект Wallet по коду валюты, либо None, если его нет"""
        return self._wallets.get(currency_code.upper())

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Возвращает общую стоимость всех валют пользователя в указанной базовой валюте
        Для упрощения используем фиксированные курсы (заглушки)
        В будущем здесь будет обращение к реальным курсам из rates.json
        """
        # Условные курсы к USD (заглушка)
        exchange_rates = {
            "USD": 1.0,
            "EUR": 1.08,
            "RUB": 0.011,
            "BTC": 60000.0,
            "ETH": 3000.0,
            "USDT": 1.0,
        }

        base_rate = exchange_rates.get(base_currency.upper(), 1.0)
        total = 0.0

        for code, wallet in self._wallets.items():
            rate_to_usd = exchange_rates.get(code, 0.0)
            total += (wallet.balance * rate_to_usd) / base_rate

        return total


    def to_dict(self) -> dict:
        """Сериализация портфеля для сохранения в JSON"""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: {"balance": wallet.balance}
                for code, wallet in self._wallets.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict, user: User) -> "Portfolio":
        """Создание портфеля из словаря (при чтении из JSON)"""
        portfolio = cls(user=user)
        for code, wallet_data in data.get("wallets", {}).items():
            wallet = portfolio.add_currency(code)
            wallet.balance = wallet_data.get("balance", 0.0)
        return portfolio

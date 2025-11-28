"""거래소 어댑터 모듈"""

from typing import Literal

from .base import BaseExchange
from .upbit import UpbitExchange

# 거래소 레지스트리
_EXCHANGES: dict[str, type[BaseExchange]] = {
    "upbit": UpbitExchange,
}


def get_exchange(
    name: Literal["upbit", "binance", "binance_futures"],
    api_key: str = "",
    secret_key: str = "",
) -> BaseExchange:
    """거래소 인스턴스 팩토리"""
    if name not in _EXCHANGES:
        available = ", ".join(_EXCHANGES.keys())
        raise ValueError(f"Unknown exchange: {name}. Available: {available}")

    return _EXCHANGES[name](api_key=api_key, secret_key=secret_key)


def register_exchange(name: str, exchange_class: type[BaseExchange]) -> None:
    """거래소 등록"""
    _EXCHANGES[name] = exchange_class


__all__ = ["BaseExchange", "UpbitExchange", "get_exchange", "register_exchange"]

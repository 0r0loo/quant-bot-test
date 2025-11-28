"""전략 모듈"""

from .base import BaseStrategy
from .ema_cross import EMACrossStrategy

# 전략 레지스트리
_STRATEGIES: dict[str, type[BaseStrategy]] = {
    "ema_cross": EMACrossStrategy,
}


def get_strategy(name: str, **kwargs) -> BaseStrategy:
    """전략 인스턴스 팩토리"""
    if name not in _STRATEGIES:
        available = ", ".join(_STRATEGIES.keys())
        raise ValueError(f"Unknown strategy: {name}. Available: {available}")

    return _STRATEGIES[name](**kwargs)


def register_strategy(name: str, strategy_class: type[BaseStrategy]) -> None:
    """전략 등록"""
    _STRATEGIES[name] = strategy_class


def list_strategies() -> list[str]:
    """등록된 전략 목록"""
    return list(_STRATEGIES.keys())


__all__ = [
    "BaseStrategy",
    "EMACrossStrategy",
    "get_strategy",
    "register_strategy",
    "list_strategies",
]

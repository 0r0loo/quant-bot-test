"""거래 신호 데이터 모델"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SignalAction(Enum):
    """신호 액션"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Signal:
    """거래 신호"""

    action: SignalAction
    strength: float = 1.0  # 0.0 ~ 1.0
    reason: str = ""
    price: Optional[float] = None

    @classmethod
    def buy(cls, strength: float = 1.0, reason: str = "") -> "Signal":
        """매수 신호 생성"""
        return cls(action=SignalAction.BUY, strength=strength, reason=reason)

    @classmethod
    def sell(cls, strength: float = 1.0, reason: str = "") -> "Signal":
        """매도 신호 생성"""
        return cls(action=SignalAction.SELL, strength=strength, reason=reason)

    @classmethod
    def hold(cls, reason: str = "") -> "Signal":
        """관망 신호 생성"""
        return cls(action=SignalAction.HOLD, strength=0.0, reason=reason)

    @property
    def is_buy(self) -> bool:
        return self.action == SignalAction.BUY

    @property
    def is_sell(self) -> bool:
        return self.action == SignalAction.SELL

    @property
    def is_hold(self) -> bool:
        return self.action == SignalAction.HOLD

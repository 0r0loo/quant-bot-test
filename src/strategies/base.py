"""전략 기본 인터페이스"""

from abc import ABC, abstractmethod

import pandas as pd

from src.models import Signal, SignalAction


class BaseStrategy(ABC):
    """전략 추상 기본 클래스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """전략 이름"""
        pass

    @property
    def params(self) -> dict:
        """전략 파라미터 (그리드 서치용)"""
        return {}

    @property
    def min_bars(self) -> int:
        """최소 필요 봉 개수"""
        return 50

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        지표 계산 및 신호 생성

        Args:
            df: OHLCV DataFrame

        Returns:
            DataFrame with 'signal' column
            - 1: 매수 (long)
            - -1: 매도 (short)
            - 0: 관망 (neutral)
        """
        pass

    def generate_signal(self, df: pd.DataFrame) -> Signal:
        """
        현재 신호 생성 (실거래용)

        Args:
            df: 최신 OHLCV DataFrame

        Returns:
            Signal 객체
        """
        result = self.calculate(df)
        last_signal = result["signal"].iloc[-1]

        if last_signal > 0:
            return Signal(
                action=SignalAction.BUY,
                strength=abs(last_signal),
                reason=self.name,
            )
        elif last_signal < 0:
            return Signal(
                action=SignalAction.SELL,
                strength=abs(last_signal),
                reason=self.name,
            )

        return Signal(action=SignalAction.HOLD, reason=self.name)

    def __repr__(self) -> str:
        params_str = ", ".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.__class__.__name__}({params_str})"

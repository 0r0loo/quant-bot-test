"""EMA 크로스 전략"""

import pandas as pd

from src.indicators import ema, rsi

from .base import BaseStrategy


class EMACrossStrategy(BaseStrategy):
    """
    EMA 크로스 전략

    - 골든 크로스 (단기 > 장기): 매수
    - 데드 크로스 (단기 < 장기): 매도
    - RSI/추세 필터로 노이즈 감소
    """

    def __init__(
        self,
        short_period: int = 5,
        long_period: int = 20,
        trend_period: int = 60,
        rsi_period: int = 14,
        rsi_threshold: int = 50,
        use_trend_filter: bool = True,
        use_rsi_filter: bool = True,
    ):
        self.short_period = short_period
        self.long_period = long_period
        self.trend_period = trend_period
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.use_trend_filter = use_trend_filter
        self.use_rsi_filter = use_rsi_filter

    @property
    def name(self) -> str:
        return f"ema_cross_{self.short_period}_{self.long_period}"

    @property
    def params(self) -> dict:
        return {
            "short_period": self.short_period,
            "long_period": self.long_period,
            "trend_period": self.trend_period,
            "rsi_threshold": self.rsi_threshold,
            "use_trend_filter": self.use_trend_filter,
            "use_rsi_filter": self.use_rsi_filter,
        }

    @property
    def min_bars(self) -> int:
        return max(self.short_period, self.long_period, self.trend_period) + 10

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """지표 계산 및 신호 생성"""
        df = df.copy()

        # EMA 계산
        df["ema_short"] = ema(df, self.short_period)
        df["ema_long"] = ema(df, self.long_period)

        if self.use_trend_filter:
            df["ema_trend"] = ema(df, self.trend_period)

        if self.use_rsi_filter:
            df["rsi"] = rsi(df, self.rsi_period)

        # 기본 신호: EMA 크로스
        df["signal"] = 0
        df.loc[df["ema_short"] > df["ema_long"], "signal"] = 1
        df.loc[df["ema_short"] < df["ema_long"], "signal"] = -1

        # 추세 필터: 상승 추세에서만 롱
        if self.use_trend_filter:
            uptrend = df["close"] > df["ema_trend"]
            df.loc[(df["signal"] == 1) & ~uptrend, "signal"] = 0

        # RSI 필터: RSI > threshold에서만 롱
        if self.use_rsi_filter:
            rsi_ok = df["rsi"] > self.rsi_threshold
            df.loc[(df["signal"] == 1) & ~rsi_ok, "signal"] = 0

        return df


class SimpleEMACrossStrategy(BaseStrategy):
    """
    단순 EMA 크로스 전략 (필터 없음)

    백테스팅 비교용
    """

    def __init__(self, short_period: int = 5, long_period: int = 20):
        self.short_period = short_period
        self.long_period = long_period

    @property
    def name(self) -> str:
        return f"simple_ema_{self.short_period}_{self.long_period}"

    @property
    def params(self) -> dict:
        return {
            "short_period": self.short_period,
            "long_period": self.long_period,
        }

    @property
    def min_bars(self) -> int:
        return self.long_period + 5

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df["ema_short"] = ema(df, self.short_period)
        df["ema_long"] = ema(df, self.long_period)

        df["signal"] = 0
        df.loc[df["ema_short"] > df["ema_long"], "signal"] = 1
        df.loc[df["ema_short"] < df["ema_long"], "signal"] = -1

        return df

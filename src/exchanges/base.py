"""거래소 기본 인터페이스"""

from abc import ABC, abstractmethod
from typing import Literal, Optional

import pandas as pd

from src.models import OrderResult, OrderSide, OrderType


class BaseExchange(ABC):
    """거래소 추상 기본 클래스"""

    def __init__(self, api_key: str = "", secret_key: str = ""):
        self._api_key = api_key
        self._secret_key = secret_key

    @property
    @abstractmethod
    def name(self) -> str:
        """거래소 이름"""
        pass

    @property
    @abstractmethod
    def market_type(self) -> Literal["spot", "futures"]:
        """시장 유형"""
        pass

    # ===== 데이터 조회 (필수 구현) =====

    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 200,
    ) -> pd.DataFrame:
        """
        OHLCV 캔들 데이터 조회

        Args:
            symbol: 심볼 (예: "BTC", "BTC/KRW", "BTCUSDT")
            interval: 시간 간격 ("1m", "5m", "15m", "1h", "4h", "1d")
            limit: 조회 개수

        Returns:
            DataFrame with columns: open, high, low, close, volume
            Index: DatetimeIndex
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> dict:
        """
        현재가 조회

        Returns:
            {"price": float, "volume": float, ...}
        """
        pass

    # ===== 동기 버전 (백테스팅용) =====

    def get_ohlcv_sync(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 200,
    ) -> pd.DataFrame:
        """동기 OHLCV 조회 (백테스팅용)"""
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.get_ohlcv(symbol, interval, limit)
        )

    # ===== 거래 기능 (선택적 구현) =====

    async def get_balance(self, currency: str = "") -> dict:
        """잔고 조회"""
        raise NotImplementedError(f"{self.name} does not support get_balance")

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderResult:
        """주문 실행"""
        raise NotImplementedError(f"{self.name} does not support place_order")

    async def cancel_order(self, order_id: str, symbol: str = "") -> bool:
        """주문 취소"""
        raise NotImplementedError(f"{self.name} does not support cancel_order")

    async def get_order(self, order_id: str, symbol: str = "") -> Optional[OrderResult]:
        """주문 조회"""
        raise NotImplementedError(f"{self.name} does not support get_order")

    # ===== 유틸리티 =====

    def _normalize_symbol(self, symbol: str) -> str:
        """심볼 정규화 (거래소별 오버라이드)"""
        return symbol

    def _normalize_interval(self, interval: str) -> str:
        """시간 간격 정규화 (거래소별 오버라이드)"""
        return interval

"""업비트 거래소 어댑터"""

import asyncio
import time
from typing import Literal, Optional

import pandas as pd
import pyupbit

from src.models import OrderResult, OrderSide, OrderStatus, OrderType

from .base import BaseExchange


class UpbitExchange(BaseExchange):
    """업비트 현물 거래소"""

    # 시간 간격 매핑
    INTERVAL_MAP = {
        "1m": "minute1",
        "3m": "minute3",
        "5m": "minute5",
        "15m": "minute15",
        "30m": "minute30",
        "1h": "minute60",
        "4h": "minute240",
        "1d": "day",
        "1w": "week",
        "1M": "month",
        # 업비트 기본 형식도 지원
        "minute1": "minute1",
        "minute60": "minute60",
        "day": "day",
    }

    def __init__(self, api_key: str = "", secret_key: str = ""):
        super().__init__(api_key, secret_key)
        self._upbit: Optional[pyupbit.Upbit] = None

        if api_key and secret_key:
            self._upbit = pyupbit.Upbit(api_key, secret_key)

    @property
    def name(self) -> str:
        return "upbit"

    @property
    def market_type(self) -> Literal["spot", "futures"]:
        return "spot"

    def _normalize_symbol(self, symbol: str) -> str:
        """심볼 정규화: BTC -> KRW-BTC"""
        if "-" in symbol:
            return symbol
        if "/" in symbol:
            base, quote = symbol.split("/")
            return f"{quote}-{base}"
        return f"KRW-{symbol}"

    def _normalize_interval(self, interval: str) -> str:
        """시간 간격 정규화"""
        return self.INTERVAL_MAP.get(interval, interval)

    async def get_ohlcv(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 200,
    ) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        ticker = self._normalize_symbol(symbol)
        interval_str = self._normalize_interval(interval)

        # 200개 이하는 한 번에 조회
        if limit <= 200:
            df = await asyncio.to_thread(
                pyupbit.get_ohlcv, ticker, interval=interval_str, count=limit
            )
            return df

        # 200개 초과시 여러 번 조회
        return await self._get_ohlcv_long(ticker, interval_str, limit)

    async def _get_ohlcv_long(
        self, ticker: str, interval: str, days: int
    ) -> pd.DataFrame:
        """장기 데이터 수집 (200개 초과)"""
        all_data = []
        to = None
        remaining = days

        while remaining > 0:
            count = min(200, remaining)

            df = await asyncio.to_thread(
                pyupbit.get_ohlcv, ticker, interval=interval, count=count, to=to
            )

            if df is None or len(df) == 0:
                break

            all_data.append(df)
            to = df.index[0]
            remaining -= len(df)

            # API 제한 방지
            await asyncio.sleep(0.2)

        if not all_data:
            return pd.DataFrame()

        result = pd.concat(all_data)
        result = result[~result.index.duplicated(keep="first")]
        return result.sort_index()

    async def get_ticker(self, symbol: str) -> dict:
        """현재가 조회"""
        ticker = self._normalize_symbol(symbol)
        price = await asyncio.to_thread(pyupbit.get_current_price, ticker)
        return {"symbol": ticker, "price": price}

    # ===== 동기 버전 (백테스팅 최적화) =====

    def get_ohlcv_sync(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 200,
    ) -> pd.DataFrame:
        """동기 OHLCV 조회 (백테스팅용) - 더 효율적"""
        ticker = self._normalize_symbol(symbol)
        interval_str = self._normalize_interval(interval)

        if limit <= 200:
            return pyupbit.get_ohlcv(ticker, interval=interval_str, count=limit)

        return self._get_ohlcv_long_sync(ticker, interval_str, limit)

    def _get_ohlcv_long_sync(self, ticker: str, interval: str, days: int) -> pd.DataFrame:
        """동기 장기 데이터 수집"""
        all_data = []
        to = None
        remaining = days

        while remaining > 0:
            count = min(200, remaining)
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=count, to=to)

            if df is None or len(df) == 0:
                break

            all_data.append(df)
            to = df.index[0]
            remaining -= len(df)
            time.sleep(0.2)

        if not all_data:
            return pd.DataFrame()

        result = pd.concat(all_data)
        result = result[~result.index.duplicated(keep="first")]
        return result.sort_index()

    # ===== 거래 기능 =====

    async def get_balance(self, currency: str = "") -> dict:
        """잔고 조회"""
        if not self._upbit:
            raise ValueError("API key required for get_balance")

        balances = await asyncio.to_thread(self._upbit.get_balances)

        if currency:
            for b in balances:
                if b["currency"] == currency.upper():
                    return {
                        "currency": b["currency"],
                        "balance": float(b["balance"]),
                        "locked": float(b["locked"]),
                        "avg_buy_price": float(b["avg_buy_price"]),
                    }
            return {"currency": currency, "balance": 0, "locked": 0}

        return {
            b["currency"]: {
                "balance": float(b["balance"]),
                "locked": float(b["locked"]),
                "avg_buy_price": float(b["avg_buy_price"]),
            }
            for b in balances
        }

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderResult:
        """주문 실행"""
        if not self._upbit:
            raise ValueError("API key required for place_order")

        ticker = self._normalize_symbol(symbol)

        if side == OrderSide.BUY:
            if order_type == OrderType.MARKET:
                # 시장가 매수: price에 총 금액 입력
                result = await asyncio.to_thread(
                    self._upbit.buy_market_order, ticker, quantity
                )
            else:
                result = await asyncio.to_thread(
                    self._upbit.buy_limit_order, ticker, price, quantity
                )
        else:
            if order_type == OrderType.MARKET:
                result = await asyncio.to_thread(
                    self._upbit.sell_market_order, ticker, quantity
                )
            else:
                result = await asyncio.to_thread(
                    self._upbit.sell_limit_order, ticker, price, quantity
                )

        return OrderResult(
            order_id=result.get("uuid", ""),
            symbol=ticker,
            side=side,
            price=result.get("price", 0),
            quantity=result.get("volume", 0),
            filled_quantity=result.get("executed_volume", 0),
            status=OrderStatus.PENDING,
        )

    async def cancel_order(self, order_id: str, symbol: str = "") -> bool:
        """주문 취소"""
        if not self._upbit:
            raise ValueError("API key required for cancel_order")

        result = await asyncio.to_thread(self._upbit.cancel_order, order_id)
        return result is not None

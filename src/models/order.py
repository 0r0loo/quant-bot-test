"""주문 관련 데이터 모델"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    """주문 방향"""

    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """주문 유형"""

    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(Enum):
    """주문 상태"""

    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """주문 정보"""

    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OrderResult:
    """주문 결과"""

    order_id: str
    symbol: str
    side: OrderSide
    price: Decimal
    quantity: Decimal
    filled_quantity: Decimal
    status: OrderStatus
    fee: Decimal = Decimal("0")
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Position:
    """포지션 정보"""

    symbol: str
    side: OrderSide
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")

    def update_price(self, price: Decimal) -> None:
        """현재가 업데이트"""
        self.current_price = price
        if self.side == OrderSide.BUY:
            self.unrealized_pnl = (price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.quantity

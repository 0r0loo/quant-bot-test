"""백테스트 성과 지표 계산"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BacktestMetrics:
    """백테스트 성과 지표"""

    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float = 0.0
    avg_trade_return: float = 0.0

    def __str__(self) -> str:
        return (
            f"수익률: {self.total_return:.2%} | "
            f"연환산: {self.annual_return:.2%} | "
            f"샤프: {self.sharpe_ratio:.2f} | "
            f"MDD: {self.max_drawdown:.2%} | "
            f"승률: {self.win_rate:.2%} | "
            f"거래: {self.total_trades}회"
        )

    def to_dict(self) -> dict:
        return {
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "profit_factor": self.profit_factor,
            "avg_trade_return": self.avg_trade_return,
        }


def calculate_metrics(
    returns: pd.Series,
    equity_curve: np.ndarray | pd.Series,
    signals: pd.Series | None = None,
) -> BacktestMetrics:
    """
    성과 지표 계산

    Args:
        returns: 전략 수익률 시리즈
        equity_curve: 자산 곡선
        signals: 신호 시리즈 (거래 횟수 계산용)

    Returns:
        BacktestMetrics 객체
    """
    returns = returns.dropna()

    if len(returns) == 0:
        return BacktestMetrics(
            total_return=0,
            annual_return=0,
            sharpe_ratio=0,
            max_drawdown=0,
            win_rate=0,
            total_trades=0,
        )

    # 총 수익률
    total_return = (1 + returns).prod() - 1

    # 연환산 수익률
    days = len(returns)
    if days > 0 and total_return > -1:
        annual_return = (1 + total_return) ** (365 / days) - 1
    else:
        annual_return = 0

    # 변동성 및 샤프 비율
    volatility = returns.std() * np.sqrt(365)
    sharpe_ratio = annual_return / volatility if volatility > 0 else 0

    # 최대 낙폭 (MDD)
    if isinstance(equity_curve, pd.Series):
        equity = equity_curve.values
    else:
        equity = equity_curve

    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_drawdown = drawdown.min()

    # 거래 횟수
    if signals is not None:
        position_changes = signals.diff().fillna(0)
        total_trades = int((position_changes != 0).sum())
    else:
        total_trades = int((returns != 0).sum())

    # 승률
    winning_returns = returns[returns > 0]
    losing_returns = returns[returns < 0]
    total_trading_days = len(winning_returns) + len(losing_returns)
    win_rate = len(winning_returns) / total_trading_days if total_trading_days > 0 else 0

    # 수익 팩터
    total_gains = winning_returns.sum() if len(winning_returns) > 0 else 0
    total_losses = abs(losing_returns.sum()) if len(losing_returns) > 0 else 0
    profit_factor = total_gains / total_losses if total_losses > 0 else float("inf")

    # 평균 거래 수익률
    avg_trade_return = returns[returns != 0].mean() if (returns != 0).any() else 0

    return BacktestMetrics(
        total_return=total_return,
        annual_return=annual_return,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
        total_trades=total_trades,
        profit_factor=profit_factor,
        avg_trade_return=avg_trade_return,
    )


def calculate_hodl_return(df: pd.DataFrame) -> float:
    """단순 보유 수익률 계산"""
    if len(df) < 2:
        return 0
    return (df["close"].iloc[-1] / df["close"].iloc[0]) - 1

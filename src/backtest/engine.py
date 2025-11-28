"""백테스트 엔진"""

from dataclasses import dataclass, field
from itertools import product
from typing import Type

import numpy as np
import pandas as pd

from src.strategies.base import BaseStrategy

from .metrics import BacktestMetrics, calculate_hodl_return, calculate_metrics


@dataclass
class BacktestResult:
    """백테스트 결과"""

    strategy_name: str
    params: dict
    metrics: BacktestMetrics
    hodl_return: float
    equity_curve: np.ndarray
    signals: np.ndarray
    df: pd.DataFrame = field(repr=False)

    def __str__(self) -> str:
        return (
            f"[{self.strategy_name}]\n"
            f"  {self.metrics}\n"
            f"  HODL: {self.hodl_return:.2%}"
        )

    def summary(self) -> dict:
        """결과 요약 딕셔너리"""
        return {
            "strategy": self.strategy_name,
            **self.params,
            **self.metrics.to_dict(),
            "hodl_return": self.hodl_return,
        }


class BacktestEngine:
    """
    벡터화 백테스트 엔진

    빠른 성능을 위해 NumPy/Pandas 벡터 연산 사용
    """

    def __init__(
        self,
        fee_rate: float = 0.001,
        slippage: float = 0.001,
        initial_capital: float = 10_000_000,
    ):
        """
        Args:
            fee_rate: 거래 수수료율 (기본 0.1%)
            slippage: 슬리피지 (기본 0.1%)
            initial_capital: 초기 자본금
        """
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.total_cost = fee_rate + slippage
        self.initial_capital = initial_capital

    def run(self, df: pd.DataFrame, strategy: BaseStrategy) -> BacktestResult:
        """
        단일 백테스트 실행

        Args:
            df: OHLCV DataFrame
            strategy: 전략 인스턴스

        Returns:
            BacktestResult 객체
        """
        # 전략 계산
        result_df = strategy.calculate(df)

        # 벡터화 수익률 계산
        returns = result_df["close"].pct_change()
        signals = result_df["signal"]

        # 포지션 변화 (거래 발생)
        position_changes = signals.diff().fillna(0).abs()

        # 전략 수익률 = (가격 수익률 * 이전 신호) - 거래 비용
        strategy_returns = (returns * signals.shift(1)) - (position_changes * self.total_cost)
        strategy_returns = strategy_returns.fillna(0)

        # 자산 곡선
        equity_curve = self.initial_capital * (1 + strategy_returns).cumprod()

        # 성과 지표 계산
        metrics = calculate_metrics(strategy_returns, equity_curve, signals)

        # HODL 수익률
        hodl_return = calculate_hodl_return(df)

        return BacktestResult(
            strategy_name=strategy.name,
            params=strategy.params,
            metrics=metrics,
            hodl_return=hodl_return,
            equity_curve=equity_curve.values,
            signals=signals.values,
            df=result_df,
        )

    def grid_search(
        self,
        df: pd.DataFrame,
        strategy_class: Type[BaseStrategy],
        param_grid: dict,
        sort_by: str = "sharpe_ratio",
    ) -> pd.DataFrame:
        """
        파라미터 그리드 서치

        Args:
            df: OHLCV DataFrame
            strategy_class: 전략 클래스
            param_grid: 파라미터 그리드 {"param_name": [값들]}
            sort_by: 정렬 기준 지표

        Returns:
            결과 DataFrame (정렬됨)
        """
        results = []
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        for values in product(*param_values):
            params = dict(zip(param_names, values))

            try:
                strategy = strategy_class(**params)
                result = self.run(df, strategy)
                results.append(result.summary())
            except Exception as e:
                print(f"Error with params {params}: {e}")
                continue

        if not results:
            return pd.DataFrame()

        results_df = pd.DataFrame(results)

        # 정렬
        if sort_by in results_df.columns:
            results_df = results_df.sort_values(sort_by, ascending=False)

        return results_df.reset_index(drop=True)

    def walk_forward(
        self,
        df: pd.DataFrame,
        strategy_class: Type[BaseStrategy],
        param_grid: dict,
        train_ratio: float = 0.5,
    ) -> dict:
        """
        Walk-Forward 테스트

        훈련 기간에서 최적 파라미터를 찾고,
        테스트 기간에서 검증

        Args:
            df: OHLCV DataFrame
            strategy_class: 전략 클래스
            param_grid: 파라미터 그리드
            train_ratio: 훈련 기간 비율 (기본 50%)

        Returns:
            {"train_result": ..., "test_result": ..., "best_params": ...}
        """
        split_idx = int(len(df) * train_ratio)
        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()

        # 훈련 기간 최적화
        train_results = self.grid_search(train_df, strategy_class, param_grid)

        if len(train_results) == 0:
            return {"error": "No valid results in training period"}

        # 최적 파라미터 추출
        best_row = train_results.iloc[0]
        best_params = {
            k: (int(v) if isinstance(v, (float, np.floating)) and v == int(v) else v)
            for k, v in best_row.items()
            if k in param_grid
        }

        # 테스트 기간 검증
        strategy = strategy_class(**best_params)
        test_result = self.run(test_df, strategy)

        return {
            "train_period": f"{train_df.index[0].date()} ~ {train_df.index[-1].date()}",
            "test_period": f"{test_df.index[0].date()} ~ {test_df.index[-1].date()}",
            "best_params": best_params,
            "train_sharpe": float(best_row["sharpe_ratio"]),
            "train_return": float(best_row["total_return"]),
            "test_result": test_result,
        }

    def compare_strategies(
        self,
        df: pd.DataFrame,
        strategies: list[BaseStrategy],
    ) -> pd.DataFrame:
        """
        여러 전략 비교

        Args:
            df: OHLCV DataFrame
            strategies: 전략 리스트

        Returns:
            비교 결과 DataFrame
        """
        results = []

        for strategy in strategies:
            try:
                result = self.run(df, strategy)
                results.append(result.summary())
            except Exception as e:
                print(f"Error with {strategy.name}: {e}")

        return pd.DataFrame(results)

import pandas as pd
import numpy as np
from dataclasses import dataclass
from collector import get_ohlcv_long
from indicators import rsi, vwap_rolling


@dataclass
class BacktestConfig:
    """백테스팅 설정"""
    data_days: int = 730
    rsi_values: list = None
    vwap_values: list = None
    fee_rate: float = 0.001  # 수수료 0.05% * 2 (매수+매도)
    slippage: float = 0.001  # 슬리피지 0.1%

    def __post_init__(self):
        self.rsi_values = self.rsi_values or [30, 40, 50, 60, 70]
        self.vwap_values = self.vwap_values or [10, 15, 20, 25, 30]

    @property
    def total_cost(self):
        return self.fee_rate + self.slippage


class Backtester:
    def __init__(self, df: pd.DataFrame, cost: float = 0.002):
        self.df = df
        self.cost = cost
        self.hodl_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1

    def run(self, rsi_threshold: int, vwap_period: int) -> dict:
        """단일 백테스팅 실행"""
        df = self.df.copy()

        # 지표 계산
        df['rsi'] = rsi(df, 14)
        df['vwap'] = vwap_rolling(df, vwap_period)
        df['vwap_prev'] = df['vwap'].shift(1)
        df['vwap_prev2'] = df['vwap'].shift(2)

        # 신호 생성
        vwap_up = (df['vwap'] > df['vwap_prev']) & (df['vwap_prev'] <= df['vwap_prev2'])
        vwap_down = (df['vwap'] < df['vwap_prev']) & (df['vwap_prev'] >= df['vwap_prev2'])

        df['signal'] = np.nan
        df.loc[(df['rsi'] > rsi_threshold) & vwap_up, 'signal'] = 1
        df.loc[vwap_down, 'signal'] = 0
        df['signal'] = df['signal'].ffill().fillna(0)

        # 포지션 변화 감지
        df['position'] = df['signal'].diff().fillna(0)

        # 수익률 계산
        df['return'] = df['close'].pct_change()
        df['strategy_return'] = df['return'] * df['signal'].shift(1)

        # 거래 비용 차감 (진입/청산 시)
        df['trade_cost'] = df['position'].abs() * self.cost
        df['strategy_return'] = df['strategy_return'] - df['trade_cost']

        return self._calculate_metrics(df)

    def _calculate_metrics(self, df: pd.DataFrame) -> dict:
        """성과 지표 계산"""
        returns = df['strategy_return'].dropna()

        if len(returns) == 0:
            return None

        total = (1 + returns).prod() - 1
        days = len(returns)
        annual = (1 + total) ** (365 / days) - 1
        vol = returns.std() * np.sqrt(365)
        sharpe = annual / vol if vol > 0 else 0

        cumulative = (1 + returns).cumprod()
        mdd = ((cumulative - cumulative.cummax()) / cumulative.cummax()).min()

        trades = (df['position'] != 0).sum()

        return {
            'total_return': total,
            'annual_return': annual,
            'sharpe': sharpe,
            'mdd': mdd,
            'trades': int(trades)
        }

    def run_grid_search(self, rsi_values: list, vwap_values: list) -> pd.DataFrame:
        """파라미터 그리드 서치"""
        results = []

        for rsi_val in rsi_values:
            for vwap_val in vwap_values:
                metrics = self.run(rsi_val, vwap_val)
                if metrics:
                    results.append({'rsi': rsi_val, 'vwap': vwap_val, **metrics})

        df = pd.DataFrame(results)
        return df.sort_values('sharpe', ascending=False) if len(df) > 0 else df


class WalkForwardTester:
    def __init__(self, df: pd.DataFrame, config: BacktestConfig):
        self.df = df
        self.config = config

    def run(self, train_ratio: float = 0.5) -> dict:
        """Walk-Forward 테스트 실행"""
        split_idx = int(len(self.df) * train_ratio)

        train_df = self.df.iloc[:split_idx].copy()
        test_df = self.df.iloc[split_idx:].copy()

        # 훈련 데이터로 최적 파라미터 찾기
        train_backtester = Backtester(train_df, self.config.total_cost)
        train_results = train_backtester.run_grid_search(
            self.config.rsi_values,
            self.config.vwap_values
        )

        if len(train_results) == 0:
            return None

        best = train_results.iloc[0]
        best_rsi = int(best['rsi'])
        best_vwap = int(best['vwap'])

        # 테스트 데이터로 검증
        test_backtester = Backtester(test_df, self.config.total_cost)
        test_metrics = test_backtester.run(best_rsi, best_vwap)

        return {
            'train': {
                'period': f"{train_df.index[0].date()} ~ {train_df.index[-1].date()}",
                'days': len(train_df),
                'best_rsi': best_rsi,
                'best_vwap': best_vwap,
                'metrics': best.to_dict()
            },
            'test': {
                'period': f"{test_df.index[0].date()} ~ {test_df.index[-1].date()}",
                'days': len(test_df),
                'hodl': test_backtester.hodl_return,
                'metrics': test_metrics
            }
        }


class ResultPrinter:
    @staticmethod
    def header(df: pd.DataFrame, config: BacktestConfig):
        print(f"기간: {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)}일)")
        print(f"거래비용: {config.total_cost:.2%} (수수료 {config.fee_rate:.2%} + 슬리피지 {config.slippage:.2%})")

    @staticmethod
    def hodl(hodl_return: float):
        print(f"단순 보유: {hodl_return:.2%}")

    @staticmethod
    def grid_results(results: pd.DataFrame):
        print()
        print(f"{'RSI':<5}{'VWAP':<6}{'수익률':>9}{'연환산':>9}{'샤프':>7}{'MDD':>9}{'거래':>6}")
        print("-" * 51)

        for _, r in results.iterrows():
            print(f"{int(r['rsi']):<5}{int(r['vwap']):<6}"
                  f"{r['total_return']:>8.2%} {r['annual_return']:>8.2%} "
                  f"{r['sharpe']:>6.2f} {r['mdd']:>8.2%} {r['trades']:>5}")

    @staticmethod
    def best(results: pd.DataFrame):
        best = results.iloc[0]
        print()
        print(f"=== 최적: RSI {int(best['rsi'])}, VWAP {int(best['vwap'])} ===")
        print(f"샤프 {best['sharpe']:.2f} | 수익률 {best['total_return']:.2%} | MDD {best['mdd']:.2%}")

    @staticmethod
    def walk_forward(result: dict):
        train = result['train']
        test = result['test']

        print()
        print("=" * 55)
        print("WALK-FORWARD 테스트 결과")
        print("=" * 55)

        print()
        print(f"[훈련 기간] {train['period']} ({train['days']}일)")
        print(f"최적 파라미터: RSI {train['best_rsi']}, VWAP {train['best_vwap']}")
        print(f"훈련 성과 - 수익률: {train['metrics']['total_return']:.2%}, "
              f"샤프: {train['metrics']['sharpe']:.2f}, MDD: {train['metrics']['mdd']:.2%}")

        print()
        print(f"[테스트 기간] {test['period']} ({test['days']}일)")
        print(f"단순 보유: {test['hodl']:.2%}")

        if test['metrics']:
            m = test['metrics']
            print(f"전략 성과 - 수익률: {m['total_return']:.2%}, "
                  f"샤프: {m['sharpe']:.2f}, MDD: {m['mdd']:.2%}")

            print()
            if m['total_return'] > test['hodl']:
                print("✅ 전략이 단순 보유를 이겼습니다")
            else:
                print("❌ 단순 보유가 더 좋았습니다")

            if m['sharpe'] > 1:
                print("✅ 샤프 비율 양호 (> 1)")
            else:
                print("⚠️ 샤프 비율 낮음")
        else:
            print("테스트 기간에 거래 없음")


def main_grid(config: BacktestConfig):
    """그리드 서치 실행"""
    print("=== 그리드 서치 모드 ===")
    print()
    print("데이터 수집 중...")
    df = get_ohlcv_long("day", config.data_days)

    ResultPrinter.header(df, config)

    backtester = Backtester(df, config.total_cost)
    ResultPrinter.hodl(backtester.hodl_return)

    print("\n파라미터 테스트 중...")
    results = backtester.run_grid_search(config.rsi_values, config.vwap_values)

    ResultPrinter.grid_results(results)
    ResultPrinter.best(results)

    return results


def main_walk_forward(config: BacktestConfig):
    """Walk-Forward 테스트 실행"""
    print("=== WALK-FORWARD 모드 ===")
    print()
    print("데이터 수집 중...")
    df = get_ohlcv_long("day", config.data_days)

    ResultPrinter.header(df, config)

    tester = WalkForwardTester(df, config)
    result = tester.run(train_ratio=0.5)

    ResultPrinter.walk_forward(result)

    return result


if __name__ == "__main__":
    config = BacktestConfig(
        data_days=730,
        rsi_values=[30, 40, 50, 60, 70],
        vwap_values=[10, 15, 20, 25, 30],
        fee_rate=0.001,  # 0.1%
        slippage=0.001  # 0.1%
    )

    # 모드 선택
    mode = "walk_forward"  # "grid" 또는 "walk_forward"

    if mode == "grid":
        main_grid(config)
    else:
        main_walk_forward(config)
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

    def __post_init__(self):
        self.rsi_values = self.rsi_values or [30, 40, 50, 60, 70]
        self.vwap_values = self.vwap_values or [10, 15, 20, 25, 30]


class Backtester:
    def __init__(self, df: pd.DataFrame):
        self.df = df
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

        # 수익률 계산
        df['return'] = df['close'].pct_change()
        df['strategy_return'] = df['return'] * df['signal'].shift(1)
        df['position'] = df['signal'].diff()

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

        trades = (df['position'].fillna(0) != 0).sum()

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

        return pd.DataFrame(results).sort_values('sharpe', ascending=False)


class ResultPrinter:
    @staticmethod
    def print_header(df: pd.DataFrame):
        """헤더 정보 출력"""
        print(f"기간: {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)}일)")

    @staticmethod
    def print_hodl(hodl_return: float):
        """단순 보유 수익률 출력"""
        print(f"단순 보유: {hodl_return:.2%}")

    @staticmethod
    def print_results(results: pd.DataFrame):
        """결과 테이블 출력"""
        print()
        print(f"{'RSI':<5}{'VWAP':<6}{'수익률':>9}{'연환산':>9}{'샤프':>7}{'MDD':>9}{'거래':>6}")
        print("-" * 51)

        for _, r in results.iterrows():
            print(f"{int(r['rsi']):<5}{int(r['vwap']):<6}"
                  f"{r['total_return']:>8.2%} {r['annual_return']:>8.2%} "
                  f"{r['sharpe']:>6.2f} {r['mdd']:>8.2%} {r['trades']:>5}")

    @staticmethod
    def print_best(results: pd.DataFrame):
        """최적 파라미터 출력"""
        best = results.iloc[0]
        print()
        print(f"=== 최적: RSI {int(best['rsi'])}, VWAP {int(best['vwap'])} ===")
        print(f"샤프 {best['sharpe']:.2f} | 수익률 {best['total_return']:.2%} | MDD {best['mdd']:.2%}")


def main(config: BacktestConfig):
    """메인 실행"""
    print("데이터 수집 중...")
    df = get_ohlcv_long("day", config.data_days)

    printer = ResultPrinter()
    printer.print_header(df)

    backtester = Backtester(df)
    printer.print_hodl(backtester.hodl_return)

    print("\n파라미터 테스트 중...")
    results = backtester.run_grid_search(config.rsi_values, config.vwap_values)

    printer.print_results(results)
    printer.print_best(results)

    return results


if __name__ == "__main__":
    # 여기서 파라미터 변경
    config = BacktestConfig(
        data_days=730,
        rsi_values=[30, 40, 50, 60, 70],
        vwap_values=[10, 15, 20, 25, 30]
    )

    results = main(config)
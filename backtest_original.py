import pandas as pd
import numpy as np
from collector import get_ohlcv
from indicators import ema


def run_backtest(df, short_period=5, long_period=20):
    """이동평균 크로스 전략 백테스팅"""

    df = df.copy()
    df['ema_short'] = ema(df, short_period)
    df['ema_long'] = ema(df, long_period)

    # 매매 신호 생성
    df['signal'] = 0
    df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1  # 매수
    df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1  # 매도

    # 포지션 변화 감지 (진입/청산 시점)
    df['position'] = df['signal'].diff()

    # 수익률 계산
    df['return'] = df['close'].pct_change()
    df['strategy_return'] = df['return'] * df['signal'].shift(1)

    return df


def calculate_metrics(df):
    """성과 지표 계산"""

    strategy_returns = df['strategy_return'].dropna()

    # 총 수익률
    total_return = (1 + strategy_returns).prod() - 1

    # 연환산 수익률 (일봉 기준)
    days = len(strategy_returns)
    annual_return = (1 + total_return) ** (365 / days) - 1

    # 변동성 (연환산)
    volatility = strategy_returns.std() * np.sqrt(365)

    # 샤프 비율 (무위험 수익률 0 가정)
    sharpe = annual_return / volatility if volatility > 0 else 0

    # MDD
    cumulative = (1 + strategy_returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    mdd = drawdown.min()

    # 거래 횟수
    trades = (df['position'] != 0).sum()

    # 승률
    winning_trades = (strategy_returns > 0).sum()
    total_trades = (strategy_returns != 0).sum()
    win_rate = winning_trades / total_trades if total_trades > 0 else 0

    return {
        '총 수익률': f"{total_return:.2%}",
        '연환산 수익률': f"{annual_return:.2%}",
        '샤프 비율': f"{sharpe:.2f}",
        'MDD': f"{mdd:.2%}",
        '거래 횟수': trades,
        '승률': f"{win_rate:.2%}"
    }


if __name__ == "__main__":
    # 200일치 데이터로 백테스팅
    df = get_ohlcv("day", 200)

    # 백테스팅 실행
    result = run_backtest(df, short_period=5, long_period=20)

    # 성과 지표 출력
    metrics = calculate_metrics(result)

    print("=== 백테스팅 결과 ===")
    print(f"기간: {result.index[0].date()} ~ {result.index[-1].date()}")
    print(f"전략: EMA 5/20 크로스")
    print()
    for key, value in metrics.items():
        print(f"{key}: {value}")
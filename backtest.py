import pandas as pd
import numpy as np
from collector import get_ohlcv
from indicators import ema, sma, rsi


def run_backtest_v2(df, short_period=5, long_period=20, trend_period=60):
    """개선된 전략: EMA 크로스 + RSI 필터 + 추세 필터"""

    df = df.copy()

    # 지표 계산
    df['ema_short'] = ema(df, short_period)
    df['ema_long'] = ema(df, long_period)
    df['ema_trend'] = ema(df, trend_period)
    df['rsi'] = rsi(df, 14)
    df['vol_ma'] = df['volume'].rolling(window=20).mean()

    # 조건 정의
    golden_cross = (df['ema_short'] > df['ema_long']) & (df['ema_short'].shift(1) <= df['ema_long'].shift(1))
    dead_cross = (df['ema_short'] < df['ema_long']) & (df['ema_short'].shift(1) >= df['ema_long'].shift(1))

    uptrend = df['close'] > df['ema_trend']
    rsi_ok = df['rsi'] > 50
    volume_ok = df['volume'] > df['vol_ma']

    # 매매 신호
    df['signal'] = 0
    df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1
    df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1

    # 필터 적용: 조건 안 맞으면 중립
    df.loc[(df['signal'] == 1) & (~uptrend | ~rsi_ok), 'signal'] = 0

    df['position'] = df['signal'].diff()
    df['return'] = df['close'].pct_change()
    df['strategy_return'] = df['return'] * df['signal'].shift(1)

    return df


def calculate_metrics(df):
    """성과 지표 계산"""

    strategy_returns = df['strategy_return'].dropna()

    total_return = (1 + strategy_returns).prod() - 1

    days = len(strategy_returns)
    annual_return = (1 + total_return) ** (365 / days) - 1

    volatility = strategy_returns.std() * np.sqrt(365)
    sharpe = annual_return / volatility if volatility > 0 else 0

    cumulative = (1 + strategy_returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    mdd = drawdown.min()

    trades = (df['position'] != 0).sum()

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


def buy_and_hold(df):
    """단순 보유 수익률"""
    return (df['close'].iloc[-1] / df['close'].iloc[0]) - 1


if __name__ == "__main__":
    df = get_ohlcv("day", 200)

    # 기존 전략
    from backtest_original import run_backtest

    result_v1 = run_backtest(df.copy(), 5, 20)
    metrics_v1 = calculate_metrics(result_v1)

    # 개선 전략
    result_v2 = run_backtest_v2(df.copy(), 5, 20, 60)
    metrics_v2 = calculate_metrics(result_v2)

    # 단순 보유
    hodl = buy_and_hold(df)

    print("=== 전략 비교 ===")
    print(f"기간: {df.index[0].date()} ~ {df.index[-1].date()}")
    print()
    print("[ 단순 보유 (HODL) ]")
    print(f"총 수익률: {hodl:.2%}")
    print()
    print("[ 기존 전략: EMA 크로스 ]")
    for k, v in metrics_v1.items():
        print(f"{k}: {v}")
    print()
    print("[ 개선 전략: EMA 크로스 + RSI + 추세 필터 ]")
    for k, v in metrics_v2.items():
        print(f"{k}: {v}")
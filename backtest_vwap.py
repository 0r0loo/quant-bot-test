import pandas as pd
import numpy as np
from collector import get_ohlcv
from indicators import rsi, vwap_rolling


def run_backtest_vwap(df, rsi_threshold=70, vwap_period=20):
    """RSI + VWAP 전환 전략"""

    df = df.copy()

    # 지표 계산
    df['rsi'] = rsi(df, 14)
    df['vwap'] = vwap_rolling(df, vwap_period)
    df['vwap_prev'] = df['vwap'].shift(1)
    df['vwap_prev2'] = df['vwap'].shift(2)

    # VWAP 전환 감지
    vwap_turning_up = (df['vwap'] > df['vwap_prev']) & (df['vwap_prev'] <= df['vwap_prev2'])
    vwap_turning_down = (df['vwap'] < df['vwap_prev']) & (df['vwap_prev'] >= df['vwap_prev2'])

    # 매매 신호
    df['signal'] = np.nan

    # 매수: RSI > 70 이고 VWAP 하락→상승 전환
    df.loc[(df['rsi'] > rsi_threshold) & vwap_turning_up, 'signal'] = 1

    # 매도: VWAP 상승→하락 전환
    df.loc[vwap_turning_down, 'signal'] = 0

    # 신호 유지 (forward fill)
    df['signal'] = df['signal'].ffill().fillna(0)

    # 수익률 계산
    df['return'] = df['close'].pct_change()
    df['strategy_return'] = df['return'] * df['signal'].shift(1)
    df['position'] = df['signal'].diff()

    return df


def calculate_metrics(df):
    """성과 지표 계산"""

    strategy_returns = df['strategy_return'].dropna()

    total_return = (1 + strategy_returns).prod() - 1

    days = len(strategy_returns)
    if days == 0:
        return {'에러': '데이터 부족'}

    annual_return = (1 + total_return) ** (365 / days) - 1

    volatility = strategy_returns.std() * np.sqrt(365)
    sharpe = annual_return / volatility if volatility > 0 else 0

    cumulative = (1 + strategy_returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (cumulative - peak) / peak
    mdd = drawdown.min()

    trades = (df['position'].fillna(0) != 0).sum()

    winning_days = (strategy_returns > 0).sum()
    trading_days = (strategy_returns != 0).sum()
    win_rate = winning_days / trading_days if trading_days > 0 else 0

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

    result = run_backtest_vwap(df, rsi_threshold=30, vwap_period=20)
    metrics = calculate_metrics(result)
    hodl = buy_and_hold(df)

    print("=== RSI + VWAP 전략 백테스팅 ===")
    print(f"기간: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"조건: RSI > 70 이고 VWAP 상승 전환시 매수, VWAP 하락 전환시 매도")
    print()
    print(f"[ 단순 보유 ]: {hodl:.2%}")
    print()
    print("[ 전략 성과 ]")
    for k, v in metrics.items():
        print(f"{k}: {v}")

    # 최근 신호 확인
    print()
    print("[ 최근 5일 신호 ]")
    print(result[['close', 'rsi', 'vwap', 'signal']].tail())
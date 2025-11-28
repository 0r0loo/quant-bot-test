import pandas as pd


def sma(df, period):
    """단순 이동평균"""
    return df['close'].rolling(window=period).mean()


def ema(df, period):
    """지수 이동평균"""
    return df['close'].ewm(span=period, adjust=False).mean()


def rsi(df, period=14):
    """RSI (상대강도지수)"""
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(df, fast=12, slow=26, signal=9):
    """MACD"""
    ema_fast = ema(df, fast)
    ema_slow = ema(df, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def bollinger_bands(df, period=20, std_dev=2):
    """볼린저 밴드"""
    middle = sma(df, period)
    std = df['close'].rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return upper, middle, lower


def vwap(df):
    """VWAP (거래량 가중 평균 가격)"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    return (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

def vwap_rolling(df, period=20):
    """Rolling VWAP (일정 기간 기준)"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    pv = typical_price * df['volume']
    return pv.rolling(window=period).sum() / df['volume'].rolling(window=period).sum()


if __name__ == "__main__":
    from collector import get_ohlcv

    df = get_ohlcv("day", 100)

    df['sma5'] = sma(df, 5)
    df['sma20'] = sma(df, 20)
    df['rsi'] = rsi(df)

    print("최근 5일 데이터 + 지표:")
    print(df[['close', 'sma5', 'sma20', 'rsi']].tail())
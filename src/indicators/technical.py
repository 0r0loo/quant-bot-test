"""기술적 지표 함수들

모든 함수는 pandas Series 또는 DataFrame을 받아서 Series를 반환합니다.
벡터화된 연산으로 빠른 성능을 제공합니다.
"""

import numpy as np
import pandas as pd


def sma(data: pd.DataFrame | pd.Series, period: int) -> pd.Series:
    """
    단순 이동평균 (Simple Moving Average)

    Args:
        data: DataFrame (close 컬럼 사용) 또는 Series
        period: 이동평균 기간

    Returns:
        SMA Series
    """
    close = data["close"] if isinstance(data, pd.DataFrame) else data
    return close.rolling(window=period).mean()


def ema(data: pd.DataFrame | pd.Series, period: int) -> pd.Series:
    """
    지수 이동평균 (Exponential Moving Average)

    Args:
        data: DataFrame (close 컬럼 사용) 또는 Series
        period: 이동평균 기간

    Returns:
        EMA Series
    """
    close = data["close"] if isinstance(data, pd.DataFrame) else data
    return close.ewm(span=period, adjust=False).mean()


def rsi(data: pd.DataFrame | pd.Series, period: int = 14) -> pd.Series:
    """
    상대강도지수 (Relative Strength Index)

    Args:
        data: DataFrame (close 컬럼 사용) 또는 Series
        period: RSI 기간 (기본 14)

    Returns:
        RSI Series (0-100)
    """
    close = data["close"] if isinstance(data, pd.DataFrame) else data
    delta = close.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(
    data: pd.DataFrame | pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence)

    Args:
        data: DataFrame (close 컬럼 사용) 또는 Series
        fast: 빠른 EMA 기간 (기본 12)
        slow: 느린 EMA 기간 (기본 26)
        signal: 시그널 라인 기간 (기본 9)

    Returns:
        (MACD 라인, 시그널 라인, 히스토그램)
    """
    close = data["close"] if isinstance(data, pd.DataFrame) else data

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def bollinger_bands(
    data: pd.DataFrame | pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    볼린저 밴드 (Bollinger Bands)

    Args:
        data: DataFrame (close 컬럼 사용) 또는 Series
        period: 이동평균 기간 (기본 20)
        std_dev: 표준편차 배수 (기본 2)

    Returns:
        (상단 밴드, 중간 밴드, 하단 밴드)
    """
    close = data["close"] if isinstance(data, pd.DataFrame) else data

    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    return upper, middle, lower


def vwap(data: pd.DataFrame) -> pd.Series:
    """
    VWAP (Volume Weighted Average Price) - 누적

    Args:
        data: DataFrame with high, low, close, volume columns

    Returns:
        VWAP Series
    """
    typical_price = (data["high"] + data["low"] + data["close"]) / 3
    return (typical_price * data["volume"]).cumsum() / data["volume"].cumsum()


def vwap_rolling(data: pd.DataFrame, period: int = 20) -> pd.Series:
    """
    Rolling VWAP (일정 기간 기준)

    Args:
        data: DataFrame with high, low, close, volume columns
        period: 롤링 기간 (기본 20)

    Returns:
        Rolling VWAP Series
    """
    typical_price = (data["high"] + data["low"] + data["close"]) / 3
    pv = typical_price * data["volume"]
    return pv.rolling(window=period).sum() / data["volume"].rolling(window=period).sum()


def atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    평균 실제 범위 (Average True Range)

    Args:
        data: DataFrame with high, low, close columns
        period: ATR 기간 (기본 14)

    Returns:
        ATR Series
    """
    high = data["high"]
    low = data["low"]
    close = data["close"]

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()


def stochastic(
    data: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """
    스토캐스틱 (Stochastic Oscillator)

    Args:
        data: DataFrame with high, low, close columns
        k_period: %K 기간 (기본 14)
        d_period: %D 기간 (기본 3)

    Returns:
        (%K, %D)
    """
    high = data["high"]
    low = data["low"]
    close = data["close"]

    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    stoch_d = stoch_k.rolling(window=d_period).mean()

    return stoch_k, stoch_d


# ===== 편의 함수 =====


def add_all_indicators(
    df: pd.DataFrame,
    ema_periods: list[int] = [5, 20, 60],
    rsi_period: int = 14,
) -> pd.DataFrame:
    """
    DataFrame에 주요 지표 추가

    Args:
        df: OHLCV DataFrame
        ema_periods: EMA 기간 리스트
        rsi_period: RSI 기간

    Returns:
        지표가 추가된 DataFrame
    """
    df = df.copy()

    # EMA
    for period in ema_periods:
        df[f"ema_{period}"] = ema(df, period)

    # RSI
    df["rsi"] = rsi(df, rsi_period)

    # MACD
    df["macd"], df["macd_signal"], df["macd_hist"] = macd(df)

    # Bollinger Bands
    df["bb_upper"], df["bb_middle"], df["bb_lower"] = bollinger_bands(df)

    # VWAP
    df["vwap"] = vwap_rolling(df, 20)

    return df

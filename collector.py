import pyupbit
import pandas as pd
import time


def get_current_price():
    """현재가 조회"""
    return pyupbit.get_current_price("KRW-BTC")


def get_ohlcv(interval="day", count=200):
    """캔들 데이터 조회"""
    df = pyupbit.get_ohlcv("KRW-BTC", interval=interval, count=count)
    return df


def get_ohlcv_long(interval="day", days=730):
    """장기 캔들 데이터 조회 (여러 번 호출해서 이어붙이기)"""

    all_data = []
    to = None
    remaining = days

    while remaining > 0:
        count = min(200, remaining)

        if to is None:
            df = pyupbit.get_ohlcv("KRW-BTC", interval=interval, count=count)
        else:
            df = pyupbit.get_ohlcv("KRW-BTC", interval=interval, count=count, to=to)

        if df is None or len(df) == 0:
            break

        all_data.append(df)
        to = df.index[0]
        remaining -= len(df)

        time.sleep(0.2)  # API 제한 방지

    if not all_data:
        return None

    result = pd.concat(all_data)
    result = result[~result.index.duplicated(keep='first')]
    result = result.sort_index()

    return result


if __name__ == "__main__":
    print("=== 장기 데이터 수집 테스트 ===")
    df = get_ohlcv_long("day", 730)
    print(f"수집 기간: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"총 {len(df)}일치 데이터")
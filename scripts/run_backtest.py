#!/usr/bin/env python3
"""
백테스트 실행 스크립트

사용법:
    python scripts/run_backtest.py
    python scripts/run_backtest.py --symbol BTC --days 365
    python scripts/run_backtest.py --grid-search
    python scripts/run_backtest.py --walk-forward
"""

import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest import BacktestEngine
from src.exchanges import get_exchange
from src.strategies import EMACrossStrategy
from src.strategies.ema_cross import SimpleEMACrossStrategy


def run_single_backtest(args):
    """단일 전략 백테스트"""
    print(f"\n{'='*60}")
    print(f"단일 백테스트: {args.symbol}")
    print(f"{'='*60}")

    # 거래소에서 데이터 조회
    exchange = get_exchange("upbit")
    df = exchange.get_ohlcv_sync(args.symbol, interval=args.interval, limit=args.days)

    print(f"데이터 기간: {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)}일)")

    # 백테스트 엔진
    engine = BacktestEngine(
        fee_rate=args.fee_rate,
        slippage=args.slippage,
    )

    # 전략 생성
    strategies = [
        SimpleEMACrossStrategy(short_period=5, long_period=20),
        EMACrossStrategy(
            short_period=5,
            long_period=20,
            trend_period=60,
            use_trend_filter=True,
            use_rsi_filter=True,
        ),
    ]

    # 비교 실행
    results = engine.compare_strategies(df, strategies)

    print(f"\n{'='*60}")
    print("전략 비교 결과")
    print(f"{'='*60}")

    for _, row in results.iterrows():
        print(f"\n[{row['strategy']}]")
        print(f"  수익률: {row['total_return']:.2%}")
        print(f"  연환산: {row['annual_return']:.2%}")
        print(f"  샤프비율: {row['sharpe_ratio']:.2f}")
        print(f"  MDD: {row['max_drawdown']:.2%}")
        print(f"  승률: {row['win_rate']:.2%}")
        print(f"  거래횟수: {row['total_trades']}")

    print(f"\nHODL 수익률: {results['hodl_return'].iloc[0]:.2%}")


def run_grid_search(args):
    """그리드 서치"""
    print(f"\n{'='*60}")
    print(f"그리드 서치: {args.symbol}")
    print(f"{'='*60}")

    exchange = get_exchange("upbit")
    df = exchange.get_ohlcv_sync(args.symbol, interval=args.interval, limit=args.days)

    print(f"데이터 기간: {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)}일)")

    engine = BacktestEngine(fee_rate=args.fee_rate, slippage=args.slippage)

    # 파라미터 그리드
    param_grid = {
        "short_period": [3, 5, 7, 10],
        "long_period": [15, 20, 25, 30],
        "rsi_threshold": [40, 50, 60],
    }

    print(f"\n파라미터 조합: {len(list(param_grid.values())[0]) * len(list(param_grid.values())[1]) * len(list(param_grid.values())[2])}개")

    results = engine.grid_search(df, EMACrossStrategy, param_grid)

    print(f"\n{'='*60}")
    print("상위 10개 결과")
    print(f"{'='*60}")

    top_10 = results.head(10)
    for i, row in top_10.iterrows():
        print(
            f"\n{i+1}. short={int(row['short_period'])}, "
            f"long={int(row['long_period'])}, "
            f"rsi={int(row['rsi_threshold'])}"
        )
        print(f"   수익률: {row['total_return']:.2%} | 샤프: {row['sharpe_ratio']:.2f} | MDD: {row['max_drawdown']:.2%}")


def run_walk_forward(args):
    """Walk-Forward 테스트"""
    print(f"\n{'='*60}")
    print(f"Walk-Forward 테스트: {args.symbol}")
    print(f"{'='*60}")

    exchange = get_exchange("upbit")
    df = exchange.get_ohlcv_sync(args.symbol, interval=args.interval, limit=args.days)

    print(f"데이터 기간: {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)}일)")

    engine = BacktestEngine(fee_rate=args.fee_rate, slippage=args.slippage)

    param_grid = {
        "short_period": [3, 5, 7, 10],
        "long_period": [15, 20, 25, 30],
        "rsi_threshold": [40, 50, 60],
    }

    result = engine.walk_forward(
        df,
        EMACrossStrategy,
        param_grid,
        train_ratio=args.train_ratio,
    )

    print(f"\n{'='*60}")
    print("Walk-Forward 결과")
    print(f"{'='*60}")

    print(f"\n훈련 기간: {result['train_period']}")
    print(f"테스트 기간: {result['test_period']}")
    print(f"\n최적 파라미터: {result['best_params']}")
    print(f"훈련 샤프비율: {result['train_sharpe']:.2f}")
    print(f"훈련 수익률: {result['train_return']:.2%}")

    test = result["test_result"]
    print(f"\n[테스트 기간 성과]")
    print(f"  {test.metrics}")
    print(f"  HODL: {test.hodl_return:.2%}")


def main():
    parser = argparse.ArgumentParser(description="퀀트봇 백테스트")

    # 기본 옵션
    parser.add_argument("--symbol", default="BTC", help="심볼 (기본: BTC)")
    parser.add_argument("--interval", default="1d", help="시간 간격 (기본: 1d)")
    parser.add_argument("--days", type=int, default=365, help="데이터 기간 (기본: 365)")
    parser.add_argument("--fee-rate", type=float, default=0.001, help="수수료율 (기본: 0.001)")
    parser.add_argument("--slippage", type=float, default=0.001, help="슬리피지 (기본: 0.001)")

    # 실행 모드
    parser.add_argument("--grid-search", action="store_true", help="그리드 서치 실행")
    parser.add_argument("--walk-forward", action="store_true", help="Walk-Forward 테스트")
    parser.add_argument("--train-ratio", type=float, default=0.5, help="훈련 비율 (기본: 0.5)")

    args = parser.parse_args()

    try:
        if args.grid_search:
            run_grid_search(args)
        elif args.walk_forward:
            run_walk_forward(args)
        else:
            run_single_backtest(args)
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

# Quant Bot

암호화폐 퀀트 트레이딩 봇 - 백테스팅 및 자동매매 시스템

## 기능

- **백테스팅**: 과거 데이터로 전략 성과 검증
- **파라미터 최적화**: 그리드 서치, Walk-Forward 테스트
- **다중 거래소**: 업비트, 바이낸스 (현물/선물)
- **커스텀 전략**: 쉽게 새 전략 추가 가능

## 설치

```bash
# 의존성 설치
pip install -e .

# 개발 의존성 포함
pip install -e ".[dev]"
```

## 빠른 시작

### CLI로 백테스트

```bash
# 기본 백테스트 (BTC, 1년)
python scripts/run_backtest.py

# 옵션 지정
python scripts/run_backtest.py --symbol ETH --days 730

# 그리드 서치 (최적 파라미터 탐색)
python scripts/run_backtest.py --grid-search

# Walk-Forward 테스트 (과적합 검증)
python scripts/run_backtest.py --walk-forward
```

### 코드에서 사용

```python
from src.exchanges import get_exchange
from src.strategies import EMACrossStrategy
from src.backtest import BacktestEngine

# 데이터 조회
exchange = get_exchange("upbit")
df = exchange.get_ohlcv_sync("BTC", interval="1d", limit=365)

# 전략 생성
strategy = EMACrossStrategy(
    short_period=5,
    long_period=20,
    use_rsi_filter=True
)

# 백테스트 실행
engine = BacktestEngine(fee_rate=0.001, slippage=0.001)
result = engine.run(df, strategy)

print(result)
# [ema_cross_5_20]
#   수익률: 10.88% | 연환산: 10.91% | 샤프: 0.30 | MDD: -20.60%
```

## CLI 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--symbol` | BTC | 거래 심볼 |
| `--interval` | 1d | 시간 간격 (1m, 5m, 1h, 4h, 1d) |
| `--days` | 365 | 데이터 기간 |
| `--fee-rate` | 0.001 | 거래 수수료 (0.1%) |
| `--slippage` | 0.001 | 슬리피지 (0.1%) |
| `--grid-search` | - | 그리드 서치 실행 |
| `--walk-forward` | - | Walk-Forward 테스트 |
| `--train-ratio` | 0.5 | 훈련 데이터 비율 |

## 프로젝트 구조

```
quant-bot/
├── config/
│   └── settings.py          # 설정 (API 키, 거래 설정)
├── src/
│   ├── models/              # 데이터 모델
│   │   ├── candle.py        # OHLCV
│   │   ├── order.py         # 주문, 포지션
│   │   └── signal.py        # 거래 신호
│   ├── exchanges/           # 거래소 어댑터
│   │   ├── base.py          # 기본 인터페이스
│   │   └── upbit.py         # 업비트
│   ├── indicators/          # 기술적 지표
│   │   └── technical.py     # SMA, EMA, RSI, MACD, BB, VWAP
│   ├── strategies/          # 전략
│   │   ├── base.py          # 기본 인터페이스
│   │   └── ema_cross.py     # EMA 크로스 전략
│   ├── backtest/            # 백테스팅
│   │   ├── engine.py        # 백테스트 엔진
│   │   └── metrics.py       # 성과 지표
│   └── trading/             # 실거래 (개발 중)
├── scripts/
│   └── run_backtest.py      # 백테스트 CLI
└── tests/
```

## 사용 가능한 지표

```python
from src.indicators import (
    sma,              # 단순 이동평균
    ema,              # 지수 이동평균
    rsi,              # RSI (0-100)
    macd,             # MACD (line, signal, histogram)
    bollinger_bands,  # 볼린저 밴드 (upper, middle, lower)
    vwap,             # VWAP (누적)
    vwap_rolling,     # Rolling VWAP
    atr,              # ATR (Average True Range)
    stochastic,       # 스토캐스틱 (%K, %D)
)
```

## 커스텀 전략 만들기

`src/strategies/my_strategy.py`:

```python
import pandas as pd
from src.strategies.base import BaseStrategy
from src.indicators import rsi, bollinger_bands

class BollingerRSIStrategy(BaseStrategy):
    """볼린저 밴드 + RSI 조합 전략"""

    def __init__(self, bb_period=20, rsi_period=14, rsi_lower=30, rsi_upper=70):
        self.bb_period = bb_period
        self.rsi_period = rsi_period
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper

    @property
    def name(self):
        return f"bb_rsi_{self.bb_period}"

    @property
    def params(self):
        return {
            "bb_period": self.bb_period,
            "rsi_period": self.rsi_period,
            "rsi_lower": self.rsi_lower,
            "rsi_upper": self.rsi_upper,
        }

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 지표 계산
        df["upper"], df["middle"], df["lower"] = bollinger_bands(df, self.bb_period)
        df["rsi"] = rsi(df, self.rsi_period)

        # 신호 생성
        df["signal"] = 0

        # 매수: 하단 밴드 터치 + RSI 과매도
        buy_condition = (df["close"] < df["lower"]) & (df["rsi"] < self.rsi_lower)
        df.loc[buy_condition, "signal"] = 1

        # 매도: 상단 밴드 터치 + RSI 과매수
        sell_condition = (df["close"] > df["upper"]) & (df["rsi"] > self.rsi_upper)
        df.loc[sell_condition, "signal"] = -1

        return df
```

전략 등록 후 사용:

```python
from src.strategies import register_strategy
from src.strategies.my_strategy import BollingerRSIStrategy

register_strategy("bb_rsi", BollingerRSIStrategy)

# 그리드 서치
engine.grid_search(df, BollingerRSIStrategy, {
    "bb_period": [15, 20, 25],
    "rsi_lower": [25, 30, 35],
    "rsi_upper": [65, 70, 75],
})
```

## 설정

`.env` 파일 생성:

```env
# 업비트 API (실거래용)
UPBIT_API_KEY=your_api_key
UPBIT_SECRET_KEY=your_secret_key

# 바이낸스 API
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
```

## 성과 지표

| 지표 | 설명 |
|------|------|
| 수익률 | 총 수익률 |
| 연환산 | 연환산 수익률 |
| 샤프비율 | 위험 대비 수익 (높을수록 좋음) |
| MDD | 최대 낙폭 (낮을수록 좋음) |
| 승률 | 수익 거래 비율 |
| 거래횟수 | 총 거래 횟수 |

## 로드맵

- [x] 백테스팅 엔진
- [x] 업비트 거래소
- [x] EMA 크로스 전략
- [ ] 바이낸스 현물/선물
- [ ] 실시간 자동매매
- [ ] 텔레그램 알림
- [ ] 웹 대시보드

## 라이선스

MIT

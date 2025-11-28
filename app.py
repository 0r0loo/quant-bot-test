"""
퀀트봇 백테스팅 대시보드

실행: streamlit run app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.exchanges import get_exchange
from src.strategies import EMACrossStrategy
from src.strategies.ema_cross import SimpleEMACrossStrategy
from src.backtest import BacktestEngine

# 페이지 설정
st.set_page_config(
    page_title="퀀트봇 백테스팅",
    page_icon="📈",
    layout="wide"
)

st.title("📈 퀀트봇 백테스팅 대시보드")

# 사이드바 - 파라미터 설정
st.sidebar.header("⚙️ 설정")

# 데이터 설정
st.sidebar.subheader("📊 데이터")
symbol = st.sidebar.selectbox(
    "코인",
    ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA"],
    index=0
)
days = st.sidebar.slider("기간 (일)", 30, 730, 365)
interval = st.sidebar.selectbox(
    "시간 간격",
    ["1d", "4h", "1h"],
    index=0
)

# 전략 파라미터
st.sidebar.subheader("📐 전략 파라미터")
short_period = st.sidebar.slider("단기 EMA", 3, 20, 5)
long_period = st.sidebar.slider("장기 EMA", 10, 60, 20)
trend_period = st.sidebar.slider("추세 EMA", 30, 120, 60)
rsi_threshold = st.sidebar.slider("RSI 기준", 30, 70, 50)

use_trend_filter = st.sidebar.checkbox("추세 필터 사용", value=True)
use_rsi_filter = st.sidebar.checkbox("RSI 필터 사용", value=True)

# 거래 비용
st.sidebar.subheader("💰 거래 비용")
fee_rate = st.sidebar.slider("수수료 (%)", 0.0, 0.5, 0.1, 0.05) / 100
slippage = st.sidebar.slider("슬리피지 (%)", 0.0, 0.5, 0.1, 0.05) / 100


# 데이터 로딩 (캐싱)
@st.cache_data(ttl=300)
def load_data(symbol: str, interval: str, days: int):
    exchange = get_exchange("upbit")
    return exchange.get_ohlcv_sync(symbol, interval=interval, limit=days)


# 백테스트 실행
def run_backtest(df, short_period, long_period, trend_period, rsi_threshold,
                 use_trend_filter, use_rsi_filter, fee_rate, slippage):
    engine = BacktestEngine(fee_rate=fee_rate, slippage=slippage)

    # 필터 적용 전략
    strategy = EMACrossStrategy(
        short_period=short_period,
        long_period=long_period,
        trend_period=trend_period,
        rsi_threshold=rsi_threshold,
        use_trend_filter=use_trend_filter,
        use_rsi_filter=use_rsi_filter,
    )

    # 단순 전략 (비교용)
    simple_strategy = SimpleEMACrossStrategy(
        short_period=short_period,
        long_period=long_period,
    )

    result = engine.run(df, strategy)
    simple_result = engine.run(df, simple_strategy)

    return result, simple_result


# 메인 실행
with st.spinner("데이터 로딩 중..."):
    df = load_data(symbol, interval, days)

if df is not None and len(df) > 0:
    # 백테스트 실행
    result, simple_result = run_backtest(
        df, short_period, long_period, trend_period, rsi_threshold,
        use_trend_filter, use_rsi_filter, fee_rate, slippage
    )

    # 상단 지표 카드
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "총 수익률",
            f"{result.metrics.total_return:.2%}",
            delta=f"vs HODL {result.metrics.total_return - result.hodl_return:.2%}"
        )

    with col2:
        st.metric("연환산 수익률", f"{result.metrics.annual_return:.2%}")

    with col3:
        st.metric("샤프 비율", f"{result.metrics.sharpe_ratio:.2f}")

    with col4:
        st.metric("MDD", f"{result.metrics.max_drawdown:.2%}")

    with col5:
        st.metric("승률", f"{result.metrics.win_rate:.2%}")

    # 차트
    st.subheader("📊 성과 차트")

    # 자산 곡선 계산
    hodl_equity = 10_000_000 * (df['close'] / df['close'].iloc[0])

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=("자산 곡선", "가격 & EMA", "RSI")
    )

    # 자산 곡선
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=result.equity_curve,
            name="전략 (필터)",
            line=dict(color="blue", width=2)
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=simple_result.equity_curve,
            name="전략 (단순)",
            line=dict(color="orange", width=1, dash="dash")
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=hodl_equity.values,
            name="HODL",
            line=dict(color="gray", width=1, dash="dot")
        ),
        row=1, col=1
    )

    # 가격 & EMA
    result_df = result.df
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="가격",
            showlegend=False
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=result_df['ema_short'],
            name=f"EMA {short_period}",
            line=dict(color="orange", width=1)
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=result_df['ema_long'],
            name=f"EMA {long_period}",
            line=dict(color="purple", width=1)
        ),
        row=2, col=1
    )

    # RSI
    if 'rsi' in result_df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=result_df['rsi'],
                name="RSI",
                line=dict(color="green", width=1)
            ),
            row=3, col=1
        )

        # RSI 기준선
        fig.add_hline(y=rsi_threshold, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="gray", row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="gray", row=3, col=1)

    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # 전략 비교 테이블
    st.subheader("📋 전략 비교")

    comparison_data = {
        "지표": ["총 수익률", "연환산", "샤프비율", "MDD", "승률", "거래횟수"],
        "EMA + 필터": [
            f"{result.metrics.total_return:.2%}",
            f"{result.metrics.annual_return:.2%}",
            f"{result.metrics.sharpe_ratio:.2f}",
            f"{result.metrics.max_drawdown:.2%}",
            f"{result.metrics.win_rate:.2%}",
            result.metrics.total_trades,
        ],
        "EMA 단순": [
            f"{simple_result.metrics.total_return:.2%}",
            f"{simple_result.metrics.annual_return:.2%}",
            f"{simple_result.metrics.sharpe_ratio:.2f}",
            f"{simple_result.metrics.max_drawdown:.2%}",
            f"{simple_result.metrics.win_rate:.2%}",
            simple_result.metrics.total_trades,
        ],
        "HODL": [
            f"{result.hodl_return:.2%}",
            f"{((1 + result.hodl_return) ** (365/len(df)) - 1):.2%}",
            "-",
            "-",
            "-",
            0,
        ],
    }

    st.table(pd.DataFrame(comparison_data))

    # 데이터 기간 정보
    st.caption(f"📅 데이터 기간: {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)}개 봉)")

else:
    st.error("데이터를 불러올 수 없습니다.")

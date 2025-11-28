"""프로젝트 설정 - Pydantic Settings 기반"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExchangeSettings(BaseSettings):
    """거래소 API 설정"""

    model_config = SettingsConfigDict(env_prefix="")

    # 업비트
    upbit_api_key: str = ""
    upbit_secret_key: str = ""

    # 바이낸스
    binance_api_key: str = ""
    binance_secret_key: str = ""


class BacktestSettings(BaseSettings):
    """백테스트 설정"""

    model_config = SettingsConfigDict(env_prefix="BACKTEST_")

    initial_capital: float = Field(default=10_000_000, description="초기 자본금 (KRW)")
    fee_rate: float = Field(default=0.001, description="거래 수수료율 (0.1%)")
    slippage: float = Field(default=0.001, description="슬리피지 (0.1%)")


class TradingSettings(BaseSettings):
    """실거래 설정"""

    model_config = SettingsConfigDict(env_prefix="TRADING_")

    max_position_size: float = Field(default=1.0, description="최대 포지션 크기 (0.0~1.0)")
    stop_loss: float = Field(default=0.05, description="손절 비율 (5%)")
    take_profit: float = Field(default=0.1, description="익절 비율 (10%)")


class Settings(BaseSettings):
    """전역 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 기본 설정
    default_exchange: Literal["upbit", "binance"] = "upbit"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # 하위 설정
    exchange: ExchangeSettings = Field(default_factory=ExchangeSettings)
    backtest: BacktestSettings = Field(default_factory=BacktestSettings)
    trading: TradingSettings = Field(default_factory=TradingSettings)


@lru_cache
def get_settings() -> Settings:
    """설정 싱글톤"""
    return Settings()


# 편의를 위한 전역 인스턴스
settings = get_settings()

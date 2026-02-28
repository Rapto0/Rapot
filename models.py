"""
SQLAlchemy ORM Modelleri
Sinyal, trade, tarama geçmişi ve bot istatistikleri için veritabanı modelleri.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


# ==================== ENUMS ====================


class SignalType(enum.Enum):
    """Sinyal türü."""

    BUY = "AL"
    SELL = "SAT"


class MarketType(enum.Enum):
    """Piyasa türü."""

    BIST = "BIST"
    CRYPTO = "Kripto"


class StrategyType(enum.Enum):
    """Strateji türü."""

    COMBO = "COMBO"
    HUNTER = "HUNTER"


class TradeStatus(enum.Enum):
    """Trade durumu."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class TradeDirection(enum.Enum):
    """Trade yönü."""

    BUY = "BUY"
    SELL = "SELL"


# ==================== MODELS ====================


class Signal(Base):
    """
    Sinyal modeli.

    COMBO ve HUNTER stratejilerinden gelen AL/SAT sinyallerini saklar.
    """

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    market_type = Column(String(10), nullable=False)  # BIST, Kripto
    strategy = Column(String(20), nullable=False)  # COMBO, HUNTER
    signal_type = Column(String(5), nullable=False)  # AL, SAT
    timeframe = Column(String(15), nullable=False)  # 1D, W-FRI, 2W-FRI, 3W-FRI, ME
    score = Column(String(50))  # Örn: "+4/-0" veya "7/7"
    price = Column(Float, default=0.0)
    special_tag = Column(
        String(20), nullable=True, index=True
    )  # BELES, COK_UCUZ, PAHALI, FAHIS_FIYAT
    details = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    trades = relationship("Trade", back_populates="signal", lazy="dynamic")

    # Composite unique constraint
    __table_args__ = (Index("idx_signal_lookup", "symbol", "strategy", "timeframe"),)

    def __repr__(self) -> str:
        return (
            f"<Signal(id={self.id}, symbol='{self.symbol}', "
            f"strategy='{self.strategy}', type='{self.signal_type}')>"
        )

    def to_dict(self) -> dict:
        """Model'i dictionary'ye çevirir."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "market_type": self.market_type,
            "strategy": self.strategy,
            "signal_type": self.signal_type,
            "timeframe": self.timeframe,
            "score": self.score,
            "price": self.price,
            "special_tag": self.special_tag,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Trade(Base):
    """
    Trade modeli.

    Sinyallere dayalı alım/satım işlemlerini ve PnL takibini sağlar.
    """

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    market_type = Column(String(10), nullable=False)
    direction = Column(String(5), nullable=False)  # BUY, SELL
    price = Column(Float, nullable=False)  # entry price
    quantity = Column(Float, nullable=False, default=1.0)
    pnl = Column(Float, default=0.0)
    status = Column(String(15), default="OPEN", index=True)  # OPEN, CLOSED, CANCELLED
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    # Relationship
    signal = relationship("Signal", back_populates="trades")

    def __repr__(self) -> str:
        return (
            f"<Trade(id={self.id}, symbol='{self.symbol}', "
            f"direction='{self.direction}', status='{self.status}')>"
        )

    def calculate_pnl(self, current_price: float) -> float:
        """
        PnL hesaplar.

        Args:
            current_price: Güncel fiyat

        Returns:
            pnl_amount
        """
        if self.direction == "BUY":
            pnl = (current_price - self.price) * self.quantity
        else:
            pnl = (self.price - current_price) * self.quantity

        return pnl

    def close(self, exit_price: float) -> None:
        """Trade'i kapatır."""
        self.pnl = self.calculate_pnl(exit_price)
        self.status = "CLOSED"
        self.closed_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Model'i dictionary'ye çevirir."""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "market_type": self.market_type,
            "direction": self.direction,
            "price": self.price,
            "quantity": self.quantity,
            "pnl": self.pnl,
            "status": self.status,
            "signal_id": self.signal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


class ScanHistory(Base):
    """
    Tarama geçmişi modeli.

    Her tarama döngüsünün istatistiklerini saklar.
    """

    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_type = Column(String(20), nullable=False)  # BIST, Kripto, Full
    mode = Column(String(10), default="sync")  # sync, async
    symbols_scanned = Column(Integer, default=0)
    signals_found = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return (
            f"<ScanHistory(id={self.id}, type='{self.scan_type}', "
            f"symbols={self.symbols_scanned}, signals={self.signals_found})>"
        )

    def to_dict(self) -> dict:
        """Model'i dictionary'ye çevirir."""
        return {
            "id": self.id,
            "scan_type": self.scan_type,
            "mode": self.mode,
            "symbols_scanned": self.symbols_scanned,
            "signals_found": self.signals_found,
            "errors_count": self.errors_count,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class BotStat(Base):
    """
    Bot istatistikleri modeli.

    Key-value formatında bot durumu ve ayarlarını saklar.
    """

    __tablename__ = "bot_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stat_name = Column(String(50), nullable=False, unique=True, index=True)
    stat_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<BotStat(name='{self.stat_name}', value='{self.stat_value}')>"

    def to_dict(self) -> dict:
        """Model'i dictionary'ye çevirir."""
        return {
            "id": self.id,
            "stat_name": self.stat_name,
            "stat_value": self.stat_value,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AIAnalysis(Base):
    """
    AI Analiz modeli.

    Gemini AI tarafından üretilen teknik analizleri saklar.
    """

    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    market_type = Column(String(10), nullable=False)  # BIST, Kripto
    scenario_name = Column(String(50))  # COMBO AL, HUNTER DİP, vb.
    signal_type = Column(String(5))  # AL, SAT
    analysis_text = Column(Text, nullable=False)  # AI tarafından üretilen yorum
    technical_data = Column(Text)  # JSON string - teknik göstergeler
    provider = Column(String(20))
    model = Column(String(100))
    backend = Column(String(50))
    prompt_version = Column(String(50))
    sentiment_score = Column(Integer)
    sentiment_label = Column(String(20))
    confidence_score = Column(Integer)
    risk_level = Column(String(20))
    technical_bias = Column(String(20))
    technical_strength = Column(Integer)
    news_bias = Column(String(20))
    news_strength = Column(Integer)
    headline_count = Column(Integer)
    latency_ms = Column(Integer)
    error_code = Column(String(40))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    signal = relationship("Signal", backref="analyses")

    def __repr__(self) -> str:
        return (
            f"<AIAnalysis(id={self.id}, symbol='{self.symbol}', "
            f"scenario='{self.scenario_name}')>"
        )

    def to_dict(self) -> dict:
        """Model'i dictionary'ye çevirir."""
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "market_type": self.market_type,
            "scenario_name": self.scenario_name,
            "signal_type": self.signal_type,
            "analysis_text": self.analysis_text,
            "technical_data": self.technical_data,
            "provider": self.provider,
            "model": self.model,
            "backend": self.backend,
            "prompt_version": self.prompt_version,
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.sentiment_label,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level,
            "technical_bias": self.technical_bias,
            "technical_strength": self.technical_strength,
            "news_bias": self.news_bias,
            "news_strength": self.news_strength,
            "headline_count": self.headline_count,
            "latency_ms": self.latency_ms,
            "error_code": self.error_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

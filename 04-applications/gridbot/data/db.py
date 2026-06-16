from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlmodel import SQLModel, Field, Session, create_engine, Relationship


class GridType(str, Enum):
    ARITHMETIC = "arithmetic"
    GEOMETRIC = "geometric"


class GridStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class Grid(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    grid_type: str = Field(default="arithmetic")
    status: str = Field(default="idle", index=True)

    upper_price: float
    lower_price: float
    grid_count: int
    investment_amount: float
    quantity_per_grid: float

    realized_pnl: float = 0.0
    total_buy_volume: float = 0.0
    total_sell_volume: float = 0.0
    total_trades: int = 0

    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_tick_at: Optional[datetime] = None

    levels: List["GridLevel"] = Relationship(
        back_populates="grid",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    trades: List["Trade"] = Relationship(
        back_populates="grid",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class GridLevel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    grid_id: int = Field(foreign_key="grid.id", index=True)
    level_index: int
    price: float

    buy_order_id: Optional[str] = None
    sell_order_id: Optional[str] = None
    buy_filled: bool = False
    sell_filled: bool = False
    buy_filled_at: Optional[datetime] = None
    sell_filled_at: Optional[datetime] = None

    grid: Grid = Relationship(back_populates="levels")


class Trade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    grid_id: int = Field(foreign_key="grid.id", index=True)
    symbol: str
    buy_price: float
    sell_price: float
    quantity: float
    profit: float
    profit_pct: float
    buy_filled_at: datetime
    sell_filled_at: datetime

    grid: Grid = Relationship(back_populates="trades")


class DailyStat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(index=True)
    total_realized_pnl: float = 0.0
    total_trades: int = 0
    active_grids: int = 0
    ai_coin_picks: Optional[str] = None
    sentiment_score: Optional[float] = None
    regime_summary: Optional[str] = None


class CoinAnalysis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    analyzed_at: datetime = Field(default_factory=datetime.now)
    regime: Optional[str] = None
    sentiment_score: Optional[float] = None
    grid_suitability: Optional[float] = None
    ai_reasoning: Optional[str] = None
    recommendation: Optional[str] = None


def init_db(db_url: str):
    connect_args = {"check_same_thread": False}
    if "sqlite" in db_url:
        connect_args["timeout"] = 30

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    SQLModel.metadata.create_all(engine)

    if "sqlite" in db_url:
        from sqlmodel import text
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            conn.execute(text("PRAGMA busy_timeout=5000"))
            conn.commit()

    return engine


def get_session(engine):
    with Session(engine) as session:
        yield session

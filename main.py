#!/usr/bin/env python3
"""
==============================================================================
AUTO SCANNER v2.0 - Streamlit Web Application
==============================================================================
"""

import warnings
warnings.filterwarnings('ignore')

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, time, date
import time as time_module
import json
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import Enum
from copy import deepcopy
import uuid
import io


# ==============================================================================
# PAGE CONFIG
# ==============================================================================

st.set_page_config(
    page_title="Auto Scanner v2.0",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# CUSTOM CSS
# ==============================================================================

st.markdown("""
<style>
    /* Main header */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #e94560;
    }
    .main-header h1 {
        color: #e94560;
        margin: 0;
        font-size: 2em;
    }
    .main-header p {
        color: #a8a8a8;
        margin: 5px 0 0 0;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        color: white;
    }
    .metric-card h3 {
        color: #a8a8a8;
        font-size: 0.85em;
        margin: 0;
    }
    .metric-card h2 {
        color: #e94560;
        margin: 5px 0;
    }

    /* Signal cards */
    .signal-call {
        background: linear-gradient(135deg, #0d3b0d, #1a5c1a);
        border: 1px solid #2ecc71;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
    }
    .signal-put {
        background: linear-gradient(135deg, #3b0d0d, #5c1a1a);
        border: 1px solid #e74c3c;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
    }

    /* Trade status badges */
    .badge-active {
        background: #f39c12;
        color: black;
        padding: 3px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8em;
    }
    .badge-target {
        background: #2ecc71;
        color: black;
        padding: 3px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8em;
    }
    .badge-sl {
        background: #e74c3c;
        color: white;
        padding: 3px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8em;
    }
    .badge-time {
        background: #3498db;
        color: white;
        padding: 3px 10px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8em;
    }

    /* VIX indicator */
    .vix-low { color: #2ecc71; font-weight: bold; }
    .vix-moderate { color: #f39c12; font-weight: bold; }
    .vix-high { color: #e67e22; font-weight: bold; }
    .vix-extreme { color: #e74c3c; font-weight: bold; }

    /* Pivot table */
    .pivot-table {
        width: 100%;
        border-collapse: collapse;
    }
    .pivot-table td, .pivot-table th {
        padding: 8px 12px;
        text-align: center;
        border: 1px solid #333;
    }

    /* Confidence stars */
    .stars { color: #f1c40f; font-size: 1.2em; }

    /* Hide streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1a2e;
        border-radius: 5px;
        padding: 8px 16px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# CONFIGURATION
# ==============================================================================

class Config:
    INDEX_SYMBOLS = {
        'NIFTY': '^NSEI',
        'BANKNIFTY': '^NSEBANK',
        'SENSEX': '^BSESN',
        'FINNIFTY': 'NIFTY_FIN_SERVICE.NS'
    }

    STRIKE_STEPS = {
        'NIFTY': 50, 'BANKNIFTY': 100,
        'SENSEX': 100, 'FINNIFTY': 50
    }

    LOT_SIZES = {
        'NIFTY': 25, 'BANKNIFTY': 15,
        'SENSEX': 10, 'FINNIFTY': 25
    }

    VIX_SYMBOL = '^INDIAVIX'
    VIX_HALT_THRESHOLD = 40

    SMA_PERIOD = 50
    RSI_PERIOD = 14
    RSI_CALL_THRESHOLD = 60
    RSI_PUT_THRESHOLD = 40

    MOMENTUM_THRESHOLD_930 = 0.15
    MOMENTUM_THRESHOLD_1100 = 0.20
    ITM_STRIKES_DEEP = 2

    OI_SIGNAL_THRESHOLD = 0.10

    STOPLOSS_PCT = 0.25
    RISK_REWARD_RATIO = 2

    INTRADAY_EXIT_TIME = time(15, 15)
    BTST_EXIT_TIME = time(9, 30)

    CPR_NARROW_THRESHOLD = 0.5
    SCAN_INTERVAL = 60
    CHART_INTERVAL = '5m'
    CHART_PERIOD = '5d'

    LOG_DIR = "trade_logs"
    LOG_FILE_PREFIX = "scanner_trades"
    PERFORMANCE_FILE = "performance_summary.json"


# ==============================================================================
# ENUMS & DATA CLASSES
# ==============================================================================

class SignalType(Enum):
    CALL = "CALL"
    PUT = "PUT"
    NONE = "NONE"


class MarketType(Enum):
    TRENDING = "TRENDING"
    RANGEBOUND = "RANGEBOUND"
    UNKNOWN = "UNKNOWN"


class EntryType(Enum):
    MOMENTUM_930 = "MOMENTUM_9:30AM"
    BTST_1100 = "BTST_11:00AM"
    OI_BREAKOUT = "OI_BREAKOUT"


class TradeStatus(Enum):
    ACTIVE = "ACTIVE"
    TARGET_HIT = "TARGET_HIT"
    SL_HIT = "SL_HIT"
    TIME_EXIT = "TIME_EXIT"
    MANUAL_EXIT = "MANUAL_EXIT"
    EXPIRED = "EXPIRED"


@dataclass
class PivotPoints:
    pivot: float = 0.0
    r1: float = 0.0
    r2: float = 0.0
    r3: float = 0.0
    s1: float = 0.0
    s2: float = 0.0
    s3: float = 0.0
    tc: float = 0.0
    bc: float = 0.0
    cpr_width: float = 0.0
    cpr_width_pct: float = 0.0


@dataclass
class MarketPath:
    index_name: str = ""
    closing_price: float = 0.0
    pivots: PivotPoints = field(default_factory=PivotPoints)
    market_type: MarketType = MarketType.UNKNOWN
    expected_range_pct: float = 0.0
    expected_range_points: float = 0.0
    vix: float = 0.0
    bias: str = "NEUTRAL"
    path_description: str = ""


@dataclass
class OptionSignal:
    trade_id: str = ""
    index: str = ""
    signal_type: SignalType = SignalType.NONE
    entry_type: EntryType = EntryType.MOMENTUM_930
    strike_price: float = 0.0
    entry_price: float = 0.0
    stop_loss: float = 0.0
    target: float = 0.0
    risk_reward: float = 0.0
    lot_size: int = 0
    max_loss: float = 0.0
    max_profit: float = 0.0
    timestamp: str = ""
    sma_confirmed: bool = False
    rsi_confirmed: bool = False
    rsi_value: float = 0.0
    oi_confirmed: bool = False
    momentum_confirmed: bool = False
    vix_safe: bool = False
    confidence_score: int = 0


@dataclass
class TrackedTrade:
    trade_id: str = ""
    signal: OptionSignal = field(default_factory=OptionSignal)
    status: TradeStatus = TradeStatus.ACTIVE
    entry_time: str = ""
    exit_time: str = ""
    exit_price: float = 0.0
    current_price: float = 0.0
    pnl_points: float = 0.0
    pnl_amount: float = 0.0
    pnl_percentage: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = 0.0
    scan_number: int = 0
    date: str = ""
    exit_reason: str = ""

    def to_dict(self) -> dict:
        return {
            'trade_id': self.trade_id,
            'date': self.date,
            'index': self.signal.index,
            'type': self.signal.signal_type.value,
            'entry_type': self.signal.entry_type.value,
            'strike': self.signal.strike_price,
            'entry_price': self.signal.entry_price,
            'stop_loss': self.signal.stop_loss,
            'target': self.signal.target,
            'exit_price': self.exit_price,
            'current_price': self.current_price,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'status': self.status.value,
            'pnl_points': self.pnl_points,
            'pnl_amount': self.pnl_amount,
            'pnl_percentage': self.pnl_percentage,
            'entry_time': self.entry_time,
            'exit_time': self.exit_time,
            'exit_reason': self.exit_reason,
            'confidence': self.signal.confidence_score,
            'lot_size': self.signal.lot_size,
            'sma_confirmed': self.signal.sma_confirmed,
            'rsi_confirmed': self.signal.rsi_confirmed,
            'rsi_value': self.signal.rsi_value,
            'oi_confirmed': self.signal.oi_confirmed,
            'vix_safe': self.signal.vix_safe,
            'scan_number': self.scan_number,
            'risk_reward': self.signal.risk_reward,
        }


# ==============================================================================
# TRADE TRACKER
# ==============================================================================

class TradeTracker:
    def __init__(self):
        self.active_trades: List[TrackedTrade] = []
        self.closed_trades: List[TrackedTrade] = []
        self.all_trades: List[TrackedTrade] = []
        self.daily_stats: Dict = {}
        self.session_date: str = date.today().strftime("%Y-%m-%d")
        os.makedirs(Config.LOG_DIR, exist_ok=True)

    def add_trade(self, signal: OptionSignal, scan_number: int) -> TrackedTrade:
        for t in self.active_trades:
            if (t.signal.index == signal.index and
                t.signal.strike_price == signal.strike_price and
                t.signal.signal_type == signal.signal_type):
                return t

        trade = TrackedTrade()
        trade.trade_id = (
            f"T{datetime.now().strftime('%H%M%S')}_"
            f"{uuid.uuid4().hex[:6].upper()}"
        )
        trade.signal = deepcopy(signal)
        trade.status = TradeStatus.ACTIVE
        trade.entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade.date = self.session_date
        trade.current_price = signal.entry_price
        trade.highest_price = signal.entry_price
        trade.lowest_price = signal.entry_price
        trade.scan_number = scan_number

        self.active_trades.append(trade)
        self.all_trades.append(trade)
        return trade

    def update_prices(self, index_name: str,
                      simulated_price_change: float = None):
        for trade in self.active_trades:
            if trade.signal.index != index_name and index_name != "ALL":
                continue
            if trade.status != TradeStatus.ACTIVE:
                continue

            if simulated_price_change is not None:
                change_factor = simulated_price_change
            else:
                np.random.seed(
                    int(datetime.now().timestamp() * 1000) % 2**31
                )
                change_factor = np.random.uniform(-0.05, 0.06)

            trade.current_price = round(
                trade.signal.entry_price * (1 + change_factor), 2
            )
            trade.highest_price = max(
                trade.highest_price, trade.current_price
            )
            trade.lowest_price = min(
                trade.lowest_price, trade.current_price
            )
            trade.pnl_points = round(
                trade.current_price - trade.signal.entry_price, 2
            )
            trade.pnl_amount = round(
                trade.pnl_points * trade.signal.lot_size, 2
            )
            trade.pnl_percentage = round(
                (trade.pnl_points / trade.signal.entry_price) * 100, 2
            ) if trade.signal.entry_price > 0 else 0

            if trade.current_price <= trade.signal.stop_loss:
                self._close_trade(
                    trade, TradeStatus.SL_HIT,
                    trade.signal.stop_loss, "Stop Loss Hit"
                )
            elif trade.current_price >= trade.signal.target:
                self._close_trade(
                    trade, TradeStatus.TARGET_HIT,
                    trade.signal.target, "Target Achieved"
                )

    def check_time_exit(self):
        now = datetime.now().time()
        for trade in self.active_trades[:]:
            if trade.status != TradeStatus.ACTIVE:
                continue
            if (trade.signal.entry_type != EntryType.BTST_1100 and
                    now >= Config.INTRADAY_EXIT_TIME):
                self._close_trade(
                    trade, TradeStatus.TIME_EXIT,
                    trade.current_price,
                    f"Time Exit at {now.strftime('%H:%M')}"
                )

    def _close_trade(self, trade, status, exit_price, reason):
        trade.status = status
        trade.exit_price = exit_price
        trade.exit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        trade.exit_reason = reason
        trade.pnl_points = round(exit_price - trade.signal.entry_price, 2)
        trade.pnl_amount = round(
            trade.pnl_points * trade.signal.lot_size, 2
        )
        trade.pnl_percentage = round(
            (trade.pnl_points / trade.signal.entry_price) * 100, 2
        ) if trade.signal.entry_price > 0 else 0
        if trade in self.active_trades:
            self.active_trades.remove(trade)
        self.closed_trades.append(trade)

    def force_close_all(self, reason="End of Day"):
        for trade in self.active_trades[:]:
            self._close_trade(
                trade, TradeStatus.TIME_EXIT,
                trade.current_price, reason
            )

    def get_daily_stats(self) -> Dict:
        all_closed = self.closed_trades
        if not all_closed and not self.active_trades:
            return {
                'date': self.session_date,
                'total_signals': 0, 'active': 0, 'closed': 0,
                'targets_hit': 0, 'sl_hit': 0, 'time_exits': 0,
                'winners': 0, 'losers': 0,
                'win_rate': 0, 'total_pnl': 0,
                'avg_pnl_per_trade': 0,
                'best_trade_pnl': 0, 'worst_trade_pnl': 0,
                'total_winners_pnl': 0, 'total_losers_pnl': 0,
                'avg_winner': 0, 'avg_loser': 0,
                'profit_factor': 0, 'max_drawdown': 0,
                'index_breakdown': {}, 'confidence_analysis': {},
            }

        targets = [
            t for t in all_closed if t.status == TradeStatus.TARGET_HIT
        ]
        sls = [t for t in all_closed if t.status == TradeStatus.SL_HIT]
        time_exits = [
            t for t in all_closed if t.status == TradeStatus.TIME_EXIT
        ]
        winners = [t for t in all_closed if t.pnl_amount > 0]
        losers = [t for t in all_closed if t.pnl_amount < 0]

        total_pnl = sum(t.pnl_amount for t in all_closed)
        winners_pnl = sum(t.pnl_amount for t in winners) if winners else 0
        losers_pnl = sum(t.pnl_amount for t in losers) if losers else 0
        total_trades = len(all_closed)
        win_rate = (
            (len(winners) / total_trades * 100) if total_trades > 0 else 0
        )
        profit_factor = (
            abs(winners_pnl / losers_pnl)
            if losers_pnl != 0 else float('inf')
        )

        running_pnl = 0
        peak = 0
        max_dd = 0
        for t in all_closed:
            running_pnl += t.pnl_amount
            peak = max(peak, running_pnl)
            dd = peak - running_pnl
            max_dd = max(max_dd, dd)

        index_stats = {}
        for idx_name in Config.INDEX_SYMBOLS.keys():
            idx_trades = [
                t for t in all_closed if t.signal.index == idx_name
            ]
            idx_winners = [t for t in idx_trades if t.pnl_amount > 0]
            idx_pnl = sum(t.pnl_amount for t in idx_trades)
            index_stats[idx_name] = {
                'trades': len(idx_trades),
                'winners': len(idx_winners),
                'win_rate': (
                    len(idx_winners) / len(idx_trades) * 100
                ) if idx_trades else 0,
                'pnl': idx_pnl
            }

        conf_stats = {}
        for score in range(1, 6):
            sc_trades = [
                t for t in all_closed
                if t.signal.confidence_score == score
            ]
            sc_winners = [t for t in sc_trades if t.pnl_amount > 0]
            sc_pnl = sum(t.pnl_amount for t in sc_trades)
            conf_stats[f"score_{score}"] = {
                'trades': len(sc_trades),
                'winners': len(sc_winners),
                'win_rate': (
                    len(sc_winners) / len(sc_trades) * 100
                ) if sc_trades else 0,
                'pnl': sc_pnl
            }

        stats = {
            'date': self.session_date,
            'total_signals': len(self.all_trades),
            'active': len(self.active_trades),
            'closed': len(all_closed),
            'targets_hit': len(targets),
            'sl_hit': len(sls),
            'time_exits': len(time_exits),
            'winners': len(winners),
            'losers': len(losers),
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 2),
            'avg_pnl_per_trade': (
                round(total_pnl / total_trades, 2)
                if total_trades > 0 else 0
            ),
            'best_trade_pnl': round(
                max((t.pnl_amount for t in all_closed), default=0), 2
            ),
            'worst_trade_pnl': round(
                min((t.pnl_amount for t in all_closed), default=0), 2
            ),
            'total_winners_pnl': round(winners_pnl, 2),
            'total_losers_pnl': round(losers_pnl, 2),
            'avg_winner': (
                round(winners_pnl / len(winners), 2) if winners else 0
            ),
            'avg_loser': (
                round(losers_pnl / len(losers), 2) if losers else 0
            ),
            'profit_factor': (
                round(profit_factor, 2)
                if profit_factor != float('inf') else 999.99
            ),
            'max_drawdown': round(max_dd, 2),
            'index_breakdown': index_stats,
            'confidence_analysis': conf_stats,
        }
        self.daily_stats = stats
        return stats

    def get_trades_df(self) -> pd.DataFrame:
        if not self.all_trades:
            return pd.DataFrame()
        return pd.DataFrame([t.to_dict() for t in self.all_trades])

    def get_csv_data(self) -> str:
        df = self.get_trades_df()
        if df.empty:
            return ""
        return df.to_csv(index=False)

    def get_json_data(self) -> str:
        export_data = {
            'session_date': self.session_date,
            'export_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'summary': self.get_daily_stats(),
            'trades': [t.to_dict() for t in self.all_trades]
        }
        return json.dumps(export_data, indent=2, default=str)

    def export_to_csv(self, filename=None):
        if filename is None:
            filename = os.path.join(
                Config.LOG_DIR,
                f"{Config.LOG_FILE_PREFIX}_{self.session_date}.csv"
            )
        df = self.get_trades_df()
        if not df.empty:
            df.to_csv(filename, index=False)
        return filename

    def export_to_json(self, filename=None):
        if filename is None:
            filename = os.path.join(
                Config.LOG_DIR,
                f"{Config.LOG_FILE_PREFIX}_{self.session_date}.json"
            )
        with open(filename, 'w') as f:
            f.write(self.get_json_data())
        return filename


# ==============================================================================
# TECHNICAL INDICATORS
# ==============================================================================

class TechnicalIndicators:
    @staticmethod
    def calculate_sma(data, period):
        return data.rolling(window=period).mean()

    @staticmethod
    def calculate_rsi(data, period=14):
        delta = data.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        for i in range(period, len(avg_gain)):
            avg_gain.iloc[i] = (
                (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
            )
            avg_loss.iloc[i] = (
                (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period
            )
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_pivot_points(high, low, close):
        pp = PivotPoints()
        pp.pivot = (high + low + close) / 3
        pp.r1 = (2 * pp.pivot) - low
        pp.r2 = pp.pivot + (high - low)
        pp.r3 = high + 2 * (pp.pivot - low)
        pp.s1 = (2 * pp.pivot) - high
        pp.s2 = pp.pivot - (high - low)
        pp.s3 = low - 2 * (high - pp.pivot)
        pp.bc = (high + low) / 2
        pp.tc = (pp.pivot - pp.bc) + pp.pivot
        pp.cpr_width = abs(pp.tc - pp.bc)
        pp.cpr_width_pct = (
            (pp.cpr_width / pp.pivot) * 100 if pp.pivot > 0 else 0
        )
        return pp

    @staticmethod
    def calculate_expected_range(spot_price, vix):
        daily_range_pct = vix / np.sqrt(365)
        daily_range_points = spot_price * (daily_range_pct / 100)
        return daily_range_pct, daily_range_points

    @staticmethod
    def get_atm_strike(spot_price, step):
        return round(spot_price / step) * step

    @staticmethod
    def get_itm_strikes(spot_price, step, signal_type, depth=2):
        atm = TechnicalIndicators.get_atm_strike(spot_price, step)
        strikes = []
        for i in range(1, depth + 1):
            if signal_type == SignalType.CALL:
                strikes.append(atm - (i * step))
            else:
                strikes.append(atm + (i * step))
        return strikes


# ==============================================================================
# DATA FETCHER
# ==============================================================================

class DataFetcher:
    @staticmethod
    @st.cache_data(ttl=55)
    def fetch_index_data(symbol, period='5d', interval='5m'):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            return data if not data.empty else None
        except Exception:
            return None

    @staticmethod
    @st.cache_data(ttl=55)
    def fetch_daily_data(symbol, period='10d'):
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval='1d')
            return data if not data.empty else None
        except Exception:
            return None

    @staticmethod
    @st.cache_data(ttl=55)
    def fetch_vix():
        try:
            vix = yf.Ticker(Config.VIX_SYMBOL)
            data = vix.history(period='5d')
            if data.empty:
                return 15.0
            return float(data['Close'].iloc[-1])
        except Exception:
            return 15.0


# ==============================================================================
# SIMULATED OPTION DATA
# ==============================================================================

class SimulatedOptionData:
    @staticmethod
    def estimate_premium(spot, strike, option_type, vix=15,
                         days_to_expiry=7):
        if option_type == SignalType.CALL:
            intrinsic = max(0, spot - strike)
        else:
            intrinsic = max(0, strike - spot)
        daily_vol = vix / np.sqrt(365) / 100
        time_value = spot * daily_vol * np.sqrt(days_to_expiry) * 0.4
        premium = intrinsic + time_value
        return round(max(premium, time_value * 0.5), 2)

    @staticmethod
    def simulate_oi_data(spot, step, num_strikes=10):
        atm = TechnicalIndicators.get_atm_strike(spot, step)
        oi_data = {'calls': {}, 'puts': {}}
        np.random.seed(int(spot) % 1000)
        for i in range(-num_strikes, num_strikes + 1):
            strike = atm + (i * step)
            distance = abs(i)
            base_oi = max(100000, 500000 - distance * 50000)
            if i > 0:
                call_oi = int(
                    base_oi * (1.2 + np.random.uniform(0, 0.5))
                )
                put_oi = int(
                    base_oi * (0.6 + np.random.uniform(0, 0.3))
                )
            elif i < 0:
                call_oi = int(
                    base_oi * (0.6 + np.random.uniform(0, 0.3))
                )
                put_oi = int(
                    base_oi * (1.2 + np.random.uniform(0, 0.5))
                )
            else:
                call_oi = int(
                    base_oi * (1.0 + np.random.uniform(0, 0.3))
                )
                put_oi = int(
                    base_oi * (1.0 + np.random.uniform(0, 0.3))
                )
            oi_data['calls'][strike] = call_oi
            oi_data['puts'][strike] = put_oi
        return oi_data


# ==============================================================================
# MARKET PATH ANALYZER
# ==============================================================================

class MarketPathAnalyzer:
    def __init__(self):
        self.tech = TechnicalIndicators()

    def analyze(self, index_name, daily_data, vix):
        path = MarketPath()
        path.index_name = index_name
        path.vix = vix
        if daily_data is None or daily_data.empty:
            path.path_description = "Insufficient data"
            return path
        latest = daily_data.iloc[-1]
        path.closing_price = float(latest['Close'])
        high = float(latest['High'])
        low = float(latest['Low'])
        close = float(latest['Close'])
        path.pivots = self.tech.calculate_pivot_points(high, low, close)
        er = self.tech.calculate_expected_range(close, vix)
        path.expected_range_pct, path.expected_range_points = er
        if path.pivots.cpr_width_pct < Config.CPR_NARROW_THRESHOLD:
            path.market_type = MarketType.TRENDING
        else:
            path.market_type = MarketType.RANGEBOUND
        if close > path.pivots.pivot:
            path.bias = "BULLISH"
        elif close < path.pivots.pivot:
            path.bias = "BEARISH"
        else:
            path.bias = "NEUTRAL"
        return path


# ==============================================================================
# SIGNAL GENERATOR
# ==============================================================================

class SignalGenerator:
    def __init__(self):
        self.tech = TechnicalIndicators()
        self.sim = SimulatedOptionData()

    def generate_signals(self, index_name, intraday_data,
                         daily_data, vix, market_path):
        signals = []
        if intraday_data is None or intraday_data.empty:
            return signals
        current_price = float(intraday_data['Close'].iloc[-1])
        step = Config.STRIKE_STEPS.get(index_name, 50)
        lot_size = Config.LOT_SIZES.get(index_name, 25)
        sma = self.tech.calculate_sma(
            intraday_data['Close'], Config.SMA_PERIOD
        )
        rsi = self.tech.calculate_rsi(
            intraday_data['Close'], Config.RSI_PERIOD
        )
        current_sma = (
            float(sma.iloc[-1])
            if not pd.isna(sma.iloc[-1]) else current_price
        )
        current_rsi = (
            float(rsi.iloc[-1])
            if not pd.isna(rsi.iloc[-1]) else 50.0
        )
        vix_safe = vix < Config.VIX_HALT_THRESHOLD
        oi_data = self.sim.simulate_oi_data(current_price, step)

        if self._check_call(
            current_price, current_sma, current_rsi, market_path
        ):
            atm = self.tech.get_atm_strike(current_price, step)
            itm = self.tech.get_itm_strikes(
                current_price, step, SignalType.CALL,
                Config.ITM_STRIKES_DEEP
            )
            for strike in [atm] + itm:
                sig = self._create_signal(
                    index_name, SignalType.CALL, strike,
                    current_price, current_sma, current_rsi,
                    vix, vix_safe, oi_data, lot_size, step
                )
                if sig and sig.confidence_score >= 3:
                    signals.append(sig)

        if self._check_put(
            current_price, current_sma, current_rsi, market_path
        ):
            atm = self.tech.get_atm_strike(current_price, step)
            itm = self.tech.get_itm_strikes(
                current_price, step, SignalType.PUT,
                Config.ITM_STRIKES_DEEP
            )
            for strike in [atm] + itm:
                sig = self._create_signal(
                    index_name, SignalType.PUT, strike,
                    current_price, current_sma, current_rsi,
                    vix, vix_safe, oi_data, lot_size, step
                )
                if sig and sig.confidence_score >= 3:
                    signals.append(sig)

        signals.sort(key=lambda x: x.confidence_score, reverse=True)
        return signals

    def _check_call(self, price, sma, rsi, path):
        score = sum([
            price > sma,
            rsi > Config.RSI_CALL_THRESHOLD,
            path.bias in ["BULLISH", "NEUTRAL"]
        ])
        return score >= 2

    def _check_put(self, price, sma, rsi, path):
        score = sum([
            price < sma,
            rsi < Config.RSI_PUT_THRESHOLD,
            path.bias in ["BEARISH", "NEUTRAL"]
        ])
        return score >= 2

    def _create_signal(self, index_name, signal_type, strike, spot,
                       sma, rsi, vix, vix_safe, oi_data,
                       lot_size, step):
        sig = OptionSignal()
        sig.trade_id = (
            f"S{datetime.now().strftime('%H%M%S')}_"
            f"{uuid.uuid4().hex[:4]}"
        )
        sig.index = index_name
        sig.signal_type = signal_type
        sig.strike_price = strike
        sig.lot_size = lot_size
        sig.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        now = datetime.now().time()
        sig.entry_type = (
            EntryType.MOMENTUM_930
            if now <= time(10, 0) else EntryType.BTST_1100
        )
        premium = self.sim.estimate_premium(
            spot, strike, signal_type, vix
        )
        if premium <= 0:
            return None
        sig.entry_price = premium
        sl_points = premium * Config.STOPLOSS_PCT
        sig.stop_loss = round(premium - sl_points, 2)
        sig.target = round(
            premium + (sl_points * Config.RISK_REWARD_RATIO), 2
        )
        sig.risk_reward = Config.RISK_REWARD_RATIO
        sig.max_loss = round(sl_points * lot_size, 2)
        sig.max_profit = round(
            sl_points * Config.RISK_REWARD_RATIO * lot_size, 2
        )
        sig.sma_confirmed = (
            (spot > sma) if signal_type == SignalType.CALL
            else (spot < sma)
        )
        sig.rsi_value = rsi
        sig.rsi_confirmed = (
            (rsi > Config.RSI_CALL_THRESHOLD)
            if signal_type == SignalType.CALL
            else (rsi < Config.RSI_PUT_THRESHOLD)
        )
        sig.vix_safe = vix_safe
        if signal_type == SignalType.CALL:
            sig.oi_confirmed = (
                oi_data['puts'].get(strike, 0) > 300000
            )
        else:
            sig.oi_confirmed = (
                oi_data['calls'].get(strike, 0) > 300000
            )
        sig.momentum_confirmed = True
        sig.confidence_score = sum([
            sig.sma_confirmed, sig.rsi_confirmed,
            sig.vix_safe, sig.oi_confirmed,
            sig.momentum_confirmed
        ])
        return sig


# ==============================================================================
# CHART BUILDERS (Plotly)
# ==============================================================================

def build_price_chart(intraday_data, index_name, pivots=None):
    """Build candlestick chart with pivot lines."""
    if intraday_data is None or intraday_data.empty:
        return None

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=[f'{index_name} Price', 'Volume']
    )

    fig.add_trace(go.Candlestick(
        x=intraday_data.index,
        open=intraday_data['Open'],
        high=intraday_data['High'],
        low=intraday_data['Low'],
        close=intraday_data['Close'],
        name='Price',
        increasing_line_color='#2ecc71',
        decreasing_line_color='#e74c3c',
    ), row=1, col=1)

    # SMA
    sma = TechnicalIndicators.calculate_sma(
        intraday_data['Close'], Config.SMA_PERIOD
    )
    fig.add_trace(go.Scatter(
        x=intraday_data.index, y=sma,
        name=f'SMA {Config.SMA_PERIOD}',
        line=dict(color='#f39c12', width=1.5),
    ), row=1, col=1)

    # Pivot lines
    if pivots:
        colors = {
            'R2': '#e74c3c', 'R1': '#e74c3c',
            'Pivot': '#f39c12',
            'S1': '#2ecc71', 'S2': '#2ecc71',
        }
        values = {
            'R2': pivots.r2, 'R1': pivots.r1,
            'Pivot': pivots.pivot,
            'S1': pivots.s1, 'S2': pivots.s2,
        }
        for label, val in values.items():
            fig.add_hline(
                y=val, line_dash="dash",
                line_color=colors[label],
                annotation_text=f"{label}: {val:,.0f}",
                annotation_position="right",
                row=1, col=1
            )

    # Volume
    if 'Volume' in intraday_data.columns:
        colors_vol = [
            '#2ecc71' if c >= o else '#e74c3c'
            for c, o in zip(
                intraday_data['Close'], intraday_data['Open']
            )
        ]
        fig.add_trace(go.Bar(
            x=intraday_data.index,
            y=intraday_data['Volume'],
            name='Volume',
            marker_color=colors_vol,
            opacity=0.5,
        ), row=2, col=1)

    fig.update_layout(
        template='plotly_dark',
        height=500,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=50, t=30, b=30),
    )
    return fig


def build_rsi_chart(intraday_data, index_name):
    """Build RSI chart."""
    if intraday_data is None or intraday_data.empty:
        return None

    rsi = TechnicalIndicators.calculate_rsi(
        intraday_data['Close'], Config.RSI_PERIOD
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=intraday_data.index, y=rsi,
        name='RSI', line=dict(color='#9b59b6', width=2),
        fill='tozeroy', fillcolor='rgba(155, 89, 182, 0.1)',
    ))
    fig.add_hline(
        y=70, line_dash="dash", line_color="#e74c3c",
        annotation_text="Overbought (70)"
    )
    fig.add_hline(
        y=30, line_dash="dash", line_color="#2ecc71",
        annotation_text="Oversold (30)"
    )
    fig.add_hline(
        y=60, line_dash="dot", line_color="#f39c12",
        annotation_text="Call Threshold"
    )
    fig.add_hline(
        y=40, line_dash="dot", line_color="#f39c12",
        annotation_text="Put Threshold"
    )
    fig.update_layout(
        template='plotly_dark', height=250,
        yaxis_range=[0, 100],
        title=f"{index_name} RSI ({Config.RSI_PERIOD})",
        margin=dict(l=50, r=50, t=40, b=30),
    )
    return fig


def build_equity_curve(tracker):
    """Build equity curve chart."""
    if not tracker.closed_trades:
        return None

    cum_pnl = []
    running = 0
    labels = []
    for i, t in enumerate(tracker.closed_trades, 1):
        running += t.pnl_amount
        cum_pnl.append(running)
        labels.append(f"Trade #{i}")

    colors = ['#2ecc71' if p >= 0 else '#e74c3c' for p in cum_pnl]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=cum_pnl,
        mode='lines+markers',
        name='Cumulative P&L',
        line=dict(color='#3498db', width=2),
        marker=dict(color=colors, size=8),
        fill='tozeroy',
        fillcolor='rgba(52, 152, 219, 0.1)',
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
    fig.update_layout(
        template='plotly_dark', height=350,
        title="📈 Equity Curve",
        xaxis_title="Trades", yaxis_title="Cumulative P&L (₹)",
        margin=dict(l=50, r=50, t=40, b=30),
    )
    return fig


def build_pnl_distribution(tracker):
    """Build P&L distribution chart."""
    if not tracker.closed_trades:
        return None

    pnl_values = [t.pnl_amount for t in tracker.closed_trades]
    colors = ['#2ecc71' if p >= 0 else '#e74c3c' for p in pnl_values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"T{i+1}" for i in range(len(pnl_values))],
        y=pnl_values,
        marker_color=colors,
        name='P&L per Trade',
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
    fig.update_layout(
        template='plotly_dark', height=300,
        title="📊 P&L Distribution",
        xaxis_title="Trade", yaxis_title="P&L (₹)",
        margin=dict(l=50, r=50, t=40, b=30),
    )
    return fig


def build_win_rate_gauge(win_rate):
    """Build win rate gauge chart."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=win_rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Win Rate %", 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#3498db"},
            'steps': [
                {'range': [0, 40], 'color': '#e74c3c'},
                {'range': [40, 50], 'color': '#e67e22'},
                {'range': [50, 60], 'color': '#f39c12'},
                {'range': [60, 80], 'color': '#2ecc71'},
                {'range': [80, 100], 'color': '#27ae60'},
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75, 'value': win_rate
            }
        }
    ))
    fig.update_layout(
        template='plotly_dark', height=250,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def build_confidence_chart(conf_stats):
    """Build confidence score analysis chart."""
    scores = []
    win_rates = []
    pnls = []
    trade_counts = []

    for score in range(1, 6):
        key = f"score_{score}"
        if key in conf_stats and conf_stats[key]['trades'] > 0:
            scores.append(f"{'⭐' * score}")
            win_rates.append(conf_stats[key]['win_rate'])
            pnls.append(conf_stats[key]['pnl'])
            trade_counts.append(conf_stats[key]['trades'])

    if not scores:
        return None

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=['Win Rate by Confidence', 'P&L by Confidence']
    )
    fig.add_trace(go.Bar(
        x=scores, y=win_rates, name='Win Rate %',
        marker_color='#3498db', text=[f"{wr:.0f}%" for wr in win_rates],
        textposition='auto',
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=scores, y=pnls, name='P&L ₹',
        marker_color=[
            '#2ecc71' if p >= 0 else '#e74c3c' for p in pnls
        ],
        text=[f"₹{p:,.0f}" for p in pnls],
        textposition='auto',
    ), row=1, col=2)
    fig.update_layout(
        template='plotly_dark', height=300,
        showlegend=False,
        margin=dict(l=50, r=50, t=40, b=30),
    )
    return fig


# ==============================================================================
# SESSION STATE INITIALIZATION
# ==============================================================================

def init_session_state():
    """Initialize all session state variables."""
    if 'tracker' not in st.session_state:
        st.session_state.tracker = TradeTracker()
    if 'scan_count' not in st.session_state:
        st.session_state.scan_count = 0
    if 'last_scan_time' not in st.session_state:
        st.session_state.last_scan_time = None
    if 'scan_results' not in st.session_state:
        st.session_state.scan_results = {}
    if 'market_paths' not in st.session_state:
        st.session_state.market_paths = {}
    if 'vix_value' not in st.session_state:
        st.session_state.vix_value = None
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'intraday_data_cache' not in st.session_state:
        st.session_state.intraday_data_cache = {}
    if 'scan_log' not in st.session_state:
        st.session_state.scan_log = []


init_session_state()


# ==============================================================================
# SCAN ENGINE
# ==============================================================================

def run_scan():
    """Execute a full scan cycle."""
    st.session_state.scan_count += 1
    st.session_state.last_scan_time = datetime.now()

    fetcher = DataFetcher()
    analyzer = MarketPathAnalyzer()
    signal_gen = SignalGenerator()
    tracker = st.session_state.tracker

    # Fetch VIX
    vix = fetcher.fetch_vix() or 15.0
    st.session_state.vix_value = vix

    all_signals = {}
    market_paths = {}
    intraday_cache = {}

    if vix >= Config.VIX_HALT_THRESHOLD:
        st.session_state.scan_results = {}
        st.session_state.market_paths = {}
        return

    for index_name, symbol in Config.INDEX_SYMBOLS.items():
        daily_data = fetcher.fetch_daily_data(symbol)
        intraday_data = fetcher.fetch_index_data(
            symbol,
            period=Config.CHART_PERIOD,
            interval=Config.CHART_INTERVAL
        )

        if daily_data is not None and not daily_data.empty:
            path = analyzer.analyze(index_name, daily_data, vix)
            market_paths[index_name] = path

            signals = signal_gen.generate_signals(
                index_name, intraday_data, daily_data, vix, path
            )
            all_signals[index_name] = signals

            # Track signals
            for sig in signals:
                tracker.add_trade(sig, st.session_state.scan_count)

            # Update prices
            if intraday_data is not None and len(intraday_data) >= 2:
                price_change = (
                    (float(intraday_data['Close'].iloc[-1]) -
                     float(intraday_data['Close'].iloc[-2])) /
                    float(intraday_data['Close'].iloc[-2])
                )
                tracker.update_prices(index_name, price_change)
            else:
                tracker.update_prices(index_name)

            if intraday_data is not None:
                intraday_cache[index_name] = intraday_data
        else:
            all_signals[index_name] = []

    tracker.check_time_exit()

    st.session_state.scan_results = all_signals
    st.session_state.market_paths = market_paths
    st.session_state.intraday_data_cache = intraday_cache

    # Log
    st.session_state.scan_log.append({
        'scan': st.session_state.scan_count,
        'time': datetime.now().strftime("%H:%M:%S"),
        'signals': sum(len(v) for v in all_signals.values()),
        'active': len(tracker.active_trades),
        'closed': len(tracker.closed_trades),
    })


# ==============================================================================
# SIDEBAR
# ==============================================================================

def render_sidebar():
    """Render the sidebar navigation and controls."""
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center; padding:10px;'>
            <h2>🔍 Auto Scanner</h2>
            <p style='color:#a8a8a8;'>v2.0 with Trade Tracking</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Navigation
        page = st.radio(
            "📌 Navigation",
            [
                "🔍 Scanner Dashboard",
                "📊 Market Path",
                "📋 Active Trades",
                "🏁 Closed Trades",
                "📈 Performance",
                "📜 All Recommendations",
                "🧪 Simulation",
                "📂 Backtest & Logs"
            ],
            index=0,
        )

        st.divider()

        # Scanner Controls
        st.subheader("⚙️ Controls")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Scan Now", use_container_width=True,
                         type="primary"):
                run_scan()
                st.rerun()
        with col2:
            if st.button("🔄 Clear", use_container_width=True):
                st.session_state.tracker = TradeTracker()
                st.session_state.scan_count = 0
                st.session_state.scan_results = {}
                st.session_state.market_paths = {}
                st.session_state.scan_log = []
                st.rerun()

        # Auto refresh
        auto_interval = st.selectbox(
            "Auto-Refresh Interval",
            [None, 30, 60, 120, 300],
            format_func=lambda x: (
                "Off" if x is None else f"{x}s"
            ),
            index=0,
        )

        if auto_interval:
            st.session_state.auto_refresh = True
            st.markdown(
                f"🔄 Auto-refreshing every **{auto_interval}s**"
            )
        else:
            st.session_state.auto_refresh = False

        st.divider()

        # Quick Stats
        st.subheader("📊 Quick Stats")
        tracker = st.session_state.tracker
        st.metric("Total Scans", st.session_state.scan_count)
        st.metric("Active Trades", len(tracker.active_trades))
        st.metric("Closed Trades", len(tracker.closed_trades))
        st.metric("Total Signals", len(tracker.all_trades))

        if tracker.closed_trades:
            total_pnl = sum(t.pnl_amount for t in tracker.closed_trades)
            st.metric(
                "Total P&L",
                f"₹{total_pnl:,.0f}",
                delta=f"₹{total_pnl:,.0f}",
                delta_color="normal"
            )

        if st.session_state.last_scan_time:
            st.caption(
                f"Last scan: "
                f"{st.session_state.last_scan_time.strftime('%H:%M:%S')}"
            )

        st.divider()

        # Export
        st.subheader("💾 Export")
        if tracker.all_trades:
            csv_data = tracker.get_csv_data()
            json_data = tracker.get_json_data()

            st.download_button(
                "📄 Download CSV",
                csv_data,
                f"trades_{tracker.session_date}.csv",
                "text/csv",
                use_container_width=True,
            )
            st.download_button(
                "📄 Download JSON",
                json_data,
                f"trades_{tracker.session_date}.json",
                "application/json",
                use_container_width=True,
            )

            if st.button("💾 Save to Disk", use_container_width=True):
                tracker.export_to_csv()
                tracker.export_to_json()
                st.success("Saved to trade_logs/")
        else:
            st.caption("Run a scan first to export data")

        return page, auto_interval


# ==============================================================================
# PAGE RENDERERS
# ==============================================================================

def render_scanner_dashboard():
    """Render the main scanner dashboard."""

    # Header
    st.markdown("""
    <div class='main-header'>
        <h1>🔍 AUTO SCANNER v2.0</h1>
        <p>Nifty • BankNifty • Sensex • FinNifty</p>
    </div>
    """, unsafe_allow_html=True)

    tracker = st.session_state.tracker
    vix = st.session_state.vix_value

    # VIX Status
    if vix is not None:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if vix < 20:
                vix_color = "normal"
                vix_label = "🟢 LOW"
            elif vix < 30:
                vix_color = "off"
                vix_label = "🟡 MODERATE"
            elif vix < 40:
                vix_color = "off"
                vix_label = "🟠 HIGH"
            else:
                vix_color = "inverse"
                vix_label = "🔴 EXTREME"
            st.metric("India VIX", f"{vix:.2f}", vix_label,
                      delta_color=vix_color)
        with col2:
            st.metric("Scan #", st.session_state.scan_count)
        with col3:
            st.metric("Active", len(tracker.active_trades))
        with col4:
            st.metric("Closed", len(tracker.closed_trades))
        with col5:
            total_pnl = sum(
                t.pnl_amount for t in tracker.closed_trades
            )
            st.metric(
                "Day P&L",
                f"₹{total_pnl:,.0f}",
                delta_color="normal"
            )

        if vix >= Config.VIX_HALT_THRESHOLD:
            st.error(
                f"⛔ TRADING HALTED - VIX ({vix:.1f}) > "
                f"{Config.VIX_HALT_THRESHOLD}!"
            )
            return
    else:
        st.info("👆 Click **Scan Now** to start scanning")
        return

    st.divider()

    # Signals by Index
    scan_results = st.session_state.scan_results
    market_paths = st.session_state.market_paths
    intraday_cache = st.session_state.intraday_data_cache

    if not scan_results:
        st.info(
            "No scan results yet. Click **▶️ Scan Now** in the sidebar."
        )
        return

    tabs = st.tabs(list(Config.INDEX_SYMBOLS.keys()))

    for tab, index_name in zip(tabs, Config.INDEX_SYMBOLS.keys()):
        with tab:
            path = market_paths.get(index_name)
            signals = scan_results.get(index_name, [])
            intraday = intraday_cache.get(index_name)

            if path:
                # Market summary
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Close", f"₹{path.closing_price:,.2f}")
                with c2:
                    bias_icon = (
                        "📈" if path.bias == "BULLISH"
                        else "📉" if path.bias == "BEARISH"
                        else "➡️"
                    )
                    st.metric("Bias", f"{bias_icon} {path.bias}")
                with c3:
                    mkt_icon = (
                        "🔥" if path.market_type == MarketType.TRENDING
                        else "📊"
                    )
                    st.metric(
                        "Market Type",
                        f"{mkt_icon} {path.market_type.value}"
                    )
                with c4:
                    st.metric(
                        "Range",
                        f"±{path.expected_range_pct:.2f}%",
                        f"±{path.expected_range_points:,.0f} pts"
                    )

                # Pivot Points
                with st.expander("📐 Pivot Points & CPR", expanded=False):
                    pc1, pc2, pc3, pc4, pc5 = st.columns(5)
                    with pc1:
                        st.metric("R2", f"{path.pivots.r2:,.2f}")
                    with pc2:
                        st.metric("R1", f"{path.pivots.r1:,.2f}")
                    with pc3:
                        st.metric("Pivot", f"{path.pivots.pivot:,.2f}")
                    with pc4:
                        st.metric("S1", f"{path.pivots.s1:,.2f}")
                    with pc5:
                        st.metric("S2", f"{path.pivots.s2:,.2f}")

                    st.caption(
                        f"CPR Width: {path.pivots.cpr_width_pct:.3f}% | "
                        f"TC: {path.pivots.tc:,.2f} | "
                        f"BC: {path.pivots.bc:,.2f}"
                    )

                # Chart
                if intraday is not None:
                    with st.expander("📈 Price Chart", expanded=True):
                        chart = build_price_chart(
                            intraday, index_name, path.pivots
                        )
                        if chart:
                            st.plotly_chart(
                                chart, use_container_width=True
                            )

                    with st.expander("📊 RSI Chart", expanded=False):
                        rsi_chart = build_rsi_chart(intraday, index_name)
                        if rsi_chart:
                            st.plotly_chart(
                                rsi_chart, use_container_width=True
                            )

            # Signals
            st.subheader(f"📋 Signals ({len(signals)})")

            if not signals:
                st.info(f"No valid signals for {index_name}")
            else:
                for sig in signals:
                    is_call = sig.signal_type == SignalType.CALL
                    emoji = "📈" if is_call else "📉"
                    color = "#2ecc71" if is_call else "#e74c3c"
                    direction = "CALL" if is_call else "PUT"
                    stars = "⭐" * sig.confidence_score + (
                        "☆" * (5 - sig.confidence_score)
                    )

                    with st.container():
                        st.markdown(
                            f"""
                            <div style='border:1px solid {color};
                            border-radius:10px; padding:15px;
                            margin:5px 0;
                            background:rgba(0,0,0,0.2);'>
                            <h4>{emoji} {direction} | {sig.entry_type.value}
                            | Strike: {sig.strike_price:,.0f}</h4>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        sc1, sc2, sc3, sc4 = st.columns(4)
                        with sc1:
                            st.metric(
                                "Entry", f"₹{sig.entry_price:,.2f}"
                            )
                        with sc2:
                            st.metric(
                                "Stop Loss", f"₹{sig.stop_loss:,.2f}"
                            )
                        with sc3:
                            st.metric(
                                "Target", f"₹{sig.target:,.2f}"
                            )
                        with sc4:
                            st.metric(
                                "Confidence", f"{sig.confidence_score}/5"
                            )

                        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
                        with fc1:
                            st.markdown(
                                f"SMA {'✅' if sig.sma_confirmed else '❌'}"
                            )
                        with fc2:
                            st.markdown(
                                f"RSI {'✅' if sig.rsi_confirmed else '❌'}"
                                f" ({sig.rsi_value:.0f})"
                            )
                        with fc3:
                            st.markdown(
                                f"VIX {'✅' if sig.vix_safe else '❌'}"
                            )
                        with fc4:
                            st.markdown(
                                f"OI {'✅' if sig.oi_confirmed else '❌'}"
                            )
                        with fc5:
                            st.markdown(stars)

                        st.caption(
                            f"Lot: {sig.lot_size} | "
                            f"Max Loss: ₹{sig.max_loss:,.0f} | "
                            f"Max Profit: ₹{sig.max_profit:,.0f} | "
                            f"R:R = 1:{sig.risk_reward:.0f}"
                        )
                        st.divider()


def render_market_path():
    """Render the Market Path page."""
    st.header("🔮 Market Path Analysis")

    market_paths = st.session_state.market_paths

    if not market_paths:
        st.info(
            "Run a scan first to see market path analysis. "
            "Click **▶️ Scan Now** in the sidebar."
        )
        return

    for index_name, path in market_paths.items():
        with st.expander(f"📊 {index_name}", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Close", f"₹{path.closing_price:,.2f}")
                bias_icon = (
                    "📈" if path.bias == "BULLISH"
                    else "📉" if path.bias == "BEARISH"
                    else "➡️"
                )
                st.metric("Bias", f"{bias_icon} {path.bias}")
            with c2:
                mkt_icon = (
                    "🔥" if path.market_type == MarketType.TRENDING
                    else "📊"
                )
                st.metric(
                    "Type", f"{mkt_icon} {path.market_type.value}"
                )
                st.metric("VIX", f"{path.vix:.2f}")
            with c3:
                st.metric(
                    "Expected Range",
                    f"±{path.expected_range_pct:.2f}%"
                )
                st.metric(
                    "Range Points",
                    f"±{path.expected_range_points:,.0f}"
                )

            # Pivot levels visual
            st.subheader("📐 Pivot Levels")
            pivot_data = {
                'Level': ['R3', 'R2', 'R1', 'TC', 'Pivot', 'BC',
                          'S1', 'S2', 'S3'],
                'Price': [
                    path.pivots.r3, path.pivots.r2, path.pivots.r1,
                    path.pivots.tc, path.pivots.pivot, path.pivots.bc,
                    path.pivots.s1, path.pivots.s2, path.pivots.s3
                ]
            }
            df_pivot = pd.DataFrame(pivot_data)
            df_pivot['Price'] = df_pivot['Price'].apply(
                lambda x: f"₹{x:,.2f}"
            )

            # Horizontal bar chart for pivots
            fig_pivot = go.Figure()
            colors_p = [
                '#e74c3c', '#e74c3c', '#e74c3c',
                '#f39c12', '#f1c40f', '#f39c12',
                '#2ecc71', '#2ecc71', '#2ecc71'
            ]
            fig_pivot.add_trace(go.Bar(
                y=pivot_data['Level'],
                x=pivot_data['Price'],
                orientation='h',
                marker_color=colors_p,
                text=[f"₹{p:,.0f}" for p in pivot_data['Price']],
                textposition='auto',
            ))
            fig_pivot.add_vline(
                x=path.closing_price,
                line_dash="dash", line_color="white",
                annotation_text=f"Close: ₹{path.closing_price:,.0f}"
            )
            fig_pivot.update_layout(
                template='plotly_dark', height=350,
                margin=dict(l=50, r=50, t=20, b=20),
            )
            st.plotly_chart(fig_pivot, use_container_width=True)

            st.caption(
                f"CPR Width: {path.pivots.cpr_width_pct:.3f}% "
                f"({'Narrow → Trending' if path.pivots.cpr_width_pct < Config.CPR_NARROW_THRESHOLD else 'Wide → Rangebound'})"
            )


def render_active_trades():
    """Render the Active Trades page."""
    st.header("🟢 Active Trades")

    tracker = st.session_state.tracker

    if not tracker.active_trades:
        st.info("No active trades. Signals will appear here after scanning.")
        return

    # Summary metrics
    total_pnl = sum(t.pnl_amount for t in tracker.active_trades)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Active Trades", len(tracker.active_trades))
    with c2:
        st.metric(
            "Unrealized P&L",
            f"₹{total_pnl:,.0f}",
            delta_color="normal"
        )
    with c3:
        avg_conf = np.mean([
            t.signal.confidence_score for t in tracker.active_trades
        ])
        st.metric("Avg Confidence", f"{avg_conf:.1f}/5")

    st.divider()

    # Trade cards
    for trade in tracker.active_trades:
        is_call = trade.signal.signal_type == SignalType.CALL
        direction = "CE" if is_call else "PE"
        pnl_color = "#2ecc71" if trade.pnl_amount >= 0 else "#e74c3c"

        with st.container():
            st.markdown(
                f"""
                <div style='border:1px solid {pnl_color};
                border-radius:10px; padding:10px; margin:5px 0;
                background:rgba(0,0,0,0.2);'>
                <strong>{trade.trade_id}</strong> |
                {trade.signal.index} |
                {direction} {trade.signal.strike_price:,.0f}
                </div>
                """,
                unsafe_allow_html=True
            )

            tc1, tc2, tc3, tc4, tc5 = st.columns(5)
            with tc1:
                st.metric(
                    "Entry", f"₹{trade.signal.entry_price:,.2f}"
                )
            with tc2:
                st.metric(
                    "Current", f"₹{trade.current_price:,.2f}"
                )
            with tc3:
                st.metric("SL", f"₹{trade.signal.stop_loss:,.2f}")
            with tc4:
                st.metric(
                    "Target", f"₹{trade.signal.target:,.2f}"
                )
            with tc5:
                st.metric(
                    "P&L",
                    f"₹{trade.pnl_amount:,.0f}",
                    f"{trade.pnl_percentage:+.1f}%",
                    delta_color="normal",
                )

            # Progress bar: entry → current → target
            if trade.signal.target > trade.signal.stop_loss:
                progress = (
                    (trade.current_price - trade.signal.stop_loss) /
                    (trade.signal.target - trade.signal.stop_loss)
                )
                progress = max(0.0, min(1.0, progress))
                st.progress(progress, text=(
                    f"SL ← {progress*100:.0f}% → Target"
                ))

            st.caption(
                f"Entry: {trade.entry_time} | "
                f"High: ₹{trade.highest_price:,.2f} | "
                f"Low: ₹{trade.lowest_price:,.2f} | "
                f"Scan #{trade.scan_number}"
            )
            st.divider()

    # Force close button
    st.divider()
    if st.button(
        "🛑 Force Close All Active Trades",
        type="secondary",
        use_container_width=True
    ):
        tracker.force_close_all("Manual Close from Dashboard")
        st.success("All active trades closed!")
        st.rerun()


def render_closed_trades():
    """Render the Closed Trades page."""
    st.header("📋 Closed Trades")

    tracker = st.session_state.tracker

    if not tracker.closed_trades:
        st.info("No closed trades yet.")
        return

    # Summary
    total_pnl = sum(t.pnl_amount for t in tracker.closed_trades)
    targets = len([
        t for t in tracker.closed_trades
        if t.status == TradeStatus.TARGET_HIT
    ])
    sls = len([
        t for t in tracker.closed_trades
        if t.status == TradeStatus.SL_HIT
    ])
    time_exits = len([
        t for t in tracker.closed_trades
        if t.status == TradeStatus.TIME_EXIT
    ])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Closed", len(tracker.closed_trades))
    with c2:
        st.metric("🎯 Targets", targets)
    with c3:
        st.metric("🛑 SL Hits", sls)
    with c4:
        st.metric(
            "Total P&L",
            f"₹{total_pnl:,.0f}",
            delta_color="normal"
        )

    st.divider()

    # Table
    trade_data = []
    for t in tracker.closed_trades:
        direction = (
            "CE" if t.signal.signal_type == SignalType.CALL else "PE"
        )
        status_map = {
            TradeStatus.TARGET_HIT: "🎯 TARGET",
            TradeStatus.SL_HIT: "🛑 SL HIT",
            TradeStatus.TIME_EXIT: "⏰ TIME",
            TradeStatus.MANUAL_EXIT: "🔧 MANUAL",
        }
        trade_data.append({
            'ID': t.trade_id,
            'Index': t.signal.index,
            'Type': direction,
            'Strike': f"{t.signal.strike_price:,.0f}",
            'Entry': f"₹{t.signal.entry_price:,.2f}",
            'Exit': f"₹{t.exit_price:,.2f}",
            'P&L': f"₹{t.pnl_amount:,.0f}",
            'P&L%': f"{t.pnl_percentage:+.1f}%",
            'Status': status_map.get(t.status, t.status.value),
            'Confidence': f"{'⭐' * t.signal.confidence_score}",
            'Exit Time': (
                t.exit_time.split(' ')[1][:5] if t.exit_time else "--"
            ),
            'Reason': t.exit_reason,
        })

    df = pd.DataFrame(trade_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=400,
    )

    # P&L Distribution
    pnl_chart = build_pnl_distribution(tracker)
    if pnl_chart:
        st.plotly_chart(pnl_chart, use_container_width=True)


def render_performance():
    """Render the Performance Dashboard page."""
    st.header("📈 Performance Dashboard")

    tracker = st.session_state.tracker
    stats = tracker.get_daily_stats()

    if stats['total_signals'] == 0:
        st.info(
            "No trades to analyze yet. "
            "Run some scans to see performance metrics."
        )
        return

    # Top metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total Signals", stats['total_signals'])
    with c2:
        st.metric("Win Rate", f"{stats['win_rate']}%")
    with c3:
        pnl_delta = "Profit" if stats['total_pnl'] >= 0 else "Loss"
        st.metric(
            "Total P&L",
            f"₹{stats['total_pnl']:,.0f}",
            pnl_delta,
            delta_color="normal"
        )
    with c4:
        st.metric("Profit Factor", f"{stats['profit_factor']}")
    with c5:
        st.metric("Max Drawdown", f"₹{stats['max_drawdown']:,.0f}")

    st.divider()

    # Two columns: Gauge + Stats
    col_left, col_right = st.columns([1, 2])

    with col_left:
        # Win Rate Gauge
        gauge = build_win_rate_gauge(stats['win_rate'])
        if gauge:
            st.plotly_chart(gauge, use_container_width=True)

        # Win/Loss breakdown
        if stats['closed'] > 0:
            fig_pie = go.Figure(data=[go.Pie(
                labels=['🎯 Target', '🛑 SL Hit', '⏰ Time Exit'],
                values=[
                    stats['targets_hit'],
                    stats['sl_hit'],
                    stats['time_exits']
                ],
                hole=0.4,
                marker_colors=['#2ecc71', '#e74c3c', '#3498db'],
            )])
            fig_pie.update_layout(
                template='plotly_dark', height=250,
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=True,
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        # Detailed stats table
        detail_data = {
            'Metric': [
                '📊 Closed Trades', '📈 Winners', '📉 Losers',
                '🎯 Targets Hit', '🛑 SL Hit', '⏰ Time Exits',
                '💰 Total P&L', '📊 Avg P&L/Trade',
                '🟢 Winners P&L', '🔴 Losers P&L',
                '📈 Avg Winner', '📉 Avg Loser',
                '🏅 Best Trade', '💀 Worst Trade',
            ],
            'Value': [
                stats['closed'], stats['winners'], stats['losers'],
                stats['targets_hit'], stats['sl_hit'],
                stats['time_exits'],
                f"₹{stats['total_pnl']:,.0f}",
                f"₹{stats['avg_pnl_per_trade']:,.0f}",
                f"₹{stats['total_winners_pnl']:,.0f}",
                f"₹{stats['total_losers_pnl']:,.0f}",
                f"₹{stats['avg_winner']:,.0f}",
                f"₹{stats['avg_loser']:,.0f}",
                f"₹{stats['best_trade_pnl']:,.0f}",
                f"₹{stats['worst_trade_pnl']:,.0f}",
            ]
        }
        st.dataframe(
            pd.DataFrame(detail_data),
            use_container_width=True,
            hide_index=True,
            height=530,
        )

    st.divider()

    # Equity Curve
    equity = build_equity_curve(tracker)
    if equity:
        st.plotly_chart(equity, use_container_width=True)

    # Index Breakdown
    st.subheader("📊 Index-wise Breakdown")
    idx_data = []
    for idx_name, idx_stats in stats.get('index_breakdown', {}).items():
        if idx_stats['trades'] > 0:
            idx_data.append({
                'Index': idx_name,
                'Trades': idx_stats['trades'],
                'Winners': idx_stats['winners'],
                'Win Rate': f"{idx_stats['win_rate']:.1f}%",
                'P&L': f"₹{idx_stats['pnl']:,.0f}",
            })
    if idx_data:
        st.dataframe(
            pd.DataFrame(idx_data),
            use_container_width=True,
            hide_index=True,
        )

    # Confidence Analysis
    st.subheader("📊 Confidence Score Analysis")
    conf_chart = build_confidence_chart(
        stats.get('confidence_analysis', {})
    )
    if conf_chart:
        st.plotly_chart(conf_chart, use_container_width=True)

    conf_data = []
    for score in range(1, 6):
        key = f"score_{score}"
        cs = stats.get('confidence_analysis', {}).get(key, {})
        if cs.get('trades', 0) > 0:
            conf_data.append({
                'Score': '⭐' * score,
                'Trades': cs['trades'],
                'Winners': cs['winners'],
                'Win Rate': f"{cs['win_rate']:.1f}%",
                'P&L': f"₹{cs['pnl']:,.0f}",
            })
    if conf_data:
        st.dataframe(
            pd.DataFrame(conf_data),
            use_container_width=True,
            hide_index=True,
        )


def render_all_recommendations():
    """Render the complete daily recommendation log."""
    st.header("📜 All Recommendations")

    tracker = st.session_state.tracker

    if not tracker.all_trades:
        st.info("No recommendations generated yet.")
        return

    st.markdown(
        f"**Date:** {tracker.session_date} | "
        f"**Total:** {len(tracker.all_trades)} | "
        f"**Active:** {len(tracker.active_trades)} | "
        f"**Closed:** {len(tracker.closed_trades)}"
    )

    # Filter controls
    c1, c2, c3 = st.columns(3)
    with c1:
        filter_index = st.selectbox(
            "Index",
            ["All"] + list(Config.INDEX_SYMBOLS.keys())
        )
    with c2:
        filter_type = st.selectbox(
            "Type", ["All", "CALL", "PUT"]
        )
    with c3:
        filter_status = st.selectbox(
            "Status",
            ["All", "ACTIVE", "TARGET_HIT", "SL_HIT", "TIME_EXIT"]
        )

    # Build filtered data
    all_data = []
    for t in tracker.all_trades:
        if filter_index != "All" and t.signal.index != filter_index:
            continue
        if (filter_type != "All" and
                t.signal.signal_type.value != filter_type):
            continue
        if filter_status != "All" and t.status.value != filter_status:
            continue

        direction = (
            "CE" if t.signal.signal_type == SignalType.CALL else "PE"
        )

        status_map = {
            TradeStatus.ACTIVE: "⏳ ACTIVE",
            TradeStatus.TARGET_HIT: "🎯 TARGET",
            TradeStatus.SL_HIT: "🛑 SL HIT",
            TradeStatus.TIME_EXIT: "⏰ TIME",
            TradeStatus.MANUAL_EXIT: "🔧 MANUAL",
        }

        exit_p = (
            f"₹{t.exit_price:,.2f}"
            if t.status != TradeStatus.ACTIVE
            else f"₹{t.current_price:,.2f}"
        )

        all_data.append({
            'ID': t.trade_id,
            'Scan': t.scan_number,
            'Index': t.signal.index,
            'Type': direction,
            'Strike': f"{t.signal.strike_price:,.0f}",
            'Entry': f"₹{t.signal.entry_price:,.2f}",
            'SL': f"₹{t.signal.stop_loss:,.2f}",
            'Target': f"₹{t.signal.target:,.2f}",
            'Exit/Current': exit_p,
            'P&L': f"₹{t.pnl_amount:,.0f}",
            'P&L%': f"{t.pnl_percentage:+.1f}%",
            'Status': status_map.get(t.status, t.status.value),
            'Confidence': t.signal.confidence_score,
            'Entry Time': (
                t.entry_time.split(' ')[1][:5]
                if t.entry_time else "--"
            ),
        })

    if all_data:
        df = pd.DataFrame(all_data)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=600,
        )

        # Summary by index
        st.subheader("Summary by Index")
        for idx in Config.INDEX_SYMBOLS.keys():
            idx_trades = [
                t for t in tracker.all_trades
                if t.signal.index == idx
            ]
            if idx_trades:
                idx_pnl = sum(t.pnl_amount for t in idx_trades)
                pnl_icon = "🟢" if idx_pnl >= 0 else "🔴"
                st.markdown(
                    f"**{idx}**: {len(idx_trades)} trades | "
                    f"P&L: {pnl_icon} ₹{idx_pnl:,.0f}"
                )
    else:
        st.info("No trades match the selected filters.")


def render_simulation():
    """Render the Simulation page."""
    st.header("🧪 Simulation Mode")

    st.markdown("""
    Simulate multiple scan cycles to test the scanner's performance.
    Each scan will:
    - Fetch live market data
    - Generate signals
    - Simulate price movements
    - Track SL/Target hits
    """)

    num_scans = st.slider(
        "Number of Simulated Scans",
        min_value=1, max_value=20, value=5
    )

    delay = st.slider(
        "Delay between scans (seconds)",
        min_value=1, max_value=10, value=2
    )

    if st.button(
        "🚀 Start Simulation",
        type="primary",
        use_container_width=True
    ):
        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics_placeholder = st.empty()
        log_placeholder = st.empty()

        for i in range(num_scans):
            status_text.markdown(
                f"**Running scan {i+1}/{num_scans}...**"
            )
            progress_bar.progress((i + 1) / num_scans)

            run_scan()

            tracker = st.session_state.tracker
            with metrics_placeholder.container():
                mc1, mc2, mc3, mc4 = st.columns(4)
                with mc1:
                    st.metric("Scan", f"#{st.session_state.scan_count}")
                with mc2:
                    st.metric("Active", len(tracker.active_trades))
                with mc3:
                    st.metric("Closed", len(tracker.closed_trades))
                with mc4:
                    total_pnl = sum(
                        t.pnl_amount for t in tracker.closed_trades
                    )
                    st.metric("P&L", f"₹{total_pnl:,.0f}")

            with log_placeholder.container():
                if st.session_state.scan_log:
                    st.dataframe(
                        pd.DataFrame(st.session_state.scan_log[-10:]),
                        use_container_width=True,
                        hide_index=True,
                    )

            if i < num_scans - 1:
                time_module.sleep(delay)

        status_text.markdown("✅ **Simulation Complete!**")

        # Show results
        st.divider()
        st.subheader("📊 Simulation Results")

        stats = tracker.get_daily_stats()
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Signals", stats['total_signals'])
        with c2:
            st.metric("Win Rate", f"{stats['win_rate']}%")
        with c3:
            st.metric("Total P&L", f"₹{stats['total_pnl']:,.0f}")
        with c4:
            st.metric("Profit Factor", stats['profit_factor'])

        equity = build_equity_curve(tracker)
        if equity:
            st.plotly_chart(equity, use_container_width=True)

    # Scan log
    if st.session_state.scan_log:
        st.subheader("📝 Scan Log")
        st.dataframe(
            pd.DataFrame(st.session_state.scan_log),
            use_container_width=True,
            hide_index=True,
        )


def render_backtest():
    """Render the Backtest & Logs page."""
    st.header("📂 Backtest & Historical Logs")

    tab1, tab2 = st.tabs([
        "📂 View Logs", "📊 Backtest Analysis"
    ])

    with tab1:
        log_dir = Config.LOG_DIR
        if os.path.exists(log_dir):
            files = sorted(os.listdir(log_dir), reverse=True)
            if files:
                st.subheader(f"📁 Files in '{log_dir}/'")

                file_data = []
                for f in files:
                    fpath = os.path.join(log_dir, f)
                    size = os.path.getsize(fpath)
                    file_data.append({
                        'File': f,
                        'Size': f"{size:,} bytes",
                        'Type': (
                            'JSON' if f.endswith('.json') else 'CSV'
                        ),
                    })

                st.dataframe(
                    pd.DataFrame(file_data),
                    use_container_width=True,
                    hide_index=True,
                )

                selected_file = st.selectbox(
                    "Select file to view", files
                )

                if selected_file:
                    filepath = os.path.join(log_dir, selected_file)

                    with open(filepath, 'r') as f:
                        content = f.read()

                    if selected_file.endswith('.json'):
                        try:
                            data = json.loads(content)
                            st.json(data)
                        except json.JSONDecodeError:
                            st.code(content)
                    else:
                        try:
                            df = pd.read_csv(
                                io.StringIO(content)
                            )
                            st.dataframe(
                                df,
                                use_container_width=True,
                                hide_index=True,
                            )
                        except Exception:
                            st.code(content)

                    # Download button
                    st.download_button(
                        f"📥 Download {selected_file}",
                        content,
                        selected_file,
                        use_container_width=True,
                    )
            else:
                st.info(f"No log files in '{log_dir}/'")
        else:
            st.info(
                f"Log directory '{log_dir}/' doesn't exist yet. "
                f"Run the scanner to generate logs."
            )

    with tab2:
        st.subheader("📊 Backtest Analysis")

        if st.button(
            "🔄 Load & Analyze All Sessions",
            use_container_width=True
        ):
            backtest = BacktestEngine()

            with st.spinner("Loading historical logs..."):
                count = backtest.load_all_logs()

            if count > 0:
                st.success(f"Loaded {count} trading sessions")

                # Gather all trades
                all_trades = []
                for session in backtest.all_sessions:
                    all_trades.extend(session.get('trades', []))

                if all_trades:
                    total = len(all_trades)
                    targets = len([
                        t for t in all_trades
                        if t.get('status') == 'TARGET_HIT'
                    ])
                    sls = len([
                        t for t in all_trades
                        if t.get('status') == 'SL_HIT'
                    ])
                    winners = [
                        t for t in all_trades
                        if t.get('pnl_amount', 0) > 0
                    ]
                    losers = [
                        t for t in all_trades
                        if t.get('pnl_amount', 0) < 0
                    ]
                    total_pnl = sum(
                        t.get('pnl_amount', 0) for t in all_trades
                    )
                    win_rate = (
                        len(winners) / total * 100
                    ) if total > 0 else 0

                    bc1, bc2, bc3, bc4 = st.columns(4)
                    with bc1:
                        st.metric("Total Trades", total)
                    with bc2:
                        st.metric(
                            "Win Rate", f"{win_rate:.1f}%"
                        )
                    with bc3:
                        st.metric(
                            "Total P&L", f"₹{total_pnl:,.0f}"
                        )
                    with bc4:
                        winners_pnl = sum(
                            t.get('pnl_amount', 0) for t in winners
                        )
                        losers_pnl = sum(
                            t.get('pnl_amount', 0) for t in losers
                        )
                        pf = (
                            abs(winners_pnl / losers_pnl)
                            if losers_pnl != 0 else 999
                        )
                        st.metric(
                            "Profit Factor", f"{pf:.2f}"
                        )

                    # Confidence analysis
                    st.subheader(
                        "Confidence Score Backtest"
                    )
                    conf_bt_data = []
                    for score in range(1, 6):
                        sc_trades = [
                            t for t in all_trades
                            if t.get('confidence', 0) == score
                            and t.get('status') != 'ACTIVE'
                        ]
                        if sc_trades:
                            sc_w = [
                                t for t in sc_trades
                                if t.get('pnl_amount', 0) > 0
                            ]
                            sc_pnl = sum(
                                t.get('pnl_amount', 0)
                                for t in sc_trades
                            )
                            sc_wr = (
                                len(sc_w) / len(sc_trades) * 100
                            )
                            conf_bt_data.append({
                                'Score': '⭐' * score,
                                'Trades': len(sc_trades),
                                'Winners': len(sc_w),
                                'Win Rate': f"{sc_wr:.1f}%",
                                'Total P&L': f"₹{sc_pnl:,.0f}",
                                'Avg P&L': f"₹{sc_pnl/len(sc_trades):,.0f}",
                            })

                    if conf_bt_data:
                        st.dataframe(
                            pd.DataFrame(conf_bt_data),
                            use_container_width=True,
                            hide_index=True,
                        )

                    # All trades table
                    st.subheader("All Historical Trades")
                    st.dataframe(
                        pd.DataFrame(all_trades),
                        use_container_width=True,
                        hide_index=True,
                        height=400,
                    )
            else:
                st.warning(
                    "No historical logs found. "
                    "Run the scanner and save logs first."
                )


class BacktestEngine:
    """Load and analyze historical trade logs."""

    def __init__(self):
        self.all_sessions = []

    def load_all_logs(self):
        log_dir = Config.LOG_DIR
        if not os.path.exists(log_dir):
            return 0
        files = [
            f for f in os.listdir(log_dir) if f.endswith('.json')
        ]
        files.sort()
        for filename in files:
            filepath = os.path.join(log_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self.all_sessions.append(data)
            except Exception:
                pass
        return len(self.all_sessions)


# ==============================================================================
# MAIN APP
# ==============================================================================

def main():
    """Main Streamlit application."""

    page, auto_interval = render_sidebar()

    # Route to page
    if page == "🔍 Scanner Dashboard":
        render_scanner_dashboard()
    elif page == "📊 Market Path":
        render_market_path()
    elif page == "📋 Active Trades":
        render_active_trades()
    elif page == "🏁 Closed Trades":
        render_closed_trades()
    elif page == "📈 Performance":
        render_performance()
    elif page == "📜 All Recommendations":
        render_all_recommendations()
    elif page == "🧪 Simulation":
        render_simulation()
    elif page == "📂 Backtest & Logs":
        render_backtest()

    # Auto-refresh
    if auto_interval and st.session_state.auto_refresh:
        time_module.sleep(auto_interval)
        run_scan()
        st.rerun()


if __name__ == "__main__":
    main()
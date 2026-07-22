"""
Intraday futures backtest oriented to GC (Gold futures).

Expect input: per-contract CSV files in a directory (data/) with names like:
  GC_20230627.csv
  GC_20230927.csv
Where the YYYYMMDD in the filename is the contract expiry date.

Each CSV must have columns:
  Datetime, Open, High, Low, Close, Volume
Datetime should be timezone-aware or local; parsed as pandas DatetimeIndex.

What the script does:
- Builds a continuous minute series by choosing the highest-volume contract per calendar day.
- Runs a minute-by-minute backtest for a SMA crossover (n1, n2 in minutes).
- On entry: places market order executed at next-minute open (if available) with slippage =
    tick_slippage + impact_coef * (contracts / avg_volume_window)
  and commission per contract.
- Stops are checked intrabar: if Low <= stop (for longs) during the bar, exit at stop price.
- Position sizing for futures:
    per_contract_risk = (entry_price - stop_price) * CONTRACT_SIZE (100 oz)
    n_contracts = floor(risk_amount / per_contract_risk)
- Outputs simple performance summary and equity curve CSV.

Adjust parameters below as needed.
"""

import os
import glob
import math
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# ---------------------------
# Configuration / parameters
# ---------------------------

DATA_DIR = "data"                 # folder with contract CSVs
OUTPUT_EQUITY_CSV = "equity_curve.csv"

# Strategy params (minutes)
SMA_SHORT = 60      # e.g., 60-minute SMA (1 hour)
SMA_LONG = 240      # e.g., 240-minute SMA (4 hours)

ATR_PERIOD = 60     # ATR over 60 minutes (intraday volatility)
ATR_MULT = 2.0      # stop = entry - ATR_MULT * ATR

RISK_PER_TRADE = 0.01    # 1% of equity risked per trade
DAILY_MAX_LOSS = 0.10    # stop trading if equity drops 10% from starting cash

INITIAL_CAPITAL = 200000  # starting USD

# Futures contract specifics for GC (COMEX)
CONTRACT_SIZE = 100.0     # 100 troy ounces per contract
TICK_SIZE = 0.10          # $0.10 per ounce tick => $10 per contract
TICK_VALUE = TICK_SIZE * CONTRACT_SIZE  # dollars per tick per contract (10)

# Execution / cost model
COMMISSION_PER_CONTRACT = 2.5   # $ per side (example)
IMPACT_COEF = 0.5               # empirical multiplier for market impact (tune it)
AVG_VOLUME_WINDOW = 60          # minutes to avg volume for liquidity estimate
MIN_FILL_PCT = 0.2              # minimum fraction of next-minute volume we can consume without greater impact

# Rolling rules
ROLL_METHOD = "volume"   # 'volume' or 'days_before_expiry'
ROLL_DAYS_BEFORE_EXPIRY = 5  # used if ROLL_METHOD='days_before_expiry'

# ---------------------------
# Utilities: load and build continuous
# ---------------------------

def parse_expiry_from_filename(fname):
    # expects pattern GC_YYYYMMDD.csv
    base = os.path.basename(fname)
    parts = base.split('_')
    if len(parts) < 2:
        return None
    datepart = parts[1].split('.')[0]
    try:
        dt = datetime.strptime(datepart, "%Y%m%d").date()
        return dt
    except Exception:
        return None

def load_contract_csv(path):
    df = pd.read_csv(path, parse_dates=['Datetime'])
    df = df.set_index('Datetime').sort_index()
    # ensure numeric columns
    for c in ['Open','High','Low','Close','Volume']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        else:
            raise ValueError(f"CSV {path} missing column {c}")
    df = df.dropna(subset=['Open','High','Low','Close'])
    return df

def build_continuous_by_daily_volume(data_dir):
    """
    Build continuous minute series by selecting, for each calendar day,
    the contract (CSV) with highest total volume for that day, then
    concatenating minute bars (local contract minute bars for that day).
    This avoids manually coding minute-by-minute roll logic and is robust
    when per-contract files contain daily minute bars.
    """
    files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSVs found in {data_dir}")
    # load all contracts into memory (may be heavy for many months)
    contracts = {}
    expiries = {}
    for f in files:
        exp = parse_expiry_from_filename(f)
        if exp is None:
            print("Skipping file with unknown expiry format:", f)
            continue
        df = load_contract_csv(f)
        contracts[f] = df
        expiries[f] = exp

    # gather full date range
    all_dates = set()
    for df in contracts.values():
        all_dates.update(df.index.date)
    all_dates = sorted(all_dates)

    pieces = []
    last_used = None
    for d in all_dates:
        # among contracts that contain this date, pick contract with max volume on that date
        best_file = None
        best_vol = -1
        for f, df in contracts.items():
            # slice df for date d
            day_slice = df[df.index.date == d]
            if len(day_slice) == 0:
                continue
            vol = day_slice['Volume'].sum()
            if vol > best_vol:
                best_vol = vol
                best_file = f
        if best_file is None:
            # missing data for this date (market holiday?), skip
            continue
        day_df = contracts[best_file][contracts[best_file].index.date == d].copy()
        # optional: add column for source contract
        day_df['contract'] = os.path.basename(best_file)
        pieces.append(day_df)
        last_used = best_file

    if not pieces:
        raise RuntimeError("No day blocks assembled for continuity")
    cont = pd.concat(pieces)
    cont = cont[~cont.index.duplicated(keep='first')]
    cont = cont.sort_index()
    return cont

# ---------------------------
# Indicators
# ---------------------------

def SMA(series, n):
    return series.rolling(n).mean()

def ATR(df, n=14):
    high = df['High']
    low = df['Low']
    close = df['Close']
    prev_close = close.shift(1)
    tr1 = (high - low).abs()
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(n).mean()
    return atr

# ---------------------------
# Backtester
# ---------------------------

class IntradayFuturesBacktester:
    def __init__(self, df,
                 sma_short=SMA_SHORT, sma_long=SMA_LONG,
                 atr_period=ATR_PERIOD, atr_mult=ATR_MULT,
                 risk_per_trade=RISK_PER_TRADE,
                 initial_capital=INITIAL_CAPITAL,
                 commission_per_contract=COMMISSION_PER_CONTRACT,
                 contract_size=CONTRACT_SIZE,
                 tick_size=TICK_SIZE,
                 impact_coef=IMPACT_COEF,
                 avg_volume_window=AVG_VOLUME_WINDOW,
                 min_fill_pct=MIN_FILL_PCT,
                 daily_max_loss=DAILY_MAX_LOSS):
        self.df = df.copy()
        self.sma_short = sma_short
        self.sma_long = sma_long
        self.atr_period = atr_period
        self.atr_mult = atr_mult
        self.risk_per_trade = risk_per_trade
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.cash = initial_capital
        self.position = 0  # signed number of contracts
        self.entry_price = None
        self.entry_dt = None
        self.stop_price = None
        self.contract_size = contract_size
        self.tick_size = tick_size
        self.tick_value = tick_size * contract_size
        self.commission_per_contract = commission_per_contract
        self.impact_coef = impact_coef
        self.avg_volume_window = avg_volume_window
        self.min_fill_pct = min_fill_pct
        self.daily_max_loss = daily_max_loss

        # indicators
        self.df['sma_short'] = SMA(self.df['Close'], self.sma_short)
        self.df['sma_long'] = SMA(self.df['Close'], self.sma_long)
        self.df['atr'] = ATR(self.df, n=self.atr_period)
        self.df['avg_vol'] = self.df['Volume'].rolling(self.avg_volume_window).mean().fillna(method='bfill')

        # bookkeeping
        self.trade_log = []
        self.equity_curve = []

        # for drawdown calc
        self.peak_equity = self.equity

    def _calc_slippage(self, price, contracts, avg_vol):
        """
        Slippage model: base tick slippage + impact proportional to contracts / avg_vol
        Units returned are in price dollars (per ounce).
        For futures GC priced per ounce, tick is $0.10; we return dollars per ounce.
        """
        # base slippage: one tick
        base = self.tick_size
        # impact: (contracts / avg_vol) * impact_coef * price
        if avg_vol <= 0 or np.isnan(avg_vol):
            impact = self.impact_coef * 0.001 * price  # fallback tiny %
        else:
            # avg_vol is number of contracts? In our CSV Volume may be in contracts traded; assume it's number of contracts per minute.
            # If Volume is in shares/oz, user must ensure consistency.
            impact = self.impact_coef * (contracts / max(1.0, avg_vol)) * price
        return base + impact

    def run(self):
        idx = self.df.index
        n = len(self.df)
        for i in range(n - 1):  # we may reference i+1 for next-open execution
            row = self.df.iloc[i]
            now = idx[i]

            # update mark-to-market unrealized P&L for equity curve
            mkt_price = row['Close']
            unreal_pnl = 0.0
            if self.position != 0:
                unreal_pnl = (mkt_price - self.entry_price) * self.position * self.contract_size
            total_equity = self.cash + unreal_pnl
            self.equity = total_equity

            # record equity
            self.equity_curve.append({'Datetime': now, 'Equity': self.equity})

            # check daily max loss (since start)
            if self.equity <= self.initial_capital * (1 - self.daily_max_loss):
                print(f"Daily max loss hit at {now}, equity {self.equity:.2f}. Stopping trading.")
                break

            # signals: require sma available
            s_short = row['sma_short']
            s_long = row['sma_long']
            if np.isnan(s_short) or np.isnan(s_long):
                continue

            # Cross detection: use previous bar to detect cross
            prev = self.df.iloc[i-1] if i >= 1 else None
            crossed_up = False
            crossed_down = False
            if prev is not None and not np.isnan(prev['sma_short']) and not np.isnan(prev['sma_long']):
                crossed_up = (prev['sma_short'] <= prev['sma_long']) and (s_short > s_long)
                crossed_down = (prev['sma_short'] >= prev['sma_long']) and (s_short < s_long)

            # If we have position, check intrabar stop: use current bar Low
            if self.position > 0:
                low = row['Low']
                if low <= self.stop_price:
                    # assume stop fill at stop_price (conservative)
                    exit_price = self.stop_price
                    contracts = self.position
                    pnl = (exit_price - self.entry_price) * contracts * self.contract_size
                    comm = contracts * self.commission_per_contract
                    self.cash += pnl - comm
                    self.trade_log.append({
                        'entry_dt': self.entry_dt, 'exit_dt': now, 'entry_price': self.entry_price,
                        'exit_price': exit_price, 'contracts': contracts, 'pnl': pnl, 'commission': comm,
                        'reason': 'stop_hit'
                    })
                    # reset position
                    self.position = 0
                    self.entry_price = None
                    self.entry_dt = None
                    self.stop_price = None
                    # update equity after exit
                    self.equity = self.cash
                    self.equity_curve.append({'Datetime': now + pd.Timedelta(seconds=1), 'Equity': self.equity})
                    continue  # move to next minute

            # Exit signal (sma cross down) -> schedule market exit executed next minute open
            if crossed_down and self.position > 0:
                # execute at next minute open (i+1) if exists, else current close
                exec_idx = i + 1 if (i + 1) < n else i
                exec_price = self.df.iloc[exec_idx]['Open'] if (i + 1) < n else row['Close']
                avg_vol = self.df.iloc[exec_idx]['avg_vol'] if (i + 1) < n else row['avg_vol']
                slippage = self._calc_slippage(exec_price, abs(self.position), avg_vol)
                fill_price = exec_price - slippage  # exit long -> favorable direction subtract slippage? be conservative, add slippage cost
                # to be conservative, treat slippage as cost: for both buy and sell we'll adjust away from filled price
                fill_price = exec_price - slippage
                contracts = self.position
                pnl = (fill_price - self.entry_price) * contracts * self.contract_size
                comm = contracts * self.commission_per_contract
                self.cash += pnl - comm
                self.trade_log.append({
                    'entry_dt': self.entry_dt, 'exit_dt': self.df.index[exec_idx], 'entry_price': self.entry_price,
                    'exit_price': fill_price, 'contracts': contracts, 'pnl': pnl, 'commission': comm,
                    'reason': 'sma_cross_exit'
                })
                # reset
                self.position = 0
                self.entry_price = None
                self.entry_dt = None
                self.stop_price = None
                # advance i? we continue loop; note cash/equity updated
                continue

            # Entry signal (sma crossed up) and no position -> place market buy executed next minute open
            if crossed_up and self.position == 0:
                # entry executed at next bar open if exists
                exec_idx = i + 1 if (i + 1) < n else i
                exec_price = self.df.iloc[exec_idx]['Open'] if (i + 1) < n else row['Close']
                atr_now = row['atr']
                if np.isnan(atr_now) or atr_now <= 0:
                    continue  # skip if no atr
                stop_price = exec_price - self.atr_mult * atr_now
                per_contract_risk = (exec_price - stop_price) * self.contract_size
                if per_contract_risk <= 0:
                    continue
                risk_amount

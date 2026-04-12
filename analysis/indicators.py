# analysis/indicators.py

import pandas as pd
import ta
from config.settings import INDICATOR_SETTINGS, MIN_DAYS_FOR_SMA200
from db.database import load_prices, save_indicators

# =============================================================================
# COMPUTE ALL INDICATORS
# =============================================================================

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a price DataFrame (with columns: date, open, high, low, close, volume),
    compute all technical indicators and return enriched DataFrame.

    Indicators computed:
        - EMA20, EMA50        (trend)
        - SMA200              (long-term trend)
        - RSI                 (momentum)
        - MACD, Signal, Hist  (momentum + direction)
        - ATR                 (volatility)
        - Volume MA           (volume context)
    """

    if df.empty:
        return df

    df = df.copy()
    df = df.sort_values("date").reset_index(drop=True)

    cfg = INDICATOR_SETTINGS

    # -------------------------------------------------------------------------
    # TREND: EMA 20
    # -------------------------------------------------------------------------
    df["ema20"] = ta.trend.EMAIndicator(
        close=df["close"],
        window=cfg["ema_short"]
    ).ema_indicator()

    # -------------------------------------------------------------------------
    # TREND: EMA 50
    # -------------------------------------------------------------------------
    df["ema50"] = ta.trend.EMAIndicator(
        close=df["close"],
        window=cfg["ema_long"]
    ).ema_indicator()

    # -------------------------------------------------------------------------
    # TREND: SMA 200
    # -------------------------------------------------------------------------
    df["sma200"] = ta.trend.SMAIndicator(
        close=df["close"],
        window=cfg["sma_long"]
    ).sma_indicator()

    # -------------------------------------------------------------------------
    # MOMENTUM: RSI
    # -------------------------------------------------------------------------
    df["rsi"] = ta.momentum.RSIIndicator(
        close=df["close"],
        window=cfg["rsi_period"]
    ).rsi()

    # -------------------------------------------------------------------------
    # MOMENTUM: MACD
    # -------------------------------------------------------------------------
    macd_indicator = ta.trend.MACD(
        close=df["close"],
        window_fast=cfg["macd_fast"],
        window_slow=cfg["macd_slow"],
        window_sign=cfg["macd_signal"],
    )
    df["macd"]        = macd_indicator.macd()
    df["macd_signal"] = macd_indicator.macd_signal()
    df["macd_hist"]   = macd_indicator.macd_diff()

    # -------------------------------------------------------------------------
    # VOLATILITY: ATR (Average True Range)
    # -------------------------------------------------------------------------
    df["atr"] = ta.volatility.AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=cfg["atr_period"]
    ).average_true_range()

    # -------------------------------------------------------------------------
    # VOLUME: Volume Moving Average
    # -------------------------------------------------------------------------
    df["volume_ma"] = df["volume"].rolling(
        window=cfg["volume_ma"]
    ).mean()

    return df


# =============================================================================
# COMPUTE + SAVE TO DATABASE
# =============================================================================

def compute_and_save(symbol: str) -> int:
    """
    Load prices for a symbol from DB, compute indicators,
    and save results back to DB.
    Returns number of rows saved.
    """
    print(f"Computing indicators for {symbol}...")

    df = load_prices(symbol)

    if df.empty:
        print(f"  [WARN] No price data found for {symbol}")
        return 0

    if len(df) < 30:
        print(f"  [WARN] Not enough data for {symbol} ({len(df)} rows)")
        return 0

    df = compute_indicators(df)

    # Prepare indicator-only DataFrame for saving
    indicator_cols = [
        "date", "ema20", "ema50", "sma200",
        "rsi", "macd", "macd_signal", "macd_hist",
        "atr", "volume_ma"
    ]
    df_ind = df[indicator_cols].copy()

    # Convert date back to string for saving
    df_ind["date"] = df_ind["date"].dt.strftime("%Y-%m-%d")

    rows = save_indicators(symbol, df_ind)
    print(f"  [DB] {symbol}: {rows} indicator rows saved")
    return rows


# =============================================================================
# COMPUTE ALL STOCKS
# =============================================================================

def compute_all_indicators():
    """
    Compute and save indicators for all symbols that have price data in DB.
    """
    from db.database import get_available_symbols

    symbols = get_available_symbols()

    if not symbols:
        print("[WARN] No symbols found in database. Run price collector first.")
        return

    print("=" * 50)
    print(f"Computing indicators for {len(symbols)} symbols")
    print("=" * 50)

    for symbol in symbols:
        compute_and_save(symbol)

    print("=" * 50)
    print("Indicator computation complete.")
    print("=" * 50)


# =============================================================================
# GET LATEST INDICATOR VALUES (for signal engine + summary)
# =============================================================================

def get_latest_indicators(symbol: str) -> dict:
    """
    Return the most recent indicator values for a symbol as a dict.
    Loads from prices (to compute fresh) rather than DB indicators
    so dashboard always gets up-to-date values.

    Returns dict with keys:
        close, ema20, ema50, sma200, rsi,
        macd, macd_signal, macd_hist,
        atr, volume, volume_ma, date
    Returns empty dict if data unavailable.
    """
    df = load_prices(symbol)

    if df.empty or len(df) < 30:
        return {}

    df = compute_indicators(df)

    # Get last row (most recent date)
    last = df.iloc[-1]

    return {
        "date":        str(last["date"])[:10],
        "close":       round(last["close"], 2),
        "ema20":       round(last["ema20"],  2) if pd.notna(last["ema20"])  else None,
        "ema50":       round(last["ema50"],  2) if pd.notna(last["ema50"])  else None,
        "sma200":      round(last["sma200"], 2) if pd.notna(last["sma200"]) else None,
        "rsi":         round(last["rsi"],    2) if pd.notna(last["rsi"])    else None,
        "macd":        round(last["macd"],   4) if pd.notna(last["macd"])   else None,
        "macd_signal": round(last["macd_signal"], 4) if pd.notna(last["macd_signal"]) else None,
        "macd_hist":   round(last["macd_hist"],   4) if pd.notna(last["macd_hist"])   else None,
        "atr":         round(last["atr"],    2) if pd.notna(last["atr"])    else None,
        "volume":      int(last["volume"])        if pd.notna(last["volume"])   else None,
        "volume_ma":   round(last["volume_ma"], 0) if pd.notna(last["volume_ma"]) else None,
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    compute_all_indicators()
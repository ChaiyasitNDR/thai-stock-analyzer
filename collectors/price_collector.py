# collectors/price_collector.py

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from db.database import save_prices, get_last_updated
from config.settings import THAI_STOCKS, DEFAULT_PERIOD_DAYS

# =============================================================================
# FETCH SINGLE STOCK
# =============================================================================

def fetch_prices(symbol: str, days: int = DEFAULT_PERIOD_DAYS) -> pd.DataFrame:
    """
    Fetch OHLCV data from yfinance for a single symbol.
    Returns a cleaned DataFrame with columns:
        date, open, high, low, close, volume
    Returns empty DataFrame if fetch fails.
    """
    try:
        end_date   = datetime.today()
        start_date = end_date - timedelta(days=days)

        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            auto_adjust=True,
        )

        if df.empty:
            print(f"  [WARN] No data returned for {symbol}")
            return pd.DataFrame()

        # Reset index so Date becomes a column
        df = df.reset_index()

        # Rename columns to lowercase
        df = df.rename(columns={
            "Date":   "date",
            "Open":   "open",
            "High":   "high",
            "Low":    "low",
            "Close":  "close",
            "Volume": "volume",
        })

        # Keep only needed columns
        df = df[["date", "open", "high", "low", "close", "volume"]]

        # Normalize date to string YYYY-MM-DD (strip timezone info)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

        # Drop rows with missing close price
        df = df.dropna(subset=["close"])

        print(f"  [OK] {symbol}: {len(df)} rows fetched")
        return df

    except Exception as e:
        print(f"  [ERROR] Failed to fetch {symbol}: {e}")
        return pd.DataFrame()


# =============================================================================
# FETCH + SAVE SINGLE STOCK
# =============================================================================

def collect_prices(symbol: str, days: int = DEFAULT_PERIOD_DAYS) -> int:
    """
    Fetch prices for one symbol and save to database.
    Returns number of new rows inserted.
    """
    print(f"Collecting prices for {symbol}...")
    df = fetch_prices(symbol, days=days)

    if df.empty:
        return 0

    rows = save_prices(symbol, df)
    print(f"  [DB] {symbol}: {rows} new rows saved")
    return rows


# =============================================================================
# FETCH + SAVE ALL STOCKS
# =============================================================================

def collect_all_prices(days: int = DEFAULT_PERIOD_DAYS):
    """
    Fetch and save prices for all stocks in THAI_STOCKS list.
    Prints a summary when done.
    """
    print("=" * 50)
    print(f"Starting price collection for {len(THAI_STOCKS)} stocks")
    print("=" * 50)

    total_rows = 0
    failed     = []

    for symbol in THAI_STOCKS:
        rows = collect_prices(symbol, days=days)
        total_rows += rows
        if rows == 0:
            failed.append(symbol)

    print("=" * 50)
    print(f"Done. Total new rows saved: {total_rows}")
    if failed:
        print(f"Failed or no new data: {failed}")
    print("=" * 50)


# =============================================================================
# LOAD PRICES FOR DASHBOARD (with fallback to yfinance if DB empty)
# =============================================================================

def get_prices_for_display(
    symbol: str,
    start_date: str = None,
    end_date: str = None
) -> pd.DataFrame:
    """
    Load prices for dashboard display.
    First tries the database.
    If DB has no data, fetches directly from yfinance.
    Returns DataFrame with columns: date, open, high, low, close, volume
    """
    from db.database import load_prices

    df = load_prices(symbol, start_date=start_date, end_date=end_date)

    if df.empty:
        print(f"  [INFO] No DB data for {symbol}, fetching from yfinance...")
        df = fetch_prices(symbol)
        if not df.empty:
            save_prices(symbol, df)
            df = load_prices(symbol, start_date=start_date, end_date=end_date)

    return df


# =============================================================================
# MAIN — run this file directly to collect all prices
# =============================================================================

if __name__ == "__main__":
    collect_all_prices()
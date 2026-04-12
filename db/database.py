# db/database.py

import sqlite3
import pandas as pd
from config.settings import DB_PATH

# =============================================================================
# CONNECTION
# =============================================================================

def get_connection():
    """Return a SQLite connection to the database."""
    import os
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# TABLE CREATION
# =============================================================================

def init_db():
    """Create all tables if they do not exist yet."""
    conn = get_connection()
    cur = conn.cursor()

    # --- Prices table ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            volume      REAL,
            UNIQUE(symbol, date)
        )
    """)

    # --- Indicators table ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            ema20       REAL,
            ema50       REAL,
            sma200      REAL,
            rsi         REAL,
            macd        REAL,
            macd_signal REAL,
            macd_hist   REAL,
            atr         REAL,
            volume_ma   REAL,
            UNIQUE(symbol, date)
        )
    """)

    # --- News table ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol       TEXT,
            category     TEXT    NOT NULL,
            macro_tag    TEXT,
            source       TEXT,
            title        TEXT    NOT NULL,
            published_at TEXT,
            url          TEXT,
            UNIQUE(url)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized OK.")


# =============================================================================
# PRICES — WRITE
# =============================================================================

def save_prices(symbol: str, df: pd.DataFrame):
    """
    Save OHLCV dataframe to prices table.
    df must have columns: date, open, high, low, close, volume
    Skips duplicates silently (INSERT OR IGNORE).
    """
    conn = get_connection()
    cur = conn.cursor()

    rows_inserted = 0
    for _, row in df.iterrows():
        cur.execute("""
            INSERT OR IGNORE INTO prices
                (symbol, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol,
            str(row["date"]),
            row.get("open"),
            row.get("high"),
            row.get("low"),
            row.get("close"),
            row.get("volume"),
        ))
        rows_inserted += cur.rowcount

    conn.commit()
    conn.close()
    return rows_inserted


# =============================================================================
# PRICES — READ
# =============================================================================

def load_prices(symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Load OHLCV data for a symbol from the database.
    Returns a DataFrame sorted by date ascending.
    """
    conn = get_connection()

    query = "SELECT * FROM prices WHERE symbol = ?"
    params = [symbol]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date ASC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])

    return df


# =============================================================================
# INDICATORS — WRITE
# =============================================================================

def save_indicators(symbol: str, df: pd.DataFrame):
    """
    Save computed indicators to indicators table.
    df must have columns: date, ema20, ema50, sma200, rsi,
                          macd, macd_signal, macd_hist, atr, volume_ma
    """
    conn = get_connection()
    cur = conn.cursor()

    rows_inserted = 0
    for _, row in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO indicators
                (symbol, date, ema20, ema50, sma200, rsi,
                 macd, macd_signal, macd_hist, atr, volume_ma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol,
            str(row["date"]),
            row.get("ema20"),
            row.get("ema50"),
            row.get("sma200"),
            row.get("rsi"),
            row.get("macd"),
            row.get("macd_signal"),
            row.get("macd_hist"),
            row.get("atr"),
            row.get("volume_ma"),
        ))
        rows_inserted += cur.rowcount

    conn.commit()
    conn.close()
    return rows_inserted


# =============================================================================
# INDICATORS — READ
# =============================================================================

def load_indicators(symbol: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Load indicators for a symbol from the database.
    Returns a DataFrame sorted by date ascending.
    """
    conn = get_connection()

    query = "SELECT * FROM indicators WHERE symbol = ?"
    params = [symbol]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date ASC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])

    return df


# =============================================================================
# NEWS — WRITE
# =============================================================================

def save_news(items: list[dict]):
    """
    Save a list of news dicts to the news table.
    Each dict must have: title, url, category
    Optional keys: symbol, macro_tag, source, published_at
    Skips duplicates by URL silently.
    """
    conn = get_connection()
    cur = conn.cursor()

    rows_inserted = 0
    for item in items:
        cur.execute("""
            INSERT OR IGNORE INTO news
                (symbol, category, macro_tag, source, title, published_at, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item.get("symbol"),
            item.get("category", "global"),
            item.get("macro_tag"),
            item.get("source"),
            item.get("title", ""),
            item.get("published_at"),
            item.get("url", ""),
        ))
        rows_inserted += cur.rowcount

    conn.commit()
    conn.close()
    return rows_inserted


# =============================================================================
# NEWS — READ
# =============================================================================

def load_news(
    category: str = None,
    symbol: str = None,
    macro_tag: str = None,
    limit: int = 50
) -> pd.DataFrame:
    """
    Load news from the database with optional filters.
    Returns a DataFrame sorted by published_at descending (newest first).
    """
    conn = get_connection()

    query = "SELECT * FROM news WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if symbol:
        query += " AND symbol = ?"
        params.append(symbol)
    if macro_tag:
        query += " AND macro_tag = ?"
        params.append(macro_tag)

    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    return df


# =============================================================================
# UTILITY
# =============================================================================

def get_available_symbols() -> list:
    """Return list of symbols that have price data in the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM prices ORDER BY symbol")
    symbols = [row[0] for row in cur.fetchall()]
    conn.close()
    return symbols


def get_last_updated(symbol: str) -> str:
    """Return the most recent date for a symbol in the prices table."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT MAX(date) FROM prices WHERE symbol = ?", (symbol,)
    )
    result = cur.fetchone()[0]
    conn.close()
    return result or "No data"

# =============================================================================
# USER PREFERENCES — บันทึกค่าที่ผู้ใช้เลือกล่าสุด
# =============================================================================

def save_preference(key: str, value: str):
    """บันทึก preference ลง database"""
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        INSERT OR REPLACE INTO preferences (key, value)
        VALUES (?, ?)
    """, (key, value))

    conn.commit()
    conn.close()


def load_preference(key: str, default: str = None) -> str:
    """โหลด preference จาก database"""
    conn = get_connection()
    cur  = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cur.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else default
    except Exception:
        conn.close()
        return default
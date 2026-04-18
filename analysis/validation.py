# analysis/validation.py — v2 (bug fixes + better metrics)

import pandas as pd
import numpy as np
from datetime import datetime

# =============================================================================
# REGIME LABELING
# =============================================================================

def label_regime(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ema20" not in df.columns or "ema50" not in df.columns:
        from analysis.indicators import compute_indicators
        df = compute_indicators(df)

    df["ema_spread_pct"] = (
        abs(df["ema20"] - df["ema50"]) / df["close"] * 100
    ).fillna(0)
    df["range_20_pct"] = (
        (df["high"].rolling(20).max() - df["low"].rolling(20).min())
        / df["close"] * 100
    ).fillna(0)

    df["regime"] = "Mixed"
    df.loc[
        (df["ema_spread_pct"] >= 2.0) & (df["range_20_pct"] >= 5.0),
        "regime"
    ] = "Trending"
    df.loc[
        (df["ema_spread_pct"] < 1.0) & (df["range_20_pct"] < 3.0),
        "regime"
    ] = "Ranging"
    return df


# =============================================================================
# SIGNAL LABELING — แก้ bug ลำดับ RSI (ทำ WATCH ก่อน แล้วทับด้วย OVERSOLD/OVERBOUGHT)
# =============================================================================

def label_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "ema20" not in df.columns:
        from analysis.indicators import compute_indicators
        df = compute_indicators(df)

    # --- Trend Signal ---
    df["sig_trend"] = "NEUTRAL"
    df.loc[
        (df["close"] > df["ema20"]) & (df["ema20"] > df["ema50"]),
        "sig_trend"
    ] = "BULLISH"
    df.loc[
        (df["close"] < df["ema20"]) & (df["ema20"] < df["ema50"]),
        "sig_trend"
    ] = "BEARISH"
    if "sma200" in df.columns:
        df.loc[
            (df["close"] > df["ema20"]) &
            (df["ema20"] > df["ema50"]) &
            (df["ema50"] > df["sma200"]),
            "sig_trend"
        ] = "STRONG_BULLISH"
        df.loc[
            (df["close"] < df["ema20"]) &
            (df["ema20"] < df["ema50"]) &
            (df["ema50"] < df["sma200"]),
            "sig_trend"
        ] = "STRONG_BEARISH"

    # --- RSI Signal — แก้ bug: ทำ WATCH ก่อน แล้วทับด้วย extreme ---
    df["sig_rsi"] = "NEUTRAL"
    df.loc[df["rsi"] < 40,  "sig_rsi"] = "WATCH_OVERSOLD"    # ทำก่อน
    df.loc[df["rsi"] < 30,  "sig_rsi"] = "OVERSOLD"           # ทับทีหลัง ✅
    df.loc[df["rsi"] > 60,  "sig_rsi"] = "WATCH_OVERBOUGHT"  # ทำก่อน
    df.loc[df["rsi"] > 70,  "sig_rsi"] = "OVERBOUGHT"         # ทับทีหลัง ✅

    # --- MACD Signal ---
    df["sig_macd"] = "NEUTRAL"
    df.loc[
        (df["macd"] > df["macd_signal"]) & (df["macd_hist"] > 0),
        "sig_macd"
    ] = "BULLISH"
    df.loc[
        (df["macd"] < df["macd_signal"]) & (df["macd_hist"] < 0),
        "sig_macd"
    ] = "BEARISH"

    return df


# =============================================================================
# FUTURE RETURNS
# =============================================================================

def add_future_returns(
    df: pd.DataFrame,
    horizons: list = [1, 3, 5, 10]
) -> pd.DataFrame:
    df = df.copy()
    for h in horizons:
        df[f"future_return_{h}d"] = (
            df["close"].shift(-h) / df["close"] - 1
        ) * 100
    return df


# =============================================================================
# HIT RATE — แก้ precision/recall + เพิ่ม avg_hit, avg_miss, median
# =============================================================================

def compute_hit_rate(
    df:            pd.DataFrame,
    signal_col:    str,
    signal_value:  str,
    horizon:       int,
    direction:     str = "up",
    regime_filter: str = None,
    min_sample:    int = 10,
) -> dict:
    return_col = f"future_return_{horizon}d"
    if return_col not in df.columns:
        return {"available": False, "reason": f"ไม่มี column {return_col}"}

    mask = df[signal_col] == signal_value
    if regime_filter:
        mask = mask & (df["regime"] == regime_filter)

    subset = df[mask][return_col].dropna()

    if len(subset) < min_sample:
        return {
            "available":   False,
            "reason":      f"ข้อมูลน้อย ({len(subset)} ครั้ง, ต้องการ ≥ {min_sample})",
            "sample_size": len(subset),
        }

    # Hit / Miss
    if direction == "up":
        hit_mask = subset > 0
    else:
        hit_mask = subset < 0

    hits   = hit_mask.sum()
    misses = len(subset) - hits

    hit_rate = hits / len(subset) * 100
    avg_all  = subset.mean()
    avg_hit  = subset[hit_mask].mean()  if hits   > 0 else 0.0
    avg_miss = subset[~hit_mask].mean() if misses > 0 else 0.0
    median   = subset.median()

    # =================================================================
    # FIXED Profit Factor
    # gross_profit = sum of POSITIVE returns (absolute)
    # gross_loss   = sum of ABSOLUTE VALUE of negative returns
    # PF >= 0 always
    # =================================================================
    positive_returns = subset[subset > 0]
    negative_returns = subset[subset < 0]

    gross_profit = positive_returns.sum()          # always >= 0
    gross_loss   = abs(negative_returns.sum())     # always >= 0

    if gross_loss == 0 and gross_profit > 0:
        profit_factor        = 9999.0              # แสดงเป็น "∞"
        profit_factor_display = "∞ (ไม่มีขาดทุน)"
    elif gross_profit == 0 and gross_loss > 0:
        profit_factor        = 0.0
        profit_factor_display = "0.00"
    elif gross_profit == 0 and gross_loss == 0:
        profit_factor        = None
        profit_factor_display = "N/A"
    else:
        profit_factor        = round(gross_profit / gross_loss, 2)
        profit_factor_display = str(profit_factor)

    # =================================================================
    # FIXED Expectancy = p(win)*avg_win + p(loss)*avg_loss
    # avg_miss มีเครื่องหมายลบอยู่แล้ว → ไม่ต้องลบซ้ำ
    # =================================================================
    p_win  = hits / len(subset)
    p_loss = 1 - p_win
    expectancy = round(p_win * avg_hit + p_loss * avg_miss, 3)

    # Baseline avg (ทุกวันไม่กรอง signal)
    baseline_avg = df[return_col].dropna().mean()
    delta_vs_baseline = round(avg_all - baseline_avg, 2)
    baseline_label = (
        "✅ ดีกว่า baseline"
        if delta_vs_baseline > 0
        else "❌ แย่กว่า baseline"
    )

    # Rule-based interpretation hint
    hint = _generate_hint(hit_rate, avg_all, avg_hit, avg_miss,
                          delta_vs_baseline, signal_value, direction)

    max_dd = _compute_max_drawdown(subset)

    return {
        "available":              True,
        "signal":                 f"{signal_col}={signal_value}",
        "horizon":                horizon,
        "regime":                 regime_filter or "all",
        "sample_size":            int(len(subset)),
        # Accuracy
        "hit_rate":               round(hit_rate, 1),
        # Profitability
        "avg_return":             round(avg_all, 2),
        "avg_return_hit":         round(avg_hit, 2),
        "avg_return_miss":        round(avg_miss, 2),
        "median_return":          round(median, 2),
        "profit_factor":          profit_factor,
        "profit_factor_display":  profit_factor_display,
        "expectancy":             expectancy,
        "max_drawdown":           round(max_dd, 2),
        # Baseline
        "baseline_avg":           round(baseline_avg, 2),
        "delta_vs_baseline":      delta_vs_baseline,
        "baseline_label":         baseline_label,
        # Hint
        "hint":                   hint,
    }


def _generate_hint(
    hit_rate:          float,
    avg_all:           float,
    avg_hit:           float,
    avg_miss:          float,
    delta_vs_baseline: float,
    signal_value:      str,
    direction:         str,
) -> str:
    """Rule-based interpretation hint — ไม่ใช้ LLM"""

    # Hit ต่ำแต่ avg บวก → contrarian
    if hit_rate < 45 and avg_all > 0 and direction == "down":
        return (
            f"⚠️ Hit ต่ำ ({hit_rate:.0f}%) แต่ avg return ยังบวก "
            "→ สัญญาณนี้อาจเป็น contrarian ในตลาดขาขึ้น"
        )

    # Hit สูงและ delta บวก → สัญญาณดี
    if hit_rate >= 55 and delta_vs_baseline > 0:
        return (
            f"✅ Hit {hit_rate:.0f}% และดีกว่า baseline "
            f"+{delta_vs_baseline:.2f}% → สัญญาณนี้มีประโยชน์"
        )

    # Hit สูงแต่ avg_hit น้อย → win เล็ก
    if hit_rate >= 55 and 0 < avg_hit < 1.0:
        return (
            f"⚠️ Hit สูง ({hit_rate:.0f}%) แต่กำไรต่อครั้งน้อย "
            f"({avg_hit:.2f}%) → ระวัง transaction cost"
        )

    # Hit ต่ำมาก → ใช้ระวัง
    if hit_rate < 40:
        return (
            f"🔴 Hit เพียง {hit_rate:.0f}% → สัญญาณนี้ "
            "ทายทิศได้น้อยกว่าสุ่มในชุดข้อมูลนี้"
        )

    # แย่กว่า baseline
    if delta_vs_baseline < -0.5:
        return (
            f"❌ ผลตอบแทนเฉลี่ยต่ำกว่า baseline "
            f"{delta_vs_baseline:.2f}% → สัญญาณอาจไม่ช่วยเพิ่มมูลค่า"
        )

    return "ℹ️ สัญญาณอยู่ในระดับปานกลาง — ควรใช้ประกอบ indicator อื่น"

def _compute_max_drawdown(returns: pd.Series) -> float:
    """คำนวณ max drawdown จาก series of returns"""
    try:
        cum = (1 + returns / 100).cumprod()
        dd  = (cum - cum.cummax()) / cum.cummax() * 100
        return abs(dd.min())
    except Exception:
        return 0.0

# =============================================================================
# SIGNAL DECAY
# =============================================================================

def compute_signal_decay(
    df:           pd.DataFrame,
    signal_col:   str,
    signal_value: str,
    horizons:     list = [1, 3, 5, 10],
    direction:    str = "up",
) -> list:
    results = []
    for h in horizons:
        r = compute_hit_rate(df, signal_col, signal_value, h, direction)
        r["horizon"] = h
        results.append(r)
    return results


# =============================================================================
# FULL VALIDATION
# =============================================================================

def run_validation(
    df:       pd.DataFrame,
    symbol:   str,
    horizons: list = [1, 3, 5, 10],
) -> dict:
    if len(df) < 60:
        return {
            "available": False,
            "reason":    f"ข้อมูลน้อยเกินไป ({len(df)} วัน, ต้องการ ≥ 60)"
        }

    from analysis.indicators import compute_indicators
    df_ind = compute_indicators(df.copy())
    df_ind = label_regime(df_ind)
    df_ind = label_signals(df_ind)
    df_ind = add_future_returns(df_ind, horizons)

    results = {
        "available":   True,
        "symbol":      symbol,
        "computed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "n_days":      len(df),
        "horizons":    horizons,
        "signals":     {},
        "decay":       {},
        "regime_dist": {},
    }

    results["regime_dist"] = df_ind["regime"].value_counts().to_dict()

    signal_configs = [
        ("sig_trend", "BULLISH",        "up"),
        ("sig_trend", "BEARISH",        "down"),
        ("sig_trend", "STRONG_BULLISH", "up"),
        ("sig_rsi",   "OVERSOLD",       "up"),
        ("sig_rsi",   "OVERBOUGHT",     "down"),
        ("sig_macd",  "BULLISH",        "up"),
        ("sig_macd",  "BEARISH",        "down"),
    ]

    for sig_col, sig_val, direction in signal_configs:
        key = f"{sig_col}_{sig_val}"
        results["signals"][key] = {
            "overall":  compute_hit_rate(df_ind, sig_col, sig_val, 5, direction),
            "trending": compute_hit_rate(df_ind, sig_col, sig_val, 5, direction, "Trending"),
            "ranging":  compute_hit_rate(df_ind, sig_col, sig_val, 5, direction, "Ranging"),
        }
        results["decay"][key] = compute_signal_decay(
            df_ind, sig_col, sig_val, horizons, direction
        )

    return results


# =============================================================================
# SAVE / LOAD
# =============================================================================

def save_validation_results(symbol: str, results: dict):
    from db.database import get_connection
    import json
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS validation_results (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol       TEXT NOT NULL,
            computed_at  TEXT NOT NULL,
            results_json TEXT NOT NULL,
            UNIQUE(symbol)
        )
    """)
    cur.execute("""
        INSERT OR REPLACE INTO validation_results
            (symbol, computed_at, results_json)
        VALUES (?, ?, ?)
    """, (symbol, results.get("computed_at",""), json.dumps(results, ensure_ascii=False)))
    conn.commit()
    conn.close()


def load_validation_results(symbol: str) -> dict:
    from db.database import get_connection
    import json
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                computed_at TEXT NOT NULL,
                results_json TEXT NOT NULL,
                UNIQUE(symbol)
            )
        """)
        cur.execute(
            "SELECT results_json FROM validation_results WHERE symbol=?",
            (symbol,)
        )
        row = cur.fetchone()
        conn.close()
        return json.loads(row[0]) if row else {"available": False, "reason": "ยังไม่มีข้อมูล"}
    except Exception as e:
        conn.close()
        return {"available": False, "reason": str(e)}
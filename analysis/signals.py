# analysis/signals.py

from config.settings import RSI_ZONES, MACRO_SECTOR_IMPACT, STOCK_SECTOR

# =============================================================================
# RULE 1: TREND SIGNAL
# Logic: Compare EMA20 / EMA50 / SMA200 alignment
# =============================================================================

def analyze_trend(ind: dict) -> dict:
    """
    Rules:
        STRONG BULLISH  : close > EMA20 > EMA50 > SMA200
        BULLISH         : close > EMA20 > EMA50 (SMA200 unavailable or below)
        NEUTRAL         : mixed alignment
        BEARISH         : close < EMA20 < EMA50
        STRONG BEARISH  : close < EMA20 < EMA50 < SMA200
    """
    close  = ind.get("close")
    ema20  = ind.get("ema20")
    ema50  = ind.get("ema50")
    sma200 = ind.get("sma200")

    if not all([close, ema20, ema50]):
        return {"signal": "INSUFFICIENT DATA", "detail": "EMA values unavailable"}

    has_sma200 = sma200 is not None

    if has_sma200:
        if close > ema20 > ema50 > sma200:
            return {
                "signal": "STRONG BULLISH",
                "detail": f"Price ({close}) > EMA20 ({ema20}) > EMA50 ({ema50}) > SMA200 ({sma200})"
            }
        if close < ema20 < ema50 < sma200:
            return {
                "signal": "STRONG BEARISH",
                "detail": f"Price ({close}) < EMA20 ({ema20}) < EMA50 ({ema50}) < SMA200 ({sma200})"
            }

    if close > ema20 > ema50:
        return {
            "signal": "BULLISH",
            "detail": f"Price ({close}) > EMA20 ({ema20}) > EMA50 ({ema50})"
        }
    if close < ema20 < ema50:
        return {
            "signal": "BEARISH",
            "detail": f"Price ({close}) < EMA20 ({ema20}) < EMA50 ({ema50})"
        }

    return {
        "signal": "NEUTRAL",
        "detail": f"Mixed EMA alignment — Price ({close}), EMA20 ({ema20}), EMA50 ({ema50})"
    }


# =============================================================================
# RULE 2: RSI SIGNAL
# Logic: Zone-based momentum reading
# =============================================================================

def analyze_rsi(ind: dict) -> dict:
    """
    Rules:
        RSI < 30  : OVERSOLD      — potential bounce zone
        RSI 30-40 : WATCH OVERSOLD — recovering from low
        RSI 40-60 : NEUTRAL
        RSI 60-70 : WATCH OVERBOUGHT — approaching high
        RSI > 70  : OVERBOUGHT    — potential pullback zone
    """
    rsi = ind.get("rsi")

    if rsi is None:
        return {"signal": "INSUFFICIENT DATA", "detail": "RSI unavailable"}

    z = RSI_ZONES

    if rsi < z["oversold"]:
        return {
            "signal": "OVERSOLD",
            "detail": f"RSI = {rsi:.1f} — below {z['oversold']}, potential bounce zone"
        }
    if rsi < z["oversold_watch"]:
        return {
            "signal": "WATCH OVERSOLD",
            "detail": f"RSI = {rsi:.1f} — recovering from oversold territory"
        }
    if rsi > z["overbought"]:
        return {
            "signal": "OVERBOUGHT",
            "detail": f"RSI = {rsi:.1f} — above {z['overbought']}, potential pullback zone"
        }
    if rsi > z["overbought_watch"]:
        return {
            "signal": "WATCH OVERBOUGHT",
            "detail": f"RSI = {rsi:.1f} — approaching overbought territory"
        }

    return {
        "signal": "NEUTRAL",
        "detail": f"RSI = {rsi:.1f} — in neutral zone ({z['neutral_low']}–{z['neutral_high']})"
    }


# =============================================================================
# RULE 3: MACD SIGNAL
# Logic: Crossover + histogram direction
# =============================================================================

def analyze_macd(ind: dict) -> dict:
    """
    Rules:
        MACD > Signal AND Hist > 0  : BULLISH MOMENTUM
        MACD < Signal AND Hist < 0  : BEARISH MOMENTUM
        MACD crosses above Signal   : BULLISH CROSSOVER
        MACD crosses below Signal   : BEARISH CROSSOVER
        Otherwise                   : NEUTRAL
    """
    macd        = ind.get("macd")
    macd_signal = ind.get("macd_signal")
    macd_hist   = ind.get("macd_hist")

    if any(v is None for v in [macd, macd_signal, macd_hist]):
        return {"signal": "INSUFFICIENT DATA", "detail": "MACD values unavailable"}

    if macd > macd_signal and macd_hist > 0:
        return {
            "signal": "BULLISH MOMENTUM",
            "detail": f"MACD ({macd:.4f}) > Signal ({macd_signal:.4f}), Histogram positive ({macd_hist:.4f})"
        }
    if macd < macd_signal and macd_hist < 0:
        return {
            "signal": "BEARISH MOMENTUM",
            "detail": f"MACD ({macd:.4f}) < Signal ({macd_signal:.4f}), Histogram negative ({macd_hist:.4f})"
        }

    return {
        "signal": "NEUTRAL",
        "detail": f"MACD ({macd:.4f}), Signal ({macd_signal:.4f}), Histogram ({macd_hist:.4f})"
    }


# =============================================================================
# RULE 4: VOLUME SIGNAL
# Logic: Compare current volume vs volume moving average
# =============================================================================

def analyze_volume(ind: dict) -> dict:
    """
    Rules:
        Volume > 1.5x Volume MA : HIGH VOLUME — confirms price move
        Volume < 0.5x Volume MA : LOW VOLUME  — weak conviction
        Otherwise               : NORMAL VOLUME
    """
    volume    = ind.get("volume")
    volume_ma = ind.get("volume_ma")

    if not volume or not volume_ma:
        return {"signal": "INSUFFICIENT DATA", "detail": "Volume data unavailable"}

    ratio = volume / volume_ma

    if ratio > 1.5:
        return {
            "signal": "HIGH VOLUME",
            "detail": f"Volume ({int(volume):,}) is {ratio:.1f}x above MA ({int(volume_ma):,}) — strong conviction"
        }
    if ratio < 0.5:
        return {
            "signal": "LOW VOLUME",
            "detail": f"Volume ({int(volume):,}) is {ratio:.1f}x below MA ({int(volume_ma):,}) — weak conviction"
        }

    return {
        "signal": "NORMAL VOLUME",
        "detail": f"Volume ({int(volume):,}) is {ratio:.1f}x of MA ({int(volume_ma):,})"
    }


# =============================================================================
# RULE 5: VOLATILITY SIGNAL
# Logic: ATR relative to price
# =============================================================================

def analyze_volatility(ind: dict) -> dict:
    """
    Rules:
        ATR/Price > 3%  : HIGH VOLATILITY  — elevated risk
        ATR/Price < 1%  : LOW VOLATILITY   — quiet market
        Otherwise       : NORMAL VOLATILITY
    """
    atr   = ind.get("atr")
    close = ind.get("close")

    if not atr or not close:
        return {"signal": "INSUFFICIENT DATA", "detail": "ATR unavailable"}

    atr_pct = (atr / close) * 100

    if atr_pct > 3.0:
        return {
            "signal": "HIGH VOLATILITY",
            "detail": f"ATR = {atr:.2f} ({atr_pct:.1f}% of price) — elevated daily risk"
        }
    if atr_pct < 1.0:
        return {
            "signal": "LOW VOLATILITY",
            "detail": f"ATR = {atr:.2f} ({atr_pct:.1f}% of price) — quiet, low-risk environment"
        }

    return {
        "signal": "NORMAL VOLATILITY",
        "detail": f"ATR = {atr:.2f} ({atr_pct:.1f}% of price)"
    }


# =============================================================================
# CONFIDENCE LEVEL
# Logic: Count how many signals agree on direction
# =============================================================================

def compute_confidence(signals: dict) -> dict:
    """
    Count bullish vs bearish signals across all rules.
    Returns confidence level: HIGH / MEDIUM / LOW
    and a score summary.

    Bullish signals  : STRONG BULLISH, BULLISH, OVERSOLD,
                       BULLISH MOMENTUM, BULLISH CROSSOVER
    Bearish signals  : STRONG BEARISH, BEARISH, OVERBOUGHT,
                       BEARISH MOMENTUM, BEARISH CROSSOVER
    """
    BULLISH_SIGNALS = {
        "STRONG BULLISH", "BULLISH", "OVERSOLD",
        "BULLISH MOMENTUM", "BULLISH CROSSOVER", "WATCH OVERSOLD"
    }
    BEARISH_SIGNALS = {
        "STRONG BEARISH", "BEARISH", "OVERBOUGHT",
        "BEARISH MOMENTUM", "BEARISH CROSSOVER", "WATCH OVERBOUGHT"
    }

    bullish_count = 0
    bearish_count = 0

    for key, result in signals.items():
        sig = result.get("signal", "")
        if sig in BULLISH_SIGNALS:
            bullish_count += 1
        elif sig in BEARISH_SIGNALS:
            bearish_count += 1

    total = bullish_count + bearish_count
    dominant = "BULLISH" if bullish_count >= bearish_count else "BEARISH"

    if total == 0:
        confidence = "LOW"
    elif max(bullish_count, bearish_count) >= 3:
        confidence = "HIGH"
    elif max(bullish_count, bearish_count) >= 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "confidence":    confidence,
        "dominant":      dominant,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "detail": (
            f"{bullish_count} bullish signal(s), "
            f"{bearish_count} bearish signal(s) out of {total} decisive signal(s)"
        )
    }


# =============================================================================
# GLOBAL MACRO IMPACT
# Logic: Map recent macro news tags to affected Thai sectors
# =============================================================================

def analyze_macro_impact(symbol: str, recent_macro_tags: list[str]) -> list[dict]:
    """
    Given a stock symbol and a list of recent macro_tags from news,
    return list of impact statements relevant to this stock's sector.

    Example output:
        [
            {
                "macro_tag": "energy",
                "direction": "positive",
                "reason": "Rising energy prices benefit Thai energy producers"
            }
        ]
    """
    sector  = STOCK_SECTOR.get(symbol, "unknown")
    impacts = []

    for tag in set(recent_macro_tags):
        rule = MACRO_SECTOR_IMPACT.get(tag)
        if not rule:
            continue
        if sector in rule["sectors"]:
            impacts.append({
                "macro_tag": tag,
                "direction": rule["direction"],
                "reason":    rule["reason"],
            })

    return impacts


# =============================================================================
# MASTER SIGNAL RUNNER
# Returns all signals + confidence for a given indicator dict
# =============================================================================

def run_all_signals(symbol: str, ind: dict, recent_macro_tags: list[str] = None) -> dict:
    """
    Run all rule-based signal analyses for a symbol.
    Returns a structured dict with all signals and confidence level.
    """
    if not ind:
        return {"error": "No indicator data available"}

    signals = {
        "trend":      analyze_trend(ind),
        "rsi":        analyze_rsi(ind),
        "macd":       analyze_macd(ind),
        "volume":     analyze_volume(ind),
        "volatility": analyze_volatility(ind),
    }

    confidence = compute_confidence(signals)

    macro_impacts = []
    if recent_macro_tags:
        macro_impacts = analyze_macro_impact(symbol, recent_macro_tags)

    return {
        "symbol":        symbol,
        "date":          ind.get("date"),
        "signals":       signals,
        "confidence":    confidence,
        "macro_impacts": macro_impacts,
    }

# =============================================================================
# TRADING RECOMMENDATION (Rule-Based)
# คำนวณราคาแนะนำซื้อ/ขาย/stop loss จาก indicator
# =============================================================================

def compute_trading_recommendation(ind: dict, signals: dict, confidence: dict) -> dict:
    """
    คำนวณคำแนะนำการซื้อขายแบบ rule-based
    ใช้ ATR เป็นหน่วยวัดระยะราคา
    ไม่ใช้ AI — ทุก rule อธิบายได้จากตัวเลขบน chart
    """
    close = ind.get("close")
    atr   = ind.get("atr")
    ema20 = ind.get("ema20")
    ema50 = ind.get("ema50")

    if not close or not atr:
        return {"error": "ข้อมูลไม่เพียงพอในการคำนวณ"}

    dominant   = confidence.get("dominant", "NEUTRAL")
    conf_level = confidence.get("confidence", "LOW")
    bull_count = confidence.get("bullish_count", 0)
    bear_count = confidence.get("bearish_count", 0)
    total      = bull_count + bear_count

    # --- % ความเชื่อมั่น ---
    if total == 0:
        up_pct   = 50.0
        down_pct = 50.0
    else:
        up_pct   = round((bull_count / total) * 100, 1)
        down_pct = round((bear_count / total) * 100, 1)

    # --- ควรซื้อหรือขาย ---
    should_buy  = dominant == "BULLISH"  and conf_level in ["MEDIUM", "HIGH"]
    should_sell = dominant == "BEARISH"  and conf_level in ["MEDIUM", "HIGH"]

    # --- ราคาซื้อเป็นขั้นบันได (3 ระดับ) ---
    # ใช้ ATR เป็นตัวกำหนดระยะห่างแต่ละขั้น
    buy_levels = [
        round(close - (atr * 0.5), 2),   # ขั้นที่ 1: ใกล้ราคาปัจจุบัน
        round(close - (atr * 1.0), 2),   # ขั้นที่ 2: ต่ำกว่า 1 ATR
        round(close - (atr * 1.5), 2),   # ขั้นที่ 3: ต่ำกว่า 1.5 ATR
    ]

    # --- ราคาขายเป็นขั้นบันได (3 ระดับ) ---
    # ใช้ EMA เป็น resistance + ATR เป็นระยะ
    sell_target1 = ema20 if ema20 and ema20 > close else round(close + (atr * 0.5), 2)
    sell_target2 = ema50 if ema50 and ema50 > close else round(close + (atr * 1.0), 2)
    sell_target3 = round(close + (atr * 2.0), 2)

    sell_levels = [
        round(sell_target1, 2),
        round(sell_target2, 2),
        round(sell_target3, 2),
    ]

    # --- Stop Loss ---
    # Rule: ต่ำกว่าราคาปัจจุบัน 1.5x ATR (หรือ EMA50 แล้วแต่อะไรต่ำกว่า)
    stop_loss_atr  = round(close - (atr * 1.5), 2)
    stop_loss_ema  = round(ema50 - (atr * 0.5), 2) if ema50 else stop_loss_atr
    stop_loss      = min(stop_loss_atr, stop_loss_ema)

    return {
        "should_buy":   should_buy,
        "should_sell":  should_sell,
        "dominant":     dominant,
        "conf_level":   conf_level,
        "up_pct":       up_pct,
        "down_pct":     down_pct,
        "buy_levels":   buy_levels,
        "sell_levels":  sell_levels,
        "stop_loss":    stop_loss,
        "atr_used":     round(atr, 2),
        "close":        close,
    }
# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    from analysis.indicators import get_latest_indicators

    symbol = "PTT.BK"
    ind    = get_latest_indicators(symbol)

    # Simulate some macro tags from recent news
    fake_tags = ["energy", "rates", "china"]

    result = run_all_signals(symbol, ind, fake_tags)

    print(f"\n=== Signals for {symbol} ===")
    print(f"Date: {result['date']}")
    print(f"\nConfidence: {result['confidence']['confidence']} ({result['confidence']['dominant']})")
    print(f"  {result['confidence']['detail']}")

    print("\n--- Individual Signals ---")
    for name, sig in result["signals"].items():
        print(f"  {name:12s}: {sig['signal']:20s} | {sig['detail']}")

    print("\n--- Macro Impacts ---")
    for impact in result["macro_impacts"]:
        print(f"  [{impact['macro_tag']}] {impact['direction'].upper()} — {impact['reason']}")
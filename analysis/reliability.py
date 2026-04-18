# analysis/reliability.py
# Reliability Framework v2 — Non-self-deceiving scoring
# แก้ไข: Band inflation, stricter thresholds, audit trail

import pandas as pd
from datetime import datetime

# =============================================================================
# มิติที่ 1: Signal Agreement (SA) — max 25 คะแนน
# เพิ่ม conflict_penalty สำหรับสัญญาณขัดแย้ง
# =============================================================================

def compute_signal_agreement(signals: dict) -> dict:
    BULLISH = {
        "STRONG BULLISH", "BULLISH", "OVERSOLD",
        "BULLISH MOMENTUM", "BULLISH CROSSOVER", "WATCH OVERSOLD"
    }
    BEARISH = {
        "STRONG BEARISH", "BEARISH", "OVERBOUGHT",
        "BEARISH MOMENTUM", "BEARISH CROSSOVER", "WATCH OVERBOUGHT"
    }

    bull = bear = neutral = 0
    for result in signals.values():
        sig = result.get("signal", "")
        if sig in BULLISH:
            bull += 1
        elif sig in BEARISH:
            bear += 1
        else:
            neutral += 1

    total = bull + bear

    if total < 2:
        base_score    = 0
        agreement_pct = 0.0
    else:
        agreement_pct = max(bull, bear) / total
        if agreement_pct >= 0.80:
            base_score = 25
        elif agreement_pct >= 0.60:
            base_score = 15
        elif agreement_pct >= 0.40:
            base_score = 8
        else:
            base_score = 0

    # Conflict penalty — หักเมื่อมีสัญญาณขัดแย้ง
    conflict_penalty = 0
    if bull > 0 and bear > 0:
        conflict_ratio   = min(bull, bear) / total
        conflict_penalty = int(conflict_ratio * 10)

    final_score = max(0, base_score - conflict_penalty)

    return {
        "score":            final_score,
        "max":              25,
        "base_score":       base_score,
        "conflict_penalty": conflict_penalty,
        "bull_count":       bull,
        "bear_count":       bear,
        "neutral_count":    neutral,
        "agreement_pct":    round(agreement_pct * 100, 1),
        "dominant":         "ขาขึ้น" if bull >= bear else "ขาลง",
        "explanation": (
            f"indicator {max(bull,bear)} ใน {total} ตัวเห็นตรงกัน "
            f"({round(agreement_pct*100,1)}%) "
            f"หักสัญญาณขัดแย้ง -{conflict_penalty}"
        ),
        "audit": {
            "formula":  "max(bull,bear)/total * 25 - conflict_penalty",
            "values":   f"bull={bull}, bear={bear}, total={total}",
            "base":     base_score,
            "penalty":  conflict_penalty,
            "final":    final_score,
        }
    }


# =============================================================================
# มิติที่ 2: Data Quality (DQ) — max 50 คะแนน
# เข้มขึ้น: 3 วัน = 12 คะแนน (ไม่ใช่ 20)
# Hard cap: >5 วัน → Band ≤ C
# =============================================================================

def compute_data_quality(ind: dict, df: pd.DataFrame) -> dict:
    issues      = []
    hard_cap    = None  # จะ set ถ้าข้อมูลเก่ามาก
    days_old    = 999
    freshness_score = 0

    # --- Freshness ---
    try:
        last_date = pd.to_datetime(df["date"].max())
        days_old  = (datetime.now() - last_date).days

        if days_old == 0:
            freshness_score = 30
        elif days_old == 1:
            freshness_score = 25
            issues.append("ข้อมูลล่าสุดเมื่อวาน")
        elif days_old == 2:
            freshness_score = 18
            issues.append(f"ข้อมูลล่าสุดเมื่อ {days_old} วันที่แล้ว")
        elif days_old == 3:
            freshness_score = 12  # ลดจาก 20 → 12
            issues.append(f"ข้อมูลล่าสุดเมื่อ {days_old} วันที่แล้ว")
        elif days_old <= 5:
            freshness_score = 5
            issues.append(
                f"ข้อมูลเก่า {days_old} วัน — ควร Refresh ก่อนวิเคราะห์"
            )
        else:
            freshness_score = 0
            hard_cap        = "C"  # บังคับ Band ≤ C
            issues.append(
                f"ข้อมูลเก่ามาก {days_old} วัน — ไม่ควรใช้วิเคราะห์"
            )
    except Exception:
        issues.append("ไม่สามารถตรวจสอบความสดของข้อมูลได้")

    # --- Completeness ---
    completeness_score = 0
    missing_count      = 0

    if ind.get("sma200"):
        completeness_score += 20
    else:
        missing_count += 1
        issues.append("ไม่มี SMA200 — ข้อมูลน้อยกว่า 200 วัน")

    if ind.get("ema50"):
        completeness_score += 15
    else:
        missing_count += 1
        issues.append("ไม่มี EMA50")

    if ind.get("ema20") and ind.get("rsi") and ind.get("macd"):
        completeness_score += 10
    else:
        missing_count += 1
        issues.append("ขาด EMA20, RSI หรือ MACD")

    completeness_score = max(0, completeness_score - (missing_count * 5))
    raw_score          = freshness_score + completeness_score
    final_score        = min(raw_score, 50)

    return {
        "score":              final_score,
        "max":                50,
        "freshness_score":    freshness_score,
        "completeness_score": completeness_score,
        "days_old":           days_old,
        "hard_cap":           hard_cap,
        "issues":             issues,
        "explanation": (
            f"ข้อมูลอายุ {days_old} วัน (freshness={freshness_score}) | "
            f"indicator ครบ {5-missing_count}/5 ตัว"
        ),
        "audit": {
            "formula":     "freshness_score + completeness_score, cap=50",
            "freshness":   freshness_score,
            "completeness": completeness_score,
            "raw":         raw_score,
            "final":       final_score,
            "hard_cap":    hard_cap,
        }
    }


# =============================================================================
# มิติที่ 3: Regime Suitability (RS) — max 15 คะแนน
# =============================================================================

def compute_regime_suitability(df: pd.DataFrame, ind: dict) -> dict:
    score   = 0
    regime  = "ไม่ทราบ"
    explanation = ""

    try:
        recent      = df.tail(20)
        price_range = (
            (recent["high"].max() - recent["low"].min())
            / recent["close"].mean() * 100
        )
        ema20  = ind.get("ema20")
        ema50  = ind.get("ema50")
        close  = ind.get("close")
        ema_spread = (
            abs(ema20 - ema50) / close * 100
            if ema20 and ema50 and close else 0
        )

        if price_range >= 5.0 and ema_spread >= 2.0:
            score   = 15
            regime  = "Trending"
            explanation = (
                f"ตลาดมีแนวโน้มชัดเจน "
                f"(range={price_range:.1f}%, EMA spread={ema_spread:.1f}%) "
                f"— trend tools น่าเชื่อถือ"
            )
        elif price_range < 3.0 and ema_spread < 1.0:
            score   = 5
            regime  = "Ranging (Sideways)"
            explanation = (
                f"ตลาด Sideways "
                f"(range={price_range:.1f}%, EMA spread={ema_spread:.1f}%) "
                f"— EMA/MACD อาจให้สัญญาณหลอก"
            )
        else:
            score   = 10
            regime  = "Mixed"
            explanation = (
                f"ตลาดอยู่ในช่วงเปลี่ยนผ่าน "
                f"(range={price_range:.1f}%, EMA spread={ema_spread:.1f}%)"
            )
    except Exception as e:
        score       = 5
        regime      = "คำนวณไม่ได้"
        explanation = f"ไม่สามารถประเมิน regime: {e}"

    return {
        "score":       score,
        "max":         15,
        "regime":      regime,
        "explanation": explanation,
        "audit": {
            "formula": "price_range>=5 & ema_spread>=2 → 15, Sideways → 5",
            "final":   score,
        }
    }


# =============================================================================
# มิติที่ 4: Risk Context (RC) — max 10 คะแนน
# เข้มขึ้น: RSI > 65 trigger (ไม่ใช่ 70)
# =============================================================================

def compute_risk_context(ind: dict) -> dict:
    score    = 10
    warnings = []

    rsi    = ind.get("rsi")
    atr    = ind.get("atr")
    close  = ind.get("close")
    vol    = ind.get("volume")
    vol_ma = ind.get("volume_ma")
    ema20  = ind.get("ema20")

    # RSI extreme — threshold ลดจาก 70 → 65
    if rsi:
        if rsi > 70:
            score -= 5
            warnings.append(
                f"RSI = {rsi:.1f} (Overbought >70) — "
                "momentum อาจพลิกกลับ"
            )
        elif rsi > 65:
            score -= 3  # NEW: ใกล้ Overbought ก็หักแล้ว
            warnings.append(
                f"RSI = {rsi:.1f} (ใกล้ Overbought >65) — "
                "ระวัง momentum ชะลอ"
            )
        elif rsi < 30:
            score -= 5
            warnings.append(
                f"RSI = {rsi:.1f} (Oversold <30) — "
                "ราคาอาจ rebound แต่ไม่รับประกัน"
            )
        elif rsi < 35:
            score -= 3  # NEW: ใกล้ Oversold
            warnings.append(
                f"RSI = {rsi:.1f} (ใกล้ Oversold <35)"
            )

    # ATR สูงเกินไป
    if atr and close:
        atr_pct = (atr / close) * 100
        if atr_pct > 4.0:
            score -= 3
            warnings.append(
                f"ATR = {atr_pct:.1f}% ของราคา — "
                f"ความเสี่ยงสูง อาจแกว่ง ±{atr:.2f} บาท/วัน"
            )

    # Volume ต่ำ
    if vol and vol_ma and vol_ma > 0:
        ratio = vol / vol_ma
        if ratio < 0.5:
            score -= 2
            warnings.append(
                f"Volume ต่ำกว่าค่าเฉลี่ย {ratio:.1f}x — "
                "การเคลื่อนไหวอาจไม่มีน้ำหนัก"
            )

    # ราคาห่าง EMA20
    if close and ema20:
        gap_pct = abs(close - ema20) / ema20 * 100
        if gap_pct > 5.0:
            score -= 1
            warnings.append(
                f"ราคาห่าง EMA20 ถึง {gap_pct:.1f}% — "
                "อาจ mean-revert"
            )

    score = max(0, score)

    return {
        "score":       score,
        "max":         10,
        "warnings":    warnings,
        "explanation": (
            "ไม่พบความเสี่ยงพิเศษ" if not warnings
            else f"พบ {len(warnings)} ข้อควรระวัง"
        ),
        "audit": {
            "formula": "เริ่มที่ 10 หักตาม RSI/ATR/Volume/EMA gap",
            "final":   score,
            "warnings": warnings,
        }
    }


# =============================================================================
# มิติที่ 5: Sample Adequacy (SQ) — max 15 คะแนน
# =============================================================================

def compute_sample_adequacy(df: pd.DataFrame) -> dict:
    n = len(df)

    if n >= 200:
        score   = 15
        quality = "ดีมาก"
        note    = f"มีข้อมูล {n} วัน — เพียงพอสำหรับ indicator ทั้งหมด"
    elif n >= 50:
        score   = 10
        quality = "พอใช้"
        note    = f"มีข้อมูล {n} วัน — indicator ส่วนใหญ่ใช้ได้ แต่ไม่มี SMA200"
    elif n >= 26:
        score   = 5
        quality = "น้อย"
        note    = f"มีข้อมูล {n} วัน — เพียงพอแค่ MACD ขั้นต่ำ"
    else:
        score   = 0
        quality = "ไม่เพียงพอ"
        note    = f"มีข้อมูลเพียง {n} วัน — indicator ไม่น่าเชื่อถือ"

    return {
        "score":       score,
        "max":         15,
        "n_days":      n,
        "quality":     quality,
        "explanation": note,
        "audit": {
            "formula": ">=200→15, >=50→10, >=26→5, <26→0",
            "n_days":  n,
            "final":   score,
        }
    }


# =============================================================================
# GUARDRAILS v2 — เข้มขึ้น
# RSI > 65 trigger, SA < 50% trigger, data > 2 วัน trigger
# =============================================================================

def apply_guardrails(
    band:     str,
    ind:      dict,
    signals:  dict,
    dq:       dict,
    sa:       dict,
) -> dict:
    BAND_ORDER   = ["D", "C", "B", "A"]
    triggers     = []
    downgrade_by = 0

    rsi    = ind.get("rsi")
    vol    = ind.get("volume")
    vol_ma = ind.get("volume_ma")

    # 1. RSI > 65 (เข้มขึ้นจาก 70)
    if rsi and rsi > 65:
        triggers.append(
            f"RSI = {rsi:.1f} ใกล้/เกิน Overbought (threshold: 65)"
        )
        downgrade_by = max(downgrade_by, 1)

    # 2. RSI < 35
    if rsi and rsi < 35:
        triggers.append(
            f"RSI = {rsi:.1f} ใกล้/ต่ำกว่า Oversold (threshold: 35)"
        )
        downgrade_by = max(downgrade_by, 1)

    # 3. Signal Agreement ต่ำ
    if sa.get("agreement_pct", 100) < 50:
        triggers.append(
            f"Signal Agreement ต่ำกว่า 50% "
            f"({sa.get('agreement_pct',0):.1f}%)"
        )
        downgrade_by = max(downgrade_by, 1)

    # 4. ข้อมูลอายุ > 2 วัน (เข้มขึ้นจาก 5 วัน)
    days_old = dq.get("days_old", 0)
    if days_old > 2:
        triggers.append(
            f"ข้อมูลอายุ {days_old} วัน (threshold: >2 วัน)"
        )
        downgrade_by = max(downgrade_by, 1)

    # 5. Volume ต่ำมาก
    if vol and vol_ma and vol_ma > 0 and (vol / vol_ma) < 0.3:
        triggers.append("Volume ต่ำกว่าค่าเฉลี่ยมากกว่า 70%")
        downgrade_by = max(downgrade_by, 1)

    # 6. ไม่มี SMA200
    if not ind.get("sma200"):
        triggers.append("ไม่มี SMA200 — ข้อมูลไม่เพียงพอ")
        downgrade_by = max(downgrade_by, 1)

    # 7. MACD กับ RSI ขัดแย้ง
    macd_sig = signals.get("macd", {}).get("signal", "")
    rsi_sig  = signals.get("rsi",  {}).get("signal", "")
    if (("BULLISH" in macd_sig and "OVERBOUGHT" in rsi_sig) or
            ("BEARISH" in macd_sig and "OVERSOLD" in rsi_sig)):
        triggers.append("MACD และ RSI ส่งสัญญาณขัดแย้งกัน")
        downgrade_by = max(downgrade_by, 1)

    # Hard cap จาก DQ (ข้อมูลเก่ามาก)
    hard_cap = dq.get("hard_cap")

    # คำนวณ Band หลัง downgrade
    current_idx = BAND_ORDER.index(band) if band in BAND_ORDER else 0
    new_idx     = max(0, current_idx - downgrade_by)
    final_band  = BAND_ORDER[new_idx]

    # Apply hard cap
    if hard_cap and BAND_ORDER.index(final_band) > BAND_ORDER.index(hard_cap):
        final_band = hard_cap
        triggers.append(f"Hard cap: Band ≤ {hard_cap} เนื่องจากข้อมูลเก่า")

    return {
        "original_band": band,
        "final_band":    final_band,
        "downgraded":    final_band != band,
        "downgrade_by":  downgrade_by,
        "triggers":      triggers,
    }


# =============================================================================
# SANITY CHECKS v2
# =============================================================================

def run_sanity_checks(ind: dict, df: pd.DataFrame, signals: dict) -> list:
    warnings = []

    # 1. ข้อมูลน้อย
    if len(df) < 50:
        warnings.append({
            "level":   "สูง",
            "icon":    "🔴",
            "message": (
                f"ข้อมูลน้อยกว่า 50 วัน ({len(df)} วัน) — "
                "indicator อาจไม่เสถียร"
            )
        })

    # 2. RSI ใกล้ Overbought + Trend Bullish
    rsi_sig   = signals.get("rsi",   {}).get("signal", "")
    trend_sig = signals.get("trend", {}).get("signal", "")
    rsi       = ind.get("rsi", 50)

    if rsi > 65 and "BULLISH" in trend_sig:
        warnings.append({
            "level":   "กลาง",
            "icon":    "🟡",
            "message": (
                f"RSI = {rsi:.1f} ใกล้ Overbought แต่ Trend Bullish — "
                "momentum อาจชะลอในระยะสั้น"
            )
        })

    # 3. MACD กับ RSI ขัดแย้ง
    macd_sig = signals.get("macd", {}).get("signal", "")
    if (("BULLISH" in macd_sig and "OVERBOUGHT" in rsi_sig) or
            ("BEARISH" in macd_sig and "OVERSOLD" in rsi_sig)):
        warnings.append({
            "level":   "กลาง",
            "icon":    "🟡",
            "message": (
                f"MACD ({macd_sig}) และ RSI ({rsi_sig}) ขัดแย้ง — "
                "รอสัญญาณชัดเจนขึ้น"
            )
        })

    # 4. Volume ต่ำมาก
    vol    = ind.get("volume")
    vol_ma = ind.get("volume_ma")
    if vol and vol_ma and vol_ma > 0:
        ratio = vol / vol_ma
        if ratio < 0.3:
            warnings.append({
                "level":   "สูง",
                "icon":    "🔴",
                "message": (
                    f"Volume ต่ำกว่าค่าเฉลี่ย {ratio:.1f}x — "
                    "การเคลื่อนไหวอาจไม่สะท้อนแรงซื้อขายจริง"
                )
            })

    # 5. ราคาห่าง EMA20
    close = ind.get("close")
    ema20 = ind.get("ema20")
    if close and ema20:
        gap = abs(close - ema20) / ema20 * 100
        if gap > 7:
            warnings.append({
                "level":   "กลาง",
                "icon":    "🟡",
                "message": (
                    f"ราคาห่างจาก EMA20 ถึง {gap:.1f}% — "
                    "อาจเกิด Mean Reversion"
                )
            })

    # 6. ไม่มี SMA200
    if not ind.get("sma200"):
        warnings.append({
            "level":   "กลาง",
            "icon":    "🟡",
            "message": (
                "ไม่มี SMA200 — ไม่สามารถยืนยันแนวโน้มระยะยาวได้ "
                "กด Refresh เพื่อโหลดข้อมูล 365 วัน"
            )
        })

    return warnings


# =============================================================================
# HISTORICAL CONTEXT
# =============================================================================

def compute_historical_context(df: pd.DataFrame, signals: dict) -> dict:
    try:
        from analysis.indicators import compute_indicators
        df_full = compute_indicators(df.copy())
        rsi_sig = signals.get("rsi", {}).get("signal", "")

        if rsi_sig == "OVERSOLD":
            mask = df_full["rsi"] < 30
        elif rsi_sig == "OVERBOUGHT":
            mask = df_full["rsi"] > 70
        elif rsi_sig == "WATCH OVERSOLD":
            mask = (df_full["rsi"] >= 30) & (df_full["rsi"] < 40)
        elif rsi_sig == "WATCH OVERBOUGHT":
            mask = (df_full["rsi"] >= 60) & (df_full["rsi"] < 70)
        else:
            mask = (df_full["rsi"] >= 40) & (df_full["rsi"] <= 60)

        df_full["future_return"] = (
            df_full["close"].shift(-5) / df_full["close"] - 1
        )
        subset = df_full[mask]["future_return"].dropna()

        if len(subset) < 10:
            return {
                "available": False,
                "reason":    f"ข้อมูลน้อยเกินไป ({len(subset)} ครั้ง, ต้องการ ≥ 10)"
            }

        up_count   = int((subset > 0).sum())
        down_count = int((subset <= 0).sum())
        avg_return = round(subset.mean() * 100, 2)

        return {
            "available":   True,
            "rsi_zone":    rsi_sig,
            "sample":      len(subset),
            "up_count":    up_count,
            "down_count":  down_count,
            "avg_return":  avg_return,
            "note": (
                "⚠️ บริบทประวัติศาสตร์เท่านั้น "
                "ไม่ใช่การพยากรณ์ราคาในอนาคต"
            )
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}


# =============================================================================
# MASTER: compute_reliability v2
# Band thresholds เข้มขึ้น: A≥80, B≥60, C≥35, D<35
# =============================================================================

def compute_reliability(
    ind:     dict,
    df:      pd.DataFrame,
    signals: dict,
) -> dict:

    sa = compute_signal_agreement(signals)
    dq = compute_data_quality(ind, df)
    rs = compute_regime_suitability(df, ind)
    rc = compute_risk_context(ind)
    sq = compute_sample_adequacy(df)

    raw_total = sa["score"] + dq["score"] + rs["score"] + rc["score"] + sq["score"]

    # Apply Guardrails ก่อน เพื่อนำ triggers มาหักคะแนนด้วย
    # ต้อง apply guardrail ก่อนคำนวณ total จริง
    _guardrail_check = apply_guardrails(
        "A", ind, signals, dq, sa
    )
    guardrail_penalty = _guardrail_check["downgrade_by"] * 20

    total = max(0, min(raw_total - guardrail_penalty, 100))

    # Band thresholds เข้มขึ้น
    if total >= 80:
        band       = "A"
        band_th    = "สูง"
        band_color = "🟢"
        meaning    = "ข้อมูลครบ สัญญาณชัดเจน — เหมาะสำหรับประกอบการวิเคราะห์"
    elif total >= 60:
        band       = "B"
        band_th    = "ปานกลาง"
        band_color = "🟡"
        meaning    = "ข้อมูลพอใช้ มีบางสัญญาณขัดแย้ง — ใช้ด้วยความระมัดระวัง"
    elif total >= 35:
        band       = "C"
        band_th    = "ต่ำ"
        band_color = "🟠"
        meaning    = "ข้อมูลไม่ครบหรือสัญญาณขัดแย้งมาก — ใช้เป็นข้อมูลเบื้องต้นเท่านั้น"
    else:
        band       = "D"
        band_th    = "ต่ำมาก"
        band_color = "🔴"
        meaning    = "ข้อมูลไม่เพียงพอ — ไม่แนะนำให้วิเคราะห์จากข้อมูลชุดนี้"

# Band จาก total score ที่หัก penalty แล้ว — ไม่ downgrade ซ้ำ
    guardrail  = _guardrail_check
    guardrail["final_band"] = band  # ใช้ band จาก score ที่หักแล้ว
    guardrail["downgraded"] = band != guardrail["original_band"]
    final_band = band

    # อัปเดต band_th และ meaning ถ้า Band เปลี่ยน
    BAND_META = {
        "A": ("สูง",     "🟢", "ข้อมูลครบ สัญญาณชัดเจน"),
        "B": ("ปานกลาง", "🟡", "ข้อมูลพอใช้ ใช้ด้วยความระมัดระวัง"),
        "C": ("ต่ำ",     "🟠", "ข้อมูลไม่ครบ ใช้เป็นข้อมูลเบื้องต้นเท่านั้น"),
        "D": ("ต่ำมาก",  "🔴", "ข้อมูลไม่เพียงพอ ไม่แนะนำให้วิเคราะห์"),
    }
    band_th, band_color, meaning = BAND_META.get(
        final_band, BAND_META["D"]
    )

    # Sanity Checks
    sanity_warnings = run_sanity_checks(ind, df, signals)

    # Historical Context
    hist_context = compute_historical_context(df, signals)

    # Audit Trail
    audit_trail = {
        "signal_agreement": sa["audit"],
        "data_quality":     dq["audit"],
        "regime":           rs["audit"],
        "risk_context":     rc["audit"],
        "sample_adequacy":  sq["audit"],
        "band_before_guardrail": band,
        "band_after_guardrail":  final_band,
        "guardrail_triggers":    guardrail["triggers"],
        "raw_score":             raw_total,
        "guardrail_penalty":     guardrail_penalty,
        "total_score":           total,
        "band_thresholds":       "A≥80, B≥60, C≥35, D<35",
    }

    return {
        "total_score":        total,
        "band":               final_band,
        "band_th":            band_th,
        "band_color":         band_color,
        "meaning":            meaning,
        "dimensions": {
            "signal_agreement": sa,
            "data_quality":     dq,
            "regime":           rs,
            "risk_context":     rc,
            "sample_adequacy":  sq,
        },
        "guardrail":          guardrail,
        "sanity_warnings":    sanity_warnings,
        "historical_context": hist_context,
        "audit_trail":        audit_trail,
    }
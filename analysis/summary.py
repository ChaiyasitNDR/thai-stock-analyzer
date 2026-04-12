# analysis/summary.py

from datetime import datetime
from db.database import load_news

# =============================================================================
# ส่วนที่ 1: ข้อมูลจริง (Facts)
# =============================================================================

def build_facts_section(symbol: str, ind: dict) -> str:
    if not ind:
        return "## 📊 ข้อมูลจริง\n_ไม่มีข้อมูล indicator_\n"

    sma200_text = f"{ind['sma200']:.2f}" if ind.get("sma200") else "N/A (ข้อมูลไม่เพียงพอ)"
    macd_text   = f"{ind['macd']:.4f}"   if ind.get("macd")   else "N/A"
    sig_text    = f"{ind['macd_signal']:.4f}" if ind.get("macd_signal") else "N/A"
    hist_text   = f"{ind['macd_hist']:.4f}"   if ind.get("macd_hist")   else "N/A"
    atr_text    = f"{ind['atr']:.2f}"    if ind.get("atr")    else "N/A"
    vol_ma_text = f"{int(ind['volume_ma']):,}" if ind.get("volume_ma") else "N/A"

    return f"""## 📊 ส่วนที่ 1: ข้อมูลจริง (ค่าที่คำนวณได้)

| ตัวชี้วัด      | ค่า           |
|----------------|---------------|
| สัญลักษณ์      | {symbol}      |
| วันที่         | {ind.get('date', 'N/A')} |
| ราคาปิด        | {ind.get('close', 'N/A')} บาท |
| EMA 20         | {ind.get('ema20', 'N/A')} |
| EMA 50         | {ind.get('ema50', 'N/A')} |
| SMA 200        | {sma200_text} |
| RSI (14)       | {ind.get('rsi', 'N/A')} |
| MACD           | {macd_text}   |
| MACD Signal    | {sig_text}    |
| MACD Histogram | {hist_text}   |
| ATR (14)       | {atr_text}    |
| ปริมาณซื้อขาย | {int(ind['volume']):,} |
| Volume MA(20)  | {vol_ma_text} |
"""


# =============================================================================
# ส่วนที่ 2: การวิเคราะห์ตามกฎ (Interpretation)
# =============================================================================

def build_interpretation_section(signals: dict) -> str:
    trend      = signals.get("trend",      {})
    rsi        = signals.get("rsi",        {})
    macd       = signals.get("macd",       {})
    volume     = signals.get("volume",     {})
    volatility = signals.get("volatility", {})

    SIGNAL_TH = {
        "STRONG BULLISH":    "แนวโน้มขาขึ้นแข็งแกร่ง",
        "BULLISH":           "แนวโน้มขาขึ้น",
        "NEUTRAL":           "เป็นกลาง",
        "BEARISH":           "แนวโน้มขาลง",
        "STRONG BEARISH":    "แนวโน้มขาลงแข็งแกร่ง",
        "OVERSOLD":          "ขายมากเกินไป (โอกาส Rebound)",
        "WATCH OVERSOLD":    "เริ่มฟื้นตัวจากโซน Oversold",
        "OVERBOUGHT":        "ซื้อมากเกินไป (ระวัง Pullback)",
        "WATCH OVERBOUGHT":  "ใกล้โซน Overbought",
        "BULLISH MOMENTUM":  "โมเมนตัมขาขึ้น",
        "BEARISH MOMENTUM":  "โมเมนตัมขาลง",
        "HIGH VOLUME":       "ปริมาณซื้อขายสูง",
        "LOW VOLUME":        "ปริมาณซื้อขายต่ำ",
        "NORMAL VOLUME":     "ปริมาณซื้อขายปกติ",
        "HIGH VOLATILITY":   "ความผันผวนสูง",
        "NORMAL VOLATILITY": "ความผันผวนปกติ",
        "LOW VOLATILITY":    "ความผันผวนต่ำ",
        "INSUFFICIENT DATA": "ข้อมูลไม่เพียงพอ",
    }

    def th(sig):
        return SIGNAL_TH.get(sig, sig)

    lines = ["## 🔍 ส่วนที่ 2: การวิเคราะห์ตามกฎ\n"]

    lines.append("**แนวโน้ม (EMA/SMA)**")
    lines.append(f"- สัญญาณ: `{th(trend.get('signal',''))}`")
    lines.append(f"- เหตุผล: {trend.get('detail', 'N/A')}\n")

    lines.append("**โมเมนตัม (RSI)**")
    lines.append(f"- สัญญาณ: `{th(rsi.get('signal',''))}`")
    lines.append(f"- เหตุผล: {rsi.get('detail', 'N/A')}\n")

    lines.append("**โมเมนตัม (MACD)**")
    lines.append(f"- สัญญาณ: `{th(macd.get('signal',''))}`")
    lines.append(f"- เหตุผล: {macd.get('detail', 'N/A')}\n")

    lines.append("**ปริมาณซื้อขาย (Volume)**")
    lines.append(f"- สัญญาณ: `{th(volume.get('signal',''))}`")
    lines.append(f"- เหตุผล: {volume.get('detail', 'N/A')}\n")

    lines.append("**ความผันผวน (ATR)**")
    lines.append(f"- สัญญาณ: `{th(volatility.get('signal',''))}`")
    lines.append(f"- เหตุผล: {volatility.get('detail', 'N/A')}\n")

    return "\n".join(lines)


# =============================================================================
# ส่วนที่ 3: บริบทโลก และผลกระทบต่อไทย
# =============================================================================

def build_global_context_section(
    symbol: str,
    macro_impacts: list,
    recent_global_news: list
) -> str:
    lines = ["## 🌍 ส่วนที่ 3: บริบทตลาดโลก และผลกระทบต่อไทย\n"]

    DIRECTION_TH = {
        "positive": "เชิงบวก",
        "negative": "เชิงลบ",
        "mixed":    "ผสม",
    }

    if not macro_impacts:
        lines.append("_ไม่พบสัญญาณ Macro ที่ส่งผลกระทบต่อหุ้นนี้โดยตรง_\n")
    else:
        lines.append("**สัญญาณ Macro ที่กระทบต่อกลุ่มอุตสาหกรรมของหุ้นนี้:**\n")
        for impact in macro_impacts:
            icon = {"positive": "🟢", "negative": "🔴", "mixed": "🟡"}.get(
                impact["direction"], "⚪"
            )
            direction_th = DIRECTION_TH.get(impact["direction"], impact["direction"])
            lines.append(
                f"- {icon} **[{impact['macro_tag'].upper()}]** "
                f"ผลกระทบ{direction_th} — {impact['reason']}"
            )
        lines.append("")

    if recent_global_news:
        lines.append("**ข่าวตลาดโลกล่าสุด (จาก RSS):**\n")
        for i, news in enumerate(recent_global_news[:8], 1):
            tag = news.get("macro_tag", "")
            tag_text = f" `[{tag}]`" if tag else ""
            lines.append(f"{i}. {news.get('title', '')}{tag_text}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# ส่วนที่ 4: ความเสี่ยงและข้อควรระวัง
# =============================================================================

def build_risks_section(ind: dict, signals: dict, confidence: dict) -> str:
    lines = ["## ⚠️ ส่วนที่ 4: ความเสี่ยงและข้อควรระวัง\n"]
    risks = []

    if ind.get("sma200") is None:
        risks.append(
            "**ข้อมูลไม่สมบูรณ์**: ไม่สามารถคำนวณ SMA200 ได้ เนื่องจากมีข้อมูลน้อยกว่า 200 วัน "
            "ไม่สามารถยืนยันแนวโน้มระยะยาวได้"
        )

    conf_level = confidence.get("confidence", "LOW")
    bull = confidence.get("bullish_count", 0)
    bear = confidence.get("bearish_count", 0)

    if conf_level == "LOW":
        risks.append(
            "**ความเชื่อมั่นต่ำ**: สัญญาณยังไม่ชัดเจนหรือขัดแย้งกัน "
            "ไม่ควรตัดสินใจลงทุนโดยอิงจากการวิเคราะห์นี้เพียงอย่างเดียว"
        )
    elif bull > 0 and bear > 0:
        risks.append(
            f"**สัญญาณขัดแย้ง**: มี {bull} สัญญาณขาขึ้น และ {bear} สัญญาณขาลง "
            "ทิศทางตลาดยังไม่ชัดเจน"
        )

    rsi_signal = signals.get("rsi", {}).get("signal", "")
    if rsi_signal == "OVERBOUGHT":
        risks.append(
            "**RSI Overbought**: ราคาอาจขึ้นมาเร็วเกินไป "
            "มีความเสี่ยงที่จะเกิด Pullback ในระยะสั้น"
        )
    elif rsi_signal == "OVERSOLD":
        risks.append(
            "**RSI Oversold**: ราคาตกลงมามาก อาจเกิด Rebound "
            "แต่ไม่มีการรับประกันว่าจะฟื้นตัว"
        )

    vol_signal = signals.get("volatility", {}).get("signal", "")
    if vol_signal == "HIGH VOLATILITY":
        risks.append(
            "**ความผันผวนสูง**: ATR บ่งชี้ว่าราคาแกว่งตัวรุนแรง "
            "ความเสี่ยงในการถือหุ้นช่วงนี้สูงกว่าปกติ"
        )

    volume_signal = signals.get("volume", {}).get("signal", "")
    if volume_signal == "LOW VOLUME":
        risks.append(
            "**ปริมาณซื้อขายต่ำ**: การเคลื่อนไหวของราคาบน Volume ต่ำ "
            "อาจไม่สะท้อนแรงซื้อ/ขายที่แท้จริง"
        )

    if not risks:
        risks.append("ไม่พบ Flag ความเสี่ยงพิเศษในขณะนี้ แต่ความเสี่ยงตลาดทั่วไปยังคงมีอยู่เสมอ")

    for risk in risks:
        lines.append(f"- {risk}")

    lines.append("")
    return "\n".join(lines)


# =============================================================================
# ส่วนที่ 5: คำแนะนำเชิงกลยุทธ์ (Rule-Based)
# =============================================================================

def build_trading_recommendation_section(rec: dict) -> str:
    if not rec or "error" in rec:
        return "## 💡 ส่วนที่ 5: คำแนะนำเชิงกลยุทธ์\n_ข้อมูลไม่เพียงพอ_\n"

    lines = ["## 💡 ส่วนที่ 5: คำแนะนำเชิงกลยุทธ์ (Rule-Based)\n"]

    # ควรซื้อหรือขาย
    if rec["should_buy"]:
        action_icon = "🟢"
        action_text = "**แนะนำพิจารณาซื้อ** (สัญญาณส่วนใหญ่เป็นขาขึ้น)"
    elif rec["should_sell"]:
        action_icon = "🔴"
        action_text = "**แนะนำพิจารณาขาย** (สัญญาณส่วนใหญ่เป็นขาลง)"
    else:
        action_icon = "🟡"
        action_text = "**รอดูสถานการณ์** (สัญญาณยังไม่ชัดเจน)"

    lines.append(f"### {action_icon} ทิศทางแนะนำ: {action_text}\n")

    # ราคาปัจจุบันและ ATR
    lines.append(
        f"_ราคาปิดล่าสุด: **{rec['close']} บาท** | "
        f"ATR (ความผันผวนต่อวัน): **{rec['atr_used']} บาท**_\n"
    )

    # ราคาซื้อแบบขั้นบันได
    lines.append("### 📥 ราคาที่ควรตั้งซื้อ (เป็นขั้นบันได)")
    lines.append("_แต่ละขั้นใช้ ATR เป็นตัวกำหนดระยะห่าง — ซื้อแบบแบ่งพอร์ต_\n")
    lines.append("| ขั้น | ราคาซื้อ (บาท) | เหตุผล |")
    lines.append("|------|----------------|--------|")
    lines.append(f"| ขั้นที่ 1 | **{rec['buy_levels'][0]}** | ใกล้ราคาปัจจุบัน (-0.5 ATR) |")
    lines.append(f"| ขั้นที่ 2 | **{rec['buy_levels'][1]}** | ต่ำกว่า 1 ATR จากราคาปัจจุบัน |")
    lines.append(f"| ขั้นที่ 3 | **{rec['buy_levels'][2]}** | ต่ำกว่า 1.5 ATR (โซน Support) |")
    lines.append("")

    # ราคาขายแบบขั้นบันได
    lines.append("### 📤 ราคาที่ควรตั้งขาย (เป็นขั้นบันได)")
    lines.append("_ใช้ EMA เป็น Resistance หลัก + ATR เป็นระยะเป้าหมาย_\n")
    lines.append("| ขั้น | ราคาขาย (บาท) | เหตุผล |")
    lines.append("|------|----------------|--------|")
    lines.append(f"| ขั้นที่ 1 | **{rec['sell_levels'][0]}** | แนว EMA20 / +0.5 ATR |")
    lines.append(f"| ขั้นที่ 2 | **{rec['sell_levels'][1]}** | แนว EMA50 / +1.0 ATR |")
    lines.append(f"| ขั้นที่ 3 | **{rec['sell_levels'][2]}** | เป้าหมาย +2.0 ATR |")
    lines.append("")

    # Stop Loss
    lines.append("### 🛑 ราคา Stop Loss")
    lines.append(
        f"| Stop Loss | **{rec['stop_loss']} บาท** |"
        f" ต่ำกว่าราคาปัจจุบัน 1.5x ATR หรือต่ำกว่า EMA50 |"
    )
    lines.append("")

    # % ความเชื่อมั่น
    lines.append("### 📊 ความเชื่อมั่นในทิศทางราคา")
    lines.append("_คำนวณจากสัดส่วนสัญญาณขาขึ้น vs ขาลง — ไม่ใช่ความน่าจะเป็นทางสถิติ_\n")

    up_bar   = int(rec['up_pct'] / 10)
    down_bar = int(rec['down_pct'] / 10)

    lines.append(f"| ทิศทาง | % ความเชื่อมั่น | Indicator Bar |")
    lines.append(f"|--------|----------------|---------------|")
    lines.append(f"| 📈 ขาขึ้น | **{rec['up_pct']}%** | {'🟩' * up_bar}{'⬜' * (10 - up_bar)} |")
    lines.append(f"| 📉 ขาลง  | **{rec['down_pct']}%** | {'🟥' * down_bar}{'⬜' * (10 - down_bar)} |")
    lines.append("")

    return "\n".join(lines)


# =============================================================================
# ส่วนที่ 6: ข้อจำกัดความรับผิดชอบ
# =============================================================================

def build_disclaimer_section() -> str:
    return """## 📋 ส่วนที่ 6: ข้อจำกัดความรับผิดชอบ

> **การวิเคราะห์นี้จัดทำขึ้นเพื่อการศึกษาและประกอบการตัดสินใจเท่านั้น**
>
> - สัญญาณทั้งหมดมาจากกฎ rule-based ที่ชัดเจน ไม่ใช้ AI หรือ Machine Learning
> - **ไม่ใช่คำแนะนำการลงทุน** ห้ามใช้เป็นปัจจัยเดียวในการตัดสินใจซื้อขาย
> - ผลการวิเคราะห์ในอดีตไม่ได้รับประกันผลในอนาคต
> - ราคาแนะนำซื้อ/ขาย/Stop Loss คำนวณจากสูตร ATR — ไม่ใช่คำแนะนำจากผู้เชี่ยวชาญ
> - ควรปรึกษาผู้แนะนำการลงทุนที่ได้รับใบอนุญาตก่อนตัดสินใจลงทุนเสมอ
> - ผู้พัฒนาระบบนี้ไม่รับผิดชอบต่อความเสียหายใดๆ ที่เกิดจากการใช้งาน
"""


# =============================================================================
# MASTER SUMMARY BUILDER
# =============================================================================

def build_summary(
    symbol:        str,
    ind:           dict,
    signals:       dict,
    confidence:    dict,
    macro_impacts: list,
    rec:           dict = None,
) -> str:
    try:
        news_df = load_news(category="global", limit=10)
        recent_global_news = news_df.to_dict("records") if not news_df.empty else []
    except Exception:
        recent_global_news = []

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conf_level = confidence.get("confidence", "N/A")
    dominant   = confidence.get("dominant",   "N/A")

    CONF_TH = {"HIGH": "สูง", "MEDIUM": "ปานกลาง", "LOW": "ต่ำ"}
    DOM_TH  = {"BULLISH": "ขาขึ้น", "BEARISH": "ขาลง"}

    header = f"""# 📈 รายงานวิเคราะห์หุ้น: {symbol}
_สร้างเมื่อ: {now}_

**ความเชื่อมั่นโดยรวม: `{CONF_TH.get(conf_level, conf_level)}` | ทิศทาง: `{DOM_TH.get(dominant, dominant)}`**
_{confidence.get('detail', '')}_

---
"""

    facts      = build_facts_section(symbol, ind)
    interp     = build_interpretation_section(signals)
    global_ctx = build_global_context_section(symbol, macro_impacts, recent_global_news)
    risks      = build_risks_section(ind, signals, confidence)
    trading    = build_trading_recommendation_section(rec) if rec else ""
    disclaimer = build_disclaimer_section()

    return "\n".join([
        header,
        facts,       "---",
        interp,      "---",
        global_ctx,  "---",
        risks,       "---",
        trading,     "---",
        disclaimer,
    ])


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    from analysis.indicators import get_latest_indicators
    from analysis.signals import run_all_signals, compute_trading_recommendation

    symbol = "PTT.BK"
    ind    = get_latest_indicators(symbol)
    tags   = ["energy", "rates", "china"]
    result = run_all_signals(symbol, ind, tags)
    rec    = compute_trading_recommendation(ind, result["signals"], result["confidence"])

    summary = build_summary(
        symbol        = symbol,
        ind           = ind,
        signals       = result["signals"],
        confidence    = result["confidence"],
        macro_impacts = result["macro_impacts"],
        rec           = rec,
    )
    print(summary)
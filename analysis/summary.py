# analysis/summary.py
# Template-based summary — ภาษาไทย ไม่ใช้ LLM
# ทุกประโยคมาจากกฎที่อ่านได้ ไม่ใช่ความเห็น

from datetime import datetime
from db.database import load_news

# =============================================================================
# Model Card — แสดงตลอด ไม่ซ่อน
# =============================================================================

def build_model_card() -> str:
    return """## ℹ️ ระบบนี้คืออะไร? (Model Card)

> **Thai Stock Analyzer — Rule-Based Decision Support Tool**
>
> - ระบบนี้ใช้กฎ **rule-based** ที่กำหนดไว้ล่วงหน้า ไม่ใช้ AI หรือ Machine Learning
> - **ไม่ใช่คำแนะนำการลงทุน** — ผลลัพธ์ทุกอย่างเป็น "ข้อมูลประกอบการคิด" เท่านั้น
> - ความน่าเชื่อถือ (Reliability Band) วัดจากคุณภาพข้อมูลและความสอดคล้องของ indicator
>   **ไม่ใช่ความน่าจะเป็นทางสถิติ**
> - ราคาที่แสดงในช่วงวางแผน คำนวณจากสูตร ATR — เปลี่ยนทุกวันตามราคาตลาด
> - ควรปรึกษาผู้แนะนำการลงทุนที่ได้รับใบอนุญาตก่อนตัดสินใจลงทุนเสมอ
"""


# =============================================================================
# ส่วนที่ 1: Snapshot — ภาพรวมทันที
# =============================================================================

def build_snapshot_section(symbol: str, ind: dict, reliability: dict) -> str:
    if not ind:
        return "## 📌 ภาพรวม\n_ไม่มีข้อมูล_\n"

    band       = reliability.get("band", "D")
    band_th    = reliability.get("band_th", "ต่ำมาก")
    band_color = reliability.get("band_color", "🔴")
    meaning    = reliability.get("meaning", "")
    total      = reliability.get("total_score", 0)

    # ทิศทางที่ระบบตรวจพบ
    sa = reliability.get("dimensions", {}).get("signal_agreement", {})
    dominant_th = sa.get("dominant", "ไม่ชัดเจน")

    guardrail = reliability.get("guardrail", {})
    downgrade_text = ""
    if guardrail.get("downgraded"):
        triggers = guardrail.get("triggers", [])
        downgrade_text = (
            f"\n> ⬇️ **Band ถูกลดระดับอัตโนมัติ** จาก "
            f"{guardrail['original_band']} → {guardrail['final_band']} "
            f"เนื่องจาก: {', '.join(triggers)}"
        )

    return f"""## 📌 ส่วนที่ 1: ภาพรวม (Snapshot)

| รายการ | ค่า |
|--------|-----|
| หุ้น | **{symbol}** |
| ราคาปิดล่าสุด | **{ind.get('close', 'N/A')} บาท** |
| วันที่ข้อมูล | {ind.get('date', 'N/A')} |
| ระดับความน่าเชื่อถือ | {band_color} **Band {band} — {band_th}** ({total}/100) |
| ทิศทางที่ระบบตรวจพบ | ระบบเห็นสัญญาณ **{dominant_th}** เป็นหลัก |

> {meaning}{downgrade_text}

⚠️ _ทิศทางที่ระบบตรวจพบ ≠ การพยากรณ์ราคา และ ≠ คำแนะนำซื้อขาย_
"""


# =============================================================================
# ส่วนที่ 2: ข้อมูลจริง (Facts)
# =============================================================================

def build_facts_section(symbol: str, ind: dict, reliability: dict) -> str:
    if not ind:
        return "## 📊 ข้อมูลจริง\n_ไม่มีข้อมูล indicator_\n"

    dims = reliability.get("dimensions", {})
    sq   = dims.get("sample_adequacy", {})
    dq   = dims.get("data_quality", {})

    sma200_text = f"{ind['sma200']:.2f}"   if ind.get("sma200") else "N/A (ข้อมูลน้อยกว่า 200 วัน)"
    macd_text   = f"{ind['macd']:.4f}"     if ind.get("macd")   else "N/A"
    sig_text    = f"{ind['macd_signal']:.4f}" if ind.get("macd_signal") else "N/A"
    hist_text   = f"{ind['macd_hist']:.4f}"   if ind.get("macd_hist")   else "N/A"
    atr_text    = f"{ind['atr']:.2f}"      if ind.get("atr")    else "N/A"
    vol_ma_text = f"{int(ind['volume_ma']):,}" if ind.get("volume_ma") else "N/A"

    return f"""## 📊 ส่วนที่ 2: ข้อมูลจริง (สิ่งที่ระบบเห็น)

_ข้อมูลทั้งหมดนี้คำนวณจากราคาตลาดจริง ไม่มีการตีความหรือเพิ่มเติมความเห็น_

| ตัวชี้วัด | ค่า | หมายเหตุ |
|-----------|-----|---------|
| ราคาปิด | **{ind.get('close', 'N/A')} บาท** | ราคาปิดล่าสุด |
| EMA 20 | {ind.get('ema20', 'N/A')} | ค่าเฉลี่ยเคลื่อนที่ 20 วัน |
| EMA 50 | {ind.get('ema50', 'N/A')} | ค่าเฉลี่ยเคลื่อนที่ 50 วัน |
| SMA 200 | {sma200_text} | ค่าเฉลี่ยเคลื่อนที่ 200 วัน |
| RSI (14) | {ind.get('rsi', 'N/A')} | Momentum: 0-30=Oversold, 70-100=Overbought |
| MACD | {macd_text} | |
| MACD Signal | {sig_text} | |
| MACD Histogram | {hist_text} | บวก=momentum ขาขึ้น, ลบ=ขาลง |
| ATR (14) | {atr_text} บาท | ความผันผวนเฉลี่ยต่อวัน |
| Volume | {int(ind['volume']):,} | ปริมาณซื้อขายวันล่าสุด |
| Volume MA(20) | {vol_ma_text} | ค่าเฉลี่ย volume 20 วัน |

**คุณภาพข้อมูล:** {dq.get('explanation', 'N/A')} | **จำนวนข้อมูล:** {sq.get('explanation', 'N/A')}
"""


# =============================================================================
# ส่วนที่ 3: การตีความตามกฎ (Interpretation)
# =============================================================================

def build_interpretation_section(signals: dict, reliability: dict) -> str:
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
        "OVERSOLD":          "ขายมากเกินไป",
        "WATCH OVERSOLD":    "เริ่มฟื้นตัวจาก Oversold",
        "OVERBOUGHT":        "ซื้อมากเกินไป",
        "WATCH OVERBOUGHT":  "ใกล้โซน Overbought",
        "BULLISH MOMENTUM":  "Momentum ขาขึ้น",
        "BEARISH MOMENTUM":  "Momentum ขาลง",
        "HIGH VOLUME":       "ปริมาณซื้อขายสูงกว่าปกติ",
        "LOW VOLUME":        "ปริมาณซื้อขายต่ำกว่าปกติ",
        "NORMAL VOLUME":     "ปริมาณซื้อขายปกติ",
        "HIGH VOLATILITY":   "ความผันผวนสูง",
        "NORMAL VOLATILITY": "ความผันผวนปกติ",
        "LOW VOLATILITY":    "ความผันผวนต่ำ",
        "INSUFFICIENT DATA": "ข้อมูลไม่เพียงพอ",
    }

    def th(sig): return SIGNAL_TH.get(sig, sig)

    # Regime warning
    regime = reliability.get("dimensions", {}).get("regime", {})
    regime_warning = ""
    if regime.get("regime") == "Ranging (Sideways)":
        regime_warning = (
            "\n> ⚠️ **ตลาด Sideways** — EMA และ MACD อาจให้สัญญาณหลอกในภาวะนี้\n"
        )

    lines = [
        "## 🔍 ส่วนที่ 3: การตีความตามกฎ (สิ่งที่ indicator บอก)",
        "",
        "_ทุกการตีความมาจากกฎ if/else ที่กำหนดไว้ล่วงหน้า "
        "ไม่ใช่ความเห็นหรือการพยากรณ์_",
        regime_warning,
    ]

    for name, sig, name_th in [
        ("trend",      trend,      "แนวโน้ม (EMA/SMA)"),
        ("rsi",        rsi,        "Momentum (RSI)"),
        ("macd",       macd,       "Momentum (MACD)"),
        ("volume",     volume,     "ปริมาณซื้อขาย"),
        ("volatility", volatility, "ความผันผวน (ATR)"),
    ]:
        lines.append(f"**{name_th}**")
        lines.append(f"- ระบบตรวจพบ: `{th(sig.get('signal',''))}`")
        lines.append(f"- เหตุผล: {sig.get('detail', 'N/A')}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# ส่วนที่ 4: Reliability Band — รายละเอียด
# =============================================================================

def build_reliability_section(reliability: dict) -> str:
    dims  = reliability.get("dimensions", {})
    band  = reliability.get("band", "D")
    total = reliability.get("total_score", 0)
    color = reliability.get("band_color", "⚪")

    sa = dims.get("signal_agreement", {})
    dq = dims.get("data_quality", {})
    rs = dims.get("regime", {})
    rc = dims.get("risk_context", {})
    sq = dims.get("sample_adequacy", {})

    # Sanity warnings
    warnings = reliability.get("sanity_warnings", [])
    warning_text = ""
    if warnings:
        warning_text = "\n**⚠️ ข้อควรระวัง:**\n"
        for w in warnings:
            warning_text += f"- {w['icon']} [{w['level']}] {w['message']}\n"

    # Historical context
    hist = reliability.get("historical_context", {})
    hist_text = ""
    if hist.get("available"):
        hist_text = f"""
**📜 บริบทประวัติศาสตร์ (ไม่ใช่การพยากรณ์):**
- RSI Zone: {hist['rsi_zone']} | ตัวอย่างในอดีต: {hist['sample']} ครั้ง
- ราคาขึ้นใน 5 วัน: {hist['up_count']} ครั้ง | ลง: {hist['down_count']} ครั้ง
- ผลตอบแทนเฉลี่ย 5 วัน: {hist['avg_return']}%
- _{hist['note']}_
"""

    return f"""## 🎯 ส่วนที่ 4: ระดับความน่าเชื่อถือ (Reliability Band)

{color} **Band {band} — คะแนนรวม {total}/100**

| มิติ | คะแนน | คะแนนเต็ม | รายละเอียด |
|------|-------|-----------|-----------|
| Signal Agreement | {sa.get('score',0)} | {sa.get('max',0)} | {sa.get('explanation','')} |
| Data Quality | {dq.get('score',0)} | {dq.get('max',0)} | {dq.get('explanation','')} |
| Regime Suitability | {rs.get('score',0)} | {rs.get('max',0)} | {rs.get('explanation','')} |
| Risk Context | {rc.get('score',0)} | {rc.get('max',0)} | {rc.get('explanation','')} |
| Sample Adequacy | {sq.get('score',0)} | {sq.get('max',0)} | {sq.get('explanation','')} |

> **Band A** = ข้อมูลครบ สัญญาณชัด | **Band B** = พอใช้ ระวัง |
> **Band C** = ไม่ครบ ใช้เบื้องต้นเท่านั้น | **Band D** = ไม่เพียงพอ
{warning_text}{hist_text}"""


# =============================================================================
# ส่วนที่ 5: Decision Checklist
# =============================================================================

def build_decision_checklist(
    ind:     dict,
    signals: dict,
    rec:     dict,
) -> str:
    if not ind or not rec:
        return "## ✅ ส่วนที่ 5: Decision Checklist\n_ข้อมูลไม่เพียงพอ_\n"

    close = rec.get("close", 0)
    atr   = rec.get("atr_used", 0)
    ema20 = ind.get("ema20", 0)
    ema50 = ind.get("ema50", 0)

    # Scenario planning
    scenario_bull = f"ถ้าราคาปิดเหนือ EMA20 ({ema20}) → สัญญาณ Trend อาจเปลี่ยนเป็น Bullish"
    scenario_bear = f"ถ้าราคาปิดต่ำกว่า EMA50 ({ema50}) → สัญญาณ Trend อาจเปลี่ยนเป็น Bearish"
    invalidation  = rec.get("invalidation", "N/A")

    return f"""## ✅ ส่วนที่ 5: Decision Checklist

_รายการนี้ช่วยให้คิดอย่างเป็นระบบก่อนตัดสินใจ — ไม่ใช่คำสั่งซื้อขาย_

**ก่อนตัดสินใจ ควรตรวจสอบ:**
- [ ] แนวโน้มหลักสอดคล้องกับ timeframe ที่คุณลงทุนหรือไม่?
- [ ] Risk/Reward อยู่ในระดับที่รับได้หรือไม่?
- [ ] มีข่าวสำคัญที่อาจกระทบหุ้นนี้หรือไม่? (ดูส่วนข่าว)
- [ ] Reliability Band อยู่ในระดับที่คุณไว้ใจได้หรือไม่?
- [ ] มีสัญญาณ invalidation ชัดเจนหรือไม่?

**Scenario Planning:**
- 📈 {scenario_bull}
- 📉 {scenario_bear}

**แนว Invalidation:** ~{invalidation} บาท
_(ถ้าราคาต่ำกว่านี้ = thesis เสีย ควรทบทวนสถานะ)_
"""


# =============================================================================
# ส่วนที่ 6: Risk Controls — ATR Zones
# =============================================================================

#def build_risk_controls_section(rec: dict) -> str:
#    if not rec or "error" in rec:
#        return "## 🛡️ ส่วนที่ 6: Risk Controls\n_ข้อมูลไม่เพียงพอ_\n"
#
    # ทิศทางที่ระบบตรวจพบ
 #   if rec["system_sees_bullish"]:
 #       direction_text = "🟢 ระบบตรวจพบสัญญาณ **ขาขึ้น** เป็นหลัก"
 #   elif rec["system_sees_bearish"]:
 #       direction_text = "🔴 ระบบตรวจพบสัญญาณ **ขาลง** เป็นหลัก"
 #   else:
 #       direction_text = "🟡 ระบบ **ยังไม่เห็นทิศทางชัดเจน**"
#
 #   lines = [
  #      "## 🛡️ ส่วนที่ 6: Risk Controls & ช่วงราคาสำหรับวางแผน",
   #     "",
    #    f"{direction_text}",
     #   "",
      #  f"_ราคาปิดล่าสุด: **{rec['close']} บาท** | "
       # f"ATR (ความผันผวนเฉลี่ยต่อวัน): **{rec['atr_used']} บาท**_",
        #"",
#        "> ⚠️ **ช่วงราคาด้านล่างคือ 'ช่วงสำหรับวางแผน' เท่านั้น**",
 #       "> คำนวณจากสูตร ATR — เปลี่ยนทุกวันตามราคาตลาด",
  #      "> **ไม่ใช่ราคาเป้าหมาย ไม่ใช่คำแนะนำซื้อขาย**",
   #     "",
    #    "### 📥 ช่วงราคาพิจารณาซื้อ (แบ่งเป็น 3 ระดับ)",
     #   "_แนวคิด: แบ่งซื้อเป็น lot ตามระดับราคา ไม่ใส่ทั้งหมดในครั้งเดียว_",
      #  "",
#        "| ระดับ | ช่วงราคา (บาท) | สูตรคำนวณ |",
 #       "|-------|---------------|-----------|",
  #      f"| ระดับที่ 1 | ~{rec['buy_zones'][0]} | ราคาปิด − 0.5×ATR |",
   #     f"| ระดับที่ 2 | ~{rec['buy_zones'][1]} | ราคาปิด − 1.0×ATR |",
    #    f"| ระดับที่ 3 | ~{rec['buy_zones'][2]} | ราคาปิด − 1.5×ATR |",
     #   "",
      #  "### 📤 ช่วงราคาพิจารณาขาย (แบ่งเป็น 3 ระดับ)",
       # "_แนวคิด: ทยอยขายเป็น lot ที่แนว EMA และ ATR target_",
 #       "",
  #      "| ระดับ | ช่วงราคา (บาท) | สูตรคำนวณ |",
   #     "|-------|---------------|-----------|",
    #    f"| ระดับที่ 1 | ~{rec['sell_zones'][0]} | แนว EMA20 หรือ +0.5×ATR |",
     #   f"| ระดับที่ 2 | ~{rec['sell_zones'][1]} | แนว EMA50 หรือ +1.0×ATR |",
      #  f"| ระดับที่ 3 | ~{rec['sell_zones'][2]} | +2.0×ATR จากราคาปิด |",
       # "",
#        "### 🛑 แนว Invalidation",
 #       f"| แนว Invalidation | ~**{rec['invalidation']} บาท** |",
  #      f"| สูตร | ต่ำกว่า min(ราคาปิด − 1.5×ATR, EMA50 − 0.5×ATR) |",
   #     "",
    #    "_ถ้าราคาปิดต่ำกว่าแนว Invalidation = สมมติฐานการวิเคราะห์อาจเสีย "
     #   "ควรทบทวนสถานะ ไม่ใช่ stop loss อัตโนมัติ_",
      #  "",
       # "### 📊 สัดส่วนสัญญาณ (ไม่ใช่ความน่าจะเป็น)",
#        "_คำนวณจากจำนวน indicator ที่เห็นตรงกัน "
 #       "ไม่ใช่ probability ทางสถิติ_",
  #      "",
   #     "| ทิศทาง | สัดส่วนสัญญาณ |",
    #    "|--------|--------------|",
     #   f"| 📈 สัญญาณขาขึ้น | {rec['up_pct']}% ของสัญญาณที่ชัดเจน |",
      #  f"| 📉 สัญญาณขาลง | {rec['down_pct']}% ของสัญญาณที่ชัดเจน |",
#    ]
#
 #   return "\n".join(lines)

def build_risk_controls_section(rec: dict, horizon: str = "medium") -> str:
    """
    แสดงช่วงราคาสำหรับวางแผน ปรับตาม horizon
    ที่เลือก — ไม่ใช่คำแนะนำซื้อขาย
    """
    if not rec or "error" in rec:
        return "## 🛡️ ส่วนที่ 6: Risk Controls\n_ข้อมูลไม่เพียงพอ_\n"

    from config.settings import HORIZON_CONFIG
    cfg   = HORIZON_CONFIG.get(horizon, HORIZON_CONFIG["medium"])
    close = rec.get("close", 0)
    atr   = rec.get("atr_used", 0)
    ema20 = rec.get("sell_zones", [0])[0]
    ema50 = rec.get("sell_zones", [0, 0])[1]

    # คำนวณ zones ใหม่ตาม horizon multiplier
    bm = cfg["atr_buy_mult"]
    sm = cfg["atr_sell_mult"]
    im = cfg["atr_invalid_mult"]

    buy_zones = [
        round(close - (atr * bm[0]), 2),
        round(close - (atr * bm[1]), 2),
        round(close - (atr * bm[2]), 2),
    ]
    sell_zones = [
        round(close + (atr * sm[0]), 2),
        round(close + (atr * sm[1]), 2),
        round(close + (atr * sm[2]), 2),
    ]
    invalidation = round(close - (atr * im), 2)

    # ทิศทางที่ระบบตรวจพบ
    if rec.get("system_sees_bullish"):
        direction_text = "🟢 ระบบตรวจพบสัญญาณ **ขาขึ้น** เป็นหลัก"
    elif rec.get("system_sees_bearish"):
        direction_text = "🔴 ระบบตรวจพบสัญญาณ **ขาลง** เป็นหลัก"
    else:
        direction_text = "🟡 ระบบ **ยังไม่เห็นทิศทางชัดเจน**"

    lines = [
        "## 🛡️ ส่วนที่ 6: Risk Controls & ช่วงราคาสำหรับวางแผน",
        "",
        f"**ระยะเวลาที่เลือก:** {cfg['label']}",
        f"_{cfg['indicator_note']}_",
        "",
        f"{direction_text}",
        "",
        f"> 💡 **แนวทาง ({cfg['label']}):** {cfg['guidance']}",
        "",
        f"> ⚠️ **ความเสี่ยง:** {cfg['risk_note']}",
        "",
        f"_ราคาปิดล่าสุด: **{close} บาท** | "
        f"ATR (ความผันผวนเฉลี่ยต่อวัน): **{atr} บาท**_",
        "",
        "> ⚠️ **ช่วงราคาด้านล่างคือ 'ช่วงสำหรับวางแผน' เท่านั้น**",
        "> คำนวณจากสูตร ATR × multiplier ตามระยะที่เลือก",
        "> **ไม่ใช่ราคาเป้าหมาย ไม่ใช่คำแนะนำซื้อขาย**",
        "",
        "### 📥 ช่วงราคาพิจารณาซื้อ",
        "_แบ่งเป็น 3 ระดับ — แนวคิดแบ่งซื้อเป็น lot ไม่ใส่ทั้งหมดครั้งเดียว_",
        "",
        "| ระดับ | ช่วงราคา (บาท) | สูตร |",
        "|-------|---------------|------|",
        f"| ระดับที่ 1 | ~{buy_zones[0]} | ปิด − {bm[0]}×ATR |",
        f"| ระดับที่ 2 | ~{buy_zones[1]} | ปิด − {bm[1]}×ATR |",
        f"| ระดับที่ 3 | ~{buy_zones[2]} | ปิด − {bm[2]}×ATR |",
        "",
        "### 📤 ช่วงราคาพิจารณาขาย",
        "_ทยอยขายเป็น lot — ไม่ใช่ target price_",
        "",
        "| ระดับ | ช่วงราคา (บาท) | สูตร |",
        "|-------|---------------|------|",
        f"| ระดับที่ 1 | ~{sell_zones[0]} | ปิด + {sm[0]}×ATR |",
        f"| ระดับที่ 2 | ~{sell_zones[1]} | ปิด + {sm[1]}×ATR |",
        f"| ระดับที่ 3 | ~{sell_zones[2]} | ปิด + {sm[2]}×ATR |",
        "",
        "### 🛑 แนว Invalidation",
        f"| แนว Invalidation | ~**{invalidation} บาท** | ปิด − {im}×ATR |",
        "",
        "_ถ้าราคาปิดต่ำกว่านี้ = thesis อาจเสีย ควรทบทวนสถานะ_",
        "",
        "### 📊 สัดส่วนสัญญาณ (ไม่ใช่ความน่าจะเป็น)",
        "",
        "| ทิศทาง | สัดส่วนสัญญาณ |",
        "|--------|--------------|",
        f"| 📈 สัญญาณขาขึ้น | {rec.get('up_pct', 0)}% |",
        f"| 📉 สัญญาณขาลง  | {rec.get('down_pct', 0)}% |",
        "",
        "_คำนวณจากจำนวน indicator ที่เห็นตรงกัน ไม่ใช่ probability_",
    ]

    return "\n".join(lines)
# =============================================================================
# ส่วนที่ 7: Global Context
# =============================================================================

def build_global_context_section(
    symbol:        str,
    macro_impacts: list,
    recent_global_news: list,
) -> str:
    lines = [
        "## 🌍 ส่วนที่ 7: บริบทตลาดโลก",
        "",
        "_ข่าวด้านล่างมาจาก RSS feed โดยตรง "
        "ระบบไม่ได้วิเคราะห์หรือสรุปเนื้อหา_",
        "",
    ]

    DIRECTION_TH = {
        "positive": "เชิงบวกต่อกลุ่มนี้",
        "negative": "เชิงลบต่อกลุ่มนี้",
        "mixed":    "ผลกระทบผสม",
    }

    if macro_impacts:
        lines.append("**Macro Tags ที่อาจกระทบกลุ่มอุตสาหกรรมของหุ้นนี้:**\n")
        for impact in macro_impacts:
            icon = {"positive": "🟢", "negative": "🔴", "mixed": "🟡"}.get(
                impact["direction"], "⚪"
            )
            direction_th = DIRECTION_TH.get(impact["direction"], impact["direction"])
            lines.append(
                f"- {icon} **[{impact['macro_tag'].upper()}]** "
                f"{direction_th} — {impact['reason']}"
            )
        lines.append("")

    if recent_global_news:
        lines.append("**ข่าวตลาดโลกล่าสุด:**\n")
        for i, news in enumerate(recent_global_news[:8], 1):
            tag      = news.get("macro_tag", "")
            tag_text = f" `[{tag}]`" if tag else " `[ทั่วไป]`"
            lines.append(f"{i}. {news.get('title', '')}{tag_text}")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# ส่วนที่ 8: ความเสี่ยงและข้อควรระวัง
# =============================================================================

def build_risks_section(ind: dict, signals: dict, reliability: dict) -> str:
    lines  = ["## ⚠️ ส่วนที่ 8: ความเสี่ยงและข้อควรระวัง\n"]
    risks  = []
    dims   = reliability.get("dimensions", {})
    dq     = dims.get("data_quality", {})

    # ข้อมูลไม่ครบ
    for issue in dq.get("issues", []):
        risks.append(f"**ข้อมูล:** {issue}")

    # Sanity warnings จาก reliability
    for w in reliability.get("sanity_warnings", []):
        risks.append(f"{w['icon']} **[{w['level']}]** {w['message']}")

    # Guardrail triggers
    guardrail = reliability.get("guardrail", {})
    for trigger in guardrail.get("triggers", []):
        risks.append(f"🔽 **Auto-Downgrade:** {trigger}")

    if not risks:
        risks.append("ไม่พบ Flag ความเสี่ยงพิเศษในขณะนี้ "
                     "แต่ความเสี่ยงตลาดทั่วไปยังคงมีอยู่เสมอ")

    for risk in risks:
        lines.append(f"- {risk}")

    lines.append("")
    return "\n".join(lines)


# =============================================================================
# ส่วนที่ 9: Disclaimer
# =============================================================================

def build_disclaimer_section() -> str:
    return """## 📋 ส่วนที่ 9: ข้อจำกัดความรับผิดชอบ

> **การวิเคราะห์นี้จัดทำขึ้นเพื่อการศึกษาและประกอบการตัดสินใจเท่านั้น**
>
> - สัญญาณทั้งหมดมาจากกฎ rule-based ที่ชัดเจน ไม่ใช้ AI หรือ Machine Learning
> - **ไม่ใช่คำแนะนำการลงทุน** ห้ามใช้เป็นปัจจัยเดียวในการตัดสินใจ
> - Reliability Band ไม่ใช่ความน่าจะเป็นทางสถิติ
> - ช่วงราคาสำหรับวางแผนคำนวณจาก ATR — เปลี่ยนทุกวัน
> - ผู้พัฒนาไม่รับผิดชอบต่อความเสียหายใดๆ จากการใช้งาน
> - ควรปรึกษาผู้แนะนำการลงทุนที่ได้รับใบอนุญาตก่อนตัดสินใจเสมอ
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
    reliability:   dict = None,
) -> str:

    try:
        news_df = load_news(category="global", limit=10)
        recent_global_news = (
            news_df.to_dict("records") if not news_df.empty else []
        )
    except Exception:
        recent_global_news = []

    if reliability is None:
        reliability = {}

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = f"""# 📈 รายงานวิเคราะห์หุ้น: {symbol}
_สร้างเมื่อ: {now}_

---
"""

    model_card  = build_model_card()
    snapshot    = build_snapshot_section(symbol, ind, reliability)
    facts       = build_facts_section(symbol, ind, reliability)
    interp      = build_interpretation_section(signals, reliability)
    rel_section = build_reliability_section(reliability)
    checklist   = build_decision_checklist(ind, signals, rec) if rec else ""
    risk_ctrl   = build_risk_controls_section(rec) if rec else ""
    global_ctx  = build_global_context_section(
        symbol, macro_impacts, recent_global_news
    )
    risks       = build_risks_section(ind, signals, reliability)
    disclaimer  = build_disclaimer_section()

    return "\n".join([
        header,
        model_card,   "---",
        snapshot,     "---",
        facts,        "---",
        interp,       "---",
        rel_section,  "---",
        checklist,    "---",
        risk_ctrl,    "---",
        global_ctx,   "---",
        risks,        "---",
        disclaimer,
    ])


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    from analysis.indicators import get_latest_indicators, compute_indicators
    from analysis.signals import run_all_signals, compute_trading_recommendation
    from analysis.reliability import compute_reliability
    from db.database import load_prices

    symbol = "PTT.BK"
    df     = load_prices(symbol)
    ind    = get_latest_indicators(symbol)
    result = run_all_signals(symbol, ind, ["energy", "rates"])
    rec    = compute_trading_recommendation(
        ind, result["signals"], result["confidence"]
    )
    rel    = compute_reliability(ind, df, result["signals"])

    summary = build_summary(
        symbol        = symbol,
        ind           = ind,
        signals       = result["signals"],
        confidence    = result["confidence"],
        macro_impacts = result["macro_impacts"],
        rec           = rec,
        reliability   = rel,
    )
    print(summary)
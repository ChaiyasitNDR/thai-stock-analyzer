# app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from db.database import (
    init_db, load_news, get_last_updated,
    save_preference, load_preference
)
from collectors.price_collector import get_prices_for_display, collect_prices
from collectors.news_collector import collect_all_news
from analysis.indicators import compute_indicators, get_latest_indicators
from analysis.signals import run_all_signals, compute_trading_recommendation
from analysis.summary import build_summary
from analysis.reliability import compute_reliability
from config.settings import THAI_STOCKS, DEFAULT_STOCK, HORIZON_CONFIG

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Thai Stock Analyzer",
    page_icon="📈",
    layout="wide",
)

# Mobile-friendly CSS
st.markdown("""
    <style>
        @media (max-width: 768px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
        }
        .band-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 1.1em;
        }
        .band-a { background-color: #1a7a1a; color: white; }
        .band-b { background-color: #b8860b; color: white; }
        .band-c { background-color: #cc5500; color: white; }
        .band-d { background-color: #8b0000; color: white; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# INIT DATABASE
# =============================================================================

init_db()

# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("📈 Thai Stock Analyzer")
st.sidebar.markdown("_SET Market | Rule-Based Analysis_")
st.sidebar.markdown("---")

# Stock selector — จำหุ้นล่าสุดที่ดู
last_symbol = load_preference("last_symbol", default=DEFAULT_STOCK)
if last_symbol in THAI_STOCKS:
    default_index = THAI_STOCKS.index(last_symbol)
else:
    default_index = THAI_STOCKS.index(DEFAULT_STOCK)

st.sidebar.markdown("### เลือกหุ้น")

custom_symbol = st.sidebar.text_input(
    "พิมพ์ชื่อหุ้น (เช่น MINT.BK)",
    value="" if last_symbol in THAI_STOCKS else last_symbol,
    placeholder="เช่น MINT.BK, BEM.BK",
)

if custom_symbol.strip():
    symbol = custom_symbol.strip().upper()
    st.sidebar.success(f"ใช้หุ้น: {symbol}")
else:
    symbol = st.sidebar.selectbox(
        "หรือเลือกจากรายการ",
        options=THAI_STOCKS,
        index=default_index,
    )

save_preference("last_symbol", symbol)

# Date range
st.sidebar.markdown("### ช่วงเวลา")
end_date_default   = datetime.today()
start_date_default = end_date_default - timedelta(days=365)
start_date = st.sidebar.date_input("วันเริ่มต้น", value=start_date_default)
end_date   = st.sidebar.date_input("วันสิ้นสุด",  value=end_date_default)

# Indicator toggles
st.sidebar.markdown("### แสดง Indicator บน Chart")
show_ema20  = st.sidebar.checkbox("EMA 20",  value=True)
show_ema50  = st.sidebar.checkbox("EMA 50",  value=True)
show_sma200 = st.sidebar.checkbox("SMA 200", value=True)

st.sidebar.markdown("---")

# Horizon Selector
st.sidebar.markdown("### ⏱️ ระยะเวลาการลงทุน")
st.sidebar.caption(
    "เลือกระยะที่คุณสนใจ — "
    "ระบบจะปรับช่วงราคาวางแผนให้เหมาะสม"
)

horizon = st.sidebar.radio(
    "ระยะเวลา",
    options=["short", "medium", "long"],
    format_func=lambda x: HORIZON_CONFIG[x]["label"],
    index=1,  # default = medium
)

# แสดง guidance ตาม horizon
with st.sidebar.expander("ℹ️ ระยะนี้เน้นอะไร?"):
    cfg = HORIZON_CONFIG[horizon]
    st.caption(cfg["indicator_note"])
    st.caption(cfg["guidance"])
    st.warning(cfg["risk_note"])

st.sidebar.caption(
    "⚠️ การเลือกระยะปรับการแสดงผลเท่านั้น "
    "ไม่ใช่คำแนะนำให้ลงทุนในระยะนั้น"
)

st.sidebar.markdown("---")

# Data collection
st.sidebar.markdown("### ดึงข้อมูล")

if st.sidebar.button("🔄 Refresh ราคาหุ้น"):
    with st.spinner(f"กำลังดึงข้อมูล {symbol}..."):
        collect_prices(symbol, days=365)
    st.success("อัปเดตราคาหุ้นแล้ว!")
    st.cache_data.clear()

if st.sidebar.button("📰 Refresh ข่าว"):
    with st.spinner("กำลังดึงข่าว..."):
        collect_all_news()
    st.success("อัปเดตข่าวแล้ว!")

last_updated = get_last_updated(symbol)
st.sidebar.markdown("---")
st.sidebar.caption(f"ข้อมูลล่าสุด: {last_updated}")

# =============================================================================
# LOAD DATA
# =============================================================================

@st.cache_data(ttl=300)
def load_chart_data(sym, start, end):
    df = get_prices_for_display(
        sym,
        start_date=str(start),
        end_date=str(end),
    )
    if df.empty:
        return df
    return compute_indicators(df)

df = load_chart_data(symbol, start_date, end_date)

# =============================================================================
# MAIN TITLE
# =============================================================================

st.title(f"📈 {symbol} — Thai Stock Analysis")
st.caption(f"วันที่วิเคราะห์: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if df.empty:
    st.warning(
        f"ไม่พบข้อมูลราคาของ **{symbol}** "
        "กรุณากด **🔄 Refresh ราคาหุ้น** ใน Sidebar"
    )
    st.stop()

# =============================================================================
# COMPUTE ALL SIGNALS & RELIABILITY
# =============================================================================

ind = get_latest_indicators(symbol)

try:
    global_news_df    = load_news(category="global", limit=30)
    recent_macro_tags = (
        global_news_df["macro_tag"].dropna().unique().tolist()
        if not global_news_df.empty else []
    )
except Exception:
    recent_macro_tags = []

result = run_all_signals(symbol, ind, recent_macro_tags) if ind else {}
rec    = compute_trading_recommendation(
    ind, result.get("signals", {}), result.get("confidence", {})
) if ind else {}

from db.database import load_prices as _load_prices
df_full = _load_prices(symbol)
rel     = compute_reliability(
    ind, df_full, result.get("signals", {})
) if ind and not df_full.empty else {}

# =============================================================================
# PANEL 1: SNAPSHOT — ภาพรวมทันที
# =============================================================================

st.markdown("---")
st.subheader("📌 ภาพรวม (Snapshot)")

if ind and rel:
    band       = rel.get("band", "D")
    band_th    = rel.get("band_th", "ต่ำมาก")
    band_color = rel.get("band_color", "🔴")
    total      = rel.get("total_score", 0)
    meaning    = rel.get("meaning", "")

    BAND_CSS = {"A": "band-a", "B": "band-b", "C": "band-c", "D": "band-d"}
    band_css = BAND_CSS.get(band, "band-d")

    sa       = rel.get("dimensions", {}).get("signal_agreement", {})
    dominant = sa.get("dominant", "ไม่ชัดเจน")

    snap_col1, snap_col2, snap_col3 = st.columns(3)

    with snap_col1:
        if len(df) >= 2:
            prev_close = df.iloc[-2]["close"]
            curr_close = df.iloc[-1]["close"]
            price_chg  = curr_close - prev_close
            price_pct  = (price_chg / prev_close) * 100
        else:
            curr_close = df.iloc[-1]["close"]
            price_chg  = price_pct = 0

        st.metric(
            "ราคาปิดล่าสุด",
            f"{curr_close:.2f} บาท",
            f"{price_chg:+.2f} ({price_pct:+.1f}%)",
        )

    with snap_col2:
        st.markdown(
            f"**ระดับความน่าเชื่อถือ**  \n"
            f"<span class='band-badge {band_css}'>"
            f"Band {band} — {band_th} ({total}/100)"
            f"</span>",
            unsafe_allow_html=True,
        )
        st.caption(meaning)

    with snap_col3:
        dir_icon = "📈" if dominant == "ขาขึ้น" else "📉" if dominant == "ขาลง" else "➡️"
        st.markdown(f"**ระบบตรวจพบสัญญาณ**  \n{dir_icon} **{dominant}** เป็นหลัก")
        st.caption("≠ การพยากรณ์ราคา และ ≠ คำแนะนำซื้อขาย")

    # Guardrail warning
    guardrail = rel.get("guardrail", {})
    if guardrail.get("downgraded"):
        triggers = guardrail.get("triggers", [])
        st.warning(
            f"⬇️ **Band ถูกลดระดับอัตโนมัติ** "
            f"จาก {guardrail['original_band']} → {guardrail['final_band']}  \n"
            + "  \n".join([f"- {t}" for t in triggers])
        )

    # Sanity warnings
    sanity = rel.get("sanity_warnings", [])
    if sanity:
        with st.expander(f"⚠️ พบ {len(sanity)} ข้อควรระวัง — คลิกเพื่อดู"):
            for w in sanity:
                st.markdown(f"{w['icon']} **[{w['level']}]** {w['message']}")

# =============================================================================
# PANEL 2: METRICS ROW
# =============================================================================

if ind:
    st.markdown("---")
    col1, col2 = st.columns(2)
    col3, col4, col5 = st.columns(3)

    col1.metric("EMA 20", f"{ind['ema20']:.2f}" if ind.get("ema20") else "N/A")
    col2.metric("EMA 50", f"{ind['ema50']:.2f}" if ind.get("ema50") else "N/A")
    col3.metric("RSI (14)", f"{ind['rsi']:.1f}" if ind.get("rsi") else "N/A")
    col4.metric("ATR (14)", f"{ind['atr']:.2f}" if ind.get("atr") else "N/A")
    col5.metric(
        "SMA 200",
        f"{ind['sma200']:.2f}" if ind.get("sma200") else "N/A"
    )

# =============================================================================
# PANEL 3: CHART
# =============================================================================

st.markdown("---")
st.subheader("📊 Price Chart")

fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.55, 0.25, 0.20],
    subplot_titles=["ราคา + Indicators", "RSI (14)", "MACD"],
)

# Candlestick
fig.add_trace(
    go.Candlestick(
        x=df["date"],
        open=df["open"], high=df["high"],
        low=df["low"],   close=df["close"],
        name="ราคา",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ),
    row=1, col=1,
)

if show_ema20 and "ema20" in df.columns:
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["ema20"],
        name="EMA 20", line=dict(color="#ff9800", width=1.5),
    ), row=1, col=1)

if show_ema50 and "ema50" in df.columns:
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["ema50"],
        name="EMA 50", line=dict(color="#2196f3", width=1.5),
    ), row=1, col=1)

if show_sma200 and "sma200" in df.columns:
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["sma200"],
        name="SMA 200", line=dict(color="#9c27b0", width=1.5, dash="dash"),
    ), row=1, col=1)

# RSI
if "rsi" in df.columns:
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["rsi"],
        name="RSI", line=dict(color="#ff9800", width=1.5),
    ), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red",   opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
    fig.add_hline(y=50, line_dash="dot",  line_color="gray",  opacity=0.3, row=2, col=1)

# MACD
if "macd" in df.columns and "macd_signal" in df.columns:
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["macd"],
        name="MACD", line=dict(color="#2196f3", width=1.5),
    ), row=3, col=1)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["macd_signal"],
        name="Signal", line=dict(color="#ff9800", width=1.5),
    ), row=3, col=1)
    if "macd_hist" in df.columns:
        colors = ["#26a69a" if v >= 0 else "#ef5350"
                  for v in df["macd_hist"].fillna(0)]
        fig.add_trace(go.Bar(
            x=df["date"], y=df["macd_hist"],
            name="Histogram", marker_color=colors, opacity=0.6,
        ), row=3, col=1)

fig.update_layout(
    height=700,
    xaxis_rangeslider_visible=False,
    plot_bgcolor="#0e1117",
    paper_bgcolor="#0e1117",
    font_color="#fafafa",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    margin=dict(l=40, r=40, t=40, b=40),
)
fig.update_xaxes(gridcolor="#1e2130")
fig.update_yaxes(gridcolor="#1e2130")
st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# PANEL 4: VOLUME
# =============================================================================

st.subheader("📦 Volume")
vol_fig = go.Figure()
vol_colors = [
    "#26a69a" if df["close"].iloc[i] >= df["open"].iloc[i] else "#ef5350"
    for i in range(len(df))
]
vol_fig.add_trace(go.Bar(
    x=df["date"], y=df["volume"],
    name="Volume", marker_color=vol_colors, opacity=0.8,
))
if "volume_ma" in df.columns:
    vol_fig.add_trace(go.Scatter(
        x=df["date"], y=df["volume_ma"],
        name="Volume MA(20)", line=dict(color="#ff9800", width=1.5),
    ))
vol_fig.update_layout(
    height=200,
    plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
    font_color="#fafafa",
    margin=dict(l=40, r=40, t=20, b=40),
)
vol_fig.update_xaxes(gridcolor="#1e2130")
vol_fig.update_yaxes(gridcolor="#1e2130")
st.plotly_chart(vol_fig, use_container_width=True)

# =============================================================================
# PANEL 5: NEWS
# =============================================================================

st.markdown("---")
st.subheader("📰 ข่าวสาร")

from analysis.news_ranker import process_news_for_display
from config.settings import STOCK_SECTOR

# โหลดข่าวทั้งหมด
try:
    th_news_df  = load_news(category="thailand", limit=30)
    gl_news_df  = load_news(category="global",   limit=30)
    th_news_all = th_news_df.to_dict("records") if not th_news_df.empty else []
    gl_news_all = gl_news_df.to_dict("records") if not gl_news_df.empty else []
except Exception:
    th_news_all = []
    gl_news_all = []

# ดึง sector
sector = STOCK_SECTOR.get(symbol, None)

# Process ข่าวไทย
th_processed = process_news_for_display(
    th_news_all, symbol, sector,
    relevance_threshold=25, n_clusters=3
)

# Process ข่าวโลก
gl_processed = process_news_for_display(
    gl_news_all, symbol, sector,
    relevance_threshold=15, n_clusters=4
)

# --- Tabs ---
tab_rel, tab_th, tab_gl = st.tabs([
    f"⭐ เกี่ยวข้อง ({th_processed['stats']['relevant_count'] + gl_processed['stats']['relevant_count']})",
    f"🇹🇭 ข่าวไทย ({th_processed['stats']['total']})",
    f"🌍 ข่าวโลก ({gl_processed['stats']['total']})",
])

# --- Tab: ข่าวเกี่ยวข้อง ---
with tab_rel:
    st.caption(
        f"ข่าวที่เกี่ยวข้องกับ **{symbol}** "
        f"โดยตรง — เรียงตาม relevance score"
    )

    all_relevant = (
        th_processed["relevant"] +
        gl_processed["relevant"]
    )
    all_relevant = sorted(
        all_relevant,
        key=lambda x: x.get("relevance_score", 0),
        reverse=True
    )

    if not all_relevant:
        st.info(
            f"ไม่พบข่าวที่เกี่ยวข้องกับ {symbol} โดยตรง  \n"
            "ลองกด 📰 Refresh ข่าว หรือดูข่าวทั่วไปใน tab อื่น"
        )
    else:
        for item in all_relevant[:10]:
            score  = item.get("relevance_score", 0)
            reason = item.get("relevance_reason", "")
            tag    = item.get("macro_tag", "")
            source = item.get("source", "")

            # Badge สี
            if score >= 60:
                score_badge = "🔴 สำคัญ"
            elif score >= 30:
                score_badge = "🟡 เกี่ยวข้อง"
            else:
                score_badge = "🟢 อาจเกี่ยวข้อง"

            st.markdown(f"**{item.get('title','')}**")

            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.caption(f"_{source}_")
            with col_b:
                badge_text = score_badge
                if tag:
                    badge_text += f" | `{tag}`"
                st.caption(badge_text)

            if reason and reason != "ไม่เกี่ยวข้องโดยตรง":
                st.caption(f"เหตุผล: {reason}")

            with st.expander("ดูลิงก์และเวลา"):
                st.write(f"🔗 {item.get('url', '')}")
                st.write(f"🕐 {str(item.get('published_at',''))[:16]}")

            st.markdown("---")

# --- Tab: ข่าวไทย ---
with tab_th:
    if not th_news_all:
        st.info("ยังไม่มีข่าวไทย กด 📰 Refresh ข่าว ใน Sidebar")
    else:
        # แสดง relevant ก่อน
        if th_processed["relevant"]:
            st.markdown("#### ⭐ ข่าวที่เกี่ยวข้อง")
            for item in th_processed["relevant"]:
                st.markdown(f"**{item.get('title','')}**")
                st.caption(
                    f"_{item.get('source','')}_ | "
                    f"relevance: {item.get('relevance_score',0)}"
                )
                with st.expander("ดูลิงก์"):
                    st.write(f"🔗 {item.get('url','')}")
                    st.write(f"🕐 {str(item.get('published_at',''))[:16]}")
                st.markdown("---")

        # แสดง clusters
        if th_processed["clusters"]:
            st.markdown("#### 📋 ข่าวทั่วไป (จัดกลุ่มแล้ว)")
            for summary in th_processed["clusters"]:
                if not summary:
                    continue
                count    = summary.get("count", 0)
                rep      = summary.get("representative", "")
                keywords = summary.get("keywords", [])
                sources  = summary.get("sources", [])

                label = f"📦 {rep[:60]}{'...' if len(rep)>60 else ''} (+{count-1} ข่าวคล้ายกัน)"
                with st.expander(label):
                    if keywords:
                        st.caption(f"keywords: {', '.join(keywords)}")
                    st.caption(f"sources: {', '.join(sources)}")
                    st.markdown("---")
                    for sub in summary.get("items", []):
                        st.markdown(
                            f"- {sub.get('title','')}  \n"
                            f"  _{sub.get('source','')} — "
                            f"{str(sub.get('published_at',''))[:16]}_"
                        )

# --- Tab: ข่าวโลก ---
with tab_gl:
    if not gl_news_all:
        st.info("ยังไม่มีข่าวโลก กด 📰 Refresh ข่าว ใน Sidebar")
    else:
        # แสดง relevant ก่อน
        if gl_processed["relevant"]:
            st.markdown("#### ⭐ ข่าวที่อาจกระทบ")
            for item in gl_processed["relevant"]:
                tag = item.get("macro_tag", "")
                st.markdown(f"**{item.get('title','')}**")
                st.caption(
                    f"_{item.get('source','')}_ "
                    + (f"| `{tag}`" if tag else "")
                )
                with st.expander("ดูลิงก์"):
                    st.write(f"🔗 {item.get('url','')}")
                    st.write(f"🕐 {str(item.get('published_at',''))[:16]}")
                st.markdown("---")

        # แสดง clusters ข่าวโลก
        if gl_processed["clusters"]:
            st.markdown("#### 📋 ข่าวทั่วไป (จัดกลุ่มแล้ว)")
            for summary in gl_processed["clusters"]:
                if not summary:
                    continue
                count    = summary.get("count", 0)
                rep      = summary.get("representative", "")
                keywords = summary.get("keywords", [])
                tags     = summary.get("macro_tags", [])

                label = f"📦 {rep[:60]}{'...' if len(rep)>60 else ''} (+{count-1} ข่าวคล้ายกัน)"
                with st.expander(label):
                    if keywords:
                        st.caption(f"keywords: {', '.join(keywords)}")
                    if tags:
                        st.caption(
                            f"macro tags: {', '.join(str(t) for t in tags if t and isinstance(t, str))}"
                        )
                    st.markdown("---")
                    for sub in summary.get("items", []):
                        tag = sub.get("macro_tag", "")
                        st.markdown(
                            f"- {sub.get('title','')} "
                            + (f"`{tag}`" if tag else "") +
                            f"  \n  _{sub.get('source','')} — "
                            f"{str(sub.get('published_at',''))[:16]}_"
                        )
            st.markdown("---")

# =============================================================================
# PANEL 6: ANALYSIS SUMMARY — 9 Tabs
# =============================================================================

st.markdown("---")
st.subheader("🧠 รายงานวิเคราะห์ (Rule-Based)")

if not ind:
    st.warning(
        "ข้อมูลไม่เพียงพอสำหรับการวิเคราะห์  \n"
        "กด **🔄 Refresh ราคาหุ้น** เพื่อดึงข้อมูลอย่างน้อย 60 วัน"
    )
else:
    # Signal breakdown table
    SIGNAL_TH = {
        "STRONG BULLISH":    "แนวโน้มขาขึ้นแข็งแกร่ง",
        "BULLISH":           "แนวโน้มขาขึ้น",
        "NEUTRAL":           "เป็นกลาง",
        "BEARISH":           "แนวโน้มขาลง",
        "STRONG BEARISH":    "แนวโน้มขาลงแข็งแกร่ง",
        "OVERSOLD":          "ขายมากเกินไป",
        "WATCH OVERSOLD":    "เริ่มฟื้นจาก Oversold",
        "OVERBOUGHT":        "ซื้อมากเกินไป",
        "WATCH OVERBOUGHT":  "ใกล้โซน Overbought",
        "BULLISH MOMENTUM":  "Momentum ขาขึ้น",
        "BEARISH MOMENTUM":  "Momentum ขาลง",
        "HIGH VOLUME":       "ปริมาณสูง",
        "LOW VOLUME":        "ปริมาณต่ำ",
        "NORMAL VOLUME":     "ปริมาณปกติ",
        "HIGH VOLATILITY":   "ผันผวนสูง",
        "NORMAL VOLATILITY": "ผันผวนปกติ",
        "LOW VOLATILITY":    "ผันผวนต่ำ",
        "INSUFFICIENT DATA": "ข้อมูลไม่เพียงพอ",
    }
    NAME_TH = {
        "trend":      "แนวโน้ม (EMA/SMA)",
        "rsi":        "Momentum (RSI)",
        "macd":       "Momentum (MACD)",
        "volume":     "ปริมาณซื้อขาย",
        "volatility": "ความผันผวน (ATR)",
    }


    cfg_h = HORIZON_CONFIG[horizon]
    signal_rows = []
    for name, sig in result.get("signals", {}).items():
        raw_sig = sig.get("signal", "")

        # เพิ่ม tag ตาม horizon
        if name in cfg_h["emphasize"]:
            emphasis = "⭐ เน้น"
        elif name in cfg_h["de_emphasize"]:
            emphasis = "🔅 ลดความสำคัญ"
        else:
            emphasis = "—"

        signal_rows.append({
            "ตัวชี้วัด":       NAME_TH.get(name, name),
            "สัญญาณ":          SIGNAL_TH.get(raw_sig, raw_sig),
            f"น้ำหนัก ({cfg_h['label'][:6]})": emphasis,
            "รายละเอียด":     sig.get("detail", ""),
        })

    st.dataframe(
        pd.DataFrame(signal_rows),
        use_container_width=True,
        hide_index=True,
    )

    # 9 Tabs
    (
        tab1, tab2, tab3,
        tab4, tab5, tab6,
        tab7, tab8, tab9
    ) = st.tabs([
        "ℹ️ Model Card",
        "📌 Snapshot",
        "📊 ข้อมูลจริง",
        "🔍 การตีความ",
        "🎯 Reliability",
        "✅ Checklist",
        "🛡️ Risk Controls",
        "🌍 บริบทโลก",
        "⚠️ ความเสี่ยง",
    ])

    from analysis.summary import (
        build_model_card,
        build_snapshot_section,
        build_facts_section,
        build_interpretation_section,
        build_reliability_section,
        build_decision_checklist,
        build_risk_controls_section,
        build_global_context_section,
        build_risks_section,
    )

    macro_impacts = result.get("macro_impacts", [])

    with tab1:
        st.markdown(build_model_card())

    with tab2:
        st.markdown(build_snapshot_section(symbol, ind, rel))

    with tab3:
        st.markdown(build_facts_section(symbol, ind, rel))

    with tab4:
        st.markdown(build_interpretation_section(
            result.get("signals", {}), rel
        ))

    with tab5:
        st.markdown(build_reliability_section(rel))
# Validation Panel
        st.markdown("---")
        st.markdown("### 📊 ประสิทธิภาพสัญญาณในอดีต (Walk-Forward)")

        from analysis.validation import (
            run_validation, save_validation_results,
            load_validation_results
        )

        val_results = load_validation_results(symbol)

        col_v1, col_v2 = st.columns([3, 1])
        with col_v2:
            if st.button("🔄 คำนวณ Validation ใหม่"):
                with st.spinner("กำลังคำนวณ..."):
                    val_results = run_validation(df_full, symbol)
                    if val_results.get("available"):
                        save_validation_results(symbol, val_results)
                        st.success("คำนวณเสร็จแล้ว!")
                    else:
                        st.error(val_results.get("reason", ""))

        if not val_results.get("available"):
            st.info(
                f"ℹ️ {val_results.get('reason', 'ยังไม่มีข้อมูล')}  \n"
                "กดปุ่ม **🔄 คำนวณ Validation ใหม่** เพื่อเริ่มต้น"
            )
        else:
            st.caption(
                f"คำนวณเมื่อ: {val_results.get('computed_at','')} | "
                f"ข้อมูล: {val_results.get('n_days',0)} วัน"
            )

            # Regime distribution
            regime_dist = val_results.get("regime_dist", {})
            if regime_dist:
                total_days = sum(regime_dist.values())
                r_cols = st.columns(len(regime_dist))
                for i, (regime, count) in enumerate(regime_dist.items()):
                    pct = count / total_days * 100
                    r_cols[i].metric(
                        f"Regime: {regime}",
                        f"{count} วัน",
                        f"{pct:.0f}%"
                    )

            st.markdown("---")

            # Signal Decay Chart
            st.markdown("---")
            # --- Hit Rate Table ปรับปรุงใหม่ ---
            st.markdown("#### Hit Rate ต่อ Signal (horizon = 5 วัน)")
            st.caption(
                "⚠️ ตัวเลขจากอดีตเท่านั้น ไม่ใช่การพยากรณ์ | "
                "Hit Rate = % ครั้งที่ราคาไปทิศที่สัญญาณคาด | "
                "Avg Hit = ผลตอบแทนเฉลี่ยเฉพาะครั้งที่ถูก | "
                "Avg Miss = เฉพาะครั้งที่ผิด"
            )

            SIGNAL_NAME_TH = {
                "sig_trend_BULLISH":        "Trend: Bullish ↑",
                "sig_trend_BEARISH":        "Trend: Bearish ↓",
                "sig_trend_STRONG_BULLISH": "Trend: Strong Bullish ↑↑",
                "sig_rsi_OVERSOLD":         "RSI: Oversold ↑",
                "sig_rsi_OVERBOUGHT":       "RSI: Overbought ↓",
                "sig_macd_BULLISH":         "MACD: Bullish ↑",
                "sig_macd_BEARISH":         "MACD: Bearish ↓",
            }

            val_rows = []
           # --- คำนิยาม metric (แสดงก่อนตาราง) ---
            with st.expander("📖 คำนิยาม metric ทั้งหมด"):
                st.markdown("""
| Metric | ความหมาย |
|--------|---------|
| **Hit Rate** | % ครั้งที่ราคาไปทิศที่สัญญาณคาด |
| **Hit (Trend)** | % ครั้งที่ราคาไปทิศที่สัญญาณคาด ในช่วงตลาดขาขึ้น|
| **Hit (Range)** | % ครั้งที่ราคาไปทิศที่สัญญาณคาด ในช่วงตลาดSideway|
| **Avg(ถูก)** | ผลตอบแทนเฉลี่ยเฉพาะครั้งที่ทำนายถูก |
| **Avg(ผิด)** | ผลตอบแทนเฉลี่ยเฉพาะครั้งที่ทำนายผิด |
| **Profit Factor** | กำไรรวม ÷ ขาดทุนรวม (>1 = คุ้มค่า, ∞ = ไม่มีขาดทุนเลย) |
| **Expectancy** | ผลตอบแทนเฉลี่ยต่อสัญญาณในระยะยาว (บวก = ดี) |
| **vs Baseline** | เปรียบกับ "ไม่ใช้สัญญาณ" — ถ้าบวก = สัญญาณช่วยเพิ่มมูลค่า |
""")

# แสดง Regime Distribution ให้รู้ว่า Ranging มีกี่วัน
            regime_dist = val_results.get("regime_dist", {})
            if regime_dist:
                total = sum(regime_dist.values())
                rd_cols = st.columns(len(regime_dist))
                for i, (regime, count) in enumerate(regime_dist.items()):
                    pct = count / total * 100
                    rd_cols[i].metric(
                        regime,
                        f"{count} วัน ({pct:.0f}%)"
                    )
                if regime_dist.get("Ranging", 0) < 10:
                    st.caption(
                        f"⚠️ Ranging มีเพียง {regime_dist.get('Ranging',0)} วัน "
                        "— Hit(Range) จึงแสดง N/A เพราะข้อมูลไม่เพียงพอ"
                    )

            # --- Accuracy Table ---
            st.markdown("**📐 Signal Accuracy**")
            acc_rows = []
            for key, val in val_results.get("signals", {}).items():
                overall  = val.get("overall",  {})
                trending = val.get("trending", {})
                ranging  = val.get("ranging",  {})
                if not overall.get("available"):
                    continue
                hr = overall.get("hit_rate", 0)
                hr_icon = "🟢" if hr >= 55 else ("🟡" if hr >= 40 else "🔴")
                acc_rows.append({
                    "สัญญาณ":       SIGNAL_NAME_TH.get(key, key),
                    "Hit Rate":     f"{hr_icon} {hr:.0f}%",
                    "Hit(Trend)":   f"{trending.get('hit_rate',0):.0f}%" if trending.get("available") else "N/A",
                    "Hit(Range)": (
                        f"{ranging.get('hit_rate',0):.0f}%"
                        if ranging.get("available")
                        else "N/A (Ranging น้อย)"
                    ),
                    "n (ครั้ง)":    overall.get("sample_size", 0),
                })
            if acc_rows:
                st.dataframe(pd.DataFrame(acc_rows),
                             use_container_width=True, hide_index=True)

            st.markdown("---")

            # --- Profitability Table ---
            st.markdown("**💰 Signal Profitability**")
            prof_rows = []
            for key, val in val_results.get("signals", {}).items():
                overall = val.get("overall", {})
                if not overall.get("available"):
                    continue
                pf_display = overall.get("profit_factor_display", "N/A")
                pf_val     = overall.get("profit_factor")
                pf_icon = (
                    "🟢" if pf_val and pf_val >= 1.0 else
                    "🔴" if pf_val is not None else "⚪"
                )
                exp = overall.get("expectancy", 0)
                prof_rows.append({
                    "สัญญาณ":        SIGNAL_NAME_TH.get(key, key),
                    "Avg(ทั้งหมด)":  f"{overall.get('avg_return',0):+.2f}%",
                    "Avg(ถูก)":      f"{overall.get('avg_return_hit',0):+.2f}%",
                    "Avg(ผิด)":      f"{overall.get('avg_return_miss',0):+.2f}%",
                    "Profit Factor": f"{pf_icon} {pf_display}",
                    "Expectancy":    f"{exp:+.3f}%",
                    "vs Baseline":   overall.get("baseline_label", "N/A"),
                    "💡 Hint":       overall.get("hint", ""),
                })
            if prof_rows:
                st.dataframe(pd.DataFrame(prof_rows),
                             use_container_width=True, hide_index=True)

            # --- Signal Decay Chart (สีขาว) ---
            st.markdown("---")
            st.markdown("#### 📉 Signal Decay — hit rate เปลี่ยนตาม horizon")
            st.caption(
                "เส้นสูงกว่า 50% = สัญญาณนั้นดีกว่าสุ่ม | "
                "ถ้าเส้นลงเมื่อ horizon ยาวขึ้น = สัญญาณใช้ได้แค่ระยะสั้น"
            )

            decay_fig = go.Figure()

            COLORS = {
                "sig_trend_BULLISH":        "#00e676",
                "sig_trend_BEARISH":        "#ff5252",
                "sig_trend_STRONG_BULLISH": "#ffd600",
                "sig_rsi_OVERSOLD":         "#40c4ff",
                "sig_rsi_OVERBOUGHT":       "#ff6d00",
                "sig_macd_BULLISH":         "#e040fb",
                "sig_macd_BEARISH":         "#ffab40",
            }

            has_data = False
            for key, decay_list in val_results.get("decay", {}).items():
                x_vals, y_vals = [], []
                for pt in decay_list:
                    if pt.get("available"):
                        x_vals.append(pt["horizon"])
                        y_vals.append(pt["hit_rate"])

                if len(x_vals) >= 2:
                    has_data = True
                    decay_fig.add_trace(go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        name=SIGNAL_NAME_TH.get(key, key),
                        mode="lines+markers",
                        line=dict(color=COLORS.get(key, "#ffffff"), width=2),
                        marker=dict(size=8),
                    ))

            if has_data:
                decay_fig.add_hline(
                    y=50,
                    line_dash="dash",
                    line_color="#ffffff",
                    opacity=0.6,
                    annotation_text="50% (เทียบเท่าสุ่ม)",
                    annotation_font_color="#ffffff",
                    annotation_font_size=12,
                )
                decay_fig.update_layout(
                    height=400,
                    plot_bgcolor="#1a1a2e",
                    paper_bgcolor="#1a1a2e",
                    font=dict(color="#ffffff", size=13),  # ✅ ตัวหนังสือขาว
                    xaxis=dict(
                        title=dict(
                            text="Horizon (วัน)",
                            font=dict(color="#ffffff", size=14)
                        ),
                        tickvals=[1, 3, 5, 10],
                        tickfont=dict(color="#ffffff", size=13),
                        gridcolor="#333355",
                        linecolor="#ffffff",
                    ),
                    yaxis=dict(
                        title=dict(
                            text="Hit Rate (%)",
                            font=dict(color="#ffffff", size=14)
                        ),
                        range=[0, 100],
                        tickfont=dict(color="#ffffff", size=13),
                        gridcolor="#333355",
                        linecolor="#ffffff",
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        font=dict(color="#ffffff", size=12),
                        bgcolor="rgba(0,0,0,0)",
                    ),
                    margin=dict(l=50, r=30, t=60, b=50),
                )
                st.plotly_chart(decay_fig, use_container_width=True)
            else:
                st.info("ข้อมูลไม่เพียงพอสำหรับ Signal Decay Chart")

    with tab6:
        st.markdown(build_decision_checklist(
            ind, result.get("signals", {}), rec
        ))


    with tab7:
        # แสดง horizon ที่เลือกอยู่
        cfg = HORIZON_CONFIG[horizon]
        st.info(
            f"⏱️ **ระยะเวลาที่เลือก:** {cfg['label']}  \n"
            f"_{cfg['indicator_note']}_"
        )
        st.markdown(build_risk_controls_section(rec, horizon=horizon))

    with tab8:
        try:
            gl_news_df   = load_news(category="global", limit=8)
            global_news  = gl_news_df.to_dict("records") if not gl_news_df.empty else []
        except Exception:
            global_news = []
        st.markdown(build_global_context_section(
            symbol, macro_impacts, global_news
        ))

    with tab9:
        st.markdown(build_risks_section(
            ind, result.get("signals", {}), rel
        ))

    # Full report expander
    st.markdown("---")
    with st.expander("📄 ดูรายงานฉบับเต็ม (ทุกส่วนรวมกัน)"):
        full_summary = build_summary(
            symbol        = symbol,
            ind           = ind,
            signals       = result.get("signals", {}),
            confidence    = result.get("confidence", {}),
            macro_impacts = macro_impacts,
            rec           = rec,
            reliability   = rel,
        )
        st.markdown(full_summary)
        st.download_button(
            label="⬇️ ดาวน์โหลดรายงาน (.md)",
            data=full_summary,
            file_name=f"{symbol}_report_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown",
        )
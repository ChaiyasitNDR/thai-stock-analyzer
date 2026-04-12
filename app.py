# app.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from db.database import init_db, load_news, get_last_updated, save_preference, load_preference
from collectors.price_collector import get_prices_for_display, collect_prices
from collectors.news_collector import collect_all_news
from analysis.indicators import compute_indicators, get_latest_indicators
from analysis.signals import run_all_signals, compute_trading_recommendation
from analysis.summary import build_summary
from config.settings import THAI_STOCKS, DEFAULT_STOCK, MACRO_KEYWORDS

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Thai Stock Analyzer",
    page_icon="📈",
    layout="wide",
)
# ตรวจสอบขนาดหน้าจอ — ปรับ layout อัตโนมัติ
st.markdown("""
    <style>
        /* ปรับ sidebar บนมือถือ */
        @media (max-width: 768px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            /* ตัวอักษรใน metric ใหญ่ขึ้น */
            [data-testid="metric-container"] {
                width: 100%;
            }
        }
    </style>
""", unsafe_allow_html=True)
# =============================================================================
# INIT DATABASE ON FIRST RUN
# =============================================================================

init_db()

# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("📈 Thai Stock Analyzer")
st.sidebar.markdown("_SET Market | Rule-Based Analysis_")
st.sidebar.markdown("---")

# โหลดหุ้นล่าสุดที่ดู
last_symbol = load_preference("last_symbol", default=DEFAULT_STOCK)

# ถ้าหุ้นล่าสุดอยู่ใน list ให้ใช้ index นั้น
if last_symbol in THAI_STOCKS:
    default_index = THAI_STOCKS.index(last_symbol)
else:
    default_index = THAI_STOCKS.index(DEFAULT_STOCK)

# Stock selector
st.sidebar.markdown("### Stock Selection")

custom_symbol = st.sidebar.text_input(
    "Type custom ticker (e.g. AOT.BK)",
    value="" if last_symbol in THAI_STOCKS else last_symbol,
    placeholder="e.g. MINT.BK, BEM.BK",
)

if custom_symbol.strip():
    symbol = custom_symbol.strip().upper()
    st.sidebar.success(f"Using custom ticker: {symbol}")
else:
    symbol = st.sidebar.selectbox(
        "Or select from list",
        options=THAI_STOCKS,
        index=default_index,
    )

# บันทึกหุ้นที่เลือกล่าสุดทุกครั้งที่เปลี่ยน
save_preference("last_symbol", symbol)

# Date range
st.sidebar.markdown("### Date Range")
end_date_default   = datetime.today()
start_date_default = end_date_default - timedelta(days=365)

start_date = st.sidebar.date_input("Start Date", value=start_date_default)
end_date   = st.sidebar.date_input("End Date",   value=end_date_default)

# Indicator toggles
st.sidebar.markdown("### Chart Overlays")
show_ema20  = st.sidebar.checkbox("EMA 20",  value=True)
show_ema50  = st.sidebar.checkbox("EMA 50",  value=True)
show_sma200 = st.sidebar.checkbox("SMA 200", value=True)

st.sidebar.markdown("---")

# Data collection buttons
st.sidebar.markdown("### Data Collection")

if st.sidebar.button("🔄 Refresh Price Data"):
    with st.spinner(f"Fetching prices for {symbol}..."):
        collect_prices(symbol, days=365)
    st.success("Price data updated!")

if st.sidebar.button("📰 Refresh News"):
    with st.spinner("Fetching news feeds..."):
        collect_all_news()
    st.success("News updated!")

# Last updated
last_updated = get_last_updated(symbol)
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Last price data:** {last_updated}")

# =============================================================================
# LOAD DATA
# =============================================================================

@st.cache_data(ttl=300)
def load_chart_data(symbol, start, end):
    df = get_prices_for_display(
        symbol,
        start_date=str(start),
        end_date=str(end),
    )
    if df.empty:
        return df
    df = compute_indicators(df)
    return df

df = load_chart_data(symbol, start_date, end_date)

# =============================================================================
# MAIN TITLE
# =============================================================================

st.title(f"📈 {symbol} — Thai Stock Analysis")
st.markdown(f"_Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")

# =============================================================================
# CHECK FOR EMPTY DATA
# =============================================================================

if df.empty:
    st.warning(
        f"No price data found for **{symbol}**. "
        "Click **Refresh Price Data** in the sidebar to fetch data."
    )
    st.stop()

# =============================================================================
# METRICS ROW
# =============================================================================

ind = get_latest_indicators(symbol)

if ind:
    # บน Desktop แสดง 2 + 3 คอลัมน์
    col1, col2 = st.columns(2)
    col3, col4, col5 = st.columns(3)

    # Price change
    if len(df) >= 2:
        prev_close = df.iloc[-2]["close"]
        curr_close = df.iloc[-1]["close"]
        price_chg  = curr_close - prev_close
        price_pct  = (price_chg / prev_close) * 100
    else:
        prev_close = curr_close = df.iloc[-1]["close"]
        price_chg  = price_pct = 0

    col1.metric(
        "Close Price",
        f"{curr_close:.2f} THB",
        f"{price_chg:+.2f} ({price_pct:+.1f}%)",
    )
    col2.metric("EMA 20",  f"{ind['ema20']:.2f}"  if ind.get('ema20')  else "N/A")
    col3.metric("EMA 50",  f"{ind['ema50']:.2f}"  if ind.get('ema50')  else "N/A")
    col4.metric("RSI (14)",f"{ind['rsi']:.1f}"    if ind.get('rsi')    else "N/A")
    col5.metric("ATR (14)",f"{ind['atr']:.2f}"    if ind.get('atr')    else "N/A")
    
st.markdown("---")

# =============================================================================
# MAIN CHART: Candlestick + EMA/SMA overlays
# =============================================================================

st.subheader("📊 Price Chart")

fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.55, 0.25, 0.20],
    subplot_titles=["Price + Indicators", "RSI (14)", "MACD"],
)

# --- Candlestick ---
fig.add_trace(
    go.Candlestick(
        x=df["date"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Price",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
    ),
    row=1, col=1,
)

# --- EMA 20 ---
if show_ema20 and "ema20" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["ema20"],
            name="EMA 20",
            line=dict(color="#ff9800", width=1.5),
        ),
        row=1, col=1,
    )

# --- EMA 50 ---
if show_ema50 and "ema50" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["ema50"],
            name="EMA 50",
            line=dict(color="#2196f3", width=1.5),
        ),
        row=1, col=1,
    )

# --- SMA 200 ---
if show_sma200 and "sma200" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["sma200"],
            name="SMA 200",
            line=dict(color="#9c27b0", width=1.5, dash="dash"),
        ),
        row=1, col=1,
    )

# --- RSI Panel ---
if "rsi" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["rsi"],
            name="RSI",
            line=dict(color="#ff9800", width=1.5),
        ),
        row=2, col=1,
    )
    # RSI zones
    fig.add_hline(y=70, line_dash="dash", line_color="red",   opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
    fig.add_hline(y=50, line_dash="dot",  line_color="gray",  opacity=0.3, row=2, col=1)

# --- MACD Panel ---
if "macd" in df.columns and "macd_signal" in df.columns:
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["macd"],
            name="MACD",
            line=dict(color="#2196f3", width=1.5),
        ),
        row=3, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["date"], y=df["macd_signal"],
            name="Signal",
            line=dict(color="#ff9800", width=1.5),
        ),
        row=3, col=1,
    )

    # MACD Histogram
    if "macd_hist" in df.columns:
        colors = ["#26a69a" if v >= 0 else "#ef5350" for v in df["macd_hist"].fillna(0)]
        fig.add_trace(
            go.Bar(
                x=df["date"], y=df["macd_hist"],
                name="Histogram",
                marker_color=colors,
                opacity=0.6,
            ),
            row=3, col=1,
        )

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
# VOLUME CHART
# =============================================================================

st.subheader("📦 Volume")

vol_fig = go.Figure()

vol_colors = [
    "#26a69a" if df["close"].iloc[i] >= df["open"].iloc[i] else "#ef5350"
    for i in range(len(df))
]

vol_fig.add_trace(go.Bar(
    x=df["date"],
    y=df["volume"],
    name="Volume",
    marker_color=vol_colors,
    opacity=0.8,
))

if "volume_ma" in df.columns:
    vol_fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["volume_ma"],
        name="Volume MA(20)",
        line=dict(color="#ff9800", width=1.5),
    ))

vol_fig.update_layout(
    height=200,
    plot_bgcolor="#0e1117",
    paper_bgcolor="#0e1117",
    font_color="#fafafa",
    margin=dict(l=40, r=40, t=20, b=40),
    showlegend=True,
)
vol_fig.update_xaxes(gridcolor="#1e2130")
vol_fig.update_yaxes(gridcolor="#1e2130")

st.plotly_chart(vol_fig, use_container_width=True)

st.markdown("---")

# =============================================================================
# NEWS PANELS
# =============================================================================

# บนมือถือแสดงข่าวเป็น Tab แทนที่จะเป็น 2 คอลัมน์
tab1, tab2 = st.tabs(["🇹🇭 ข่าวไทย", "🌍 ข่าวโลก"])

with tab1:
    st.subheader("🇹🇭 Thailand & Company News")
    th_news = load_news(category="thailand", limit=10)
    if th_news.empty:
        st.info("ยังไม่มีข่าว กด Refresh News ใน Sidebar")
    else:
        for _, row in th_news.iterrows():
            tag = f" `{row['macro_tag']}`" if row.get("macro_tag") else ""
            sym = f" `{row['symbol']}`"    if row.get("symbol")    else ""
            st.markdown(
                f"**[{row['title']}]({row['url']})**{sym}{tag}  \n"
                f"_{row['source']} — {str(row['published_at'])[:16]}_"
            )
            st.markdown("---")

with tab2:
    st.subheader("🌍 Global Macro News")
    gl_news = load_news(category="global", limit=10)
    if gl_news.empty:
        st.info("ยังไม่มีข่าว กด Refresh News ใน Sidebar")
    else:
        for _, row in gl_news.iterrows():
            tag = f" `{row['macro_tag']}`" if row.get("macro_tag") else ""
            st.markdown(
                f"**[{row['title']}]({row['url']})**{tag}  \n"
                f"_{row['source']} — {str(row['published_at'])[:16]}_"
            )
            st.markdown("---")

st.markdown("---")

# =============================================================================
# ANALYSIS SUMMARY
# =============================================================================

st.subheader("🧠 Rule-Based Analysis Summary")

if not ind:
    st.warning(
        "Insufficient indicator data. "
        "Click **Refresh Price Data** to fetch at least 60 days of history."
    )
else:
    # Get recent macro tags from news
    try:
        global_news_df  = load_news(category="global", limit=30)
        recent_macro_tags = (
            global_news_df["macro_tag"]
            .dropna()
            .unique()
            .tolist()
        ) if not global_news_df.empty else []
    except Exception:
        recent_macro_tags = []

    # Run signals
   
    result = run_all_signals(symbol, ind, recent_macro_tags)
    rec    = compute_trading_recommendation(ind, result["signals"], result["confidence"])

    # Confidence badge
    conf      = result["confidence"]["confidence"]
    dominant  = result["confidence"]["dominant"]
    CONF_TH   = {"HIGH": "สูง", "MEDIUM": "ปานกลาง", "LOW": "ต่ำ"}
    DOM_TH    = {"BULLISH": "ขาขึ้น", "BEARISH": "ขาลง"}
    conf_color = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(conf, "⚪")

    st.markdown(
        f"### {conf_color} ความเชื่อมั่น: **{CONF_TH.get(conf, conf)}** | "
        f"ทิศทาง: **{DOM_TH.get(dominant, dominant)}**  \n"
        f"_{result['confidence']['detail']}_"
    )

    # Signal table
    SIGNAL_TH = {
        "STRONG BULLISH": "แนวโน้มขาขึ้นแข็งแกร่ง",
        "BULLISH": "แนวโน้มขาขึ้น",
        "NEUTRAL": "เป็นกลาง",
        "BEARISH": "แนวโน้มขาลง",
        "STRONG BEARISH": "แนวโน้มขาลงแข็งแกร่ง",
        "OVERSOLD": "ขายมากเกินไป",
        "WATCH OVERSOLD": "เริ่มฟื้นจาก Oversold",
        "OVERBOUGHT": "ซื้อมากเกินไป",
        "WATCH OVERBOUGHT": "ใกล้โซน Overbought",
        "BULLISH MOMENTUM": "โมเมนตัมขาขึ้น",
        "BEARISH MOMENTUM": "โมเมนตัมขาลง",
        "HIGH VOLUME": "ปริมาณซื้อขายสูง",
        "LOW VOLUME": "ปริมาณซื้อขายต่ำ",
        "NORMAL VOLUME": "ปริมาณซื้อขายปกติ",
        "HIGH VOLATILITY": "ความผันผวนสูง",
        "NORMAL VOLATILITY": "ความผันผวนปกติ",
        "LOW VOLATILITY": "ความผันผวนต่ำ",
        "INSUFFICIENT DATA": "ข้อมูลไม่เพียงพอ",
    }

    st.markdown("#### สรุปสัญญาณ")
    signal_rows = []
    for name, sig in result["signals"].items():
        NAME_TH = {
            "trend": "แนวโน้ม (EMA/SMA)",
            "rsi": "โมเมนตัม (RSI)",
            "macd": "โมเมนตัม (MACD)",
            "volume": "ปริมาณซื้อขาย",
            "volatility": "ความผันผวน (ATR)",
        }
        signal_rows.append({
            "ตัวชี้วัด": NAME_TH.get(name, name),
            "สัญญาณ":    SIGNAL_TH.get(sig.get("signal", ""), sig.get("signal", "")),
            "รายละเอียด": sig.get("detail", ""),
        })
    st.dataframe(
        pd.DataFrame(signal_rows),
        use_container_width=True,
        hide_index=True,
    )

    # Full summary
    st.markdown("#### รายงานวิเคราะห์ฉบับเต็ม")
    summary_text = build_summary(
        symbol        = symbol,
        ind           = ind,
        signals       = result["signals"],
        confidence    = result["confidence"],
        macro_impacts = result["macro_impacts"],
        rec           = rec,
    )
    st.markdown(summary_text)
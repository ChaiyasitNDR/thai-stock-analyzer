# config/settings.py

# =============================================================================
# THAI STOCK LIST (SET)
# Format: "TICKER.BK" (yfinance format for Thai stocks)
# =============================================================================

THAI_STOCKS = [
    # Banking & Finance
    "SCB.BK",       # Siam Commercial Bank
    "KBANK.BK",     # Kasikorn Bank
    "BBL.BK",       # Bangkok Bank
    "KTB.BK",       # Krungthai Bank
    "TTB.BK",       # TMBThanachart Bank

    # Energy & Utilities
    "PTT.BK",       # PTT (National Oil Company)
    "PTTEP.BK",     # PTT Exploration & Production
    "GULF.BK",      # Gulf Energy Development
    "GPSC.BK",      # Global Power Synergy
    "RATCH.BK",     # Ratch Group

    # Commerce & Retail
    "CPALL.BK",     # CP All (7-Eleven Thailand)
    "CRC.BK",       # Central Retail Corporation
    "HMPRO.BK",     # Home Product Center
    "BJC.BK",       # Berli Jucker

    # Industrials & Property
    "SCC.BK",       # SCG (Siam Cement Group)
    "AOT.BK",       # Airports of Thailand
    "WHA.BK",       # WHA Corporation
    "AMATA.BK",     # Amata Corporation

    # Property & Real Estate
    "CPN.BK",       # Central Pattana
    "LH.BK",        # Land and Houses

    # Healthcare
    "BDMS.BK",      # Bangkok Dusit Medical Services
    "BH.BK",        # Bumrungrad Hospital

    # Food & Beverage
    "CPF.BK",       # Charoen Pokphand Foods
    "TU.BK",        # Thai Union Group
    "OSP.BK",       # Osotspa

    # Telecom & Tech
    "ADVANC.BK",    # Advanced Info Service (AIS)
    "TRUE.BK",      # True Corporation
    "INTUCH.BK",    # Intouch Holdings
]

# Default stock shown when dashboard first loads
DEFAULT_STOCK = "PTT.BK"

# =============================================================================
# SECTOR MAPPING
# Maps each ticker to its sector (used for macro impact analysis)
# =============================================================================

STOCK_SECTOR = {
    "SCB.BK":    "banking",
    "KBANK.BK":  "banking",
    "BBL.BK":    "banking",
    "KTB.BK":    "banking",
    "TTB.BK":    "banking",

    "PTT.BK":    "energy",
    "PTTEP.BK":  "energy",
    "GULF.BK":   "energy",
    "GPSC.BK":   "energy",
    "RATCH.BK":  "energy",

    "CPALL.BK":  "commerce",
    "CRC.BK":    "commerce",
    "HMPRO.BK":  "commerce",
    "BJC.BK":    "commerce",

    "SCC.BK":    "industrial",
    "AOT.BK":    "transport",
    "WHA.BK":    "industrial",
    "AMATA.BK":  "industrial",

    "CPN.BK":    "property",
    "LH.BK":     "property",

    "BDMS.BK":   "healthcare",
    "BH.BK":     "healthcare",

    "CPF.BK":    "food",
    "TU.BK":     "food",
    "OSP.BK":    "food",

    "ADVANC.BK": "telecom",
    "TRUE.BK":   "telecom",
    "INTUCH.BK": "telecom",
}

# =============================================================================
# RSS FEED URLS
# =============================================================================

# --- Company / Thailand news feeds ---
THAILAND_NEWS_FEEDS = [
    {
        "source": "Bangkok Post - Business",
        "url": "https://www.bangkokpost.com/rss/data/business.xml",
        "category": "thailand",
    },
    {
        "source": "The Nation - Business",
        "url": "https://www.nationthailand.com/rss/business",
        "category": "thailand",
    },
    {
        "source": "SET News (Official)",
        "url": "https://www.set.or.th/th/market/news/rss-feed.xml",
        "category": "thailand",
    },
]

# --- Global / Macro news feeds ---
GLOBAL_NEWS_FEEDS = [
    {
        "source": "Reuters - Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "category": "global",
    },
    {
        "source": "Reuters - World",
        "url": "https://feeds.reuters.com/Reuters/worldNews",
        "category": "global",
    },
    {
        "source": "CNBC - World Economy",
        "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "category": "global",
    },
    {
        "source": "CNBC - Finance",
        "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "category": "global",
    },
    {
        "source": "BBC - Business",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "category": "global",
    },
    {
        "source": "FT - World",
        "url": "https://www.ft.com/world?format=rss",
        "category": "global",
    },
]

# =============================================================================
# MACRO TAG KEYWORDS
# Used to auto-tag news articles by topic
# =============================================================================

MACRO_KEYWORDS = {
    "energy": [
        "oil", "crude", "petroleum", "natural gas", "LNG",
        "energy price", "OPEC", "brent", "WTI",
    ],
    "rates": [
        "interest rate", "federal reserve", "Fed rate", "rate hike",
        "rate cut", "monetary policy", "central bank", "BOT rate",
        "inflation", "CPI", "yield",
    ],
    "china": [
        "china", "chinese", "beijing", "PBoC", "yuan", "renminbi",
        "shanghai", "china economy", "china gdp", "sino",
    ],
    "geopolitics": [
        "war", "conflict", "sanction", "tariff", "trade war",
        "NATO", "russia", "ukraine", "middle east", "taiwan strait",
        "south china sea",
    ],
    "commodities": [
        "gold", "copper", "iron ore", "steel", "rubber",
        "palm oil", "rice", "wheat", "commodity",
    ],
    "usd": [
        "dollar", "USD", "DXY", "dollar index", "baht",
        "THB", "currency", "forex", "exchange rate",
    ],
    "trade": [
        "export", "import", "trade balance", "current account",
        "supply chain", "manufacturing", "PMI",
    ],
}

# =============================================================================
# MACRO TAG → AFFECTED THAI SECTORS
# Rule: if news has this macro_tag → these sectors may be impacted
# =============================================================================

MACRO_SECTOR_IMPACT = {
    "energy": {
        "sectors": ["energy"],
        "direction": "positive",
        "reason": "Rising energy prices benefit Thai energy producers (PTT, PTTEP)",
    },
    "rates": {
        "sectors": ["banking", "property"],
        "direction": "mixed",
        "reason": "Rate hikes may compress margins for property; banking NIM may widen",
    },
    "china": {
        "sectors": ["industrial", "food", "commerce"],
        "direction": "negative",
        "reason": "China slowdown reduces Thai export demand and tourism inflow",
    },
    "geopolitics": {
        "sectors": ["energy", "transport"],
        "direction": "negative",
        "reason": "Geopolitical tension raises supply chain risk and oil price volatility",
    },
    "commodities": {
        "sectors": ["food", "industrial"],
        "direction": "mixed",
        "reason": "Commodity prices affect input costs for Thai food and industrial sectors",
    },
    "usd": {
        "sectors": ["banking", "commerce", "energy"],
        "direction": "mixed",
        "reason": "Strong USD raises import costs; benefits exporters; THB volatility risk",
    },
    "trade": {
        "sectors": ["industrial", "food", "telecom"],
        "direction": "mixed",
        "reason": "Trade data directly affects Thai export-oriented sectors",
    },
}

# =============================================================================
# TECHNICAL INDICATOR SETTINGS
# =============================================================================

INDICATOR_SETTINGS = {
    "ema_short":  20,       # EMA 20
    "ema_long":   50,       # EMA 50
    "sma_long":   200,      # SMA 200
    "rsi_period": 14,       # RSI period
    "macd_fast":  12,       # MACD fast
    "macd_slow":  26,       # MACD slow
    "macd_signal": 9,       # MACD signal
    "atr_period": 14,       # ATR period
    "volume_ma":  20,       # Volume moving average period
}

# RSI zone thresholds
RSI_ZONES = {
    "oversold":       30,
    "oversold_watch": 40,
    "neutral_low":    40,
    "neutral_high":   60,
    "overbought_watch": 60,
    "overbought":     70,
}

# =============================================================================
# DATA SETTINGS
# =============================================================================

DEFAULT_PERIOD_DAYS = 365       # How many days of history to fetch by default
MIN_DAYS_FOR_SMA200 = 220       # Minimum data points needed to compute SMA200
DB_PATH = "data/thai_stocks.db" # SQLite database file path

# =============================================================================
# HORIZON CONFIG — ระยะเวลาการลงทุน
# =============================================================================

HORIZON_CONFIG = {
    "short": {
        "label":              "📅 ระยะสั้น (1–10 วัน)",
        "emphasize":          ["rsi", "macd", "volume"],
        "de_emphasize":       ["sma200"],
        "atr_buy_mult":       [0.3, 0.6, 1.0],
        "atr_sell_mult":      [0.3, 0.6, 1.0],
        "atr_invalid_mult":   1.0,
        "validation_horizon": 5,
        "guidance": (
            "ระยะสั้น: RSI และ MACD มีความสำคัญมากกว่า SMA200 "
            "ควรระวัง noise และ false signal — "
            "ช่วงราคาวางแผนแคบกว่าระยะยาว"
        ),
        "risk_note": (
            "ระยะสั้นมีความเสี่ยงสูง — "
            "ราคาอาจแกว่งได้มากใน 1-2 วัน "
            "และ transaction cost มีผลต่อผลตอบแทนมากกว่า"
        ),
        "indicator_note": (
            "เน้น: RSI, MACD, Volume | "
            "ลดความสำคัญ: SMA200 (ระยะยาวเกินไป)"
        ),
    },
    "medium": {
        "label":              "📆 ระยะกลาง (2–8 สัปดาห์)",
        "emphasize":          ["trend", "macd", "volume"],
        "de_emphasize":       [],
        "atr_buy_mult":       [0.5, 1.0, 1.5],
        "atr_sell_mult":      [0.5, 1.0, 2.0],
        "atr_invalid_mult":   1.5,
        "validation_horizon": 15,
        "guidance": (
            "ระยะกลาง: EMA alignment และ trend มีความสำคัญ "
            "รอสัญญาณยืนยันจากหลาย indicator ก่อนตัดสินใจ — "
            "ช่วงราคาวางแผนกว้างกว่าระยะสั้น"
        ),
        "risk_note": (
            "ต้องทนต่อความผันผวนระหว่างทาง "
            "และติดตามข่าวสารเป็นระยะ "
            "macro events อาจเปลี่ยนทิศทางได้"
        ),
        "indicator_note": (
            "เน้น: EMA Trend, MACD, Volume | "
            "ใช้ทุก indicator ประกอบ"
        ),
    },
    "long": {
        "label":              "🗓️ ระยะยาว (3–12 เดือน)",
        "emphasize":          ["trend", "sma200", "volatility"],
        "de_emphasize":       ["rsi", "macd"],
        "atr_buy_mult":       [1.0, 2.0, 3.0],
        "atr_sell_mult":      [1.0, 2.0, 4.0],
        "atr_invalid_mult":   3.0,
        "validation_horizon": 60,
        "guidance": (
            "ระยะยาว: SMA200 และ trend หลักมีความสำคัญที่สุด "
            "RSI และ MACD ระยะสั้นมีความสำคัญน้อยกว่า — "
            "ช่วงราคาวางแผนกว้างที่สุด"
        ),
        "risk_note": (
            "ต้องพร้อมรับมือการเปลี่ยนแปลง macro และ fundamental "
            "ของบริษัทในระยะยาว "
            "ราคาอาจผันผวนมากก่อนถึงเป้าหมาย"
        ),
        "indicator_note": (
            "เน้น: SMA200, EMA Trend, ATR | "
            "ลดความสำคัญ: RSI, MACD (noise ระยะสั้น)"
        ),
    },
}
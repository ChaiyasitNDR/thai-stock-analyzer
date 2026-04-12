# collectors/news_collector.py

import feedparser
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from db.database import save_news
from config.settings import (
    THAILAND_NEWS_FEEDS,
    GLOBAL_NEWS_FEEDS,
    MACRO_KEYWORDS,
    THAI_STOCKS,
)

# =============================================================================
# HELPER: Parse published date from RSS entry
# =============================================================================

def parse_date(entry) -> str:
    """
    Try to extract and normalize published date from RSS entry.
    Returns date string in format YYYY-MM-DD HH:MM:SS or empty string.
    """
    # Try 'published' field first
    if hasattr(entry, "published"):
        try:
            dt = parsedate_to_datetime(entry.published)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    # Try 'updated' field as fallback
    if hasattr(entry, "updated"):
        try:
            dt = parsedate_to_datetime(entry.updated)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    # Return current time if nothing works
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =============================================================================
# HELPER: Auto-tag news with macro category
# =============================================================================

def detect_macro_tag(title: str) -> str:
    """
    Scan news title for macro keywords.
    Returns the first matching macro_tag or None.
    """
    title_lower = title.lower()
    for tag, keywords in MACRO_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return tag
    return None


# =============================================================================
# HELPER: Match news title to a Thai stock symbol
# =============================================================================

def detect_symbol(title: str) -> str:
    """
    Check if title mentions a Thai stock ticker or company name.
    Returns matched symbol (e.g. 'PTT.BK') or None.
    """
    COMPANY_NAMES = {
        "PTT":      "PTT.BK",
        "PTTEP":    "PTTEP.BK",
        "SCB":      "SCB.BK",
        "KBANK":    "KBANK.BK",
        "Kasikorn": "KBANK.BK",
        "Bangkok Bank": "BBL.BK",
        "BBL":      "BBL.BK",
        "KTB":      "KTB.BK",
        "Krungthai":"KTB.BK",
        "CPALL":    "CPALL.BK",
        "CP All":   "CPALL.BK",
        "7-Eleven": "CPALL.BK",
        "Central Retail": "CRC.BK",
        "CRC":      "CRC.BK",
        "SCG":      "SCC.BK",
        "Siam Cement": "SCC.BK",
        "AOT":      "AOT.BK",
        "Airports of Thailand": "AOT.BK",
        "BDMS":     "BDMS.BK",
        "Bangkok Dusit": "BDMS.BK",
        "Bumrungrad": "BH.BK",
        "AIS":      "ADVANC.BK",
        "Advanced Info": "ADVANC.BK",
        "True":     "TRUE.BK",
        "Gulf Energy": "GULF.BK",
        "GULF":     "GULF.BK",
        "CPF":      "CPF.BK",
        "Charoen Pokphand Foods": "CPF.BK",
        "Thai Union": "TU.BK",
        "Land and Houses": "LH.BK",
        "CPN":      "CPN.BK",
        "Central Pattana": "CPN.BK",
    }

    title_lower = title.lower()
    for name, symbol in COMPANY_NAMES.items():
        if name.lower() in title_lower:
            return symbol
    return None


# =============================================================================
# FETCH: Single RSS feed
# =============================================================================

def fetch_feed(feed_config: dict) -> list[dict]:
    """
    Fetch and parse a single RSS feed.
    Returns a list of news dicts ready for save_news().
    """
    source   = feed_config["source"]
    url      = feed_config["url"]
    category = feed_config["category"]

    print(f"  Fetching: {source}")

    try:
        feed = feedparser.parse(url)

        if feed.bozo and not feed.entries:
            print(f"    [WARN] Feed error or empty: {source}")
            return []

        items = []
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "").strip()

            if not title or not link:
                continue

            published_at = parse_date(entry)
            macro_tag    = detect_macro_tag(title)
            symbol       = detect_symbol(title) if category == "thailand" else None

            items.append({
                "symbol":       symbol,
                "category":     category,
                "macro_tag":    macro_tag,
                "source":       source,
                "title":        title,
                "published_at": published_at,
                "url":          link,
            })

        print(f"    [OK] {len(items)} articles found")
        return items

    except Exception as e:
        print(f"    [ERROR] {source}: {e}")
        return []


# =============================================================================
# COLLECT: Thailand news
# =============================================================================

def collect_thailand_news() -> int:
    """
    Fetch all Thailand/company RSS feeds and save to database.
    Returns total new rows inserted.
    """
    print("\n--- Collecting Thailand News ---")
    all_items = []

    for feed_config in THAILAND_NEWS_FEEDS:
        items = fetch_feed(feed_config)
        all_items.extend(items)

    if not all_items:
        print("  [WARN] No Thailand news fetched.")
        return 0

    rows = save_news(all_items)
    print(f"  [DB] {rows} new Thailand news saved")
    return rows


# =============================================================================
# COLLECT: Global macro news
# =============================================================================

def collect_global_news() -> int:
    """
    Fetch all global macro RSS feeds and save to database.
    Returns total new rows inserted.
    """
    print("\n--- Collecting Global News ---")
    all_items = []

    for feed_config in GLOBAL_NEWS_FEEDS:
        items = fetch_feed(feed_config)
        all_items.extend(items)

    if not all_items:
        print("  [WARN] No global news fetched.")
        return 0

    rows = save_news(all_items)
    print(f"  [DB] {rows} new global news saved")
    return rows


# =============================================================================
# COLLECT: All news (Thailand + Global)
# =============================================================================

def collect_all_news() -> int:
    """
    Fetch and save all news feeds (Thailand + Global).
    Returns total new rows inserted.
    """
    print("=" * 50)
    print("Starting news collection")
    print("=" * 50)

    total = 0
    total += collect_thailand_news()
    total += collect_global_news()

    print("\n" + "=" * 50)
    print(f"News collection done. Total new articles: {total}")
    print("=" * 50)
    return total


# =============================================================================
# MAIN — run this file directly to collect all news
# =============================================================================

if __name__ == "__main__":
    collect_all_news()
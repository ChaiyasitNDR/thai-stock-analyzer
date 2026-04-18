# analysis/news_ranker.py
# News Ranking + Clustering — Deterministic, No LLM
# ใช้ rule-based scoring + TF-IDF clustering

from config.settings import MACRO_KEYWORDS, STOCK_SECTOR

# =============================================================================
# COMPANY NAME MAP สำหรับ Relevance Scoring
# =============================================================================

COMPANY_NAME_MAP = {
    "PTT":            "PTT.BK",
    "PTTEP":          "PTTEP.BK",
    "SCB":            "SCB.BK",
    "KBANK":          "KBANK.BK",
    "Kasikorn":       "KBANK.BK",
    "Bangkok Bank":   "BBL.BK",
    "BBL":            "BBL.BK",
    "KTB":            "KTB.BK",
    "Krungthai":      "KTB.BK",
    "CPALL":          "CPALL.BK",
    "CP All":         "CPALL.BK",
    "7-Eleven":       "CPALL.BK",
    "Central Retail": "CRC.BK",
    "CRC":            "CRC.BK",
    "SCG":            "SCC.BK",
    "Siam Cement":    "SCC.BK",
    "AOT":            "AOT.BK",
    "Airports of Thailand": "AOT.BK",
    "BDMS":           "BDMS.BK",
    "Bangkok Dusit":  "BDMS.BK",
    "Bumrungrad":     "BH.BK",
    "AIS":            "ADVANC.BK",
    "Advanced Info":  "ADVANC.BK",
    "True":           "TRUE.BK",
    "Gulf Energy":    "GULF.BK",
    "GULF":           "GULF.BK",
    "CPF":            "CPF.BK",
    "Thai Union":     "TU.BK",
    "Land and Houses": "LH.BK",
    "CPN":            "CPN.BK",
    "Central Pattana": "CPN.BK",
    "KKP":            "KKP.BK",
    "Kiatnakin":      "KKP.BK",
    "TISCO":          "TISCO.BK",
    "MTC":            "MTC.BK",
    "MINT":           "MINT.BK",
    "Minor":          "MINT.BK",
    "BEM":            "BEM.BK",
    "DELTA":          "DELTA.BK",
}

SECTOR_KEYWORDS = {
    "banking":    [
        "bank", "ธนาคาร", "interest rate", "NIM",
        "loan", "deposit", "credit", "NPL"
    ],
    "energy":     [
        "oil", "gas", "petroleum", "energy", "LNG",
        "refinery", "solar", "power plant"
    ],
    "property":   [
        "real estate", "อสังหา", "mortgage",
        "condo", "housing", "property"
    ],
    "healthcare": [
        "hospital", "โรงพยาบาล", "medical",
        "healthcare", "clinic", "pharma"
    ],
    "commerce":   [
        "retail", "ค้าปลีก", "consumer",
        "shopping", "e-commerce", "mall"
    ],
    "industrial": [
        "factory", "manufacturing", "โรงงาน",
        "export", "industrial estate", "WHA", "AMATA"
    ],
    "transport":  [
        "airport", "airline", "สนามบิน",
        "aviation", "logistics", "freight"
    ],
    "telecom":    [
        "telecom", "5G", "mobile", "internet",
        "broadband", "spectrum"
    ],
    "food":       [
        "food", "อาหาร", "agriculture", "farm",
        "seafood", "poultry", "livestock"
    ],
}

# =============================================================================
# A) RELEVANCE SCORING — Rule-Based
# =============================================================================

def score_relevance(
    title:       str,
    description: str,
    symbol:      str,
    sector:      str = None,
) -> tuple:
    """
    คำนวณ relevance score 0-100
    Returns: (score, reason_list)

    Rules:
    - Ticker match in title    → +40
    - Company name match       → +30
    - Sector keyword match     → +20
    - Macro tag match          → +10
    """
    score   = 0
    reasons = []
    text    = (title + " " + (description or "")).lower()

    ticker_base = symbol.replace(".BK", "").lower()

    # 1. Ticker match
    if ticker_base in text:
        score += 40
        reasons.append(f"ticker match ({ticker_base.upper()})")

    # 2. Company name match
    for name, sym in COMPANY_NAME_MAP.items():
        if sym == symbol and name.lower() in text:
            score += 30
            reasons.append(f"company name ({name})")
            break

    # 3. Sector keyword match
    if sector and sector in SECTOR_KEYWORDS:
        for kw in SECTOR_KEYWORDS[sector]:
            if kw.lower() in text:
                score += 20
                reasons.append(f"sector keyword ({kw})")
                break

    # 4. Macro tag match
    for tag, keywords in MACRO_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                score += 10
                reasons.append(f"macro ({tag})")
                break

    final_score = min(score, 100)
    reason_text = ", ".join(reasons) if reasons else "ไม่เกี่ยวข้องโดยตรง"

    return final_score, reason_text


# =============================================================================
# B) BATCH SCORING — ให้คะแนนข่าวทั้งหมดในครั้งเดียว
# =============================================================================

def score_news_batch(
    news_items: list,
    symbol:     str,
    sector:     str = None,
) -> list:
    """
    ให้คะแนน relevance ข่าวทั้งหมด
    Returns list ของ dict พร้อม relevance_score และ relevance_reason
    """
    scored = []
    for item in news_items:
        title = item.get("title", "")
        desc  = item.get("description", "") or ""
        score, reason = score_relevance(title, desc, symbol, sector)
        scored.append({
            **item,
            "relevance_score":  score,
            "relevance_reason": reason,
        })
    return scored


# =============================================================================
# C) TF-IDF CLUSTERING — Deterministic
# =============================================================================

def cluster_news_tfidf(
    news_items:  list,
    n_clusters:  int = 4,
    min_samples: int = 2,
) -> dict:
    """
    จัดกลุ่มข่าวด้วย TF-IDF + KMeans
    Deterministic: random_state=42

    Returns: dict {cluster_id: [items]}
    """
    if len(news_items) < min_samples:
        return {0: news_items}

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.cluster import KMeans

        titles = [item.get("title", "") for item in news_items]

        vectorizer = TfidfVectorizer(
            max_features=50,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        X = vectorizer.fit_transform(titles)

        n = min(n_clusters, len(titles))
        kmeans = KMeans(
            n_clusters=n,
            random_state=42,
            n_init=10,
        )
        labels = kmeans.fit_predict(X)

        clusters = {}
        for item, label in zip(news_items, labels):
            key = int(label)
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(item)

        return clusters

    except ImportError:
        # ถ้าไม่มี sklearn ใช้ grouping แบบง่าย
        return _simple_group(news_items)
    except Exception:
        return {0: news_items}


def _simple_group(news_items: list) -> dict:
    """
    Fallback grouping ถ้าไม่มี sklearn
    จัดกลุ่มตาม macro_tag
    """
    groups = {}
    for item in news_items:
        tag = item.get("macro_tag") or "ทั่วไป"
        if tag not in groups:
            groups[tag] = []
        groups[tag].append(item)
    # แปลง key เป็น int
    return {i: v for i, v in enumerate(groups.values())}


# =============================================================================
# D) CLUSTER SUMMARY — Extractive
# =============================================================================

def summarize_cluster(items: list) -> dict:
    """
    สร้าง extractive summary ของแต่ละ cluster
    - representative headline (อันแรก)
    - top keywords จาก TF-IDF
    - macro tags ที่พบ
    - sources ที่มา
    """
    if not items:
        return {}

    titles = [i.get("title", "") for i in items]
    tags   = [i.get("macro_tag") for i in items if i.get("macro_tag")]
    sources = list(set(i.get("source", "") for i in items))

    # Keywords
    keywords = []
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(
            max_features=5,
            stop_words="english",
            ngram_range=(1, 2),
        )
        vec.fit_transform(titles)
        keywords = vec.get_feature_names_out().tolist()
    except Exception:
        # Fallback: ใช้คำที่พบบ่อย
        from collections import Counter
        all_words = " ".join(titles).lower().split()
        stop = {"the", "a", "an", "in", "of", "to", "and",
                "is", "for", "on", "at", "by", "as", "are"}
        keywords = [
            w for w, _ in Counter(
                w for w in all_words if w not in stop
            ).most_common(5)
        ]

    return {
        "representative": items[0]["title"],
        "keywords":       keywords,
        "count":          len(items),
        "macro_tags":     list(set(tags)),
        "sources":        sources,
        "items":          items,
    }


# =============================================================================
# E) MASTER: Process News for Display
# =============================================================================

def process_news_for_display(
    news_items:         list,
    symbol:             str,
    sector:             str = None,
    relevance_threshold: int = 25,
    n_clusters:         int = 4,
) -> dict:
    """
    Pipeline ครบวงจร:
    1. Score relevance ทุกชิ้น
    2. แบ่งเป็น relevant vs general
    3. Cluster general news
    4. สร้าง summary แต่ละ cluster

    Returns:
    {
        "relevant":  [scored items],
        "clusters":  [cluster summaries],
        "stats": {total, relevant_count, general_count}
    }
    """
    if not news_items:
        return {
            "relevant": [],
            "clusters": [],
            "stats": {"total": 0, "relevant_count": 0, "general_count": 0}
        }

    # Step 1: Score
    scored = score_news_batch(news_items, symbol, sector)

    # Step 2: แบ่ง relevant vs general
    relevant = [
        i for i in scored
        if i.get("relevance_score", 0) >= relevance_threshold
    ]
    general  = [
        i for i in scored
        if i.get("relevance_score", 0) < relevance_threshold
    ]

    # เรียง relevant ตาม score สูงสุดก่อน
    relevant = sorted(
        relevant,
        key=lambda x: x.get("relevance_score", 0),
        reverse=True
    )

    # Step 3: Cluster general
    clusters_raw = cluster_news_tfidf(general, n_clusters=n_clusters)

    # Step 4: Summarize clusters
    cluster_summaries = []
    for cluster_id, items in clusters_raw.items():
        if items:
            summary = summarize_cluster(items)
            cluster_summaries.append(summary)

    # เรียง cluster ตามจำนวนข่าวมากสุดก่อน
    cluster_summaries = sorted(
        cluster_summaries,
        key=lambda x: x.get("count", 0),
        reverse=True
    )

    return {
        "relevant":  relevant,
        "clusters":  cluster_summaries,
        "stats": {
            "total":          len(scored),
            "relevant_count": len(relevant),
            "general_count":  len(general),
        }
    }
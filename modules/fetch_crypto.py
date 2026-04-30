from pathlib import Path
import json

from modules.utils import safe_get_json


# =========================
# Binance 資料
# =========================

def get_coingecko_spot_fallback(symbol):
    """
    Binance 現貨失敗時的 CoinGecko 備援價格。
    目前先支援 BTCUSDT / ETHUSDT。
    """
    symbol_map = {
        "BTCUSDT": "bitcoin",
        "ETHUSDT": "ethereum",
    }

    coin_id = symbol_map.get(symbol)

    if not coin_id:
        return {
            "symbol": symbol,
            "price": None,
            "price_change_pct": None,
            "quote_volume": None,
        }

    url = "https://api.coingecko.com/api/v3/coins/markets"

    data = safe_get_json(
        url,
        params={
            "vs_currency": "usd",
            "ids": coin_id,
            "price_change_percentage": "24h",
            "sparkline": "false",
        },
        source_name=f"CoinGecko 備援價格 {symbol}",
    )

    if not data or not isinstance(data, list):
        return {
            "symbol": symbol,
            "price": None,
            "price_change_pct": None,
            "quote_volume": None,
        }

    item = data[0]

    try:
        return {
            "symbol": symbol,
            "price": float(item.get("current_price", 0)),
            "price_change_pct": float(item.get("price_change_percentage_24h", 0)),
            "quote_volume": float(item.get("total_volume", 0)),
        }
    except Exception:
        return {
            "symbol": symbol,
            "price": None,
            "price_change_pct": None,
            "quote_volume": None,
        }


def get_binance_spot_price(symbol):
    """
    取得 Binance 現貨 24H ticker。
    若 Binance 在雲端失敗，改用 CoinGecko 備援。
    """
    url = "https://api.binance.com/api/v3/ticker/24hr"

    data = safe_get_json(
        url,
        params={"symbol": symbol},
        source_name=f"Binance 現貨 {symbol}",
    )

    if not data:
        print(f"[警告] Binance 現貨 {symbol} 抓取失敗，改用 CoinGecko 備援。")
        return get_coingecko_spot_fallback(symbol)

    try:
        price = float(data.get("lastPrice", 0))
        price_change_pct = float(data.get("priceChangePercent", 0))
        quote_volume = float(data.get("quoteVolume", 0))

        # 如果 Binance 回傳異常空值，也改用 CoinGecko
        if price <= 0:
            print(f"[警告] Binance 現貨 {symbol} 價格異常，改用 CoinGecko 備援。")
            return get_coingecko_spot_fallback(symbol)

        return {
            "symbol": symbol,
            "price": price,
            "price_change_pct": price_change_pct,
            "quote_volume": quote_volume,
        }

    except Exception as e:
        print(f"[警告] Binance 現貨 {symbol} 解析失敗：{e}，改用 CoinGecko 備援。")
        return get_coingecko_spot_fallback(symbol)

def get_bybit_funding(symbol):
    """
    Binance Funding 失敗時的 Bybit 備援。
    目前支援 BTCUSDT / ETHUSDT 等 USDT 永續合約。
    """
    url = "https://api.bybit.com/v5/market/tickers"

    data = safe_get_json(
        url,
        params={
            "category": "linear",
            "symbol": symbol,
        },
        source_name=f"Bybit Funding 備援 {symbol}",
    )

    if not data:
        return None

    try:
        result = data.get("result", {})
        items = result.get("list", [])

        if not items:
            return None

        item = items[0]
        funding_rate = item.get("fundingRate")

        if funding_rate is None:
            return None

        return float(funding_rate)

    except Exception as e:
        print(f"[警告] Bybit Funding {symbol} 解析失敗：{e}")
        return None

def get_binance_funding(symbol):
    """
    取得 Binance Funding。
    若 Binance 在雲端失敗，改用 Bybit Funding 備援。
    """
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"

    data = safe_get_json(
        url,
        params={"symbol": symbol},
        source_name=f"Binance Funding {symbol}",
    )

    if not data:
        print(f"[警告] Binance Funding {symbol} 抓取失敗，改用 Bybit 備援。")
        return get_bybit_funding(symbol)

    try:
        funding = data.get("lastFundingRate")

        if funding is None:
            print(f"[警告] Binance Funding {symbol} 無 lastFundingRate，改用 Bybit 備援。")
            return get_bybit_funding(symbol)

        return float(funding)

    except Exception as e:
        print(f"[警告] Binance Funding {symbol} 解析失敗：{e}，改用 Bybit 備援。")
        return get_bybit_funding(symbol)


def get_binance_open_interest(symbol):
    url = "https://fapi.binance.com/fapi/v1/openInterest"
    data = safe_get_json(
        url,
        params={"symbol": symbol},
        source_name=f"Binance OI {symbol}",
    )

    if not data:
        return None

    return float(data.get("openInterest", 0))


# =========================
# Alternative.me 恐懼貪婪
# =========================

def get_fear_greed_index():
    url = "https://api.alternative.me/fng/"
    data = safe_get_json(
        url,
        params={"limit": 1},
        source_name="Alternative.me 恐懼貪婪",
    )

    if not data or "data" not in data:
        return {
            "value": None,
            "classification": "無資料",
        }

    item = data["data"][0]
    return {
        "value": int(item.get("value", 0)),
        "classification": item.get("value_classification", "無資料"),
    }


# =========================
# CoinGecko 板塊輪動
# =========================

def get_coingecko_categories():
    """
    抓取 CoinGecko 板塊分類資料
    用來觀察資金往哪些主題流動

    注意：
    CoinGecko categories 是分類市值變化，不等於真正資金流入。
    因此這裡會做品質過濾，避免穩定幣、小板塊、異常分類干擾判斷。
    """
    url = "https://api.coingecko.com/api/v3/coins/categories"
    data = safe_get_json(
        url,
        source_name="CoinGecko 板塊分類",
    )

    if not data or not isinstance(data, list):
        return {
            "top_categories": [],
            "weak_categories": [],
            "score": 0,
            "summary": "CoinGecko 板塊資料抓取失敗，暫時無法判斷板塊輪動。",
        }

    cleaned = []

    # 不適合拿來當交易板塊輪動的分類
    blacklist_keywords = [
        "stablecoin",
        "stablecoins",
        "usd stablecoin",
        "try stablecoin",
        "eur stablecoin",
        "gbp stablecoin",
        "fiat",
        "launchpad",
        "pump",
        "vault",
        "bridged",
        "wrapped",
        "liquid staking tokens",
    ]

    # 小型 ecosystem 很容易被單一代幣扭曲
    # 但大型 ecosystem 例如 Solana Ecosystem / Ethereum Ecosystem 仍可保留
    small_noise_keywords = [
        "cookie",
        "science",
        "erc 404",
    ]

    for item in data:
        name = item.get("name", "未知板塊")
        name_lower = name.lower()

        market_cap = item.get("market_cap")
        volume_24h = item.get("volume_24h")
        change_24h = item.get("market_cap_change_24h")

        # 必要資料缺失就跳過，不再硬補 0
        if market_cap is None or volume_24h is None or change_24h is None:
            continue

        try:
            market_cap = float(market_cap)
            volume_24h = float(volume_24h)
            change_24h = float(change_24h)
        except Exception:
            continue

        # 排除穩定幣、Launchpad、包裝資產等不適合當作輪動板塊的分類
        if any(keyword in name_lower for keyword in blacklist_keywords):
            continue

        # 排除明顯小型雜訊分類
        if any(keyword in name_lower for keyword in small_noise_keywords):
            continue

        # 基本流動性與市值門檻
        if market_cap < 100_000_000:
            continue

        if volume_24h < 5_000_000:
            continue

        # 排除極端異常值
        # 真正大型板塊一天漲 50% 以上通常很可疑，容易是分類統計問題
        if abs(change_24h) > 50:
            continue

        cleaned.append({
            "name": name,
            "market_cap": market_cap,
            "volume_24h": volume_24h,
            "change_24h": change_24h,
        })

    if not cleaned:
        return {
            "top_categories": [],
            "weak_categories": [],
            "score": 0,
            "summary": "CoinGecko 板塊資料經過品質過濾後為空，暫時無法判斷板塊輪動。",
        }

    top_categories = sorted(
        cleaned,
        key=lambda x: x["change_24h"],
        reverse=True,
    )[:8]

    weak_categories = sorted(
        cleaned,
        key=lambda x: x["change_24h"],
    )[:5]

    score = 0

    positive_count = sum(1 for x in cleaned if x["change_24h"] > 1)
    negative_count = sum(1 for x in cleaned if x["change_24h"] < -1)

    if positive_count > negative_count * 1.3:
        score += 1
        market_tone = "經過品質過濾後，多數有效板塊上漲，代表市場風險偏好正在改善。"
    elif negative_count > positive_count * 1.3:
        score -= 1
        market_tone = "經過品質過濾後，多數有效板塊下跌，代表市場風險偏好偏弱。"
    else:
        market_tone = "有效板塊漲跌分歧，代表市場資金仍在輪動，尚未形成全面性方向。"

    strong_names = "、".join([x["name"] for x in top_categories[:3]])

    if top_categories and top_categories[0]["change_24h"] >= 5:
        score += 1
        hot_tone = f"其中 {strong_names} 表現較強，可能是短線資金關注的主題。"
    else:
        hot_tone = f"目前較強板塊為 {strong_names}，但強度尚未到全面爆發。"

    summary = market_tone + hot_tone

    return {
        "top_categories": top_categories,
        "weak_categories": weak_categories,
        "score": score,
        "summary": summary,
    }

# =========================
# V2.1 板塊交叉驗證模型
# CoinGecko 分類 + Binance 代表幣追蹤
# =========================

SECTOR_WATCHLIST_PATH = Path("sector_watchlist.json")


def load_sector_watchlist():
    if not SECTOR_WATCHLIST_PATH.exists():
        return {}

    try:
        with SECTOR_WATCHLIST_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[警告] sector_watchlist.json 讀取失敗：{e}")
        return {}


def get_coingecko_category_raw():
    """
    取得 CoinGecko 原始分類資料。
    用於第三方分類參考，不直接等同於真實資金流。
    """
    url = "https://api.coingecko.com/api/v3/coins/categories"
    data = safe_get_json(
        url,
        source_name="CoinGecko 分類原始資料",
    )

    if not data or not isinstance(data, list):
        return []

    return data


def get_symbol_24hr_for_sector(symbol):
    """
    取得 Binance 代表幣 24H 資料。
    用於代表幣追蹤，不代表官方板塊分類。
    """
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = safe_get_json(
        url,
        params={"symbol": symbol},
        source_name=f"Binance 代表幣追蹤 {symbol}",
    )

    if not data:
        return None

    try:
        return {
            "symbol": symbol,
            "price_change_pct": float(data.get("priceChangePercent", 0)),
            "quote_volume": float(data.get("quoteVolume", 0)),
            "last_price": float(data.get("lastPrice", 0)),
        }
    except Exception:
        return None


def match_coingecko_sector(coingecko_raw, keywords):
    """
    用 sector_watchlist.json 裡的 coingecko_keywords
    去比對 CoinGecko 分類名稱。
    """
    matched = []

    for item in coingecko_raw:
        name = item.get("name", "")
        name_lower = name.lower()

        market_cap = item.get("market_cap")
        volume_24h = item.get("volume_24h")
        change_24h = item.get("market_cap_change_24h")

        for keyword in keywords:
            keyword_lower = keyword.lower()

            if keyword_lower in name_lower:
                try:
                    matched.append({
                        "name": name,
                        "market_cap": float(market_cap or 0),
                        "volume_24h": float(volume_24h or 0),
                        "change_24h": float(change_24h or 0),
                    })
                except Exception:
                    pass

    if not matched:
        return {
            "matched": False,
            "status": "無對應分類",
            "change_24h": None,
            "matched_names": [],
        }

    # 如果有多個分類符合，取市值最高者，避免小分類干擾
    best = sorted(
        matched,
        key=lambda x: x["market_cap"],
        reverse=True,
    )[0]

    change = best["change_24h"]

    if change >= 2:
        status = "偏強"
    elif change <= -2:
        status = "偏弱"
    else:
        status = "中性"

    return {
        "matched": True,
        "status": status,
        "change_24h": change,
        "matched_names": [x["name"] for x in matched[:3]],
        "main_category": best["name"],
    }


def build_watchlist_sector_flow(sector_info):
    """
    用 Binance 代表幣追蹤板塊內主要幣種狀態。
    不宣稱是官方分類，只作為交叉驗證。
    """
    symbols = sector_info.get("symbols", [])
    rows = []

    for symbol in symbols:
        row = get_symbol_24hr_for_sector(symbol)

        if row is None:
            continue

        # 成交額太低的幣先排除，避免雜訊
        if row["quote_volume"] < 1_000_000:
            continue

        rows.append(row)

    if not rows:
        return {
            "status": "無有效代表幣",
            "change_24h": None,
            "volume_24h": 0,
            "coin_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "symbols": [],
        }

    total_volume = sum(x["quote_volume"] for x in rows)

    if total_volume <= 0:
        weighted_change = sum(x["price_change_pct"] for x in rows) / len(rows)
    else:
        weighted_change = sum(
            x["price_change_pct"] * x["quote_volume"]
            for x in rows
        ) / total_volume

    positive_count = sum(1 for x in rows if x["price_change_pct"] > 0)
    negative_count = sum(1 for x in rows if x["price_change_pct"] < 0)

    if weighted_change >= 2 and positive_count >= max(1, len(rows) * 0.5):
        status = "偏強"
    elif weighted_change <= -2 and negative_count >= max(1, len(rows) * 0.5):
        status = "偏弱"
    else:
        status = "中性"

    return {
        "status": status,
        "change_24h": weighted_change,
        "volume_24h": total_volume,
        "coin_count": len(rows),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "symbols": [x["symbol"] for x in rows],
    }


def judge_consistency(coingecko_status, watchlist_status):
    """
    判斷第三方分類與代表幣追蹤是否一致。
    """
    if coingecko_status == "無對應分類" and watchlist_status == "無有效代表幣":
        return "低", "低"

    if coingecko_status == "無對應分類":
        if watchlist_status in ["偏強", "偏弱"]:
            return "中", "中"
        return "低", "低"

    if watchlist_status == "無有效代表幣":
        if coingecko_status in ["偏強", "偏弱"]:
            return "低", "低"
        return "低", "低"

    if coingecko_status == watchlist_status and coingecko_status in ["偏強", "偏弱"]:
        return "高", "中高"

    if coingecko_status == watchlist_status and coingecko_status == "中性":
        return "中", "中"

    if coingecko_status == "中性" or watchlist_status == "中性":
        return "中", "中"

    return "低", "低"


def build_sector_cross_validation():
    """
    板塊交叉驗證：
    CoinGecko 第三方分類 + Binance 代表幣追蹤 + 一致性 + 可信度。
    """
    watchlist = load_sector_watchlist()
    coingecko_raw = get_coingecko_category_raw()
    

    if not watchlist:
        return {
            "rows": [],
            "summary": "找不到 sector_watchlist.json，暫時無法建立板塊交叉驗證。",
        }

    rows = []

    for sector_key, sector_info in watchlist.items():
        sector_name = sector_info.get("name", sector_key)
        keywords = sector_info.get("coingecko_keywords", [])

        cg_result = match_coingecko_sector(coingecko_raw, keywords)
        wl_result = build_watchlist_sector_flow(sector_info)

        consistency, confidence = judge_consistency(
            cg_result.get("status"),
            wl_result.get("status"),
        )

        # 綜合判斷，盡量保守，不過度宣稱
        if confidence in ["中高", "高"] and cg_result.get("status") == wl_result.get("status"):
            final_status = cg_result.get("status")
        elif wl_result.get("status") in ["偏強", "偏弱"] and cg_result.get("status") in ["無對應分類", "中性"]:
            final_status = f"代表幣{wl_result.get('status')}"
        elif cg_result.get("status") in ["偏強", "偏弱"] and wl_result.get("status") == "中性":
            final_status = f"分類{cg_result.get('status')}"
        else:
            final_status = "觀察中"

        rows.append({
            "key": sector_key,
            "name": sector_name,

            "coingecko_status": cg_result.get("status"),
            "coingecko_change": cg_result.get("change_24h"),
            "coingecko_category": cg_result.get("main_category", "無"),

            "watchlist_status": wl_result.get("status"),
            "watchlist_change": wl_result.get("change_24h"),
            "watchlist_volume": wl_result.get("volume_24h", 0),
            "coin_count": wl_result.get("coin_count", 0),
            "positive_count": wl_result.get("positive_count", 0),
            "negative_count": wl_result.get("negative_count", 0),

            "consistency": consistency,
            "confidence": confidence,
            "final_status": final_status,
        })

    # 排序：可信度高、代表幣漲幅高的排前面
    confidence_rank = {
        "高": 3,
        "中高": 2,
        "中": 1,
        "低": 0,
    }

    rows = sorted(
        rows,
        key=lambda x: (
            confidence_rank.get(x["confidence"], 0),
            x["watchlist_change"] if x["watchlist_change"] is not None else -999,
        ),
        reverse=True,
    )

    strong_rows = [
        x for x in rows
        if "偏強" in x["final_status"]
    ]

    if strong_rows:
        strong_names = "、".join([x["name"] for x in strong_rows[:3]])
        summary = (
            f"板塊交叉驗證顯示，{strong_names} 目前相對偏強。"
            "此結論來自第三方分類與代表幣追蹤的交叉檢查，仍需搭配成交量、Funding 與大盤環境判斷。"
        )
    else:
        summary = (
            "目前板塊交叉驗證沒有出現高度一致的強勢主題。"
            "市場可能仍處於輪動觀察期，或資金集中度尚不明顯。"
        )

    return {
        "rows": rows,
        "summary": summary,
    }

# =========================
# 整合加密資料
# =========================

def get_crypto_data():
    btc_spot = get_binance_spot_price("BTCUSDT")
    eth_spot = get_binance_spot_price("ETHUSDT")

    btc_funding = get_binance_funding("BTCUSDT")
    eth_funding = get_binance_funding("ETHUSDT")

    btc_oi = get_binance_open_interest("BTCUSDT")
    eth_oi = get_binance_open_interest("ETHUSDT")

    fear_greed = get_fear_greed_index()
    categories = get_coingecko_categories()
    sector_validation = build_sector_cross_validation()

    return {
    "btc": {
        **btc_spot,
        "funding": btc_funding,
        "oi": btc_oi,
    },
    "eth": {
        **eth_spot,
        "funding": eth_funding,
        "oi": eth_oi,
    },
    "fear_greed": fear_greed,
    "categories": categories,
    "sector_validation": sector_validation,
}
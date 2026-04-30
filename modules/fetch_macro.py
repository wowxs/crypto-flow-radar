from pathlib import Path
import json
import yfinance as yf

from modules.utils import set_source_status, write_error_log


MACRO_INPUT_PATH = Path("macro_input.json")
MACRO_LATEST_PATH = Path("data/processed/macro_latest.json")
    
def load_macro_input():
    """
    讀取手動宏觀資料。
    當 FRED 快取 macro_latest.json 不存在時，作為備援資料。
    """
    global MACRO_META

    if not MACRO_INPUT_PATH.exists():
        print("[警告] 找不到 macro_input.json，將使用空白宏觀資料。")
        MACRO_META = {
            "source": "無資料",
            "generated_at": "無資料",
            "mode": "empty",
        }
        return {}

    try:
        with MACRO_INPUT_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)

        MACRO_META = {
            "source": "手動 macro_input.json",
            "generated_at": "無資料",
            "mode": "manual",
        }

        print(f"[成功] 已讀取 macro_input.json，共 {len(data)} 筆宏觀資料。")
        return data

    except Exception as e:
        msg = f"[警告] macro_input.json 讀取失敗：{e}"
        print(msg)
        write_error_log(msg)

        MACRO_META = {
            "source": "讀取失敗",
            "generated_at": "無資料",
            "mode": "error",
        }

        return {}


def load_macro_latest():
    """
    讀取 update_macro_data.py 產生的 FRED 宏觀快取資料。
    """
    global MACRO_META

    if not MACRO_LATEST_PATH.exists():
        print("[提示] 找不到 data/processed/macro_latest.json，將退回使用 macro_input.json。")
        MACRO_META = {
            "source": "手動 macro_input.json",
            "generated_at": "無資料",
            "mode": "manual",
        }
        return None

    try:
        with MACRO_LATEST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)

        indicators = data.get("indicators", {})

        if not indicators:
            print("[警告] macro_latest.json 沒有 indicators 欄位，將退回使用 macro_input.json。")
            MACRO_META = {
                "source": "手動 macro_input.json",
                "generated_at": "無資料",
                "mode": "manual",
            }
            return None

        MACRO_META = {
            "source": data.get("source", "FRED"),
            "generated_at": data.get("generated_at", "無資料"),
            "mode": "cache",
        }

        print(f"[成功] 已讀取 FRED 宏觀快取，共 {len(indicators)} 筆資料。")
        return indicators

    except Exception as e:
        msg = f"[警告] macro_latest.json 讀取失敗：{e}"
        print(msg)
        write_error_log(msg)

        MACRO_META = {
            "source": "手動 macro_input.json",
            "generated_at": "無資料",
            "mode": "manual",
        }

        return None

def load_macro_base_data():
    """
    優先讀取 FRED 快取 macro_latest.json。
    如果沒有快取，才退回 macro_input.json。
    """
    macro_latest = load_macro_latest()

    if macro_latest:
        return macro_latest

    return load_macro_input()

def get_yfinance_change(symbol, name):
    """
    抓取 yfinance 標的最近兩天收盤價，計算漲跌幅。
    目前用於 DXY / 10Y / QQQ。
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval="1d")

        if hist.empty or len(hist) < 2:
            msg = f"yfinance {name} 資料不足"
            print(f"[警告] {msg}")
            write_error_log(msg)
            set_source_status(f"yfinance {name}", False, "資料不足")

            return {
                "name": name,
                "symbol": symbol,
                "price": None,
                "change_pct": None,
                "status": "資料不足",
                "score": 0,
                "summary": f"{name} 資料不足，暫時無法判斷。",
            }

        latest_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        change_pct = (latest_close - prev_close) / prev_close * 100

        set_source_status(f"yfinance {name}", True, "正常")

        return {
            "name": name,
            "symbol": symbol,
            "price": latest_close,
            "change_pct": change_pct,
        }

    except Exception as e:
        msg = f"[警告] yfinance 抓取失敗：{name} {symbol} | {e}"
        print(msg)
        write_error_log(msg)
        set_source_status(f"yfinance {name}", False, str(e))

        return {
            "name": name,
            "symbol": symbol,
            "price": None,
            "change_pct": None,
            "status": "抓取失敗",
            "score": 0,
            "summary": f"{name} 抓取失敗，暫時無法判斷。",
        }


def build_market_macro_auto():



    """
    自動抓取 DXY / 10Y / QQQ，並產生分數與因果解讀。
    """
    results = {}

    dxy = get_yfinance_change("DX-Y.NYB", "DXY 美元指數")
    us10y = get_yfinance_change("^TNX", "10Y 美債殖利率")
    qqq = get_yfinance_change("QQQ", "Nasdaq 100 / QQQ")

    # DXY 判讀
    dxy_change = dxy.get("change_pct")

    if dxy_change is None:
        results["dxy_auto"] = dxy
    else:
        if dxy_change <= -0.3:
            score = 1
            status = "走弱"
            summary = (
                f"DXY 近一日下跌 {dxy_change:.2f}%，代表美元壓力下降。"
                "美元走弱通常會降低風險資產的壓力，對 BTC、ETH、Nasdaq 偏正面。"
                "但仍需搭配美債殖利率與股市風險偏好一起觀察。"
            )
        elif dxy_change >= 0.3:
            score = -1
            status = "走強"
            summary = (
                f"DXY 近一日上漲 {dxy_change:.2f}%，代表美元走強。"
                "美元走強通常會吸引資金回流美元資產，使 BTC、ETH、科技股等風險資產承壓。"
                "如果同時看到美債殖利率上升，市場壓力會更明顯。"
            )
        else:
            score = 0
            status = "變化不大"
            summary = (
                f"DXY 近一日變化 {dxy_change:.2f}%，美元方向暫時不明顯。"
                "這代表美元對風險資產的壓力目前偏中性，需要觀察後續是否突破區間。"
            )

        results["dxy_auto"] = {
            "name": "DXY 美元指數",
            "status": status,
            "score": score,
            "summary": summary,
        }

    # 10Y 美債判讀
    us10y_change = us10y.get("change_pct")
    us10y_price = us10y.get("price")

    if us10y_change is None:
        results["us10y_auto"] = us10y
    else:
        yield_pct = us10y_price / 10 if us10y_price is not None else None

        if us10y_change <= -1.0:
            score = 1
            status = "下行"
            summary = (
                f"10Y 美債殖利率近一日下行 {us10y_change:.2f}%，目前約 {yield_pct:.2f}%。"
                "殖利率下行代表市場利率壓力下降，通常有利於科技股與加密貨幣等高風險資產。"
                "如果同時 DXY 走弱，對風險偏好的支持會更明顯。"
            )
        elif us10y_change >= 1.0:
            score = -1
            status = "上行"
            summary = (
                f"10Y 美債殖利率近一日上行 {us10y_change:.2f}%，目前約 {yield_pct:.2f}%。"
                "殖利率上行代表折現率與資金成本壓力提高，通常會壓制科技股與加密貨幣。"
                "如果同時 DXY 走強，市場可能更偏避險。"
            )
        else:
            score = 0
            status = "變化不大"
            summary = (
                f"10Y 美債殖利率近一日變化 {us10y_change:.2f}%，目前約 {yield_pct:.2f}%。"
                "利率壓力暫時沒有明顯擴大，對風險資產影響偏中性。"
            )

        results["us10y_auto"] = {
            "name": "10Y 美債殖利率",
            "status": status,
            "score": score,
            "summary": summary,
        }

    # QQQ 判讀
    qqq_change = qqq.get("change_pct")

    if qqq_change is None:
        results["qqq_auto"] = qqq
    else:
        if qqq_change >= 1.0:
            score = 1
            status = "風險偏好改善"
            summary = (
                f"QQQ 近一日上漲 {qqq_change:.2f}%，代表科技股風險偏好改善。"
                "科技股與加密貨幣同屬高風險資產，當 Nasdaq 表現強勢時，通常有助於市場情緒回暖。"
            )
        elif qqq_change <= -1.0:
            score = -1
            status = "風險偏好轉弱"
            summary = (
                f"QQQ 近一日下跌 {qqq_change:.2f}%，代表科技股風險偏好下降。"
                "當科技股承壓時，市場通常會降低對高波動資產的配置，BTC 與 ETH 也容易受到情緒拖累。"
            )
        else:
            score = 0
            status = "變化不大"
            summary = (
                f"QQQ 近一日變化 {qqq_change:.2f}%，科技股風險偏好暫時沒有明顯方向。"
                "這種情況下，加密市場可能更受自身資金流與合約情緒影響。"
            )

        results["qqq_auto"] = {
            "name": "Nasdaq 100 / QQQ",
            "status": status,
            "score": score,
            "summary": summary,
        }

    return results

def get_macro_meta():
    return MACRO_META
import requests
from config import FRED_API_KEY
from modules.utils import set_source_status, write_error_log


FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


def fetch_fred_series(series_id, limit=12):
    """
    抓取 FRED 指標資料。
    series_id 例如：
    CPIAUCSL = CPI
    PPIACO = PPI
    PCEPI = PCE
    PAYEMS = NFP
    UNRATE = 失業率
    """
    if not FRED_API_KEY:
        msg = "FRED_API_KEY 尚未設定，無法抓取 FRED 資料。"
        print("[警告]", msg)
        write_error_log(msg)
        set_source_status("FRED API", False, "API Key 未設定")
        return []

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }

    try:
        response = requests.get(FRED_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        observations = data.get("observations", [])

        set_source_status(f"FRED {series_id}", True, "正常")
        return observations

    except Exception as e:
        msg = f"FRED {series_id} 抓取失敗：{e}"
        print("[警告]", msg)
        write_error_log(msg)
        set_source_status(f"FRED {series_id}", False, str(e))
        return []


def get_latest_numeric(series_id):
    """
    取得 FRED 指標最新有效數值與前值。
    """
    observations = fetch_fred_series(series_id, limit=12)

    valid = []

    for item in observations:
        value = item.get("value")

        if value in [None, "."]:
            continue

        try:
            valid.append({
                "date": item.get("date"),
                "value": float(value),
            })
        except Exception:
            continue

    if len(valid) < 2:
        return None

    latest = valid[0]
    previous = valid[1]

    change = latest["value"] - previous["value"]

    return {
        "series_id": series_id,
        "latest_date": latest["date"],
        "latest_value": latest["value"],
        "previous_value": previous["value"],
        "change": change,
    }

def get_latest_with_yoy_mom(series_id):
    """
    取得最新值、前值、MoM、YoY。
    適用：CPI / PPI / PCE 這類指數型資料。
    """
    observations = fetch_fred_series(series_id, limit=24)

    valid = []

    for item in observations:
        value = item.get("value")

        if value in [None, "."]:
            continue

        try:
            valid.append({
                "date": item.get("date"),
                "value": float(value),
            })
        except Exception:
            continue

    # FRED 目前是 desc，所以 valid[0] 是最新，valid[1] 是前一月，valid[12] 是去年同期
    if len(valid) < 13:
        return None

    latest = valid[0]
    previous = valid[1]
    year_ago = valid[12]

    mom = (latest["value"] - previous["value"]) / previous["value"] * 100
    yoy = (latest["value"] - year_ago["value"]) / year_ago["value"] * 100

    return {
        "series_id": series_id,
        "latest_date": latest["date"],
        "latest_value": latest["value"],
        "previous_value": previous["value"],
        "year_ago_value": year_ago["value"],
        "mom": mom,
        "yoy": yoy,
    }


def build_fred_macro_snapshot():
    """
    建立 FRED 宏觀快照。
    """
    cpi = get_latest_with_yoy_mom("CPIAUCSL")
    ppi = get_latest_with_yoy_mom("PPIACO")
    pce = get_latest_with_yoy_mom("PCEPI")
    nfp = get_latest_numeric("PAYEMS")
    unemployment = get_latest_numeric("UNRATE")

    result = {
        "cpi": cpi,
        "ppi": ppi,
        "pce": pce,
        "nfp": nfp,
        "unemployment": unemployment,
    }

    return result
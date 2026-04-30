from pathlib import Path
from datetime import datetime
import requests


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

ERROR_LOG_PATH = LOG_DIR / "error_log.txt"

DATA_SOURCE_STATUS = {}


def set_source_status(source_name, ok=True, message="正常"):
    DATA_SOURCE_STATUS[source_name] = {
        "ok": ok,
        "message": message,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def write_error_log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"[{now}] {message}\n"

    try:
        with ERROR_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass


def safe_get_json(url, params=None, timeout=10, source_name="未知資料源"):
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()

        set_source_status(source_name, True, "正常")
        return response.json()

    except Exception as e:
        msg = f"[資料抓取失敗] {source_name} | {url} | {e}"
        print(msg)
        write_error_log(msg)
        set_source_status(source_name, False, str(e))
        return None


def fmt_price(value):
    if value is None:
        return "無資料"
    return f"{value:,.2f}"


def fmt_pct(value):
    if value is None:
        return "無資料"
    return f"{value * 100:.4f}%"


def fmt_number(value):
    if value is None:
        return "無資料"
    return f"{value:,.2f}"


def fmt_usd(value):
    if value is None:
        return "無資料"

    value = float(value)

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    else:
        return f"${value:,.0f}"


def fmt_change(value):
    if value is None:
        return "無資料"
    return f"{value:.2f}%"


def score_class(value):
    if value is None:
        return "neutral"

    if value > 0:
        return "good"
    elif value < 0:
        return "bad"
    else:
        return "neutral"


def risk_class(value):
    if value is None:
        return "neutral"

    if value >= 4:
        return "bad"
    elif value >= 2:
        return "neutral"
    else:
        return "good"


def market_score_class(value):
    if value >= 3:
        return "good"
    elif value >= -2:
        return "neutral"
    else:
        return "bad"


def change_class(value):
    if value is None:
        return "neutral"

    if value > 0:
        return "good"
    elif value < 0:
        return "bad"
    else:
        return "neutral"


def funding_class(value):
    if value is None:
        return "neutral"

    if value > 0.0005:
        return "bad"
    elif value > 0.0003:
        return "neutral"
    elif value >= 0:
        return "good"
    else:
        return "neutral"
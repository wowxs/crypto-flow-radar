from pathlib import Path
import json
from datetime import datetime

from modules.fred_client import build_fred_macro_snapshot


OUTPUT_PATH = Path("data/processed/macro_latest.json")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def fmt_pct(value):
    if value is None:
        return "無資料"
    return f"{value:.2f}%"


def build_inflation_judgement(
    name,
    data,
    yoy_hot_level=3.0,
    mom_hot_level=0.3,
    severe_yoy_level=None,
    severe_mom_level=None,
    hot_score=-2,
    mild_hot_score=-1,
    cool_score=2,
):
    """
    CPI / PPI / PCE 判讀。

    yoy_hot_level：年增率偏熱門檻
    mom_hot_level：月增率偏熱門檻
    severe_yoy_level / severe_mom_level：嚴重偏熱門檻
    hot_score：嚴重偏熱分數
    mild_hot_score：一般偏熱分數
    cool_score：降溫分數
    """
    if not data:
        return {
            "name": name,
            "status": "無資料",
            "score": 0,
            "summary": f"{name} 目前沒有取得 FRED 資料，暫時無法判斷。",
        }

    mom = data.get("mom")
    yoy = data.get("yoy")
    latest_date = data.get("latest_date")

    if mom is None or yoy is None:
        return {
            "name": name,
            "status": "資料不足",
            "score": 0,
            "summary": f"{name} 資料不足，暫時無法判斷。",
        }

    severe_yoy_level = severe_yoy_level if severe_yoy_level is not None else yoy_hot_level + 1.0
    severe_mom_level = severe_mom_level if severe_mom_level is not None else mom_hot_level + 0.3

    # 嚴重偏熱：年增與月增都明顯偏高
    if yoy >= severe_yoy_level and mom >= severe_mom_level:
        status = "通膨明顯偏熱"
        score = hot_score
        summary = (
            f"{name} 最新資料日期為 {latest_date}。"
            f"年增率約 {fmt_pct(yoy)}，月增率約 {fmt_pct(mom)}，兩者都明顯偏高，顯示通膨壓力仍強。"
            "這通常會使市場下修降息預期，並推升美債殖利率與美元壓力，"
            "對 BTC、ETH、Nasdaq 等風險資產偏負面。"
        )

    # 一般偏熱：高於門檻，但尚未到嚴重升溫
    elif yoy >= yoy_hot_level and mom >= mom_hot_level:
        status = "通膨偏熱"
        score = mild_hot_score
        summary = (
            f"{name} 最新資料日期為 {latest_date}。"
            f"年增率約 {fmt_pct(yoy)}，月增率約 {fmt_pct(mom)}，顯示通膨壓力仍高於理想狀態。"
            "這代表市場對降息的期待可能受到壓制，風險資產短線容易承受估值壓力。"
            "不過若 DXY 與 10Y 美債沒有同步走強，市場可能不會完全以利空解讀。"
        )

    # 年增偏高，但月增放緩
    elif yoy >= yoy_hot_level and mom < mom_hot_level:
        status = "年增偏高但月增降溫"
        score = 0
        summary = (
            f"{name} 最新資料日期為 {latest_date}。"
            f"年增率約 {fmt_pct(yoy)}，仍處於偏高區間，但月增率約 {fmt_pct(mom)}，短線升溫壓力較前期放緩。"
            "這代表通膨尚未完全回到理想區間，但短線壓力沒有進一步擴大，"
            "市場通常會偏中性解讀，需要搭配 DXY、10Y 美債與 Fed 預期觀察。"
        )

    # 年增不高，但月增再升溫
    elif yoy < yoy_hot_level and mom >= mom_hot_level:
        status = "短線再升溫"
        score = mild_hot_score
        summary = (
            f"{name} 最新資料日期為 {latest_date}。"
            f"年增率約 {fmt_pct(yoy)}，整體不算極端偏熱，但月增率約 {fmt_pct(mom)}，顯示短線價格壓力重新升溫。"
            "這種情況容易讓市場擔心通膨降溫不順，對風險資產會形成一定壓力。"
        )

    # 明確降溫
    else:
        status = "通膨降溫"
        score = cool_score
        summary = (
            f"{name} 最新資料日期為 {latest_date}。"
            f"年增率約 {fmt_pct(yoy)}，月增率約 {fmt_pct(mom)}，顯示通膨壓力相對降溫。"
            "通膨降溫通常會提高市場對 Fed 降息或政策轉向寬鬆的期待，"
            "有利於科技股與加密貨幣等風險資產。"
        )

    return {
        "name": name,
        "status": status,
        "score": score,
        "summary": summary,
        "latest_date": latest_date,
        "mom": mom,
        "yoy": yoy,
    }


def build_nfp_judgement(data):
    if not data:
        return {
            "name": "NFP 非農就業",
            "status": "無資料",
            "score": 0,
            "summary": "NFP 目前沒有取得 FRED 資料，暫時無法判斷。",
        }

    change = data.get("change")
    latest_date = data.get("latest_date")

    if change is None:
        return {
            "name": "NFP 非農就業",
            "status": "資料不足",
            "score": 0,
            "summary": "NFP 資料不足，暫時無法判斷。",
        }

    # PAYEMS 單位通常是千人，所以 178 = 178,000 人
    jobs_added = change * 1000

    if change >= 250:
        status = "就業過強"
        score = -1
        summary = (
            f"NFP 最新資料日期為 {latest_date}，新增就業約 {jobs_added:,.0f} 人。"
            "新增就業明顯偏強，代表勞動市場仍具韌性，可能讓 Fed 不急於降息，"
            "對風險資產形成一定壓力。"
        )
    elif change >= 100:
        status = "就業穩健"
        score = 0
        summary = (
            f"NFP 最新資料日期為 {latest_date}，新增就業約 {jobs_added:,.0f} 人。"
            "新增就業維持穩健，代表經濟仍有一定韌性。"
            "這不一定是利空，但若通膨同時偏熱，市場可能擔心 Fed 維持高利率更久。"
        )
    elif change >= 0:
        status = "就業降溫"
        score = 1
        summary = (
            f"NFP 最新資料日期為 {latest_date}，新增就業約 {jobs_added:,.0f} 人。"
            "新增就業放緩，代表勞動市場開始降溫，可能提高市場對降息的期待，"
            "對風險資產偏正面。"
        )
    else:
        status = "就業轉弱"
        score = -1
        summary = (
            f"NFP 最新資料日期為 {latest_date}，就業人數減少約 {abs(jobs_added):,.0f} 人。"
            "就業轉弱可能提高降息預期，但也可能引發市場對經濟衰退的擔憂，"
            "對風險資產不一定是單純利多。"
        )

    return {
        "name": "NFP 非農就業",
        "status": status,
        "score": score,
        "summary": summary,
        "latest_date": latest_date,
        "jobs_added": jobs_added,
    }


def build_unemployment_judgement(data):
    if not data:
        return {
            "name": "失業率",
            "status": "無資料",
            "score": 0,
            "summary": "失業率目前沒有取得 FRED 資料，暫時無法判斷。",
        }

    latest = data.get("latest_value")
    previous = data.get("previous_value")
    change = data.get("change")
    latest_date = data.get("latest_date")

    if latest is None or previous is None or change is None:
        return {
            "name": "失業率",
            "status": "資料不足",
            "score": 0,
            "summary": "失業率資料不足，暫時無法判斷。",
        }

    if change >= 0.2:
        status = "失業率上升"
        score = 1
        summary = (
            f"失業率最新資料日期為 {latest_date}，由 {previous:.1f}% 上升至 {latest:.1f}%。"
            "失業率上升代表勞動市場降溫，可能提高降息預期，短線對風險資產偏正面；"
            "但若升幅過快，也可能引發經濟衰退疑慮。"
        )
    elif change <= -0.2:
        status = "失業率下降"
        score = -1
        summary = (
            f"失業率最新資料日期為 {latest_date}，由 {previous:.1f}% 下降至 {latest:.1f}%。"
            "失業率下降代表勞動市場仍強，可能降低市場對快速降息的期待，"
            "對風險資產有一定壓制。"
        )
    else:
        status = "失業率變化不大"
        score = 0
        summary = (
            f"失業率最新資料日期為 {latest_date}，目前約 {latest:.1f}%，前值約 {previous:.1f}%。"
            "失業率變化不大，代表勞動市場暫時沒有明顯惡化或過熱，"
            "對市場影響偏中性。"
        )

    return {
        "name": "失業率",
        "status": status,
        "score": score,
        "summary": summary,
        "latest_date": latest_date,
        "latest_value": latest,
        "previous_value": previous,
        "change": change,
    }


def build_macro_latest():
    snapshot = build_fred_macro_snapshot()

    macro_latest = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "FRED",
        "indicators": {
            "cpi": build_inflation_judgement(
                "CPI 消費者物價指數",
                snapshot.get("cpi"),
                yoy_hot_level=3.0,
                mom_hot_level=0.3,
                severe_yoy_level=4.0,
                severe_mom_level=0.6,
                hot_score=-2,
                mild_hot_score=-1,
                cool_score=2,
            ),
            "ppi": build_inflation_judgement(
                "PPI 生產者物價指數",
                snapshot.get("ppi"),
                yoy_hot_level=3.0,
                mom_hot_level=0.4,
                severe_yoy_level=6.0,
                severe_mom_level=1.0,
                hot_score=-2,
                mild_hot_score=-1,
                cool_score=1,
            ),
             "pce": build_inflation_judgement(
                "PCE 個人消費支出物價指數",
                snapshot.get("pce"),
                yoy_hot_level=2.5,
                mom_hot_level=0.3,
                severe_yoy_level=3.5,
                severe_mom_level=0.6,
                hot_score=-2,
                mild_hot_score=-1,
                cool_score=2,
            ),
            "nfp": build_nfp_judgement(snapshot.get("nfp")),
            "unemployment": build_unemployment_judgement(snapshot.get("unemployment")),
        },
    }

    return macro_latest


def main():
    macro_latest = build_macro_latest()

    OUTPUT_PATH.write_text(
        json.dumps(macro_latest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"已更新宏觀快取：{OUTPUT_PATH}")

    for key, item in macro_latest["indicators"].items():
        print(key, item["status"], item["score"])


if __name__ == "__main__":
    main()
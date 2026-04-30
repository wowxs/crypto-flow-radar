from pathlib import Path
import json
import yfinance as yf
import webbrowser


from modules.fetch_crypto import get_crypto_data
from modules.fetch_macro import load_macro_base_data, build_market_macro_auto, get_macro_meta
from modules.scoring import (
    calculate_macro_score,
    calculate_crypto_flow_score,
    calculate_heat_risk_score,
    classify_market,
)
from modules.flow_model import analyze_flow_source
from modules.narrative import build_final_narrative, build_today_summary
from modules.html_builder import build_html
# =========================
# 基本設定
# =========================

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

REPORT_PATH = OUTPUT_DIR / "crypto_flow_radar.html"


# =========================
# 主程式
# =========================

def main():
    print("Crypto Flow Radar V1 正在抓取資料...")

    crypto = get_crypto_data()

    macro_input = load_macro_base_data()
    macro_meta = get_macro_meta()

    auto_macro = build_market_macro_auto()
    macro_input.update(auto_macro)

    macro_score, macro_details = calculate_macro_score(macro_input)
    flow_score, flow_reasons = calculate_crypto_flow_score(crypto)
    heat_score, heat_warnings = calculate_heat_risk_score(crypto)
    flow_source = analyze_flow_source(crypto)

    total_score = macro_score + flow_score - heat_score
    market_state = classify_market(total_score)

    final_narrative = build_final_narrative(
        macro_score,
        flow_score,
        heat_score,
        market_state,
    )

    today_summary = build_today_summary(
        macro_score=macro_score,
        flow_score=flow_score,
        heat_score=heat_score,
        total_score=total_score,
        market_state=market_state,
        flow_source=flow_source,
        heat_warnings=heat_warnings,
    )

    html = build_html(
    crypto=crypto,
    macro_details=macro_details,
    macro_score=macro_score,
    flow_score=flow_score,
    flow_reasons=flow_reasons,
    heat_score=heat_score,
    heat_warnings=heat_warnings,
    flow_source=flow_source,
    today_summary=today_summary,
    macro_meta=macro_meta,
    total_score=total_score,
    market_state=market_state,
    final_narrative=final_narrative,
    )

    REPORT_PATH.write_text(html, encoding="utf-8")

    print("完成！")
    print(f"報告已輸出：{REPORT_PATH}")

    report_full_path = REPORT_PATH.resolve()
    webbrowser.open(report_full_path.as_uri())
    print("已自動開啟報告。")

if __name__ == "__main__":
    main()
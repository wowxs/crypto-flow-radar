import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


from config import APP_NAME, APP_VERSION, APP_SUBTITLE, REPORT_DISCLAIMER, DATA_SOURCES
from modules.utils import DATA_SOURCE_STATUS
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



def fmt_usd_short(value):
    if value is None:
        return "無資料"

    try:
        value = float(value)
    except Exception:
        return "無資料"

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B 美元"
    elif value >= 10_000_000:
        return f"{value / 10_000_000:.2f} 千萬美元"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f} 百萬美元"
    else:
        return f"{value:,.0f} 美元"


def fmt_pct_short(value):
    if value is None:
        return "無資料"

    try:
        value = float(value)
    except Exception:
        return "無資料"

    return f"{value:.2f}%"


st.set_page_config(
    page_title="Crypto Flow Radar",
    page_icon="📡",
    layout="wide",
)



PROJECT_ROOT = Path(__file__).resolve().parent
HTML_REPORT_PATH = PROJECT_ROOT / "output" / "crypto_flow_radar.html"
SECTOR_WATCHLIST_PATH = PROJECT_ROOT / "sector_watchlist.json"
SECTOR_WATCHLIST_DRAFT_PATH = PROJECT_ROOT / "data" / "processed" / "sector_watchlist_draft.json"

def run_macro_update():
    script_path = PROJECT_ROOT / "update_macro_data.py"

    if not script_path.exists():
        return False, "找不到 update_macro_data.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output = ""

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += "\n[錯誤輸出]\n" + result.stderr

    if result.returncode != 0:
        return False, output or f"更新失敗，return code = {result.returncode}"

    return True, output or "宏觀資料更新完成。"

def run_html_report():
    script_path = PROJECT_ROOT / "app.py"

    if not script_path.exists():
        return False, "找不到 app.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output = ""

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += "\n[錯誤輸出]\n" + result.stderr

    if result.returncode != 0:
        return False, output or f"HTML 報告產生失敗，return code = {result.returncode}"

    return True, output or "HTML 報告產生完成。"

def run_full_update():
    """
    Streamlit 版一鍵完整更新：
    1. 更新 FRED 宏觀快取
    2. 清除 Streamlit 快取
    3. 重新載入頁面
    """
    ok_macro, macro_message = run_macro_update()

    if not ok_macro:
        return False, "宏觀資料更新失敗：\n" + macro_message

    return True, "完整資料更新完成。\n\n" + macro_message

def get_html_report_bytes():
    if not HTML_REPORT_PATH.exists():
        return None

    try:
        return HTML_REPORT_PATH.read_bytes()
    except Exception:
        return None

def load_sector_watchlist_for_ui():
    if not SECTOR_WATCHLIST_PATH.exists():
        return {}

    try:
        with SECTOR_WATCHLIST_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
    
def save_sector_watchlist_draft(data):
    try:
        SECTOR_WATCHLIST_DRAFT_PATH.parent.mkdir(parents=True, exist_ok=True)

        with SECTOR_WATCHLIST_DRAFT_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True, f"已儲存草稿：{SECTOR_WATCHLIST_DRAFT_PATH}"
    except Exception as e:
        return False, f"儲存草稿失敗：{e}"

def apply_sector_watchlist_draft():
    if not SECTOR_WATCHLIST_DRAFT_PATH.exists():
        return False, "找不到草稿檔：data/processed/sector_watchlist_draft.json"

    try:
        with SECTOR_WATCHLIST_DRAFT_PATH.open("r", encoding="utf-8") as f:
            draft = json.load(f)

        if not isinstance(draft, dict) or not draft:
            return False, "草稿檔格式不正確或內容為空。"

        backup_dir = PROJECT_ROOT / "stable_backup"
        backup_dir.mkdir(exist_ok=True)

        backup_path = backup_dir / f"sector_watchlist_backup_before_apply_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        if SECTOR_WATCHLIST_PATH.exists():
            original_text = SECTOR_WATCHLIST_PATH.read_text(encoding="utf-8")
            backup_path.write_text(original_text, encoding="utf-8")

        SECTOR_WATCHLIST_PATH.write_text(
            json.dumps(draft, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return True, f"已套用草稿到正式清單，並備份原檔至：{backup_path}"

    except Exception as e:
        return False, f"套用草稿失敗：{e}"

@st.cache_data(ttl=300)
def load_dashboard_data():
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

    return {
        "crypto": crypto,
        "macro_meta": macro_meta,
        "macro_score": macro_score,
        "macro_details": macro_details,
        "flow_score": flow_score,
        "flow_reasons": flow_reasons,
        "heat_score": heat_score,
        "heat_warnings": heat_warnings,
        "flow_source": flow_source,
        "total_score": total_score,
        "market_state": market_state,
        "final_narrative": final_narrative,
        "today_summary": today_summary,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


st.title(f"📡 {APP_NAME} 加密資金流雷達")
st.caption(f"{APP_VERSION}｜{APP_SUBTITLE}")

col_a, col_b = st.columns([1, 1])

with col_a:
    if st.button("🔄 重新整理資料", use_container_width=True, key="btn_top_refresh"):
        st.cache_data.clear()
        st.rerun()

with col_b:
    st.info("目前為 Streamlit Web 測試版，結果僅用於市場環境判讀，不構成投資建議。")

data = load_dashboard_data()

macro_meta = data["macro_meta"]

with st.sidebar:
    st.header("📡 Crypto Flow Radar")

    st.write(f"**版本：** {APP_VERSION}")
    st.write(f"**資料更新時間：** {data['updated_at']}")
    st.write("**Streamlit 快取：** 300 秒")

    st.divider()

    st.subheader("宏觀資料")
    st.write(f"**來源：** {macro_meta.get('source', '無資料')}")
    st.write(f"**更新時間：** {macro_meta.get('generated_at', '無資料')}")
    st.write(f"**讀取模式：** {macro_meta.get('mode', '無資料')}")

    st.divider()

    st.subheader("資料來源")
    for source in DATA_SOURCES:
        st.write(f"- {source}")

    st.divider()

    if st.button("🚀 一鍵更新全部資料", use_container_width=True, key="btn_full_update"):
        with st.spinner("正在更新全部資料..."):
            ok, message = run_full_update()

        if ok:
            st.success("完整資料更新完成")
            st.text(message)
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("完整資料更新失敗")
            st.text(message)

    if st.button("📥 更新 FRED 宏觀資料", use_container_width=True, key="btn_update_fred"):
        with st.spinner("正在更新 FRED 宏觀資料..."):
            ok, message = run_macro_update()

        if ok:
            st.success("FRED 宏觀資料更新完成")
            st.text(message)
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("FRED 宏觀資料更新失敗")
            st.text(message)

    if st.button("📄 產生 HTML 報告", use_container_width=True, key="btn_generate_html"):
        with st.spinner("正在產生 HTML 報告..."):
            ok, message = run_html_report()

        if ok:
            st.success("HTML 報告產生完成")
            st.text(message)
            st.info("報告位置：output/crypto_flow_radar.html")
        else:
            st.error("HTML 報告產生失敗")
            st.text(message)

    html_bytes = get_html_report_bytes()

    if html_bytes:
        st.download_button(
            label="⬇️ 下載 HTML 報告",
            data=html_bytes,
            file_name="crypto_flow_radar.html",
            mime="text/html",
            use_container_width=True,
            key="btn_download_html",
        )
    else:
        st.caption("尚未偵測到 HTML 報告。可先按「產生 HTML 報告」。")

    if st.button("🔄 清除快取並重新整理", use_container_width=True, key="btn_sidebar_clear_cache"):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    st.subheader("使用方式")
    st.write("本頁會自動讀取目前專案資料與 API 資料。")
    st.code("streamlit run streamlit_app.py")

    st.divider()

    st.caption(REPORT_DISCLAIMER)

tab_overview, tab_macro, tab_flow, tab_sector, tab_watchlist, tab_charts, tab_status = st.tabs([
    "總覽",
    "宏觀",
    "資金流",
    "板塊",
    "代表幣清單",
    "圖表",
    "資料狀態",
])

summary = data["today_summary"]
market_state = data["market_state"]
flow_source = data["flow_source"]
crypto = data["crypto"]

btc = crypto["btc"]
eth = crypto["eth"]
fg = crypto["fear_greed"]

categories = crypto.get("categories", {})
top_categories = categories.get("top_categories", [])
weak_categories = categories.get("weak_categories", [])
sector_validation = crypto.get("sector_validation", {})

with tab_overview:
    st.subheader("今日重點摘要")

    info1, info2, info3 = st.columns(3)

    info1.info(f"頁面資料載入時間：{data['updated_at']}")
    info2.info(f"宏觀快取時間：{macro_meta.get('generated_at', '無資料')}")
    info3.info("Streamlit 快取：300 秒")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("市場總分", data["total_score"])
    c2.metric("市場狀態", summary.get("market_status", "無資料"))
    c3.metric("主要推動來源", summary.get("main_source", "無資料"))
    c4.metric("行情健康程度", summary.get("health", "無資料"))

    st.write("**一句話判讀**")
    st.write(summary.get("one_liner", ""))

    st.write("**策略環境**")
    st.write(summary.get("strategy_text", ""))

    st.write("**風險提醒**")
    st.warning(summary.get("risk_text", ""))

    st.divider()

    st.subheader("分數拆解")

    s1, s2, s3 = st.columns(3)

    s1.metric("宏觀分數", data["macro_score"])
    s2.metric("資金流分數", data["flow_score"])
    s3.metric("過熱風險", data["heat_score"])

    st.caption(f"資料更新時間：{data['updated_at']}")

    st.divider()

    st.subheader("加密市場即時資料")

    m1, m2, m3, m4 = st.columns(4)

    m1.metric("BTC 價格", f"{btc.get('price', 0):,.2f}", f"{btc.get('price_change_pct', 0):.2f}%")
    m2.metric("ETH 價格", f"{eth.get('price', 0):,.2f}", f"{eth.get('price_change_pct', 0):.2f}%")
    m3.metric("恐懼貪婪", fg.get("value", "無資料"), fg.get("classification", ""))
    m4.metric("BTC Funding", f"{(btc.get('funding') or 0) * 100:.4f}%")

with tab_macro:
    st.subheader("宏觀判讀區")

    macro_meta = data["macro_meta"]
    macro_details = data["macro_details"]

    meta_col1, meta_col2, meta_col3 = st.columns(3)

    meta_col1.metric("宏觀資料來源", macro_meta.get("source", "無資料"))
    meta_col2.metric("宏觀更新時間", macro_meta.get("generated_at", "無資料"))
    meta_col3.metric("讀取模式", macro_meta.get("mode", "無資料"))

    st.caption(
        "這一區用來判斷大環境對風險資產的影響。重點不是單看某一個數字，"
        "而是理解數據如何影響 Fed 預期、美元、美債殖利率與市場風險偏好。"
    )

    macro_df = pd.DataFrame(macro_details)

    if not macro_df.empty:
        macro_df = macro_df.rename(columns={
            "name": "指標",
            "status": "狀態",
            "score": "分數",
            "summary": "因果解讀",
        })

        st.dataframe(
            macro_df[["指標", "狀態", "分數"]],
            use_container_width=True,
            hide_index=True,
        )

        st.write("### 宏觀因果解讀")

        for item in macro_details:
            name = item.get("name", "未知指標")
            status = item.get("status", "無資料")
            score = item.get("score", 0)
            summary_text = item.get("summary", "")

            with st.expander(f"{name}｜{status}｜分數 {score}", expanded=False):
                st.write(summary_text)
    else:
        st.warning("目前沒有宏觀判讀資料。")

    st.divider()

    st.subheader("宏觀總結")

    if data["macro_score"] >= 3:
        st.success("宏觀環境目前偏支持風險資產。")
    elif data["macro_score"] <= -2:
        st.error("宏觀環境目前對風險資產仍有壓力。")
    else:
        st.info("宏觀環境目前偏中性，市場可能更受加密內部資金流影響。")

with tab_flow:
    st.subheader("加密資金流判讀區")

    flow_col1, flow_col2 = st.columns(2)

    with flow_col1:
        st.metric("資金流分數", data["flow_score"])

        st.write("**資金流判讀理由**")
        for reason in data["flow_reasons"]:
            st.write(f"- {reason}")

    with flow_col2:
        st.metric("過熱風險分數", data["heat_score"])

        st.write("**過熱警示**")
        for warning in data["heat_warnings"]:
            if data["heat_score"] >= 4:
                st.error(warning)
            elif data["heat_score"] >= 2:
                st.warning(warning)
            else:
                st.info(warning)

    st.divider()

    st.subheader("資金流來源模型")

    flow_source = data["flow_source"]

    fs1, fs2, fs3, fs4 = st.columns(4)

    fs1.metric("現貨買盤", flow_source.get("spot_score", 0))
    fs2.metric("合約槓桿", flow_source.get("leverage_score", 0))
    fs3.metric("市場情緒", flow_source.get("sentiment_score", 0))
    fs4.metric("板塊輪動", flow_source.get("sector_score", 0))

    st.write("**主要推動來源**")
    st.info(flow_source.get("main_source", "無資料"))

    st.write("**行情健康程度**")
    health = flow_source.get("health", "無資料")

    if health in ["健康", "輪動健康"]:
        st.success(health)
    elif health in ["偏槓桿", "情緒偏熱"]:
        st.warning(health)
    elif health in ["資金不足"]:
        st.error(health)
    else:
        st.info(health)

    st.write("**模型判讀**")
    st.write(flow_source.get("narrative", ""))

    st.write("**細節訊號**")
    notes = flow_source.get("notes", [])

    if notes:
        for note in notes:
            st.write(f"- {note}")
    else:
        st.write("- 目前沒有明顯資金來源訊號。")
# ===== 板塊 Tab =====
with tab_sector:
    st.subheader("板塊交叉驗證雷達")

    st.caption(
        "本區使用 CoinGecko 第三方分類資料作為市場分類參考，"
        "並搭配 Binance 代表幣 24H 交易資料進行交叉驗證。"
        "可信度越高，代表第三方分類與代表幣追蹤方向越一致。"
    )

    st.write(sector_validation.get("summary", ""))

    sector_rows = sector_validation.get("rows", [])

    if sector_rows:
        sector_df = pd.DataFrame(sector_rows)

        sector_view = sector_df.rename(columns={
            "name": "主題",
            "coingecko_status": "CoinGecko 分類",
            "coingecko_change": "CoinGecko 漲跌",
            "watchlist_status": "代表幣追蹤",
            "watchlist_change": "代表幣漲跌",
            "coin_count": "代表幣數",
            "positive_count": "上漲數",
            "negative_count": "下跌數",
            "consistency": "一致性",
            "confidence": "可信度",
            "final_status": "綜合狀態",
        })

        show_cols = [
            "主題",
            "CoinGecko 分類",
            "CoinGecko 漲跌",
            "代表幣追蹤",
            "代表幣漲跌",
            "代表幣數",
            "上漲數",
            "下跌數",
            "一致性",
            "可信度",
            "綜合狀態",
        ]

        st.dataframe(
            sector_view[show_cols],
            use_container_width=True,
            hide_index=True,
        )

        st.write("### 板塊詳細解讀")

        for item in sector_rows:
            name = item.get("name", "未知主題")
            confidence = item.get("confidence", "無資料")
            final_status = item.get("final_status", "觀察中")

            with st.expander(f"{name}｜{final_status}｜可信度 {confidence}", expanded=False):
                st.write(f"**CoinGecko 分類狀態：** {item.get('coingecko_status', '無資料')}")
                st.write(f"**CoinGecko 對應分類：** {item.get('coingecko_category', '無')}")
                st.write(f"**CoinGecko 24H 漲跌：** {item.get('coingecko_change', '無資料')}")
                st.write(f"**代表幣追蹤狀態：** {item.get('watchlist_status', '無資料')}")
                st.write(f"**代表幣加權漲跌：** {item.get('watchlist_change', '無資料')}")
                st.write(f"**代表幣成交額：** {item.get('watchlist_volume', 0):,.0f}")
                st.write(f"**代表幣數：** {item.get('coin_count', 0)}")
                st.write(f"**上漲 / 下跌：** {item.get('positive_count', 0)} / {item.get('negative_count', 0)}")
                st.write(f"**一致性：** {item.get('consistency', '無資料')}")
                st.write(f"**可信度：** {item.get('confidence', '無資料')}")
    else:
        st.warning("目前沒有板塊交叉驗證資料。")

    st.divider()

    st.subheader("板塊輪動雷達")

    st.caption(
        "此區顯示 CoinGecko 第三方分類資料經過過濾後的板塊輪動狀況。"
        "此資料適合作為市場熱度參考，不應單獨視為真實資金流入證明。"
    )

    st.write(categories.get("summary", ""))

    col_top, col_weak = st.columns(2)

    with col_top:
        st.write("### 強勢板塊 Top 8")

        if top_categories:
            top_df = pd.DataFrame(top_categories)

            top_view = top_df.rename(columns={
                "name": "板塊",
                "market_cap": "市值",
                "volume_24h": "24H 成交量",
                "change_24h": "24H 漲跌",
            })

            top_view["市值"] = top_view["市值"].apply(fmt_usd_short)
            top_view["24H 成交量"] = top_view["24H 成交量"].apply(fmt_usd_short)
            top_view["24H 漲跌"] = top_view["24H 漲跌"].apply(fmt_pct_short)

            st.dataframe(
                top_view[["板塊", "市值", "24H 成交量", "24H 漲跌"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("目前沒有強勢板塊資料。")

    with col_weak:
        st.write("### 弱勢板塊 Top 5")

        if weak_categories:
            weak_df = pd.DataFrame(weak_categories)

            weak_view = weak_df.rename(columns={
                "name": "板塊",
                "market_cap": "市值",
                "volume_24h": "24H 成交量",
                "change_24h": "24H 漲跌",
            })

            weak_view["市值"] = weak_view["市值"].apply(fmt_usd_short)
            weak_view["24H 成交量"] = weak_view["24H 成交量"].apply(fmt_usd_short)
            weak_view["24H 漲跌"] = weak_view["24H 漲跌"].apply(fmt_pct_short)

            st.dataframe(
                weak_view[["板塊", "市值", "24H 成交量", "24H 漲跌"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.warning("目前沒有弱勢板塊資料。")

# ===== 代表幣清單 Tab =====
with tab_watchlist:
    st.subheader("代表幣追蹤清單")

    st.caption(
        "這一區顯示目前 sector_watchlist.json 中設定的代表幣追蹤清單。"
        "代表幣追蹤用於輔助驗證 CoinGecko 第三方分類，不代表官方板塊定義。"
    )

    watchlist = load_sector_watchlist_for_ui()

    if not watchlist:
        st.warning("目前沒有讀取到 sector_watchlist.json。")
    else:
        rows = []

        for key, item in watchlist.items():
            rows.append({
                "代號": key,
                "主題名稱": item.get("name", key),
                "CoinGecko 關鍵字": "、".join(item.get("coingecko_keywords", [])),
                "代表幣": "、".join(item.get("symbols", [])),
                "代表幣數": len(item.get("symbols", [])),
            })

        watchlist_df = pd.DataFrame(rows)

        st.dataframe(
            watchlist_df,
            use_container_width=True,
            hide_index=True,
        )

        st.write("### 詳細清單")

        for key, item in watchlist.items():
            name = item.get("name", key)
            symbols = item.get("symbols", [])
            keywords = item.get("coingecko_keywords", [])

            with st.expander(f"{name}｜{len(symbols)} 檔代表幣", expanded=False):
                st.write("**CoinGecko 關鍵字：**")
                st.write("、".join(keywords) if keywords else "無")

                st.write("**代表幣：**")
                st.code(", ".join(symbols))

        st.divider()

        st.subheader("代表幣清單編輯草稿")

        st.caption(
            "這裡可以建立修改草稿，但不會直接覆蓋正式 sector_watchlist.json。"
            "輸出後請先檢查 data/processed/sector_watchlist_draft.json，確認沒問題再手動替換正式檔案。"
        )

        selected_key = st.selectbox(
            "選擇要建立草稿的主題",
            options=list(watchlist.keys()),
            format_func=lambda k: watchlist[k].get("name", k),
            key="watchlist_edit_select",
        )

        selected_item = watchlist[selected_key]

        new_name = st.text_input(
            "主題名稱",
            value=selected_item.get("name", selected_key),
            key="watchlist_edit_name",
        )

        new_keywords_text = st.text_area(
            "CoinGecko 關鍵字，用逗號分隔",
            value=", ".join(selected_item.get("coingecko_keywords", [])),
            key="watchlist_edit_keywords",
        )

        new_symbols_text = st.text_area(
            "代表幣交易對，用逗號分隔，例如 FETUSDT, WLDUSDT, RENDERUSDT",
            value=", ".join(selected_item.get("symbols", [])),
            key="watchlist_edit_symbols",
        )

        if st.button("💾 儲存為草稿", use_container_width=True, key="btn_save_watchlist_draft"):
            draft = dict(watchlist)

            new_keywords = [
                x.strip()
                for x in new_keywords_text.split(",")
                if x.strip()
            ]

            new_symbols = [
                x.strip().upper()
                for x in new_symbols_text.split(",")
                if x.strip()
            ]

            draft[selected_key] = {
                "name": new_name.strip() or selected_key,
                "coingecko_keywords": new_keywords,
                "symbols": new_symbols,
            }

            ok, message = save_sector_watchlist_draft(draft)

            if ok:
                st.success(message)
                st.info("這只是草稿，尚未覆蓋正式 sector_watchlist.json。")
            else:
                st.error(message)
                st.divider()

        st.subheader("套用草稿到正式清單")

        st.caption(
            "此操作會把 data/processed/sector_watchlist_draft.json 套用到正式 sector_watchlist.json。"
            "系統會先自動備份目前正式清單到 stable_backup，再進行覆蓋。"
        )

        if SECTOR_WATCHLIST_DRAFT_PATH.exists():
            st.success("已偵測到草稿檔，可以套用。")
        else:
            st.info("目前尚未偵測到草稿檔。請先儲存草稿。")

        confirm_apply = st.checkbox(
            "我確認要用草稿覆蓋正式代表幣清單",
            key="confirm_apply_watchlist_draft",
        )

        if st.button(
            "✅ 套用草稿到正式清單",
            use_container_width=True,
            key="btn_apply_watchlist_draft",
            disabled=not confirm_apply,
        ):
            ok, message = apply_sector_watchlist_draft()

            if ok:
                st.success(message)
                st.cache_data.clear()
                st.info("請按左側「清除快取並重新整理」，或重新整理頁面，讓新清單生效。")
            else:
                st.error(message)


# ===== 圖表 Tab =====

with tab_charts:
    st.subheader("圖表總覽")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.write("### 資金流來源模型分數")

        flow_labels = ["現貨買盤", "合約槓桿", "市場情緒", "板塊輪動"]
        flow_values = [
            flow_source.get("spot_score", 0),
            flow_source.get("leverage_score", 0),
            flow_source.get("sentiment_score", 0),
            flow_source.get("sector_score", 0),
        ]

        fig_flow = go.Figure()
        fig_flow.add_trace(go.Bar(
            x=flow_labels,
            y=flow_values,
            text=flow_values,
            textposition="auto",
        ))

        fig_flow.update_layout(
            height=360,
            margin=dict(l=20, r=20, t=30, b=40),
            yaxis_title="分數",
        )

        st.plotly_chart(fig_flow, use_container_width=True)

    with chart_col2:
        st.write("### BTC / ETH Funding 對比")

        funding_labels = ["BTC Funding", "ETH Funding"]
        funding_values = [
            (btc.get("funding") or 0) * 100,
            (eth.get("funding") or 0) * 100,
        ]

        fig_funding = go.Figure()
        fig_funding.add_trace(go.Bar(
            x=funding_labels,
            y=funding_values,
            text=[f"{v:.4f}%" for v in funding_values],
            textposition="auto",
        ))

        fig_funding.update_layout(
            height=360,
            margin=dict(l=20, r=20, t=30, b=40),
            yaxis_title="Funding Rate (%)",
        )

        st.plotly_chart(fig_funding, use_container_width=True)

    st.write("### 強勢板塊 Top 8｜24H 漲跌")

    if top_categories:
        names = [x["name"] for x in top_categories[:8]]
        changes = [x["change_24h"] for x in top_categories[:8]]

        fig_sector = go.Figure()
        fig_sector.add_trace(go.Bar(
            x=changes,
            y=names,
            orientation="h",
            text=[f"{v:.2f}%" for v in changes],
            textposition="auto",
        ))

        fig_sector.update_layout(
            height=460,
            margin=dict(l=140, r=20, t=30, b=40),
            xaxis_title="24H 漲跌幅 (%)",
            yaxis=dict(autorange="reversed"),
        )

        st.plotly_chart(fig_sector, use_container_width=True)
    else:
        st.warning("目前沒有板塊資料可產生圖表。")
# ===== 資料狀態 Tab =====
with tab_status:
    st.subheader("資料來源狀態")

    st.info(
        f"頁面資料載入時間：{data['updated_at']}｜"
        f"宏觀資料來源：{macro_meta.get('source', '無資料')}｜"
        f"宏觀快取時間：{macro_meta.get('generated_at', '無資料')}｜"
        "Streamlit 快取 TTL：300 秒"
    )

    st.caption(
        "這一區用來檢查各資料來源是否正常。若某個來源異常，報告仍可能輸出，"
        "但相關判讀需要保守看待。"
    )

    if DATA_SOURCE_STATUS:
        source_rows = []

        for source_name, info in DATA_SOURCE_STATUS.items():
            source_rows.append({
                "資料來源": source_name,
                "狀態": "正常" if info.get("ok") else "異常",
                "訊息": info.get("message", ""),
                "時間": info.get("time", ""),
            })

        source_df = pd.DataFrame(source_rows)

        st.dataframe(
            source_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("目前尚未記錄資料來源狀態。")
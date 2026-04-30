from datetime import datetime
from config import APP_NAME, APP_VERSION, APP_SUBTITLE, REPORT_DISCLAIMER, DATA_SOURCES

from modules.utils import (
    DATA_SOURCE_STATUS,
    fmt_price,
    fmt_pct,
    fmt_number,
    fmt_usd,
    fmt_change,
    score_class,
    risk_class,
    market_score_class,
    change_class,
    funding_class,
)

from modules.charts import (
    build_category_chart,
    build_flow_source_chart,
    build_funding_chart,
)

def build_html(
    crypto,
    macro_details,
    macro_score,
    flow_score,
    flow_reasons,
    heat_score,
    heat_warnings,
    flow_source,
    today_summary,
    macro_meta,
    total_score,
    market_state,
    final_narrative,
):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_sources_text = " / ".join(DATA_SOURCES)
    btc = crypto["btc"]
    eth = crypto["eth"]
    fg = crypto["fear_greed"]
    categories = crypto.get("categories", {})
    sector_validation = crypto.get("sector_validation", {})
    total_score_cls = market_score_class(total_score)
    macro_score_cls = score_class(macro_score)
    flow_score_cls = score_class(flow_score)
    heat_score_cls = risk_class(heat_score)
    summary_risk_cls = risk_class(today_summary.get("heat_score", 0))
    summary_total_cls = market_score_class(today_summary.get("total_score", 0))
    btc_change_cls = change_class(btc.get("price_change_pct"))
    eth_change_cls = change_class(eth.get("price_change_pct"))

    btc_funding_cls = funding_class(btc.get("funding"))
    eth_funding_cls = funding_class(eth.get("funding"))
    macro_rows = ""
    for item in macro_details:
        macro_rows += f"""
        <tr>
            <td>{item['name']}</td>
            <td>{item['status']}</td>
            <td>{item['score']}</td>
            <td>{item['summary']}</td>
        </tr>
        """

    flow_list = "".join(f"<li>{r}</li>" for r in flow_reasons)
    warning_list = "".join(f"<li>{w}</li>" for w in heat_warnings)

    flow_source_notes = "".join(f"<li>{note}</li>" for note in flow_source.get("notes", []))

    if not flow_source_notes:
        flow_source_notes = "<li>目前沒有明顯資金來源訊號。</li>"  
    category_chart_html = build_category_chart(categories)
    flow_source_chart_html = build_flow_source_chart(flow_source)
    funding_chart_html = build_funding_chart(crypto)

    sector_validation_rows = ""

    for item in sector_validation.get("rows", []):
        confidence_cls = "good" if item.get("confidence") in ["高", "中高"] else "neutral"

        if item.get("confidence") == "低":
            confidence_cls = "bad"

        cg_change = item.get("coingecko_change")
        wl_change = item.get("watchlist_change")

        cg_change_text = "無資料" if cg_change is None else fmt_change(cg_change)
        wl_change_text = "無資料" if wl_change is None else fmt_change(wl_change)

        sector_validation_rows += f"""
        <tr>
            <td>{item.get("name", "")}</td>
            <td>{item.get("coingecko_status", "無資料")}<br><span class="label">{cg_change_text}</span></td>
            <td>{item.get("watchlist_status", "無資料")}<br><span class="label">{wl_change_text}</span></td>
            <td>{item.get("coin_count", 0)} 檔<br><span class="label">{item.get("positive_count", 0)} 漲 / {item.get("negative_count", 0)} 跌</span></td>
            <td>{item.get("consistency", "無資料")}</td>
            <td><span class="badge {confidence_cls}">{item.get("confidence", "無資料")}</span></td>
            <td>{item.get("final_status", "觀察中")}</td>
        </tr>
        """

    if not sector_validation_rows:
        sector_validation_rows = """
        <tr>
            <td colspan="7">目前沒有板塊交叉驗證資料。</td>
        </tr>
        """

    source_status_rows = ""

    for source_name, info in DATA_SOURCE_STATUS.items():
        status_text = "正常" if info.get("ok") else "異常"
        status_cls = "good" if info.get("ok") else "bad"

        source_status_rows += f"""
        <tr>
            <td>{source_name}</td>
            <td class="{status_cls}">{status_text}</td>
            <td>{info.get("message", "")}</td>
            <td>{info.get("time", "")}</td>
        </tr>
        """

    if not source_status_rows:
        source_status_rows = """
        <tr>
            <td colspan="4">目前尚未記錄資料來源狀態。</td>
        </tr>
        """

    category_rows = ""

    for item in categories.get("top_categories", []):
        cat_change_cls = "positive" if item["change_24h"] >= 0 else "danger"

        category_rows += f"""
        <tr>
        <td>{item['name']}</td>
        <td>{fmt_usd(item['market_cap'])}</td>
        <td>{fmt_usd(item['volume_24h'])}</td>
        <td class="{cat_change_cls}">{fmt_change(item['change_24h'])}</td>
    </tr>
    """

    weak_category_rows = ""

    for item in categories.get("weak_categories", []):
        weak_change_cls = "positive" if item["change_24h"] >= 0 else "danger"

        weak_category_rows += f"""
        <tr>
        <td>{item['name']}</td>
        <td>{fmt_usd(item['market_cap'])}</td>
        <td>{fmt_usd(item['volume_24h'])}</td>
        <td class="{weak_change_cls}">{fmt_change(item['change_24h'])}</td>
    </tr>
    """

    if not category_rows:
        category_rows = """
        <tr>
            <td colspan="4">目前沒有取得板塊資料，可能是 CoinGecko API 暫時限制或網路問題。</td>
        </tr>
        """

    if not weak_category_rows:
        weak_category_rows = """
        <tr>
            <td colspan="4">目前沒有取得弱勢板塊資料。</td>
        </tr>
        """


    html = f"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <title>Crypto Flow Radar 加密資金流雷達</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        body {{
            font-family: "Microsoft JhengHei", Arial, sans-serif;
            background: #0f172a;
            color: #e5e7eb;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 1180px;
            margin: auto;
            padding: 28px;
        }}
        .hero {{
            background: linear-gradient(135deg, #1e293b, #111827);
            border: 1px solid #334155;
            border-radius: 18px;
            padding: 28px;
            margin-bottom: 20px;
        }}
        h1 {{
            margin: 0 0 8px 0;
            font-size: 34px;
        }}
        .subtitle {{
            color: #94a3b8;
            font-size: 16px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }}
        .card {{
            background: #111827;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 18px;
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 20px;
            color: #f8fafc;
        }}
        .big-score {{
            font-size: 46px;
            font-weight: bold;
            color: #38bdf8;
        }}
        .status {{
            font-size: 24px;
            font-weight: bold;
            color: #facc15;
        }}
        .label {{
            color: #94a3b8;
            font-size: 14px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
        }}
        th, td {{
            border-bottom: 1px solid #334155;
            padding: 10px;
            text-align: left;
            vertical-align: top;
        }}
        th {{
            color: #cbd5e1;
            background: #1e293b;
        }}
        ul {{
            line-height: 1.8;
        }}
        .narrative {{
            white-space: pre-line;
            line-height: 1.9;
            color: #e2e8f0;
        }}
        .positive {{
            color: #86efac;
        }}
        .warning {{
            color: #fde68a;
        }}
        .danger {{
            color: #fca5a5;
        }}

                .good {{
            color: #86efac;
        }}

        .neutral {{
            color: #fde68a;
        }}

        .bad {{
            color: #fca5a5;
        }}

        .badge {{
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: bold;
            border: 1px solid #334155;
            background: #1e293b;
        }}

        .badge.good {{
            background: rgba(34, 197, 94, 0.12);
            border-color: rgba(34, 197, 94, 0.45);
            color: #86efac;
        }}

        .badge.neutral {{
            background: rgba(250, 204, 21, 0.12);
            border-color: rgba(250, 204, 21, 0.45);
            color: #fde68a;
        }}

        .badge.bad {{
            background: rgba(248, 113, 113, 0.12);
            border-color: rgba(248, 113, 113, 0.45);
            color: #fca5a5;
        }}

        .metric-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 10px 0;
            border-bottom: 1px solid #1f2937;
        }}

        .metric-row:last-child {{
            border-bottom: none;
        }}

        .metric-name {{
            color: #94a3b8;
        }}

        .metric-value {{
            font-size: 20px;
            font-weight: bold;
        }}

        .section-note {{
            color: #94a3b8;
            font-size: 14px;
            line-height: 1.7;
        }}

        .mini-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-top: 12px;
        }}

        .mini-card {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 14px;
        }}

        .mini-card .label {{
            margin-bottom: 6px;
        }}
        .footer {{
            color: #64748b;
            font-size: 13px;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
<div class="container">

    <div class="hero">
        <h1>{APP_NAME} 加密資金流雷達 <span class="badge neutral">{APP_VERSION}</span></h1>
        <div class="subtitle">{APP_SUBTITLE}</div>
        <p>不是告訴你能不能進場，而是告訴你現在適合用什麼方式進場。</p>
        <div class="label">更新時間：{now}</div>
    </div>

    <div class="card">
        <h2>今日重點摘要</h2>
        <p class="section-note">
            這一區會把整份報告濃縮成第一眼可以理解的市場狀態、資金來源、風險與策略環境。
        </p>

        <div class="mini-grid">
            <div class="mini-card">
                <div class="label">今日市場狀態</div>
                <div class="status">{today_summary.get("market_status", "無資料")}</div>
            </div>

            <div class="mini-card">
                <div class="label">市場總分</div>
                <div class="big-score {summary_total_cls}">{today_summary.get("total_score", 0)}</div>
            </div>

            <div class="mini-card">
                <div class="label">主要推動來源</div>
                <div class="status">{today_summary.get("main_source", "無資料")}</div>
            </div>

            <div class="mini-card">
                <div class="label">行情健康程度</div>
                <div class="status">{today_summary.get("health", "無資料")}</div>
            </div>

            <div class="mini-card">
                <div class="label">主要風險等級</div>
                <div class="badge {summary_risk_cls}">{today_summary.get("risk_level", "無資料")}</div>
            </div>

            <div class="mini-card">
                <div class="label">主要風險點</div>
                <div>{today_summary.get("risk_points", "無資料")}</div>
            </div>
        </div>

        <h3>一句話判讀</h3>
        <div class="narrative">{today_summary.get("one_liner", "")}</div>

        <h3>策略環境</h3>
        <div class="narrative">{today_summary.get("strategy_text", "")}</div>

        <h3>風險提醒</h3>
        <div class="narrative">{today_summary.get("risk_text", "")}</div>
    </div>    

        <div class="grid">
        <div class="card">
            <h2>市場總分</h2>
            <div class="big-score {total_score_cls}">{total_score}</div>
            <div class="badge {total_score_cls}">{market_state['status']}</div>
            <div class="label" style="margin-top:10px;">宏觀分數 + 資金流分數 - 過熱風險</div>
        </div>

        <div class="card">
            <h2>分數拆解</h2>
            <div class="metric-row">
                <span class="metric-name">宏觀分數</span>
                <span class="metric-value {macro_score_cls}">{macro_score}</span>
            </div>
            <div class="metric-row">
                <span class="metric-name">資金流分數</span>
                <span class="metric-value {flow_score_cls}">{flow_score}</span>
            </div>
            <div class="metric-row">
                <span class="metric-name">過熱風險</span>
                <span class="metric-value {heat_score_cls}">{heat_score}</span>
            </div>
        </div>

        <div class="card">
            <h2>策略環境</h2>
            <p>{market_state['strategy']}</p>
        </div>

        <div class="card">
            <h2>恐懼貪婪</h2>
            <div class="big-score">{fg.get("value", "無資料")}</div>
            <div class="badge neutral">{fg.get("classification", "無資料")}</div>
        </div>
    </div>

        <div class="card">
        <h2>圖表總覽</h2>
        <p class="section-note">
            這裡用視覺化方式快速觀察板塊輪動、資金流來源與 Funding 熱度。
            圖表不是買賣訊號，而是幫助你判斷市場結構。
        </p>

        <div class="mini-grid">
            <div class="mini-card">
                {flow_source_chart_html}
            </div>

            <div class="mini-card">
                {funding_chart_html}
            </div>
        </div>

        <div style="margin-top:16px;">
            {category_chart_html}
        </div>
    </div>
    <div class="card">
        <h2>加密市場即時資料</h2>
        <table>
            <tr>
                <th>標的</th>
                <th>價格</th>
                <th>24H 漲跌</th>
                <th>24H 成交額</th>
                <th>Funding</th>
                <th>OI 未平倉量</th>
            </tr>
            <tr>
                <td><strong>BTCUSDT</strong></td>
                <td>{fmt_price(btc['price'])}</td>
                <td class="{btc_change_cls}">{fmt_number(btc['price_change_pct'])}%</td>
                <td>{fmt_number(btc['quote_volume'])}</td>
                <td class="{btc_funding_cls}">{fmt_pct(btc['funding'])}</td>
                <td>{fmt_number(btc['oi'])}</td>
            </tr>
            <tr>
                <td><strong>ETHUSDT</strong></td>
                <td>{fmt_price(eth['price'])}</td>
                <td class="{eth_change_cls}">{fmt_number(eth['price_change_pct'])}%</td>
                <td>{fmt_number(eth['quote_volume'])}</td>
                <td class="{eth_funding_cls}">{fmt_pct(eth['funding'])}</td>
                <td>{fmt_number(eth['oi'])}</td>
            </tr>
        </table>
    </div>

    <div class="card">
        <h2>宏觀判讀區</h2>
        <p>
            這一區用來判斷大環境對風險資產的影響。重點不是單看某一個數字，
            而是理解數據如何影響 Fed 預期、美元、美債殖利率與市場風險偏好。
        </p>
    <div class="mini-grid">
        <div class="mini-card">
            <div class="label">宏觀資料來源</div>
            <div>{macro_meta.get("source", "無資料")}</div>
        </div>

        <div class="mini-card">
            <div class="label">宏觀資料更新時間</div>
            <div>{macro_meta.get("generated_at", "無資料")}</div>
        </div>

        <div class="mini-card">
            <div class="label">讀取模式</div>
            <div>{macro_meta.get("mode", "無資料")}</div>
        </div>
    </div>

        <table>
            <tr>
                <th>指標</th>
                <th>狀態</th>
                <th>分數</th>
                <th>因果解讀</th>
            </tr>
            {macro_rows}
        </table>
    </div>

    <div class="card">
        <h2>加密資金流判讀區</h2>
        <p>資金流分數：<strong class="positive">{flow_score}</strong></p>
        <ul>
            {flow_list}
        </ul>
        <div class="card">
        <h2>資金流來源模型</h2>
        <p>
            這一區用來判斷目前行情比較像是由現貨買盤、合約槓桿、情緒追價，
            還是板塊輪動所推動。它不是買賣訊號，而是用來判斷行情結構是否健康。
        </p>

                <div class="mini-grid">
            <div class="mini-card">
                <div class="label">主要推動來源</div>
                <div class="status">{flow_source.get("main_source", "無資料")}</div>
            </div>

            <div class="mini-card">
                <div class="label">健康程度</div>
                <div class="status">{flow_source.get("health", "無資料")}</div>
            </div>

            <div class="mini-card">
                <div class="label">現貨買盤分數</div>
                <div class="big-score">{flow_source.get("spot_score", 0)}</div>
            </div>

            <div class="mini-card">
                <div class="label">合約槓桿分數</div>
                <div class="big-score">{flow_source.get("leverage_score", 0)}</div>
            </div>

            <div class="mini-card">
                <div class="label">情緒推動分數</div>
                <div class="big-score">{flow_source.get("sentiment_score", 0)}</div>
            </div>

            <div class="mini-card">
                <div class="label">板塊輪動分數</div>
                <div class="big-score">{flow_source.get("sector_score", 0)}</div>
            </div>
        </div>

        <h3>模型判讀</h3>
        <div class="narrative">{flow_source.get("narrative", "")}</div>

        <h3>細節訊號</h3>
        <ul>
            {flow_source_notes}
        </ul>
    </div>
    </div>

    
    <div class="card">
        <h2>板塊交叉驗證雷達</h2>
        <p class="section-note">
        本區使用 CoinGecko 第三方分類資料作為市場分類參考，並搭配 Binance 代表幣 24H 交易資料進行交叉驗證。
        代表幣追蹤不等於官方板塊定義，而是用來觀察該主題中主要可交易資產是否同步走強或轉弱。
        可信度越高，代表第三方分類與代表幣追蹤方向越一致；可信度偏低時，代表該主題可能受到資料異常、單一小幣波動或分類差異影響，需保守解讀。
    </p>

    <p class="section-note">
        判讀原則：若 CoinGecko 分類與代表幣追蹤同時偏強，且代表幣上漲家數較多，才視為較可靠的短線主題強勢。
        若只有單一來源偏強，則標記為觀察中，不直接視為明確資金流入。
    </p>

        <div class="narrative">{sector_validation.get("summary", "")}</div>

        <table>
            <tr>
                <th>主題</th>
                <th>CoinGecko 分類</th>
                <th>代表幣追蹤</th>
                <th>代表幣數</th>
                <th>一致性</th>
                <th>可信度</th>
                <th>綜合狀態</th>
            </tr>
            {sector_validation_rows}
        </table>
    </div>

        <div class="card">
        <h2>板塊輪動雷達</h2>
        <p>
            這一區用來觀察加密市場資金正在流向哪些主題。
            如果強勢板塊集中在 AI、Meme、L1、RWA、DeFi 等高風險主題，通常代表市場風險偏好正在升溫。
        </p>

        <h3>強勢板塊 Top 8</h3>
        <table>
            <tr>
                <th>板塊</th>
                <th>市值</th>
                <th>24H 成交量</th>
                <th>24H 漲跌</th>
            </tr>
            {category_rows}
        </table>

        <h3>弱勢板塊 Top 5</h3>
        <table>
            <tr>
                <th>板塊</th>
                <th>市值</th>
                <th>24H 成交量</th>
                <th>24H 漲跌</th>
            </tr>
            {weak_category_rows}
        </table>
    </div>

    <div class="card">
        <h2>過熱警示區</h2>
        <p>過熱風險分數：<strong class="warning">{heat_score}</strong></p>
        <ul>
            {warning_list}
        </ul>
    </div>

    <div class="card">
        <h2>最終市場判讀</h2>
        <div class="narrative">{final_narrative}</div>
    </div>

     <div class="card">
        <h2>資料來源狀態</h2>
        <p class="section-note">
            這一區用來確認各資料來源是否正常。若某個來源異常，報告仍可能輸出，但相關判讀需要保守看待。
        </p>

        <table>
            <tr>
                <th>資料來源</th>
                <th>狀態</th>
                <th>訊息</th>
                <th>時間</th>
            </tr>
            {source_status_rows}
        </table>
    </div>   

    <div class="footer">
        <strong>{APP_NAME} {APP_VERSION}</strong><br>
        資料來源：{data_sources_text}<br>
        {REPORT_DISCLAIMER}
    </div>

</div>
</body>
</html>
"""
    return html
import plotly.graph_objects as go


def build_category_chart(categories):
    """
    板塊 Top 8 漲跌圖
    """
    top_categories = categories.get("top_categories", [])

    if not top_categories:
        return "<p class='section-note'>目前沒有板塊資料可產生圖表。</p>"

    names = [x["name"] for x in top_categories[:8]]
    changes = [x["change_24h"] for x in top_categories[:8]]

    colors = [
        "rgba(34, 197, 94, 0.8)" if v >= 0 else "rgba(248, 113, 113, 0.8)"
        for v in changes
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=changes,
        y=names,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.2f}%" for v in changes],
        textposition="auto",
        hovertemplate="%{y}<br>24H 漲跌：%{x:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        title="強勢板塊 Top 8｜24H 漲跌",
        template="plotly_dark",
        height=420,
        margin=dict(l=120, r=30, t=60, b=40),
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        xaxis=dict(title="24H 漲跌幅 (%)"),
        yaxis=dict(autorange="reversed"),
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_flow_source_chart(flow_source):
    """
    資金流來源模型分數圖
    """
    labels = ["現貨買盤", "合約槓桿", "市場情緒", "板塊輪動"]
    values = [
        flow_source.get("spot_score", 0),
        flow_source.get("leverage_score", 0),
        flow_source.get("sentiment_score", 0),
        flow_source.get("sector_score", 0),
    ]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=[
            "rgba(34, 197, 94, 0.8)",
            "rgba(250, 204, 21, 0.8)",
            "rgba(56, 189, 248, 0.8)",
            "rgba(168, 85, 247, 0.8)",
        ],
        text=[str(v) for v in values],
        textposition="auto",
        hovertemplate="%{x}<br>分數：%{y}<extra></extra>",
    ))

    fig.update_layout(
        title="資金流來源模型分數",
        template="plotly_dark",
        height=360,
        margin=dict(l=40, r=30, t=60, b=40),
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        yaxis=dict(title="分數"),
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_funding_chart(crypto):
    """
    BTC / ETH Funding 對比圖
    """
    btc = crypto.get("btc", {})
    eth = crypto.get("eth", {})

    labels = ["BTC Funding", "ETH Funding"]
    values = [
        (btc.get("funding") or 0) * 100,
        (eth.get("funding") or 0) * 100,
    ]

    colors = []

    for v in values:
        raw = v / 100

        if raw > 0.0005:
            colors.append("rgba(248, 113, 113, 0.8)")
        elif raw > 0.0003:
            colors.append("rgba(250, 204, 21, 0.8)")
        elif raw >= 0:
            colors.append("rgba(34, 197, 94, 0.8)")
        else:
            colors.append("rgba(56, 189, 248, 0.8)")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f"{v:.4f}%" for v in values],
        textposition="auto",
        hovertemplate="%{x}<br>Funding：%{y:.4f}%<extra></extra>",
    ))

    fig.update_layout(
        title="BTC / ETH Funding Rate 對比",
        template="plotly_dark",
        height=320,
        margin=dict(l=40, r=30, t=60, b=40),
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e5e7eb"),
        yaxis=dict(title="Funding Rate (%)"),
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)
def build_final_narrative(macro_score, flow_score, heat_score, market_state):
    return f"""
目前市場環境屬於「{market_state['status']}」。

宏觀分數為 {macro_score}，代表目前大環境對風險資產的影響需要綜合判斷。
如果通膨數據降溫，通常會提高市場對降息的期待，進而降低美元與美債殖利率壓力，對 BTC、ETH、Nasdaq 等風險資產較有利。
但如果就業數據過強，市場又可能擔心 Fed 不急著降息，因此宏觀面可能出現利多與壓力並存的狀況。

加密資金流分數為 {flow_score}，代表目前幣圈內部資金動能的強弱。
若 BTC、ETH 價格上升，成交量放大，而且 Funding 沒有明顯過熱，這通常代表行情較健康。
但如果主要是 OI 上升與 Funding 過高推動，而現貨量沒有跟上，則要小心行情是由槓桿堆出來的。

過熱風險分數為 {heat_score}。
過熱警示不是叫你不能進場，而是提醒目前的追價成本與波動風險正在提高。
任何市場都可以有策略，但不同環境要使用不同打法。

策略環境建議：
{market_state['strategy']}
"""


def build_today_summary(
    macro_score,
    flow_score,
    heat_score,
    total_score,
    market_state,
    flow_source,
    heat_warnings,
):
    """
    今日重點摘要：
    把整份報告壓縮成使用者第一眼能看懂的決策摘要。
    """

    market_status = market_state.get("status", "無資料")
    main_source = flow_source.get("main_source", "無資料")
    health = flow_source.get("health", "無資料")

    if heat_score >= 4:
        risk_level = "高"
        risk_text = "過熱風險偏高，需避免高槓桿追價，並注意快速回調或去槓桿波動。"
    elif heat_score >= 2:
        risk_level = "中"
        risk_text = "短線有一定過熱跡象，參與時應降低槓桿，優先等待回調或確認訊號。"
    else:
        risk_level = "低"
        risk_text = "目前未出現明顯過熱訊號，短線風險相對可控，但仍需搭配策略與停損。"

    if macro_score >= 3:
        macro_text = "宏觀環境偏支持風險資產。"
    elif macro_score <= -2:
        macro_text = "宏觀環境對風險資產仍有壓力。"
    else:
        macro_text = "宏觀環境偏中性，市場可能更受加密內部資金流影響。"

    if flow_score >= 4:
        flow_text = "加密市場內部資金動能偏強。"
    elif flow_score >= 1:
        flow_text = "加密市場資金動能略偏正面。"
    elif flow_score <= -2:
        flow_text = "加密市場資金動能偏弱。"
    else:
        flow_text = "加密市場資金動能尚未形成明確方向。"

    short_risks = []

    for warning in heat_warnings[:2]:
        if "Funding" in warning:
            short_risks.append("Funding 過熱")
        elif "恐懼貪婪" in warning:
            short_risks.append("情緒偏熱")
        elif "OI" in warning:
            short_risks.append("OI 槓桿堆積")
        elif "軋空" in warning:
            short_risks.append("軋空風險")
        else:
            short_risks.append("短線波動風險")

    if not short_risks:
        short_risks = ["暫無明顯過熱警示"]

    risk_points = "、".join(list(dict.fromkeys(short_risks)))

    one_liner = (
        f"目前市場屬於「{market_status}」，"
        f"主要推動來源為「{main_source}」，"
        f"行情健康程度為「{health}」。"
        f"{macro_text}{flow_text}"
    )

    strategy_text = market_state.get("strategy", "請依照自身策略與風險承受度操作。")

    return {
        "market_status": market_status,
        "main_source": main_source,
        "health": health,
        "risk_level": risk_level,
        "risk_points": risk_points,
        "risk_text": risk_text,
        "one_liner": one_liner,
        "strategy_text": strategy_text,
        "total_score": total_score,
        "macro_score": macro_score,
        "flow_score": flow_score,
        "heat_score": heat_score,
    }
def analyze_flow_source(crypto):
    """
    資金流來源模型：
    判斷行情比較偏向現貨推動、合約槓桿推動、情緒推動、板塊輪動，或資金不足。
    """

    btc = crypto["btc"]
    eth = crypto["eth"]
    fg = crypto.get("fear_greed", {})
    categories = crypto.get("categories", {})
    sector_validation = crypto.get("sector_validation", {})

    spot_score = 0
    leverage_score = 0
    sentiment_score = 0
    sector_score = 0
    risk_notes = []

    # =========================
    # 1. 現貨推動判斷
    # =========================

    btc_change = btc.get("price_change_pct")
    eth_change = eth.get("price_change_pct")

    btc_volume = btc.get("quote_volume")
    eth_volume = eth.get("quote_volume")

    if btc_change is not None and btc_volume is not None:
        if btc_change > 1 and btc_volume > 10_000_000_000:
            spot_score += 2
            risk_notes.append("BTC 上漲且成交額較高，代表現貨市場參與度偏強。")
        elif btc_change > 1 and btc_volume <= 10_000_000_000:
            spot_score += 1
            risk_notes.append("BTC 上漲但成交額未明顯放大，現貨支撐仍需觀察。")

    if eth_change is not None and eth_volume is not None:
        if eth_change > 1 and eth_volume > 5_000_000_000:
            spot_score += 2
            risk_notes.append("ETH 上漲且成交額較高，代表主流幣現貨資金活躍。")
        elif eth_change > 1 and eth_volume <= 5_000_000_000:
            spot_score += 1
            risk_notes.append("ETH 上漲但成交額未明顯放大，主流幣現貨支撐仍需確認。")

    # =========================
    # 2. 合約槓桿推動判斷
    # =========================

    btc_funding = btc.get("funding")
    eth_funding = eth.get("funding")

    if btc_funding is not None:
        if btc_funding > 0.0005:
            leverage_score += 2
            risk_notes.append("BTC Funding 偏高，代表多頭槓桿情緒較強。")
        elif btc_funding > 0:
            leverage_score += 1
            risk_notes.append("BTC Funding 為正，代表多頭願意付費持倉。")

    if eth_funding is not None:
        if eth_funding > 0.0005:
            leverage_score += 2
            risk_notes.append("ETH Funding 偏高，代表 ETH 多頭槓桿情緒較強。")
        elif eth_funding > 0:
            leverage_score += 1
            risk_notes.append("ETH Funding 為正，代表 ETH 多頭情緒存在。")

    if btc_change is not None and btc_change > 1 and spot_score <= 1 and leverage_score >= 2:
        risk_notes.append("BTC 上漲但現貨支撐不強，同時 Funding 偏高，行情可能偏向槓桿推動。")

    # =========================
    # 3. 情緒推動判斷
    # =========================

    fg_value = fg.get("value")

    if fg_value is not None:
        if fg_value >= 80:
            sentiment_score += 2
            risk_notes.append("恐懼貪婪指數進入極度貪婪，市場追價情緒明顯升溫。")
        elif fg_value >= 65:
            sentiment_score += 1
            risk_notes.append("恐懼貪婪指數偏高，市場情緒偏熱。")
        elif fg_value <= 25:
            sentiment_score -= 1
            risk_notes.append("恐懼貪婪指數偏低，市場情緒保守，反而可能提供觀察低吸的環境。")

    # =========================
    # 4. 板塊輪動推動判斷
    # =========================

    category_score = categories.get("score", 0)
    top_categories = categories.get("top_categories", [])

    if category_score > 0:
        sector_score += category_score

    if top_categories:
        strong_count = sum(1 for x in top_categories[:8] if x.get("change_24h", 0) > 3)

        if strong_count >= 4:
            sector_score += 2
            risk_notes.append("多個第三方分類 24H 漲幅超過 3%，代表板塊輪動較明顯。")
        elif strong_count >= 2:
            sector_score += 1
            risk_notes.append("部分第三方分類表現強勢，代表市場存在主題資金輪動。")

    # 加入板塊交叉驗證：可信度較高且偏強的主題，才額外加分
    validation_rows = sector_validation.get("rows", [])
    validated_strong = [
        x for x in validation_rows
        if "偏強" in str(x.get("final_status", "")) and x.get("confidence") in ["中高", "高"]
    ]

    if len(validated_strong) >= 3:
        sector_score += 2
        names = "、".join([x.get("name", "") for x in validated_strong[:3]])
        risk_notes.append(f"板塊交叉驗證中有多個可信度較高的偏強主題：{names}，代表主題輪動較有一致性。")
    elif len(validated_strong) >= 1:
        sector_score += 1
        names = "、".join([x.get("name", "") for x in validated_strong[:2]])
        risk_notes.append(f"板塊交叉驗證中出現可信度較高的偏強主題：{names}。")

    # =========================
    # 5. 判斷主要來源
    # =========================

    source_scores = {
        "現貨買盤": spot_score,
        "合約槓桿": leverage_score,
        "市場情緒": sentiment_score,
        "板塊輪動": sector_score,
    }

    sorted_sources = sorted(source_scores.items(), key=lambda x: x[1], reverse=True)
    main_sources = [name for name, score in sorted_sources if score > 0]

    if not main_sources:
        main_source_text = "資金動能不明顯"
    elif len(main_sources) == 1:
        main_source_text = main_sources[0]
    else:
        main_source_text = " + ".join(main_sources[:2])

    # =========================
    # 6. 健康程度判斷
    # =========================

    if spot_score >= 3 and leverage_score <= 2:
        health = "健康"
        health_summary = "現貨成交支撐相對明顯，且槓桿情緒尚未過度擁擠，行情結構較健康。"
    elif leverage_score >= 4 and spot_score <= 2:
        health = "偏槓桿"
        health_summary = "行情較可能由合約槓桿推動，若價格回落，容易出現快速去槓桿波動。"
    elif sentiment_score >= 2 and leverage_score >= 2:
        health = "情緒偏熱"
        health_summary = "市場情緒與槓桿同時升溫，短線追價風險提高。"
    elif sector_score >= 2 and spot_score >= 1:
        health = "輪動健康"
        health_summary = "板塊輪動明顯，且主流幣仍有一定成交支撐，代表風險偏好正在擴散。"
    elif spot_score <= 0 and leverage_score <= 0 and sector_score <= 0:
        health = "資金不足"
        health_summary = "目前看不到明顯現貨、槓桿或板塊資金推動，市場可能仍偏觀望。"
    else:
        health = "中等"
        health_summary = "目前市場有一定資金動能，但來源尚未完全一致，需要持續觀察。"

    # =========================
    # 7. 最終判讀文字
    # =========================

    narrative = f"""
主要推動來源：{main_source_text}
健康程度：{health}

{health_summary}

這個模型不是用來判斷一定會漲或跌，而是用來理解這波行情的燃料來源。
如果是現貨買盤推動，行情通常較健康；如果是合約槓桿或情緒推動，短線波動通常會更大。
若板塊輪動擴散，代表市場風險偏好可能正在提升，但仍要觀察 BTC 與 ETH 是否能維持穩定。
"""

    return {
        "spot_score": spot_score,
        "leverage_score": leverage_score,
        "sentiment_score": sentiment_score,
        "sector_score": sector_score,
        "main_source": main_source_text,
        "health": health,
        "summary": health_summary,
        "notes": risk_notes,
        "narrative": narrative,
    }
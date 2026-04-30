# =========================
# 宏觀分數
# =========================

def calculate_macro_score(macro_input):
    score = 0
    details = []

    if not macro_input:
        details.append({
            "name": "宏觀資料",
            "status": "無資料",
            "score": 0,
            "summary": "目前沒有成功讀取 macro_input.json，請確認檔案是否與 app.py 放在同一層，且 JSON 格式正確。",
        })
        return score, details

    for key, item in macro_input.items():
        s = item.get("score", 0)
        score += s

        details.append({
            "name": item.get("name", key.upper()),
            "status": item.get("status", "無資料"),
            "score": s,
            "summary": item.get("summary", ""),
        })

    return score, details


# =========================
# 加密資金流分數
# =========================

def calculate_crypto_flow_score(crypto):
    score = 0
    reasons = []

    btc = crypto["btc"]
    eth = crypto["eth"]

    # BTC / ETH 價格動能
    if btc["price_change_pct"] is not None:
        if btc["price_change_pct"] > 1:
            score += 1
            reasons.append("BTC 24H 上漲超過 1%，代表主流資產短線動能偏正面。")
        elif btc["price_change_pct"] < -1:
            score -= 1
            reasons.append("BTC 24H 下跌超過 1%，代表主流資產短線承壓。")

    if eth["price_change_pct"] is not None:
        if eth["price_change_pct"] > 1:
            score += 1
            reasons.append("ETH 24H 上漲超過 1%，代表風險偏好有所改善。")
        elif eth["price_change_pct"] < -1:
            score -= 1
            reasons.append("ETH 24H 下跌超過 1%，代表山寨與高 beta 資產情緒偏弱。")

    # 成交額判斷
    if btc["quote_volume"] and eth["quote_volume"]:
        if btc["quote_volume"] > 10_000_000_000:
            score += 1
            reasons.append("BTC 24H 成交額較高，代表市場參與度不低。")
        if eth["quote_volume"] > 5_000_000_000:
            score += 1
            reasons.append("ETH 24H 成交額較高，代表主流幣資金活躍。")

    # Funding 判斷
    btc_funding = btc["funding"]
    eth_funding = eth["funding"]

    if btc_funding is not None:
        if 0 <= btc_funding <= 0.0003:
            score += 1
            reasons.append("BTC Funding 為正但未明顯過熱，代表多頭情緒存在但尚未極端擁擠。")
        elif btc_funding < 0:
            reasons.append("BTC Funding 為負，代表空頭付費，若價格止跌，可能存在軋空條件。")

    if eth_funding is not None:
        if 0 <= eth_funding <= 0.0003:
            score += 1
            reasons.append("ETH Funding 為正但未明顯過熱，代表 ETH 多頭情緒相對健康。")
        elif eth_funding < 0:
            reasons.append("ETH Funding 為負，代表市場對 ETH 較保守，後續需觀察是否出現止跌反彈。")

    # CoinGecko / 板塊輪動分數
    categories = crypto.get("categories", {})
    category_score = categories.get("score", 0)
    category_summary = categories.get("summary", "")

    score += category_score

    if category_summary:
        reasons.append("板塊輪動：" + category_summary)

    # 板塊交叉驗證摘要
    sector_validation = crypto.get("sector_validation", {})
    sector_summary = sector_validation.get("summary", "")

    if sector_summary:
        reasons.append("板塊交叉驗證：" + sector_summary)

    if not reasons:
        reasons.append("目前加密資料不足，暫時無法完整判斷資金流。")

    return score, reasons


# =========================
# 過熱風險分數
# =========================

def calculate_heat_risk_score(crypto):
    risk_score = 0
    warnings = []

    btc = crypto["btc"]
    eth = crypto["eth"]
    fg = crypto["fear_greed"]

    # Funding 過熱
    for name, coin in [("BTC", btc), ("ETH", eth)]:
        funding = coin["funding"]

        if funding is not None:
            if funding > 0.0005:
                risk_score += 2
                warnings.append(
                    f"{name} Funding 偏高，代表多頭願意支付較高成本持倉。"
                    f"這通常代表短線看多情緒強，但也意味著多頭部位可能擁擠，追多風險提高。"
                )
            elif funding < -0.0003:
                risk_score += 1
                warnings.append(
                    f"{name} Funding 明顯為負，代表空頭情緒偏重。"
                    f"若價格沒有繼續下跌，可能產生軋空風險。"
                )

    # 恐懼貪婪
    fg_value = fg.get("value")

    if fg_value is not None:
        if fg_value >= 80:
            risk_score += 2
            warnings.append(
                "恐懼貪婪指數進入極度貪婪區，代表市場追價情緒明顯升溫。"
                "這不是代表不能做多，而是代表高槓桿追價的風險報酬比下降。"
            )
        elif fg_value >= 65:
            risk_score += 1
            warnings.append(
                "恐懼貪婪指數偏高，市場情緒較熱。"
                "若同時伴隨 Funding 過高與 OI 堆積，需要注意短線回調。"
            )
        elif fg_value <= 25:
            warnings.append(
                "恐懼貪婪指數偏低，市場情緒保守。"
                "這類環境不一定是壞事，反而可能提供分批觀察與低吸研究的機會。"
            )

    # 價格急漲搭配 Funding 偏高
    if btc["price_change_pct"] is not None and btc["funding"] is not None:
        if btc["price_change_pct"] > 3 and btc["funding"] > 0.0005:
            risk_score += 2
            warnings.append(
                "BTC 價格短線急漲且 Funding 偏高，代表行情可能由槓桿多頭推動。"
                "若現貨量沒有持續跟上，後續容易出現多頭獲利了結或多殺多。"
            )

    if not warnings:
        warnings.append(
            "目前未出現明顯過熱警示。這代表短線風險相對可控，但仍需要搭配自己的策略與停損規劃。"
        )

    return risk_score, warnings


# =========================
# 市場狀態分類
# =========================

def classify_market(total_score):
    if total_score >= 7:
        return {
            "status": "強勢風險偏好",
            "strategy": "趨勢策略較有優勢，但仍要避免高槓桿追高。可優先觀察回調承接與強勢板塊延續。",
            "tone": "市場動能明顯偏強，重點是不要因為情緒過熱而失去風控。",
        }
    elif total_score >= 3:
        return {
            "status": "偏多環境",
            "strategy": "適合尋找回調承接、強勢板塊輪動與分批布局機會。",
            "tone": "市場環境偏正面，但仍需要觀察過熱風險是否擴大。",
        }
    elif total_score >= -2:
        return {
            "status": "中性震盪",
            "strategy": "適合等待確認、區間策略、降低槓桿，避免在沒有方向時重倉。",
            "tone": "市場沒有明確單邊方向，這不代表沒有機會，而是需要更重視進場位置與策略條件。",
        }
    elif total_score >= -6:
        return {
            "status": "偏弱環境",
            "strategy": "適合防守布局、觀察低吸條件、等待止跌確認，或用較小倉位測試策略。",
            "tone": "市場偏弱不代表完全不能入場，而是代表策略要更重視分批、倉位與風險控制。",
        }
    else:
        return {
            "status": "高壓環境",
            "strategy": "適合保留現金、等待恐慌釋放後的機會，或只用極小倉位觀察。",
            "tone": "高壓環境中機會通常來自恐慌後的錯殺，但不適合盲目重倉。",
        }
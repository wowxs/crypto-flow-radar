import os
from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    FRED_API_KEY = st.secrets.get("FRED_API_KEY", os.getenv("FRED_API_KEY", ""))
except Exception:
    FRED_API_KEY = os.getenv("FRED_API_KEY", "")


APP_NAME = "Crypto Flow Radar"
APP_VERSION = "V5.0"
APP_SUBTITLE = "宏觀 × 資金流 × 過熱警示 × 策略環境判讀"

REPORT_DISCLAIMER = "本工具僅用於市場環境判讀與資料整理，不構成投資建議。"

DATA_SOURCES = [
    "Binance Spot",
    "Binance Futures",
    "CoinGecko Categories",
    "Alternative.me Fear & Greed",
    "yfinance DXY / US10Y / QQQ",
    "FRED Macro Data",
]
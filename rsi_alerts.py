# rsi_alerts.py (Streamlit version with fixed RSI calculation using Wilder's smoothing)
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os
import streamlit as st
import requests

# Email configuration from environment or secrets
def send_email(subject, body):
    from_address = os.environ.get("EMAIL_FROM")
    to_address = os.environ.get("EMAIL_TO")
    password = os.environ.get("EMAIL_PASS")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_address, password)
        server.send_message(msg)

# Calculate RSI using Wilder's smoothing
def calculate_rsi(series, period=14):
    if series.dropna().shape[0] < period + 1:
        raise ValueError("Not enough data to calculate RSI")
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Streamlit UI
st.set_page_config(page_title="RSI Monitor", layout="centered")
st.title("📈 RSI Monitor for Stocks")

# GitHub raw URL of tickers.txt
github_ticker_url = "https://raw.githubusercontent.com/anujvarma-original/rsi_alerts/main/tickers.txt"

try:
    response = requests.get(github_ticker_url)
    response.raise_for_status()
    tickers = [line.strip() for line in response.text.splitlines() if line.strip()]
except Exception as e:
    st.error(f"Failed to load tickers from GitHub: {e}")
    st.stop()

results = []
with st.spinner("Fetching RSI data..."):
    for ticker in tickers:
        try:
            print(f"Processing {ticker}...")
            data = yf.download(ticker, period="60d", interval="1d", auto_adjust=True)

            if data.empty or "Close" not in data.columns:
                print(f"No data for {ticker}. Marking as unavailable.")
                results.append({"Ticker": ticker, "RSI": "N/A", "Alert Status": "Data Missing"})
                continue

            close_prices = data["Close"].dropna()
            print

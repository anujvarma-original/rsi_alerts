# rsi_alerts.py (Streamlit version reading tickers from GitHub and showing all tickers)
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

# Calculate RSI
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
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
            data = yf.download(ticker, period="3mo", interval="1d", auto_adjust=False)

            if data.empty or "Close" not in data.columns:
                print(f"No data for {ticker}. Marking as unavailable.")
                results.append({"Ticker": ticker, "RSI": "N/A", "Alert Status": "Data Missing"})
                continue

            close_prices = data["Close"]
            rsi = calculate_rsi(close_prices)

            print(f"RSI raw series tail for {ticker}:")
            print(rsi.tail())

            if rsi.empty or rsi.isna().all():
                print(f"RSI is empty or all NaN for {ticker}. Including as N/A.")
                results.append({"Ticker": ticker, "RSI": "N/A", "Alert Status": "Insufficient Data"})
                continue

            current_rsi = rsi.dropna().iloc[-1]
            current_rsi = round(current_rsi, 2)
            alert_status = "Not Sent"

            if current_rsi < 30:
                send_email(
                    subject=f"RSI Alert: {ticker} is Oversold",
                    body=f"The RSI for {ticker} has dropped below 30. Current RSI: {current_rsi:.2f}"
                )
                alert_status = "Sent (Oversold)"
            elif current_rsi > 70:
                send_email(

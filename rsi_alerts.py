# rsi_alerts.py (Streamlit version with alert status)
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os
import streamlit as st

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
st.title("📈 RSI Monitor for Stocks")

uploaded_file = st.file_uploader("Upload a list of stock tickers (one per line)", type="txt")

if uploaded_file is not None:
    tickers = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.strip()]
    results = []

    with st.spinner("Fetching RSI data..."):
        for ticker in tickers:
            try:
                data = yf.download(ticker, period="3mo", interval="1d", auto_adjust=False)
                if data.empty or "Close" not in data.columns:
                    st.warning(f"No data for {ticker}. Skipping.")
                    continue

                close_prices = data["Close"]
                rsi = calculate_rsi(close_prices)
                current_rsi = round(rsi.iloc[-1], 2)
                alert_status = "Not Sent"

                if current_rsi < 30:
                    send_email(
                        subject=f"RSI Alert: {ticker} is Oversold",
                        body=f"The RSI for {ticker} has dropped below 30. Current RSI: {current_rsi:.2f}"
                    )
                    alert_status = "Sent (Oversold)"
                elif current_rsi > 70:
                    send_email(
                        subject=f"RSI Alert: {ticker} is Overbought",
                        body=f"The RSI for {ticker} has risen above 70. Current RSI: {current_rsi:.2f}"
                    )
                    alert_status = "Sent (Overbought)"

                results.append({"Ticker": ticker, "RSI": current_rsi, "Alert Status": alert_status})

            except Exception as e:
                st.error(f"Error processing {ticker}: {e}")

    if resu

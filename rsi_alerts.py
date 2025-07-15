# rsi_alerts.py with fallback to Yahoo Finance for RSI
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import streamlit as st
import requests
import yfinance as yf
import time

# Read email and API settings from secrets
from_address = st.secrets["email"]["from"]
to_address = st.secrets["email"]["to"]
email_password = st.secrets["email"]["password"]
api_key = st.secrets["alphavantage"]["ALPHAVANTAGE_KEY"]

# Email sending function
def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_address, email_password)
        server.send_message(msg)

# Calculate RSI using Yahoo Finance fallback
def calculate_rsi_yahoo(close_prices, period=14):
    delta = close_prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Alpha Vantage RSI and price fetcher with fallback
def get_rsi_and_price(ticker, api_key):
    rsi_url = (
        f"https://www.alphavantage.co/query?function=RSI&symbol={ticker}"
        f"&interval=daily&time_period=14&series_type=close&apikey={api_key}"
    )
    price_url = (
        f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}"
        f"&apikey={api_key}"
    )
    try:
        rsi_response = requests.get(rsi_url)
        rsi_response.raise_for_status()
        rsi_data = rsi_response.json()

        if "Note" in rsi_data:
            raise ValueError("API rate limit exceeded")
        if "Error Message" in rsi_data:
            raise ValueError("Invalid ticker or unsupported symbol")

        rsi_tech = rsi_data.get("Technical Analysis: RSI")
        if not rsi_tech:
            raise ValueError("RSI data missing")

        latest_date = sorted(rsi_tech.keys())[-1]
        rsi_value = rsi_tech[latest_date].get("RSI")
        if rsi_value is None:
            raise ValueError("RSI value not found")

        price_response = requests.get(price_url)
        price_response.raise_for_status()
        price_data = price_response.json()
        quote = price_data.get("Global Quote", {})
        price = quote.get("05. price")

        if price is None:
            raise ValueError("Price data missing")

        return float(rsi_value), float(price)

    except Exception as e:
        print(f"Alpha Vantage failed for {ticker}: {e}. Falling back to Yahoo Finance.")
        try:
            data = yf.download(ticker, period="2mo", interval="1d", progress=False)
            if data.empty or "Close" not in data.columns:
                raise ValueError("Yahoo Finance returned no data")
            rsi_series = calculate_rsi_yahoo(data["Close"].dropna())
            current_rsi = rsi_series.dropna().iloc[-1]
            current_price = data["Close"].dropna().iloc[-1]
            return float(current_rsi), float(current_price)
        except Exception as e2:
            return f"Error: {str(e2)}", None

# Streamlit UI
st.set_page_config(page_title="RSI Monitor", layout="centered")
st.title("📈 RSI Monitor via Alpha Vantage with Yahoo Finance Fallback")

# Read tickers from GitHub
github_ticker_url = "https://raw.githubusercontent.com/anujvarma-original/rsi_alerts/main/tickers.txt"
try:
    response = requests.get(github_ticker_url)
    response.raise_for_status()
    tickers = [line.strip() for line in response.text.splitlines() if line.strip()]
except Exception as e:
    st.error(f"Failed to load tickers from GitHub: {e}")
    st.stop()

results = []

with st.spinner("Fetching RSI and price data..."):
    for ticker in tickers:
        print(f"Fetching RSI and price for {ticker}...")
        rsi_value, price = get_rsi_and_price(ticker, api_key)
        time.sleep(12)

        if isinstance(rsi_value, str) and rsi_value.startswith("Error"):
            results.append({"Ticker": ticker, "RSI": "N/A", "Price": "N/A", "Alert Status": rsi_value})
            continue

        alert_status = "Not Sent"
        if rsi_value < 30:
            send_email(
                subject=f"RSI Alert: {ticker} is Oversold",
                body=f"The RSI for {ticker} has dropped below 30. Current RSI: {rsi_value:.2f}, Price: ${price:.2f}"
            )
            alert_status = "

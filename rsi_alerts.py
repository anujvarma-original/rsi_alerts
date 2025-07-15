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

# Alpha Vantage RSI and price fetcher with fallback to Yahoo Finance
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

        rsi_tech = rsi_data.get("Technical Analysis: RSI", {})
        if not rsi_tech:
            raise ValueError("RSI data missing from Alpha Vantage")

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
        print(f"Alpha Vantage error for {ticker}: {e}. Falling back to Yahoo Finance.")
        try:
            data = yf.download(ticker, period="3mo", interval="1d", auto_adjust=True)
            if data.empty or "Close" not in data.columns:
                return f"Error: No data found for {ticker}", None

            close_prices = data["Close"].dropna()
            delta = clos

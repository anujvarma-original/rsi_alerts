import pandas as pd
import smtplib
from email.mime.text import MIMEText
import streamlit as st
import requests
import yfinance as yf
import time
import math

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
        rsi_response = requests.get(rsi_url, timeout=20)
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

        price_response = requests.get(price_url, timeout=20)
        price_response.raise_for_status()
        price_data = price_response.json()
        quote = price_data.get("Global Quote", {})
        price = quote.get("05. price")

        if price is None:
            raise ValueError("Price data missing")

        rsi_value, price = float(rsi_value), float(price)
        if not math.isfinite(rsi_value) or not 0 <= rsi_value <= 100 or not math.isfinite(price) or price <= 0:
            raise ValueError("Provider returned invalid RSI or price")
        return rsi_value, price

    except Exception as e:
        print(f"Alpha Vantage error for {ticker}: {e}. Falling back to Yahoo Finance.")
        try:
            data = yf.download(
                ticker.replace(".", "-"), period="3mo", interval="1d",
                auto_adjust=True, progress=False, threads=False, timeout=20,
            )
            rsi_value, price = calculate_rsi_and_price(data)
            return rsi_value, price
        except Exception as e2:
            return f"Error: {str(e2)}", None

def calculate_rsi_and_price(data, period=14):
    """Normalize Yahoo's single-ticker columns and compute the existing SMA RSI."""
    if data is None or data.empty or "Close" not in data.columns:
        raise ValueError("No closing-price data returned")
    close = data["Close"]
    # Recent yfinance versions return a DataFrame even for one ticker.
    if isinstance(close, pd.DataFrame):
        if close.shape[1] != 1:
            raise ValueError("Expected closing prices for exactly one ticker")
        close = close.iloc[:, 0]
    close = pd.to_numeric(close, errors="coerce").replace(
        [float("inf"), float("-inf")], float("nan")
    ).dropna().sort_index()
    if len(close) < period + 1:
        raise ValueError(f"Need at least {period + 1} valid closing prices")
    delta = close.diff()
    avg_gain = delta.clip(lower=0).rolling(period, min_periods=period).mean()
    avg_loss = (-delta.clip(upper=0)).rolling(period, min_periods=period).mean()
    gain, loss = float(avg_gain.iloc[-1]), float(avg_loss.iloc[-1])
    # Avoid 0/0 (flat prices) and division by zero (all gains).
    rsi = 50.0 if gain == 0 and loss == 0 else (
        100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)
    )
    price = float(close.iloc[-1])
    if not math.isfinite(rsi) or not math.isfinite(price) or price <= 0:
        raise ValueError("Unable to calculate a valid RSI and price")
    return float(rsi), price

# Streamlit UI
st.set_page_config(page_title="RSI Monitor", layout="centered")
st.title("📈 RSI Monitor via Alpha Vantage (with fallback)")

# Read tickers from GitHub
github_ticker_url = "https://raw.githubusercontent.com/anujvarma-original/rsi_alerts/main/tickers.txt"
try:
    response = requests.get(github_ticker_url, timeout=20)
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
        time.sleep(12)  # respect API rate limits

        if isinstance(rsi_value, str) and rsi_value.startswith("Error"):
            results.append({"Ticker": ticker, "RSI": "N/A", "Price": "N/A", "Alert Status": rsi_value})
            continue

        alert_status = "Not Sent"
        try:
            if rsi_value < 30:
                send_email(
                    subject=f"RSI Alert: {ticker} is Oversold",
                    body=f"The RSI for {ticker} has dropped below 30. Current RSI: {rsi_value}, Price: ${price:.2f}"
                )
                alert_status = "Sent (Oversold)"
            elif rsi_value > 70:
                send_email(
                    subject=f"RSI Alert: {ticker} is Overbought",
                    body=f"The RSI for {ticker} has risen above 70. Current RSI: {rsi_value}, Price: ${price:.2f}"
                )
                alert_status = "Sent (Overbought)"
        except Exception as exc:
            alert_status = f"Email failed: {exc}"

        results.append({"Ticker": ticker, "RSI": round(rsi_value, 2), "Price": round(price, 2), "Alert Status": alert_status})

# Display results
if results:
    df = pd.DataFrame(results)

    def color_rsi(val):
        try:
            v = float(val)
            if v > 70:
                return "background-color: #ffcccc"  # RED for overbought
            elif v < 30:
                return "background-color: #ccffcc"  # GREEN for oversold
            else:
                return "background-color: #ffffcc"  # YELLOW for neutral
        except:
            return "background-color: #f2f2f2"  # GREY for N/A

    styled_df = df.style.format({
        "RSI": lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x,
        "Price": lambda x: f"${x:.2f}" if isinstance(x, (int, float)) else x
    }).map(color_rsi, subset=["RSI"])

    valid_count = sum(isinstance(row["RSI"], (int, float)) for row in results)
    if valid_count == len(results):
        st.success(f"Retrieved RSI and price for all {valid_count} tickers.")
    else:
        st.warning(f"Retrieved {valid_count} of {len(results)} tickers. See Alert Status for errors.")
    st.write("### Current RSI & Price Summary")
    st.dataframe(styled_df, width="stretch", hide_index=True)
else:
    st.warning("No RSI data was calculated.", icon="⚠️")

import pandas as pd
import smtplib
from email.mime.text import MIMEText
import streamlit as st
import requests
import time

# Email & API config from Streamlit secrets
from_address = st.secrets["email"]["from"]
to_address = st.secrets["email"]["to"]
email_password = st.secrets["email"]["password"]
api_key = st.secrets["alphavantage"]["ALPHAVANTAGE_KEY"]

# Email sender
def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_address, email_password)
        server.send_message(msg)

# Fetch RSI and price from Alpha Vantage
def get_rsi_and_price(ticker, api_key):
    rsi_url = f"https://www.alphavantage.co/query?function=RSI&symbol={ticker}&interval=daily&time_period=14&series_type=close&apikey={api_key}"
    price_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}"

    try:
        rsi_response = requests.get(rsi_url)
        rsi_response.raise_for_status()
        if "API rate limit exceeded" in rsi_response.text:
            return "QuotaExceeded", None

        rsi_data = rsi_response.json()
        if "Error Message" in rsi_data:
            raise ValueError("Invalid ticker or unsupported symbol")

        rsi_tech = rsi_data.get("Technical Analysis: RSI", {})
        if not rsi_tech:
            raise ValueError("RSI data missing")
        latest_date = sorted(rsi_tech.keys())[-1]
        rsi_value = rsi_tech[latest_date].get("RSI")
        if not rsi_value:
            raise ValueError("RSI value not found")

        price_response = requests.get(price_url)
        price_response.raise_for_status()
        if "API rate limit exceeded" in price_response.text:
            return "QuotaExceeded", None

        price_data = price_response.json()
        quote = price_data.get("Global Quote", {})
        price = quote.get("05. price")
        if not price:
            raise ValueError("Price data missing")

        return float(rsi_value), float(price)
    except Exception as e:
        return f"Error: {str(e)}", None

# Streamlit UI setup
st.set_page_config(page_title="RSI Monitor", layout="centered")
st.title("📈 RSI Monitor via Alpha Vantage")

# Load tickers from GitHub
github_ticker_url = "https://raw.githubusercontent.com/anujvarma-original/rsi_alerts/main/tickers.txt"
try:
    response = requests.get(github_ticker_url)
    response.raise_for_status()
    tickers = [line.strip() for line in response.text.splitlines() if line.strip()]
except Exception as e:
    st.error(f"Failed to load tickers from GitHub: {e}")
    st.stop()

results = []
quota_alert_sent = False

with st.spinner("Fetching RSI and price data..."):
    for ticker in tickers:
        print(f"Fetching data for {ticker}...")
        rsi_value, price = get_rsi_and_price(ticker, api_key)
        time.sleep(12)  # Respect Alpha Vantage limit

        if rsi_value == "QuotaExceeded":
            if not quota_alert_sent:
                send_email(
                    subject="Alpha Vantage API Quota Exceeded",
                    body="Your Alpha Vantage API quota has been exceeded. RSI alerts have been paused until the next reset."
                )
                quota_alert_sent = True
            results.append({
                "Ticker": ticker,
                "RSI": "N/A",
                "Price": "N/A",
                "Alert Status": "Quota Exceeded"
            })
            continue

        if isinstance(rsi_value, str) and rsi_value.startswith("Error"):
            results.append({
                "Ticker": ticker,
                "RSI": "N/A",
                "Price": "N/A",
                "Alert Status": rsi_value
            })
            continue

        alert_status = "Not Sent"
        if rsi_value < 30:
            send_email(
                subject=f"RSI Alert: {ticker} is Oversold",
                body=f"The RSI for {ticker} has dropped below 30.\nRSI: {rsi_value:.2f}, Price: ${price:.2f}"
            )
            alert_status = "Sent (Oversold)"
        elif rsi_value > 70:
            send_email(
                subject=f"RSI Alert: {ticker} is Overbought",
                body=f"The RSI for {ticker} has risen above 70.\nRSI: {rsi_value:.2f}, Price: ${price:.2f}"
            )
            alert_status = "Sent (Overbought)"

        results.append({
            "Ticker": ticker,
            "RSI": round(rsi_value, 2),
            "Price": round(price, 2),
            "Alert Status": alert_status
        })

# Display results
if results:
    df = pd.DataFrame(results)

    def color_rsi(val):
        try:
            v = float(val)
            if v < 30:
                return "background-color: #ffcccc"
            elif v > 70:
                return "background-color: #ccffcc"
            else:
                return "background-color: #ffffcc"
        except:
            return "background-color: #f2f2f2"

    styled_df = df.style.format({
        "RSI": lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x,
        "Price": lambda x: f"${x:.2f}" if isinstance(x, (int, float)) else x
    }).applymap(color_rsi, subset=["RSI"])

    st.success("RSI and price data retrieved successfully!")
    st.write("### RSI & Price Summary")
    st.dataframe(styled_df, use_container_width=True)
else:
    st.warning("No data was retrieved.", icon="⚠️")

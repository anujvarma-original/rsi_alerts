import pandas as pd
import smtplib
from email.mime.text import MIMEText
import streamlit as st
import requests
import time

# Email sending function using Streamlit secrets
def send_email(subject, body):
    from_address = st.secrets["EMAIL_FROM"]
    to_address = st.secrets["EMAIL_TO"]
    password = st.secrets["EMAIL_PASS"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_address, password)
        server.send_message(msg)

# Alpha Vantage RSI fetcher with error diagnostics
def get_rsi_alphavantage(ticker, api_key):
    url = (
        f"https://www.alphavantage.co/query?function=RSI&symbol={ticker}"
        f"&interval=daily&time_period=14&series_type=close&apikey={api_key}"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "Note" in data:
            raise ValueError("API rate limit exceeded")
        if "Error Message" in data:
            raise ValueError("Invalid ticker or unsupported symbol")

        rsi_data = data.get("Technical Analysis: RSI", {})
        if not rsi_data:
            raise ValueError("RSI data missing from response")

        latest_date = sorted(rsi_data.keys())[-1]
        rsi_value = rsi_data[latest_date].get("RSI")
        if rsi_value is None:
            raise ValueError("RSI value not found for latest date")

        return float(rsi_value)
    except Exception as e:
        return f"Error: {str(e)}"

# Streamlit UI
st.set_page_config(page_title="RSI Monitor", layout="centered")
st.title("📈 RSI Monitor via Alpha Vantage")

# Read tickers from GitHub
github_ticker_url = "https://raw.githubusercontent.com/anujvarma-original/rsi_alerts/main/tickers.txt"
try:
    response = requests.get(github_ticker_url)
    response.raise_for_status()
    tickers = [line.strip() for line in response.text.splitlines() if line.strip()]
except Exception as e:
    st.error(f"Failed to load tickers from GitHub: {e}")
    st.stop()

api_key = st.secrets["ALPHAVANTAGE_KEY"]
results = []

with st.spinner("Fetching RSI data from Alpha Vantage..."):
    for ticker in tickers:
        print(f"Fetching RSI for {ticker}...")
        rsi_value = get_rsi_alphavantage(ticker, api_key)
        time.sleep(12)  # respect free tier limits

        if isinstance(rsi_value, str) and rsi_value.startswith("Error"):
            results.append({"Ticker": ticker, "RSI": "N/A", "Alert Status": rsi_value})
            continue

        alert_status = "Not Sent"
        if rsi_value < 30:
            send_email(
                subject=f"RSI Alert: {ticker} is Oversold",
                body=f"The RSI for {ticker} has dropped below 30. Current RSI: {rsi_value}"
            )
            alert_status = "Sent (Oversold)"
        elif rsi_value > 70:
            send_email(
                subject=f"RSI Alert: {ticker} is Overbought",
                body=f"The RSI for {ticker} has risen above 70. Current RSI: {rsi_value}"
            )
            alert_status = "Sent (Overbought)"

        results.append({"Ticker": ticker, "RSI": round(rsi_value, 2), "Alert Status": alert_status})

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
        "RSI": lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x
    }).applymap(color_rsi, subset=["RSI"])

    st.success("RSI data retrieved successfully!")
    st.write("### Current RSI Summary")
    st.dataframe(styled_df, use_container_width=True)
else:
    st.warning("No RSI data was calculated.", icon="⚠️")

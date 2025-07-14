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

# Alpha Vantage RSI fetcher
def get_rsi_alphavantage(ticker, api_key):
    url = (
        f"https://www.alphavantage.co/query?function=RSI&symbol={ticker}"
        f"&interval=daily&time_period=14&series_type=close&apikey={api_key}"
    )
    response = requests.get(url)
    data = response.json()
    try:
        rsi_data = data["Technical Analysis: RSI"]
        latest_date = sorted(rsi_data.keys())[-1]
        return float(rsi_data[latest_date]["RSI"])
    except Exception as e:
        print(f"Error fetching RSI for {ticker}: {e}")
        return None

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
        try:
            print(f"Fetching RSI for {ticker}...")
            rsi_value = get_rsi_alphavantage(ticker, api_key)
            time.sleep(12)  # to respect free tier rate limits (5 calls/min)

            if rsi_value is None:
                results.append({"Ticker": ticker, "RSI": "N/A", "Alert Status": "Data Missing"})
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

        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            results.append({"Ticker": ticker, "RSI": "N/A", "Alert Status": f"Error: {str(e)}"})

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

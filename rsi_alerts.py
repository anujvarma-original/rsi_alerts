# rsi_alerts.py (Streamlit version with robust RSI fix)
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
st.set_page_config(page_title="RSI Monitor", layout="centered")
st.title("📈 RSI Monitor for Stocks")

uploaded_file = st.file_uploader("Upload a list of stock tickers (one per line)", type="txt")

if uploaded_file is not None:
    tickers = [line.decode("utf-8").strip() for line in uploaded_file.readlines() if line.strip()]
    results = []

    with st.spinner("Fetching RSI data..."):
        for ticker in tickers:
            try:
                print(f"Processing {ticker}...")
                data = yf.download(ticker, period="3mo", interval="1d", auto_adjust=False)
                if data.empty or "Close" not in data.columns:
                    print(f"No data for {ticker}. Skipping.")
                    continue

                close_prices = data["Close"]
                rsi = calculate_rsi(close_prices)

                if rsi.empty or rsi.isna().all():
                    print(f"RSI is empty or all NaN for {ticker}. Skipping.")
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
                        subject=f"RSI Alert: {ticker} is Overbought",
                        body=f"The RSI for {ticker} has risen above 70. Current RSI: {current_rsi:.2f}"
                    )
                    alert_status = "Sent (Overbought)"

                results.append({"Ticker": ticker, "RSI": current_rsi, "Alert Status": alert_status})
                print(f"{ticker}: RSI = {current_rsi}, Alert = {alert_status}")

            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                st.error(f"Error processing {ticker}: {e}")

    if results:
        df = pd.DataFrame(results)[["Ticker", "RSI", "Alert Status"]]

        def color_rsi(val):
            if val < 30:
                return "background-color: #ffcccc"  # red shade
            elif val > 70:
                return "background-color: #ccffcc"  # green shade
            else:
                return "background-color: #ffffcc"  # yellow shade

        styled_df = df.style.format({"RSI": "{:.2f}"}).applymap(color_rsi, subset=["RSI"])

        print("\nFinal RSI Summary:")
        print(df.to_string(index=False))

        st.success("RSI data retrieved successfully!")
        st.write("### Current RSI Summary")
        st.dataframe(styled_df, use_container_width=True)
    else:
        print("No RSI data was calculated.")
        st.warning("No RSI data was calculated.")
else:
    st.info("Please upload a ticker list to begin.")

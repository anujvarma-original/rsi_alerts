# rsi_alerts.py
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import datetime
import os

FLAG_FILE = "/tmp/rsi_last_alert.txt"
TICKERS_FILE = "tickers.txt"

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

# Read last alert state
def read_last_alert(ticker):
    file = f"{FLAG_FILE}_{ticker}"
    if not os.path.exists(file):
        return "none"
    with open(file, "r") as f:
        return f.read().strip()

# Update alert state
def write_last_alert(ticker, state):
    file = f"{FLAG_FILE}_{ticker}"
    with open(file, "w") as f:
        f.write(state)

# Main logic
def check_rsi_alert(ticker):
    data = yf.download(ticker, period="3mo", interval="1d")
    close_prices = data["Close"]
    rsi = calculate_rsi(close_prices)
    current_rsi = rsi.iloc[-1]

    last_state = read_last_alert(ticker)

    if current_rsi < 30 and last_state != "low":
        send_email(
            subject=f"RSI Alert for {ticker}: Oversold",
            body=f"RSI dropped below 30. Current RSI: {current_rsi:.2f}"
        )
        write_last_alert(ticker, "low")

    elif current_rsi > 70 and last_state != "high":
        send_email(
            subject=f"RSI Alert for {ticker}: Overbought",
            body=f"RSI rose above 70. Current RSI: {current_rsi:.2f}"
        )
        write_last_alert(ticker, "high")

    elif 30 <= current_rsi <= 70 and last_state != "neutral":
        write_last_alert(ticker, "neutral")

if __name__ == "__main__":
    if not os.path.exists(TICKERS_FILE):
        print("Ticker file not found.")
    else:
        with open(TICKERS_FILE, "r") as f:
            tickers = [line.strip() for line in f if line.strip()]
        for ticker in tickers:
            try:
                check_rsi_alert(ticker)
            except Exception as e:
                print(f"Error processing {ticker}: {e}")

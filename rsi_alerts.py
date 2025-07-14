# rsi_alerts.py
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os

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

if __name__ == "__main__":
    if not os.path.exists(TICKERS_FILE):
        print("Ticker file not found.")
        exit()

    with open(TICKERS_FILE, "r") as f:
        tickers = [line.strip() for line in f if line.strip()]

    results = []

    for ticker in tickers:
        try:
            data = yf.download(ticker, period="3mo", interval="1d")
            close_prices = data["Close"]
            rsi = calculate_rsi(close_prices)
            current_rsi = rsi.iloc[-1]
            results.append({"Ticker": ticker, "RSI": round(current_rsi, 2)})

            if current_rsi < 30:
                send_email(
                    subject=f"RSI Alert: {ticker} is Oversold",
                    body=f"The RSI for {ticker} has dropped below 30. Current RSI: {current_rsi:.2f}"
                )
            elif current_rsi > 70:
                send_email(
                    subject=f"RSI Alert: {ticker} is Overbought",
                    body=f"The RSI for {ticker} has risen above 70. Current RSI: {current_rsi:.2f}"
                )

        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    df = pd.DataFrame(results)
    print("\nCurrent RSI Values:")
    print(df.to_string(index=False))

import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os
import streamlit as st
import requests

# Email sending function
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

# RSI calculation using Wilder's exponential smoothing
def calculate_rsi(series, period=14):
    if series.dropna().shape[0] < period + 1:
        raise ValueError("Not enough data to calculate RSI")
    delta = series.diff()

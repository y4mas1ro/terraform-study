import boto3
import yfinance as yf
import json
import time
import os
from decimal import Decimal
from datetime import datetime

ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
STREAM_NAME  = os.getenv("KINESIS_STREAM", "stock-price-stream")
SYMBOLS      = os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT,TSLA").split(",")
INTERVAL     = float(os.getenv("INTERVAL", "3"))


def get_kinesis():
    return boto3.client(
        "kinesis",
        endpoint_url=ENDPOINT_URL,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


def wait_for_stream(kinesis):
    print(f"Waiting for Kinesis stream '{STREAM_NAME}'...")
    while True:
        try:
            kinesis.describe_stream_summary(StreamName=STREAM_NAME)
            print("Stream ready.")
            return
        except Exception:
            time.sleep(3)


def fetch_history(symbol):
    print(f"Fetching history: {symbol}")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="5d", interval="1m").dropna()
    print(f"  {symbol}: {len(df)} rows")
    return df


def main():
    kinesis = get_kinesis()
    wait_for_stream(kinesis)

    histories = {s: fetch_history(s) for s in SYMBOLS}
    max_len = max(len(df) for df in histories.values())
    print(f"Replaying {max_len} data points (looping). Interval={INTERVAL}s")

    idx = 0
    while True:
        for symbol in SYMBOLS:
            df = histories[symbol]
            row = df.iloc[idx % len(df)]
            record = {
                "symbol":    symbol,
                "timestamp": datetime.utcnow().isoformat(),
                "open":      round(float(row["Open"]),  4),
                "high":      round(float(row["High"]),  4),
                "low":       round(float(row["Low"]),   4),
                "close":     round(float(row["Close"]), 4),
                "volume":    int(row["Volume"]),
            }
            try:
                kinesis.put_record(
                    StreamName=STREAM_NAME,
                    Data=json.dumps(record),
                    PartitionKey=symbol,
                )
                print(f"[{symbol}] close=${record['close']:.2f}")
            except Exception as e:
                print(f"Error sending {symbol}: {e}")
        idx += 1
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

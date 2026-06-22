import boto3
import json
import time
import os
import math
import random
from datetime import datetime

ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
STREAM_NAME  = os.getenv("KINESIS_STREAM", "stock-price-stream")
SYMBOLS      = os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT,TSLA").split(",")
INTERVAL     = float(os.getenv("INTERVAL", "3"))

# 初期株価（実際の価格帯に近い値）
INITIAL_PRICES = {
    "AAPL":  195.0,
    "GOOGL": 175.0,
    "MSFT":  415.0,
    "TSLA":  250.0,
}

# 銘柄ごとのボラティリティ（TSLA は高め）
VOLATILITY = {
    "AAPL":  0.0015,
    "GOOGL": 0.0015,
    "MSFT":  0.0012,
    "TSLA":  0.0030,
}


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


def next_price(symbol, current):
    """幾何ブラウン運動で次の価格を生成"""
    sigma = VOLATILITY.get(symbol, 0.002)
    mu    = 0.00005  # 微小な上昇トレンド
    shock = sigma * random.gauss(0, 1)
    new_close = current * math.exp(mu + shock)
    new_close = max(new_close, 1.0)

    spread = new_close * 0.0008
    open_p = current + random.uniform(-spread, spread)
    high_p = max(open_p, new_close) + abs(random.gauss(0, spread))
    low_p  = min(open_p, new_close) - abs(random.gauss(0, spread))

    return {
        "symbol":    symbol,
        "timestamp": datetime.utcnow().isoformat(),
        "open":      round(open_p,    4),
        "high":      round(high_p,    4),
        "low":       round(low_p,     4),
        "close":     round(new_close, 4),
        "volume":    random.randint(100_000, 5_000_000),
    }, new_close


def main():
    kinesis = get_kinesis()
    wait_for_stream(kinesis)

    prices = {s: INITIAL_PRICES.get(s, 100.0) for s in SYMBOLS}
    print(f"Starting simulation for: {SYMBOLS}")

    while True:
        for symbol in SYMBOLS:
            record, prices[symbol] = next_price(symbol, prices[symbol])
            try:
                kinesis.put_record(
                    StreamName=STREAM_NAME,
                    Data=json.dumps(record),
                    PartitionKey=symbol,
                )
                print(f"[{symbol}] close=${record['close']:.2f}  vol={record['volume']:,}")
            except Exception as e:
                print(f"Error sending {symbol}: {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

import boto3
import json
import time
import os
from decimal import Decimal

ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
STREAM_NAME  = os.getenv("KINESIS_STREAM", "stock-price-stream")
TABLE_NAME   = os.getenv("DYNAMODB_TABLE", "stock-prices")


def get_clients():
    kwargs = dict(
        endpoint_url=ENDPOINT_URL,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    return boto3.client("kinesis", **kwargs), boto3.resource("dynamodb", **kwargs)


def wait_for_stream(kinesis):
    print(f"Waiting for Kinesis stream '{STREAM_NAME}'...")
    while True:
        try:
            kinesis.describe_stream_summary(StreamName=STREAM_NAME)
            print("Stream ready.")
            return
        except Exception:
            time.sleep(3)


def get_shard_iterators(kinesis):
    shards = kinesis.list_shards(StreamName=STREAM_NAME)["Shards"]
    iterators = []
    for shard in shards:
        resp = kinesis.get_shard_iterator(
            StreamName=STREAM_NAME,
            ShardId=shard["ShardId"],
            ShardIteratorType="LATEST",
        )
        iterators.append(resp["ShardIterator"])
    return iterators


def store(table, data):
    table.put_item(Item={
        "symbol":    data["symbol"],
        "timestamp": data["timestamp"],
        "open":      Decimal(str(data["open"])),
        "high":      Decimal(str(data["high"])),
        "low":       Decimal(str(data["low"])),
        "close":     Decimal(str(data["close"])),
        "volume":    data["volume"],
    })


def main():
    kinesis, dynamodb = get_clients()
    wait_for_stream(kinesis)
    table = dynamodb.Table(TABLE_NAME)

    iterators = get_shard_iterators(kinesis)
    print(f"Consuming {len(iterators)} shard(s)...")

    while True:
        next_iterators = []
        for it in iterators:
            try:
                resp = kinesis.get_records(ShardIterator=it, Limit=100)
                for rec in resp["Records"]:
                    data = json.loads(rec["Data"])
                    store(table, data)
                    print(f"Stored [{data['symbol']}] close=${data['close']:.2f} @ {data['timestamp']}")
                nxt = resp.get("NextShardIterator")
                if nxt:
                    next_iterators.append(nxt)
            except Exception as e:
                print(f"Error: {e}")
                next_iterators.append(it)
        iterators = next_iterators
        time.sleep(1)


if __name__ == "__main__":
    main()

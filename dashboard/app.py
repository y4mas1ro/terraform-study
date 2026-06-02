import streamlit as st
import boto3
import pandas as pd
import plotly.graph_objects as go
from boto3.dynamodb.conditions import Key
import os
import time

ENDPOINT_URL  = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
TABLE_NAME    = os.getenv("DYNAMODB_TABLE", "stock-prices")
SYMBOLS       = os.getenv("SYMBOLS", "AAPL,GOOGL,MSFT,TSLA").split(",")
REFRESH_SEC   = int(os.getenv("REFRESH_INTERVAL", "5"))

st.set_page_config(page_title="Stock Dashboard", page_icon="📈", layout="wide")


@st.cache_resource
def get_table():
    db = boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT_URL,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )
    return db.Table(TABLE_NAME)


def query_symbol(symbol, limit=120):
    table = get_table()
    resp = table.query(
        KeyConditionExpression=Key("symbol").eq(symbol),
        ScanIndexForward=False,
        Limit=limit,
    )
    items = resp.get("Items", [])
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(int)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def make_chart(df, symbol):
    color = "#00c49f"
    latest = df["close"].iloc[-1]
    first  = df["close"].iloc[0]
    if latest < first:
        color = "#ff4b4b"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["close"],
        mode="lines",
        fill="tozeroy",
        line=dict(width=2, color=color),
        fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.1)",
        name=symbol,
        hovertemplate="$%{y:.2f}<br>%{x}<extra></extra>",
    ))
    fig.update_layout(
        height=240,
        margin=dict(l=0, r=0, t=5, b=0),
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=True),
        yaxis=dict(showgrid=True, gridcolor="#333"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── Layout ──────────────────────────────────────────────────────────────────
st.title("📈 Real-time Stock Dashboard")
st.caption("Yahoo Finance → Kinesis (ministack) → DynamoDB → Streamlit")

placeholder = st.empty()

while True:
    with placeholder.container():
        cols = st.columns(len(SYMBOLS))
        for i, symbol in enumerate(SYMBOLS):
            df = query_symbol(symbol)
            with cols[i]:
                if df.empty:
                    st.metric(symbol, "–", "waiting for data...")
                    continue

                latest    = df["close"].iloc[-1]
                prev      = df["close"].iloc[-2] if len(df) > 1 else latest
                delta     = latest - prev
                delta_pct = (delta / prev * 100) if prev else 0

                st.metric(
                    label=f"**{symbol}**",
                    value=f"${latest:.2f}",
                    delta=f"{delta:+.2f} ({delta_pct:+.2f}%)",
                )
                st.plotly_chart(make_chart(df, symbol), use_container_width=True)

        st.caption(f"Last updated: {time.strftime('%H:%M:%S')} · 自動更新: {REFRESH_SEC}秒ごと")

    time.sleep(REFRESH_SEC)
    st.rerun()

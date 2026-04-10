#!/usr/bin/env python3
"""
fetch_market.py — 抓取市場數據快照（股市、匯率、原油、黃金、加密貨幣）
輸出 JSON，供 LLM 寫市場快照時引用確切數字。

Usage: python3 fetch_market.py [--output market.json]

⚠️ FALLBACK NOTE (2026-04-02):
yfinance 經常被 Yahoo Finance rate limit 擋掉，導致亞股數據缺失。
如果 yfinance 失敗，可用 web_fetch 抓 Trading Economics 作為備用：
  - https://tradingeconomics.com/taiwan/stock-market (TAIEX)
  - https://tradingeconomics.com/japan/stock-market (Nikkei 225)
  這些頁面用靜態 HTML，web_fetch 可以直接抓到數據。
"""
import argparse
import json
import sys
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    print("需要 yfinance: pip install yfinance", file=sys.stderr)
    sys.exit(1)


TICKERS = {
    # US indices
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow Jones": "^DJI",
    # Europe
    "STOXX 600": "^STOXX",
    # Asia
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Shanghai Composite": "000001.SS",
    "TAIEX": "^TWII",
    # Forex
    "USD/JPY": "JPY=X",
    "EUR/USD": "EURUSD=X",
    "USD/TWD": "TWD=X",
    # Commodities
    "WTI Crude": "CL=F",
    "Brent Crude": "BZ=F",
    "Gold": "GC=F",
    # Crypto
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
}


def fetch_all():
    results = {}
    symbols = list(TICKERS.values())
    names = list(TICKERS.keys())

    # Batch download for efficiency
    try:
        data = yf.download(symbols, period="5d", progress=False, threads=True)
    except Exception as e:
        print(f"yfinance batch download failed: {e}", file=sys.stderr)
        return results

    close = data.get("Close", data.get("Adj Close"))
    if close is None or close.empty:
        print("No close data returned", file=sys.stderr)
        return results

    for name, symbol in TICKERS.items():
        try:
            if symbol in close.columns:
                series = close[symbol].dropna()
            elif len(TICKERS) == 1:
                series = close.dropna()
            else:
                continue

            if len(series) < 2:
                continue

            latest = float(series.iloc[-1])
            prev = float(series.iloc[-2])
            change_pct = ((latest - prev) / prev) * 100

            # Freshness: strictly within 24h of now (UTC). Anything older — including
            # stock closes older than a day — is stale and should not be reported.
            last_ts = series.index[-1]
            if last_ts.tzinfo is None:
                last_ts = last_ts.tz_localize("UTC")
            age_hours = round(
                (datetime.now(timezone.utc) - last_ts.to_pydatetime()).total_seconds()
                / 3600,
                1,
            )
            is_fresh = age_hours <= 24

            results[name] = {
                "price": round(latest, 2),
                "prev_close": round(prev, 2),
                "change_pct": round(change_pct, 2),
                "date": str(series.index[-1].date()),
                "age_hours": age_hours,
                "is_fresh": is_fresh,
            }
        except Exception as e:
            print(f"Error processing {name}: {e}", file=sys.stderr)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()

    print("Fetching market data...", file=sys.stderr)
    data = fetch_all()

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "markets": data,
    }

    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()

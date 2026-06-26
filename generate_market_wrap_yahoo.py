from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import urllib.parse
import urllib.request
from typing import Any

from market_wrap_common import summary_line_europe, summary_line_us, write_market_outputs
from market_wrap_common import load_json


USER_AGENT = "Mozilla/5.0"
UTC = dt.timezone.utc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-path",
        default=str(pathlib.Path(__file__).resolve().parent / "market_wrap_yahoo_config.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(pathlib.Path(__file__).resolve().parent / "output"),
    )
    parser.add_argument("--market", choices=["all", "us", "europe"], default="all")
    parser.add_argument("--as-of-date")
    return parser.parse_args()


def parse_as_of_date(raw: str | None) -> dt.date:
    if raw:
        return dt.date.fromisoformat(raw)
    return dt.datetime.now(UTC).date()


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        import json

        return json.load(response)


def fetch_series(symbol: str, start: dt.date, end: dt.date, price_scale: float = 1.0) -> list[tuple[dt.date, float]]:
    period1 = int(dt.datetime.combine(start, dt.time.min, tzinfo=UTC).timestamp())
    period2 = int(dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=UTC).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
        f"?period1={period1}&period2={period2}&interval=1d&includePrePost=false&events=div%2Csplits"
    )
    payload = fetch_json(url)
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise RuntimeError(f"Yahoo Finance returned no chart result for {symbol}.")

    row = result[0]
    timestamps = row.get("timestamp") or []
    closes = (((row.get("indicators") or {}).get("quote") or [{}])[0].get("close")) or []

    series: list[tuple[dt.date, float]] = []
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        price_date = dt.datetime.fromtimestamp(timestamp, UTC).date()
        series.append((price_date, round(float(close) * price_scale, 6)))

    series.sort(key=lambda item: item[0])
    if not series:
        raise RuntimeError(f"Yahoo Finance returned empty price series for {symbol}.")
    return series


def get_point_on_or_before(series: list[tuple[dt.date, float]], target_date: dt.date) -> tuple[dt.date, float] | None:
    eligible = [item for item in series if item[0] <= target_date]
    return eligible[-1] if eligible else None


def get_previous_point(series: list[tuple[dt.date, float]], target_date: dt.date) -> tuple[dt.date, float] | None:
    eligible = [item for item in series if item[0] < target_date]
    return eligible[-1] if eligible else None


def build_row(item: dict[str, Any], series_by_symbol: dict[str, list[tuple[dt.date, float]]], summary_date: dt.date) -> dict[str, Any] | None:
    symbol = item["symbol"]
    series = series_by_symbol.get(symbol)
    if not series:
        return None

    current = get_point_on_or_before(series, summary_date)
    if not current:
        return None

    previous = get_previous_point(series, current[0])
    if not previous:
        return None

    current_date, last = current
    _, prev = previous
    change = last - prev
    change_pct = (change / prev) * 100 if prev else 0.0

    return {
        "Name": item["name"],
        "Symbol": symbol,
        "Date": current_date.isoformat(),
        "Last": round(last, 4),
        "Previous": round(prev, 4),
        "Change": round(change, 4),
        "ChangePct": round(change_pct, 4),
        "ChangeStyle": item.get("changeStyle", "pct"),
    }


def build_us_payload(
    market_config: dict[str, Any],
    series_by_symbol: dict[str, list[tuple[dt.date, float]]],
    summary_date: dt.date,
) -> dict[str, Any]:
    index_rows = [build_row(item, series_by_symbol, summary_date) for item in market_config["indices"]]
    macro_rows = [build_row(item, series_by_symbol, summary_date) for item in market_config.get("macro", [])]
    sector_rows = [build_row(item, series_by_symbol, summary_date) for item in market_config.get("sectors", [])]
    megacap_rows = [build_row(item, series_by_symbol, summary_date) for item in market_config.get("megacaps", [])]

    index_rows = [row for row in index_rows if row]
    macro_rows = [row for row in macro_rows if row]
    sector_rows = [row for row in sector_rows if row]
    megacap_rows = [row for row in megacap_rows if row]

    top_sectors = sorted(sector_rows, key=lambda row: row["ChangePct"], reverse=True)[:3]
    weakest_sectors = sorted(sector_rows, key=lambda row: row["ChangePct"])[:3]
    megacap_leaders = sorted(megacap_rows, key=lambda row: row["ChangePct"], reverse=True)[:3]
    megacap_laggards = sorted(megacap_rows, key=lambda row: row["ChangePct"])[:3]

    return {
        "marketKey": market_config["key"],
        "outputStem": market_config["outputStem"],
        "reportTitle": market_config["reportTitle"],
        "subtitleSuffix": market_config["subtitleSuffix"],
        "summaryDate": summary_date.isoformat(),
        "priceSource": "Yahoo Finance",
        "oneLineSummary": summary_line_us(index_rows, sector_rows, macro_rows),
        "indices": index_rows,
        "macro": macro_rows,
        "topSectors": top_sectors,
        "weakestSectors": weakest_sectors,
        "megacapLeaders": megacap_leaders,
        "megacapLaggards": megacap_laggards,
    }


def build_europe_payload(
    market_config: dict[str, Any],
    series_by_symbol: dict[str, list[tuple[dt.date, float]]],
    summary_date: dt.date,
) -> dict[str, Any]:
    index_rows = [build_row(item, series_by_symbol, summary_date) for item in market_config["indices"]]
    index_rows = [row for row in index_rows if row]

    return {
        "marketKey": market_config["key"],
        "outputStem": market_config["outputStem"],
        "reportTitle": market_config["reportTitle"],
        "subtitleSuffix": market_config["subtitleSuffix"],
        "summaryDate": summary_date.isoformat(),
        "priceSource": "Yahoo Finance",
        "oneLineSummary": summary_line_europe(index_rows),
        "indices": index_rows,
        "macro": [],
        "topSectors": [],
        "weakestSectors": [],
        "megacapLeaders": [],
        "megacapLaggards": [],
    }


def run_market(market_config: dict[str, Any], as_of_date: dt.date, output_dir: pathlib.Path) -> tuple[str, str]:
    items: list[dict[str, Any]] = []
    items.extend(market_config.get("indices", []))
    items.extend(market_config.get("macro", []))
    items.extend(market_config.get("sectors", []))
    items.extend(market_config.get("megacaps", []))

    start = as_of_date - dt.timedelta(days=15)
    series_by_symbol: dict[str, list[tuple[dt.date, float]]] = {}
    for item in items:
        symbol = item["symbol"]
        if symbol in series_by_symbol:
            continue
        series_by_symbol[symbol] = fetch_series(symbol, start, as_of_date, item.get("priceScale", 1.0))

    summary_series = series_by_symbol[market_config["summarySymbol"]]
    summary_point = get_point_on_or_before(summary_series, as_of_date)
    if not summary_point:
        raise RuntimeError(f"Unable to determine summary date for {market_config['key']}.")
    summary_date = summary_point[0]

    if market_config["key"] == "us":
        payload = build_us_payload(market_config, series_by_symbol, summary_date)
    else:
        payload = build_europe_payload(market_config, series_by_symbol, summary_date)

    write_market_outputs(output_dir, payload)
    return summary_date.isoformat(), market_config["outputStem"]


def main() -> None:
    args = parse_args()
    config = load_json(pathlib.Path(args.config_path))
    output_dir = pathlib.Path(args.output_dir)
    as_of_date = parse_as_of_date(args.as_of_date)

    markets = config["markets"]
    if args.market != "all":
        markets = [market for market in markets if market["key"] == args.market]

    if not markets:
        raise RuntimeError("No market configuration selected.")

    for market in markets:
        display_date, stem = run_market(market, as_of_date, output_dir)
        print(f"Generated {stem} for {display_date}")


if __name__ == "__main__":
    main()

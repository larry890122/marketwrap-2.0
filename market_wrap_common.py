from __future__ import annotations

import datetime as dt
import json
import pathlib
from typing import Any


LABELS_ZH = {
    "S&P 500": "S&P 500",
    "Dow Jones": "道瓊工業指數",
    "Nasdaq Composite": "那斯達克綜合指數",
    "Russell 2000": "羅素 2000",
    "VIX": "VIX",
    "US 10Y Treasury": "美國 10 年期公債殖利率",
    "DXY": "美元指數",
    "WTI Front": "WTI 原油近月",
    "Technology": "科技",
    "Financials": "金融",
    "Energy": "能源",
    "Health Care": "醫療保健",
    "Industrials": "工業",
    "Consumer Discretionary": "非必需消費",
    "Consumer Staples": "必需消費",
    "Utilities": "公用事業",
    "Materials": "原物料",
    "Real Estate": "不動產",
    "Communication Services": "通訊服務",
    "Apple": "Apple",
    "Microsoft": "Microsoft",
    "NVIDIA": "NVIDIA",
    "Amazon": "Amazon",
    "Alphabet": "Alphabet",
    "Meta": "Meta",
    "Tesla": "Tesla",
    "Broadcom": "Broadcom",
    "FTSE 100": "FTSE 100",
    "CAC 40": "CAC 40",
    "DAX": "DAX",
}


def get_label(name: str) -> str:
    return LABELS_ZH.get(name, name)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def format_signed(value: float, decimals: int = 2) -> str:
    return f"{value:+.{decimals}f}"


def format_last_value(row: dict[str, Any]) -> str:
    style = row.get("ChangeStyle", "pct")
    last = row.get("Last")
    if last is None:
        return "n/a"
    if style == "bps":
        return f"{last:.3f}%"
    return f"{last:.2f}"


def format_change_text(row: dict[str, Any]) -> str:
    style = row.get("ChangeStyle", "pct")
    if style == "abs":
        return format_signed(float(row.get("Change", 0.0)))
    if style == "bps":
        return f"{format_signed(float(row.get('Change', 0.0)) * 100)} bp"
    return f"{format_signed(float(row.get('ChangePct', 0.0)))}%"


def ranked_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "無資料"
    return "、".join(f"{get_label(row['Name'])} {format_change_text(row)}" for row in rows)


def display_lines(title: str, rows: list[dict[str, Any]]) -> list[str]:
    lines = [f"## {title}"]
    for row in rows:
        lines.append(f"- {get_label(row['Name'])}：{format_last_value(row)}（{format_change_text(row)}）")
    return lines


def tone_text(index_rows: list[dict[str, Any]]) -> str:
    moves = [float(row["ChangePct"]) for row in index_rows]
    if not moves:
        return "主要指數缺少資料"

    positive_count = sum(1 for move in moves if move > 0)
    negative_count = sum(1 for move in moves if move < 0)
    average = sum(moves) / len(moves)

    if positive_count == len(moves):
        if average >= 1:
            return "主要指數全面走強"
        if average >= 0.3:
            return "主要指數普遍收高"
        return "主要指數小幅上揚"

    if negative_count == len(moves):
        if average <= -1:
            return "主要指數全面走弱"
        if average <= -0.3:
            return "主要指數普遍收低"
        return "主要指數小幅回落"

    return "主要指數漲跌互見"


def summary_line_us(
    index_rows: list[dict[str, Any]],
    sector_rows: list[dict[str, Any]],
    macro_rows: list[dict[str, Any]],
) -> str:
    tone = tone_text(index_rows)
    if not sector_rows:
        return tone

    top_sector = max(sector_rows, key=lambda row: row["ChangePct"])
    bottom_sector = min(sector_rows, key=lambda row: row["ChangePct"])
    ten_year = next((row for row in macro_rows if row["Name"] == "US 10Y Treasury"), None)
    vix = next((row for row in macro_rows if row["Name"] == "VIX"), None)

    if ten_year and ten_year["Change"] > 0:
        rate_text = "美國 10 年期公債殖利率走高"
    elif ten_year and ten_year["Change"] < 0:
        rate_text = "美國 10 年期公債殖利率回落"
    else:
        rate_text = "美國 10 年期公債殖利率大致持平"

    if vix and vix["Change"] > 0:
        vix_text = "市場波動升溫"
    elif vix and vix["Change"] < 0:
        vix_text = "市場波動降溫"
    else:
        vix_text = "市場波動大致持平"

    return (
        f"{tone}，類股以{get_label(top_sector['Name'])}領漲、"
        f"{get_label(bottom_sector['Name'])}相對承壓；{rate_text}，{vix_text}。"
    )


def summary_line_europe(index_rows: list[dict[str, Any]]) -> str:
    if not index_rows:
        return "歐股主要指數缺少資料"

    positive = [row for row in index_rows if row["ChangePct"] > 0]
    negative = [row for row in index_rows if row["ChangePct"] < 0]
    leader = max(index_rows, key=lambda row: row["ChangePct"])
    laggard = min(index_rows, key=lambda row: row["ChangePct"])

    if positive and negative:
        tone = "歐股三大指數漲跌互見"
    elif positive:
        tone = "歐股三大指數全面走高"
    else:
        tone = "歐股三大指數全面走低"

    return f"{tone}，{get_label(leader['Name'])}表現相對較強，{get_label(laggard['Name'])}相對承壓。"


def render_market_markdown(payload: dict[str, Any]) -> list[str]:
    summary_date = dt.date.fromisoformat(payload["summaryDate"])
    display_date_zh = f"{summary_date.year}年{summary_date.month:02d}月{summary_date.day:02d}日"

    lines = [
        f"# {payload['reportTitle']} | {payload['summaryDate']}",
        "",
        f"副標：{display_date_zh} {payload['subtitleSuffix']}",
        "",
        "## 盤勢摘要",
        payload.get("oneLineSummary", "無摘要"),
    ]

    top_sectors = payload.get("topSectors") or []
    weakest_sectors = payload.get("weakestSectors") or []
    megacap_leaders = payload.get("megacapLeaders") or []
    megacap_laggards = payload.get("megacapLaggards") or []

    if top_sectors:
        lines.append(f"- 最強族群：{ranked_summary(top_sectors)}")
    if weakest_sectors:
        lines.append(f"- 最弱族群：{ranked_summary(weakest_sectors)}")
    if megacap_leaders:
        lines.append(f"- 大型股強勢：{ranked_summary(megacap_leaders)}")
    if megacap_laggards:
        lines.append(f"- 大型股弱勢：{ranked_summary(megacap_laggards)}")

    commentary = payload.get("marketCommentary") or {}
    if commentary.get("comment"):
        lines.extend(
            [
                "",
                "## 市場評論",
                commentary["comment"],
            ]
        )
        if commentary.get("driverSummary"):
            lines.append(f"- 驅動摘要：{commentary['driverSummary']}")
        if commentary.get("marketImplication"):
            lines.append(f"- 關鍵觀察：{commentary['marketImplication']}")

    lines.append("")
    lines.extend(display_lines("主要指數", payload.get("indices") or []))

    macro_rows = payload.get("macro") or []
    if macro_rows:
        lines.append("")
        lines.extend(display_lines("跨資產觀察", macro_rows))

    if top_sectors:
        lines.append("")
        lines.extend(display_lines("領漲族群", top_sectors))
    if weakest_sectors:
        lines.append("")
        lines.extend(display_lines("領跌族群", weakest_sectors))
    if megacap_leaders:
        lines.append("")
        lines.extend(display_lines("大型股強勢名單", megacap_leaders))
    if megacap_laggards:
        lines.append("")
        lines.extend(display_lines("大型股弱勢名單", megacap_laggards))

    sources = commentary.get("sources") or []
    if sources:
        lines.extend(["", "## 參考來源"])
        for source in sources:
            source_name = source.get("source_name", "Unknown")
            title = source.get("title", source_name)
            url = source.get("url", "")
            if url:
                lines.append(f"- [{source_name}] {title} - {url}")
            else:
                lines.append(f"- [{source_name}] {title}")

    return lines


def write_market_outputs(output_dir: pathlib.Path, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    display_date = payload["summaryDate"]
    stem = payload["outputStem"]
    markdown_lines = render_market_markdown(payload)
    markdown_text = "\n".join(markdown_lines).rstrip() + "\n"

    dated_markdown = output_dir / f"{display_date}_{stem}.md"
    latest_markdown = output_dir / f"latest_{stem}.md"
    dated_json = output_dir / f"{display_date}_{stem}.json"
    latest_json = output_dir / f"latest_{stem}.json"

    dated_markdown.write_text(markdown_text, encoding="utf-8")
    latest_markdown.write_text(markdown_text, encoding="utf-8")
    write_json(dated_json, payload)
    write_json(latest_json, payload)

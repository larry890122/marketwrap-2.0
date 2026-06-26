from __future__ import annotations

import argparse
import html
import os
import pathlib
import smtplib
from email.message import EmailMessage
from typing import Any

from market_wrap_common import (
    compact_source_host,
    format_change_text,
    format_last_value,
    get_label,
    load_json,
    ranked_summary,
)


def parse_args() -> argparse.Namespace:
    root = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--us-payload-path", default=str(root / "output" / "latest_us_market_wrap.json"))
    parser.add_argument("--europe-payload-path", default=str(root / "output" / "latest_europe_market_snapshot.json"))
    parser.add_argument("--us-markdown-path", default=str(root / "output" / "latest_us_market_wrap.md"))
    parser.add_argument("--europe-markdown-path", default=str(root / "output" / "latest_europe_market_snapshot.md"))
    parser.add_argument("--recipient", default=os.environ.get("EMAIL_TO", ""))
    parser.add_argument("--sender", default=os.environ.get("GMAIL_SENDER", ""))
    parser.add_argument("--password", default=os.environ.get("GMAIL_APP_PASSWORD", ""))
    parser.add_argument("--smtp-host", default=os.environ.get("GMAIL_SMTP_HOST", "smtp.gmail.com"))
    parser.add_argument("--smtp-port", type=int, default=int(os.environ.get("GMAIL_SMTP_PORT", "465")))
    parser.add_argument("--print-only", action="store_true")
    return parser.parse_args()


def format_row(row: dict[str, Any]) -> str:
    return f"- {get_label(row.get('Name', 'Unknown'))}: {format_last_value(row)} ({format_change_text(row)})"


def build_source_line(source: dict[str, Any]) -> str:
    source_name = source.get("source_name", "Unknown")
    title = source.get("title", "Untitled")
    host = compact_source_host(source.get("url", ""))
    if host:
        return f"- {source_name}: {title} [{host}]"
    return f"- {source_name}: {title}"


def build_market_section(title: str, payload: dict[str, Any]) -> list[str]:
    divider = "=" * 72
    lines = [divider, title, divider]
    lines.append(f"日期            {payload.get('summaryDate', 'n/a')}")
    if payload.get("priceSource"):
        lines.append(f"價格來源        {payload['priceSource']}")
    if payload.get("oneLineSummary"):
        lines.extend(["", "HEADLINE", payload["oneLineSummary"]])

    commentary = payload.get("marketCommentary") or {}
    if commentary.get("driverSummary"):
        lines.extend(["", "CORE DRIVER", commentary["driverSummary"]])
    if commentary.get("comment"):
        lines.extend(["", "BUYSIDE VIEW", commentary["comment"]])
    if commentary.get("marketImplication"):
        lines.extend(["", "NEXT SESSION", commentary["marketImplication"]])

    lines.extend(["", "MARKET DASHBOARD"])
    for row in payload.get("indices") or []:
        lines.append(format_row(row))

    macro_rows = payload.get("macro") or []
    if macro_rows:
        lines.extend(["", "MACRO / COMMODITIES"])
        for row in macro_rows:
            lines.append(format_row(row))

    top_sectors = payload.get("topSectors") or []
    weakest_sectors = payload.get("weakestSectors") or []
    if top_sectors or weakest_sectors:
        lines.extend(["", "STYLE / SECTORS"])
        lines.append(f"- 領漲族群: {ranked_summary(top_sectors)}")
        lines.append(f"- 領跌族群: {ranked_summary(weakest_sectors)}")

    megacap_leaders = payload.get("megacapLeaders") or []
    megacap_laggards = payload.get("megacapLaggards") or []
    if megacap_leaders or megacap_laggards:
        lines.append(f"- Mega-cap 相對抗跌: {ranked_summary(megacap_leaders)}")
        lines.append(f"- Mega-cap 壓力來源: {ranked_summary(megacap_laggards)}")

    sources = commentary.get("sources") or []
    if sources:
        lines.extend(["", "SOURCES"])
        for source in sources:
            lines.append(build_source_line(source))

    return lines


def build_rows_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e5e7eb;color:#111827;'>{html.escape(get_label(row.get('Name', 'Unknown')))}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:right;color:#111827;'>{html.escape(format_last_value(row))}</td>"
            f"<td style='padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:right;color:#111827;'>{html.escape(format_change_text(row))}</td>"
            "</tr>"
        )

    return (
        "<table role='presentation' style='width:100%;border-collapse:collapse;margin-top:10px;font-size:13px;'>"
        "<thead><tr>"
        "<th style='padding:8px 10px;text-align:left;border-bottom:2px solid #cbd5e1;color:#475569;'>項目</th>"
        "<th style='padding:8px 10px;text-align:right;border-bottom:2px solid #cbd5e1;color:#475569;'>最新</th>"
        "<th style='padding:8px 10px;text-align:right;border-bottom:2px solid #cbd5e1;color:#475569;'>變動</th>"
        "</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def build_source_html(source: dict[str, Any]) -> str:
    source_name = html.escape(source.get("source_name", "Unknown"))
    title = html.escape(source.get("title", "Untitled"))
    url = source.get("url", "")
    host = compact_source_host(url)
    host_html = (
        f"<span style='display:inline-block;margin-left:8px;padding:2px 8px;border:1px solid #d1d5db;border-radius:999px;color:#6b7280;font-size:11px;'>{html.escape(host)}</span>"
        if host
        else ""
    )
    if url:
        return (
            "<li style='margin-bottom:8px;'>"
            f"<strong>{source_name}</strong>: "
            f"<a href='{html.escape(url, quote=True)}' style='color:#0f172a;text-decoration:none;'>{title}</a>"
            f"{host_html}</li>"
        )
    return f"<li style='margin-bottom:8px;'><strong>{source_name}</strong>: {title}</li>"


def build_market_section_html(title: str, payload: dict[str, Any]) -> str:
    commentary = payload.get("marketCommentary") or {}
    summary = html.escape(payload.get("oneLineSummary", "無資料"))
    driver = html.escape(commentary.get("driverSummary", ""))
    comment = html.escape(commentary.get("comment", ""))
    implication = html.escape(commentary.get("marketImplication", ""))
    sources = commentary.get("sources") or []

    sector_block = ""
    top_sectors = payload.get("topSectors") or []
    weakest_sectors = payload.get("weakestSectors") or []
    megacap_leaders = payload.get("megacapLeaders") or []
    megacap_laggards = payload.get("megacapLaggards") or []
    if top_sectors or weakest_sectors or megacap_leaders or megacap_laggards:
        sector_block = (
            "<div style='margin-top:16px;padding:16px 18px;border:1px solid #e5e7eb;background:#fafaf9;'>"
            "<div style='font-size:11px;letter-spacing:1.2px;color:#64748b;text-transform:uppercase;'>Style & Sectors</div>"
            f"<p style='margin:10px 0 0;color:#111827;line-height:1.7;'><strong>領漲族群：</strong>{html.escape(ranked_summary(top_sectors))}</p>"
            f"<p style='margin:6px 0 0;color:#111827;line-height:1.7;'><strong>領跌族群：</strong>{html.escape(ranked_summary(weakest_sectors))}</p>"
            f"<p style='margin:6px 0 0;color:#111827;line-height:1.7;'><strong>Mega-cap 相對抗跌：</strong>{html.escape(ranked_summary(megacap_leaders))}</p>"
            f"<p style='margin:6px 0 0;color:#111827;line-height:1.7;'><strong>Mega-cap 壓力來源：</strong>{html.escape(ranked_summary(megacap_laggards))}</p>"
            "</div>"
        )

    macro_html = build_rows_html(payload.get("macro") or [])
    macro_block = ""
    if macro_html:
        macro_block = (
            "<div style='margin-top:18px;'>"
            "<div style='font-size:11px;letter-spacing:1.2px;color:#64748b;text-transform:uppercase;margin-bottom:6px;'>Macro / Commodities</div>"
            f"{macro_html}</div>"
        )

    sources_block = ""
    if sources:
        sources_block = (
            "<div style='margin-top:18px;'>"
            "<div style='font-size:11px;letter-spacing:1.2px;color:#64748b;text-transform:uppercase;margin-bottom:8px;'>Sources</div>"
            f"<ul style='margin:0;padding-left:18px;color:#111827;'>{''.join(build_source_html(source) for source in sources)}</ul>"
            "</div>"
        )

    return (
        "<section style='margin-top:28px;padding:26px 28px;border:1px solid #d6d3d1;background:#ffffff;'>"
        f"<div style='font-size:22px;font-weight:700;color:#111827;'>{html.escape(title)}</div>"
        f"<div style='margin-top:4px;color:#6b7280;font-size:13px;'>Date: {html.escape(payload.get('summaryDate', 'n/a'))} | Price Source: {html.escape(payload.get('priceSource', 'n/a'))}</div>"
        "<div style='margin-top:18px;padding:18px 20px;background:#f8fafc;border-left:4px solid #0f172a;'>"
        "<div style='font-size:11px;letter-spacing:1.2px;color:#64748b;text-transform:uppercase;'>Headline</div>"
        f"<div style='margin-top:8px;font-size:16px;line-height:1.7;color:#111827;'>{summary}</div>"
        "</div>"
        "<div style='margin-top:18px;padding:18px 20px;border:1px solid #e5e7eb;background:#fff;'>"
        "<div style='font-size:11px;letter-spacing:1.2px;color:#64748b;text-transform:uppercase;'>Buyside View</div>"
        f"<p style='margin:10px 0 0;color:#111827;line-height:1.8;'><strong>核心驅動：</strong>{driver}</p>"
        f"<p style='margin:10px 0 0;color:#111827;line-height:1.8;'><strong>買方觀點：</strong>{comment}</p>"
        f"<p style='margin:10px 0 0;color:#111827;line-height:1.8;'><strong>下一交易日觀察：</strong>{implication}</p>"
        "</div>"
        "<div style='margin-top:18px;'>"
        "<div style='font-size:11px;letter-spacing:1.2px;color:#64748b;text-transform:uppercase;margin-bottom:6px;'>Market Dashboard</div>"
        f"{build_rows_html(payload.get('indices') or [])}</div>"
        f"{macro_block}"
        f"{sector_block}"
        f"{sources_block}"
        "</section>"
    )


def build_subject(us_payload: dict[str, Any], europe_payload: dict[str, Any]) -> str:
    us_date = us_payload.get("summaryDate", "")
    eu_date = europe_payload.get("summaryDate", "")
    if us_date and us_date == eu_date:
        return f"每日市場晨報 | {us_date}"
    if us_date and eu_date:
        return f"每日市場晨報 | US {us_date} | Europe {eu_date}"
    return "每日市場晨報"


def build_body(us_payload: dict[str, Any], europe_payload: dict[str, Any]) -> str:
    lines = ["DAILY MARKET WRAP", ""]
    lines.extend(build_market_section("美股", us_payload))
    lines.append("")
    lines.extend(build_market_section("歐股", europe_payload))
    return "\n".join(lines)


def build_html_body(us_payload: dict[str, Any], europe_payload: dict[str, Any]) -> str:
    summary_date = html.escape(us_payload.get("summaryDate") or europe_payload.get("summaryDate", ""))
    return (
        "<html><body style='margin:0;padding:0;background:#f5f5f4;font-family:Georgia,\"Times New Roman\",serif;'>"
        "<div style='max-width:980px;margin:0 auto;padding:32px 20px 40px;'>"
        "<div style='background:#0f172a;color:#f8fafc;padding:28px 32px;border-bottom:4px solid #cbd5e1;'>"
        "<div style='font-size:12px;letter-spacing:1.8px;text-transform:uppercase;color:#cbd5e1;'>Daily Market Wrap</div>"
        "<div style='margin-top:10px;font-size:30px;font-weight:700;'>Global Morning Note</div>"
        f"<div style='margin-top:8px;font-size:14px;color:#e2e8f0;'>Reporting Date: {summary_date}</div>"
        "</div>"
        f"{build_market_section_html('美股', us_payload)}"
        f"{build_market_section_html('歐股', europe_payload)}"
        "</div></body></html>"
    )


def attach_file(message: EmailMessage, path: pathlib.Path) -> None:
    if not path.exists():
        return
    message.add_attachment(
        path.read_bytes(),
        maintype="text",
        subtype="markdown" if path.suffix.lower() == ".md" else "plain",
        filename=path.name,
    )


def send_email(
    *,
    smtp_host: str,
    smtp_port: int,
    sender: str,
    password: str,
    recipient: str,
    subject: str,
    body: str,
    html_body: str,
    attachments: list[pathlib.Path],
) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    message.add_alternative(html_body, subtype="html")

    for attachment in attachments:
        attach_file(message, attachment)

    with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
        server.login(sender, password)
        server.send_message(message)


def main() -> None:
    args = parse_args()
    us_payload = load_json(pathlib.Path(args.us_payload_path))
    europe_payload = load_json(pathlib.Path(args.europe_payload_path))
    subject = build_subject(us_payload, europe_payload)
    body = build_body(us_payload, europe_payload)
    html_body = build_html_body(us_payload, europe_payload)

    if args.print_only:
        print(subject)
        print("")
        print(body)
        return

    if not args.recipient:
        raise ValueError("Missing recipient. Set --recipient or EMAIL_TO.")
    if not args.sender:
        raise ValueError("Missing sender. Set --sender or GMAIL_SENDER.")
    if not args.password:
        raise ValueError("Missing app password. Set --password or GMAIL_APP_PASSWORD.")

    attachments = [pathlib.Path(args.us_markdown_path), pathlib.Path(args.europe_markdown_path)]
    send_email(
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
        sender=args.sender,
        password=args.password,
        recipient=args.recipient,
        subject=subject,
        body=body,
        html_body=html_body,
        attachments=attachments,
    )
    print(f"Sent market wrap email to {args.recipient}.")


if __name__ == "__main__":
    main()

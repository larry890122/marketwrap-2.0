from __future__ import annotations

import argparse
import os
import pathlib
import smtplib
from email.message import EmailMessage
from typing import Any

from market_wrap_common import format_change_text, format_last_value, get_label, load_json, ranked_summary


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


def build_market_section(title: str, payload: dict[str, Any]) -> list[str]:
    lines = [title]
    lines.append(f"日期: {payload.get('summaryDate', 'n/a')}")
    if payload.get("priceSource"):
        lines.append(f"股價來源: {payload['priceSource']}")
    if payload.get("oneLineSummary"):
        lines.append(f"盤勢摘要: {payload['oneLineSummary']}")

    commentary = payload.get("marketCommentary") or {}
    if commentary.get("driverSummary"):
        lines.append(f"驅動摘要: {commentary['driverSummary']}")
    if commentary.get("comment"):
        lines.append(f"市場評論: {commentary['comment']}")
    if commentary.get("marketImplication"):
        lines.append(f"關鍵觀察: {commentary['marketImplication']}")

    lines.append("")
    lines.append("主要指數")
    for row in payload.get("indices") or []:
        lines.append(format_row(row))

    macro_rows = payload.get("macro") or []
    if macro_rows:
        lines.append("")
        lines.append("跨資產觀察")
        for row in macro_rows:
            lines.append(format_row(row))

    top_sectors = payload.get("topSectors") or []
    weakest_sectors = payload.get("weakestSectors") or []
    if top_sectors or weakest_sectors:
        lines.append("")
        lines.append(f"領漲族群: {ranked_summary(top_sectors)}")
        lines.append(f"領跌族群: {ranked_summary(weakest_sectors)}")

    megacap_leaders = payload.get("megacapLeaders") or []
    megacap_laggards = payload.get("megacapLaggards") or []
    if megacap_leaders or megacap_laggards:
        lines.append("")
        lines.append(f"大型股強勢: {ranked_summary(megacap_leaders)}")
        lines.append(f"大型股弱勢: {ranked_summary(megacap_laggards)}")

    sources = commentary.get("sources") or []
    if sources:
        lines.append("")
        lines.append("參考來源")
        for source in sources:
            lines.append(f"- [{source.get('source_name', 'Unknown')}] {source.get('title', 'Untitled')} - {source.get('url', '')}")

    return lines


def build_subject(us_payload: dict[str, Any], europe_payload: dict[str, Any]) -> str:
    us_date = us_payload.get("summaryDate", "")
    eu_date = europe_payload.get("summaryDate", "")
    if us_date and us_date == eu_date:
        return f"每日市場晨報 | {us_date}"
    if us_date and eu_date:
        return f"每日市場晨報 | US {us_date} | EU {eu_date}"
    return "每日市場晨報"


def build_body(us_payload: dict[str, Any], europe_payload: dict[str, Any]) -> str:
    lines = ["每日市場晨報", ""]
    lines.extend(build_market_section("美股", us_payload))
    lines.append("")
    lines.extend(build_market_section("歐股", europe_payload))
    return "\n".join(lines)


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
    attachments: list[pathlib.Path],
) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

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
        attachments=attachments,
    )
    print(f"Sent market wrap email to {args.recipient}.")


if __name__ == "__main__":
    main()

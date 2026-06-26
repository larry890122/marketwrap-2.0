from __future__ import annotations

import datetime as dt
import pathlib

from market_wrap_common import load_json, write_market_outputs


UTC = dt.timezone.utc
OUTPUT_DIR = pathlib.Path(__file__).resolve().parent / "output"


def build_sources(context: dict) -> list[dict]:
    return [
        {
            "source_name": article.get("source_name", "Unknown"),
            "title": article.get("title", "Untitled"),
            "url": article.get("url", ""),
            "published_at": article.get("published_at"),
        }
        for article in (context.get("articles") or [])[:5]
    ]


def build_us_commentary(context: dict) -> dict:
    return {
        "comment": (
            "美股表面上是窄幅震盪，實際訊號是風險偏好從 mega-cap 科技向循環與小型股分散。"
            "S&P 500 幾乎收平、Nasdaq 下跌 0.46%，但 Dow 與 Russell 2000 分別上漲 0.14% 與 0.71%；"
            "同時工業、醫療與原材料領漲，非必需消費與通訊服務落後，顯示投資人沒有全面降風險，"
            "而是在 Apple、Microsoft、Amazon 壓力下重新評估 AI 交易的擁擠度。10 年期殖利率回落提供估值支撐，"
            "但 WTI 反彈與 VIX 小升使盤面仍偏選股而非單邊 beta。"
        ),
        "driverSummary": (
            "主軸是科技股退潮與殖利率下行並存；Micron 相關 AI 情緒未能抵消大型科技與非必需消費賣壓，"
            "資金轉向工業、醫療、原材料與小型股。"
        ),
        "marketImplication": (
            "下一交易日觀察 Nasdaq 能否止跌、Apple 與軟體權重股是否續弱，以及小型股/工業的相對強勢能否延續；"
            "若殖利率續降但科技仍弱，市場可能維持高分化輪動。"
        ),
        "sources": build_sources(context),
        "model": "codex-gpt-5.4",
        "generated_at": dt.datetime.now(UTC).isoformat(),
        "fallback_used": True,
    }


def build_europe_commentary(context: dict) -> dict:
    return {
        "comment": (
            "歐股呈現較乾淨的反彈，FTSE 100、CAC 40 與 DAX 同步收高，其中 DAX 上漲 1.03% 領先。"
            "油價回落舒緩通膨與實質所得壓力，疊加美國 AI 鏈財報後風險情緒修復，使歐洲盤面從防禦轉向景氣循環。"
            "FTSE 受能源壓力緩和與大型股支撐，DAX 的領漲則反映出口與工業 beta 對全球成長預期更敏感；"
            "這不是單純避險反彈，而是資金重新承擔景氣與估值風險。"
        ),
        "driverSummary": (
            "核心驅動是油價回到較可控區間、通膨壓力下降，以及全球 AI/景氣循環情緒修復；"
            "DAX 領漲凸顯市場願意加回高 beta 歐洲工業曝險。"
        ),
        "marketImplication": (
            "後續重點是能源價格是否延續回落、歐元與利率是否壓抑出口股估值，以及 DAX 領漲能否擴散到 CAC 與 FTSE；"
            "若擴散失敗，歐股反彈仍可能回到指數內部分化。"
        ),
        "sources": build_sources(context),
        "model": "codex-gpt-5.4",
        "generated_at": dt.datetime.now(UTC).isoformat(),
        "fallback_used": True,
    }


def update_market(payload_name: str, context_name: str, commentary_builder, report_title: str, subtitle: str) -> None:
    payload_path = OUTPUT_DIR / payload_name
    context_path = OUTPUT_DIR / context_name
    payload = load_json(payload_path)
    context = load_json(context_path)
    payload["reportTitle"] = report_title
    payload["subtitleSuffix"] = subtitle
    payload["marketCommentary"] = commentary_builder(context)
    write_market_outputs(OUTPUT_DIR, payload)


def main() -> None:
    update_market(
        "latest_us_market_wrap.json",
        "latest_us_market_news_context.json",
        build_us_commentary,
        "美股市場晨報",
        "美股收盤回顧",
    )
    update_market(
        "latest_europe_market_snapshot.json",
        "latest_europe_market_news_context.json",
        build_europe_commentary,
        "歐股市場晨報",
        "歐股收盤回顧",
    )
    print("Updated Codex-authored market commentary for US and Europe.")


if __name__ == "__main__":
    main()

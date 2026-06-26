from __future__ import annotations

import pathlib

from market_wrap_common import load_json, write_market_outputs


ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


def rewrite_us() -> None:
    path = OUTPUT_DIR / "latest_us_market_wrap.json"
    payload = load_json(path)
    payload["reportTitle"] = "美股投資晨報"
    payload["subtitleSuffix"] = "美股收盤整理"
    payload["priceSource"] = "Yahoo Finance"
    payload["oneLineSummary"] = (
        "主要指數漲跌互見，Dow 與小型股維持相對強勢，但大型科技拖累 Nasdaq；"
        "殖利率回落未能完全抵消 Apple 與 mega-cap 的賣壓。"
    )
    payload["marketCommentary"] = {
        "comment": (
            "昨晚美股的核心不是單純指數持平，而是結構性分化進一步擴大。Micron 財報強勁帶動部分 AI 與記憶體鏈反彈，但 Apple 因產品漲價下跌 6.1%，"
            "連同 Microsoft、Amazon 走弱，讓 Nasdaq 下跌 0.46%、S&P 500 幾乎收平；相對地，Dow 與 Russell 2000 分別上漲 0.14% 與 0.71%，"
            "顯示資金正從 mega-cap 成長轉向工業、醫療保健與較高 domestic beta 的區塊。10 年期美債殖利率回落約 0.6bp，本應有利 duration，"
            "但大市仍被權值股獲利了結主導，代表市場目前交易的是擁擠部位重整，而非全面 risk-off。"
        ),
        "driverSummary": (
            "主驅動是 Micron 帶來的 AI 樂觀與 Apple 價格上調引發的需求疑慮同時存在，"
            "使半導體與大型平台股表現分化，資金因此轉向工業、小型股與醫療保健。"
        ),
        "marketImplication": (
            "隔日觀察重點在於半導體強勢能否擴散到更廣泛科技，還是市場仍只接受去 mega-cap 化的輪動。"
        ),
        "sources": [
            {
                "source_name": "AP",
                "title": "Wall Street drifts to a mixed finish after Micron soars and Apple drops",
                "url": "https://apnews.com/article/119e56cb6b1fc041b46af9bb778bdf07",
                "published_at": "2026-06-25",
            },
            {
                "source_name": "AP",
                "title": "How major US stock indexes fared Thursday 6/25/2026",
                "url": "https://apnews.com/article/18741e4dabafb7a44b41231159f10599",
                "published_at": "2026-06-25",
            },
            {
                "source_name": "MarketWatch",
                "title": "U.S. stocks end the day mixed as Big Tech takes a hit",
                "url": "https://www.marketwatch.com/livecoverage/stock-market-today-dow-s-p-500-nasdaq-micron-earnings-results-pce-inflation-data/card/u-s-stocks-end-the-day-mixed-as-big-tech-takes-a-hit-VJobHwP9HUe7YiDMrasG",
                "published_at": "2026-06-25",
            },
        ],
        "model": "codex-gpt-5.4",
        "generated_at": payload.get("marketCommentary", {}).get("generated_at"),
        "fallback_used": False,
    }
    write_market_outputs(OUTPUT_DIR, payload)


def rewrite_europe() -> None:
    path = OUTPUT_DIR / "latest_europe_market_snapshot.json"
    payload = load_json(path)
    payload["reportTitle"] = "歐洲股市晨報"
    payload["subtitleSuffix"] = "歐股收盤整理"
    payload["priceSource"] = "Yahoo Finance"
    payload["oneLineSummary"] = (
        "歐股三大指數同步收高，DAX 領漲、FTSE 100 創兩個月高位；"
        "油價回到戰前區間與 AI 情緒修復，帶動景氣與風險資產同步反彈。"
    )
    payload["marketCommentary"] = {
        "comment": (
            "歐股昨晚是較乾淨的 broad-based rebound。FTSE 100、CAC 40 與 DAX 分別上漲 0.65%、0.55% 與 1.03%，其中 DAX 領先，"
            "反映市場不只在交易油價回落帶來的通膨舒緩，也開始把 Micron 財報後重啟的 AI 與景氣循環情緒反映到歐洲出口與工業權重股。"
            "Guardian 報導指出油價一度回到伊朗衝突前水準，英國市場同時受房屋與利率敏感股帶動；這與德股領漲相互印證，說明風格已由前一日的防守分化，"
            "轉向對 cyclicals 與 beta 更友善的配置。對 buyside 而言，關鍵不是指數創高本身，而是這波反彈是否能在油價止跌後仍維持。"
        ),
        "driverSummary": (
            "主驅動是油價回落舒緩通膨與利率壓力，加上美國半導體財報重新點燃 AI 風險偏好，"
            "使德國工業與英國利率敏感板塊同步受惠。"
        ),
        "marketImplication": (
            "若油價維持低位且 DAX 繼續領先，代表歐股反彈正從通膨舒緩交易擴散到成長與景氣交易。"
        ),
        "sources": [
            {
                "source_name": "Guardian",
                "title": "Ryanair ditches family seating fees; Markets at record highs as oil hits pre-Iran war levels - as it happened",
                "url": "https://www.theguardian.com/business/live/2026/jun/25/oil-price-lowest-since-us-iran-war-uk-firms-burnham-reeves-haldane-latest-news-updates",
                "published_at": "2026-06-25",
            },
            {
                "source_name": "WSJ",
                "title": "Stock Futures Higher as Micron Revives AI Enthusiasm, Oil Hits Prewar Level",
                "url": "https://www.wsj.com/finance/stocks/stock-futures-higher-as-micron-revives-ai-enthusiasm-oil-hits-prewar-level-7d3f7bc0",
                "published_at": "2026-06-25",
            },
        ],
        "model": "codex-gpt-5.4",
        "generated_at": payload.get("marketCommentary", {}).get("generated_at"),
        "fallback_used": False,
    }
    write_market_outputs(OUTPUT_DIR, payload)


def main() -> None:
    rewrite_us()
    rewrite_europe()
    print("Rewrote latest market wrap payloads with UTF-8 AI commentary.")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import urllib.request
from typing import Any

from market_wrap_common import load_json, write_market_outputs


UTC = dt.timezone.utc
OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.4-mini"


def parse_args() -> argparse.Namespace:
    root = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["all", "us", "europe"], default="all")
    parser.add_argument("--output-dir", default=str(root / "output"))
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    return parser.parse_args()


def derive_context_path(output_dir: pathlib.Path, market_key: str) -> pathlib.Path:
    if market_key == "us":
        return output_dir / "latest_us_market_news_context.json"
    return output_dir / "latest_europe_market_news_context.json"


def derive_payload_path(output_dir: pathlib.Path, market_key: str) -> pathlib.Path:
    if market_key == "us":
        return output_dir / "latest_us_market_wrap.json"
    return output_dir / "latest_europe_market_snapshot.json"


def build_market_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "summaryDate": payload.get("summaryDate"),
        "oneLineSummary": payload.get("oneLineSummary"),
        "indices": payload.get("indices", []),
        "macro": payload.get("macro", []),
        "topSectors": payload.get("topSectors", []),
        "weakestSectors": payload.get("weakestSectors", []),
        "megacapLeaders": payload.get("megacapLeaders", []),
        "megacapLaggards": payload.get("megacapLaggards", []),
    }


def build_prompts(payload: dict[str, Any], context: dict[str, Any]) -> tuple[str, str]:
    market_name = "美股" if payload["marketKey"] == "us" else "歐股"
    system_prompt = (
        "你是 buyside 早會前使用的市場策略助理。"
        "請根據提供的價格訊號與新聞材料，產出繁體中文、高資訊密度、偏 sell-side / buyside 晨報口吻的市場評論。"
        "不要空泛，不要用『市場觀望』『投資人消化消息』這類低資訊密度句子。"
        "只根據提供資料歸納，不得杜撰。"
        "輸出必須是 JSON，且只包含 comment、driverSummary、marketImplication 三個欄位。"
        "三個欄位的值都必須是單一字串，不可輸出陣列、物件或條列。"
    )

    instructions = {
        "market": market_name,
        "rules": [
            "comment 必須為單一段落，100-180 字。",
            "先說市場主驅動，再說板塊/風格傳導，最後點出隔日最值得觀察的延伸。",
            "至少交叉引用一個價格訊號與一個新聞驅動。",
            "如果新聞不足，只能保守歸納並明確反映材料有限。",
            "marketImplication 只做觀察，不提供投資建議或交易指令。",
        ],
        "marketData": build_market_snapshot(payload),
        "articles": context.get("articles", []),
    }
    user_prompt = json.dumps(instructions, ensure_ascii=False, indent=2)
    return system_prompt, user_prompt


def extract_response_text(response_payload: dict[str, Any]) -> str:
    if isinstance(response_payload.get("output_text"), str) and response_payload["output_text"].strip():
        return response_payload["output_text"].strip()

    texts: list[str] = []
    for item in response_payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    return "\n".join(texts).strip()


def parse_model_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_text_field(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        parts = [normalize_text_field(item) for item in value]
        return " ".join(part for part in parts if part).strip()

    if isinstance(value, dict):
        for key in ("text", "summary", "value", "content"):
            normalized = normalize_text_field(value.get(key))
            if normalized:
                return normalized
        return json.dumps(value, ensure_ascii=False).strip()

    if value is None:
        return ""

    return str(value).strip()


def call_openai(api_key: str, model: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    body = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
        "max_output_tokens": 700,
    }
    payload_bytes = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_ENDPOINT,
        data=payload_bytes,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        response_payload = json.loads(response.read().decode("utf-8"))

    return parse_model_json(extract_response_text(response_payload))


def fallback_commentary(payload: dict[str, Any], context: dict[str, Any], model: str, reason: str) -> dict[str, Any]:
    articles = context.get("articles", [])
    sources = [
        {
            "source_name": article.get("source_name", "Unknown"),
            "title": article.get("title", "Untitled"),
            "url": article.get("url", ""),
            "published_at": article.get("published_at"),
        }
        for article in articles[:5]
    ]

    implication = "請優先觀察指數與板塊是否延續同方向，並留意利率、油價與權值股對 headline 的再定價。"
    return {
        "comment": f"評論生成失敗：{reason}。請先參考下方價格摘要與外部來源，手動判讀當日市場主驅動。",
        "driverSummary": payload.get("oneLineSummary", "缺少可用的市場摘要。"),
        "marketImplication": implication,
        "sources": sources,
        "model": model,
        "generated_at": dt.datetime.now(UTC).isoformat(),
        "fallback_used": True,
        "error": reason,
    }


def build_commentary(payload: dict[str, Any], context: dict[str, Any], api_key: str, model: str) -> dict[str, Any]:
    articles = context.get("articles", [])
    fallback_used = len(articles) < 2 or context.get("fallbackUsed", False)

    if not api_key:
        return fallback_commentary(payload, context, model, "OpenAI API key missing")

    system_prompt, user_prompt = build_prompts(payload, context)
    try:
        model_response = call_openai(api_key, model, system_prompt, user_prompt)
    except Exception as exc:
        return fallback_commentary(payload, context, model, str(exc))

    if not isinstance(model_response, dict):
        return fallback_commentary(
            payload,
            context,
            model,
            f"Unexpected model response type: {type(model_response).__name__}",
        )

    sources = [
        {
            "source_name": article.get("source_name", "Unknown"),
            "title": article.get("title", "Untitled"),
            "url": article.get("url", ""),
            "published_at": article.get("published_at"),
        }
        for article in articles[:5]
    ]

    return {
        "comment": normalize_text_field(model_response.get("comment", "")),
        "driverSummary": normalize_text_field(model_response.get("driverSummary", "")),
        "marketImplication": normalize_text_field(model_response.get("marketImplication", "")),
        "sources": sources,
        "model": model,
        "generated_at": dt.datetime.now(UTC).isoformat(),
        "fallback_used": fallback_used,
    }


def main() -> None:
    args = parse_args()
    output_dir = pathlib.Path(args.output_dir)
    model = args.model or DEFAULT_MODEL
    markets = ["us", "europe"] if args.market == "all" else [args.market]

    for market_key in markets:
        payload = load_json(derive_payload_path(output_dir, market_key))
        context_path = derive_context_path(output_dir, market_key)
        context = load_json(context_path) if context_path.exists() else {"articles": [], "fallbackUsed": True}

        payload["marketCommentary"] = build_commentary(payload, context, args.api_key, model)
        write_market_outputs(output_dir, payload)
        print(f"Updated commentary for {market_key}")


if __name__ == "__main__":
    main()

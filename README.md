# Daily Market Wrap GitHub Package

這個資料夾是可直接放上 GitHub 的精簡版本，使用 Yahoo Finance 抓股價，並由 GitHub Actions 每天上午 8:00（台北時間）自動產出市場晨報，再寄到 Gmail。

## 功能

- Yahoo Finance 價格資料抓取
- 美股與歐股晨報 Markdown / JSON 輸出
- 多來源市場新聞蒐集
- OpenAI 生成 buyside 口吻市場評論
- Gmail 自動寄送與 GitHub Actions 排程

## 主要檔案

- `generate_market_wrap_yahoo.py`
- `generate_market_news_context.py`
- `generate_market_commentary.py`
- `run_daily_market_wrap.py`
- `send_market_wrap_email.py`
- `market_wrap_common.py`
- `market_wrap_yahoo_config.json`
- `.github/workflows/market-wrap-yahoo.yml`

## GitHub Actions Secrets

到 GitHub：
`Settings` -> `Secrets and variables` -> `Actions`

新增以下 secrets：

- `EMAIL_TO`：收件人 Gmail
- `GMAIL_SENDER`：寄件 Gmail
- `GMAIL_APP_PASSWORD`：寄件 Gmail 的 App Password
- `OPENAI_API_KEY`：OpenAI API key

可選環境變數：

- `OPENAI_MODEL`：預設 `gpt-5.4-mini`

## Gmail 設定

寄件 Gmail 需要：

1. 開啟兩步驟驗證
2. 建立 App Password
3. 把該密碼填進 `GMAIL_APP_PASSWORD`

## 排程時間

工作流使用 UTC cron：

- `0 0 * * *`

這等於台北時間每天 `08:00`。

## 本地測試

```powershell
python .\run_daily_market_wrap.py --target-date 2026-06-24
python .\send_market_wrap_email.py --print-only
```

如果沒有 `OPENAI_API_KEY`，流程仍會完成，但市場評論會進入 fallback 模式，email 會註明評論生成失敗。

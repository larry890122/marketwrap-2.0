# Daily Market Wrap

這是一個可直接放上 GitHub 的精簡版本，會抓取 Yahoo Finance 市場資料、彙整新聞脈絡、生成繁體中文買方口吻評論，並透過 Gmail 寄出每日美股與歐股晨報。

## 功能

- 產出美股與歐股的 JSON / Markdown 晨報
- 蒐集 Google News RSS 與原文摘要作為市場背景
- 使用 OpenAI 生成買方風格市場評論
- 支援 GitHub Actions 定時執行與 artifact 上傳
- 若 OpenAI 暫時不可用，可自動走 fallback 評論流程

## 專案檔案

- `generate_market_wrap_yahoo.py`：抓取指數、利率、原油與產業 ETF 資料
- `generate_market_news_context.py`：整理美股與歐股新聞脈絡
- `generate_market_commentary.py`：生成市場評論
- `send_market_wrap_email.py`：預覽或寄送 email
- `run_daily_market_wrap.py`：串起整條日報流程
- `market_wrap_common.py`：共用格式化與輸出函式
- `.github/workflows/market-wrap-yahoo.yml`：GitHub Actions 排程

## 執行需求

- Python `3.12` 或以上
- 不需要額外安裝第三方套件，目前全部使用標準函式庫
- 若要寄信，需要 Gmail App Password
- 若要 AI 評論，需要 `OPENAI_API_KEY`

## 本地執行

```powershell
python -X utf8 .\run_daily_market_wrap.py --target-date 2026-06-25
python -X utf8 .\send_market_wrap_email.py --print-only
```

若只想單獨測試某一步，也可以分開跑：

```powershell
python -X utf8 .\generate_market_wrap_yahoo.py --market all
python -X utf8 .\generate_market_news_context.py --market all
python -X utf8 .\generate_market_commentary.py --market all
```

## GitHub 設定

在 GitHub repository 中開啟：
`Settings` -> `Secrets and variables` -> `Actions`

新增以下 `Secrets`：

- `EMAIL_TO`：收件人 Gmail
- `GMAIL_SENDER`：寄件 Gmail
- `GMAIL_APP_PASSWORD`：Gmail App Password
- `OPENAI_API_KEY`：OpenAI API key

可選的 `Variables`：

- `OPENAI_MODEL`：預設為 `gpt-5.4-mini`

## Workflow 排程

目前排程為：

- `0 0 * * *`

也就是台北時間每天上午 `08:00`。

工作流會依序執行：

1. 抓取最新市場資料
2. 建立新聞背景
3. 生成市場評論
4. 預覽 email 內容
5. 正式寄送 email
6. 上傳 `output/` 產物作為 artifact

## 輸出與版控

- `output/` 是執行後自動產生的資料夾，不納入版控
- `__pycache__/`、虛擬環境與本機設定檔也已排除
- 推上 GitHub 前，不需要手動清理每日輸出

## 備註

- 若沒有 `OPENAI_API_KEY`，流程仍可完成，但會使用 fallback 評論內容
- `generate_market_commentary.py` 已加入模型回傳型別防呆，避免 `driverSummary` 回傳陣列時讓流程中斷

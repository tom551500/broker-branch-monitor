# 分點監控（Broker Branch Monitor）

自動監控特定券商分點，是否對你的自選股清單有大量買賣超，透過 Telegram 推播。

## 運作方式

每週一到五台灣時間 16:00（分點資料公布後）自動執行：

1. 依照 `src/config.py` 裡的 `LEGEND_BROKERS`，查詢每個分點今天買賣了哪些股票
   （資料來源：富邦e01證券網站的公開分點進出排行頁面，免費但非正式 API，
   網站改版時可能需要調整 `src/fetcher.py` 的 `parse_table()`）
2. 過濾成只保留出現在 `WATCHLIST`（你的自選股清單）裡的股票
3. 淨買賣超低於 `NOTIFY_THRESHOLD` 張的視為雜訊，不推播
4. 組成訊息推播到 Telegram
5. 同時存一份 JSON 到 `output/`，上傳為 GitHub Actions artifact（留存30天）

## 設定步驟

### 1. 填入你的 56 檔監控清單

打開 `src/config.py`，把 `WATCHLIST` 換成你實際的股票清單。

### 2. 申請 Telegram Bot

1. 在 Telegram 搜尋 `@BotFather`，傳 `/newbot`，依指示取得 **Bot Token**
2. 跟你剛建立的 Bot 隨便傳一句話（例如「hi」）
3. 瀏覽器打開：
   `https://api.telegram.org/bot<你的TOKEN>/getUpdates`
   在回傳的 JSON 裡找到 `"chat":{"id": 數字}`，這個數字就是你的 **Chat ID**

### 3. 設定 GitHub Secrets

Repo 的 Settings → Secrets and variables → Actions → New repository secret：

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | 上一步拿到的 Bot Token |
| `TELEGRAM_CHAT_ID` | 上一步拿到的 Chat ID |

### 4. 推上 GitHub，排程就會自動生效

workflow 檔案在 `.github/workflows/daily_report.yml`，也支援手動觸發：
Actions 分頁 → Daily Broker Branch Report → Run workflow。

## 本機測試

```bash
pip install -r requirements.txt
cd src

# 先測資料抓取邏輯，不會真的推播（沒設環境變數會自動略過 Telegram）
python run_report.py

# 設定好環境變數後才能測試真的推播
export TELEGRAM_BOT_TOKEN="你的token"
export TELEGRAM_CHAT_ID="你的chat_id"
python run_report.py
```

## 可以調整的設定（`src/config.py`）

- `LEGEND_BROKERS`：要監控的分點清單，可自行增減
- `WATCHLIST`：你的自選股清單
- `DEFAULT_DAYS`：查詢區間天數，預設只看當日（1）
- `NOTIFY_THRESHOLD`：淨買賣超推播門檻（張），避免小量變動洗版

## 已知限制

- 資料來源是公開網頁，不是正式 API：網站結構若改版，爬蟲可能失效，
  需要重新調整 `src/fetcher.py` 裡的 `parse_table()`
- `LEGEND_BROKERS` 清單是市場上流傳的「知名分點」整理，風格標籤主觀，
  僅供參考，不保證準確或持續有效
- 僅供個人研究使用，資料不構成投資建議

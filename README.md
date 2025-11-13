# 台股新聞熱門股票追蹤系統

自動化追蹤台股新聞中提及的熱門股票,結合三大法人買超排行,提供即時股價與分析。

## 功能特色

- 🔥 **新聞熱度追蹤**: 自動爬取台股新聞,統計股票被提及次數
- 📊 **買超排行整合**: 結合三大法人買超數據
- 💹 **即時股價**: 從 Yahoo 股市抓取最新股價資訊
- 🤖 **自動化執行**: GitHub Actions 每天自動更新 4 次
- 📱 **網頁介面**: 提供美觀的視覺化展示介面

## 系統架構

```
├── stock_analysis.py          # 主程式
├── index.html                 # 網頁介面
├── requirements.txt           # Python 套件清單
├── .github/
│   └── workflows/
│       └── stock_analysis.yml # GitHub Actions 設定
└── StockInfo/                 # 資料儲存目錄
    ├── TSE_hotstock_data.json # 上市股票資料
    ├── OTC_hotstock_data.json # 上櫃股票資料
    ├── twstock_news.json      # 新聞資料
    ├── TSE_buy_ranking.txt    # 上市買超排行
    ├── OTC_buy_ranking.txt    # 上櫃買超排行
    ├── tse_company_list.csv   # 上市公司清單
    └── otc_company_list.csv   # 上櫃公司清單
```

## 快速開始

### 1. 準備資料檔案

在 `StockInfo/` 資料夾中放置以下檔案:

- `tse_company_list.csv`: 上市公司清單 (格式: 代碼,名稱,產業)
- `otc_company_list.csv`: 上櫃公司清單 (格式: 代碼,名稱,產業)
- `TSE_buy_ranking.txt`: 上市買超排行 (格式: #,代碼,名稱,買超張數)
- `OTC_buy_ranking.txt`: 上櫃買超排行 (格式: #,代碼,名稱,買超張數)

### 2. 啟用 GitHub Pages

1. 前往 Repository Settings
2. 找到 Pages 設定
3. Source 選擇 `Deploy from a branch`
4. Branch 選擇 `main` / `(root)`
5. Save

### 3. 設定 GitHub Actions

GitHub Actions 已自動設定,會在以下時間執行:
- 每天早上 9:00
- 每天早上 10:00
- 每天早上 11:00
- 每天早上 12:00
- **週六休息**

### 4. 手動執行

也可以手動觸發執行:
1. 前往 Actions 頁籤
2. 選擇 "Taiwan Stock Analysis"
3. 點擊 "Run workflow"

## 本地測試

```bash
# 安裝相依套件
pip install -r requirements.txt

# 執行分析
python stock_analysis.py

# 使用本地伺服器測試網頁
python -m http.server 8000
# 然後開啟瀏覽器訪問 http://localhost:8000
```

## 環境變數

可以透過環境變數設定執行模式:

```bash
# 只處理上市 (TSE)
export PROCESS_MODE=TSE

# 只處理上櫃 (OTC)
export PROCESS_MODE=OTC

# 同時處理上市與上櫃 (預設)
export PROCESS_MODE=BOTH
```

## 資料格式說明

### 公司清單 CSV 格式
```csv
1101,台泥,水泥工業
2330,台積電,半導體業
```

### 買超排行 TXT 格式
```
#,代碼,名稱,買超張數
1,2330,台積電,12345
2,2454,聯發科,6789
```

### 輸出 JSON 格式
```json
{
  "update_time": "2025-01-15 10:30:00",
  "market": "TSE",
  "total_news": 150,
  "hot_stocks_count": 20,
  "stocks": [
    {
      "code": "2330",
      "name": "台積電",
      "market": "TSE",
      "mention_count": 15,
      "yesterday_buy": 12345,
      "current_price": "580.00",
      "open_price": "575.00",
      "change": "+5.00",
      "change_percent": "+0.87%",
      "buy_volume": "8500",
      "sell_volume": "6200",
      "update_time": "2025-01-15 10:30:00"
    }
  ]
}
```

## 注意事項

⚠️ **重要提醒**:

1. **資料更新時間**: 台股交易時間為週一至週五 09:00-13:30,系統設定在 9:00-12:00 每小時執行一次
2. **週六休市**: GitHub Actions 設定週六不執行 (cron 設定 0-5 代表週日到週五)
3. **爬蟲限制**: Yahoo 股市有反爬蟲機制,請適當設定延遲時間 (目前為 1.5 秒)
4. **GitHub Actions 限制**: 免費帳號每月有 2000 分鐘的執行時間限制
5. **檔案大小**: JSON 檔案建議控制在 100KB 以內以確保載入速度

## 技術棧

- **後端**: Python 3.10
- **爬蟲**: requests, BeautifulSoup4
- **資料處理**: pandas
- **自動化**: GitHub Actions
- **前端**: HTML, CSS, JavaScript
- **部署**: GitHub Pages

## License

MIT License

## 作者

Frank - 台股分析愛好者

## 更新日誌

### 2025-01-15
- ✅ 從 Google Colab 遷移到 GitHub Actions
- ✅ 新增自動化排程執行
- ✅ 網頁介面支援自動載入 JSON
- ✅ 優化資料儲存結構

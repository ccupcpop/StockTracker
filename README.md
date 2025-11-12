# 📊 股票即時買賣盤監控系統

自動化股票買賣盤數據抓取系統，使用 GitHub Actions 每小時自動執行，並透過 GitHub Pages 提供網頁查看介面。

## ✨ 功能特色

- 🤖 **自動化抓取**: 使用 GitHub Actions 每小時自動抓取股票即時買賣盤數據
- 📈 **雙市場支援**: 同時支援台灣證交所 (TSE) 和櫃買中心 (OTC)
- 🧪 **測試模式**: 內建測試模式，可在非交易時間使用模擬數據測試系統
- 💾 **數據儲存**: 所有歷史數據自動儲存在 `data/` 目錄
- 🌐 **網頁查看**: 透過 GitHub Pages 提供美觀的數據查看介面
- 📜 **歷史記錄**: 保留最近 100 筆歷史數據供查詢
- 💾 **CSV 匯出**: 支援將數據匯出為 CSV 格式

## 🚀 快速開始

### 1. Fork 或複製此專案

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. 準備股票清單文件

確保專案根目錄有以下兩個文件：

- `TSE_buy_ranking.txt` - 上市買超股票清單
- `OTC_buy_ranking.txt` - 上櫃買超股票清單

文件格式範例：
```
# TSE - 2025-11-11
1,2337,旺宏,80345
2,6770,力積電,63108
...
```

### 3. 啟用 GitHub Actions

1. 進入專案的 **Settings** > **Actions** > **General**
2. 在 **Workflow permissions** 中選擇 **Read and write permissions**
3. 儲存設定

### 4. 啟用 GitHub Pages

1. 進入專案的 **Settings** > **Pages**
2. 在 **Source** 中選擇 **Deploy from a branch**
3. 選擇 **main** 分支和 **/docs** 目錄
4. 點擊 **Save**

### 5. 手動觸發第一次執行

1. 進入 **Actions** 標籤
2. 選擇 **股票數據抓取** workflow
3. 點擊 **Run workflow** 按鈕
4. 等待執行完成

### 6. 查看網頁

執行完成後，可透過以下網址查看：
```
https://YOUR_USERNAME.github.io/YOUR_REPO/
```

## 📁 專案結構

```
.
├── .github/
│   └── workflows/
│       └── fetch_data.yml          # GitHub Actions 配置
├── data/                            # 數據儲存目錄
│   ├── latest.json                  # 最新數據
│   ├── data_list.json               # 數據列表索引
│   └── stock_data_YYYYMMDD_HHMMSS.json  # 歷史數據
├── docs/
│   └── index.html                   # 網頁查看介面
├── fetch_stock_data.py              # 數據抓取腳本
├── TSE_buy_ranking.txt              # 上市買超清單
├── OTC_buy_ranking.txt              # 上櫃買超清單
└── README.md                        # 說明文件
```

## ⚙️ 配置說明

### 修改執行頻率

編輯 `.github/workflows/fetch_data.yml` 文件：

```yaml
on:
  schedule:
    - cron: '0 * * * *'  # 每小時執行一次
```

常用 cron 表達式範例：
- `0 * * * *` - 每小時執行
- `*/30 * * * *` - 每 30 分鐘執行
- `0 */2 * * *` - 每 2 小時執行
- `0 9-17 * * 1-5` - 週一到週五，每天 9:00-17:00 每小時執行

### 調整數據保留數量

編輯 `fetch_stock_data.py` 中的 `update_data_list` 函數：

```python
# 只保留最近 100 筆記錄
data_list = data_list[-100:]
```

## 📊 數據格式

### latest.json 結構

```json
{
  "timestamp": "20251112_143000",
  "date": "2025-11-12",
  "time": "14:30:00",
  "tse": [
    {
      "code": "2337",
      "name": "旺宏",
      "yesterday_buy": 80345,
      "currentPrice": "45.5",
      "buyTotal": 12500,
      "sellTotal": 8300,
      "diff": 4200,
      "time": "14:30:00",
      "success": true
    }
  ],
  "otc": [...]
}
```

## 🔧 本地測試

### 測試模式（推薦用於開發）

腳本內建測試模式，可在非交易時間使用模擬數據：

```bash
# 編輯 fetch_stock_data.py，設定 TEST_MODE = True
# 第 14-16 行

# 安裝依賴
pip install requests urllib3

# 執行腳本（使用模擬數據）
python fetch_stock_data.py
```

**測試模式特點**：
- ✅ 快速執行，無需網路連線
- ✅ 生成合理的模擬數據
- ✅ 適合功能開發和驗證
- ✅ 可在任何時間執行

詳細說明請參考 [TEST_MODE_GUIDE.md](TEST_MODE_GUIDE.md)

### 正式模式

```bash
# 編輯 fetch_stock_data.py，設定 TEST_MODE = False

# 安裝依賴
pip install requests urllib3

# 執行抓取腳本（抓取真實數據）
python fetch_stock_data.py
```

### 本地查看網頁

```bash
cd docs
python -m http.server 8000
```

然後開啟瀏覽器訪問 `http://localhost:8000`

## 📝 注意事項

1. **請求頻率**: 台灣證交所 API 有請求頻率限制，腳本已加入隨機延遲機制
2. **交易時間**: 建議在台股交易時間內執行才能獲取有效數據 (週一至週五 9:00-13:30)
3. **測試模式**: 開發測試時可啟用 TEST_MODE，部署前記得改為 False
4. **數據準確性**: 即時數據可能有延遲，僅供參考
5. **GitHub Actions 限制**: 免費帳號每月有 2000 分鐘的執行時間限制

## 🐛 疑難排解

### Actions 執行失敗

1. 檢查是否已啟用 **Read and write permissions**
2. 確認 `TSE_buy_ranking.txt` 和 `OTC_buy_ranking.txt` 文件存在
3. 查看 Actions 日誌中的錯誤訊息

### 網頁無法顯示

1. 確認 GitHub Pages 已正確設定
2. 等待幾分鐘讓 Pages 部署完成
3. 清除瀏覽器快取後重新載入

### 數據抓取失敗

1. 可能是證交所 API 暫時無法訪問
2. 股票代號可能不正確
3. 可能遇到請求頻率限制

## 📄 授權

MIT License

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

## ⚠️ 免責聲明

本系統僅供學習和研究使用，數據來源為台灣證交所公開資料。投資有風險，請謹慎決策。

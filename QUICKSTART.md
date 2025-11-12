# 🚀 快速開始指南

## 📦 方式一：直接使用（推薦）

### 步驟 1：建立 GitHub 儲存庫

1. 登入 GitHub
2. 點擊右上角 **+** > **New repository**
3. 填寫儲存庫名稱，例如：`stock-monitor`
4. 選擇 **Public**（GitHub Pages 需要）
5. 點擊 **Create repository**

### 步驟 2：上傳文件

方式 A - 使用 Git 命令行：

```bash
# 下載並解壓縮專案文件
cd stock-monitor-project

# 初始化 Git
git init
git add .
git commit -m "Initial commit"

# 連接到 GitHub
git remote add origin https://github.com/YOUR_USERNAME/stock-monitor.git
git branch -M main
git push -u origin main
```

方式 B - 使用 GitHub 網頁上傳：

1. 進入你的新儲存庫
2. 點擊 **uploading an existing file**
3. 拖曳所有文件到頁面（包括 `.github` 目錄）
4. 點擊 **Commit changes**

### 步驟 3：設定 GitHub Actions 權限

1. 進入儲存庫的 **Settings**
2. 點擊左側 **Actions** > **General**
3. 滾動到 **Workflow permissions**
4. 選擇 **Read and write permissions**
5. 勾選 **Allow GitHub Actions to create and approve pull requests**
6. 點擊 **Save**

### 步驟 4：啟用 GitHub Pages

1. 在 **Settings** 中點擊 **Pages**
2. 在 **Source** 選擇 **Deploy from a branch**
3. **Branch** 選擇 **main**
4. **Folder** 選擇 **/docs**
5. 點擊 **Save**

### 步驟 5：手動執行第一次抓取

**建議先用測試模式驗證**：

1. 確認 `fetch_stock_data.py` 中的 `TEST_MODE = True`（預設已啟用）
2. 點擊儲存庫上方的 **Actions** 標籤
3. 點擊左側的 **股票數據抓取**
4. 點擊右側的 **Run workflow** 按鈕
5. 點擊綠色的 **Run workflow** 確認
6. 等待執行完成（約 1-2 分鐘）

**確認成功後切換到正式模式**：

1. 編輯 `fetch_stock_data.py`，將第 16 行改為 `TEST_MODE = False`
2. 提交並推送更改：
   ```bash
   git add fetch_stock_data.py
   git commit -m "切換到正式模式"
   git push
   ```
3. 系統會自動開始抓取真實數據

💡 **提示**：測試模式使用模擬數據，速度更快，適合首次驗證流程

### 步驟 6：查看結果

執行完成後，訪問你的網站：
```
https://YOUR_USERNAME.github.io/stock-monitor/
```

## ⏰ 自動執行時間

系統會在以下時間自動執行：
- **每小時整點執行一次**
- 例如：00:00, 01:00, 02:00, ..., 23:00

建議的執行時間（台股交易時段）：
- 週一至週五 09:00 - 13:30

## 🔧 自訂執行時間

如果只想在交易時段執行，編輯 `.github/workflows/fetch_data.yml`：

```yaml
on:
  schedule:
    # 只在週一到週五的 9:00-13:00 每小時執行
    - cron: '0 9-13 * * 1-5'
```

常用 cron 表達式：

| 表達式 | 說明 |
|--------|------|
| `0 * * * *` | 每小時執行 |
| `*/30 * * * *` | 每 30 分鐘執行 |
| `0 */2 * * *` | 每 2 小時執行 |
| `0 9-17 * * 1-5` | 週一到週五 9:00-17:00 每小時執行 |
| `0 9,12,15 * * 1-5` | 週一到週五 9:00, 12:00, 15:00 執行 |

⚠️ **注意**：GitHub Actions 使用 UTC 時間，台灣時間 = UTC + 8 小時
- 如果要在台灣時間 09:00 執行，cron 應設為 `0 1 * * *` (UTC 01:00)

## 📊 更新股票清單

當你想追蹤不同的股票時：

1. 編輯 `TSE_buy_ranking.txt` 或 `OTC_buy_ranking.txt`
2. 提交並推送更改：
   ```bash
   git add *.txt
   git commit -m "更新股票清單"
   git push
   ```
3. GitHub Actions 會自動使用新清單

## 🐛 疑難排解

### 問題 1：Actions 執行失敗
**解決方法**：
1. 檢查 Actions 權限是否設為 "Read and write"
2. 查看 Actions 日誌找出錯誤訊息
3. 確認股票清單文件格式正確

### 問題 2：網頁顯示 404
**解決方法**：
1. 確認 GitHub Pages 已啟用
2. 確認選擇了正確的分支和目錄 (main / /docs)
3. 等待 2-5 分鐘讓 Pages 部署完成
4. 清除瀏覽器快取

### 問題 3：數據抓取失敗
**解決方法**：
1. 非交易時間可能無法取得數據（這是正常的）
2. 證交所 API 可能暫時無法訪問
3. 檢查股票代號是否正確
4. 查看 Actions 日誌中的詳細錯誤

### 問題 4：網頁載入空白
**解決方法**：
1. 確認至少執行過一次 Actions
2. 檢查 `data/` 目錄是否有 `latest.json`
3. 開啟瀏覽器開發者工具查看錯誤訊息

## 📈 進階功能

### 1. 測試模式

**適用場景**：
- 開發測試時
- 非交易時間（晚上、週末）
- 初次設定驗證流程
- 無網路連線時

**啟用方法**：
編輯 `fetch_stock_data.py`：
```python
# 第 14-16 行
TEST_MODE = True  # 測試模式
# TEST_MODE = False  # 正式模式
```

**特點**：
- ✅ 使用模擬數據，執行速度快
- ✅ 根據昨日買超量生成合理數據
- ✅ 數據會標記 `"test_mode": true`
- ✅ 可在任何時間執行

詳細說明：[TEST_MODE_GUIDE.md](TEST_MODE_GUIDE.md)

### 2. 本地測試

```bash
# 安裝依賴
pip install requests urllib3

# 執行腳本
python fetch_stock_data.py

# 本地查看網頁
cd docs
python -m http.server 8000
# 訪問 http://localhost:8000
```

### 3. 手動觸發執行

除了自動排程，你可以隨時手動執行：
1. 進入 **Actions** 標籤
2. 選擇 **股票數據抓取**
3. 點擊 **Run workflow**

### 3. 查看執行歷史

在 **Actions** 標籤中可以看到：
- 所有執行記錄
- 執行時間
- 執行狀態（成功/失敗）
- 詳細日誌

## 💡 提示

1. **第一次設定完成後**，建議手動執行一次確認運作正常
2. **非交易時間**執行可能無法取得有效數據
3. **GitHub Actions 免費額度**：每月 2000 分鐘，足夠每小時執行
4. **數據更新延遲**：證交所數據可能有 1-2 分鐘延遲

## 📞 需要協助？

如果遇到問題：
1. 查看專案的 README.md
2. 檢查 GitHub Actions 日誌
3. 確認所有設定步驟都已完成

---

祝你使用愉快！📊✨

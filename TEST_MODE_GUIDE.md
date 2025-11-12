# 🧪 測試模式使用說明

## 什麼是測試模式？

測試模式 (TEST_MODE) 讓你可以在**非交易時間**或**沒有網路連線**時，使用模擬數據來測試系統運作。

## 🔧 如何切換模式？

### 啟用測試模式（使用模擬數據）

編輯 `fetch_stock_data.py`，找到第 14-16 行：

```python
# ==================== 測試模式設定 ====================
# 設為 True 時使用模擬數據，False 時從證交所抓取真實數據
TEST_MODE = True
# ====================================================
```

### 啟用正式模式（抓取真實數據）

將 `TEST_MODE` 改為 `False`：

```python
# ==================== 測試模式設定 ====================
# 設為 True 時使用模擬數據，False 時從證交所抓取真實數據
TEST_MODE = False
# ====================================================
```

## 📊 模擬數據說明

### 數據生成邏輯

測試模式會根據**昨日買超量**生成合理的模擬數據：

1. **昨日買超股票** (yesterday_buy > 0)
   - 今日委買量較高（1.2-2.0 倍）
   - 今日委賣量較低（0.5-1.0 倍）

2. **昨日賣超股票** (yesterday_buy < 0)
   - 今日委買量較低（0.5-1.0 倍）
   - 今日委賣量較高（1.2-2.0 倍）

3. **股價範圍**：10-500 元之間隨機生成

4. **交易時間**：模擬 09:00-13:59 之間的時間

### 數據特點

✅ **合理性**：數據會根據昨日買超情況生成，更接近真實情況
✅ **隨機性**：每次執行都會生成不同數據
✅ **完整性**：包含所有必要欄位（價格、委買、委賣、時間等）
✅ **快速性**：不需要網路請求，執行速度快

## 🎯 使用場景

### 何時使用測試模式？

✅ **開發測試**：開發時快速驗證功能
✅ **非交易時間**：晚上或週末想看系統運作
✅ **網路受限**：無法連接證交所 API
✅ **學習演示**：教學或展示用途
✅ **初次設定**：第一次設定 GitHub Actions 時驗證流程

### 何時使用正式模式？

✅ **實際監控**：真正要追蹤股票買賣盤時
✅ **交易時間**：週一到週五 09:00-13:30
✅ **正式部署**：部署到 GitHub Actions 正式運行

## 📝 數據對比

### 測試模式數據範例

```json
{
  "code": "2337",
  "name": "旺宏",
  "yesterday_buy": 80345,
  "currentPrice": "117.94",
  "buyTotal": 14594,
  "sellTotal": 8214,
  "diff": 6380,
  "time": "11:20:52",
  "success": true
}
```

### 正式模式數據範例

```json
{
  "code": "2337",
  "name": "旺宏",
  "yesterday_buy": 80345,
  "currentPrice": "45.50",
  "buyTotal": 12500,
  "sellTotal": 8300,
  "diff": 4200,
  "time": "13:25:15",
  "success": true
}
```

## 🚀 實際操作流程

### 本地測試流程

```bash
# 1. 編輯腳本啟用測試模式
# 設定 TEST_MODE = True

# 2. 執行腳本
python fetch_stock_data.py

# 3. 查看生成的數據
cat data/latest.json

# 4. 在瀏覽器中查看網頁
cd docs
python -m http.server 8000
# 訪問 http://localhost:8000
```

### GitHub Actions 部署流程

```bash
# 1. 先用測試模式驗證（TEST_MODE = True）
git add fetch_stock_data.py
git commit -m "測試：使用模擬數據驗證系統"
git push

# 2. 在 GitHub Actions 中手動執行一次
# 確認執行成功

# 3. 切換到正式模式（TEST_MODE = False）
git add fetch_stock_data.py
git commit -m "正式：切換到真實數據抓取"
git push
```

## ⚙️ 進階設定

### 調整模擬數據參數

如果想要調整模擬數據的生成規則，可以編輯 `fetch_stock_data.py` 中的 `generate_mock_data` 函數：

```python
def generate_mock_data(stock_code, stock_name, yesterday_buy):
    base_volume = abs(yesterday_buy) // 10  # 調整基礎委託量
    
    # 調整委買委賣的倍數範圍
    if yesterday_buy > 0:
        buy_multiplier = random.uniform(1.2, 2.0)   # 可以修改這裡
        sell_multiplier = random.uniform(0.5, 1.0)  # 可以修改這裡
    
    # 調整價格範圍
    current_price = round(random.uniform(10, 500), 2)  # 可以修改範圍
```

### 調整執行速度

測試模式下的延遲時間可以調整：

```python
# 在 get_stock_order_info 函數中
time.sleep(random.uniform(0.01, 0.05))  # 調整延遲範圍
```

## 📊 數據驗證

### 檢查數據品質

執行後可以檢查以下項目：

```bash
# 1. 檢查數據檔案是否生成
ls -lh data/

# 2. 檢查 JSON 格式是否正確
python -m json.tool data/latest.json > /dev/null && echo "JSON 格式正確"

# 3. 檢查數據筆數
cat data/latest.json | grep -o '"code"' | wc -l

# 4. 檢查測試模式標記
cat data/latest.json | grep test_mode
```

應該看到：
- ✅ `latest.json` 存在
- ✅ `test_mode: true` 存在
- ✅ TSE 和 OTC 各有數據

## ⚠️ 重要提醒

1. **部署前切換**：記得部署到 GitHub Actions 前將 TEST_MODE 改為 False
2. **數據標記**：測試模式生成的數據會有 `"test_mode": true` 標記
3. **不要混用**：建議清空 data 目錄後再切換模式，避免混淆
4. **網頁顯示**：測試模式的數據在網頁上也能正常顯示
5. **執行速度**：測試模式執行速度更快（無網路延遲）

## 💡 最佳實踐

### 推薦工作流程

```
1. 本地開發 → 使用測試模式
   ↓
2. 功能驗證 → 使用測試模式
   ↓
3. GitHub 首次部署 → 使用測試模式驗證流程
   ↓
4. 確認無誤後 → 切換到正式模式
   ↓
5. 正式運行 → 定期檢查數據品質
```

### Git 提交訊息範例

```bash
# 測試階段
git commit -m "🧪 測試：啟用測試模式進行功能驗證"

# 正式上線
git commit -m "✅ 正式：切換到真實數據抓取模式"
```

## 🔍 疑難排解

### 問題 1：測試模式下沒有生成數據

**檢查**：
- 確認 TEST_MODE = True
- 確認股票清單文件存在
- 查看終端機錯誤訊息

### 問題 2：數據看起來不合理

**說明**：測試模式是隨機生成的模擬數據，僅供測試使用，不代表真實市場情況。

### 問題 3：切換到正式模式後無法抓取數據

**可能原因**：
- 非交易時間
- 證交所 API 無法連接
- 請求過於頻繁被限制

**解決**：
- 在交易時間（週一至週五 09:00-13:30）執行
- 檢查網路連線
- 稍等片刻後重試

---

希望這份說明能幫助你更好地使用測試模式！🎉

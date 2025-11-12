# 🎉 更新完成！TEST_MODE 功能已加入

## ✨ 新增功能

### 🧪 測試模式 (TEST_MODE)

現在 `fetch_stock_data.py` 已經加入測試模式功能！

**主要特點**：
- ✅ 可在非交易時間使用模擬數據
- ✅ 執行速度快，無需網路連線
- ✅ 根據昨日買超量智能生成合理數據
- ✅ 數據會標記 `"test_mode": true` 以便識別
- ✅ 適合開發測試和功能驗證

## 🔧 如何使用

### 快速切換模式

編輯 `fetch_stock_data.py` 第 14-16 行：

```python
# ==================== 測試模式設定 ====================
# 設為 True 時使用模擬數據，False 時從證交所抓取真實數據
TEST_MODE = True   # ← 改這裡！
# ====================================================
```

- `TEST_MODE = True` → 使用模擬數據（測試模式）
- `TEST_MODE = False` → 抓取真實數據（正式模式）

### 執行看看

```bash
# 測試模式（預設已啟用）
python fetch_stock_data.py

# 你會看到：
# 🔧🔧🔧🔧🔧🔧🔧🔧🔧🔧
# ⚠️  測試模式已啟用 - 使用模擬數據
# 🔧🔧🔧🔧🔧🔧🔧🔧🔧🔧
```

## 📊 生成的數據範例

測試模式會生成包含完整欄位的數據：

```json
{
  "timestamp": "20251112_084156",
  "date": "2025-11-12",
  "time": "08:41:56",
  "test_mode": true,  ← 標記為測試數據
  "tse": [
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
  ]
}
```

## 📚 完整文檔

已為你準備了完整的使用說明：

1. **README.md** - 專案主要說明（已更新測試模式說明）
2. **QUICKSTART.md** - 快速開始指南（已加入測試模式步驟）
3. **TEST_MODE_GUIDE.md** - 測試模式完整使用指南（新增）⭐
4. **FILE_STRUCTURE.txt** - 檔案結構說明

## 🚀 建議使用流程

### 開發階段（使用測試模式）

```bash
# 1. 設定測試模式
TEST_MODE = True

# 2. 本地測試
python fetch_stock_data.py

# 3. 查看數據
cat data/latest.json

# 4. 測試網頁
cd docs && python -m http.server 8000
```

### 部署 GitHub Actions（先測試再正式）

```bash
# 第一步：用測試模式驗證流程
# TEST_MODE = True
git add .
git commit -m "🧪 測試：驗證 GitHub Actions 流程"
git push

# 在 GitHub Actions 手動執行一次，確認成功

# 第二步：切換到正式模式
# TEST_MODE = False
git add fetch_stock_data.py
git commit -m "✅ 正式：啟用真實數據抓取"
git push
```

## 🎯 測試模式的智能數據生成

測試模式不是隨機亂數，而是根據**昨日買超量**生成合理數據：

### 昨日買超股票 (yesterday_buy > 0)
```
委買量：較高（1.2-2.0 倍基礎量）
委賣量：較低（0.5-1.0 倍基礎量）
結果：今日傾向繼續買超 ✅
```

### 昨日賣超股票 (yesterday_buy < 0)
```
委買量：較低（0.5-1.0 倍基礎量）
委賣量：較高（1.2-2.0 倍基礎量）
結果：今日傾向繼續賣超 ❌
```

這樣生成的數據更接近真實市場行為！

## 📋 檢查清單

使用測試模式前，請確認：

- [x] 已閱讀 TEST_MODE_GUIDE.md
- [x] 知道如何切換 TEST_MODE
- [x] 了解測試模式和正式模式的差異
- [x] 部署前記得改為 TEST_MODE = False

## 🔍 快速驗證

執行以下命令檢查測試模式是否正常運作：

```bash
# 1. 執行腳本
python fetch_stock_data.py

# 2. 檢查是否有測試模式標記
grep -q '"test_mode": true' data/latest.json && echo "✅ 測試模式運作正常"

# 3. 檢查數據筆數
echo "TSE 股票數: $(grep -o '"code"' data/latest.json | head -70 | wc -l)"
echo "OTC 股票數: $(grep -o '"code"' data/latest.json | tail -70 | wc -l)"
```

## 💡 使用技巧

### 技巧 1：快速在兩種模式間切換

可以用註解來快速切換：

```python
TEST_MODE = True   # 測試模式
# TEST_MODE = False  # 正式模式（部署時取消這行的註解）
```

### 技巧 2：用環境變數控制

如果需要更靈活的控制，可以改成：

```python
import os
TEST_MODE = os.getenv('TEST_MODE', 'False').lower() == 'true'
```

然後在執行時：
```bash
TEST_MODE=true python fetch_stock_data.py  # 測試模式
python fetch_stock_data.py  # 正式模式（預設）
```

### 技巧 3：區分測試和正式數據

查看數據時可以用 jq 過濾：

```bash
# 檢查是否為測試數據
cat data/latest.json | jq '.test_mode'

# 只看測試數據
find data -name "*.json" -exec sh -c 'jq ".test_mode" {} | grep -q true && echo {}' \;
```

## ⚠️ 重要提醒

1. **部署前切換**：GitHub Actions 部署前務必將 TEST_MODE 改為 False
2. **數據混用**：切換模式前建議清空 data 目錄
3. **標記檢查**：正式數據會有 `"test_mode": false` 或無此欄位
4. **網頁顯示**：測試數據和真實數據在網頁上都能正常顯示

## 📞 需要協助？

- 📖 完整說明：[TEST_MODE_GUIDE.md](TEST_MODE_GUIDE.md)
- 🚀 快速開始：[QUICKSTART.md](QUICKSTART.md)
- 📋 專案說明：[README.md](README.md)
- 🗂️ 檔案結構：[FILE_STRUCTURE.txt](FILE_STRUCTURE.txt)

---

🎉 現在你可以隨時使用測試模式來開發和測試了！

祝使用愉快！ 📊✨

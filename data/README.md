# 數據儲存目錄

此目錄用於儲存股票即時買賣盤數據。

## 文件說明

- `latest.json` - 最新抓取的數據
- `data_list.json` - 所有數據檔案的索引列表
- `stock_data_YYYYMMDD_HHMMSS.json` - 歷史數據檔案（含時間戳記）

## 自動維護

- GitHub Actions 會自動更新此目錄
- 歷史記錄保留最近 100 筆
- 舊數據會自動清理

## 數據格式

請參考主目錄的 README.md 文件。

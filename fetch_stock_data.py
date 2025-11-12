# -*- coding: utf-8 -*-
"""
股票即時買賣盤數據抓取腳本
每小時執行一次，抓取 TSE 和 OTC 買超排名股票的即時買賣盤數據
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import time
import os
from datetime import datetime
import random

# ==================== 測試模式設定 ====================
# 設為 True 時使用模擬數據，False 時從證交所抓取真實數據
TEST_MODE = False
# ====================================================

def create_robust_session():
    """創建具有重試機制的 Session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

session = create_robust_session()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Referer': 'https://mis.twse.com.tw/stock/index.jsp',
}

def load_buy_ranking(filename):
    """載入買超排名股票清單"""
    stocks = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) >= 4:
                    stocks.append({
                        'code': parts[1].strip(),
                        'name': parts[2].strip(),
                        'yesterday_buy': int(parts[3])
                    })
        print(f"✓ 從 {filename} 載入 {len(stocks)} 檔股票")
        return stocks
    except Exception as e:
        print(f"✗ 載入 {filename} 失敗: {e}")
        return []

def generate_mock_data(stock_code, stock_name, yesterday_buy):
    """生成模擬數據（測試模式使用）"""
    # 根據昨日買超量生成合理的委買委賣數據
    base_volume = abs(yesterday_buy) // 10  # 基礎委託量
    
    # 如果昨日是買超，今日傾向委買較多
    if yesterday_buy > 0:
        buy_multiplier = random.uniform(1.2, 2.0)
        sell_multiplier = random.uniform(0.5, 1.0)
    # 如果昨日是賣超，今日傾向委賣較多
    elif yesterday_buy < 0:
        buy_multiplier = random.uniform(0.5, 1.0)
        sell_multiplier = random.uniform(1.2, 2.0)
    else:
        buy_multiplier = random.uniform(0.8, 1.5)
        sell_multiplier = random.uniform(0.8, 1.5)
    
    buy_total = int(base_volume * buy_multiplier) + random.randint(100, 1000)
    sell_total = int(base_volume * sell_multiplier) + random.randint(100, 1000)
    
    # 生成模擬價格（10-500 之間）
    current_price = round(random.uniform(10, 500), 2)
    
    # 生成模擬時間
    hour = random.randint(9, 13)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    mock_time = f"{hour:02d}:{minute:02d}:{second:02d}"
    
    return {
        'code': stock_code,
        'name': stock_name,
        'currentPrice': str(current_price),
        'buyTotal': buy_total,
        'sellTotal': sell_total,
        'diff': buy_total - sell_total,
        'time': mock_time,
        'success': True
    }

def get_stock_order_info(stock_code, stock_name='', yesterday_buy=0):
    """獲取股票即時買賣盤資訊"""
    
    # 測試模式：使用模擬數據
    if TEST_MODE:
        time.sleep(random.uniform(0.01, 0.05))  # 模擬網路延遲
        return generate_mock_data(stock_code, stock_name, yesterday_buy)
    
    # 正式模式：從證交所 API 抓取真實數據
    try:
        # 判斷市場
        if stock_code.startswith('00') or len(stock_code) == 4:
            exchange = 'tse'
        else:
            exchange = 'otc'
        
        url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
        params = {
            'ex_ch': f'{exchange}_{stock_code}.tw',
            'json': '1',
            '_': str(int(time.time() * 1000))
        }
        
        # 隨機延遲避免請求過於頻繁
        time.sleep(random.uniform(0.2, 0.5))
        
        response = session.get(url, params=params, headers=HEADERS, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('rtcode') == '0000' and data.get('msgArray') and len(data['msgArray']) > 0:
                stock = data['msgArray'][0]
                
                # 解析委賣和委買資料
                sell_str = stock.get('f', '')
                buy_str = stock.get('g', '')
                
                sell_volumes = [int(v) for v in sell_str.split('_') if v and v.replace('-', '').isdigit()]
                buy_volumes = [int(v) for v in buy_str.split('_') if v and v.replace('-', '').isdigit()]
                
                sell_total = sum(sell_volumes) if sell_volumes else 0
                buy_total = sum(buy_volumes) if buy_volumes else 0
                
                return {
                    'code': stock_code,
                    'name': stock.get('n', stock_name),
                    'currentPrice': stock.get('z', '-'),
                    'buyTotal': buy_total,
                    'sellTotal': sell_total,
                    'diff': buy_total - sell_total,
                    'time': stock.get('t', ''),
                    'success': True
                }
        
        return {'code': stock_code, 'name': stock_name, 'success': False}
        
    except Exception as e:
        print(f"✗ {stock_code} 查詢失敗: {e}")
        return {'code': stock_code, 'name': stock_name, 'success': False}

def fetch_market_data(market_name, filename):
    """抓取指定市場的數據"""
    mode_str = "【測試模式 - 使用模擬數據】" if TEST_MODE else "【正式模式 - 抓取真實數據】"
    print(f"\n{'='*60}")
    print(f"開始抓取 {market_name} 數據... {mode_str}")
    print(f"{'='*60}")
    
    stocks = load_buy_ranking(filename)
    if not stocks:
        print(f"✗ 無法載入 {market_name} 股票清單")
        return []
    
    results = []
    success_count = 0
    fail_count = 0
    
    for i, stock in enumerate(stocks, 1):
        print(f"[{i}/{len(stocks)}] 查詢 {stock['code']} {stock['name']}...", end=' ')
        
        result = get_stock_order_info(
            stock['code'], 
            stock['name'], 
            stock.get('yesterday_buy', 0)
        )
        
        # 合併原有資訊
        merged = {**stock, **result}
        results.append(merged)
        
        if result['success']:
            success_count += 1
            print(f"✓ 買:{result['buyTotal']} 賣:{result['sellTotal']}")
        else:
            fail_count += 1
            print("✗ 失敗")
    
    print(f"\n{market_name} 統計: 成功 {success_count} / 失敗 {fail_count}")
    return results

def save_data(tse_data, otc_data):
    """儲存數據到 data 目錄"""
    # 建立 data 目錄
    os.makedirs('data', exist_ok=True)
    
    # 產生時間戳記
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    date_str = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')
    
    # 儲存最新數據 (latest.json)
    latest_data = {
        'timestamp': timestamp,
        'date': date_str,
        'time': time_str,
        'test_mode': TEST_MODE,
        'tse': tse_data,
        'otc': otc_data
    }
    
    latest_file = 'data/latest.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(latest_data, f, ensure_ascii=False, indent=2)
    print(f"\n✓ 已儲存最新數據: {latest_file}")
    
    # 儲存歷史數據 (含時間戳記)
    history_file = f'data/stock_data_{timestamp}.json'
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(latest_data, f, ensure_ascii=False, indent=2)
    print(f"✓ 已儲存歷史數據: {history_file}")
    
    # 更新數據列表
    update_data_list(timestamp, date_str, time_str, len(tse_data), len(otc_data))

def update_data_list(timestamp, date_str, time_str, tse_count, otc_count):
    """更新數據檔案列表"""
    list_file = 'data/data_list.json'
    
    # 讀取現有列表
    if os.path.exists(list_file):
        with open(list_file, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
    else:
        data_list = []
    
    # 新增記錄
    data_list.append({
        'timestamp': timestamp,
        'date': date_str,
        'time': time_str,
        'tse_count': tse_count,
        'otc_count': otc_count,
        'filename': f'stock_data_{timestamp}.json'
    })
    
    # 只保留最近 100 筆記錄
    data_list = data_list[-100:]
    
    # 儲存列表
    with open(list_file, 'w', encoding='utf-8') as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已更新數據列表: {list_file}")

def main():
    print("=" * 60)
    print("股票即時買賣盤數據抓取系統")
    print("=" * 60)
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if TEST_MODE:
        print("\n" + "🔧 " * 20)
        print("⚠️  測試模式已啟用 - 使用模擬數據")
        print("🔧 " * 20)
        print("→ 如需抓取真實數據，請編輯腳本將 TEST_MODE 改為 False")
        print("=" * 60 + "\n")
    else:
        print("\n✅ 正式模式 - 從證交所抓取真實數據\n")
    
    # 抓取 TSE 數據
    tse_data = fetch_market_data('上市 (TSE)', 'TSE_buy_ranking.txt')
    
    # 等待一下避免請求過於密集
    print("\n等待 5 秒後繼續...")
    time.sleep(5)
    
    # 抓取 OTC 數據
    otc_data = fetch_market_data('上櫃 (OTC)', 'OTC_buy_ranking.txt')
    
    # 儲存數據
    save_data(tse_data, otc_data)
    
    print("\n" + "=" * 60)
    print("✓ 數據抓取完成!")
    print("=" * 60)

if __name__ == '__main__':
    main()

"""
台股即時股價抓取系統
從 HTML 檔案讀取股票代碼，抓取即時股價資訊
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import pytz
import re
import time
import traceback

# ========== 執行設定 ==========
PROCESS_MODE = os.environ.get('PROCESS_MODE', 'BOTH')  # 'TSE', 'OTC', 'BOTH'
TW_TZ = pytz.timezone('Asia/Taipei')

# 超時設定
REQUEST_TIMEOUT = 10
MAX_RETRY = 3
STOCK_DELAY = 1.5

# ========== 路徑設定 ==========
BASE_PATH = os.path.join(os.path.dirname(__file__), 'StockInfo')

if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

# HTML 檔案路徑
TSE_ANALYSIS_HTML = os.path.join(BASE_PATH, 'tse_analysis_result_complete.html')
OTC_ANALYSIS_HTML = os.path.join(BASE_PATH, 'otc_analysis_result_complete.html')
ALL_TSE_HTML = os.path.join(BASE_PATH, 'ALL_TSE.html')
ALL_OTC_HTML = os.path.join(BASE_PATH, 'ALL_OTC.html')

# 輸出檔案路徑
TSE_OUTPUT_JSON = os.path.join(BASE_PATH, 'TSE_hotstock_data.json')
OTC_OUTPUT_JSON = os.path.join(BASE_PATH, 'OTC_hotstock_data.json')

# ========== 日誌函數 ==========
def log_info(message):
    timestamp = datetime.now(TW_TZ).strftime('%H:%M:%S')
    print(f"[{timestamp}] ℹ️  {message}")
    sys.stdout.flush()

def log_success(message):
    timestamp = datetime.now(TW_TZ).strftime('%H:%M:%S')
    print(f"[{timestamp}] ✅ {message}")
    sys.stdout.flush()

def log_warning(message):
    timestamp = datetime.now(TW_TZ).strftime('%H:%M:%S')
    print(f"[{timestamp}] ⚠️  {message}")
    sys.stdout.flush()

def log_error(message):
    timestamp = datetime.now(TW_TZ).strftime('%H:%M:%S')
    print(f"[{timestamp}] ❌ {message}")
    sys.stdout.flush()

# ========== HTML 解析函數 ==========
def extract_stocks_from_html(html_path, market_type):
    """從 HTML 檔案中提取股票代碼和名稱"""
    if not os.path.exists(html_path):
        log_warning(f"找不到檔案: {html_path}")
        return {}
    
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        stocks = {}
        
        # 查找所有表格行
        rows = soup.find_all('tr')
        log_info(f"在 {os.path.basename(html_path)} 中找到 {len(rows)} 行")
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                # 嘗試從第一個或第二個欄位提取股票代碼
                for i in range(min(3, len(cells))):
                    cell_text = cells[i].get_text(strip=True)
                    # 匹配 4 位數字的股票代碼
                    match = re.search(r'\b(\d{4})\b', cell_text)
                    if match:
                        stock_code = match.group(1)
                        # 嘗試找到股票名稱（可能在同一欄位或下一欄位）
                        stock_name = cell_text.replace(stock_code, '').strip()
                        if not stock_name and i + 1 < len(cells):
                            stock_name = cells[i + 1].get_text(strip=True)
                        
                        if stock_name:
                            stocks[stock_code] = stock_name
                        break
        
        log_success(f"從 {os.path.basename(html_path)} 提取了 {len(stocks)} 檔股票")
        return stocks
        
    except Exception as e:
        log_error(f"解析 HTML 失敗: {e}")
        return {}

def load_stocks_from_html_files(market_type):
    """載入指定市場的所有股票"""
    all_stocks = {}
    
    if market_type == 'TSE':
        files = [TSE_ANALYSIS_HTML, ALL_TSE_HTML]
    elif market_type == 'OTC':
        files = [OTC_ANALYSIS_HTML, ALL_OTC_HTML]
    else:
        return {}
    
    for html_file in files:
        stocks = extract_stocks_from_html(html_file, market_type)
        all_stocks.update(stocks)
    
    log_info(f"{market_type} 市場總共載入 {len(all_stocks)} 檔股票")
    return all_stocks

# ========== 股價抓取函數 ==========
def get_stock_info(stock_code, market='TSE'):
    """抓取單一股票即時資訊（從 Yahoo Finance）"""
    if market == 'TSE':
        url = f"https://tw.stock.yahoo.com/quote/{stock_code}.TW"
    else:
        url = f"https://tw.stock.yahoo.com/quote/{stock_code}.TWO"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(MAX_RETRY):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                if attempt < MAX_RETRY - 1:
                    time.sleep(1)
                    continue
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            stock_info = {'股票代碼': stock_code}
            
            # 提取各項資訊
            field_mappings = {
                '成交價': ['成交', '成交價'],
                '開盤價': ['開盤'],
                '漲跌': ['漲跌'],
                '漲跌幅': ['漲跌幅', '漲跌(%)'],
            }
            
            for field_name, search_terms in field_mappings.items():
                for term in search_terms:
                    span = soup.find('span', string=re.compile(term))
                    if span and span.parent:
                        value = span.parent.get_text().replace(term, '').strip()
                        if value:
                            stock_info[field_name] = value
                            break
            
            # 提取委買委賣小計
            buy_total = sell_total = '無資料'
            all_divs = soup.find_all('div', class_=True)
            for div in all_divs:
                class_str = ' '.join(div.get('class', []))
                div_text = div.get_text()
                if 'Mend(16px)' in class_str and '小計' in div_text:
                    match = re.search(r'([\d,]+)\s*小計', div_text)
                    if match:
                        buy_total = match.group(1).replace(',', '')
                if 'Mstart(16px)' in class_str and 'Mend(0)' in class_str and '小計' in div_text:
                    match = re.search(r'小計\s*([\d,]+)', div_text)
                    if match:
                        sell_total = match.group(1).replace(',', '')
            
            stock_info['委買小計'] = buy_total
            stock_info['委賣小計'] = sell_total
            return stock_info
            
        except Exception as e:
            if attempt < MAX_RETRY - 1:
                time.sleep(1)
            continue
    
    return None

def fetch_stocks_price(stocks_dict, market_type, delay=1.5):
    """批次抓取股票即時資訊"""
    results = []
    total = len(stocks_dict)
    log_info(f"開始抓取 {market_type} {total} 檔股票...")
    
    for i, (code, name) in enumerate(stocks_dict.items(), 1):
        if i % 10 == 0 or i == total:
            log_info(f"進度: {i}/{total} ({i*100//total}%)")
        
        info = get_stock_info(code, market_type)
        if info:
            result = {
                'code': code,
                'name': name,
                'market': market_type,
                'current_price': info.get('成交價', '-'),
                'open_price': info.get('開盤價', '-'),
                'change': info.get('漲跌', '-'),
                'change_percent': info.get('漲跌幅', '-'),
                'buy_volume': info.get('委買小計', '-'),
                'sell_volume': info.get('委賣小計', '-'),
                'update_time': datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S')
            }
            results.append(result)
        
        if i < total:
            time.sleep(delay)
    
    log_success(f"完成 {len(results)}/{total} 檔")
    return results

# ========== 主程式 ==========
def main():
    try:
        print("\n" + "=" * 80)
        print("台股即時股價抓取系統")
        print("=" * 80)
        log_info(f"處理模式: {PROCESS_MODE}")
        log_info(f"執行時間: {datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 處理 TSE 市場
        if PROCESS_MODE in ['TSE', 'BOTH']:
            log_info("開始處理 TSE (上市) 市場...")
            tse_stocks = load_stocks_from_html_files('TSE')
            
            if tse_stocks:
                tse_stock_data = fetch_stocks_price(tse_stocks, 'TSE', STOCK_DELAY)
                
                if tse_stock_data:
                    tse_output = {
                        'update_time': datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S'),
                        'market': 'TSE',
                        'stock_count': len(tse_stock_data),
                        'stocks': tse_stock_data
                    }
                    with open(TSE_OUTPUT_JSON, 'w', encoding='utf-8') as f:
                        json.dump(tse_output, f, ensure_ascii=False, indent=2)
                    log_success(f"TSE 資料已儲存: {len(tse_stock_data)} 檔")
            else:
                log_warning("TSE 市場沒有找到股票資料")
        
        # 處理 OTC 市場
        if PROCESS_MODE in ['OTC', 'BOTH']:
            log_info("開始處理 OTC (上櫃) 市場...")
            otc_stocks = load_stocks_from_html_files('OTC')
            
            if otc_stocks:
                otc_stock_data = fetch_stocks_price(otc_stocks, 'OTC', STOCK_DELAY)
                
                if otc_stock_data:
                    otc_output = {
                        'update_time': datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S'),
                        'market': 'OTC',
                        'stock_count': len(otc_stock_data),
                        'stocks': otc_stock_data
                    }
                    with open(OTC_OUTPUT_JSON, 'w', encoding='utf-8') as f:
                        json.dump(otc_output, f, ensure_ascii=False, indent=2)
                    log_success(f"OTC 資料已儲存: {len(otc_stock_data)} 檔")
            else:
                log_warning("OTC 市場沒有找到股票資料")
        
        print("\n" + "=" * 80)
        log_success("所有任務完成!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        log_error(f"程式執行失敗: {e}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
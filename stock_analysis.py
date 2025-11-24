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

# 買超排行榜檔案路徑
TSE_BUY_RANKING = os.path.join(BASE_PATH, 'TSE_buy_ranking.txt')
OTC_BUY_RANKING = os.path.join(BASE_PATH, 'OTC_buy_ranking.txt')

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

# ========== 買超排行榜載入函數 ==========
def load_buy_ranking(filepath):
    """載入買超排行榜檔案"""
    buy_ranking = {}
    if not os.path.exists(filepath):
        log_warning(f"找不到檔案: {filepath}")
        return buy_ranking
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            # 跳過註解和空行
            if line.startswith('#') or not line:
                continue
            
            # 解析格式: #,代碼,名稱,買超量
            parts = line.split(',')
            if len(parts) >= 4:
                code = parts[1].strip()
                name = parts[2].strip()
                buy_volume = parts[3].strip()
                try:
                    buy_ranking[code] = {
                        'name': name,
                        'volume': int(buy_volume)
                    }
                except:
                    pass
        
        log_success(f"載入買超排行: {len(buy_ranking)} 檔 - {os.path.basename(filepath)}")
        return buy_ranking
        
    except Exception as e:
        log_error(f"載入買超排行榜失敗: {e}")
        return buy_ranking

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
            stock_info = {
                '昨收': '-',
                '成交': '-',
                '漲跌': '-',
                '漲跌幅': '-',
                '開盤': '-',
                '委買小計': '-',
                '委賣小計': '-',
                '委買量': ['-', '-', '-', '-', '-'],  # 五檔委買量
                '委賣量': ['-', '-', '-', '-', '-']   # 五檔委賣量
            }
            
            # 方法1: 從 price-detail-item 的 li 元素中提取資料
            # 這是最可靠的方法，因為結構清楚
            all_list_items = soup.find_all('li', class_=re.compile('price-detail-item'))
            
            for li in all_list_items:
                # 找到標籤 span (包含 "成交"、"昨收" 等文字)
                label_span = li.find('span', class_=re.compile('C\\(#232a31\\)'))
                if not label_span:
                    continue
                
                label = label_span.get_text(strip=True)
                
                # 找到數值 span (包含實際數字)
                value_span = li.find('span', class_=re.compile('Fw\\(600\\)'))
                if not value_span:
                    continue
                
                value = value_span.get_text(strip=True)
                
                # 檢查該 span 的 class 來判斷顏色（漲跌）
                value_classes = ' '.join(value_span.get('class', []))
                is_up = 'trend-up' in value_classes or 'c-trend-up' in value_classes
                is_down = 'trend-down' in value_classes or 'c-trend-down' in value_classes
                
                # 根據標籤分配到對應的欄位
                if label == '成交':
                    stock_info['成交'] = value
                elif label == '昨收':
                    stock_info['昨收'] = value
                elif label == '開盤':
                    stock_info['開盤'] = value
                elif label == '漲跌':
                    # 根據顏色添加正負號
                    if value and value != '-':
                        if not value.startswith(('+', '-')):
                            if is_up:
                                stock_info['漲跌'] = f'+{value}'
                            elif is_down:
                                stock_info['漲跌'] = f'-{value}' if not value.startswith('-') else value
                            else:
                                # 嘗試用數字判斷
                                try:
                                    num_val = float(value.replace(',', ''))
                                    if num_val > 0:
                                        stock_info['漲跌'] = f'+{value}'
                                    elif num_val < 0:
                                        stock_info['漲跌'] = value
                                    else:
                                        stock_info['漲跌'] = '0.00'
                                except:
                                    stock_info['漲跌'] = value
                        else:
                            stock_info['漲跌'] = value
                    else:
                        stock_info['漲跌'] = value
                        
                elif label == '漲跌幅':
                    # 根據顏色添加正負號
                    clean_value = value.replace('%', '').strip()
                    if clean_value and clean_value != '-':
                        if not clean_value.startswith(('+', '-')):
                            if is_up:
                                stock_info['漲跌幅'] = f'+{clean_value}%'
                            elif is_down:
                                stock_info['漲跌幅'] = f'-{clean_value}%' if not clean_value.startswith('-') else f'{clean_value}%'
                            else:
                                # 嘗試用數字判斷
                                try:
                                    num_val = float(clean_value)
                                    if num_val > 0:
                                        stock_info['漲跌幅'] = f'+{clean_value}%'
                                    elif num_val < 0:
                                        stock_info['漲跌幅'] = f'{clean_value}%'
                                    else:
                                        stock_info['漲跌幅'] = '0.00%'
                                except:
                                    stock_info['漲跌幅'] = value
                        else:
                            # 已經有符號，確保有百分號
                            if not value.endswith('%'):
                                stock_info['漲跌幅'] = f'{value}%'
                            else:
                                stock_info['漲跌幅'] = value
                    else:
                        stock_info['漲跌幅'] = value
            
            # 方法2: 提取委買委賣小計（從 div 的所有文字內容）
            all_divs = soup.find_all('div', class_=True)
            for div in all_divs:
                # 取得 div 內所有文字（包括直接文字節點）
                all_text = [s.strip().strip('"') for s in div.stripped_strings]
                
                # 必須包含「小計」且至少有2個元素
                if len(all_text) < 2 or '小計' not in all_text:
                    continue
                
                # 委買小計: 數字在前，"小計"在後
                if all_text[-1] == '小計' and re.match(r'^[\d,]+$', all_text[0]) and stock_info['委買小計'] == '-':
                    value = all_text[0].replace(',', '')
                    if len(value) <= 10:
                        stock_info['委買小計'] = value
                
                # 委賣小計: "小計"在前，數字在後
                elif all_text[0] == '小計' and re.match(r'^[\d,]+$', all_text[-1]) and stock_info['委賣小計'] == '-':
                    value = all_text[-1].replace(',', '')
                    if len(value) <= 10:
                        stock_info['委賣小計'] = value
            
            # 方法3: 提取五檔委買量和委賣量
            # 找到包含 "量" 和 "委買價" 的區塊（委買區）
            # 找到包含 "量" 和 "委賣價" 的區塊（委賣區）
            
            # 尋找包含五檔掛單資訊的區塊
            # 委買量在左邊區塊（W(50%)），委賣量在右邊區塊（W(50%)）
            w50_divs = soup.find_all('div', class_=re.compile(r'W\(50%\)'))
            
            for w50_div in w50_divs:
                # 檢查此區塊是否包含 "量" 和 "委買價" 或 "委賣價"
                div_text = w50_div.get_text()
                
                # 委買區塊 (包含 "委買價")
                if '委買價' in div_text:
                    # 找到所有 Flxg(2) 的 div，這些包含五檔數據
                    flxg_divs = w50_div.find_all('div', class_=re.compile(r'Flxg\(2\)'))
                    buy_volumes = []
                    
                    for flxg_div in flxg_divs:
                        # 在每個 Flxg(2) div 中找數字
                        # 委買量的結構: 數字在第一個位置
                        inner_divs = flxg_div.find_all('div', class_=re.compile(r'Pos\(r\)'))
                        for inner_div in inner_divs:
                            # 找到包含數字的 div
                            num_div = inner_div.find('div', class_=re.compile(r'Bgc\(#7dcbff\)'))
                            if num_div:
                                num_text = num_div.get_text(strip=True).strip('"').replace(',', '')
                                if re.match(r'^[\d,]+$', num_text.replace(',', '')):
                                    buy_volumes.append(num_text)
                    
                    # 如果找到數據，更新 stock_info
                    if buy_volumes:
                        for i, vol in enumerate(buy_volumes[:5]):
                            stock_info['委買量'][i] = vol
                
                # 委賣區塊 (包含 "委賣價")
                elif '委賣價' in div_text:
                    flxg_divs = w50_div.find_all('div', class_=re.compile(r'Flxg\(2\)'))
                    sell_volumes = []
                    
                    for flxg_div in flxg_divs:
                        inner_divs = flxg_div.find_all('div', class_=re.compile(r'Pos\(r\)'))
                        for inner_div in inner_divs:
                            num_div = inner_div.find('div', class_=re.compile(r'Bgc\(#7dcbff\)'))
                            if num_div:
                                num_text = num_div.get_text(strip=True).strip('"').replace(',', '')
                                if re.match(r'^[\d,]+$', num_text.replace(',', '')):
                                    sell_volumes.append(num_text)
                    
                    if sell_volumes:
                        for i, vol in enumerate(sell_volumes[:5]):
                            stock_info['委賣量'][i] = vol
            
            return stock_info
            
        except Exception as e:
            if attempt < MAX_RETRY - 1:
                time.sleep(1)
            continue
    
    return None

def fetch_stocks_price(stocks_dict, market_type, delay=1.5):
    """批次抓取股票即時資訊
    
    stocks_dict 格式可以是:
    1. {code: name} - 從 HTML 提取
    2. {code: {'name': name, 'volume': volume}} - 從買超排行讀取
    """
    results = []
    total = len(stocks_dict)
    log_info(f"開始抓取 {market_type} {total} 檔股票...")
    
    for i, (code, data) in enumerate(stocks_dict.items(), 1):
        if i % 10 == 0 or i == total:
            log_info(f"進度: {i}/{total} ({i*100//total}%)")
        
        # 判斷 data 是字串還是字典
        if isinstance(data, dict):
            name = data.get('name', '')
            yesterday_buy = data.get('volume', 0)
        else:
            name = data
            yesterday_buy = 0
        
        info = get_stock_info(code, market_type)
        if info:
            # 委買量需要反轉順序（從最高買價到最低買價）
            bid_vols = info.get('委買量', ['-', '-', '-', '-', '-'])
            bid_vols_reversed = bid_vols[::-1] if isinstance(bid_vols, list) else bid_vols
            
            result = {
                'code': code,
                'name': name,
                'market': market_type,
                'yesterday_buy': yesterday_buy,
                'close_price': info.get('昨收', '-'),
                'current_price': info.get('成交', '-'),
                'change': info.get('漲跌', '-'),
                'change_percent': info.get('漲跌幅', '-'),
                'buy_volume': info.get('委買小計', '-'),
                'sell_volume': info.get('委賣小計', '-'),
                'bid_volumes': bid_vols_reversed,  # 五檔委買量（反轉順序）
                'ask_volumes': info.get('委賣量', ['-', '-', '-', '-', '-'])   # 五檔委賣量
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
            
            # 優先載入買超排行榜，如果沒有則載入 HTML
            tse_stocks = load_buy_ranking(TSE_BUY_RANKING)
            if not tse_stocks:
                log_info("找不到買超排行榜，改從 HTML 檔案載入...")
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
            
            # 優先載入買超排行榜，如果沒有則載入 HTML
            otc_stocks = load_buy_ranking(OTC_BUY_RANKING)
            if not otc_stocks:
                log_info("找不到買超排行榜，改從 HTML 檔案載入...")
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
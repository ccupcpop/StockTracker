"""
台股即時股價抓取系統 - 非同步加速版
使用證交所 API 批量抓取，速度大幅提升
"""

import os
import sys
import asyncio
import aiohttp
import json
import csv
import time
import traceback
from datetime import datetime
import pytz

# ========== 執行設定 ==========
PROCESS_MODE = os.environ.get('PROCESS_MODE', 'BOTH')  # 'TSE', 'OTC', 'BOTH'
READ_ALL = os.environ.get('READ_ALL', 'False').lower() == 'true'  # True: 每天第一次從CSV讀取, False: 全部從ranking.txt讀取

TW_TZ = pytz.timezone('Asia/Taipei')

# 批量抓取設定
BATCH_SIZE = 40
CONCURRENT_REQUESTS = 3
REQUEST_DELAY = 1.5
TIMEOUT = 20
DEBUG = False

# ========== 路徑設定 ==========
BASE_PATH = os.path.join(os.path.dirname(__file__), 'StockInfo')

if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

# 股票列表檔案
TSE_COMPANY_LIST = os.path.join(BASE_PATH, 'tse_company_list.csv')
OTC_COMPANY_LIST = os.path.join(BASE_PATH, 'otc_company_list.csv')

# 買超排行榜檔案
TSE_BUY_RANKING = os.path.join(BASE_PATH, 'TSE_buy_ranking.txt')
OTC_BUY_RANKING = os.path.join(BASE_PATH, 'OTC_buy_ranking.txt')

# 輸出檔案路徑
TSE_OUTPUT_JSON = os.path.join(BASE_PATH, 'TSE_hotstock_data.json')
OTC_OUTPUT_JSON = os.path.join(BASE_PATH, 'OTC_hotstock_data.json')

# ========== API URLs ==========
REALTIME_API = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
TWSE_INST_API = "https://www.twse.com.tw/fund/T86"
TPEX_INST_API = "https://www.tpex.org.tw/web/stock/3insti/daily_trade/3itrade_hedge_result.php"

# ========== Headers ==========
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://mis.twse.com.tw/stock/index.jsp',
}

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

# ========== 日期判斷函數 ==========
def is_first_run_today(ranking_file):
    """
    判斷今天是否第一次執行
    - READ_ALL = False: 永遠返回 False，全部從 ranking.txt 讀取
    - READ_ALL = True: 透過檢查 ranking.txt 第一行的日期來判斷
    """
    # READ_ALL = False 時，永遠從 ranking.txt 讀取
    if not READ_ALL:
        log_info(f"READ_ALL=False，從排行榜讀取")
        return False
    
    today_str = datetime.now(TW_TZ).strftime('%Y-%m-%d')
    
    if not os.path.exists(ranking_file):
        log_info(f"排行榜檔案不存在，將從 CSV 讀取全部")
        return True
    
    try:
        with open(ranking_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        
        # 格式: # TSE - 2025-11-26 或 # OTC - 2025-11-26
        if first_line.startswith('#'):
            parts = first_line.split('-', 1)
            if len(parts) >= 2:
                date_part = parts[1].strip()
                # 可能是 "2025-11-26" 格式
                if date_part == today_str:
                    log_info(f"今天已執行過，從排行榜讀取")
                    return False
                else:
                    log_info(f"排行榜日期 ({date_part}) 非今天，將從 CSV 讀取全部")
                    return True
    except Exception as e:
        log_warning(f"讀取排行榜日期失敗: {e}")
    
    return True

def get_ranking_file(market):
    """取得對應市場的排行榜檔案路徑"""
    return TSE_BUY_RANKING if market == 'TSE' else OTC_BUY_RANKING

def get_csv_file(market):
    """取得對應市場的 CSV 檔案路徑"""
    return TSE_COMPANY_LIST if market == 'TSE' else OTC_COMPANY_LIST

# ========== 價格格式化函數 ==========
def format_price(price_str):
    """
    根據價格大小格式化:
    - >= 1000: 取整數
    - >= 100 且 < 1000: 取小數點第一位
    - < 100: 取小數點第二位
    """
    if price_str in ['-', '', None]:
        return '-'
    
    try:
        price = float(price_str)
        if price >= 1000:
            return str(int(round(price)))
        elif price >= 100:
            return f"{price:.1f}"
        else:
            return f"{price:.2f}"
    except (ValueError, TypeError):
        return str(price_str)

# ========== 股票列表載入函數 ==========
def load_stocks_from_csv(filepath):
    """從 CSV 載入股票列表"""
    stocks = {}
    if not os.path.exists(filepath):
        log_warning(f"找不到檔案: {filepath}")
        return stocks
    
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    code = row[0].strip()
                    name = row[1].strip()
                    stocks[code] = {'name': name, 'volume': 0}
        
        log_success(f"從 CSV 載入: {len(stocks)} 檔 - {os.path.basename(filepath)}")
        return stocks
    except Exception as e:
        log_error(f"載入 CSV 失敗: {e}")
        return stocks

def load_stocks_from_ranking(filepath):
    """從買超排行榜載入"""
    stocks = {}
    if not os.path.exists(filepath):
        log_warning(f"找不到檔案: {filepath}")
        return stocks
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            parts = line.split(',')
            if len(parts) >= 4:
                code = parts[1].strip()
                name = parts[2].strip()
                try:
                    volume = int(parts[3].strip())
                except:
                    volume = 0
                stocks[code] = {'name': name, 'volume': volume}
        
        log_success(f"從排行榜載入: {len(stocks)} 檔 - {os.path.basename(filepath)}")
        return stocks
    except Exception as e:
        log_error(f"載入排行榜失敗: {e}")
        return stocks

# ========== 儲存排行榜函數 ==========
def save_to_ranking(results, market, institutional_data):
    """
    將有成交價的股票儲存到排行榜檔案
    格式: 排名,代碼,名稱,法人買賣超
    """
    ranking_file = get_ranking_file(market)
    today_str = datetime.now(TW_TZ).strftime('%Y-%m-%d')
    
    # 過濾有成交價的股票
    valid_stocks = []
    for stock in results:
        current_price = stock.get('current_price', '-')
        if current_price not in ['-', '', None, '0']:
            try:
                price = float(current_price)
                if price > 0:
                    valid_stocks.append(stock)
            except:
                pass
    
    # 按法人買賣超排序 (由大到小)
    valid_stocks.sort(key=lambda x: x.get('yesterday_buy', 0), reverse=True)
    
    # 寫入檔案
    try:
        with open(ranking_file, 'w', encoding='utf-8') as f:
            f.write(f"# {market} - {today_str}\n")
            
            for idx, stock in enumerate(valid_stocks, 1):
                code = stock['code']
                name = stock['name'].ljust(16)  # 對齊
                volume = stock.get('yesterday_buy', 0)
                f.write(f"{idx},{code},{name},{volume}\n")
        
        log_success(f"已儲存排行榜: {ranking_file} ({len(valid_stocks)} 檔有成交價)")
        return len(valid_stocks)
    except Exception as e:
        log_error(f"儲存排行榜失敗: {e}")
        return 0

# ========== 非同步抓取函數 ==========
async def get_institutional_data(session, market):
    """取得三大法人買賣超"""
    today = datetime.now(TW_TZ)
    institutional = {}
    
    if market == 'TSE':
        try:
            url = f"{TWSE_INST_API}?response=json&date={today.strftime('%Y%m%d')}&selectType=ALL"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                text = await resp.text()
                data = json.loads(text)
                
                if data.get('stat') == 'OK' and data.get('data'):
                    for row in data['data']:
                        code = row[0].strip()
                        try:
                            buy_sell = int(row[-1].replace(',', '')) // 1000
                            institutional[code] = buy_sell
                        except:
                            pass
            log_info(f"  上市法人資料: {len(institutional)} 筆")
        except Exception as e:
            log_warning(f"  上市法人資料失敗: {e}")
    
    elif market == 'OTC':
        try:
            tpex_date = f"{today.year-1911}/{today.month:02d}/{today.day:02d}"
            url = f"{TPEX_INST_API}?l=zh-tw&se=AL&t=D&d={tpex_date}"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                text = await resp.text()
                data = json.loads(text)
                
                if data.get('aaData'):
                    for row in data['aaData']:
                        code = str(row[0]).strip()
                        try:
                            buy_sell = int(str(row[-1]).replace(',', '')) // 1000
                            institutional[code] = buy_sell
                        except:
                            pass
            log_info(f"  上櫃法人資料: {len(institutional)} 筆")
        except Exception as e:
            log_warning(f"  上櫃法人資料失敗: {e}")
    
    return institutional

async def fetch_batch(session, codes, market):
    """請求單批股票即時報價"""
    market_code = 'tse' if market == 'TSE' else 'otc'
    param = "|".join([f"{market_code}_{code}.tw" for code in codes])
    url = f"{REALTIME_API}?ex_ch={param}&json=1&delay=0"
    
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT)) as resp:
            if resp.status != 200:
                if DEBUG:
                    log_warning(f"HTTP {resp.status}")
                return []
            
            text = await resp.text()
            data = json.loads(text)
            
            if data.get('rtcode') == '0000':
                return data.get('msgArray', [])
            else:
                if DEBUG:
                    log_warning(f"rtcode: {data.get('rtcode')}")
    except asyncio.TimeoutError:
        if DEBUG:
            log_warning("Timeout")
    except Exception as e:
        if DEBUG:
            log_warning(f"Error: {e}")
    return []

def parse_stock_data(raw, institutional_data, stock_info, market, is_first_run):
    """解析股票資料"""
    code = raw.get('c', '')
    info = stock_info.get(code, {})
    name = info.get('name', raw.get('n', ''))
    
    # 如果不是第一次執行且排行榜有買超資料，使用排行榜的資料
    if not is_first_run and info.get('volume', 0) != 0:
        yesterday_buy = info.get('volume', 0)
    else:
        yesterday_buy = institutional_data.get(code, 0)
    
    # 昨收、現價
    yesterday_close = raw.get('y', '-')

    # 現價：z 有值就用 z，否則用買一價
    current_price = '-'
    z_val = raw.get('z', '')
    if z_val and z_val != '-':
        current_price = z_val
    else:
        # 用買一價 (b 的第一個)
        bid_first = raw.get('b', '').split('_')[0]
        if bid_first and bid_first != '-':
            current_price = bid_first
    
    change_str = "-"
    change_pct_str = "-"
    try:
        y = float(yesterday_close) if yesterday_close not in ['-', '', None] else 0
        z = float(current_price) if current_price not in ['-', '', None] else y
        if y > 0:
            change = z - y
            change_pct = (change / y * 100)
            change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
            change_pct_str = f"+{change_pct:.2f}%" if change_pct >= 0 else f"{change_pct:.2f}%"
    except:
        pass
    
    bid_volumes = [v for v in raw.get('g', '').split('_') if v][:5]
    ask_volumes = [v for v in raw.get('f', '').split('_') if v][:5]
    bid_volumes = (bid_volumes + ['0'] * 5)[:5]
    ask_volumes = (ask_volumes + ['0'] * 5)[:5]
    
    try:
        buy_vol = sum(int(v) for v in bid_volumes if v.isdigit())
        sell_vol = sum(int(v) for v in ask_volumes if v.isdigit())
    except:
        buy_vol = sell_vol = 0
    
    return {
        'code': code,
        'name': name,
        'market': market,
        'yesterday_buy': yesterday_buy,
        'close_price': str(yesterday_close),
        'current_price': str(current_price),
        'change': change_str,
        'change_percent': change_pct_str,
        'buy_volume': str(buy_vol),
        'sell_volume': str(sell_vol),
        'bid_volumes': bid_volumes,
        'ask_volumes': ask_volumes
    }

async def fetch_market_stocks(session, stocks_dict, market, is_first_run):
    """抓取指定市場的所有股票"""
    results = []
    codes = list(stocks_dict.keys())
    total = len(codes)
    
    if total == 0:
        return results, {}
    
    # 取得法人資料
    log_info(f"取得 {market} 法人買賣超...")
    institutional_data = await get_institutional_data(session, market)
    
    # 分批抓取
    batches = [codes[i:i+BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
    log_info(f"開始抓取 {market} {total} 檔股票 (分 {len(batches)} 批)...")
    
    success_count = 0
    
    for idx, batch in enumerate(batches):
        raw_data = await fetch_batch(session, batch, market)
        
        for raw in raw_data:
            parsed = parse_stock_data(raw, institutional_data, stocks_dict, market, is_first_run)
            if parsed['code']:
                results.append(parsed)
                success_count += 1
        
        progress = min((idx + 1) * BATCH_SIZE, total)
        if (idx + 1) % 5 == 0 or idx == len(batches) - 1:
            log_info(f"  進度: {progress}/{total} ({progress*100//total}%) | 成功: {success_count}")
        
        if idx < len(batches) - 1:
            await asyncio.sleep(REQUEST_DELAY)
    
    log_success(f"{market} 完成: {success_count}/{total} 檔")
    return results, institutional_data

def parse_change_percent(pct_str):
    """解析漲跌幅字串為數字，用於排序"""
    try:
        clean = pct_str.replace('%', '').replace('+', '').strip()
        return float(clean)
    except:
        return -9999

def save_results(results, market, output_path):
    """儲存結果到 JSON，並格式化價格"""
    # 按漲跌幅排序 (由大到小)
    results.sort(key=lambda x: parse_change_percent(x['change_percent']), reverse=True)
    
    # 格式化價格
    for stock in results:
        stock['close_price'] = format_price(stock['close_price'])
        stock['current_price'] = format_price(stock['current_price'])
    
    output = {
        'update_time': datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S'),
        'market': market,
        'stock_count': len(results),
        'stocks': results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    log_success(f"已儲存: {output_path} ({len(results)} 檔)")

# ========== 非同步主函數 ==========
async def async_main():
    """非同步主函數"""
    print("\n" + "=" * 70)
    print("台股即時股價抓取系統 - 非同步加速版")
    print("=" * 70)
    log_info(f"處理模式: {PROCESS_MODE}")
    log_info(f"READ_ALL: {READ_ALL} ({'每天第一次從CSV讀取' if READ_ALL else '全部從ranking.txt讀取'})")
    log_info(f"執行時間: {datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    start_time = time.time()
    
    # 建立 session
    connector = aiohttp.TCPConnector(limit=10, force_close=True)
    
    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        
        # 處理 TSE
        if PROCESS_MODE in ['TSE', 'BOTH']:
            print("\n" + "-" * 50)
            log_info("處理 TSE (上市) 市場...")
            
            # 判斷今天是否第一次執行
            tse_first_run = False #is_first_run_today(TSE_BUY_RANKING)
            
            if tse_first_run:
                log_info("📥 從 CSV 讀取全部股票...")
                tse_stocks = load_stocks_from_csv(TSE_COMPANY_LIST)
            else:
                log_info("📋 從排行榜讀取股票...")
                tse_stocks = load_stocks_from_ranking(TSE_BUY_RANKING)
            
            if tse_stocks:
                tse_results, tse_institutional = await fetch_market_stocks(
                    session, tse_stocks, 'TSE', tse_first_run
                )
                
                if tse_results:
                    # 第一次執行時，儲存有成交價的股票到排行榜
                    if tse_first_run:
                        save_to_ranking(tse_results, 'TSE', tse_institutional)
                    
                    save_results(tse_results, 'TSE', TSE_OUTPUT_JSON)
            else:
                log_warning("TSE 沒有找到股票資料")
        
        # 處理 OTC
        if PROCESS_MODE in ['OTC', 'BOTH']:
            print("\n" + "-" * 50)
            log_info("處理 OTC (上櫃) 市場...")
            
            # 判斷今天是否第一次執行
            otc_first_run = is_first_run_today(OTC_BUY_RANKING)
            
            if otc_first_run:
                log_info("📥 從 CSV 讀取全部股票...")
                otc_stocks = load_stocks_from_csv(OTC_COMPANY_LIST)
            else:
                log_info("📋 從排行榜讀取股票...")
                otc_stocks = load_stocks_from_ranking(OTC_BUY_RANKING)
            
            if otc_stocks:
                otc_results, otc_institutional = await fetch_market_stocks(
                    session, otc_stocks, 'OTC', otc_first_run
                )
                
                if otc_results:
                    # 第一次執行時，儲存有成交價的股票到排行榜
                    if otc_first_run:
                        save_to_ranking(otc_results, 'OTC', otc_institutional)
                    
                    save_results(otc_results, 'OTC', OTC_OUTPUT_JSON)
            else:
                log_warning("OTC 沒有找到股票資料")
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 70)
    log_success(f"所有任務完成! 總耗時: {elapsed:.1f} 秒")
    print("=" * 70 + "\n")

# ========== 主程式入口 ==========
def main():
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(async_main())
        
    except Exception as e:
        log_error(f"程式執行失敗: {e}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()

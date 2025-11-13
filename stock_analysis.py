"""
台股新聞熱門股票分析系統 - 兩階段執行版本
階段1: 爬取新聞 + 分析股票 + 生成新聞排行榜
階段2: 讀取買超排行 + 抓取即時股價
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import pytz
import re
import pandas as pd
from collections import defaultdict
import time
import traceback

# ========== 執行設定 ==========
STAGE = os.environ.get('STAGE', '2')  # '1' = 只執行階段1, '2' = 執行階段2 (包含階段1的結果)
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

NEWS_JSON = os.path.join(BASE_PATH, 'twstock_news.json')
TSE_NEWS_RANKING = os.path.join(BASE_PATH, 'TSE_news_ranking.txt')
OTC_NEWS_RANKING = os.path.join(BASE_PATH, 'OTC_news_ranking.txt')
TSE_BUY_RANKING = os.path.join(BASE_PATH, 'TSE_buy_ranking.txt')
OTC_BUY_RANKING = os.path.join(BASE_PATH, 'OTC_buy_ranking.txt')
TSE_OUTPUT_JSON = os.path.join(BASE_PATH, 'TSE_hotstock_data.json')
OTC_OUTPUT_JSON = os.path.join(BASE_PATH, 'OTC_hotstock_data.json')
TSE_CSV = os.path.join(BASE_PATH, 'tse_company_list.csv')
OTC_CSV = os.path.join(BASE_PATH, 'otc_company_list.csv')

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

# ========== 新聞爬蟲函數 ==========
def clean_title(title_text):
    if not title_text:
        return ""
    title = title_text.strip()
    if title.startswith('前往'):
        title = title[2:]
    title = title.replace('【即時新聞】', '')
    if title.endswith('文章頁'):
        title = title[:-3]
    patterns_to_remove = [r'^前往', r'文章頁$', r'^查看', r'點擊查看$', r'^閱讀']
    for pattern in patterns_to_remove:
        title = re.sub(pattern, '', title)
    title = ' '.join(title.split())
    return title.strip()

def parse_publish_time(soup_element):
    try:
        time_patterns = [
            soup_element.find('time'),
            soup_element.find(class_=re.compile('time|date|published')),
            soup_element.find('span', class_=re.compile('time|date')),
        ]
        for time_elem in time_patterns:
            if time_elem:
                if time_elem.get('datetime'):
                    return time_elem.get('datetime')
                time_text = time_elem.get_text(strip=True)
                if time_text:
                    return time_text
        return None
    except:
        return None

def scrape_twstock_news():
    url = "https://cmnews.com.tw/twstock/twstock_news"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9',
    }
    
    for attempt in range(MAX_RETRY):
        try:
            log_info(f"嘗試抓取新聞 (第 {attempt + 1}/{MAX_RETRY} 次)...")
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                log_warning(f"HTTP 狀態碼: {response.status_code}")
                if attempt < MAX_RETRY - 1:
                    time.sleep(2)
                    continue
                return []
            
            soup = BeautifulSoup(response.text, 'lxml')
            current_time = datetime.now(TW_TZ)
            news_list = []
            seen_urls = set()
            
            articles = soup.find_all('a', href=lambda x: x and '/article/' in x)
            log_info(f"找到 {len(articles)} 篇文章連結")
            
            for article in articles:
                news_url = article.get('href', '')
                if news_url and not news_url.startswith('http'):
                    news_url = 'https://cmnews.com.tw' + news_url
                if news_url in seen_urls:
                    continue
                title_text = article.get_text(strip=True)
                clean_title_text = clean_title(title_text)
                if clean_title_text and len(clean_title_text) > 5:
                    seen_urls.add(news_url)
                    publish_time = parse_publish_time(article.parent if article.parent else article)
                    news_item = {
                        'title': clean_title_text,
                        'url': news_url,
                        'publish_time': publish_time if publish_time else "未知",
                        'scraped_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'timezone': 'Asia/Taipei'
                    }
                    news_list.append(news_item)
            
            log_success(f"成功抓取 {len(news_list)} 則新聞")
            return news_list
            
        except Exception as e:
            log_error(f"抓取新聞失敗: {e}")
            if attempt < MAX_RETRY - 1:
                time.sleep(2)
    
    return []

def load_existing_news(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                log_info(f"載入現有新聞: {len(data)} 則")
                return data
        except:
            return []
    return []

def filter_news_by_time(news_list, hours=24):
    current_time = datetime.now(TW_TZ)
    time_limit = current_time - timedelta(hours=hours)
    filtered_news = []
    for news in news_list:
        try:
            news_time_str = news['scraped_time']
            news_time = datetime.strptime(news_time_str, '%Y-%m-%d %H:%M:%S')
            news_time = TW_TZ.localize(news_time)
            if news_time >= time_limit:
                filtered_news.append(news)
        except:
            filtered_news.append(news)
    log_info(f"過濾後保留 {len(filtered_news)} 則 (24小時內)")
    return filtered_news

def merge_news(existing_news, new_news):
    news_dict = {}
    for news in existing_news:
        news_dict[news['url']] = news
    for news in new_news:
        news_dict[news['url']] = news
    merged = list(news_dict.values())
    merged.sort(key=lambda x: x['scraped_time'], reverse=True)
    return merged

def save_news_to_json(news_list, filepath):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
        log_success(f"儲存新聞: {len(news_list)} 則")
    except Exception as e:
        log_error(f"儲存失敗: {e}")

# ========== 股票清單載入 ==========
def load_stock_list(filepath, market_type):
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig', header=None)
        stock_dict = {}
        for _, row in df.iterrows():
            code = str(row[0]).strip()
            name = str(row[1]).strip()
            industry = str(row[2]).strip() if len(row) > 2 else ""
            name_clean = re.sub(r'\s+', '', name)
            stock_dict[name_clean] = {
                'code': code,
                'name': name,
                'industry': industry,
                'market': market_type
            }
        log_success(f"{market_type} 股票清單: {len(stock_dict)} 檔")
        return stock_dict
    except Exception as e:
        log_error(f"載入 {market_type} 失敗: {e}")
        return {}

def analyze_news_stocks(news_list, tse_stocks, otc_stocks):
    log_info("分析新聞中的股票...")
    all_stocks = {}
    all_stocks.update(tse_stocks)
    all_stocks.update(otc_stocks)
    stock_mentions = defaultdict(lambda: {'count': 0, 'news': []})
    
    for news in news_list:
        title = news.get('title', '')
        url = news.get('url', '')
        title_clean = re.sub(r'\s+', '', title)
        for stock_name, stock_info in all_stocks.items():
            if stock_name in title_clean or stock_info['code'] in title:
                stock_mentions[stock_name]['count'] += 1
                stock_mentions[stock_name]['info'] = stock_info
                stock_mentions[stock_name]['news'].append({
                    'title': title,
                    'url': url,
                    'time': news.get('scraped_time', '')
                })
    
    log_success(f"找到 {len(stock_mentions)} 檔被提及的股票")
    return stock_mentions

# ========== 新聞排行榜處理 ==========
def load_existing_news_ranking(filepath):
    """載入現有的新聞排行榜"""
    ranking = {}
    if not os.path.exists(filepath):
        log_info(f"無現有排行榜: {filepath}")
        return ranking
    
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
                count = parts[3].strip()
                try:
                    ranking[code] = {
                        'name': name,
                        'count': int(count)
                    }
                except:
                    pass
        log_info(f"載入現有排行: {len(ranking)} 檔")
        return ranking
    except Exception as e:
        log_error(f"載入排行榜失敗: {e}")
        return ranking

def save_news_ranking(stock_mentions, filepath, market_type):
    """儲存新聞排行榜，與當天現有資料合併去重（每天7點會重置）"""
    # 載入現有排行（當天的）
    existing_ranking = load_existing_news_ranking(filepath)
    
    # 合併新舊資料
    merged_ranking = {}
    
    # 加入現有資料
    for code, data in existing_ranking.items():
        merged_ranking[code] = {
            'name': data['name'],
            'count': data['count']
        }
    
    # 加入新資料（累加提及次數）
    for stock_name, data in stock_mentions.items():
        if data['info']['market'] == market_type:
            code = data['info']['code']
            name = data['info']['name']
            count = data['count']
            
            if code in merged_ranking:
                # 如果已存在，累加次數
                merged_ranking[code]['count'] += count
            else:
                # 新增
                merged_ranking[code] = {
                    'name': name,
                    'count': count
                }
    
    # 排序並儲存
    sorted_stocks = sorted(merged_ranking.items(), key=lambda x: x[1]['count'], reverse=True)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('#,代碼,名稱,提及次數\n')
            for rank, (code, data) in enumerate(sorted_stocks, 1):
                f.write(f"{rank},{code},{data['name']},{data['count']}\n")
        log_success(f"儲存 {market_type} 新聞排行: {len(sorted_stocks)} 檔")
    except Exception as e:
        log_error(f"儲存排行榜失敗: {e}")

# ========== 買超排行榜載入 ==========
def load_buy_ranking(filepath):
    buy_ranking = {}
    if not os.path.exists(filepath):
        log_warning(f"找不到檔案: {filepath}")
        return buy_ranking
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
                buy_volume = parts[3].strip()
                try:
                    buy_ranking[code] = {
                        'name': name,
                        'volume': int(buy_volume)
                    }
                except:
                    pass
        log_success(f"載入買超排行: {len(buy_ranking)} 檔")
        return buy_ranking
    except Exception as e:
        log_error(f"載入買超排行榜失敗: {e}")
        return buy_ranking

# ========== Yahoo 股價爬蟲 ==========
def get_stock_info(stock_code, market):
    suffix = '.TW' if market == 'TSE' else '.TWO'
    yahoo_code = f"{stock_code}{suffix}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    url = f'https://tw.stock.yahoo.com/quote/{yahoo_code}'
    
    for attempt in range(MAX_RETRY):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            stock_info = {'股票代碼': stock_code, '市場': market}
            price_items = soup.find_all('li', class_=re.compile(r'price-detail-item'))
            field_map = {'開盤': '開盤價', '漲跌幅': '漲跌幅', '漲跌': '漲跌'}
            stock_info['成交價'] = '無資料'
            for field in field_map.values():
                stock_info[field] = '無資料'
            for item in price_items:
                item_text = item.get_text().strip()
                if item_text.startswith('成交') and '金額' not in item_text and '量' not in item_text:
                    value = item_text[2:].strip().replace(',', '')
                    stock_info['成交價'] = value
                    continue
                for keyword, field_name in field_map.items():
                    if item_text.startswith(keyword):
                        value = item_text[len(keyword):].strip().replace(',', '')
                        if field_name in ['漲跌', '漲跌幅'] and value != '無資料' and value:
                            all_spans = item.find_all('span')
                            is_down = is_up = False
                            for span in all_spans:
                                span_class = ' '.join(span.get('class', []))
                                if 'trend-down' in span_class:
                                    is_down = True
                                    break
                                elif 'trend-up' in span_class:
                                    is_up = True
                                    break
                            if is_down:
                                value = f"-{value}" if not value.startswith('-') else value
                            elif is_up:
                                value = f"+{value}" if not value.startswith('+') else value
                            else:
                                if '-' not in value and '+' not in value:
                                    value = f"+{value}"
                        stock_info[field_name] = value
                        break
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
        except:
            if attempt < MAX_RETRY - 1:
                time.sleep(1)
            continue
    return None

def fetch_stocks_price(stock_codes, market_type, delay=1.5):
    """批次抓取股票即時資訊"""
    results = []
    total = len(stock_codes)
    log_info(f"開始抓取 {market_type} {total} 檔股票...")
    
    for i, (code, data) in enumerate(stock_codes, 1):
        if i % 10 == 0 or i == total:
            log_info(f"進度: {i}/{total} ({i*100//total}%)")
        
        info = get_stock_info(code, market_type)
        if info:
            result = {
                'code': code,
                'name': data['name'],
                'market': market_type,
                'buy_volume_yesterday': data.get('volume', 0),
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

# ========== 階段1: 新聞收集與排行 ==========
def stage1_news_collection():
    """階段1: 爬取新聞 + 分析股票 + 生成排行榜"""
    print("\n" + "=" * 80)
    print("【階段 1: 新聞收集與分析】")
    print("=" * 80)
    
    # 檢查是否為早上 7 點（當天第一次執行）
    current_hour = datetime.now(TW_TZ).hour
    if current_hour == 7:
        log_info("偵測到早上 7 點 - 刪除舊的新聞排行榜...")
        
        # 刪除 TSE 排行榜
        if os.path.exists(TSE_NEWS_RANKING):
            os.remove(TSE_NEWS_RANKING)
            log_success("已刪除 TSE_news_ranking.txt")
        
        # 刪除 OTC 排行榜
        if os.path.exists(OTC_NEWS_RANKING):
            os.remove(OTC_NEWS_RANKING)
            log_success("已刪除 OTC_news_ranking.txt")
        
        log_info("開始新的一天的新聞統計")
    
    # 爬取新聞
    log_info("開始爬取新聞...")
    existing_news = load_existing_news(NEWS_JSON)
    new_news = scrape_twstock_news()
    
    if new_news:
        merged_news = merge_news(existing_news, new_news)
        filtered_news = filter_news_by_time(merged_news, hours=24)
        save_news_to_json(filtered_news, NEWS_JSON)
    else:
        filtered_news = existing_news
        log_warning(f"使用現有新聞: {len(filtered_news)} 則")
    
    # 載入股票清單
    log_info("載入股票清單...")
    tse_stocks = load_stock_list(TSE_CSV, 'TSE')
    otc_stocks = load_stock_list(OTC_CSV, 'OTC')
    
    # 分析新聞
    stock_mentions = analyze_news_stocks(filtered_news, tse_stocks, otc_stocks)
    
    # 儲存新聞排行榜（根據 PROCESS_MODE 決定要儲存哪個市場）
    log_info(f"生成新聞排行榜 (模式: {PROCESS_MODE})...")
    
    if PROCESS_MODE in ['TSE', 'BOTH']:
        save_news_ranking(stock_mentions, TSE_NEWS_RANKING, 'TSE')
    
    if PROCESS_MODE in ['OTC', 'BOTH']:
        save_news_ranking(stock_mentions, OTC_NEWS_RANKING, 'OTC')
    
    log_success("階段1完成!")

# ========== 階段2: 即時股價抓取 ==========
def stage2_price_collection():
    """階段2: 讀取買超排行 + 抓取即時股價"""
    print("\n" + "=" * 80)
    print(f"【階段 2: 即時股價抓取】(模式: {PROCESS_MODE})")
    print("=" * 80)
    
    # 載入買超排行
    log_info("載入買超排行...")
    tse_buy_ranking = load_buy_ranking(TSE_BUY_RANKING) if PROCESS_MODE in ['TSE', 'BOTH'] else {}
    otc_buy_ranking = load_buy_ranking(OTC_BUY_RANKING) if PROCESS_MODE in ['OTC', 'BOTH'] else {}
    
    # 抓取 TSE 股價
    if tse_buy_ranking and PROCESS_MODE in ['TSE', 'BOTH']:
        log_info("處理 TSE 市場...")
        tse_stock_data = fetch_stocks_price(list(tse_buy_ranking.items()), 'TSE', STOCK_DELAY)
        
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
    
    # 抓取 OTC 股價
    if otc_buy_ranking and PROCESS_MODE in ['OTC', 'BOTH']:
        log_info("處理 OTC 市場...")
        otc_stock_data = fetch_stocks_price(list(otc_buy_ranking.items()), 'OTC', STOCK_DELAY)
        
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
    
    log_success("階段2完成!")

# ========== 主程式 ==========
def main():
    try:
        print("\n" + "=" * 80)
        print("台股新聞熱門股票分析系統 - 兩階段版本")
        print("=" * 80)
        log_info(f"執行階段: {STAGE}")
        log_info(f"處理模式: {PROCESS_MODE}")
        log_info(f"執行時間: {datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        if STAGE == '1':
            # 只執行階段1
            stage1_news_collection()
        elif STAGE == '2':
            # 執行階段2（階段2會使用階段1的結果）
            stage2_price_collection()
        else:
            log_error(f"未知的階段: {STAGE}")
            sys.exit(1)
        
        print("\n" + "=" * 80)
        log_success("所有任務完成!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        log_error(f"程式執行失敗: {e}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()

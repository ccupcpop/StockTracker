"""
台股新聞熱門股票分析系統 - GitHub Actions 版本
"""

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import pytz
import re
import pandas as pd
from collections import defaultdict
import time

# ========== 執行設定 ==========
PROCESS_MODE = os.environ.get('PROCESS_MODE', 'BOTH')  # 'TSE', 'OTC', 'BOTH'
TW_TZ = pytz.timezone('Asia/Taipei')

# ========== 路徑設定 ==========
BASE_PATH = os.path.join(os.path.dirname(__file__), 'StockInfo')

# 確保 StockInfo 資料夾存在
if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

NEWS_JSON = os.path.join(BASE_PATH, 'twstock_news.json')
TSE_RANKING = os.path.join(BASE_PATH, 'TSE_buy_ranking.txt')
OTC_RANKING = os.path.join(BASE_PATH, 'OTC_buy_ranking.txt')
TSE_OUTPUT_JSON = os.path.join(BASE_PATH, 'TSE_hotstock_data.json')
OTC_OUTPUT_JSON = os.path.join(BASE_PATH, 'OTC_hotstock_data.json')
TSE_CSV = os.path.join(BASE_PATH, 'tse_company_list.csv')
OTC_CSV = os.path.join(BASE_PATH, 'otc_company_list.csv')

# ========== 新聞爬蟲函數 ==========
def clean_title(title_text):
    """清理新聞標題"""
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
    """解析新聞發布時間"""
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
    """爬取台股新聞"""
    url = "https://cmnews.com.tw/twstock/twstock_news"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9',
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            return []
        soup = BeautifulSoup(response.text, 'lxml')
        current_time = datetime.now(TW_TZ)
        news_list = []
        seen_urls = set()
        articles = soup.find_all('a', href=lambda x: x and '/article/' in x)
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
        return news_list
    except Exception as e:
        print(f"❌ 抓取新聞失敗: {e}")
        return []

def load_existing_news(filepath):
    """載入現有新聞"""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def filter_news_by_time(news_list, hours=24):
    """過濾指定時間內的新聞"""
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
    return filtered_news

def merge_news(existing_news, new_news):
    """合併新舊新聞"""
    news_dict = {}
    for news in existing_news:
        news_dict[news['url']] = news
    for news in new_news:
        news_dict[news['url']] = news
    merged = list(news_dict.values())
    merged.sort(key=lambda x: x['scraped_time'], reverse=True)
    return merged

def save_news_to_json(news_list, filepath):
    """儲存新聞到 JSON"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 儲存失敗: {e}")

# ========== 股票清單載入 ==========
def load_stock_list(filepath, market_type):
    """載入股票清單"""
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
        return stock_dict
    except Exception as e:
        print(f"❌ 載入 {market_type} 失敗: {e}")
        return {}

def analyze_news_stocks(news_list, tse_stocks, otc_stocks):
    """分析新聞中提及的股票"""
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
    return stock_mentions

# ========== 買超排行榜載入 ==========
def load_buy_ranking(filepath):
    """載入買超排行榜"""
    buy_ranking = {}
    if not os.path.exists(filepath):
        print(f"⚠️ 找不到檔案: {filepath}")
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
                    buy_volume_int = int(buy_volume)
                    buy_ranking[code] = {
                        'name': name,
                        'volume': buy_volume_int
                    }
                except:
                    pass
        return buy_ranking
    except Exception as e:
        print(f"❌ 載入買超排行榜失敗: {e}")
        return buy_ranking

def merge_stocks(news_stocks, buy_ranking, stock_list, market_type):
    """合併新聞股票和買超股票"""
    merged = {}
    
    # 加入新聞股票
    for stock_name, data in news_stocks.items():
        if data['info']['market'] == market_type:
            code = data['info']['code']
            buy_info = buy_ranking.get(code, {})
            buy_volume = buy_info.get('volume', 0)
            
            merged[code] = {
                'code': code,
                'name': data['info']['name'],
                'market': market_type,
                'mention_count': data['count'],
                'yesterday_buy': buy_volume,
                'source': 'news'
            }
    
    # 加入買超排行股票
    for code, buy_info in buy_ranking.items():
        buy_volume = buy_info['volume']
        if code not in merged:
            found = False
            for stock_name, stock_info in stock_list.items():
                if stock_info['code'] == code and stock_info['market'] == market_type:
                    merged[code] = {
                        'code': code,
                        'name': stock_info['name'],
                        'market': market_type,
                        'mention_count': 0,
                        'yesterday_buy': buy_volume,
                        'source': 'buy'
                    }
                    found = True
                    break
            if not found:
                merged[code] = {
                    'code': code,
                    'name': buy_info['name'],
                    'market': market_type,
                    'mention_count': 0,
                    'yesterday_buy': buy_volume,
                    'source': 'buy'
                }
        else:
            merged[code]['yesterday_buy'] = buy_volume
    
    return merged

# ========== Yahoo 股價爬蟲 ==========
def get_stock_info(stock_code, market):
    """抓取股票即時資訊"""
    suffix = '.TW' if market == 'TSE' else '.TWO'
    yahoo_code = f"{stock_code}{suffix}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    url = f'https://tw.stock.yahoo.com/quote/{yahoo_code}'
    try:
        response = requests.get(url, headers=headers, timeout=10)
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
    except Exception as e:
        return None

def fetch_stocks_price(stock_list, delay=1.5):
    """批次抓取股票資訊"""
    results = []
    total = len(stock_list)
    print(f"\n開始抓取 {total} 檔股票...")
    for i, stock_data in enumerate(stock_list, 1):
        code = stock_data['code']
        name = stock_data['name']
        market = stock_data['market']
        print(f"[{i}/{total}] {code} {name}...", end=" ")
        info = get_stock_info(code, market)
        if info:
            result = {
                'code': code,
                'name': name,
                'market': market,
                'mention_count': stock_data['mention_count'],
                'yesterday_buy': stock_data['yesterday_buy'],
                'current_price': info.get('成交價', '-'),
                'open_price': info.get('開盤價', '-'),
                'change': info.get('漲跌', '-'),
                'change_percent': info.get('漲跌幅', '-'),
                'buy_volume': info.get('委買小計', '-'),
                'sell_volume': info.get('委賣小計', '-'),
                'update_time': datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S')
            }
            results.append(result)
            print("✓")
        else:
            print("✗")
        if i < total:
            time.sleep(delay)
    print(f"完成 {len(results)}/{total}\n")
    return results

# ========== 主程式 ==========
def main():
    print("\n" + "=" * 80)
    print(f"執行模式: {PROCESS_MODE}")
    print(f"執行時間: {datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # ===== 第一階段 =====
    print("\n[第一階段: 爬取新聞]")
    existing_news = load_existing_news(NEWS_JSON)
    new_news = scrape_twstock_news()
    if new_news:
        merged_news = merge_news(existing_news, new_news)
        filtered_news = filter_news_by_time(merged_news, hours=24)
        save_news_to_json(filtered_news, NEWS_JSON)
        print(f"✓ 新抓取: {len(new_news)} 則, 24小時內: {len(filtered_news)} 則")
    else:
        filtered_news = existing_news
        print(f"✓ 使用現有 {len(filtered_news)} 則")
    
    # ===== 第二階段 =====
    print("\n[第二階段: 分析新聞股票]")
    tse_stocks = load_stock_list(TSE_CSV, 'TSE')
    otc_stocks = load_stock_list(OTC_CSV, 'OTC')
    print(f"✓ 載入股票清單: TSE {len(tse_stocks)} 檔, OTC {len(otc_stocks)} 檔")
    
    all_stocks = {}
    all_stocks.update(tse_stocks)
    all_stocks.update(otc_stocks)
    stock_mentions = analyze_news_stocks(filtered_news, tse_stocks, otc_stocks)
    print(f"✓ 新聞提及股票總數: {len(stock_mentions)} 檔")
    
    # ===== 第三階段 =====
    print("\n[第三階段: 載入買超排行]")
    tse_buy_ranking = load_buy_ranking(TSE_RANKING) if PROCESS_MODE in ['TSE', 'BOTH'] else {}
    otc_buy_ranking = load_buy_ranking(OTC_RANKING) if PROCESS_MODE in ['OTC', 'BOTH'] else {}
    
    print(f"✓ 載入買超排行: TSE {len(tse_buy_ranking)} 檔, OTC {len(otc_buy_ranking)} 檔")
    
    # ===== 第四階段 =====
    print("\n[第四階段: 合併股票]")
    tse_merged = merge_stocks(stock_mentions, tse_buy_ranking, all_stocks, 'TSE') if PROCESS_MODE in ['TSE', 'BOTH'] else {}
    otc_merged = merge_stocks(stock_mentions, otc_buy_ranking, all_stocks, 'OTC') if PROCESS_MODE in ['OTC', 'BOTH'] else {}
    
    print(f"✓ 合併後: TSE {len(tse_merged)} 檔, OTC {len(otc_merged)} 檔")
    
    # ===== 第五階段 =====
    print("\n[第五階段: 抓取股價]")
    tse_stock_data = []
    if tse_merged and PROCESS_MODE in ['TSE', 'BOTH']:
        sorted_tse = sorted(tse_merged.values(), key=lambda x: (x['mention_count'], x['yesterday_buy']), reverse=True)
        tse_stock_data = fetch_stocks_price(sorted_tse, delay=1.5)
    
    otc_stock_data = []
    if otc_merged and PROCESS_MODE in ['OTC', 'BOTH']:
        sorted_otc = sorted(otc_merged.values(), key=lambda x: (x['mention_count'], x['yesterday_buy']), reverse=True)
        otc_stock_data = fetch_stocks_price(sorted_otc, delay=1.5)
    
    # ===== 第六階段 =====
    print("\n[第六階段: 儲存]")
    if tse_stock_data:
        tse_output = {
            'update_time': datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'market': 'TSE',
            'total_news': len(filtered_news),
            'hot_stocks_count': len(tse_stock_data),
            'stocks': tse_stock_data
        }
        with open(TSE_OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(tse_output, f, ensure_ascii=False, indent=2)
        print(f"✓ TSE: {len(tse_stock_data)} 檔")
    
    if otc_stock_data:
        otc_output = {
            'update_time': datetime.now(TW_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'market': 'OTC',
            'total_news': len(filtered_news),
            'hot_stocks_count': len(otc_stock_data),
            'stocks': otc_stock_data
        }
        with open(OTC_OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(otc_output, f, ensure_ascii=False, indent=2)
        print(f"✓ OTC: {len(otc_stock_data)} 檔")
    
    print("\n✅ 完成")

if __name__ == "__main__":
    main()

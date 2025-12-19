import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import os

def read_ranking_file(filename):
    """讀取排名檔案"""
    stocks = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split(',')
            if len(parts) >= 4:
                stock_id = parts[1]
                stock_name = parts[2]
                foreign_buy = int(parts[3])
                stocks.append({
                    'stock_id': stock_id,
                    'stock_name': stock_name,
                    'foreign_buy': foreign_buy
                })
    return pd.DataFrame(stocks)

def get_stock_price_data(stock_id, days=60):
    """獲取股票價格資料"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    url = 'https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY'
    params = {
        'date': end_date.strftime('%Y%m%d'),
        'stockNo': stock_id,
        'response': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'data' not in data or not data['data']:
            return None
            
        df = pd.DataFrame(data['data'], columns=['日期', '成交股數', '成交金額', '開盤價', 
                                                   '最高價', '最低價', '收盤價', '漲跌價差', '成交筆數'])
        
        df['收盤價'] = pd.to_numeric(df['收盤價'].str.replace(',', ''), errors='coerce')
        df['成交股數'] = pd.to_numeric(df['成交股數'].str.replace(',', ''), errors='coerce')
        df['最高價'] = pd.to_numeric(df['最高價'].str.replace(',', ''), errors='coerce')
        df['最低價'] = pd.to_numeric(df['最低價'].str.replace(',', ''), errors='coerce')
        
        return df
    except:
        return None

def calculate_ma(prices, period):
    """計算移動平均線"""
    if len(prices) < period:
        return None
    return prices[-period:].mean()

def calculate_kd(df, n=9):
    """計算KD指標"""
    if len(df) < n:
        return None, None
    
    high = df['最高價'].astype(float)
    low = df['最低價'].astype(float)
    close = df['收盤價'].astype(float)
    
    rsv = ((close.iloc[-1] - low.rolling(n).min().iloc[-1]) / 
           (high.rolling(n).max().iloc[-1] - low.rolling(n).min().iloc[-1])) * 100
    
    k = 50
    d = 50
    
    for i in range(len(df) - n + 1, len(df)):
        rsv_i = ((close.iloc[i] - low.rolling(n).min().iloc[i]) / 
                (high.rolling(n).max().iloc[i] - low.rolling(n).min().iloc[i])) * 100
        k = k * 2/3 + rsv_i * 1/3
        d = d * 2/3 + k * 1/3
    
    return k, d

def analyze_stock(stock_id, stock_name, foreign_buy):
    """分析單一股票"""
    df = get_stock_price_data(stock_id)
    
    if df is None or len(df) < 20:
        return None
    
    current_price = df['收盤價'].iloc[-1]
    ma5 = calculate_ma(df['收盤價'], 5)
    ma10 = calculate_ma(df['收盤價'], 10)
    ma20 = calculate_ma(df['收盤價'], 20)
    k, d = calculate_kd(df)
    
    avg_volume = df['成交股數'].mean()
    current_volume = df['成交股數'].iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
    
    return {
        'stock_id': stock_id,
        'stock_name': stock_name,
        'foreign_buy': foreign_buy,
        'current_price': current_price,
        'ma5': ma5,
        'ma10': ma10,
        'ma20': ma20,
        'k': k,
        'd': d,
        'volume_ratio': volume_ratio
    }

def generate_html_report(tse_results, otc_results, output_file):
    """生成HTML報告"""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>股票分析報告 - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 30px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .buy {{ color: green; font-weight: bold; }}
        .sell {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>上市股票分析報告</h1>
    <table>
        <tr>
            <th>股票代號</th>
            <th>股票名稱</th>
            <th>外資買超(張)</th>
            <th>收盤價</th>
            <th>MA5</th>
            <th>MA10</th>
            <th>MA20</th>
            <th>K值</th>
            <th>D值</th>
            <th>量比</th>
        </tr>
"""
    
    for result in tse_results:
        if result:
            buy_class = 'buy' if result['foreign_buy'] > 0 else 'sell'
            html += f"""        <tr>
            <td>{result['stock_id']}</td>
            <td>{result['stock_name']}</td>
            <td class="{buy_class}">{result['foreign_buy']:,}</td>
            <td>{result['current_price']:.2f}</td>
            <td>{result['ma5']:.2f if result['ma5'] else 'N/A'}</td>
            <td>{result['ma10']:.2f if result['ma10'] else 'N/A'}</td>
            <td>{result['ma20']:.2f if result['ma20'] else 'N/A'}</td>
            <td>{result['k']:.2f if result['k'] else 'N/A'}</td>
            <td>{result['d']:.2f if result['d'] else 'N/A'}</td>
            <td>{result['volume_ratio']:.2f}</td>
        </tr>
"""
    
    html += """    </table>
    <h1>上櫃股票分析報告</h1>
    <table>
        <tr>
            <th>股票代號</th>
            <th>股票名稱</th>
            <th>外資買超(張)</th>
            <th>收盤價</th>
            <th>MA5</th>
            <th>MA10</th>
            <th>MA20</th>
            <th>K值</th>
            <th>D值</th>
            <th>量比</th>
        </tr>
"""
    
    for result in otc_results:
        if result:
            buy_class = 'buy' if result['foreign_buy'] > 0 else 'sell'
            html += f"""        <tr>
            <td>{result['stock_id']}</td>
            <td>{result['stock_name']}</td>
            <td class="{buy_class}">{result['foreign_buy']:,}</td>
            <td>{result['current_price']:.2f}</td>
            <td>{result['ma5']:.2f if result['ma5'] else 'N/A'}</td>
            <td>{result['ma10']:.2f if result['ma10'] else 'N/A'}</td>
            <td>{result['ma20']:.2f if result['ma20'] else 'N/A'}</td>
            <td>{result['k']:.2f if result['k'] else 'N/A'}</td>
            <td>{result['d']:.2f if result['d'] else 'N/A'}</td>
            <td>{result['volume_ratio']:.2f}</td>
        </tr>
"""
    
    html += """    </table>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

def main():
    print("開始分析...")
    
    # 讀取排名檔案
    tse_df = read_ranking_file('StockInfo/TSE_buy_ranking.txt')
    otc_df = read_ranking_file('StockInfo/OTC_buy_ranking.txt')
    
    print(f"上市股票: {len(tse_df)} 檔")
    print(f"上櫃股票: {len(otc_df)} 檔")
    
    # 分析上市股票
    tse_results = []
    for idx, row in tse_df.iterrows():
        print(f"分析上市 {idx+1}/{len(tse_df)}: {row['stock_id']} {row['stock_name']}")
        result = analyze_stock(row['stock_id'], row['stock_name'], row['foreign_buy'])
        tse_results.append(result)
        time.sleep(3)  # 避免請求過快
    
    # 分析上櫃股票
    otc_results = []
    for idx, row in otc_df.iterrows():
        print(f"分析上櫃 {idx+1}/{len(otc_df)}: {row['stock_id']} {row['stock_name']}")
        result = analyze_stock(row['stock_id'], row['stock_name'], row['foreign_buy'])
        otc_results.append(result)
        time.sleep(3)
    
    # 生成報告
    generate_html_report(tse_results, otc_results, 'StockInfo/analysis_result.html')
    print("分析完成！")

if __name__ == '__main__':
    main()

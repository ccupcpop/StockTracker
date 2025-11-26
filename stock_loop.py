"""
台股即時股價抓取系統 - 循環執行器
每 5 分鐘自動執行一次 stock_analysis.py
"""

import time
import sys
import os
from datetime import datetime, timedelta
import pytz

# 設定台灣時區
TW_TZ = pytz.timezone('Asia/Taipei')

# 執行間隔 (秒)
INTERVAL = 5 * 60  # 5 分鐘

def run_analysis():
    """執行股票分析"""
    try:
        import stock_analysis
        stock_analysis.main()
        return True
    except Exception as e:
        print(f"[錯誤] 執行失敗: {e}")
        return False

def main():
    print("\n" + "=" * 70)
    print("  台股即時股價抓取系統 - 循環執行模式")
    print("  每 5 分鐘自動更新一次")
    print("  按 Ctrl+C 停止")
    print("=" * 70 + "\n")
    
    run_count = 0
    
    while True:
        try:
            run_count += 1
            now = datetime.now(TW_TZ)
            
            print(f"\n{'#' * 70}")
            print(f"# 第 {run_count} 次執行 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'#' * 70}")
            
            # 執行分析
            success = run_analysis()
            
            # 計算下次執行時間
            next_run = datetime.now(TW_TZ) + timedelta(seconds=INTERVAL)
            
            if success:
                print(f"\n[OK] 資料已更新，網頁會自動重新載入")
            
            print(f"[等待] 下次執行: {next_run.strftime('%H:%M:%S')} (5 分鐘後)")
            print("-" * 70)
            
            # 等待
            time.sleep(INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n[停止] 使用者中斷執行")
            break
        except Exception as e:
            print(f"\n[錯誤] {e}")
            print("[重試] 30 秒後重新執行...")
            time.sleep(30)

if __name__ == "__main__":
    main()

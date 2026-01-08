import geoip2.database
import os

# 設定您的檔案名稱
db_path = 'GeoLite2-City.mmdb'

if not os.path.exists(db_path):
    print("❌ 找不到檔案，請確認檔案名稱是否正確！")
else:
    # 1. 檢查檔案大小
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"📂 資料庫檔案大小: {size_mb:.2f} MB")

    if size_mb < 50:
        print("⚠️ 警告：您的檔案太小了！")
        print("   您可能下載到了 'GeoLite2-Country' (只有國家) 或 'ASN' 版本。")
        print("   請務必下載 'GeoLite2 City' 版本 (通常大於 60MB)。")
    else:
        print("✅ 檔案大小正常，看起來是 City 版本。")

    # 2. 測試 Google DNS (8.8.8.8)
    try:
        with geoip2.database.Reader(db_path) as reader:
            # 測試 8.8.8.8
            r1 = reader.city('8.8.8.8')
            c1 = r1.country.name or "未知"
            city1 = r1.city.name or "未知"
            print(f"🔍 測試 8.8.8.8: 國家=[{c1}], 城市=[{city1}]")
            
            # 測試原本的 1.1.1.1
            r2 = reader.city('1.1.1.1')
            c2 = r2.country.name or "未知"
            city2 = r2.city.name or "未知"
            print(f"🔍 測試 1.1.1.1: 國家=[{c2}], 城市=[{city2}] (免費版可能無資料)")

    except Exception as e:
        print(f"❌ 查詢失敗: {e}")
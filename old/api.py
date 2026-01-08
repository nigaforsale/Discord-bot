from fastapi import FastAPI
import geoip2.database
import socket
import os

app = FastAPI()

# 設定資料庫檔案路徑
CITY_DB_PATH = "GeoLite2-City.mmdb"
ASN_DB_PATH = "GeoLite2-ASN.mmdb"  # 如果您有下載 ASN 資料庫就用，沒有也沒關係

@app.get("/")
def read_root():
    return {"status": "online", "message": "Local GeoIP API is running"}

@app.get("/json/{ip}")
async def get_ip_info(ip: str):
    # 初始化回傳格式 (模仿 ip-api.com 的結構，減少修改 bot 的成本)
    result = {
        "status": "success",
        "query": ip,
        "country": "Unknown",
        "city": "Unknown",
        "isp": "Unknown",
        "reverse": "",
        "message": ""
    }

    # 1. 查詢地理位置 (City DB)
    if os.path.exists(CITY_DB_PATH):
        try:
            with geoip2.database.Reader(CITY_DB_PATH) as reader:
                response = reader.city(ip)
                # 嘗試讀取，若無資料則維持 Unknown
                result["country"] = response.country.name or "Unknown"
                result["city"] = response.city.name or "Unknown"
        except Exception:
            pass 
    else:
        result["message"] += "City DB not found. "

    # 2. 查詢 ISP (ASN DB) - 選用
    if os.path.exists(ASN_DB_PATH):
        try:
            with geoip2.database.Reader(ASN_DB_PATH) as reader:
                response = reader.asn(ip)
                result["isp"] = response.autonomous_system_organization or "Unknown"
        except Exception:
            pass

    # 3. 反向 DNS 查詢 (速度取決於系統 DNS)
    try:
        # 設定 1 秒逾時，避免卡住
        socket.setdefaulttimeout(1)
        result["reverse"] = socket.gethostbyaddr(ip)[0]
    except Exception:
        pass

    return result
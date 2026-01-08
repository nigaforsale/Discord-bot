import re
import aiohttp
import ipaddress
import dns.resolver
import GPUtil
import psutil
from datetime import datetime

# 清理網域字串
def clean_domain(url):
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    return url.split('/')[0].split(':')[0]

# WHOIS 日期格式化
def format_whois_date(d):
    if isinstance(d, list):
        d = d[0] if len(d) > 0 else None
    return d.strftime('%Y-%m-%d') if d else "未知"

# 檢查是否為受限 IP
def check_ip_restricted(ip_str):
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        if ip_obj.is_loopback: return "❌ 拒絕存取：不允許查詢本機回環位址 (Loopback)。"
        if ip_obj.is_private: return "❌ 拒絕存取：不允許查詢私有網路位址 (Private IP)。"
        if ip_obj.is_multicast: return "❌ 拒絕存取：不允許查詢多播位址 (Multicast)。"
        return None
    except ValueError:
        return "NOT_IP"

# 進度條
def create_progress_bar(percent, length=10):
    percent = max(0, min(100, percent))
    filled_length = int(length * percent / 100)
    bar = '▰' * filled_length + '▱' * (length - filled_length)
    return f"`{bar}` {percent}%"

# 硬體資訊函式 (GPU/Disk)
def get_gpu_info():
    try:
        gpus = GPUtil.getGPUs()
        if not gpus: return None
        gpu = gpus[0]
        return {"name": gpu.name, "load": gpu.load * 100, "memory": gpu.memoryUtil * 100, "temp": gpu.temperature}
    except Exception: return None

def get_disk_info():
    disk_results = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for partition in partitions:
            if 'cdrom' in partition.opts or partition.fstype == '': continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                label = partition.device if partition.device else partition.mountpoint
                disk_results.append({
                    "label": label, "percent": usage.percent,
                    "used": round(usage.used / (1024**3), 2), "total": round(usage.total / (1024**3), 2)
                })
            except (PermissionError, OSError): continue
        return disk_results
    except Exception: return None

# IP 查詢 (純邏輯，錯誤往上拋)
async def get_ip_info(ip_address):
    # 使用原本的外部 API 網址，並指定需要的欄位
    url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country,city,isp,reverse,query"
    
    # 因為是連線到外部網路，Timeout 設為 10 秒比較保險
    timeout = aiohttp.ClientTimeout(total=10)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    # 如果 API 回傳非 200 (例如 429 請求過多)，拋出錯誤
                    raise RuntimeError(f"IP-API HTTP 錯誤 {response.status}")
    except Exception as e:
        # 將錯誤往上拋，交給 commands.py 和 error.py 處理
        raise e
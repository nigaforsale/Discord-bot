import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import dns.resolver
import socket
import aiohttp
import time
import psutil
import logging
import ipaddress
from datetime import datetime, timedelta
import asyncio
import whois
import re

# --- 配置 Logging ---
# 建立日誌記錄器
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)

# 設定日誌格式
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')

# 檔案處理器：將日誌寫入 bot.log (使用 utf-8 編碼防止中文亂碼)
file_handler = logging.FileHandler('bot.log', encoding='utf-8')
file_handler.setFormatter(formatter)

# 控制台處理器：將日誌顯示在螢幕上
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# 加入處理器
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents=discord.Intents.all()
intents.members = True
bot_start_time = datetime.now()

class DNSBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)

    async def setup_hook(self):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 正在同步斜線指令...")
        await self.tree.sync()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 同步成功！")

bot = DNSBot()

# --- 日誌記錄 ---
def log_command(interaction: discord.Interaction, command_name: str, details: str):
    user = interaction.user
    guild = interaction.guild.name if interaction.guild else "私訊"
    # 使用 logger 記錄資訊
    logger.info(f"[LOG] 使用者: {user} | 伺服器: {guild} | 指令: /{command_name} | 內容: {details}")

# --- IP 查詢函式 ---
async def get_ip_info(ip_address):
    url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country,city,isp,reverse,query"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return None

# --- DNS 解析函式 ---
def get_dns_records(target):
    embed = discord.Embed(
        title="🌐 DNS 解析工具",
        description=f"解析目標: `{target}`",
        color=discord.Color.green()
    )

    # 1. 解析 A 紀錄 (IPv4)
    try:
        a_records = dns.resolver.resolve(target, 'A')
        ips = [rdata.address for rdata in a_records]
        embed.add_field(name="📌 A Record", value="\n".join(f"`{ip}`" for ip in ips), inline=False)
    except Exception:
        embed.add_field(name="📌 A Record", value="❌ 無 A 紀錄", inline=False)

    # 2. 解析 CNAME 紀錄
    try:
        cname_records = dns.resolver.resolve(target, 'CNAME')
        cnames = [str(rdata.target) for rdata in cname_records]
        embed.add_field(name="🔗 CNAME", value="\n".join(f"`{cn}`" for cn in cnames), inline=False)
    except Exception:
        pass # 沒有 CNAME 是正常的，不一定要顯示

    # 3. 解析 MX 紀錄 (郵件伺服器)
    try:
        mx_records = dns.resolver.resolve(target, 'MX')
        mxs = [f"Prio {r.preference}: `{r.exchange}`" for r in mx_records]
        embed.add_field(name="📧 MX Record", value="\n".join(mxs), inline=False)
    except Exception:
        pass

    embed.set_footer(text="使用 /dns <domain> 進行查詢")
    return embed

# 輔助函式：清理網域字串
def clean_domain(url):
    # 移除 http://, https://, www. 以及路徑
    url = re.sub(r'^https?://', '', url)
    url = re.sub(r'^www\.', '', url)
    return url.split('/')[0].split(':')[0]

# --- 斜線指令定義 ---
# --- 指令 /help ---
@bot.tree.command(name="help", description="顯示機器人功能說明清單")
async def help_command(interaction: discord.Interaction):
    # 新增 LOG
    log_command(interaction, "help", "查詢說明選單")
    
    embed = discord.Embed(
        title="🛠️ 指令清單",
        description="歡迎使用本機器人，以下是目前支援的指令：",
        color=discord.Color.orange()
    )
    
    embed.add_field(
        name="🌐 `/dns [domain]`", 
        value="解析指定網域的 A 紀錄、CNAME 等 DNS 資訊。", 
        inline=False
    )
    
    embed.add_field(
        name="🔍 `/ip [ip_address]`", 
        value="查詢 IP 的地理位置（國家、城市）、ISP 供應商以及反向 DNS 紀錄。", 
        inline=False
    )
    
    embed.add_field(
        name="❓ `/help`", 
        value="顯示此幫助選單。", 
        inline=False
    )

    embed.add_field(
        name="🏓 `/ping`",
        value="查看延遲與伺服器運行資訊。",
        inline=False
    )

    embed.add_field(
        name="📋 `/whois [domain]`", 
        value="查詢網域的註冊商、日期與過期時間。", 
        inline=False
    )

    embed.set_footer(text="提示：直接在對話框輸入 / 即可看到指令選單。")
    
    await interaction.response.send_message(embed=embed)

# --- 指令 /dns ---
@bot.tree.command(name="dns", description="查詢 DNS 紀錄 (A, CNAME, MX)")
@app_commands.describe(host="網域名稱", ephemeral="是否在 60 秒後自動刪除結果？")
async def dns_command(interaction: discord.Interaction, host: str, ephemeral: bool = True):
    await interaction.response.defer()
    log_command(interaction, "dns", f"{host} (自動刪除: {ephemeral})")

    # 1. 安全檢查：防止解析本機或私有 IP
    try:
        ip_check = ipaddress.ip_address(host)
        if ip_check.is_loopback or ip_check.is_private:
            await interaction.followup.send("❌ 拒絕存取：禁止解析本機或私有網路地址。")
            return
    except ValueError:
        pass

    embed = discord.Embed(
        title="🌐 DNS 解析結果", 
        description=f"目標: `{host}`", 
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    # 2. 查詢 A 紀錄 (IPv4)
    try:
        a_records = dns.resolver.resolve(host, 'A')
        ips = [rdata.address for rdata in a_records]
        embed.add_field(name="📌 A Record", value="\n".join(f"`{ip}`" for ip in ips), inline=False)
    except Exception:
        embed.add_field(name="📌 A Record", value="❌ 無 A 紀錄", inline=False)

    # 3. 查詢 CNAME 紀錄 (若無則顯示無)
    try:
        cname_records = dns.resolver.resolve(host, 'CNAME')
        cnames = [str(rdata.target) for rdata in cname_records]
        embed.add_field(name="🔗 CNAME (Alias)", value="\n".join(f"`{cn}`" for cn in cnames), inline=False)
    except Exception:
        # 使用者要求：如果沒有 CNAME 就顯示無
        embed.add_field(name="🔗 CNAME (Alias)", value="❌ 無 CNAME 紀錄", inline=False)

    # 4. 查詢 MX 紀錄 (郵件伺服器)
    try:
        mx_records = dns.resolver.resolve(host, 'MX')
        mxs = [f"優先級 {r.preference}: `{r.exchange}`" for r in mx_records]
        embed.add_field(name="📧 MX Record", value="\n".join(mxs), inline=False)
    except Exception:
        embed.add_field(name="📧 MX Record", value="❌ 無 MX 紀錄", inline=False)

    msg = await interaction.followup.send(embed=embed)
    
    # 5. 非同步自動刪除 (asyncio.sleep 不會卡住機器人)
    if ephemeral:
        await asyncio.sleep(60) 
        try:
            await msg.delete()
            logger.info(f"已自動刪除網域 {host} 的解析訊息。")
        except discord.NotFound:
            pass

# --- 指令 /ip ---
@bot.tree.command(name="ip", description="查詢 IP 詳細資訊 (自動過濾私有與本機 IP)")
@app_commands.describe(ip="請輸入要查詢的 IPv4 地址")
async def ip_command(interaction: discord.Interaction, ip: str):
    await interaction.response.defer()
    log_command(interaction, "ip", ip)
    
    try:
        # 1. 驗證 IP 格式並檢查是否為私有/回環地址
        ip_obj = ipaddress.ip_address(ip)
        
        if ip_obj.is_loopback:
            await interaction.followup.send("❌ 拒絕存取：不允許查詢本機回環位址 (Loopback)。")
            return
        if ip_obj.is_private:
            await interaction.followup.send("❌ 拒絕存取：不允許查詢私有網路位址 (Private IP)。")
            return
        if ip_obj.is_multicast:
            await interaction.followup.send("❌ 拒絕存取：不允許查詢多播位址 (Multicast)。")
            return

    except ValueError:
        await interaction.followup.send("❌ 錯誤：這不是一個有效的 IPv4 地址格式。")
        return

    # 2. 呼叫 API 查詢
    try:
        data = await get_ip_info(ip)
        
        if data and data.get("status") == "success":
            embed = discord.Embed(
                title=f"🔍 IP 詳細資訊: {ip}",
                color=discord.Color.blue()
            )
            embed.add_field(name="🌍 國家", value=data.get("country", "未知"), inline=True)
            embed.add_field(name="🏙️ 城市", value=data.get("city", "未知"), inline=True)
            embed.add_field(name="🏢 ISP 供應商", value=data.get("isp", "未知"), inline=False)
            
            rev_dns = data.get("reverse") if data.get("reverse") else "無反向 DNS 紀錄"
            embed.add_field(name="🔄 反向 DNS", value=f"`{rev_dns}`", inline=False)
            
            await interaction.followup.send(embed=embed)
        else:
            # API 回傳失敗 (例如 API 限制或找不到該公網 IP)
            error_msg = data.get("message", "未知 API 錯誤")
            await interaction.followup.send(f"❌ API 查詢失敗：{error_msg}")
            
    except Exception as e:
        logger.error(f"IP 查詢時發生非預期錯誤: {e}")
        await interaction.followup.send("❌ 伺服器內部錯誤，請稍後再試。")

# --- 指令 /ping  ---
@bot.tree.command(name="ping", description="測試延遲並查看系統與 CPU 狀態")
async def ping_command(interaction: discord.Interaction):
    # 已包含 LOG
    log_command(interaction, "ping", "系統資訊查詢")
    
    start_time = time.time()
    await interaction.response.send_message("🏓 正在讀取系統數據...")
    end_time = time.time()

    # --- 系統數據收集 ---
    uptime = datetime.now() - bot_start_time
    uptime_str = str(uptime).split('.')[0]
    process = psutil.Process(os.getpid())
    memory_usage = process.memory_info().rss / 1024 / 1024
    cpu_usage = psutil.cpu_percent(interval=0.1) 
    cpu_count_logical = psutil.cpu_count()
    cpu_count_physical = psutil.cpu_count(logical=False)

    embed = discord.Embed(
        title="🖥️ 機器人與伺服器狀態",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💓 API 延遲", value=f"`{round(bot.latency * 1000)}ms`", inline=True)
    embed.add_field(name="⏳ 往返延遲", value=f"`{round((end_time - start_time) * 1000)}ms`", inline=True)
    embed.add_field(name="📊 CPU 使用率", value=f"`{cpu_usage}%`", inline=True)
    embed.add_field(name="🧠 CPU 核心", value=f"`{cpu_count_physical}C / {cpu_count_logical}T`", inline=True)
    embed.add_field(name="💾 記憶體佔用", value=f"`{round(memory_usage, 2)} MB`", inline=True)
    embed.add_field(name="⏱️ 運行時間 (Uptime)", value=f"`{uptime_str}`", inline=False)

    embed.set_footer(text=f"伺服器節點: {socket.gethostname()}")
    await interaction.edit_original_response(content=None, embed=embed)

# --- 指令 /whois (整合修正版) ---
@bot.tree.command(name="whois", description="查詢網域的註冊資訊 (Whois)")
@app_commands.describe(domain="要查詢的網域名稱 (例如 google.com)")
async def whois_command(interaction: discord.Interaction, domain: str):
    await interaction.response.defer()
    
    # 1. 清理與記錄
    target_domain = clean_domain(domain.strip().lower())
    log_command(interaction, "whois", target_domain)

    # 2. 基本檢查：是否為有效網域格式
    if "." not in target_domain:
        await interaction.followup.send(f"❌ `{target_domain}` 看起來不像是有效的網域。")
        return

    # 3. 安全檢查：如果是直接輸入 IP 則拒絕
    try:
        ipaddress.ip_address(target_domain)
        await interaction.followup.send("❌ WHOIS 指令目前僅支援網域查詢（例如 google.com），請勿輸入 IP。")
        return
    except ValueError:
        pass

    # 4. 執行 WHOIS 查詢
    try:
        loop = asyncio.get_event_loop()
        # 使用 run_in_executor 避免阻塞 Event Loop
        w = await loop.run_in_executor(None, whois.whois, target_domain)
        
        # 定義日期格式化輔助函式
        def format_date(d):
            if isinstance(d, list):
                d = d[0] if len(d) > 0 else None
            return d.strftime('%Y-%m-%d') if d else "未知"

        # 5. 建立 Embed (在此定義變數)
        embed = discord.Embed(
            title=f"📋 WHOIS 查詢結果: {target_domain}",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )

        embed.add_field(name="🏢 註冊商 (Registrar)", value=w.registrar or "未知", inline=False)
        embed.add_field(name="📅 註冊日期", value=format_date(w.creation_date), inline=True)
        embed.add_field(name="⏳ 到期日期", value=format_date(w.expiration_date), inline=True)
        
        # 處理名稱伺服器 (NS)
        ns_info = "未知"
        if w.name_servers:
            ns_list = w.name_servers if isinstance(w.name_servers, list) else [w.name_servers]
            ns_info = "\n".join(ns_list)
        
        embed.add_field(name="🌐 名稱伺服器 (NS)", value=f"```\n{ns_info}\n```", inline=False)
        embed.set_footer(text="WHOIS 數據查詢完成")

        # 6. 正確發送 Embed
        await interaction.followup.send(embed=embed)

    except Exception as e:
        # 捕捉常見的解析或連線錯誤
        if "getaddrinfo failed" in str(e) or "11001" in str(e):
            logger.error(f"WHOIS DNS 解析失敗: {target_domain}")
            await interaction.followup.send(f"❌ 無法解析網域 `{target_domain}`，請檢查該網域是否存在。")
        else:
            logger.error(f"WHOIS 未知錯誤: {e}")
            await interaction.followup.send(f"❌ 無法取得 `{target_domain}` 的資訊。請確認網域輸入正確。")
    
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("ERROR: CAN'T FIND DISCORD_TOKEN。Please check .env file.")
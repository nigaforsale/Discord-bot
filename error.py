import os
import logging
import discord
import aiohttp
import traceback
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
WEBHOOK_URL = os.getenv('LOG_WEBHOOK_URL')

# --- 自動建立 log 資料夾 ---
LOG_DIR = "log"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    print(f"📁 已建立日誌資料夾: {LOG_DIR}/")

# --- 初始化 Logger ---
logger = logging.getLogger('discord_bot')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')

# 檔案處理器：路徑指向 log/bot.log
file_handler = logging.FileHandler(os.path.join(LOG_DIR, 'bot.log'), encoding='utf-8')
file_handler.setFormatter(formatter)

# 控制台處理器
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# 啟動時檢查 Webhook 狀態
if WEBHOOK_URL:
    print(f"✅ Webhook URL 已載入: {WEBHOOK_URL[:10]}...")
else:
    print("⚠️ 警告: 未偵測到 LOG_WEBHOOK_URL")

# --- 基礎 Webhook 發送功能 ---
async def send_webhook_log(message, level="INFO"):
    if not WEBHOOK_URL: return
    
    clean_message = (message[:3800] + '\n...(內容過長已截斷)') if len(message) > 3800 else message
    BOT_NAME = "系統監控助手"
    
    color = 0x3498db # INFO: 藍色
    if level == "ERROR": color = 0xe74c3c # 紅色
    elif level == "WARNING": color = 0xf1c40f # 黃色

    payload = {
        "username": BOT_NAME,
        "embeds": [{
            "title": f"📊 系統日誌 - {level}",
            "description": f"```python\n{clean_message}\n```",
            "color": color,
            "footer": {"text": f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        }]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(WEBHOOK_URL, json=payload) as resp:
                if resp.status not in [200, 204]:
                    print(f"Webhook 發送失敗: {resp.status}")
        except Exception as e:
            print(f"Webhook 連線異常: {e}")

# --- 一般指令記錄 (Info Log) ---
def log_command(interaction: discord.Interaction, command_name: str, details: str, bot=None):
    user = interaction.user
    guild = interaction.guild.name if interaction.guild else "私訊"
    log_msg = f"使用者: {user} | 伺服器: {guild} | 指令: /{command_name} | 內容: {details}"
    
    logger.info(f"[CMD] {log_msg}")
    
    if bot and WEBHOOK_URL:
        bot.loop.create_task(send_webhook_log(log_msg, "INFO"))

# --- 警告記錄 (Warning Log) ---
def log_warning(interaction: discord.Interaction, details: str, bot=None):
    cmd_name = interaction.command.name if interaction.command else "Unknown"
    user = interaction.user
    
    logger.warning(f"指令警告 [/{cmd_name}]: {details}")

    if bot and WEBHOOK_URL:
        report = (
            f"⚠️ **輸入無效/被拒絕**\n"
            f"🔹 **指令**: `/{cmd_name}`\n"
            f"👤 **使用者**: `{user}`\n"
            f"📝 **詳情**: {details}"
        )
        bot.loop.create_task(send_webhook_log(report, "WARNING"))

# --- 錯誤處理核心 (Error Handler) ---
async def handle_command_error(interaction: discord.Interaction, error, bot=None):
    orig_error = getattr(error, 'original', error)
    full_error = "".join(traceback.format_exception(type(orig_error), orig_error, orig_error.__traceback__))
    
    cmd_name = interaction.command.name if interaction.command else "Unknown"
    
    # 寫入本地 Log (現在會寫入 log/bot.log)
    logger.error(f"指令錯誤 [/{cmd_name}]:\n{full_error}")

    # 發送 Webhook
    if WEBHOOK_URL:
        short_error = (full_error[-1500:]) if len(full_error) > 1500 else full_error
        report = (
            f"🚨 **系統執行報錯**\n"
            f"🔹 **指令**: `/{cmd_name}`\n"
            f"👤 **使用者**: `{interaction.user}`\n"
            f"📍 **位置**: `{interaction.guild.name if interaction.guild else '私訊'}`\n"
            f"```python\n{short_error}\n```"
        )
        await send_webhook_log(report, "ERROR")

    # 回覆使用者
    try:
        msg = "❌ 系統執行出錯，已自動回報管理員。"
        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)
    except:
        pass
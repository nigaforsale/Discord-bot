import discord
import yt_dlp
import asyncio
import error

# FFmpeg 設定 (優化串流品質與重連)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# YTDL 設定 (加入 cookiefile 避免 429 錯誤，並使用最穩定的客戶端)
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto', 
    'source_address': '0.0.0.0',
    # 嘗試模擬瀏覽器以減少被擋的機率
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

queues = {}

# 輔助：搜尋歌曲 (run_in_executor 防止卡死)
async def search_song(query):
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        return {
            'url': data['url'], 
            'title': data['title'],
            'duration': data['duration'],
            'webpage_url': data['webpage_url']
        }
    except Exception as e:
        error.logger.error(f"YTDL 搜尋錯誤: {e}")
        return None

# 輔助：播放下一首
def play_next(interaction: discord.Interaction, bot):
    guild_id = interaction.guild.id
    
    if guild_id in queues and len(queues[guild_id]) > 0:
        song = queues[guild_id].pop(0)
        voice_client = interaction.guild.voice_client
        
        # [修正] 再次檢查連線狀態，如果斷線就停止
        if voice_client and voice_client.is_connected():
            try:
                source = discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS)
                voice_client.play(source, after=lambda e: play_next(interaction, bot))
                error.logger.info(f"自動播放下一首: {song['title']}")
            except Exception as e:
                error.logger.error(f"播放下一首失敗: {e}")
        else:
            error.logger.warning("嘗試播放下一首時發現已斷線")
    else:
        error.logger.info(f"佇列已空 ({guild_id})")

# 核心：加入佇列並播放
async def add_to_queue(interaction: discord.Interaction, query: str, bot):
    guild_id = interaction.guild.id
    
    # 1. 搜尋歌曲
    song = await search_song(query)
    if not song:
        return "❌ 找不到歌曲，可能是 YouTube 限制或格式不支援。"

    # 2. 初始化佇列
    if guild_id not in queues:
        queues[guild_id] = []

    voice_client = interaction.guild.voice_client

    # [關鍵修正] 如果搜尋完發現沒連線，嘗試重新連線
    if not voice_client or not voice_client.is_connected():
        if interaction.user.voice:
            try:
                voice_client = await interaction.user.voice.channel.connect()
            except Exception as e:
                return f"❌ 無法重新連線語音頻道: {e}"
        else:
            return "❌ 您不在語音頻道中，無法播放。"

    # 3. 播放邏輯
    if voice_client.is_playing() or voice_client.is_paused():
        queues[guild_id].append(song)
        return f"🎵 已加入佇列：**{song['title']}** (第 {len(queues[guild_id])} 順位)"
    else:
        try:
            source = discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS)
            voice_client.play(source, after=lambda e: play_next(interaction, bot))
            return f"▶️ 現正播放：**{song['title']}**\n🔗 {song['webpage_url']}"
        except Exception as e:
            error.logger.error(f"播放失敗: {e}")
            return f"❌ 播放發生錯誤 (請檢查 FFmpeg 是否安裝): {e}"
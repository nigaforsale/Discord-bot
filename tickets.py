import discord
from discord.ui import View, Button
import error
import asyncio
import os
from datetime import datetime

# --- 按鈕介面：開啟客服單 ---
class TicketLauncher(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        if isinstance(error, discord.NotFound) and error.code == 10062:
            return
        await super().on_error(interaction, error, item)

    @discord.ui.button(label="📩 開啟客服單", style=discord.ButtonStyle.blurple, custom_id="ticket_create_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        user = interaction.user
        
        ticket_name = f"ticket-{user.name.lower().replace(' ', '-')}"
        existing_channel = discord.utils.get(guild.text_channels, name=ticket_name)
        
        if existing_channel:
            await interaction.followup.send(f"❌ 您已經有一個客服單了：{existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        try:
            channel = await guild.create_text_channel(
                name=ticket_name, 
                overwrites=overwrites, 
                reason=f"Ticket created by {user}",
                topic=str(user.id)
            )
            
            embed = discord.Embed(title="📨 客服單已建立", description=f"您好 {user.mention}。", color=discord.Color.green())
            await channel.send(user.mention, embed=embed, view=TicketControls())
            
            await interaction.followup.send(f"✅ 客服單已建立：{channel.mention}", ephemeral=True)
            error.log_command(interaction, "ticket_create", f"建立頻道 {channel.name}", interaction.client)

        except Exception as e:
            error.logger.error(f"建立 Ticket 失敗: {e}")
            try:
                await interaction.followup.send("❌ 建立失敗，請檢查機器人權限。", ephemeral=True)
            except: pass

# --- 按鈕介面：管理客服單 ---
class TicketControls(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        if isinstance(error, discord.NotFound) and error.code == 10062:
            return
        await super().on_error(interaction, error, item)

    @discord.ui.button(label="🔒 關閉並儲存紀錄", style=discord.ButtonStyle.red, custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await interaction.followup.send("💾 正在儲存對話紀錄，頻道將在 5 秒後刪除...")
        
        channel = interaction.channel
        closer_user = interaction.user 
        
        save_dir = "log/transcripts"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        transcript = [f"--- Ticket Transcript: {channel.name} ---", f"Time: {datetime.now()}", "-"*30]
        
        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime('%Y-%m-%d %H:%M:%S')
            author = f"{message.author.name}"
            content = message.content
            line = f"[{timestamp}] {author}: {content}"
            transcript.append(line)
            if message.attachments:
                for attachment in message.attachments:
                    transcript.append(f"    [附件]: {attachment.url}")
        
        transcript.append("-" * 30)
        transcript_text = "\n".join(transcript)

        file_name = f"{channel.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        file_path = os.path.join(save_dir, file_name)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
            
        error.logger.info(f"客服單紀錄已儲存: {file_path}")

        # [重點修正] 抓取接收者
        recipient = None
        if channel.topic and channel.topic.isdigit():
            ticket_owner_id = int(channel.topic)
            try:
                # 改用 fetch_member (API 請求)，解決 get_member (Cache) 找不到人的問題
                recipient = await interaction.guild.fetch_member(ticket_owner_id)
            except discord.NotFound:
                # 如果使用者已經退出伺服器
                error.logger.warning(f"使用者 {ticket_owner_id} 已離開，無法發送紀錄。")
                recipient = None
            except Exception:
                recipient = None
        
        # 如果真的抓不到開單者，才寄給管理員
        if not recipient:
            recipient = closer_user

        try:
            discord_file = discord.File(file_path)
            await recipient.send(f"📄 這是 `{channel.name}` 的對話紀錄副本。", file=discord_file)
        except Exception:
            pass

        await asyncio.sleep(5)
        await channel.delete(reason=f"Closed by {closer_user.name}")
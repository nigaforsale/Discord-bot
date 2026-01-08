import discord
from discord import app_commands
from discord.ui import Select, View
import asyncio
import dns.resolver
import whois
import utils
import error
import tickets
from datetime import datetime
import time
import psutil

#        UI 組件：Help 下拉選單

class HelpSelect(Select):
    def __init__(self, bot, bot_start_time):
        self.bot = bot
        self.bot_start_time = bot_start_time
        
        options = [
            discord.SelectOption(
                label="🏠 首頁", 
                description="查看機器人狀態與簡介", 
                value="home", 
                emoji="🏠"
            ),
            discord.SelectOption(
                label="🛠️ 工具指令", 
                description="DNS、IP、Whois、Ping 查詢工具", 
                value="tools", 
                emoji="🛠️"
            ),
            discord.SelectOption(
                label="ℹ️ 資訊查詢", 
                description="查看使用者、伺服器資訊與頭像", 
                value="info", 
                emoji="ℹ️"
            ),
            discord.SelectOption(
                label="🛡️ 管理員指令", 
                description="踢出、封鎖、刪除訊息、客服系統", 
                value="admin", 
                emoji="🛡️"
            ),
            
        ]
        super().__init__(placeholder="請選擇您要查看的指令分類...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        
        # --- 1. 首頁 Embed ---
        if value == "home":
            uptime = str(datetime.now() - self.bot_start_time).split('.')[0]
            ping = round(self.bot.latency * 1000)
            
            embed = discord.Embed(
                title="🤖 幫助中心",
                description="請從下方選單選擇指令類別。",
                color=discord.Color.from_rgb(44, 47, 51) # 深色系
            )
            embed.add_field(name="⏱️ 運行時間", value=f"`{uptime}`", inline=True)
            embed.add_field(name="💓 系統延遲", value=f"`{ping} ms`", inline=True)
            embed.add_field(name="📚 指令總數", value=f"`{len(self.bot.tree.get_commands())}` 個", inline=True)
            
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            embed.set_image(url="https://i.pinimg.com/736x/46/f5/b4/46f5b4064a5bf82b9d4af012313d2f95.jpg") # 您可以換成自己的橫幅圖，或刪除這行

        # --- 2. 工具指令 Embed ---
        elif value == "tools":
            embed = discord.Embed(
                title="🛠️ 工具指令清單",
                description="網路工具。",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🌐 `/dns <domain>`", 
                value="查詢網域解析紀錄 (A, CNAME, MX)", 
                inline=False
            )
            embed.add_field(
                name="🔍 `/ip <ip>`", 
                value="查詢 IP 地理位置與 ISP 資訊", 
                inline=False
            )
            embed.add_field(
                name="📋 `/whois <domain>`", 
                value="查詢網域註冊商與到期日", 
                inline=False
            )
            embed.add_field(
                name="🏓 `/ping`", 
                value="查看機器人延遲與伺服器硬體狀態", 
                inline=False
            )
        elif value == "info":
            embed = discord.Embed(
                title="ℹ️ 資訊查詢",
                description="查看使用者、伺服器資訊與頭像",
                color=discord.Color.green()
            )
            embed.add_field(
                name="👤 `/userinfo`", 
                value="查詢成員資訊", 
                inline=False
            )
            embed.add_field(
                name="🏰 `/serverinfo`", 
                value="查詢伺服器資訊", 
                inline=False
            )
            embed.add_field(
                name="🖼️ `/avatar`", 
                value="偷看頭像", 
                inline=False
            )

        # --- 3. 管理員指令 Embed ---
        elif value == "admin":
            embed = discord.Embed(
                title="🛡️ 管理員專用指令",
                description="僅限管理員。",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🎫 `/ticket_setup [channel]`", 
                value="建立「開啟客服單」的按鈕面板", 
                inline=False
            )
            embed.add_field(
                name="🗑️ `/delete [count]`", 
                value="批量刪除指定數量的訊息", 
                inline=False
            )
            embed.add_field(
                name="✏️ `/nick <member> <name>`", 
                value="強制修改成員暱稱", 
                inline=False
            )
            embed.add_field(
                name="👢 `/kick <member>`", 
                value="踢出成員", 
                inline=False
            )
            embed.add_field(
                name="🔨 `/ban <member>`", 
                value="封鎖成員", 
                inline=False
            )

        embed.set_footer(text=f"由 {interaction.user.display_name} 查詢 • {datetime.now().strftime('%H:%M')}", icon_url=interaction.user.display_avatar.url)
        
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(View):
    def __init__(self, bot, bot_start_time):
        super().__init__(timeout=60) # 60秒後選單失效
        self.add_item(HelpSelect(bot, bot_start_time))
        
    async def on_timeout(self):
        # 超時後鎖定選單，提示使用者重新輸入指令
        for item in self.children:
            item.disabled = True
        # 注意：這裡無法編輯原本的訊息，除非我們有儲存 message 物件，
        # 但通常為了簡單起見，讓它單純失效即可。

def setup_commands(tree, bot_start_time):
    bot = tree.client

    # --- /help ---
    @tree.command(name="help", description="開啟互動式幫助選單")
    async def help_command(interaction: discord.Interaction):
        error.log_command(interaction, "help", "開啟互動選單", bot)
        
        # 預設顯示首頁 Embed
        uptime = str(datetime.now() - bot_start_time).split('.')[0]
        embed = discord.Embed(
            title="🤖 幫助中心",
            description="請點擊下方選單查看詳細指令。",
            color=discord.Color.from_rgb(44, 47, 51)
        )
        embed.add_field(name="⏱️ 運行時間", value=f"`{uptime}`", inline=True)
        embed.add_field(name="💓 延遲", value=f"`{round(bot.latency * 1000)} ms`", inline=True)
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        
        # 發送 Embed 與 View (下拉選單)
        view = HelpView(bot, bot_start_time)
        await interaction.response.send_message(embed=embed, view=view)

    # --- /dns ---
    @tree.command(name="dns", description="查詢 DNS 紀錄")
    async def dns_command(interaction: discord.Interaction, host: str, ephemeral: bool = True):
        await interaction.response.defer()
        error.log_command(interaction, "dns", f"{host}", bot)
        
        # 1. 檢查 IP
        check_result = utils.check_ip_restricted(host)
        if check_result and check_result != "NOT_IP":
            await interaction.followup.send(check_result)
            error.log_warning(interaction, f"嘗試查詢受限 IP: {host}", bot)
            return

        embed = discord.Embed(title="🌐 DNS 解析結果", description=f"目標: `{host}`", color=discord.Color.green(), timestamp=datetime.now())
        
        try:
            a_records = dns.resolver.resolve(host, 'A')
            embed.add_field(name="📌 A Record", value="\n".join([r.address for r in a_records]), inline=False)
        except Exception:
            embed.add_field(name="📌 A Record", value="❌ 無 A 紀錄", inline=False)
        
        try:
            cname_records = dns.resolver.resolve(host, 'CNAME')
            embed.add_field(name="🔗 CNAME", value="\n".join([str(r.target) for r in cname_records]), inline=False)
        except Exception:
            embed.add_field(name="🔗 CNAME", value="❌ 無 CNAME 紀錄", inline=False)
            
        try:
            mx_records = dns.resolver.resolve(host, 'MX')
            embed.add_field(name="📧 MX Record", value="\n".join([f"{r.preference}: {r.exchange}" for r in mx_records]), inline=False)
        except Exception:
            embed.add_field(name="📧 MX Record", value="❌ 無 MX 紀錄", inline=False)

        msg = await interaction.followup.send(embed=embed)
        if ephemeral:
            await asyncio.sleep(25) 
            try: await msg.delete()
            except: pass

    # --- /ip ---
    @tree.command(name="ip", description="查詢 IP 詳細資訊")
    async def ip_command(interaction: discord.Interaction, ip: str, ephemeral: bool = True):
        await interaction.response.defer()
        error.log_command(interaction, "ip", ip, bot)
        try:
            check_result = utils.check_ip_restricted(ip)
            
            if check_result == "NOT_IP":
                await interaction.followup.send("❌ 錯誤：請輸入有效的 IPv4 地址。")
                error.log_warning(interaction, f"格式錯誤 (非 IPv4): {ip}", bot)
                return
            
            if check_result:
                await interaction.followup.send(check_result)
                error.log_warning(interaction, f"嘗試查詢受限 IP: {ip}", bot)
                return

            data = await utils.get_ip_info(ip)
            if data and data.get("status") == "success":
                embed = discord.Embed(title=f"🔍 IP 詳細資訊: {ip}", color=discord.Color.blue())
                embed.add_field(name="🌍 國家", value=data.get("country", "未知"), inline=True)
                embed.add_field(name="🏙️ 城市", value=data.get("city", "未知"), inline=True)
                embed.add_field(name="🏢 ISP", value=data.get("isp", "未知"), inline=False)
                embed.add_field(name="🔄 反向 DNS", value=f"`{data.get('reverse', '無')}`", inline=False)
                await interaction.followup.send(embed=embed)
            else:
                raise ValueError(f"API 回傳錯誤: {data.get('message', '未知')}")
        except Exception as e:
            raise e
        
        msg = await interaction.followup.send(embed=embed)
        if ephemeral:
            await asyncio.sleep(25) 
            try: await msg.delete()
            except: pass

    # --- /whois ---
    @tree.command(name="whois", description="查詢網域註冊資訊")
    async def whois_command(interaction: discord.Interaction, domain: str, ephemeral: bool = True):
        await interaction.response.defer()
        target = utils.clean_domain(domain.strip().lower())
        error.log_command(interaction, "whois", target, bot)

        if "." not in target:
            await interaction.followup.send(f"❌ `{target}` 無效網域。")
            error.log_warning(interaction, f"網域格式錯誤: {target}", bot)
            return
            
        try:
            loop = asyncio.get_event_loop()
            w = await loop.run_in_executor(None, whois.whois, target)
            embed = discord.Embed(title=f"📋 WHOIS 查詢結果: {target}", color=discord.Color.purple(), timestamp=datetime.now())
            embed.add_field(name="🏢 註冊商", value=w.registrar or "未知", inline=False)
            embed.add_field(name="📅 註冊日期", value=utils.format_whois_date(w.creation_date), inline=True)
            embed.add_field(name="⏳ 到期日期", value=utils.format_whois_date(w.expiration_date), inline=True)
            ns = "\n".join(w.name_servers) if isinstance(w.name_servers, list) else (w.name_servers or "未知")
            embed.add_field(name="🌐 名稱伺服器 (NS)", value=f"```\n{ns}\n```", inline=False)
            await interaction.followup.send(embed=embed)
        except Exception as e:
            raise e
        
        msg = await interaction.followup.send(embed=embed)
        if ephemeral:
            await asyncio.sleep(25) 
            try: await msg.delete()
            except: pass
    # --- /ping ---
    @tree.command(name="ping", description="查看延遲與系統狀態")
    async def ping_command(interaction: discord.Interaction):
        error.log_command(interaction, "ping", "系統狀態查詢", bot)
        start_time = time.time()
        await interaction.response.send_message("🏓 讀取中...")
        end_time = time.time()

        uptime = str(datetime.now() - bot_start_time).split('.')[0]
        cpu_usage = psutil.cpu_percent(interval=None)
        ram_usage = psutil.virtual_memory().percent
        gpu_data = utils.get_gpu_info()
        disks_data = utils.get_disk_info()

        embed = discord.Embed(title="🖥️ 系統儀表板", color=discord.Color.blue(), timestamp=datetime.now())
        embed.add_field(name="💓 延遲", value=f"`{round(tree.client.latency * 1000)}ms`", inline=True)
        embed.add_field(name="⏱️ 運行", value=f"`{uptime}`", inline=True)
        embed.add_field(name="📊 CPU", value=utils.create_progress_bar(cpu_usage), inline=False)
        embed.add_field(name="💾 RAM", value=utils.create_progress_bar(ram_usage), inline=False)

        if disks_data:
            for disk in disks_data:
                embed.add_field(name=f"💽 {disk['label']}", value=f"{utils.create_progress_bar(disk['percent'])}\n{disk['used']}/{disk['total']} GB", inline=False)
        
        if gpu_data:
            embed.add_field(name=f"🎮 {gpu_data['name']}", value=f"負載: {utils.create_progress_bar(gpu_data['load'])}\n溫度: `{gpu_data['temp']}°C`", inline=False)

        await interaction.edit_original_response(content=None, embed=embed)

    # --- /userinfo ---
    @tree.command(name="userinfo", description="查看成員詳細資訊 (註冊日、加入日、身分組)")
    @app_commands.describe(member="選擇要查詢的成員 (預設為自己)")
    async def userinfo_command(interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        
        # 建立 Embed
        embed = discord.Embed(title=f"👤 使用者資訊: {target.name}", color=target.color)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # 1. 基本資料
        embed.add_field(name="🆔 ID", value=f"`{target.id}`", inline=True)
        embed.add_field(name="📛 暱稱", value=target.nick or "無", inline=True)
        embed.add_field(name="🤖 機器人?", value="是" if target.bot else "否", inline=True)
        
        # 2. 時間資料 (使用 Discord Timestamp 格式 <t:timestamp:R>)
        created_at = int(target.created_at.timestamp())
        joined_at = int(target.joined_at.timestamp())
        embed.add_field(name="📅 帳號註冊", value=f"<t:{created_at}:D> (<t:{created_at}:R>)", inline=False)
        embed.add_field(name="📥 加入時間", value=f"<t:{joined_at}:D> (<t:{joined_at}:R>)", inline=False)
        
        # 3. 身分組 (過濾掉 @everyone)
        roles = [role.mention for role in target.roles if role.name != "@everyone"]
        role_str = ", ".join(roles) if roles else "無身分組"
        if len(role_str) > 1000: role_str = role_str[:1000] + "..." # 防止過長
        
        embed.add_field(name=f"🎭 身分組 ({len(roles)})", value=role_str, inline=False)
        
        await interaction.response.send_message(embed=embed)

    # --- /serverinfo ---
    @tree.command(name="serverinfo", description="查看本伺服器詳細資訊")
    async def serverinfo_command(interaction: discord.Interaction):
        guild = interaction.guild
        
        embed = discord.Embed(title=f"🏰 伺服器資訊: {guild.name}", color=discord.Color.gold())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # 統計人數
        total = guild.member_count
        bots = len([m for m in guild.members if m.bot])
        humans = total - bots
        
        embed.add_field(name="👑 擁有者", value=guild.owner.mention, inline=True)
        embed.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="🌍 地區/等級", value=f"Level {guild.premium_tier}", inline=True)
        
        created_at = int(guild.created_at.timestamp())
        embed.add_field(name="📅 成立時間", value=f"<t:{created_at}:D> (<t:{created_at}:R>)", inline=False)
        
        embed.add_field(name="👥 成員統計", value=f"總數: **{total}**\n人類: **{humans}**\n機器人: **{bots}**", inline=True)
        embed.add_field(name="📺 頻道統計", value=f"文字: **{len(guild.text_channels)}**\n語音: **{len(guild.voice_channels)}**", inline=True)
        
        await interaction.response.send_message(embed=embed)

    # --- /avatar ---
    @tree.command(name="avatar", description="獲取使用者的高清頭像")
    @app_commands.describe(member="選擇成員 (預設為自己)")
    async def avatar_command(interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        
        embed = discord.Embed(title=f"🖼️ {target.display_name} 的頭像", color=target.color)
        embed.set_image(url=target.display_avatar.url)
        
        # 提供下載連結按鈕
        view = discord.ui.View()
        btn = discord.ui.Button(label="下載圖片", url=target.display_avatar.url, style=discord.ButtonStyle.link)
        view.add_item(btn)
        
        await interaction.response.send_message(embed=embed, view=view)

    # ==========================
    #      管理員指令區
    # ==========================
    
    # --- /ticket_setup ---    
    @tree.command(name="ticket_setup", description="[管理員] 發送客服單建立面板")
    @app_commands.describe(channel="請選擇要發送面板的頻道 (若不選則發送至當前頻道)")
    @app_commands.default_permissions(administrator=True)
    async def ticket_setup_command(interaction: discord.Interaction, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        error.log_command(interaction, "ticket_setup", f"建立面板於 #{target_channel.name}", bot)
        
        if not target_channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(f"❌ 錯誤：我沒有權限在 {target_channel.mention} 發送訊息。", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎫 客服單系統",
            description="如果您需要點單、售後、 詢問，請點擊下方按鈕開啟客服單。",
            color=discord.Color.blue()
        )
        embed.set_footer(text="系統監控助手 • Ticket System")
        
        try:
            await target_channel.send(embed=embed, view=tickets.TicketLauncher())
            await interaction.response.send_message(f"✅ 客服面板已成功發送至 {target_channel.mention}", ephemeral=True)
        except Exception as e:
            error.logger.error(f"發送面板失敗: {e}")
            await interaction.response.send_message(f"❌ 發送失敗: {e}", ephemeral=True)

    # --- /nick ---
    @tree.command(name="nick", description="[管理員] 修改成員暱稱")
    @app_commands.describe(member="選擇成員", name="新的暱稱")
    @app_commands.default_permissions(administrator=True)
    async def nick_command(interaction: discord.Interaction, member: discord.Member, name: str):
        error.log_command(interaction, "nick", f"修改 {member} -> {name}", bot)

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ 錯誤：我無法修改該成員 (他的身分組比我高)。", ephemeral=True)
            return

        try:
            await member.edit(nick=name)
            await interaction.response.send_message(f"✅ 已將 {member.mention} 的暱稱改為 `{name}`", ephemeral=True)
        except Exception as e:
            error.logger.error(f"Nick 失敗: {e}")
            await interaction.response.send_message(f"❌ 修改失敗: {e}", ephemeral=True)

    # --- /kick ---
    @tree.command(name="kick", description="[管理員] 踢出成員")
    @app_commands.describe(member="選擇成員", reason="踢出原因 (選填)")
    @app_commands.default_permissions(administrator=True)
    async def kick_command(interaction: discord.Interaction, member: discord.Member, reason: str = "未提供原因"):
        error.log_command(interaction, "kick", f"踢出 {member} 原因: {reason}", bot)

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ 錯誤：我無法踢出該成員 (權限不足)。", ephemeral=True)
            return

        try:
            await member.kick(reason=reason)
            embed = discord.Embed(title="👢 成員已踢出", description=f"{member.mention} 已被踢出伺服器。", color=discord.Color.red())
            embed.add_field(name="原因", value=reason)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            error.logger.error(f"Kick 失敗: {e}")
            await interaction.response.send_message(f"❌ 踢出失敗: {e}", ephemeral=True)

    # --- /ban ---
    @tree.command(name="ban", description="[管理員] 封鎖成員")
    @app_commands.describe(member="選擇成員", reason="封鎖原因 (選填)")
    @app_commands.default_permissions(administrator=True)
    async def ban_command(interaction: discord.Interaction, member: discord.Member, reason: str = "未提供原因"):
        error.log_command(interaction, "ban", f"封鎖 {member} 原因: {reason}", bot)

        if member.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message("❌ 錯誤：我無法封鎖該成員 (權限不足)。", ephemeral=True)
            return

        try:
            await member.ban(reason=reason)
            embed = discord.Embed(title="🔨 成員已封鎖", description=f"{member.mention} 已被封鎖。", color=discord.Color.dark_red())
            embed.add_field(name="原因", value=reason)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            error.logger.error(f"Ban 失敗: {e}")
            await interaction.response.send_message(f"❌ 封鎖失敗: {e}", ephemeral=True)
    
    # --- /delete ---
    @tree.command(name="delete", description="[管理員] 批量刪除訊息")
    @app_commands.describe(count="要刪除的訊息數量 (預設 5)")
    @app_commands.default_permissions(manage_messages=True) # 權限限制
    async def delete_command(interaction: discord.Interaction, count: int = 5):
        # 1. 記錄日誌
        error.log_command(interaction, "delete", f"刪除 {count} 條訊息", bot)
        
        # 2. 回覆一個「只有你看得到的」訊息，避免這條訊息也被刪掉或留著礙眼
        await interaction.response.defer(ephemeral=True)

        try:
            # 3. 執行刪除 (purge)
            deleted = await interaction.channel.purge(limit=count)
            
            # 4. 回報結果
            await interaction.followup.send(f"🗑️ 已成功刪除 **{len(deleted)}** 則訊息。", ephemeral=True)
            
        except Exception as e:
            error.logger.error(f"Delete 失敗: {e}")
            await interaction.followup.send(f"❌ 刪除失敗: {e}", ephemeral=True)
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime
import asyncio
import error
import tickets
import commands as bot_commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class DNSBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.members = True
        super().__init__(command_prefix='/', intents=intents)

    async def setup_hook(self):
        error.logger.info("正在同步斜線指令...")
        
        self.tree.on_error = self.on_app_command_error

        self.add_view(tickets.TicketLauncher())
        self.add_view(tickets.TicketControls())
        
        bot_commands.setup_commands(self.tree, bot_start_time)
        
        await self.tree.sync()
        error.logger.info("機器人已準備就緒！")

    async def on_app_command_error(self, interaction: discord.Interaction, error_obj: app_commands.AppCommandError):
        await error.handle_command_error(interaction, error_obj, self)

bot_start_time = datetime.now()
bot = DNSBot()

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        error.logger.error("錯誤：找不到 DISCORD_TOKEN，請檢查 .env 檔案。")
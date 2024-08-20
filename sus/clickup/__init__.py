"""Integration with ClickUp."""

from sus.clickup.abstract import *
from sus.basiclib import unix_to_datetime, escape_url
from discord.ext  import tasks, commands
import asyncio
import datetime
import discord

REPORT_CHANNEL_ID, MENTION_ID = None, None
@config_handler.after_load
def __load_config():
    global REPORT_CHANNEL_ID, MENTION_ID
    REPORT_CHANNEL_ID = config_handler.get_configuration("clickup.report_channel_id")
    MENTION_ID = config_handler.get_configuration("clickup.mention_id")
 
class ClickupCog(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.prober.start()
        self.next_reminder: datetime.datetime = self.next_morning(datetime.datetime.now())

    @classmethod
    def next_morning(cls, t: datetime.datetime):
        """Produce a datetime for the next moring (8 o'clock)"""
        return datetime.datetime(t.year, t.month, t.day + (1 if t.hour >= 8 else 0), 8, 0, 0, 0)

    def cog_unload(self):
        self.prober.cancel()

    @commands.slash_command()
    async def list_tasks(self, ctx: discord.ApplicationContext):
        """
        List all tasks from a user.
        """
        await ctx.defer()
        
        data = ClickupData()
        msg = ""
        tasks = data.get_all_tasks()
        tasks.sort(key=lambda x: (0 if x.due_date else 1, x.due_date))
        for task in tasks:
            due_date = unix_to_datetime(task.due_date) if task.due_date else "No Due!"
            msg += f"- Task [{task.id}](<{task.url}>) {task.name}, due at **{due_date}**\n"

        await ctx.followup.send(msg)
        channel = ctx.interaction.channel
        if channel:
            await channel.send(msg, suppress=True)
        

    @tasks.loop(hours=23.9)
    async def prober(self):
        await asyncio.sleep(max(0, (self.next_reminder - datetime.datetime.now()).total_seconds()))
        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        user = await self.bot.fetch_user(MENTION_ID)

        data = ClickupData()
        msg = f"{user.mention}\n# Daily Reminder {datetime.datetime.now().strftime('%b %d')}\n"
        tasks = data.get_all_tasks()
        tasks.sort(key=lambda x: (0 if x.due_date else 1, x.due_date))
        for task in tasks[:10]:
            due_date = unix_to_datetime(task.due_date) if task.due_date else "No Due!"
            msg += f"- Task [{task.id}](<{task.url}>) {task.name}, due at **{due_date}**\n"
        if len(tasks) > 10:
            msg += f"\nThere are still **{len(tasks) - 10}** more tasks."
        await channel.send(msg, suppress=True)
        self.next_reminder = self.next_morning(self.next_reminder)

    @prober.before_loop
    async def before_prober(self):
        await self.bot.wait_until_ready()
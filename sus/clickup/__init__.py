"""Integration with ClickUp."""

from sus.clickup.abstract import *
from sus.basiclib import unix_to_datetime, escape_url
from discord.ext import tasks, commands
import asyncio
import datetime
import discord

REPORT_CHANNEL_ID, MENTION_ID = None, None


@config_handler.after_load
def __load_config():
    global REPORT_CHANNEL_ID, MENTION_ID
    REPORT_CHANNEL_ID = config_handler.get_configuration(
        "clickup.report_channel_id")
    MENTION_ID = config_handler.get_configuration("clickup.mention_id")


class ClickupCog(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.prober.start()
        self.next_reminder: datetime.datetime = self.next_morning(
            datetime.datetime.now())

    @classmethod
    def next_morning(cls, t: datetime.datetime):
        """Produce a datetime for the next moring (8 o'clock)"""
        return datetime.datetime(t.year, t.month, t.day + (1 if t.hour >= 8 else 0), 8, 0, 0, 0)

    def cog_unload(self):
        self.prober.cancel()

    @classmethod
    def stringify_tasks(cls, task_list: list[ClickupTask]) -> str:
        msg = ""
        for task in task_list:
            due_date = f"Due at **`{unix_to_datetime(task.due_date)}`**" if task.due_date else "**No Due!**"
            msg += f"- :page_facing_up: {due_date}: [`{task.id}`](<{task.url}>) {task.name}\n"
        return msg

    def parse_tasks(self, truncate_num: int = 10) -> str:
        data = ClickupData()
        tasks = data.get_all_tasks()
        tasks.sort(key=lambda x: (0 if x.due_date else 1, x.due_date))

        # Custom logic of categorize tasks
        unreleased: list[ClickupTask] = []
        in_progress: list[ClickupTask] = []
        done: list[ClickupTask] = []
        for task in tasks:
            if task.status.type == "open":
                unreleased.append(task)
            elif task.status.type == "custom":
                in_progress.append(task)
            elif task.status.type == "done":
                done.append(task)

        return ("## :mag: Opened\n" + 
                self.stringify_tasks(unreleased[:truncate_num]) + 
                "## :chart_with_upwards_trend: In Progress\n" + 
                self.stringify_tasks(in_progress[:truncate_num]))

    @commands.slash_command()
    async def list_tasks(self, ctx: discord.ApplicationContext, truncate_num: int = 10):
        """
        List all tasks from a user.
        """
        await ctx.defer()
        await ctx.followup.send(self.parse_tasks(truncate_num))

    @tasks.loop(hours=23.9)
    async def prober(self):
        await asyncio.sleep(max(0, (self.next_reminder - datetime.datetime.now()).total_seconds()))
        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        user = await self.bot.fetch_user(MENTION_ID)
        msg = (f"{user.mention}\n" + 
               f"# Daily Reminder {datetime.datetime.now().strftime('%b %d')}\n" +
                self.parse_tasks())
        await channel.send(msg, suppress=True)
        self.next_reminder = self.next_morning(self.next_reminder)

    @prober.before_loop
    async def before_prober(self):
        await self.bot.wait_until_ready()

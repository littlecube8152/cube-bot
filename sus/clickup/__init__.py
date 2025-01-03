"""Integration with ClickUp."""

from sus.clickup.abstract import *
from sus.basiclib import unix_to_datetime, unix_to_time
from discord.ext import tasks, commands
import asyncio
import datetime
import discord

REPORT_CHANNEL_ID, MENTION_ID = None, None

# Special tags
T_COURSE = "course"
T_ASSIGNMENT = "assignment"
T_EXAM = "exam"
T_EVENT = "event"
T_MEETING = "meeting"

NUM_TRUNC = 20
NUM_BATCH = 10


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
        if t.hour >= 7:
            t += datetime.timedelta(days=1)
        return datetime.datetime(t.year, t.month, t.day, 7, 0, 0, 0)

    def cog_unload(self):
        self.prober.cancel()

    @classmethod
    def stringify_tasks(cls, task_list: list[ClickupTask], header: str, enable_title: bool) -> str:

        def get_timedelta(due_time: float):
            delta = datetime.datetime.fromtimestamp(due_time) - datetime.datetime.now()
            
            negative = False
            if delta < datetime.timedelta(seconds=0):
                negative = True
                delta = -delta

            # if delta < DELTA_IMPORTANT:
            if delta.days == 0:
                ddays = f""
            else:
                ddays = f"**`{delta.days}`**`d`"

            if delta.seconds // 3600 == 0 and delta.days == 0:
                dhour = f"**`<1`**`h`"
            elif delta.seconds // 3600 == 0:
                dhour = f""
            else:
                dhour = f"**`{delta.seconds // 3600}`**`h`"

            return f"{'-' if negative else ''}{ddays}{dhour} - `{unix_to_datetime(due_time)}`"

        msg = ""
        for task in task_list:
            link = f"[`{task.id}`](<{task.url}>)"

            due = "At\t"
            if T_ASSIGNMENT in task.tags:
                emoji = "pencil"
                due = "Due "
            elif T_EXAM in task.tags:
                emoji = "scroll"
            elif T_EVENT in task.tags:
                emoji = "jigsaw"
            elif T_MEETING in task.tags:
                emoji = "fire"
            elif T_COURSE in task.tags:
                emoji = "book"
            else:
                emoji = "page_facing_up"

            if T_COURSE in task.tags:
                if task.due_date is not None:
                    due += f"**`{unix_to_time(task.due_date)}`**"
                else:
                    due += "**\"What do you mean the course has no time?\"**"
            else:
                if task.due_date is not None:
                    due += get_timedelta(task.due_date)
                else:
                    due += "**No Due!**"

            msg += (f"- :{emoji}: {due}: {link} {task.name}\n")

        if len(msg) and enable_title:
            msg = header + msg

        return msg

    def parse_tasks(self, start: int = 0, end: int = NUM_BATCH, enable_title: bool = True) -> str:
        data = ClickupData()
        tasks = data.get_tasks()
        tasks.sort(key=lambda x: (0 if x.due_date else 1, x.due_date))

        # Custom logic of categorize tasks
        course: list[ClickupTask] = []
        unreleased: list[ClickupTask] = []
        in_progress: list[ClickupTask] = []
        done: list[ClickupTask] = []
        for task in tasks:
            if T_COURSE in task.tags:
                if datetime.datetime.fromtimestamp(task.due_date).day != datetime.datetime.now().day:
                    continue
                course.append(task)
            elif task.status.type == "open" or task.status.type == "custom":
                # unreleased.append(task)
                in_progress.append(task)
            elif task.status.type == "done":
                done.append(task)

        msg = (self.stringify_tasks(course[start:end],
                                    "## :teacher: Today's Schedule\n", enable_title) +
               # self.stringify_tasks(unreleased[:truncate_num],
               #                      "## :mag: Opened\n") +
               self.stringify_tasks(in_progress[start:end],
                                    "## :chart_with_upwards_trend: In Progress\n", enable_title))
        if msg == "":
            msg = "## :white_check_mark: A Day Off!"

        return msg

    @commands.slash_command()
    async def list_tasks(self, ctx: discord.ApplicationContext, truncate_num: int = NUM_BATCH):
        """
        List all tasks from a user.
        """
        await ctx.defer()
        for i in range(0, truncate_num, NUM_BATCH):
            await ctx.followup.send(self.parse_tasks(i, min(i + NUM_BATCH, truncate_num)))

    @tasks.loop(hours=23.9)
    async def prober(self):
        await asyncio.sleep(max(0, (self.next_reminder - datetime.datetime.now()).total_seconds()))
        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        user = await self.bot.fetch_user(MENTION_ID)
        header = (f"{user.mention}\n" +
                  f"# Daily Reminder {datetime.datetime.now().strftime('%b %d')}\n")
        
        await channel.send(header + self.parse_tasks(0, min(NUM_BATCH, NUM_TRUNC)), suppress=True)
        for i in range(NUM_BATCH, NUM_TRUNC, NUM_BATCH):
            await channel.send(self.parse_tasks(i, min(i + NUM_BATCH, NUM_TRUNC), enable_title=False), suppress=True)
        self.next_reminder = self.next_morning(self.next_reminder)

    @prober.before_loop
    async def before_prober(self):
        await self.bot.wait_until_ready()

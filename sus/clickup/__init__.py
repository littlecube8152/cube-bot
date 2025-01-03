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

NUM_TRUNC = 15
SUBTASK_EXPAND = 3
DISCORD_LIMIT = 2000 - 10


@config_handler.after_load
def __load_config():
    global REPORT_CHANNEL_ID, MENTION_ID
    REPORT_CHANNEL_ID = config_handler.get_configuration(
        "clickup.report_channel_id")
    MENTION_ID = config_handler.get_configuration("clickup.mention_id")


class ClickupCog(commands.Cog):
    # Daily reminder at 7 am
    daily_reminder_time = 7

    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.prober.start()
        self.next_reminder: datetime.datetime = self.next_morning(
            datetime.datetime.now())
        self.data = ClickupData(True)

    @classmethod
    def next_morning(cls, t: datetime.datetime):
        """Produce a datetime for the next moring"""
        clock = ClickupCog.daily_reminder_time
        if t.hour >= clock:
            t += datetime.timedelta(days=1)
        return datetime.datetime(t.year, t.month, t.day, clock, 0, 0, 0)

    def cog_unload(self):
        self.prober.cancel()

    @classmethod
    def stringify_tasks(cls, task_list: list[ClickupTask], header: str, trunc: int = -1) -> list[str]:

        def get_timedelta(due_time: float):
            delta = datetime.datetime.fromtimestamp(
                due_time) - datetime.datetime.now()

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

        msg = []
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

            name = task.name if task.parent_task is None else f"[{task.parent_task.name}] {task.name}"
            msg.append(f"- :{emoji}: {due}: {link} {name}\n")

        if trunc != -1 and len(msg) > trunc:
            remain = len(msg) - trunc
            del msg[trunc:]
            msg.append(f"... and **{remain}** more task(s)\n")

        if len(msg) > 0:
            msg.insert(0, header)

        return msg

    def parse_tasks(self, truncate: int = NUM_TRUNC) -> list[str]:
        self.data.update()
        tasks = self.data.get_expanded_tasks(max_child=SUBTASK_EXPAND)

        tasks.sort(key=lambda x: (0 if x.due_date else 1, x.due_date))

        # Custom logic of categorize tasks
        course: list[ClickupTask] = []
        in_progress: list[ClickupTask] = []

        for task in tasks:
            if T_COURSE in task.tags:
                if datetime.datetime.fromtimestamp(task.due_date).day != datetime.datetime.now().day:
                    continue
                course.append(task)
            elif task.status.type == "open" or task.status.type == "custom":
                in_progress.append(task)

        msg = (self.stringify_tasks(course, header="## :teacher: Today's Schedule\n") +
               self.stringify_tasks(in_progress, header="## :chart_with_upwards_trend: In Progress\n", trunc=truncate))

        if len(msg) == 0:
            msg = ["## :face_with_monocle: :partying_face No tasks? No way!\n"]

        return msg

    @commands.slash_command()
    async def list_tasks(self, ctx: discord.ApplicationContext, truncate: int = NUM_TRUNC):
        """
        List all tasks from a user.
        """
        await ctx.defer()
        task_msg = self.parse_tasks(truncate=truncate)

        current_msg = ""
        for i in range(len(task_msg)):
            # Just to be safe

            if len(current_msg) + len(task_msg[i]) > DISCORD_LIMIT:
                await ctx.followup.send(current_msg)
                current_msg = ""

            current_msg += task_msg[i]

        if current_msg != "":
            await ctx.followup.send(current_msg)

    @tasks.loop(hours=23.9)
    async def prober(self):
        await asyncio.sleep(max(0, (self.next_reminder - datetime.datetime.now()).total_seconds()))

        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        user = await self.bot.fetch_user(MENTION_ID)

        task_msg = [f"{user.mention}\n",
                    f"# Daily Reminder {datetime.datetime.now().strftime('%b %d')}\n"] + self.parse_tasks()
        current_msg = ""
        for i in range(len(task_msg)):
            # Just to be safe

            if len(current_msg) + len(task_msg[i]) > DISCORD_LIMIT:
                await channel.send(current_msg, suppress=True)
                current_msg = ""

            current_msg += task_msg[i]

        if current_msg != "":
            await channel.send(current_msg, suppress=True)

        self.next_reminder = self.next_morning(self.next_reminder)

    @prober.before_loop
    async def before_prober(self):
        await self.bot.wait_until_ready()

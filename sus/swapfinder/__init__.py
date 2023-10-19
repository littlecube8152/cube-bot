from sus.swapfinder.swapfinder import *
from discord.ext import tasks, commands
from discord import client
import time

SCAN_PATH = '/tmp'
REPORT_CHANNEL_ID = 1164606072024207450

class SwapFinderCog(commands.Cog):
    def __init__(self, bot):
        self.sf = VimSwapFileFinder()
        self.bot = bot
        self.prober.start()

    def cog_unload(self):
        self.prober.cancel()

    @tasks.loop(minutes=5.0)
    async def prober(self):
        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        flist = self.sf.scan_directory(SCAN_PATH)
        self.sf.update_time()
        for filename, size, owner, last_modify, preview in flist:
            await channel.send(f'`{owner}` did some unprotected edit with swap file `{filename}` at time `{str(last_modify)}`:\n```{preview}```')
            time.sleep(0.200) # sleep 0.2s to prevent too much input

    @prober.before_loop
    async def before_printer(self):
        await self.bot.wait_until_ready()
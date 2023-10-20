from sus.swapfinder.swapfinder import *
from sus.basiclib import *
from sus.idfinder import StudentIDFinder as sidf
from discord.ext  import tasks, commands
import time

SCAN_PATH = '/tmp'
REPORT_CHANNEL_ID = 1164606072024207450
MAX_PREVIEW_SIZE = 1024 * 1024 * 8   # 8 MB

class SwapFinderCog(commands.Cog):
    def __init__(self, bot):
        self.sf = VimSwapFileFinder()
        self.bot = bot
        self.prober.start()

    def cog_unload(self):
        self.prober.cancel()

    @commands.slash_command()
    async def scan_tmp(self, ctx):
        """
        Perform a scan.
        """
        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        flist = self.sf.scan_directory(SCAN_PATH, True)
        self.sf.update_time()
        await ctx.respond(f"Found {len(flist)} unprotected edit.")
        for filename, size, owner, last_modify, preview in flist:
            await channel.send(f'`{owner}` did some unprotected edit with swap file `{filename}` (size `{convert_bytes(size)}`) at time `{str(last_modify)}`:', file=preview.name)
            preview.close()
            time.sleep(0.200) # sleep 0.2s to prevent too much input

    @tasks.loop(minutes=5.0)
    async def prober(self):
        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        flist = self.sf.scan_directory(SCAN_PATH)
        self.sf.update_time()
        for filename, size, owner, last_modify, preview in flist:
            await channel.send(f'`{owner}`(``) did some unprotected edit with swap file `{filename}` (size `{convert_bytes(size)}`) at time `{str(last_modify)}`:\n```{preview}```')
            time.sleep(0.200) # sleep 0.2s to prevent too much input

    @prober.before_loop
    async def before_prober(self):
        await self.bot.wait_until_ready()
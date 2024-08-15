from   sus.swapfinder.swapfinder import *
from   sus.basiclib import *
from   sus.config import config_handler
from   sus.idfinder import StudentIDFinder as sidf
from   discord.ext  import tasks, commands
import time
import discord

# Define and load configurations

SCAN_PATH, REPORT_CHANNEL_ID, MAX_PREVIEW_SIZE = None, None, None
@config_handler.after_load
def __load_config():
    global SCAN_PATH, REPORT_CHANNEL_ID, MAX_PREVIEW_SIZE
    SCAN_PATH =         config_handler.get_configuration("swapfinder.scan_path")
    REPORT_CHANNEL_ID = config_handler.get_configuration("swapfinder.report_channel_id")
    MAX_PREVIEW_SIZE =  config_handler.get_configuration("swapfinder.max_preview_size")   

# Integration with discord

class SwapFinderCog(commands.Cog):
    def __init__(self, bot):
        self.sf = VimSwapFileFinder()
        self.bot = bot
        self.prober.start()

    def cog_unload(self):
        self.prober.cancel()

    @commands.slash_command()
    async def scan_tmp(self, ctx: discord.ApplicationContext, delay_hour: int = 1):
        """
        Perform a scan. Default find by time delayed by 1 hour.
        """
        await ctx.defer()
        
        self.sf.update_time(datetime.datetime.now() - datetime.timedelta(hours=delay_hour))
        flist = self.sf.scan_directory(SCAN_PATH, True)
        self.sf.update_time()

        await ctx.followup.send(f"Found {len(flist)} unprotected edit.")
        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        
        for filename, size, owner, last_modify, preview in flist:
            if size < MAX_PREVIEW_SIZE:
                await channel.send(f'`{owner}` did some unprotected edit with swap file `{filename}` (size `{convert_bytes(size)}`) at time `{str(last_modify)}`:', file=discord.File(preview.name, filename=filename[:-4]))
            else:
                await channel.send(f'`{owner}` did some unprotected edit with swap file `{filename}` (size `{convert_bytes(size)}`) at time `{str(last_modify)}`. File is too huge.')
            preview.close()
            time.sleep(0.200) # sleep 0.2s to prevent too much input

    @tasks.loop(minutes=5.0)
    async def prober(self):
        channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        flist = self.sf.scan_directory(SCAN_PATH)
        self.sf.update_time()
        for filename, size, owner, last_modify, preview in flist:
            if preview == '': # prevent weird display error
                preview = '\n'
            await channel.send(f'`{owner} ({sidf.query_id(owner)})` did some unprotected edit with swap file `{filename}` (size `{convert_bytes(size)}`) at time `{str(last_modify)}`:\n```{preview}```')
            time.sleep(0.200) # sleep 0.2s to prevent too much input

    @prober.before_loop
    async def before_prober(self):
        await self.bot.wait_until_ready()
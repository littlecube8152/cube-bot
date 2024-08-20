import json
import psutil
import discord
import datetime
import sus.config
from   sus.config import config_handler
import sus.idfinder
import sus.swapfinder
from   sus.basiclib import *
import sus.clickup

token = None

@config_handler.after_load
def __load_config():
    global token
    token =  config_handler.get_configuration("token")

bot = discord.Bot()
start_time = datetime.datetime.now()

def lazy_embed(title, color, section_list = {}, description = None, inline = True):

    embed = discord.Embed (
        title=title,
        description=description,
        color=color,
        timestamp=datetime.datetime.now()
    )

    for section, content in section_list.items():
        embed.add_field(name=section, value=content, inline=inline)
        
    embed.set_author(name=bot.user.display_name, icon_url=bot.user.display_avatar.url)

    return embed

@bot.slash_command()
async def hello(ctx, name: str = None):
    """
    Say hello. Testing.
    """
    name = name or ctx.author.name
    await ctx.respond(f"Hello {name}!")

@bot.slash_command()
async def delete(ctx: discord.ApplicationContext, count: int = 0):
    """
    Delete messages.
    """
    if ctx.author.id == 582151572646133770:
        reply = await ctx.respond(f"Deleting...", ephemeral=True)
        deleted = 0
        async for msg in ctx.channel.history(limit=count, before=ctx.message):
            deleted += 1
            await msg.delete()
        await reply.edit_original_response(content=f"Deleted **{deleted}** message(s). Shhhh!", delete_after=5.0)
    else:
        await ctx.respond(f"You don't have permission to invoke this dangerous command.", ephemeral=True, delete_after=5.0)

@bot.slash_command()
async def botstat(ctx):

    bot_process = psutil.Process()
    with bot_process.oneshot():
        cpu = bot_process.cpu_percent()
        threads = bot_process.num_threads()
        meminfo = bot_process.memory_full_info()
        rss = meminfo.rss
        vms = meminfo.vms
        uss = meminfo.uss
        nice = bot_process.nice()
        
    total_cpu = psutil.cpu_count()
    total_mem = psutil.virtual_memory().total

    embed = lazy_embed("Bot Status",
                       discord.Colour.dark_blue(),
                       section_list=
                       {"CPU": 
                            f"`{cpu} / {total_cpu}`",
                        "Threads": 
                            f"`{threads}`",
                        "Uptime": 
                            f"`{convert_time((datetime.datetime.now() - start_time).total_seconds())}`",
                        "Nice": 
                            f"`{nice}`",
                        "Memory (RSS, VMS, USS)": 
                            f"`{convert_bytes(rss)}, {convert_bytes(vms)}, {convert_bytes(uss)} / {convert_bytes(total_mem)}`",
                        "Latency":
                            f"`{bot.latency * 1000:.2f}ms`"
                        })
    
    await ctx.respond(embed=embed)

def load_module(module: discord.Cog):
    print(f"Load module {module.__cog_name__}...")
    bot.add_cog(module(bot))
    for c in module.get_commands(module):
        print(f"Registered command {c.name}")

def main():
    config_handler.load()
    load_module(sus.swapfinder.SwapFinderCog)
    load_module(sus.idfinder.StudentIDCog)
    load_module(sus.clickup.ClickupCog)
    print(f"Running bot on token {token[:5]}...{token[-5:]}")
    bot.run(token)

if __name__ == '__main__':
    main()
import json
import psutil
import discord
import datetime
import math
import subprocess
import re

token = ""
bot = discord.Bot()
start_time = datetime.datetime.now()

# Opening Token JSON file
def load_token():
    global token
    token_file = open('config.json')
    token = json.load(token_file)['token']
    token_file.close()

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

def convert_bytes(n):
    prefix = ['', 'K', 'M', 'G', 'T']
    for i in reversed(range(len(prefix))):
        if n >= 1 << (10 * i):
            return "%.2f %sB" % (float(n) / (1 << (10 * i)), prefix[i])

def convert_time(t):
    unit = ['ms', 's', 'm', 'h', 'd']
    ratio = [0.001, 1, 60, 60 * 60, 24 * 60 * 60]
    for i in reversed(range(1, len(unit))):
        if t >= ratio[i]:
            first = math.floor(t / ratio[i])
            t = t - ratio[i] * first
            second = round(t / ratio[i - 1])
            return "%d%s %d%s" % (first, unit[i], second, unit[i - 1])

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

@bot.slash_command()
async def get_name(ctx, student_id: str = None):
    """
    Get a given name of id by ldap on workstation.
    """
    embed = discord.Embed (
        title="Bot Status",
        color=discord.Colour.dark_blue(),
        timestamp=datetime.datetime.now()
    )
    embed = discord.Embed (
        title="Bot Status",
        color=discord.Colour.dark_blue(),
        timestamp=datetime.datetime.now()
    )
    if re.match(r"^[br][0-9]{8}$", student_id):
        res = subprocess.run(["gn", student_id], capture_output=True)
        print(f"Query {student_id}: exit code {res.returncode}, stderr {res.stderr}, stdout {res.stdout}")

        if res.returncode != 0:
            await ctx.respond(f"Error! Process exited with code `{res.returncode}`")
        else:
            name = "Not found" if res.stdout == b"" else res.stdout.decode()
            await ctx.respond(f"`{student_id}` → `{name}`")
    else:
        await ctx.respond(f"Error! ID is not valid.")


def main():
    load_token()
    print(f"Running bot on token {token[:5]}...{token[-5:]}")
    bot.run(token)

if __name__ == '__main__':
    main()
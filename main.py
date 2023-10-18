import json
import psutil
import discord

token = ""
bot = discord.Bot()

# Opening Token JSON file
def load_token():
    global token
    token_file = open('token.json')
    token = json.load(token_file)['token']
    token_file.close()


@bot.slash_command()
async def hello(ctx, name: str = None):
    name = name or ctx.author.name
    await ctx.respond(f"Hello {name}!")

@bot.slash_command()
async def botstat(ctx):
    await ctx.respond(f"WIP")

def main():
    load_token()
    print(f"Running bot on token {token[:5]}...{token[-5:]}")
    bot.run(token)

if __name__ == '__main__':
    main()
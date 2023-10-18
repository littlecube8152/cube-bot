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
async def botstat(ctx, name: discord.Option(discord.SlashCommandOptionType.user)):
    await ctx.respond(f"WIP")

def main():
    load_token()
    bot.run(token)

if __name__ == '__main__':
    main()
import discord

import utils.botconfig as cfg

initial_extensions = ['apps', 'games', 'music', 'tasks', 'utilities']
intents = discord.Intents.all()
client = discord.Bot(description='A bot that does things.', allowed_mentions=discord.AllowedMentions(
                         users=False, everyone=False, roles=False, replied_user=True), intents=intents)

if __name__ == '__main__':
    for extension in initial_extensions:
        client.load_extension('cogs.' + extension)

bottype = input("1 for Noyabot, 2 for Noyadev: ")
tokens = {1: cfg.main_token, 2: cfg.dev_token}
client.run(tokens[int(bottype)])

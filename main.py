import discord

initial_extensions = ['games', 'music', 'stats', 'tasks', 'utilities']
intents = discord.Intents.all()
client = discord.Bot(description='A bot that does things.', allowed_mentions=discord.AllowedMentions(
                         users=False, everyone=False, roles=False, replied_user=True), intents=intents)

if __name__ == '__main__':
    for extension in initial_extensions:
        client.load_extension('cogs.' + extension)

bottype = input("1 for Noyabot, 2 for Noyadev: ")
tokens = {1: "main_token",
          2: "dev_token"}

client.run(tokens[int(bottype)])

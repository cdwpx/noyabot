import time
import traceback

import discord
from discord.ext import commands, tasks
from tinydb import TinyDB, Query

import utils.botconfig as cfg


class Tasks(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Starting bot as {self.client.user}... (ID: {self.client.user.id})\nCreated by Cic1e')
        self.presence_loop.start()
        self.remind_check.start()
        print('Ready!')

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if hasattr(ctx.command, 'on_error'):
            return
        cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return
        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandOnCooldown):
            num = round(error.retry_after) + int(time.time())
            await ctx.respond(f"{cfg.error} This command is on cooldown! Try again <t:{num}:R>", ephemeral=True)
        elif isinstance(error, discord.HTTPException):
            ez = int(error.status)
            if ez == 400:  # not always true
                await ctx.respond(f"{cfg.error} This message is over 2,000 characters!", ephemeral=True)
            elif ez == 403:
                await ctx.respond(f"{cfg.error} Do I have enough permissions?", ephemeral=True)
            else:
                pass
        elif isinstance(error, commands.NotOwner):
            await ctx.respond(f"{cfg.error} Sorry bucko, only my creator can do that >:)", ephemeral=True)
        else:
            embed = discord.Embed(title="Uh oh, an error!", description=f"```\n{error}```", color=discord.Color.red())
            embed.set_footer(text="Error info has been sent")
            await ctx.respond(embed=embed, ephemeral=True)
            msg = ''.join(traceback.format_exception(error.__class__, error, error.__traceback__))
            echannel = self.client.get_channel(cfg.discorderrorchannel)
            msg2 = f'```\n{msg}```'
            if len(msg2) > 4096:
                msg2 = '```\nUh oh, this error is too large. Check the console for more details```'
                print(msg)
            errorbed = discord.Embed(title=f"Error: /{ctx.command}", description=f"{msg2}", color=discord.Color.red())
            errorbed.set_footer(text=f"User: {ctx.interaction.user}\nGuild: {ctx.interaction.guild}")
            await echannel.send(embed=errorbed)

    @tasks.loop(minutes=10)
    async def presence_loop(self):
        await self.client.change_presence(
            status=discord.Status.online, activity=discord.Game(f"in {len(self.client.guilds)} servers"))

    @tasks.loop(seconds=1)
    async def remind_check(self):
        db = TinyDB('data/remind.json')
        query = Query()
        results = db.search(query.time < int(time.time()))
        db.remove(query.time < int(time.time()))
        for r in results:
            channel = self.client.get_channel(r.get('channel'))
            user = self.client.get_user(r.get('user'))
            msg = "... well, you didn't say" if not r.get('message') else r.get('message')
            m = discord.AllowedMentions(users=[user])
            try:
                await channel.send(f"Hey {user.mention}! You wanted me to remind you about {msg}", allowed_mentions=m)
            except:
                pass


def setup(client):
    client.add_cog(Tasks(client))

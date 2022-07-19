import discord
from discord import user_command
from discord.ext import commands

from cogs.utilities import StatButtons


class Apps(commands.Cog):  # cmds that don't really fit in any of the other categories

    def __init__(self, client):
        self.client = client

    @user_command(name="Get user stats")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def stats_cmd(self, ctx, user: discord.Member):
        guildcheck = True if ctx.guild else False
        embed = StatButtons.user_embed(user, guildcheck)
        await ctx.respond(embed=embed, ephemeral=True)


def setup(client):
    client.add_cog(Apps(client))

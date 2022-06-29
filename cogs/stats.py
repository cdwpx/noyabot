import discord
from discord import slash_command, Option
from discord.ext import commands

import utils.botconfig as cfg


def user_embed(user, guildcheck):
    bi = int(user.created_at.timestamp())
    if not guildcheck:
        embed = discord.Embed(title=f"Stats | {user}", color=discord.Color.dark_grey())
        embed.add_field(name="__Created__", value=f"<t:{bi}:D>\n(<t:{bi}:R>)", inline=False)
    else:
        jo = int(user.joined_at.timestamp())
        r = len(user.roles) - 1
        other = [f"{r} Role" if r == 1 else f"{r} Roles"]
        embed = discord.Embed(title=f"Stats | {user}", color=user.color)
        embed.add_field(name="__Created__", value=f"<t:{bi}:D>\n(<t:{bi}:R>)", inline=True)
        embed.add_field(name="__Joined__", value=f"<t:{jo}:D>\n(<t:{jo}:R>)", inline=True)
        if user.premium_since:
            other.append(f"Boosting since <t:{user.premium_since.timestamp()}:D>")
        embed.add_field(name="__Other Info__", value="\n".join(other), inline=False)
    embed.set_thumbnail(url=f"{user.display_avatar}")
    embed.set_footer(text=f"ID: {user.id}")
    return embed


def guild_embed(guild):
    bi = int(guild.created_at.timestamp())
    other = []
    numbers = [len(guild.categories), len(guild.channels), len(guild.threads), len(guild.roles) - 1, len(guild.emojis)]
    key = ["Category", "Channel", "Thread", "Role", "Emote"]
    for n, k in zip(numbers, key):
        if n == 1:
            other.append(f"{n} {k}")
        else:
            k = k + 's' if k != "Category" else "Categories"
            other.append(f"{n} {k}")
    desc = str(guild.description).strip()
    embed = discord.Embed(title=f"Stats | {guild.name}", color=cfg.embed_color, description=f"{desc}")
    embed.add_field(name="__Birthday__", value=f"<t:{bi}:D>\n(<t:{bi}:R>)", inline=True)
    embed.add_field(name="__Verification__", value=f"{str(guild.verification_level).capitalize()}", inline=True)
    embed.add_field(name="__Members__", value=f"{guild.member_count}", inline=True)
    embed.add_field(name="__Other Info__", value=", ".join(other), inline=False)
    embed.set_thumbnail(url=f"{guild.icon}")
    embed.set_footer(text=f"ID: {guild.id}")
    return embed


class StatButtons(discord.ui.View):

    def __init__(self, *items, user):
        super().__init__(*items)
        self.user = user

    @discord.ui.button(label="User", style=discord.ButtonStyle.green)
    async def user(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = user_embed(self.user, True)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Server", style=discord.ButtonStyle.blurple)
    async def server(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = guild_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed)


class Stats(commands.Cog):

    def __init__(self, client):
        self.client = client

    @slash_command(description="Get stats for various discord stuff")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def stats(self, ctx,
                    member: Option(discord.Member, description="Select a user", required=False, default=None),
                    hidden: Option(bool, description="Show results to only yourself?", required=False, default=None)):
        if ctx.guild:
            user = member or ctx.author
            if not ctx.guild.get_member(user.id):
                return await ctx.respond(f"{cfg.error} I can't find this member!", ephemeral=True)
            view = StatButtons(user=user)
            embed = user_embed(user, True)
        else:
            view = None
            embed = user_embed(ctx.author, False)
        await ctx.respond(embed=embed, view=view, ephemeral=hidden)


def setup(client):
    client.add_cog(Stats(client))

import discord
from discord import slash_command, Option
from discord.ext import commands

freeoptions = [["YouTube", "Watch videos together!"], ["Betrayal.io", "Among Us Clone"],
               ["Fishington.io", "Epic fishing game"], ["Word Snack", "Make words from a few letters"],
               ["Sketch Heads", "Drawing game"]]
premiumoptions = [["Poker", "Poker night!"], ["Chess", "Play some chess!"], ["Checkers", "Play some checkers!"],
                  ["Letter League", "Scrabble clone"], ["SpellCast", "Another scrabble clone"],
                  ["Awkword", "Create sentences with friends"], ["Blazing 8s", "Card game like Crazy Eights"],
                  ["Land-io", "Claim territory by making trails"], ["Putt Party", "Golf game with powerups"],
                  ["Bobble League", "Turn-based soccer"]]
keys = {"YouTube": 880218394199220334, "Betrayal.io": 773336526917861400, "Fishington.io": 814288819477020702,
        "Word Snack": 879863976006127627, "Sketch Heads": 902271654783242291, "Poker": 755827207812677713,
        "Chess": 832012774040141894, "Checkers": 832013003968348200, "Letter League": 879863686565621790,
        "SpellCast": 852509694341283871, "Awkword": 879863881349087252, "Blazing 8s": 832025144389533716,
        "Land-io": 903769130790969345, "Putt Party": 945737671223947305, "Bobble League": 947957217959759964}


class AcSelect(discord.ui.Select):
    def __init__(self, channel, author, prem):
        self.channel = channel
        self.author = author
        self.prem = prem

        options = []
        for activity in freeoptions:
            name = activity[0]
            desc = activity[1]
            options.append(discord.SelectOption(label=f"{name}", description=f"{desc}"))
        if self.prem:
            for activity in premiumoptions:
                name = activity[0]
                desc = activity[1]
                options.append(discord.SelectOption(label=f"{name}", description=f"{desc}"))
        super().__init__(placeholder="Pick an activity!", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return await interaction.response.send_message("<:n_no:987886730625560626> Invalid user!", ephemeral=True)
        selection = self.values[0]
        activityid = keys[selection]
        invite = await self.channel.create_activity_invite(activity=activityid, max_age=3600)
        await interaction.response.edit_message(content=f"{invite}", view=None)


class Games(commands.Cog):

    def __init__(self, client):
        self.client = client

    @slash_command(description="Get stats for various discord stuff")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def activity(self, ctx,
                       channel: Option(discord.VoiceChannel, description="Where do you want the invite?",
                                       required=True, default=None)):
        if not channel:
            return await ctx.respond(f"<:n_no:987886730625560626> You must specify a channel!", ephemeral=True)
        prem = True if ctx.guild.premium_tier != 0 else False
        view = discord.ui.View()
        view.add_item(AcSelect(channel, ctx.author, prem))
        await ctx.respond(view=view)


def setup(client):
    client.add_cog(Games(client))

import operator
import random
import re
import time
from functools import reduce
from random import randint

import discord
from discord import slash_command, Option
from discord.ext import commands
from tinydb import TinyDB

from utils.time import timey_whimy

ops = {'+': operator.add, '-': operator.sub, '*': operator.mul, '/': operator.truediv}
rtime = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'n': 2592000, 'y': 31536000}

Time = time


class Utilities(commands.Cog):

    def __init__(self, client):
        self.client = client

    @slash_command(description="Roll some dice")
    @commands.cooldown(3, 5, commands.BucketType.user)
    async def roll(self, ctx, *, amount: Option(str, "Available formats: 20, d20, 2d20, 2d20+5, etc", required=False)):
        if amount is None:
            amount = "20"
        opslist = ['+', '-', '*', '/']
        splits = re.split('([^a-zA-Z0-9])', amount.replace(" ", ""))
        a = splits[::2]  # ndn
        b = splits[1::2]  # operators
        cal = []  # total from values
        val = []  # random rolls
        final = []
        check = False
        checkerror = False
        for x in a:
            e = [int(s) for s in re.findall(r'\d+', x)]
            try:
                if len(e) > 1:
                    diceo = e[0]
                    valueo = e[1]
                else:
                    diceo = 1
                    valueo = e[0]
            except IndexError:
                return await ctx.respond(
                    "<:n_no:987886730625560626> Dice not in correct format! Use `n`, `dn`, or `ndn`", ephemeral=True)
            dice = min(max(abs(diceo), 1), 999)
            value = min(max(abs(valueo), 1), 999999999)
            if dice != diceo or value != valueo:
                checkerror = True
            if dice == 1:
                if x.isdigit() and check is True:
                    cal.append(int(x))
                    val.append(int(x))
                else:
                    numbers = randint(1, value)
                    cal.append(numbers)
                    val.append(numbers)
            else:
                numbers = [randint(1, value) for x in range(dice)]
                total = reduce(lambda q, p: p + q, numbers)
                cal.append(total)
                val.append(str(tuple(numbers)))
            check = True
        tot = cal[0]
        for c, o in zip(cal[1:], b):
            if not any(o in s for s in opslist):
                return await ctx.respond(
                    "<:n_no:987886730625560626> Can't use this operator, you need to use `+, -, *, or /`",
                    ephemeral=True)
            else:
                try:
                    tot = ops[o](tot, int(c))
                except ZeroDivisionError or OverflowError:
                    return await ctx.respond(
                        "<:n_no:987886730625560626> I had trouble calculating this roll! Try again, maybe?",
                        ephemeral=True)
        final.append(f"**{round(tot, 2)}!**")
        if tot == cal[0] == val[0]:
            pass
        else:
            j = cal[0]
            try:
                k = val[0].replace("(", "").replace(")", "")
                final.append(f"({k} = {j})")
            except AttributeError:
                final.append(f"{j}")
        for c, k, o in zip(cal[1:], val[1:], b):
            if c == k:
                final.extend([o, f"{c}"])
            else:
                v = k.replace("(", "").replace(")", "")
                final.extend([o, f"({v} = {c})"])
        msg = " ".join(final)
        if len(msg) > 2000:
            await ctx.respond(f"You rolled **{round(tot, 2)}!**")
        else:
            await ctx.respond(f"You rolled {msg}")
        if checkerror:
            await ctx.respond("<:n_no:987886730625560626> One or more of your numbers was higher "
                              "than 999d999999999, so it was automatically lowered", ephemeral=True)

    @slash_command(description="Set a reminder for later")
    @commands.cooldown(3, 5, commands.BucketType.user)
    async def remind(self, ctx,
                     time: Option(str, description="Examples: 5m, 5 minutes, 5m3s", required=False, default="5m"),
                     message: Option(str, description="What am I reminding you?", required=False),
                     hidden: Option(bool, description="Should the confirmation message be private?",
                                    required=False, default=False)):
        splits = re.findall('(\d+|[A-Za-z]+)', time.replace(" ", "").lower())
        a = splits[::2]  # values
        b = splits[1::2]  # modifiers
        c = []  # finalized modifiers
        timein = 0
        for x in b:
            if 'month' in x:
                c.append('n')
            else:
                c.append(x[0])
        for value, modifier in zip(a, c):
            try:
                calc = rtime[modifier]
                tget = int(value) * calc
            except:
                return await ctx.respond("<:n_no:987886730625560626> Woah, I don't recognize that time. I can do "
                                         "'5 minutes', or '5 minutes 3 seconds', or '5m3s'", ephemeral=True)
            timein += tget
        timeout = min(max(abs(timein), 1), 315360000)
        totime = timeout + int(Time.time())
        data = {'time': totime, 'channel': ctx.channel.id, 'user': ctx.author.id, 'message': message}
        db = TinyDB('data/remind.json')
        db.insert(data)
        if message:
            await ctx.respond(f"You got it, I'll remind you about `{message}` in {timey_whimy(timeout)}...",
                              ephemeral=hidden)
        else:
            await ctx.respond(f"You got it, I'll remind you in {timey_whimy(timeout)}...", ephemeral=hidden)

    @slash_command(description="Mention a random person")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def someone(self, ctx,
                      role: Option(discord.Role, description="Filter members by role", required=False, default=None)):
        if not ctx.guild:
            return await ctx.respond(f"That someone is you!")
        init_memberlist = await ctx.guild.fetch_members(limit=1000).flatten()
        if role:
            memberlist = []
            for member in init_memberlist:
                if role in member.roles:
                    memberlist.append(member)
        else:
            memberlist = init_memberlist
        get_member = random.choice(memberlist)
        m = discord.AllowedMentions(users=[get_member])
        await ctx.respond(f"{get_member.mention}", allowed_mentions=m)


def setup(client):
    client.add_cog(Utilities(client))

import ast
import operator
import random
import re
import time as timey
from functools import reduce
from random import randint
from typing import Union

import discord
from discord import slash_command, Option
from discord.ext import commands

import utils.botconfig as cfg
from utils.database import RemindBase

ops_map = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
           ast.Invert: operator.neg}
rtime = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'n': 2592000}


class Calculate(ast.NodeVisitor):

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return ops_map[type(node.op)](left, right)

    def visit_Num(self, node):
        return node.n

    def visit_Expr(self, node):
        return self.visit(node.value)

    @classmethod
    def evaluate(cls, expression):
        tree = ast.parse(expression)
        calc = cls()
        return calc.visit(tree.body[0])


class Utilities(commands.Cog):

    def __init__(self, client):
        self.client = client

    @slash_command(description="Roll some dice")
    @commands.cooldown(3, 5, commands.BucketType.user)
    async def roll(self, ctx, *, amount: Option(str, "Examples: 20, d20, 2d20, 2d20+5, etc", required=False)):
        amt = '1d20' if not amount else amount
        calcthis = amt.replace(" ", "")  # iteration of amount that will instead be used for final calculations
        rolls = re.findall(r'(\d*[a-zA-Z]\d+)', amt)  # find the NdN's in a roll
        checkerror = False  # check if rolls got nerfed
        for dice in rolls:
            splits = re.findall(r'(\d+)', dice)
            try:
                val = 1 if not splits[0] else int(splits[0])
                sid = int(splits[1])
                value = min(max(abs(val), 1), 999)  # d20 -> 1d20
                sides = min(max(abs(sid), 1), 999999999)
                if value < val or sides < sid:
                    checkerror = True  # numbers are nerfed because hoo boy, randomizing high numbers is LAGGY
            except (ValueError, IndexError):
                return await ctx.respond(f"{cfg.error} Dice not in correct format! Use `n`, `dn`, or `ndn`",
                                         ephemeral=True)
            numbers = [randint(1, sides) for x in range(value)]
            formatnumbers = f"{numbers}".replace('[', '').replace(']', '')
            total = reduce(lambda q, p: p + q, numbers)
            if formatnumbers == str(total):
                amt = amt.replace(dice, f"[{total}]", 1)
            else:
                amt = amt.replace(dice, f"[{formatnumbers} = {total}]", 1)
            calcthis = calcthis.replace(dice, f"{total}", 1)
        calcthis = re.sub(r'([\d)])(\()', r"\1*\2", calcthis)  # add * to parenthesis such as 2(5) or (5)(5)
        try:
            result = Calculate.evaluate(calcthis)
        except (ZeroDivisionError, OverflowError, TypeError, SyntaxError, KeyError) as e:
            #  print(f"-----\nString: {amount}\nCalculation: {calcthis}\nErrortype: {e}")
            return await ctx.respond(f"{cfg.error} I had trouble calculating this roll! Try again, maybe?",
                                     ephemeral=True)
        characters = "-+*/"
        for char in characters:
            amt = amt.replace(char, f" {char} ")  # provides spacing for better readability
        msg = f"You rolled **{result}!** {amt}"
        if not result:  # you rolled none!
            return await ctx.respond(f"{cfg.error} Invalid result! (null) Try again?", ephemeral=True)
        elif len(msg) > 2000 or f"[{result}]" == amt:  # simplify message if either too long, or redundant
            msg = f"You rolled **{result}!**"
        elif amount == str(result):  # for basic rolls, like /roll 20
            simpleroll = randint(1, min(int(result), 1))
            msg = f"You rolled **{simpleroll}!**"
        await ctx.respond(msg)
        if checkerror:
            await ctx.respond(f"{cfg.error} One or more of your rolls was higher than 999d999999999, so it was "
                              f"automatically lowered", ephemeral=True)

    @slash_command(description="Set a reminder for later")
    @commands.cooldown(2, 8, commands.BucketType.user)
    async def remind(self, ctx,
                     time: Option(str, description="Examples: 5m, 5 minutes, 5m3s", required=False, default="5m"),
                     message: Option(str, description="What am I reminding you?", required=False),
                     hidden: Option(bool, description="Should the confirmation message be private?",
                                    required=False, default=False)):
        if message and len(message) > 1950:
            return await ctx.respond(f"{cfg.error} This message is too long!", ephemeral=True)
        splits = re.findall(r'(\d+|[A-Za-z]+)', time.replace(" ", "").lower())
        values = splits[::2]  # the amount of time
        modifiers = splits[1::2]  # type of time (eg. s for seconds)
        finalmods = []  # finalized modifiers
        timein = 0
        for x in modifiers:
            if 'month' in x:
                finalmods.append('n')  # use 'n' for months because minutes already uses 'm'
            else:
                finalmods.append(x[0])
        for value, modifier in zip(values, finalmods):
            try:
                calc = rtime[modifier]
                tget = int(value) * calc
            except (ValueError, KeyError):
                return await ctx.respond(f"{cfg.error} Woah, I don't recognize that time. I can do '5 minutes', "
                                         f"or '5 minutes 3 seconds', or '5m3s'", ephemeral=True)
            timein += tget
        timeout = min(max(abs(timein), 1), 31557600)
        totime = timeout + int(timey.time())
        RemindBase.insert_reminder(time=totime, channel=ctx.channel.id, user=ctx.user.id, msg=message)
        await ctx.respond(f"{cfg.success} Sure thing, I'll remind you <t:{totime}:R>", ephemeral=hidden)

    @slash_command(description="Mention a random person")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def someone(self, ctx,
                      channel: Option(Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel],
                                      description="Filter members by channel", required=False),
                      role: Option(discord.Role, description="Filter members by role", required=False)):
        if not ctx.guild:
            return await ctx.respond("That someone is you!")
        if channel:
            init_memberlist = channel.members
        else:
            init_memberlist = await ctx.guild.fetch_members(limit=1000).flatten()
        if role:
            memberlist = []
            for member in init_memberlist:
                if role in member.roles:
                    memberlist.append(member)
        else:
            memberlist = init_memberlist
        if not memberlist:
            return await ctx.respond(f"{cfg.error} Nobody to ping!", ephemeral=True)
        get_member = random.choice(memberlist)
        m = discord.AllowedMentions(users=[get_member])
        await ctx.respond(f"{get_member.mention}", allowed_mentions=m)


def setup(client):
    client.add_cog(Utilities(client))

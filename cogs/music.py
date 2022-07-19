import re
import time
from typing import Union

import discord
import lavalink
from discord import slash_command, Option
from discord.ext import commands

import utils.botconfig as cfg

RURL = re.compile(r'https?://(?:www\.)?.+')


def create_embed(track, position):
    pos = time.strftime('%H:%M:%S', time.gmtime(int(position / 1000)))
    dur = time.strftime('%H:%M:%S', time.gmtime(int(track.duration / 1000)))
    embed = discord.Embed(title=f"{track.title}", description=f"*{track.author}*", color=cfg.embed_color)
    embed.add_field(name="__Position__", value=f"{pos}/{dur}", inline=True)
    embed.add_field(name="__Video URL__", value=f"[Click here!]({track.uri})", inline=False)
    embed.set_footer(text=f"Requested by {track.requester}")
    return embed


def confirmation(message):
    embed = discord.Embed(title=cfg.success + f" {message}", color=cfg.embed_color)
    return embed


async def cleanup(player):
    player.queue.clear()
    await player.stop()


class Player(discord.VoiceClient):

    def __init__(self, client: discord.Client, channel: Union[discord.VoiceChannel, discord.StageChannel]):
        super().__init__(client, channel)
        self.client = client
        self.channel = channel
        if hasattr(self.client, 'lavalink'):
            self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        lavalink_data = {'t': 'VOICE_SERVER_UPDATE', 'd': data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        lavalink_data = {'t': 'VOICE_STATE_UPDATE', 'd': data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False,
                      self_mute: bool = False) -> None:
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        player = self.lavalink.player_manager.get(self.channel.guild.id)
        if not force and not player.is_connected:
            return
        await self.channel.guild.change_voice_state(channel=None)
        player.channel_id = None
        self.cleanup()


class SongSelect(discord.ui.Select):
    def __init__(self, client, tracks, requester):
        self.client = client
        self.tracks = tracks
        self.requester = requester
        self.keys = {}

        options = []
        for track in self.tracks:
            options.append(discord.SelectOption(label=f"{track.title}", description=f"By {track.author}"))
            self.keys[f'{track.title}'] = track
        super().__init__(placeholder="Pick a song!", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.requester:
            return await interaction.response.send_message(f"{cfg.error} Invalid user!", ephemeral=True)
        selection = self.values[0]
        song = self.keys[f"{selection}"]
        info = song['info']
        await interaction.response.edit_message(embed=confirmation(f"Adding {info['title']} to the player"), view=None)
        player = self.client.lavalink.player_manager.get(interaction.guild.id)
        player.add(track=song, requester=self.requester.id)
        if not player.is_playing:
            await player.play()


class Queue(discord.ui.View):

    def __init__(self, client, queue, length):
        super().__init__()
        self.client = client
        self.queue = queue
        self.length = length
        self.position = 0
        self.max = len(queue[::10]) - 1

    @discord.ui.button(label="Previous 10", style=discord.ButtonStyle.gray)
    async def queue_prev(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.position -= 1
        if self.position == 0:
            button.disabled = True
        if self.children[2].disabled:
            self.children[2].disabled = False
        page = 10 * self.position
        songlist = []
        count = 1
        for song in self.queue[page:page + 10]:
            songlist.append(f"**{count + page}:** `{song}`")
            count += 1
        embed = discord.Embed(title="Upcoming Songs", description=f"\n".join(songlist), color=cfg.embed_color)
        embed.set_footer(text=f"{(10 * self.position - 1) + count} of {len(self.queue)} songs - {self.length}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Go Back", style=discord.ButtonStyle.red)
    async def queue_return(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.client.lavalink.player_manager.get(interaction.guild.id)
        embed = create_embed(player.current, player.position)
        await interaction.response.edit_message(embed=embed, view=Buttons(self.client))

    @discord.ui.button(label="Next 10", style=discord.ButtonStyle.gray)
    async def queue_next(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.position += 1
        if self.position == self.max:
            button.disabled = True
        if self.children[0].disabled:
            self.children[0].disabled = False
        page = 10 * self.position
        songlist = []
        count = 1
        for song in self.queue[page:page + 10]:
            songlist.append(f"**{count + page}:** `{song}`")
            count += 1
        embed = discord.Embed(title="Upcoming Songs", description=f"\n".join(songlist), color=cfg.embed_color)
        embed.set_footer(text=f"{(10 * self.position - 1) + count} of {len(self.queue)} songs - {self.length}")
        await interaction.response.edit_message(embed=embed, view=self)


class Buttons(discord.ui.View):

    def __init__(self, client):
        super().__init__()
        self.client = client

    def controller(self, interaction):
        player = self.client.lavalink.player_manager.get(interaction.guild.id)
        return player

    @staticmethod
    def compilequeue(queue):
        titles = []
        lengths = []
        for song in queue:
            titles.append(song.title)
            lengths.append(int(song.duration / 1000))
        return titles, lengths

    @discord.ui.button(emoji=cfg.pause, label="Play/Pause", style=discord.ButtonStyle.gray, row=1)
    async def button_pauseplay(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        embed = create_embed(player.current, player.position)
        if not player.paused:
            await player.set_pause(pause=True)
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.channel.send(f"{interaction.user.display_name} paused the music")
        else:
            await player.set_pause(pause=False)
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.channel.send(f"{interaction.user.display_name} resumed the music")

    @discord.ui.button(emoji=cfg.skip, label="Skip", style=discord.ButtonStyle.gray, row=1)
    async def button_forward(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        embed = create_embed(player.current, player.position)
        await player.skip()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(f"{interaction.user.display_name} skipped the song")

    @discord.ui.button(emoji=cfg.stop, label="Stop", style=discord.ButtonStyle.gray, row=1)
    async def button_stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        embed = discord.Embed(title=f"Stopping player...", color=discord.Color.red())
        voice = interaction.guild.voice_client
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.channel.send(f"{interaction.user.display_name} stopped the player")
        if voice:
            await voice.disconnect(force=True)
        await cleanup(player)

    @discord.ui.button(emoji=cfg.shuffle, label="Shuffle", style=discord.ButtonStyle.gray, row=2)
    async def button_shuffle(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        embed = create_embed(player.current, player.position)
        await interaction.response.edit_message(embed=embed, view=self)
        if not player.shuffle:
            player.set_shuffle(shuffle=True)
            await interaction.channel.send(f"{interaction.user.display_name} shuffling the queue!")
        else:
            player.set_shuffle(shuffle=False)
            await interaction.channel.send(f"{interaction.user.display_name} no longer shuffling the queue!")

    @discord.ui.button(emoji=cfg.repeat, label="Repeat", style=discord.ButtonStyle.gray, row=2)
    async def button_loop(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        embed = create_embed(player.current, player.position)
        await interaction.response.edit_message(embed=embed, view=self)
        if not player.repeat:
            player.set_repeat(repeat=True)
            await interaction.channel.send(f"{interaction.user.display_name} looping the queue!")
        else:
            player.set_repeat(repeat=False)
            await interaction.channel.send(f"{interaction.user.display_name} no longer looping the queue!")

    @discord.ui.button(emoji=cfg.queue, label="Queue", style=discord.ButtonStyle.gray, row=2)
    async def button_queue(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        queue, length = self.compilequeue(player.queue)
        songlist = []
        count = 1
        for song in queue[:10]:
            songlist.append(f"**{count}:** `{song}`")
            count += 1
        totallength = time.strftime('%H hours, %M minutes, %S seconds', time.gmtime(sum(length)))
        embed = discord.Embed(title="Upcoming Songs", description=f"\n".join(songlist), color=cfg.embed_color)
        embed.set_footer(text=f"10 of {len(queue)} songs - {totallength}")
        view = Queue(self.client, queue, totallength)
        ex = view.children[1:] if len(queue) > 10 else view.children[1:2]
        view.disable_all_items(exclusions=ex)
        await interaction.response.edit_message(embed=embed, view=view)


class Music(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.client.lavalink = None
        client.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        await self.client.wait_until_ready()
        lavaclient = lavalink.Client(self.client.user.id)
        lavaclient.add_node(host=cfg.l_host, port=cfg.l_port, password=cfg.l_password, region=cfg.l_region)
        lavaclient.add_event_hooks(self)
        self.client.lavalink = lavaclient

    @lavalink.listener(lavalink.events.QueueEndEvent)
    async def queue_ending(self, event: lavalink.QueueEndEvent):
        guild_id = event.player.guild_id
        guild = self.client.get_guild(guild_id)
        await guild.voice_client.disconnect(force=True)

    @staticmethod
    def is_privileged(ctx, track):
        return track.requester == ctx.author.id or ctx.author.guild_permissions.kick_members

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        voice = discord.utils.get(self.client.voice_clients, guild=member.guild)
        player = self.client.lavalink.player_manager.get(member.guild.id)
        if not voice:
            if player:
                await cleanup(player)
            return
        elif voice.channel != before.channel:  # ignore if the member joined a voice channel
            return
        elif member.bot:
            return
        if after.channel != before.channel:
            memberlist = []
            for m in before.channel.members:
                if m.bot:
                    continue
                memberlist.append(m)
            if not memberlist:
                if player.is_playing:
                    await cleanup(player)
                await voice.disconnect(force=True)

    @slash_command(description="Play some music")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def music(self, ctx, search: Option(str, description="Music query or URL", required=False, default=None)):
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            return await ctx.respond(f"{cfg.error} You need to be in a voice channel", ephemeral=True)
        player = self.client.lavalink.player_manager.create(ctx.guild.id)
        try:
            await channel.connect(cls=Player)
        except discord.ClientException:
            await ctx.guild.voice_client.move_to(channel)
        if search:
            if len(search) > 256:
                return await ctx.respond(f"{cfg.error} Search query has a maximum of 256 characters!", ephemeral=True)
            elif player.is_playing:
                if len(player.queue) >= 250:
                    return await ctx.respond(f"{cfg.error} The queue is full!", ephemeral=True)
            search = f'ytsearch:{search}' if not RURL.match(search) else search
            results = await player.node.get_tracks(search)
            tracks = results.tracks
            match results.load_type:
                case lavalink.LoadType.PLAYLIST:
                    total = len(player.queue)
                    count = 0
                    for track in tracks:
                        if total + count < 250:
                            player.add(track=track, requester=ctx.author.id)
                            count += 1
                    await ctx.respond(embed=confirmation(f"Added {count} songs to the player"))
                    if not player.is_playing:
                        await player.play()
                case lavalink.LoadType.TRACK:
                    song = tracks[0]
                    await ctx.respond(embed=confirmation(f"Adding {song.title} to the player"))
                    player.add(track=song, requester=ctx.author.id)
                    if not player.is_playing:
                        await player.play()
                case lavalink.LoadType.SEARCH:
                    view = discord.ui.View()
                    view.add_item(SongSelect(self.client, tracks[:5], ctx.author))
                    await ctx.respond(view=view)
                case _:
                    return await ctx.respond(f"{cfg.error} Couldn't find any music!", ephemeral=True)
        else:
            if not player.is_playing:
                return await ctx.respond(f"{cfg.error} No music playing!", ephemeral=True)
            check = self.is_privileged(ctx, player.current)
            bview = Buttons(self.client) if check else None
            embed = create_embed(player.current, player.position)
            await ctx.respond(embed=embed, view=bview, ephemeral=True)


def setup(client):
    client.add_cog(Music(client))

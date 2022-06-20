import re
import time
from typing import Union

import discord
import lavalink
from discord import slash_command, Option
from discord.ext import commands

RURL = re.compile(r'https?://(?:www\.)?.+')


def create_embed(track, position):
    pos = time.strftime('%H:%M:%S', time.gmtime(int(position / 1000)))
    dur = time.strftime('%H:%M:%S', time.gmtime(int(track.duration / 1000)))
    embed = discord.Embed(title=f"{track.title}", description=f"*{track.author}*", color=discord.Color.gold())
    embed.add_field(name="__Position__", value=f"{pos}/{dur}", inline=True)
    embed.add_field(name="__Video URL__", value=f"[Click here!]({track.uri})", inline=False)
    embed.set_footer(text=f"Requested by {track.requester}")
    return embed


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
    def __init__(self, client, results, author):
        self.client = client
        self.results = results['tracks'][:5]
        self.author = author
        self.keys = {}

        options = []
        for track in self.results:
            info = track['info']
            title = info['title']
            options.append(discord.SelectOption(label=f"{title}", description=f"By {info['author']}"))
            self.keys[f'{title}'] = track
        super().__init__(placeholder="Pick a song!", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            return await interaction.response.send_message("<:n_no:987886730625560626> Invalid user!", ephemeral=True)
        selection = self.values[0]
        song = self.keys[f"{selection}"]
        info = song['info']
        await interaction.response.edit_message(content=f"```fix\nAdding {info['title']} to the player\n```", view=None)
        player = self.client.lavalink.player_manager.create(interaction.guild.id)
        player.add(requester=self.author.id, track=song)
        if not player.is_playing:
            await player.play()


class Queue(discord.ui.View):

    def __init__(self, client):
        super().__init__()
        self.client = client

    @discord.ui.button(label="Go Back", style=discord.ButtonStyle.red)
    async def queue_return(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.client.lavalink.player_manager.get(interaction.guild.id)
        embed = create_embed(player.current, player.position)
        await interaction.response.edit_message(embed=embed, view=Buttons(self.client))


class Buttons(discord.ui.View):

    def __init__(self, client):
        super().__init__()
        self.client = client

    def controller(self, interaction):
        player = self.client.lavalink.player_manager.get(interaction.guild.id)
        return player

    @staticmethod
    async def cleanup(player):
        player.queue.clear()
        await player.stop()

    @staticmethod
    def compilequeue(queue):
        out = []
        for song in queue:
            out.append(song.title)
        return out

    @discord.ui.button(emoji="<:n_pause:987879632441311285>", label="Play/Pause", style=discord.ButtonStyle.gray, row=1)
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

    @discord.ui.button(emoji="<:n_skip:987879627680796754>", label="Skip", style=discord.ButtonStyle.gray, row=1)
    async def button_forward(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        embed = create_embed(player.current, player.position)
        await player.skip()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.channel.send(f"{interaction.user.display_name} skipped the song")

    @discord.ui.button(emoji="<:n_stop:987879633913536572>", label="Stop", style=discord.ButtonStyle.gray, row=1)
    async def button_stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        embed = discord.Embed(title=f"Stopping player...", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=None)
        await interaction.channel.send(f"{interaction.user.display_name} stopped the player")
        await self.cleanup(player)
        await interaction.guild.voice_client.disconnect(force=True)

    @discord.ui.button(emoji="<:n_shuffle:987879631409512458>", label="Shuffle", style=discord.ButtonStyle.gray, row=2)
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

    @discord.ui.button(emoji="<:n_repeat:987879630000259162>", label="Repeat", style=discord.ButtonStyle.gray, row=2)
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

    @discord.ui.button(emoji="<:n_list:987879635029217301>", label="Queue", style=discord.ButtonStyle.gray, row=2)
    async def button_queue(self, button: discord.ui.Button, interaction: discord.Interaction):
        player = self.controller(interaction)
        queue = self.compilequeue(player.queue)
        songlist = []
        count = 1
        for song in queue[:10]:
            songlist.append(f"**{count}:** `{song}`")
            count += 1
        embed = discord.Embed(title=f"Next 10 Songs", description=f"\n".join(songlist), color=discord.Color.gold())
        await interaction.response.edit_message(embed=embed, view=Queue(self.client))


class Music(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.client.lavalink = None
        client.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        await self.client.wait_until_ready()
        lavaclient = lavalink.Client(self.client.user.id)
        lavaclient.add_node('<ip>', '<port>', '<password>', '<region>', 'default')
        lavalink.add_event_hook(self.track_hook)
        self.client.lavalink = lavaclient

    async def track_hook(self, event):
        if isinstance(event, lavalink.events.QueueEndEvent):
            guild_id = int(event.player.guild_id)
            guild = self.client.get_guild(guild_id)
            await guild.voice_client.disconnect(force=True)

    @staticmethod
    def is_privileged(ctx, track):
        return track.requester == ctx.author.id or ctx.author.guild_permissions.kick_members

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                    after: discord.VoiceState):
        if member.bot:
            return
        voice = discord.utils.get(self.client.voice_clients, guild=member.guild)
        if not voice:
            return
        elif voice.channel != before.channel:
            return
        if after.channel != before.channel:
            memberlist = []
            for m in before.channel.members:
                if m.bot:
                    continue
                memberlist.append(m)
            if not memberlist:
                player = self.client.lavalink.player_manager.get(member.guild.id)
                if player.is_playing:
                    player.queue.clear()
                    await player.stop()
                await voice.disconnect(force=True)

    @slash_command(description="Play some music")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def music(self, ctx, search: Option(str, description="Music query or URL", required=False, default=None)):
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            return await ctx.respond("<:n_no:987886730625560626> You need to be in a voice channel", ephemeral=True)
        player = self.client.lavalink.player_manager.create(ctx.guild.id)
        try:
            await channel.connect(cls=Player)
        except discord.ClientException:
            await ctx.guild.voice_client.move_to(channel)
        if search:
            if len(search) > 256:
                return await ctx.respond("<:n_no:987886730625560626> Search query has a maximum of 256 characters!",
                                         ephemeral=True)
            if not RURL.match(search):
                search = f'ytsearch:{search}'
            results = await player.node.get_tracks(search)
            if not results or not results['tracks']:
                return await ctx.respond("<:n_no:987886730625560626> Couldn't find any music!", ephemeral=True)
            elif len(results['tracks']) == 1:
                song = results['tracks'][0]
                info = song['info']
                await ctx.respond(f"```fix\nAdding {info['title']} to the player\n```")
                player.add(requester=ctx.author.id, track=song)
                if not player.is_playing:
                    await player.play()
            else:
                view = discord.ui.View()
                view.add_item(SongSelect(self.client, results, ctx.author))
                await ctx.respond(view=view)
        else:
            if not player.is_playing:
                return await ctx.respond("<:n_no:987886730625560626> No music playing!", ephemeral=True)
            check = self.is_privileged(ctx, player.current)
            bview = Buttons(self.client) if check else None
            embed = create_embed(player.current, player.position)
            await ctx.respond(embed=embed, view=bview, ephemeral=True)


def setup(client):
    client.add_cog(Music(client))

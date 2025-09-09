import discord
from discord.ext import commands
from discord import app_commands

import os
import json
from dotenv import load_dotenv
import asyncio

RADIO_URL = "https://s2.radio.co/s2b2b68744/listen"
CHANNEL_FILE = "radio_channel.json"

load_dotenv()
TOKEN = os.getenv("satin")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="/", intents=intents)

CUSTOM_STATUSES = [
	discord.Activity(type=discord.ActivityType.listening, name="BadRadio.nz"),
	discord.CustomActivity(name="go support BadRadio, theyre what makes this possible!"),
	discord.CustomActivity(name="use /radio"),
	discord.CustomActivity(name="ponk"),
	discord.CustomActivity(name="phonk my goat"),
	discord.CustomActivity(name="ignoring 99.9% of requests"),
	discord.Activity(type=discord.ActivityType.listening, name="SOUDIERE, DJ Yung VAmp, NxxxxxS, Dj Smokey, Roland Jones."),
]

async def status_cycler():
	await bot.wait_until_ready()
	while not bot.is_closed():
		for status in CUSTOM_STATUSES:
			await bot.change_presence(status=discord.Status.idle, activity=status)
			await asyncio.sleep(30)

def save_channel(guild_id, channel_id):
	try:
		with open(CHANNEL_FILE, "r") as f:
			data = json.load(f)
	except (FileNotFoundError, json.JSONDecodeError):
		data = {}
	data[str(guild_id)] = channel_id
	with open(CHANNEL_FILE, "w") as f:
		json.dump(data, f)

def get_channel(guild_id):
	try:
		with open(CHANNEL_FILE, "r") as f:
			data = json.load(f)
		return data.get(str(guild_id))
	except (FileNotFoundError, json.JSONDecodeError):
		return None

@bot.tree.command(name="leave", description="Disconnect the bot from the current voice channel.")
async def leave(interaction: discord.Interaction):
	guild = interaction.guild
	vc = guild.voice_client
	if vc and vc.is_connected():
		await vc.disconnect()
		await interaction.response.send_message("Disconnected from the voice channel.")
	else:
		await interaction.response.send_message("I'm not connected to any voice channel.", ephemeral=True)

@bot.tree.command(name="setchannel", description="Set the voice channel for radio.")
@app_commands.describe(channel="Voice channel to use (mention or ID)")
@app_commands.checks.has_permissions(administrator=True)
async def setchannel(interaction: discord.Interaction, channel: str):
	guild = interaction.guild
	voice_channel = None
	# Try to get by mention or ID, but only allow voice channels
	if channel.startswith("<#") and channel.endswith(">"):
		channel_id = int(channel[2:-1])
		ch = guild.get_channel(channel_id)
		if isinstance(ch, discord.VoiceChannel):
			voice_channel = ch
	else:
		try:
			channel_id = int(channel)
			ch = guild.get_channel(channel_id)
			if isinstance(ch, discord.VoiceChannel):
				voice_channel = ch
		except ValueError:
			# Try by name, only among voice channels
			for ch in guild.voice_channels:
				if ch.name == channel or ch.name == channel.lstrip("#"):
					voice_channel = ch
					break
	if not voice_channel:
		await interaction.response.send_message("Voice channel not found. Please provide a valid voice channel mention, ID, or name.", ephemeral=True)
		return
	save_channel(guild.id, voice_channel.id)
	await interaction.response.send_message(f"Radio channel set to {voice_channel.mention}", ephemeral=True)

async def play_radio(vc, interaction=None, channel=None, retry_count=0):
	ffmpeg_options = {
		'options': '-vn',
		'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
	}
	try:
		source = await discord.FFmpegOpusAudio.from_probe(RADIO_URL, **ffmpeg_options)
		def after_playing(error):
			if error or not vc.is_playing():
				# Schedule a reconnect on the event loop
				fut = asyncio.run_coroutine_threadsafe(
					play_radio(vc),
					vc.client.loop
				)
		vc.play(source, after=after_playing)
		if interaction and channel:
			await interaction.followup.send(f"Playing radio in {channel.mention}")
	except Exception as e:
		if retry_count < 5:
			await asyncio.sleep(3)
			await play_radio(vc, interaction, channel, retry_count+1)
		else:
			if interaction:
				await interaction.followup.send(f"Failed to play radio after retries: {e}", ephemeral=True)

@bot.tree.command(name="radio", description="Join the set channel and play radio.")
async def radio(interaction: discord.Interaction):
	await interaction.response.defer(thinking=True, ephemeral=False)
	guild = interaction.guild
	channel_id = get_channel(guild.id)
	if not channel_id:
		await interaction.followup.send("No channel set. Use /setchannel first.", ephemeral=True)
		return
	channel = guild.get_channel(int(channel_id))
	if not channel or not isinstance(channel, discord.VoiceChannel):
		await interaction.followup.send("Saved channel not found.", ephemeral=True)
		return
	# Connect and play
	if guild.voice_client:
		vc = guild.voice_client
		if vc.channel.id != channel.id:
			await vc.move_to(channel)
	else:
		vc = await channel.connect()
	if not vc.is_playing():
		await play_radio(vc, interaction, channel)
	else:
		await interaction.followup.send("Already playing.", ephemeral=True)

@setchannel.error
async def setchannel_error(interaction: discord.Interaction, error):
	if isinstance(error, app_commands.errors.MissingPermissions):
		await interaction.response.send_message("You need admin permissions to use this command.", ephemeral=True)
	else:
		await interaction.response.send_message(f"Error: {error}", ephemeral=True)


@bot.event
async def on_ready():
	print(f"Logged in as {bot.user}")
	try:
		synced = await bot.tree.sync()
		print(f"Synced {len(synced)} commands.")
	except Exception as e:
		print(f"Failed to sync commands: {e}")
	bot.loop.create_task(status_cycler())


# Switch to 'Listening to BadRadio.nz' when joining a voice channel, revert to cycling when leaving all
@bot.event
async def on_voice_state_update(member, before, after):
	if member.id != bot.user.id:
		return
	# Joined a voice channel
	if after.channel and (not before.channel or before.channel.id != after.channel.id):
		await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="BadRadio.nz"))
	# Left all voice channels
	elif before.channel and not after.channel:
		# Restart the status cycler
		bot.loop.create_task(status_cycler())

bot.run(TOKEN)

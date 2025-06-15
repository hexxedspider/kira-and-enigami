import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os
import random
import aiohttp
from bs4 import BeautifulSoup
import asyncpraw
import xml.etree.ElementTree as ET
import asyncio
from datetime import datetime
import threading

load_dotenv()
bot3 = os.getenv("bot3")
OWNER_ID = int(os.getenv("BOT3DM"))

intents = discord.Intents.default()
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="$", intents=intents)
        self.synced = False

bot = MyBot()

def nsfw_check():
    async def predicate(interaction: discord.Interaction):
        if interaction.guild and not interaction.channel.is_nsfw():
            try:
                await interaction.user.send("This command can only be used in NSFW channels or in DMs.")
            except discord.Forbidden:
                await interaction.response.send_message("Please enable DMs to receive error messages.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

LOG_FILE = "command_log_3.txt"

def log_command(interaction: discord.Interaction):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = f"{interaction.user.name}#{interaction.user.discriminator}"
    command_used = interaction.command.name
    guild_name = interaction.guild.name if interaction.guild else "DM"
    log_line = f"[enigami chamber's] [{timestamp}] [{guild_name}] {username}: {command_used}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

async def send_post(interaction, post):
    file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
    post_id = post.get("id")
    tags = post.get("tags", "")

    if not file_url:
        await interaction.response.send_message("No image URL found in the post.", ephemeral=True)
        return

    if file_url.endswith((".mp4", ".webm", ".gif")):
        await interaction.response.send_message(f"Rule34 video/gif: [View]({file_url})")
    else:
        embed = discord.Embed(
            title="Rule34 Result",
            url=f"https://rule34.xxx/index.php?page=post&s=view&id={post_id}",
            description=f"Tags: `{tags[:250]}...`" if tags else None,
            color=discord.Color.blue()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: Rule34")
        await interaction.response.send_message(embed=embed)

stash_cache = {}
stash_cache_lock = threading.Lock()

stashex_cache = {}
stashex_cache_lock = threading.Lock()

def get_stash_files(folder_path):
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
    with stash_cache_lock:
        if folder_path in stash_cache:
            return stash_cache[folder_path]
        if not os.path.isdir(folder_path):
            return []
        files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(valid_extensions)
        ]
        stash_cache[folder_path] = files
        return files

def get_stashex_files(folder_path):
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
    with stash_cache_lock:
        if folder_path in stash_cache:
            return stash_cache[folder_path]
        if not os.path.isdir(folder_path):
            return []
        files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith(valid_extensions)
        ]
        stash_cache[folder_path] = files
        return files

@bot.tree.command(name="help", description="Show help for NSFW stash commands")
async def help_command(interaction: discord.Interaction):
    log_command(interaction)
    embed = discord.Embed(title="⛧°. ⋆𓌹*♰*𓌺⋆. °⛧", color=discord.Color.blue())
    embed.add_field(
        name="/stash",
        value="Use '/stashex' for examples. Usage: /stash folder:shiku (or other name) \nAvailable folders: 'shiku', 'yashima', 'vivi', 'saeya', 'muerte'",
        inline=True,
    )
    embed.set_footer(text="Use these commands in NSFW channels only, or DMs.")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stashex", description="Show an example image from a folder")
@app_commands.describe(folder="Folder name (shiku, yashima, vivi, etc.)")
@nsfw_check()
async def stashex(interaction: discord.Interaction, folder: str):
    log_command(interaction)
    base_path = "stashex"
    folder_path = os.path.join(base_path, folder)

    folder_messages = {
        "shiku": "Here is an example of what Shiku looks like.",
        "yashima": "Here is an example of what Yashima looks like.",
        "vivi": "Here is an example of what Vivi looks like.",
    }

    files = get_stashex_files(folder_path)

    if not os.path.isdir(folder_path):
        await interaction.response.send_message(f"Invalid path ({folder}). Either a typo, or doesn't exist.", ephemeral=True)
        return

    if not files:
        await interaction.response.send_message(f"No images found.", ephemeral=True)
        return

    selected = random.choice(files)
    image_path = os.path.join(folder_path, selected)

    try:
        if folder in folder_messages:
            await interaction.response.send_message(folder_messages[folder], ephemeral=True)
        await interaction.followup.send(file=discord.File(image_path))
    except Exception as e:
        await interaction.response.send_message(f"Error sending image: {e}", ephemeral=True)

@bot.tree.command(name="stash", description="Send a random image from a folder")
@app_commands.describe(folder="Folder name (shiku, yashima, vivi, etc.)")
@nsfw_check()
async def stash(interaction: discord.Interaction, folder: str):
    log_command(interaction)
    base_path = "stash"
    folder_path = os.path.join(base_path, folder)

    files = get_stash_files(folder_path)

    if not os.path.isdir(folder_path):
        await interaction.response.send_message(f"Folder '{folder}' does not exist.", ephemeral=True)
        return

    if not files:
        await interaction.response.send_message(f"No image files found in '{folder}'.", ephemeral=True)
        return

    selected = random.choice(files)
    image_path = os.path.join(folder_path, selected)

    try:
        await interaction.response.send_message(file=discord.File(image_path))
    except Exception as e:
        await interaction.response.send_message(f"Error sending image: {e}", ephemeral=False)

# discord.CustomActivity(name=""),
async def cycle_status():
    await bot.wait_until_ready()
    statuses = [
        discord.Activity(type=discord.ActivityType.listening, name="mommy asmr"),
        discord.CustomActivity(name="/help on your command...\n\n pun intended."),
        discord.CustomActivity(name="/stashex"),
        discord.CustomActivity(name="coming to you revamped!"),
        discord.Activity(type=discord.ActivityType.listening, name="7xvn"),
        discord.CustomActivity(name="new command soon (/request)"),
    ]
    while not bot.is_closed():
        for status in statuses:
            await bot.change_presence(status=discord.Status.online, activity=status)
            await asyncio.sleep(15)

@bot.tree.command(name="github", description="Sends the GitHub repo link for the bot.")
async def github(interaction: discord.Interaction):
    """Sends the GitHub repo link for the bot."""
    await interaction.response.send_message("[GitHub](https://github.com/hexxedspider/kira-and-enigami)", ephemeral=True)

@bot.tree.command(
    name="request",
    description="Sends a DM to the owner, intended for requesting more characters in /stash"
)
@app_commands.describe(message="describe them.")
async def request(
    interaction: discord.Interaction,
    message: str
):
    owner = await bot.fetch_user(OWNER_ID)
    user = interaction.user
    dm_content = (
        f"New request from {user} (ID: {user.id}):\n\n"
        f"{message}"
    )
    await owner.send(dm_content)
    await interaction.response.send_message("your request was sent to the owner, he also has your username so he knows who to ping when it's ready.", ephemeral=True)

@bot.event
async def on_ready():
    if not bot.synced:
        await bot.tree.sync()
        bot.synced = True
    bot.loop.create_task(cycle_status())
    print(f"Logged in as {bot.user}")

bot.run(bot3)
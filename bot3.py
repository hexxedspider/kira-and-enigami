import discord
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

intents = discord.Intents.default()
intents.message_content = True 

# command_prefix is just that, thats what make $help, $help. change to whatever if you want to.
bot = commands.Bot(command_prefix="$", intents=intents, help_command=None)

def nsfw_check():
    async def predicate(ctx):
        if ctx.guild and not ctx.channel.is_nsfw():
            try:
                await ctx.author.send("This command can only be used in NSFW channels or in DMs.")
            except discord.Forbidden:
                await ctx.reply("Please enable DMs to receive error messages.")
            return False
        return True
    return commands.check(predicate)

# stores each command used, date, time, who, what
LOG_FILE = "command_log_3.txt"

def log_command(ctx):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = f"{ctx.author.name}#{ctx.author.discriminator}"
    command_used = ctx.message.content
    guild_name = ctx.guild.name if ctx.guild else "DM"

    log_line = f"[enigami chamber's] [{timestamp}] [{guild_name}] {username}: {command_used}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

@bot.event
async def on_command(ctx):
    log_command(ctx)

async def send_post(ctx, post):
    file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
    post_id = post.get("id")
    tags = post.get("tags", "")

    if not file_url:
        await ctx.send("No image URL found in the post.")
        return

    # Check for video/gif
    if file_url.endswith((".mp4", ".webm", ".gif")):
        await ctx.send(f"Rule34 video/gif: [View]({file_url})")
    else:
        embed = discord.Embed(
            title="Rule34 Result",
            url=f"https://rule34.xxx/index.php?page=post&s=view&id={post_id}",
            description=f"Tags: `{tags[:250]}...`" if tags else None,
            color=discord.Color.blue()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: Rule34")
        await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    if ctx.guild:
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    # if guild but not nsfw, send to dms
    if ctx.guild and not ctx.channel.is_nsfw():
        try:
            await ctx.author.send(
                "$help command can only be used in NSFW channels. Try again in an age-restricted channel or here in DMs."
            )
        except discord.Forbidden:
            await ctx.reply("Please enable DMs to receive error messages.")
        return

    embed = discord.Embed(title="⛧°. ⋆𓌹*♰*𓌺⋆. °⛧", color=discord.Color.blue())
    embed.add_field(name="$r34",value="Search Rule34 posts by tags. Use spaces to separate multiple tags. Supports embeds.",inline=True,)
    embed.add_field(name="$stash",value="Use '$stashex' for examples. Usage: $stash shiku (or other name) \nAvailable folders: 'shiku', 'yashima', 'vivi', 'saeya', 'muerte'",inline=True,)
    embed.set_footer(text="Use these commands in NSFW channels only, or DMs.")

    if ctx.guild is None:
        await ctx.author.send(embed=embed)
    else:
        await ctx.send(embed=embed)

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

@bot.command()
async def stashex(ctx, folder: str):
    base_path = "stashex"
    folder_path = os.path.join(base_path, folder)

    folder_messages = {
        "shiku": "Here is an example of what Shiku looks like.",
        "yashima": "Here is an example of what Yashima looks like.",
        "vivi": "Here is an example of what Vivi looks like.",
    }

    files = get_stashex_files(folder_path)

    if not os.path.isdir(folder_path):
        await ctx.send(f"Invalid path ({folder}). Either a typo, or doesn't exist.")
        return
    
    if not files:
        await ctx.send(f"No images found.")
        return

    selected = random.choice(files)
    image_path = os.path.join(folder_path, selected)

    try:
        if folder in folder_messages:
            await ctx.send(folder_messages[folder])
        await ctx.send(file=discord.File(image_path))
    except Exception as e:
        await ctx.send(f"Error sending image: {e}")

@bot.command()
async def stash(ctx, folder: str):
    base_path = "stash"
    folder_path = os.path.join(base_path, folder)

    files = get_stash_files(folder_path)

    if not os.path.isdir(folder_path):
        await ctx.send(f"Folder '{folder}' does not exist.")
        return

    if not files:
        await ctx.send(f"No image files found in '{folder}'.")
        return

    selected = random.choice(files)
    image_path = os.path.join(folder_path, selected)

    try:
        await ctx.send(file=discord.File(image_path))
    except Exception as e:
        await ctx.send(f"Error sending image: {e}")
        
@bot.command()
async def r34(ctx, *, args: str):
    parts = args.split()
    repeat = 1
    interval = 0

    if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
        repeat = int(parts[-2])
        interval = int(parts[-1])
        tags_list = parts[:-2]
    elif len(parts) >= 2 and parts[-1].isdigit():
        repeat = int(parts[-1])
        tags_list = parts[:-1]
    else:
        tags_list = parts

    if not tags_list:
        await ctx.send("Please provide at least one tag.")
        return

    combined_tags = "_".join(tags_list)

    if ctx.guild and not ctx.channel.is_nsfw():
        try:
            await ctx.author.send("This command can only be used in NSFW channels. Try again in a proper channel or in DMs.")
        except discord.Forbidden:
            await ctx.reply("Please enable DMs to receive error messages.")
        return

    async with aiohttp.ClientSession() as session:
        for i in range(repeat):
            url = f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit=50&tags={combined_tags}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    await ctx.send("Error contacting Rule34 API.")
                    return
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    await ctx.send("Failed to decode Rule34 response.")
                    return

            if data:
                post = random.choice(data)
                await send_post(ctx, post)
            else:
                await ctx.send("No posts found for those tags.")
                return

            if i < repeat - 1 and interval > 0:
                await asyncio.sleep(interval)

# Load Reddit credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

reddit = None  # global placeholder

@bot.event
async def on_ready():
    global reddit
    if reddit is None:
        reddit = asyncpraw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
    print(f"Logged in as {bot.user}, Reddit client initialized")

@bot.command()
async def invslavelink(ctx):
    try:
        await ctx.author.send("[Link here.](https://discord.com/oauth2/authorize?client_id=1380780651120296076&permissions=8&integration_type=0&scope=bot)")
    except discord.Forbidden:
        error = await ctx.send("I couldn't DM you. Please check your privacy settings.")
        await error.delete(delay=5)

    await ctx.message.delete(delay=0.1)

# Run the bot
bot.run(bot3)

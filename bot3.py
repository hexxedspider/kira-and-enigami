import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import random
import aiohttp
import asyncio

# Load token from .env
load_dotenv()
BOT3 = os.getenv("BOT3")

# Configure intents
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content

# Create bot instance
bot = commands.Bot(command_prefix="$", intents=intents, help_command=None)

# Store running loops by channel ID
r34_loops = {}

# ---------- NSFW check decorator ----------
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

# ---------- HELP command ----------
@bot.command()
async def help(ctx):
    # Delete invoking message if in a guild
    if ctx.guild:
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    # If in guild but channel not NSFW, send help in DMs
    if ctx.guild and not ctx.channel.is_nsfw():
        try:
            await ctx.author.send(
                "$help command can only be used in NSFW channels. Try again in an age-restricted channel or here in DMs."
            )
        except discord.Forbidden:
            await ctx.reply("Please enable DMs to receive error messages.")
        return

    embed = discord.Embed(title="⛧°. ⋆𓌹*♰*𓌺⋆. °⛧", color=discord.Color.blue())
    embed.add_field(
        name="$r34 <tags>",
        value="Search Rule34 posts by tags. Use spaces to separate multiple tags. Supports embeds.",
        inline=False,
    )
    embed.add_field(
        name="enigami r34 <tags>",
        value="Custom version of $r34 command with similar functionality.",
    )
    embed.add_field(
        name="$stopr34",
        value="Stop repeating Rule34 posts in the current channel.",
        inline=False,
    )
    embed.set_footer(text="Use these commands in NSFW channels only.")

    if ctx.guild is None:
        await ctx.author.send(embed=embed)
    else:
        await ctx.send(embed=embed)

# Dictionary to keep track of active loops by channel ID
r34_loops = {}

# ---------- Rule34 command ----------
@bot.command()
async def r34(ctx, *, args: str):
    # Parse tags and optional interval
    parts = args.split()
    interval = 10  # default 10 seconds
    if parts and parts[-1].isdigit():
        interval = int(parts[-1])
        tags = parts[:-1]
    else:
        tags = parts

    if not tags:
        await ctx.send("Please provide tags for Rule34 search.")
        return

    # Stop existing loop in this channel if any before starting new
    if ctx.channel.id in r34_loops:
        r34_loops[ctx.channel.id].cancel()

    # Create a task to send a new post every `interval` seconds
    task = bot.loop.create_task(r34_repeating_task(ctx, " ".join(tags), interval))
    r34_loops[ctx.channel.id] = task
    await ctx.send(f"Started repeating Rule34 posts for tags: `{ ' '.join(tags) }` every {interval} seconds.")

# optional r34_custom command (same as r34)
@bot.command()
async def r34_custom(ctx, *, args: str):
    parts = args.split()
    interval = 10
    if parts and parts[-1].isdigit():
        interval = int(parts[-1])
        tags = parts[:-1]
    else:
        tags = parts

    if not tags:
        await ctx.send("Please provide tags for Rule34 search.")
        return

    if ctx.channel.id in r34_loops:
        r34_loops[ctx.channel.id].cancel()

    task = bot.loop.create_task(r34_repeating_task(ctx, " ".join(tags), interval))
    r34_loops[ctx.channel.id] = task
    await ctx.send(f"Started repeating Rule34 posts for tags: `{ ' '.join(tags) }` every {interval} seconds.")

@bot.command()
async def stopr34(ctx):
    # Stop the loop if it exists in this channel
    task = r34_loops.pop(ctx.channel.id, None)
    if task:
        task.cancel()
        await ctx.send("Stopped repeating Rule34 posts in this channel.")
    else:
        await ctx.send("No repeating Rule34 posts are running in this channel.")

async def r34_repeating_task(ctx_or_msg, tags: str, interval: int):
    try:
        while True:
            await r34_logic(ctx_or_msg, tags)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        # Loop was cancelled, just exit gracefully
        pass

# send_post function (single version)
async def send_post(channel, post):
    url = post.get("file_url") or post.get("preview_url")
    if not url:
        await channel.send("No media URL found.")
        return

    if url.endswith(('.mp4', '.webm')):
        message = f"Rule34 Result - [Video Link]({url})"
    elif url.endswith('.gif'):
        message = f"Rule34 Result - [GIF Image Link]({url})"
    else:
        message = f"Rule34 Result - [Image Link]({url})"

    await channel.send(message)

# r34_logic function (single unified)
async def r34_logic(ctx_or_msg, tags: str):
    channel = getattr(ctx_or_msg, 'channel', None)
    guild = getattr(ctx_or_msg, 'guild', None)
    author = getattr(ctx_or_msg, 'author', None)

    # Allow usage in NSFW channels or DMs only
    if guild is not None and channel is not None and not channel.is_nsfw():
        try:
            await author.send(
                "This command can only be used in NSFW channels or in DMs. Try again in a proper channel or DM me."
            )
        except discord.Forbidden:
            if hasattr(ctx_or_msg, 'reply'):
                await ctx_or_msg.reply("Please enable DMs to receive error messages.")
            else:
                await channel.send(f"{author.mention} Please enable DMs to receive error messages.")
        return

    tags_list = tags.split()
    combined_tags = "_".join(tags_list)

    async with aiohttp.ClientSession() as session:
        url = f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit=50&tags={combined_tags}"
        async with session.get(url) as resp:
            if resp.status != 200:
                await channel.send("Error contacting Rule34 API.")
                return
            try:
                data = await resp.json(content_type=None)
            except Exception:
                await channel.send("Failed to decode Rule34 response.")
                return

        if data:
            if "animated" in tags_list:
                # Try to find mp4/webm videos first
                video_posts = [post for post in data if post.get("file_url", "").endswith(('.mp4', '.webm'))]
                if video_posts:
                    post = random.choice(video_posts)
                    await send_post(channel, post)
                    return
                # Fallback: try gifs as animated images
                gif_posts = [post for post in data if post.get("file_url", "").endswith('.gif')]
                if gif_posts:
                    post = random.choice(gif_posts)
                    await send_post(channel, post)
                    return
                await channel.send("No animated videos or gifs found for those tags.")
                return
            else:
                post = random.choice(data)
                await send_post(channel, post)
                return

        # Fallback: individual tags, same video and gif filtering for "animated"
        for tag in tags_list:
            url = f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit=50&tags={tag}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    continue
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    continue

            if data:
                if tag == "animated":
                    video_posts = [post for post in data if post.get("file_url", "").endswith(('.mp4', '.webm'))]
                    if video_posts:
                        post = random.choice(video_posts)
                        await send_post(channel, post)
                        return
                    gif_posts = [post for post in data if post.get("file_url", "").endswith('.gif')]
                    if gif_posts:
                        post = random.choice(gif_posts)
                        await send_post(channel, post)
                        return
                    else:
                        continue
                else:
                    post = random.choice(data)
                    await send_post(channel, post)
                    return

        await channel.send("No posts found for those tags.")

# run the bot
bot.run(BOT3)
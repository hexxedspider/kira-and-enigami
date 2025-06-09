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

# Load token from .env
load_dotenv()
BOT2 = os.getenv("BOT2")

# Configure intents
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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
                "!help command can only be used in NSFW channels. Try again in an age-restricted channel or here in DMs."
            )
        except discord.Forbidden:
            await ctx.reply("Please enable DMs to receive error messages.")
        return

    embed = discord.Embed(title="⛧°. ⋆𓌹*♰*𓌺⋆. °⛧", color=discord.Color.blue())
    embed.add_field(name="!r34",value="Search Rule34 posts by tags. Use spaces to separate multiple tags. Supports embeds.",inline=True,)
    embed.add_field( name="!nlife",value=("Searches Nekos.life API for requested tags. Way less lewd than Rule34, but still NSFW.\nAvailable categories: lewd, gasm, ngif, smug, fox_girl"),inline=True,)
    embed.add_field(name="!ptn",value="Search Pornhub for videos and grabs their thumbnail.",inline=True,)
    embed.add_field(name="!wpic",value=("!waifupic <category> to get a random NSFW image from waifu.pics.\nAvailable categories: waifu, neko, trap, blowjob"),inline=True,)
    embed.add_field(name="!yandere",value=("Search Yande.re for NSFW images by tags. Use spaces to separate tags.\nUsed like r34, and can also handle videos and gifs."),inline=True,)
    embed.add_field(name="!gelbooru",value=("Search Gelbooru for NSFW images by tags. Use spaces to separate tags.\nUsed like r34, and can also handle videos and gifs."),inline=True,)
    embed.add_field(name="!danbooru",value=("Similar to Gelbooru, except typically considered better.\nUsed like r34, and can also handle videos and gifs."),inline=True,)
    embed.add_field(name="!femboy", value="Fetches a random femboy image from Reddit. Only works in DMs. Fuck you Froggy for saying I should make this.", inline=True)
    embed.add_field(name="!xbooru", value=("Search Xbooru for NSFW images by tags. Use spaces to separate tags.\nUsed like r34, and can also handle videos and gifs."), inline=True)
    embed.add_field(name="!realbooru", value=("Search Realbooru for NSFW images by tags. Use spaces to separate tags.\nUsed like r34, and can also handle videos and gifs.\nTheir API is currently broken."), inline=True)
    embed.add_field(name="!konachan", value=("Search Konachan for NSFW images by tags. Use spaces to separate tags.\nUsed like r34, and can also handle videos and gifs."), inline=True)
    embed.add_field(name="Example usage",value=("'!r34 big_boobs goth' for multiple tags.\n'!ptn goth mom' to search Pornhub and provide a thumbnail."),inline=True,)

    embed.set_footer(text="Use these commands in NSFW channels only, or DMs.")

    if ctx.guild is None:
        await ctx.author.send(embed=embed)
    else:
        await ctx.send(embed=embed)

# ---------- Rule34 command ----------
@bot.command()
async def r34(ctx, *, tags: str):
    if ctx.guild and not ctx.channel.is_nsfw():
        try:
            await ctx.author.send("This command can only be used in NSFW channels. Try again in a proper channel or in DMs.")
        except discord.Forbidden:
            await ctx.reply("Please enable DMs to receive error messages.")
        return

    tags_list = tags.split()
    combined_tags = "_".join(tags_list)

    async with aiohttp.ClientSession() as session:
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
            return

        # Fallback: try individual tags
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
                post = random.choice(data)
                await send_post(ctx, post)
                return

        await ctx.send("No posts found for those tags.")

async def send_post(ctx, post):
    url = post.get("file_url") or post.get("preview_url")
    if not url:
        await ctx.send("No media URL found.")
        return

    if url.endswith(('.mp4', '.webm')):
        preview = post.get("preview_url")
        message = f"Rule34 Result - [Video Link]({url})"
    else:
        message = f"Rule34 Result - [Image Link]({url})"

    await ctx.send(message)

# ---------- Nekos.life command ----------
async def fetch_nekos_image(session, endpoint):
    url = f"https://nekos.life/api/v2/img/{endpoint}"
    async with session.get(url) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()
        return data.get("url")

@bot.command()
@nsfw_check()
async def nlife(ctx, category: str = None):
    valid_categories = {"lewd", "gasm", "ngif", "smug", "fox_girl"}

    if category is None:
        category = random.choice(list(valid_categories))
    else:
        category = category.lower()
        if category not in valid_categories:
            await ctx.send(f"Invalid category! Please choose from: {', '.join(valid_categories)}")
            return

    async with aiohttp.ClientSession() as session:
        image_url = await fetch_nekos_image(session, category)
        if not image_url:
            await ctx.send("Failed to get image.")
            return

    cache_buster = random.randint(100000, 999999)
    image_url_with_cb = f"{image_url}?cb={cache_buster}"

    embed = discord.Embed(title=f"Random {category.capitalize()}", color=discord.Color.red())
    embed.set_image(url=image_url_with_cb)
    await ctx.send(embed=embed)

# ---------- Pornhub previews command ----------
async def fetch_pornhub_previews(search_term):
    url = f"https://www.pornhub.com/video/search?search={search_term}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()
            soup = BeautifulSoup(text, "html.parser")

            videos = soup.find_all("div", class_="phimage")

            previews = []
            for video in videos:
                img = video.find("img")
                if img:
                    thumb_url = img.get("data-src") or img.get("src")
                    if thumb_url:
                        previews.append(thumb_url)
            return previews

@bot.command()
@nsfw_check()
async def ptn(ctx, *, search: str = None):
    if not search:
        await ctx.send("Please provide a search term.")
        return

    try:
        previews = await fetch_pornhub_previews(search)
        if not previews:
            await ctx.send("No previews found for your search.")
            return

        chosen_preview = random.choice(previews)

        embed = discord.Embed(
            title=f"Pornhub preview for '{search}'",
            color=discord.Color.red()
        )
        embed.set_image(url=chosen_preview)
        embed.set_footer(text="Source: Pornhub")

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error fetching previews: {e}")

# ---------- Waifu.pics NSFW command ----------
@bot.command()
@nsfw_check()
async def wpic(ctx, category: str = None):
    valid_categories = {"waifu", "neko", "trap", "blowjob"}

    if category is None:
        category = random.choice(list(valid_categories))
    else:
        category = category.lower()
        if category not in valid_categories:
            await ctx.send(f"Invalid category! Choose from: {', '.join(valid_categories)}")
            return

    async with aiohttp.ClientSession() as session:
        url = f"https://api.waifu.pics/nsfw/{category}"
        async with session.get(url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch image.")
                return
            data = await resp.json()
            image_url = data.get("url")

    embed = discord.Embed(
        title=f"NSFW {category.capitalize()} from waifu.pics",
        color=discord.Color.purple()
    )
    embed.set_image(url=image_url)
    embed.set_footer(text="Powered by waifu.pics")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def yandere(ctx, *, tags: str = None):
    # Format tags for URL
    tag_string = "+".join(tags.split()) if tags else ""
    base_url = "https://yande.re/post.json"
    query = f"?limit=100&tags=rating:explicit+{tag_string}"

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url + query) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from yande.re.")
                return
            try:
                results = await resp.json()
            except:
                await ctx.send("Failed to parse Yande.re response.")
                return

    if not results:
        await ctx.send("No results found for those tags.")
        return

    # Pick a random image from the results
    post = random.choice(results)
    image_url = post.get("file_url")
    preview_url = post.get("preview_url")
    post_id = post.get("id")

    if not image_url:
        await ctx.send("No image found in the selected post.")
        return

    embed = discord.Embed(
        title="Yande.re Result",
        url=f"https://yande.re/post/show/{post_id}",
        description=f"Tags: `{post.get('tags')[:250]}...`",
        color=discord.Color.dark_magenta()
    )
    embed.set_image(url=image_url if image_url.endswith((".png", ".jpg", ".jpeg")) else preview_url)
    embed.set_footer(text="Source: yande.re")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def gelbooru(ctx, *, tags: str = None):
    base_url = "https://gelbooru.com/index.php"
    limit = 100

    # Compose tags query, add rating:explicit for NSFW
    query_tags = " ".join(tags.split()) if tags else ""
    full_tags = f"{query_tags} rating:explicit"

    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": 1,
        "limit": limit,
        "tags": full_tags,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Gelbooru.")
                return
            try:
                data = await resp.json()
            except:
                await ctx.send("Failed to parse Gelbooru response.")
                return

    posts = data if isinstance(data, list) else data.get("post") or []

    if not posts:
        await ctx.send("No results found for those tags.")
        return

    # Pick random post
    post = random.choice(posts)

    # Extract image url
    file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
    post_id = post.get("id")
    tags_str = post.get("tags", "")

    if not file_url:
        await ctx.send("No image URL found in the post.")
        return

    # Check if the URL is a video type
    video_extensions = (".mp4", ".webm", ".gif")

    if file_url.endswith(video_extensions):
        # Send the video link as a clickable message instead of embedding
        await ctx.send(f"Gelbooru video post: [Click here to view]({file_url})")
    else:
        embed = discord.Embed(
            title="Gelbooru Result",
            url=f"https://gelbooru.com/index.php?page=post&s=view&id={post_id}",
            description=f"Tags: `{tags_str[:250]}...`" if tags_str else None,
            color=discord.Color.dark_red()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: Gelbooru")

        await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def danbooru(ctx, *, tags: str = None):
    base_url = "https://danbooru.donmai.us/posts.json"
    limit = 100

    tag_string = " ".join(tags.split()) if tags else ""
    params = {
        "limit": limit,
        "tags": f"{tag_string} rating:explicit"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Danbooru.")
                return
            try:
                data = await resp.json()
            except Exception:
                await ctx.send("Failed to parse Danbooru response.")
                return

    if not data:
        await ctx.send("No results found for those tags.")
        return

    post = random.choice(data)
    file_url = post.get("file_url") or post.get("large_file_url") or post.get("preview_file_url")
    post_id = post.get("id")
    tag_string = post.get("tag_string", "")

    if not file_url:
        await ctx.send("No image URL found in the post.")
        return

    video_exts = (".mp4", ".webm", ".gif")

    if file_url.endswith(video_exts):
        # Send direct link for video/gif files
        await ctx.send(f"Danbooru video post: [Click here to view]({file_url})")
    else:
        embed = discord.Embed(
            title="Danbooru Result",
            url=f"https://danbooru.donmai.us/posts/{post_id}",
            description=f"Tags: `{tag_string[:250]}...`" if tag_string else None,
            color=discord.Color.dark_red()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: Danbooru")

        await ctx.send(embed=embed)

@bot.command()
async def invslavelink(ctx):
    try:
        await ctx.author.send("[Link here.](https://discord.com/oauth2/authorize?client_id=1380780651120296076&permissions=8&integration_type=0&scope=bot)")
    except discord.Forbidden:
        error = await ctx.send("I couldn't DM you. Please check your privacy settings.")
        await error.delete(delay=5)

    await ctx.message.delete(delay=0.1)

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
async def femboy(ctx):
    # Only allow in DMs
    if ctx.guild is not None:
        try:
            await ctx.author.send("This command can only be used in DMs. Please message me directly.")
        except discord.Forbidden:
            await ctx.reply("Please enable DMs to use this command.")
        return

    if reddit is None:
        await ctx.send("Reddit client not ready. Please try again shortly.")
        return

    subreddits = ["femboy", "femboy_irl", "FemboyGifs", "Femboys", "femboyNSFW"]
    chosen_sub = random.choice(subreddits)

    try:
        subreddit = await reddit.subreddit(chosen_sub)
        posts = [
            post async for post in subreddit.hot(limit=50)
            if not post.stickied and post.url.endswith((".jpg", ".png", ".gif", ".jpeg"))
        ]

        if not posts:
            await ctx.send("Couldn't find any femboy images right now.")
            return

        post = random.choice(posts)
        await ctx.send(post.url)

    except Exception as e:
        await ctx.send("An error occurred while fetching the image.")
        print(f"Error: {e}")

@bot.command()
@nsfw_check()
async def xbooru(ctx, *, tags: str = None):
    base_url = "https://xbooru.com/index.php"
    query_tags = " ".join(tags.split()) if tags else ""
    full_tags = f"{query_tags} rating:explicit"

    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": 1,
        "limit": 100,
        "tags": full_tags,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Xbooru.")
                return
            try:
                data = await resp.json()
            except:
                await ctx.send("Failed to parse Xbooru response.")
                return

    posts = data if isinstance(data, list) else data.get("post") or []
    if not posts:
        await ctx.send("No results found.")
        return

    post = random.choice(posts)
    file_url = post.get("file_url")
    post_id = post.get("id")
    tags_str = post.get("tags", "")

    if not file_url:
        await ctx.send("No image URL found.")
        return

    if file_url.endswith((".mp4", ".webm", ".gif")):
        await ctx.send(f"Xbooru video: [View]({file_url})")
    else:
        embed = discord.Embed(
            title="Xbooru Result",
            url=f"https://xbooru.com/index.php?page=post&s=view&id={post_id}",
            description=f"Tags: `{tags_str[:250]}...`" if tags_str else None,
            color=discord.Color.red()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: Xbooru")
        await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def realbooru(ctx, *, tags: str = None):

    base_url = "https://realbooru.com/index.php"
    limit = 100

    # Realbooru uses underscores, not spaces
    query_tags = "_".join(tags.split()) if tags else ""
    full_tags = query_tags  # don't add "rating:explicit"

    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "limit": limit,
        "tags": full_tags
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Realbooru.")
                return

            try:
                text_data = await resp.text()
                root = ET.fromstring(text_data)
                posts = root.findall(".//post")
            except Exception as e:
                await ctx.send("Failed to parse Realbooru response.")
                print(f"[Realbooru Error] {e}")
                return

    if not posts:
        await ctx.send("No results found for those tags.")
        return

    post = random.choice(posts)
    file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
    post_id = post.get("id")
    tag_str = post.get("tags", "")

    if not file_url:
        await ctx.send("No media URL found.")
        return

    if file_url.endswith((".mp4", ".webm", ".gif")):
        await ctx.send(f"Realbooru video post: [Click here to view]({file_url})")
    else:
        embed = discord.Embed(
            title="Realbooru Result",
            url=f"https://realbooru.com/index.php?page=post&s=view&id={post_id}",
            description=f"Tags: `{tag_str[:250]}...`" if tag_str else None,
            color=discord.Color.dark_red()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: Realbooru")

        await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
@commands.cooldown(1, random.randint(4, 7), commands.BucketType.user)
async def konachan(ctx, *, tags: str = None):
    base_url = "https://konachan.com/post.xml"
    query_tags = " ".join(tags.split()) if tags else ""
    full_tags = f"{query_tags} rating:explicit"

    params = {
        "limit": 100,
        "tags": full_tags,
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Konachan.")
                return
            text = await resp.text()

    try:
        root = ET.fromstring(text)
        posts = root.findall("post")
    except:
        await ctx.send("Error parsing XML from Konachan.")
        return

    if not posts:
        await ctx.send("No results found.")
        return

    post = random.choice(posts)
    file_url = post.attrib.get("file_url")
    post_id = post.attrib.get("id")
    tags_str = post.attrib.get("tags", "")

    if  not file_url:
        await ctx.send("No image URL found.")
        return

    if file_url.endswith((".mp4", ".webm", ".gif")):
        await ctx.send(f"Konachan video: [View]({file_url})")
    else:
        embed = discord.Embed(
            title="Konachan Result",
            url=f"https://konachan.com/post/show/{post_id}",
            description=f"Tags: `{tags_str[:250]}...`" if tags_str else None,
            color=discord.Color.red()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: Konachan")
        await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def tbib(ctx, *, tags: str = None):
    base_url = "https://tbib.org/index.php"
    limit = 100

    # Format tags: "tag1 tag2" → "tag1+tag2"
    formatted_tags = "+".join(tags.split()) if tags else ""
    full_tags = f"{formatted_tags}+rating:explicit"

    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": 1,
        "limit": limit,
        "tags": full_tags
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as resp:
            if resp.status != 200:
             await ctx.send("❌ Failed to fetch from TBIB.")
             return
    text = await resp.text()
    print(text)  # <-- Debug: see raw response
    try:
        data = await resp.json()
    except Exception as e:
        await ctx.send("❌ Failed to parse TBIB response.")
        print(f"Parsing error: {e}")
        return


    posts = data if isinstance(data, list) else data.get("post") or []

    if not posts:
        await ctx.send("No results found for those tags.")
        return

    post = random.choice(posts)
    file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
    post_id = post.get("id")
    tags_str = post.get("tags", "")

    if not file_url:
        await ctx.send("No image URL found in the post.")
        return

    if file_url.endswith((".mp4", ".webm", ".gif")):
        await ctx.send(f"TBIB video post: [Click here to view]({file_url})")
    else:
        embed = discord.Embed(
            title="TBIB Result",
            url=f"https://tbib.org/index.php?page=post&s=view&id={post_id}",
            description=f"Tags: `{tags_str[:250]}...`" if tags_str else None,
            color=discord.Color.dark_red()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: TBIB")

        await ctx.send(embed=embed)


# Run the bot
bot.run(BOT2)

import discord, os, random, aiohttp, asyncio, asyncpraw
from discord.ext import commands
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET
try:
    from redgifs import API as RedGifsAPI
    REDGIFS_AVAILABLE = True
except ImportError:
    REDGIFS_AVAILABLE = False

load_dotenv()
BOT2 = os.getenv("BOT2")

intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

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

LOG_FILE = "command_log_2.txt"

def log_command(ctx):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = f"{ctx.author.name}"
    command_used = ctx.message.content
    guild_name = ctx.guild.name if ctx.guild else "DM"

    log_line = f"[enigami chamber's] [{timestamp}] [{guild_name}] {username}: {command_used}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

@bot.event
async def on_command(ctx):
    log_command(ctx)

@bot.command()
async def help(ctx, category: str = None):
    if ctx.guild:
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    if ctx.guild and not ctx.channel.is_nsfw():
        try:
            await ctx.author.send(
                "!help command can only be used in NSFW channels. Try again in an age-restricted channel or here in DMs."
            )
        except discord.Forbidden:
            await ctx.reply("Please enable DMs to receive error messages.")
        return

    if category:
        category = category.lower()
        if category == "video" or category == "videos":
            embed = discord.Embed(title="🎥 Video Commands", color=discord.Color.red())
            embed.add_field(name="!ptn", value="Search Pornhub for videos and grabs their thumbnail.", inline=True)
            embed.add_field(name="!xnxx", value="Search XNXX for videos. Returns embed with thumbnail and direct link.", inline=True)
            embed.add_field(name="!xvideos", value="Search XVideos for videos. Returns embed with thumbnail and direct link.", inline=True)
            embed.add_field(name="!tube8", value="Search Tube8 for videos. Returns embed with thumbnail and direct link.", inline=True)
            embed.add_field(name="!youporn", value="Search YouPorn for videos. Returns embed with thumbnail and direct link.", inline=True)
            embed.add_field(name="!pornmd", value="Search PornMD for video clips. Returns embed with thumbnail and direct link.", inline=True)
            embed.set_footer(text="Use !help for all commands or !help <category> for specific categories.")

        elif category == "image" or category == "images":
            embed = discord.Embed(title="🖼️ Image Commands", color=discord.Color.blue())
            embed.add_field(name="!r34", value="Search Rule34 posts by tags. Use spaces to separate multiple tags. Supports embeds.", inline=True)
            embed.add_field(name="!nlife", value="Searches Nekos.life API for requested tags. Available categories: lewd, gasm, ngif, smug, fox_girl", inline=True)
            embed.add_field(name="!wpic", value="Get random NSFW image from waifu.pics. Categories: waifu, neko, trap, blowjob", inline=True)
            embed.add_field(name="!yandere", value="Search Yande.re for NSFW images by tags.", inline=True)
            embed.add_field(name="!gelbooru", value="Search Gelbooru for NSFW images by tags.", inline=True)
            embed.add_field(name="!danbooru", value="Search Danbooru for NSFW images by tags.", inline=True)
            embed.add_field(name="!xbooru", value="Search Xbooru for NSFW images by tags.", inline=True)
            embed.add_field(name="!realbooru", value="Search Realbooru for NSFW images by tags.", inline=True)
            embed.add_field(name="!konachan", value="Search Konachan for NSFW images by tags.", inline=True)
            embed.add_field(name="!sankaku", value="Search Sankaku Complex for NSFW images by tags.", inline=True)
            embed.add_field(name="!wallhaven", value="Search WallHaven for NSFW images using their API.", inline=True)
            embed.add_field(name="!hypnohub", value="Search HypnoHub for hypnosis-themed NSFW images.", inline=True)
            embed.set_footer(text="Use !help for all commands or !help <category> for specific categories.")

        elif category == "manga":
            embed = discord.Embed(title="📚 Manga Commands", color=discord.Color.purple())
            embed.add_field(name="!hitomi", value="Search Hitomi.la for NSFW manga galleries by tags.", inline=True)
            embed.add_field(name="!nhentai", value="Search NHentai for hentai manga by query. Returns gallery covers.", inline=True)
            embed.add_field(name="!hfound", value="Search Hentai Foundry for NSFW artwork by query.", inline=True)
            embed.add_field(name="!puruin", value="Search Pururin for NSFW manga galleries by tags.", inline=True)
            embed.set_footer(text="Use !help for all commands or !help <category> for specific categories.")

        elif category == "other" or category == "misc":
            embed = discord.Embed(title="🔧 Other Commands", color=discord.Color.green())
            embed.add_field(name="!femboy", value="Fetches a random femboy image from Reddit. Only works in DMs.", inline=True)
            embed.add_field(name="!redgifs", value="Search RedGifs for NSFW GIFs using their API.", inline=True)
            embed.add_field(name="!cdm", value="Clears all messages sent by the bot in the channel with 1.1 second intervals.", inline=True)
            embed.add_field(name="!github", value="Get the GitHub repository link.", inline=True)
            embed.add_field(name="!invslavelink", value="Get the bot invite link.", inline=True)
            embed.set_footer(text="Use !help for all commands or !help <category> for specific categories.")

        else:
            embed = discord.Embed(title="❓ Help Categories", description="Available categories: `video`, `images`, `manga`, `other`", color=discord.Color.orange())
            embed.add_field(name="Usage", value="`!help` - Show all commands\n`!help video` - Video commands\n`!help images` - Image commands\n`!help manga` - Manga commands\n`!help other` - Other commands", inline=False)
            embed.set_footer(text="Use these commands in NSFW channels only, or DMs.")

    else:
        embed = discord.Embed(title="⛧°. ⋆𓌹*♰*𓌺⋆. °⛧", description="**Categorized Help System**\nUse `!help <category>` for specific commands:\n• `!help video` - Video commands\n• `!help images` - Image commands\n• `!help manga` - Manga commands\n• `!help other` - Other commands", color=discord.Color.blue())
        embed.add_field(name="Quick Commands", value="`!r34`, `!ptn`, `!nlife`, `!wpic`, `!femboy`", inline=True)
        embed.add_field(name="Total Commands", value="25+ NSFW commands available", inline=True)
        embed.add_field(name="Example Usage", value="`!r34 big_boobs goth` for multiple tags\n`!ptn goth mom` to search Pornhub", inline=True)
        embed.set_footer(text="Use these commands in NSFW channels only, or DMs. Use !help <category> for detailed help.")

    if ctx.guild is None:
        await ctx.author.send(embed=embed)
    else:
        await ctx.send(embed=embed)

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

    post = random.choice(posts)

    file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
    post_id = post.get("id")
    tags_str = post.get("tags", "")

    if not file_url:
        await ctx.send("No image URL found in the post.")
        return

    video_extensions = (".mp4", ".webm", ".gif")

    if file_url.endswith(video_extensions):
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
async def github(ctx):
    """Sends the GitHub repo link for the bot.""" 
    await ctx.send("[GitHub](https://github.com/hexxedspider/kira-and-enigami)")

@bot.command()
async def invslavelink(ctx):
    try:
        await ctx.author.send("[Link here.](https://discord.com/oauth2/authorize?client_id=1130756120701579354&permissions=8&integration_type=0&scope=bot)")
    except discord.Forbidden:
        error = await ctx.send("I couldn't DM you. Please check your privacy settings.")
        await error.delete(delay=5)

    await ctx.message.delete(delay=0.1)

@bot.command()
async def cdm(ctx):
    """Clears all messages sent by the bot in the channel with 1.1 second intervals."""
    if ctx.guild and not ctx.author.guild_permissions.manage_messages:
        await ctx.send("You need 'Manage Messages' permission to use this command.")
        return

    deleted_count = 0
    async for message in ctx.channel.history(limit=100):
        if message.author == bot.user:
            try:
                await message.delete()
                deleted_count += 1
            except discord.NotFound:
                # Message might be too old or already deleted
                pass
            await asyncio.sleep(1.1)

    await ctx.send(f"Deleted {deleted_count} of my messages.", delete_after=5)

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

reddit = None 

async def cycle_status():
    await bot.wait_until_ready()
    statuses = [
        discord.Activity(type=discord.ActivityType.listening, name="what im told to do"),
        discord.CustomActivity(name="fuck it, mmh~"),
        discord.CustomActivity(name="im slightly unhinged but you already know that if you have me added"),
        discord.CustomActivity(name="AHH STOP- !"),
        discord.CustomActivity(name="im available for download as well, .github"),
        discord.CustomActivity(name="no i dont have weird time with kira, quit asking"),
        discord.CustomActivity(name="!help because ! is way better than .]"),
        discord.CustomActivity(name="i have a brother and sister"),
        discord.CustomActivity(name="use !invslavelink for my sister"),
    ]
    while not bot.is_closed():
        for status in statuses:
            await bot.change_presence(status=discord.Status.idle, activity=status)
            await asyncio.sleep(15)

@bot.event
async def on_ready():
    global reddit
    if reddit is None:
        reddit = asyncpraw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
    bot.loop.create_task(cycle_status())
    print(f"Logged in as {bot.user}, Reddit client initialized")

@bot.command()
async def femboy(ctx):
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

    query_tags = "_".join(tags.split()) if tags else ""
    full_tags = query_tags

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
    print(text)
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

@bot.command()
@nsfw_check()
async def sankaku(ctx, *, tags: str = None):
    base_url = "https://idol.sankakucomplex.com/post/index.json"
    limit = 100

    tag_string = " ".join(tags.split()) if tags else ""
    params = {
        "limit": limit,
        "tags": f"{tag_string} rating:explicit"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Sankaku.")
                return
            try:
                data = await resp.json()
            except Exception:
                await ctx.send("Failed to parse Sankaku response.")
                return

    if not data:
        await ctx.send("No results found for those tags.")
        return

    post = random.choice(data)
    file_url = post.get("file_url") or post.get("sample_url") or post.get("preview_url")
    post_id = post.get("id")
    tag_string = post.get("tags", [])

    if not file_url:
        await ctx.send("No image URL found in the post.")
        return

    video_exts = (".mp4", ".webm", ".gif")

    if file_url.endswith(video_exts):
        await ctx.send(f"Sankaku video post: [Click here to view]({file_url})")
    else:
        embed = discord.Embed(
            title="Sankaku Result",
            url=f"https://idol.sankakucomplex.com/post/show/{post_id}",
            description=f"Tags: `{', '.join(tag_string)[:250]}...`" if tag_string else None,
            color=discord.Color.blue()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: Sankaku Complex")

        await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def hitomi(ctx, *, tags: str = None):
    if not tags:
        await ctx.send("Please provide search tags for Hitomi.la.")
        return

    search_query = "+".join(tags.split())
    search_url = f"https://hitomi.la/search.html?{search_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Hitomi.la.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    galleries = soup.find_all("div", class_="gallery")

    if not galleries:
        await ctx.send("No results found for those tags.")
        return

    gallery = random.choice(galleries)
    link = gallery.find("a")
    if not link:
        await ctx.send("No gallery link found.")
        return

    gallery_url = "https://hitomi.la" + link.get("href")
    title = link.get("title", "Hitomi.la Gallery")

    # Try to get cover image
    cover_img = gallery.find("img")
    cover_url = None
    if cover_img:
        cover_url = "https:" + cover_img.get("src") if cover_img.get("src").startswith("//") else cover_img.get("src")

    embed = discord.Embed(
        title=title[:256],
        url=gallery_url,
        color=discord.Color.green()
    )
    if cover_url:
        embed.set_image(url=cover_url)
    embed.set_footer(text="Source: Hitomi.la")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def nhentai(ctx, *, query: str = None):
    if not query:
        await ctx.send("Please provide a search query for NHentai.")
        return

    search_url = f"https://nhentai.net/search/?q={query.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from NHentai.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    galleries = soup.find_all("div", class_="gallery")

    if not galleries:
        await ctx.send("No results found for that query.")
        return

    gallery = random.choice(galleries)
    link = gallery.find("a")
    if not link:
        await ctx.send("No gallery link found.")
        return

    gallery_url = "https://nhentai.net" + link.get("href")
    title = link.get("title", "NHentai Gallery")

    # Try to get cover image
    cover_img = gallery.find("img")
    cover_url = None
    if cover_img:
        cover_url = cover_img.get("src")
        if cover_url.startswith("//"):
            cover_url = "https:" + cover_url

    embed = discord.Embed(
        title=title[:256],
        url=gallery_url,
        color=discord.Color.purple()
    )
    if cover_url:
        embed.set_image(url=cover_url)
    embed.set_footer(text="Source: NHentai")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def hfound(ctx, *, query: str = None):
    if not query:
        await ctx.send("Please provide a search query for Hentai Foundry.")
        return

    search_url = f"https://www.hentai-foundry.com/search/pictures?query={query.replace(' ', '+')}&filter_by[]=rating&filter_multi[]=explicit"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Hentai Foundry.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    thumbnails = soup.find_all("img", class_="thumbnail")

    if not thumbnails:
        await ctx.send("No results found for that query.")
        return

    thumb = random.choice(thumbnails)
    img_url = thumb.get("src")
    if img_url.startswith("//"):
        img_url = "https:" + img_url

    # Get the parent link for full image
    parent = thumb.find_parent("a")
    if parent:
        full_url = "https://www.hentai-foundry.com" + parent.get("href")
    else:
        full_url = search_url

    embed = discord.Embed(
        title="Hentai Foundry Result",
        url=full_url,
        color=discord.Color.orange()
    )
    embed.set_image(url=img_url)
    embed.set_footer(text="Source: Hentai Foundry")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def puruin(ctx, *, tags: str = None):
    if not tags:
        await ctx.send("Please provide search tags for Pururin.")
        return

    search_query = "+".join(tags.split())
    search_url = f"https://pururin.io/search?q={search_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Pururin.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    galleries = soup.find_all("div", class_="gallery")

    if not galleries:
        await ctx.send("No results found for those tags.")
        return

    gallery = random.choice(galleries)
    link = gallery.find("a")
    if not link:
        await ctx.send("No gallery link found.")
        return

    gallery_url = "https://pururin.io" + link.get("href")
    title = link.get("title", "Pururin Gallery")

    # Try to get cover image
    cover_img = gallery.find("img")
    cover_url = None
    if cover_img:
        cover_url = cover_img.get("src")
        if cover_url.startswith("//"):
            cover_url = "https:" + cover_url

    embed = discord.Embed(
        title=title[:256],
        url=gallery_url,
        color=discord.Color.teal()
    )
    if cover_url:
        embed.set_image(url=cover_url)
    embed.set_footer(text="Source: Pururin")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def xnxx(ctx, *, search: str = None):
    if not search:
        await ctx.send("Please provide a search term for XNXX.")
        return

    search_url = f"https://www.xnxx.com/search/{search.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from XNXX.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    videos = soup.find_all("div", class_="thumb-block")

    if not videos:
        await ctx.send("No videos found for that search.")
        return

    video = random.choice(videos)
    link = video.find("a")
    if not link:
        await ctx.send("No video link found.")
        return

    video_url = "https://www.xnxx.com" + link.get("href")
    title = link.get("title", "XNXX Video")

    # Get thumbnail
    img = video.find("img")
    thumb_url = None
    if img:
        thumb_url = img.get("data-src") or img.get("src")
        if thumb_url and thumb_url.startswith("//"):
            thumb_url = "https:" + thumb_url

    embed = discord.Embed(
        title=title[:256],
        url=video_url,
        color=discord.Color.red()
    )
    if thumb_url:
        embed.set_image(url=thumb_url)
    embed.set_footer(text="Source: XNXX")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def xvideos(ctx, *, search: str = None):
    if not search:
        await ctx.send("Please provide a search term for XVideos.")
        return

    search_url = f"https://www.xvideos.com/?k={search.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from XVideos.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    videos = soup.find_all("div", class_="thumb-block")

    if not videos:
        await ctx.send("No videos found for that search.")
        return

    video = random.choice(videos)
    link = video.find("a")
    if not link:
        await ctx.send("No video link found.")
        return

    video_url = "https://www.xvideos.com" + link.get("href")
    title = link.get("title", "XVideos Video")

    # Get thumbnail
    img = video.find("img")
    thumb_url = None
    if img:
        thumb_url = img.get("data-src") or img.get("src")
        if thumb_url and thumb_url.startswith("//"):
            thumb_url = "https:" + thumb_url

    embed = discord.Embed(
        title=title[:256],
        url=video_url,
        color=discord.Color.blue()
    )
    if thumb_url:
        embed.set_image(url=thumb_url)
    embed.set_footer(text="Source: XVideos")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def tube8(ctx, *, search: str = None):
    if not search:
        await ctx.send("Please provide a search term for Tube8.")
        return

    search_url = f"https://www.tube8.com/search.html?q={search.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from Tube8.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    videos = soup.find_all("div", class_="thumb-block")

    if not videos:
        await ctx.send("No videos found for that search.")
        return

    video = random.choice(videos)
    link = video.find("a")
    if not link:
        await ctx.send("No video link found.")
        return

    video_url = "https://www.tube8.com" + link.get("href")
    title = link.get("title", "Tube8 Video")

    # Get thumbnail
    img = video.find("img")
    thumb_url = None
    if img:
        thumb_url = img.get("data-src") or img.get("src")
        if thumb_url and thumb_url.startswith("//"):
            thumb_url = "https:" + thumb_url

    embed = discord.Embed(
        title=title[:256],
        url=video_url,
        color=discord.Color.green()
    )
    if thumb_url:
        embed.set_image(url=thumb_url)
    embed.set_footer(text="Source: Tube8")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def youporn(ctx, *, search: str = None):
    if not search:
        await ctx.send("Please provide a search term for YouPorn.")
        return

    search_url = f"https://www.youporn.com/search/?query={search.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from YouPorn.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    videos = soup.find_all("div", class_="thumb-block")

    if not videos:
        await ctx.send("No videos found for that search.")
        return

    video = random.choice(videos)
    link = video.find("a")
    if not link:
        await ctx.send("No video link found.")
        return

    video_url = "https://www.youporn.com" + link.get("href")
    title = link.get("title", "YouPorn Video")

    # Get thumbnail
    img = video.find("img")
    thumb_url = None
    if img:
        thumb_url = img.get("data-src") or img.get("src")
        if thumb_url and thumb_url.startswith("//"):
            thumb_url = "https:" + thumb_url

    embed = discord.Embed(
        title=title[:256],
        url=video_url,
        color=discord.Color.purple()
    )
    if thumb_url:
        embed.set_image(url=thumb_url)
    embed.set_footer(text="Source: YouPorn")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def wallhaven(ctx, *, query: str = None):
    if not query:
        await ctx.send("Please provide a search query for WallHaven.")
        return

    api_url = f"https://wallhaven.cc/api/v1/search?q={query.replace(' ', '+')}&purity=001"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from WallHaven.")
                return
            try:
                data = await resp.json()
            except Exception:
                await ctx.send("Failed to parse WallHaven response.")
                return

    if not data.get("data"):
        await ctx.send("No images found for that query.")
        return

    image = random.choice(data["data"])
    image_url = image["path"]
    image_id = image["id"]
    resolution = image["resolution"]

    embed = discord.Embed(
        title=f"WallHaven Image ({resolution})",
        url=f"https://wallhaven.cc/w/{image_id}",
        color=discord.Color.teal()
    )
    embed.set_image(url=image_url)
    embed.set_footer(text="Source: WallHaven")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def hypnohub(ctx, *, tags: str = None):
    base_url = "https://hypnohub.net/index.php"
    limit = 100

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
                await ctx.send("Failed to fetch from HypnoHub.")
                return
            try:
                data = await resp.json()
            except:
                await ctx.send("Failed to parse HypnoHub response.")
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

    video_extensions = (".mp4", ".webm", ".gif")

    if file_url.endswith(video_extensions):
        await ctx.send(f"HypnoHub video post: [Click here to view]({file_url})")
    else:
        embed = discord.Embed(
            title="HypnoHub Result",
            url=f"https://hypnohub.net/index.php?page=post&s=view&id={post_id}",
            description=f"Tags: `{tags_str[:250]}...`" if tags_str else None,
            color=discord.Color.dark_purple()
        )
        embed.set_image(url=file_url)
        embed.set_footer(text="Source: HypnoHub")

        await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def pornmd(ctx, *, search: str = None):
    if not search:
        await ctx.send("Please provide a search term for PornMD.")
        return

    search_url = f"https://www.pornmd.com/search?query={search.replace(' ', '+')}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                await ctx.send("Failed to fetch from PornMD.")
                return
            text = await resp.text()

    soup = BeautifulSoup(text, "html.parser")
    videos = soup.find_all("div", class_="thumb")

    if not videos:
        await ctx.send("No videos found for that search.")
        return

    video = random.choice(videos)
    link = video.find("a")
    if not link:
        await ctx.send("No video link found.")
        return

    video_url = "https://www.pornmd.com" + link.get("href")
    title = link.get("title", "PornMD Video")

    # Get thumbnail
    img = video.find("img")
    thumb_url = None
    if img:
        thumb_url = img.get("data-src") or img.get("src")
        if thumb_url and thumb_url.startswith("//"):
            thumb_url = "https:" + thumb_url

    embed = discord.Embed(
        title=title[:256],
        url=video_url,
        color=discord.Color.orange()
    )
    if thumb_url:
        embed.set_image(url=thumb_url)
    embed.set_footer(text="Source: PornMD")

    await ctx.send(embed=embed)

@bot.command()
@nsfw_check()
async def redgifs(ctx, *, search: str = None):
    if not search:
        await ctx.send("Please provide a search term for RedGifs.")
        return

    if not REDGIFS_AVAILABLE:
        await ctx.send("RedGifs library not installed. Please install with: `pip install redgifs`")
        return

    try:
        api = RedGifsAPI()
        api.login()

        search_result = api.search(search, count=50)
        gifs = search_result.gifs

        if not gifs:
            await ctx.send(f"No results found for '{search}'.")
            return

        gif = random.choice(gifs)
        gif_url = gif.urls.hd or gif.urls.sd
        title = getattr(gif, 'title', 'RedGifs GIF')

        # Send the GIF URL directly (like in your selfbot)
        await ctx.send(f"**{title}**\n{gif_url}")

    except Exception as e:
        print(f"[ERROR] RedGifs API Error: {e}")
        await ctx.send("An error occurred while fetching RedGifs content.")

bot.run(BOT2)

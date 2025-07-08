import discord, os, random, asyncio, threading
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime

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
    username = f"{interaction.user.name}"
    command_used = getattr(interaction.command, "name", "unknown")
    guild_name = interaction.guild.name if interaction.guild else "DM"
    log_line = f"[enikami - enigami extended] [{timestamp}] [{guild_name}] {username}: {command_used}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Failed to log command: {e}")

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
        "saeya": "Here is an example of what Saeya looks like.",
        "muerte": "Here is an example of what Muerte looks like.",
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
    ]
    while not bot.is_closed():
        for status in statuses:
            await bot.change_presence(status=discord.Status.online, activity=status)
            await asyncio.sleep(15)

@bot.tree.command(name="github", description="Sends the GitHub repo link for the bot.")
async def github(interaction: discord.Interaction):
    """Sends the GitHub repo link for the bot."""
    await interaction.response.send_message("[GitHub](https://github.com/hexxedspider/kira-and-enigami)", ephemeral=True)


# these will not make sense if you used this bot since they're my emojis but still, you can replace them or remove this command entirely
@bot.tree.command(name="emj", description="Lists all bot emojis.")
async def listemojis(interaction: discord.Interaction):
    await interaction.response.send_message(
        "<a:twerk3:1384639220299075594><a:twerk2:1384636773006835712><a:twerk:1384636863901339718>\n<:thosewhoknow:1384639663473688748>\n<a:tease2:1384639182579962048><a:tease:1384636357758029855>\n<a:sucktit:1384637100569137242><a:sucka:1384635746299805721><a:canicallyoumommy:1384639196723019847>\n<a:spank4:1384636364695539762><a:spank3:1384636858096418906><a:spank2:1384636971972034633><a:spank:1384636980091949136>\n<a:pussylick:1384637029823942757>\n<:praying:1384637171214057633>\n<a:nsfwfuck12:1384639567037989038><a:nsfwfuck11:1384639030209282048><a:nsfwfuck10:1384636377282383902><a:nsfwfuck9:1384636542391292065><a:nsfwfuck8:1384636685807124500><a:nsfwfuck7:1384636714701684769><a:nsfwfuck6:1384636802044002354><a:nsfwfuck5:1384636813221560350><a:nsfwfuck4:1384636819580387560><a:nsfwfuck3:1384637070193987736><a:nsfwfuck2:1384637119506550834><a:nsfwfuck:1384637150871421141>\n<a:mommy:1384636896965296201>\n<a:lick3:1384636557654360074><a:lick2:1384637014762061874><a:lick:1384637114372722840>\n<a:handprint:1384639093694136340>\n<a:finger3:1384636385197031434><a:finger2:1384636914048700468><a:finger:1384637024236998707>\n<a:facesit:1384636672850788362>\n<a:cumshot3:1384639561258242059><a:cumshot2:1384636614613143663><a:cumshot:1384636766522179655>\n<a:creampie:1384637092747022530>\n<a:cowgirl:1384636736944083077>\n<:choking:1384636608485261402>\n<a:blowjob6:1384639228398276680><a:blowjob5:1384639208043446333><a:blowjob4:1384636513500790825><a:blowjob3:1384636597168902284><a:blowjob2:1384636724512161873><a:blowjob:1384637106877497554>\n<a:assgrab4:1384639086857551872><a:assgrab3:1384639008914538516><a:assgrab2:1384637126238535680><a:assgrab:1384637131552719058>\n<:9s:1384636006451515433><:8s:1384635996292780185><:7s:1384635814448857168><:6s:1384635808878825515><:5s:1384635802264404028><:4s:1384635790059114516><:3s:1384635770211401818><:2s:1384635764360614012><:1s:1384635726724993024><:10s:1384636014839988368>\n\n<a:kisskiss:1384636529401397349>",
        ephemeral=True
    )

IMAGE_FOLDER = "ggif"
MAX_ATTACHMENTS = 10

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Sync failed: {e}")
    bot.loop.create_task(cycle_status())
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="nd", description="Random NSFW dump.")
async def dump_images(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)

    if not os.path.exists(IMAGE_FOLDER):
        return await interaction.followup.send("Image folder not found.", ephemeral=True)

    image_files = [
        discord.File(os.path.join(IMAGE_FOLDER, f))
        for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4"))
    ]

    if not image_files:
        return await interaction.followup.send("No images found in the folder.", ephemeral=True)

    for i in range(0, len(image_files), MAX_ATTACHMENTS):
        chunk = image_files[i:i + MAX_ATTACHMENTS]
        await interaction.followup.send(files=chunk, ephemeral=True)

bot.run(bot3)
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import random
import aiohttp
import asyncpraw 
from discord.ui import View, Button
from discord import ButtonStyle, app_commands
from collections import defaultdict
import re
from tinydb import TinyDB, Query
from datetime import datetime, timedelta
import json
import time
import asyncio
from types import SimpleNamespace

# 🔧 Force working directory to script's folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

#db.json stores shit
db = TinyDB("db.json")  # Now in root directory

# ✅ Load environment variables
load_dotenv()
BOT1 = os.getenv("BOT1")

# line 8 pulls from the .env file, make your own .env file with this exact code "TOKEN=(your bot token)"
load_dotenv()

# actually grabbing the token from the .env file
BOT1 = os.getenv("BOT1")

# intents are basic permissions that the bot needs to function
# e.g. intents.message_content allows the bot to read the content of messages
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

# prefix, just like / but not.
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

# Path to your log file
LOG_FILE = "command_log_1.txt"

def log_command(ctx):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username = f"{ctx.author.name}"
    command_used = ctx.message.content
    guild_name = ctx.guild.name if ctx.guild else "DM"

    log_line = f"[kirabiter] [{timestamp}] [{guild_name}] {username}: {command_used}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)

@bot.event
async def on_command(ctx):
    log_command(ctx)

BALANCE_FILE = os.path.join("db.json")

if not os.path.exists(BALANCE_FILE) or os.path.getsize(BALANCE_FILE) == 0:
    with open(BALANCE_FILE, "w") as f:
        json.dump({}, f, indent=4)
    balances = {}

async def complete_investment(user_id, ctx):
    investment_table = db.table("investments")
    entry = investment_table.get(User.id == user_id)
    if not entry:
        return

    now = time.time()
    elapsed = now - entry["start_time"]
    remaining = max(0, 300 - elapsed)

    await asyncio.sleep(remaining)

    profit = int(entry["amount"] * 1.2)
    balance = get_full_balance(user_id)
    new_wallet = balance["wallet"] + profit
    set_full_balance(user_id, new_wallet, balance["bank"])

    investment_table.remove(User.id == user_id)
    investments.pop(user_id, None)

    await ctx.send(f"<@{user_id}>, your investment of ${entry['amount']} returned ${profit}!")

investments = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    
    investment_table = db.table("investments")
    for entry in investment_table.all():
        user_id = entry["id"]
        # If investment is already overdue, finish it instantly
        # If not, schedule it
        fake_ctx = await bot.fetch_user(int(user_id))
        if fake_ctx:
            investments[user_id] = bot.loop.create_task(complete_investment(user_id, fake_ctx))

@bot.event
async def on_ready():
    investment_table = db.table("investments")

    for entry in investment_table.all():
        user_id = entry["id"]
        try:
            user = await bot.fetch_user(int(user_id))
            fake_ctx = SimpleNamespace(author=user, send=user.send)
            investments[user_id] = bot.loop.create_task(complete_investment(user_id, fake_ctx))
        except Exception as e:
            print(f"Couldn't resume investment for {user_id}: {e}")


# Load balances
try:
    with open(BALANCE_FILE, "r") as f:
        balances = json.load(f)
except FileNotFoundError:
    balances = {}

def get_full_balance(user_id: str):
    user_data = balances.get(user_id)

    if isinstance(user_data, dict) and "wallet" in user_data and "bank" in user_data:
        return user_data
    else:
        # Convert old format (int balance only) to full format
        initial_wallet = user_data if isinstance(user_data, int) else 100
        balances[user_id] = {"wallet": max(initial_wallet, 0), "bank": 0}
        with open(BALANCE_FILE, "w") as f:
            json.dump(balances, f, indent=4)
        return balances[user_id]

def set_full_balance(user_id: str, wallet: int, bank: int):
    balances[user_id] = {"wallet": max(wallet, 0), "bank": max(bank, 0)}
    with open(BALANCE_FILE, "w") as f:
        json.dump(balances, f, indent=4)

#load shop items cause it didnt before
SHOP_FILE = "shop_items.json"

try:
    with open(SHOP_FILE, "r") as f:
        shop_items = json.load(f)
except FileNotFoundError:
    shop_items = {}

def get_balance(user_id: int) -> int:
    user_key = str(user_id)
    if user_key not in balances:
        balances[user_key] = {"wallet": 100, "bank": 0}
        with open(BALANCE_FILE, "w") as f:
            json.dump(balances, f, indent=4)
    return balances[user_key]["wallet"]

async def update_balance(user_id: int, amount: int, ctx: commands.Context = None):
    user_key = str(user_id)
    # Ensure user data exists
    if user_key not in balances:
        balances[user_key] = {"wallet": 100, "bank": 0}

    current = balances[user_key].get("wallet", 100)
    new_balance = max(current + amount, 0)
    balances[user_key]["wallet"] = new_balance

    # Save balances to file
    with open(BALANCE_FILE, "w") as f:
        json.dump(balances, f, indent=4)

    # Assign bankrupt role if balance just dropped to zero
    if current > 0 and new_balance == 0 and ctx is not None:
        await assign_bankrupt_role(ctx, user_id)

async def assign_bankrupt_role(ctx, user_id):
    guild = ctx.guild
    member = guild.get_member(user_id)
    if member is None:
        return

    # Find or create the role
    role_name = "Once Bankrupt"
    role = discord.utils.get(guild.roles, name=role_name)
    if role is None:
        try:
            role = await guild.create_role(name=role_name)
        except discord.Forbidden:
            await ctx.send("I don't have permission to create roles.")
            return

    # Assign the role
    if role not in member.roles:
        try:
            await member.add_roles(role)
            await ctx.send(f"{member.mention} has gone bankrupt and earned the **{role_name}** role.")
        except discord.Forbidden:
            await ctx.send("I can't assign roles. Please check my permissions.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    apply_bank_interest.start()

@bot.command()
@app_commands.describe(item="The item to buy from the shop")
async def invenilink(ctx):
    try:
        await ctx.author.send("[Link here.](https://discord.com/oauth2/authorize?client_id=1380716495767605429&permissions=8&integion_type=0&scope=bot)")
    except discord.Forbidden:
        error = await ctx.send("I couldn't DM you. Please check your privacy settings.")
        await error.delete(delay=5)

    await ctx.message.delete(delay=0.1)

class HelpView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=60)  # Timeout after 60 seconds
        self.embeds = embeds
        self.current = 0

    async def update_message(self, interaction):
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = (self.current + 1) % len(self.embeds)
        await self.update_message(interaction)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current = (self.current - 1) % len(self.embeds)
        await self.update_message(interaction)

# embed.add_field(name="", value="", inline=True)
@bot.command()
async def help(ctx):
    embed1 = discord.Embed(
        title="Help Page 1",
        description="Fun & Info Commands",
        color=discord.Color.blurple()
    )
    embed1 = discord.Embed(
    title="Help Page 1",
    description="Reply Commands - Replies to 'example' whenever it's messaged.",
    color=discord.Color.blurple()
)
    embed1.add_field(name="'peak'", value="peak", inline=True)
    embed1.add_field(name="'real'", value="real", inline=True)
    embed1.add_field(name="'kirabiter'", value="Replies with a random greeting to the mention of it's name.", inline=True)
    embed1.add_field(name="'...end it...'", value="Replies with a random sentence encouraging you.", inline=True)

    embed2 = discord.Embed(
    title="Help Page 2",
    description="Basic Commands",
    color=discord.Color.blurple()
)
    embed2.add_field(name=".die", value="Roll a 6 sided die.", inline=True)
    embed2.add_field(name=".cf", value="Flip a coin.", inline=True)
    embed2.add_field(name=".eightball", value="Ask the Eightball a question.", inline=True)
    embed2.add_field(name=".sava", value="Grabs the server's icon/avatar.", inline=True)
    embed2.add_field(name=".define", value="Get the definition of a term from Urban Dictionary.", inline=True)
    embed2.add_field(name=".ava", value="Grab the icon/avatar of a user (mention person).", inline=True)

    embed3 = discord.Embed(
    title="Help Page 3",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed3.add_field(name=".userinfo", value="Get info about a user.", inline=True)
    embed3.add_field(name=".serverinfo", value="Get info about the server.", inline=True)
    embed3.add_field(name=".uinfcmd", value="This will send an embed with what 'userinfo' will return.", inline=True)
    embed3.add_field(name=".dminfo", value="Returns a message with the info of your user, but tweaked to work in DMs.", inline=True)
    embed3.add_field(name=".rps", value="Play rock paper scissors against the bot, also pairs with .rpsstats. Rewards money.", inline=True)
    embed3.add_field(name=".red", value="Fetches media from a subreddit. Example: .red aww image/gif - .red [nsfw subreddit] image/gif true.", inline=True)

    embed4 = discord.Embed(
    title="Help Page 4",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed4.add_field(name=".balance", value="Shows you the current amount of currency you have.", inline=True)
    embed4.add_field(name=".gamble", value="50 percent chance of either winning or losing, add the amount you'd like to bet after typing .gamble.", inline=True)
    embed4.add_field(name=".daily", value="Gives a daily bonus of 100.", inline=True)
    embed4.add_field(name=".say", value="Forces the bot to say your message in the same channel, and it deletes your original message.", inline=True)
    embed4.add_field(name=".github", value="Sends a link to the bot's github (all three are in the repo').", inline=True)

    embed5 = discord.Embed(
    title="Help Page 5",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed5.add_field(name=".shop", value="Sends an embed with the current shop.", inline=True)
    embed5.add_field(name=".buy", value="Buy something from the shop.", inline=True)
    embed5.add_field(name=".inventory", value="Shows off your inventory of tags.", inline=True)
    embed5.add_field(name=".sell", value="Sells an item you have.", inline=True)
    embed5.add_field(name=".cfmilestones", value="Shows milestones of coinflips and the attached roles.", inline=True)
    embed5.add_field(name=".cfstats", value="Shows your coinflip stats.", inline=True)

    embed6 = discord.Embed(
    title="Help Page 6",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed6.add_field(name=".bet", value="Starts a coinflip challenge for a specified amount of money.", inline=True)
    embed6.add_field(name=".acceptbet", value="Accepts a coinflip challenge from another user.", inline=True)
    embed6.add_field(name=".bailout", value="Only able to be used if you have no money, 12h cooldown, awards $50.", inline=True)
    # Create the view with embeds
    view = HelpView([embed1, embed2, embed3, embed4, embed5, embed6])
    await ctx.send(embed=embed1, view=view)

@bot.command()
async def die(ctx):
    roll = random.randint(1, 6)
    await ctx.send(f"🎲 You rolled a {roll}!")

@bot.command()
async def uinfcmd(ctx):
    embed = discord.Embed(
        title="User Info Command",
        description="This command provides detailed information about a user.",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Username and Discriminator.", value="Exactly what it says, discrim will always return a 0 as they don't use it anymore, only on bots and unused accounts.", inline=False)
    embed.add_field(name="ID", value="Grants the userid, which typically isn't useful.", inline=False)
    embed.add_field(name="Top Role", value="The highest role someone has, for non-staff it'll typically be a color role.", inline=False)
    embed.add_field(name="Joined server and discord.", value="Exactly as it says.", inline=False)

    embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
    await ctx.send(embed=embed)
@bot.command()
async def dminfo(ctx, member: discord.Member = None):
    member = member or ctx.author  # Default to the person who ran the command

    embed = discord.Embed(
        title=f"User Info: {member}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.add_field(name="Username", value=member.name, inline=True)
    embed.add_field(name="Discriminator", value=member.discriminator, inline=True)
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Joined Discord", value=member.created_at.strftime("%b %d, %Y"), inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author  # Default to the person who ran the command

    embed = discord.Embed(
        title=f"User Info: {member}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.add_field(name="Username", value=member.name, inline=True)
    embed.add_field(name="Discriminator", value=member.discriminator, inline=True)
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"), inline=False)
    embed.add_field(name="Joined Discord", value=member.created_at.strftime("%b %d, %Y"), inline=False)

    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Normalize: lowercase, remove punctuation, strip extra spaces
    msg_content = re.sub(r'[^\w\s]', '', message.content.lower()).strip()

    if msg_content == "real":
        await message.reply("real")

    elif msg_content == "peak":
        await message.reply("peak")

    elif "ending it" in msg_content:
        responses = [
            "DO IT, NO BALLS", "do it", "waiting for you to do it",
            "do it already", "do it, pussy", "do it, you won't",
            "do it, you won't do it", "do it, you won't do it, pussy"
        ]
        await message.reply(random.choice(responses))

    # If the bot is mentioned by name
    bot_names = [bot.user.name.lower()]
    if message.guild:
        member = message.guild.get_member(bot.user.id)
        if member and member.nick:
            bot_names.append(member.nick.lower())

    if any(name in msg_content for name in bot_names):
        greetings = [
            "wsp?", "wsp", "hey", "helloo", "hi", "yo", "LEAVE ME ALONE", "SHUT THE FUCK UP", "don't bother me",
            "what you trynna get into?", "leave me alone", "yea mane?", "don't speak my name",
            "you sound better when you're not talking", "please be quiet", "god you sound obnoxious", "yes honey?", "yes my darling?",
            "dont take my compliments to heart, im forced to say it.",
            "just came back from coolville, they ain't know you", "want to go down the slide with me?", "want to go on the swings? the playground's empty.",
            "just came back from coolville, they said you're the mayor", "lowkey dont know what im doing give me a sec", ".help is NOT my name, try again",
            "hold on im shoving jelly beans up my ass", "cant talk, im at the doctors, but tell me why they said i need to stop letting people finish in me ??"
            "cant talk rn, to make a long story short, im being chased for putting barbeque sauce on random people",
            "im at the dentist rn but they said i need to stop doing oral ??", "the aliens are coming, hide", "im coming, hide", "how the fuck does this thing work?"
            "i cnat fiind my glases, 1 sec", "i difnt fnid my glasess", "holy fuck shut up", "do you ever be quiet?", "will you die if you stop talking?", "yeah?", "what?",
            "i felt lonely for a long time, but then i bought a jetski", "Kirabiter, coming to a server near you soon!", "this is a secret!", "use .nsfw for a secret :P",
            "ay im at the chiropracters rn, but she told me i have to stop taking backshots, give me a sec",
        ]
        await message.reply(random.choice(greetings))

    await bot.process_commands(message)

@bot.command()
async def eightball(ctx, *, question: str):
    responses = [
        "Yes", "No", "maybe ?", "Definitely", "Absolutely not, even a cracked out person would agree with me", 
        "Ask again later, I'm jacking it.", "Yeah, probably", "Unlikely", "idk gang"
    ]
    await ctx.send(f"🎱 Question: {question}\nAnswer: {random.choice(responses)}")

@bot.command()
async def cf(ctx):
    await ctx.send(f"The coin landed on **{random.choice(['Heads', 'Tails'])}**!")

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"{guild.name}",
        description="Server Information",
        color=discord.Color.dark_red()
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Owner", value=guild.owner, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def ava(ctx, member: discord.Member = None):
    member = member or ctx.author
    avatar_url = member.avatar.url if member.avatar else "No avatar"
    await ctx.send(f"{member.mention}'s avatar: {avatar_url}")

@bot.command()
async def define(ctx, *, term: str):
    """Fetches the definition of a term from Urban Dictionary."""
    url = f"https://api.urbandictionary.com/v0/define?term={term}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                await ctx.send(f"Sorry, couldn't fetch definitions for **{term}**.")
                return
            data = await resp.json()

    if not data["list"]:
        await ctx.send(f"No results found for **{term}** on Urban Dictionary.")
        return

    # Take the top definition
    top_def = data["list"][0]
    definition = top_def["definition"]
    example = top_def.get("example", "")
    author = top_def.get("author", "Unknown")

    # Urban Dictionary definitions often contain [brackets], remove or replace them
    import re
    clean_def = re.sub(r"\[|\]", "", definition)
    clean_example = re.sub(r"\[|\]", "", example)

    embed = discord.Embed(
        title=f"Urban Dictionary: {term}",
        description=clean_def,
        color=discord.Color.purple()
    )
    if clean_example:
        embed.add_field(name="Example", value=clean_example, inline=False)
    embed.set_footer(text=f"Defined by {author}")

    await ctx.send(embed=embed)

reddit = None  # global placeholder

@bot.event
async def on_ready():
    global reddit
    if reddit is None:
        reddit = asyncpraw.Reddit(
            client_id="SpJjzgRg0fUK8TKAmGsWdw",
            client_secret="B88RbmU0BQ7dRc2LC1_3cGYeHbc3dw",
            user_agent="DiscordBot by u/suicidespiders"
        )
    print(f"Logged in as {bot.user}")

@bot.command()
async def red(ctx, subreddit: str = "subreddit", media_type: str = None, nsfw: bool = False):
    global reddit
    if reddit is None:
        await ctx.send("Reddit client not ready yet, please try again later.")
        return

    # Check if the subreddit is marked as NSFW and if the channel allows it
    if nsfw:
        # Only allow NSFW content in guild channels that are marked NSFW
        if not isinstance(ctx.channel, discord.TextChannel) or not ctx.channel.is_nsfw():
            await ctx.send("This channel is not marked as NSFW. NSFW content can only be requested in age-restricted channels.")
            return


    try:
        subreddit_obj = await reddit.subreddit(subreddit)
        posts = [post async for post in subreddit_obj.hot(limit=100)]

        filtered_posts = []
        for post in posts:
            url = post.url.lower()

            # Enforce NSFW preference
            if (not nsfw and post.over_18) or (nsfw and not post.over_18):
                continue

            if media_type == "image" and url.endswith((".jpg", ".jpeg", ".png", ".webp", ".webm")):
                filtered_posts.append(post)
            elif media_type == "gif" and url.endswith(".gif"):
                filtered_posts.append(post)
            elif media_type == "video" and post.is_video:
                filtered_posts.append(post)
            elif media_type is None:
                if post.is_video or hasattr(post, 'gallery_data') or url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                    filtered_posts.append(post)

        if not filtered_posts:
            await ctx.send(f"No matching media found in r/{subreddit}.")
            return

        chosen = random.choice(filtered_posts)
        embed = discord.Embed(title=chosen.title, url=chosen.url, color=discord.Color.orange())
        embed.set_footer(text=f"From r/{subreddit} | 👍 {chosen.score} | 💬 {chosen.num_comments}")

        if chosen.is_video:
            video_url = chosen.media["reddit_video"]["fallback_url"]
            embed.description = f"[Video Link]({video_url})\n*Videos can't be embedded in Discord.*"
            embed.set_image(url=chosen.thumbnail if chosen.thumbnail.startswith("http") else discord.Embed.Empty)
        elif hasattr(chosen, 'gallery_data'):
            ids = [item['media_id'] for item in chosen.gallery_data['items']]
            meta = chosen.media_metadata
            if meta and ids:
                img_url = meta[ids[0]]['s']['u'].replace('&amp;', '&')
                embed.set_image(url=img_url)
        else:
            embed.set_image(url=chosen.url)

        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"Error fetching from Reddit: {e}")

@bot.command()
async def sava(ctx, *, user: discord.User = None):
    user = user or ctx.author

    pfp_url = user.display_avatar.url

    embed = discord.Embed(
        title=f"{user.display_name}'s Profile Picture",
        color=discord.Color.blue()
    )
    embed.set_image(url=pfp_url)

    await ctx.send(embed=embed)

db = TinyDB('db.json')
balances_table = db.table('balances')
User = Query()

rps_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0})

@bot.command()
async def rps(ctx):
    class RPSView(View):
        def __init__(self, user):
            super().__init__(timeout=30)
            self.user = user

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.user:
                await interaction.response.send_message("This is not your game!", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="Rock", style=ButtonStyle.primary)
        async def rock(self, interaction: discord.Interaction, button):
            await play_game(interaction, "rock", self.user)

        @discord.ui.button(label="Paper", style=ButtonStyle.success)
        async def paper(self, interaction: discord.Interaction, button):
            await play_game(interaction, "paper", self.user)

        @discord.ui.button(label="Scissors", style=ButtonStyle.danger)
        async def scissors(self, interaction: discord.Interaction, button):
            await play_game(interaction, "scissors", self.user)

    async def play_game(interaction, user_choice, user):
        choices = ["rock", "paper", "scissors"]
        bot_choice = random.choice(choices)

        WIN_REWARD = 50
        LOSS_PENALTY = 25
        TIE_REWARD = 25

        user_id = str(user.id)

        # Load balance data (wallet + bank)
        balance_data = get_full_balance(user_id)
        wallet = balance_data.get("wallet", 0)
        bank = balance_data.get("bank", 0)

        if user_choice == bot_choice:
            outcome = "It's a tie!"
            rps_stats[user.id]["ties"] += 1
            wallet += TIE_REWARD
            coin_change = TIE_REWARD
        elif (
            (user_choice == "rock" and bot_choice == "scissors") or
            (user_choice == "paper" and bot_choice == "rock") or
            (user_choice == "scissors" and bot_choice == "paper")
        ):
            outcome = "You won!"
            rps_stats[user.id]["wins"] += 1
            wallet += WIN_REWARD
            coin_change = WIN_REWARD
        else:
            outcome = "I win! Better luck next time."
            rps_stats[user.id]["losses"] += 1
            wallet = max(wallet - LOSS_PENALTY, 0)
            coin_change = -LOSS_PENALTY

        # Save updated wallet and bank
        set_full_balance(user_id, wallet, bank)

        stats = rps_stats[user.id]
        stats_msg = f"Wins: {stats['wins']}, Losses: {stats['losses']}, Ties: {stats['ties']}"
        coin_msg = f"You {'gained' if coin_change > 0 else 'lost'} ${abs(coin_change)}."

        await interaction.response.edit_message(
            content=(
                f"You chose **{user_choice}**.\nI chose **{bot_choice}**.\n\n"
                f"{outcome}\n\n{coin_msg}\n\n📊 **Your RPS Stats:** {stats_msg}"
            ),
            view=None
        )

    await ctx.send("Let's play Rock Paper Scissors! Choose one:", view=RPSView(ctx.author))

@bot.command()
async def rpsstats(ctx, member: discord.Member = None):
    member = member or ctx.author  # Defaults to command user
    stats = rps_stats.get(member.id)

    if not stats:
        await ctx.send(f"No RPS stats found for {member.display_name} yet.")
        return

    embed = discord.Embed(
        title=f"🧾 Rock Paper Scissors Stats for {member.display_name}",
        description=(
            f"**Wins:** {stats['wins']}\n"
            f"**Losses:** {stats['losses']}\n"
            f"**Ties:** {stats['ties']}"
        ),
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

# Kick command
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member.display_name} has been kicked. Reason: {reason or 'No reason provided'}")
    except Exception as e:
        await ctx.send(f"Failed to kick {member.display_name}. Error: {e}")

# Ban command
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"{member.display_name} has been banned. Reason: {reason or 'No reason provided'}")
    except Exception as e:
        await ctx.send(f"Failed to ban {member.display_name}. Error: {e}")

# Unban command
@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = await ctx.guild.bans()
    member_name = member_name.lower()

    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name.lower() == member_name or f"{user.name.lower()}#{user.discriminator}" == member_name:
            try:
                await ctx.guild.unban(user)
                await ctx.send(f"Unbanned {user.name}#{user.discriminator}")
                return
            except Exception as e:
                await ctx.send(f"Could not unban {user.name}. Error: {e}")
                return
    await ctx.send(f"User '{member_name}' not found in banned list.")

# Mute command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await ctx.send("'Muted' role not found! Please create one and set its permissions properly.")
        return

    if muted_role in member.roles:
        await ctx.send(f"{member.display_name} is already muted.")
        return

    try:
        await member.add_roles(muted_role, reason=reason)
        await ctx.send(f"{member.display_name} has been muted. Reason: {reason or 'No reason provided'}")
    except Exception as e:
        await ctx.send(f"Failed to mute {member.display_name}. Error: {e}")

# Unmute command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await ctx.send("'Muted' role not found! Please create one and set its permissions properly.")
        return

    if muted_role not in member.roles:
        await ctx.send(f"{member.display_name} is not muted.")
        return

    try:
        await member.remove_roles(muted_role)
        await ctx.send(f"{member.display_name} has been unmuted.")
    except Exception as e:
        await ctx.send(f"Failed to unmute {member.display_name}. Error: {e}")

# Clear command (bulk delete messages)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount <= 0:
        await ctx.send("Please specify a positive number of messages to delete.")
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to delete the command message too
        await ctx.send(f"Deleted {len(deleted)-1} messages.", delete_after=5)
    except Exception as e:
        await ctx.send(f"Failed to delete messages. Error: {e}")

@bot.command()
async def cleardm(ctx, amount: int = 5):
    if ctx.guild is not None:
        await ctx.send("This command is for DMs only.")
        return

    deleted_count = 0
    async for message in ctx.channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()
            deleted_count += 1
            if deleted_count >= amount:
                break
    await ctx.send(f"Deleted {deleted_count} messages I sent in this DM.", delete_after=5)

@bot.command()
async def say(ctx, *, message):
    """Repeats the user's message."""
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
        await ctx.send(f"{role.name} given to {member.mention}.")
    else:
        await ctx.send(f"Role '{role_name}' not found.")

user_balances = {}  # In-memory storage of user balances (use a database for persistence)

def get_balance(user_id):
    result = db.get(User.id == user_id)
    if result is None:
        db.insert({"id": user_id, "balance": 100})
        return 100
    return result["balance"]

def set_balance(user_id, new_balance):
    if db.contains(User.id == user_id):
        db.update({"balance": new_balance}, User.id == user_id)
    else:
        db.insert({"id": user_id, "balance": new_balance})

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    data = get_full_balance(user_id)
    wallet = data.get("wallet", 0)
    bank = data.get("bank", 0)
    await ctx.send(f"{ctx.author.mention}, your wallet has ${wallet} and your bank has ${bank}.")

@bot.command()
async def gamble(ctx, amount: int):
    user_id = str(ctx.author.id)
    data = get_full_balance(user_id)
    balance = data.get("wallet", 0)

    if amount <= 0:
        await ctx.send("Please enter a valid amount to gamble.")
        return

    if amount > balance:
        await ctx.send("You don't have enough money.")
        return

    # Gamble result
    if random.random() < 0.5:
        new_balance = balance - amount
        result = f"You lost ${amount}."
    else:
        new_balance = balance + amount
        result = f"You won ${amount}!"

    data["wallet"] = new_balance
    set_full_balance(user_id, data["wallet"], data.get("bank", 0))

    await ctx.send(f"{ctx.author.mention}, {result} New wallet balance: ${new_balance}.")

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()

    # Get user record or create default
    user_data = db.get(User.id == user_id)
    if not user_data:
        db.insert({"id": user_id, "last_claim": None})
        user_data = db.get(User.id == user_id)

    last_claim = user_data.get("last_claim")
    if last_claim:
        last_claim_time = datetime.fromisoformat(last_claim)
        diff = now - last_claim_time
        if diff < timedelta(hours=24):
            remaining = timedelta(hours=24) - diff
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(
                f"You already claimed your daily bonus! "
                f"Come back in {hours}h {minutes}m {seconds}s."
            )
            return

    # Daily bonus logic using full balance system
    bonus_amount = 100
    data = get_full_balance(user_id)
    new_wallet = data['wallet'] + bonus_amount
    set_full_balance(user_id, new_wallet, data['bank'])

    # Update last_claim timestamp
    db.update({"last_claim": now.isoformat()}, User.id == user_id)

    await ctx.send(f"{ctx.author.mention}, you received your daily bonus of ${bonus_amount}. Your new wallet balance is ${new_wallet}.")

@bot.command()
async def github(ctx):
    """Sends the GitHub repo link for the bot."""
    await ctx.send("Check out the bot's GitHub [here](https://github.com/hexxedspider/kira-and-enigami)")
@bot.command()
async def nsfw(ctx):
    """"Sends a secret message when the user types .nsfw."""
    await ctx.send("youre a fucking loser. you typed .nsfw, you know that right? you did this willingly. you could have just typed .help, but no, you had to type .nsfw. you know what? im not even mad, im just disappointed. you could have been a good person, but instead you chose to be a fucking loser. i hope youre happy with yourself. you know what? im not even going to delete this message, because you deserve to see it. you deserve to see how much of a fucking loser you are. i hope you feel ashamed of yourself. i hope you never type .nsfw again. i hope you never come back to this server. i hope you leave and never come back. fuck you.")

pending_coinflips = {}  # Stores challenges as {challenger_id: {"amount": int}}

def get_balance(user_id):
    result = db.get(User.id == user_id)
    if result is None:
        db.insert({"id": user_id, "balance": 100})
        return 100
    return result["balance"]

def set_balance(user_id, new_balance):
    if db.contains(User.id == user_id):
        db.update({"balance": new_balance}, User.id == user_id)
    else:
        db.insert({"id": user_id, "balance": new_balance})

# User starts a coinflip challenge
@bot.command()
async def bet(ctx, amount: int):
    user_id = str(ctx.author.id)

    if user_id in pending_coinflips:
        await ctx.send("You already have a pending coinflip.")
        return

    if amount <= 0:
        await ctx.send("Invalid amount.")
        return

    balance = get_balance(user_id)
    if amount > balance:
        await ctx.send("You don't have enough money.")
        return

    pending_coinflips[user_id] = {"amount": amount}
    await ctx.send(f"{ctx.author.mention} has started a coinflip for ${amount}! Type `.acceptbet @{ctx.author.name}` to accept.")

# Another user accepts the coinflip
@bot.command()
async def acceptbet(ctx, challenger: discord.Member):
    challenger_id = str(challenger.id)
    accepter_id = str(ctx.author.id)

    if challenger_id not in pending_coinflips:
        await ctx.send("That user has no pending coinflip.")
        return

    if challenger_id == accepter_id:
        await ctx.send("You can't accept your own coinflip.")
        return

    amount = pending_coinflips[challenger_id]["amount"]

    challenger_balance = get_balance(challenger_id)
    accepter_balance = get_balance(accepter_id)

    if accepter_balance < amount:
        await ctx.send("You don't have enough money to accept the coinflip.")
        return
    if challenger_balance < amount:
        await ctx.send("The challenger no longer has enough money.")
        del pending_coinflips[challenger_id]
        return

    # Flip the coin
    winner_id = random.choice([challenger_id, accepter_id])
    loser_id = accepter_id if winner_id == challenger_id else challenger_id

    set_balance(winner_id, get_balance(winner_id) + amount)
    set_balance(loser_id, get_balance(loser_id) - amount)

    del pending_coinflips[challenger_id]

    winner = await bot.fetch_user(int(winner_id))
    loser = await bot.fetch_user(int(loser_id))

    # Update wins
    new_wins = increment_cf_wins(str(winner.id))

    # Check for milestone
    if new_wins in milestone_roles:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        role_name = milestone_roles[new_wins]
        if role and role not in winner.roles:
            await winner.add_roles(role)
            await ctx.send(f"{winner.mention} reached {new_wins} coinflip wins and earned the **{role_name}** role!")

    await ctx.send(f"Coin flipped! {winner.mention} wins ${amount} from {loser.mention}!")

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def pay(ctx, member: discord.Member, amount: int):
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)

    if sender_id == receiver_id:
        await ctx.send("You can't pay yourself.")
        return

    if amount <= 0:
        await ctx.send("Amount must be greater than 0.")
        return

    # Load full balances
    sender_data = get_full_balance(sender_id)
    receiver_data = get_full_balance(receiver_id)

    sender_wallet = sender_data.get("wallet", 0)
    receiver_wallet = receiver_data.get("wallet", 0)

    if sender_wallet < amount:
        await ctx.send("You don't have enough money in your wallet.")
        return

    # Perform the transaction
    sender_wallet -= amount
    receiver_wallet += amount

    set_full_balance(sender_id, sender_wallet, sender_data.get("bank", 0))
    set_full_balance(receiver_id, receiver_wallet, receiver_data.get("bank", 0))

    await ctx.send(f"{ctx.author.mention} paid {member.mention} ${amount}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def reloadshop(ctx):
    global shop_items
    with open("shop.json", "r") as f:
        shop_items = json.load(f)
    await ctx.send("Shop items reloaded from file.")


@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="Shop", color=discord.Color.gold())
    for item_name, data in shop_items.items():
        embed.add_field(name=item_name.capitalize(), value=f"${data['price']}.\nRole: {data['role_name']}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item: str):
    item = item.lower()
    user_id = str(ctx.author.id)

    if ctx.guild is None:
        await ctx.send("This command can only be used in a server, not in DMs.")
        return

    if item not in shop_items:
        await ctx.send("That item doesn't exist in the shop.")
        return

    data = shop_items[item]
    price = data["price"]
    role_name = data["role_name"]

    # Find the role in the guild
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("This role is not set up in the server.")
        return

    if role in ctx.author.roles:
        await ctx.send("You already have this role.")
        return

    balance = get_balance(user_id)
    if balance < price:
        await ctx.send(f"You need ${price} to buy this role, but you have ${balance}.")
        return

    # Deduct money and add role
    set_balance(user_id, balance - price)
    await ctx.author.add_roles(role)
    await ctx.send(f"You bought the **{role_name}** role for ${price}! Enjoy!")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def createshoproles(ctx):
    created = []
    for item in shop_items.values():
        role_name = item["role_name"]
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.guild.create_role(name=role_name)
            created.append(role_name)
    if created:
        await ctx.send(f"Created roles: {', '.join(created)}")
    else:
        await ctx.send("All shop roles already exist.")

@bot.command()
async def inventory(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    owned_roles = []
    for item in shop_items.values():
        role = discord.utils.get(ctx.guild.roles, name=item["role_name"])
        if role and role in member.roles:
            owned_roles.append(role.name)

    if owned_roles:
        await ctx.send(f"{member.mention}'s Inventory: {', '.join(owned_roles)}")
    else:
        await ctx.send(f"{member.mention} doesn't own any shop roles yet.")

@bot.command()
async def sell(ctx, item: str):
    item = item.lower()
    user_id = str(ctx.author.id)

    if item not in shop_items:
        await ctx.send("That item doesn't exist in the shop.")
        return

    data = shop_items[item]
    role_name = data["role_name"]
    refund = data["price"] // 2

    # Find role in guild
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send("The role for this item doesn't exist.")
        return

     # Check if it's sellable
    if not data.get("sellable", True):  # default to True if missing
        await ctx.send("This item cannot be sold, as it's either a limited or an admin role.")
        return

    # Check if user owns the role
    if role not in ctx.author.roles:
        await ctx.send("You don't own this role.")
        return

    # Remove role and give refund
    await ctx.author.remove_roles(role)
    current_balance = get_balance(user_id)
    set_balance(user_id, current_balance + refund)

    await ctx.send(f"You sold **{role_name}** for ${refund}.")

cf_stats = db.table("coinflip_stats")

# Load milestones from JSON file
def load_milestones():
    try:
        with open('milestones.json', 'r') as f:
            data = json.load(f)
            # Keys are strings, convert to int
            return {int(k): v for k, v in data.items()}
    except FileNotFoundError:
        return {}

milestone_roles = load_milestones()

def get_cf_wins(user_id):
    user = cf_stats.get(Query().id == user_id)
    return user.get("wins", 0) if user else 0

def increment_cf_wins(user_id):
    current = get_cf_wins(user_id)
    cf_stats.upsert({"id": user_id, "wins": current + 1}, Query().id == user_id)
    return current + 1

@bot.command()
async def cfmilestones(ctx):
    if not milestone_roles:
        await ctx.send("No coinflip milestones are set.")
        return

    lines = []
    for wins, role_name in sorted(milestone_roles.items()):
        lines.append(f"**{wins} wins:** {role_name}")

    msg = "**Coinflip Milestones:**\n" + "\n".join(lines)
    await ctx.send(msg)

@bot.command()
async def cfstats(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    wins = get_cf_wins(str(member.id))
    embed = discord.Embed(
        title=f"Coinflip Stats for {member.display_name}",
        description=f"**Wins:** {wins}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def adminpanel(ctx):
    """Sends admin commands only if used in the admin channel."""
    admin_channel_id = 1380720256456200202  # Replace with your admin channel ID

    if ctx.channel.id != admin_channel_id:
        await ctx.send(f"Please use this command in <#{admin_channel_id}>.")
        return

    admin_commands = """
    **Admin Commands:**
    - `.kick @user [reason]` - Kick a user from the server.
    - `.ban @user [reason]` - Ban a user from the server.
    - `.unban username#1234` - Unban a user by their name and discriminator.
    - `.mute @user [reason]` - Mute a user by adding the Muted role.
    - `.unmute @user` - Remove the Muted role from a user.
    - `.clear <number>` - Bulk delete messages in the current channel.
    - `.giverole @user role_name` - Give a role to a user.
    - `.money @user role_name [amount]` - Give money to a user, only used for testing purposes.
    """

    await ctx.send(admin_commands)
    await ctx.message.delete()  # Optional: delete their command message

@bot.command()
@commands.has_permissions(administrator=True)
async def money(ctx, member: discord.Member, amount: int):
    """Gives a specified amount of money to a member."""
    user_id = str(member.id)
    if amount <= 0:
        await ctx.send("Please enter a valid amount to give.")
        return
    balance = get_balance(user_id)
    new_balance = balance + amount
    set_balance(user_id, new_balance)
    await ctx.send(f"Gave ${amount} to {member.mention}. New balance: ${new_balance}.")

from discord.ext import commands
import time

# Cooldown tracking (in-memory, resets on bot restart)
bailout_timestamps = {}

BAILOUT_AMOUNT = 50  # or whatever amount
BAILOUT_COOLDOWN = 43200  # 24 hours in seconds

bailout_timestamps = {}  # Ideally load/save this persistently

@bot.command()
async def bailout(ctx):
    user_id = str(ctx.author.id)
    data = get_full_balance(user_id)
    wallet = data.get("wallet", 0)
    bank = data.get("bank", 0)
    now = time.time()

    # Check both wallet and bank
    if wallet > 0 or bank > 0:
        await ctx.send("You still have money! Bailout is only for completely bankrupt users.")
        return

    last_used = bailout_timestamps.get(user_id, 0)
    remaining = int(BAILOUT_COOLDOWN - (now - last_used))
    if remaining > 0:
        hours, remainder = divmod(remaining, 3600)
        minutes, _ = divmod(remainder, 60)
        await ctx.send(f"You need to wait {hours}h {minutes}m before using bailout again.")
        return

    # Award bailout amount to wallet
    set_full_balance(user_id, BAILOUT_AMOUNT, 0)
    bailout_timestamps[user_id] = now

    role = discord.utils.get(ctx.guild.roles, name="Once Bankrupt")
    if role:
        await ctx.author.add_roles(role)

    await ctx.send(f"{ctx.author.mention}, you’ve been bailed out with ${BAILOUT_AMOUNT}!")

@bot.command()
async def kiratest(ctx):
    """sends the bot's test server"""
    await ctx.send("Kirabiter is being constantly tested, which extends to enigami, and enikami. If you want to join the test server, [click here or the invite underneath.](https://discord.gg/aCWhx4TK)")

@bot.command()
@commands.cooldown(1, 300, commands.BucketType.user)  # 5 min cooldown per user
async def rob(ctx, target: discord.Member):
    thief_id = str(ctx.author.id)
    target_id = str(target.id)

    if target.bot:
        await ctx.send("You can't rob bots! They're my sisters!")
        return

    if ctx.author.id == target.id:
        await ctx.send("You can't rob yourself, dingus.")
        return

    thief_balance = get_balance(thief_id)
    target_balance = get_balance(target_id)

    if target_balance < 100:
        await ctx.send(f"{target.mention} doesn't have enough money to rob.")
        return

    if thief_balance < 50:
        await ctx.send("You need at least $50 to attempt a robbery.")
        return

    success = random.random() < 0.8 # 20% success chance

    if success:
        stolen_amount = int(target_balance * 0.2)
        new_thief_balance = thief_balance + stolen_amount
        new_target_balance = target_balance - stolen_amount

        set_balance(thief_id, new_thief_balance)
        set_balance(target_id, new_target_balance)

        await ctx.send(f"Success! You stole $**{stolen_amount}** from {target.mention}!")
    else:
        lost_amount = int(thief_balance * 0.7)
        new_thief_balance = max(thief_balance - lost_amount, 0)
        set_balance(thief_id, new_thief_balance)

        await ctx.send(f"You failed the robbery and lost $**{lost_amount}**!")

@bot.command()
async def deposit(ctx, amount: int):
    user_id = str(ctx.author.id)

    # Ensure user data exists
    if user_id not in balances:
        balances[user_id] = {"wallet": 0, "bank": 0}

    data = balances[user_id]

    # Sanity checks
    if amount <= 0:
        await ctx.send("Please enter a positive amount to deposit.")
        return
    if amount > data.get("wallet", 0):
        await ctx.send("You don't have enough in your wallet to deposit that amount.")
        return

    # Deposit operation
    data["wallet"] -= amount
    data["bank"] += amount

    # Save
    with open(BALANCE_FILE, "w") as f:
        json.dump(balances, f, indent=4)

    await ctx.send(f"Deposited ${amount} into your bank account.")

@bot.command()
async def withdraw(ctx, amount: int):
    user_id = str(ctx.author.id)
    data = get_full_balance(user_id)

    if amount <= 0 or amount > data["bank"]:
        await ctx.send("Invalid amount to withdraw.")
        return

    data["wallet"] += amount
    data["bank"] -= amount
    set_full_balance(user_id, data["wallet"], data["bank"])

    await ctx.send(f"You withdrew ${amount} from your bank.")

@tasks.loop(minutes=1)
async def apply_bank_interest():
    INTEREST_CAP = 5000

    for user_id, data in balances.items():
        if isinstance(data, dict) and "bank" in data:
            current_bank = data["bank"]

            # Get last interest payout time or default to long ago
            last_claim_str = data.get("last_interest")
            last_claim = datetime.fromisoformat(last_claim_str) if last_claim_str else datetime.min

            now = datetime.utcnow()

            # Only apply interest if 24 hours have passed
            if now - last_claim >= timedelta(minutes=1):
                if current_bank > 0:
                    interest = int(current_bank * 1.2)
                    interest = min(interest, INTEREST_CAP)
                    data["bank"] += interest

                    # Update last interest payout time
                    data["last_interest"] = now.isoformat()

    with open(BALANCE_FILE, "w") as f:
        json.dump(balances, f, indent=4)

MAX_BANK_BALANCE = 100000

# Card values for blackjack
card_values = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10,
    "A": 11  # We'll handle Ace as 1 or 11 dynamically
}

def calculate_hand_value(hand):
    card_values = {
        "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
        "8": 8, "9": 9, "10": 10,
        "J": 10, "Q": 10, "K": 10,
        "A": 11
    }
    total = 0
    aces = 0
    for card in hand:
        total += card_values[card]
        if card == "A":
            aces += 1
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def draw_card(deck):
    return deck.pop(random.randint(0, len(deck) - 1))

@bot.command()
async def blackjack(ctx, bet: int = None):
    user_id = str(ctx.author.id)

    if bet is None:
        await ctx.send("Please specify an amount to bet.")
        return

    # Load user wallet balance (replace get_full_balance with your own function)
    data = get_full_balance(user_id)
    wallet = data.get("wallet", 0)

    if bet <= 0:
        await ctx.send("You can't bet nothing.")
        return
    if bet > wallet:
        await ctx.send("You don't have enough money to bet that amount.")
        return

    # Deduct bet immediately
    data["wallet"] -= bet
    set_full_balance(user_id, data["wallet"], data.get("bank", 0))

    deck = [str(n) for n in range(2, 11)] + ["J", "Q", "K", "A"] * 4
    player_hand = [draw_card(deck), draw_card(deck)]
    dealer_hand = [draw_card(deck), draw_card(deck)]

    class BlackjackView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.player_hand = player_hand
            self.dealer_hand = dealer_hand
            self.deck = deck
            self.bet = bet
            self.user_id = user_id

        def hand_str(self, hand):
            return ", ".join(hand)

        def game_result(self):
            player_val = calculate_hand_value(self.player_hand)
            dealer_val = calculate_hand_value(self.dealer_hand)

            if player_val > 21:
                return "Bust! You lose."
            elif dealer_val > 21:
                return "Dealer busts! You win!"
            elif player_val == dealer_val:
                return "It's a tie!"
            elif player_val > dealer_val:
                return "You win!"
            else:
                return "You lose!"

        async def update_balance(self, amount: int):
            data = get_full_balance(self.user_id)
            data["wallet"] = max(data.get("wallet", 0) + amount, 0)
            set_full_balance(self.user_id, data["wallet"], data.get("bank", 0))

        async def end_game(self, interaction, result_msg):
            if "win" in result_msg.lower():
                payout = self.bet * 2  # double the bet as winnings including original bet
                await self.update_balance(payout)
                updated_data = get_full_balance(self.user_id)
                payout_msg = f"You won ${payout}! You now have ${updated_data['wallet']} in your wallet."
            elif "tie" in result_msg.lower():
                payout = self.bet  # return original bet on tie
                await self.update_balance(payout)
                updated_data = get_full_balance(self.user_id)
                payout_msg = f"It's a tie! Your bet of ${self.bet} was returned. You now have ${updated_data['wallet']} in your wallet."
            else:
                updated_data = get_full_balance(self.user_id)
                payout_msg = f"You lost your bet of ${self.bet}. You now have ${updated_data['wallet']} in your wallet."

            await interaction.response.edit_message(
                content=(
                    f"Your hand: {self.hand_str(self.player_hand)} (Value: {calculate_hand_value(self.player_hand)})\n"
                    f"Dealer's hand: {self.hand_str(self.dealer_hand)} (Value: {calculate_hand_value(self.dealer_hand)})\n\n"
                    f"**{result_msg}**\n{payout_msg}"
                ),
                view=None
            )
            self.stop()

        @discord.ui.button(label="Hit", style=ButtonStyle.primary)
        async def hit(self, interaction, button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return

            self.player_hand.append(draw_card(self.deck))
            player_val = calculate_hand_value(self.player_hand)

            if player_val > 21:
                # Player busts, game ends
                await self.end_game(interaction, "Bust! You lose.")
            else:
                await interaction.response.edit_message(
                    content=(
                        f"Your hand: {self.hand_str(self.player_hand)} (Value: {player_val})\n"
                        f"Dealer's visible card: {self.dealer_hand[0]}\n\n"
                        "Hit or Stand?"
                    ),
                    view=self
                )

        @discord.ui.button(label="Stand", style=ButtonStyle.success)
        async def stand(self, interaction, button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("This isn't your game!", ephemeral=True)
                return

            dealer_val = calculate_hand_value(self.dealer_hand)
            while dealer_val < 17:
                self.dealer_hand.append(draw_card(self.deck))
                dealer_val = calculate_hand_value(self.dealer_hand)

            result_msg = self.game_result()
            await self.end_game(interaction, result_msg)

    view = BlackjackView()
    await ctx.send(
        f"You bet ${bet}.\n"
        f"Your hand: {view.hand_str(player_hand)} (Value: {calculate_hand_value(player_hand)})\n"
        f"Dealer's visible card: {dealer_hand[0]}\n\n"
        "Hit or Stand?",
        view=view
    )

def get_full_balance(user_id: str):
    user_data = balances.get(user_id)
    if isinstance(user_data, dict) and "wallet" in user_data and "bank" in user_data:
        return user_data
    else:
        # Convert old format (int) to full format
        initial_wallet = user_data if isinstance(user_data, int) else 100
        balances[user_id] = {"wallet": max(initial_wallet, 0), "bank": 0}
        return balances[user_id]

@bot.command()
async def invest(ctx, amount: int):
    user_id = str(ctx.author.id)
    data = get_full_balance(user_id)

    if amount <= 0:
        await ctx.send("Investment amount must be positive.")
        return

    if data["wallet"] < amount:
        await ctx.send("You don't have enough money in your wallet.")
        return

    # Check if already invested
    if user_id in investments:
        await ctx.send("You already have an active investment.")
        return

    # Deduct money
    new_wallet = data["wallet"] - amount
    set_full_balance(user_id, new_wallet, data["bank"])

    await ctx.send(f"You invested ${amount}. You now have ${new_wallet} in your wallet.")

    # Store investment with current timestamp
    start_time = time.time()
    investments[user_id] = {
        "task": bot.loop.create_task(complete_investment(ctx, user_id, amount)),
        "start_time": start_time,
        "duration": 300  # seconds (5 minutes)
    }

async def complete_investment(ctx, user_id, amount):
    await asyncio.sleep(300)  # 5 minutes
    profit = int(amount * 1.2)

    # Re-load balances after time delay
    updated = get_full_balance(user_id)
    new_wallet = updated["wallet"] + profit
    set_full_balance(user_id, new_wallet, updated["bank"])

    # Remove from active investments
    investments.pop(user_id, None)

    await ctx.send(f"{ctx.author.mention}, your ${amount} investment has grown to ${profit}!")

@bot.command()
async def timeinvest(ctx):
    user_id = str(ctx.author.id)
    if user_id not in investments:
        await ctx.send("You don't have any active investments right now.")
        return

    inv = investments[user_id]
    elapsed = time.time() - inv["start_time"]
    remaining = max(0, inv["duration"] - elapsed)
    minutes, seconds = divmod(int(remaining), 60)

    await ctx.send(f"Your investment will complete in {minutes}m {seconds}s.")

# runs the bot with the token from the .env file
bot.run(BOT1)
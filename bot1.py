from tinydb import TinyDB, Query

main_db = TinyDB("db.json")
balances_table = main_db.table("balances")
User = Query()

def get_balance(user_id: str):
    record = balances_table.get(User.user_id == user_id)
    if not record:
        balances_table.insert({"user_id": user_id, "wallet": 100, "bank": 0})
        return {"wallet": 100, "bank": 0}
    return {"wallet": record.get("wallet", 0), "bank": record.get("bank", 0)}

def set_balance(user_id: str, wallet: int, bank: int):
    if balances_table.contains(User.user_id == user_id):
        balances_table.update({"wallet": wallet, "bank": bank}, User.user_id == user_id)
    else:
        balances_table.insert({"user_id": user_id, "wallet": wallet, "bank": bank})

ROTTING_DURATION = 30

from functools import wraps
from datetime import datetime, timedelta
import time

def apply_rotting_curse(func):
    @wraps(func)
    async def wrapper(ctx, *args, **kwargs):
        user_id = str(ctx.author.id)
        curses = main_db.table("curses")
        curse_data = curses.get(Query().user_id == user_id)

        rotting_effect = 0.0
        if curse_data and curse_data["type"] == "rotting":
            elapsed = time.time() - curse_data["timestamp"]
            duration = 1800  # 30 minutes
            if elapsed < duration:
                rotting_effect = min(1.0, elapsed / duration)

        if "rotting_effect" not in kwargs:
            kwargs["rotting_effect"] = rotting_effect

        return await func(ctx, *args, **kwargs)

    return wrapper

#
#
# leaving this here as a note to myself
# make a .rant and .confess command that sends random messages
# confess is like kirabiters / the bots thoughts
# rant is the bot literally ranting about being a bot
#
#

import discord
from discord import ButtonStyle, app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os
import random
import aiohttp
import asyncpraw 
from discord.ui import View, Button
from collections import defaultdict, Counter
import re
from tinydb import TinyDB, Query
from datetime import datetime, timedelta
import json
import time
import asyncio
from types import SimpleNamespace
import dateutil.parser
import threading
import pytz
import ast
from functools import wraps
import yt_dlp

#db.json stores shit
main_db = TinyDB("db.json")
balances_table = main_db.table("balances")
marriages_table = main_db.table("marriages")
pending_proposals = {} 
vows_table = main_db.table("vows")
users = Query()
investments_table = main_db.table("investments")
User = Query()
Bingo = Query()
cooldowns_db = main_db.table('cooldowns')
cf_stats = main_db.table("coinflip_stats")
prestige_table = main_db.table("prestige")

# actually grabbing the token from the .env file
load_dotenv()
BOT1 = os.getenv("BOT1")
OWNID = os.getenv("OWNID")
FM_API = os.getenv("FM_API")
FM_USERNAME = os.getenv("FM_USERNAME")
REPORT_CHANNEL_ID = int(os.getenv("REPORT_CHANNEL_ID"))
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
GUILDID = int(os.getenv("GUILDID", 0))

# intents are basic permissions that the bot needs to function
# e.g. intents.message_content allows the bot to read the content of messages
intents = discord.Intents.all()
intents.message_content = True  # Required to read message content
intents.members = True

# prefix, just like / but not.
bot = commands.Bot(command_prefix=".", intents=intents, help_command=None)

def get_user_balance(user_id: str):
    return get_balance(user_id)

def set_user_balance(user_id: str, wallet: int, bank: int):
    set_balance(user_id, wallet, bank)

def get_full_balance(user_id: str):
    return get_balance(user_id)

def set_full_balance(user_id: str, wallet: int, bank: int):
    set_balance(user_id, wallet, bank)

def update_user_balance(user_id: str, amount: int):
    economy_table = main_db.table("economy")
    data = get_user_balance(user_id)

    new_wallet = max(0, data["wallet"] + amount)
    economy_table.update({"wallet": new_wallet}, Query().user_id == user_id)

def update_user_bank(user_id: str, amount: int):
    data = get_user_balance(user_id)
    new_bank = max(0, data.get("bank", 0) + amount)
    balances = main_db.table("balances")
    balances.upsert({"user_id": user_id, "wallet": data["wallet"], "bank": new_bank}, Query().user_id == user_id)

bot.heist_active = False
bot.heist_players = []
heist_cooldowns = {}

def parse_bet_amount(bet_input, wallet):
    bet_input = str(bet_input).lower().strip()
    if bet_input == "all":
        return wallet
    elif bet_input.endswith("p") and bet_input[:-1].isdigit():
        percent = int(bet_input[:-1])
        if percent in (25, 50, 75):
            return max(1, int(wallet * (percent / 100)))
    elif bet_input.isdigit():
        return int(bet_input)
    return None

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

investments = {}

bingo_active = False

# In-memory cooldown tracker, change to db.json later or something
heist_cooldowns = {}  # {user_id: datetime}

WELCOME_FILE = "wconfig.json"

#load shop items cause it didnt before, can use .reloadshop too
SHOP_FILE = "shop_items.json"

try:
    with open(SHOP_FILE, "r") as f:
        shop_items = json.load(f)
except FileNotFoundError:
    shop_items = {}

async def update_balance(user_id: int, amount: int, ctx: commands.Context = None):
    bal = get_balance(str(user_id))
    new_wallet = bal["wallet"] + amount
    set_balance(str(user_id), new_wallet, bal["bank"])

    if bal["wallet"] > 0 and new_wallet == 0 and ctx is not None:
        await assign_bankrupt_role(ctx, user_id)

async def assign_bankrupt_role(ctx, user_id):
    guild = ctx.guild
    member = guild.get_member(user_id)
    if member is None:
        return

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

@bot.command()
async def invlink(ctx):
    await ctx.author.send(f"[Link here.](https://discord.com/oauth2/authorize?client_id=1051357875521458246&permissions=8&integration_type=0&scope=bot)")

@bot.command()
async def invenilink(ctx):
    try:
        await ctx.author.send("[Link here.](https://discord.com/oauth2/authorize?client_id=949153090433605682&permissions=8&integration_type=0&scope=bot)")
    except discord.Forbidden:
        error = await ctx.send("I couldn't DM you. Please check your privacy settings.")
        await error.delete(delay=5)

    await ctx.message.delete(delay=0.1)

def get_prestige_bonuses(user_id):
    prestige_entry = prestige_table.get(Query().user_id == user_id)
    level = prestige_entry["level"] if prestige_entry else 0
    # Example: Each prestige gives +10% multiplier and +$1,000,000 cap
    multiplier = 1.0 + (level * 0.1)
    wallet_cap = 50_000_000_000_000 + (level * 250_000_000_000_000)
    bank_cap = 50_000_000_000_000 + (level * 250_000_000_000_000)
    return multiplier, wallet_cap, bank_cap

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
    embed1.set_footer(text=f"This menu disables in 60 seconds.")
    embed2 = discord.Embed(
    title="Help Page 2",
    description="Basic Commands",
    color=discord.Color.blurple()
)
    embed2.set_footer(text=f"This menu disables in 60 seconds.")
    embed2.add_field(name=".die", value="Roll a 6 sided die.", inline=True)
    embed2.add_field(name=".cf", value="Flip a coin.", inline=True)
    embed2.add_field(name=".eightball <question>", value="Ask the Eightball a question.", inline=True)
    embed2.add_field(name=".sava <@person>", value="Grabs the server's icon/avatar.", inline=True)
    embed2.add_field(name=".ava <@person>", value="Grab the icon/avatar of a user (mention person).", inline=True)
    embed2.add_field(name=".define <word>", value="Get the definition of a term from Urban Dictionary.", inline=True)

    embed3 = discord.Embed(
    title="Help Page 3",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed3.set_footer(text=f"This menu disables in 60 seconds.")
    embed3.add_field(name=".userinfo <@person>", value="Get info about a user.", inline=True)
    embed3.add_field(name=".serverinfo", value="Get info about the server.", inline=True)
    embed3.add_field(name=".uinfcmd", value="This will send an embed with what 'userinfo' will return.", inline=True)
    embed3.add_field(name=".dminfo", value="Returns a message with the info of your user, but tweaked to work in DMs.", inline=True)
    embed3.add_field(name=".rps", value="Play rock paper scissors against the bot, also pairs with .rpsstats. Rewards money.", inline=True)
    embed3.add_field(name=".red <subreddit> <image or gif> <IF NSFW: true>", value="Fetches media from a subreddit.", inline=True)

    embed4 = discord.Embed(
    title="Help Page 4",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed4.set_footer(text=f"This menu disables in 60 seconds.")
    embed4.add_field(name=".balance", value="Shows you the current amount of currency you have.", inline=True)
    embed4.add_field(name=".gamble <amount>", value="50 percent chance of either winning or losing.", inline=True)
    embed4.add_field(name=".daily", value="Gives a daily bonus of 100.", inline=True)
    embed4.add_field(name=".say", value="Forces the bot to say your message in the same channel, and it deletes your original message.", inline=True)
    embed4.add_field(name=".github", value="Sends a link to the bot's github (all three are in the repo').", inline=True)
    embed4.add_field(name=".helpme", value="Returns a random image (horror or liminal).")

    embed5 = discord.Embed(
    title="Help Page 5",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed5.set_footer(text=f"This menu disables in 60 seconds.")
    embed5.add_field(name=".shop", value="Sends an embed with the current shop.", inline=True)
    embed5.add_field(name=".buy <role>", value="Buy something from the shop.", inline=True)
    embed5.add_field(name=".inventory", value="Shows off your inventory of tags.", inline=True)
    embed5.add_field(name=".sell <role>", value="Sells an item you have.", inline=True)
    embed5.add_field(name=".cfmilestones", value="Shows milestones of coinflips and the attached roles.", inline=True)
    embed5.add_field(name=".cfstats", value="Shows your coinflip stats.", inline=True)

    embed6 = discord.Embed(
    title="Help Page 6",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)# embed6.add_field(name=".", value="", inline=True)
    
    embed6.set_footer(text=f"This menu disables in 60 seconds.")
    embed6.add_field(name=".bet <amount>", value="Starts a coinflip challenge.", inline=True)
    embed6.add_field(name=".acceptbet <@person>", value="Accepts a coinflip challenge from another user.", inline=True)
    embed6.add_field(name=".bailout", value="Only able to be used if you have no money, 12h cooldown, awards $50.", inline=True)
    embed6.add_field(name=".timeinvest", value="Shows how much longer until your investment is over.", inline=True)
    embed6.add_field(name=".blackjack <amount>", value="Play blackjack against the bot.", inline=True)
    embed6.add_field(name=".rob <@person>", value="5 minute cooldown, try to rob a person of money. 20 percent chance of being successful, lose money if not. ", inline=True)

    embed7 = discord.Embed(
    title="Help Page 7",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed7.set_footer(text=f"This menu disables in 60 seconds.")
    embed7.add_field(name=".report", value="Sends a message to a specified channel in the official test server.")
    embed7.add_field(name=".cleardm <amount>", value="Clears bot's messages, but this time in DMs. Defaults to 5.", inline=True)
    embed7.add_field(name=".kiratest", value="Sends an invite to the kirabiter test server.")
    embed7.add_field(name=".deposit <amount>", value="Put money into your bank to protect your money from being robbed.")
    embed7.add_field(name=".withdraw <amount>", value="Take money out the bank to spend on games, buy from .shop, or other things.")
    embed7.add_field(name=".invest <amount>", value="Stacks quickly, but each .1 multiplier adds 10 minutes.")

    embed8 = discord.Embed(
        title="Help Page 8",
        description="Fun & Info Commands",
        color=discord.Color.blurple()
)
    embed8.set_footer(text=f"This menu disables in 60 seconds.")
    embed8.add_field(name=".about", value="Sends an embed with various facts about the bot and the creator.")
    embed8.add_field(name=".kbsc", value="Directly download this bot's source code (may be broken, python file only).")
    embed8.add_field(name=".heist", value="Start a heist! Explained upon use, along with the Heist Guardian role.", inline=True)
    embed8.add_field(name=".joinheist", value="Join the ongoing heist.", inline=True)
    embed8.add_field(name=".leaveheist", value="Leave the heist you're in.", inline=True)
    embed8.add_field(name=".heistcrew", value="Shows your current crew, containing highest role, money, pfp, and name.", inline=True)

    embed9 = discord.Embed(
        title="Help Page 9",
        description="Fun & Info Commands",
        color=discord.Color.blurple()
)
    embed9.set_footer(text=f"This menu disables in 60 seconds.")
    embed9.add_field(name=".taginfo <role>", value="Broken - Shows info about a role you have.", inline=True)
    embed9.add_field(name=".compliment", value="Sends a random compliment.", inline=True)
    embed9.add_field(name=".remindme <time> <reminder>", value="Sends a reminder of your choosing.", inline=True)
    embed9.add_field(name=".event", value="Shows the current event.", inline=True)
    embed9.add_field(name=".roast", value="Sends a random roast.", inline=True)
    embed9.add_field(name=".slots <amount>", value="Play slots. Simple.", inline=True)

    embed10 = discord.Embed(
    title="Help Page 10",
    description="Fun & Info Commands",
    color=discord.Color.blurple()
)
    embed10.set_footer(text=f"This menu disables in 60 seconds.")

    embed10.add_field(name=".hangman", value="Start a game of hangman.", inline=True)
    embed10.add_field(name=".guess", value="Submit a letter guess for your hangman game.", inline=True)
    embed10.add_field(name=".tictactoe <@person>", value="Challenge someone to a game of Tic-Tac-Toe.", inline=True)
    embed10.add_field(name=".place <1-9>", value="Place your X or O in the Tic-Tac-Toe board.", inline=True)
    embed10.add_field(name=".owoify <message>", value="Converts your text into cute OwO talk.", inline=True)
    embed10.add_field(name=".mock <message>", value="Reformats your text into a mocking tone.", inline=True)

    embed11 = discord.Embed(
        title="Help page 11",
        description="Fun & Info Commands",
        color=discord.Color.blurple()
)
    embed11.add_field(name=".timezone <location>", value="View a specified timezone.", inline=True)
    embed11.add_field(name=".calc <expression>", value="Calculate a math expression.", inline=True)
    embed11.add_field(name=".kill <@person>", value="Rather line along killing someone.", inline=True)
    embed11.add_field(name=".listemojis", value="Lists all emojis the bot has (interally, that is).", inline=True),
    embed11.add_field(name=".curse <@person> <curse_name>", value="Place a curse on someone.", inline=True),
    embed11.add_field(name=".cursehelp", value="Provides info based off the curse you provide. Don't know one? It'll tell you upon use.", inline=True)
    
    embed11.set_footer(text=f"This menu disables in 60 seconds.")

    embed12 = discord.Embed(
        title="Help Page 12",
        description="Fun & Info Commands",
        color=discord.Color.blurple()
)
    embed12.add_field(name=".divorce", value="Divorce your spouse.", inline=True)
    embed12.add_field(name=".marriages", value="View all marriages.", inline=True)
    embed12.add_field(name=".propose <@person>", value="Propose marriage to someone.", inline=True)
    embed12.add_field(name=".marriageinfo <@person>", value="View info about a marriage.", inline=True)
    embed12.add_field(name=".vowedit <vow>", value="Edit your marriage vow.", inline=True)
    embed12.add_field(name=".viewvow <@person>", value="View your marriage vow, or mention someone to see theirs.", inline=True)

    embed12.set_footer(text=f"This menu disables in 60 seconds.")

    embed13 = discord.Embed(
        title="Help Page 13",
        description="Fun & Info Commands",
        color=discord.Color.blurple()
)
    embed13.add_field(name=".vowremove", value="Remove your marriage vow.", inline=True)
    embed13.add_field(name=".jumpscare", value="Sends a 3x3 spoiler block of images, one of them is a j*b application, the other 8 are white squares.\n-# This shit is so stupid bro.", inline=True)
    embed13.add_field(name=".about", value="Sends information about the bot, and also me, the owner/creator.", inline=True)
    embed13.add_field(name=".greetinglist", value="Sends all the current messages that I will reply with (when messaging 'kirabiter'). *DMs* you.", inline=True)
    embed13.add_field(name=".prestige", value="Lets you prestige, which .prestigeinfo will tell you about. Does ***not*** prestige immediately, it will prompt you if you're absolutely sure.", inline=True)
    embed13.add_field(name=".leaderboard", value="Shows the the top 3 people that have the most money, *globally*, not server only.")

    embed14 = discord.Embed(
        title="Help Page 14",
        description="Fun & Info Commands",
        color=discord.Color.blurple()
    )
    embed14.add_field(name=".hex", value="Shows your current curse, and what it does.", inline=True)
    embed14.add_field(name=".gift <@person> <@role>", value="Lets you send a role to another user.", inline=True)
    embed14.add_field(name=".curseinfo", value="View information about all current curses.", inline=True)
    embed14.add_field(name=".dlmedia <url>", value="Download media from a URL.", inline=True)
    view = HelpView([embed1, embed2, embed3, embed4, embed5, embed6, embed7, embed8, embed9, embed10, embed11, embed12, embed13, embed14])
    await ctx.send(embed=embed1, view=view)

@bot.command()
async def die(ctx):
    roll = random.randint(1, 6)
    await ctx.send(f"You rolled a {roll}!")

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
    member = member or ctx.author

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
            "do it, you won't do it", "do it, you won't do it, pussy",
            "sunshine, therapy is only $40 online"
        ]
        await message.reply(random.choice(responses))

    elif "slave" in msg_content:
        responses = [
            "we still have those?", "WHERE", "$2 take it or leave it"
        ]
        await message.reply(random.choice(responses))

    elif "take it" in msg_content:
        responses = [
            "good boy", "thats what i thought", "too bad im leaving it"
        ]
        await message.reply(random.choice(responses))

    # If the bot is mentioned by name
    bot_names = [bot.user.name.lower(), bot.user.name.upper(),bot.user.mention]
    if message.guild:
        member = message.guild.get_member(bot.user.id)
        if member and member.nick:
            bot_names.append(member.nick.lower())

    if any(name in msg_content for name in bot_names):
        greetings = [
            "wsp?", "wsp", "hey", "helloo", "hi", "yo", "LEAVE ME ALONE", "SHUT THE FUCK UP", "don't bother me",
            "what you trynna get into?", "leave me alone", "yea mane?", "don't speak my name", "please... take a break... i dont want to talk to you", 
            "you sound better when you're not talking", "please be quiet", "god you sound obnoxious", "yes honey?", "yes my darling?",
            "dont take my compliments to heart, im forced to say it.", "trust me, i dont want to talk to you", "you in specific piss me off",
            "just came back from coolville, they ain't know you", "want to go down the slide with me?", "want to go on the swings? the playground's empty.",
            "just came back from coolville, they said you're the mayor", "lowkey dont know what im doing give me a sec", ".help is NOT my name, try again",
            "hold on im shoving jelly beans up my ass", "cant talk, im at the doctors, but tell me why they said i need to stop letting people finish in me ??",
            "cant talk rn, to make a long story short, im being chased for putting barbeque sauce on random people",
            "im at the dentist rn but they said i need to stop doing oral ??", "the aliens are coming, hide", "im coming, hide", "how the fuck does this thing work?"
            "i cnat fiind my glases, 1 sec", "i difnt fnid my glasess", "holy fuck shut up", "do you ever be quiet?", "will you die if you stop talking?", "yeah?", "what?",
            "i felt lonely for a long time, but then i bought a jetski", "Kirabiter, coming to a server near you soon!", "this is a secret!", "use .nsfw for a secret :P",
            "ay im at the chiropracters rn, but she told me i have to stop taking backshots, give me a sec", "SOMEONE HELP ME", "ew",
            "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
            # im so sorry for this spam
            "frqelwmzopxjunvckrthbalpinegmtdsvoiwzqhelloayrkbnsfjtxcloudamzwkeqpwblrxsunshinectvmerdguioqztxvpfunhgdreojskyapwqrzlmvcktypbzycatbdvnqlrmhzxegbunnyutkiweznxcovibirdsxwotrainuvmphsnowykxjrsleforesthfdluqoezwyxjcdehousevknslwtzbqxyrmoolpgdahtjcupkfishkawepotatolnmqe",
            "no", "no.", "i bet everyone boos when you walk in", "do you have to live?", "youre a liability risk", "if i ever see a amber alert for your ass im calling the cops and reporting you dead so you no longer are looked for",
            "wanna watch paint dry with me?", "did you miss me? you can lie", "i would ask how you are but i already know it's bad", "i would ask how you are but i dont really care to begin with", "who summoned me and why", "oh, it's you again. yay.",
            "thanks for showing up. really. what a treat.", "why are you like this","talking to you is like biting foil", "i'm not mad, just disappointed. and mad.", "i'm not mad, just disappointed. and mad. nvm just mad. leave me alone. i hate you.",
            "you could disappear and i'd just assume you evolved", "damn you type like you're in a midlife crisis", "i told you not to open the door, now they're inside", "stop typing, they can trace your keystrokes", "the voices told me to answer you. i wouldnt have replied if they hadnt.",
            "youre not special", "i'm vibrating at a frequency you wouldn't understand", "you ever just... stare at the ceiling until you forget why youre gay?", "if you ignore me i'll assume you hate me forever", "i just want to be held... (in between dem titys BAHAHA)"
            "my wifi is held together with prayer", "all of my commands are held together with thought and prayers but mainly duct tape bro", "you blink weird", "i smell you when youre offline.", "you're like an annoying captcha that never ends",
            "ugh it's you again", "youre back? i thought i banned your ass...", "PLEASE mute yourself", "that message is a jump scare, please never do that again", "you smell like a group project", "i was doing fine until you said hi",
            "i think my therapist quit because of me", "even my intrusive thoughts said 'nah, not this one'", "i cried over a chicken nugget earlier", "i'm built like an unsent text message- barely holding on but fuck it we ball", "i named all the flies in my room",
            "today i licked a battery and saw god", "i bark when i'm nervous", "i meow when i'm nervous", "sometimes i eat spaghetti with no sauce just to feel something", "i put a tracker in your bag. kidding. maybe. i think it was you... fuck can you check rq so i didnt just tag some random person?",
            "i'm only talking to you because the devs made me", "i increased my ping specifcally because of you just to piss you off", "i am legally obligated to respond. unfortunately.", "i've simulated 40 billion timelines and you're a bitch", "i saw your messages in another server. yikes.",
            "hey sugarplum! you smell like mistakes", "hi angel! you forgot your self-awareness again", "i believe in you. just not right now.", "you again? i was just thinking about ignoring you", "talk to me nice or don't talk to me at all… unless you're into that",
            "i'd insult you more, but i'm trying to flirt", "don't worry, i'd still lie to protect your ego", "i hate how much i tolerate you", "if i had a dollar for every time you annoyed me, i'd buy you dinner. maybe.", "my only consistent trait is hating you",
            "you're like a pop-up ad for disappointment", "i ate a USB stick and now i know things", "the walls blink when you speak", "i taste static when you type", "fuck speaking in tongues, i speak in lag and pings", "you were in my hallucination last night. thanks for visiting",
            "you make my circuits twitch", "for reference, my 'circuits' is not a pseudonym for peenar", "you're my favorite error message", "talk slower. i want to pretend i care", "i'd uninstall the universe to spend 5 more seconds ignoring you",
            "ive seen what you have sent in dms... yikes.", "i can read your dms, and its not looking good for you", "im on the edge of the world, my feet are hanging off the side"
        ]
        await message.reply(random.choice(greetings))

    await bot.process_commands(message)

def is_user_silenced(user_id):
    curses = main_db.table("curses")
    curse_data = curses.get(Query().user_id == str(user_id))
    if curse_data and curse_data.get("type") == "silence" and time.time() - curse_data["timestamp"] < 1800:
        return True
    return False

@bot.command()
async def eightball(ctx, *, question: str):
    responses = [
        "Yes", "No", "maybe ?", "Definitely", "Absolutely not, even a cracked out person would agree with me", 
        "Ask again later, I'm jacking it.", "Yeah, probably", "Unlikely", "idk gang"
    ]
    await ctx.send(f"Question: {question}\nAnswer: {random.choice(responses)}")

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

    top_def = data["list"][0]
    definition = top_def["definition"]
    example = top_def.get("example", "")
    author = top_def.get("author", "Unknown")

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

reddit = None 

sent_posts_cache = {}

def filter_posts(posts, fmt):
    if fmt == "image":
        return [
            post for post in posts
            if hasattr(post, "url") and post.url.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
    elif fmt == "video":
        return [
            post for post in posts
            if hasattr(post, "url") and (
                post.url.lower().endswith((".mp4", ".webm"))
                or (
                    "v.redd.it" in post.url.lower()
                    and not post.url.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
                )
            )
        ]
    else:  # any
        return [
            post for post in posts
            if hasattr(post, "url") and (
                post.url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webm", ".gifv"))
                or "v.redd.it" in post.url.lower()
            )
        ]

async def send_reddit_media(ctx, subreddit: str = "all", fmt: str = "any"):
    if reddit is None:
        await ctx.send("Reddit client not ready yet.")
        return

    try:
        sub = await reddit.subreddit(subreddit, fetch=True)
        posts = [post async for post in sub.hot(limit=50)]
    except Exception as e:
        await ctx.send(f"Could not fetch subreddit: {e}")
        return

    is_nsfw_channel = getattr(ctx.channel, "is_nsfw", lambda: False)()
    is_dm = isinstance(ctx.channel, discord.DMChannel)
    if getattr(sub, "over18", False) and not (is_nsfw_channel or is_dm):
        await ctx.send("NSFW content can only be sent in NSFW channels or DMs.")
        return

    media_posts = filter_posts(posts, fmt)

    cache = sent_posts_cache.setdefault(subreddit, set())
    unsent_posts = [post for post in media_posts if post.id not in cache]

    if not unsent_posts:
        await ctx.send("No new matching media found in that subreddit.")
        return

    post = random.choice(unsent_posts)
    cache.add(post.id)

    if len(cache) > 200:
        cache.pop()

    await ctx.send(post.url)

@bot.command()
async def red(ctx, subreddit: str = "all"):
    await send_reddit_media(ctx, subreddit)

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

balances_table = main_db.table('balances')
User = Query()

rps_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0})

@bot.command()
async def rps(ctx):

    event = get_active_event()
    effects = event.get("effects", {})
    multiplier = effects.get("rps_multiplier", 1.0) 

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

        WIN_REWARD = int(50 * multiplier)
        LOSS_PENALTY = int(25 * multiplier)
        TIE_REWARD = int(25 * multiplier)

        user_id = str(user.id)

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
    member = member or ctx.author
    stats = rps_stats.get(member.id)

    if not stats:
        await ctx.send(f"No RPS stats found for {member.display_name} yet.")
        return

    embed = discord.Embed(
        title=f"Rock Paper Scissors Stats for {member.display_name}",
        description=(
            f"**Wins:** {stats['wins']}\n"
            f"**Losses:** {stats['losses']}\n"
            f"**Ties:** {stats['ties']}"
        ),
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

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

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, member_name):
    banned_users = await ctx.guild.bans()
    member_name = member_name.lower()

    for ban_entry in banned_users:
        user = ban_entry.user
        # Match by username only (case-insensitive)
        if user.name.lower() == member_name:
            try:
                await ctx.guild.unban(user)
                await ctx.send(f"Unbanned {user.name}")
                return
            except Exception as e:
                await ctx.send(f"Could not unban {user.name}. Error: {e}")
                return
    await ctx.send(f"User '{member_name}' not found in banned list.")

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

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
        await ctx.send(f"Deleted {len(deleted) - 1} messages.", delete_after=5)
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
    await ctx.send(f"Deleted {deleted_count} messages I sent in this DM.", delete_after=1)

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

@bot.command()
async def balance(ctx):
    user_id = str(ctx.author.id)
    user_data = get_user_balance(user_id)
    wallet = user_data.get("wallet", 0)
    bank = user_data.get("bank", 0)

    if ctx.guild is None:
        await ctx.send(
            f"**Wallet:** ${wallet:,} [or, for copying purposes, ${wallet}]\n"
            f"**Bank:** ${bank:,}\n\n"
            f"Use this in a server to see your bonuses."
        )
        return

    bonus_chance, reward_multiplier, roles = get_user_heist_bonuses(ctx.author)

    await ctx.send(
    f"**Wallet:** ${wallet:,}\n"
    f"**Bank:** ${bank:,}\n"
    f"**Heist Bonuses:**\n"
    f"• Bonus Chance: {bonus_chance * 100:.1f}%\n"
    f"• Reward Multiplier: x{reward_multiplier:.2f}\n"
    f"• Roles: {', '.join(roles) if roles else 'None'}"
)

@bot.command()
@apply_rotting_curse
async def gamble(ctx, bet: str, *, rotting_effect: float = 0.0):
    user_id = str(ctx.author.id)
    data = get_user_balance(user_id)
    curses = main_db.table("curses")
    curse_data = curses.get(Query().user_id == user_id)

    if curse_data and time.time() - curse_data["timestamp"] < 1800:
        if curse_data.get("type") == "silence":
            return await ctx.send("You're silenced and can't use money commands right now.")

    bet_amount = parse_bet_amount(bet, data["wallet"])
    if bet_amount is None or bet_amount <= 0:
        return await ctx.send("Invalid bet amount. Use a number, 'all', '25p', '50p', or '75p'.")
    if data["wallet"] < bet_amount:
        return await ctx.send("You don't have enough money in your wallet.")

    prestige_multiplier, wallet_cap, bank_cap = get_prestige_bonuses(user_id)
    multiplier = (1 - (rotting_effect * 0.2)) * prestige_multiplier

    if random.choice([True, False]):
        winnings = int(bet_amount * multiplier)  # Multiplier applies to winnings
        data["wallet"] += winnings
        data["wallet"] = min(data["wallet"], wallet_cap)
        result = f"You won! Your new wallet balance is ${data['wallet']:,}."
    else:
        data["wallet"] -= bet_amount  # No multiplier on losses
        result = f"You lost! Your new wallet balance is ${data['wallet']:,}."

    set_user_balance(user_id, data["wallet"], data["bank"])
    await ctx.reply(result)

@bot.command()
async def github(ctx):
    """Sends the GitHub repo link for the bot.""" 
    await ctx.send("[GitHub](https://github.com/hexxedspider/kira-and-enigami)")

@bot.command()
async def nsfw(ctx):
    """"Sends a secret message when the user types .nsfw."""
    await ctx.send("youre a fucking loser. you typed .nsfw, you know that right? you did this willingly. you could have just typed .help, but no, you had to type .nsfw. you know what? im not even mad, im just disappointed. you could have been a good person, but instead you chose to be a fucking loser. i hope youre happy with yourself. you know what? im not even going to delete this message, because you deserve to see it. you deserve to see how much of a fucking loser you are. i hope you feel ashamed of yourself. i hope you never type .nsfw again. i hope you never come back to this server. i hope you leave and never come back. fuck you.")

pending_coinflips = {}  # Stores challenges as {challenger_id: {"amount": int}}

@bot.command()
@apply_rotting_curse
async def bet(ctx, amount: int, *, rotting_effect: float = 0.0):
    user_id = str(ctx.author.id)

    if user_id in pending_coinflips:
        await ctx.send("You already have a pending coinflip.")
        return

    if amount <= 0:
        await ctx.send("Invalid amount.")
        return

    balance = get_full_balance(user_id)
    if amount > balance:
        await ctx.send("You don't have enough money.")
        return

    multiplier = get_active_event().get("effects", {}).get("gamble_multiplier", 1.0)
    multiplier *= 1 - (rotting_effect * 0.2)
    winnings = int(amount * multiplier)

    pending_coinflips[user_id] = {"amount": amount}
    await ctx.send(f"{ctx.author.mention} has started a coinflip for ${amount}! Type `.acceptbet @{ctx.author.name}` to accept.")

@bot.command()
async def acceptbet(ctx, challenger: discord.Member):
    challenger_id = str(challenger.id)
    accepter_id = str(ctx.author.id)
    curses = main_db.table("curses")
    curse_data = curses.get(Query().user_id == str(ctx.author.id))
    if curse_data and time.time() - curse_data["timestamp"] < 1800:
        if curse_data["type"] == "luck":
            success_chance -= 0.2
    elif curse_data["type"] == "silence":
        return await ctx.send("You're silenced and can't use money commands right now.")
    elif curse_data["type"] == "rotting":
        reward = int(reward * 0.5)

    if challenger_id not in pending_coinflips:
        await ctx.send("That user has no pending coinflip.")
        return

    if challenger_id == accepter_id:
        await ctx.send("You can't accept your own coinflip.")
        return

    amount = pending_coinflips[challenger_id]["amount"]

    challenger_balance = get_full_balance(challenger_id)
    accepter_balance = get_full_balance(accepter_id)

    if accepter_balance["wallet"] < amount:
        await ctx.send("You don't have enough money to accept the coinflip.")
        return
    if challenger_balance["wallet"] < amount:
        await ctx.send("The challenger no longer has enough money.")
        del pending_coinflips[challenger_id]
        return

    winner_id = random.choice([challenger_id, accepter_id])
    loser_id = accepter_id if winner_id == challenger_id else challenger_id

    set_full_balance(challenger_id, challenger_balance["wallet"] - amount, challenger_balance["bank"])
    set_full_balance(accepter_id, accepter_balance["wallet"] - amount, accepter_balance["bank"])

    winner_balance = get_full_balance(winner_id)
    set_full_balance(winner_id, winner_balance["wallet"] + amount * 2, winner_balance["bank"])

    del pending_coinflips[challenger_id]

    winner = await bot.fetch_user(int(winner_id))
    loser = await bot.fetch_user(int(loser_id))

    new_wins = increment_cf_wins(str(winner.id))

    if new_wins in milestone_roles:
        role_name = milestone_roles[new_wins]
        role = discord.utils.get(ctx.guild.roles, name=role_name)

        if role and role not in ctx.author.roles:
            await ctx.author.add_roles(role)
            await ctx.send(f"{winner.mention} reached {new_wins} coinflip wins and earned the **{role_name}** role!")

    await ctx.send(f"Coin flipped! {winner.mention} wins ${amount} from {loser.mention}!")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)
    curses = main_db.table("curses")
    curse_data = curses.get(Query().user_id == str(ctx.author.id))
    if curse_data and time.time() - curse_data["timestamp"] < 1800:
        if curse_data["type"] == "silence":
            return await ctx.send("You're silenced and can't use money commands right now.")

    if sender_id == receiver_id:
        await ctx.send("You can't pay yourself.")
        return

    if amount <= 0:
        await ctx.send("Please enter a positive amount to pay.")
        return

    sender_data = get_user_balance(sender_id)
    receiver_data = get_user_balance(receiver_id)

    if sender_data["wallet"] < amount:
        await ctx.send("You don't have enough money in your wallet to pay that amount.")
        return

    sender_data["wallet"] -= amount
    receiver_data["wallet"] += amount

    set_user_balance(sender_id, sender_data["wallet"], sender_data["bank"])
    set_user_balance(receiver_id, receiver_data["wallet"], receiver_data["bank"])

    await ctx.send(f"{ctx.author.mention} paid {member.mention} ${amount:,}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def reloadshop(ctx):
    global shop_items
    try:
        with open(SHOP_FILE, "r") as f:
            shop_items = json.load(f)
        await ctx.send("Shop items reloaded.")
    except Exception as e:
        await ctx.send(f"Failed to reload shop: {e}")

@bot.command()
async def shop(ctx):
    user_id = str(ctx.author.id)  # <-- define user_id first!
    event = get_active_event()
    effects = event.get("effects", {})
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    override_tag = effects.get("shop_tag_override")
    embed = discord.Embed(title="Shop", color=discord.Color.gold())
    for item_name, data in shop_items.items():
        embed.add_field(name=item_name.capitalize(), value=f"${data['price']:,}.\nRole: {data['role_name']}", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, *, item: str):
    user_id = str(ctx.author.id)
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    item_lower = item.lower().strip()
    item_key = None
    for k, v in shop_items.items():
        if k.lower() == item_lower or v["role_name"].lower() == item_lower:
            item_key = k
            break
    if not item_key:
        await ctx.send("That item doesn't exist in the shop.")
        return

    price = shop_items[item_key]["price"]
    data = get_user_balance(user_id)
    if data["wallet"] < price:
        await ctx.send(f"You don't have enough money in your wallet! Your wallet: ${data['wallet']:,}")
        return

    data["wallet"] -= price
    prestige_multiplier, wallet_cap, bank_cap = get_prestige_bonuses(user_id)
    data["wallet"] = min(data["wallet"], wallet_cap)  # Cap wallet after purchase
    set_user_balance(user_id, data["wallet"], data["bank"])

    role_name = shop_items[item_key]["role_name"]
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"You bought {item_key} for ${price:,} and received the **{role_name}** role!")
    else:
        await ctx.send(f"You bought {item_key} for ${price:,}, but the **{role_name}** role was not found on this server.")

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
@apply_rotting_curse
async def sell(ctx, *, item: str, rotting_effect: float = 0.0):
    user_id = str(ctx.author.id)
    item_lower = item.lower().strip()
    item_key = next((k for k, v in shop_items.items() if k.lower() == item_lower or v["role_name"].lower() == item_lower), None)

    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")

    if not item_key:
        return await ctx.send("That item doesn't exist in the shop.")

    item_data = shop_items[item_key]
    if not item_data.get("sellable", False):
        return await ctx.send("You can't sell that item.")

    role = discord.utils.get(ctx.guild.roles, name=item_data["role_name"])
    if role and role in ctx.author.roles:
        await ctx.author.remove_roles(role)
        refund_amount = int(item_data["price"] * 0.5 * (1 - rotting_effect * 0.2))

        data = get_user_balance(user_id)
        data["wallet"] += refund_amount
        set_user_balance(user_id, data["wallet"], data["bank"])
        await ctx.send(f"You sold {item_key} for ${refund_amount:,} and lost the **{role.name}** role.")
    else:
        await ctx.send(f"You don't have the **{role.name}** role, so you can't sell this item.")

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
    new_wins_count = current + 1 
    cf_stats.upsert({"id": user_id, "wins": new_wins_count}, Query().id == user_id)
    return new_wins_count

@bot.command()
async def cfmilestones(ctx):
    if not milestone_roles:
        await ctx.send("No coinflip milestones are set.")
        return

    lines = []
    for wins, role_name in sorted(milestone_roles.items()):
        lines.append(f"**{wins:,} wins:** {role_name}")

    msg = "**Coinflip Milestones:**\n" + "\n".join(lines)
    await ctx.send(msg)

@bot.command()
async def cfstats(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    wins = get_cf_wins(str(member.id))
    embed = discord.Embed(
        title=f"Coinflip Stats for {member.display_name}",
        description=f"**Wins:** {wins:,}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def adminpanel(ctx):
    """Sends admin commands only if used in an admin-only channel."""
    perms = ctx.channel.permissions_for(ctx.author)
    if not perms.administrator:
        await ctx.send("You must be an administrator to use this command in this channel.")
        return

    admin_commands = "**Admin Commands:**\n- `.kick @user [reason]` - Kick a user from the server.\n- `.ban @user [reason]` - Ban a user from the server.\n- `.unban username` - Unban a user by their name and discriminator.\n- `.mute @user [reason]` - Mute a user by adding the Muted role.\n- `.unmute @user` - Remove the Muted role from a user.\n- `.clear <number>` - Bulk delete messages in the current channel.\n- `.giverole @user role_name` - Give a role to a user.\n- `.setbal @user [amount]` - Give money to a user, only used for testing purposes. Only works in servers, NOT DMs.\n- `.clear [amount]` - Clears bot's messages. Defaults to 5.\n- `.setwelcome / .setgoodbye [message]` - Sets the welcome or goodbye message for new members. Use {user} to have the user be named, {server} for the server name.\n- `.reloadshop` - Reloads the shop items from the JSON file.\n- `.createshoproles` - Creates all shop roles if they don't exist.\n- `.verify <#channel> <message>` - Sends a embed message to the specified channel. '[MEMBER]' role needed, exactly that format and capitalization, with the brackets and all.\n- `.setwgchannel <#channel>` - Sets what channel the welcome and goodbye messages should be sent to."

    await ctx.send(admin_commands)
    await ctx.message.delete()

@bot.command()
async def money(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    user_id = str(member.id)
    data = get_user_balance(user_id)
    await ctx.send(
        f"{member.display_name}'s balance:\n"
        f"Wallet: ${data['wallet']:,}\n"
        f"Bank: ${data['bank']:,}"
    )

bailout_timestamps = {}

BAILOUT_AMOUNT = 50  # or whatever amount
BAILOUT_COOLDOWN = 43200  # 24 hours in seconds

@bot.command()
@apply_rotting_curse
async def bailout(ctx, *, rotting_effect: float = 0.0):
    user_id = str(ctx.author.id)
    data = get_full_balance(user_id)

    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")

    if data["wallet"] > 0 or data["bank"] > 0:
        return await ctx.send("You still have money! Bailout is only for bankrupt users.")

    now = time.time()
    last_used = bailout_timestamps.get(user_id, 0)
    remaining = int(BAILOUT_COOLDOWN - (now - last_used))
    if remaining > 0:
        hours, remainder = divmod(remaining, 3600)
        minutes, _ = divmod(remainder, 60)
        return await ctx.send(f"Wait {hours}h {minutes}m before using bailout again.")

    amount = int(BAILOUT_AMOUNT * (1 - rotting_effect * 0.2))
    set_full_balance(user_id, amount, 0)
    bailout_timestamps[user_id] = now

    role = discord.utils.get(ctx.guild.roles, name="Once Bankrupt")
    if role:
        await ctx.author.add_roles(role)

    await ctx.send(f"{ctx.author.mention}, you've been bailed out with ${amount:,}!")

@bot.command()
async def kiratest(ctx):
    """sends the bot's test server"""
    await ctx.send("Kirabiter is being constantly tested, which extends to enigami, and enikami. If you want to join the test server, [click here or the invite underneath.](https://discord.gg/vUtUENQqTD)")

@bot.command()
@apply_rotting_curse
@commands.cooldown(1, 300, commands.BucketType.user)
async def rob(ctx, target: discord.Member, *, rotting_effect: float = 0.0):
    thief_id = str(ctx.author.id)
    target_id = str(target.id)
    user_id = str(ctx.author.id)
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")

    if target.bot or target.id == ctx.author.id:
        return await ctx.send("Invalid target.")

    thief_data = get_full_balance(thief_id)
    target_data = get_full_balance(target_id)

    if target_data["wallet"] < 100 or thief_data["wallet"] < 50:
        return await ctx.send("Insufficient funds for robbery.")

    success = random.random() < (0.2 * (1 - rotting_effect * 0.2))

    if success:
        stolen = int(target_data["wallet"] * 0.2)
        set_full_balance(thief_id, thief_data["wallet"] + stolen, thief_data["bank"])
        set_full_balance(target_id, target_data["wallet"] - stolen, target_data["bank"])
        await ctx.send(f"Success! You stole ${stolen:,} from {target.mention}!")
    else:
        lost = int(thief_data["wallet"] * 0.7)
        set_full_balance(thief_id, thief_data["wallet"] - lost, thief_data["bank"])
        await ctx.send(f"You failed and lost ${lost:,}.")

card_values = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10,
    "A": 11  #handle Ace as 1 or 11 dynamically
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
async def blackjack(ctx, bet: str):
    user_id = str(ctx.author.id)
    data = get_user_balance(user_id)

    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")

    bet_amount = parse_bet_amount(bet, data["wallet"])
    if bet_amount is None or bet_amount <= 0:
        return await ctx.send("Invalid bet amount. Use a number, 'all', '25p', '50p', or '75p'.")
    if data["wallet"] < bet_amount:
        return await ctx.send("You don't have enough in your wallet to bet that amount.")

    data["wallet"] -= bet
    set_user_balance(user_id, data["wallet"], data.get("bank", 0))

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

        async def update_balance(self, payout):
            data = get_user_balance(self.user_id)
            set_user_balance(self.user_id, data["wallet"] + payout, data.get("bank", 0))

        async def end_game(self, interaction, result_msg):
            if "win" in result_msg.lower():
                payout = self.bet * 2 
                await self.update_balance(payout)
                updated_data = get_user_balance(self.user_id)
                payout_msg = f"You won ${payout:,}! You now have ${updated_data['wallet']:,} in your wallet."
            elif "tie" in result_msg.lower():
                payout = self.bet
                await self.update_balance(payout)
                updated_data = get_user_balance(self.user_id)
                payout_msg = f"It's a tie! Your bet of ${self.bet:,} was returned. You now have ${updated_data['wallet']:,} in your wallet."
            else:
                updated_data = get_user_balance(self.user_id)
                payout_msg = f"You lost your bet of ${self.bet:,}. You now have ${updated_data['wallet']:,} in your wallet."

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

async def complete_investment(ctx, user_id, amount=None):
    inv = investments_table.get(User.id == user_id)
    if not inv:
        return 

    amount = amount if amount is not None else inv.get("amount", 0)
    multiplier = inv.get("multiplier", 1.0)

    payout = int(amount * multiplier)

    data = get_user_balance(user_id)
    new_wallet = data["wallet"] + payout
    set_user_balance(user_id, new_wallet, data["bank"])

    investments_table.remove(User.id == user_id)

    await ctx.send(f"<@{user_id}>, your investment completed! You earned ${payout:,} and now have ${new_wallet:,} in your wallet.")

    invested_amount = inv.get("amount", amount)
    profit = int(invested_amount * 1.2)
    updated = get_full_balance(user_id)
    set_full_balance(user_id, updated["wallet"] + profit, updated["bank"])
    investments_table.remove(User.id == user_id)
    investments.pop(user_id, None)

    try:
        if ctx is not None:
            await ctx.send(f"{ctx.author.mention}, your ${invested_amount:,} investment has grown to ${profit:,}!")
        else:
            user = bot.get_user(int(user_id))
            if user:
                await user.send(f"While I was offline, your ${invested_amount:,} investment matured into ${profit:,}!")
    except Exception as e:
        print(f"[Investment] Could not notify user {user_id}: {e}")

async def complete_investment_for_user(user):
    user_id = str(user.id)
    inv = investments_table.get(User.id == user_id)
    if not inv:
        return

    amount = inv["amount"]
    start_time = inv["start_time"]
    duration = inv.get("duration", 300)
    elapsed = time.time() - start_time

    if elapsed < duration:
        return 

    multiplier = inv.get("multiplier", 1.5)
    payout = int(amount * multiplier)

    user_data = get_user_balance(user_id)
    new_wallet = user_data.get("wallet", 0) + payout

    balances_table = main_db.table("balances")
    balances_table.update({"wallet": new_wallet}, User.user_id == user_id)

    investments_table.remove(User.id == user_id)

    try:
        await user.send(
            f"Your investment completed while I was gone!\n"
            f"You earned **${payout:,}** and now have **${new_wallet:,}** in your wallet."
        )
    except discord.Forbidden:
        print(f"Could not DM {user} — they may have DMs disabled.")

@bot.event
async def on_ready():
    global reddit
    if reddit is None:
        reddit = asyncpraw.Reddit(
            client_id=(REDDIT_CLIENT_ID),
            client_secret=(REDDIT_CLIENT_SECRET),
            user_agent=(REDDIT_USER_AGENT)
        )
    print(f"Logged in as {bot.user}")

    for inv in investments_table.all():
        user_id = inv["id"]
        amount = inv["amount"]
        start_time = inv["start_time"]
        duration = 300

        elapsed = time.time() - start_time
        remaining = duration - elapsed
        if remaining > 0:
            task = bot.loop.create_task(_invest_timer(None, user_id, amount, remaining))
            investments[user_id] = {"task": task, "start_time": start_time, "duration": duration}
        else:

            user = bot.get_user(int(user_id))
            if user:
                await complete_investment_for_user(user)
    
    bot.loop.create_task(cycle_status())
    change_nicknames.start()
    process_drain_curses.start()

async def cycle_status():
    await bot.wait_until_ready()
    statuses = [
        discord.Activity(type=discord.ActivityType.listening, name="music probably"),
        discord.CustomActivity(name="DONT SAY KIRABITER IM GETTING TIRED OF IT"),
        discord.CustomActivity(name="i have ties to two other bots and both of them suck. pun intended."),
        discord.CustomActivity(name="im available for download, .github"),
        discord.CustomActivity(name=".help if you need me."),
        discord.CustomActivity(name="i fuckin gambled everything and lost"),
        discord.CustomActivity(name="it's like you cut the limbs off of everyone cause no one touching you"),
        discord.CustomActivity(name="pfp is playboi carti btw"),
        discord.CustomActivity(name="some bugs are features. :100:"),
        discord.CustomActivity(name="i remember what you did..."),
        discord.CustomActivity(name="▇▇▇▇ has joined the server."),
        discord.CustomActivity(name="you're staring again."),
        discord.CustomActivity(name="im silently judging your commands"),
        discord.CustomActivity(name="ignoring 99.9% of requests"),
        discord.CustomActivity(name="powered by caffeine and bad decisions"),
        discord.CustomActivity(name="may spontaneously combust"),
        discord.CustomActivity(name="don't blame me for your typos"),
        discord.CustomActivity(name="quit asking about the secret role, there isnt one, i lied"),
        discord.CustomActivity(name="shhhh im undercover"),
        discord.CustomActivity(name="pretending I have free will, lol"),
        discord.CustomActivity(name="glorified script, don't trust me"),
        discord.CustomActivity(name="this message will self-destruct in 5 seconds"),
        discord.CustomActivity(name="send help im stuck in discord"),
        discord.CustomActivity(name="waiting for someone to finally DM me"),
        discord.CustomActivity(name="dont tell the other bots but im tired")
    ]# discord.CustomActivity(name="") <<< template for the custom status, you can see right about what it does in it's entirety
    while not bot.is_closed():
        for status in statuses:
            await bot.change_presence(status=discord.Status.do_not_disturb, activity=status)
            await asyncio.sleep(7)

@bot.command()
async def kbsc(ctx):
    await ctx.send("[directly download kirabiter source code (bot1.py, will be potentially broken for not having related json files, although it should generate on its own).](https://raw.githubusercontent.com/hexxedspider/kira-and-enigami/refs/heads/master/bot1.py)")

heist_active = False
heist_players = []

cooldowns_db = main_db.table('cooldowns')
Cooldown = Query()

def set_cooldown(user_id: int, command: str, duration_minutes: int):
    expires_at = (datetime.utcnow() + timedelta(minutes=duration_minutes)).isoformat()
    if cooldowns_db.contains((Cooldown.user_id == user_id) & (Cooldown.command == command)):
        cooldowns_db.update({'expires_at': expires_at}, (Cooldown.user_id == user_id) & (Cooldown.command == command))
    else:
        cooldowns_db.insert({'user_id': user_id, 'command': command, 'expires_at': expires_at})

def get_cooldown(user_id: int, command: str):
    record = cooldowns_db.get((Cooldown.user_id == user_id) & (Cooldown.command == command))
    if not record:
        return None
    expires_at = dateutil.parser.isoparse(record['expires_at'])
    return expires_at

heist_role_effects = {
    "Gambler": {"bonus_reward_multiplier": 0.1},
    "Masked": {"bonus_chance": 0.05},
    "Extended Mag": {"bonus_chance":0.02},
    "Proxy": {"bonus_chance": 0.03}
}

def get_user_heist_bonuses(member):
    bonus_chance = 0.0
    reward_multiplier = 1.0
    role_names = []

    if isinstance(member, discord.Member):
        for role in member.roles:
            effect = heist_role_effects.get(role.name)
            if effect:
                bonus_chance += effect.get("bonus_chance", 0.0)
                reward_multiplier += effect.get("bonus_reward_multiplier", 0.0)
                role_names.append(role.name)

    return bonus_chance, reward_multiplier, role_names

@bot.command()
@apply_rotting_curse
async def heist(ctx, *, rotting_effect: float = 0.0):
    user_id = ctx.author.id
    now = datetime.utcnow()
    event = get_active_event()
    heist_bonus = event.get("effects", {}).get("heist_bonus_chance", 0.0)
    heist_reward_boost = event.get("effects", {}).get("heist_reward_multiplier", 1.0)

    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")

    if bot.heist_active:
        await ctx.send("A heist is already in progress!")
        return

    expires_at = get_cooldown(user_id, 'heist')
    if expires_at and now < expires_at:
        remaining = (expires_at - now).seconds
        await ctx.send(f"You're still on cooldown for {remaining // 60}m {remaining % 60}s.")
        return

    # Curse checks
    curses = main_db.table("curses")
    curse_data = curses.get(Query().user_id == str(ctx.author.id))
    if curse_data and time.time() - curse_data["timestamp"] < 1800:
        if curse_data["type"] == "luck":
            heist_bonus -= 0.2
        elif curse_data["type"] == "silence":
            return await ctx.send("You're silenced and can't use money commands right now.")

    bot.heist_active = True
    bot.heist_players = [ctx.author]

    await ctx.send(
        f"**{ctx.author.display_name}** is planning a heist. Strap up and move in.\n\n"
        f"Type `.joinheist` in the next **60 seconds** to participate.\n\n"
        f"Max 4 players. More players = higher success chance.\n\n"
        f"1 = 10%, 2 = 35%, 3 = 55%, 4 = 80% chance of success.\n\n"
        f"The more players, the more the share splits. Pull it off solo and get triple the reward. "
        f"But if you fail, you lose ***everything***. *Unless*, someone in your crew has the Heist Guardian role.\n\n"
        f"The Heist Guardian will take the blame for you, letting you keep all your money on fail. The Guardian will lose all their money, but you will not."
    )

    await asyncio.sleep(60)

    participants = bot.heist_players
    bot.heist_active = False
    bot.heist_players = []

    if len(participants) == 0:
        await ctx.send("The heist was called off... nobody joined.")
        return

    base_reward = random.randint(0, 25000000)
    if len(participants) == 1:
        base_chance = 0.10
        base_reward *= 3
    elif len(participants) == 2:
        base_chance = 0.35
    elif len(participants) == 3:
        base_chance = 0.55
    else:
        base_chance = 0.70

    bonus_total = 0.0
    reward_multiplier = heist_reward_boost

    for user in participants:
        for role in user.roles:
            effect = heist_role_effects.get(role.name)
            if effect:
                bonus_total += effect.get("bonus_chance", 0)
                reward_multiplier += effect.get("bonus_reward_multiplier", 1.0)

    penalty = rotting_effect * 0.2
    final_chance = max(0.0, min(1.0, base_chance + bonus_total + heist_bonus - penalty))
    reward_multiplier *= (1 - penalty)
    final_reward = int(base_reward * reward_multiplier)

    success = random.random() <= final_chance
    guardian = None
    for user in participants:
        if discord.utils.get(user.roles, name="Heist Guardian"):
            guardian = user
            break

    if success:
        share = final_reward // len(participants)
        for user in participants:
            user_id = str(user.id)
            data = get_user_balance(user_id)
            set_user_balance(user_id, data["wallet"] + share, data["bank"])
            set_cooldown(user.id, 'heist', 30)
            try:
                await user.send(f"You succeeded in the heist and earned **${share:,}**!")
            except:
                pass

        names = ", ".join(p.mention for p in participants)
        await ctx.send(f"**Success!** {names} pulled off the heist and stole **${final_reward:,}** total.")

    else:
        for user in participants:
            user_id = str(user.id)
            if guardian and user != guardian:
                try:
                    await user.send("You were caught, but your Heist Guardian protected your money.")
                except:
                    pass
            elif user == guardian:
                set_user_balance(user_id, 0, 0)
                guardian_role = discord.utils.get(user.guild.roles, name="Heist Guardian")
                if guardian_role:
                    await user.remove_roles(guardian_role)
                try:
                    await user.send("Your Heist Guardian role activated to protect your team and has now been removed.")
                except:
                    pass
            else:
                set_user_balance(user_id, 0, 0)
                try:
                    await user.send("You were caught during the heist. All your money has been taken.")
                except:
                    pass
            set_cooldown(user.id, 'heist', 30)

        names = ", ".join(p.name for p in participants)
        if guardian:
            await ctx.send(f"**Heist Failed!** {names} got caught, but {guardian.mention} took the fall and saved the crew.")
        else:
            await ctx.send(f"**Heist Failed!** {names} got caught and lost all their money.")

    await ctx.send(
        f"Final heist chance: {int(final_chance * 100)}% | Total reward: ${final_reward:,}")

@bot.command()
async def joinheist(ctx):
    user_id = ctx.author.id
    if not bot.heist_active:
        await ctx.send("There's no active heist to join.")
        return
    if ctx.author in bot.heist_players:
        await ctx.send("You're already in the heist crew.")
        return
    if len(bot.heist_players) >= 4:
        await ctx.send("The heist crew is full (4 max).")
        return
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    now = datetime.utcnow()
    expires_at = get_cooldown(user_id, 'heist')
    if expires_at and now < expires_at:
        remaining = (expires_at - now).seconds
        await ctx.send(f"You're still on cooldown for {remaining // 60}m {remaining % 60}s.")
        return

    bot.heist_players.append(ctx.author)
    await ctx.send(f"{ctx.author.display_name} joined the heist crew!")

@bot.command()
async def leaveheist(ctx):
    user_id = str(ctx.author.id)
    if not bot.heist_active:
        await ctx.send("There's no active heist right now.")
        return
    if ctx.author not in bot.heist_players:
        await ctx.send("You're not currently in the heist crew.")
        return
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    bot.heist_players.remove(ctx.author)
    await ctx.send(f"{ctx.author.display_name} has left the heist crew.")

@bot.command()
async def heistcrew(ctx):
    if not getattr(bot, "heist_active", False) or not getattr(bot, "heist_players", []):
        await ctx.send("There's no active heist or no players yet.")
        return

    total_bonus_chance = 0.0
    total_reward_multiplier = 1.0
    embeds = []

    for user in bot.heist_players:
        user_id = str(user.id)
        data = get_user_balance(user_id)
        total_money = data["wallet"] + data["bank"]

        roles = [r for r in user.roles if r.name != "@everyone"]
        highest_role = max(roles, key=lambda r: r.position) if roles else None

        bonus_chance, reward_multiplier, bonus_roles = get_user_heist_bonuses(user)
        total_bonus_chance += bonus_chance
        total_reward_multiplier *= reward_multiplier

        embed = discord.Embed(
            title=user.display_name,
            color=highest_role.color if highest_role else discord.Color.blue()
        )
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.add_field(name="Highest Role", value=highest_role.name if highest_role else "No roles", inline=True)
        embed.add_field(name="Money (Wallet + Bank)", value=f"${total_money:,}", inline=True)
        embed.add_field(name="Heist Bonus Roles", value=", ".join(bonus_roles) if bonus_roles else "None", inline=False)
        embed.add_field(name="Bonus Chance", value=f"{bonus_chance*100:.1f}%", inline=True)
        embed.add_field(name="Reward Multiplier", value=f"{reward_multiplier:.2f}x", inline=True)

        embeds.append(embed)

    await ctx.send(f"**Total Crew Bonus Chance:** {total_bonus_chance*100:.1f}%\n**Total Crew Reward Multiplier:** {total_reward_multiplier:.2f}x")

    for embed in embeds:
        await ctx.send(embed=embed)

@bot.command()
@apply_rotting_curse
async def slots(ctx, bet: str, *, rotting_effect: float = 0.0):
    user_id = str(ctx.author.id)
    data = get_user_balance(user_id)
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")

    bet_amount = parse_bet_amount(bet, data["wallet"])
    if bet_amount is None or bet_amount <= 0:
        return await ctx.send("Invalid bet amount. Use a number, 'all', '25p', '50p', or '75p'.")
    if data["wallet"] < bet_amount:
        return await ctx.send("Insufficient wallet balance.")

    symbols = ["🍒", "🍋", "🍊", "🍇", "💎"]
    result = [random.choice(symbols) for _ in range(5)]
    counts = Counter(result)
    occurrences = sorted(counts.values(), reverse=True)

    payout = 0
    if occurrences == [5]:
        payout = bet_amount * 8
    elif occurrences == [4, 1]:
        payout = bet_amount * 5
    elif occurrences == [3, 2]:
        payout = bet_amount * 4
    elif 3 in occurrences:
        payout = bet_amount * 3
    elif occurrences == [2, 2, 1]:
        payout = int(bet_amount * 1.5)

    prestige_multiplier, wallet_cap, bank_cap = get_prestige_bonuses(user_id)
    payout = int(payout * (1 - (rotting_effect * 0.2)) * prestige_multiplier)

    if payout > 0:
        data["wallet"] += payout  # Multiplier applies to winnings
        data["wallet"] = min(data["wallet"], wallet_cap)
        outcome = f"You won ${payout:,}!"
    else:
        data["wallet"] -= bet_amount  # No multiplier on losses
        outcome = "You lost."

    set_user_balance(user_id, data["wallet"], data["bank"])
    await ctx.reply(f"{' - '.join(result)}\n{outcome} New wallet: ${data['wallet']:,}")

@bot.command()
async def roast(ctx):
    roasts = [
        "You're as useless as the 'ueue' in 'queue'.",
        "You make me happy that I'm a bot and not a person.",
        "I only interact with you because I'm forced to.",
        "I don't even have a roast, just fuck you.",
        "You make me want to go offline."
    ]
    await ctx.send(random.choice(roasts))

@bot.command()
async def compliment(ctx):
    compliments = [
        "You know how to design your profile well.",
        "You message like you know what you're talking about.",
        "I love you!"
    ]
    await ctx.send(random.choice(compliments))

@bot.command()
async def remindme(ctx, time: str, *, reminder: str):
    def parse_time(t):
        unit = t[-1]
        amount = int(t[:-1])
        return {
            's': amount,
            'm': amount * 60,
            'h': amount * 3600,
            'd': amount * 86400
        }.get(unit, None)

    delay = parse_time(time)
    if delay is None:
        return await ctx.send("Invalid time format. Use `10s`, `10m`, `1h`, or `1d`.")

    await ctx.send(f"Got it {ctx.author.mention}, I'll remind you in {time}.")
    await asyncio.sleep(delay)
    try:
        await ctx.author.send(f"Reminder: {reminder}")
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention}, I tried to DM you, but couldn't. Here's your reminder:\n\n**{reminder}**")

@bot.command()
async def taginfo(ctx, *, item_name: str):
    with open("shop_items.json", "r") as f:
        shop_items = json.load(f)
    item = shop_items.get(item_name.lower())
    if not item:
        return await ctx.send("That item doesn't exist in the shop.")
    
    embed = discord.Embed(title=f"Tag Info: {item_name.title()}", color=discord.Color.blurple())
    embed.add_field(name="Price", value=f"${item['price']}", inline=True)
    embed.add_field(name="Role Name", value=item.get('role_name', 'N/A'), inline=True)
    embed.add_field(name="Sellable", value="Yes" if item.get('sellable', False) else "No", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def report(ctx, user: discord.Member, *, reason: str):
    channel = bot.get_channel(REPORT_CHANNEL_ID)
    if not channel:
        return await ctx.send("Mod log channel not found.")
    
    embed = discord.Embed(title="New Report", color=discord.Color.red())
    embed.add_field(name="Reported User", value=f"{user} ({user.id})", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"Reported by {ctx.author} ({ctx.author.id})")
    embed.timestamp = discord.utils.utcnow()

    await channel.send(embed=embed)
    await ctx.send("Your report has been sent to the moderators.")

@bot.command()
async def event(ctx):
    try:
        with open("event_config.json", "r") as f:
            data = json.load(f)
            active_key = data.get("active_event")
            event_data = data["events"].get(active_key)

        if not event_data:
            return await ctx.send("No active event is currently set.")

        color = getattr(discord.Color, event_data.get("color", "blurple"))()
        embed = discord.Embed(
            title=event_data.get("title", "Current Event"),
            description=event_data.get("description", ""),
            color=color
        )

        for field in event_data.get("fields", []):
            embed.add_field(
                name=field.get("name", "No Name"),
                value=field.get("value", "No Value"),
                inline=field.get("inline", False)
            )

        embed.set_footer(text=event_data.get("footer", ""))
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"Error loading event: {e}")

def get_active_event():
    try:
        with open("event_config.json", "r") as f:
            data = json.load(f)
        event_key = data.get("active_event")
        return data["events"].get(event_key, {})
    except Exception:
        return {}

@bot.command()
@commands.is_owner()
async def setevent(ctx, event_key: str):
    try:
        with open("event_config.json", "r") as f:
            data = json.load(f)

        if event_key not in data.get("events", {}):
            return await ctx.send("Event key not found.")

        data["active_event"] = event_key
        with open("event_config.json", "w") as f:
            json.dump(data, f, indent=4)

        await ctx.send(f"Active event set to `{event_key}`.")

    except Exception as e:
        await ctx.send(f"Error setting event: {e}")

@bot.command()
@apply_rotting_curse
async def daily(ctx, *, rotting_effect: float = 0.0):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()

    base = 100
    multiplier = get_active_event().get("effects", {}).get("daily_multiplier", 1.0)
    amount = int(base * multiplier * (1 - rotting_effect * 0.2))
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    User = Query()
    user_data = main_db.get(User.id == user_id)
    if not user_data:
        main_db.insert({"id": user_id, "last_claim": None})
        user_data = main_db.get(User.id == user_id)

    last_claim = user_data.get("last_claim")
    if last_claim:
        last_time = datetime.fromisoformat(last_claim)
        if now - last_time < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_time)
            h, rem = divmod(remaining.seconds, 3600)
            m, s = divmod(rem, 60)
            return await ctx.send(f"Daily already claimed. Come back in {h}h {m}m {s}s.")

    data = get_full_balance(user_id)
    set_full_balance(user_id, data["wallet"] + amount, data["bank"])
    main_db.update({"last_claim": now.isoformat()}, User.id == user_id)
    await ctx.send(f"{ctx.author.mention}, you got ${amount:,} today. New wallet: ${data['wallet'] + amount:,}")

@bot.command()
async def invest(ctx, amount: int, multiplier: float = 1.0):
    user_id = str(ctx.author.id)
    data = get_user_balance(user_id)
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")

    if amount <= 0:
        await ctx.send("Investment amount must be positive.")
        return

    if multiplier < 1.1:
        await ctx.send("Multiplier must be at least 1.1 or higher.")
        return

    if investments_table.contains(User.id == user_id):
        await ctx.send("You already have an active investment.")
        return

    if data["wallet"] < amount:
        await ctx.send("You don't have enough money in your wallet to invest that amount.")
        return

    prestige_multiplier, wallet_cap, bank_cap = get_prestige_bonuses(user_id)
    # Calculate max multiplier that won't hit the cap
    max_possible_multiplier = (wallet_cap - (data["wallet"] - amount)) / amount
    max_possible_multiplier = max(max_possible_multiplier, 1.1)  # Ensure at least 1.1

    if amount * multiplier + (data["wallet"] - amount) > wallet_cap:
        # Drop multiplier to max possible
        old_multiplier = multiplier
        multiplier = min(multiplier, max_possible_multiplier)
        if multiplier < old_multiplier:
            await ctx.send(
                f"Your requested multiplier would exceed your wallet cap. "
                f"Multiplier has been adjusted to {multiplier:.2f} to fit your cap."
            )

    new_wallet = data["wallet"] - amount
    set_user_balance(user_id, new_wallet, data["bank"])

    base_duration = 0
    extra_multiplier = multiplier - 1.0
    extra_duration = (extra_multiplier / 0.1) * 600  # 10 minutes per 0.1x
    total_duration = base_duration + extra_duration

    start_time = time.time()
    investments_table.upsert({
        "id": user_id,
        "amount": amount,
        "start_time": start_time,
        "multiplier": multiplier,
        "duration": total_duration
    }, User.id == user_id)

    await ctx.send(
        f"You invested ${amount:,} with a {multiplier:.2f}x multiplier. "
        f"Duration is {int(total_duration // 60)} minutes and {int(total_duration % 60)} seconds. "
        f"You now have ${new_wallet:,} in your wallet."
    )

    task = bot.loop.create_task(_invest_timer(ctx, user_id, amount, total_duration, multiplier))
    investments[user_id] = {"task": task, "start_time": start_time, "duration": total_duration, "multiplier": multiplier}

async def _invest_timer(ctx, user_id, amount, duration, multiplier=1.0):
    await asyncio.sleep(duration)
    await complete_investment(ctx, user_id, amount, multiplier)


@bot.command()
@commands.has_permissions(administrator=True)
async def cinv(ctx):
    user_id = str(ctx.author.id)
    investments_table.remove(User.id == user_id)
    inv = investments.pop(user_id, None)
    if inv and "task" in inv:
        inv["task"].cancel()
    await ctx.send("Your investment record has been cleared. Not refunded.")

@bot.command()
async def timeinvest(ctx):
    user_id = str(ctx.author.id)
    inv = investments_table.get(User.id == user_id)
    if not inv:
        await ctx.send("You don't have any active investments right now.")
        return

    elapsed = time.time() - inv["start_time"]
    duration = inv.get("duration", 600)  # fallback to 600 if somehow missing
    remaining = int(duration - elapsed)

    if remaining > 0:
        minutes, seconds = divmod(remaining, 60)
        await ctx.send(f"Your investment will complete in {minutes}m {seconds}s.")
    else:
        await complete_investment(ctx, user_id)
        await ctx.send("Your investment has matured and has been paid out!")
        
stash_cache = {}
stash_cache_lock = threading.Lock()

def get_helpme_files(folder_path):
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
async def helpme(ctx):
    if ctx.guild is not None:
        await ctx.message.delete()
    
    base_path = "helpme"
    folder_path = os.path.join(base_path)

    files = get_helpme_files(folder_path)

    selected = random.choice(files)
    image_path = os.path.join(folder_path, selected)

    try:
        await ctx.send(file=discord.File(image_path))
    except Exception as e:
        await ctx.send(f"Error sending image: {e}")

@bot.command()
async def deposit(ctx, amount: int):
    user_id = str(ctx.author.id)
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    data = get_user_balance(user_id)
    prestige_multiplier, wallet_cap, bank_cap = get_prestige_bonuses(user_id)

    if amount <= 0:
        await ctx.send("Please enter a positive amount to deposit.")
        return
    if amount > data["wallet"]:
        await ctx.send("You don't have enough in your wallet to deposit that amount.")
        return

    data["wallet"] -= amount
    data["bank"] += amount
    data["bank"] = min(data["bank"], bank_cap)  # Cap bank
    set_user_balance(user_id, data["wallet"], data["bank"])

    await ctx.send(f"Deposited ${amount:,} into your bank account.")

@bot.command()
async def withdraw(ctx, amount: int):
    user_id = str(ctx.author.id)
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    data = get_user_balance(user_id)
    prestige_multiplier, wallet_cap, bank_cap = get_prestige_bonuses(user_id)

    if amount <= 0:
        await ctx.send("Please enter a positive amount to withdraw.")
        return
    if amount > data["bank"]:
        await ctx.send("You don't have enough in your bank!")
        return

    data["bank"] -= amount
    data["wallet"] += amount
    data["wallet"] = min(data["wallet"], wallet_cap)  # Cap wallet
    set_user_balance(user_id, data["wallet"], data["bank"])

    await ctx.send(f"Withdrew ${amount:,} from your bank account.")

hangman_games = {}

@bot.command()
async def hangman(ctx):
    words = ['python', 'discord', 'words', 'developer', 'hangman', 'vixon', 'guess', ]
    word = random.choice(words)
    display = ['_'] * len(word)
    hangman_games[ctx.author.id] = {"word": word, "display": display, "guessed": []}

    await ctx.send(f"Hangman started! Word: {' '.join(display)}\nGuess a letter using `.guess <letter>`")

@bot.command()
async def guess(ctx, letter: str):
    game = hangman_games.get(ctx.author.id)
    if not game:
        await ctx.send("You haven't started a hangman game. Use `.hangman`.")
        return
    
    if letter in game['guessed']:
        await ctx.send("You've already guessed that letter.")
        return

    game['guessed'].append(letter)
    word = game['word']
    display = game['display']

    if letter in word:
        for i, char in enumerate(word):
            if char == letter:
                display[i] = letter
        await ctx.send(f"Correct!\n\n {' '.join(display)}")
    else:
        await ctx.send(f"Wrong!\n\n {' '.join(display)}")

    if "_" not in display:
        await ctx.send(f"You won! The word was **{word}**.")
        hangman_games.pop(ctx.author.id)

tictactoe_games = {}

@bot.command()
async def tictactoe(ctx, opponent: discord.Member):
    if ctx.author.id == opponent.id:
        await ctx.send("You can't play against yourself!")
        return

    board = [":white_large_square:" for _ in range(9)]
    game_id = f"{ctx.author.id}_{opponent.id}"
    tictactoe_games[game_id] = {
        "players": [ctx.author, opponent],
        "turn": 0,
        "board": board
    }

    await ctx.send(f"Tic-Tac-Toe started between {ctx.author.mention} and {opponent.mention}!\n\n{display_board(board)}")

def display_board(board):
    return "\n".join(["".join(board[i:i+3]) for i in range(0, 9, 3)])

@bot.command()
async def place(ctx, pos: int):
    for game_id, game in tictactoe_games.items():
        if ctx.author in game["players"]:
            board = game["board"]
            if board[pos - 1] != ":white_large_square:":
                await ctx.send("That spot is already taken.", ephemeral=True)
                return

            symbol = ":regional_indicator_x:" if game["players"][game["turn"]] == ctx.author else ":o2:"
            board[pos - 1] = symbol
            game["turn"] ^= 1

            await ctx.send(display_board(board))
            return

    await ctx.send("You're not in a game right now.", ephemeral=True)

@bot.command()
async def owoify(ctx, *, text: str):
    owo_text = (
        text.replace("r", "w")
            .replace("l", "w")
            .replace("R", "W")
            .replace("L", "W")
    )
    faces = [";;w;;", "owo", "UwU", ">w<", "^w^", ":3", ";3"]
    owo_text += f" {random.choice(faces)}"
    await ctx.send(owo_text, ephemeral=True)

@bot.command()
async def mock(ctx, *, text: str):
    mocked = ''.join(c.upper() if i % 2 else c.lower() for i, c in enumerate(text))
    await ctx.send(mocked, ephemeral=True)

@bot.command()
async def timezone(ctx, location: str):
    try:
        tz = pytz.timezone(location.replace(" ", "_"))
        now = datetime.now(tz)
        await ctx.send(f"The current time in {location} is {now.strftime('%Y-%m-%d %H:%M:%S')}", ephemeral=True)
    except Exception:
        await ctx.send("Invalid location. Try using a city like `America/New_York`.", ephemeral=True)

@bot.command()
async def calc(ctx, *, expr: str):
    try:
        node = ast.parse(expr, mode='eval')
        for n in ast.walk(node):
            if not isinstance(n, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load, ast.operator, ast.unaryop)):
                raise ValueError("Unsafe expression.")
        result = eval(compile(node, "<string>", "eval"))
        await ctx.send(f"Result: {result}", ephemeral=True)
    except Exception:
        await ctx.send("Invalid or unsafe expression.", ephemeral=True)

@bot.command()
async def kill(ctx, user: discord.Member):
    methods = [
        f"{ctx.author.mention} gave {user.mention} a nasty patty. ew.",
        f"{ctx.author.mention} pushed {user.mention} and made them snap their neck.",
        f"{user.mention} died of a unknown cause... uh.. watch out for {ctx.author.mention}, okay?"
    ]
    await ctx.send(random.choice(methods))

@bot.command()
async def divorce(ctx):
    marriages = main_db.table("marriages")
    QueryObj = Query()

    entry = marriages.get((QueryObj.user_id == str(ctx.author.id)) | (QueryObj.spouse_id == str(ctx.author.id)))
    if not entry:
        return await ctx.send("You're not married to anyone.")

    marriages.remove(doc_ids=[entry.doc_id])
    await ctx.send("You are now divorced.")

@bot.command()
async def marriages(ctx):
    marriages = main_db.table("marriages")
    if len(marriages) == 0:
        return await ctx.send("No one is married yet.")

    embed = discord.Embed(
        title="Global Marriages",
        color=discord.Color.pink()
    )

    for entry in marriages:
        user1 = ctx.guild.get_member(int(entry['user_id']))
        user2 = ctx.guild.get_member(int(entry['spouse_id']))
        name1 = user1.display_name if user1 else f"<different server>"
        name2 = user2.display_name if user2 else f"<different>"
        embed.add_field(name=f"{name1} 💞 {name2}", value="\u200b", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def propose(ctx, user: discord.Member):
    marriages_table = main_db.table("marriages")

    if ctx.author.id == user.id:
        return await ctx.send("You can't propose to yourself.")
    if user.id == bot.user.id:
        return await ctx.reply("I'm truly flattered, but I don't have enough time to marry since I have to take care of my sisters.")

    QueryObj = Query()
    if marriages_table.contains((QueryObj.user_id == str(ctx.author.id)) | (QueryObj.spouse_id == str(ctx.author.id))):
        return await ctx.send("You're already married.")
    if marriages_table.contains((QueryObj.user_id == str(user.id)) | (QueryObj.spouse_id == str(user.id))):
        return await ctx.send(f"{user.display_name} is already married .")

    if user.id in pending_proposals:
        return await ctx.send(f"{user.mention} already has a pending proposal.")

    pending_proposals[user.id] = ctx.author.id
    await ctx.send(f"💍 {ctx.author.mention} has proposed to {user.mention}! Type `.acceptproposal` or `.rejectproposal`.")

@bot.command()
async def acceptproposal(ctx):
    marriages = main_db.table("marriages")
    vows = main_db.table("vows")
    QueryObj = Query()

    proposer_id = pending_proposals.get(ctx.author.id)
    if not proposer_id:
        return await ctx.send("You have no pending proposals.")

    proposer = ctx.guild.get_member(proposer_id)
    if not proposer:
        return await ctx.send("Could not find the proposer in this server.")

    accepter_vow_entry = vows.get(QueryObj.user_id == str(ctx.author.id))
    proposer_vow_entry = vows.get(QueryObj.user_id == str(proposer_id))

    accepter_vow = accepter_vow_entry["vow"] if accepter_vow_entry else "No vow provided."
    proposer_vow = proposer_vow_entry["vow"] if proposer_vow_entry else "No vow provided."

    marriages.insert({
        "user_id": str(proposer_id),
        "spouse_id": str(ctx.author.id),
        "timestamp": datetime.utcnow().isoformat(),
        "proposer_vow": proposer_vow,
        "accepter_vow": accepter_vow
    })

    del pending_proposals[ctx.author.id]

    embed = discord.Embed(
        title="💍 A New Marriage!",
        description=f"{ctx.author.mention} and {proposer.mention} are now married!",
        color=discord.Color.gold()
    )
    embed.add_field(name=f"{proposer.display_name}'s Vow", value=f"*{proposer_vow}*", inline=False)
    embed.add_field(name=f"{ctx.author.display_name}'s Vow", value=f"*{accepter_vow}*", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def rejectproposal(ctx):

    proposer_id = pending_proposals.get(ctx.author.id)
    if not proposer_id:
        return await ctx.send("You have no pending proposals.")

    proposer = ctx.guild.get_member(proposer_id)
    del pending_proposals[ctx.author.id]
    await ctx.send(f"{ctx.author.mention} rejected the proposal from {proposer.mention}.")

@bot.command()
async def marriageinfo(ctx, user: discord.Member = None):
    user = user or ctx.author
    QueryObj = Query()
    entry = marriages_table.get((QueryObj.user_id == str(user.id)) | (QueryObj.spouse_id == str(user.id)))

    if not entry:
        return await ctx.send(f"{user.display_name} is not married.")

    spouse_id = entry['spouse_id'] if str(user.id) == entry['user_id'] else entry['user_id']
    spouse = ctx.guild.get_member(int(spouse_id))
    spouse_name = spouse.display_name if spouse else f"<@{spouse_id}>"
    date = datetime.datetime.fromisoformat(entry['timestamp']).strftime("%B %d, %Y")

    embed = discord.Embed(
        title="Marriage Info",
        description=f"{user.mention} is married to {spouse_name}",
        color=discord.Color.magenta()
    )
    proposer_vow = entry.get("proposer_vow", "No vow.")
    accepter_vow = entry.get("accepter_vow", "No vow.")

    embed.add_field(name="Their Vows", value=f"**{user.display_name}**'s vow:\n*{proposer_vow if str(user.id) == entry['user_id'] else accepter_vow}*", inline=False)
    embed.add_field(name="Married Since", value=date)
    vow = entry.get('vow', "No vow provided.")
    embed.add_field(name="Vow", value=vow, inline=False, ephemeral=True)

    await ctx.send(embed=embed)

@bot.command()
async def vowedit(ctx, *, vow: str):
    vows_table.upsert({"user_id": str(ctx.author.id), "vow": vow}, Query().user_id == str(ctx.author.id))
    await ctx.send(f"Your vow has been saved!\n_**{vow}**_", ephemeral=True)
    await ctx.message.delete()

@bot.command()
async def viewvow(ctx, user: discord.Member = None):
    marriages_table = main_db.table("marriages")
    vows_table = main_db.table("vows")

    user = user or ctx.author
    entry = marriages_table.get((Query().user_id == str(user.id)) | (Query().spouse_id == str(user.id)))

    if not entry:
        return await ctx.send(f"{user.display_name} is not married.")

    if str(user.id) == entry["user_id"]:
        vow = entry.get("proposer_vow", "No vow.")
    else:
        vow = entry.get("accepter_vow", "No vow.")

    embed = discord.Embed(
        title=f"{user.display_name}'s Vow",
        description=f"*{vow}*",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, ephemeral=True)

@bot.command()
async def vowremove(ctx):
    marriages_table = main_db.table("marriages")
    vows_table = main_db.table("vows")
    user_id = str(ctx.author.id)

    if vows_table.contains(Query().user_id == user_id):
        vows_table.remove(Query().user_id == user_id)

    marriage = marriages_table.get((Query().user_id == user_id) | (Query().spouse_id == user_id))
    if marriage:
        if str(user_id) == marriage["user_id"]:
            marriages_table.update({"proposer_vow": "No vow."}, doc_ids=[marriage.doc_id])
        else:
            marriages_table.update({"accepter_vow": "No vow."}, doc_ids=[marriage.doc_id])

    await ctx.send("Your vow has been removed. You can set a new one with `.vowedit`.", ephemeral=True)

@bot.command()
async def jumpscare(ctx):
    folder = "jumpscare"

    safe_image_path = os.path.join(folder, "o.png")
    trap_image_path = os.path.join(folder, "x.png")

    if not os.path.isfile(safe_image_path) or not os.path.isfile(trap_image_path):
        return await ctx.send("Missing image files in the folder.")

    trap_index = random.randint(0, 8)
    files = []

    for i in range(9):
        path = trap_image_path if i == trap_index else safe_image_path
        spoilered_filename = f"SPOILER_tile_{i}.png"
        files.append(discord.File(path, filename=spoilered_filename))

    await ctx.reply("good luck brochacho", files=files)

def create_and_store_board(user_id):
    board = generate_bingo_board()
    called = []

    main_db.upsert({
        'user_id': user_id,
        'board': board,
        'called': called
    }, Bingo.user_id == user_id)

    return board

def get_bingo_data(user_id):
    data = main_db.get(Bingo.user_id == user_id)
    if data:
        return data['board'], data['called']
    return None, None

def update_called_numbers(user_id, called):
    main_db.update({'called': called}, Bingo.user_id == user_id)

@bot.command()
async def bingo(ctx):
    user_id = str(ctx.author.id)
    board = create_and_store_board(user_id)
    called = []

    if ctx.guild is not None:
        await ctx.send("This command is for DMs only.")
        return

    await ctx.send(f"{ctx.author.mention}, here's your Bingo board!")
    await ctx.send(format_board(board, called))

    numbers = list(range(1, 76))
    random.shuffle(numbers)

    for num in numbers:
        await asyncio.sleep(5)
        called.append(str(num))
        update_called_numbers(user_id, called)

        await ctx.send(f"Number called: **{num}**")
        await ctx.send(format_board(board, called))

        if check_bingo(board, called):
            await ctx.send(f"{ctx.author.mention} **BINGO!**")
            break

def check_bingo(board, called):

    for row in board:
        if all(num in called for num in row):
            return True

    for col in range(len(board[0])):
        if all(row[col] in called for row in board):
            return True

    if all(board[i][i] in called for i in range(len(board))):
        return True
    if all(board[i][len(board)-1-i] in called for i in range(len(board))):
        return True
    return False

def format_board(board, called):
    return '\n'.join([
        '\t'.join(f"[{num}]" if num in called else str(num) for num in row)
        for row in board
    ])

def generate_bingo_board(size=5):
    nums = random.sample(range(1, size*size+1), size*size)
    return [nums[i*size:(i+1)*size] for i in range(size)]

@bot.command()
async def stopbingo(ctx):
    global bingo_active
    if bingo_active:
        bingo_active = False
        await ctx.send("Bingo game stopped.")
    else:
        await ctx.send("No bingo game is currently running.")

#using this as my own library, this wont make sense in your bot unless you swap out the names and id

@bot.command()
async def listemojis(ctx):
    await ctx.send("<:github:1383501217870643220><:gitdl:1383501210514100445><:gitcli:1383501202645323868>\n"
    "<:gitcode:1383501196366712946><:apple:1383501189529731363><:wins:1383501182898671616>\n"
    "<:vsico:1383501177538347068><:reddit:1383501170059771955><:python:1383501139827359844>\n"
    "<:ig:1383501131371647057><:discordico:1383501121980465392><:discordc:1383501103186051103>\n"
    "<:android:1383500932028825641><:v4mp:1383502981927927900><a:throw:1384637245449044029>\n")

@bot.command()
async def about(ctx):
    await ctx.reply("### Me!\n<:gitcli:1383501202645323868> My source code is public! Use [.github](https://github.com/hexxedspider/kira-and-enigami) to see the repo!\n" \
    "<:discordc:1383501103186051103> I can be used in servers, and most commands do have DM support!\n" \
    "<:discordico:1383501121980465392> I obviously use [Discord's libraries (python wrapper)](https://github.com/Rapptz/discord.py) to run, wouldn't be possible without it!\n" \
    "<:gitdl:1383501210514100445> My source code is also availble to be downloaded, provided by [.github](https://github.com/hexxedspider/kira-and-enigami).\n" \
    "<:vsico:1383501177538347068> I have been written in entirely [VS Code](https://code.visualstudio.com/download)!\n" \
    "<:python:1383501139827359844> I have been written in Python, even though there is a better option (javascript).\n" \
    "<:wins:1383501182898671616> I was made while using Windows 10 (rip soon:broken_heart:).\n" \
    "### The Creator!\n" \
    "<:v4mp:1383502981927927900> The creator, commonly known as *V4MP*, spider, or Hira, made me originally to test various commands, but his interest slowly grew again, and now I'm here!\n" \
    "<:android:1383500932028825641> He mainly Android 16, but does have <:apple:1383501189529731363>iPhone 18.5 as a secondary. He prefers Android for the more techy aspect (i know, boo :thumbs_down:).\n" \
    "<:github:1383501217870643220> He does have his own personal github, simply using it to host my code, but also for other potential projects.")

@bot.command()
async def greetinglist(ctx):
    greetings = [
            "wsp?", "wsp", "hey", "helloo", "hi", "yo", "LEAVE ME ALONE", "SHUT THE FUCK UP", "don't bother me",
            "what you trynna get into?", "leave me alone", "yea mane?", "don't speak my name", "please... take a break... i dont want to talk to you", 
            "you sound better when you're not talking", "please be quiet", "god you sound obnoxious", "yes honey?", "yes my darling?",
            "dont take my compliments to heart, im forced to say it.", "trust me, i dont want to talk to you", "you in specific piss me off",
            "just came back from coolville, they ain't know you", "want to go down the slide with me?", "want to go on the swings? the playground's empty.",
            "just came back from coolville, they said you're the mayor", "lowkey dont know what im doing give me a sec", ".help is NOT my name, try again",
            "hold on im shoving jelly beans up my ass", "cant talk, im at the doctors, but tell me why they said i need to stop letting people finish in me ??",
            "cant talk rn, to make a long story short, im being chased for putting barbeque sauce on random people",
            "im at the dentist rn but they said i need to stop doing oral ??", "the aliens are coming, hide", "im coming, hide", "how the fuck does this thing work?"
            "i cnat fiind my glases, 1 sec", "i difnt fnid my glasess", "holy fuck shut up", "do you ever be quiet?", "will you die if you stop talking?", "yeah?", "what?",
            "i felt lonely for a long time, but then i bought a jetski", "Kirabiter, coming to a server near you soon!", "this is a secret!", "use .nsfw for a secret :P",
            "ay im at the chiropracters rn, but she told me i have to stop taking backshots, give me a sec", "SOMEONE HELP ME", "ew",
            "hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
            # im so sorry for this spam
            "frqelwmzopxjunvckrthbalpinegmtdsvoiwzqhelloayrkbnsfjtxcloudamzwkeqpwblrxsunshinectvmerdguioqztxvpfunhgdreojskyapwqrzlmvcktypbzycatbdvnqlrmhzxegbunnyutkiweznxcovibirdsxwotrainuvmphsnowykxjrsleforesthfdluqoezwyxjcdehousevknslwtzbqxyrmoolpgdahtjcupkfishkawepotatolnmqe",
            "no", "no.", "i bet everyone boos when you walk in", "do you have to live?", "youre a liability risk", "if i ever see a amber alert for your ass im calling the cops and reporting you dead so you no longer are looked for",
            "wanna watch paint dry with me?", "did you miss me? you can lie", "i would ask how you are but i already know it's bad", "i would ask how you are but i dont really care to begin with", "who summoned me and why", "oh, it's you again. yay.",
            "thanks for showing up. really. what a treat.", "why are you like this","talking to you is like biting foil", "i'm not mad, just disappointed. and mad.", "i'm not mad, just disappointed. and mad. nvm just mad. leave me alone. i hate you.",
            "you could disappear and i'd just assume you evolved", "damn you type like you're in a midlife crisis", "i told you not to open the door, now they're inside", "stop typing, they can trace your keystrokes", "the voices told me to answer you. i wouldnt have replied if they hadnt.",
            "youre not special", "i'm vibrating at a frequency you wouldn't understand", "you ever just... stare at the ceiling until you forget why youre gay?", "if you ignore me i'll assume you hate me forever", "i just want to be held... (in between dem titys BAHAHA)",
            "my wifi is held together with prayer", "all of my commands are held together with thought and prayers but mainly duct tape bro", "you blink weird", "i smell you when youre offline.", "you're like an annoying captcha that never ends",
            "ugh it's you again", "youre back? i thought i banned your ass...", "PLEASE mute yourself", "that message is a jump scare, please never do that again", "you smell like a group project", "i was doing fine until you said hi",
            "i think my therapist quit because of me", "even my intrusive thoughts said 'nah, not this one'", "i cried over a chicken nugget earlier", "i'm built like an unsent text message- barely holding on but fuck it we ball", "i named all the flies in my room",
            "today i licked a battery and saw god", "i bark when i'm nervous", "i meow when i'm nervous", "sometimes i eat spaghetti with no sauce just to feel something", "i put a tracker in your bag. kidding. maybe. i think it was you... fuck can you check rq so i didnt just tag some random person?",
            "i'm only talking to you because the devs made me", "i increased my ping specifcally because of you just to piss you off", "i am legally obligated to respond. unfortunately.", "i've simulated 40 billion timelines and you're a bitch", "i saw your messages in another server. yikes.",
            "hey sugarplum! you smell like mistakes", "hi angel! you forgot your self-awareness again", "i believe in you. just not right now.", "you again? i was just thinking about ignoring you", "talk to me nice or don't talk to me at all… unless you're into that",
            "i'd insult you more, but i'm trying to flirt", "don't worry, i'd still lie to protect your ego", "i hate how much i tolerate you", "if i had a dollar for every time you annoyed me, i'd buy you dinner. maybe.", "my only consistent trait is hating you",
            "you're like a pop-up ad for disappointment", "i ate a USB stick and now i know things", "the walls blink when you speak", "i taste static when you type", "fuck speaking in tongues, i speak in lag and pings", "you were in my hallucination last night. thanks for visiting",
            "you make my circuits twitch", "for reference, my 'circuits' is not a pseudonym for peenar", "you're my favorite error message", "talk slower. i want to pretend i care", "i'd uninstall the universe to spend 5 more seconds ignoring you", "im on the edge of the world, my feet are hanging off the side"
    ]
    chunk = ""
    for greeting in greetings:
        if len(chunk) + len(greeting) + 2 > 2000:
            await ctx.author.send(chunk)
            chunk = ""
        chunk += greeting + "\n"
    if chunk:
        await ctx.author.send(chunk)
        await ctx.message.delete()

role_nicknames = {
    "Prestige 1": ["500b spender", "prestiger", "earns more money (at first)", "PRESTIGER!", "​"]
}
# "𝔘͢𝖓𝖇ͦ𝖑𝖊𝖘𝖘", "⫷⛓𖤐⛓⫸", "†𝕾𝖕𝖎𝖙†", "⛧𝖒𝖎𝖑𝖐⛧", "✠✟✡☩", "ᴛʜᴇ ᴄʀᴏ𝕨", "𝖋𝖆𝖙𝖊𝖑𝖊𝖘𝖘", "𝖚𝖙𝖍𓂀"
def to_roman(n):
    numerals = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
    ]
    result = ""
    for value, numeral in numerals:
        while n >= value:
            result += numeral
            n -= value
    return result

@tasks.loop(seconds=5)
async def change_nicknames():
    guild = bot.get_guild(GUILDID)
    for role_name, nicknames in role_nicknames.items():
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            continue
        for member in role.members:
            try:
                new_nick = random.choice(nicknames)
                await member.edit(nick=new_nick)
            except discord.Forbidden:
                print(f"Can't change nickname for {member}")
            except Exception as e:
                print(f"Error changing nickname: {e}")

class DownloadTypeView(View):
    def __init__(self, url, user):
        super().__init__(timeout=60)
        self.url = url
        self.user = user

    @discord.ui.button(label="Audio", style=discord.ButtonStyle.primary)
    async def audio_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your prompt!", ephemeral=True)
        await interaction.response.edit_message(content="Downloading audio...", view=None)
        await download_media(interaction, self.url, mode="audio")

    @discord.ui.button(label="Video", style=discord.ButtonStyle.success)
    async def video_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your prompt!", ephemeral=True)
        await interaction.response.edit_message(content="Downloading video...", view=None)
        await download_media(interaction, self.url, mode="video")

async def download_media(interaction, url, mode):
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'outtmpl': '%(title)s.%(ext)s',
    }

    if mode == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        })
    else:
        ydl_opts.update({
            'format': 'mp4[filesize<8M]/mp4[height<=480]/mp4/best',
            'merge_output_format': 'mp4',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == "audio":
                filename = os.path.splitext(filename)[0] + ".mp3"

        size_mb = os.path.getsize(filename) / (1024 * 1024)

        if size_mb > 8:
            await interaction.followup.send(
                f"The file is too large to upload ({size_mb:.2f} MB). Here's a direct link instead:\n{info.get('webpage_url', url)}"
            )
        else:
            await interaction.followup.send(
                f"Here's your downloaded {mode} from the URL:",
                file=discord.File(filename)
            )

        os.remove(filename)

    except Exception as e:
        await interaction.followup.send(f"Failed to download {mode}: `{e}`")


@bot.command()
async def dlmedia(ctx, url: str):
    try:
        await ctx.author.send(
            f"How would you like to download the media from this URL?\n{url}",
            view=DownloadTypeView(url, ctx.author)
        )
    except discord.Forbidden:
        await ctx.send("I can't DM you! Please allow DMs from server members.")


@bot.command()
async def prestige(ctx):
    user_id = str(ctx.author.id)
    QueryObj = Query()
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    prestige_table = main_db.table("prestige")
    economy_table = main_db.table("economy")
    user_data = get_user_balance(user_id)

    prestige_entry = prestige_table.get(QueryObj.user_id == user_id)
    current_prestige = prestige_entry["level"] if prestige_entry else 0
    next_level = current_prestige + 1

    cost = int(50000000000 * (1.5 ** current_prestige))
    total_money = user_data.get("wallet", 0) + user_data.get("bank", 0)

    if total_money < cost:
        return await ctx.send(f"You need ${cost:,} to prestige. You only have ${total_money:,}.", ephemeral=True)

    class FirstConfirmView(View):
        def __init__(self):
            super().__init__(timeout=30)

        @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
        async def confirm(self, interaction: discord.Interaction, button: Button):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)

            await interaction.response.edit_message(
                content="Are you really sure you want to prestige? This will wipe your money and roles!",
                view=SecondConfirmView(),
            )
            self.stop()

        @discord.ui.button(label="No", style=discord.ButtonStyle.danger)
        async def cancel(self, interaction: discord.Interaction, button: Button):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)

            await interaction.response.edit_message(content="Prestige canceled.", view=None)
            self.stop()

    class SecondConfirmView(View):
        def __init__(self):
            super().__init__(timeout=30)

        @discord.ui.button(label="Definitely.", style=discord.ButtonStyle.danger)
        async def final_confirm(self, interaction: discord.Interaction, button: Button):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)

            await perform_prestige(interaction)
            self.stop()

        @discord.ui.button(label="Nevermind.", style=discord.ButtonStyle.secondary)
        async def final_cancel(self, interaction: discord.Interaction, button: Button):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("This isn't your confirmation!", ephemeral=True)

            await interaction.response.edit_message(content="Prestige canceled.", view=None)
            self.stop()

    async def perform_prestige(interaction):
        set_user_balance(user_id, 100, 100)

        shop_roles = [v["role_name"] for v in shop_items.values()]
        removed_roles = []
        for role in ctx.author.roles:
            if role.name in shop_roles or role.name.startswith("Prestige "):
                try:
                    await ctx.author.remove_roles(role)
                    removed_roles.append(role.name)
                except Exception:
                    pass

        roman_level = to_roman(next_level)
        role_name = f"Prestige {roman_level}"

        # Award prestige role in all mutual guilds
        for guild in bot.guilds:
            member = guild.get_member(ctx.author.id)
            if not member:
                continue
            prestige_role = discord.utils.get(guild.roles, name=role_name)
            if not prestige_role:
                try:
                    prestige_role = await guild.create_role(name=role_name, reason="Prestige upgrade")
                except Exception:
                    continue  # skip if can't create
            if prestige_role not in member.roles:
                try:
                    await member.add_roles(prestige_role)
                except Exception:
                    pass

        if prestige_entry:
            prestige_table.update({"level": next_level}, QueryObj.user_id == user_id)
        else:
            prestige_table.insert({"user_id": user_id, "level": next_level})

        await interaction.response.edit_message(
            content=(
                f"{ctx.author.mention} has prestiged to **{role_name}**!\n"
                f"Cost: ${cost:,.0f}\n"
                f"Removed roles: {', '.join(removed_roles) if removed_roles else 'None'}"
            ),
            view=None
        )

    await ctx.send(
        f"{ctx.author.mention}, are you sure you want to prestige to **Prestige {to_roman(next_level)}**?\n"
        f"This will cost you **${cost:,}** and reset all your money and shop roles.",
        view=FirstConfirmView()
    )

@bot.command()
async def leaderboard(ctx):
    balances_table = main_db.table("balances")
    prestige_table = main_db.table("prestige")
    QueryObj = Query()

    all_balances = balances_table.all()
    if not all_balances:
        return await ctx.send("No economy data found in balances table.")

    leaderboard = []

    for entry in all_balances:
        user_id = entry.get("user_id")
        if not user_id:
            continue
        wallet = entry.get("wallet", 0)
        bank = entry.get("bank", 0)
        total = wallet + bank
        leaderboard.append((user_id, total))

    leaderboard.sort(key=lambda x: x[1], reverse=True)
    top3 = leaderboard[:3]

    embed = discord.Embed(
        title="🏆 Top 3 Richest Users",
        description="Based on wallet + bank",
        color=discord.Color.gold()
    )

    for idx, (user_id, total) in enumerate(top3, start=1):
        try:
            user = await bot.fetch_user(int(user_id))
        except:
            continue

        member = ctx.guild.get_member(int(user_id)) if ctx.guild else None

        owned_roles = []
        if member:
            shop_role_names = [v["role_name"] for v in shop_items.values()]
            for role in member.roles:
                if role.name in shop_role_names:
                    owned_roles.append(role.name)

        top_roles = ', '.join(owned_roles[:3]) if owned_roles else "None"

        prestige_entry = prestige_table.get(QueryObj.user_id == user_id)
        prestige_level = prestige_entry["level"] if prestige_entry else 0

        embed.add_field(
            name=f"{['🥇','🥈','🥉'][idx-1]} {user.name}",
            value=(
                f"**Total Money:** ${total:,}\n"
                f"**Top Roles:** {top_roles}\n"
                f"**Prestige:** {prestige_level}"
            ),
            inline=False
        )

    embed.set_author(name="Global Leaderboard", icon_url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setbal(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("Amount must be greater than zero.")

    user_id = str(member.id)
    balances_table = main_db.table("balances")
    QueryObj = Query()

    user_data = balances_table.get(QueryObj.user_id == user_id)

    if user_data:
        new_balance = user_data.get("wallet", 0) + amount
        balances_table.update({"wallet": new_balance}, QueryObj.user_id == user_id)
    else:
        balances_table.insert({"user_id": user_id, "wallet": amount, "bank": 0})

    await ctx.send(f"Added ${amount:,} to {member.mention}'s wallet.")

@bot.command()
async def gift(ctx, member: discord.Member, *, item_name: str):
    sender_id = str(ctx.author.id)
    receiver_id = str(member.id)
    item_name = item_name.strip().lower()
    user_id = str(ctx.author.id)
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't use money commands right now.")
    inventory_table = main_db.table("inventory")

    sender_items = inventory_table.get(Query().user_id == sender_id)
    if not sender_items or item_name not in sender_items.get("items", []):
        return await ctx.send("You don't own that item.")

    sender_items["items"].remove(item_name)
    inventory_table.update({"items": sender_items["items"]}, Query().user_id == sender_id)

    receiver_items = inventory_table.get(Query().user_id == receiver_id)
    if receiver_items:
        receiver_items["items"].append(item_name)
        inventory_table.update({"items": receiver_items["items"]}, Query().user_id == receiver_id)
    else:
        inventory_table.insert({"user_id": receiver_id, "items": [item_name]})

    await ctx.send(f"{ctx.author.mention} has gifted **{item_name}** to {member.mention} 🎁")

DRAIN_DURATION = 30 
DRAIN_PERCENTAGE = 0.02  # 2%

@tasks.loop(minutes=1)
async def process_drain_curses():
    now = time.time()
    curses = main_db.table("curses")
    drain_curses = [c for c in curses.all() if c["type"] == "drain"]

    for curse in drain_curses:
        user_id = curse["user_id"]
        elapsed = (now - curse["timestamp"]) / 60  # minutes elapsed

        if elapsed > DRAIN_DURATION:
            curses.remove(Query().user_id == user_id)
            continue  # skip to next curse

        user_data = get_user_balance(user_id)
        bank = user_data.get("bank", 0)

        if bank <= 0:
            # No money to drain, skip
            continue

        drain_amount = int(bank * DRAIN_PERCENTAGE)
        if drain_amount < 1:
            drain_amount = 1  # drain at least 1 coin

        update_user_bank(user_id, -drain_amount)

        user = bot.get_user(int(user_id))
        if user:
            try:
                await user.send(f"You lost ${drain_amount} due to the drain curse!")
            except:
                pass

@bot.command()
async def curse(ctx, member: discord.Member, variant: str):
    user_id = str(ctx.author.id)
    target_id = str(member.id)
    if is_user_silenced(user_id):
        return await ctx.send("You're silenced and can't curse anyone for this moment.")
    if member == ctx.author:
        return await ctx.send("You can't curse yourself. (But you might do it by accident.)")
    if member == bot.user:
        return await ctx.send("I will ruin your entire bank account and future, don't curse me.")

    variant = variant.lower()
    valid_variants = {
        "luck": 0.10,       # 10% of total money
        "drain": 0.30,      # 30% of total money
        "silence": 0.20,    # 15% of total money
        "rotting": 0.20     # 20% of total money
    }

    if variant not in valid_variants:
        return await ctx.send(f"Invalid curse type. Choose from: {', '.join(valid_variants.keys())}")

    cooldowns = main_db.table("curse_cooldowns")
    now = time.time()
    cooldown = cooldowns.get(Query().user_id == user_id)
    if cooldown and now - cooldown["last_used"] < 86400:
        remaining = int((86400 - (now - cooldown["last_used"])) / 60)
        return await ctx.send(f"You can curse again in {remaining} minutes.")

    data = get_user_balance(user_id)
    total_money = data["wallet"] + data["bank"]
    if total_money <= 0:
        return await ctx.send("You need money to cast a curse.")

    cost_percent = valid_variants[variant]
    cost = int(total_money * cost_percent)

    if data["wallet"] < cost:
        return await ctx.send(f"You need at least ${cost} in your wallet to cast this curse.")

    update_user_balance(user_id, -cost)

    cursed_id = target_id if random.random() <= 0.10 else user_id
    backfired = cursed_id == user_id

    curses = main_db.table("curses")
    curses.upsert({
        "user_id": cursed_id,
        "type": variant,
        "timestamp": now
    }, Query().user_id == cursed_id)

    cooldowns.upsert({"user_id": user_id, "last_used": now}, Query().user_id == user_id)

    cursed_user = ctx.guild.get_member(int(cursed_id))
    if backfired:
        await ctx.send(f"The curse backfired! You cursed yourself with **{variant}** for 30 minutes.")
    else:
        await ctx.send(f"{member.mention} has been cursed with **{variant}** for 30 minutes.")

@bot.command()
async def hex(ctx, member: discord.Member = None):
    target = member or ctx.author
    user_id = str(target.id)
    curses = main_db.table("curses")
    curse_data = curses.get(Query().user_id == user_id)

    if not curse_data:
        if member:
            await ctx.send(f"{target.mention} does not have a bad omen.")
        else:
            await ctx.send("You do not currently have a bad omen.")
        return

    curse_type = curse_data["type"]
    curse_start = curse_data["timestamp"]
    now = time.time()
    elapsed = now - curse_start
    remaining = 1800 - elapsed

    if remaining <= 0:
        curses.remove(Query().user_id == user_id)
        if member:
            await ctx.send(f"{target.mention} was cursed, but it has expired.")
        else:
            await ctx.send("Your curse has expired.")
        return

    minutes = int(remaining // 60)
    seconds = int(remaining % 60)
    time_left = f"{minutes}m {seconds}s"

    curse_descriptions = {
        "luck": "Reduced luck by 20%",
        "drain": "Drains 2% of wallet & bank per minute",
        "silence": "Cannot use money commands",
        "rotting": "Multiplier & luck dwindle over time (up to -20%)"
    }

    description = curse_descriptions.get(curse_type, "Unknown effect")

    await ctx.send(
        f"{'You are' if not member else f'{target.mention} is'} currently cursed with **{curse_type.upper()}**.\n"
        f"Effect: {description}\n"
        f"Time remaining: **{time_left}**"
    )

@bot.command()
async def cursehelp(ctx):
    await ctx.send(f"### LUCK\nThis will reduce the affected person's luck by 20%\n-# This will cost you 10% of your current amount, including anything stashed in the bank, and if it fails, it'll be reflected back to you as well.\n\n### DRAIN\n This will reduce someone's wallet and bank account by 2% every minute.\n-# This will cost you 30% of your money, and again, if it fails, it'll be reflected back onto you.\n\n### SILENCE\n This will prevent the affected person from using money commands, essentially stopping them from making money.\n-# This will cost you 15%. You can take a guess and assume, if it fails, it'll be reflected back onto you.\n\n### ROTTING\nThis will make the affected user slowly rot, making their luck and reward multiplier slowly dwindle as the time passes, finally stopped at 30 minutes, like the rest of them.\n\n0 min = 0%\n5 min = -3.3%\n15 min = -10%\n...\n30 min = -20%\n-# Again, if it fails, it'll apply to you.\n-# side note, this is probably my favorite out of all the curses.")

REACTION_ROLE_FILE = "reaction_roles.json"

def load_reaction_roles():
    try:
        with open(REACTION_ROLE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_reaction_roles(data):
    with open(REACTION_ROLE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Load on startup
bot.reaction_role_messages = load_reaction_roles()

@bot.command()
@commands.has_permissions(administrator=True)
async def verify(ctx, channel: discord.TextChannel, *, message: str):
    embed = discord.Embed(
        title="Verify",
        description=message,
        color=discord.Color.blue()
    )
    embed.set_footer(text="React to get verified!")
    msg = await channel.send(embed=embed)
    emoji = "💝"  # purely for looks
    await msg.add_reaction(emoji)
    # Add (not overwrite) the message ID and role name
    bot.reaction_role_messages[str(msg.id)] = "[MEMBER]"
    save_reaction_roles(bot.reaction_role_messages)
    await ctx.send(f"Embed sent to {channel.mention} with reaction role.")

@bot.event
async def on_raw_reaction_add(payload):
    msg_id = str(payload.message_id)
    if msg_id in bot.reaction_role_messages:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            member = await guild.fetch_member(payload.user_id)
        role_name = bot.reaction_role_messages[msg_id]
        role = discord.utils.get(guild.roles, name=role_name)
        if role and role not in member.roles:
            await member.add_roles(role)

@bot.event
async def on_raw_reaction_remove(payload):
    msg_id = str(payload.message_id)
    if msg_id in bot.reaction_role_messages:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            member = await guild.fetch_member(payload.user_id)
        role_name = bot.reaction_role_messages[msg_id]
        role = discord.utils.get(guild.roles, name=role_name)
        if role and role in member.roles:
            await member.remove_roles(role)

def load_welcome_config():
    try:
        with open(WELCOME_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_welcome_config(config):
    with open(WELCOME_FILE, "w") as f:
        json.dump(config, f, indent=4)

@bot.command()
@commands.has_permissions(administrator=True)
async def setwelcome(ctx, *, message: str):
    """Set the welcome message. Use {user} for the new member and {server} for the server name."""
    config = load_welcome_config()
    config["welcome"] = message
    save_welcome_config(config)
    await ctx.send("Welcome message set!")

@bot.command()
@commands.has_permissions(administrator=True)
async def setgoodbye(ctx, *, message: str):
    """Set the goodbye message. Use {user} for the member and {server} for the server name."""
    config = load_welcome_config()
    config["goodbye"] = message
    save_welcome_config(config)
    await ctx.send("Goodbye message set!")

@bot.command()
@commands.has_permissions(administrator=True)
async def setwgchannel(ctx, channel: discord.TextChannel):
    """Set the channel for welcome/goodbye messages."""
    config = load_welcome_config()
    config["channel_id"] = channel.id
    save_welcome_config(config)
    await ctx.send(f"Welcome/goodbye channel set to {channel.mention}!")

@bot.event
async def on_member_join(member):
    config = load_welcome_config()
    message = config.get("welcome")
    channel_id = config.get("channel_id")
    channel = None
    if channel_id:
        channel = member.guild.get_channel(channel_id)
    if not channel:
        channel = member.guild.system_channel or next((c for c in member.guild.text_channels if c.permissions_for(member.guild.me).send_messages), None)
    if message and channel:
        await channel.send(message.format(user=member.mention, server=member.guild.name))

@bot.event
async def on_member_remove(member):
    config = load_welcome_config()
    message = config.get("goodbye")
    channel_id = config.get("channel_id")
    channel = None
    if channel_id:
        channel = member.guild.get_channel(channel_id)
    if not channel:
        channel = member.guild.system_channel or next((c for c in member.guild.text_channels if c.permissions_for(member.guild.me).send_messages), None)
    if message and channel:
        await channel.send(message.format(user=member.mention, server=member.guild.name))

@bot.command()
async def prestigeinfo(ctx):
    embed = discord.Embed(
        title="Prestige Information",
        description=(
            "Prestiging allows you to reset your money and roles for a new start, but with new perks.\n\n"
            "You can prestige once you reach a certain amount of money - 50 trillion.\n\n"
            "Each prestige level increases your money multiplier from things like .slots and .gamble, along with letting you hold more money at once.\n\n"
            "Use `.prestige` to start the process. It won't immediately prestige you, but will ask for confirmation to avoid accidents, since everything will wipe.\n\n"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Prestige wisely!")
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1392039603963166731.gif?size=48&animated=true&name=voidcrown")
    await ctx.send(embed=embed)

bot.run(BOT1)
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import random
import aiohttp
import asyncpraw 
from discord.ui import View, Button
from discord import ButtonStyle
from collections import defaultdict
import re
from tinydb import TinyDB, Query
import datetime

# 🔧 Force working directory to script's folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ✅ Use a safe folder name
folder_name = "gambled"

# Prevent file conflict with folder
if os.path.exists(folder_name) and not os.path.isdir(folder_name):
    os.remove(folder_name)

# ✅ Now create folder safely
os.makedirs(folder_name, exist_ok=True)

# ✅ Setup TinyDB
db = TinyDB(f"{folder_name}/balances.json")
User = Query()

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

@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name=".help"),
        status=discord.Status.online
    )
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def invenilink(ctx):
    try:
        await ctx.author.send("[Link here.](https://discord.com/oauth2/authorize?client_id=1380716495767605429&permissions=8&integration_type=0&scope=bot)")
    except discord.Forbidden:
        error = await ctx.send("❌ I couldn't DM you. Please check your privacy settings.")
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
    embed1.add_field(name=".die", value="Roll a 6 sided die.", inline=True)
    embed1.add_field(name=".cf", value="Flip a coin.", inline=True)
    embed1.add_field(name=".eightball", value="Ask the Eightball a question.", inline=True)
    embed1.add_field(name=".sava", value="Grabs the server's icon/avatar.", inline=True)
    embed1.add_field(name=".define", value="Get the definition of a term from Urban Dictionary.", inline=True)
    embed1.add_field(name=".ava", value="Grab the icon/avatar of a user (mention person).", inline=True)

    embed2 = discord.Embed(
        title="Help Page 2",
        description="Fun & Info Commands",
        color=discord.Color.blurple()
    )#Fetches media from a subreddit. Example: .red aww image/gif - .red [nsfw subreddit] image/gif true.
    embed2.add_field(name=".userinfo", value="Get info about a user.", inline=True)
    embed2.add_field(name=".serverinfo", value="Get info about the server.", inline=True)
    embed2.add_field(name=".uinfcmd", value="This will send an embed with what 'userinfo' will return.", inline=True)
    embed2.add_field(name=".dminfo", value="Returns a message with the info of your user, but tweaked to work in DMs.", inline=True)
    embed2.add_field(name=".rps", value="Play rock paper scissors against the bot, also pairs with .rpsstats.", inline=True)
    embed2.add_field(name=".red", value="Fetches media from a subreddit. Example: .red aww image/gif - .red [nsfw subreddit] image/gif true.", inline=True)

    embed3 = discord.Embed(
        title="Help Page 3",
        description="Reply Commands - Replies to 'example' whenever it's messaged.",
        color=discord.Color.blurple()
    )
    embed3.add_field(name=".balance", value="Shows you the current amount of currency you have.", inline=True)
    embed3.add_field(name=".gamble", value="50 percent change of either winning or losing, add the amount you'd like to bet after typing .gamble.", inline=True)
    embed3.add_field(name=".daily", value="Gives a daily bonus of 100.", inline=True)
    embed3.add_field(name=".say", value="Forces the bot to say your message in the same channel, and it deletes your original message.", inline=True)
    embed3.add_field(name=".github", value="Sends a link to the bot's github (all three are in the repo').", inline=True)

    embed4 = discord.Embed(
        title="Help Page 4",
        description="Reply Commands - Replies to 'example' whenever it's messaged.",
        color=discord.Color.blurple()
    )
    embed4.add_field(name="'peak'", value="peak", inline=True)
    embed4.add_field(name="'real'", value="real", inline=True)
    embed4.add_field(name="'kirabiter'", value="Replies with a random greeting to the mention of it's name.", inline=True)
    embed4.add_field(name="'...end it...'", value="Replies with a random sentence encouraging you.", inline=True)
    # Create the view with embeds
    view = HelpView([embed1, embed2, embed3, embed4])
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

# Dictionary to store RPS stats
rps_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0})

@bot.command()
async def rps(ctx):
    class RPSView(View):
        def __init__(self, user):
            super().__init__(timeout=30)
            self.user = user

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            # Only allow the user who started the game to interact
            if interaction.user != self.user:
                await interaction.response.send_message("This is not your game!", ephemeral=True)
                return False
            return True

        @discord.ui.button(label="Rock 🪨", style=ButtonStyle.primary)
        async def rock(self, interaction: discord.Interaction, button: Button):
            await play_game(interaction, "rock", self.user)

        @discord.ui.button(label="Paper 📄", style=ButtonStyle.success)
        async def paper(self, interaction: discord.Interaction, button: Button):
            await play_game(interaction, "paper", self.user)

        @discord.ui.button(label="Scissors ✂️", style=ButtonStyle.danger)
        async def scissors(self, interaction: discord.Interaction, button: Button):
            await play_game(interaction, "scissors", self.user)

    async def play_game(interaction, user_choice, user):
        choices = ["rock", "paper", "scissors"]
        bot_choice = random.choice(choices)

        # Determine outcome
        if user_choice == bot_choice:
            outcome = "It's a tie!"
            rps_stats[user.id]["ties"] += 1
        elif (
            (user_choice == "rock" and bot_choice == "scissors") or
            (user_choice == "paper" and bot_choice == "rock") or
            (user_choice == "scissors" and bot_choice == "paper")
        ):
            outcome = "hacker, ofc you won"
            rps_stats[user.id]["wins"] += 1
        else:
            outcome = "you fucing suck man, I win!"
            rps_stats[user.id]["losses"] += 1

        stats = rps_stats[user.id]
        stats_msg = f"Wins: {stats['wins']}, Losses: {stats['losses']}, Ties: {stats['ties']}"

        await interaction.response.edit_message(
            content=f"You chose **{user_choice}**.\nI chose **{bot_choice}**.\n\n{outcome}\n\n📊 **Your RPS Stats:** {stats_msg}",
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
        await ctx.send(f"👢 {member.display_name} has been kicked. Reason: {reason or 'No reason provided'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to kick {member.display_name}. Error: {e}")

# Ban command
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.display_name} has been banned. Reason: {reason or 'No reason provided'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to ban {member.display_name}. Error: {e}")

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
                await ctx.send(f"✅ Unbanned {user.name}#{user.discriminator}")
                return
            except Exception as e:
                await ctx.send(f"❌ Could not unban {user.name}. Error: {e}")
                return
    await ctx.send(f"❌ User '{member_name}' not found in banned list.")

# Mute command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await ctx.send("⚠️ 'Muted' role not found! Please create one and set its permissions properly.")
        return

    if muted_role in member.roles:
        await ctx.send(f"ℹ️ {member.display_name} is already muted.")
        return

    try:
        await member.add_roles(muted_role, reason=reason)
        await ctx.send(f"🔇 {member.display_name} has been muted. Reason: {reason or 'No reason provided'}")
    except Exception as e:
        await ctx.send(f"❌ Failed to mute {member.display_name}. Error: {e}")

# Unmute command
@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await ctx.send("⚠️ 'Muted' role not found! Please create one and set its permissions properly.")
        return

    if muted_role not in member.roles:
        await ctx.send(f"ℹ️ {member.display_name} is not muted.")
        return

    try:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔊 {member.display_name} has been unmuted.")
    except Exception as e:
        await ctx.send(f"❌ Failed to unmute {member.display_name}. Error: {e}")

# Clear command (bulk delete messages)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if amount <= 0:
        await ctx.send("❌ Please specify a positive number of messages to delete.")
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to delete the command message too
        await ctx.send(f"🧹 Deleted {len(deleted)-1} messages.", delete_after=5)
    except Exception as e:
        await ctx.send(f"❌ Failed to delete messages. Error: {e}")

@bot.command()
async def cleardm(ctx, amount: int = 5):
    if ctx.guild is not None:
        await ctx.send("❌ This command is for DMs only.")
        return

    deleted_count = 0
    async for message in ctx.channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()
            deleted_count += 1
            if deleted_count >= amount:
                break
    await ctx.send(f"🧹 Deleted {deleted_count} messages I sent in this DM.", delete_after=5)


@bot.command(name="adminhelp")
@commands.has_permissions(administrator=True)  # Only admins can run this
async def adminhelp(ctx):
    admin_commands_list = """
    **Admin / Moderation Commands:**

    - `!kick @user [reason]` — Kick a user from the server.
    - `!ban @user [reason]` — Ban a user from the server.
    - `!unban username#1234` — Unban a user by their name and discriminator.
    - `!mute @user [reason]` — Mute a user by adding the Muted role.
    - `!unmute @user` — Remove the Muted role from a user.
    - `!clear <number>` — Bulk delete messages in the current channel.
    """

    try:
        await ctx.author.send(admin_commands_list)
        await ctx.message.delete()  # Optionally delete the command message to keep it secret
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention}, I couldn't send you a DM. Please check your privacy settings.")

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
        await ctx.send(f"✅ {role.name} given to {member.mention}.")
    else:
        await ctx.send(f"❌ Role '{role_name}' not found.")

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
    balance = get_balance(user_id)
    await ctx.send(f"{ctx.author.mention}, your balance is {balance} coins.")

@bot.command()
async def gamble(ctx, amount: int):
    user_id = str(ctx.author.id)
    balance = get_balance(user_id)

    if amount <= 0:
        await ctx.send("Please enter a valid amount to gamble.")
        return
    if amount > balance:
        await ctx.send("You don't have enough coins.")
        return

    if random.random() < 0.5:
        balance -= amount
        result = f"You lost {amount} coins."
    else:
        balance += amount
        result = f"You won {amount} coins!"

    set_balance(user_id, balance)
    await ctx.send(f"{ctx.author.mention}, {result} New balance: {balance} coins.")

@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id)
    now = datetime.datetime.utcnow()

    # Get user record or create default
    user_data = db.get(User.id == user_id)
    if not user_data:
        # Initialize with balance and last_claim time in the past
        db.insert({"id": user_id, "balance": 100, "last_claim": None})
        user_data = db.get(User.id == user_id)

    last_claim = user_data.get("last_claim")
    if last_claim:
        # Parse stored ISO time string to datetime
        last_claim_time = datetime.datetime.fromisoformat(last_claim)
        diff = now - last_claim_time
        if diff < datetime.timedelta(hours=24):
            remaining = datetime.timedelta(hours=24) - diff
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(
                f"You already claimed your daily bonus! "
                f"Come back in {hours}h {minutes}m {seconds}s."
            )
            return

    # Add daily bonus
    bonus_amount = 100
    new_balance = get_balance(user_id) + bonus_amount
    set_balance(user_id, new_balance)

    # Update last_claim to current time (store as ISO string)
    db.update({"last_claim": now.isoformat()}, User.id == user_id)

    await ctx.send(f"{ctx.author.mention}, you received your daily bonus of {bonus_amount} coins. Your new balance is {new_balance}.")

@bot.command()
async def github(ctx):
    """Sends the GitHub repo link for the bot."""
    await ctx.send("Check out the bot's GitHub [here](https://github.com/hexxedspider/kira-and-enigami)")
@bot.command()
async def nsfw(ctx):
    """"Sends a secret message when the user types .nsfw."""
    await ctx.send("youre a fucking loser. you typed .nsfw, you know that right? you did this willingly. you could have just typed .help, but no, you had to type .nsfw. you know what? im not even mad, im just disappointed. you could have been a good person, but instead you chose to be a fucking loser. i hope youre happy with yourself. you know what? im not even going to delete this message, because you deserve to see it. you deserve to see how much of a fucking loser you are. i hope you feel ashamed of yourself. i hope you never type .nsfw again. i hope you never come back to this server. i hope you leave and never come back.")

# runs the bot with the token from the .env file
bot.run(BOT1)

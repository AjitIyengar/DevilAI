import discord
import os
import json
import re
import random
import asyncio
from discord.ext import commands
from flask import Flask
from threading import Thread
from datetime import datetime, UTC

with open("token.txt", "r") as file:
    TOKEN = file.read().strip()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = commands.Bot(command_prefix="$", intents=intents)

app = Flask("")

@app.route("/")
def home():
    return "I'm alive!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

CONFIG_FILE = "config.json"
RESPONSES_FILE = "responses.json"

PRIVATE_CHANNEL_ID = 1484098395055587388
TIMEOUT_SECONDS = 600  
ALLOWED_CHANNEL_ID = 198569039906209793

def load_config():
    if not os.path.exists(CONFIG_FILE):
        data = {
            "token_counter": 0,
            "requests": {}
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return data

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_responses():
    with open(RESPONSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_auto_response(user, text):
    data = load_responses()
    text_lower = text.lower()

    matched_responses = []

    for category in data["categories"].values():
        for keyword in category["keywords"]:
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                matched_responses.extend(category["responses"])
                break

    if not matched_responses:
        matched_responses = data["generic"]

    response = random.choice(matched_responses)
    return response.replace("{user}", user)

async def check_timeouts():
    await client.wait_until_ready()

    while not client.is_closed():
        config = load_config()
        now = datetime.now(UTC)

        updated = False

        for token, data in config["requests"].items():

            if data["status"] != "pending":
                continue

            try:
                timestamp = datetime.fromisoformat(data["timestamp"])

                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=UTC)
            except:
                continue

            elapsed = (now - timestamp).total_seconds()

            if elapsed >= TIMEOUT_SECONDS:
                try:
                    channel = client.get_channel(data["channel_id"])

                    if channel:
                        msg = await channel.fetch_message(data["message_id"])

                        auto_response = get_auto_response(
                            data["username"],
                            data["text"]
                        )

                        await msg.reply(auto_response)

                    data["status"] = "answered"
                    data["response"] = "AUTO"
                    updated = True

                except Exception as e:
                    print(f"Timeout error: {e}")

        if updated:
            save_config(config)

        await asyncio.sleep(30) 

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(check_timeouts()) 

@client.event
async def on_message(message):

    if message.author.bot:
        return

    if client.user in message.mentions:

        config = load_config()

        config["token_counter"] += 1
        token = config["token_counter"]

        cleaned_text = re.sub(
            rf"<@!?{client.user.id}>",
            "",
            message.content
        ).strip()

        config["requests"][str(token)] = {
            "message_id": message.id,
            "channel_id": message.channel.id,
            "user_id": message.author.id,
            "username": str(message.author),
            "text": cleaned_text,
            "status": "pending",
            "timestamp": datetime.now(UTC).isoformat()
        }

        save_config(config)

        await message.reply("Devil.AI is thinking... please wait a moment.")

        channel = client.get_channel(PRIVATE_CHANNEL_ID)

        if channel:
            embed = discord.Embed(
                title=f"New Request #{token}",
                color=discord.Color.pink()
            )

            embed.add_field(
                name="User",
                value=str(message.author),
                inline=False
            )

            embed.add_field(
                name="Channel",
                value=f"<#{message.channel.id}>",
                inline=False
            )

            embed.add_field(
                name="Message",
                value=cleaned_text if cleaned_text else "(empty)",
                inline=False
            )

            embed.add_field(
                name="Jump to Message",
                value=f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}",
                inline=False
            )

            embed.set_footer(text=f"Token: {token}")

            await channel.send(embed=embed)

    await client.process_commands(message)

@client.command()
async def respond(ctx, token: int, *, response: str):

    if ctx.channel.id != PRIVATE_CHANNEL_ID:
        return

    config = load_config()
    token = str(token)

    if token not in config["requests"]:
        return

    data = config["requests"][token]

    if data["status"] == "answered":
        return

    try:
        channel = client.get_channel(data["channel_id"])

        if channel:
            original_message = await channel.fetch_message(data["message_id"])
            await original_message.reply(response)

        config["requests"][token]["status"] = "answered"
        config["requests"][token]["response"] = response

        save_config(config)

    except Exception as e:
        print(e)

@client.command()
async def voltorbflip(ctx):

    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        return await ctx.send(f"❌ You can only use this command in <#{ALLOWED_CHANNEL_ID}>.")
    
    try:
        with open("gamecorner.json", "r") as file:
            players = json.load(file)
    except FileNotFoundError:
        players = []

    player = next((p for p in players if p["user_id"] == str(ctx.author.id)), None)
    if player is None:
        player = {"user_id": str(ctx.author.id), "username": ctx.author.name, "coins": 0, "level": 1}
        players.append(player)

    level_data = {
        1: [(3, 1, 6), (0, 3, 6), (5, 0, 6), (2, 2, 6), (4, 1, 6)],
        2: [(1, 3, 7), (6, 0, 7), (3, 2, 7), (0, 4, 7), (5, 1, 7)],
        3: [(2, 3, 8), (7, 0, 8), (4, 2, 8), (1, 4, 8), (6, 1, 8)],
        4: [(3, 3, 8), (0, 5, 8), (8, 0, 10), (5, 2, 10), (2, 4, 10)],
        5: [(7, 1, 10), (4, 3, 10), (1, 5, 10), (9, 0, 10), (6, 2, 10)],
        6: [(3, 4, 10), (0, 6, 10), (8, 1, 10), (5, 3, 10), (2, 5, 10)],
        7: [(7, 2, 10), (4, 4, 10), (1, 6, 13), (9, 1, 13), (6, 3, 10)],
        8: [(0, 7, 10), (8, 2, 10), (5, 4, 10), (2, 6, 10), (7, 3, 10)]
    }

    board_size = 5
    choice = random.choice(level_data[player["level"]])
    twos, threes, voltorbs = choice

    hidden_board = [[1 for _ in range(board_size)] for _ in range(board_size)]
    positions = [(r, c) for r in range(board_size) for c in range(board_size)]
    random.shuffle(positions)

    for _ in range(voltorbs):
        r, c = positions.pop()
        hidden_board[r][c] = 'V'
    for _ in range(threes):
        r, c = positions.pop()
        hidden_board[r][c] = 3
    for _ in range(twos):
        r, c = positions.pop()
        hidden_board[r][c] = 2

    revealed = [[False]*board_size for _ in range(board_size)]
    coins = 0
    first_guess = True

    def format_board():
        rows = []
        header = "    1  2  3  4  5"

        for r in range(board_size):
            row_str = chr(65 + r) + "  "
            for c in range(board_size):
                if revealed[r][c]:
                    val = hidden_board[r][c]
                    row_str += {
                        1: "1️⃣ ",
                        2: "2️⃣ ",
                        3: "3️⃣ ",
                        'V': "💣 "
                    }[val]
                else:
                    row_str += "⬛ "

            row_sum = sum(val if isinstance(val, int) else 0 for val in hidden_board[r])
            vol_count = sum(1 for val in hidden_board[r] if val == 'V')

            row_str += f"| {row_sum}  {'💣'*vol_count}"
            rows.append(row_str)

        col_sums = []
        col_vols = []

        for c in range(board_size):
            total = 0
            bombs = 0
            for r in range(board_size):
                val = hidden_board[r][c]
                if isinstance(val, int):
                    total += val
                elif val == 'V':
                    bombs += 1

            col_sums.append(f"{total:2}")
            col_vols.append(f"{bombs:2}")

        footer1 = "⬇  " + " ".join(col_sums)
        footer2 = "💣 " + " ".join(col_vols)

        return (
            "```\n"
            + header + "\n"
            + "\n".join(rows)
            + f"\n{footer1}\n{footer2}\nTotal coins: {coins}```"
        )

    embed = discord.Embed(
        title=f"Voltorb Flip – Level {player['level']}",
        description=format_board(),
        color=0xf5a9b8
    )

    msg = await ctx.send(embed=embed)

    total_specials = twos + threes
    revealed_specials = 0

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    while True:
        try:
            guess_msg = await client.wait_for('message', check=check, timeout=300)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Game timed out.")
            return

        guess = guess_msg.content.upper()

        if guess == "QUIT":
            player["coins"] += coins
            player["level"] = 1
            break

        if len(guess)!=2 or guess[0] not in "ABCDE" or guess[1] not in "12345":
            await ctx.send("Use A1 format")
            continue

        r = ord(guess[0])-65
        c = int(guess[1])-1

        if revealed[r][c]:
            continue

        revealed[r][c]=True
        val = hidden_board[r][c]

        if val=='V':
            coins=0
            player["level"]=1
            break

        if first_guess:
            coins=val
            first_guess=False
        else:
            coins*=val

        if val in [2,3]:
            revealed_specials+=1

        if revealed_specials==total_specials:
            player["coins"]+=coins
            if player["level"]<8:
                player["level"]+=1
            break

        embed.description = format_board()
        await msg.edit(embed=embed)

    with open("gamecorner.json","w") as f:
        json.dump(players,f,indent=4)

    embed.description = format_board() + f"\nGame Over! Coins: {coins}"
    await msg.edit(embed=embed)

@client.command()
async def vflipleaderboard(ctx):
    try:
        with open("gamecorner.json", "r") as file:
            players = json.load(file)
    except FileNotFoundError:
        return await ctx.send("No data.")

    players.sort(key=lambda x: x["coins"], reverse=True)

    text = "\n".join(
        f"{i+1}. {p['username']} - {p['coins']}"
        for i,p in enumerate(players[:10])
    )

    embed = discord.Embed(title="Voltorb Flip Leaderboard", description=text, color=0xf5a9b8)
    await ctx.send(embed=embed)

ROLE_MAP = {
    "intern": 1488357130921705765,
    "janitor": 1488357354780229692,
    "entry level": 1488357581494947961,
    "ritual consultant": 1488357853923119244,
    "devil-it support tier 1": 1488358067656720485,
    "under operations 2": 1488358257675206716,
    "senior pit boss management 3": 1488358419986513981,
    "devil resources communications": 1488358574726844497,
    "assistant vp business outreach division": 1488358846194782369,
    "chief fiendish officer": 1488359036138291472,
    "soup": 1047522525472637008
}

@client.command()
async def promote(ctx, role_name: str, member: discord.Member = None):
    role_name = role_name.lower()

    if role_name not in ROLE_MAP:
        return await ctx.send("❌ Role not found.")

    role = ctx.guild.get_role(ROLE_MAP[role_name])

    if role is None:
        return await ctx.send("❌ Role ID is invalid.")

    if ctx.author.guild_permissions.manage_roles:
        target = member if member else ctx.author
    else:
        target = ctx.author
        if member:
            return await ctx.send("❌ You can't assign roles to others.")

    try:
        await target.add_roles(role)
        await ctx.send(f"✅ Added **{role.name}** to {target.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to add that role.")

@client.command()
async def demote(ctx, role_name: str, member: discord.Member = None):
    role_name = role_name.lower()

    if role_name not in ROLE_MAP:
        return await ctx.send("❌ Role not found.")

    role = ctx.guild.get_role(ROLE_MAP[role_name])

    if role is None:
        return await ctx.send("❌ Role ID is invalid.")

    if ctx.author.guild_permissions.manage_roles:
        target = member if member else ctx.author
    else:
        target = ctx.author
        if member:
            return await ctx.send("❌ You can't remove roles from others.")

    try:
        await target.remove_roles(role)
        await ctx.send(f"✅ Removed **{role.name}** from {target.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to remove that role.")

load_config()
keep_alive()
client.run(TOKEN)

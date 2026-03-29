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

PRIVATE_CHANNEL_ID = 1320402706833084448
TIMEOUT_SECONDS = 60  

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

load_config()
keep_alive()
client.run(TOKEN)
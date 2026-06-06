import os
import sys
import threading
import asyncio
import discord
import requests
from flask import Flask

# ====================== FLASK KEEP-ALIVE ======================
app = Flask('')

@app.route('/')
def home():
    return "HookupDCtoTG Bridge is running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ====================== CONFIG ======================
DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
DISCORD_CHANNEL_ID = int(os.environ.get('DISCORD_CHANNEL_ID', 0))
TARGET_SERVER_ID = int(os.environ.get('TARGET_SERVER_ID', 0))
HIGH_ROLE_ID = int(os.environ.get('HIGH_ROLE_ID', 0))

if not all([DISCORD_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ Missing required environment variables!")
    sys.exit(1)

# ====================== DISCORD ======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Discord Bot online as {client.user}")

# Forwarding + Discord Commands
@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Forwarding
    if message.channel.id == DISCORD_CHANNEL_ID:
        text = f"**{message.author}**:\n{message.content or ''}"
        if message.embeds:
            for embed in message.embeds:
                if embed.title: text += f"\n**{embed.title}**"
                if embed.description: text += f"\n{embed.description}"
        if message.attachments:
            for att in message.attachments:
                text += f"\n📎 {att.url}"
        
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text[:4000], "parse_mode": "Markdown"}
            )
        except:
            pass

    # Discord Invite Command
    if message.content.lower() in ["!invite", "!join", "/invite"]:
        await send_invite(message.author, message.channel)

async def send_invite(user, channel=None):
    if not TARGET_SERVER_ID:
        if channel: await channel.send("❌ Server not configured.")
        return
    try:
        guild = client.get_guild(TARGET_SERVER_ID)
        invite = await guild.text_channels[0].create_invite(
            max_age=0, max_uses=1, unique=True
        )
        msg = f"✅ **Your Invite**\n{invite.url}\n\n→ Auto high role on join!"
        await user.send(msg)
        if channel:
            await channel.send("✅ Invite sent to DMs!")
    except Exception as e:
        print(f"Invite error: {e}")
        if channel:
            await channel.send("❌ Failed to create invite.")

# Auto Role
@client.event
async def on_member_join(member: discord.Member):
    if member.guild.id == TARGET_SERVER_ID and HIGH_ROLE_ID:
        try:
            role = member.guild.get_role(HIGH_ROLE_ID)
            if role:
                await member.add_roles(role)
                print(f"✅ High role given to {member}")
        except Exception as e:
            print(f"Role error: {e}")

# ====================== TELEGRAM ======================
async def telegram_polling():
    offset = 0
    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30}
            )
            data = resp.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if msg and msg.get("text"):
                        text = msg["text"].lower().strip()
                        chat_id = msg["chat"]["id"]
                        if text in ["/invite", "!invite", "!join"]:
                            try:
                                guild = client.get_guild(TARGET_SERVER_ID)
                                invite = await guild.text_channels[0].create_invite(
                                    max_age=0, max_uses=1, unique=True
                                )
                                response = f"✅ **Discord Invite**\n{invite.url}\n\n→ Auto high role!"
                                requests.post(
                                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                                    json={"chat_id": chat_id, "text": response}
                                )
                            except:
                                requests.post(
                                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                                    json={"chat_id": chat_id, "text": "❌ Failed to create invite."}
                                )
        except Exception as e:
            print(f"Telegram error: {e}")
        await asyncio.sleep(1)

# ====================== START ======================
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    loop = asyncio.get_event_loop()
    loop.create_task(telegram_polling())
    client.run(DISCORD_TOKEN)

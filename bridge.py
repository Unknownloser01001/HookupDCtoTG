import os
import sys
import threading
import discord
import requests
from flask import Flask

# --- 1. TINY WEB SERVER FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    # Render automatically gives us a PORT variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --------------------------------------

DISCORD_TOKEN = os.environ.get('DISCORD_TOKEN')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
DISCORD_CHANNEL_ID = 112233445566778899  # <-- Keep your actual ID here

if not all([DISCORD_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
    print("Missing environment variables!")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Bot successfully launched on Render!")

@client.event
async def on_message(message):
    if message.author.bot: return
    if message.channel.id == DISCORD_CHANNEL_ID:
        telegram_text = f"**{message.author.name}**:\n{message.content}"
        if message.attachments:
            for file in message.attachments:
                telegram_text += f"\n📎 Attachment: {file.url}"

        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(telegram_url, json={"chat_id": TELEGRAM_CHAT_ID, "text": telegram_text, "parse_mode": "Markdown"})

# Run the web server in the background, then start the Discord Bot
if __name__ == "__main__":
    t = threading.Thread(target=run_web_server)
    t.start()
    client.run(DISCORD_TOKEN)


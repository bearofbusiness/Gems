import os
import sqlite3

from dotenv import load_dotenv
import discord
from discord.ext import commands
#from discord import app_commands
#from discord.ui import Button, View


load_dotenv(".env/.env")
key = os.environ.get('token')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.reactions = True

# SQLite database setup
db_connection = sqlite3.connect("reactions.db")
cursor = db_connection.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS gem_reacted_messages (message_id TEXT PRIMARY KEY)""")
db_connection.commit()

# Check if a message ID exists in the database
def is_message_reacted(message_id):
    cursor.execute("SELECT 1 FROM gem_reacted_messages WHERE message_id = ?", (str(message_id),))
    return cursor.fetchone() is not None

# Add a message ID to the database
def add_message_to_db(message_id):
    cursor.execute("INSERT INTO gem_reacted_messages (message_id) VALUES (?)", (str(message_id),))
    db_connection.commit()

bot = commands.Bot(command_prefix="!", intents=intents)

# Global storage for tracking reactions
#reaction_tracker = {}

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

# Reaction-based Image Download
@bot.event
async def on_raw_reaction_add(event: discord.RawReactionActionEvent):
    user = await bot.fetch_user(event.user_id)

    if user.bot:
        return


    channel = await bot.fetch_channel(event.channel_id)
    message = await channel.fetch_message(event.message_id)


    emoji = event.emoji

    print(str(emoji))

    if is_message_reacted(message.id):
        print(f"Message {message.id} has already been processed.")
        return

    if str(emoji) != "💎":
        return

    reaction_count = 0
    for reaction in message.reactions:
        if reaction.emoji == "💎":
            reaction_count = reaction.count
            break

    if reaction_count < 2:
        return

    if message.author.id == bot.user.id:
        return

    # Ensure the message has an image attachment
    if message.attachments:
        attachment = message.attachments[0]
        file = await attachment.to_file()
        await message.reply(
            "💎", file=file
        )
    elif message.embeds:
        embed = message.embeds[0]
        #if embed and embed.image.url:  # Check if the embed has an image
        #print(str(embed))
        await message.reply(
            message.content
        )

    add_message_to_db(message.id)
    print(f"Stored message ID {message.id} in the database.")


# Sync application commands with Discord
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Graceful shutdown to close the database connection
@bot.event
async def on_close():
    db_connection.close()
# Run the bot
bot.run(key)

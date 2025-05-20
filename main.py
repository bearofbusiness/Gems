import os
import sqlite3
import hashlib
import json
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

load_dotenv(".env/.env")
key = os.environ.get('token')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = {
        "gem_reacted_messages": [],
        "coal_banned_hashes": {},
        "banned_phrases": {}
    }
DATA_FILE = "data.json"
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        db = json.load(f)


def save_db():
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=4)

def hash_attachment(attachment: discord.Attachment, data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

# Reaction-based Image Download
@bot.event
async def on_raw_reaction_add(event: discord.RawReactionActionEvent):
    user = await bot.fetch_user(event.user_id)

    if user.bot:
        return

    channel = await bot.fetch_channel(event.channel_id)
    message = await channel.fetch_message(event.message_id)

    emoji = event.emoji

    if str(emoji) == "💎":

        gem_count = 0
        for reaction in message.reactions:
            if reaction.emoji == "💎":
                gem_count = reaction.count
                break

        if gem_count < 2 or message.author.id == bot.user.id:
            return

        if gem_count >= 5:
            try:
                await message.pin()
                await message.reply("HWABAG!! 💎💎💎", delete_after=5)
            except discord.Forbidden:
                pass

        if str(message.id) in db["gem_reacted_messages"]:
            return

        if message.attachments:
            attachment = message.attachments[0]
            file = await attachment.to_file()
            file.spoiler = attachment.is_spoiler()
            await message.reply("💎", file=file)
        elif message.embeds:
            await message.reply("💎\n" + message.content)

        db["gem_reacted_messages"].append(str(message.id))
        save_db()

    elif "coal" in emoji.name:
        coal_count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == str(emoji):
                coal_count = reaction.count
                break

        if coal_count >= 5:
            if message.attachments:
                attachment = message.attachments[0]
                data = await attachment.read()
                file_hash = hash_attachment(attachment, data)

                if file_hash not in db["coal_banned_hashes"]:
                    db["coal_banned_hashes"].append(file_hash)
                    save_db()

                await message.reply("HWNBAG!!!", delete_after=5)
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
            elif message.content:
                phrase = message.content.strip().lower()
                guild_id = str(message.guild.id)
                if not (guild_id in db["banned_phrases"]):
                    db["banned_phrases"][guild_id] = []
                if phrase not in db["banned_phrases"][guild_id]:
                    db["banned_phrases"][guild_id].append(phrase)
                    await message.reply("HWNBAG!!!", delete_after=5)
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        print(f"Failed to delete message: {message.id} content: {message.content} guild: {message.guild.name}")
                    save_db()


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    content_lower = message.content.lower()

    # Image hash check
    for attachment in message.attachments:
        data = await attachment.read()
        file_hash = hash_attachment(attachment, data)
        if file_hash in db["coal_banned_hashes"]:
            await message.reply("HWNBAG!!!", delete_after=5)
            try:
                await message.delete()
                print("Deleted banned image upload.")
            except Exception as e:
                print(f"Failed to delete image: {e}")
            return

    # Phrase block check
    banned_list = db["banned_phrases"].get(str(message.guild.id), [])
    for phrase in banned_list:
        if phrase in content_lower:
            try:
                await message.delete()
                print(f"Deleted message for banned phrase: '{phrase}' in {message.guild.name}")
            except discord.Forbidden:
                pass
            return

    await bot.process_commands(message)



@bot.tree.command(name="listbans", description="List banned phrases in this server")
@app_commands.checks.has_permissions(manage_messages=True)
async def listbans(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    phrases = db["banned_phrases"].get(guild_id, [])
    if not phrases:
        await interaction.response.send_message("No banned phrases in this server.", ephemeral=True)
        return

    msg = "**Banned Phrases:**\n" + "\n".join(f"- {p}" for p in phrases)
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="clearbans", description="Clear all banned phrases in this server")
@app_commands.checks.has_permissions(administrator=True)
async def clearbans(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    if guild_id in db["banned_phrases"]:
        db["banned_phrases"].pop(guild_id)
        save_db()
        await interaction.response.send_message("Banned phrases cleared.", ephemeral=True)
    else:
        await interaction.response.send_message("No banned phrases to clear.", ephemeral=True)


# Sync application commands with Discord
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    print(f"Bot logged in as {bot.user}")

# Run the bot
bot.run(key)

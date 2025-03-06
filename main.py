import nextcord
from nextcord.ext import commands
import os
import json
import logging
import datetime
import sqlite3
import asyncio
import colorama
from colorama import Fore, Style
from typing import Optional, List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AltGenBot")

colorama.init(autoreset=True)

# Load configuration
try:
    with open("config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    logger.error("Config file not found. Please create a config.json file.")
    exit(1)

# Initialize bot with intents
intents = nextcord.Intents.all()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=config.get("prefix", "!"),
    intents=intents,
    help_command=None
)

def setup_database():
    conn = sqlite3.connect('altgen.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        is_vip INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        gen_count INTEGER DEFAULT 0,
        last_gen TIMESTAMP,
        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        display_name TEXT,
        vip_only INTEGER DEFAULT 0,
        icon TEXT DEFAULT '🔑'
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        command TEXT,
        service TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database setup complete")

if not os.path.exists("data"):
    os.makedirs("data")
    logger.info("Created data directory")

@bot.event
async def on_ready():
    setup_database()
    
    await bot.change_presence(
        activity=nextcord.Activity(
            type=nextcord.ActivityType.watching,
            name="/help | GhostGen v1.0"
        )
    )
    
    print(f"{Fore.CYAN}╔{'═' * 50}╗")
    print(f"{Fore.CYAN}║ {Fore.YELLOW}GhostGen v1.0  {Fore.GREEN}is now online!{' ' * 24}║")
    print(f"{Fore.CYAN}║ {Fore.WHITE}Logged in as: {Fore.MAGENTA}{bot.user}{' ' * (33 - len(str(bot.user)))}║")
    print(f"{Fore.CYAN}║ {Fore.WHITE}Bot ID: {Fore.MAGENTA}{bot.user.id}{' ' * (39 - len(str(bot.user.id)))}║")
    print(f"{Fore.CYAN}║ {Fore.WHITE}Servers: {Fore.MAGENTA}{len(bot.guilds)}{' ' * (40 - len(str(len(bot.guilds))))}║")
    print(f"{Fore.CYAN}╚{'═' * 50}╝")
    
    # Load all command modules
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            try:
                bot.load_extension(f"commands.{filename[:-3]}")
                logger.info(f"Loaded extension: {filename[:-3]}")
            except Exception as e:
                logger.error(f"Failed to load extension {filename}: {e}")
    
    # Sync commands with Discord
    try:
        synced_commands = await bot.sync_application_commands()
        logger.info(f"Synced {len(synced_commands)} application commands globally")
        print(f"{Fore.GREEN}Synced {len(synced_commands)} application commands globally")
    except Exception as e:
        logger.error(f"Error syncing application commands: {e}")
        print(f"{Fore.RED}Failed to sync commands: {e}")

@bot.event
async def on_application_command_error(interaction: nextcord.Interaction, error):
    if isinstance(error, commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏰ This command is on cooldown. Try again in {error.retry_after:.2f} seconds.",
            ephemeral=True
        )
    elif isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You don't have the required permissions to use this command.",
            ephemeral=True
        )
    else:
        logger.error(f"Error in command {interaction.application_command.name}: {error}")
        await interaction.response.send_message(
            "❌ An error occurred while executing this command.",
            ephemeral=True
        )

@bot.event
async def on_member_join(member: nextcord.Member):
    conn = sqlite3.connect('altgen.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (member.id, str(member))
    )
    
    conn.commit()
    conn.close()
    
    print(f"{Fore.GREEN}[JOIN] {member} joined the server")

# Helper functions
def log_command(user_id: int, username: str, command: str, service: str = None):
    conn = sqlite3.connect('altgen.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO logs (user_id, username, command, service) VALUES (?, ?, ?, ?)",
        (user_id, username, command, service)
    )
    
    conn.commit()
    conn.close()
    
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    service_str = f" | Service: {service}" if service else ""
    print(f"{Fore.BLUE}[{timestamp}] {Fore.GREEN}[COMMAND] {Fore.YELLOW}{username} {Fore.WHITE}used {Fore.MAGENTA}{command}{service_str}")

def is_vip(user_id: int) -> bool:
    conn = sqlite3.connect('altgen.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    return bool(result[0]) if result else False

def is_admin(user_id: int) -> bool:
    conn = sqlite3.connect('altgen.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    return bool(result[0]) if result else False

def get_services() -> List[Dict[str, Any]]:
    conn = sqlite3.connect('altgen.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, display_name, vip_only, icon FROM services")
    services = [
        {
            "name": row[0],
            "display_name": row[1],
            "vip_only": bool(row[2]),
            "icon": row[3]
        }
        for row in cursor.fetchall()
    ]
    
    conn.close()
    return services

# Test slash command to verify slash commands are working
@bot.slash_command(name="test", description="Test if slash commands are working")
async def test(interaction: nextcord.Interaction):
    await interaction.response.send_message("Slash commands are working!", ephemeral=True)

if __name__ == "__main__":
    bot.run(config["token"])

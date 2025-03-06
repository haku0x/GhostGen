import nextcord
from nextcord.ext import commands
import os
import json
import datetime
import platform
import psutil
import time
import sqlite3

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("config.json", "r") as f:
            self.config = json.load(f)
        self.start_time = time.time()
    
    @nextcord.slash_command(
        name="list",
        description="List all available services"
    )
    async def list_services(self, interaction: nextcord.Interaction):
        from main import log_command, is_vip
        log_command(interaction.user.id, str(interaction.user), "/list")
        
        user_is_vip = is_vip(interaction.user.id) or interaction.user.get_role(self.config["vip_role_id"]) is not None
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        if user_is_vip:
            cursor.execute(
                "SELECT name, display_name, icon, vip_only FROM services ORDER BY vip_only DESC, display_name ASC"
            )
        else:
            cursor.execute(
                "SELECT name, display_name, icon, vip_only FROM services WHERE vip_only = 0 ORDER BY display_name ASC"
            )
        
        services = cursor.fetchall()
        conn.close()
        
        if not services:
            await interaction.response.send_message(
                "❌ No services available.",
                ephemeral=True
            )
            return
        
        embed = nextcord.Embed(
            title="🔑 Available Services",
            description="Use `/gen service:name` to generate an account",
            color=int(self.config["embed_color_info"], 16),
            timestamp=datetime.datetime.now()
        )
        
        vip_services = []
        normal_services = []
        
        for name, display_name, icon, vip_only in services:
            stock = self._get_stock(name)
            status = "✅ Available" if stock > 0 else "❌ Out of stock"
            
            service_entry = {
                "name": name,
                "display": display_name,
                "icon": icon,
                "status": status,
                "stock": stock
            }
            
            if vip_only:
                vip_services.append(service_entry)
            else:
                normal_services.append(service_entry)
        
        if user_is_vip and vip_services:
            embed.add_field(
                name="⭐ VIP SERVICES",
                value="\u200b",
                inline=False
            )
            
            for service in vip_services:
                embed.add_field(
                    name=f"{service['icon']} {service['display']}",
                    value=f"{service['status']} | Stock: {service['stock']}",
                    inline=True
                )
        
        if normal_services:
            embed.add_field(
                name="🔹 STANDARD SERVICES",
                value="\u200b",
                inline=False
            )
            
            for service in normal_services:
                embed.add_field(
                    name=f"{service['icon']} {service['display']}",
                    value=f"{service['status']} | Stock: {service['stock']}",
                    inline=True
                )
        
        if not user_is_vip:
            embed.add_field(
                name="⭐ UPGRADE TO VIP",
                value="Get access to exclusive services and reduced cooldowns!\nUse `/upgrade` to see available VIP plans.",
                inline=False
            )
        
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    def _get_stock(self, service: str) -> int:
        try:
            with open(f"data/{service}.txt", "r") as f:
                return len(f.read().splitlines())
        except FileNotFoundError:
            return 0
    
    @nextcord.slash_command(
        name="help",
        description="Show help information"
    )
    async def help(self, interaction: nextcord.Interaction):
        from main import log_command, is_admin, is_vip
        log_command(interaction.user.id, str(interaction.user), "/help")
        
        user_is_admin = is_admin(interaction.user.id) or interaction.user.get_role(self.config["admin_role_id"]) is not None
        user_is_vip = is_vip(interaction.user.id) or interaction.user.get_role(self.config["vip_role_id"]) is not None
        
        embed = nextcord.Embed(
            title="🤖 HakuGen v1.0 Help",
            description="Premium Account Generator",
            color=int(self.config["embed_color"], 16),
            timestamp=datetime.datetime.now()
        )
        
        user_commands = [
            ("/gen service:name", "Generate an account for the specified service"),
            ("/list", "List all available services"),
            ("/help", "Show this help message"),
            ("/ping", "Check if the bot is online")
        ]
        
        embed.add_field(
            name="📋 User Commands",
            value="\n".join([f"**{cmd}** - {desc}" for cmd, desc in user_commands]),
            inline=False
        )
        
        if user_is_vip:
            vip_commands = [
                ("/vipstatus", "Check your VIP status and benefits")
            ]
            
            embed.add_field(
                name="⭐ VIP Commands",
                value="\n".join([f"**{cmd}** - {desc}" for cmd, desc in vip_commands]),
                inline=False
            )
        else:
            embed.add_field(
                name="⭐ VIP Benefits",
                value="• Access to exclusive VIP-only services\n• Reduced cooldown (10 minutes vs 1 hour)\n• Priority support\n\nUse `/upgrade` to see available VIP plans.",
                inline=False
            )
        
        if user_is_admin:
            admin_commands = [
                ("/add service:name", "Add accounts to a service"),
                ("/stock [service:name]", "Check the stock of accounts"),
                ("/adduser user:@user role:role", "Add or modify a user's permissions"),
                ("/logs [limit:10] [user:@user]", "View recent command logs"),
                ("/purge service:name confirm:confirm", "Delete a service and all its accounts"),
                ("/stats", "Show bot statistics")
            ]
            
            embed.add_field(
                name="🔧 Admin Commands",
                value="\n".join([f"**{cmd}** - {desc}" for cmd, desc in admin_commands]),
                inline=False
            )
        
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.slash_command(
        name="ping",
        description="Check if the bot is online"
    )
    async def ping(self, interaction: nextcord.Interaction):
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/ping")
        
        latency = round(self.bot.latency * 1000)
        embed = nextcord.Embed(
            title="🏓 Pong!",
            description=f"Bot latency: **{latency}ms**",
            color=int(self.config["embed_color_info"], 16),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.slash_command(
        name="stats",
        description="Show bot statistics"
    )
    async def stats(self, interaction: nextcord.Interaction):
        from main import is_admin
        if not (is_admin(interaction.user.id) or interaction.user.get_role(self.config["admin_role_id"]) is not None):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/stats")
        
        uptime = time.time() - self.start_time
        days, remainder = divmod(int(uptime), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        memory_usage = f"{memory.percent}% ({memory.used / 1024**2:.1f}MB / {memory.total / 1024**2:.1f}MB)"
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM services")
        service_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM services WHERE vip_only = 1")
        vip_service_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
        vip_user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(gen_count) FROM users")
        total_gens = cursor.fetchone()[0] or 0
        
        account_count = 0
        for filename in os.listdir("data"):
            if filename.endswith(".txt"):
                with open(f"data/{filename}", "r") as f:
                    account_count += len(f.read().splitlines())
        
        conn.close()
        
        embed = nextcord.Embed(
            title="📊 Bot Statistics",
            color=int(self.config["embed_color_info"], 16),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="Bot Version", value="1.0", inline=True)
        embed.add_field(name="Nextcord Version", value=nextcord.__version__, inline=True)
        embed.add_field(name="Python Version", value=platform.python_version(), inline=True)
        
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="CPU Usage", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="Memory Usage", value=memory_usage, inline=True)
        
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Users", value=str(user_count), inline=True)
        embed.add_field(name="VIP Users", value=str(vip_user_count), inline=True)
        
        embed.add_field(name="Services", value=str(service_count), inline=True)
        embed.add_field(name="VIP Services", value=str(vip_service_count), inline=True)
        embed.add_field(name="Total Accounts", value=str(account_count), inline=True)
        
        embed.add_field(name="Total Generations", value=str(total_gens), inline=True)
        
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.slash_command(
        name="upgrade",
        description="View VIP upgrade options"
    )
    async def upgrade(self, interaction: nextcord.Interaction):
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/upgrade")
        
        embed = nextcord.Embed(
            title="⭐ Upgrade to VIP",
            description="Unlock premium features and exclusive services!",
            color=int(self.config["embed_color"], 16),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(
            name="🔹 VIP Benefits",
            value="• Access to exclusive VIP-only services\n• Reduced cooldown (10 minutes vs 1 hour)\n• Priority support\n• Early access to new services",
            inline=False
        )
        
        embed.add_field(
            name="💎 VIP Plans",
            value="• **Monthly**: $5.99/month\n• **Quarterly**: $14.99 ($5.00/month)\n• **Yearly**: $49.99 ($4.17/month)",
            inline=False
        )
        
        embed.add_field(
            name="💳 How to Purchase",
            value="Contact an administrator to purchase VIP access.",
            inline=False
        )
        
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.slash_command(
        name="vipstatus",
        description="Check your VIP status and benefits"
    )
    async def vipstatus(self, interaction: nextcord.Interaction):
        from main import is_vip
        if not (is_vip(interaction.user.id) or interaction.user.get_role(self.config["vip_role_id"]) is not None):
            await interaction.response.send_message(
                "❌ You are not a VIP user. Use `/upgrade` to see available VIP plans.",
                ephemeral=True
            )
            return
        
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/vipstatus")
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT gen_count, join_date FROM users WHERE user_id = ?",
            (interaction.user.id,)
        )
        result = cursor.fetchone()
        
        if result is None:
            gen_count = 0
            join_date = datetime.datetime.now().isoformat()
        else:
            gen_count, join_date = result
        
        cursor.execute("SELECT COUNT(*) FROM services WHERE vip_only = 1")
        vip_service_count = cursor.fetchone()[0]
        
        conn.close()
        
        join_datetime = datetime.datetime.fromisoformat(join_date)
        join_str = join_datetime.strftime("%Y-%m-%d")
        
        embed = nextcord.Embed(
            title="⭐ VIP Status",
            description=f"You are a VIP user, {interaction.user.mention}!",
            color=int(self.config["embed_color"], 16),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(
            name="🔹 Your Benefits",
            value="• Access to exclusive VIP-only services\n• Reduced cooldown (10 minutes vs 1 hour)\n• Priority support\n• Early access to new services",
            inline=False
        )
        
        embed.add_field(
            name="📊 Your Stats",
            value=f"• Member since: {join_str}\n• Accounts generated: {gen_count}\n• VIP services available: {vip_service_count}",
            inline=False
        )
        
        embed.add_field(
            name="🔑 Next Generation",
            value="You can generate your next account immediately with the `/gen` command!",
            inline=False
        )
        
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(UtilityCog(bot))


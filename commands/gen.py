import nextcord
from nextcord import SlashOption
from nextcord.ext import commands
import os
import json
import random
import datetime
import sqlite3
import asyncio
from typing import List, Dict, Optional
import colorama
from colorama import Fore, Style

class GeneratorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("config.json", "r") as f:
            self.config = json.load(f)
    
    def _get_account(self, service: str) -> Optional[str]:
        """Get a random account from the service file"""
        try:
            with open(f"data/{service}.txt", "r") as f:
                accounts = f.read().splitlines()
                
            if not accounts:
                return None
                
            account = random.choice(accounts)
            
            accounts.remove(account)
            with open(f"data/{service}.txt", "w") as f:
                f.write("\n".join(accounts))
                
            return account
        except FileNotFoundError:
            return None
    
    def _get_stock(self, service: str) -> int:
        """Get the number of accounts available for a service"""
        try:
            with open(f"data/{service}.txt", "r") as f:
                return len(f.read().splitlines())
        except FileNotFoundError:
            return 0
    
    def _can_generate(self, user_id: int, is_vip: bool) -> tuple[bool, int]:
        """Check if user can generate an account and return cooldown time left"""
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT last_gen FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result is None:
            # Add user to database
            cursor.execute(
                "INSERT INTO users (user_id, username, is_vip) VALUES (?, ?, ?)",
                (user_id, f"User_{user_id}", int(is_vip))
            )
            conn.commit()
            conn.close()
            return True, 0
        
        last_gen = result[0]
        if last_gen is None:
            conn.close()
            return True, 0
        
        # Convert string timestamp to datetime
        last_gen_time = datetime.datetime.fromisoformat(last_gen)
        current_time = datetime.datetime.now()
        
        # Calculate time difference
        time_diff = (current_time - last_gen_time).total_seconds()
        
        # Get cooldown based on VIP status
        cooldown = self.config["vip_cooldown"] if is_vip else self.config["normal_cooldown"]
        
        if time_diff < cooldown:
            conn.close()
            return False, int(cooldown - time_diff)
        
        conn.close()
        return True, 0
    
    def _update_last_gen(self, user_id: int):
        """Update last generation time for user"""
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET last_gen = ?, gen_count = gen_count + 1 WHERE user_id = ?",
            (datetime.datetime.now().isoformat(), user_id)
        )
        
        conn.commit()
        conn.close()
    
    def _get_service_info(self, service_name: str) -> Optional[Dict]:
        """Get service info from database"""
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name, display_name, vip_only, icon FROM services WHERE name = ?",
            (service_name,)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if result is None:
            return None
        
        return {
            "name": result[0],
            "display_name": result[1],
            "vip_only": bool(result[2]),
            "icon": result[3]
        }
    
    @nextcord.slash_command(
        name="gen",
        description="Generate an account for a specific service"
    )
    async def gen(
        self, 
        interaction: nextcord.Interaction, 
        service: str = SlashOption(
            name="service",
            description="The service to generate an account for",
            required=True
        )
    ):
        from main import log_command, is_vip, is_admin
        log_command(
            interaction.user.id, 
            f"{interaction.user.name}#{interaction.user.discriminator}", 
            "/gen", 
            service
        )
        
        service_info = self._get_service_info(service)
        if not service_info:
            await interaction.response.send_message(
                f"❌ Service `{service}` not found. Use `/list` to see available services.",
                ephemeral=True
            )
            return
        
        user_is_vip = is_vip(interaction.user.id) or interaction.user.get_role(self.config["vip_role_id"]) is not None
        if service_info["vip_only"] and not user_is_vip:
            embed = nextcord.Embed(
                title="⭐ VIP Only Service",
                description=f"**{service_info['display_name']}** is a VIP-only service.",
                color=int(self.config["embed_color_error"], 16)
            )
            embed.add_field(
                name="Upgrade Today!",
                value="Get access to exclusive services and reduced cooldowns by upgrading to VIP!",
                inline=False
            )
            embed.add_field(
                name="How to Upgrade",
                value="Use `/upgrade` to see available VIP plans.",
                inline=False
            )
            embed.set_footer(text=self.config["footer_text"])
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        can_gen, time_left = self._can_generate(interaction.user.id, user_is_vip)
        if not can_gen:
            minutes, seconds = divmod(time_left, 60)
            hours, minutes = divmod(minutes, 60)
            
            time_format = ""
            if hours > 0:
                time_format += f"{hours}h "
            if minutes > 0:
                time_format += f"{minutes}m "
            time_format += f"{seconds}s"
            
            embed = nextcord.Embed(
                title="⏰ Cooldown Active",
                description=f"You need to wait **{time_format}** before generating another account.",
                color=int(self.config["embed_color_error"], 16)
            )
            
            if not user_is_vip:
                embed.add_field(
                    name="⭐ VIP Benefits",
                    value="VIP users have a reduced cooldown of only 10 minutes!\nUse `/upgrade` to see available VIP plans.",
                    inline=False
                )
            
            embed.set_footer(text=self.config["footer_text"])
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        account = self._get_account(service)
        if not account:
            await interaction.response.send_message(
                f"❌ No accounts available for `{service_info['display_name']}`. Please contact an administrator.",
                ephemeral=True
            )
            return
        
        self._update_last_gen(interaction.user.id)
        
        try:
            username, password = account.split(':', 1)
        except ValueError:
            username = "Unknown"
            password = account
        
        try:
            embed = nextcord.Embed(
                title=f"{service_info['icon']}	GhostGen | Generated Account",
                description="Your account has been generated successfully!\nKeep it safe and **do not share it** with anyone.",
                color=int(self.config["embed_color"], 16)
            )
            
            embed.add_field(
                name="👤 Username",
                value=f"```{username}```",
                inline=True
            )
            embed.add_field(
                name="🔒 Password",
                value=f"```{password}```",
                inline=True
            )
            
            embed.add_field(
                name="",
                value="**EXTREME ACCESS\nUPGRADE TODAY!**",
                inline=True
            )
            
            embed.add_field(
                name="",
                value="**EXCLUSIVE COMMANDS**",
                inline=True
            )
            
            current_time = datetime.datetime.now().strftime("%H:%M Uhr")
            embed.add_field(
                name="",
                value=f"⚠️ You must change the password to keep the account • heute um {current_time}",
                inline=False
            )
            
            view = nextcord.ui.View()
            view.add_item(nextcord.ui.Button(label=f"{service_info['display_name']} Login", style=nextcord.ButtonStyle.secondary))
            view.add_item(nextcord.ui.Button(label="View Profile", style=nextcord.ButtonStyle.secondary))
            view.add_item(nextcord.ui.Button(label="⭐ Upgrade", style=nextcord.ButtonStyle.secondary))
            view.add_item(nextcord.ui.Button(label="Report Account", style=nextcord.ButtonStyle.danger))
            
            embed.set_thumbnail(url="https://i.imgur.com/ZdG19gYb.jpg")
            
            await interaction.user.send(embed=embed, view=view)
            
            await interaction.response.send_message(
                f"✅ Your **{service_info['display_name']}** account has been sent to your DMs!",
                ephemeral=True
            )
        except nextcord.Forbidden:
            await interaction.response.send_message(
                "❌ I couldn't send you a DM. Please enable DMs from server members.",
                ephemeral=True
            )
    
    @gen.on_autocomplete("service")
    async def gen_autocomplete(self, interaction: nextcord.Interaction, service: str):
        from main import is_vip
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        user_is_vip = is_vip(interaction.user.id) or interaction.user.get_role(self.config["vip_role_id"]) is not None
        
        if user_is_vip:
            cursor.execute("SELECT name, display_name FROM services")
        else:
            cursor.execute("SELECT name, display_name FROM services WHERE vip_only = 0")
        
        services = [(row[0], row[1]) for row in cursor.fetchall()]
        conn.close()
        
        if service:
            services = [
                (name, display) for name, display in services 
                if service.lower() in name.lower() or service.lower() in display.lower()
            ]
        
        return [f"{name}" for name, display in services][:25]

def setup(bot):
    bot.add_cog(GeneratorCog(bot))


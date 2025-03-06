import nextcord
from nextcord import SlashOption
from nextcord.ext import commands
import os
import json
import datetime
import sqlite3
import asyncio
from typing import List, Optional

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("config.json", "r") as f:
            self.config = json.load(f)
    
    def _is_admin(self, interaction: nextcord.Interaction) -> bool:
        from main import is_admin
        return (
            is_admin(interaction.user.id) or 
            interaction.user.get_role(self.config["admin_role_id"]) is not None
        )
    
    @nextcord.slash_command(
        name="add",
        description="Add accounts to a service"
    )
    async def add(
        self, 
        interaction: nextcord.Interaction, 
        service: str = SlashOption(
            name="service",
            description="The service to add accounts to",
            required=True
        )
    ):
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/add", service)
        
        await interaction.response.defer(ephemeral=True)
        
        await interaction.followup.send(
            "📤 Please upload a text file with accounts (one per line).",
            ephemeral=True
        )
        
        def check(m):
            return m.author.id == interaction.user.id and m.attachments
        
        try:
            message = await self.bot.wait_for("message", check=check, timeout=60)
            attachment = message.attachments[0]
            
            if not attachment.filename.endswith((".txt", ".config")):
                await interaction.followup.send(
                    "❌ Please upload a .txt or .config file.",
                    ephemeral=True
                )
                return
            
            content = await attachment.read()
            accounts = content.decode("utf-8").splitlines()
            
            try:
                await message.delete()
            except:
                pass
        except asyncio.TimeoutError:
            await interaction.followup.send(
                "❌ Timed out waiting for file upload.",
                ephemeral=True
            )
            return
        
        accounts = [acc for acc in accounts if acc.strip()]
        
        if not accounts:
            await interaction.followup.send(
                "❌ No valid accounts found in the file.",
                ephemeral=True
            )
            return
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT display_name FROM services WHERE name = ?", (service,))
        result = cursor.fetchone()
        
        if result is None:
            await interaction.followup.send(
                f"⚠️ Service `{service}` doesn't exist. Do you want to create it? (yes/no)",
                ephemeral=True
            )
            
            def check(m):
                return m.author.id == interaction.user.id and m.content.lower() in ["yes", "no"]
            
            try:
                message = await self.bot.wait_for("message", check=check, timeout=30)
                
                if message.content.lower() == "yes":
                    display_name = service.capitalize()
                    
                    await interaction.followup.send(
                        f"📝 Enter a display name for `{service}` (default: {display_name}):",
                        ephemeral=True
                    )
                    
                    def check_name(m):
                        return m.author.id == interaction.user.id
                    
                    try:
                        name_message = await self.bot.wait_for("message", check=check_name, timeout=30)
                        if name_message.content.strip():
                            display_name = name_message.content.strip()
                    except asyncio.TimeoutError:
                        pass
                
                    await interaction.followup.send(
                        f"⭐ Should `{service}` be VIP-only? (yes/no)",
                        ephemeral=True
                    )
                    
                    def check_vip(m):
                        return m.author.id == interaction.user.id and m.content.lower() in ["yes", "no"]
                    
                    vip_only = 0
                    try:
                        vip_message = await self.bot.wait_for("message", check=check_vip, timeout=30)
                        if vip_message.content.lower() == "yes":
                            vip_only = 1
                    except asyncio.TimeoutError:
                        pass
                    
                    await interaction.followup.send(
                        f"🔣 Enter an emoji icon for `{service}` (default: 🔑):",
                        ephemeral=True
                    )
                    
                    icon = "🔑"
                    try:
                        icon_message = await self.bot.wait_for("message", check=check_name, timeout=30)
                        if icon_message.content.strip():
                            icon = icon_message.content.strip()
                    except asyncio.TimeoutError:
                        pass
                    
                    cursor.execute(
                        "INSERT INTO services (name, display_name, vip_only, icon) VALUES (?, ?, ?, ?)",
                        (service, display_name, vip_only, icon)
                    )
                    conn.commit()
                else:
                    await interaction.followup.send(
                        "❌ Operation cancelled.",
                        ephemeral=True
                    )
                    conn.close()
                    return
            except asyncio.TimeoutError:
                await interaction.followup.send(
                    "❌ Timed out waiting for response.",
                    ephemeral=True
                )
                conn.close()
                return
        
        conn.close()
        
        file_path = f"data/{service}.txt"
        mode = "a" if os.path.exists(file_path) else "w"
        
        with open(file_path, mode) as f:
            f.write("\n".join(accounts) + "\n")
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        cursor.execute("SELECT display_name FROM services WHERE name = ?", (service,))
        display_name = cursor.fetchone()[0]
        conn.close()
        
        embed = nextcord.Embed(
            title="✅ Accounts Added",
            description=f"Successfully added **{len(accounts)}** accounts to **{display_name}**.",
            color=int(self.config["embed_color_success"], 16),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="Service", value=display_name, inline=True)
        embed.add_field(name="Accounts", value=str(len(accounts)), inline=True)
        embed.add_field(name="Total Stock", value=str(self._get_stock(service)), inline=True)
        
        embed.set_footer(text=self.config["footer_text"])
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    def _get_stock(self, service: str) -> int:
        try:
            with open(f"data/{service}.txt", "r") as f:
                return len(f.read().splitlines())
        except FileNotFoundError:
            return 0
    
    @nextcord.slash_command(
        name="stock",
        description="Check the stock of accounts for a service"
    )
    async def stock(
        self, 
        interaction: nextcord.Interaction, 
        service: Optional[str] = SlashOption(
            name="service",
            description="The service to check stock for (leave empty for all services)",
            required=False
        )
    ):
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/stock", service)
        
        embed = nextcord.Embed(
            title="📊 Account Stock",
            color=int(self.config["embed_color_info"], 16),
            timestamp=datetime.datetime.now()
        )
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        if service:
            cursor.execute("SELECT display_name, icon FROM services WHERE name = ?", (service,))
            result = cursor.fetchone()
            
            if not result:
                await interaction.response.send_message(
                    f"❌ Service `{service}` not found.",
                    ephemeral=True
                )
                conn.close()
                return
            
            display_name, icon = result
            
            stock = self._get_stock(service)
            
            embed.add_field(
                name=f"{icon} {display_name}",
                value=f"**{stock}** accounts available",
                inline=False
            )
        else:
            cursor.execute("SELECT name, display_name, icon FROM services ORDER BY display_name")
            services = cursor.fetchall()
            
            if not services:
                await interaction.response.send_message(
                    "❌ No services found.",
                    ephemeral=True
                )
                conn.close()
                return
            
            for service_name, display_name, icon in services:
                stock = self._get_stock(service_name)
                
                embed.add_field(
                    name=f"{icon} {display_name}",
                    value=f"**{stock}** accounts available",
                    inline=True
                )
        
        conn.close()
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.slash_command(
        name="adduser",
        description="Add or modify a user's permissions"
    )
    async def adduser(
        self,
        interaction: nextcord.Interaction,
        user: nextcord.Member = SlashOption(
            name="user",
            description="The user to modify",
            required=True
        ),
        role: str = SlashOption(
            name="role",
            description="The role to assign",
            required=True,
            choices={"VIP": "vip", "Admin": "admin", "Normal": "normal"}
        )
    ):
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/adduser", f"{user.name}:{role}")
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
        result = cursor.fetchone()
        
        if result is None:
            cursor.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?)",
                (user.id, str(user))
            )
        
        if role == "vip":
            cursor.execute(
                "UPDATE users SET is_vip = 1, is_admin = 0 WHERE user_id = ?",
                (user.id,)
            )
            role_name = "VIP"
        elif role == "admin":
            cursor.execute(
                "UPDATE users SET is_vip = 1, is_admin = 1 WHERE user_id = ?",
                (user.id,)
            )
            role_name = "Admin"
        else:  # normal
            cursor.execute(
                "UPDATE users SET is_vip = 0, is_admin = 0 WHERE user_id = ?",
                (user.id,)
            )
            role_name = "Normal"
        
        conn.commit()
        conn.close()
        
        embed = nextcord.Embed(
            title="👤 User Updated",
            description=f"Successfully updated {user.mention}'s permissions.",
            color=int(self.config["embed_color_success"], 16),
            timestamp=datetime.datetime.now()
        )
        
        embed.add_field(name="User", value=str(user), inline=True)
        embed.add_field(name="New Role", value=role_name, inline=True)
        
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.slash_command(
        name="logs",
        description="View recent command logs"
    )
    async def logs(
        self,
        interaction: nextcord.Interaction,
        limit: int = SlashOption(
            name="limit",
            description="Number of logs to show (max 50)",
            required=False,
            min_value=1,
            max_value=50,
            default=10
        ),
        user: nextcord.Member = SlashOption(
            name="user",
            description="Filter logs by user",
            required=False
        )
    ):
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/logs")
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        if user:
            cursor.execute(
                "SELECT username, command, service, timestamp FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user.id, limit)
            )
        else:
            cursor.execute(
                "SELECT username, command, service, timestamp FROM logs ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        
        logs = cursor.fetchall()
        conn.close()
        
        if not logs:
            await interaction.response.send_message(
                "❌ No logs found.",
                ephemeral=True
            )
            return
        
        embed = nextcord.Embed(
            title="📜 Command Logs",
            color=int(self.config["embed_color_info"], 16),
            timestamp=datetime.datetime.now()
        )
        
        log_text = ""
        for username, command, service, timestamp in logs:
            dt = datetime.datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            
            service_str = f" ({service})" if service else ""
            log_text += f"`{time_str}` **{username}**: {command}{service_str}\n"
        
        embed.description = log_text
        embed.set_footer(text=self.config["footer_text"])
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @nextcord.slash_command(
        name="purge",
        description="Delete a service and all its accounts"
    )
    async def purge(
        self,
        interaction: nextcord.Interaction,
        service: str = SlashOption(
            name="service",
            description="The service to delete",
            required=True
        ),
        confirm: str = SlashOption(
            name="confirm",
            description="Type 'confirm' to confirm deletion",
            required=True
        )
    ):
        if not self._is_admin(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.",
                ephemeral=True
            )
            return
        
        if confirm.lower() != "confirm":
            await interaction.response.send_message(
                "❌ Operation cancelled. You must type 'confirm' to confirm deletion.",
                ephemeral=True
            )
            return
        
        from main import log_command
        log_command(interaction.user.id, str(interaction.user), "/purge", service)
        
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT display_name FROM services WHERE name = ?", (service,))
        result = cursor.fetchone()
        
        if not result:
            await interaction.response.send_message(
                f"❌ Service `{service}` not found.",
                ephemeral=True
            )
            conn.close()
            return
        
        display_name = result[0]
        
        cursor.execute("DELETE FROM services WHERE name = ?", (service,))
        conn.commit()
        conn.close()
        
        file_path = f"data/{service}.txt"
        if os.path.exists(file_path):
            os.remove(file_path)
        
        embed = nextcord.Embed(
            title="🗑️ Service Deleted",
            description=f"Successfully deleted service **{display_name}** and all its accounts.",
            color=int(self.config["embed_color_success"], 16),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_footer(text=self.config["footer_text"])
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @add.on_autocomplete("service")
    @stock.on_autocomplete("service")
    @purge.on_autocomplete("service")
    async def service_autocomplete(self, interaction: nextcord.Interaction, service: str):
        conn = sqlite3.connect('altgen.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, display_name FROM services")
        services = [(row[0], row[1]) for row in cursor.fetchall()]
        
        conn.close()
        
        if not service:
            return [s[0] for s in services][:25]
        
        return [
            s[0] for s in services 
            if service.lower() in s[0].lower() or service.lower() in s[1].lower()
        ][:25]

def setup(bot):
    bot.add_cog(AdminCog(bot))


# 🚀 GhostGen - Account Generator

GhostGen is a Discord bot designed to manage and distribute pre-existing  accounts. It does **not** generate accounts itself but allows administrators to store and distribute them via commands. 🔥

---

## ✨ Features
✅ Store and manage premium accounts in a local folder  
✅ User, VIP, and Admin commands for easy access  
✅ Check stock, logs, and manage user roles  
✅ Securely distribute accounts without exposing credentials publicly via dm

---

## 🛠 Installation
### 📌 Requirements
- Python 3.x
- `discord.py` and required dependencies

### 🚀 Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/HakuGenBot.git
   cd HakuGenBot
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure the bot:**
   - Rename `config.example.json` to `config.json`
   - Edit `config.json` with your bot token and settings

4. **Run the bot:**
   ```bash
   python bot.py
   ```

---

## ⚙️ Configuration
Edit `config.json` to set up your bot:
```json
{
  "token": "YOUR_BOT_TOKEN",  // Your Discord bot token
  "guild_id": "YOUR_GUILD_ID",  // The ID of your Discord server
  "admin_role_id": YOUR_ADMIN_ROLE_ID,  // The role ID for administrators
  "vip_role_id": YOUR_VIP_ROLE_ID,  // The role ID for VIP users
  "normal_cooldown": 3600,  // Cooldown time (in seconds) for normal users
  "vip_cooldown": 600,  // Cooldown time (in seconds) for VIP users
  "embed_color": "0xFF5733",  // Default embed color
  "embed_color_success": "0x00FF7F",  // Success message color
  "embed_color_error": "0xFF0000",  // Error message color
  "embed_color_info": "0x3498DB",  // Informational message color
  "footer_text": "GhostGen v1.0 | Premium Account Generator",  // Footer text for embeds
  "bot_avatar": "https://imgur.com/youravatar"  // Bot avatar URL
}
```
🔹 **Note:** The bot does **not** generate accounts. Administrators must manually add accounts to the specified storage folder.

---

## 📖 Usage
- **User Commands:** `/gen`, `/list`, `/help`, `/ping`
- **VIP Commands:** `/vipstatus`
- **Admin Commands:** `/add`, `/stock`, `/adduser`, `/logs`, `/purge`, `/stats`

---

## ⚠️ Disclaimer
GhostGen does **not** create or provide premium accounts. It is a management tool that helps distribute pre-existing accounts securely.

---

## 📜 License
MIT License

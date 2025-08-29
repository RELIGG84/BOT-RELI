import discord
import requests
import json
import random
import os
import asyncio
from discord.ui import Button, View
from datetime import datetime, timedelta

# Importimi i librarive të nevojshme
try:
    import youtube_dl
    import nacl
except ImportError:
    print("Nuk u gjetën libraritë e nevojshme. Po instaloj...")
    os.system('pip install youtube_dl PyNaCl')
    print("Instalimi përfundoi. Ju lutem, ridizni botin.")
    exit()

#----------------------------------------------------
# TË DHËNAT TUAJA PERSONALE (PLOTËSOJINI TË GJITHA!)
#----------------------------------------------------
# Këtu duhet të vendosni token-in tuaj personal të botit
TOKEN = 'MTQxMDc0MzU0OTAxNTg4ODA2NA.G0oxWM.HjdFNC07xMxJyoqGbxptEkm1auO38kEHGXiKJc'

# ID-të e kanaleve në serverin tënd
WELCOME_CHANNEL_ID = 1073356064164155515
LOGGING_CHANNEL_ID = 1192153384371896480
ROLE_SELECTION_CHANNEL_ID = 1410810519127986288
ANNOUNCEMENT_CHANNEL_ID = 1410985202364322003
MODERATION_CHANNEL_ID = 1410985314582921216
VERIFICATION_CHANNEL_ID = 1410985457344450580
LFG_CHANNEL_ID = 1410985566064869491  # ⚠️ SHTO KËTU ID-në e kanalit "lfg" (looking for game)

# Emrat e roleve që boti do të përdorë
DEFAULT_ROLE_NAME = 'Anëtar'
UNVERIFIED_ROLE_NAME = 'I Paverifikuar'
SUPPORTER_ROLE_NAME = 'RELI Supporter'
YOUTUBE_ROLE_NAME = 'YouTube Subscriber'
TIKTOK_ROLE_NAME = 'TikTok Follower'
INSTAGRAM_ROLE_NAME = 'Instagram Follower'
TWITCH_ROLE_NAME = 'Twitch Follower'

# Të dhënat e krijuesit të serverit
CREATOR_CODE = "RELI"
CREATOR_NAME = "RELI"

# KODI I MAPIT TUAJ TË FORTNITE
MAP_CODE = "7188-6091-4920 https://fortnite.gg/island?code=7188-6091-4920"

# LINQET TUAJA TË RRJETEVE SOCIALE
TIKTOK_LINK = "https://www.tiktok.com/@religg"
INSTAGRAM_LINK = "https://www.instagram.com/reli.88888/"
TWITCH_LINK = "https://www.twitch.tv/religg50"
YOUTUBE_LINK = "https://www.youtube.com/@RELI-GG"

# LISTA E HITEVE TË REJA PËR KOMANDËN /hitlist
HITLIST = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", 
    "https://www.youtube.com/watch?v=y6120QO_i-k"  
]

# TË DHËNAT E ROLEVE PËR BUTONA
ROLES = [
    {"name": "Fortnite", "emoji": "🎮"},
    {"name": "VALORANT", "emoji": "🔫"},
    {"name": "Shqipëri", "emoji": "🇦🇱"},
    {"name": "Kosovë", "emoji": "🇽🇰"}
]

# LISTA E FJALËVE OFENDUESE NË SHQIP (Shto/Fshij sipas nevojës)
OFFENSIVE_WORDS = [
    "robt", "mut", "kac", "kurv", "peder", "pidh", "bysh", "byth", "qif", "qiell",
    "bitch", "fuck", "asshole", "pederast", "drogaxhi", "rober"
]

# API-ja publike e Fortnite
FORTNITE_SHOP_API = "https://fortnite-api.com/v2/shop/br"
FORTNITE_STATS_API = "https://fortnite-api.com/v2/stats/br/v2"
FORTNITE_STW_API = "https://fortnite-api.com/v1/stw/missions"

#----------------------------------------------------
# KLASA DHE FUNKSIONET KRYESORE TË BOTIT
#----------------------------------------------------

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# Emri i skedarit ku do të ruhen emrat e përdoruesve
USERS_FILE = 'users.json'
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({}, f)

# Funksioni për të llogaritur nivelin
def get_level(xp):
    level = 0
    while get_required_xp(level + 1) <= xp:
        level += 1
    return level

# Funksioni për të llogaritur pikët e nevojshme për nivelin tjetër
def get_required_xp(level):
    return 5 * (level ** 2) + 50 * level + 100

# OPSIONET PËR MUZIKËN
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
ffmpeg_options = {'options': '-vn'}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# KLASA E BUTONAVE PËR VERIFIKIM
class VerifyView(View):
    def __init__(self, bot_client):
        super().__init__(timeout=None)
        self.bot_client = bot_client
        
    @discord.ui.button(label="Verifiko Tani!", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button_callback(self, interaction: discord.Interaction, button: Button):
        member = interaction.user
        guild = interaction.guild
        
        verified_role = discord.utils.get(guild.roles, name=DEFAULT_ROLE_NAME)
        unverified_role = discord.utils.get(guild.roles, name=UNVERIFIED_ROLE_NAME)
        
        if not verified_role or not unverified_role:
            await interaction.response.send_message("Ndodhi një gabim me rolet. Ju lutem kontaktoni administratorin.", ephemeral=True)
            return

        if verified_role in member.roles:
            await interaction.response.send_message("Ju jeni tashmë i verifikuar!", ephemeral=True)
            return
            
        try:
            await member.add_roles(verified_role)
            await member.remove_roles(unverified_role)
            
            dm_embed = discord.Embed(
                title=f"🎉 Mirë se erdhe në server, {member.name}! 🎉",
                description=f"Mirë se erdhe në familjen tonë! Tani ke akses të plotë në të gjitha kanalet. ❤️\n\n"
                              f"Për të na mbështetur, përdor kodin e krijuesit **{CREATOR_CODE}** në dyqanin e Fortnite! 🌟\n\n"
                              f"Nëse ke bërë subscribe/follow, përdor komandën `/prove-follow` për të marrë një rol special në server! ✨",
                color=discord.Color.red()
            )
            dm_embed.add_field(name="Më ndiq në rrjete sociale:", value=f"**YouTube:** {YOUTUBE_LINK}\n**TikTok:** {TIKTOK_LINK}\n**Twitch:** {TWITCH_LINK}\n**Instagram:** {INSTAGRAM_LINK}", inline=False)
            dm_embed.set_footer(text="Shpresojmë të kënaqesh në server!")

            try:
                await member.send(embed=dm_embed)
            except discord.Forbidden:
                pass # Nuk mund të dërgoj mesazh privat

            await interaction.response.send_message("Jeni verifikuar me sukses! Udhëzimet e tjera i ke në mesazhin privat.", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("Nuk kam leje për të ndryshuar rolet. Ju lutem, kontrolloni lejet e mia.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Ndodhi një gabim: {e}", ephemeral=True)

# KLASA E BUTONAVE PËR ZGJEDHJEN E ROLEVE
class RoleSelectionView(View):
    def __init__(self, roles_data):
        super().__init__(timeout=None)
        for role_data in roles_data:
            button = Button(label=role_data['name'], style=discord.ButtonStyle.secondary, emoji=role_data['emoji'], custom_id=role_data['name'])
            button.callback = self.button_callback
            self.add_item(button)
    async def button_callback(self, interaction: discord.Interaction):
        role_name = interaction.item.custom_id
        guild = interaction.guild
        member = interaction.user
        role = discord.utils.get(guild.roles, name=role_name)
        if role is None:
            await interaction.response.send_message(f"Roli '{role_name}' nuk u gjet. Lajmëroni administratorin.", ephemeral=True)
            return
        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"Roli **{role.name}** ju dha me sukses!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Nuk kam leje për të dhënë këtë rol. Ju lutemi kontrolloni lejet e mia.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Ndodhi një gabim: {e}", ephemeral=True)

# KLASA PËR KËRKIM LOJTARËSH
class LFGView(View):
    def __init__(self, creator_id, game, players_needed):
        super().__init__(timeout=3600)  # Skadon pas 1 ore
        self.creator_id = creator_id
        self.game = game
        self.players_needed = players_needed
        self.players_joined = 0

    @discord.ui.button(label="Bashkohu!", style=discord.ButtonStyle.green)
    async def join_button_callback(self, interaction: discord.Interaction, button: Button):
        if self.players_joined >= self.players_needed:
            await interaction.response.send_message("Grupi tashmë është plot!", ephemeral=True)
            return
        
        creator = interaction.guild.get_member(self.creator_id)
        if not creator:
            await interaction.response.send_message("Lojtari që nisi kërkesën u largua.", ephemeral=True)
            return
            
        self.players_joined += 1
        
        await interaction.response.send_message(f"{interaction.user.mention} u bashkua me sukses!", ephemeral=True)
        
        if self.players_joined >= self.players_needed:
            await interaction.message.edit(content=f"**GRUPI ËSHTË PLOT!** 🥳", view=None)
            await creator.send(f"Hey {creator.mention}, grupi juaj për **{self.game}** është plot! Filloni të luani!")
        else:
            await interaction.message.edit(content=f"Kërkohen {self.players_needed - self.players_joined} lojtarë të tjerë për **{self.game}**!", view=self)

# EVENTS DHE FUNKSIONET KRYESORE
#----------------------------------------------------
@client.event
async def on_ready():
    await tree.sync()
    print(f'Boti {client.user} u lidh me sukses dhe është gati!')
    client.loop.create_task(check_inactivity())
    client.loop.create_task(send_daily_shop())

@client.event
async def on_member_join(member):
    unverified_role = discord.utils.get(member.guild.roles, name=UNVERIFIED_ROLE_NAME)
    if unverified_role:
        await member.add_roles(unverified_role)
    else:
        print(f'Roli "{UNVERIFIED_ROLE_NAME}" nuk u gjet.')
    
    welcome_channel = client.get_channel(VERIFICATION_CHANNEL_ID)
    if welcome_channel:
        await welcome_channel.send(f"Mirë se erdhe në server, **{member.mention}**! Për të vazhduar, shko në mesazhin tënd privat dhe ndiq udhëzimet. ❤️", delete_after=10)

@client.event
async def on_member_remove(member):
    logging_channel = client.get_channel(LOGGING_CHANNEL_ID)
    if logging_channel:
        await logging_channel.send(f"**{member.name}** u largua nga serveri. Na mbetet një anëtar më pak. 😢")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    
    if user_id not in users:
        users[user_id] = {"ban_warnings": 0, "last_message": None, "xp": 0}

    # Shto pikë për çdo mesazh (10 pikë per mesazh)
    users[user_id]["xp"] = users[user_id].get("xp", 0) + 10
    
    message_content_lower = message.content.lower()
    is_offensive = any(word in message_content_lower for word in OFFENSIVE_WORDS)
    
    if is_offensive:
        try:
            await message.delete()
            member = message.author
            
            if member.guild_permissions.administrator or member.id == member.guild.owner.id:
                await member.send("Përdorimi i fjalëve ofenduese nuk lejohet në këtë server, por si administrator nuk do të ndëshkoheni.")
                return

            users[user_id]["ban_warnings"] = users[user_id].get("ban_warnings", 0) + 1
            
            warnings_count = users[user_id]["ban_warnings"]
            logging_channel = client.get_channel(LOGGING_CHANNEL_ID)
            
            if warnings_count < 3:
                dm_message = f"**Paralajmërim:** Mesazhi juaj u fshi pasi përdorët gjuhë të papërshtatshme. Ky është paralajmërimi juaj i **{warnings_count}**-të. Pas 3 shkeljeve, do të ndaloheni përgjithmonë nga serveri."
                await member.send(dm_message)
                if logging_channel:
                    await logging_channel.send(f"Anëtari **{member.name}** mori paralajmërimin e **{warnings_count}**-të për gjuhë ofenduese.")
            else:
                await member.send(f"Jeni ndaluar përgjithmonë nga serveri pasi tejkaloni limitin e paralajmërimeve ({warnings_count} shkelje).")
                await member.ban(reason="Përdorim i përsëritur i gjuhës ofenduese.")
                if logging_channel:
                    await logging_channel.send(f"Anëtari **{member.name}** u ndalua përgjithmonë pas **{warnings_count}** shkeljesh.")
                del users[user_id]
                
        except discord.Forbidden:
            logging_channel = client.get_channel(LOGGING_CHANNEL_ID)
            if logging_channel:
                await logging_channel.send("Nuk kam leje të fshij mesazhe ose të ndëshkoj anëtarë. Ju lutem kontrolloni lejet.")
        except Exception as e:
            print(f"Gabim gjatë ndëshkimit: {e}")
    
    users[user_id]['last_message'] = datetime.now().isoformat()
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

async def check_inactivity():
    await client.wait_until_ready()
    logging_channel = client.get_channel(LOGGING_CHANNEL_ID)
    if not logging_channel:
        return
    while not client.is_closed():
        await asyncio.sleep(86400)
        with open(USERS_FILE, 'r') as f:
            users_data = json.load(f)
        now = datetime.now()
        members_to_kick = []
        for user_id, data in users_data.items():
            last_message_str = data.get('last_message')
            if last_message_str:
                last_message_date = datetime.fromisoformat(last_message_str)
                time_since_last_message = now - last_message_date
                if time_since_last_message > timedelta(days=30):
                    members_to_kick.append(user_id)
        for user_id in members_to_kick:
            try:
                member_to_kick = await logging_channel.guild.fetch_member(int(user_id))
                if member_to_kick:
                    if member_to_kick.guild_permissions.administrator or member_to_kick.id == member_to_kick.guild.owner.id:
                        continue
                    kick_reason = "U largua për shkak të pasivitetit (mbi 30 ditë pa mesazh)."
                    await member_to_kick.kick(reason=kick_reason)
                    await logging_channel.send(f"Anëtari **{member_to_kick.name}** u largua automatikisht për shkak të pasivitetit.")
                    del users_data[user_id]
                    with open(USERS_FILE, 'w') as f:
                        json.dump(users_data, f, indent=4)
            except (discord.Forbidden, discord.HTTPException, ValueError):
                pass
            except Exception as e:
                print(f"Gabim gjatë largimit të anëtarit {user_id}: {e}")

async def send_daily_shop():
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.sleep(3600 * 24)
        try:
            response = requests.get(FORTNITE_SHOP_API)
            response.raise_for_status()
            data = response.json().get('data')
            if not data or not data.get('featured') or not data.get('featured')['entries']:
                continue
            
            announcement_channel = client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            if announcement_channel:
                embed = discord.Embed(
                    title="Dyqani i Fortnite i sotëm! 🛒",
                    description=f"Mos harroni të përdorni kodin e krijuesit **{CREATOR_CODE}**!",
                    color=discord.Color.blue()
                )
                items_to_display = data['featured']['entries']
                for item in items_to_display[:5]:
                    name = item.get('items')[0]['name']
                    price = item.get('finalPrice')
                    rarity = item.get('items')[0]['rarity']['displayValue']
                    embed.add_field(name=f"{name} ({rarity})", value=f"Çmimi: {price} V-Bucks", inline=False)
                
                await announcement_channel.send(embed=embed)
        except Exception as e:
            print(f"Gabim gjatë dërgimit të dyqanit të përditshëm: {e}")

# KOMANDAT E MODERIMIT
#----------------------------------------------------
@tree.command(name="kick", description="Largoni një anëtar nga serveri.")
@discord.app_commands.describe(member="Anëtari që do të largohet", reason="Arsyeja e largimit.")
@discord.app_commands.default_permissions(kick_members=True)
async def kick_command(interaction: discord.Interaction, member: discord.Member, reason: str = "Asnjë arsye nuk u specifikua."):
    if member.guild_permissions.administrator:
        await interaction.response.send_message("Nuk mund të largoni një administrator.", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"Anëtari **{member.name}** u largua. Arsyeja: {reason}")

@tree.command(name="ban", description="Ndaloje një anëtar nga serveri.")
@discord.app_commands.describe(member="Anëtari që do të ndalohet", reason="Arsyeja e ndalimit.")
@discord.app_commands.default_permissions(ban_members=True)
async def ban_command(interaction: discord.Interaction, member: discord.Member, reason: str = "Asnjë arsye nuk u specifikua."):
    if member.guild_permissions.administrator:
        await interaction.response.send_message("Nuk mund të ndaloni një administrator.", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"Anëtari **{member.name}** u ndalua. Arsyeja: {reason}")

@tree.command(name="unban", description="Zhblloko një përdorues nga serveri duke përdorur ID-në e tij.")
@discord.app_commands.describe(userid="ID e përdoruesit për të zhbllokuar.")
@discord.app_commands.default_permissions(ban_members=True)
async def unban_command(interaction: discord.Interaction, userid: str):
    try:
        user = await client.fetch_user(int(userid))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"Përdoruesi me ID `{userid}` u zhbllokua me sukses.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("Nuk u gjet asnjë përdorues i ndaluar me këtë ID.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Gabim gjatë zhbllokimit: {e}", ephemeral=True)

@tree.command(name="warn", description="Jepi një paralajmërim një anëtari dhe regjistroje atë.")
@discord.app_commands.describe(member="Anëtari që do të paralajmërohet.", reason="Arsyeja e paralajmërimit.")
@discord.app_commands.default_permissions(kick_members=True)
async def warn_command(interaction: discord.Interaction, member: discord.Member, reason: str):
    if member.guild_permissions.administrator or member.id == member.guild.owner.id:
        await interaction.response.send_message("Nuk mund të paralajmëroni një administrator.", ephemeral=True)
        return
    try:
        dm_message = f"**Paralajmërim:** Ju keni marrë një paralajmërim nga moderatori **{interaction.user.name}** në serverin **{interaction.guild.name}**. Arsyeja: **{reason}**."
        await member.send(dm_message)
        logging_channel = client.get_channel(LOGGING_CHANNEL_ID)
        if logging_channel:
            await logging_channel.send(f"Moderatori **{interaction.user.name}** paralajmëroi anëtarin **{member.name}** me arsyen: **{reason}**.")
        await interaction.response.send_message(f"Anëtari **{member.name}** u paralajmërua me sukses.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Nuk mund t'i dërgoj mesazh privat anëtarit.", ephemeral=True)

@tree.command(name="announce", description="Dërgo një njoftim si admin.")
@discord.app_commands.describe(message="Mesazhi i njoftimit.")
@discord.app_commands.default_permissions(administrator=True)
async def announce_command(interaction: discord.Interaction, message: str):
    announcement_channel = client.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if announcement_channel:
        embed = discord.Embed(
            title="Njoftim i Rëndësishëm!",
            description=message,
            color=discord.Color.red()
        )
        await announcement_channel.send(embed=embed)
        await interaction.response.send_message("Njoftimi u dërgua me sukses!", ephemeral=True)
    else:
        await interaction.response.send_message("Kanali i njoftimeve nuk u gjet. Ju lutemi kontrolloni ID-në e kanalit.", ephemeral=True)

@tree.command(name="ban-request", description="Dërgo një kërkesë private tek pronari i serverit për zhbllokim (unban).")
@discord.app_commands.describe(banned_username="Emri i përdoruesit të ndaluar që dëshiron të zhbllokohet.")
async def ban_request_command(interaction: discord.Interaction, banned_username: str):
    owner = interaction.guild.owner
    if not owner:
        await interaction.response.send_message("Nuk u gjet pronari i serverit për të dërguar kërkesën.", ephemeral=True)
        return
    try:
        await owner.send(f"**Kërkesë për Zhbllokim!**\n"
                          f"Anëtari **{interaction.user.name}** ka dërguar një kërkesë për zhbllokimin e përdoruesit **{banned_username}**.")
        await interaction.response.send_message(f"Kërkesa juaj për zhbllokim për **{banned_username}** u dërgua me sukses tek pronari i serverit.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Nuk munda t'i dërgoj mesazh privat pronarit të serverit. Ai/ajo mund t'i ketë DM-të e mbyllura.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Ndodhi një gabim gjatë dërgimit të kërkesës: {e}", ephemeral=True)

# KOMANDAT E MUZIKËS
#----------------------------------------------------
@tree.command(name="play", description="Luaj një këngë nga YouTube ose URL-ja.")
@discord.app_commands.describe(url="URL-ja e këngës në YouTube ose emri i saj.")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    if not interaction.user.voice:
        return await interaction.followup.send("Duhet të jesh në një kanal zëri për të luajtur muzikë.")
    channel = interaction.user.voice.channel
    try:
        if interaction.guild.voice_client is None:
            await channel.connect()
        else:
            await interaction.guild.voice_client.move_to(channel)
        player = await YTDLSource.from_url(url, loop=client.loop, stream=True)
        interaction.guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await interaction.followup.send(f'Tani po luaj: **{player.title}**')
    except Exception as e:
        await interaction.followup.send(f'Ndodhi një gabim: {e}')

@tree.command(name="stop", description="Ndaloje muzikën dhe largohu nga kanali zanor.")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("Muzika u ndalua. U largova nga kanali zanor.")
    else:
        await interaction.response.send_message("Boti nuk është në një kanal zanor.")

@tree.command(name="pause", description="Ndaloje muzikën përkohësisht.")
async def pause(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        await interaction.response.send_message("Muzika u ndalua përkohësisht.")
    else:
        await interaction.response.send_message("Asnjë muzikë nuk po luhet.")

@tree.command(name="resume", description="Rifilloje muzikën.")
async def resume(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        await interaction.response.send_message("Muzika u rifillua.")
    else:
        await interaction.response.send_message("Muzika nuk është ndalur.")

@tree.command(name="hitlist", description="Luaj një këngë hitlist.")
async def hitlist_command(interaction: discord.Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message("Duhet të jesh në një kanal zëri për të luajtur hitlist.")
    channel = interaction.user.voice.channel
    try:
        if interaction.guild.voice_client is None:
            await channel.connect()
        else:
            await interaction.guild.voice_client.move_to(channel)
        url = random.choice(HITLIST)
        player = await YTDLSource.from_url(url, loop=client.loop, stream=True)
        interaction.guild.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await interaction.response.send_message(f'Tani po luaj: **{player.title}** nga hitlist!')
    except Exception as e:
        await interaction.response.send_message(f'Ndodhi një gabim: {e}')

# KOMANDAT E BUTONAVE TE RROLEVE
#----------------------------------------------------
@tree.command(name="zgjidh-rolet", description="Dërgon një mesazh me butona për të zgjedhur rolet.")
@discord.app_commands.default_permissions(administrator=True)
async def send_role_buttons(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Zgjidh Rolet",
        description="Klikoni mbi butonat për të marrë rolet tuaja të preferuara!",
        color=discord.Color.green()
    )
    view = RoleSelectionView(ROLES)
    await interaction.response.send_message(embed=embed, view=view)

@tree.command(name="verifiko-serverin", description="Dërgon mesazhin e verifikimit me buton.")
@discord.app_commands.default_permissions(administrator=True)
async def send_verify_message(interaction: discord.Interaction):
    verify_channel = client.get_channel(VERIFICATION_CHANNEL_ID)
    if not verify_channel:
        await interaction.response.send_message("Kanali i verifikimit nuk u gjet. Ju lutem, kontrolloni ID-në e kanalit.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Verifikimi i Anëtarit",
        description="Për të marrë akses të plotë në server, ju lutem klikoni butonin më poshtë për t'u verifikuar. Pasi të verifikoheni, do të merrni udhëzime të mëtejshme.",
        color=discord.Color.blue()
    )
    view = VerifyView(client)
    await verify_channel.send(embed=embed, view=view)
    await interaction.response.send_message("Mesazhi i verifikimit u dërgua me sukses!", ephemeral=True)

# KOMANDAT E FORTNITE
#----------------------------------------------------
@tree.command(name="stats", description="Shfaq statistikat e lojtarit të regjistruar të Fortnite.")
async def stats_command(interaction: discord.Interaction):
    await interaction.response.defer()
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    user_id = str(interaction.user.id)
    if user_id not in users or "name" not in users[user_id]:
        await interaction.followup.send("Ju lutemi regjistroni ID-në tuaj të Epic Games duke përdorur `/regjistro-fortnite [ID_epic_games]`.")
        return
    player_name = users[user_id]["name"]
    try:
        response = requests.get(FORTNITE_STATS_API, params={'name': player_name})
        response.raise_for_status()
        data = response.json().get('data')
        if data:
            stats = data['stats']['all']['overall']
            embed = discord.Embed(
                title=f"Statistikat e Fortnite për {data['account']['name']}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Fitore", value=stats.get('wins', 0), inline=True)
            embed.add_field(name="Vrasje", value=stats.get('kills', 0), inline=True)
            embed.add_field(name="Vlerësimi K/D", value=f"{stats.get('kd', 0):.2f}", inline=True)
            embed.add_field(name="Ndeshje të Luajtura", value=stats.get('matches', 0), inline=True)
            embed.add_field(name="Kohëzgjatja (Orë)", value=f"{stats.get('minutesPlayed', 0) / 60:.2f}", inline=True)
            embed.add_field(name="Shkalla e Fitorjeve", value=f"{stats.get('winRatio', 0):.2f}%", inline=True)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Nuk u gjetën të dhëna për këtë lojtar. Kontrolloni emrin dhe provoni përsëri.")
    except requests.exceptions.RequestException:
        await interaction.followup.send("Nuk mund të lidhem me API-në e Fortnite. Ju lutemi provoni përsëri më vonë.")

@tree.command(name="shop", description="Shfaq artikujt e dyqanit të Fortnite të sotëm.")
async def shop_command(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        response = requests.get(FORTNITE_SHOP_API)
        response.raise_for_status()
        data = response.json().get('data')
        if not data or not data.get('featured') or not data.get('featured')['entries']:
            await interaction.followup.send("Nuk u gjetën artikuj në dyqan sot.")
            return
        
        embed = discord.Embed(
            title="Dyqani i Fortnite i sotëm",
            description=f"Artikuj të rinj dhe kthime!",
            color=discord.Color.blue()
        )
        
        items_to_display = data['featured']['entries']
        
        for item in items_to_display[:10]:
            name = item.get('items')[0]['name']
            price = item.get('finalPrice')
            rarity = item.get('items')[0]['rarity']['displayValue']
            image_url = item.get('items')[0]['images']['icon']
            
            embed.add_field(name=f"{name} ({rarity})", value=f"Çmimi: {price} V-Bucks", inline=True)
        
        await interaction.followup.send(embed=embed)
    except requests.exceptions.RequestException:
        await interaction.followup.send("Nuk mund të lidhem me API-në e Fortnite. Ju lutemi provoni përsëri më vonë.")

@tree.command(name="regjistro-fortnite", description="Regjistro ID-në tuaj të Epic Games dhe merr kodin e krijuesit.")
@discord.app_commands.describe(player_name="ID-ja juaj e Epic Games", used_code="Konfirmo nëse ke përdorur kodin e krijuesit.")
@discord.app_commands.choices(used_code=[
    discord.app_commands.Choice(name="Po", value="yes"),
    discord.app_commands.Choice(name="Jo", value="no")
])
async def register_command(interaction: discord.Interaction, player_name: str, used_code: str = "no"):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    
    if user_id not in users:
        users[user_id] = {"name": player_name, "xp": 0, "last_message": datetime.now().isoformat()}
    else:
        users[user_id]["name"] = player_name
    
    response_message = f"Faleminderit! ID-ja juaj **{player_name}** është regjistruar. ✅\n\n"
    
    if used_code == "yes":
        supporter_role = discord.utils.get(interaction.guild.roles, name=SUPPORTER_ROLE_NAME)
        if supporter_role:
            try:
                await interaction.user.add_roles(supporter_role)
                response_message += f"Faleminderit që përdor kodin tim! Tani ju është dhënë roli **{SUPPORTER_ROLE_NAME}**! ❤️"
            except discord.Forbidden:
                response_message += "Nuk kam leje për të dhënë rolin e mbështetësit. Ju lutem kontrolloni lejet e mia."
        else:
            response_message += f"Roli `{SUPPORTER_ROLE_NAME}` nuk u gjet. Ju lutemi kontaktoni një administrator."
    else:
        response_message += f"Për të na mbështetur, përdorni kodin e krijuesit **`{CREATOR_CODE}`** në dyqan! 🤩"
        
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)
        
    await interaction.followup.send(response_message)

@tree.command(name="map", description="Shfaq kodin e hartës së lojës me mundësinë e kopjimit.")
async def map_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Harta e Lojës",
        description=f"Kopjoni kodin e hartës më poshtë dhe luani me miqtë!",
        color=discord.Color.purple()
    )
    embed.add_field(name="Kodi i Hartës", value=f"```\n{MAP_CODE}\n```", inline=False)
    await interaction.response.send_message(embed=embed)

@tree.command(name="prove-follow", description="Dërgo një kërkesë për rol social. Përfshini një screenshot.")
@discord.app_commands.describe(platform="Zgjidhni platformën.", username="Emri juaj i përdoruesit në atë platformë.")
@discord.app_commands.choices(platform=[
    discord.app_commands.Choice(name="YouTube", value="youtube"),
    discord.app_commands.Choice(name="TikTok", value="tiktok"),
    discord.app_commands.Choice(name="Instagram", value="instagram"),
    discord.app_commands.Choice(name="Twitch", value="twitch")
])
async def prove_follow_command(interaction: discord.Interaction, platform: discord.app_commands.Choice[str], username: str):
    mod_channel = client.get_channel(MODERATION_CHANNEL_ID)
    if not mod_channel:
        await interaction.response.send_message("Kanali i moderimit nuk u gjet. Ju lutemi kontaktoni një administrator.", ephemeral=True)
        return
        
    embed = discord.Embed(
        title="Kërkesë për Rol Social!",
        description=f"Anëtari **{interaction.user.name}** ka kërkuar një rol social.",
        color=discord.Color.gold()
    )
    embed.add_field(name="Platforma", value=f"**{platform.name}**", inline=True)
    embed.add_field(name="Përdoruesi", value=f"**{username}**", inline=True)
    embed.set_footer(text=f"ID-ja e anëtarit: {interaction.user.id}")
    
    await mod_channel.send(f"⚠️ Kërkesë e re për rol! Modertorë, ju lutem verifikoni dhe përdorni `/add-social-role`.", embed=embed)
    await interaction.response.send_message(f"Kërkesa juaj për rolin **{platform.name}** u dërgua te moderatorët. Ju lutem jepni një screenshot si dëshmi.", ephemeral=True)

@tree.command(name="add-social-role", description="Jepi një anëtari një rol social pas verifikimit.")
@discord.app_commands.describe(member="Anëtari që do të marrë rolin.", platform="Roli që do t'i jepet.")
@discord.app_commands.choices(platform=[
    discord.app_commands.Choice(name="YouTube", value="youtube"),
    discord.app_commands.Choice(name="TikTok", value="tiktok"),
    discord.app_commands.Choice(name="Instagram", value="instagram"),
    discord.app_commands.Choice(name="Twitch", value="twitch")
])
@discord.app_commands.default_permissions(manage_roles=True)
async def add_social_role_command(interaction: discord.Interaction, member: discord.Member, platform: discord.app_commands.Choice[str]):
    role_to_give = None
    if platform.value == "youtube":
        role_to_give = discord.utils.get(interaction.guild.roles, name=YOUTUBE_ROLE_NAME)
    elif platform.value == "tiktok":
        role_to_give = discord.utils.get(interaction.guild.roles, name=TIKTOK_ROLE_NAME)
    elif platform.value == "instagram":
        role_to_give = discord.utils.get(interaction.guild.roles, name=INSTAGRAM_ROLE_NAME)
    elif platform.value == "twitch":
        role_to_give = discord.utils.get(interaction.guild.roles, name=TWITCH_ROLE_NAME)
    
    if not role_to_give:
        await interaction.response.send_message(f"Roli `{platform.name}` nuk u gjet. Ju lutem kontaktoni një administrator.", ephemeral=True)
        return
        
    try:
        await member.add_roles(role_to_give)
        await interaction.response.send_message(f"Roli **{role_to_give.name}** iu dha anëtarit **{member.name}** me sukses.", ephemeral=True)
        try:
            await member.send(f"Përshëndetje! Roli juaj **{role_to_give.name}** u verifikua dhe u dha në serverin **{interaction.guild.name}**! Faleminderit për mbështetjen!")
        except discord.Forbidden:
            pass # Nuk mund të dërgoj mesazh privat, por roli u dha gjithsesi.
    except discord.Forbidden:
        await interaction.response.send_message("Nuk kam leje për të dhënë këtë rol. Ju lutem kontrolloni lejet e mia.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Ndodhi një gabim: {e}", ephemeral=True)

# KOMANDAT E STW
#----------------------------------------------------
@tree.command(name="stw-info", description="Shfaq informacion rreth misioneve aktuale në Save the World.")
async def stw_info_command(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        response = requests.get(FORTNITE_STW_API, params={'language': 'sq'})
        response.raise_for_status()
        data = response.json().get('data', [])
        
        embed = discord.Embed(
            title="Misionet e Save the World",
            description="Misionet aktuale të lojës, përfshirë ato me V-Bucks dhe Gjim-XP!",
            color=discord.Color.orange()
        )
        
        vbucks_missions = [
            mission for mission in data if "vbucks" in mission.get('rewards', {}) and mission.get('rewards', {}).get('vbucks')
        ]
        
        xp_missions = [
            mission for mission in data if "xp" in mission.get('rewards', {}) and mission.get('rewards', {}).get('xp')
        ]
        
        if vbucks_missions:
            vbucks_list = "\n".join([f"**{m['mission']['name']}** - {m['rewards']['vbucks']} V-Bucks" for m in vbucks_missions])
            embed.add_field(name="Misionet me V-Bucks:", value=vbucks_list, inline=False)
        
        if xp_missions:
            xp_list = "\n".join([f"**{m['mission']['name']}** - {m['rewards']['xp']} Gjim-XP" for m in xp_missions])
            embed.add_field(name="Misionet me Gjim-XP:", value=xp_list, inline=False)

        if not vbucks_missions and not xp_missions:
            embed.add_field(name="Misionet e Ditës", value="Asnjë mision i veçantë nuk u gjet aktualisht.", inline=False)
        
        await interaction.followup.send(embed=embed)
    except requests.exceptions.RequestException:
        await interaction.followup.send("Nuk mund të lidhem me API-në e Fortnite. Ju lutemi provoni përsëri më vonë.")

# KOMANDAT E INFORMACIONIT TE SERVERIT
#----------------------------------------------------
@tree.command(name="online", description="Shfaq numrin e anëtarëve online.")
async def online_command(interaction: discord.Interaction):
    online_members = [member for member in interaction.guild.members if member.status != discord.Status.offline]
    total_members = len(interaction.guild.members)
    online_count = len(online_members)
    
    embed = discord.Embed(
        title="Statusi i anëtarëve",
        description=f"Anëtarë online: **{online_count}**\nAnëtarë total: **{total_members}**",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)
    
# KOMANDAT E SISTEMIT TË PIKËVE
#----------------------------------------------------
@tree.command(name="xp", description="Shfaq pikët dhe nivelin tënd aktual.")
async def xp_command(interaction: discord.Interaction):
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    user_id = str(interaction.user.id)
    if user_id not in users or "xp" not in users[user_id]:
        await interaction.response.send_message("Nuk ke pikë akoma! Fillo duke shkruar mesazhe.", ephemeral=True)
        return
        
    xp = users[user_id]["xp"]
    level = get_level(xp)
    xp_for_next_level = get_required_xp(level + 1)
    
    embed = discord.Embed(
        title=f"Statistikat e XP për {interaction.user.name}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Niveli Aktual", value=f"**{level}**", inline=True)
    embed.add_field(name="Pikët Totale", value=f"**{xp} XP**", inline=True)
    embed.add_field(name="Për Nivelin Tjetër", value=f"**{xp_for_next_level - xp} XP** më shumë", inline=False)
    
    await interaction.response.send_message(embed=embed)

@tree.command(name="leaderboard", description="Shfaq listën e 10 anëtarëve me më shumë pikë.")
async def leaderboard_command(interaction: discord.Interaction):
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    
    sorted_users = sorted(users.items(), key=lambda item: item[1].get("xp", 0), reverse=True)
    
    embed = discord.Embed(
        title="Klasifikimi i Anëtarëve",
        description="Top 10 anëtarët me më shumë pikë XP!",
        color=discord.Color.red()
    )
    
    for rank, (user_id, user_data) in enumerate(sorted_users[:10], start=1):
        try:
            member = await interaction.guild.fetch_member(int(user_id))
            name = member.name
        except:
            name = "Përdorues i larguar"
        
        xp = user_data.get("xp", 0)
        level = get_level(xp)
        
        embed.add_field(name=f"#{rank}. {name}", value=f"Niveli: **{level}** | Pikë: **{xp} XP**", inline=False)
    
    await interaction.response.send_message(embed=embed)

# KOMANDAT E KËRKIMIT TË LOJTARËVE
#----------------------------------------------------
@tree.command(name="lf-game", description="Kërkon lojtarë për të luajtur një lojë.")
@discord.app_commands.describe(game="Emri i lojës", players="Numri i lojtarëve që kërkon (maksimumi 9)")
async def lfg_command(interaction: discord.Interaction, game: str, players: int):
    if players < 1 or players > 9:
        await interaction.response.send_message("Numri i lojtarëve duhet të jetë nga 1 deri në 9.", ephemeral=True)
        return
        
    lfg_channel = client.get_channel(LFG_CHANNEL_ID)
    if not lfg_channel:
        await interaction.response.send_message("Kanali i kërkimit të lojtarëve (LFG) nuk u gjet. Ju lutemi kontaktoni administratorin.", ephemeral=True)
        return
        
    embed = discord.Embed(
        title=f"Kërkohet lojtar për **{game}**!",
        description=f"**{interaction.user.name}** po kërkon {players} lojtarë të tjerë.",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=interaction.user.avatar.url)
    
    view = LFGView(creator_id=interaction.user.id, game=game, players_needed=players)
    await lfg_channel.send(f"{interaction.user.mention} po kërkon lojtarë!", embed=embed, view=view)
    await interaction.response.send_message("Kërkesa juaj u dërgua me sukses!", ephemeral=True)

# KOMANDË E VECANTË PËR SINKRONIZIMIN
@tree.command(name="sync", description="Sinkronizon të gjitha komandat me Discord-in. Vetëm për pronarin.")
@discord.app_commands.default_permissions(administrator=True)
async def sync_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        await tree.sync()
        await interaction.followup.send("Komandat u sinkronizuan me sukses.")
    except Exception as e:
        await interaction.followup.send(f"Gabim gjatë sinkronizimit: {e}")

client.run(MTQxMDc0MzU0OTAxNTg4ODA2NA.G0oxWM.HjdFNC07xMxJyoqGbxptEkm1auO38kEHGXiKJc)
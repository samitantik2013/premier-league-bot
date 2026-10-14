"""Discord football league bot. Configure DISCORD_TOKEN in Railway variables."""
from __future__ import annotations

import os
import random
import sqlite3
import time
import unicodedata
from datetime import datetime, timezone

import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", ".")
DB_PATH = os.getenv("DATABASE_PATH", "football_bot.sqlite3")
MATCH_ROLE = 1553136364789309552
MANAGER_ROLE = 1553136374637535323
TD_ROLE = 1553136397102227588
KAP_CHANNEL = 1553137059726762176
STAT_LOG_CHANNEL = 1556078549176426546
CARD_ROLE = MATCH_ROLE
FIX_ROLE = 1559864470715760702
STATS_ROLE = 1559864880595468298

TEAMS = {
    "manchestercity": "Manchester City", "liverpool": "Liverpool",
    "astonvilla": "Aston Villa", "everton": "Everton",
    "crystalpalace": "Crystal Palace", "arsenal": "Arsenal",
    "manchesterunited": "Manchester United", "tottenham": "Tottenham",
    "chelsea": "Chelsea",
}
ALIASES = {"mancity": "manchestercity", "city": "manchestercity", "astonvila": "astonvilla",
           "manutd": "manchesterunited", "mu": "manchesterunited", "spurs": "tottenham",
           "cp": "crystalpalace"}
POSITIONS = ["GK", "RB", "CB", "CB", "LB", "CDM", "CM", "CAM", "RW", "ST", "LW"]
ATTRS = ["bitiricilik", "dribbling", "kisa_pas", "uzun_pas", "ara_pasi", "sut", "top_kapma", "hiz", "fizik", "refleks"]
POSITION_NAMES = {
    "sagbek": "Sağ Bek", "solbek": "Sol Bek", "stoper": "Stoper", "kaleci": "Kaleci",
    "ortasaha": "Orta Saha", "defansifortasaha": "Defansif Orta Saha",
    "ofansifortasaha": "Ofansif Orta Saha", "solkanat": "Sol Kanat",
    "sagkanat": "Sağ Kanat", "santrafor": "Santrafor",
}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

def db(sql, params=(), fetch=False):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, params)
        rows = cur.fetchall() if fetch else cur.rowcount
        con.commit()
        return rows

db("""CREATE TABLE IF NOT EXISTS players(user_id INTEGER PRIMARY KEY, name TEXT NOT NULL,
 team TEXT, position TEXT, stats TEXT NOT NULL DEFAULT '{}', silver TEXT DEFAULT '', gold TEXT DEFAULT '')""")
db("CREATE TABLE IF NOT EXISTS managers(team TEXT PRIMARY KEY, user_id INTEGER NOT NULL)")
db("CREATE TABLE IF NOT EXISTS lineups(team TEXT PRIMARY KEY, formation TEXT NOT NULL, slots TEXT NOT NULL, updated INTEGER NOT NULL)")
db("CREATE TABLE IF NOT EXISTS goals(user_id INTEGER PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0)")
db("CREATE TABLE IF NOT EXISTS assists(user_id INTEGER PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0)")
db("CREATE TABLE IF NOT EXISTS clean_sheets(user_id INTEGER PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0)")
db("CREATE TABLE IF NOT EXISTS training(user_id INTEGER PRIMARY KEY, normal INTEGER DEFAULT 0, silver INTEGER DEFAULT 0, gold INTEGER DEFAULT 0)")
db("CREATE TABLE IF NOT EXISTS cooldowns(user_id INTEGER, kind TEXT, stamp REAL, PRIMARY KEY(user_id,kind))")
db("CREATE TABLE IF NOT EXISTS match_usage(match_id TEXT, team TEXT, subs INTEGER DEFAULT 0, PRIMARY KEY(match_id,team))")
db("CREATE TABLE IF NOT EXISTS rankings(user_id INTEGER PRIMARY KEY, goals INTEGER DEFAULT 0, assists INTEGER DEFAULT 0, clean_sheets INTEGER DEFAULT 0)")
db("CREATE TABLE IF NOT EXISTS ranking_events(user_id INTEGER NOT NULL, kind TEXT NOT NULL, created REAL NOT NULL)")
db("CREATE TABLE IF NOT EXISTS kap_claims(user_id INTEGER PRIMARY KEY, normal INTEGER DEFAULT 0, silver INTEGER DEFAULT 0, gold INTEGER DEFAULT 0, penalty INTEGER DEFAULT 0)")

def norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s.casefold()) if c.isalnum())

def team_key(value: str):
    k = ALIASES.get(norm(value), norm(value))
    return k if k in TEAMS else None

def has_role(member, role_id):
    return any(r.id == role_id for r in getattr(member, "roles", [])) or getattr(member, "guild_permissions", None) and member.guild_permissions.administrator

async def deny(ctx, role_id):
    if not has_role(ctx.author, role_id):
        await ctx.reply("❌ Bu komut için gerekli rolün yok.", mention_author=False)
        return True
    return False

def player_row(user_id):
    rows = db("SELECT * FROM players WHERE user_id=?", (user_id,), True)
    return rows[0] if rows else None

def stat_value(user_id, table):
    rows = db(f"SELECT count FROM {table} WHERE user_id=?", (user_id,), True)
    return rows[0][0] if rows else 0

async def log_stats(guild, text):
    ch = guild.get_channel(STAT_LOG_CHANNEL) if guild else None
    if ch:
        await ch.send(text)

@bot.event
async def on_ready():
    for v in (AntSistemView,):
        bot.add_view(v())
    print(f"Bot aktif: {bot.user}")

@bot.command(name="yardim", aliases=["help"])
async def help_cmd(ctx):
    e = discord.Embed(title="⚽ Lig Botu Komutları", color=discord.Color.blurple())
    e.description = ("`.macbasla takım1 takım2` · `.tdata @kişi takım` · `.transfer @kişi eski takım yeni takım`\n"
      "`.takımadı` oyuncu listesi · `.livekadroguncelle takım [diziliş] [11 oyuncu/NPC]` · `.livekadro [takım]`\n"
      "`.degisikliktakım çıkan giren` · `.kap` · `.kart [@kişi]` kart görüntüle · `.kartolustur @kişi pozisyon [isim]` · `.fix @kişi +49 bitiricilik +49 dribbling`\n"
      "`.ekle @kişi nitelik miktar` · `.sil @kişi nitelik miktar` · `.siralama [haftalik]` · `.golkralligi/.asistkralligi/.kalecikralligi`\n"
      "`.antsistem` antrenman paneli")
    await ctx.send(embed=e)

@bot.command()
async def tdata(ctx, member: discord.Member, team: str):
    if await deny(ctx, TD_ROLE): return
    key = team_key(team)
    if not key: return await ctx.reply("Takım bulunamadı.")
    db("INSERT INTO managers(team,user_id) VALUES(?,?) ON CONFLICT(team) DO UPDATE SET user_id=excluded.user_id", (key, member.id))
    await ctx.send(f"✅ {member.mention}, **{TEAMS[key]}** takımının teknik direktörü oldu.")

@bot.command()
async def transfer(ctx, member: discord.Member, old_team: str, new_team: str):
    if await deny(ctx, TD_ROLE): return
    old, new = team_key(old_team), team_key(new_team)
    if not new: return await ctx.reply("Yeni takım bulunamadı.")
    if old and player_row(member.id):
        db("UPDATE players SET team=? WHERE user_id=?", (new, member.id))
    else:
        row = player_row(member.id)
        if not row: return await ctx.reply("Bu oyuncunun kartı yok. Önce `.kartolustur` kullan.")
        db("UPDATE players SET team=? WHERE user_id=?", (new, member.id))
    await ctx.send(f"🔁 {member.mention}: **{TEAMS[old] if old else 'Takımsız'} → {TEAMS[new]}**")

@bot.command(name="macbasla")
async def macbasla(ctx, first: str, second: str):
    if await deny(ctx, MATCH_ROLE): return
    a, b = team_key(first), team_key(second)
    if not a or not b or a == b: return await ctx.reply("İki farklı geçerli takım yaz. Örnek: `.macbasla liverpool arsenal`")
    players = db("SELECT user_id,team,name FROM players WHERE team IN (?,?)", (a,b), True)
    # Skill rolls use the player's average attributes; unregistered lineup slots use a balanced NPC.
    line = {a: [], b: []}
    for p in players: line[p["team"]].append(p)
    score = {a:0,b:0}; events=[]
    for minute in range(4, 90, random.randint(7, 12)):
        team = random.choice((a,b)); squad=line[team]
        if random.random() > .46: continue
        if squad:
            scorer=random.choice(squad); card=player_row(scorer["user_id"]); import json
            stats=json.loads(card["stats"]); skill=sum(stats.values())/max(1,len(stats))
            chance=max(.16,min(.62,.20+(skill-65)*.008))
            if random.random() < chance:
                score[team]+=1; db("INSERT INTO ranking_events(user_id,kind,created) VALUES(?,?,?)",(scorer["user_id"],"goal",time.time())); db("INSERT INTO goals(user_id,count) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET count=count+1", (scorer["user_id"],))
                db("INSERT INTO rankings(user_id,goals) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET goals=goals+1", (scorer["user_id"],))
                assists=[x for x in squad if x["user_id"] != scorer["user_id"]]
                assist_note=""
                if assists and random.random()<.72:
                    assistant=random.choice(assists); db("INSERT INTO ranking_events(user_id,kind,created) VALUES(?,?,?)",(assistant["user_id"],"assist",time.time())); db("INSERT INTO assists(user_id,count) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET count=count+1", (assistant["user_id"],))
                    db("INSERT INTO rankings(user_id,assists) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET assists=assists+1", (assistant["user_id"],))
                    assist_note=f" · Asist: **{assistant['name']}**"
                events.append(f"`{minute}'` ⚽ **{scorer['name']}** ({TEAMS[team]}){assist_note}")
            else: events.append(f"`{minute}'` 🧤 Kaleci kurtardı! ({TEAMS[team]})")
        elif random.random()<.24:
            score[team]+=1; events.append(f"`{minute}'` ⚽ **NPC oyuncu** ({TEAMS[team]})")
        else: events.append(f"`{minute}'` ⚡ Tehlikeli atak, savunma uzaklaştırdı ({TEAMS[team]})")
    e=discord.Embed(title=f"🏟️ {TEAMS[a]} - {TEAMS[b]}", description=f"## {score[a]} - {score[b]}\n\n"+("\n".join(events) if events else "Maçta gol olmadı."), color=discord.Color.dark_green())
    e.set_footer(text="90' • Maç tamamlandı")
    await ctx.send(embed=e)
    await log_stats(ctx.guild, f"🏟️ {TEAMS[a]} {score[a]}–{score[b]} {TEAMS[b]} | Maç {ctx.message.id}")

class KapModal(discord.ui.Modal, title="KAP Başvurusu"):
    message = discord.ui.TextInput(label="Mesajın", style=discord.TextStyle.paragraph, max_length=1500, placeholder="Mesajını buraya yaz...")
    async def on_submit(self, interaction: discord.Interaction):
        channel=interaction.guild.get_channel(KAP_CHANNEL) if interaction.guild else None
        if not channel: return await interaction.response.send_message("Başvuru kanalı bulunamadı.", ephemeral=True)
        e=discord.Embed(title="📨 Yeni KAP Mesajı", description=self.message.value, color=discord.Color.orange())
        e.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        await channel.send(embed=e)
        await interaction.response.send_message("Mesajın iletildi.", ephemeral=True)

@bot.command()
async def kap(ctx):
    if await deny(ctx, TD_ROLE): return
    await ctx.send("KAP mesajı yazmak için butona bas:", view=KapOpenView())

class KapOpenView(discord.ui.View):
    def __init__(self): super().__init__(timeout=300)
    @discord.ui.button(label="Mesaj yaz", style=discord.ButtonStyle.primary, emoji="✍️")
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_role(interaction.user, TD_ROLE):
            return await interaction.response.send_message("Bu formu açma yetkin yok.", ephemeral=True)
        await interaction.response.send_modal(KapModal())

@bot.command(name="kartolustur")
async def kartolustur(ctx, member: discord.Member, *, details: str = ""):
    if await deny(ctx, CARD_ROLE): return
    parts=details.strip().split(maxsplit=1)
    position_key=norm(parts[0]) if parts else ""
    if position_key not in POSITION_NAMES:
        choices=" · ".join(POSITION_NAMES.values())
        return await ctx.reply(f"Pozisyon seçmelisin. Kullanım: `.kartolustur @kişi sagbek [oyuncu adı]`\nPozisyonlar: {choices}")
    position=POSITION_NAMES[position_key]
    name=(parts[1].strip() if len(parts)>1 else "") or member.display_name
    if player_row(member.id): return await ctx.reply("Bu oyuncunun kartı zaten var.")
    stats={attr:50 for attr in ATTRS}
    import json
    db("INSERT INTO players(user_id,name,position,stats) VALUES(?,?,?,?)", (member.id,name,position,json.dumps(stats,ensure_ascii=False)))
    await ctx.send(f"🪪 {member.mention} için **{name}** kartı oluşturuldu. Pozisyon: **{position}** · GEN: **50**")

@bot.command(name="fix")
async def fix(ctx, member: discord.Member, *, changes: str):
    if await deny(ctx, FIX_ROLE): return
    import json, re
    row=player_row(member.id)
    if not row: return await ctx.reply("Oyuncu kartı bulunamadı.")
    stats=json.loads(row["stats"]); pairs=re.findall(r"\+?(\d+)\s+([\wçğıöşüÇĞİÖŞÜ]+)", changes.casefold())
    if not pairs: return await ctx.reply("Örnek: `.fix @kişi +49 bitiricilik +49 dribbling`")
    updated=[]
    for amount,key in pairs:
        key=key.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
        aliases={"bitiricilik":"bitiricilik","dribbling":"dribbling","pas":"kisa_pas","kisapas":"kisa_pas","uzunpas":"uzun_pas","arapasi":"ara_pasi","sut":"sut","topkapma":"top_kapma","hiz":"hiz","fizik":"fizik","refleks":"refleks"}
        k=aliases.get(key)
        if k:
            stats[k]=min(99, max(1, stats.get(k,65)+int(amount))); updated.append(f"{k}: {stats[k]}")
    if not updated: return await ctx.reply("Nitelik adlarını tanıyamadım.")
    vals=list(stats.values()); avg=sum(vals)/len(vals)
    db("UPDATE players SET stats=? WHERE user_id=?",(json.dumps(stats,ensure_ascii=False),member.id))
    await ctx.send(f"✅ **{row['name']}** kartı güncellendi · GEN **{round(avg)}** · Pozisyon **{row['position'] or 'Belirlenmedi'}**\n"+" · ".join(updated))

@bot.command(name="kart", aliases=["s"])
async def show_card(ctx, member: discord.Member = None):
    member = member or ctx.author
    row=player_row(member.id)
    if not row: return await ctx.reply("Kart bulunamadı.")
    import json
    stats=json.loads(row["stats"]); e=discord.Embed(title=f"🪪 {row['name']}", color=discord.Color.blue())
    e.add_field(name="Pozisyon",value=row["position"] or "Belirlenmedi",inline=True)
    e.add_field(name="GEN",value=str(round(sum(stats.values())/max(1,len(stats)))),inline=True)
    e.add_field(name="Takım",value=TEAMS.get(row["team"],"Takımsız"),inline=True)
    e.add_field(name="Nitelikler",value="\n".join(f"{k.replace('_',' ').title()}: **{v}**" for k,v in stats.items()),inline=False)
    e.add_field(name="Kariyer",value=f"Gol {stat_value(member.id,'goals')} · Asist {stat_value(member.id,'assists')} · Clean sheet {stat_value(member.id,'clean_sheets')}",inline=False)
    await ctx.send(embed=e)

@bot.command()
async def ekle(ctx, member: discord.Member, attribute: str, amount: int):
    if await deny(ctx, STATS_ROLE): return
    await change_stat(ctx,member,attribute,amount)

@bot.command()
async def sil(ctx, member: discord.Member, attribute: str, amount: int):
    if await deny(ctx, STATS_ROLE): return
    await change_stat(ctx,member,attribute,-amount)

async def change_stat(ctx,member,attribute,delta):
    import json
    row=player_row(member.id)
    if not row: return await ctx.reply("Kart bulunamadı.")
    key=attribute.casefold().replace("-","_").replace(" ","_")
    if key not in ATTRS: return await ctx.reply("Nitelik: "+", ".join(ATTRS))
    stats=json.loads(row["stats"]); stats[key]=max(1,min(99,stats.get(key,65)+delta))
    db("UPDATE players SET stats=? WHERE user_id=?",(json.dumps(stats,ensure_ascii=False),member.id))
    await ctx.send(f"✅ {member.mention} · {key}: **{stats[key]}**")
    await log_stats(ctx.guild,f"📊 {ctx.author} → {member} · {key} {delta:+d} (yeni: {stats[key]})")

@bot.command(name="livekadroguncelle")
async def lineup_update(ctx, team: str, formation: str="4-3-3", *, players: str=""):
    key=team_key(team)
    if not key: return await ctx.reply("Takım bulunamadı.")
    managers=db("SELECT user_id FROM managers WHERE team=?",(key,),True)
    is_manager=managers and managers[0][0]==ctx.author.id
    if not is_manager and not has_role(ctx.author,MANAGER_ROLE): return await ctx.reply("Bu takımın teknik direktörü veya kadro yöneticisi olmalısın.")
    slots=[x.strip() for x in players.split(",") if x.strip()][:11]
    slots += ["NPC"]*(11-len(slots))
    db("INSERT INTO lineups(team,formation,slots,updated) VALUES(?,?,?,?) ON CONFLICT(team) DO UPDATE SET formation=excluded.formation,slots=excluded.slots,updated=excluded.updated",(key,formation,", ".join(slots),int(time.time())))
    await ctx.send(f"✅ **{TEAMS[key]}** kadrosu kaydedildi · `{formation}`\n"+"\n".join(f"{i+1}. {p}" for i,p in enumerate(slots)))

@bot.command(name="livekadro")
async def lineup_show(ctx, team: str=""):
    key=team_key(team) if team else None
    rows=db("SELECT * FROM lineups WHERE team=?" if key else "SELECT * FROM lineups ORDER BY updated DESC LIMIT 1",(key,) if key else (),True)
    if not rows: return await ctx.reply("Henüz kaydedilmiş kadro yok.")
    row=rows[0]; await ctx.send(embed=discord.Embed(title=f"🧩 {TEAMS[row['team']]} · {row['formation']}",description="\n".join(f"{i+1}. {p}" for i,p in enumerate(row['slots'].split(", "))),color=discord.Color.green()))

async def make_sub(ctx,key,outgoing,incoming):
    managers=db("SELECT user_id FROM managers WHERE team=?",(key,),True)
    if not has_role(ctx.author,MANAGER_ROLE) and not (managers and managers[0][0]==ctx.author.id):
        return await ctx.reply("Bu komut için takım direktörü veya kadro yöneticisi rolü gerekli.")
    rows=db("SELECT * FROM lineups WHERE team=?",(key,),True)
    if not rows: return await ctx.reply("Önce kadro kaydedilmeli.")
    match_id=str(ctx.channel.id)+":"+str(ctx.message.created_at.date())
    used=db("SELECT subs FROM match_usage WHERE match_id=? AND team=?",(match_id,key),True)
    n=used[0][0] if used else 0
    if n>=5: return await ctx.reply("Bu maçta takımın 5 değişiklik hakkı doldu.")
    slots=rows[0]["slots"].split(", ")
    if outgoing not in slots: return await ctx.reply("Çıkan oyuncu kadroda görünmüyor.")
    if incoming in slots and incoming!="NPC": return await ctx.reply("Giren oyuncu zaten kadroda.")
    slots[slots.index(outgoing)]=incoming
    db("UPDATE lineups SET slots=?,updated=? WHERE team=?",(", ".join(slots),int(time.time()),key))
    db("INSERT INTO match_usage(match_id,team,subs) VALUES(?,?,1) ON CONFLICT(match_id,team) DO UPDATE SET subs=subs+1",(match_id,key))
    await ctx.send(f"🔄 **{TEAMS[key]}**: {outgoing} ⬅️ {incoming} · değişiklik `{n+1}/5`")

for _key in TEAMS:
    async def _sub_cmd(ctx, outgoing: str, incoming: str, _k=_key):
        await make_sub(ctx, _k, outgoing, incoming)
    bot.command(name="degisiklik" + _key)(_sub_cmd)

def team_command(key):
    async def show(ctx):
        rows=db("SELECT user_id,name FROM players WHERE team=? ORDER BY name",(key,),True)
        if not rows: return await ctx.reply(f"{TEAMS[key]} kadrosunda kayıtlı oyuncu yok.")
        pages=[rows[i:i+10] for i in range(0,len(rows),10)]
        embeds=[]
        for page_no,page in enumerate(pages,1):
            e=discord.Embed(title=f"⚽ {TEAMS[key]} Oyuncuları",description="\n".join(f"{i+(page_no-1)*10+1}. <@{r['user_id']}> · **{r['name']}**" for i,r in enumerate(page)),color=discord.Color.blue())
            e.set_footer(text=f"Sayfa {page_no}/{len(pages)}")
            embeds.append(e)
        if len(embeds)==1: return await ctx.send(embed=embeds[0])
        await ctx.send(embed=embeds[0],view=Paginator(embeds,ctx.author.id))
    return show

class Paginator(discord.ui.View):
    def __init__(self,embeds,user_id): super().__init__(timeout=180); self.embeds=embeds; self.index=0; self.user_id=user_id
    async def interaction_check(self,interaction):
        if interaction.user.id!=self.user_id: await interaction.response.send_message("Bu sayfalama komutu sana ait değil.",ephemeral=True); return False
        return True
    @discord.ui.button(label="◀",style=discord.ButtonStyle.secondary)
    async def prev(self,interaction,button): self.index=(self.index-1)%len(self.embeds); await interaction.response.edit_message(embed=self.embeds[self.index],view=self)
    @discord.ui.button(label="▶",style=discord.ButtonStyle.secondary)
    async def next(self,interaction,button): self.index=(self.index+1)%len(self.embeds); await interaction.response.edit_message(embed=self.embeds[self.index],view=self)

for _key in TEAMS:
    async def _team_cmd(ctx,_k=_key): await team_command(_k)(ctx)
    bot.command(name=_key)(_team_cmd)

@bot.command(name="golkralligi",aliases=["gol"]) 
async def goals(ctx): await leaderboard(ctx,"goals","⚽ Gol Krallığı")
@bot.command(name="asistkralligi",aliases=["asist"]) 
async def assists_cmd(ctx): await leaderboard(ctx,"assists","🅰️ Asist Krallığı")
@bot.command(name="kalecikralligi",aliases=["clean-sheet","temizsayfa"]) 
async def clean(ctx): await leaderboard(ctx,"clean_sheets","🧤 Clean Sheet Sıralaması")

@bot.command(name="siralama", aliases=["sıralama", "ranking"])
async def siralama(ctx, period: str = "genel"):
    """Show combined player ranking: .siralama or .siralama haftalik."""
    period=period.casefold()
    if period in ("haftalık", "weekly", "haftalik"):
        since=time.time()-7*24*60*60
        rows=db("SELECT user_id, SUM(CASE WHEN kind='goal' THEN 3 WHEN kind='assist' THEN 2 ELSE 0 END) AS points, SUM(kind='goal') AS goals, SUM(kind='assist') AS assists FROM ranking_events WHERE created>=? GROUP BY user_id ORDER BY points DESC, goals DESC LIMIT 20",(since,),True)
        title="📅 Haftalık Oyuncu Sıralaması"
    elif period in ("genel", "all", "alltime", "tumu", "tümü"):
        rows=db("SELECT user_id, goals*3+assists*2+clean_sheets AS points, goals, assists, clean_sheets FROM rankings WHERE goals+assists+clean_sheets>0 ORDER BY points DESC, goals DESC LIMIT 20",fetch=True)
        title="🏆 Genel Oyuncu Sıralaması"
    else:
        return await ctx.reply("Kullanım: `.siralama` (genel) veya `.siralama haftalik`")
    if not rows: return await ctx.reply("Bu dönem için henüz sıralama verisi yok.")
    lines=[]
    for i,r in enumerate(rows,1):
        extra=f"Gol {r['goals']} · Asist {r['assists']}"
        if 'clean_sheets' in r.keys(): extra+=f" · Clean sheet {r['clean_sheets']}"
        lines.append(f"**{i}.** <@{r['user_id']}> — **{r['points']} puan** ({extra})")
    e=discord.Embed(title=title,description="\n".join(lines),color=discord.Color.gold())
    e.set_footer(text="Gol: 3 puan · Asist: 2 puan · Clean sheet: 1 puan")
    await ctx.send(embed=e)

async def leaderboard(ctx,field,title):
    if await deny(ctx,STATS_ROLE): return
    rows=db(f"SELECT user_id,{field} AS n FROM rankings WHERE {field}>0 ORDER BY {field} DESC LIMIT 20",fetch=True)
    if not rows: return await ctx.reply("Henüz istatistik yok.")
    await ctx.send(embed=discord.Embed(title=title,description="\n".join(f"**{i}.** <@{r['user_id']}> — **{r['n']}**" for i,r in enumerate(rows,1)),color=discord.Color.gold()))

# Training panel adapted from the supplied snippet. Progress and cooldowns persist in SQLite.
def ant_panel_embed():
    e=discord.Embed(title="🏋️ ANTRENMAN MERKEZİ",description="Antrenmanını seç ve ilerleme ödüllerini aç.",color=discord.Color.blurple())
    e.add_field(name="🏋️ Antrenman",value="Her 1 saatte bir · 10/10 olunca 10 nitelik hakkı",inline=False)
    e.add_field(name="🥈 Gümüş beceri",value="Her 30 dakikada bir · 50/50 olunca gümüş beceri seçimi",inline=False)
    e.add_field(name="🥇 Altın beceri",value="Her 30 dakikada bir · 100/100 olunca altın beceri seçimi",inline=False)
    e.add_field(name="⚽ Penaltı",value="Her 1 saatte bir · Gol olursa 5 nitelik hakkı",inline=False)
    e.set_footer(text="Premier Support • Antrenman Sistemi"); return e

def training_data(uid):
    rows=db("SELECT * FROM training WHERE user_id=?",(uid,),True)
    if rows: return rows[0]
    db("INSERT OR IGNORE INTO training(user_id) VALUES(?)",(uid,)); return db("SELECT * FROM training WHERE user_id=?",(uid,),True)[0]

def cooldown(uid,kind,seconds):
    rows=db("SELECT stamp FROM cooldowns WHERE user_id=? AND kind=?",(uid,kind),True)
    remain=seconds-(time.time()-rows[0][0]) if rows else 0
    return max(0,int(remain))

class AntSistemView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    async def train(self,interaction,kind,maximum,seconds,label,emoji):
        uid=interaction.user.id; remain=cooldown(uid,kind,seconds)
        if remain: return await interaction.response.send_message(f"⏳ Tekrar kullanmak için {remain//60} dakika {remain%60} saniye bekle.",ephemeral=True)
        data=training_data(uid); current=data[kind]
        if current>=maximum: return await interaction.response.send_message(f"🎉 İlerlemen zaten {maximum}/{maximum}.",ephemeral=True)
        current+=1; db(f"UPDATE training SET {kind}=? WHERE user_id=?",(current,uid)); db("INSERT INTO cooldowns(user_id,kind,stamp) VALUES(?,?,?) ON CONFLICT(user_id,kind) DO UPDATE SET stamp=excluded.stamp",(uid,kind,time.time()))
        await interaction.response.send_message(f"{emoji} İlerleme: **{current}/{maximum}**"+(" · Ödül hakkı kazandın!" if current==maximum else ""),ephemeral=True)
        channel=interaction.guild.get_channel(int(os.getenv("ANT_KANAL_ID","0"))) if interaction.guild else None
        if channel:
            bar="🟩"*(current*10//maximum)+"⬜"*(10-current*10//maximum)
            await channel.send(embed=discord.Embed(title=f"{emoji} {label}",description=f"{interaction.user.mention}\n{bar}\n**İlerleme:** `{current}/{maximum}`",color=discord.Color.blue()))
    @discord.ui.button(label="🏋️ Antrenman",style=discord.ButtonStyle.primary,custom_id="ant_normal")
    async def normal(self,i,b): await self.train(i,"normal",10,3600,"ANTRENMAN İLERLEMESİ","🏋️")
    @discord.ui.button(label="🥈 Gümüş Beceri",style=discord.ButtonStyle.secondary,custom_id="ant_gumus")
    async def gumus(self,i,b): await self.train(i,"silver",50,1800,"GÜMÜŞ BECERİ İLERLEMESİ","🥈")
    @discord.ui.button(label="🥇 Altın Beceri",style=discord.ButtonStyle.success,custom_id="ant_altin")
    async def altin(self,i,b): await self.train(i,"gold",100,1800,"ALTIN BECERİ İLERLEMESİ","🥇")
    @discord.ui.button(label="⚽ Penaltı",style=discord.ButtonStyle.danger,custom_id="ant_penalti")
    async def penalti(self,i,b):
        remain=cooldown(i.user.id,"penalty",3600)
        if remain: return await i.response.send_message(f"⏳ {remain//60} dakika beklemelisin.",ephemeral=True)
        db("INSERT INTO cooldowns(user_id,kind,stamp) VALUES(?,?,?) ON CONFLICT(user_id,kind) DO UPDATE SET stamp=excluded.stamp",(i.user.id,"penalty",time.time()))
        goal=random.random()<.25; result="⚽ GOL!" if goal else random.choice(["🧤 KALECİ KURTARDI!","🥅 DİREK!","❌ AUT!"])
        channel=i.guild.get_channel(int(os.getenv("PEN_KANAL_ID",os.getenv("ANT_KANAL_ID","0")))) if i.guild else None
        if channel: await channel.send(embed=discord.Embed(title="⚽ PENALTI ANTRENMANI",description=f"{i.user.mention}\n## {result}",color=discord.Color.green() if goal else discord.Color.red()))
        await i.response.send_message(f"Penaltı sonucu: **{result}**"+(" · 5 nitelik hakkı kazandın!" if goal else ""),ephemeral=True)

@bot.command(name="antsistem",aliases=["antpanel"])
async def antsistem(ctx):
    allowed=int(os.getenv("ANT_SISTEM_KULLANICI_ID","0"))
    if allowed and ctx.author.id!=allowed: return await ctx.reply("Bu paneli kullanma yetkin yok.",delete_after=5)
    await ctx.send(embed=ant_panel_embed(),view=AntSistemView())

@bot.event
async def on_command_error(ctx,error):
    if isinstance(error,commands.CommandNotFound): return
    if isinstance(error,commands.MissingRequiredArgument): return await ctx.reply(f"Eksik bilgi. Kullanım: `{PREFIX}yardim`",mention_author=False)
    if isinstance(error,commands.BadArgument): return await ctx.reply("Kullanıcıyı etiketle ve komut biçimini kontrol et.",mention_author=False)
    if isinstance(error,commands.CheckFailure): return await ctx.reply("Bu komutu kullanma yetkin yok.",mention_author=False)
    raise error

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN ortam değişkeni tanımlı değil. Railway Variables bölümüne ekle.")
    bot.run(TOKEN)

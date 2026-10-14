"""Football RP bot for Discord. Python 3.10+ / discord.py 2.x."""
import os
import json
import time
import random
import asyncio
import sqlite3
import unicodedata
from datetime import datetime, timezone

import discord
from discord.ext import commands

# Set DISCORD_TOKEN in Railway Variables. Never paste the token into this file.
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", ".")
DB_FILE = os.getenv("DATABASE_PATH", "football_rp.sqlite3")

# Server role and channel IDs supplied in the conversation.
MATCH_ROLE = 1553136364789309552
SQUAD_ROLE = 1553136374637535323
DIRECTOR_ROLE = 1553136397102227588
KAP_CHANNEL = 1553137059726762176
STAT_LOG_CHANNEL = 1556078549176426546
CARD_ROLE = MATCH_ROLE
FIX_ROLE = 1559864470715760702
STAT_ROLE = 1559864880595468298

TEAMS = {
    "manchestercity": "Manchester City", "liverpool": "Liverpool",
    "astonvilla": "Aston Villa", "everton": "Everton",
    "crystalpalace": "Crystal Palace", "arsenal": "Arsenal",
    "manchesterunited": "Manchester United", "tottenham": "Tottenham",
    "chelsea": "Chelsea",
}
TEAM_ALIASES = {"city": "manchestercity", "mancity": "manchestercity", "astonvila": "astonvilla",
                "manutd": "manchesterunited", "spurs": "tottenham", "mu": "manchesterunited"}
POSITIONS = {
    "sagbek": "Sağ Bek", "solbek": "Sol Bek", "stoper": "Stoper", "kaleci": "Kaleci",
    "ortasaha": "Orta Saha", "defansifortasaha": "Defansif Orta Saha",
    "ofansifortasaha": "Ofansif Orta Saha", "solkanat": "Sol Kanat",
    "sagkanat": "Sağ Kanat", "santrafor": "Santrafor",
}
ATTRIBUTES = ["bitiricilik", "dribbling", "kisa_pas", "uzun_pas", "ara_pasi", "sut", "top_kapma", "hiz", "fizik", "refleks"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)
active_matches = {}  # (guild_id, channel_id) -> in-memory live match

def connect():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con

def query(sql, params=(), one=False):
    with connect() as con:
        cur = con.execute(sql, params)
        result = cur.fetchone() if one else cur.fetchall()
        con.commit()
        return result

def setup_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS players(user_id INTEGER PRIMARY KEY, name TEXT NOT NULL, team TEXT, position TEXT NOT NULL, stats TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS managers(team TEXT PRIMARY KEY, user_id INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS lineups(team TEXT PRIMARY KEY, formation TEXT NOT NULL, players TEXT NOT NULL, updated INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS player_stats(user_id INTEGER PRIMARY KEY, goals INTEGER DEFAULT 0, assists INTEGER DEFAULT 0, clean_sheets INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, kind TEXT NOT NULL, created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS standings(team TEXT PRIMARY KEY, played INTEGER DEFAULT 0, won INTEGER DEFAULT 0, drawn INTEGER DEFAULT 0, lost INTEGER DEFAULT 0, gf INTEGER DEFAULT 0, ga INTEGER DEFAULT 0, points INTEGER DEFAULT 0);
        """)
setup_db()

def clean_key(text):
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.casefold()) if ch.isalnum())

def resolve_team(text):
    key = TEAM_ALIASES.get(clean_key(text), clean_key(text))
    return key if key in TEAMS else None

def is_staff(member, role_id):
    return bool(getattr(member, "guild_permissions", None) and member.guild_permissions.administrator) or any(r.id == role_id for r in getattr(member, "roles", []))

async def require(ctx, role_id):
    if not is_staff(ctx.author, role_id):
        await ctx.reply("Bu komut için gerekli rolün yok.", mention_author=False)
        return False
    return True

def get_player(user_id):
    return query("SELECT * FROM players WHERE user_id=?", (user_id,), one=True)

def get_stats(user_id):
    row = query("SELECT * FROM player_stats WHERE user_id=?", (user_id,), one=True)
    return row or {"goals": 0, "assists": 0, "clean_sheets": 0}

async def stat_log(guild, message):
    channel = guild.get_channel(STAT_LOG_CHANNEL) if guild else None
    if channel:
        await channel.send(message)

@bot.event
async def on_ready():
    print(f"Futbol RP botu hazır: {bot.user}")

@bot.command(name="yardim", aliases=["help", "komutlar"])
async def help_command(ctx):
    e = discord.Embed(title="⚽ FUTBOL RP • KOMUT REHBERİ", description="Komutların başında nokta kullan. Köşeli parantez içi bilgi isteğe bağlıdır.", color=discord.Color.blurple())
    e.add_field(name="🏟️ Maç ve lig", value="`.macbasla takım1 takım2` maç başlat\n`.puan` puan tablosu\n`.siralama [haftalik]` oyuncu sıralaması", inline=False)
    e.add_field(name="👥 Takım ve kadro", value="`.tdata @kişi takım` teknik direktör ata\n`.transfer @kişi eski takım yeni takım`\n`.livekadroguncelle takım diziliş oyuncu1, oyuncu2, ...`\n`.livekadro [takım]`\n`.degisikliktakım çıkan giren` maç sırasında değişiklik\n`.takımadı` takım oyuncuları", inline=False)
    e.add_field(name="🪪 Oyuncu RP", value="`.kartolustur @kişi pozisyon [oyuncu adı]`\n`.kart [@kişi]`\n`.fix @kişi +10 bitiricilik +5 hiz`\n`.ekle @kişi nitelik miktar` · `.sil @kişi nitelik miktar`", inline=False)
    e.add_field(name="📨 Diğer", value="`.kap` yetkili başvuru formu\n`.yardim` bu rehber", inline=False)
    e.set_footer(text="Canlı maçlar yaklaşık 20 saniyede oynanır. Maç sırasında değişiklik için ilgili komutu kullan.")
    await ctx.send(embed=e)

@bot.command(name="tdata")
async def set_manager(ctx, member: discord.Member, team: str):
    if not await require(ctx, DIRECTOR_ROLE): return
    key = resolve_team(team)
    if not key: return await ctx.reply("Takım tanınmadı. `.yardim` ile takım adlarına bak.")
    query("INSERT INTO managers(team,user_id) VALUES(?,?) ON CONFLICT(team) DO UPDATE SET user_id=excluded.user_id", (key, member.id))
    await ctx.send(f"✅ {member.mention}, **{TEAMS[key]}** teknik direktörü olarak atandı.")

@bot.command(name="transfer")
async def transfer(ctx, member: discord.Member, old_team: str, new_team: str):
    if not await require(ctx, DIRECTOR_ROLE): return
    new = resolve_team(new_team)
    if not new: return await ctx.reply("Yeni takım tanınmadı.")
    player = get_player(member.id)
    if not player: return await ctx.reply("Oyuncu kartı yok. Önce `.kartolustur` kullan.")
    old = resolve_team(old_team)
    if old and player["team"] and old != player["team"]:
        return await ctx.reply(f"Oyuncu şu anda {TEAMS.get(player['team'], 'takımsız')} takımında.")
    query("UPDATE players SET team=? WHERE user_id=?", (new, member.id))
    await ctx.send(f"🔁 **{player['name']}**: {TEAMS.get(old, 'Takımsız')} → **{TEAMS[new]}**")

@bot.command(name="kartolustur")
async def create_card(ctx, member: discord.Member, *, details: str = ""):
    if not await require(ctx, CARD_ROLE): return
    parts = details.strip().split(maxsplit=1)
    pos_key = clean_key(parts[0]) if parts else ""
    if pos_key not in POSITIONS:
        return await ctx.reply("Pozisyon seç: sagbek, solbek, stoper, kaleci, ortasaha, defansifortasaha, ofansifortasaha, solkanat, sagkanat veya santrafor.")
    if get_player(member.id): return await ctx.reply("Bu kullanıcının oyuncu kartı zaten var.")
    name = parts[1].strip() if len(parts) > 1 else member.display_name
    stats = {attr: 50 for attr in ATTRIBUTES}
    query("INSERT INTO players(user_id,name,position,stats) VALUES(?,?,?,?)", (member.id, name, POSITIONS[pos_key], json.dumps(stats, ensure_ascii=False)))
    query("INSERT OR IGNORE INTO player_stats(user_id) VALUES(?)", (member.id,))
    await ctx.send(f"🪪 {member.mention} için **{name}** kartı açıldı · **{POSITIONS[pos_key]}** · GEN **50**")

@bot.command(name="kart", aliases=["s"])
async def show_card(ctx, member: discord.Member = None):
    member = member or ctx.author
    player = get_player(member.id)
    if not player: return await ctx.reply("Oyuncu kartı bulunamadı.")
    stats = json.loads(player["stats"])
    overall = round(sum(stats.values()) / max(1, len(stats)))
    career = get_stats(member.id)
    e = discord.Embed(title=f"🪪 {player['name']}", color=discord.Color.blue())
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="GEN", value=f"**{overall}**", inline=True)
    e.add_field(name="Pozisyon", value=player["position"], inline=True)
    e.add_field(name="Takım", value=TEAMS.get(player["team"], "Takımsız"), inline=True)
    e.add_field(name="Nitelikler", value="\n".join(f"{k.replace('_',' ').title()}: **{v}**" for k,v in stats.items()), inline=False)
    e.add_field(name="Kariyer", value=f"⚽ {career['goals']} gol · 🅰️ {career['assists']} asist · 🧤 {career['clean_sheets']} clean sheet", inline=False)
    await ctx.send(embed=e)

@bot.command(name="fix")
async def fix_card(ctx, member: discord.Member, *, changes: str):
    if not await require(ctx, FIX_ROLE): return
    player = get_player(member.id)
    if not player: return await ctx.reply("Kart bulunamadı.")
    import re
    pairs = re.findall(r"\+?(\d+)\s+([\wçğıöşüÇĞİÖŞÜ]+)", changes.casefold())
    aliases = {"bitiricilik":"bitiricilik", "dribbling":"dribbling", "kisapas":"kisa_pas", "uzunpas":"uzun_pas", "arapasi":"ara_pasi", "sut":"sut", "topkapma":"top_kapma", "hiz":"hiz", "fizik":"fizik", "refleks":"refleks"}
    stats = json.loads(player["stats"]); changed=[]
    for amount, raw in pairs:
        key = clean_key(raw)
        key = aliases.get(key)
        if key:
            stats[key] = max(1, min(99, stats[key] + int(amount)))
            changed.append(f"{key.replace('_',' ')} {stats[key]}")
    if not changed: return await ctx.reply("Örnek: `.fix @kişi +10 bitiricilik +5 hiz`")
    query("UPDATE players SET stats=? WHERE user_id=?", (json.dumps(stats, ensure_ascii=False), member.id))
    overall = round(sum(stats.values()) / len(stats))
    await ctx.send(f"✅ **{player['name']}** güncellendi · GEN **{overall}** · " + " · ".join(changed))
    await stat_log(ctx.guild, f"📊 {ctx.author.mention}, {member.mention} kartını güncelledi: " + ", ".join(changed))

async def change_attribute(ctx, member, attribute, amount):
    player = get_player(member.id)
    if not player: return await ctx.reply("Kart bulunamadı.")
    key = clean_key(attribute)
    map_key = {clean_key(x.replace('_',' ')):x for x in ATTRIBUTES}
    key = map_key.get(key)
    if not key: return await ctx.reply("Nitelik tanınmadı. Örnek: bitiricilik, dribbling, kisa_pas, hiz.")
    stats = json.loads(player["stats"]); stats[key] = max(1, min(99, stats[key] + amount))
    query("UPDATE players SET stats=? WHERE user_id=?", (json.dumps(stats, ensure_ascii=False), member.id))
    await ctx.send(f"✅ {member.mention} · {key.replace('_',' ')} **{stats[key]}** · GEN **{round(sum(stats.values())/len(stats))}**")
    await stat_log(ctx.guild, f"📈 {member.mention}: {key} {amount:+d} → {stats[key]}")

@bot.command(name="ekle")
async def add_stat(ctx, member: discord.Member, attribute: str, amount: int):
    if await require(ctx, STAT_ROLE): await change_attribute(ctx, member, attribute, abs(amount))

@bot.command(name="sil")
async def remove_stat(ctx, member: discord.Member, attribute: str, amount: int):
    if await require(ctx, STAT_ROLE): await change_attribute(ctx, member, attribute, -abs(amount))

@bot.command(name="livekadroguncelle")
async def update_lineup(ctx, team: str, formation: str, *, members: str = ""):
    key = resolve_team(team)
    if not key: return await ctx.reply("Takım tanınmadı.")
    manager = query("SELECT user_id FROM managers WHERE team=?", (key,), one=True)
    if not is_staff(ctx.author, SQUAD_ROLE) and not (manager and manager["user_id"] == ctx.author.id):
        return await ctx.reply("Bu takımın teknik direktörü veya kadro yöneticisi olmalısın.")
    players = [p.strip() or "NPC" for p in members.split(",")][:11]
    players += ["NPC"] * (11-len(players))
    query("INSERT INTO lineups(team,formation,players,updated) VALUES(?,?,?,?) ON CONFLICT(team) DO UPDATE SET formation=excluded.formation,players=excluded.players,updated=excluded.updated", (key, formation, json.dumps(players, ensure_ascii=False), int(time.time())))
    await ctx.send(embed=lineup_embed(key, formation, players))

def lineup_embed(key, formation, players):
    e = discord.Embed(title=f"🧩 {TEAMS[key]} · {formation}", description="\n".join(f"**{i+1}.** {p}" for i,p in enumerate(players)), color=discord.Color.green())
    return e

@bot.command(name="livekadro")
async def show_lineup(ctx, team: str = ""):
    key = resolve_team(team) if team else None
    row = query("SELECT * FROM lineups WHERE team=?" if key else "SELECT * FROM lineups ORDER BY updated DESC LIMIT 1", (key,) if key else (), one=True)
    if not row: return await ctx.reply("Henüz kadro kaydedilmemiş.")
    await ctx.send(embed=lineup_embed(row["team"], row["formation"], json.loads(row["players"])))

def roster_for(team):
    saved = query("SELECT players FROM lineups WHERE team=?", (team,), one=True)
    if saved:
        return json.loads(saved["players"])
    rows = query("SELECT name FROM players WHERE team=? ORDER BY name LIMIT 11", (team,))
    result = [r["name"] for r in rows]
    return result + ["NPC"] * (11-len(result))

def name_rating(name):
    if name == "NPC": return 60
    row = query("SELECT stats FROM players WHERE name=? COLLATE NOCASE LIMIT 1", (name,), one=True)
    if not row: return 60
    attrs = json.loads(row["stats"])
    return sum(attrs.values()) / len(attrs)

def match_embed(match, final=False):
    e = discord.Embed(title=f"🏟️ {TEAMS[match['home']]} - {TEAMS[match['away']]}", color=discord.Color.gold() if final else discord.Color.dark_green())
    e.description = f"## {match['score'][match['home']]} - {match['score'][match['away']]}\n\n" + ("\n".join(match["events"][-12:]) or "Maç başladı, ilk düdük çaldı.")
    e.set_footer(text="Maç tamamlandı" if final else f"Canlı RP maçı · {match['minute']}'")
    return e

@bot.command(name="macbasla", aliases=["maçbaşlat"])
async def start_match(ctx, first: str, second: str):
    if not await require(ctx, MATCH_ROLE): return
    home, away = resolve_team(first), resolve_team(second)
    if not home or not away or home == away: return await ctx.reply("İki farklı geçerli takım yaz. Örnek: `.macbasla liverpool arsenal`")
    slot=(ctx.guild.id, ctx.channel.id)
    if slot in active_matches: return await ctx.reply("Bu kanalda zaten canlı bir maç var.")
    match={"home":home,"away":away,"score":{home:0,away:0},"squads":{home:roster_for(home),away:roster_for(away)},"subs":{home:0,away:0},"minute":0,"events":[]}
    active_matches[slot]=match
    message=await ctx.send(embed=match_embed(match))
    try:
        for minute in range(10, 91, 10):
            await asyncio.sleep(2)
            match["minute"]=minute
            team=random.choice([home,away]); opponent=away if team==home else home
            scorer=random.choice(match["squads"][team]); rating=name_rating(scorer)
            goal_chance=max(.13,min(.54,.24+(rating-60)*.008))
            if random.random()<goal_chance:
                match["score"][team]+=1
                text=f"`{minute}'` ⚽ **{scorer}** golü buldu! ({TEAMS[team]})"
                player=query("SELECT user_id FROM players WHERE name=? COLLATE NOCASE LIMIT 1",(scorer,),one=True)
                if player:
                    query("INSERT INTO player_stats(user_id,goals) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET goals=goals+1",(player["user_id"],))
                    query("INSERT INTO events(user_id,kind,created) VALUES(?,?,?)",(player["user_id"],"goal",int(time.time())))
                if random.random()<.62:
                    assists=[n for n in match["squads"][team] if n!=scorer and n!="NPC"]
                    if assists:
                        assister=random.choice(assists); text+=f" · Asist: **{assister}**"
                        player=query("SELECT user_id FROM players WHERE name=? COLLATE NOCASE LIMIT 1",(assister,),one=True)
                        if player:
                            query("INSERT INTO player_stats(user_id,assists) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET assists=assists+1",(player["user_id"],))
                            query("INSERT INTO events(user_id,kind,created) VALUES(?,?,?)",(player["user_id"],"assist",int(time.time())))
            else:
                text=f"`{minute}'` 🧤 {TEAMS[opponent]} savunması atağı durdurdu."
            match["events"].append(text)
            await message.edit(embed=match_embed(match))
        await message.edit(embed=match_embed(match, final=True))
        save_result(match)
        await stat_log(ctx.guild, f"🏟️ {TEAMS[home]} {match['score'][home]}–{match['score'][away]} {TEAMS[away]}")
    finally:
        active_matches.pop(slot,None)

def save_result(match):
    h,a=match["home"],match["away"]; hg,ag=match["score"][h],match["score"][a]
    for team in (h,a): query("INSERT OR IGNORE INTO standings(team) VALUES(?)",(team,))
    if hg>ag: results={h:(1,0,0,3),a:(0,0,1,0)}
    elif hg<ag: results={h:(0,0,1,0),a:(1,0,0,3)}
    else: results={h:(0,1,0,1),a:(0,1,0,1)}
    for team,gf,ga in ((h,hg,ag),(a,ag,hg)):
        w,d,l,p=results[team]
        query("UPDATE standings SET played=played+1,won=won+?,drawn=drawn+?,lost=lost+?,gf=gf+?,ga=ga+?,points=points+? WHERE team=?",(w,d,l,gf,ga,p,team))
        if ga==0:
            keepers=query("SELECT user_id FROM players WHERE team=? AND position='Kaleci'",(team,))
            for keeper in keepers:
                query("INSERT INTO player_stats(user_id,clean_sheets) VALUES(?,1) ON CONFLICT(user_id) DO UPDATE SET clean_sheets=clean_sheets+1",(keeper["user_id"],))
                query("INSERT INTO events(user_id,kind,created) VALUES(?,?,?)",(keeper["user_id"],"clean_sheet",int(time.time())))

async def substitute(ctx, team_key, outgoing, incoming):
    slot=(ctx.guild.id,ctx.channel.id); match=active_matches.get(slot)
    if not match or team_key not in (match["home"],match["away"]): return await ctx.reply("Bu kanalda o takımın canlı maçı yok.")
    manager=query("SELECT user_id FROM managers WHERE team=?",(team_key,),one=True)
    if not is_staff(ctx.author,SQUAD_ROLE) and not (manager and manager["user_id"]==ctx.author.id):
        return await ctx.reply("Bu takımın direktörü veya kadro yöneticisi olmalısın.")
    if match["subs"][team_key]>=5: return await ctx.reply("Bu maçta 5 değişiklik hakkı doldu.")
    squad=match["squads"][team_key]
    if outgoing not in squad: return await ctx.reply("Çıkan oyuncu sahadaki kadroda bulunamadı.")
    if incoming in squad and incoming!="NPC": return await ctx.reply("Girecek oyuncu zaten sahada.")
    squad[squad.index(outgoing)]=incoming; match["subs"][team_key]+=1
    await ctx.send(f"🔄 **{TEAMS[team_key]}** değişikliği: {outgoing} ⬅️ {incoming} · `{match['subs'][team_key]}/5`")

for _team in TEAMS:
    async def _sub_command(ctx, outgoing: str, incoming: str, _key=_team):
        await substitute(ctx,_key,outgoing,incoming)
    bot.command(name="degisiklik"+_team)(_sub_command)

class RosterPages(discord.ui.View):
    def __init__(self, pages, owner):
        super().__init__(timeout=180); self.pages=pages; self.owner=owner; self.index=0
    async def interaction_check(self, interaction):
        if interaction.user.id!=self.owner:
            await interaction.response.send_message("Bu sayfaları yalnızca komutu yazan kişi kullanabilir.",ephemeral=True); return False
        return True
    @discord.ui.button(label="◀",style=discord.ButtonStyle.secondary)
    async def previous(self,interaction,button):
        self.index=(self.index-1)%len(self.pages); await interaction.response.edit_message(embed=self.pages[self.index],view=self)
    @discord.ui.button(label="▶",style=discord.ButtonStyle.secondary)
    async def next(self,interaction,button):
        self.index=(self.index+1)%len(self.pages); await interaction.response.edit_message(embed=self.pages[self.index],view=self)

async def team_roster(ctx,key):
    rows=query("SELECT user_id,name,position FROM players WHERE team=? ORDER BY name",(key,))
    if not rows: return await ctx.reply(f"{TEAMS[key]} takımında kayıtlı oyuncu yok.")
    pages=[]
    for start in range(0,len(rows),10):
        batch=rows[start:start+10]
        e=discord.Embed(title=f"⚽ {TEAMS[key]} Oyuncuları",description="\n".join(f"**{i+start+1}.** <@{r['user_id']}> · {r['name']} — {r['position']}" for i,r in enumerate(batch)),color=discord.Color.blue())
        e.set_footer(text=f"Sayfa {len(pages)+1}/{(len(rows)+9)//10}"); pages.append(e)
    await ctx.send(embed=pages[0],view=RosterPages(pages,ctx.author.id) if len(pages)>1 else None)

for _team in TEAMS:
    async def _roster_command(ctx,_key=_team): await team_roster(ctx,_key)
    bot.command(name=_team)(_roster_command)

@bot.command(name="puan",aliases=["lig"])
async def points(ctx):
    rows=query("SELECT * FROM standings ORDER BY points DESC,(gf-ga) DESC,gf DESC")
    if not rows: return await ctx.reply("Puan tablosu için henüz maç oynanmadı.")
    body="`#  Takım                 O  G  B  M  AV  P`\n"+"\n".join(f"`{i:<2} {TEAMS[r['team']]:<20} {r['played']:>2} {r['won']:>2} {r['drawn']:>2} {r['lost']:>2} {r['gf']-r['ga']:>3} {r['points']:>2}`" for i,r in enumerate(rows,1))
    await ctx.send(embed=discord.Embed(title="🏆 RP Lig Tablosu",description=body,color=discord.Color.gold()))

@bot.command(name="siralama",aliases=["ranking"])
async def ranking(ctx, period="genel"):
    weekly=clean_key(period) in ("haftalik","weekly")
    since=int(time.time()-7*86400) if weekly else 0
    rows=query("SELECT user_id,SUM(CASE kind WHEN 'goal' THEN 3 WHEN 'assist' THEN 2 WHEN 'clean_sheet' THEN 1 ELSE 0 END) points FROM events WHERE created>=? GROUP BY user_id ORDER BY points DESC LIMIT 15",(since,))
    if not rows: return await ctx.reply("Bu dönem için sıralama verisi yok.")
    title="📅 Haftalık Oyuncu Sıralaması" if weekly else "🏅 Genel Oyuncu Sıralaması"
    text="\n".join(f"**{i}.** <@{r['user_id']}> — **{r['points']} puan**" for i,r in enumerate(rows,1))
    await ctx.send(embed=discord.Embed(title=title,description=text+"\n\nGol 3 · Asist 2 · Clean sheet 1 puan",color=discord.Color.gold()))

@bot.command(name="golkralligi")
async def top_scorers(ctx): await leaderboard(ctx,"goals","⚽ Gol Krallığı")
@bot.command(name="asistkralligi")
async def top_assists(ctx): await leaderboard(ctx,"assists","🅰️ Asist Krallığı")
@bot.command(name="kalecikralligi")
async def top_clean_sheets(ctx): await leaderboard(ctx,"clean_sheets","🧤 Kaleci Sıralaması")

async def leaderboard(ctx,field,title):
    rows=query(f"SELECT user_id,{field} n FROM player_stats WHERE {field}>0 ORDER BY {field} DESC LIMIT 15")
    if not rows: return await ctx.reply("Henüz istatistik yok.")
    await ctx.send(embed=discord.Embed(title=title,description="\n".join(f"**{i}.** <@{r['user_id']}> — {r['n']}" for i,r in enumerate(rows,1)),color=discord.Color.gold()))

class KapModal(discord.ui.Modal,title="Futbol RP • KAP Mesajı"):
    content=discord.ui.TextInput(label="Mesajın",style=discord.TextStyle.paragraph,max_length=1500,placeholder="Mesajını buraya yaz...")
    async def on_submit(self,interaction):
        channel=interaction.guild.get_channel(KAP_CHANNEL) if interaction.guild else None
        if not channel: return await interaction.response.send_message("KAP kanalı bulunamadı.",ephemeral=True)
        e=discord.Embed(title="📨 Yeni KAP Mesajı",description=self.content.value,color=discord.Color.orange())
        e.set_author(name=str(interaction.user),icon_url=interaction.user.display_avatar.url)
        await channel.send(embed=e); await interaction.response.send_message("Mesajın iletildi.",ephemeral=True)

class KapButton(discord.ui.View):
    @discord.ui.button(label="Mesaj yaz",style=discord.ButtonStyle.primary,emoji="✍️")
    async def open_modal(self,interaction,button):
        if not is_staff(interaction.user,DIRECTOR_ROLE): return await interaction.response.send_message("Bu formu kullanma yetkin yok.",ephemeral=True)
        await interaction.response.send_modal(KapModal())

@bot.command(name="kap")
async def kap(ctx):
    if await require(ctx,DIRECTOR_ROLE): await ctx.send("KAP mesajını yazmak için butona bas:",view=KapButton(timeout=300))

@bot.event
async def on_command_error(ctx,error):
    if isinstance(error,commands.CommandNotFound): return
    if isinstance(error,commands.MissingRequiredArgument): return await ctx.reply("Bilgi eksik. Komutları görmek için `.yardim` yaz.",mention_author=False)
    if isinstance(error,commands.BadArgument): return await ctx.reply("Kullanıcıyı etiketleyip komut biçimini kontrol et. `.yardim` yaz.",mention_author=False)
    if isinstance(error,commands.CommandOnCooldown): return await ctx.reply("Biraz bekleyip tekrar dene.",mention_author=False)
    raise error

if __name__ == "__main__":
    if not TOKEN: raise SystemExit("DISCORD_TOKEN ayarlanmamış. Railway → Variables bölümüne ekle.")
    bot.run(TOKEN)

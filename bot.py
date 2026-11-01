"""Turkish football statistics and moderation bot for discord.py 2.x."""

import asyncio
from datetime import timedelta
import os
import re
import sqlite3
from pathlib import Path

import discord
from discord.ext import commands


PREFIX = "."
DB_PATH = Path(os.getenv("DATABASE_PATH", "data/stats.sqlite3"))
MAX_PURGE = 100
MAX_MUTE_MINUTES = 28 * 24 * 60
ATTRIBUTES = {
    "Atak": ["Orta Açma", "Bitiricilik", "Kafa İsabeti", "Kısa Pas", "Voleler"],
    "Savunma": ["Ayakta Müdahale", "Kayarak Müdahale"],
    "Beceri": ["Dribbling", "Falso", "Serbest Vuruş İsabeti", "Uzun Pas", "Top Kontrolü"],
    "Güç": ["Şut Gücü", "Zıplama", "Dayanıklılık", "Güç", "Uzaktan Şut"],
    "Hareket": ["Hızlanma", "Sprint Hızı", "Çeviklik", "Reaksiyonlar", "Denge"],
    "Mentalite": ["Agresiflik", "Top Kesme", "Pozisyon Alma", "Görüş", "Penaltı"],
    "Kaleci": ["Kaleci Atlayışı", "Kaleci Top Kontrolü", "Kaleci Vuruşu", "Kaleci Pozisyon Alma", "Kaleci Refleksler"],
}
ATTRIBUTE_LOOKUP = {name.casefold(): name for names in ATTRIBUTES.values() for name in names}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.execute("PRAGMA busy_timeout = 15000")
    return connection


def init_db():
    with connect_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS stats (
            guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            weekly INTEGER NOT NULL DEFAULT 0 CHECK (weekly >= 0),
            total INTEGER NOT NULL DEFAULT 0 CHECK (total >= 0),
            PRIMARY KEY (guild_id, user_id))""")
        db.execute("""CREATE TABLE IF NOT EXISTS training (
            guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            attribute TEXT NOT NULL, amount INTEGER NOT NULL CHECK (amount > 0),
            PRIMARY KEY (guild_id, user_id, attribute))""")


def get_stats(guild_id, user_id):
    with connect_db() as db:
        row = db.execute("SELECT weekly, total FROM stats WHERE guild_id=? AND user_id=?",
                         (guild_id, user_id)).fetchone()
    return row or (0, 0)


def change_stats(guild_id, user_id, weekly=0, total=0):
    with connect_db() as db:
        current = db.execute("SELECT weekly, total FROM stats WHERE guild_id=? AND user_id=?",
                             (guild_id, user_id)).fetchone() or (0, 0)
        new_weekly, new_total = current[0] + weekly, current[1] + total
        if new_weekly < 0 or new_total < 0:
            raise ValueError("Bir istatistik sıfırın altına inemez.")
        db.execute("""INSERT INTO stats(guild_id,user_id,weekly,total) VALUES(?,?,?,?)
            ON CONFLICT(guild_id,user_id) DO UPDATE SET weekly=excluded.weekly,total=excluded.total""",
                   (guild_id, user_id, new_weekly, new_total))


def display_name(member):
    return discord.utils.escape_markdown(member.display_name)


async def confirm_everyone(ctx, action):
    await ctx.send(
        f"⚠️ **Toplu {action} onayı**: Bu sunucudaki kayıtlı herkes etkilenecek. "
        f"Devam etmek için 30 saniye içinde `{PREFIX}onay {action}` yaz. İptal için başka bir şey yaz."
    )

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel

    try:
        answer = await bot.wait_for("message", timeout=30, check=check)
    except asyncio.TimeoutError:
        await ctx.send("Süre doldu; işlem yapılmadı.")
        return False
    if answer.content.strip().lower() != f"{PREFIX}onay {action}":
        await ctx.send("Onay alınmadı; işlem yapılmadı.")
        return False
    return True


@bot.event
async def on_ready():
    init_db()
    print(f"Bot hazır: {bot.user} (discord.py {discord.__version__})")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("Bu komut için gerekli sunucu yetkin yok.", mention_author=False)
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.reply("Botun bu işlemi yapacak yetkisi yok. Rol sırasını ve bot izinlerini kontrol et.", mention_author=False)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"Eksik bilgi: `{error.param.name}`. Kullanım için `.yardim` yaz.", mention_author=False)
    elif isinstance(error, commands.BadArgument):
        await ctx.reply("Girilen kullanıcı, miktar veya süre anlaşılamadı. `.yardim` yaz.", mention_author=False)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"Biraz bekle: {error.retry_after:.1f} saniye.", mention_author=False)
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.reply("Bu komut yalnızca sunucuda kullanılabilir.", mention_author=False)
    else:
        print(f"Komut hatası ({ctx.command}): {error!r}")
        await ctx.reply("Bir hata oluştu. Bot yöneticisi konsol kayıtlarını kontrol edebilir.", mention_author=False)


@bot.command(name="yardim")
async def help_command(ctx):
    await ctx.send(
        "**Futbol botu komutları**\n"
        "`.s [@kişi]` — haftalık ve toplam puanını gösterir.\n"
        "`.ekle @kişi miktar [haftalık|toplam]` / `.sil ...` — istatistik yönetimi.\n"
        "`.ekle @kişi miktar [nitelik]` — nitelikli ekleme haftalık antrenman olarak kaydedilir.\n"
        "`.siralama` — haftalık toplamları ve çalışılan nitelikleri gösterir. `.antmerkez` — nitelik listesini açar.\n"
        "`.aktar @kişi` — haftalık puanını toplama ekler ve haftalığı sıfırlar.\n"
        "`.aktar @everyone` — kayıtlı herkes için aynı işlemi yapar; yönetici onayı gerekir.\n"
        "`.sifirla @kişi` / `.sifirla @everyone` — istatistikleri sıfırlar; toplu işlem yönetici onayı ister.\n"
        "`.k [haftalık|toplam]` — ilk 10 sıralama.\n"
        "`.kick @kişi [sebep]`, `.ban @kişi [sebep]`, `.mute @kişi 10m [sebep]`, `.msil 20` (1–100).\n"
        "İstatistik yönetimi için **İstatistikleri Yönet** veya Yönetici izni gerekir."
    )


@bot.command(name="s")
@commands.guild_only()
async def show_stats(ctx, member: discord.Member = None):
    member = member or ctx.author
    weekly, total = get_stats(ctx.guild.id, member.id)
    await ctx.send(f"⚽ **{display_name(member)}** — Haftalık: **{weekly}** | Toplam: **{total}**")


def stat_manager():
    return commands.has_guild_permissions(manage_guild=True)


@bot.command(name="ekle")
@commands.guild_only()
@stat_manager()
async def add_stats(ctx, member: discord.Member, *, details: str):
    parts = details.split()
    amount_part = next((part for part in parts if part.isdigit()), None)
    if amount_part is None:
        raise commands.BadArgument("Miktar belirtilmeli")
    amount = int(amount_part)
    remainder = [part for part in parts if part != amount_part]
    period_tokens = {"haftalık", "haftalik", "toplam"}
    period = next((part.lower() for part in remainder if part.lower() in period_tokens), "haftalık")
    attribute_text = " ".join(part for part in remainder if part.lower() not in period_tokens)
    if amount <= 0 or amount > 100000:
        raise commands.BadArgument("Miktar 1–100000 arasında olmalı")
    attribute = ATTRIBUTE_LOOKUP.get(attribute_text.casefold()) if attribute_text else None
    if attribute_text and not attribute:
        raise commands.BadArgument("Nitelik .antmerkez listesinden seçilmeli")
    if attribute and period == "toplam":
        raise commands.BadArgument("Antrenman niteliği haftalık kayda eklenir; `toplam` ile kullanılamaz")
    change_stats(ctx.guild.id, member.id, **({"total": amount} if period == "toplam" else {"weekly": amount}))
    if attribute:
        with connect_db() as db:
            db.execute("""INSERT INTO training(guild_id,user_id,attribute,amount) VALUES(?,?,?,?)
                ON CONFLICT(guild_id,user_id,attribute) DO UPDATE SET amount=amount+excluded.amount""",
                       (ctx.guild.id, member.id, attribute, amount))
    label = f" — {attribute} antrenmanı" if attribute else ""
    await ctx.send(f"✅ {display_name(member)} adlı üyeye {amount} {period} puan eklendi{label}.")


@bot.command(name="sil")
@commands.guild_only()
@stat_manager()
async def remove_stats(ctx, member: discord.Member, amount: int, period: str = "haftalık"):
    period = period.lower()
    if amount <= 0 or amount > 100000:
        raise commands.BadArgument("Miktar 1–100000 arasında olmalı")
    if period not in ("haftalık", "haftalik", "toplam"):
        raise commands.BadArgument("Dönem haftalık veya toplam olmalı")
    try:
        change_stats(ctx.guild.id, member.id, **({"total": -amount} if period == "toplam" else {"weekly": -amount}))
    except ValueError as exc:
        await ctx.send(f"❌ {exc}")
        return
    if period != "toplam":
        weekly_after, _ = get_stats(ctx.guild.id, member.id)
        with connect_db() as db:
            rows = db.execute("SELECT attribute,amount FROM training WHERE guild_id=? AND user_id=? ORDER BY amount ASC,attribute DESC",
                              (ctx.guild.id, member.id)).fetchall()
            tracked_total = sum(value for _, value in rows)
            to_remove = max(0, amount - max(0, (weekly_after + amount) - tracked_total))
            for attribute, value in rows:
                if not to_remove:
                    break
                reduction = min(value, to_remove)
                if reduction == value:
                    db.execute("DELETE FROM training WHERE guild_id=? AND user_id=? AND attribute=?",
                               (ctx.guild.id, member.id, attribute))
                else:
                    db.execute("UPDATE training SET amount=amount-? WHERE guild_id=? AND user_id=? AND attribute=?",
                               (reduction, ctx.guild.id, member.id, attribute))
                to_remove -= reduction
    await ctx.send(f"✅ {display_name(member)} adlı üyeden {amount} {period} puan silindi.")


async def transfer_all(guild_id):
    with connect_db() as db:
        db.execute("UPDATE stats SET total=total+weekly, weekly=0 WHERE guild_id=?", (guild_id,))


@bot.command(name="aktar")
@commands.guild_only()
@stat_manager()
async def transfer_stats(ctx, target: str):
    if target.lower() in ("@everyone", "everyone", "herkes"):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("Toplu aktarım yalnızca sunucu yöneticilerine açıktır.")
            return
        if await confirm_everyone(ctx, "aktar"):
            await transfer_all(ctx.guild.id)
            with connect_db() as db:
                db.execute("DELETE FROM training WHERE guild_id=?", (ctx.guild.id,))
            await ctx.send("✅ Kayıtlı tüm üyelerin haftalık puanları toplama aktarıldı.")
        return
    member = await commands.MemberConverter().convert(ctx, target)
    weekly, _ = get_stats(ctx.guild.id, member.id)
    change_stats(ctx.guild.id, member.id, weekly=-weekly, total=weekly)
    with connect_db() as db:
        db.execute("DELETE FROM training WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    await ctx.send(f"✅ {display_name(member)} için {weekly} haftalık puan toplama aktarıldı.")


@bot.command(name="sifirla")
@commands.guild_only()
@stat_manager()
async def reset_stats(ctx, target: str):
    if target.lower() in ("@everyone", "everyone", "herkes"):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("Toplu sıfırlama yalnızca sunucu yöneticilerine açıktır.")
            return
        if await confirm_everyone(ctx, "sifirla"):
            with connect_db() as db:
                db.execute("DELETE FROM stats WHERE guild_id=?", (ctx.guild.id,))
                db.execute("DELETE FROM training WHERE guild_id=?", (ctx.guild.id,))
            await ctx.send("✅ Sunucudaki kayıtlı tüm istatistikler sıfırlandı.")
        return
    member = await commands.MemberConverter().convert(ctx, target)
    with connect_db() as db:
        db.execute("DELETE FROM stats WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
        db.execute("DELETE FROM training WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    await ctx.send(f"✅ {display_name(member)} adlı üyenin istatistikleri sıfırlandı.")


@bot.command(name="k")
@commands.guild_only()
async def leaderboard(ctx, period: str = "haftalık"):
    period = period.lower()
    column = "total" if period == "toplam" else "weekly"
    if period not in ("haftalık", "haftalik", "toplam"):
        raise commands.BadArgument("Dönem haftalık veya toplam olmalı")
    with connect_db() as db:
        rows = db.execute(f"SELECT user_id,{column} FROM stats WHERE guild_id=? AND {column}>0 ORDER BY {column} DESC,user_id ASC LIMIT 10",
                           (ctx.guild.id,)).fetchall()
    if not rows:
        await ctx.send("Henüz sıralama verisi yok.")
        return
    lines = []
    for rank, (user_id, score) in enumerate(rows, 1):
        member = ctx.guild.get_member(user_id)
        name = display_name(member) if member else f"Kullanıcı {user_id}"
        lines.append(f"**{rank}.** {name} — {score}")
    await ctx.send(f"🏆 **{period.title()} sıralaması**\n" + "\n".join(lines))


@bot.command(name="siralama", aliases=["sıralama"])
@commands.guild_only()
async def weekly_training_leaderboard(ctx):
    with connect_db() as db:
        rows = db.execute("SELECT user_id,weekly FROM stats WHERE guild_id=? AND weekly>0 ORDER BY weekly DESC,user_id ASC LIMIT 10",
                           (ctx.guild.id,)).fetchall()
        details = {user_id: db.execute("SELECT attribute,amount FROM training WHERE guild_id=? AND user_id=? ORDER BY amount DESC,attribute",
                                       (ctx.guild.id, user_id)).fetchall() for user_id, _ in rows}
    if not rows:
        await ctx.send("Bu hafta henüz antrenman puanı yok.")
        return
    lines = []
    for rank, (user_id, weekly) in enumerate(rows, 1):
        member = ctx.guild.get_member(user_id)
        name = display_name(member) if member else f"Kullanıcı {user_id}"
        skills = details[user_id]
        trained = ", ".join(f"{attribute} +{amount}" for attribute, amount in skills) if skills else "Nitelik belirtilmedi"
        lines.append(f"**{rank}. {name}** — Haftalık: **{weekly}**\n↳ {trained}")
    await ctx.send("📊 **Haftalık antrenman sıralaması**\n" + "\n".join(lines))


@bot.command(name="antmerkez", aliases=["antrenmanmerkezi"])
async def training_center(ctx):
    embed = discord.Embed(title="🏋️ Antrenman Merkezi", description="`.ekle @kişi miktar nitelik` ile haftalık antrenman kaydı ekleyebilirsin.")
    for category, attributes in ATTRIBUTES.items():
        embed.add_field(name=category, value=" • ".join(attributes), inline=False)
    await ctx.send(embed=embed)


@bot.command(name="kick")
@commands.guild_only()
@commands.has_guild_permissions(kick_members=True)
@commands.bot_has_guild_permissions(kick_members=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def kick_member(ctx, member: discord.Member, *, reason="Belirtilmedi"):
    if member == ctx.author or member == ctx.guild.owner or member.top_role >= ctx.author.top_role:
        await ctx.send("Bu üyeyi rol sırası nedeniyle atamazsın.")
        return
    await member.kick(reason=f"{ctx.author} tarafından: {reason[:300]}")
    await ctx.send(f"✅ {display_name(member)} sunucudan atıldı. Sebep: {reason[:300]}")


@bot.command(name="ban")
@commands.guild_only()
@commands.has_guild_permissions(ban_members=True)
@commands.bot_has_guild_permissions(ban_members=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def ban_member(ctx, member: discord.Member, *, reason="Belirtilmedi"):
    if member == ctx.author or member == ctx.guild.owner or member.top_role >= ctx.author.top_role:
        await ctx.send("Bu üyeyi rol sırası nedeniyle yasaklayamazsın.")
        return
    await member.ban(reason=f"{ctx.author} tarafından: {reason[:300]}", delete_message_seconds=0)
    await ctx.send(f"✅ {display_name(member)} sunucudan yasaklandı. Sebep: {reason[:300]}")


@bot.command(name="mute")
@commands.guild_only()
@commands.has_guild_permissions(moderate_members=True)
@commands.bot_has_guild_permissions(moderate_members=True)
@commands.cooldown(1, 5, commands.BucketType.user)
async def mute_member(ctx, member: discord.Member, duration: str, *, reason="Belirtilmedi"):
    match = re.fullmatch(r"([1-9]\d*)([mhd])", duration.lower())
    if not match:
        await ctx.send("Süreyi `10m`, `2h` veya `1d` biçiminde yaz.")
        return
    amount, unit = int(match.group(1)), match.group(2)
    minutes = amount * {"m": 1, "h": 60, "d": 1440}[unit]
    if minutes > MAX_MUTE_MINUTES:
        await ctx.send("En uzun susturma süresi 28 gündür.")
        return
    if member == ctx.author or member == ctx.guild.owner or member.top_role >= ctx.author.top_role:
        await ctx.send("Bu üyeyi rol sırası nedeniyle susturamazsın.")
        return
    await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=f"{ctx.author}: {reason[:300]}")
    await ctx.send(f"✅ {display_name(member)} {duration} süreyle susturuldu. Sebep: {reason[:300]}")


@bot.command(name="msil")
@commands.guild_only()
@commands.has_guild_permissions(manage_messages=True)
@commands.bot_has_guild_permissions(manage_messages=True, read_message_history=True)
@commands.cooldown(1, 3, commands.BucketType.user)
async def delete_messages(ctx, amount: int):
    if amount < 1 or amount > MAX_PURGE:
        await ctx.send("Bir seferde 1–100 mesaj silebilirsin.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1, reason=f"{ctx.author} mesaj temizleme komutu")
    notice = await ctx.send(f"🧹 {max(0, len(deleted)-1)} mesaj silindi.")
    await notice.delete(delay=5)


def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN ortam değişkeni ayarlanmamış.")
    init_db()
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()


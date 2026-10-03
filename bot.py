import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

# =========================
# VERİLER
# =========================

haftalik = {}
all_time = {}

# Sıfırlama / aktarma yetkisi olan rol
HAFTALIK_SIFIRLAMA_ROL_ID = 1553136364789309552

NITELIKLER = [
    "Orta Açma",
    "Bitiricilik",
    "Kafa İsabeti",
    "Kısa Pas",
    "Voleler",
    "Ayakta Müdahale",
    "Kayarak Müdahale",
    "Dribbling",
    "Falso",
    "Serbest Vuruş İsabeti",
    "Uzun Pas",
    "Top Kontrolü",
    "Şut Gücü",
    "Zıplama",
    "Dayanıklılık",
    "Güç",
    "Uzaktan Şut",
    "Hızlanma",
    "Sprint Hızı",
    "Çeviklik",
    "Reaksiyonlar",
    "Denge",
    "Agresiflik",
    "Top Kesme",
    "Pozisyon Alma",
    "Görüş",
    "Penaltı",
    "Kaleci Atlayışı",
    "Kaleci Top Kontrolü",
    "Kaleci Vuruşu",
    "Kaleci Pozisyon Alma",
    "Kaleci Refleksler"
]


# =========================
# ALL TIME EMBED
# =========================

def all_time_embed(uye):

    veriler = all_time.get(uye.id, {})
    toplam = sum(veriler.values())

    if veriler:
        nitelikler = "\n".join(
            f"**{isim}:** {deger}"
            for isim, deger in veriler.items()
        )
    else:
        nitelikler = "*Henüz nitelik eklenmemiş.*"

    embed = discord.Embed(
        title=f"{uye.display_name} - İstatistikler",
        color=discord.Color.blurple()
    )

    embed.description = (
        "🎯 **Basılan Nitelikler**\n"
        f"{nitelikler}\n\n"
        "📈 **Toplam Stat**\n"
        f"**{toplam}**"
    )

    embed.set_footer(
        text="Premier Support • İstatistikler"
    )

    return embed


# =========================
# HAFTALIK EMBED
# =========================

def haftalik_embed(uye):

    veriler = haftalik.get(uye.id, {})
    toplam = sum(veriler.values())

    if veriler:
        nitelikler = "\n".join(
            f"**{isim}:** {deger}"
            for isim, deger in veriler.items()
        )
    else:
        nitelikler = "*Henüz haftalık nitelik eklenmemiş.*"

    embed = discord.Embed(
        title=f"{uye.display_name} - Haftalık İstatistikler",
        color=discord.Color.blurple()
    )

    embed.description = (
        "🎯 **Haftalık Nitelikler**\n"
        f"{nitelikler}\n\n"
        "📈 **Toplam Stat**\n"
        f"**{toplam}**"
    )

    embed.set_footer(
        text="Premier Support • Haftalık İstatistikler"
    )

    return embed


# =========================
# BUTONLAR
# =========================

class IstatistikView(discord.ui.View):

    def __init__(self, uye):
        super().__init__(timeout=180)
        self.uye = uye

    @discord.ui.button(
        label="Haftalık",
        emoji="📊",
        style=discord.ButtonStyle.primary
    )
    async def haftalik_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.edit_message(
            embed=haftalik_embed(self.uye),
            view=self
        )

    @discord.ui.button(
        label="All Time",
        emoji="🏆",
        style=discord.ButtonStyle.secondary
    )
    async def all_time_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.edit_message(
            embed=all_time_embed(self.uye),
            view=self
        )


# =========================
# BOT AÇILDI
# =========================

@bot.event
async def on_ready():

    print(f"{bot.user} aktif!")


# =========================
# .S KOMUTU
# =========================

@bot.command()
async def s(ctx, uye: discord.Member = None):

    if uye is None:
        uye = ctx.author

    await ctx.send(
        embed=all_time_embed(uye),
        view=IstatistikView(uye)
    )


# =========================
# .EKLE
# SADECE HAFTALIK
# =========================

@bot.command()
async def ekle(
    ctx,
    uye: discord.Member,
    deger: int,
    *,
    nitelik: str
):

    if deger < 1 or deger > 49:

        await ctx.send(
            "❌ Değer **1 ile 49 arasında** olmalı."
        )

        return

    bulunan = None

    for isim in NITELIKLER:

        if isim.lower() == nitelik.lower():

            bulunan = isim
            break

    if bulunan is None:

        await ctx.send(
            "❌ Geçersiz nitelik.\n"
            "Örnek: `.ekle @Mauro 35 Dribbling`"
        )

        return

    if uye.id not in haftalik:
        haftalik[uye.id] = {}

    haftalik[uye.id][bulunan] = deger

    await ctx.send(
        f"✅ {uye.mention} → **{bulunan}: {deger}** "
        f"haftalığa eklendi."
    )


# =========================
# YETKİ KONTROLÜ
# =========================

def yetkili_mi(ctx):

    rol = ctx.guild.get_role(
        HAFTALIK_SIFIRLAMA_ROL_ID
    )

    if rol is None:
        return False

    return rol in ctx.author.roles


# =========================
# HAFTALIK SIFIRLA
# =========================

async def haftalik_sifirla_islemi(ctx, uye=None):

    if not yetkili_mi(ctx):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    # @everyone
    if ctx.message.mention_everyone:

        for member in ctx.guild.members:
            haftalik.pop(member.id, None)

        await ctx.send(
            "✅ Sunucudaki herkesin **Haftalık nitelikleri sıfırlandı.**"
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Bir kullanıcı etiketle."
        )

        return

    haftalik.pop(uye.id, None)

    await ctx.send(
        f"✅ {uye.mention} kullanıcısının "
        f"**Haftalık nitelikleri sıfırlandı.**"
    )


@bot.command(name="haftaliksifirla")
async def haftaliksifirla(
    ctx,
    uye: discord.Member = None
):

    await haftalik_sifirla_islemi(ctx, uye)


@bot.command(name="haftaliksıfırla")
async def haftaliksifirla_2(
    ctx,
    uye: discord.Member = None
):

    await haftalik_sifirla_islemi(ctx, uye)


# =========================
# ALL TIME SIFIRLA
# =========================

async def all_time_sifirla_islemi(ctx, uye=None):

    if not yetkili_mi(ctx):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    # @everyone
    if ctx.message.mention_everyone:

        for member in ctx.guild.members:
            all_time.pop(member.id, None)

        await ctx.send(
            "✅ Sunucudaki herkesin **All Time nitelikleri sıfırlandı.**"
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Bir kullanıcı etiketle."
        )

        return

    all_time.pop(uye.id, None)

    await ctx.send(
        f"✅ {uye.mention} kullanıcısının "
        f"**All Time nitelikleri sıfırlandı.**"
    )


@bot.command(name="alltimesifirla")
async def alltimesifirla(
    ctx,
    uye: discord.Member = None
):

    await all_time_sifirla_islemi(ctx, uye)


@bot.command(name="alltimesıfırla")
async def alltimesifirla_2(
    ctx,
    uye: discord.Member = None
):

    await all_time_sifirla_islemi(ctx, uye)


# =========================
# AKTAR
# HAFTALIK → ALL TIME
# =========================

@bot.command()
async def aktar(
    ctx,
    uye: discord.Member = None
):

    if not yetkili_mi(ctx):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Bir kullanıcı etiketle."
        )

        return

    veriler = haftalik.get(uye.id, {})

    if not veriler:

        await ctx.send(
            f"❌ {uye.mention} kullanıcısının "
            f"aktarılacak haftalık niteliği yok."
        )

        return

    if uye.id not in all_time:
        all_time[uye.id] = {}

    for isim, deger in veriler.items():

        all_time[uye.id][isim] = (
            all_time[uye.id].get(isim, 0) + deger
        )

    haftalik.pop(uye.id, None)

    await ctx.send(
        f"✅ {uye.mention} kullanıcısının "
        f"**Haftalık nitelikleri All Time'a aktarıldı.**\n"
        f"Haftalık verileri silindi."
    )


# =========================
# BOTU BAŞLAT
# =========================

bot.run(os.getenv("DISCORD_TOKEN"))

import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)

haftalik = {}
all_time = {}

YONETIM_ROL_ID = 1553136364789309552
EKLE_SIL_ROL_ID = 1553136385538654329

NITELIKLER = [
    "Orta Açma", "Bitiricilik", "Kafa İsabeti", "Kısa Pas", "Voleler",
    "Ayakta Müdahale", "Kayarak Müdahale", "Dribbling", "Falso",
    "Serbest Vuruş İsabeti", "Uzun Pas", "Top Kontrolü", "Şut Gücü",
    "Zıplama", "Dayanıklılık", "Güç", "Uzaktan Şut", "Hızlanma",
    "Sprint Hızı", "Çeviklik", "Reaksiyonlar", "Denge", "Agresiflik",
    "Top Kesme", "Pozisyon Alma", "Görüş", "Penaltı",
    "Kaleci Atlayışı", "Kaleci Top Kontrolü", "Kaleci Vuruşu",
    "Kaleci Pozisyon Alma", "Kaleci Refleksler"
]


# =========================
# EMBEDLER
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

    embed.set_footer(text="Premier Support • İstatistikler")
    return embed


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

    embed.set_footer(text="Premier Support • Haftalık İstatistikler")
    return embed


# =========================
# .s BUTONLARI
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
    async def haftalik_button(self, interaction, button):
        await interaction.response.edit_message(
            embed=haftalik_embed(self.uye),
            view=self
        )

    @discord.ui.button(
        label="All Time",
        emoji="🏆",
        style=discord.ButtonStyle.secondary
    )
    async def all_time_button(self, interaction, button):
        await interaction.response.edit_message(
            embed=all_time_embed(self.uye),
            view=self
        )


# =========================
# READY
# =========================

@bot.event
async def on_ready():
    print(f"{bot.user} aktif!")


# =========================
# .s
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
# YETKİ KONTROLLERİ
# =========================

def yonetim_yetkili_mi(ctx):
    if ctx.guild is None:
        return False

    rol = ctx.guild.get_role(YONETIM_ROL_ID)

    if rol is None:
        return False

    return rol in ctx.author.roles


def ekle_sil_yetkili_mi(ctx):
    if ctx.guild is None:
        return False

    rol = ctx.guild.get_role(EKLE_SIL_ROL_ID)

    if rol is None:
        return False

    return rol in ctx.author.roles


# =========================
# STAT PARSE
# =========================

def statlari_parse_et(veriler):

    pattern = r"(\d+)\s+(.+?)(?=\s*,?\s*\d+\s+|$)"

    eslesmeler = re.findall(pattern, veriler)

    bulunanlar = []
    hatalar = []

    for deger_str, nitelik in eslesmeler:

        deger = int(deger_str)
        nitelik = nitelik.strip(" ,")

        if deger < 1 or deger > 49:
            hatalar.append(
                f"**{nitelik}** → değer 1-49 arasında olmalı."
            )
            continue

        bulunan = None

        for isim in NITELIKLER:
            if isim.lower() == nitelik.lower():
                bulunan = isim
                break

        if bulunan is None:
            hatalar.append(
                f"Geçersiz nitelik: **{nitelik}**"
            )
            continue

        bulunanlar.append((bulunan, deger))

    return bulunanlar, hatalar


# =========================
# STAT TALEP EMBED
# =========================

def stat_talep_embed(talep):

    uye = talep["uye"]
    statlar = talep["statlar"]
    sebep = talep.get("sebep")

    stat_listesi = "\n".join(
        f"**{isim}: {deger}**"
        for isim, deger in statlar
    )

    embed = discord.Embed(
        title="📋 Stat Ekleme Talebi",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="👤 Oyuncu",
        value=uye.mention,
        inline=False
    )

    embed.add_field(
        name="🎯 Eklenecek Nitelikler",
        value=stat_listesi,
        inline=False
    )

    if sebep:
        embed.add_field(
            name="📝 Sebep",
            value=sebep,
            inline=False
        )
    else:
        embed.add_field(
            name="📝 Sebep",
            value="*Henüz sebep girilmedi.*",
            inline=False
        )

    embed.set_footer(
        text="Statlar onay verilene kadar eklenmez."
    )

    return embed


# =========================
# SEBEP MODAL
# =========================

class SebepModal(discord.ui.Modal, title="Stat Ekleme Sebebi"):

    sebep = discord.ui.TextInput(
        label="Sebep",
        placeholder="Statların neden eklendiğini yaz...",
        required=True,
        min_length=2,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, talep):
        super().__init__()
        self.talep = talep

    async def on_submit(self, interaction):

        if interaction.user.id != self.talep["isteyen_id"]:
            await interaction.response.send_message(
                "❌ Bu stat talebini sadece talebi oluşturan kişi düzenleyebilir.",
                ephemeral=True
            )
            return

        self.talep["sebep"] = str(self.sebep)

        await interaction.response.edit_message(
            embed=stat_talep_embed(self.talep),
            view=OnayView(self.talep)
        )


# =========================
# SEBEP BUTONU
# =========================

class SebepView(discord.ui.View):

    def __init__(self, talep):
        super().__init__(timeout=300)
        self.talep = talep

    @discord.ui.button(
        label="Sebep Gir",
        emoji="📝",
        style=discord.ButtonStyle.primary
    )
    async def sebep_gir(self, interaction, button):

        if interaction.user.id != self.talep["isteyen_id"]:
            await interaction.response.send_message(
                "❌ Bu talebi sadece talebi oluşturan kişi düzenleyebilir.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            SebepModal(self.talep)
        )


# =========================
# ONAY / İPTAL
# =========================

class OnayView(discord.ui.View):

    def __init__(self, talep):
        super().__init__(timeout=300)
        self.talep = talep

    @discord.ui.button(
        label="Onayla",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def onayla(self, interaction, button):

        if interaction.user.id != self.talep["isteyen_id"]:
            await interaction.response.send_message(
                "❌ Bu talebi sadece talebi oluşturan kişi onaylayabilir.",
                ephemeral=True
            )
            return

        if not self.talep.get("sebep"):
            await interaction.response.send_message(
                "❌ Önce **Sebep Gir** butonundan sebep yazmalısın.",
                ephemeral=True
            )
            return

        uye = self.talep["uye"]

        if uye.id not in haftalik:
            haftalik[uye.id] = {}

        for isim, deger in self.talep["statlar"]:
            haftalik[uye.id][isim] = deger

        stat_listesi = "\n".join(
            f"**{isim}: {deger}**"
            for isim, deger in self.talep["statlar"]
        )

        embed = discord.Embed(
            title="✅ Statlar Eklendi",
            color=discord.Color.green()
        )

        embed.add_field(
            name="👤 Oyuncu",
            value=uye.mention,
            inline=False
        )

        embed.add_field(
            name="🎯 Eklenen Nitelikler",
            value=stat_listesi,
            inline=False
        )

        embed.add_field(
            name="📝 Sebep",
            value=self.talep["sebep"],
            inline=False
        )

        embed.set_footer(text="Premier Support • Haftalık")

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    @discord.ui.button(
        label="İptal Et",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def iptal(self, interaction, button):

        if interaction.user.id != self.talep["isteyen_id"]:
            await interaction.response.send_message(
                "❌ Bu talebi sadece talebi oluşturan kişi iptal edebilir.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="❌ Stat Ekleme İptal Edildi",
            description=(
                f"{self.talep['uye'].mention} için oluşturulan "
                "stat ekleme talebi iptal edildi."
            ),
            color=discord.Color.red()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )


# =========================
# .ekle
# =========================

@bot.command()
async def ekle(ctx, uye: discord.Member, *, veriler: str):

    if not ekle_sil_yetkili_mi(ctx):
        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )
        return

    statlar, hatalar = statlari_parse_et(veriler)

    if not statlar:

        mesaj = "❌ Geçerli bir nitelik bulunamadı."

        if hatalar:
            mesaj += "\n" + "\n".join(hatalar)

        mesaj += (
            "\n\nÖrnek:\n"
            "`.ekle @Mauro 49 Bitiricilik, 49 Dribbling`"
        )

        await ctx.send(mesaj)
        return

    if hatalar:

        hata_mesaji = "\n".join(
            f"❌ {hata}"
            for hata in hatalar
        )

        await ctx.send(
            f"{hata_mesaji}\n\n"
            "❌ Hatalı nitelikler nedeniyle talep oluşturulmadı."
        )

        return

    talep = {
        "uye": uye,
        "statlar": statlar,
        "isteyen_id": ctx.author.id,
        "sebep": None
    }

    await ctx.send(
        embed=stat_talep_embed(talep),
        view=SebepView(talep)
    )


# =========================
# KULLANICI BUL
# =========================

def kullaniciyi_bul(ctx, metin):

    metin = metin.strip()

    if metin.lower() == "@everyone":
        return "everyone"

    if metin.lower() == "@here":
        return "everyone"

    match = re.fullmatch(
        r"<@!?(\d+)>",
        metin
    )

    if match:

        user_id = int(match.group(1))
        uye = ctx.guild.get_member(user_id)

        if uye:
            return uye

        return None

    if metin.isdigit():

        uye = ctx.guild.get_member(
            int(metin)
        )

        if uye:
            return uye

    return None


# =========================
# .sil
# =========================

@bot.command()
async def sil(ctx, uye: discord.Member, *, nitelik: str):

    if not ekle_sil_yetkili_mi(ctx):
        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )
        return

    bulunan = None

    for isim in NITELIKLER:
        if isim.lower() == nitelik.strip().lower():
            bulunan = isim
            break

    if bulunan is None:
        await ctx.send(
            f"❌ Geçersiz nitelik: **{nitelik}**"
        )
        return

    veriler = haftalik.get(uye.id, {})

    if bulunan not in veriler:
        await ctx.send(
            f"❌ {uye.mention} kullanıcısında "
            f"haftalık **{bulunan}** bulunamadı."
        )
        return

    del veriler[bulunan]

    if not veriler:
        haftalik.pop(uye.id, None)

    await ctx.send(
        f"✅ {uye.mention} kullanıcısının "
        f"haftalık **{bulunan}** niteliği silindi."
    )


# =========================
# HAFTALIK SIFIRLAMA
# =========================

async def haftalik_sifirla_islemi(ctx, metin):

    if not yonetim_yetkili_mi(ctx):
        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )
        return

    if not metin:
        await ctx.send(
            "❌ Bir kullanıcı etiketle veya `@everyone` yaz."
        )
        return

    hedef = kullaniciyi_bul(ctx, metin)

    if hedef == "everyone":

        for member in ctx.guild.members:
            haftalik.pop(member.id, None)

        await ctx.send(
            "✅ Sunucudaki herkesin "
            "**Haftalık nitelikleri sıfırlandı.**"
        )
        return

    if hedef is None:

        await ctx.send(
            "❌ Kullanıcı bulunamadı. "
            "Kullanıcıyı etiketlediğinden emin ol."
        )
        return

    haftalik.pop(hedef.id, None)

    await ctx.send(
        f"✅ {hedef.mention} kullanıcısının "
        "**Haftalık nitelikleri sıfırlandı.**"
    )


@bot.command(name="haftaliksifirla")
async def haftaliksifirla(ctx, *, metin=None):
    await haftalik_sifirla_islemi(ctx, metin)


@bot.command(name="haftaliksıfırla")
async def haftaliksifirla_2(ctx, *, metin=None):
    await haftalik_sifirla_islemi(ctx, metin)


# =========================
# ALL TIME SIFIRLAMA
# =========================

async def all_time_sifirla_islemi(ctx, metin):

    if not yonetim_yetkili_mi(ctx):
        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )
        return

    if not metin:
        await ctx.send(
            "❌ Bir kullanıcı etiketle veya `@everyone` yaz."
        )
        return

    hedef = kullaniciyi_bul(ctx, metin)

    if hedef == "everyone":

        for member in ctx.guild.members:
            all_time.pop(member.id, None)

        await ctx.send(
            "✅ Sunucudaki herkesin "
            "**All Time nitelikleri sıfırlandı.**"
        )
        return

    if hedef is None:

        await ctx.send(
            "❌ Kullanıcı bulunamadı. "
            "Kullanıcıyı etiketlediğinden emin ol."
        )
        return

    all_time.pop(hedef.id, None)

    await ctx.send(
        f"✅ {hedef.mention} kullanıcısının "
        "**All Time nitelikleri sıfırlandı.**"
    )


@bot.command(name="alltimesifirla")
async def alltimesifirla(ctx, *, metin=None):
    await all_time_sifirla_islemi(ctx, metin)


@bot.command(name="alltimesıfırla")
async def alltimesifirla_2(ctx, *, metin=None):
    await all_time_sifirla_islemi(ctx, metin)


# =========================
# .alltimesil
# =========================

@bot.command()
async def alltimesil(ctx, uye: discord.Member, *, nitelik: str):

    if not yonetim_yetkili_mi(ctx):
        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )
        return

    bulunan = None

    for isim in NITELIKLER:
        if isim.lower() == nitelik.strip().lower():
            bulunan = isim
            break

    if bulunan is None:
        await ctx.send(
            f"❌ Geçersiz nitelik: **{nitelik}**"
        )
        return

    veriler = all_time.get(uye.id, {})

    if bulunan not in veriler:
        await ctx.send(
            f"❌ {uye.mention} kullanıcısında "
            f"All Time **{bulunan}** bulunamadı."
        )
        return

    del veriler[bulunan]

    if not veriler:
        all_time.pop(uye.id, None)

    await ctx.send(
        f"✅ {uye.mention} kullanıcısının "
        f"All Time **{bulunan}** niteliği silindi."
    )


# =========================
# .aktar
# =========================

@bot.command()
async def aktar(ctx, uye: discord.Member = None):

    if not yonetim_yetkili_mi(ctx):
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
            "aktarılacak haftalık niteliği yok."
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
        "**Haftalık nitelikleri All Time'a aktarıldı.**\n"
        "Haftalık verileri silindi."
    )


# =========================
# HATA YÖNETİMİ
# =========================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Eksik bilgi girdin. Kullanımı kontrol et."
        )
        return

    if isinstance(error, commands.MemberNotFound):
        await ctx.send(
            "❌ Kullanıcı bulunamadı. "
            "Kullanıcıyı etiketlediğinden emin ol."
        )
        return

    print(f"Komut hatası: {error}")


# =========================
# BOTU BAŞLAT
# =========================

bot.run(os.getenv("DISCORD_TOKEN"))

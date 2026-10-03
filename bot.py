```python
import os
import re
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
# İSTATİSTİK BUTONLARI
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
# .S
# =========================

@bot.command()
async def s(ctx, uye: discord.Member = None):

    if uye is None:
        uye = ctx.author

    await ctx.send(
        embed=all_time_embed(uye),
        view=IstatistikView(uye)
    )


# =========================================================
# STAT EKLEME SİSTEMİ
# =========================================================

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

        bulunanlar.append(
            (bulunan, deger)
        )

    return bulunanlar, hatalar


# =========================
# SEBEP MODALI
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

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

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
# STAT TALEP EMBED
# =========================

def stat_talep_embed(talep):

    uye = talep["uye"]
    statlar = talep["statlar"]
    sebep = talep.get("sebep")

    stat_listesi = "\n".join(
        f"**{isim}:** {deger}"
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
# SEBEP GİR BUTONU
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
    async def sebep_gir(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

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
# ONAY / İPTAL BUTONLARI
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
    async def onayla(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.talep["isteyen_id"]:

            await interaction.response.send_message(
                "❌ Bu talebi sadece talebi oluşturan kişi onaylayabilir.",
                ephemeral=True
            )

            return

        # Sebep yoksa onaylama
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

        embed.set_footer(
            text="Premier Support • Haftalık"
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    @discord.ui.button(
        label="İptal Et",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def iptal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

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
# .EKLE
# =========================

@bot.command()
async def ekle(
    ctx,
    uye: discord.Member,
    *,
    veriler: str
):

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

    # Hatalı stat varsa onları da göster
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

    # Talep oluştur
    talep = {
        "uye": uye,
        "statlar": statlar,
        "isteyen_id": ctx.author.id,
        "sebep": None
    }

    # Hemen ekleme YOK
    await ctx.send(
        embed=stat_talep_embed(talep),
        view=SebepView(talep)
    )


# =========================
# YETKİ KONTROLÜ
# =========================

def yetkili_mi(ctx):

    if ctx.guild is None:
        return False

    rol = ctx.guild.get_role(
        HAFTALIK_SIFIRLAMA_ROL_ID
    )

    if rol is None:
        return False

    return rol in ctx.author.roles


# =========================================================
# HAFTALIK SIFIRLA
# =========================================================

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
            "✅ Sunucudaki herkesin "
            "**Haftalık nitelikleri sıfırlandı.**"
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


# =========================================================
# ALL TIME SIFIRLA
# =========================================================

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
            "✅ Sunucudaki herkesin "
            "**All Time nitelikleri sıfırlandı.**"
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


# =========================================================
# AKTAR
# HAFTALIK → ALL TIME
# =========================================================

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


# =========================================================
# HATA YAKALAMA
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "❌ Eksik bilgi girdin. "
            "Kullanımı kontrol et."
        )

        return

    if isinstance(
        error,
        commands.MemberNotFound
    ):

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

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from collections import defaultdict
from datetime import datetime, timedelta
import random
import os

# =========================================================
# AYARLAR
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

PREFIX = "."

YONETIM_ROL_ID = 1553136364789309552
EKLE_SIL_ROL_ID = 1553136385538654329
MUTE_ROL_ID = 1553136389984358552

ANT_KANAL_ID = 1553136962473304156
PEN_KANAL_ID = 1553136964042227722
GUMUS_KANAL_ID = 1556231164799225867
ALTIN_KANAL_ID = 1556231264904683570
LOG_KANAL_ID = 1556078549176426542

ANT_SISTEM_KULLANICI_ID = 1547848567287320636

# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# =========================================================
# NORMALIZE
# =========================================================

def komut_normalize(metin):
    cevir = str.maketrans({
        "ı": "i",
        "İ": "i",
        "ö": "o",
        "Ö": "o",
        "ü": "u",
        "Ü": "u",
        "ş": "s",
        "Ş": "s",
        "ç": "c",
        "Ç": "c",
        "ğ": "g",
        "Ğ": "g"
    })

    return metin.translate(cevir).lower()


class PremierBot(commands.Bot):

    def get_command(self, name):
        normal_name = komut_normalize(name)

        for command in self.commands:
            if komut_normalize(command.name) == normal_name:
                return command

            for alias in command.aliases:
                if komut_normalize(alias) == normal_name:
                    return command

        return None


bot = PremierBot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

# =========================================================
# VERİLER
# =========================================================

STATLAR = [
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

haftalik = defaultdict(lambda: defaultdict(int))
all_time = defaultdict(lambda: defaultdict(int))

# ---------------------------------------------------------
# Antrenman verileri
# ---------------------------------------------------------

antrenman = defaultdict(lambda: {
    "normal": 0,
    "gumus": 0,
    "altin": 0,
    "normal_son": None,
    "gumus_son": None,
    "altin_son": None,
    "pen_son": None
})

# =========================================================
# YARDIMCI FONKSİYONLAR
# =========================================================

def mention_user(user_id):
    return f"<@{user_id}>"


def kanal_getir(kanal_id):
    return bot.get_channel(kanal_id)


def progress_bar(current, maximum, length=10):
    current = max(0, min(current, maximum))

    dolu = round((current / maximum) * length)
    bos = length - dolu

    return "🟩" * dolu + "⬜" * bos


def sure_formatla(seconds):
    if seconds <= 0:
        return "Hazır"

    dakika = int(seconds // 60)
    saat = dakika // 60
    dakika %= 60

    if saat > 0:
        return f"{saat}s {dakika}dk"

    return f"{dakika}dk"


def cooldown_kontrol(last_time, cooldown):
    if last_time is None:
        return True, 0

    gecen = (datetime.now() - last_time).total_seconds()
    kalan = cooldown - gecen

    if kalan <= 0:
        return True, 0

    return False, int(kalan)


def kullanici_verisi(user_id):
    return antrenman[user_id]


# =========================================================
# MODERN ANTRENMAN PANELİ
# =========================================================

def ant_panel_embed(member):

    veri = kullanici_verisi(member.id)

    normal_hazir, normal_kalan = cooldown_kontrol(
        veri["normal_son"],
        3600
    )

    gumus_hazir, gumus_kalan = cooldown_kontrol(
        veri["gumus_son"],
        1800
    )

    altin_hazir, altin_kalan = cooldown_kontrol(
        veri["altin_son"],
        1800
    )

    pen_hazir, pen_kalan = cooldown_kontrol(
        veri["pen_son"],
        3600
    )

    embed = discord.Embed(
        title="🏆 PREMIER TRAINING",
        description=(
            f"### ⚡ Antrenman Merkezi\n"
            f"{member.mention}, gelişimini buradan takip edebilirsin.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.blurple(),
        timestamp=datetime.now()
    )

    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)

    # -----------------------------------------------------
    # NORMAL
    # -----------------------------------------------------

    normal_durum = (
        "🟢 **HAZIR**"
        if normal_hazir
        else f"⏳ **{sure_formatla(normal_kalan)}**"
    )

    normal_tamam = (
        "🏆 Ödül hakkı hazır!"
        if veri["normal"] >= 10
        else "10/10 olduğunda ödül hakkı kazanırsın."
    )

    embed.add_field(
        name="🏋️ ANTRENMAN",
        value=(
            f"**İlerleme:** `{veri['normal']}/10`\n"
            f"{progress_bar(veri['normal'], 10)}\n"
            f"**Durum:** {normal_durum}\n"
            f"🎁 {normal_tamam}"
        ),
        inline=False
    )

    # -----------------------------------------------------
    # GÜMÜŞ
    # -----------------------------------------------------

    gumus_durum = (
        "🟢 **HAZIR**"
        if gumus_hazir
        else f"⏳ **{sure_formatla(gumus_kalan)}**"
    )

    gumus_tamam = (
        "🥈 Beceri seçme hakkı hazır!"
        if veri["gumus"] >= 50
        else "50/50 olduğunda gümüş beceri hakkı."
    )

    embed.add_field(
        name="🥈 GÜMÜŞ BECERİ",
        value=(
            f"**İlerleme:** `{veri['gumus']}/50`\n"
            f"{progress_bar(veri['gumus'], 50)}\n"
            f"**Durum:** {gumus_durum}\n"
            f"🎁 {gumus_tamam}"
        ),
        inline=False
    )

    # -----------------------------------------------------
    # ALTIN
    # -----------------------------------------------------

    altin_durum = (
        "🟢 **HAZIR**"
        if altin_hazir
        else f"⏳ **{sure_formatla(altin_kalan)}**"
    )

    altin_tamam = (
        "🥇 Beceri seçme hakkı hazır!"
        if veri["altin"] >= 100
        else "100/100 olduğunda altın beceri hakkı."
    )

    embed.add_field(
        name="🥇 ALTIN BECERİ",
        value=(
            f"**İlerleme:** `{veri['altin']}/100`\n"
            f"{progress_bar(veri['altin'], 100)}\n"
            f"**Durum:** {altin_durum}\n"
            f"🎁 {altin_tamam}"
        ),
        inline=False
    )

    # -----------------------------------------------------
    # PENALTI
    # -----------------------------------------------------

    pen_durum = (
        "🟢 **HAZIR**"
        if pen_hazir
        else f"⏳ **{sure_formatla(pen_kalan)}**"
    )

    embed.add_field(
        name="⚽ PENALTI ANTRENMANI",
        value=(
            f"**Durum:** {pen_durum}\n"
            f"🎯 Gol ihtimali: **%25**\n"
            f"🧤 Diğer sonuçlar: Kaleci / Direk / Aut"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 BİLGİ",
        value=(
            "Ödül hakkı kazandığında bot otomatik ticket açmaz.\n"
            "Kendin yetkililerle iletişime geçebilirsin."
        ),
        inline=False
    )

    embed.set_footer(
        text="Premier Training • Premier Support"
    )

    return embed


# =========================================================
# MODERN ANTRENMAN GÖRÜNÜMÜ
# =========================================================

def ant_progress_embed(member, baslik, current, maximum, cooldown_text, renk):

    tamamlandi = current >= maximum

    if tamamlandi:
        durum = "🏆 **TAMAMLANDI**"
    else:
        durum = f"📈 **{current}/{maximum}**"

    embed = discord.Embed(
        title=baslik,
        description=(
            f"{member.mention}\n\n"
            f"{progress_bar(current, maximum)}\n\n"
            f"**İlerleme**\n"
            f"`{current}/{maximum}`\n\n"
            f"**Durum**\n"
            f"{durum}\n\n"
            f"**Sonraki Kullanım**\n"
            f"⏱️ {cooldown_text}"
        ),
        color=renk,
        timestamp=datetime.now()
    )

    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)

    if tamamlandi:
        embed.add_field(
            name="🎁 ÖDÜL HAKKI",
            value=(
                "Bu antrenman tamamlandı.\n"
                "Ödülünü almak için yetkililerle iletişime geç."
            ),
            inline=False
        )

    embed.set_footer(
        text="Premier Training • İlerlemen kaydedildi"
    )

    return embed


# =========================================================
# PANEL BUTONLARI
# =========================================================

class AntSistemView(View):

    def __init__(self):
        super().__init__(timeout=None)

    async def yetki_kontrol(self, interaction):

        if interaction.user.id != ANT_SISTEM_KULLANICI_ID:
            await interaction.response.send_message(
                "❌ Bu paneli sadece yetkili kişi kullanabilir.",
                ephemeral=True
            )
            return False

        return True

    # -----------------------------------------------------
    # NORMAL ANTRENMAN
    # -----------------------------------------------------

    @discord.ui.button(
        label="Antrenman",
        emoji="🏋️",
        style=discord.ButtonStyle.primary,
        custom_id="premier_training_normal"
    )
    async def normal(self, interaction, button):

        if not await self.yetki_kontrol(interaction):
            return

        veri = kullanici_verisi(interaction.user.id)

        hazir, kalan = cooldown_kontrol(
            veri["normal_son"],
            3600
        )

        if not hazir:
            await interaction.response.send_message(
                f"⏳ Normal antrenman için **{sure_formatla(kalan)}** beklemelisin.",
                ephemeral=True
            )
            return

        if veri["normal"] >= 10:
            await interaction.response.send_message(
                "🏆 Normal antrenmanı zaten **10/10** tamamladın.\n"
                "Ödül için yetkililerle iletişime geç.",
                ephemeral=True
            )
            return

        veri["normal"] += 1
        veri["normal_son"] = datetime.now()

        embed = ant_progress_embed(
            interaction.user,
            "🏋️ ANTRENMAN • İLERLEME",
            veri["normal"],
            10,
            "1 saat",
            discord.Color.blue()
        )

        kanal = kanal_getir(ANT_KANAL_ID)

        if kanal:
            await kanal.send(embed=embed)

        await interaction.response.edit_message(
            embed=ant_panel_embed(interaction.user),
            view=self
        )

    # -----------------------------------------------------
    # GÜMÜŞ
    # -----------------------------------------------------

    @discord.ui.button(
        label="Gümüş",
        emoji="🥈",
        style=discord.ButtonStyle.secondary,
        custom_id="premier_training_silver"
    )
    async def gumus(self, interaction, button):

        if not await self.yetki_kontrol(interaction):
            return

        veri = kullanici_verisi(interaction.user.id)

        hazir, kalan = cooldown_kontrol(
            veri["gumus_son"],
            1800
        )

        if not hazir:
            await interaction.response.send_message(
                f"⏳ Gümüş beceri için **{sure_formatla(kalan)}** beklemelisin.",
                ephemeral=True
            )
            return

        if veri["gumus"] >= 50:
            await interaction.response.send_message(
                "🥈 Gümüş beceri antrenmanını **50/50** tamamladın.\n"
                "Beceri hakkın için yetkililerle iletişime geç.",
                ephemeral=True
            )
            return

        veri["gumus"] += 1
        veri["gumus_son"] = datetime.now()

        embed = ant_progress_embed(
            interaction.user,
            "🥈 GÜMÜŞ BECERİ • İLERLEME",
            veri["gumus"],
            50,
            "30 dakika",
            discord.Color.light_grey()
        )

        kanal = kanal_getir(GUMUS_KANAL_ID)

        if kanal:
            await kanal.send(embed=embed)

        await interaction.response.edit_message(
            embed=ant_panel_embed(interaction.user),
            view=self
        )

    # -----------------------------------------------------
    # ALTIN
    # -----------------------------------------------------

    @discord.ui.button(
        label="Altın",
        emoji="🥇",
        style=discord.ButtonStyle.success,
        custom_id="premier_training_gold"
    )
    async def altin(self, interaction, button):

        if not await self.yetki_kontrol(interaction):
            return

        veri = kullanici_verisi(interaction.user.id)

        hazir, kalan = cooldown_kontrol(
            veri["altin_son"],
            1800
        )

        if not hazir:
            await interaction.response.send_message(
                f"⏳ Altın beceri için **{sure_formatla(kalan)}** beklemelisin.",
                ephemeral=True
            )
            return

        if veri["altin"] >= 100:
            await interaction.response.send_message(
                "🥇 Altın beceri antrenmanını **100/100** tamamladın.\n"
                "Beceri hakkın için yetkililerle iletişime geç.",
                ephemeral=True
            )
            return

        veri["altin"] += 1
        veri["altin_son"] = datetime.now()

        embed = ant_progress_embed(
            interaction.user,
            "🥇 ALTIN BECERİ • İLERLEME",
            veri["altin"],
            100,
            "30 dakika",
            discord.Color.gold()
        )

        kanal = kanal_getir(ALTIN_KANAL_ID)

        if kanal:
            await kanal.send(embed=embed)

        await interaction.response.edit_message(
            embed=ant_panel_embed(interaction.user),
            view=self
        )

    # -----------------------------------------------------
    # PENALTI
    # -----------------------------------------------------

    @discord.ui.button(
        label="Penaltı",
        emoji="⚽",
        style=discord.ButtonStyle.danger,
        custom_id="premier_training_penalty"
    )
    async def penalti(self, interaction, button):

        if not await self.yetki_kontrol(interaction):
            return

        veri = kullanici_verisi(interaction.user.id)

        hazir, kalan = cooldown_kontrol(
            veri["pen_son"],
            3600
        )

        if not hazir:
            await interaction.response.send_message(
                f"⏳ Penaltı antrenmanı için **{sure_formatla(kalan)}** beklemelisin.",
                ephemeral=True
            )
            return

        veri["pen_son"] = datetime.now()

        sonuc = random.choices(
            [
                "⚽ **GOL!**",
                "🧤 **KALECİ KURTARDI!**",
                "🥅 **DİREK!**",
                "❌ **AUT!**"
            ],
            weights=[25, 25, 25, 25],
            k=1
        )[0]

        # Gerçek %25 gol ihtimali
        if random.random() < 0.25:
            sonuc = "⚽ **GOL!**"
        else:
            sonuc = random.choice([
                "🧤 **KALECİ KURTARDI!**",
                "🥅 **DİREK!**",
                "❌ **AUT!**"
            ])

        embed = discord.Embed(
            title="⚽ PENALTI ANTRENMANI",
            description=(
                f"{interaction.user.mention}\n\n"
                f"# {sonuc}\n\n"
                f"🎯 Gol ihtimali: **%25**\n"
                f"⏱️ Sonraki kullanım: **1 saat**"
            ),
            color=(
                discord.Color.green()
                if "GOL" in sonuc
                else discord.Color.red()
            ),
            timestamp=datetime.now()
        )

        if interaction.user.avatar:
            embed.set_thumbnail(
                url=interaction.user.avatar.url
            )

        if "GOL" in sonuc:
            embed.add_field(
                name="🎁 ÖDÜL",
                value=(
                    "5 nitelik ödülü kazandın!\n"
                    "Ödülünü almak için yetkililerle iletişime geç."
                ),
                inline=False
            )

        embed.set_footer(
            text="Premier Training • Penaltı"
        )

        kanal = kanal_getir(PEN_KANAL_ID)

        if kanal:
            await kanal.send(embed=embed)

        await interaction.response.edit_message(
            embed=ant_panel_embed(interaction.user),
            view=self
        )


# =========================================================
# .ANTSISTEM
# =========================================================

@bot.command(name="antsistem")
async def antsistem(ctx):

    if ctx.author.id != ANT_SISTEM_KULLANICI_ID:
        await ctx.send(
            "❌ Bu komutu kullanma yetkin yok."
        )
        return

    embed = ant_panel_embed(ctx.author)

    await ctx.send(
        embed=embed,
        view=AntSistemView()
    )


# =========================================================
# İSTATİSTİK EKLEME
# =========================================================

class SebepModal(Modal):

    def __init__(self, target, miktar, stat, author):

        super().__init__(
            title="📝 İşlem Sebebi"
        )

        self.target = target
        self.miktar = miktar
        self.stat = stat
        self.author = author

        self.sebep = TextInput(
            label="Sebep",
            placeholder="İşlem sebebini yaz...",
            required=True,
            max_length=500
        )

        self.add_item(self.sebep)

    async def on_submit(self, interaction):

        view = OnayView(
            self.target,
            self.miktar,
            self.stat,
            self.sebep.value,
            self.author
        )

        embed = discord.Embed(
            title="📋 İSTATİSTİK İŞLEMİ",
            color=discord.Color.orange()
        )

        embed.add_field(
            name="👤 Oyuncu",
            value=self.target.mention,
            inline=False
        )

        embed.add_field(
            name="📊 Nitelik",
            value=self.stat,
            inline=True
        )

        embed.add_field(
            name="➕ Miktar",
            value=str(self.miktar),
            inline=True
        )

        embed.add_field(
            name="📝 Sebep",
            value=self.sebep.value,
            inline=False
        )

        await interaction.response.edit_message(
            embed=embed,
            view=view
        )


class SebepView(View):

    def __init__(self, target, miktar, stat, author):
        super().__init__(timeout=300)

        self.target = target
        self.miktar = miktar
        self.stat = stat
        self.author = author

    @discord.ui.button(
        label="Sebep Gir",
        emoji="📝",
        style=discord.ButtonStyle.primary
    )
    async def sebep(self, interaction, button):

        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Bu işlem sana ait değil.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            SebepModal(
                self.target,
                self.miktar,
                self.stat,
                self.author
            )
        )


class OnayView(View):

    def __init__(
        self,
        target,
        miktar,
        stat,
        sebep,
        author
    ):

        super().__init__(timeout=300)

        self.target = target
        self.miktar = miktar
        self.stat = stat
        self.sebep = sebep
        self.author = author

    @discord.ui.button(
        label="Onayla",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def onayla(self, interaction, button):

        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Bu işlem sana ait değil.",
                ephemeral=True
            )
            return

        haftalik[self.target.id][self.stat] += self.miktar

        toplam = haftalik[self.target.id][self.stat]

        embed = discord.Embed(
            title="✅ İŞLEM ONAYLANDI",
            description=(
                f"{self.target.mention} kullanıcısına "
                f"**+{self.miktar} {self.stat}** eklendi."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="📊 Haftalık Değer",
            value=str(toplam)
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

        kanal = kanal_getir(LOG_KANAL_ID)

        if kanal:
            log = discord.Embed(
                title="📥 İSTATİSTİK EKLENDİ",
                color=discord.Color.green()
            )

            log.add_field(
                name="👤 Oyuncu",
                value=self.target.mention
            )

            log.add_field(
                name="📊 Nitelik",
                value=self.stat
            )

            log.add_field(
                name="➕ Miktar",
                value=str(self.miktar)
            )

            log.add_field(
                name="📝 Sebep",
                value=self.sebep,
                inline=False
            )

            log.add_field(
                name="👮 İşlemi Yapan",
                value=interaction.user.mention
            )

            await kanal.send(embed=log)

    @discord.ui.button(
        label="İptal Et",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def iptal(self, interaction, button):

        if interaction.user.id != self.author.id:
            await interaction.response.send_message(
                "❌ Bu işlem sana ait değil.",
                ephemeral=True
            )
            return

        await interaction.response.edit_message(
            content="❌ İşlem iptal edildi.",
            embed=None,
            view=None
        )


# =========================================================
# .EKLE
# =========================================================

@bot.command(name="ekle")
async def ekle(ctx, member: discord.Member = None, miktar: int = None, *, stat: str = None):

    if not ctx.author.get_role(EKLE_SIL_ROL_ID):
        await ctx.send("❌ Bu komut için yetkin yok.")
        return

    if member is None or miktar is None or stat is None:
        await ctx.send(
            "Kullanım: `.ekle @oyuncu 5 Dribbling`"
        )
        return

    stat_eslesen = None

    for s in STATLAR:
        if komut_normalize(s) == komut_normalize(stat):
            stat_eslesen = s
            break

    if stat_eslesen is None:
        await ctx.send("❌ Geçersiz nitelik.")
        return

    embed = discord.Embed(
        title="📋 İSTATİSTİK EKLEME",
        description=(
            f"**Oyuncu:** {member.mention}\n"
            f"**Nitelik:** `{stat_eslesen}`\n"
            f"**Miktar:** `+{miktar}`\n\n"
            "İşlemi tamamlamak için önce sebep gir."
        ),
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed,
        view=SebepView(
            member,
            miktar,
            stat_eslesen,
            ctx.author
        )
    )


# =========================================================
# .SİL
# =========================================================

@bot.command(name="sil")
async def sil(ctx, member: discord.Member = None, miktar: int = None, *, stat: str = None):

    if not ctx.author.get_role(EKLE_SIL_ROL_ID):
        await ctx.send("❌ Bu komut için yetkin yok.")
        return

    if member is None or miktar is None or stat is None:
        await ctx.send(
            "Kullanım: `.sil @oyuncu 5 Dribbling`"
        )
        return

    stat_eslesen = None

    for s in STATLAR:
        if komut_normalize(s) == komut_normalize(stat):
            stat_eslesen = s
            break

    if stat_eslesen is None:
        await ctx.send("❌ Geçersiz nitelik.")
        return

    mevcut = haftalik[member.id][stat_eslesen]

    if mevcut < miktar:
        await ctx.send(
            f"❌ Kullanıcının haftalık `{stat_eslesen}` değeri "
            f"**{mevcut}**."
        )
        return

    haftalik[member.id][stat_eslesen] -= miktar

    embed = discord.Embed(
        title="🗑️ İSTATİSTİK SİLİNDİ",
        description=(
            f"{member.mention} → "
            f"**-{miktar} {stat_eslesen}**"
        ),
        color=discord.Color.red()
    )

    await ctx.send(embed=embed)

    kanal = kanal_getir(LOG_KANAL_ID)

    if kanal:
        log = discord.Embed(
            title="📤 İSTATİSTİK SİLİNDİ",
            color=discord.Color.red()
        )

        log.add_field(
            name="👤 Oyuncu",
            value=member.mention
        )

        log.add_field(
            name="📊 Nitelik",
            value=stat_eslesen
        )

        log.add_field(
            name="➖ Miktar",
            value=str(miktar)
        )

        log.add_field(
            name="👮 İşlemi Yapan",
            value=ctx.author.mention
        )

        await kanal.send(embed=log)


# =========================================================
# HAFTALIK EMBED
# =========================================================

def toplam_haftalik(user_id):

    return sum(
        haftalik[user_id].values()
    )


def haftalik_liderlik_embed(page=0):

    oyuncular = []

    for user_id, stats in haftalik.items():

        toplam = sum(stats.values())

        if toplam <= 0:
            continue

        oyuncular.append(
            (user_id, toplam)
        )

    oyuncular.sort(
        key=lambda x: (-x[1], x[0])
    )

    baslangic = page * 10
    secilen = oyuncular[baslangic:baslangic + 10]

    embed = discord.Embed(
        title="📊 HAFTALIK LİDERLİK",
        description="Bu haftanın en iyi oyuncuları",
        color=discord.Color.blurple()
    )

    if not secilen:
        embed.description = "Henüz veri yok."
        return embed

    siralar = ["🥇", "🥈", "🥉"]

    for i, (user_id, toplam) in enumerate(secilen):

        sira = baslangic + i + 1

        if sira <= 3:
            emoji = siralar[sira - 1]
        else:
            emoji = f"`#{sira}`"

        embed.add_field(
            name=f"{emoji} Oyuncu",
            value=(
                f"<@{user_id}>\n"
                f"📈 **{toplam} puan**"
            ),
            inline=False
        )

    embed.set_footer(
        text=f"Sayfa {page + 1}"
    )

    return embed


class HaftalikSiralamaView(View):

    def __init__(self, page=0):
        super().__init__(timeout=300)
        self.page = page

    @discord.ui.button(
        label="◀",
        style=discord.ButtonStyle.secondary
    )
    async def geri(self, interaction, button):

        if self.page <= 0:
            await interaction.response.send_message(
                "❌ İlk sayfadasın.",
                ephemeral=True
            )
            return

        self.page -= 1

        await interaction.response.edit_message(
            embed=haftalik_liderlik_embed(self.page),
            view=self
        )

    @discord.ui.button(
        label="▶",
        style=discord.ButtonStyle.secondary
    )
    async def ileri(self, interaction, button):

        oyuncu_sayisi = len([
            x for x in haftalik
            if toplam_haftalik(x) > 0
        ])

        max_page = max(
            0,
            (oyuncu_sayisi - 1) // 10
        )

        if self.page >= max_page:
            await interaction.response.send_message(
                "❌ Son sayfadasın.",
                ephemeral=True
            )
            return

        self.page += 1

        await interaction.response.edit_message(
            embed=haftalik_liderlik_embed(self.page),
            view=self
        )


# =========================================================
# .HAFTALIK
# =========================================================

@bot.command(
    name="haftalik",
    aliases=["haftalik_cmd"]
)
async def haftalik_cmd(ctx):

    await ctx.send(
        embed=haftalik_liderlik_embed(0),
        view=HaftalikSiralamaView(0)
    )


# =========================================================
# .S
# =========================================================

@bot.command(name="s")
async def stats(ctx):

    user_id = ctx.author.id

    embed = discord.Embed(
        title="📊 OYUNCU İSTATİSTİKLERİ",
        description=(
            f"👤 {ctx.author.mention}\n\n"
            "Aşağıdaki butonlardan istatistiklerini "
            "görüntüleyebilirsin."
        ),
        color=discord.Color.blurple()
    )

    toplam = sum(
        all_time[user_id].values()
    )

    embed.add_field(
        name="🏆 All Time",
        value=f"**{toplam}** toplam puan",
        inline=False
    )

    await ctx.send(
        embed=embed,
        view=StatsView(user_id)
    )


class StatsView(View):

    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(
        label="Haftalık",
        emoji="📊",
        style=discord.ButtonStyle.primary
    )
    async def weekly(self, interaction, button):

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Bu menü sana ait değil.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📊 HAFTALIK İSTATİSTİKLER",
            color=discord.Color.blurple()
        )

        stats = haftalik[self.user_id]

        for stat in STATLAR:
            if stats[stat] > 0:
                embed.add_field(
                    name=stat,
                    value=f"**{stats[stat]}**",
                    inline=True
                )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="All Time",
        emoji="🏆",
        style=discord.ButtonStyle.success
    )
    async def alltime(self, interaction, button):

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Bu menü sana ait değil.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🏆 ALL TIME İSTATİSTİKLER",
            color=discord.Color.gold()
        )

        stats = all_time[self.user_id]

        for stat in STATLAR:
            if stats[stat] > 0:
                embed.add_field(
                    name=stat,
                    value=f"**{stats[stat]}**",
                    inline=True
                )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


# =========================================================
# SIFIRLAMA
# =========================================================

@bot.command(name="haftaliksifirla")
async def haftaliksifirla(ctx):

    if not ctx.author.get_role(YONETIM_ROL_ID):
        await ctx.send("❌ Yetkin yok.")
        return

    haftalik.clear()

    await ctx.send(
        "✅ Haftalık istatistikler sıfırlandı."
    )


@bot.command(name="alltimesifirla")
async def alltimesifirla(ctx):

    if not ctx.author.get_role(YONETIM_ROL_ID):
        await ctx.send("❌ Yetkin yok.")
        return

    all_time.clear()

    await ctx.send(
        "✅ All Time istatistikleri sıfırlandı."
    )


# =========================================================
# ALL TIME AKTAR
# =========================================================

@bot.command(name="aktar")
async def aktar(ctx):

    if not ctx.author.get_role(YONETIM_ROL_ID):
        await ctx.send("❌ Yetkin yok.")
        return

    for user_id, stats in haftalik.items():

        for stat, miktar in stats.items():

            all_time[user_id][stat] += miktar

    await ctx.send(
        "✅ Haftalık istatistikler All Time'a aktarıldı."
    )


# =========================================================
# BAN
# =========================================================

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, sebep="Sebep belirtilmedi."):

    if member is None:
        await ctx.send("Kullanım: `.ban @oyuncu sebep`")
        return

    await member.ban(reason=sebep)

    await ctx.send(
        f"🔨 {member.mention} banlandı.\n"
        f"**Sebep:** {sebep}"
    )


# =========================================================
# UNBAN
# =========================================================

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_id: int):

    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)

        await ctx.send(
            f"✅ **{user}** unbanlandı."
        )

    except Exception:
        await ctx.send(
            "❌ Kullanıcı bulunamadı veya banlı değil."
        )


# =========================================================
# MUTE
# =========================================================

@bot.command(name="mute")
async def mute(ctx, member: discord.Member = None):

    if not ctx.author.get_role(MUTE_ROL_ID):
        await ctx.send("❌ Yetkin yok.")
        return

    if member is None:
        await ctx.send("Kullanım: `.mute @oyuncu`")
        return

    role = ctx.guild.get_role(MUTE_ROL_ID)

    if role is None:
        await ctx.send("❌ Mute rolü bulunamadı.")
        return

    await member.add_roles(role)

    await ctx.send(
        f"🔇 {member.mention} susturuldu."
    )


# =========================================================
# UNMUTE
# =========================================================

@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member = None):

    if not ctx.author.get_role(MUTE_ROL_ID):
        await ctx.send("❌ Yetkin yok.")
        return

    if member is None:
        await ctx.send("Kullanım: `.unmute @oyuncu`")
        return

    role = ctx.guild.get_role(MUTE_ROL_ID)

    if role is None:
        await ctx.send("❌ Mute rolü bulunamadı.")
        return

    await member.remove_roles(role)

    await ctx.send(
        f"🔊 {member.mention} susturması kaldırıldı."
    )


# =========================================================
# GÖNDER
# =========================================================

@bot.command(name="gonder")
async def gonder(ctx, *, mesaj=None):

    if not ctx.author.get_role(YONETIM_ROL_ID):
        await ctx.send("❌ Yetkin yok.")
        return

    if not mesaj:
        await ctx.send(
            "Kullanım: `.gonder mesaj`"
        )
        return

    embed = discord.Embed(
        description=mesaj,
        color=discord.Color.blurple()
    )

    if ctx.author.avatar:
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.avatar.url
        )

    embed.set_footer(
        text="Premier Support"
    )

    await ctx.send(embed=embed)


# =========================================================
# HATA YÖNETİMİ
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Bu işlem için gerekli Discord yetkisine sahip değilsin."
        )
        return

    if isinstance(error, commands.MemberNotFound):
        await ctx.send(
            "❌ Kullanıcı bulunamadı."
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Eksik kullanım. Komutun kullanım şeklini kontrol et."
        )
        return

    print(f"Komut hatası: {error}")


# =========================================================
# READY
# =========================================================

views_registered = False


@bot.event
async def on_ready():

    global views_registered

    if not views_registered:
        bot.add_view(AntSistemView())
        views_registered = True

    print("====================================")
    print(f"Bot aktif: {bot.user}")
    print(f"Sunucu sayısı: {len(bot.guilds)}")
    print("Premier Training sistemi aktif.")
    print("====================================")


# =========================================================
# BAŞLAT
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN environment variable bulunamadı!"
    )

bot.run(TOKEN)

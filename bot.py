import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import random
import re
import os
import asyncio
from dotenv import load_dotenv


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# =========================================================
# TÜRKÇE KOMUT NORMALİZASYONU
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
    command_prefix=".",
    intents=intents,
    help_command=None
)


# =========================================================
# IDLER
# =========================================================

YONETIM_ROL_ID = 1553136364789309552
EKLE_SIL_ROL_ID = 1553136385538654329
MUTE_ROL_ID = 1553136389984358552

# Antrenman ilerleme kanalı
ANT_KANAL_ID = 1553136962473304156

# Penaltı sonucu kanalı
PEN_KANAL_ID = 1553136964042227722

# Gümüş beceri ilerleme kanalı
GUMUS_KANAL_ID = 1556231164799225867

# Altın beceri ilerleme kanalı
ALTIN_KANAL_ID = 1556231264904683570

# Stat log kanalı
LOG_KANAL_ID = 1556078549176426546

# .antsistem / .ticket panelini sadece bu kullanıcı açabilir
ANT_SISTEM_KULLANICI_ID = 1547848567287320636

# Ticket sistemi
TICKET_KULLANICI_ID = 1547848567287320636
TICKET_KATEGORI_ID = 1553136756147224588
TICKET_YETKILI_ROL_ID = 1553136385538654329

KAYIT_KANAL_ID = 1553136976029417545
KAYIT_YETKILI_ROL_ID = 1553136384670441524
KAYITSIZ_ROL_ID = 1553136398146736190
FUTBOLCU_ROL_ID = 1553136443407212644
TEKNIK_DIREKTOR_ROL_ID = 1553136397102227588


# =========================================================
# STATLAR
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


# =========================================================
# VERİLER
# =========================================================

haftalik = {}
all_time = {}

# Kullanıcının antrenman ilerlemeleri
antrenman = {}

# Cooldownlar
ant_son_kullanim = {}
gumus_son_kullanim = {}
altin_son_kullanim = {}
pen_son_kullanim = {}


# =========================================================
# YARDIMCI FONKSİYONLAR
# =========================================================

def rol_var_mi(member, rol_id):

    if not isinstance(member, discord.Member):
        return False

    return any(
        role.id == rol_id
        for role in member.roles
    )


def toplam_stat(data):

    return sum(data.values())


def haftalik_siralama():

    siralama = []

    for user_id, stats in haftalik.items():

        toplam = toplam_stat(stats)

        if toplam > 0:
            siralama.append(
                (user_id, toplam)
            )

    siralama.sort(
        key=lambda x: (-x[1], x[0])
    )

    return siralama


def haftalik_sira_bul(user_id):

    siralama = haftalik_siralama()

    for index, (uid, toplam) in enumerate(
        siralama,
        start=1
    ):

        if uid == user_id:
            return index

    return None


async def log_kanalina_gonder(embed):

    kanal = bot.get_channel(
        LOG_KANAL_ID
    )

    if kanal is None:

        try:
            kanal = await bot.fetch_channel(
                LOG_KANAL_ID
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            return

    try:
        await kanal.send(
            embed=embed
        )

    except discord.HTTPException:
        pass


async def kanal_bul(kanal_id):

    kanal = bot.get_channel(
        kanal_id
    )

    if kanal is not None:
        return kanal

    try:

        return await bot.fetch_channel(
            kanal_id
        )

    except (
        discord.NotFound,
        discord.Forbidden,
        discord.HTTPException
    ):

        return None


def antrenman_verisi(user_id):

    if user_id not in antrenman:

        antrenman[user_id] = {
            "normal": 0,
            "gumus": 0,
            "altin": 0
        }

    return antrenman[user_id]


def cooldown_kontrol(
    dictionary,
    user_id,
    cooldown_saniye
):

    simdi = discord.utils.utcnow()

    son = dictionary.get(
        user_id
    )

    if son is None:

        return True, 0

    fark = (
        simdi - son
    ).total_seconds()

    if fark >= cooldown_saniye:

        return True, 0

    return False, cooldown_saniye - fark


def kalan_sure_text(saniye):

    saniye = int(saniye)

    saat = saniye // 3600
    dakika = (saniye % 3600) // 60
    saniye %= 60

    if saat > 0:

        if dakika > 0:
            return f"{saat} saat {dakika} dakika"

        return f"{saat} saat"

    if dakika > 0:

        if saniye > 0:
            return f"{dakika} dakika {saniye} saniye"

        return f"{dakika} dakika"

    return f"{saniye} saniye"


# =========================================================
# İSTATİSTİK EMBED
# =========================================================

def istatistik_embed(
    member,
    data,
    baslik,
    renk
):

    embed = discord.Embed(
        title=baslik,
        color=renk
    )

    embed.set_author(
        name=member.display_name,
        icon_url=member.display_avatar.url
    )

    if not data:

        embed.description = (
            "Henüz herhangi bir istatistik yok."
        )

    else:

        satirlar = []

        for stat, miktar in data.items():

            satirlar.append(
                f"**{stat}:** `{miktar}`"
            )

        embed.description = "\n".join(
            satirlar
        )

    embed.add_field(
        name="📊 Toplam",
        value=f"`{toplam_stat(data)}`",
        inline=False
    )

    return embed


# =========================================================
# .S BUTONLARI
# =========================================================

class IstatistikView(View):

    def __init__(self, member):

        super().__init__(
            timeout=None
        )

        self.member = member

    @discord.ui.button(
        label="📊 Haftalık",
        style=discord.ButtonStyle.primary
    )
    async def haftalik_button(
        self,
        interaction,
        button
    ):

        if interaction.user.id != self.member.id:

            await interaction.response.send_message(
                "Bu menü sana ait değil.",
                ephemeral=True
            )

            return

        data = haftalik.get(
            self.member.id,
            {}
        )

        embed = istatistik_embed(
            self.member,
            data,
            "📊 Haftalık İstatistikler",
            discord.Color.blue()
        )

        sira = haftalik_sira_bul(
            self.member.id
        )

        if sira:

            embed.add_field(
                name="🏆 Haftalık Sıra",
                value=f"`#{sira}`",
                inline=False
            )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="🏆 All Time",
        style=discord.ButtonStyle.success
    )
    async def alltime_button(
        self,
        interaction,
        button
    ):

        if interaction.user.id != self.member.id:

            await interaction.response.send_message(
                "Bu menü sana ait değil.",
                ephemeral=True
            )

            return

        data = all_time.get(
            self.member.id,
            {}
        )

        embed = istatistik_embed(
            self.member,
            data,
            "🏆 All Time İstatistikler",
            discord.Color.gold()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


# =========================================================
# .S
# =========================================================

@bot.command()
async def s(ctx):

    member = ctx.author

    data = all_time.get(
        member.id,
        {}
    )

    embed = istatistik_embed(
        member,
        data,
        "🏆 All Time İstatistikler",
        discord.Color.gold()
    )

    await ctx.send(
        embed=embed,
        view=IstatistikView(member)
    )


# =========================================================
# HAFTALIK LİDERLİK
# =========================================================

def haftalik_liderlik_embed(page=0):

    siralama = haftalik_siralama()
    per_page = 10
    baslangic = page * per_page
    oyuncular = siralama[baslangic:baslangic + per_page]

    embed = discord.Embed(
        title="🏆 HAFTALIK LİDERLİK",
        description="Bu haftanın en iyi oyuncuları.",
        color=discord.Color.gold()
    )

    if not oyuncular:
        embed.description = "Henüz haftalık sıralamada oyuncu yok."
        return embed

    satirlar = []

    for index, (user_id, toplam) in enumerate(oyuncular, start=baslangic + 1):
        member = bot.get_user(user_id)
        isim = member.mention if member else f"<@{user_id}>"

        if index == 1:
            medal = "🥇"
        elif index == 2:
            medal = "🥈"
        elif index == 3:
            medal = "🥉"
        else:
            medal = f"`#{index}`"

        stats = haftalik.get(user_id, {})
        detaylar = [f"{stat}: {miktar}" for stat, miktar in stats.items() if miktar]
        detay = " • ".join(detaylar) if detaylar else "Nitelik detayı yok."
        satirlar.append(f"{medal} {isim} — **Toplam: {toplam}**\n{detay}")

    embed.description = "\n\n".join(satirlar)

    toplam_sayfa = max(1, (len(siralama) + per_page - 1) // per_page)
    embed.set_footer(text=f"Sayfa {page + 1}/{toplam_sayfa}")
    return embed

class HaftalikSiralamaView(View):

    def __init__(self, page=0):

        super().__init__(
            timeout=120
        )

        self.page = page

    @discord.ui.button(
        label="⬅️",
        style=discord.ButtonStyle.secondary
    )
    async def onceki(
        self,
        interaction,
        button
    ):

        if self.page <= 0:

            await interaction.response.send_message(
                "İlk sayfadasın.",
                ephemeral=True
            )

            return

        self.page -= 1

        await interaction.response.edit_message(
            embed=haftalik_liderlik_embed(
                self.page
            ),
            view=self
        )

    @discord.ui.button(
        label="➡️",
        style=discord.ButtonStyle.secondary
    )
    async def sonraki(
        self,
        interaction,
        button
    ):

        siralama = haftalik_siralama()

        toplam_sayfa = max(
            1,
            (
                len(siralama) + 9
            ) // 10
        )

        if self.page >= toplam_sayfa - 1:

            await interaction.response.send_message(
                "Son sayfadasın.",
                ephemeral=True
            )

            return

        self.page += 1

        await interaction.response.edit_message(
            embed=haftalik_liderlik_embed(
                self.page
            ),
            view=self
        )


# =========================================================
# .HAFTALIK
# =========================================================

@bot.command(
    name="haftalik",
    aliases=["haftalik_cmd"]
)
async def haftalik(ctx):

    await ctx.send(
        embed=haftalik_liderlik_embed(0),
        view=HaftalikSiralamaView(0)
    )


# =========================================================
# ANTRENMAN PANEL EMBED
# =========================================================

def ant_panel_embed():

    embed = discord.Embed(
        title="🏋️ ANTRENMAN MERKEZİ",
        description=(
            "Kendini geliştir, antrenmanlarını tamamla "
            "ve özel beceri ödüllerinin kilidini aç.\n\n"
            "Aşağıdaki butonlardan istediğin antrenmanı seçebilirsin."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🏋️ Antrenman",
        value=(
            "Antrenman yapıp kendini geliştir.\n"
            "⏱️ Her **1 saatte bir** kullanılabilir.\n"
            "🎯 **10/10** yaptığında **10 nitelik hakkı** kazanırsın."
        ),
        inline=False
    )

    embed.add_field(
        name="🥈 Gümüş Beceri Antrenmanı",
        value=(
            "Gümüş beceri antrenmanı yap.\n"
            "⏱️ Her **30 dakikada bir** kullanılabilir.\n"
            "🎯 **50/50** yaptığında istediğin gümüş beceriyi seçme hakkı kazanırsın."
        ),
        inline=False
    )

    embed.add_field(
        name="🥇 Altın Beceri Antrenmanı",
        value=(
            "Altın beceri antrenmanı yap.\n"
            "⏱️ Her **30 dakikada bir** kullanılabilir.\n"
            "🎯 **100/100** yaptığında istediğin altın beceriyi seçme hakkı kazanırsın."
        ),
        inline=False
    )

    embed.add_field(
        name="⚽ Penaltı Antrenmanı",
        value=(
            "Penaltı antrenmanına girip penaltı atabilirsin.\n"
            "⏱️ Her **1 saatte bir** kullanılabilir.\n"
            "⚽ Gol atarsan **5 nitelik hakkı** kazanırsın.\n"
            "🧤 Kaleci kurtarırsa sonuç kanalda gösterilir."
        ),
        inline=False
    )

    embed.set_footer(
        text="Premier Support • Antrenman Sistemi"
    )

    return embed


# =========================================================
# ANTRENMAN PANEL VIEW
# =========================================================

class AntSistemView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🏋️ Antrenman",
        style=discord.ButtonStyle.primary,
        custom_id="ant_normal"
    )
    async def normal(
        self,
        interaction,
        button
    ):

        await normal_antrenman(
            interaction
        )

    @discord.ui.button(
        label="🥈 Gümüş Beceri Antrenmanı",
        style=discord.ButtonStyle.secondary,
        custom_id="ant_gumus"
    )
    async def gumus(
        self,
        interaction,
        button
    ):

        await gumus_antrenman(
            interaction
        )

    @discord.ui.button(
        label="🥇 Altın Beceri Antrenmanı",
        style=discord.ButtonStyle.success,
        custom_id="ant_altin"
    )
    async def altin(
        self,
        interaction,
        button
    ):

        await altin_antrenman(
            interaction
        )

    @discord.ui.button(
        label="⚽ Penaltı Antrenmanı",
        style=discord.ButtonStyle.danger,
        custom_id="ant_penalti"
    )
    async def penalti(
        self,
        interaction,
        button
    ):

        await penalti_antrenmani(
            interaction
        )


# =========================================================
# İLERLEME EMBEDİ
# =========================================================

async def ilerleme_gonder(
    kanal_id,
    member,
    baslik,
    emoji,
    mevcut,
    maksimum,
    renk
):

    kanal = await kanal_bul(
        kanal_id
    )

    if kanal is None:
        return

    oran = min(
        mevcut / maksimum,
        1
    )

    dolu = int(
        oran * 10
    )

    bos = 10 - dolu

    bar = (
        "🟩" * dolu
        + "⬜" * bos
    )

    embed = discord.Embed(
        title=f"{emoji} {baslik}",
        color=renk
    )

    embed.set_author(
        name=member.display_name,
        icon_url=member.display_avatar.url
    )

    embed.description = (
        f"{member.mention}\n\n"
        f"{bar}\n\n"
        f"**İlerleme:** `{mevcut}/{maksimum}`"
    )

    if mevcut >= maksimum:

        embed.add_field(
            name="🎉 TAMAMLANDI",
            value=(
                "Gerekli ilerlemeyi tamamladın!"
            ),
            inline=False
        )

    embed.set_footer(
        text="Premier Support • Antrenman İlerlemesi"
    )

    await kanal.send(
        embed=embed
    )


# =========================================================
# NORMAL ANTRENMAN
# =========================================================

async def normal_antrenman(
    interaction
):

    member = interaction.user

    uygun, kalan = cooldown_kontrol(
        ant_son_kullanim,
        member.id,
        3600
    )

    if not uygun:

        await interaction.response.send_message(
            "⏳ Antrenman butonunu tekrar kullanabilmek için "
            f"**{kalan_sure_text(kalan)}** beklemelisin.",
            ephemeral=True
        )

        return

    veri = antrenman_verisi(
        member.id
    )

    if veri["normal"] >= 10:

        await interaction.response.send_message(
            "🎉 Antrenman seviyen zaten **10/10**.",
            ephemeral=True
        )

        return

    ant_son_kullanim[
        member.id
    ] = discord.utils.utcnow()

    veri["normal"] += 1

    mevcut = veri["normal"]

    await interaction.response.send_message(
        f"🏋️ Antrenman yaptın!\n\n"
        f"**İlerleme:** `{mevcut}/10`",
        ephemeral=True
    )

    await ilerleme_gonder(
        ANT_KANAL_ID,
        member,
        "ANTRENMAN İLERLEMESİ",
        "🏋️",
        mevcut,
        10,
        discord.Color.blue()
    )

    if mevcut >= 10:

        await interaction.followup.send(
            "🎉 **10/10 ANRENMAN TAMAMLANDI!**\n\n"
            "10 nitelik hakkı kazandın. Ödülünü almak için yetkililerle iletişime geçebilirsin.",
            ephemeral=True
        )


# =========================================================
# GÜMÜŞ ANTRENMAN
# =========================================================

async def gumus_antrenman(
    interaction
):

    member = interaction.user

    uygun, kalan = cooldown_kontrol(
        gumus_son_kullanim,
        member.id,
        1800
    )

    if not uygun:

        await interaction.response.send_message(
            "⏳ Gümüş beceri antrenmanı butonunu tekrar "
            f"kullanabilmek için **{kalan_sure_text(kalan)}** beklemelisin.",
            ephemeral=True
        )

        return

    veri = antrenman_verisi(
        member.id
    )

    if veri["gumus"] >= 50:

        await interaction.response.send_message(
            "🎉 Gümüş beceri antrenmanın zaten **50/50**.",
            ephemeral=True
        )

        return

    gumus_son_kullanim[
        member.id
    ] = discord.utils.utcnow()

    veri["gumus"] += 1

    mevcut = veri["gumus"]

    await interaction.response.send_message(
        f"🥈 Gümüş beceri antrenmanı yaptın!\n\n"
        f"**İlerleme:** `{mevcut}/50`",
        ephemeral=True
    )

    await ilerleme_gonder(
        GUMUS_KANAL_ID,
        member,
        "GÜMÜŞ BECERİ İLERLEMESİ",
        "🥈",
        mevcut,
        50,
        discord.Color.light_grey()
    )

    if mevcut >= 50:

        await interaction.followup.send(
            "🎉 **50/50 GÜMÜŞ BECERİ TAMAMLANDI!**\n\n"
            "İstediğin gümüş beceriyi seçme hakkı kazandın. Ödülünü almak için yetkililerle iletişime geçebilirsin.",
            ephemeral=True
        )


# =========================================================
# ALTIN ANTRENMAN
# =========================================================

async def altin_antrenman(
    interaction
):

    member = interaction.user

    uygun, kalan = cooldown_kontrol(
        altin_son_kullanim,
        member.id,
        1800
    )

    if not uygun:

        await interaction.response.send_message(
            "⏳ Altın beceri antrenmanı butonunu tekrar "
            f"kullanabilmek için **{kalan_sure_text(kalan)}** beklemelisin.",
            ephemeral=True
        )

        return

    veri = antrenman_verisi(
        member.id
    )

    if veri["altin"] >= 100:

        await interaction.response.send_message(
            "🎉 Altın beceri antrenmanın zaten **100/100**.",
            ephemeral=True
        )

        return

    altin_son_kullanim[
        member.id
    ] = discord.utils.utcnow()

    veri["altin"] += 1

    mevcut = veri["altin"]

    await interaction.response.send_message(
        f"🥇 Altın beceri antrenmanı yaptın!\n\n"
        f"**İlerleme:** `{mevcut}/100`",
        ephemeral=True
    )

    await ilerleme_gonder(
        ALTIN_KANAL_ID,
        member,
        "ALTIN BECERİ İLERLEMESİ",
        "🥇",
        mevcut,
        100,
        discord.Color.gold()
    )

    if mevcut >= 100:

        await interaction.followup.send(
            "🎉 **100/100 ALTIN BECERİ TAMAMLANDI!**\n\n"
            "İstediğin altın beceriyi seçme hakkı kazandın. Ödülünü almak için yetkililerle iletişime geçebilirsin.",
            ephemeral=True
        )


# =========================================================
# PENALTI
# =========================================================

async def penalti_antrenmani(
    interaction
):

    member = interaction.user

    uygun, kalan = cooldown_kontrol(
        pen_son_kullanim,
        member.id,
        3600
    )

    if not uygun:

        await interaction.response.send_message(
            "⏳ Penaltı butonunu tekrar kullanabilmek için "
            f"**{kalan_sure_text(kalan)}** beklemelisin.",
            ephemeral=True
        )

        return

    pen_son_kullanim[
        member.id
    ] = discord.utils.utcnow()

    # %25 gol
    gol = random.random() < 0.25

    if gol:

        sonuc = "⚽ GOL!"

    else:

        sonuc = random.choice([
            "🧤 KALECİ KURTARDI!",
            "🥅 DİREK!",
            "❌ AUT!"
        ])

    if gol:

        renk = discord.Color.green()

    else:

        renk = discord.Color.red()

    embed = discord.Embed(
        title="⚽ PENALTI ANTRENMANI",
        description=(
            f"{member.mention}\n\n"
            f"## {sonuc}\n\n"
            "Penaltı antrenmanını tamamladın."
        ),
        color=renk
    )

    embed.set_author(
        name=member.display_name,
        icon_url=member.display_avatar.url
    )

    embed.set_footer(
        text="Premier Support • Penaltı Antrenmanı"
    )

    kanal = await kanal_bul(
        PEN_KANAL_ID
    )

    if kanal is not None:

        await kanal.send(
            embed=embed
        )

    await interaction.response.send_message(
        f"⚽ Penaltı sonucu: **{sonuc}**",
        ephemeral=True
    )

    if gol:

        await interaction.followup.send(
            "🎉 **GOL ATTIN!**\n\n"
            "5 nitelik hakkı kazandın. Ödülünü almak için yetkililerle iletişime geçebilirsin.",
            ephemeral=True
        )


# =========================================================
# .ANTSISTEM
# =========================================================

@bot.command(
    name="antsistem",
    aliases=["antpanel"]
)
async def antsistem(ctx):

    if ctx.author.id != ANT_SISTEM_KULLANICI_ID:

        await ctx.send(
            "❌ Bu paneli kullanma yetkin yok.",
            delete_after=5
        )

        return

    await ctx.send(
        embed=ant_panel_embed(),
        view=AntSistemView()
    )


# =========================================================
# KAYIT SİSTEMİ
# =========================================================

class KayitOnayView(View):

    def __init__(self, hedef_id, isim, kayit_eden_id):
        super().__init__(timeout=300)
        self.hedef_id = hedef_id
        self.isim = isim
        self.kayit_eden_id = kayit_eden_id
        self.tiklandi = False

    async def kayit_yap(self, interaction, rol_id, rol_adi):

        if self.tiklandi:
            await interaction.response.send_message(
                "❌ Bu kayıt işlemi zaten tamamlandı.",
                ephemeral=True
            )
            return

        if not rol_var_mi(interaction.user, KAYIT_YETKILI_ROL_ID):
            await interaction.response.send_message(
                "❌ Gerekli Kayıt Yetkilisi rolüne sahip değilsin.",
                ephemeral=True
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Bu işlem sadece sunucuda kullanılabilir.",
                ephemeral=True
            )
            return

        uye = guild.get_member(self.hedef_id)
        rol = guild.get_role(rol_id)
        kayitsiz = guild.get_role(KAYITSIZ_ROL_ID)

        if uye is None:
            await interaction.response.send_message(
                "❌ Kullanıcı sunucuda bulunamadı.",
                ephemeral=True
            )
            return

        if rol is None or kayitsiz is None:
            await interaction.response.send_message(
                "❌ Kayıt rollerinden biri bulunamadı.",
                ephemeral=True
            )
            return

        try:
            await uye.edit(
                nick=self.isim,
                reason=f"Kayıt: {interaction.user} - {rol_adi}"
            )

            if kayitsiz in uye.roles:
                await uye.remove_roles(
                    kayitsiz,
                    reason="Kayıt tamamlandı."
                )

            await uye.add_roles(
                rol,
                reason=f"Kayıt rolü: {rol_adi}"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Kullanıcının ismini veya rollerini değiştirmek için yetkim yok.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Kayıt yapılırken Discord tarafında bir hata oluştu.",
                ephemeral=True
            )
            return

        self.tiklandi = True
        for item in self.children:
            item.disabled = True

        embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed()
        embed.title = "✅ KAYIT TAMAMLANDI"
        embed.color = discord.Color.green()
        embed.add_field(
            name="👤 Kayıt Olan",
            value=f"{uye.mention} (`{uye.id}`)",
            inline=False
        )
        embed.add_field(
            name="📝 İsim",
            value=self.isim,
            inline=True
        )
        embed.add_field(
            name="⚽ Rol",
            value=rol_adi,
            inline=True
        )
        embed.add_field(
            name="🛡️ Kaydı Yapan",
            value=interaction.user.mention,
            inline=False
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


    @discord.ui.button(
        label="Futbolcu",
        emoji="⚽",
        style=discord.ButtonStyle.success,
        custom_id="kayit_futbolcu"
    )
    async def futbolcu(self, interaction, button):
        await self.kayit_yap(
            interaction,
            FUTBOLCU_ROL_ID,
            "Futbolcu"
        )


    @discord.ui.button(
        label="Teknik Direktör",
        emoji="🧠",
        style=discord.ButtonStyle.primary,
        custom_id="kayit_teknik_direktor"
    )
    async def teknik_direktor(self, interaction, button):
        await self.kayit_yap(
            interaction,
            TEKNIK_DIREKTOR_ROL_ID,
            "Teknik Direktör"
        )


@bot.command(name="k")
async def k(ctx, uye: discord.Member, *, isim):

    if ctx.channel.id != KAYIT_KANAL_ID:
        await ctx.send(
            f"❌ Bu komut sadece <#{KAYIT_KANAL_ID}> kanalında kullanılabilir.",
            delete_after=5
        )
        return

    if not rol_var_mi(ctx.author, KAYIT_YETKILI_ROL_ID):
        await ctx.send(
            "❌ Gerekli Kayıt Yetkilisi rolüne sahip değilsin.",
            delete_after=5
        )
        return

    isim = isim.strip()
    if not isim:
        await ctx.send(
            "❌ Doğru kullanım: `.k @kisi İsim Soyisim`",
            delete_after=5
        )
        return

    kayitsiz = ctx.guild.get_role(KAYITSIZ_ROL_ID)
    if kayitsiz is None:
        await ctx.send(
            "❌ Kayıtsız rolü bulunamadı.",
            delete_after=5
        )
        return

    if kayitsiz not in uye.roles:
        await ctx.send(
            "❌ Bu kullanıcı zaten kayıtlı görünüyor.",
            delete_after=5
        )
        return

    embed = discord.Embed(
        title="📋 KAYIT ONAYI",
        description=(
            "Aşağıdaki kullanıcı için kayıt işlemi başlatıldı.\n"
            "Kayıt işlemini tamamlamak için uygun rol butonuna basın."
        ),
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="👤 Kayıt Olacak",
        value=f"{uye.mention} (`{uye.id}`)",
        inline=False
    )
    embed.add_field(
        name="📝 Kayıt Olacağı İsim",
        value=f"`{isim}`",
        inline=True
    )
    embed.add_field(
        name="🛡️ Kayıt Eden",
        value=f"{ctx.author.mention}",
        inline=True
    )
    embed.set_footer(text="Premier League #FC26 • Kayıt Sistemi")

    await ctx.send(
        embed=embed,
        view=KayitOnayView(uye.id, isim, ctx.author.id)
    )


@bot.command(name="kver")
async def kver(ctx, uye: discord.Member):

    if not rol_var_mi(ctx.author, KAYIT_YETKILI_ROL_ID):
        await ctx.send(
            "❌ Gerekli Kayıt Yetkilisi rolüne sahip değilsin.",
            delete_after=5
        )
        return

    kayitsiz = ctx.guild.get_role(KAYITSIZ_ROL_ID)
    if kayitsiz is None:
        await ctx.send(
            "❌ Kayıtsız rolü bulunamadı.",
            delete_after=5
        )
        return

    try:
        await uye.edit(
            nick="Kayıtsız",
            reason=f"Kayıt geri alındı: {ctx.author}"
        )

        # Kayıt rollerini kaldır.
        for rol_id in [FUTBOLCU_ROL_ID, TEKNIK_DIREKTOR_ROL_ID]:
            rol = ctx.guild.get_role(rol_id)
            if rol is not None and rol in uye.roles:
                await uye.remove_roles(
                    rol,
                    reason="Kayıt geri alındı."
                )

        if kayitsiz not in uye.roles:
            await uye.add_roles(
                kayitsiz,
                reason="Kayıt geri alındı."
            )

        await ctx.send(
            f"✅ {uye.mention} tekrar **Kayıtsız** yapıldı."
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ Kullanıcının ismini veya rollerini değiştirmek için yetkim yok."
        )
    except discord.HTTPException:
        await ctx.send(
            "❌ Kayıt geri alınırken Discord tarafında bir hata oluştu."
        )


# =========================================================
# ÜYE GİRİŞİ
# =========================================================

@bot.event
async def on_member_join(member):

    kayitsiz = member.guild.get_role(KAYITSIZ_ROL_ID)

    if kayitsiz is None:
        return

    try:
        await member.edit(
            nick="Kayıtsız",
            reason="Sunucuya yeni katıldı."
        )
    except (discord.Forbidden, discord.HTTPException):
        pass

    try:
        await member.add_roles(
            kayitsiz,
            reason="Sunucuya yeni katıldı."
        )
    except (discord.Forbidden, discord.HTTPException):
        pass

    kanal = member.guild.get_channel(KAYIT_KANAL_ID)
    if not isinstance(kanal, discord.TextChannel):
        return

    toplam = member.guild.member_count or len(member.guild.members)
    hesap_tarihi = discord.utils.format_dt(member.created_at, "D")
    hesap_saati = discord.utils.format_dt(member.created_at, "t")

    embed = discord.Embed(
        title="👋 Yeni Bir Kullanıcı Katıldı!",
        description=(
            f"**Premier League #FC26** sunucumuza hoş geldin "
            f"**{member.display_name}**!\n\n"
            f"Seninle birlikte **{toplam}** kişiyiz. Kayıt olmak için "
            f"<@&{KAYIT_YETKILI_ROL_ID}> rolündeki yetkililerimizi beklemen yeterlidir."
        ),
        color=discord.Color.green()
    )
    embed.add_field(
        name="👤 Kullanıcı ID",
        value=f"`{member.id}`",
        inline=True
    )
    embed.add_field(
        name="📅 Hesap Oluşturulma Tarihi",
        value=f"{hesap_tarihi} {hesap_saati}",
        inline=True
    )
    embed.add_field(
        name="🛡️ Güvenilirlik Durumu",
        value="Güvenilir",
        inline=True
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="Premier League #FC26 • Kayıt Sistemi")

    await kanal.send(
        content=f"👋 Yeni kullanıcı: {member.mention}",
        embed=embed
    )


# =========================================================
# TICKET SİSTEMİ
# =========================================================

def ticket_panel_embed():

    embed = discord.Embed(
        title="🎫 PREMIER LEAGUE TICKET",
        description=(
            "Destek veya yetkili işlemleri için aşağıdaki butondan "
            "ticket açabilirsin.\n\n"
            "🎫 **Ticket Aç** butonuna basarak sana özel bir ticket "
            "kanalı oluşturabilirsin.\n\n"
            "🔇 Özellikle **mute niteliğini almak** istiyorsan "
            "ticketi açıp yetkili ekibini bekleyebilirsin.\n\n"
            "⚠️ Gereksiz ticket açmamaya ve yetkili ekibini gereksiz "
            "yere etiketlememeye dikkat et."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📌 Nasıl çalışır?",
        value=(
            "**1.** 🎫 Ticket Aç butonuna bas.\n"
            "**2.** Sana özel ticket kanalı oluşturulsun.\n"
            "**3.** Talebini ticket içerisinde belirt.\n"
            "**4.** Yetkili ekibinin gelmesini bekle."
        ),
        inline=False
    )

    embed.set_footer(
        text="Premier Support • Ticket Sistemi"
    )

    return embed


class TicketPanelView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🎫 Ticket Aç",
        style=discord.ButtonStyle.primary,
        custom_id="premier_ticket_ac"
    )
    async def ticket_ac(
        self,
        interaction,
        button
    ):

        guild = interaction.guild
        member = interaction.user

        if guild is None:

            await interaction.response.send_message(
                "❌ Bu buton sadece sunucuda kullanılabilir.",
                ephemeral=True
            )

            return

        kategori = guild.get_channel(
            TICKET_KATEGORI_ID
        )

        if not isinstance(
            kategori,
            discord.CategoryChannel
        ):

            await interaction.response.send_message(
                "❌ Ticket kategorisi bulunamadı.",
                ephemeral=True
            )

            return

        # Kullanıcının zaten açık ticketi var mı?
        for kanal in kategori.channels:

            if not isinstance(
                kanal,
                discord.TextChannel
            ):
                continue

            if kanal.topic == f"ticket_sahibi:{member.id}":

                await interaction.response.send_message(
                    f"❌ Zaten açık bir ticketin var: {kanal.mention}",
                    ephemeral=True
                )

                return

        yetkili_rol = guild.get_role(
            TICKET_YETKILI_ROL_ID
        )

        if yetkili_rol is None:

            await interaction.response.send_message(
                "❌ Yetkili rolü bulunamadı.",
                ephemeral=True
            )

            return

        bot_member = guild.me

        if bot_member is None:

            try:
                bot_member = await guild.fetch_member(
                    bot.user.id
                )
            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):
                bot_member = None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            yetkili_rol: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_messages=True
            )
        }

        if bot_member is not None:

            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True
            )

        # Kanal adında sadece güvenli karakterler kullan.
        temiz_isim = re.sub(
            r"[^a-z0-9-]",
            "-",
            komut_normalize(member.display_name)
        ).strip("-")

        if not temiz_isim:
            temiz_isim = "kullanici"

        kanal_adi = f"ticket-{temiz_isim[:18]}-{str(member.id)[-4:]}"

        try:

            ticket = await guild.create_text_channel(
                name=kanal_adi,
                category=kategori,
                overwrites=overwrites,
                topic=f"ticket_sahibi:{member.id}",
                reason=f"Ticket açıldı: {member}"
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Ticket kanalı oluşturmak için yetkim yok.",
                ephemeral=True
            )

            return

        except discord.HTTPException:

            await interaction.response.send_message(
                "❌ Ticket oluşturulurken bir hata oluştu.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="🎫 TICKET AÇILDI",
            description=(
                f"Hoş geldin {member.mention}!\n\n"
                "Yetkili ekibimiz seninle ilgilenecektir.\n\n"
                "🔇 **Mute niteliği** almak için talebini burada "
                "belirtebilir ve yetkili ekibini bekleyebilirsin.\n\n"
                "📌 İşlemin tamamlandığında ticketı kapatabilirsin."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="👤 Ticket Sahibi",
            value=member.mention,
            inline=True
        )

        embed.add_field(
            name="🛡️ Yetkili Ekibi",
            value=yetkili_rol.mention,
            inline=True
        )

        embed.set_footer(
            text="Premier Support • Ticket Sistemi"
        )

        try:

            await ticket.send(
                content=f"{member.mention} {yetkili_rol.mention}",
                embed=embed,
                view=TicketKapatView()
            )

        except discord.HTTPException:

            try:
                await ticket.delete(
                    reason="Ticket mesajı gönderilemedi."
                )
            except discord.HTTPException:
                pass

            await interaction.response.send_message(
                "❌ Ticket oluşturuldu fakat ticket mesajı gönderilemedi.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"✅ Ticketin oluşturuldu: {ticket.mention}",
            ephemeral=True
        )


class TicketKapatView(View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🔒 Ticket Kapat",
        style=discord.ButtonStyle.danger,
        custom_id="premier_ticket_kapat"
    )
    async def ticket_kapat(
        self,
        interaction,
        button
    ):

        kanal = interaction.channel

        if not isinstance(
            kanal,
            discord.TextChannel
        ):

            await interaction.response.send_message(
                "❌ Bu kanal bir ticket kanalı değil.",
                ephemeral=True
            )

            return

        if (
            kanal.category_id != TICKET_KATEGORI_ID
            or not kanal.topic
            or not kanal.topic.startswith("ticket_sahibi:")
        ):

            await interaction.response.send_message(
                "❌ Bu kanal bir ticket kanalı değil.",
                ephemeral=True
            )

            return

        try:
            ticket_sahibi_id = int(
                kanal.topic.split(":", 1)[1]
            )
        except (ValueError, IndexError):

            await interaction.response.send_message(
                "❌ Ticket sahibi bilgisi okunamadı.",
                ephemeral=True
            )

            return

        if (
            interaction.user.id != ticket_sahibi_id
            and not rol_var_mi(
                interaction.user,
                YONETIM_ROL_ID
            )
        ):

            await interaction.response.send_message(
                "❌ Bu ticketı kapatma yetkin yok.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "🔒 Ticket **3 saniye içinde** kapatılacak..."
        )

        await asyncio.sleep(3)

        try:

            await kanal.delete(
                reason=f"Ticket kapatıldı: {interaction.user}"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


# =========================================================
# .TICKET
# =========================================================

@bot.command()
async def ticket(ctx):

    if ctx.author.id != TICKET_KULLANICI_ID:

        await ctx.send(
            "❌ Bu komutu kullanma yetkin yok.",
            delete_after=5
        )

        return

    await ctx.send(
        embed=ticket_panel_embed(),
        view=TicketPanelView()
    )


# =========================================================
# EKLE SİSTEMİ
# =========================================================

class SebepModal(Modal):

    def __init__(self, data):

        super().__init__(
            title="Stat Ekleme Sebebi"
        )

        self.data = data

        self.sebep = TextInput(
            label="Sebep",
            placeholder="Stat neden ekleniyor?",
            required=True,
            max_length=500
        )

        self.add_item(
            self.sebep
        )

    async def on_submit(
        self,
        interaction
    ):

        self.data["sebep"] = (
            self.sebep.value
        )

        embed = ekle_onay_embed(
            self.data
        )

        await interaction.response.edit_message(
            embed=embed,
            view=EkleOnayView(
                self.data
            )
        )


class EkleSebepView(View):

    def __init__(self, data):

        super().__init__(
            timeout=300
        )

        self.data = data

    @discord.ui.button(
        label="📝 Sebep Gir",
        style=discord.ButtonStyle.primary
    )
    async def sebep(
        self,
        interaction,
        button
    ):

        if (
            interaction.user.id
            != self.data["isteyen_id"]
        ):

            await interaction.response.send_message(
                "Bu işlem sana ait değil.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            SebepModal(
                self.data
            )
        )


class EkleOnayView(View):

    def __init__(self, data):

        super().__init__(
            timeout=300
        )

        self.data = data

    @discord.ui.button(
        label="✅ Onayla",
        style=discord.ButtonStyle.success
    )
    async def onayla(
        self,
        interaction,
        button
    ):

        if not rol_var_mi(
            interaction.user,
            EKLE_SIL_ROL_ID
        ):

            await interaction.response.send_message(
                "❌ Bu işlemi onaylama yetkin yok.",
                ephemeral=True
            )

            return

        uye = self.data["oyuncu"]

        haftalik.setdefault(
            uye.id,
            {}
        )

        for stat, miktar in self.data["statlar"]:

            haftalik[
                uye.id
            ][stat] = (
                haftalik[
                    uye.id
                ].get(stat, 0)
                + miktar
            )

        embed = discord.Embed(
            title="📈 STAT EKLENDİ",
            color=discord.Color.green()
        )

        embed.add_field(
            name="👤 İşlemi Yapan",
            value=interaction.user.mention,
            inline=True
        )

        embed.add_field(
            name="🎯 Oyuncu",
            value=uye.mention,
            inline=True
        )

        embed.add_field(
            name="📊 Eklenen Nitelikler",
            value="\n".join(
                f"**{stat}:** +{miktar}"
                for stat, miktar
                in self.data["statlar"]
            ),
            inline=False
        )

        embed.add_field(
            name="📋 Sebep",
            value=self.data["sebep"],
            inline=False
        )

        simdi = discord.utils.utcnow()
        ts = int(
            simdi.timestamp()
        )

        embed.add_field(
            name="🕒 Zaman",
            value=(
                f"<t:{ts}:F>\n"
                f"<t:{ts}:R>"
            ),
            inline=False
        )

        embed.set_footer(
            text="Premier Support • Stat Log"
        )

        await log_kanalina_gonder(
            embed
        )

        await interaction.response.edit_message(
            content="✅ Stat ekleme işlemi onaylandı.",
            embed=None,
            view=None
        )

    @discord.ui.button(
        label="❌ İptal Et",
        style=discord.ButtonStyle.danger
    )
    async def iptal(
        self,
        interaction,
        button
    ):

        if not rol_var_mi(
            interaction.user,
            EKLE_SIL_ROL_ID
        ):

            await interaction.response.send_message(
                "❌ Bu işlemi iptal etme yetkin yok.",
                ephemeral=True
            )

            return

        await interaction.response.edit_message(
            content="❌ Stat ekleme işlemi iptal edildi.",
            embed=None,
            view=None
        )


def ekle_onay_embed(data):

    embed = discord.Embed(
        title="📈 STAT EKLEME ONAYI",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="🎯 Oyuncu",
        value=data["oyuncu"].mention,
        inline=True
    )

    embed.add_field(
        name="👤 İsteyen",
        value=f"<@{data['isteyen_id']}>",
        inline=True
    )

    embed.add_field(
        name="📊 Nitelikler",
        value="\n".join(
            f"**{stat}:** +{miktar}"
            for stat, miktar
            in data["statlar"]
        ),
        inline=False
    )

    embed.add_field(
        name="📋 Sebep",
        value=data["sebep"],
        inline=False
    )

    embed.set_footer(
        text="Sebep girildi • Onay bekleniyor"
    )

    return embed


@bot.command()
async def ekle(
    ctx,
    uye: discord.Member,
    miktar: int,
    *,
    stat
):

    if not rol_var_mi(
        ctx.author,
        EKLE_SIL_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanma yetkin yok."
        )

        return

    if miktar <= 0:

        await ctx.send(
            "❌ Miktar 0'dan büyük olmalı."
        )

        return

    bulunan = []

    for gercek_stat in STATLAR:

        if (
            komut_normalize(stat)
            == komut_normalize(gercek_stat)
        ):

            bulunan.append(
                gercek_stat
            )

            break

    if not bulunan:

        await ctx.send(
            "❌ Geçerli bir nitelik bulunamadı."
        )

        return

    data = {

        "oyuncu": uye,

        "isteyen_id": ctx.author.id,

        "statlar": [
            (x, miktar)
            for x in bulunan
        ],

        "sebep": None
    }

    embed = discord.Embed(
        title="📈 STAT EKLEME TALEBİ",
        description=(
            f"{uye.mention} adlı oyuncuya aşağıdaki "
            "nitelikler eklenecek."
        ),
        color=discord.Color.orange()
    )

    embed.add_field(
        name="📊 Nitelikler",
        value="\n".join(
            f"**{stat}:** +{miktar}"
            for stat, miktar
            in data["statlar"]
        ),
        inline=False
    )

    embed.add_field(
        name="📝 Sebep",
        value="Henüz sebep girilmedi.",
        inline=False
    )

    await ctx.send(
        embed=embed,
        view=EkleSebepView(
            data
        )
    )


# =========================================================
# SİL
# =========================================================

@bot.command()
async def sil(
    ctx,
    uye: discord.Member,
    miktar: int,
    *,
    stat
):

    if not rol_var_mi(
        ctx.author,
        EKLE_SIL_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanma yetkin yok."
        )

        return

    if miktar <= 0:

        await ctx.send(
            "❌ Miktar 0'dan büyük olmalı."
        )

        return

    bulunan = []

    for gercek_stat in STATLAR:

        if (
            komut_normalize(stat)
            == komut_normalize(gercek_stat)
        ):

            bulunan.append(
                gercek_stat
            )

            break

    if not bulunan:

        await ctx.send(
            "❌ Geçerli bir nitelik bulunamadı."
        )

        return

    if uye.id not in haftalik:

        await ctx.send(
            "❌ Bu oyuncunun haftalık istatistiği yok."
        )

        return

    gercekten_silinen = []

    for gercek_stat in bulunan:

        if (
            gercek_stat
            in haftalik[uye.id]
        ):

            haftalik[
                uye.id
            ][gercek_stat] -= miktar

            gercekten_silinen.append(
                (
                    gercek_stat,
                    miktar
                )
            )

            if (
                haftalik[
                    uye.id
                ][gercek_stat]
                <= 0
            ):

                del haftalik[
                    uye.id
                ][gercek_stat]

    if not gercekten_silinen:

        await ctx.send(
            "❌ Bu oyuncuda belirtilen stat bulunamadı."
        )

        return

    embed = discord.Embed(
        title="📉 STAT SİLİNDİ",
        color=discord.Color.red()
    )

    embed.add_field(
        name="👤 İşlemi Yapan",
        value=ctx.author.mention,
        inline=True
    )

    embed.add_field(
        name="🎯 Oyuncu",
        value=uye.mention,
        inline=True
    )

    embed.add_field(
        name="📊 Silinen Nitelikler",
        value="\n".join(
            f"**{stat}:** -{miktar}"
            for stat, miktar
            in gercekten_silinen
        ),
        inline=False
    )

    simdi = discord.utils.utcnow()
    ts = int(
        simdi.timestamp()
    )

    embed.add_field(
        name="🕒 Zaman",
        value=(
            f"<t:{ts}:F>\n"
            f"<t:{ts}:R>"
        ),
        inline=False
    )

    embed.set_footer(
        text="Premier Support • Stat Log"
    )

    await log_kanalina_gonder(
        embed
    )

    await ctx.send(
        "✅ Stat başarıyla silindi."
    )


# =========================================================
# HAFTALIK SIFIRLA
# =========================================================

@bot.command()
async def haftaliksifirla(ctx, *, hedef: str):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Gerekli yönetim rolüne sahip değilsin."
        )

        return

    if hedef.strip() == "@everyone":

        haftalik.clear()

        await ctx.send(
            "✅ Herkesin haftalık istatistikleri sıfırlandı."
        )

        return

    if not ctx.message.mentions:

        await ctx.send(
            "❌ Kullanıcı bulunamadı. **@kisi** veya **@everyone** kullan."
        )

        return

    uye = ctx.message.mentions[0]
    haftalik.pop(uye.id, None)

    await ctx.send(
        f"✅ {uye.mention} adlı kullanıcının haftalık istatistikleri sıfırlandı."
    )


# =========================================================
# ALL TIME SIFIRLA
# =========================================================

@bot.command()
async def alltimesifirla(ctx, *, hedef: str):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Gerekli yönetim rolüne sahip değilsin."
        )

        return

    if hedef.strip() == "@everyone":

        all_time.clear()

        await ctx.send(
            "✅ Herkesin All Time istatistikleri sıfırlandı."
        )

        return

    if not ctx.message.mentions:

        await ctx.send(
            "❌ Kullanıcı bulunamadı. **@kisi** veya **@everyone** kullan."
        )

        return

    uye = ctx.message.mentions[0]
    all_time.pop(uye.id, None)

    await ctx.send(
        f"✅ {uye.mention} adlı kullanıcının All Time istatistikleri sıfırlandı."
    )


# =========================================================
# ALL TIME SİL
# =========================================================

@bot.command()
async def alltimesil(
    ctx,
    uye: discord.Member,
    miktar: int,
    *,
    stat
):

    if not rol_var_mi(
        ctx.author,
        EKLE_SIL_ROL_ID
    ):

        await ctx.send(
            "❌ Gerekli yönetim rolüne sahip değilsin."
        )

        return

    if uye.id not in all_time:

        await ctx.send(
            "❌ Oyuncunun All Time verisi yok."
        )

        return

    bulunan = None

    for gercek_stat in STATLAR:

        if (
            komut_normalize(stat)
            == komut_normalize(gercek_stat)
        ):

            bulunan = gercek_stat

            break

    if bulunan is None:

        await ctx.send(
            "❌ Geçersiz stat."
        )

        return

    if (
        bulunan
        not in all_time[uye.id]
    ):

        await ctx.send(
            "❌ Bu stat oyuncuda yok."
        )

        return

    all_time[
        uye.id
    ][bulunan] -= miktar

    if (
        all_time[
            uye.id
        ][bulunan] <= 0
    ):

        del all_time[
            uye.id
        ][bulunan]

    await ctx.send(
        "✅ All Time stat silindi."
    )


# =========================================================
# AKTAR
# =========================================================

@bot.command()
async def aktar(ctx, uye: discord.Member):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Gerekli yönetim rolüne sahip değilsin."
        )

        return

    stats = haftalik.get(uye.id)

    if not stats:

        await ctx.send(
            f"❌ {uye.mention} adlı kullanıcının aktarılacak haftalık istatistiği yok."
        )

        return

    all_time.setdefault(
        uye.id,
        {}
    )

    for stat, miktar in stats.items():

        all_time[uye.id][stat] = (
            all_time[uye.id].get(stat, 0) + miktar
        )

    await ctx.send(
        f"✅ {uye.mention} adlı kullanıcının haftalık istatistikleri All Time'a aktarıldı."
    )

# =========================================================
# BAN
# =========================================================

@bot.command()
async def ban(
    ctx,
    uye: discord.Member,
    *,
    sebep="Sebep belirtilmedi."
):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Gerekli yönetim rolüne sahip değilsin."
        )

        return

    try:

        await uye.ban(
            reason=sebep
        )

        await ctx.send(
            f"🔨 {uye.mention} banlandı.\n"
            f"**Sebep:** {sebep}"
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Bu kullanıcıyı banlayamıyorum."
        )


# =========================================================
# UNBAN
# =========================================================

@bot.command()
async def unban(
    ctx,
    user_id: int
):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Gerekli yönetim rolüne sahip değilsin."
        )

        return

    try:

        user = await bot.fetch_user(
            user_id
        )

        await ctx.guild.unban(
            user
        )

        await ctx.send(
            f"✅ {user} banı kaldırıldı."
        )

    except discord.NotFound:

        await ctx.send(
            "❌ Kullanıcı bulunamadı."
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Yetkim yok."
        )


# =========================================================
# MUTE
# =========================================================


def mute_suresi_cevir(sayi, birim):

    birim = komut_normalize(birim)

    if birim in ["saniye", "saniyelik"]:
        return sayi

    if birim in ["dakika", "dakikalik"]:
        return sayi * 60

    if birim in ["saat", "saatlik"]:
        return sayi * 60 * 60

    if birim in ["gun", "gunluk"]:
        return sayi * 60 * 60 * 24

    return None


async def mute_suresi_bitir(guild_id, user_id, mute_rol_id, saniye):

    await asyncio.sleep(saniye)

    guild = bot.get_guild(guild_id)

    if guild is None:
        return

    uye = guild.get_member(user_id)

    if uye is None:
        return

    rol = guild.get_role(mute_rol_id)

    if rol is None:
        return

    if rol in uye.roles:

        try:
            await uye.remove_roles(
                rol,
                reason="Mute süresi doldu."
            )

        except discord.Forbidden:
            pass

        except discord.HTTPException:
            pass


@bot.command()
async def mute(
    ctx,
    uye: discord.Member,
    sure: int,
    birim: str,
    *,
    sebep
):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):
        await ctx.send(
            "❌ Gerekli yönetim rolüne sahip değilsin."
        )
        return

    if sure <= 0:
        await ctx.send(
            "❌ Süre 0'dan büyük olmalı."
        )
        return

    saniye = mute_suresi_cevir(
        sure,
        birim
    )

    if saniye is None:
        await ctx.send(
            "❌ Geçersiz süre birimi.\n"
            "Kullanım: `.mute @kişi 5 dakika sebep`"
        )
        return

    rol = ctx.guild.get_role(
        MUTE_ROL_ID
    )

    if rol is None:
        await ctx.send(
            "❌ Mute rolü bulunamadı."
        )
        return

    try:

        await uye.add_roles(
            rol,
            reason=sebep
        )

        await ctx.send(
            f"🔇 {uye.mention} susturuldu.\n"
            f"⏱️ **Süre:** {sure} {birim}\n"
            f"📋 **Sebep:** {sebep}"
        )

        asyncio.create_task(
            mute_suresi_bitir(
                ctx.guild.id,
                uye.id,
                MUTE_ROL_ID,
                saniye
            )
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Mute rolünü veremiyorum."
        )

    except discord.HTTPException:

        await ctx.send(
            "❌ Mute işlemi sırasında bir hata oluştu."
        )


# =========================================================
# UNMUTE
# =========================================================

@bot.command()
async def unmute(
    ctx,
    uye: discord.Member
):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):
        await ctx.send(
            "❌ Gerekli yönetim rolüne sahip değilsin."
        )
        return

    rol = ctx.guild.get_role(
        MUTE_ROL_ID
    )

    if rol is None:
        await ctx.send(
            "❌ Mute rolü bulunamadı."
        )
        return

    try:

        await uye.remove_roles(
            rol,
            reason="Manuel unmute."
        )

        await ctx.send(
            f"🔊 {uye.mention} susturulması kaldırıldı."
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Mute rolünü kaldıramıyorum."
        )

    except discord.HTTPException:

        await ctx.send(
            "❌ Unmute işlemi sırasında bir hata oluştu."
        )


# =========================================================
# GÖNDER
# =========================================================

@bot.command()
async def gonder(
    ctx,
    *,
    mesaj
):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Yetkin yok."
        )

        return

    embed = discord.Embed(
        description=mesaj,
        color=discord.Color.blurple()
    )

    embed.set_author(
        name=ctx.author.display_name,
        icon_url=ctx.author.display_avatar.url
    )

    embed.set_footer(
        text="Premier Support"
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# MESAJ SİL
# =========================================================

@bot.command(
    name="msil"
)
async def msil(
    ctx,
    miktar: int
):

    if not rol_var_mi(
        ctx.author,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanma yetkin yok.",
            delete_after=5
        )

        return

    if miktar <= 0:

        await ctx.send(
            "❌ Silinecek mesaj sayısı 0'dan büyük olmalı.",
            delete_after=5
        )

        return

    if miktar > 100:

        await ctx.send(
            "❌ Tek seferde en fazla **100 mesaj** silebilirsin.",
            delete_after=5
        )

        return

    try:

        # Komut mesajını da dahil ediyoruz.
        silinenler = await ctx.channel.purge(
            limit=miktar + 1
        )

        gercek_sayi = max(
            len(silinenler) - 1,
            0
        )

        await ctx.send(
            f"✅ Başarıyla **{gercek_sayi} mesaj** silindi.",
            delete_after=3
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Mesajları silmek için yetkim yok.",
            delete_after=5
        )

    except discord.HTTPException:

        await ctx.send(
            "❌ Mesajlar silinirken Discord tarafında bir hata oluştu.",
            delete_after=5
        )


# =========================================================
# KOMUT HATALARI / DOĞRU KULLANIM
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    komut = getattr(ctx.command, "name", "")

    kullanimlar = {
        "ban": ".ban @kisi [sebep]",
        "unban": ".unban KULLANICI_ID",
        "mute": ".mute @kisi 5 dakika sebep",
        "unmute": ".unmute @kisi",
        "k": ".k @kisi İsim Soyisim",
        "kver": ".kver @kisi",
        "msil": ".msil 10",
        "ekle": ".ekle @kisi 10 Dribbling",
        "sil": ".sil @kisi 10 Dribbling",
        "haftaliksifirla": ".haftaliksifirla @kisi veya @everyone",
        "alltimesifirla": ".alltimesifirla @kisi veya @everyone",
        "haftaliksifirla": ".haftaliksifirla @kisi",
        "alltimesifirla": ".alltimesifirla @kisi",
        "aktar": ".aktar @kisi",
    }

    if isinstance(error, commands.MissingRequiredArgument):
        kullanim = kullanimlar.get(komut)
        if kullanim:
            await ctx.send(
                f"❌ Eksik bilgi.\n**Doğru kullanım:** `{kullanim}`",
                delete_after=7
            )
        else:
            await ctx.send(
                "❌ Eksik bilgi. Komutun kullanımını kontrol et.",
                delete_after=7
            )
        return

    if isinstance(error, commands.MemberNotFound):
        kullanim = kullanimlar.get(komut)
        await ctx.send(
            "❌ Kullanıcı bulunamadı.\n"
            + (f"**Doğru kullanım:** `{kullanim}`" if kullanim else ""),
            delete_after=7
        )
        return

    if isinstance(error, commands.BadArgument):
        kullanim = kullanimlar.get(komut)
        await ctx.send(
            "❌ Girdi hatalı.\n"
            + (f"**Doğru kullanım:** `{kullanim}`" if kullanim else ""),
            delete_after=7
        )
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Gerekli yetkiye sahip değilsin.",
            delete_after=5
        )
        return

    print(f"Komut hatası ({komut}): {error}")


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(
        f"Bot aktif: {bot.user}"
    )

    # Panel butonlarının restart sonrası çalışmaya
    # devam etmesi için persistent view
    bot.add_view(
        AntSistemView()
    )

    bot.add_view(
        TicketPanelView()
    )

    bot.add_view(
        TicketKapatView()
    )


# =========================================================
# TOKEN
# =========================================================

load_dotenv()

TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN bulunamadı."
    )

bot.run(
    TOKEN
)

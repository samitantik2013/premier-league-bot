import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput
from datetime import timedelta
import random
import re
import os
from dotenv import load_dotenv


# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# =========================================================
# TÜRKÇE KARAKTER NORMALİZASYONU
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
# ROLLER
# =========================================================

YONETIM_ROL_ID = 1553136364789309552
EKLE_SIL_ROL_ID = 1553136385538654329
MUTE_ROL_ID = 1553136389984358552


# =========================================================
# KANALLAR
# =========================================================

ANT_KANAL_ID = 1553136962473304156
PEN_KANAL_ID = 1553136964042227722


# =========================================================
# VERİLER
# =========================================================

haftalik = {}
all_time = {}

antrenman = {}
ant_son_kullanim = {}

pen_son_kullanim = {}


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
# YARDIMCI FONKSİYONLAR
# =========================================================

def rol_var_mi(ctx, rol_id):

    if ctx.guild is None:
        return False

    rol = ctx.guild.get_role(rol_id)

    if rol is None:
        return False

    return rol in ctx.author.roles


def toplam_stat(statlar):
    return sum(statlar.values())


def haftalik_siralama():

    siralama = []

    for user_id, statlar in haftalik.items():

        toplam = toplam_stat(statlar)

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

    for index, (oyuncu_id, toplam) in enumerate(
        siralama,
        start=1
    ):

        if oyuncu_id == user_id:
            return index

    return None


# =========================================================
# İSTATİSTİK EMBED
# =========================================================

def istatistik_embed(user):

    statlar = all_time.get(user.id, {})

    embed = discord.Embed(
        title=f"⚽ {user.display_name} - İstatistikler",
        color=discord.Color.blurple()
    )

    if statlar:

        metin = "\n".join(
            f"**{isim}:** `{deger}`"
            for isim, deger in statlar.items()
        )

    else:

        metin = "Henüz All Time istatistiği bulunmuyor."

    embed.add_field(
        name="🎯 Basılan Nitelikler",
        value=metin,
        inline=False
    )

    toplam = toplam_stat(statlar)

    embed.add_field(
        name="📈 Toplam Stat",
        value=f"**{toplam}**",
        inline=False
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    embed.set_footer(
        text="Premier Support • İstatistikler"
    )

    return embed


# =========================================================
# HAFTALIK OYUNCU EMBED
# =========================================================

def haftalik_embed(user):

    statlar = haftalik.get(user.id, {})

    toplam = toplam_stat(statlar)

    sira = haftalik_sira_bul(user.id)

    if sira is None:
        sira_text = "Sıralamada değil"
    else:
        sira_text = f"🏆 Haftalıkta **{sira}. sıra**"

    embed = discord.Embed(
        title=f"📊 {user.display_name} - Haftalık İstatistikler",
        color=discord.Color.green()
    )

    if statlar:

        metin = "\n".join(
            f"**{isim}:** `{deger}`"
            for isim, deger in statlar.items()
        )

    else:

        metin = "Henüz haftalık istatistik bulunmuyor."

    embed.add_field(
        name="🎯 Haftalık Nitelikler",
        value=metin,
        inline=False
    )

    embed.add_field(
        name="📈 Toplam Stat",
        value=(
            f"**{toplam}**\n"
            f"{sira_text}"
        ),
        inline=False
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    embed.set_footer(
        text="Premier Support • Haftalık İstatistikler"
    )

    return embed


# =========================================================
# İSTATİSTİK BUTONLARI
# =========================================================

class IstatistikView(View):

    def __init__(self, user):

        super().__init__(
            timeout=180
        )

        self.user = user

    @discord.ui.button(
        label="Haftalık",
        emoji="📊",
        style=discord.ButtonStyle.success
    )
    async def haftalik_button(
        self,
        interaction,
        button
    ):

        if interaction.user.id != self.user.id:

            await interaction.response.send_message(
                "❌ Bu menüyü sadece komutu kullanan kişi kullanabilir.",
                ephemeral=True
            )

            return

        await interaction.response.edit_message(
            embed=haftalik_embed(self.user),
            view=self
        )

    @discord.ui.button(
        label="All Time",
        emoji="🏆",
        style=discord.ButtonStyle.primary
    )
    async def alltime_button(
        self,
        interaction,
        button
    ):

        if interaction.user.id != self.user.id:

            await interaction.response.send_message(
                "❌ Bu menüyü sadece komutu kullanan kişi kullanabilir.",
                ephemeral=True
            )

            return

        await interaction.response.edit_message(
            embed=istatistik_embed(self.user),
            view=self
        )


# =========================================================
# HAFTALIK LİDERLİK
# =========================================================

def haftalik_liderlik_embed(page=0):

    siralama = haftalik_siralama()

    oyuncu_sayisi = len(siralama)

    if oyuncu_sayisi == 0:

        embed = discord.Embed(
            title="🏆 HAFTALIK LİDERLİK",
            description=(
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📊 **Henüz sıralama oluşmadı.**\n\n"
                "Oyuncular haftalık stat kazandıkça\n"
                "burada görünmeye başlayacak.\n"
                "━━━━━━━━━━━━━━━━━━━━"
            ),
            color=discord.Color.gold()
        )

        embed.set_footer(
            text="Premier Support • Haftalık Sıralama"
        )

        return embed

    sayfa_basina = 10

    toplam_sayfa = (
        oyuncu_sayisi + sayfa_basina - 1
    ) // sayfa_basina

    if page < 0:
        page = 0

    if page >= toplam_sayfa:
        page = toplam_sayfa - 1

    baslangic = page * sayfa_basina
    bitis = baslangic + sayfa_basina

    sayfadakiler = siralama[
        baslangic:bitis
    ]

    embed = discord.Embed(
        title="🏆 HAFTALIK LİDERLİK",
        description=(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📊 **Haftanın En İyi Oyuncuları**\n"
            "Toplam haftalık statlara göre sıralanır.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.gold()
    )

    satirlar = []

    for index, (user_id, toplam) in enumerate(
        sayfadakiler,
        start=baslangic + 1
    ):

        uye = bot.get_user(user_id)

        if uye is not None:
            isim = uye.display_name
        else:
            isim = f"<@{user_id}>"

        if index == 1:
            sira_emoji = "🥇"

        elif index == 2:
            sira_emoji = "🥈"

        elif index == 3:
            sira_emoji = "🥉"

        else:
            sira_emoji = f"`#{index}`"

        satirlar.append(
            f"{sira_emoji} **{isim}**\n"
            f"   └─ 📈 **{toplam}** toplam stat"
        )

    embed.add_field(
        name="⚡ Sıralama",
        value="\n\n".join(satirlar),
        inline=False
    )

    embed.add_field(
        name="👥 Oyuncu Sayısı",
        value=f"**{oyuncu_sayisi} oyuncu**",
        inline=True
    )

    embed.add_field(
        name="📄 Sayfa",
        value=f"**{page + 1} / {toplam_sayfa}**",
        inline=True
    )

    embed.set_footer(
        text="Premier Support • Haftalık Sıralama"
    )

    return embed


# =========================================================
# HAFTALIK LİDERLİK BUTONLARI
# =========================================================

class HaftalikSiralamaView(View):

    def __init__(self, page=0):

        super().__init__(
            timeout=180
        )

        self.page = page

    @discord.ui.button(
        label="Geri",
        emoji="◀️",
        style=discord.ButtonStyle.secondary
    )
    async def geri(
        self,
        interaction,
        button
    ):

        if self.page <= 0:

            await interaction.response.send_message(
                "❌ Zaten ilk sayfadasın.",
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
        label="İleri",
        emoji="▶️",
        style=discord.ButtonStyle.secondary
    )
    async def ileri(
        self,
        interaction,
        button
    ):

        siralama = haftalik_siralama()

        toplam_sayfa = max(
            1,
            (len(siralama) + 9) // 10
        )

        if self.page >= toplam_sayfa - 1:

            await interaction.response.send_message(
                "❌ Zaten son sayfadasın.",
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
# EKLEME SEBEP MODALI
# =========================================================

class SebepModal(
    Modal,
    title="Stat Ekleme Sebebi"
):

    def __init__(self, request_data):

        super().__init__()

        self.request_data = request_data

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

        self.request_data["sebep"] = self.sebep.value

        await interaction.response.edit_message(
            embed=ekle_onay_embed(
                self.request_data
            ),
            view=EkleOnayView(
                self.request_data
            )
        )


# =========================================================
# EKLEME ONAY EMBED
# =========================================================

def ekle_onay_embed(data):

    oyuncu = data["oyuncu"]

    statlar = data["statlar"]

    sebep = data.get(
        "sebep",
        "Belirtilmedi"
    )

    metin = "\n".join(
        f"**{isim}:** `+{deger}`"
        for isim, deger in statlar.items()
    )

    embed = discord.Embed(
        title="📝 STAT EKLEME TALEBİ",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="👤 Oyuncu",
        value=oyuncu.mention,
        inline=False
    )

    embed.add_field(
        name="🎯 Eklenecek Statlar",
        value=metin,
        inline=False
    )

    embed.add_field(
        name="📋 Sebep",
        value=sebep,
        inline=False
    )

    embed.set_footer(
        text="Premier Support • Stat Onay Sistemi"
    )

    return embed


# =========================================================
# EKLEME ONAY BUTONLARI
# =========================================================

class EkleOnayView(View):

    def __init__(self, data):

        super().__init__(
            timeout=300
        )

        self.data = data

    @discord.ui.button(
        label="Onayla",
        emoji="✅",
        style=discord.ButtonStyle.success
    )
    async def onayla(
        self,
        interaction,
        button
    ):

        if interaction.user.id != self.data["isteyen"]:

            await interaction.response.send_message(
                "❌ Bu talebi sadece komutu kullanan kişi onaylayabilir.",
                ephemeral=True
            )

            return

        oyuncu = self.data["oyuncu"]

        # SADECE HAFTALIK
        if oyuncu.id not in haftalik:
            haftalik[oyuncu.id] = {}

        for isim, deger in self.data["statlar"].items():

            haftalik[oyuncu.id][isim] = (
                haftalik[oyuncu.id].get(
                    isim,
                    0
                ) + deger
            )

        embed = discord.Embed(
            title="✅ STATLAR ONAYLANDI",
            description=(
                f"{oyuncu.mention} oyuncusuna "
                "haftalık statlar başarıyla eklendi."
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="Premier Support • Stat Sistemi"
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
        interaction,
        button
    ):

        if interaction.user.id != self.data["isteyen"]:

            await interaction.response.send_message(
                "❌ Bu talebi sadece komutu kullanan kişi iptal edebilir.",
                ephemeral=True
            )

            return

        embed = discord.Embed(
            title="❌ STAT TALEBİ İPTAL EDİLDİ",
            description="Herhangi bir stat eklenmedi.",
            color=discord.Color.red()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

    @discord.ui.button(
        label="Sebep Gir",
        emoji="📝",
        style=discord.ButtonStyle.primary
    )
    async def sebep_gir(
        self,
        interaction,
        button
    ):

        if interaction.user.id != self.data["isteyen"]:

            await interaction.response.send_message(
                "❌ Bu butonu sadece komutu kullanan kişi kullanabilir.",
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            SebepModal(
                self.data
            )
        )


# =========================================================
# BOT HAZIR
# =========================================================

@bot.event
async def on_ready():

    print(
        f"{bot.user} aktif!"
    )


# =========================================================
# .s
# =========================================================

@bot.command()
async def s(
    ctx,
    uye: discord.Member = None
):

    if uye is None:
        uye = ctx.author

    await ctx.send(
        embed=istatistik_embed(uye),
        view=IstatistikView(uye)
    )


# =========================================================
# .haftalik
# =========================================================

@bot.command()
async def haftalik_cmd(ctx):

    embed = haftalik_liderlik_embed(0)

    await ctx.send(
        embed=embed,
        view=HaftalikSiralamaView(0)
    )


# =========================================================
# .ekle
# =========================================================

@bot.command()
async def ekle(
    ctx,
    uye: discord.Member = None,
    miktar: int = None,
    *,
    statlar: str = None
):

    if not rol_var_mi(
        ctx,
        EKLE_SIL_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None or miktar is None or statlar is None:

        await ctx.send(
            "❌ Kullanım: `.ekle @oyuncu 35 Dribbling`"
        )

        return

    if miktar < 1 or miktar > 49:

        await ctx.send(
            "❌ Stat değeri 1-49 arasında olmalı."
        )

        return

    bulunan = {}

    kalan = statlar

    for stat in sorted(
        STATLAR,
        key=len,
        reverse=True
    ):

        pattern = re.compile(
            re.escape(stat),
            re.IGNORECASE
        )

        if pattern.search(kalan):

            bulunan[stat] = miktar

            kalan = pattern.sub(
                "",
                kalan,
                count=1
            )

    if not bulunan:

        await ctx.send(
            "❌ Geçerli bir stat bulunamadı."
        )

        return

    data = {
        "oyuncu": uye,
        "statlar": bulunan,
        "isteyen": ctx.author.id,
        "sebep": "Belirtilmedi"
    }

    await ctx.send(
        embed=ekle_onay_embed(data),
        view=EkleOnayView(data)
    )


# =========================================================
# .sil
# =========================================================

@bot.command()
async def sil(
    ctx,
    uye: discord.Member = None,
    miktar: int = None,
    *,
    statlar: str = None
):

    if not rol_var_mi(
        ctx,
        EKLE_SIL_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None or miktar is None or statlar is None:

        await ctx.send(
            "❌ Kullanım: `.sil @oyuncu 10 Dribbling`"
        )

        return

    if miktar < 1:

        await ctx.send(
            "❌ Miktar 1 veya daha fazla olmalı."
        )

        return

    if uye.id not in haftalik:

        await ctx.send(
            "❌ Bu oyuncunun haftalık statı yok."
        )

        return

    bulunan = []

    for stat in STATLAR:

        if komut_normalize(stat) in komut_normalize(statlar):
            bulunan.append(stat)

    if not bulunan:

        await ctx.send(
            "❌ Geçerli bir stat bulunamadı."
        )

        return

    for stat in bulunan:

        if stat in haftalik[uye.id]:

            haftalik[uye.id][stat] -= miktar

            if haftalik[uye.id][stat] <= 0:

                del haftalik[uye.id][stat]

    if not haftalik[uye.id]:

        del haftalik[uye.id]

    await ctx.send(
        f"✅ {uye.mention} oyuncusundan haftalık stat düşürüldü."
    )


# =========================================================
# .haftaliksifirla
# =========================================================

@bot.command()
async def haftaliksifirla(
    ctx,
    uye: discord.Member = None
):

    if not rol_var_mi(
        ctx,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Kullanım: `.haftaliksifirla @oyuncu`"
        )

        return

    haftalik.pop(
        uye.id,
        None
    )

    await ctx.send(
        f"🔄 {uye.mention} oyuncusunun haftalık statları sıfırlandı."
    )


# =========================================================
# .alltimesifirla
# =========================================================

@bot.command()
async def alltimesifirla(
    ctx,
    uye: discord.Member = None
):

    if not rol_var_mi(
        ctx,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Kullanım: `.alltimesifirla @oyuncu`"
        )

        return

    all_time.pop(
        uye.id,
        None
    )

    await ctx.send(
        f"🔄 {uye.mention} oyuncusunun All Time statları sıfırlandı."
    )


# =========================================================
# .alltimesil
# =========================================================

@bot.command()
async def alltimesil(
    ctx,
    uye: discord.Member = None,
    miktar: int = None,
    *,
    statlar: str = None
):

    if not rol_var_mi(
        ctx,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None or miktar is None or statlar is None:

        await ctx.send(
            "❌ Kullanım: `.alltimesil @oyuncu 10 Dribbling`"
        )

        return

    if miktar < 1:

        await ctx.send(
            "❌ Miktar 1 veya daha fazla olmalı."
        )

        return

    if uye.id not in all_time:

        await ctx.send(
            "❌ Bu oyuncunun All Time statı yok."
        )

        return

    bulunan = []

    for stat in STATLAR:

        if komut_normalize(stat) in komut_normalize(statlar):
            bulunan.append(stat)

    if not bulunan:

        await ctx.send(
            "❌ Geçerli bir stat bulunamadı."
        )

        return

    for stat in bulunan:

        if stat in all_time[uye.id]:

            all_time[uye.id][stat] -= miktar

            if all_time[uye.id][stat] <= 0:

                del all_time[uye.id][stat]

    if not all_time[uye.id]:

        del all_time[uye.id]

    await ctx.send(
        f"✅ {uye.mention} oyuncusunun All Time statı düşürüldü."
    )


# =========================================================
# .aktar
# =========================================================

@bot.command()
async def aktar(
    ctx,
    uye: discord.Member = None
):

    if not rol_var_mi(
        ctx,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Kullanım: `.aktar @oyuncu`"
        )

        return

    if uye.id not in haftalik:

        await ctx.send(
            "❌ Oyuncunun aktarılacak haftalık statı yok."
        )

        return

    if uye.id not in all_time:
        all_time[uye.id] = {}

    for stat, deger in haftalik[uye.id].items():

        all_time[uye.id][stat] = (
            all_time[uye.id].get(
                stat,
                0
            ) + deger
        )

    await ctx.send(
        f"✅ {uye.mention} oyuncusunun haftalık statları All Time'a aktarıldı."
    )


# =========================================================
# .ban
# =========================================================

@bot.command()
async def ban(
    ctx,
    uye: discord.Member = None
):

    if not rol_var_mi(
        ctx,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Kullanım: `.ban @oyuncu`"
        )

        return

    if uye.id == ctx.author.id:

        await ctx.send(
            "❌ Kendini banlayamazsın."
        )

        return

    try:

        await uye.ban(
            reason=f"{ctx.author} tarafından banlandı."
        )

        embed = discord.Embed(
            title="🔨 Oyuncu Banlandı",
            description=f"{uye.mention} sunucudan banlandı.",
            color=discord.Color.red()
        )

        await ctx.send(
            embed=embed
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Bu oyuncuyu banlamak için yetkim yok."
        )


# =========================================================
# .unban
# =========================================================

@bot.command()
async def unban(
    ctx,
    kullanici_id: str = None
):

    if not rol_var_mi(
        ctx,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if kullanici_id is None:

        await ctx.send(
            "❌ Kullanım: `.unban ID`"
        )

        return

    match = re.fullmatch(
        r"<@!?(\d+)>",
        kullanici_id.strip()
    )

    if match:
        kullanici_id = match.group(1)

    try:

        user = await bot.fetch_user(
            int(kullanici_id)
        )

        await ctx.guild.unban(
            user,
            reason=f"{ctx.author} tarafından unban."
        )

        embed = discord.Embed(
            title="🔓 Ban Kaldırıldı",
            description=f"**{user}** kullanıcısının banı kaldırıldı.",
            color=discord.Color.green()
        )

        await ctx.send(
            embed=embed
        )

    except ValueError:

        await ctx.send(
            "❌ Geçerli bir kullanıcı ID'si gir."
        )

    except discord.NotFound:

        await ctx.send(
            "❌ Bu kullanıcı banlı değil veya bulunamadı."
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Ban kaldırmak için yetkim yok."
        )


# =========================================================
# .mute
# =========================================================

@bot.command()
async def mute(
    ctx,
    uye: discord.Member = None
):

    if not rol_var_mi(
        ctx,
        MUTE_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Kullanım: `.mute @oyuncu`"
        )

        return

    try:

        await uye.timeout(
            timedelta(minutes=5),
            reason=f"{ctx.author} tarafından 5 dakika mute."
        )

        embed = discord.Embed(
            title="🔇 Oyuncu Susturuldu",
            description=f"{uye.mention} **5 dakika** boyunca susturuldu.",
            color=discord.Color.orange()
        )

        await ctx.send(
            embed=embed
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Bu oyuncuyu susturmak için yetkim yok."
        )


# =========================================================
# .unmute
# =========================================================

@bot.command()
async def unmute(
    ctx,
    uye: discord.Member = None
):

    if not rol_var_mi(
        ctx,
        MUTE_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    if uye is None:

        await ctx.send(
            "❌ Kullanım: `.unmute @oyuncu`"
        )

        return

    try:

        await uye.timeout(
            None,
            reason=f"{ctx.author} tarafından mute kaldırıldı."
        )

        embed = discord.Embed(
            title="🔊 Oyuncunun Mute'u Kaldırıldı",
            description=f"{uye.mention} artık susturulmuyor.",
            color=discord.Color.green()
        )

        await ctx.send(
            embed=embed
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ Bu oyuncunun mute'unu kaldırmak için yetkim yok."
        )


# =========================================================
# .gonder
# =========================================================

@bot.command()
async def gonder(ctx, *, mesaj):

    if not rol_var_mi(
        ctx,
        YONETIM_ROL_ID
    ):

        await ctx.send(
            "❌ Bu komutu kullanmak için yetkin yok."
        )

        return

    embed = discord.Embed(
        description=mesaj
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
# .ant
# =========================================================

@bot.command()
async def ant(ctx):

    if ctx.channel.id != ANT_KANAL_ID:

        await ctx.send(
            f"❌ Bu komut sadece <#{ANT_KANAL_ID}> kanalında kullanılabilir."
        )

        return

    simdi = discord.utils.utcnow()
    user_id = ctx.author.id

    if user_id in ant_son_kullanim:

        fark = simdi - ant_son_kullanim[user_id]

        if fark.total_seconds() < 3600:

            kalan = 3600 - int(fark.total_seconds())

            dakika = kalan // 60
            saniye = kalan % 60

            embed = discord.Embed(
                title="⏳ ANTRENMAN BEKLEMEDE",
                description=(
                    f"{ctx.author.mention}\n\n"
                    "Bir sonraki antrenmana:\n"
                    f"**{dakika} dakika {saniye} saniye** kaldı."
                ),
                color=discord.Color.orange()
            )

            await ctx.send(embed=embed)

            return

    ant_son_kullanim[user_id] = simdi

    mevcut = antrenman.get(user_id, 0) + 1

    antrenman[user_id] = mevcut

    dolu = "🟩" * mevcut
    bos = "⬜" * (10 - mevcut)

    if mevcut >= 10:

        embed = discord.Embed(
            title="🏋️ ANTRENMAN",
            description=(
                f"{ctx.author.mention}\n\n"
                f"{dolu}\n\n"
                "🏆 **ANTRENMAN TAMAMLANDI!**\n\n"
                "10/10 antrenman tamamlandı.\n"
                "Yeni seri başlatıldı."
            ),
            color=discord.Color.gold()
        )

        antrenman[user_id] = 0

    else:

        embed = discord.Embed(
            title="🏋️ ANTRENMAN",
            description=(
                f"{ctx.author.mention}\n\n"
                f"{dolu}{bos}\n\n"
                f"**İlerleme:** `{mevcut}/10`\n\n"
                "⏱️ Bir sonraki antrenman: **1 saat sonra**"
            ),
            color=discord.Color.green()
        )

    embed.set_footer(
        text="Premier Support • Antrenman Sistemi"
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# .pen
# =========================================================

@bot.command()
async def pen(ctx):

    if ctx.channel.id != PEN_KANAL_ID:

        await ctx.send(
            f"❌ Bu komut sadece <#{PEN_KANAL_ID}> kanalında kullanılabilir."
        )

        return

    simdi = discord.utils.utcnow()
    user_id = ctx.author.id

    if user_id in pen_son_kullanim:

        fark = simdi - pen_son_kullanim[user_id]

        if fark.total_seconds() < 3600:

            kalan = 3600 - int(fark.total_seconds())

            dakika = kalan // 60
            saniye = kalan % 60

            embed = discord.Embed(
                title="⏳ PENALTI BEKLEMEDE",
                description=(
                    f"{ctx.author.mention}\n\n"
                    "Yeni penaltı kullanabilmek için:\n"
                    f"**{dakika} dakika {saniye} saniye** beklemelisin."
                ),
                color=discord.Color.orange()
            )

            await ctx.send(embed=embed)

            return

    pen_son_kullanim[user_id] = simdi

    sonuc = random.choice([
        "gol",
        "kaleci",
        "direk",
        "aut"
    ])

    if sonuc == "gol":

        title = "⚽ PENALTI GOL!"

        description = (
            f"{ctx.author.mention}\n\n"
            "🎯 **GOOOL!**\n"
            "Kaleci ters köşeye gitti."
        )

        color = discord.Color.green()

    elif sonuc == "kaleci":

        title = "🧤 KALECİ KURTARDI!"

        description = (
            f"{ctx.author.mention}\n\n"
            "🧤 **KALECİ KURTARDI!**\n"
            "Harika bir kurtarış."
        )

        color = discord.Color.red()

    elif sonuc == "direk":

        title = "💥 DİREK!"

        description = (
            f"{ctx.author.mention}\n\n"
            "💥 **DİREK!**\n"
            "Top direkten döndü."
        )

        color = discord.Color.orange()

    else:

        title = "💨 AUT!"

        description = (
            f"{ctx.author.mention}\n\n"
            "💨 **AUT!**\n"
            "Top kaleyi bulmadı."
        )

        color = discord.Color.light_grey()

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.add_field(
        name="🎲 Olasılıklar",
        value=(
            "⚽ Gol — **25%**\n"
            "🧤 Kaleci Kurtarır — **25%**\n"
            "💥 Direk — **25%**\n"
            "💨 Aut — **25%**\n"
        ),
        inline=False
    )

    embed.set_footer(
        text="Premier Support • Penaltı Sistemi"
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# TOKEN
# =========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

bot.run(TOKEN)

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

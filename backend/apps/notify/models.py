from django.db import models

from apps.tenants.models import SalonModel


class TelegramUlash(SalonModel):
    """Xodim Telegram akkauntini botga ulashi uchun bir martalik kod (`/start <kod>`)."""
    xodim = models.ForeignKey('tenants.Xodim', on_delete=models.CASCADE, related_name='+')
    kod = models.CharField(max_length=16, unique=True)
    tugaydi = models.DateTimeField()


class Xabar(SalonModel):
    """Telegram xabarlari navbati va jurnali. Bot sozlanmagan yoki xodim ulanmagan bo'lsa ham yozuv qoladi."""

    class Holat(models.TextChoices):
        KUTILMOQDA = 'kutilmoqda', 'Kutilmoqda'
        YUBORILDI = 'yuborildi', 'Yuborildi'
        XATO = 'xato', 'Xato'
        ULANMAGAN = 'ulanmagan', 'Xodim Telegram ulamagan'

    xodim = models.ForeignKey('tenants.Xodim', on_delete=models.CASCADE, related_name='+')
    tur = models.CharField(max_length=40)
    matn = models.TextField()
    tugmalar = models.JSONField(null=True, blank=True)  # [[{text, callback_data}], ...]
    kalit = models.CharField(max_length=80, blank=True)  # takror yubormaslik uchun (masalan, eslatma + sana)
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.KUTILMOQDA)
    xato_matni = models.CharField(max_length=300, blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    yuborilgan = models.DateTimeField(null=True, blank=True)
    # Shu vaqtgacha navbatda kutadi: xodim botda tinch vaqt yoki jamlanma tanlagan (bo'sh — darhol)
    keyin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['xodim', 'kalit'], condition=~models.Q(kalit=''),
                                    name='xabar_takrorlanmaydi'),
        ]


class Yurak(models.Model):
    """Fon vazifasi yoki bot jarayoni oxirgi marta qachon ishlagani (apps/notify/yurak.py). Salonga bog'liq emas."""
    nom = models.CharField(max_length=20, unique=True)
    vaqt = models.DateTimeField()
    ogohlantirildi = models.DateTimeField(null=True, blank=True)  # egaga «to'xtagan» deb yozilgan vaqt


class KirishKodi(models.Model):
    """Rahbar kirishi uchun Telegramga yuboriladigan bir martalik kod (FT-1.1, FT-22.3)."""
    xodim = models.OneToOneField('tenants.Xodim', on_delete=models.CASCADE, related_name='kirish_kodi')
    kod = models.CharField(max_length=128)  # xesh
    tugaydi = models.DateTimeField()
    urinish = models.PositiveSmallIntegerField(default=0)
    # Telegramdagi «Ruxsat berish» tugmasi: kod terish o'rniga — faqat so'ralgan qurilmadagi kirishga amal qiladi
    qurilma = models.ForeignKey('tenants.IshonchliQurilma', null=True, blank=True, on_delete=models.CASCADE, related_name='+')
    tasdiqlandi = models.DateTimeField(null=True, blank=True)


class SmsXabar(SalonModel):
    """Mijozga yuborilgan SMS lar jurnali va navbati (Eskiz.uz)."""

    class Holat(models.TextChoices):
        KUTILMOQDA = 'kutilmoqda', 'Kutilmoqda'
        YUBORILDI = 'yuborildi', 'Yuborildi'
        XATO = 'xato', 'Xato'

    zakaz = models.ForeignKey('orders.Zakaz', null=True, blank=True, on_delete=models.CASCADE, related_name='+')
    telefon = models.CharField(max_length=20)
    tur = models.CharField(max_length=40)
    matn = models.CharField(max_length=400)
    kalit = models.CharField(max_length=80)  # bitta zakazga bitta turdagi eslatma bir marta
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.KUTILMOQDA)
    xato_matni = models.CharField(max_length=300, blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    yuborilgan = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['salon', 'kalit'], name='sms_takrorlanmaydi'),
        ]


class TugmaBosish(models.Model):
    """Bot tugmalari statistikasi: kuniga har tugma necha marta bosilgani (keyingi soddalashtirish raqam bilan bo'lsin).

    Kim bosgani saqlanmaydi — faqat soni. «🩺 Holat» da oxirgi 30 kun ko'rsatiladi.
    """
    nom = models.CharField(max_length=40)  # 'menyu:bugun', 'tugma:kassa', 'yozish:qidiruv', 'eski:tolov' …
    sana = models.DateField()
    soni = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['nom', 'sana'], name='tugma_bosish_kunlik')]


class Murojaat(models.Model):
    """Qo'llab-quvvatlash: botdagi foydalanuvchi xabari platforma egasiga uzatilgan (har xabar — bitta qator).

    Ega javobni Telegramda shu xabarga «reply» qilib yozadi; javob qaysi chatga ketishi faqat shu qatordan olinadi
    (ega chati + undagi xabar raqami bo'yicha — Telegramda xabar raqami faqat bitta chat ichida noyob).
    """
    chat_id = models.BigIntegerField(db_index=True)                    # yozgan foydalanuvchining chati
    foydalanuvchi_xabar_id = models.BigIntegerField()                  # javob shu xabarga «reply» bo'lib boradi
    ega_chat_id = models.BigIntegerField()
    ega_xabar_id = models.BigIntegerField()                            # egadagi nusxa — ega shunga javob beradi
    ega_sarlavha_id = models.BigIntegerField(null=True, blank=True)    # izohsiz turlar (stiker…): sarlavha alohida xabar
    # Xabar matni va ismlar saqlanmaydi — ular Telegram chatlarida; bu yerda faqat yo'naltirish uchun raqamlar.
    # Salon o'chirilsa qatorlari ham o'chadi (tenants/arxiv.py `salon` maydoni bor modellarni o'zi topadi).
    xodim = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    salon = models.ForeignKey('tenants.Salon', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    yaratilgan = models.DateTimeField(auto_now_add=True)
    javob_berildi = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['ega_chat_id', 'ega_xabar_id'], name='murojaat_ega_xabari'),
                   models.Index(fields=['ega_chat_id', 'ega_sarlavha_id'], name='murojaat_ega_sarlavhasi')]


class YordamRejimi(models.Model):
    """Foydalanuvchi «qo'llab-quvvatlashga yozish» rejimida: shu vaqtgacha uning xabarlari egaga uzatiladi.

    Bazada (keshda emas): bot qayta ishga tushsa ham rejim yo'qolmaydi va xabar tasodifan zakaz qidiruviga tushmaydi.
    `xodim` — ilovadagi havola orqali kelganda havolani yaratgan xodim (kim ochgani emas).
    """
    chat_id = models.BigIntegerField(unique=True)
    xodim = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    tugaydi = models.DateTimeField()

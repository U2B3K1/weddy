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


class BilimMaqola(models.Model):
    """Qo'llab-quvvatlash bilim bazasi: bitta savol va unga tayyor javob. Agent faqat shu javoblardan birini tanlaydi
    va uni so'zma-so'z yuboradi (o'zi matn yozmaydi). Faqat `faol` maqolalar ishlatiladi; qoralamalarni ega tekshirib yoqadi."""
    class Manba(models.TextChoices):
        QORALAMA = 'qoralama', 'Qoralama (dasturchi tayyorlagan)'
        EGA = 'ega', 'Ega javobidan'
        QOLDA = 'qolda', "Ega qo'lda yozgan"

    savol = models.CharField(max_length=300)
    javob = models.TextField(max_length=2000)
    faol = models.BooleanField(default=False)
    manba = models.CharField(max_length=10, choices=Manba.choices, default=Manba.QOLDA)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    ozgargan = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['savol']

    def __str__(self):
        return self.savol


class AgentTaklif(models.Model):
    """Agent ishi: murojaat navbatga tushadi (bot jarayoni ishlaydi — so'rov kutmasin), taklif guruh mavzusiga
    «✅ Yuborish / ❌ Kerak emas» tugmalari bilan chiqadi. `savol` — telefon/karta raqamlari yashirilgan matn;
    «📚 Bazaga qo'shish» uchun saqlanadi va 30 kundan keyin o'chiriladi (agent.tozala)."""
    class Holat(models.TextChoices):
        NAVBATDA = 'navbatda', 'Navbatda'
        TAKLIF = 'taklif', 'Taklif qilindi'
        TOPILMADI = 'topilmadi', "Bazada yo'q"
        YUBORILDI = 'yuborildi', 'Yuborildi'
        RAD = 'rad', 'Kerak emas'
        TAHRIR = 'tahrir', 'Ega tahrirlamoqda'
        XATO = 'xato', 'Xato'

    murojaat = models.ForeignKey(Murojaat, on_delete=models.CASCADE, related_name='+')
    savol = models.TextField(max_length=4096)
    maqola = models.ForeignKey(BilimMaqola, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    holat = models.CharField(max_length=10, choices=Holat.choices, default=Holat.NAVBATDA)
    taklif_xabar_id = models.BigIntegerField(null=True, blank=True)   # mavzudagi taklif xabari (tugmalari bilan)
    javob = models.TextField(blank=True)  # agent yozgan javob (bilim bazasi asosida) — ega tasdiqlasa shu ketadi
    ega_javobi = models.TextField(blank=True)                          # «📚 Bazaga qo'shish» uchun
    bazada = models.BooleanField(default=False)
    xato = models.CharField(max_length=300, blank=True)
    # Ovozli xabar yoki rasm (OpenAI): Telegram fayl raqami va turi ('ovoz' | 'rasm'). Ovoz matnga aylangach `savol` ga
    # yoziladi; fayl o'zi saqlanmaydi. `baho` — foydalanuvchi bahosi avtomatik javobga: 'ha' (👍) yoki 'yoq' (👎)
    fayl_id = models.CharField(max_length=200, blank=True)
    fayl_turi = models.CharField(max_length=5, blank=True)
    baho = models.CharField(max_length=3, blank=True)
    # «Bot javob bera olmagan savollar» ro'yxatida ega ko'rib chiqdi (maqola yozdi yoki «kerak emas» dedi)
    korildi = models.BooleanField(default=False)
    yaratilgan = models.DateTimeField(auto_now_add=True)


class YordamMavzu(models.Model):
    """Qo'llab-quvvatlash guruhidagi mavzu: bitta murojaatchi (Telegram chati) — bitta mavzu.

    Foydalanuvchi xabarlari shu mavzuga tushadi; ega mavzu ichida yozgan xabar shu chatga javob bo'lib boradi.
    Guruh almashtirilsa (boshqa guruh ulansa) — eski mavzular ishlatilmaydi (`guruh_id` bo'yicha).
    """
    chat_id = models.BigIntegerField()
    guruh_id = models.BigIntegerField()
    mavzu_id = models.BigIntegerField()                 # message_thread_id
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['guruh_id', 'chat_id'], name='yordam_mavzu_chat'),
                       models.UniqueConstraint(fields=['guruh_id', 'mavzu_id'], name='yordam_mavzu_id')]


class YordamRejimi(models.Model):
    """Foydalanuvchi «qo'llab-quvvatlashga yozish» rejimida: shu vaqtgacha uning xabarlari egaga uzatiladi.

    Bazada (keshda emas): bot qayta ishga tushsa ham rejim yo'qolmaydi va xabar tasodifan zakaz qidiruviga tushmaydi.
    `xodim` — ilovadagi havola orqali kelganda havolani yaratgan xodim (kim ochgani emas).
    """
    chat_id = models.BigIntegerField(unique=True)
    xodim = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    tugaydi = models.DateTimeField()
    # Ega shu odamga oxirgi marta o'zi javob yozgan vaqt: shundan keyin bir muddat bot aralashmaydi (jonli suhbat)
    ega_yozdi = models.DateTimeField(null=True, blank=True)


class MenyuXabari(models.Model):
    """Tugma bilan chaqirilgan bot javobi («📊 Bugun», «✅ Qarorlar», xabar ostidagi tugmalar). Keyingi tugma
    bosilganda bu xabarlar va foydalanuvchining tugma xabari o'chiriladi — chatda faqat oxirgi ekran va avtomatik
    xabarlar (eslatma, hisobot, so'rovlar) qoladi (egasi so'rovi, 2026-11-27). Telegram faqat 48 soatgacha bo'lgan
    xabarni o'chirishga ruxsat beradi; eskisi qatordan o'chiriladi, xabar chatda qoladi."""
    chat_id = models.BigIntegerField()
    bot = models.CharField(max_length=20, blank=True)  # salonning o'z boti bo'lsa token raqam qismi; '' — asosiy bot
    xabar_id = models.BigIntegerField()
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['chat_id', 'bot'], name='menyu_xabari_chat')]

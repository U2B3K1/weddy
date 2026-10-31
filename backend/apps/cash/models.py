from django.db import models
from django.db.models import Q

from apps.tenants.models import SalonModel


class Smena(SalonModel):
    """Salonda bitta jismoniy kassa va bitta umumiy smena (FT-12.7)."""
    sana = models.DateField()
    ochgan = models.ForeignKey('tenants.Xodim', on_delete=models.PROTECT, related_name='+')
    ochilgan = models.DateTimeField(auto_now_add=True)
    boshlangich_qoldiq = models.BigIntegerField(default=0)
    hisobdagi_qoldiq = models.BigIntegerField(null=True, blank=True)
    fakt_qoldiq = models.BigIntegerField(null=True, blank=True)
    farq = models.BigIntegerField(null=True, blank=True)
    izoh = models.CharField(max_length=300, blank=True)
    yopilgan = models.DateTimeField(null=True, blank=True)
    # Kunlik zalog tekshiruvi natijasi (FT-12.5), smena yopilganda yoziladi
    zalog_tekshirilmagan = models.PositiveSmallIntegerField(default=0)
    zalog_yoq = models.PositiveSmallIntegerField(default=0)
    # Yopilganda seyfda qolgan naqd (rahbarga topshirilsa 0): ertaga ochuvchining boshlang'ich qoldig'i shunga solishtiriladi
    seyfda = models.BigIntegerField(null=True, blank=True)
    # Terminal sverkasi: smena yopishda terminaldan olingan summa tizimdagi terminal to'lovlari bilan solishtiriladi
    terminal_tizimda = models.BigIntegerField(null=True, blank=True)
    terminal_sverka = models.BigIntegerField(null=True, blank=True)
    terminal_farq = models.BigIntegerField(null=True, blank=True)
    # Filial kassasi yoqilgan bo'lsa smena filialga tegishli; bo'sh — salonning umumiy kassasi
    filial = models.ForeignKey('tenants.Filial', null=True, blank=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        constraints = [
            # Bir vaqtda bitta ochiq umumiy smena va har filialda bittadan ochiq smena
            models.UniqueConstraint(fields=['salon'], condition=Q(yopilgan__isnull=True, filial__isnull=True),
                                    name='salonda_bitta_ochiq_smena'),
            models.UniqueConstraint(fields=['salon', 'filial'], condition=Q(yopilgan__isnull=True, filial__isnull=False),
                                    name='filialda_bitta_ochiq_smena'),
        ]


class SmenaIshtirokchi(SalonModel):
    smena = models.ForeignKey(Smena, on_delete=models.CASCADE, related_name='ishtirokchilar')
    xodim = models.ForeignKey('tenants.Xodim', on_delete=models.PROTECT, related_name='+')
    qoshilgan = models.DateTimeField(auto_now_add=True)
    chiqqan = models.DateTimeField(null=True, blank=True)
    sanalgan_summa = models.BigIntegerField(null=True, blank=True)  # chiqishdagi naqd (FT-12.9)
    farq = models.BigIntegerField(null=True, blank=True)


class Tolov(SalonModel):
    class Tur(models.TextChoices):
        AVANS = 'avans', 'Avans'
        QOLDIQ = 'qoldiq', "Qoldiq to'lov"
        JARIMA = 'jarima', 'Jarima'
        ZALOG = 'zalog', 'Zalog'
        ZALOG_QAYTARISH = 'zalog_qaytarish', 'Zalogni qaytarish'
        VOZVRAT = 'vozvrat', 'Pulni qaytarish'
        XARAJAT = 'xarajat', 'Xarajat'
        INKASSATSIYA = 'inkassatsiya', 'Inkassatsiya'

    class Usul(models.TextChoices):
        NAQD = 'naqd', 'Naqd'
        KARTA = 'karta', 'Terminal'                 # kartadan terminal orqali — smena yopishda sverka bilan solishtiriladi
        OTKAZMA = 'otkazma', "O'tkazma"           # karta raqamiga o'tkazma — rahbar Telegramda «keldi» deb tasdiqlaydi
        CLICK = 'click', 'Click'
        PAYME = 'payme', 'Payme'

    class Tasdiq(models.TextChoices):
        KERAK_EMAS = '', 'Kerak emas'
        KUTILMOQDA = 'kutilmoqda', "Rahbar tasdig'i kutilmoqda"
        KELDI = 'keldi', 'Keldi'
        KELMADI = 'kelmadi', 'Kelmadi'

    zakaz = models.ForeignKey('orders.Zakaz', null=True, blank=True, on_delete=models.PROTECT,
                              related_name='tolovlar')
    smena = models.ForeignKey(Smena, on_delete=models.PROTECT, related_name='tolovlar')
    tur = models.CharField(max_length=16, choices=Tur.choices)
    usul = models.CharField(max_length=8, choices=Usul.choices, default=Usul.NAQD)
    summa = models.PositiveIntegerField()
    izoh = models.CharField(max_length=300, blank=True)
    xodim = models.ForeignKey('tenants.Xodim', on_delete=models.PROTECT, related_name='+')
    vaqt = models.DateTimeField(auto_now_add=True)
    # O'tkazma: pul rahbar hisobiga tushganini rahbar tasdiqlaydi; «kelmadi» — to'lov hisobga olinmaydi
    tasdiq = models.CharField(max_length=10, choices=Tasdiq.choices, blank=True, default='')
    tasdiqlagan = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    tasdiq_vaqti = models.DateTimeField(null=True, blank=True)

    KIRIM = ('avans', 'qoldiq', 'jarima', 'zalog')
    CHIQIM = ('zalog_qaytarish', 'vozvrat', 'xarajat', 'inkassatsiya')
    OTKAZMA_USULLARI = ('otkazma',)  # Click/Payme hozircha ishlatilmaydi (foydalanuvchi qarori, 2026-11-01)
    HAQIQIY = ~Q(tasdiq='kelmadi')  # hisobga olinadigan to'lovlar (rahbar «kelmadi» demaganlari)


class KassaTopshirish(SalonModel):
    """Naqd pulni topshirish: har xodim o'z qo'lidagi pulga javob beradi va uni boshqa xodimga (smenadan
    ketayotganda) yoki rahbarga beradi. Qabul qiluvchi Telegramda yoki ilovada tasdiqlaydi — keyin tortishuv bo'lmaydi.

    `hisobdagi` — topshiruvchining tizim bo'yicha qoldig'i (to'liq topshirishda); `summa` — topshiruvchi aytgani;
    `qabul_summa` — qabul qiluvchi sanagani. To'liq topshirishda farq = qabul qilingan − hisobdagi, topshiruvchiga yoziladi.
    """
    class Holat(models.TextChoices):
        KUTILMOQDA = 'kutilmoqda', 'Tasdiq kutilmoqda'
        QABUL = 'qabul', 'Qabul qilindi'

    smena = models.ForeignKey(Smena, on_delete=models.PROTECT, related_name='topshiriqlar')
    kimdan = models.ForeignKey('tenants.Xodim', on_delete=models.PROTECT, related_name='+')
    kimga = models.ForeignKey('tenants.Xodim', on_delete=models.PROTECT, related_name='+')
    rahbarga = models.BooleanField(default=False)  # pul kassadan chiqadi (inkassatsiya); aks holda smenadagi xodimga
    toliq = models.BooleanField(default=True)      # topshiruvchi bor pulini beradi (smenadan chiqish yoki yopish)
    smena_yopishda = models.BooleanField(default=False)
    ishtirokchi = models.ForeignKey(SmenaIshtirokchi, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    tolov = models.OneToOneField(Tolov, null=True, blank=True, on_delete=models.PROTECT, related_name='topshirish')
    hisobdagi = models.BigIntegerField()
    summa = models.BigIntegerField()
    qabul_summa = models.BigIntegerField(null=True, blank=True)
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.KUTILMOQDA)
    izoh = models.CharField(max_length=300, blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    qabul_vaqti = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']


class ZalogTekshiruvi(SalonModel):
    """Kun oxirida salonda saqlanayotgan hujjat/tillo zalog «joyida» deb belgilanadi (FT-12.5)."""
    smena = models.ForeignKey(Smena, on_delete=models.CASCADE, related_name='zalog_tekshiruvlari')
    zalog = models.ForeignKey('orders.Zalog', on_delete=models.CASCADE, related_name='tekshiruvlar')
    joyida = models.BooleanField()
    izoh = models.CharField(max_length=300, blank=True)
    xodim = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    vaqt = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['smena', 'zalog'], name='smenada_zalog_bir_marta'),
        ]

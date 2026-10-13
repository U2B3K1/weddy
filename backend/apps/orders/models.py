from django.db import models

from apps.catalog.models import Libos
from apps.tenants.models import SalonModel


class Mijoz(SalonModel):
    class Manba(models.TextChoices):
        INSTAGRAM = 'instagram', 'Instagram'
        TAVSIYA = 'tavsiya', 'Tavsiya'
        SALONCHI = 'salonchi', 'Salonchi'
        BOSHQA = 'boshqa', 'Boshqa'

    fio = models.CharField(max_length=200, blank=True)
    telefon = models.CharField(max_length=20)
    qoshimcha_telefon = models.CharField(max_length=20, blank=True)
    toy_sanasi = models.DateField(null=True, blank=True)
    manba = models.CharField(max_length=12, choices=Manba.choices, default=Manba.BOSHQA)
    qora_royxat = models.BooleanField(default=False)  # FT-8.3
    qora_royxat_sabab = models.CharField(max_length=300, blank=True)
    # O'lchamlar (ixtiyoriy, sm; FT-8.4): primerkada yangilanadi
    kokrak = models.PositiveSmallIntegerField(null=True, blank=True)
    bel = models.PositiveSmallIntegerField(null=True, blank=True)
    son = models.PositiveSmallIntegerField(null=True, blank=True)
    boy = models.PositiveSmallIntegerField(null=True, blank=True)
    oyoq_olchami = models.PositiveSmallIntegerField(null=True, blank=True)
    kiyim_olchami = models.CharField(max_length=20, blank=True)  # libos o'lchami bilan bir xil yoziladi (44, M ...)
    izoh = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['salon', 'telefon'], name='mijoz_telefoni_salonda_noyob'),
        ]

    def __str__(self):
        return f'{self.fio} {self.telefon}'


class Salonchi(SalonModel):
    """Makiyaj ustasi (4.6). Komissiya yoki bonus berilmaydi — faqat statistika uchun yoziladi (FT-6.5)."""
    ism = models.CharField(max_length=200)
    telefon = models.CharField(max_length=20, blank=True)
    instagram = models.CharField(max_length=200, blank=True)  # portfolio havolasi
    salon_nomi = models.CharField(max_length=200, blank=True)
    manzil = models.CharField(max_length=300, blank=True)
    izoh = models.CharField(max_length=300, blank=True)
    faol = models.BooleanField(default=True)

    class Meta:
        ordering = ['ism']

    def __str__(self):
        return self.ism


class Zakaz(SalonModel):
    class Holat(models.TextChoices):
        VAQTINCHALIK = 'vaqtinchalik', 'Vaqtinchalik bron'
        CHEGIRMA_KUTILMOQDA = 'chegirma_kutilmoqda', "Chegirma tasdig'i kutilmoqda"
        BRON = 'bron', 'Bron'
        BERILDI = 'berildi', 'Berildi'
        QAYTARILDI = 'qaytarildi', 'Qaytarildi'
        YOPILDI = 'yopildi', 'Yopildi'
        BEKOR = 'bekor', 'Bekor qilingan'

    raqam = models.PositiveIntegerField()  # salon ichida noyob (FT-22.4)
    mijoz = models.ForeignKey(Mijoz, on_delete=models.PROTECT, related_name='zakazlar')
    sotuvchi = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    salonchi = models.ForeignKey(Salonchi, null=True, blank=True, on_delete=models.SET_NULL, related_name='zakazlar')
    filial = models.ForeignKey('tenants.Filial', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')  # rasmiylashtirilgan joy
    holat = models.CharField(max_length=24, choices=Holat.choices, default=Holat.VAQTINCHALIK)
    olib_ketish = models.DateField()
    qaytarish = models.DateField()
    # Narx hisobi (FT-4.3); so'mda
    asosiy_narx = models.PositiveIntegerField(default=0)
    ustama_foiz = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ustama = models.PositiveIntegerField(default=0)
    chegirma = models.PositiveIntegerField(default=0)
    jami = models.PositiveIntegerField(default=0)
    tolangan_sana = models.DateField(null=True, blank=True)  # daromad shu kuni tan olinadi (6.1)
    # Promokod (4.18): `chegirma` — jami chegirma, `promokod_chegirma` — uning promokodga tegishli qismi
    promokod = models.ForeignKey('Promokod', null=True, blank=True, on_delete=models.SET_NULL, related_name='zakazlar')
    promokod_chegirma = models.PositiveIntegerField(default=0)
    xizmatlar = models.PositiveIntegerField(default=0)  # qo'shimcha xizmatlar (moslash); asosiy narx ichida (FT-4.3)
    # Bekor qilish (4.17): qaytarilmagan avans «boshqa daromad»ga o'tadi (6.1)
    bekor_sabab = models.CharField(max_length=300, blank=True)
    bekor_vaqti = models.DateTimeField(null=True, blank=True)
    qaytarilgan_avans = models.PositiveIntegerField(default=0)
    ushlab_qolingan_avans = models.PositiveIntegerField(default=0)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-raqam']
        constraints = [
            models.UniqueConstraint(fields=['salon', 'raqam'], name='zakaz_raqami_salonda_noyob'),
        ]

    def __str__(self):
        return f'#{self.raqam}'


class ZakazPozitsiya(SalonModel):
    zakaz = models.ForeignKey(Zakaz, on_delete=models.CASCADE, related_name='pozitsiyalar')
    libos = models.ForeignKey(Libos, on_delete=models.PROTECT, related_name='+')
    narx = models.PositiveIntegerField()  # zakaz paytidagi ijara narxi (keyin o'zgarsa ta'sir qilmaydi)
    zalog = models.PositiveIntegerField(default=0)


class Zalog(SalonModel):
    class Turi(models.TextChoices):
        PUL = 'pul', 'Pul'
        HUJJAT = 'hujjat', 'Hujjat'
        TILLO = 'tillo', 'Tillo buyum'

    class Holat(models.TextChoices):
        SAQLANMOQDA = 'saqlanmoqda', 'Saqlanmoqda'
        QAYTARILDI = 'qaytarildi', 'Qaytarildi'
        USHLAB_QOLINDI = 'ushlab_qolindi', 'Jarima uchun ushlab qolindi'

    zakaz = models.ForeignKey(Zakaz, on_delete=models.PROTECT, related_name='zaloglar')
    turi = models.CharField(max_length=8, choices=Turi.choices)
    holat = models.CharField(max_length=16, choices=Holat.choices, default=Holat.SAQLANMOQDA)
    summa = models.PositiveIntegerField(default=0)  # pul zalogi yoki taxminiy qiymat
    tavsif = models.CharField(max_length=300, blank=True)
    hujjat_turi = models.CharField(max_length=50, blank=True)
    hujjat_raqami = models.CharField(max_length=50, blank=True)
    ogirlik_gr = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    yorliq = models.CharField(max_length=20, blank=True)  # seyfdagi raqamli yorliq (FT-7.5)
    olingan = models.DateTimeField(auto_now_add=True)
    qaytarilgan = models.DateTimeField(null=True, blank=True)


class QaytarishAkti(SalonModel):
    class Tekshiruv(models.TextChoices):
        BUTUN = 'butun', 'Butun'
        DOG = 'dog', "Dog'"
        YIRTIQ = 'yirtiq', 'Yirtiq'
        AKSESSUAR_YOQ = 'aksessuar_yoq', "Aksessuar yo'q"

    zakaz = models.OneToOneField(Zakaz, on_delete=models.PROTECT, related_name='qaytarish_akti')
    sana = models.DateField()
    tekshiruv = models.CharField(max_length=16, choices=Tekshiruv.choices, default=Tekshiruv.BUTUN)
    jarima = models.PositiveIntegerField(default=0)
    ushlab_qolingan = models.PositiveIntegerField(default=0)  # pul zalogidan jarimaga
    qarz = models.PositiveIntegerField(default=0)  # to'lanmagan jarima (FT-12.13)
    kechikish_kunlari = models.PositiveSmallIntegerField(default=0)
    tortilgan_gr = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    ogirlik_mos = models.BooleanField(null=True)
    baho = models.PositiveSmallIntegerField(null=True, blank=True)  # 1–5 (FT-9.5)
    izoh = models.CharField(max_length=300, blank=True)
    xodim = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')


class TayyorChegirma(SalonModel):
    """Rahbar oldindan tasdiqlagan chegirma: sotuvchi tanlasa darhol qo'llanadi (FT-11.7)."""
    nomi = models.CharField(max_length=100)
    foiz = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    summa = models.PositiveIntegerField(null=True, blank=True)
    faol = models.BooleanField(default=True)

    def __str__(self):
        return self.nomi


class ChegirmaSorovi(SalonModel):
    class Sabab(models.TextChoices):
        DOIMIY_MIJOZ = 'doimiy_mijoz', 'Doimiy mijoz'
        NUQSON = 'nuqson', 'Libosda kichik nuqson'
        BOSHQA = 'boshqa', 'Boshqa'

    class Holat(models.TextChoices):
        KUTILMOQDA = 'kutilmoqda', 'Kutilmoqda'
        TASDIQLANDI = 'tasdiqlandi', 'Tasdiqlandi'
        RAD = 'rad', 'Rad etildi'
        TAYYOR = 'tayyor', 'Tayyor chegirma (tasdiqsiz)'

    zakaz = models.ForeignKey(Zakaz, on_delete=models.CASCADE, related_name='chegirma_sorovlari')
    sotuvchi = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    tayyor = models.ForeignKey(TayyorChegirma, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='+')
    foiz = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    summa = models.PositiveIntegerField(null=True, blank=True)
    sabab = models.CharField(max_length=16, choices=Sabab.choices, default=Sabab.BOSHQA)
    izoh = models.CharField(max_length=300, blank=True)
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.KUTILMOQDA)
    tasdiqlangan_summa = models.PositiveIntegerField(null=True, blank=True)
    rahbar = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='+')
    rahbar_izohi = models.CharField(max_length=300, blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    qaror_vaqti = models.DateTimeField(null=True, blank=True)
    # Promokod rahbar tasdig'iga yuborilgan bo'lsa (FT-21.7)
    promokod_ishlatilishi = models.OneToOneField('PromokodIshlatilishi', null=True, blank=True,
                                                 on_delete=models.SET_NULL, related_name='sorov')


class ZakazTarixi(SalonModel):
    """Zakazdagi har bir o'zgartirish va bekor qilish: kim, qachon, nima, sabab (FT-17.5)."""
    zakaz = models.ForeignKey(Zakaz, on_delete=models.CASCADE, related_name='tarix')
    xodim = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    harakat = models.CharField(max_length=30)
    eski = models.CharField(max_length=300, blank=True)
    yangi = models.CharField(max_length=300, blank=True)
    sabab = models.CharField(max_length=300, blank=True)
    vaqt = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['vaqt', 'id']


class ZakazAksessuar(SalonModel):
    """Zakazga berilgan aksessuar: qaysi dona (yorliq) berilgani yoziladi (FT-4.2)."""
    zakaz = models.ForeignKey(Zakaz, on_delete=models.CASCADE, related_name='aksessuarlar')
    dona = models.ForeignKey('catalog.AksessuarDona', on_delete=models.PROTECT, related_name='+')
    narx = models.PositiveIntegerField()  # zakaz paytidagi ijara narxi


class Promokod(SalonModel):
    """Promokod (4.18). Ishlatilgan kod o'chirilmaydi — faqat arxivlanadi, statistika saqlanadi (FT-21.10)."""

    class Turi(models.TextChoices):
        BIR_MARTALIK = 'bir_martalik', 'Bir martalik'
        KOP_MARTALIK = 'kop_martalik', "Ko'p martalik"

    class ChegirmaTuri(models.TextChoices):
        FOIZ = 'foiz', 'Foiz'
        SUMMA = 'summa', "Summa (so'm)"
        AKSESSUAR = 'aksessuar', 'Bepul aksessuar'

    class Manba(models.TextChoices):
        INSTAGRAM = 'instagram', 'Instagram'
        TELEGRAM = 'telegram', 'Telegram'
        SALONCHI = 'salonchi', 'Salonchi'
        AKSIYA = 'aksiya', 'Aksiya'

    class Holat(models.TextChoices):  # saqlanadigan holat; qolganlari (muddati o'tgan va h.k.) hisoblanadi
        FAOL = 'faol', 'Faol'
        TOXTATILGAN = 'toxtatilgan', "To'xtatilgan"
        ARXIV = 'arxiv', 'Arxiv'

    kod = models.CharField(max_length=30)
    turi = models.CharField(max_length=14, choices=Turi.choices, default=Turi.KOP_MARTALIK)
    chegirma_turi = models.CharField(max_length=10, choices=ChegirmaTuri.choices, default=ChegirmaTuri.FOIZ)
    qiymat = models.PositiveIntegerField(default=0)  # foiz (1–100) yoki summa; bepul aksessuarda ishlatilmaydi
    aksessuar = models.ForeignKey('catalog.Aksessuar', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    boshlanish = models.DateField(null=True, blank=True)
    tugash = models.DateField(null=True, blank=True)  # bo'sh — muddatsiz
    limit = models.PositiveIntegerField(null=True, blank=True)       # ko'p martalik: umumiy ishlatish soni; bo'sh — cheksiz
    bir_mijozga = models.PositiveSmallIntegerField(default=1)        # bitta mijoz necha marta ishlata oladi (FT-21.4)
    min_summa = models.PositiveIntegerField(null=True, blank=True)
    maks_chegirma = models.PositiveIntegerField(null=True, blank=True)
    kategoriyalar = models.ManyToManyField('catalog.Kategoriya', blank=True, related_name='+')
    hafta_kunlari = models.JSONField(null=True, blank=True)          # [0..6], 0 — dushanba; olib ketish kuni bo'yicha
    salonchi = models.ForeignKey(Salonchi, null=True, blank=True, on_delete=models.SET_NULL, related_name='promokodlar')
    manba = models.CharField(max_length=10, choices=Manba.choices, default=Manba.AKSIYA)
    izoh = models.CharField(max_length=300, blank=True)
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.FAOL)
    yaratgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['salon', 'kod'], name='promokod_salonda_noyob'),
        ]

    def __str__(self):
        return self.kod


class PromokodIshlatilishi(SalonModel):
    promokod = models.ForeignKey(Promokod, on_delete=models.PROTECT, related_name='ishlatilishlar')
    zakaz = models.ForeignKey(Zakaz, on_delete=models.CASCADE, related_name='promokod_ishlatilishlari')
    mijoz = models.ForeignKey(Mijoz, on_delete=models.PROTECT, related_name='+')
    sotuvchi = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    summa = models.PositiveIntegerField(default=0)
    sana = models.DateTimeField(auto_now_add=True)
    bekor = models.BooleanField(default=False)  # zakaz bekor qilinsa yoki kod olib tashlansa — kod qayta bo'shaydi (FT-21.9)


class MavsumiyNarx(SalonModel):
    """Mavsumiy ustama qoidasi (FT-15.2): sanalar oralig'i va/yoki hafta kunlari uchun foiz.

    Olib ketish kuniga bir nechta qoida to'g'ri kelsa, eng katta foiz olinadi (qo'shilmaydi).
    """
    nomi = models.CharField(max_length=100)
    boshlanish = models.DateField(null=True, blank=True)   # ikkalasi bo'sh — butun yil (faqat hafta kunlari bo'yicha)
    tugash = models.DateField(null=True, blank=True)
    hafta_kunlari = models.JSONField(null=True, blank=True)  # [0..6], 0 — dushanba; bo'sh — har kuni
    foiz = models.DecimalField(max_digits=5, decimal_places=2)
    faol = models.BooleanField(default=True)

    class Meta:
        ordering = ['boshlanish', 'id']

    def __str__(self):
        return self.nomi


class Primerka(SalonModel):
    """Primerka (FT-2.8): zakazga sana va vaqt; moslash kerak bo'lsa narxi zakazga qo'shiladi."""

    class Holat(models.TextChoices):
        REJALASHTIRILGAN = 'rejalashtirilgan', 'Rejalashtirilgan'
        OTKAZILDI = 'otkazildi', "O'tkazildi"
        BEKOR = 'bekor', 'Bekor qilingan'

    zakaz = models.ForeignKey(Zakaz, on_delete=models.CASCADE, related_name='primerkalar')
    vaqt = models.DateTimeField()
    natija = models.CharField(max_length=300, blank=True)
    moslash_narxi = models.PositiveIntegerField(default=0)
    holat = models.CharField(max_length=16, choices=Holat.choices, default=Holat.REJALASHTIRILGAN)
    xodim = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['vaqt', 'id']

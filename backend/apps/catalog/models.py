from django.db import models

from apps.tenants.models import SalonModel


class Kategoriya(SalonModel):
    class Turi(models.TextChoices):
        LIBOS = 'libos', 'Libos'
        AKSESSUAR = 'aksessuar', 'Aksessuar'

    nomi = models.CharField(max_length=100)
    turi = models.CharField(max_length=12, choices=Turi.choices, default=Turi.LIBOS)
    tartib = models.PositiveSmallIntegerField(default=0)
    bufer_kun = models.PositiveSmallIntegerField(null=True, blank=True)  # FT-2.4

    class Meta:
        ordering = ['tartib', 'nomi']
        constraints = [
            models.UniqueConstraint(fields=['salon', 'nomi', 'turi'], name='kategoriya_salonda_noyob'),
        ]

    def __str__(self):
        return self.nomi


class Libos(SalonModel):
    class Holat(models.TextChoices):
        TASDIQ_KUTILMOQDA = 'tasdiq_kutilmoqda', 'Tasdiq kutilmoqda'
        BOSH = 'bosh', "Bo'sh"
        TOZALASHDA = 'tozalashda', 'Tozalashda'
        TAMIRDA = 'tamirda', "Ta'mirda"
        SOTILDI = 'sotildi', 'Sotildi'
        HISOBDAN_CHIQARILDI = 'hisobdan_chiqarildi', 'Hisobdan chiqarildi'
        ARXIV = 'arxiv', 'Arxiv'

    artikul = models.CharField(max_length=50)
    nomi = models.CharField(max_length=200)
    kategoriya = models.ForeignKey(Kategoriya, on_delete=models.PROTECT)
    olcham = models.CharField(max_length=20, blank=True)
    rang = models.CharField(max_length=50, blank=True)
    holat = models.CharField(max_length=24, choices=Holat.choices, default=Holat.BOSH)
    ijara_narxi = models.PositiveIntegerField(default=0)
    zalog = models.PositiveIntegerField(default=0)
    # Tannarx faqat rahbarga ko'rinadi (3-bo'lim, FT-3.5)
    tannarx = models.PositiveIntegerField(null=True, blank=True)
    bufer_kun = models.PositiveSmallIntegerField(null=True, blank=True)
    qoshgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    yaratilgan = models.DateTimeField(auto_now_add=True)
    filial = models.ForeignKey('tenants.Filial', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')  # libos turgan joy
    # Raqamli manekin (4.5): fonsiz qatlam olingan rasm va sotuvchi to'g'rilagan joylashuv (FT-5.3).
    # x, y — kanvas eniga/bo'yiga nisbatan siljish (−1…1), kattalik — masshtab (1 = standart).
    manekin_rasm = models.ForeignKey('Rasm', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    # Standart: libos qatlami kanvasni to'ldiradi, shuning uchun 80% ga kichraytirib yelkadan boshlanadigan qilib qo'yiladi
    manekin_x = models.FloatField(default=0)
    manekin_y = models.FloatField(default=0.08)
    manekin_kattalik = models.FloatField(default=0.8)

    class Meta:
        ordering = ['artikul']
        constraints = [
            models.UniqueConstraint(fields=['salon', 'artikul'], name='artikul_salonda_noyob'),
        ]

    def samarali_bufer_kun(self, default=1):
        """Libos > kategoriya > standart (FT-2.4)."""
        if self.bufer_kun is not None:
            return self.bufer_kun
        if self.kategoriya.bufer_kun is not None:
            return self.kategoriya.bufer_kun
        return default

    def __str__(self):
        return f'{self.artikul} {self.nomi}'


def rasm_yoli(instance, filename):
    """Taxmin qilib bo'lmaydigan nom: boshqa salon fayl manzilini topa olmaydi (FT-22.4)."""
    import uuid
    return f'rasmlar/{instance.salon_id}/{uuid.uuid4().hex}.{filename.rsplit(".", 1)[-1]}'


class Rasm(SalonModel):
    """Libos rasmi: asl nusxa alohida saqlanadi, galereya va karta uchun avtomatik o'lchamlar (7.3)."""
    libos = models.ForeignKey(Libos, on_delete=models.CASCADE, related_name='rasmlar')
    asl = models.FileField(upload_to=rasm_yoli)
    katta = models.FileField(upload_to=rasm_yoli)    # 800 × 1200, 300 KB gacha
    kichik = models.FileField(upload_to=rasm_yoli)   # 300 × 450, 50 KB gacha
    fonsiz = models.FileField(upload_to=rasm_yoli, blank=True)  # manekin qatlami: 800 × 1200, shaffof fon, 400 KB gacha
    standart = models.BooleanField(default=True)     # False — «standart emas» belgisi rahbar ro'yxatida
    tartib = models.PositiveSmallIntegerField(default=0)
    yuklagan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tartib', 'id']


class Aksessuar(SalonModel):
    """Aksessuar turi (masalan, «Fata Klassik»): faqat ijaraga beriladi, sotilmaydi (F3, FT-4.2).

    Har bir jismoniy dona `AksessuarDona` sifatida alohida raqamli yorliq bilan hisobga olinadi.
    """

    class Holat(models.TextChoices):
        TASDIQ_KUTILMOQDA = 'tasdiq_kutilmoqda', 'Tasdiq kutilmoqda'
        FAOL = 'faol', 'Faol'
        ARXIV = 'arxiv', 'Arxiv'

    nomi = models.CharField(max_length=200)
    kod = models.CharField(max_length=10)  # yorliq prefiksi: FT -> FT-01, FT-02
    kategoriya = models.ForeignKey(Kategoriya, on_delete=models.PROTECT)
    ijara_narxi = models.PositiveIntegerField(default=0)
    tannarx = models.PositiveIntegerField(null=True, blank=True)  # faqat rahbarga ko'rinadi
    holat = models.CharField(max_length=20, choices=Holat.choices, default=Holat.FAOL)
    qoshgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    # Manekin qatlami (FT-5.2): fonsiz rasm va libos ustidagi standart joylashuvi
    manekin_rasm = models.FileField(upload_to=rasm_yoli, blank=True)
    manekin_x = models.FloatField(default=0)
    manekin_y = models.FloatField(default=0)
    manekin_kattalik = models.FloatField(default=1)

    class Meta:
        ordering = ['nomi']
        constraints = [
            models.UniqueConstraint(fields=['salon', 'kod'], name='aksessuar_kodi_salonda_noyob'),
        ]

    def __str__(self):
        return self.nomi


class AksessuarDona(SalonModel):
    class Holat(models.TextChoices):
        BOSH = 'bosh', "Bo'sh"
        TAMIRDA = 'tamirda', "Ta'mirda"
        YOQOLGAN = 'yoqolgan', "Yo'qolgan"
        ARXIV = 'arxiv', 'Arxiv'

    aksessuar = models.ForeignKey(Aksessuar, on_delete=models.CASCADE, related_name='donalar')
    filial = models.ForeignKey('tenants.Filial', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')  # dona turgan joy
    yorliq = models.CharField(max_length=20)
    holat = models.CharField(max_length=10, choices=Holat.choices, default=Holat.BOSH)

    class Meta:
        ordering = ['yorliq']
        constraints = [
            models.UniqueConstraint(fields=['salon', 'yorliq'], name='dona_yorligi_salonda_noyob'),
        ]

    def __str__(self):
        return self.yorliq


class TamirYozuvi(SalonModel):
    """Ta'mir va moslash jurnali (FT-3.10): nima qilindi, kim qildi, narxi, libos necha kun ta'mirda turdi."""
    libos = models.ForeignKey(Libos, on_delete=models.CASCADE, related_name='tamirlar')
    ish_turi = models.CharField(max_length=300)
    kim = models.CharField(max_length=200, blank=True)  # usta yoki ustaxona
    boshlangan = models.DateField()
    tugagan = models.DateField(null=True, blank=True)
    narx = models.PositiveIntegerField(default=0)
    xarajat = models.OneToOneField('finance.Xarajat', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='tamir')
    kiritgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    tugatgan = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='+')

    class Meta:
        ordering = ['-boshlangan', '-id']
        constraints = [
            # bitta libosda bir vaqtda faqat bitta ochiq ta'mir
            models.UniqueConstraint(fields=['libos'], condition=models.Q(tugagan__isnull=True),
                                    name='libosda_bitta_ochiq_tamir'),
        ]

    def kunlar(self, bugun=None):
        """Libos ta'mirda turgan kunlar (ochiq bo'lsa bugungacha); shu kuni qaytsa ham kamida 1 kun."""
        from django.utils import timezone
        oxiri = self.tugagan or bugun or timezone.localdate()
        return max(1, (oxiri - self.boshlangan).days)


class DonaTamiri(SalonModel):
    """Aksessuar donasining ta'mir jurnali: nima qilindi, kim qildi, narxi, necha kun ta'mirda turdi."""
    dona = models.ForeignKey(AksessuarDona, on_delete=models.CASCADE, related_name='tamirlar')
    ish_turi = models.CharField(max_length=300)
    kim = models.CharField(max_length=200, blank=True)
    boshlangan = models.DateField()
    tugagan = models.DateField(null=True, blank=True)
    narx = models.PositiveIntegerField(default=0)
    xarajat = models.OneToOneField('finance.Xarajat', null=True, blank=True, on_delete=models.SET_NULL, related_name='dona_tamiri')
    kiritgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    tugatgan = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['-boshlangan', '-id']
        constraints = [
            models.UniqueConstraint(fields=['dona'], condition=models.Q(tugagan__isnull=True), name='donada_bitta_ochiq_tamir'),
        ]

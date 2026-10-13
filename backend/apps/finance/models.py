from django.db import models

from apps.tenants.models import SalonModel


class Xarajat(SalonModel):
    class Modda(models.TextChoices):
        TOZALASH = 'tozalash', 'Tozalash (ximchistka)'
        TAMIR = 'tamir', "Ta'mirlash"
        BINO = 'bino', 'Bino ijarasi'
        OYLIK = 'oylik', 'Sotuvchilar oyligi'
        KOMMUNAL = 'kommunal', 'Kommunal'
        REKLAMA = 'reklama', 'Reklama'
        TRANSPORT = 'transport', 'Transport'
        BANK = 'bank', 'Bank komissiyasi'
        BOSHQA = 'boshqa', 'Boshqa'

    class Holat(models.TextChoices):
        KUTILMOQDA = 'kutilmoqda', 'Tasdiq kutilmoqda'
        TASDIQLANDI = 'tasdiqlandi', 'Tasdiqlandi'
        RAD = 'rad', 'Rad etildi'

    # To'g'ridan-to'g'ri xarajat (P&L 2-qator); qolganlari operatsion (5-qator)
    TOGRIDAN_TOGRI = ('tozalash', 'tamir')

    sana = models.DateField()
    modda = models.CharField(max_length=12)  # standart kod (Modda) yoki salon moddasi: m<id> (FT-13.1)
    summa = models.PositiveIntegerField()
    usul = models.CharField(max_length=8, default='naqd')
    izoh = models.CharField(max_length=300, blank=True)
    holat = models.CharField(max_length=12, choices=Holat.choices, default=Holat.KUTILMOQDA)
    kiritgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    tasdiqlagan = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+')
    tolov = models.OneToOneField('cash.Tolov', null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='xarajat')  # kassadan to'langan bo'lsa
    yaratilgan = models.DateTimeField(auto_now_add=True)
    # Doimiy oylik xarajatdan yaratilgan qoralama (FT-13.3): har shablondan oyiga bitta
    doimiy = models.ForeignKey('DoimiyXarajat', null=True, blank=True, on_delete=models.SET_NULL, related_name='xarajatlar')
    doimiy_oy = models.CharField(max_length=7, blank=True)
    # Xarajat qaysi filialga tegishli; bo'sh — butun salon uchun umumiy (bino ijarasi, reklama va h.k.)
    filial = models.ForeignKey('tenants.Filial', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['doimiy', 'doimiy_oy'], condition=models.Q(doimiy__isnull=False),
                                    name='doimiy_xarajat_oyiga_bitta'),
        ]


class XarajatModdasi(SalonModel):
    """Rahbar qo'shgan xarajat moddasi (FT-13.1). O'chirilmaydi — nofaol qilinadi (eski xarajatlar nomi saqlanadi)."""
    nomi = models.CharField(max_length=100)
    togridan = models.BooleanField(default=False)  # to'g'ridan-to'g'ri xarajat (P&L 2-qator), aks holda operatsion
    faol = models.BooleanField(default=True)

    class Meta:
        ordering = ['nomi']


class DoimiyXarajat(SalonModel):
    """Har oy takrorlanadigan xarajat shabloni (FT-13.3): bino ijarasi, oylik va h.k."""
    modda = models.CharField(max_length=12)
    summa = models.PositiveIntegerField()
    izoh = models.CharField(max_length=300, blank=True)
    faol = models.BooleanField(default=True)
    filial = models.ForeignKey('tenants.Filial', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        ordering = ['id']


class YopilganOy(SalonModel):
    """Yopilgan oy (FT-18.4): ma'lumotlarini faqat rahbar o'zgartira oladi; yopish paytidagi P&L saqlanadi."""
    yil = models.PositiveSmallIntegerField()
    oy = models.PositiveSmallIntegerField()
    yopgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    yopilgan = models.DateTimeField(auto_now_add=True)
    hisobot = models.JSONField(default=dict)

    class Meta:
        ordering = ['-yil', '-oy']
        constraints = [
            models.UniqueConstraint(fields=['salon', 'yil', 'oy'], name='oy_bir_marta_yopiladi'),
        ]


class BankSolishtirish(SalonModel):
    """Karta, Click va Payme tushumlarini bank ko'chirmasi bilan oylik solishtirish (FT-12.12)."""
    yil = models.PositiveSmallIntegerField()
    oy = models.PositiveSmallIntegerField()
    usul = models.CharField(max_length=8)                       # karta / click / payme
    kochirma_summa = models.BigIntegerField()                  # bank ko'chirmasidagi tushgan summa
    komissiya = models.PositiveIntegerField(default=0)         # bank komissiyasi -> xarajat moddasi
    xarajat = models.OneToOneField(Xarajat, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    kiritgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    yangilangan = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['salon', 'yil', 'oy', 'usul'], name='bank_solishtirish_noyob'),
        ]

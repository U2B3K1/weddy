from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models
from django.utils import timezone

from apps.catalog.models import Libos
from apps.tenants.models import SalonModel


class Bron(SalonModel):
    """Libosning sana oralig'ida bandligi.

    `oraliq` = olib ketish sanasi ... qaytarish sanasi + bufer kunlar (ikkala chegara ham kiradi).
    Ikki marta bronning yakuniy himoyasi — bazadagi ExclusionConstraint (7-bo'lim, FT-2.7).
    """

    class Turi(models.TextChoices):
        VAQTINCHALIK = 'vaqtinchalik', 'Vaqtinchalik'
        MUSTAHKAM = 'mustahkam', 'Mustahkam'

    libos = models.ForeignKey(Libos, on_delete=models.PROTECT, related_name='bronlar')
    oraliq = DateRangeField()
    turi = models.CharField(max_length=14, choices=Turi.choices, default=Turi.VAQTINCHALIK)
    muddati = models.DateTimeField(null=True, blank=True)  # vaqtinchalik bron tugash vaqti (FT-2.5)
    zakaz = models.ForeignKey('orders.Zakaz', null=True, blank=True, on_delete=models.CASCADE,
                              related_name='bronlar')
    yaratgan = models.ForeignKey('tenants.Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name='ikki_marta_bron_yoq',
                expressions=[('libos', RangeOperators.EQUAL), ('oraliq', RangeOperators.OVERLAPS)],
            ),
        ]

    @classmethod
    def faol(cls):
        """Muddati o'tmagan bronlar (tugagan vaqtinchalik bronlar hisobga olinmaydi)."""
        return cls.objects.exclude(turi=cls.Turi.VAQTINCHALIK, muddati__lt=timezone.now())

    @classmethod
    def kelgusi(cls):
        """Hali tugamagan faol bronlar (libos sotilish/arxivga o'tishini to'sadi)."""
        return cls.faol().filter(oraliq__endswith__gt=timezone.localdate())


class LibosQulfi(SalonModel):
    """Zakazga qo'shilayotgan libos 15 daqiqaga boshqa sotuvchidan yashiriladi (FT-2.7)."""
    libos = models.ForeignKey(Libos, on_delete=models.CASCADE, related_name='qulflar')
    oraliq = DateRangeField()
    xodim = models.ForeignKey('tenants.Xodim', on_delete=models.CASCADE, related_name='+')
    tugaydi = models.DateTimeField()


class AksessuarBron(SalonModel):
    """Aksessuar donasining sana oralig'ida bandligi; libos broni kabi bazadagi cheklov bilan himoyalangan."""
    dona = models.ForeignKey('catalog.AksessuarDona', on_delete=models.CASCADE, related_name='bronlar')
    oraliq = DateRangeField()
    turi = models.CharField(max_length=14, choices=Bron.Turi.choices, default=Bron.Turi.VAQTINCHALIK)
    muddati = models.DateTimeField(null=True, blank=True)
    zakaz = models.ForeignKey('orders.Zakaz', null=True, blank=True, on_delete=models.CASCADE,
                              related_name='aksessuar_bronlari')
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            ExclusionConstraint(
                name='aksessuar_ikki_marta_bron_yoq',
                expressions=[('dona', RangeOperators.EQUAL), ('oraliq', RangeOperators.OVERLAPS)],
            ),
        ]

    @classmethod
    def faol(cls):
        return cls.objects.exclude(turi=Bron.Turi.VAQTINCHALIK, muddati__lt=timezone.now())

    @classmethod
    def kelgusi(cls):
        """Hali tugamagan faol bronlar. Qaytarilgan zakazning bronlari o'chirilmaydi — ular donani abadiy
        «bronlari bor» qilib to'smasligi uchun o'tib ketganlari hisobga olinmaydi."""
        return cls.faol().filter(oraliq__endswith__gt=timezone.localdate())

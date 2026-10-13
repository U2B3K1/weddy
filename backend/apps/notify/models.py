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

    class Meta:
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(fields=['xodim', 'kalit'], condition=~models.Q(kalit=''),
                                    name='xabar_takrorlanmaydi'),
        ]


class KirishKodi(models.Model):
    """Rahbar kirishi uchun Telegramga yuboriladigan bir martalik kod (FT-1.1, FT-22.3)."""
    xodim = models.OneToOneField('tenants.Xodim', on_delete=models.CASCADE, related_name='kirish_kodi')
    kod = models.CharField(max_length=128)  # xesh
    tugaydi = models.DateTimeField()
    urinish = models.PositiveSmallIntegerField(default=0)


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

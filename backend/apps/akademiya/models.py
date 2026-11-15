import hashlib

from django.db import models


class Oquvchi(models.Model):
    """Akademiyada o'qiyotgan haqiqiy xodim va uning shaxsiy o'quv saloni.

    Maydon nomi ataylab `salon` emas: `salon` nomli bog'lanishi bor modellar salon arxivi va o'chirishga tushadi
    (apps/tenants/arxiv.py), bu yozuv esa ikki salonni bog'laydi.
    """
    xodim = models.OneToOneField('tenants.Xodim', null=True, blank=True, on_delete=models.CASCADE, related_name='oquvchi')
    # Mehmon — ro'yxatdan o'tmagan odam: haqiqiy xodimi yo'q, faqat ochiq darslar, o'quv saloni 24 soatdan keyin o'chadi
    mehmon = models.BooleanField(default=False)
    oquv_salon = models.OneToOneField('tenants.Salon', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    oquv_xodim = models.ForeignKey('tenants.Xodim', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    yaratilgan = models.DateTimeField(auto_now_add=True)
    oxirgi_kirish = models.DateTimeField(null=True, blank=True)
    # O'quv saloni hozir qaysi darsning boshlang'ich holatida va urug' nimalarni yaratgan (tekshiruv shunga qaraydi)
    joriy_dars = models.CharField(max_length=8, blank=True)
    dars_holati = models.JSONField(default=dict, blank=True)
    # Kurs qayta boshlanganda natijalar o'chadi, lekin eng yaxshi natija (rekord) qoladi — reytingda kattasi ko'rinadi
    rekord_xp = models.PositiveIntegerField(default=0)
    rekord_darslar = models.PositiveSmallIntegerField(default=0)
    # qayta boshlash paytidagi haftalik ball: shu hafta ichida reytingdagi o'rin ham yo'qolmaydi
    rekord_hafta = models.PositiveIntegerField(default=0)
    rekord_vaqt = models.DateTimeField(null=True, blank=True)


def kod_xeshi(kod):
    return hashlib.sha256(kod.encode()).hexdigest()


class KirishKodi(models.Model):
    """libosa.uz dan akademiyaga o'tish uchun bir martalik kod. Kodning o'zi saqlanmaydi — faqat xeshi."""
    xesh = models.CharField(max_length=64, unique=True)
    xodim = models.ForeignKey('tenants.Xodim', on_delete=models.CASCADE, related_name='+')
    tugaydi = models.DateTimeField()


class DarsNatija(models.Model):
    oquvchi = models.ForeignKey(Oquvchi, on_delete=models.CASCADE, related_name='natijalar')
    dars = models.CharField(max_length=8)
    boshlangan = models.DateTimeField(auto_now_add=True)
    bajarilgan = models.DateTimeField(null=True, blank=True)
    urinishlar = models.PositiveSmallIntegerField(default=0)  # «Tekshirish» necha marta bosilgan
    yordam = models.PositiveSmallIntegerField(default=0)      # ishlatilgan eng yuqori yordam darajasi (0 — yordamsiz)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['oquvchi', 'dars'], name='oquvchida_dars_bir_marta')]

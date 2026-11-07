"""Xodim qo'ng'iroqchasi (R2): sotuvchiga ham bildirishnomalar — rahbar qarorini kutmasdan ko'radi.

`GET /api/bildirishnomalar/` — joriy xodim uchun:
- chegirma so'rovi natijasi (u so'ragan, rahbar oxirgi 24 soatda tasdiqlagan yoki rad etgan);
- unga topshirilgan va hali qabul qilinmagan pul (cash — faqat o'qiladi);
- bugun mijozga qo'ng'iroq qilish kerak bo'lgan eslatmalar soni («Bog'landim» bosilmaganlari);
- C-24: u qabul qilgan o'tkazmani rahbar «kelmadi» deb belgilagan (pulni mijozdan qayta olish kerak) va kassadan to'lagan
  xarajati rad etilgan (kamomad) — oxirgi 7 kun. Avval bular faqat Telegramga borardi.
Hech narsa yozmaydi; «ko'rildi» belgisi qurilmada saqlanadi (frontend).
"""
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.permissions import IsStaff

from .models import ChegirmaSorovi, Zakaz

NATIJA_SOAT = 24  # chegirma qarori shuncha vaqt ko'rinadi
OGOH_KUN = 7      # «kelmadi» va rad etilgan xarajat shuncha kun ko'rinadi (qurilmada ochilguncha)


def _som(n):
    return f'{int(n or 0):,}'.replace(',', ' ') + " so'm"


def _chegirma_matni(c):
    nima = 'promokod' if c.promokod_ishlatilishi_id else 'chegirma'
    kim = f'#{c.zakaz.raqam} {c.zakaz.mijoz.fio or c.zakaz.mijoz.telefon}'
    if c.holat == ChegirmaSorovi.Holat.TASDIQLANDI:
        miqdor = f': {_som(c.tasdiqlangan_summa)}' if c.tasdiqlangan_summa else ''
        return f'{kim} — {nima} tasdiqlandi{miqdor}'
    return f"{kim} — {nima} rad etildi{f': «{c.rahbar_izohi}»' if c.rahbar_izohi else ''}"


def bildirishnomalar(salon, xodim, hozir=None):
    from apps.cash.models import KassaTopshirish

    from .views_royxat import eslatmalar

    hozir = hozir or timezone.now()
    xabarlar = []
    for c in (ChegirmaSorovi.objects.filter(salon=salon, sotuvchi=xodim, qaror_vaqti__gte=hozir - timedelta(hours=NATIJA_SOAT),
                                            holat__in=[ChegirmaSorovi.Holat.TASDIQLANDI, ChegirmaSorovi.Holat.RAD])
              .select_related('zakaz__mijoz').order_by('-qaror_vaqti')[:10]):
        xabarlar.append({'kalit': f'chegirma-{c.id}', 'tur': 'chegirma_tasdiq' if c.holat == ChegirmaSorovi.Holat.TASDIQLANDI
                         else 'chegirma_rad', 'matn': _chegirma_matni(c), 'soni': 1, 'zakaz_id': c.zakaz_id,
                         'vaqt': c.qaror_vaqti})
    from apps.cash.models import Tolov
    from apps.finance.models import Xarajat
    for t in (Tolov.objects.filter(salon=salon, xodim=xodim, tasdiq=Tolov.Tasdiq.KELMADI,
                                   tasdiq_vaqti__gte=hozir - timedelta(days=OGOH_KUN))
              .select_related('zakaz__mijoz').order_by('-tasdiq_vaqti')[:10]):
        kim = f'#{t.zakaz.raqam} {t.zakaz.mijoz.fio or t.zakaz.mijoz.telefon} — ' if t.zakaz_id else ''
        xabarlar.append({'kalit': f'kelmadi-{t.id}', 'tur': 'otkazma_kelmadi', 'soni': 1, 'zakaz_id': t.zakaz_id,
                         'summa': t.summa, 'vaqt': t.tasdiq_vaqti,
                         'matn': f"{kim}{_som(t.summa)} o'tkazma kelmadi: pulni mijozdan qayta oling"})
    for x in (Xarajat.objects.filter(salon=salon, kiritgan=xodim, holat=Xarajat.Holat.RAD, tolov__isnull=False,
                                     sana__gte=timezone.localdate() - timedelta(days=OGOH_KUN)).order_by('-sana', '-id')[:10]):
        xabarlar.append({'kalit': f'xarajat-rad-{x.id}', 'tur': 'xarajat_rad', 'soni': 1, 'summa': x.summa,
                         'matn': f"Kassadan to'langan xarajatingiz ({x.sana:%d.%m}, {_som(x.summa)}) rad etildi — kamomad hisoblanadi"})
    kutayotgan = KassaTopshirish.objects.filter(salon=salon, kimga=xodim, holat=KassaTopshirish.Holat.KUTILMOQDA)
    t = kutayotgan.aggregate(s=Sum('summa'))
    soni = kutayotgan.count()
    if soni:
        kimdan = sorted({x.kimdan.ism for x in kutayotgan.select_related('kimdan')})
        xabarlar.append({'kalit': 'topshiriq', 'tur': 'topshiriq', 'soni': soni, 'summa': t['s'] or 0,
                         'matn': f"Sizga {_som(t['s'])} topshirildi ({', '.join(kimdan)}) — sanab, qabul qiling"})
    # «Bugungi ishlar» — bosh sahifadagi kartalar bilan bir xil ta'rif; faqat ish bor bo'lsa chiqadi (vaziyatga qarab).
    # Kundalik operatsion ishlar (olib ketish, qaytarish, qo'ng'iroq) — xodimlarga; rahbarga — kechikkan va qarzdorlar
    from .views_royxat import BUGUN_FILTRLARI, _kechikkan
    bugun = timezone.localdate()
    zakazlar = Zakaz.objects.filter(salon=salon)
    rahbar = xodim.rol == xodim.Rol.RAHBAR
    for tur, son, matn in (
        ('olib', 0 if rahbar else BUGUN_FILTRLARI['bugun_olib'](zakazlar).count(), "ta mijoz bugun libos olib ketadi — qoldiq va zalogni oling"),
        ('qaytar', 0 if rahbar else BUGUN_FILTRLARI['bugun_qaytar'](zakazlar).count(), "ta libos bugun qaytariladi"),
        ('kechikkan', _kechikkan(zakazlar).count(), "ta kechikkan qaytarish — mijozga qo'ng'iroq qiling"),
    ):
        if son:
            xabarlar.append({'kalit': f'{tur}-{bugun}', 'tur': tur, 'soni': son, 'matn': f'{son} {matn}'})
    qongiroq = 0 if rahbar else sum(1 for e in eslatmalar(salon, bugun) if not e['boglangan'])
    if qongiroq:
        xabarlar.append({'kalit': f'qongiroq-{bugun}', 'tur': 'qongiroq', 'soni': qongiroq,
                         'matn': f"Bugun {qongiroq} ta mijozga qo'ng'iroq qilish kerak"})
    if rahbar:  # qarzdorlar ro'yxati faqat rahbarga ko'rinadi
        qarzdor = zakazlar.filter(holat=Zakaz.Holat.QAYTARILDI, qaytarish_akti__qarz__gt=0).count()
        if qarzdor:
            xabarlar.append({'kalit': f'qarzdor-{bugun}', 'tur': 'qarzdor', 'soni': qarzdor,
                             'matn': f"{qarzdor} ta mijoz jarima yoki zarar summasini to'lamagan"})
    return xabarlar


class BildirishnomalarView(APIView):
    """GET /api/bildirishnomalar/ → {"xabarlar": [{kalit, tur, matn, soni, zakaz_id?, summa?, vaqt?}], "soni": N}"""
    permission_classes = [IsStaff]

    def get(self, request):
        xabarlar = bildirishnomalar(request.salon, request.user)
        return Response({'xabarlar': xabarlar, 'soni': sum(x['soni'] for x in xabarlar)})

"""Nazorat eslatmalari: unutilgan tasdiqlar va libos sanog'i.

Tezkor qismi (topshiriq, o'tkazma) — Telegram bot jarayonida daqiqada bir (`tezkor_eslatmalar`): ikkita kichik so'rov,
faqat tasdiq kutayotgan yozuvlar (qisman indeks). Libos sanog'i har salonni aylanadi — soatlik cron (`eslatmalarni_yuborish`).
Har eslatma bir marta yoziladi (`kalit`), shuning uchun qayta-qayta ishga tushsa ham takrorlanmaydi.
"""
from datetime import timedelta

from django.utils import timezone

from apps.notify.services import rahbarlarga, som, xabar_yoz
from apps.tenants.models import Salon

from .models import KassaTopshirish, Tolov

TOPSHIRIQ_KUTISH = timedelta(minutes=2)    # qabul qiluvchiga qayta eslatma
TOPSHIRIQ_RAHBARGA = timedelta(minutes=15)  # shundan keyin ham tasdiqlanmasa — rahbarga
OTKAZMA_KUTISH = timedelta(minutes=2)  # mijoz hali salonda bo'lganida bilish kerak: pul kelmasa undan so'raladi
SANOQ_ORALIGI = 7  # kun


def _topshiriqlar(hozir):
    soni = 0
    for t in (KassaTopshirish.objects.filter(holat=KassaTopshirish.Holat.KUTILMOQDA, yaratilgan__lte=hozir - TOPSHIRIQ_KUTISH)
              .select_related('kimdan', 'kimga', 'salon')):
        tugmalar = [[{'text': f'✅ {som(t.summa)} qabul qildim', 'callback_data': f'kt:{t.id}:q'},
                     {'text': '✏️ Boshqa summa', 'callback_data': f'kt:{t.id}:b'}]]
        soni += bool(xabar_yoz(t.kimga, 'kassa_topshirish', f"⏰ Eslatma: {t.kimdan.ism} sizga {som(t.summa)} topshirgan — "
                               f"hali tasdiqlamadingiz. Sanab, tasdiqlang.", tugmalar, kalit=f'kt_eslatma:{t.id}'))
        # rahbarning o'zi qabul qiluvchi bo'lsa, yuqoridagi eslatma yetadi
        if not t.rahbarga and t.yaratilgan <= hozir - TOPSHIRIQ_RAHBARGA:
            soni += len([x for x in rahbarlarga(t.salon, 'kassa_topshirish_kutilmoqda',
                                                f"{t.kimdan.ism} {som(t.summa)} ni {t.kimga.ism}ga topshirgan, lekin "
                                                f"{t.kimga.ism} 15 daqiqadan beri tasdiqlamayapti.", kalit=f'kt_rahbar:{t.id}') if x])
    return soni


def _otkazmalar(hozir):
    soni = 0
    for t in (Tolov.objects.filter(tasdiq=Tolov.Tasdiq.KUTILMOQDA, vaqt__lte=hozir - OTKAZMA_KUTISH)
              .select_related('salon', 'xodim', 'zakaz')):
        tugmalar = [[{'text': '✅ Keldi', 'callback_data': f'ot:{t.id}:k'},
                     {'text': '❌ Kelmadi', 'callback_data': f'ot:{t.id}:y'}]]
        z = f' (zakaz #{t.zakaz.raqam})' if t.zakaz_id else ''
        soni += len([x for x in rahbarlarga(t.salon, 'otkazma_tasdiq',
                                            f"⏰ Eslatma: {t.get_usul_display()} {som(t.summa)}{z}, qabul qildi {t.xodim.ism} — "
                                            f"hisobingizga keldimi? Hali tasdiqlanmagan.", tugmalar, kalit=f'ot_eslatma:{t.id}') if x])
    return soni


def _sanoq(hozir):
    """Libos sanog'i haftada bir — zakazsiz ijarani faqat muntazam sanoq ushlaydi. Haftasiga bitta eslatma."""
    from apps.catalog.models import Libos, Sanoq
    from apps.catalog.sanoq import FAOL

    bugun = timezone.localdate(hozir)
    yil, hafta, _ = bugun.isocalendar()
    soni = 0
    for salon in Salon.objects.exclude(holat__in=[Salon.Holat.BLOKLANGAN, Salon.Holat.FAQAT_KORISH]):
        if not Libos.objects.filter(salon=salon, holat__in=FAOL).exists():
            continue
        oxirgi = Sanoq.objects.filter(salon=salon, yakunlangan__isnull=False).order_by('-yakunlangan').first()
        if oxirgi and (bugun - timezone.localdate(oxirgi.yakunlangan)).days < SANOQ_ORALIGI:
            continue
        qachon = (f"oxirgisi {(bugun - timezone.localdate(oxirgi.yakunlangan)).days} kun oldin" if oxirgi
                  else "hali birorta ham o'tkazilmagan")
        soni += len([x for x in rahbarlarga(salon, 'sanoq_eslatma',
                                            f"📋 Libos sanog'i {qachon}. Katalog → «Sanoq»: javondagi liboslarni o'zingiz sanang — "
                                            f"zakazsiz berilgan yoki yo'qolgan libos shunday topiladi.", kalit=f'sanoq:{yil}-{hafta}') if x])
    return soni


def tezkor_eslatmalar(hozir=None):
    """Topshiriq va o'tkazma eslatmalari (bot jarayonida daqiqada bir). Yozilgan eslatmalar soni."""
    hozir = hozir or timezone.now()
    return _topshiriqlar(hozir) + _otkazmalar(hozir)


def nazorat_eslatmalari(hozir=None):
    """Hammasi (soatlik cron; bot ishlamay qolsa ham tezkorlari shu yerda yoziladi). Yozilgan eslatmalar soni."""
    hozir = hozir or timezone.now()
    return tezkor_eslatmalar(hozir) + _sanoq(hozir)


def dashbord_nazorati(salon, bugun=None, kun=7):
    """Rahbar dashbordi uchun egasining uch savoli, oxirgi `kun` kun bo'yicha: kassada kamomad bormi (kim, qancha),
    nima diqqat talab qiladi (tasdiqlanmagan topshiriq va o'tkazma, kelmagan o'tkazma, terminal farqi), liboslar joyidami."""
    from apps.catalog.models import Sanoq

    from .models import Smena
    bugun = bugun or timezone.localdate()
    dan = bugun - timedelta(days=kun - 1)
    kamomad = {}  # xodim -> jami (faqat manfiy farqlar)
    terminal = 0
    for s in (Smena.objects.filter(salon=salon, sana__range=(dan, bugun), yopilgan__isnull=False)
              .prefetch_related('ishtirokchilar__xodim')):
        for i in s.ishtirokchilar.all():
            f = i.farq if i.farq is not None else (s.farq if i.chiqqan == s.yopilgan else None)
            if f and f < 0:
                kamomad[i.xodim.ism] = kamomad.get(i.xodim.ism, 0) + f
        terminal += s.terminal_farq or 0
    kelmadi = Tolov.objects.filter(salon=salon, tasdiq=Tolov.Tasdiq.KELMADI, tasdiq_vaqti__date__range=(dan, bugun))
    oxirgi = Sanoq.objects.filter(salon=salon, yakunlangan__isnull=False).order_by('-yakunlangan').first()
    return {
        'kun': kun,
        'kamomad': sum(kamomad.values()),
        'kamomad_xodimlar': [{'ism': k, 'summa': v} for k, v in sorted(kamomad.items(), key=lambda x: x[1])],
        'terminal_farq': terminal,
        'topshiriqlar': KassaTopshirish.objects.filter(salon=salon, holat=KassaTopshirish.Holat.KUTILMOQDA).count(),
        'otkazmalar': Tolov.objects.filter(salon=salon, tasdiq=Tolov.Tasdiq.KUTILMOQDA).count(),
        'kelmadi_soni': kelmadi.count(), 'kelmadi_summa': sum(t.summa for t in kelmadi),
        'sanoq': {'kun_oldin': (bugun - timezone.localdate(oxirgi.yakunlangan)).days, 'yoq': oxirgi.yoq,
                  'ortiqcha': oxirgi.ortiqcha, 'kutilgan': oxirgi.kutilgan} if oxirgi else None,
    }

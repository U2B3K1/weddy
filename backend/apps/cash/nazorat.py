"""Nazorat eslatmalari: unutilgan tasdiqlar va libos sanog'i.

Tezkor qismi (topshiriq, o'tkazma) — Telegram bot jarayonida daqiqada bir (`tezkor_eslatmalar`): ikkita kichik so'rov,
faqat tasdiq kutayotgan yozuvlar (qisman indeks). Qaytarilmagan liboslar — soatlik cron (`eslatmalarni_yuborish`).
Libos sanog'i eslatilmaydi: rahbar o'zi istalgan vaqtda o'tkazadi (foydalanuvchi qarori, 2026-11-01).
Har eslatma bir marta yoziladi (`kalit`), shuning uchun qayta-qayta ishga tushsa ham takrorlanmaydi.
"""
from datetime import timedelta

from django.utils import timezone

from apps.notify.services import rahbarlarga, som, xabar_yoz
from apps.tenants.models import Salon, Xodim

from .models import KassaTopshirish, Tolov

TOPSHIRIQ_KUTISH = timedelta(minutes=2)    # qabul qiluvchiga qayta eslatma
TOPSHIRIQ_RAHBARGA = timedelta(minutes=15)  # shundan keyin ham tasdiqlanmasa — rahbarga
OTKAZMA_KUTISH = timedelta(minutes=2)  # mijoz hali salonda bo'lganida bilish kerak: pul kelmasa undan so'raladi


def _yozilgan(kalitlar):
    """Shu kalitli eslatmalar allaqachon yozilganmi — har daqiqada qayta INSERT urinib ko'rmaslik uchun."""
    from apps.notify.models import Xabar
    return set(Xabar.objects.filter(kalit__in=kalitlar).values_list('kalit', flat=True)) if kalitlar else set()


def _topshiriqlar(hozir):
    soni = 0
    royxat = list(KassaTopshirish.objects.filter(holat=KassaTopshirish.Holat.KUTILMOQDA, yaratilgan__lte=hozir - TOPSHIRIQ_KUTISH)
                  .exclude(salon__holat=Salon.Holat.BLOKLANGAN).select_related('kimdan', 'kimga', 'salon'))
    bor = _yozilgan([f'kt_eslatma:{t.id}' for t in royxat] + [f'kt_rahbar:{t.id}' for t in royxat])
    for t in royxat:
        if f'kt_eslatma:{t.id}' in bor and (t.rahbarga or f'kt_rahbar:{t.id}' in bor):
            continue
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
    royxat = list(Tolov.objects.filter(tasdiq=Tolov.Tasdiq.KUTILMOQDA, vaqt__lte=hozir - OTKAZMA_KUTISH)
                  .exclude(salon__holat=Salon.Holat.BLOKLANGAN).select_related('salon', 'xodim', 'zakaz'))
    bor = _yozilgan([f'ot_eslatma:{t.id}' for t in royxat])
    for t in royxat:
        if f'ot_eslatma:{t.id}' in bor:
            continue
        tugmalar = [[{'text': '✅ Keldi', 'callback_data': f'ot:{t.id}:k'},
                     {'text': '❌ Kelmadi', 'callback_data': f'ot:{t.id}:y'}]]
        z = f' (zakaz #{t.zakaz.raqam})' if t.zakaz_id else ''
        soni += len([x for x in rahbarlarga(t.salon, 'otkazma_tasdiq',
                                            f"⏰ Eslatma: {t.get_usul_display()} {som(t.summa)}{z}, qabul qildi {t.xodim.ism} — "
                                            f"hisobingizga keldimi? Hali tasdiqlanmagan.", tugmalar, kalit=f'ot_eslatma:{t.id}') if x])
    return soni


def _qaytmagan_liboslar(hozir):
    """Qaytarish kuni kelgan (yoki o'tgan), lekin «Qaytarildi» deb qabul qilinmagan libos: kechqurun libosni bergan
    sotuvchiga va rahbarga. Libos qaytgan bo'lsa — tizimda qabul qilinmagan; qaytmagan bo'lsa — mijoz bilan bog'lanish kerak.
    Vaqt — salon sozlamasidagi `qaytarish_tekshiruv_vaqti` (standart 18:00)."""
    from apps.orders.models import Zakaz
    from apps.tenants.models import sozlama

    mahalliy = timezone.localtime(hozir)
    bugun = mahalliy.date()
    vaqtlar = {}  # salon -> tekshiruv vaqti keldimi
    soni = 0
    for z in (Zakaz.objects.filter(holat=Zakaz.Holat.BERILDI, qaytarish__lte=bugun)
              .exclude(salon__holat=Salon.Holat.BLOKLANGAN).select_related('salon', 'mijoz', 'sotuvchi')
              .prefetch_related('pozitsiyalar__libos')):
        if z.salon_id not in vaqtlar:
            vaqtlar[z.salon_id] = mahalliy.time() >= sozlama(z.salon).qaytarish_tekshiruv_vaqti
        if not vaqtlar[z.salon_id]:
            continue
        kun = (bugun - z.qaytarish).days
        liboslar = ', '.join(f'{p.libos.artikul} {p.libos.nomi}' for p in z.pozitsiyalar.all())
        matn = (f"⏰ Zakaz #{z.raqam} · {z.mijoz.fio or 'mijoz'} ({z.mijoz.telefon}): {liboslar} "
                f"{'bugun qaytarilishi kerak edi' if not kun else f'{kun} kun kechikmoqda'}, lekin «Qaytarildi» deb qabul qilinmagan.\n"
                f"Libos qaytgan bo'lsa — tizimda qabul qiling; qaytmagan bo'lsa — mijoz bilan bog'laning.")
        kalit = f'qaytmadi:{z.id}:{bugun}'
        if z.sotuvchi and z.sotuvchi.faol and z.sotuvchi.rol != Xodim.Rol.RAHBAR:
            soni += bool(xabar_yoz(z.sotuvchi, 'libos_qaytmadi', matn, kalit=kalit))
        soni += len([x for x in rahbarlarga(z.salon, 'libos_qaytmadi', matn, kalit=kalit) if x])
    return soni


def tezkor_eslatmalar(hozir=None):
    """Topshiriq va o'tkazma eslatmalari (bot jarayonida daqiqada bir). Yozilgan eslatmalar soni."""
    hozir = hozir or timezone.now()
    return _topshiriqlar(hozir) + _otkazmalar(hozir)


def nazorat_eslatmalari(hozir=None):
    """Hammasi (soatlik cron; bot ishlamay qolsa ham tezkorlari shu yerda yoziladi). Yozilgan eslatmalar soni."""
    hozir = hozir or timezone.now()
    return tezkor_eslatmalar(hozir) + _qaytmagan_liboslar(hozir)


def dashbord_nazorati(salon, bugun=None, kun=7):
    """Rahbar dashbordi uchun egasining uch savoli, oxirgi `kun` kun bo'yicha: kassada kamomad bormi (kim, qancha),
    nima diqqat talab qiladi (tasdiqlanmagan topshiriq va o'tkazma, kelmagan o'tkazma, terminal farqi), liboslar joyidami."""
    from apps.catalog.models import Sanoq

    from .models import Smena
    bugun = bugun or timezone.localdate()
    dan = bugun - timedelta(days=kun - 1)
    kamomad = {}  # xodim id -> [ism, jami] (faqat manfiy farqlar)
    terminal = 0
    for s in (Smena.objects.filter(salon=salon, sana__range=(dan, bugun), yopilgan__isnull=False)
              .prefetch_related('ishtirokchilar__xodim')):
        for i in s.ishtirokchilar.all():
            f = i.farq if i.farq is not None else (s.farq if i.chiqqan == s.yopilgan else None)
            if f and f < 0:
                kamomad.setdefault(i.xodim_id, [i.xodim.ism, 0])[1] += f
        terminal += s.terminal_farq or 0
    kelmadi = Tolov.objects.filter(salon=salon, tasdiq=Tolov.Tasdiq.KELMADI, tasdiq_vaqti__date__range=(dan, bugun))
    oxirgi = Sanoq.objects.filter(salon=salon, yakunlangan__isnull=False).order_by('-yakunlangan').first()
    return {
        'kun': kun,
        'kamomad': sum(v for _, v in kamomad.values()),
        'kamomad_xodimlar': [{'ism': ism, 'summa': v} for ism, v in sorted(kamomad.values(), key=lambda x: x[1])],
        'terminal_farq': terminal,
        'topshiriqlar': KassaTopshirish.objects.filter(salon=salon, holat=KassaTopshirish.Holat.KUTILMOQDA).count(),
        'otkazmalar': Tolov.objects.filter(salon=salon, tasdiq=Tolov.Tasdiq.KUTILMOQDA).count(),
        'kelmadi_soni': kelmadi.count(), 'kelmadi_summa': sum(t.summa for t in kelmadi),
        'sanoq': {'kun_oldin': (bugun - timezone.localdate(oxirgi.yakunlangan)).days, 'yoq': oxirgi.yoq,
                  'ortiqcha': oxirgi.ortiqcha, 'kutilgan': oxirgi.kutilgan} if oxirgi else None,
    }

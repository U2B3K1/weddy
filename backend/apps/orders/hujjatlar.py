"""Chop etiladigan hujjatlar: shartnoma (FT-10.2, FT-10.3, FT-16.1), kvitansiya va zalog dalolatnomasi (FT-7.4).

Server hujjat ma'lumotini va avtomatik bandlarni beradi; brauzer uni chop etadi yoki PDF ga saqlaydi.
"""
from django.utils import timezone

from apps.cash.models import Tolov
from apps.cash.services import tolangan_summa
from apps.tenants.models import sozlama

from .models import Zakaz, Zalog


class HujjatXatosi(Exception):
    pass


def _som(n):
    return f'{n:,}'.replace(',', ' ') + " so'm"


def _asos(zakaz):
    salon, m = zakaz.salon, zakaz.mijoz
    return {
        'zakaz_raqami': zakaz.raqam,
        'sana': timezone.localdate(),
        'salon': {'nomi': salon.nomi, 'yuridik_nom': salon.yuridik_nom or salon.nomi, 'stir': salon.stir,
                  'manzil': salon.manzil, 'telefon': salon.telefon},
        'mijoz': {'fio': m.fio, 'telefon': m.telefon},
        'sotuvchi': zakaz.sotuvchi.ism if zakaz.sotuvchi else '',
        'olib_ketish': zakaz.olib_ketish, 'qaytarish': zakaz.qaytarish,
    }


def _pozitsiyalar(zakaz):
    qatorlar = [{'nomi': f'{p.libos.artikul} {p.libos.nomi}', 'narx': p.narx}
                for p in zakaz.pozitsiyalar.select_related('libos')]
    qatorlar += [{'nomi': f'{a.dona.aksessuar.nomi} ({a.dona.yorliq})', 'narx': a.narx}
                 for a in zakaz.aksessuarlar.select_related('dona__aksessuar')]
    if zakaz.xizmatlar:  # FT-2.8: moslash xizmati alohida qator — qatorlar yig'indisi asosiy narxga teng
        qatorlar.append({'nomi': 'Moslash xizmati', 'narx': zakaz.xizmatlar})
    return qatorlar


ZALOG_MATNI = {
    'pul': "Mijoz zalog sifatida pul qoldiradi. Zalog ijara haqi emas va libos shartnomada ko'rsatilgan holatda "
           "qaytarilganda to'liq qaytariladi; jarima yoki zarar bo'lsa, summasi zalogdan ushlab qolinadi.",
    'hujjat': "Mijoz zalog sifatida hujjat qoldiradi. Hujjat salonda seyfda saqlanadi va libos qaytarilganda "
              "qaytariladi; jarima yoki zarar bo'lsa, u to'lanmaguncha hujjat qaytarilmaydi.",
    'tillo': "Mijoz zalog sifatida tillo buyum qoldiradi. Buyum tavsifi va og'irligi dalolatnomada yoziladi, "
             "qaytarishda qayta tortiladi; jarima yoki zarar bo'lsa, u to'lanmaguncha buyum qaytarilmaydi.",
}


def shartnoma(zakaz):
    """Shartnoma admin panel sozlamalariga qarab shakllanadi (FT-10.3, FT-16.1).

    Chegirma tasdiqlanmaguncha shartnoma chop etilmaydi (FT-11.3).
    """
    if zakaz.holat == Zakaz.Holat.CHEGIRMA_KUTILMOQDA:
        raise HujjatXatosi("Chegirma tasdiqlanmaguncha shartnoma va kvitansiya chop etilmaydi.")
    if zakaz.holat == Zakaz.Holat.BEKOR:
        raise HujjatXatosi('Bekor qilingan zakazga shartnoma chop etilmaydi.')
    soz = sozlama(zakaz.salon)
    tolangan = tolangan_summa(zakaz)
    bandlar = [
        {'sarlavha': 'Ijara predmeti va muddati',
         'matn': f"Salon quyida ko'rsatilgan libos va aksessuarlarni {zakaz.olib_ketish:%d.%m.%Y} dan "
                 f"{zakaz.qaytarish:%d.%m.%Y} gacha vaqtincha foydalanishga (ijaraga) beradi. Buyumlar sotilmaydi "
                 "va mijozning mulkiga o'tmaydi."},
        {'sarlavha': "To'lov",
         'matn': f"Ijara haqi jami {_som(zakaz.jami)}. Shundan {_som(tolangan)} to'langan, qoldiq "
                 f"{_som(zakaz.jami - tolangan)}. Qoldiq libos berilgunga qadar to'liq to'lanadi; qoldiq "
                 "to'lanmaguncha libos berilmaydi."},
    ]

    # Zalog bandi tanlangan zalog turiga mos keladi; hali olinmagan bo'lsa yoqilgan turlar sanaladi
    olingan = list(dict.fromkeys(zakaz.zaloglar.values_list('turi', flat=True)))
    turlar = olingan or soz.zalog_turlari()
    if olingan:
        zalog_matni = ' '.join(ZALOG_MATNI[t] for t in turlar)
    else:
        nomlar = ', '.join(Zalog.Turi(t).label.lower() for t in turlar)
        # jarima oqibati faqat yoqilgan zalog turlari bo'yicha yoziladi (FT-16.1)
        oqibat = []
        if 'pul' in turlar:
            oqibat.append('summasi pul zalogidan ushlab qolinadi')
        buyumlar = ' yoki '.join(Zalog.Turi(t).label.lower() for t in turlar if t != 'pul')
        if buyumlar:
            oqibat.append(f"{buyumlar} jarima to'lanmaguncha qaytarilmaydi")
        zalog_matni = (f"Libos berilayotganda mijoz zalog qoldiradi ({nomlar}). Zalog ijara haqi emas va libos "
                       "shartnomadagi holatda qaytarilganda to'liq qaytariladi; jarima yoki zarar bo'lsa, "
                       + ', '.join(oqibat) + '.')
    bandlar.append({'sarlavha': 'Zalog', 'matn': zalog_matni})

    bandlar.append({
        'sarlavha': 'Qaytarish va zarar uchun javobgarlik',
        'matn': f"Mijoz buyumlarni {zakaz.qaytarish:%d.%m.%Y} kuni toza va butun holda qaytaradi. Qaytarishda buyum holati "
                "tekshiriladi (dog', yirtiq, yo'qolgan aksessuar). Mijoz aybi bilan yetkazilgan zarar uchun salon belgilagan "
                "summani to'laydi."})

    if soz.kechikish_jarimasi:  # o'chirilgan bo'lsa jarima bandi chiqmaydi (S09)
        bandlar.append({
            'sarlavha': 'Kechikish jarimasi',
            'matn': f"Buyumlar belgilangan kundan kech qaytarilsa, har bir kechikkan kun uchun "
                    f"{_som(soz.kechikish_kunlik_summa)} jarima to'lanadi."})

    qismlar = []
    qoida = soz.qaytarish_qoidasi
    for i, (kun, foiz) in enumerate(qoida):
        if kun > 0:
            yuqori = f' ({qoida[i - 1][0] - 1} kungacha)' if i > 0 else ''
            qismlar.append(f"{kun} kun va undan ko'p{yuqori} qolganda — {foiz}%")
        else:
            oldingi = qoida[i - 1][0] if i > 0 else 0
            qismlar.append((f"{oldingi} kundan kam qolganda" if oldingi else 'istalgan vaqtda') + f" — {foiz}%")
    bandlar.append({
        'sarlavha': 'Bekor qilish va avansni qaytarish',
        'matn': "Zakaz libos berilgunga qadar bekor qilinishi mumkin. Avansning qaytariladigan qismi olib ketish "
                "sanasigacha qolgan kunga bog'liq: " + '; '.join(qismlar) + ". Libos berilgandan keyin zakaz bekor "
                "qilinmaydi, faqat muddatidan oldin qaytariladi."})

    # Salonning o'z bandlari (admin paneldan); avtomatik bandlar sozlamalarga bog'liq bo'lgani uchun tahrirlanmaydi
    for b in soz.shartnoma_bandlari or []:
        bandlar.append({'sarlavha': b['sarlavha'], 'matn': b['matn']})

    bandlar.append({
        'sarlavha': "Shaxsiy ma'lumotlar",
        'matn': "Mijoz ushbu shartnomani bajarish maqsadida o'zining shaxsiy ma'lumotlari (F.I.O., telefon, zalog "
                "ma'lumotlari) salon tomonidan qayta ishlanishiga va O'zbekiston hududida saqlanishiga rozilik beradi."})

    return {
        **_asos(zakaz), 'tur': 'shartnoma', 'sarlavha': f'Ijara shartnomasi № {zakaz.raqam}',
        'pozitsiyalar': _pozitsiyalar(zakaz),
        'narx': {'asosiy': zakaz.asosiy_narx, 'ustama': zakaz.ustama, 'chegirma': zakaz.chegirma,
                 'jami': zakaz.jami, 'tolangan': tolangan, 'qoldiq': zakaz.jami - tolangan},
        'bandlar': [{'raqam': i, **b} for i, b in enumerate(bandlar, 1)],
        'imzolar': ['Salon', 'Mijoz'],
    }


def kvitansiya(zakaz):
    if zakaz.holat == Zakaz.Holat.CHEGIRMA_KUTILMOQDA:
        raise HujjatXatosi("Chegirma tasdiqlanmaguncha shartnoma va kvitansiya chop etilmaydi.")
    tolovlar = zakaz.tolovlar.filter(tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA,
                                              Tolov.Tur.VOZVRAT]).select_related('xodim').order_by('vaqt')
    if not tolovlar:
        raise HujjatXatosi("Zakazda hali to'lov yo'q.")
    tolangan = tolangan_summa(zakaz)
    return {
        **_asos(zakaz), 'tur': 'kvitansiya', 'sarlavha': f"To'lov kvitansiyasi (zakaz № {zakaz.raqam})",
        'pozitsiyalar': _pozitsiyalar(zakaz),
        'tolovlar': [{'tur': t.get_tur_display(), 'summa': t.summa, 'usul': t.get_usul_display(),
                      'sana': timezone.localtime(t.vaqt).date(), 'xodim': t.xodim.ism} for t in tolovlar],
        'narx': {'jami': zakaz.jami, 'tolangan': tolangan, 'qoldiq': zakaz.jami - tolangan},
        'imzolar': ['Sotuvchi', 'Mijoz'],
    }


def dalolatnoma(zakaz):
    """Zalog qabul qilish va qaytarish dalolatnomasi; sotuvchi va mijoz imzolaydi (FT-7.4, FT-7.5)."""
    zaloglar = list(zakaz.zaloglar.all())
    if not zaloglar:
        raise HujjatXatosi('Zakazda zalog yo\'q.')
    akt = getattr(zakaz, 'qaytarish_akti', None)
    qatorlar = []
    for z in zaloglar:
        if z.turi == Zalog.Turi.PUL:
            tavsif = _som(z.summa)
        elif z.turi == Zalog.Turi.HUJJAT:
            tavsif = f'{z.hujjat_turi} № {z.hujjat_raqami}'
        else:
            tavsif = f"{z.tavsif}, {z.ogirlik_gr} g, taxminiy qiymati {_som(z.summa)}"
        qatorlar.append({'yorliq': z.yorliq, 'turi': z.get_turi_display(), 'tavsif': tavsif,
                         'holat': z.get_holat_display(),
                         'olingan': timezone.localtime(z.olingan).date(),
                         'qaytarilgan': timezone.localtime(z.qaytarilgan).date() if z.qaytarilgan else None})
    qaytarish = None
    if akt:
        qaytarish = {'sana': akt.sana, 'tekshiruv': akt.get_tekshiruv_display(), 'jarima': akt.jarima,
                     'ushlab_qolingan': akt.ushlab_qolingan, 'qarz': akt.qarz,
                     'kechikish_kunlari': akt.kechikish_kunlari, 'tortilgan_gr': akt.tortilgan_gr,
                     'ogirlik_mos': akt.ogirlik_mos}
    return {
        **_asos(zakaz), 'tur': 'dalolatnoma',
        'sarlavha': f"Zalog qabul qilish{' va qaytarish' if akt else ''} dalolatnomasi (zakaz № {zakaz.raqam})",
        'zaloglar': qatorlar, 'qaytarish_akti': qaytarish,  # 'qaytarish' — asosiy qismdagi sana
        'imzolar': ['Sotuvchi', 'Mijoz'],
    }


TURLAR = {'shartnoma': shartnoma, 'kvitansiya': kvitansiya, 'dalolatnoma': dalolatnoma}

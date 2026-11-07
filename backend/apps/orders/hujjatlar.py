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
    # C-29: pul zalog summasi — olingan bo'lsa haqiqiysi, hali olinmagan bo'lsa liboslar zalogi (oldindan ma'lum)
    pul_zalog = (sum(z.summa for z in zakaz.zaloglar.filter(turi=Zalog.Turi.PUL)) if 'pul' in olingan
                 else sum(p.zalog for p in zakaz.pozitsiyalar.all()))
    if olingan:
        zalog_matni = ' '.join(ZALOG_MATNI[t] for t in turlar)
        if pul_zalog:
            zalog_matni = zalog_matni.replace('pul qoldiradi.', f'pul qoldiradi ({_som(pul_zalog)}).', 1)
    else:
        nomlar = ', '.join(Zalog.Turi(t).label.lower() for t in turlar)
        # jarima oqibati faqat yoqilgan zalog turlari bo'yicha yoziladi (FT-16.1)
        oqibat = []
        if 'pul' in turlar:
            oqibat.append('summasi pul zalogidan ushlab qolinadi')
        buyumlar = ' yoki '.join(Zalog.Turi(t).label.lower() for t in turlar if t != 'pul')
        if buyumlar:
            oqibat.append(f"{buyumlar} jarima to'lanmaguncha qaytarilmaydi")
        if 'pul' in turlar and pul_zalog:
            nomlar = nomlar.replace('pul', f'pul — {_som(pul_zalog)}', 1)
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
    from .changes import bekor_qoidasi
    qoida, asos, avans_foizi = bekor_qoidasi(zakaz)  # QA-17: zakazga qotirilgan qoida (eski zakazda — joriy sozlama)
    for i, (kun, foiz) in enumerate(qoida):
        if kun > 0:
            yuqori = f' ({qoida[i - 1][0] - 1} kungacha)' if i > 0 else ''
            qismlar.append(f"{kun} kun va undan ko'p{yuqori} qolganda — {foiz}%")
        else:
            oldingi = qoida[i - 1][0] if i > 0 else 0
            qismlar.append((f"{oldingi} kundan kam qolganda" if oldingi else 'istalgan vaqtda') + f" — {foiz}%")
    bandlar.append({'sarlavha': 'Bekor qilish va avansni qaytarish',
                    'matn': bekor_qilish_matni(zakaz, asos, avans_foizi, qismlar)})

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


def bekor_qilish_matni(zakaz, asos, avans_foizi, qismlar):
    """Shartnomaning bekor qilish bandi zakazga qotirilgan qoidani aniq aytadi (C-21, QA-17), raqamli misol bilan."""
    boshi = "Zakaz libos berilgunga qadar bekor qilinishi mumkin. "
    oxiri = ". Libos berilgandan keyin zakaz bekor qilinmaydi, faqat muddatidan oldin qaytariladi."
    if asos == 'tolangan':
        return (boshi + "To'langan summaning qaytariladigan qismi olib ketish sanasigacha qolgan kunga bog'liq: "
                + '; '.join(qismlar) + oxiri)
    if avans_foizi:
        avans = zakaz.jami * avans_foizi // 100
        return (boshi + f"Avans — zakaz summasining {avans_foizi}% i (bu zakazda {_som(zakaz.jami)} dan {_som(avans)}). "
                "Avansning qaytariladigan qismi olib ketish sanasigacha qolgan kunga bog'liq: " + '; '.join(qismlar)
                + ". Avansdan ortiq oldindan to'langan summa to'liq qaytariladi" + oxiri)
    return (boshi + "Avansning qaytariladigan qismi olib ketish sanasigacha qolgan kunga bog'liq: " + '; '.join(qismlar)
            + ". Avans — bron qilishda avans sifatida to'langan summa; avansdan tashqari oldindan to'langan summa "
            "to'liq qaytariladi" + oxiri)


def kvitansiya(zakaz):
    """To'lovlar kvitansiyasi (C-09): mijozga qaytarilgan pul manfiy va «Qaytarildi» nomi bilan; rahbar «kelmadi»
    degan o'tkazma `kelmadi: true` (hisobga olinmagan — chizib ko'rsatiladi); bekor qilingan zakazda pastki blok
    «To'langan · Qaytarildi · Ushlab qolindi» (qoldiq yo'q — mijoz hech narsa qarzdor emas)."""
    if zakaz.holat == Zakaz.Holat.CHEGIRMA_KUTILMOQDA:
        raise HujjatXatosi("Chegirma tasdiqlanmaguncha shartnoma va kvitansiya chop etilmaydi.")
    tolovlar = zakaz.tolovlar.filter(tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA,
                                              Tolov.Tur.VOZVRAT]).select_related('xodim').order_by('vaqt')
    if not tolovlar:
        raise HujjatXatosi("Zakazda hali to'lov yo'q.")
    qatorlar = []
    for t in tolovlar:
        chiqim = t.tur == Tolov.Tur.VOZVRAT
        qatorlar.append({'tur': 'Qaytarildi' if chiqim else t.get_tur_display(), 'summa': -t.summa if chiqim else t.summa,
                         'usul': t.get_usul_display(), 'sana': timezone.localtime(t.vaqt).date(), 'xodim': t.xodim.ism,
                         'chiqim': chiqim, 'kelmadi': t.tasdiq == Tolov.Tasdiq.KELMADI})
    if zakaz.holat == Zakaz.Holat.BEKOR:
        kirim = sum(t.summa for t in tolovlar if t.tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ)
                    and t.tasdiq != Tolov.Tasdiq.KELMADI)
        qaytdi = sum(t.summa for t in tolovlar if t.tur == Tolov.Tur.VOZVRAT)
        narx = {'bekor': True, 'jami': zakaz.jami, 'tolangan': kirim, 'qaytarildi': qaytdi, 'ushlab_qolindi': kirim - qaytdi}
    else:
        tolangan = tolangan_summa(zakaz)
        narx = {'jami': zakaz.jami, 'tolangan': tolangan, 'qoldiq': zakaz.jami - tolangan}
    return {
        **_asos(zakaz), 'tur': 'kvitansiya', 'sarlavha': f"To'lov kvitansiyasi (zakaz № {zakaz.raqam})",
        'pozitsiyalar': _pozitsiyalar(zakaz), 'tolovlar': qatorlar, 'narx': narx,
        'imzolar': ['Sotuvchi', 'Mijoz'],
    }


def dalolatnoma(zakaz):
    """Zalog qabul qilish va qaytarish dalolatnomasi; sotuvchi va mijoz imzolaydi (FT-7.4, FT-7.5)."""
    zaloglar = list(zakaz.zaloglar.all())
    if not zaloglar:
        raise HujjatXatosi('Zakazda zalog yo\'q.')
    akt = getattr(zakaz, 'qaytarish_akti', None)
    qatorlar = []
    ushlash = akt.ushlab_qolingan if akt else 0  # jarima pul zaloglaridan tartib bilan ushlangan (rental.libos_qaytarish)
    for z in zaloglar:
        ushlandi = 0
        holat = z.get_holat_display()
        if z.turi == Zalog.Turi.PUL:
            tavsif = _som(z.summa)
            if z.qaytarilgan and ushlash:
                ushlandi = min(ushlash, z.summa)
                ushlash -= ushlandi
                holat = ('Jarimaga ushlab qolindi' if ushlandi == z.summa
                         else f"{_som(z.summa - ushlandi)} qaytarildi, {_som(ushlandi)} jarimaga ushlab qolindi")
        elif z.turi == Zalog.Turi.HUJJAT:
            tavsif = f'{z.hujjat_turi} № {z.hujjat_raqami}'
        else:
            tavsif = f"{z.tavsif}, {z.ogirlik_gr} g, taxminiy qiymati {_som(z.summa)}"
        qatorlar.append({'yorliq': z.yorliq, 'turi': z.get_turi_display(), 'tavsif': tavsif,
                         'holat': holat, 'ushlab_qolindi': ushlandi,
                         'olingan': timezone.localtime(z.olingan).date(),
                         # to'liq ushlangan pul zalog mijozga qaytarilmagan — «qaytarilgan» sanasi yo'q
                         'qaytarilgan': (timezone.localtime(z.qaytarilgan).date()
                                         if z.qaytarilgan and not (ushlandi and ushlandi == z.summa) else None)})
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

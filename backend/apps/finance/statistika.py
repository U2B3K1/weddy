"""Statistika va hisobotlar (6.3, 6.6). Har bir hisobot bir xil ko'rinishda qaytadi:

    {'sarlavha', 'izoh', 'ustunlar': [{'nom', 'tur'}], 'qatorlar': [[...]], 'jami': [...] | None}

`tur`: 'matn' | 'son' | 'pul' | 'foiz' | 'sana'. Hisobotlar faqat sahifada ko'rsatiladi, fayl sifatida yuklab olinmaydi (FT-18.3).
Daromad qoidasi hamma joyda bir xil: tushum — davrda TO'LIQ TO'LANGAN zakazlar (6.1).
"""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.bookings.models import Bron
from apps.cash.models import Smena, Tolov
from apps.catalog.models import Libos
from apps.orders.models import (ChegirmaSorovi, Mijoz, QaytarishAkti, Salonchi, Zakaz, ZakazPozitsiya,
                                Zalog)
from apps.tenants.models import Xodim

from .models import Xarajat

BERILGAN = (Zakaz.Holat.BERILDI, Zakaz.Holat.QAYTARILDI, Zakaz.Holat.YOPILDI)
FAOL_LIBOS = (Libos.Holat.BOSH, Libos.Holat.TOZALASHDA, Libos.Holat.TAMIRDA)


def _u(*ustunlar):
    return [{'nom': n, 'tur': t} for n, t in ustunlar]


def _tolangan(salon, dan, gacha, sotuvchi=None, filial=None):
    q = Zakaz.objects.filter(salon=salon, tolangan_sana__range=(dan, gacha)).exclude(holat=Zakaz.Holat.BEKOR)
    if filial:  # zakaz rasmiylashtirilgan filial
        q = q.filter(filial_id=filial)
    return q.filter(sotuvchi_id=sotuvchi) if sotuvchi else q


def _liboslar(salon, kategoriya=None, filial=None):
    q = Libos.objects.filter(salon=salon, holat__in=FAOL_LIBOS)
    if filial:  # libos turgan filial
        q = q.filter(filial_id=filial)
    return q.filter(kategoriya_id=kategoriya) if kategoriya else q


def libos_samaradorligi(salon, dan, gacha, kategoriya=None, filial=None, **_):
    berilgan = dict(ZakazPozitsiya.objects.filter(salon=salon, zakaz__holat__in=BERILGAN,
                                                  zakaz__olib_ketish__range=(dan, gacha))
                    .values_list('libos_id').annotate(n=Count('id')))
    davr_tushum = dict(ZakazPozitsiya.objects.filter(zakaz__in=_tolangan(salon, dan, gacha))
                       .values_list('libos_id').annotate(s=Sum('narx')))
    umumiy = dict(ZakazPozitsiya.objects.filter(salon=salon, zakaz__tolangan_sana__isnull=False)
                  .exclude(zakaz__holat=Zakaz.Holat.BEKOR).values_list('libos_id').annotate(s=Sum('narx')))
    oxirgi = {}
    for lid, sana in (ZakazPozitsiya.objects.filter(salon=salon, zakaz__holat__in=BERILGAN)
                      .values_list('libos_id', 'zakaz__olib_ketish').order_by('zakaz__olib_ketish')):
        oxirgi[lid] = sana
    # FT-15.4: libos bo'yicha o'rtacha mijoz bahosi (davrdagi qaytarishlar)
    baho = dict(ZakazPozitsiya.objects.filter(salon=salon, zakaz__qaytarish_akti__sana__range=(dan, gacha),
                                              zakaz__qaytarish_akti__baho__isnull=False)
                .values_list('libos_id').annotate(a=Avg('zakaz__qaytarish_akti__baho')))
    bugun = timezone.localdate()
    qatorlar = []
    for l in _liboslar(salon, kategoriya, filial).select_related('kategoriya').order_by('artikul'):
        jami = umumiy.get(l.id, 0)
        qatorlar.append([f'{l.artikul} {l.nomi}', l.kategoriya.nomi, berilgan.get(l.id, 0), davr_tushum.get(l.id, 0),
                         round(jami / l.tannarx * 100, 1) if l.tannarx else None, oxirgi.get(l.id),
                         (bugun - oxirgi[l.id]).days if l.id in oxirgi else None,
                         round(baho[l.id], 1) if l.id in baho else None])
    kalitlar = [l.id for l in _liboslar(salon, kategoriya, filial).order_by('artikul')]
    return {'kalitlar': kalitlar, 'sarlavha': 'Libos samaradorligi',
            'izoh': "Tushum — libosning ijara narxi bo'yicha (chegirma va ustamasiz). Qoplash — butun davrdagi tushum / tannarx.",
            'ustunlar': _u(('Libos', 'matn'), ('Kategoriya', 'matn'), ('Berilgan', 'son'), ('Tushum', 'pul'),
                           ('Qoplash', 'foiz'), ('Oxirgi marta', 'sana'), ("Bo'sh turgan kun", 'son'), ("O'rtacha baho", 'son')),
            'qatorlar': qatorlar,
            'jami': ['Jami', '', sum(q[2] for q in qatorlar), sum(q[3] for q in qatorlar), None, None, None, None]}


def kategoriyalar(salon, dan, gacha, sotuvchi=None, filial=None, **_):
    q = (ZakazPozitsiya.objects.filter(zakaz__in=_tolangan(salon, dan, gacha, sotuvchi, filial))
         .values_list('libos__kategoriya__nomi', 'libos__kategoriya_id').annotate(n=Count('zakaz', distinct=True), s=Sum('narx')).order_by('-s'))
    q = list(q)
    qatorlar = [[nom, n, s] for nom, _id, n, s in q]
    return {'kalitlar': [k for _nom, k, _n, _s in q], 'sarlavha': 'Kategoriyalar', 'izoh': "To'liq to'langan zakazlar; tushum libos ijara narxi bo'yicha.",
            'ustunlar': _u(('Kategoriya', 'matn'), ('Zakazlar', 'son'), ('Tushum', 'pul')),
            'qatorlar': qatorlar, 'jami': ['Jami', sum(q[1] for q in qatorlar), sum(q[2] for q in qatorlar)]}


def sotuvchilar(salon, dan, gacha, filial=None, **_):
    tol = {r['sotuvchi_id']: r for r in _tolangan(salon, dan, gacha, filial=filial).values('sotuvchi_id')
           .annotate(n=Count('id'), s=Sum('jami'))}
    yangi = dict(Zakaz.objects.filter(salon=salon, yaratilgan__date__range=(dan, gacha)).exclude(holat=Zakaz.Holat.BEKOR)
                 .values_list('sotuvchi_id').annotate(n=Count('id')))
    cheg = defaultdict(lambda: [0, 0])
    for sid, holat, n in (ChegirmaSorovi.objects.filter(salon=salon, yaratilgan__date__range=(dan, gacha),
                                                        holat__in=[ChegirmaSorovi.Holat.TASDIQLANDI, ChegirmaSorovi.Holat.RAD])
                          .values_list('sotuvchi_id', 'holat').annotate(n=Count('id'))):
        cheg[sid][0 if holat == ChegirmaSorovi.Holat.TASDIQLANDI else 1] = n
    baho = dict(QaytarishAkti.objects.filter(salon=salon, sana__range=(dan, gacha), baho__isnull=False)
                .values_list('zakaz__sotuvchi_id').annotate(a=Avg('baho')))
    qatorlar, kalitlar = [], []
    for x in Xodim.objects.filter(salon=salon).order_by('ism'):
        t = tol.get(x.id, {})
        if not (x.faol or t or yangi.get(x.id)):
            continue
        kalitlar.append(x.id)
        qatorlar.append([x.ism, yangi.get(x.id, 0), t.get('n', 0), t.get('s', 0) or 0, cheg[x.id][0], cheg[x.id][1],
                         round(baho[x.id], 1) if x.id in baho else None])
    return {'kalitlar': kalitlar, 'sarlavha': 'Sotuvchilar', 'izoh': '',
            'ustunlar': _u(('Sotuvchi', 'matn'), ('Yangi zakazlar', 'son'), ("To'langan zakazlar", 'son'), ('Tushum', 'pul'),
                           ('Chegirma tasdiqlandi', 'son'), ('Chegirma rad', 'son'), ("O'rtacha baho", 'son')),
            'qatorlar': qatorlar,
            'jami': ['Jami', sum(q[1] for q in qatorlar), sum(q[2] for q in qatorlar), sum(q[3] for q in qatorlar), None, None, None]}


def salonchilar(salon, dan, gacha, sotuvchi=None, **_):
    tol = {r['salonchi_id']: r for r in _tolangan(salon, dan, gacha, sotuvchi).filter(salonchi__isnull=False).values('salonchi_id')
           .annotate(s=Sum('jami'))}
    mij = dict(Zakaz.objects.filter(salon=salon, salonchi__isnull=False, yaratilgan__date__range=(dan, gacha),
                                    **({'sotuvchi_id': sotuvchi} if sotuvchi else {}))
               .exclude(holat=Zakaz.Holat.BEKOR).values_list('salonchi_id').annotate(n=Count('mijoz', distinct=True)))
    royxat = [s for s in Salonchi.objects.filter(salon=salon).order_by('ism') if s.faol or s.id in mij or s.id in tol]
    qatorlar = [[s.ism, s.salon_nomi, mij.get(s.id, 0), (tol.get(s.id) or {}).get('s') or 0] for s in royxat]
    return {'kalitlar': [s.id for s in royxat], 'sarlavha': 'Salonchilar', 'izoh': 'Komissiya berilmaydi — faqat statistika (FT-6.5).',
            'ustunlar': _u(('Salonchi', 'matn'), ('Salon', 'matn'), ('Olib kelgan mijozlar', 'son'), ('Tushum', 'pul')),
            'qatorlar': qatorlar, 'jami': ['Jami', '', sum(q[2] for q in qatorlar), sum(q[3] for q in qatorlar)]}


def mijoz_manbalari(salon, dan, gacha, sotuvchi=None, **_):
    tol = dict(_tolangan(salon, dan, gacha, sotuvchi).values_list('mijoz__manba').annotate(s=Sum('jami')))
    mij = dict(Zakaz.objects.filter(salon=salon, yaratilgan__date__range=(dan, gacha),
                                    **({'sotuvchi_id': sotuvchi} if sotuvchi else {})).exclude(holat=Zakaz.Holat.BEKOR)
               .values_list('mijoz__manba').annotate(n=Count('mijoz', distinct=True)))
    qatorlar = [[nom, mij.get(k, 0), tol.get(k) or 0] for k, nom in Mijoz.Manba.choices]
    return {'kalitlar': [k for k, _nom in Mijoz.Manba.choices], 'sarlavha': 'Mijoz manbalari', 'izoh': '',
            'ustunlar': _u(('Manba', 'matn'), ('Mijozlar', 'son'), ('Tushum', 'pul')),
            'qatorlar': qatorlar, 'jami': ['Jami', sum(q[1] for q in qatorlar), sum(q[2] for q in qatorlar)]}


def zaloglar(salon, dan, gacha, **_):
    qatorlar = []
    for g in (Zalog.objects.filter(salon=salon, holat__in=[Zalog.Holat.SAQLANMOQDA, Zalog.Holat.USHLAB_QOLINDI])
              .select_related('zakaz__mijoz').order_by('olingan')):
        qatorlar.append([g.yorliq, g.get_turi_display(), f'#{g.zakaz.raqam}', g.zakaz.mijoz.fio or g.zakaz.mijoz.telefon,
                         g.summa if g.turi == Zalog.Turi.PUL else None, timezone.localtime(g.olingan).date(),
                         g.get_holat_display()])
    pul = sum(q[4] or 0 for q in qatorlar)
    return {'sarlavha': 'Zaloglar reestri', 'izoh': 'Hozir salonda saqlanayotgan zaloglar (davrga bog\'liq emas).',
            'ustunlar': _u(('Yorliq', 'matn'), ('Turi', 'matn'), ('Zakaz', 'matn'), ('Mijoz', 'matn'), ('Pul summasi', 'pul'),
                           ('Olingan', 'sana'), ('Holat', 'matn')),
            'qatorlar': qatorlar, 'jami': [f'{len(qatorlar)} ta zalog', '', '', '', pul, None, '']}


def zalog_statistikasi(salon, dan, gacha, **_):
    q = Zalog.objects.filter(salon=salon, olingan__date__range=(dan, gacha))
    qatorlar = []
    for k, nom in Zalog.Turi.choices:
        t = q.filter(turi=k)
        qatorlar.append([nom, t.count(), t.filter(holat=Zalog.Holat.QAYTARILDI).count(),
                         t.filter(holat=Zalog.Holat.USHLAB_QOLINDI).count(), t.filter(holat=Zalog.Holat.SAQLANMOQDA).count()])
    return {'sarlavha': 'Zalog statistikasi', 'izoh': 'Davrda olingan zaloglar turi bo\'yicha (FT-7.2).',
            'ustunlar': _u(('Turi', 'matn'), ('Olingan', 'son'), ('Qaytarilgan', 'son'), ('Ushlab qolingan', 'son'),
                           ('Saqlanmoqda', 'son')),
            'qatorlar': qatorlar, 'jami': None}


def bosh_liboslar(salon, dan, gacha, kun=None, kategoriya=None, filial=None, **_):
    """FT-15.3: tushumi tannarxidan kam va `kun` kundan beri berilmagan liboslar (kun — sozlamadan, standart 60)."""
    from apps.tenants.models import sozlama
    if kun is None:
        kun = sozlama(salon).qoplamagan_kun
    bugun = timezone.localdate()
    oxirgi = {}
    for lid, sana in (ZakazPozitsiya.objects.filter(salon=salon, zakaz__holat__in=BERILGAN)
                      .values_list('libos_id', 'zakaz__olib_ketish').order_by('zakaz__olib_ketish')):
        oxirgi[lid] = sana
    umumiy = dict(ZakazPozitsiya.objects.filter(salon=salon, zakaz__tolangan_sana__isnull=False)
                  .exclude(zakaz__holat=Zakaz.Holat.BEKOR).values_list('libos_id').annotate(s=Sum('narx')))
    qatorlar = []
    for l in _liboslar(salon, kategoriya, filial).order_by('artikul'):
        asos = oxirgi.get(l.id) or timezone.localtime(l.yaratilgan).date()
        bosh_kun = (bugun - asos).days
        tushum = umumiy.get(l.id, 0)
        if bosh_kun >= kun and (l.tannarx is None or tushum < l.tannarx):
            qatorlar.append([f'{l.artikul} {l.nomi}', oxirgi.get(l.id), bosh_kun, tushum, l.tannarx])
    qatorlar.sort(key=lambda q: -q[2])
    return {'sarlavha': "Qoplamagan va bo'sh liboslar", 'izoh': f"{kun} kundan beri berilmagan va tannarxini qoplamagan liboslar.",
            'ustunlar': _u(('Libos', 'matn'), ('Oxirgi marta', 'sana'), ("Bo'sh turgan kun", 'son'), ('Jami tushum', 'pul'),
                           ('Tannarx', 'pul')),
            'qatorlar': qatorlar, 'jami': None}


def bekor_qilinganlar(salon, dan, gacha, sotuvchi=None, **_):
    qatorlar = [[f'#{z.raqam}', z.mijoz.fio or z.mijoz.telefon, timezone.localtime(z.bekor_vaqti).date(), z.bekor_sabab,
                 z.qaytarilgan_avans, z.ushlab_qolingan_avans]
                for z in Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.BEKOR, bekor_vaqti__date__range=(dan, gacha),
                                              **({'sotuvchi_id': sotuvchi} if sotuvchi else {}))
                .select_related('mijoz').order_by('bekor_vaqti')]
    return {'sarlavha': 'Bekor qilingan zakazlar', 'izoh': "Ushlab qolingan avans «boshqa daromad»ga yoziladi.",
            'ustunlar': _u(('Zakaz', 'matn'), ('Mijoz', 'matn'), ('Sana', 'sana'), ('Sabab', 'matn'),
                           ('Qaytarilgan avans', 'pul'), ('Ushlab qolingan', 'pul')),
            'qatorlar': qatorlar, 'jami': [f'{len(qatorlar)} ta', '', None, '', sum(q[4] for q in qatorlar), sum(q[5] for q in qatorlar)]}


def kechikish_va_jarimalar(salon, dan, gacha, sotuvchi=None, **_):
    aktlar = (QaytarishAkti.objects.filter(salon=salon, sana__range=(dan, gacha),
                                           **({'zakaz__sotuvchi_id': sotuvchi} if sotuvchi else {}))
              .filter(Q(kechikish_kunlari__gt=0) | Q(jarima__gt=0)).select_related('zakaz__mijoz').order_by('sana'))
    qatorlar = [[f'#{a.zakaz.raqam}', a.zakaz.mijoz.fio or a.zakaz.mijoz.telefon, a.sana, a.get_tekshiruv_display(),
                 a.kechikish_kunlari, a.jarima, a.ushlab_qolingan, a.qarz] for a in aktlar]
    return {'sarlavha': 'Kechikish va jarimalar', 'izoh': '',
            'ustunlar': _u(('Zakaz', 'matn'), ('Mijoz', 'matn'), ('Qaytarilgan', 'sana'), ('Holat', 'matn'), ('Kechikish, kun', 'son'),
                           ('Jarima', 'pul'), ('Zalogdan ushlandi', 'pul'), ('Qarz', 'pul')),
            'qatorlar': qatorlar,
            'jami': ['Jami', '', None, '', sum(q[4] for q in qatorlar), sum(q[5] for q in qatorlar), sum(q[6] for q in qatorlar),
                     sum(q[7] for q in qatorlar)]}


def xarajatlar(salon, dan, gacha, **_):
    q = Xarajat.objects.filter(salon=salon, sana__range=(dan, gacha))
    from .moddalar import modda_nomlari, togridan_kodlar
    nomlar, tk = modda_nomlari(salon), togridan_kodlar(salon)
    tasdiq = dict(q.filter(holat=Xarajat.Holat.TASDIQLANDI).values_list('modda').annotate(s=Sum('summa')))
    kutmoqda = dict(q.filter(holat=Xarajat.Holat.KUTILMOQDA).values_list('modda').annotate(s=Sum('summa')))
    qatorlar = [[nomlar[m], "To'g'ridan-to'g'ri" if m in tk else 'Operatsion', tasdiq.get(m, 0), kutmoqda.get(m, 0)]
                for m in nomlar if tasdiq.get(m) or kutmoqda.get(m)]
    return {'sarlavha': 'Xarajatlar', 'izoh': 'Tasdiq kutayotgan xarajatlar foyda/zarar hisobotiga kirmaydi.',
            'ustunlar': _u(('Modda', 'matn'), ('Turi', 'matn'), ('Tasdiqlangan', 'pul'), ('Tasdiq kutmoqda', 'pul')),
            'qatorlar': qatorlar, 'jami': ['Jami', '', sum(q[2] for q in qatorlar), sum(q[3] for q in qatorlar)]}


def pul_oqimi(salon, dan, gacha, **_):
    """Haqiqatda kirgan va chiqqan pul, to'lov usullari bo'yicha (6.1). Zalog daromad emas, lekin pul harakati."""
    q = Tolov.objects.filter(salon=salon, vaqt__date__range=(dan, gacha))
    qatorlar = []
    for usul, nom in Tolov.Usul.choices:
        u = q.filter(usul=usul)
        s = lambda *turlar: u.filter(tur__in=turlar).aggregate(s=Sum('summa'))['s'] or 0  # noqa: E731
        tushum, zalog_in = s(Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA), s(Tolov.Tur.ZALOG)
        zalog_out, xarajat, vozvrat, inkass = (s(Tolov.Tur.ZALOG_QAYTARISH), s(Tolov.Tur.XARAJAT), s(Tolov.Tur.VOZVRAT),
                                               s(Tolov.Tur.INKASSATSIYA))
        if any((tushum, zalog_in, zalog_out, xarajat, vozvrat, inkass)):
            qatorlar.append([nom, tushum, zalog_in, zalog_out, xarajat, vozvrat, inkass,
                             tushum + zalog_in - zalog_out - xarajat - vozvrat - inkass])
    j = [sum(q[i] for q in qatorlar) for i in range(1, 8)]
    return {'sarlavha': 'Pul oqimi', 'izoh': 'Kassa orqali o\'tgan pul. Kassadan tashqari (rahbar kiritgan) xarajatlar bu yerda yo\'q.',
            'ustunlar': _u(("To'lov usuli", 'matn'), ('Tushum', 'pul'), ('Zalog olindi', 'pul'), ('Zalog qaytarildi', 'pul'),
                           ('Xarajat', 'pul'), ('Pul qaytarildi', 'pul'), ('Inkassatsiya', 'pul'), ('Sof oqim', 'pul')),
            'qatorlar': qatorlar, 'jami': ['Jami', *j]}


def kassa(salon, dan, gacha, filial=None, **_):
    qatorlar = [[s.sana, s.ochgan.ism, s.boshlangich_qoldiq, s.hisobdagi_qoldiq, s.fakt_qoldiq, s.farq,
                 s.izoh if s.yopilgan else 'smena ochiq']
                for s in Smena.objects.filter(salon=salon, sana__range=(dan, gacha), **({'filial_id': filial} if filial else {}))
                .select_related('ochgan').order_by('sana', 'id')]
    return {'sarlavha': 'Kunlik kassa', 'izoh': 'Naqd pul bo\'yicha smenalar (4.12).',
            'ustunlar': _u(('Sana', 'sana'), ('Ochgan', 'matn'), ("Boshlang'ich qoldiq", 'pul'), ('Hisobdagi qoldiq', 'pul'),
                           ('Fakt qoldiq', 'pul'), ('Farq', 'pul'), ('Izoh', 'matn')),
            'qatorlar': qatorlar, 'jami': ['Farqlar jami', '', None, None, None, sum(q[5] or 0 for q in qatorlar), '']}


def bandlik(salon, dan, gacha, kategoriya=None, filial=None, **_):
    """Liboslar yuklanganligi: band kunlar (bufer bilan) / davrdagi kunlar."""
    kunlar = (gacha - dan).days + 1
    band = defaultdict(int)
    for b in Bron.faol().filter(salon=salon, oraliq__overlap=(dan, gacha + timedelta(days=1))):
        boshi, oxiri = max(b.oraliq.lower, dan), min(b.oraliq.upper, gacha + timedelta(days=1))
        band[b.libos_id] += max(0, (oxiri - boshi).days)
    qatorlar = [[f'{l.artikul} {l.nomi}', min(band[l.id], kunlar), round(min(band[l.id], kunlar) / kunlar * 100, 1)]
                for l in _liboslar(salon, kategoriya, filial).order_by('artikul')]
    qatorlar.sort(key=lambda q: -q[1])
    jami_band = sum(q[1] for q in qatorlar)
    return {'sarlavha': 'Bandlik', 'izoh': f'Davr: {kunlar} kun. Band kunlarga tozalash (bufer) kunlari ham kiradi.',
            'ustunlar': _u(('Libos', 'matn'), ('Band kunlar', 'son'), ('Yuklanganlik', 'foiz')),
            'qatorlar': qatorlar,
            'jami': ["O'rtacha", jami_band, round(jami_band / (kunlar * len(qatorlar)) * 100, 1) if qatorlar else None]}


def kelgusi_bronlar(salon, dan, gacha, **_):
    """Kelgusi oylarga band qilingan zakazlar: avanslar portfeli (FT-18.5). Davr emas, bugundan keyingi bronlar."""
    from apps.cash.services import tolangan_summa
    bugun = timezone.localdate()
    oylar = defaultdict(lambda: [0, 0, 0])
    for z in Zakaz.objects.filter(salon=salon, olib_ketish__gte=bugun, holat__in=[Zakaz.Holat.BRON, Zakaz.Holat.VAQTINCHALIK]):
        t = tolangan_summa(z)
        o = oylar[z.olib_ketish.strftime('%Y-%m')]
        o[0] += 1; o[1] += t; o[2] += z.jami - t
    qatorlar = [[oy, *v] for oy, v in sorted(oylar.items())]
    return {'sarlavha': 'Kelgusi bronlar', 'izoh': 'Bugundan keyin olib ketiladigan zakazlar, oyma-oy.',
            'ustunlar': _u(('Oy', 'matn'), ('Zakazlar', 'son'), ('Olingan avans', 'pul'), ('Kutilayotgan (qoldiq)', 'pul')),
            'qatorlar': qatorlar, 'jami': ['Jami', sum(q[1] for q in qatorlar), sum(q[2] for q in qatorlar), sum(q[3] for q in qatorlar)]}


def chegirmalar(salon, dan, gacha, sotuvchi=None, **_):
    qatorlar = []
    for s in (ChegirmaSorovi.objects.filter(salon=salon, yaratilgan__date__range=(dan, gacha),
                                            **({'sotuvchi_id': sotuvchi} if sotuvchi else {}))
              .select_related('zakaz', 'sotuvchi', 'rahbar').order_by('yaratilgan')):
        soralgan = f'{float(s.foiz):g}%' if s.foiz is not None else (f'{s.summa:,}'.replace(',', ' ') if s.summa else '')
        qatorlar.append([f'#{s.zakaz.raqam}', s.sotuvchi.ism if s.sotuvchi else '', soralgan,
                         s.izoh if s.holat == ChegirmaSorovi.Holat.TAYYOR else s.get_sabab_display(), s.get_holat_display(),
                         s.tasdiqlangan_summa, s.rahbar.ism if s.rahbar else ''])
    return {'sarlavha': 'Chegirmalar', 'izoh': '',
            'ustunlar': _u(('Zakaz', 'matn'), ('Sotuvchi', 'matn'), ("So'ralgan", 'matn'), ('Sabab', 'matn'), ('Qaror', 'matn'),
                           ('Berilgan chegirma', 'pul'), ('Rahbar', 'matn')),
            'qatorlar': qatorlar, 'jami': ['Jami', '', '', '', '', sum(q[5] or 0 for q in qatorlar), '']}


HISOBOTLAR = {
    'libos': libos_samaradorligi, 'kategoriya': kategoriyalar, 'sotuvchi': sotuvchilar, 'salonchi': salonchilar,
    'manba': mijoz_manbalari, 'zalog': zaloglar, 'zalog-statistika': zalog_statistikasi, 'bosh-liboslar': bosh_liboslar,
    'bekor': bekor_qilinganlar, 'kechikish': kechikish_va_jarimalar, 'xarajat': xarajatlar, 'pul-oqimi': pul_oqimi,
    'kassa': kassa, 'bandlik': bandlik, 'kelgusi': kelgusi_bronlar, 'chegirma': chegirmalar,
}

# Qaysi hisobotda qaysi filtr ishlaydi (FT-20.1); qolganlarida filtr ma'nosiz (masalan, kassa).
FILTRLAR = {
    'libos': ('kategoriya', 'filial'), 'bosh-liboslar': ('kategoriya', 'filial'), 'bandlik': ('kategoriya', 'filial'),
    'kategoriya': ('sotuvchi', 'filial'), 'sotuvchi': ('filial',), 'kassa': ('filial',),
    'salonchi': ('sotuvchi',), 'manba': ('sotuvchi',), 'bekor': ('sotuvchi',),
    'kechikish': ('sotuvchi',), 'chegirma': ('sotuvchi',),
}


# FT-18.2: qatorni tashkil qilgan zakazlar — faqat qatori «to'liq to'langan zakazlar»dan yig'iladigan hisobotlar uchun
TAFSILOT_FILTRI = {
    'libos': lambda k: {'pozitsiyalar__libos_id': int(k)},
    'kategoriya': lambda k: {'pozitsiyalar__libos__kategoriya_id': int(k)},
    'sotuvchi': lambda k: {'sotuvchi_id': int(k)},
    'salonchi': lambda k: {'salonchi_id': int(k)},
    'manba': lambda k: {'mijoz__manba': k},
}


def tafsilot(salon, nom, kalit, dan, gacha, **filtrlar):
    """Hisobot qatoriga kirgan, davrda to'liq to'langan zakazlar. Noma'lum hisobot yoki kalit — None.

    Hisobot ochilgan filtrlar (sotuvchi, filial) tafsilotga ham qo'llanadi — aks holda tafsilot jami u ochilgan
    filtrlangan qatordan katta chiqardi. «libos» hisobotida filtrlar libosga tegishli va qator o'zi bitta libos.
    """
    filtr = TAFSILOT_FILTRI.get(nom)
    if filtr is None:
        return None
    try:
        shart = filtr(kalit)
    except (TypeError, ValueError):
        return None
    zakaz_filtrlari = {k: v for k, v in filtrlar.items()
                       if v and k in ('sotuvchi', 'filial') and k in FILTRLAR.get(nom, ()) and nom != 'libos'}
    zakazlar = (_tolangan(salon, dan, gacha, **zakaz_filtrlari).filter(**shart).distinct().select_related('mijoz', 'sotuvchi')
                .prefetch_related('pozitsiyalar__libos').order_by('tolangan_sana', 'raqam'))
    qatorlar = [{'zakaz_id': z.id, 'raqam': z.raqam, 'sana': z.tolangan_sana, 'mijoz': z.mijoz.fio or z.mijoz.telefon,
                 'sotuvchi': z.sotuvchi.ism if z.sotuvchi else None,
                 'liboslar': [p.libos.nomi for p in z.pozitsiyalar.all()], 'jami': z.jami} for z in zakazlar]
    return {'qatorlar': qatorlar, 'jami': sum(q['jami'] for q in qatorlar)}

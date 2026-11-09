"""Ro'yxat va dashbord endpointlari: zakazlar, sotuvchi bosh ekrani (FT-1.2), rahbar dashbordi (6.5)."""
import re
from datetime import timedelta

from django.db.models import Case, Count, F, IntegerField, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cash.models import Tolov
from apps.cash.services import kassa_hisobot, ochiq_smena, tolangan_summa
from apps.catalog.models import Libos
from apps.finance import reports
from apps.finance.models import Xarajat
from apps.tenants.models import Xodim
from apps.tenants.permissions import IsRahbar, IsStaff, salon_yoza_oladimi, yozish_taqiqi

from . import hujjatlar
from .changes import muddati_otganlarni_bekor_qil
from .models import ChegirmaSorovi, Zakaz, ZakazTarixi, Zalog


def _qisqa(z):
    return {'id': z.id, 'raqam': z.raqam, 'holat': z.holat, 'mijoz': z.mijoz.fio or z.mijoz.telefon,
            'telefon': z.mijoz.telefon, 'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish,
            'jami': z.jami, 'filial': z.filial_id, 'sotuvchi': z.sotuvchi.ism if z.sotuvchi_id else None,
            'liboslar': [p.libos.nomi for p in z.pozitsiyalar.all()],
            'aksessuarlar': [f'{a.dona.aksessuar.nomi} ({a.dona.yorliq})' for a in z.aksessuarlar.all()]}


def _zakazlar(salon):
    return (Zakaz.objects.filter(salon=salon).select_related('mijoz', 'sotuvchi')
            .prefetch_related('pozitsiyalar__libos', 'aksessuarlar__dona__aksessuar'))


# To'langan summa — `cash.services.tolangan_summa` bilan bir xil ta'rif (R3, C-07): avans + qoldiq (rahbar «kelmadi»
# demagan) minus mijozga qaytarilgan (VOZVRAT — narx kamayganda farq yoki bekor qilishdagi qaytarim). Bitta so'rovda,
# zakaz boshiga emas. Boshqa JOIN (masalan, bronlar) bilan birga ishlatilmasin — Sum ko'payib ketadi.
TOLANGAN = (Coalesce(Sum('tolovlar__summa', filter=~Q(tolovlar__tasdiq='kelmadi') & Q(tolovlar__tur__in=[
    Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ])), 0)
            - Coalesce(Sum('tolovlar__summa', filter=Q(tolovlar__tur=Tolov.Tur.VOZVRAT)), 0))
AVANSSIZ = (Zakaz.Holat.VAQTINCHALIK, Zakaz.Holat.CHEGIRMA_KUTILMOQDA)


def _bron_muddati_sq():
    """A-17: avanssiz bron qachon o'zi bekor bo'ladi — zakaz bronlarining eng erta muddati (subquery, JOIN emas)."""
    from apps.bookings.models import Bron
    return Subquery(Bron.objects.filter(zakaz=OuterRef('pk'), turi=Bron.Turi.VAQTINCHALIK, muddati__isnull=False)
                    .order_by('muddati').values('muddati')[:1])


def _jadval_qs(qs):
    """Jadval qatori uchun: to'langan summa, bron muddati va birinchi libos rasmi (prefetch) — bitta so'rovda."""
    return (qs.prefetch_related('pozitsiyalar__libos__rasmlar')
            .annotate(tolangan_s=TOLANGAN, bron_muddati_s=_bron_muddati_sq()))


def _jadval_qatori(request, z):
    """Zakazlar ro'yxati, bosh ekran va qarzdorlar jadvalidagi bitta qator (bir xil ko'rinish uchun bir xil maydonlar)."""
    poz = next(iter(z.pozitsiyalar.all()), None)
    tolangan = getattr(z, 'tolangan_s', None)
    if tolangan is None:
        tolangan = tolangan_summa(z)
    return {**_qisqa(z), 'tolangan': tolangan, 'qoldiq': max(0, z.jami - tolangan),
            'bron_muddati': getattr(z, 'bron_muddati_s', None) if z.holat in AVANSSIZ else None,
            'rasm': _libos_rasmi(request, poz.libos) if poz else None,
            # Kassa → To'lov qabul chekida (maket): birinchi libosning artikuli va o'lchami
            'artikul': poz.libos.artikul if poz else None, 'olcham': poz.libos.olcham if poz else None}


def eslatmalar(salon, bugun):
    """Sotuvchiga eslatmalar (4.14): mijozga emas, sotuvchiga chiqadi — u mijoz bilan o'zi bog'lanadi.

    Bugun «Bog'landim» bosilgan eslatma `boglangan=True` bo'lib qaytadi (FT-14.2).
    """
    from datetime import timedelta
    from apps.bookings.models import Bron

    ertaga = bugun + timedelta(days=1)
    asos = Zakaz.objects.filter(salon=salon).select_related('mijoz')
    natija = []

    def qosh(tur, zakaz, matn, qoldiq=None):
        natija.append({'tur': tur, 'zakaz_id': zakaz.id, 'raqam': zakaz.raqam, 'mijoz': zakaz.mijoz.fio,
                       'telefon': zakaz.mijoz.telefon, 'matn': matn, 'qoldiq': qoldiq})

    from apps.notify.services import som
    # A-29: eslatmada qancha pul olinishi ham — sotuvchi zakazni ochmasdan mijozga aytadi
    for zk in (asos.filter(olib_ketish=ertaga, holat__in=[Zakaz.Holat.BRON, Zakaz.Holat.VAQTINCHALIK])
               .annotate(tolangan_s=TOLANGAN)):
        qoldiq = max(0, zk.jami - zk.tolangan_s)
        if zk.holat == Zakaz.Holat.VAQTINCHALIK and not zk.tolangan_s and zk.jami:
            matn = f"Ertaga libosni olib ketadi, avans hali olinmagan (jami {som(zk.jami)}). Mijozga eslating."
        elif qoldiq:
            matn = f"Ertaga libosni olib ketadi. Qoldiq {som(qoldiq)} — mijozga eslating."
        else:
            matn = "Ertaga libosni olib ketadi. To'lov to'liq — kelish vaqtini kelishib oling."
        qosh('olib_ketish_ertaga', zk, matn, qoldiq)
    for zk in asos.filter(qaytarish=bugun, holat=Zakaz.Holat.BERILDI):
        qosh('qaytarish_bugun', zk, "Bugun libos qaytarilishi kerak. Mijoz bilan bog'laning.")
    for zk in asos.filter(qaytarish__lt=bugun, holat=Zakaz.Holat.BERILDI):
        qosh('kechikdi', zk, f"Libos {(bugun - zk.qaytarish).days} kun kechikdi. Mijoz bilan bog'laning.")
    # FT-2.8: bugungi va ertangi primerkalar
    from .models import Primerka
    for p in (Primerka.objects.filter(salon=salon, holat=Primerka.Holat.REJALASHTIRILGAN,
                                      zakaz__holat__in=[Zakaz.Holat.BRON, Zakaz.Holat.VAQTINCHALIK])
              .select_related('zakaz__mijoz')):
        mahalliy = timezone.localtime(p.vaqt)
        if mahalliy.date() == bugun:
            qosh('primerka_bugun', p.zakaz, f'Bugun soat {mahalliy:%H:%M} da primerka.')
        elif mahalliy.date() == ertaga:
            qosh('primerka_ertaga', p.zakaz, f"Ertaga soat {mahalliy:%H:%M} da primerka. Mijozga eslating.")
    chegara = timezone.now() + timedelta(hours=2)
    tugayotgan = set(Bron.objects.filter(salon=salon, turi=Bron.Turi.VAQTINCHALIK, zakaz__isnull=False,
                                         muddati__gt=timezone.now(), muddati__lte=chegara)
                     .values_list('zakaz_id', flat=True))
    for zk in asos.filter(id__in=tugayotgan, holat=Zakaz.Holat.VAQTINCHALIK):
        qosh('bron_tugayapti', zk, "Avans kiritilmadi. Mijoz bilan bog'laning yoki bron bekor bo'ladi.")

    bajarilgan = set(ZakazTarixi.objects.filter(salon=salon, harakat='boglandi', vaqt__date=bugun,
                                                zakaz_id__in=[e['zakaz_id'] for e in natija])
                     .values_list('zakaz_id', 'eski'))
    for e in natija:
        e['boglangan'] = (e['zakaz_id'], e['tur']) in bajarilgan
    return natija


ZAKAZ_RAQAMI_MAX = 5   # «98», «#120» — zakaz raqami; uzunrog'i faqat telefon
TELEFON_MIN = 4        # telefon bo'yicha qidiruv kamida 4 raqamdan (aks holda «98» hamma +998… ga mos tushadi)


def q_filtri(q):
    """A-01: qidiruv matni → (filtr, aniq_raqam).

    Faqat raqamlardan iborat matn (bo'shliq, «#», «-», qavslar e'tiborsiz): ≤5 xona bo'lsa — aniq zakaz raqami
    (javobda birinchi qator), 4+ xona bo'lsa — telefon ham. «+» bilan boshlangan matn — faqat telefon.
    Boshqa matn — telefon yoki F.I.O. ichida.
    """
    q = q.strip()
    raqamlar = re.sub(r'[\s#+\-()]', '', q)
    if not raqamlar.isdigit():
        return Q(mijoz__telefon__icontains=q) | Q(mijoz__fio__icontains=q), None
    aniq = int(raqamlar) if len(raqamlar) <= ZAKAZ_RAQAMI_MAX and not q.startswith('+') else None
    f = Q(raqam=aniq) if aniq is not None else Q(pk__in=[])
    if len(raqamlar) >= TELEFON_MIN:
        f |= Q(mijoz__telefon__contains=raqamlar)
    return f, aniq


def _qidiruv(request, qs):
    """Ro'yxat va tab sonlari uchun umumiy filtr: ?filial= va ?q= (raqam yoki telefon/F.I.O.). (qs, aniq_raqam)"""
    filial = request.query_params.get('filial', '')
    if filial.isdigit():
        qs = qs.filter(filial_id=int(filial))
    q = request.query_params.get('q', '').strip()
    aniq = None
    if q:
        f, aniq = q_filtri(q)
        qs = qs.filter(f)
    return qs, aniq


def _kechikkan(qs):
    """Libos mijozda, qaytarish sanasi o'tgan."""
    return qs.filter(holat=Zakaz.Holat.BERILDI, qaytarish__lt=timezone.localdate())


OLIB_KETILMAGAN = [Zakaz.Holat.VAQTINCHALIK, Zakaz.Holat.CHEGIRMA_KUTILMOQDA, Zakaz.Holat.BRON]
# «Faol» tab (Zakazlar standart tabi): ish davom etayotgan zakazlar — yopilgan, qarzli va bekorlar tashqarida
FAOL_HOLATLAR = [*OLIB_KETILMAGAN, Zakaz.Holat.BERILDI]


def _ertaga():
    return timezone.localdate() + timedelta(days=1)


# «Bugun» tasmasi: holat emas, sanaga bog'liq tezkor filtrlar (ro'yxat ?holat= va tab sonlari bilan bir xil kalitlar).
# Bosh ekran va rahbar dashbordi ham shu ta'riflarni ishlatadi (A-10) — sonlar hamma joyda bir xil.
BUGUN_FILTRLARI = {
    'kechikkan': _kechikkan,
    'bugun_olib': lambda qs: qs.filter(olib_ketish=timezone.localdate(), holat__in=OLIB_KETILMAGAN),
    'bugun_qaytar': lambda qs: qs.filter(qaytarish=timezone.localdate(), holat=Zakaz.Holat.BERILDI),
    # sotuvchi kechqurun ertangi liboslarni tayyorlaydi (tozalash, dazmol)
    'ertaga_olib': lambda qs: qs.filter(olib_ketish=_ertaga(), holat__in=OLIB_KETILMAGAN),
    'ertaga_qaytar': lambda qs: qs.filter(qaytarish=_ertaga(), holat=Zakaz.Holat.BERILDI),
}
ROYXAT_KESIMI = 200   # ?sahifa siz eski (massiv) javob shuncha qator bilan cheklanadi
SAHIFA_STANDART, SAHIFA_MAX = 50, 200


def tolov_kutmoqda(qs):
    """Kassa → To'lov qabul: avans yoki qoldiq olinadigan zakazlar. To'liq chegirmali (0 so'm) vaqtinchalik bron ham —
    kassir uni «to'lovsiz» tasdiqlaydi. C-03: berilgan/qaytarilgan zakaz ham — o'tkazma «kelmadi» deb belgilansa qoldiq
    qaytadan paydo bo'ladi va mijozdan olinadi. `qs` TOLANGAN bilan `tolangan_s` annotatsiyasiga ega bo'lishi shart."""
    return qs.filter(holat__in=[Zakaz.Holat.VAQTINCHALIK, Zakaz.Holat.BRON, Zakaz.Holat.BERILDI, Zakaz.Holat.QAYTARILDI]).filter(
        Q(jami__gt=F('tolangan_s')) | Q(holat=Zakaz.Holat.VAQTINCHALIK, jami=0))


def _butun(qiymat, standart, kichik=0, katta=None):
    try:
        n = int(qiymat)
    except (TypeError, ValueError):
        return standart
    n = max(kichik, n)
    return min(n, katta) if katta is not None else n


def sahifala(request, qs):
    """?sahifa=1&limit=&offset= → (qatorlar, jami); `sahifa` berilmasa → (None, None) — chaqiruvchi eski javobni beradi."""
    if not request.query_params.get('sahifa'):
        return None, None
    limit = _butun(request.query_params.get('limit'), SAHIFA_STANDART, 1, SAHIFA_MAX)
    offset = _butun(request.query_params.get('offset'), 0)
    return qs[offset:offset + limit], qs.count()


class ZakazlarRoyxatiView(APIView):
    """GET /api/zakazlar/royxat/?holat=&q=&filial=

    holat: zakaz holati, `faol` (vaqtinchalik, chegirma, bron, berildi), BUGUN_FILTRLARI kaliti yoki `tolov_kutmoqda`
    (Kassa: avans/qoldiq olinadiganlar, `olib_ketish` bo'yicha, kesimsiz).
    ?sahifa=1&limit=50&offset=0 → {"natija": [...], "jami": N}; `sahifa` siz — massiv (eski format, 200 tagacha).
    Qidiruvda aniq zakaz raqami (A-01) har doim birinchi qator.
    """
    permission_classes = [IsStaff]

    def get(self, request):
        if salon_yoza_oladimi(request.salon):  # «faqat ko'rish» salonida GET hech narsa yozmaydi; cron baribir ishlaydi
            muddati_otganlarni_bekor_qil(request.salon)
        qs, aniq = _qidiruv(request, _zakazlar(request.salon))
        holat = request.query_params.get('holat')
        # Jadval uchun: to'lov progressi (to'langan / jami) va birinchi libos rasmi — bitta so'rovda, zakaz boshiga emas
        qs = _jadval_qs(qs)
        tartib, kesim = ['-raqam'], ROYXAT_KESIMI
        if holat == 'tolov_kutmoqda':
            qs, tartib, kesim = tolov_kutmoqda(qs), ['olib_ketish', 'raqam'], None
        elif holat == 'faol':
            qs = qs.filter(holat__in=FAOL_HOLATLAR)
        elif holat in BUGUN_FILTRLARI:
            qs = BUGUN_FILTRLARI[holat](qs)
        elif holat:
            qs = qs.filter(holat=holat)
        if aniq is not None:  # «98» → #98 birinchi, keyin telefonida 98 bo'lganlar
            tartib = [Case(When(raqam=aniq, then=Value(0)), default=Value(1), output_field=IntegerField()), *tartib]
        qs = qs.order_by(*tartib)
        sahifa, jami = sahifala(request, qs)
        if sahifa is not None:
            return Response({'natija': [_jadval_qatori(request, z) for z in sahifa], 'jami': jami})
        return Response([_jadval_qatori(request, z) for z in (qs if kesim is None else qs[:kesim])])


class ZakazSonlariView(APIView):
    """GET /api/zakazlar/sonlar/?q=&filial= — holat tablari yonidagi sonlar (ro'yxat bilan bir xil qidiruv).

    Kalitlar: har holat, '' (hammasi), `faol`, BUGUN_FILTRLARI kalitlari va `tolov_kutmoqda` (Zakazlar ko'rsatkich kartasi —
    Kassa «To'lov qabul» bilan bir xil ta'rif).
    """
    permission_classes = [IsStaff]

    def get(self, request):
        qs, _ = _qidiruv(request, Zakaz.objects.filter(salon=request.salon))
        sonlar = dict(qs.values_list('holat').annotate(n=Count('id')).order_by())
        return Response({**sonlar, '': sum(sonlar.values()), 'faol': sum(sonlar.get(h, 0) for h in FAOL_HOLATLAR),
                         **{k: fn(qs).count() for k, fn in BUGUN_FILTRLARI.items()},
                         'tolov_kutmoqda': tolov_kutmoqda(qs.annotate(tolangan_s=TOLANGAN)).count()})


def _libos_rasmi(request, libos):
    r = next(iter(libos.rasmlar.all()), None)  # bookings.views._birinchi_rasm bilan bir xil tartib
    return request.build_absolute_uri(r.kichik.url) if r else None


class ZakazTafsilotView(APIView):
    """Zakaz kartasi (ekran 8): pozitsiyalar, to'lovlar, zalog, qarz, tarix."""
    permission_classes = [IsStaff]

    def get(self, request, pk):
        z = _zakazlar(request.salon).filter(id=pk).first()
        if not z:
            raise NotFound('Zakaz topilmadi.')
        tolangan = tolangan_summa(z)
        akt = getattr(z, 'qaytarish_akti', None)
        from apps.bookings.models import Bron
        # A-17: avanssiz bron shu vaqtgacha avans olinmasa o'zi bekor bo'ladi (mustahkam bronda — None)
        bron_muddati = (Bron.objects.filter(zakaz=z, turi=Bron.Turi.VAQTINCHALIK, muddati__isnull=False)
                        .order_by('muddati').values_list('muddati', flat=True).first() if z.holat in AVANSSIZ else None)
        return Response({
            **_qisqa(z), 'asosiy_narx': z.asosiy_narx, 'ustama': z.ustama, 'ustama_foiz': z.ustama_foiz, 'chegirma': z.chegirma,
            'tolangan': tolangan, 'qoldiq': z.jami - tolangan, 'bron_muddati': bron_muddati,
            # kanvas kartasi: «Yaratildi … · sotuvchi», mijoz qatorida to'y sanasi va manba
            'yaratilgan': z.yaratilgan, 'toy_sanasi': z.mijoz.toy_sanasi, 'manba': z.mijoz.get_manba_display() if z.mijoz.manba else '',
            # xronologik tartib (A-30)
            'tolovlar': [{'id': t.id, 'tur': t.tur, 'tur_nomi': t.get_tur_display(), 'summa': t.summa, 'usul': t.usul,
                          'usul_nomi': t.get_usul_display(), 'xodim': t.xodim.ism, 'tasdiq': t.tasdiq,
                          'vaqt': t.vaqt, 'tuzatsa_boladi': _tuzatsa_boladimi(t)}
                         for t in z.tolovlar.select_related('xodim', 'smena').order_by('vaqt', 'id')],
            'zaloglar': [{'id': g.id, 'turi': g.turi, 'turi_nomi': g.get_turi_display(), 'holat': g.holat,
                          'holat_nomi': g.get_holat_display(), 'summa': g.summa,
                          'tavsif': g.tavsif, 'yorliq': g.yorliq} for g in z.zaloglar.all()],
            # dona_id — qaytarishda yo'qolgan donani belgilash uchun (C-10)
            'aksessuar_qatorlari': [{'id': a.id, 'dona_id': a.dona_id, 'nomi': a.dona.aksessuar.nomi, 'yorliq': a.dona.yorliq,
                                     'narx': a.narx} for a in z.aksessuarlar.all()],
            # Zakaz kartasida libos fotosi ko'rinadi — sotuvchi mijoz bilan qaysi libos haqida gaplashayotganini darhol ko'radi
            'libos_qatorlari': [{'id': p.libos_id, 'artikul': p.libos.artikul, 'nomi': p.libos.nomi, 'narx': p.narx,
                                 'olcham': p.libos.olcham, 'rasm': _libos_rasmi(request, p.libos)}
                                for p in z.pozitsiyalar.all()],
            'libos_zalogi': sum(p.libos.zalog for p in z.pozitsiyalar.all()),  # berishda pul zalogi shundan to'ladi
            'qarz': akt.qarz if akt else 0,
            'bekor_sabab': z.bekor_sabab,
            'xizmatlar': z.xizmatlar,
            'mijoz_id': z.mijoz_id,
            'olchamlar': {o: getattr(z.mijoz, o) for o in ('kokrak', 'bel', 'son', 'boy', 'oyoq_olchami', 'kiyim_olchami')},
            'primerkalar': [{'id': p.id, 'vaqt': p.vaqt, 'natija': p.natija, 'moslash_narxi': p.moslash_narxi,
                             'holat': p.holat} for p in z.primerkalar.all()],
            'promokod': z.promokod.kod if z.promokod_id else None, 'promokod_chegirma': z.promokod_chegirma,
            'salonchi': ({'id': z.salonchi_id, 'ism': z.salonchi.ism, 'instagram': z.salonchi.instagram}
                         if z.salonchi_id else None),
            'chegirma_sorovi': _chegirma_sorovi(z),
        })


def _chegirma_sorovi(z):
    """C-06, C-15: kartada nima so'ralgan / qaysi chegirma qo'llangan — oxirgi kutilayotgan yoki amaldagi so'rov."""
    s = (z.chegirma_sorovlari.filter(holat__in=[ChegirmaSorovi.Holat.KUTILMOQDA, ChegirmaSorovi.Holat.TAYYOR,
                                                ChegirmaSorovi.Holat.TASDIQLANDI], promokod_ishlatilishi__isnull=True)
         .select_related('sotuvchi', 'tayyor', 'rahbar').order_by('-yaratilgan', '-id').first())
    if not s:
        return None
    return {'id': s.id, 'holat': s.holat, 'nomi': s.tayyor.nomi if s.tayyor_id else (s.izoh if s.holat == ChegirmaSorovi.Holat.TAYYOR
                                                                                     else s.get_sabab_display()),
            'foiz': s.foiz, 'summa': s.summa, 'tasdiqlangan_summa': s.tasdiqlangan_summa,
            'sotuvchi': s.sotuvchi.ism if s.sotuvchi_id else None, 'rahbar': s.rahbar.ism if s.rahbar_id else None,
            'izoh': s.izoh, 'yaratilgan': s.yaratilgan}


class BoshEkranView(APIView):
    """Sotuvchi bosh ekrani: bugun olib ketiladigan va qaytariladigan liboslar, smena holati (FT-1.2)."""
    permission_classes = [IsStaff]

    def get(self, request):
        if salon_yoza_oladimi(request.salon):  # FT-2.5: cron ishlamay qolsa ham bron osilib qolmaydi
            muddati_otganlarni_bekor_qil(request.salon)
        bugun = timezone.localdate()
        asos = _zakazlar(request.salon)

        def z(kalit):  # Zakazlar ro'yxatidagi qator bilan bir xil (A-28): to'langan/qoldiq (A-11), rasm, bron muddati
            return [_jadval_qatori(request, x) for x in _jadval_qs(BUGUN_FILTRLARI[kalit](asos)).order_by('raqam')]
        from apps.cash.services import xodim_smenasi
        from apps.cash.views import _filial
        smena = xodim_smenasi(request.salon, request.user) or ochiq_smena(request.salon, _filial(request))
        return Response({
            'eslatmalar': eslatmalar(request.salon, bugun),
            # A-10: «bugun olib ketadi» — Zakazlar sahifasidagi chip bilan bir xil ta'rif (vaqtinchalik bron ham)
            'olib_ketiladi': z('bugun_olib'),
            'qaytariladi': z('bugun_qaytar'),
            'kechikkan': z('kechikkan'),
            # kanvas «Ertaga» paneli: ertaga olib ketadigan va qaytaradiganlar (sotuvchi kechqurun tayyorlaydi)
            'ertaga_olib': z('ertaga_olib'),
            'ertaga_qaytar': z('ertaga_qaytar'),
            'smena': {'ochiq': bool(smena), 'id': smena.id if smena else None},
        })


def _davr_bloki(salon, dan, gacha, filial=None):
    """Davr ko'rsatkichlari (FT-19.2), P&L bilan bir xil ta'rif — kassa usuli: tushum pul kirgan kun bo'yicha."""
    r = reports.foyda(salon, dan, gacha, filial)
    return {'hozirgi_daromad': r['tushum'], 'qaytarilgan': r['qaytarilgan'], 'xarajatlar': r['xarajatlar'] + r['sotuvchi_bonusi'],
            'taxminiy_sof_foyda': r['sof_foyda'], 'zakazlar_soni': r['zakazlar_soni'], 'ortacha_chek': r['ortacha_chek']}


def _oldinda(salon, bugun, kunlar=30, filial=None):
    """Keyingi 30 kun: liboslar yuklanganligi (%) va eng band kunlar (6.5)."""
    from collections import Counter
    from datetime import timedelta

    from apps.bookings.models import Bron
    from apps.finance.statistika import bandlik

    oxiri = bugun + timedelta(days=kunlar - 1)
    band = Counter()
    for b in (Bron.faol().filter(salon=salon, oraliq__overlap=(bugun, oxiri + timedelta(days=1)),
                                 **({'libos__filial_id': filial} if filial else {})).select_related('zakaz')):
        # zakaz sanalari (tozalash buferisiz): libos mijozda bo'lgan kunlar
        dan = max(b.zakaz.olib_ketish if b.zakaz else b.oraliq.lower, bugun)
        gacha = min(b.zakaz.qaytarish if b.zakaz else b.oraliq.upper - timedelta(days=1), oxiri)
        for i in range((gacha - dan).days + 1):
            band[dan + timedelta(days=i)] += 1
    eng_band = [{'sana': k, 'liboslar': n} for k, n in sorted(band.items(), key=lambda x: (-x[1], x[0]))[:3]]
    return {'kunlar': kunlar, 'bandlik_foiz': bandlik(salon, bugun, oxiri, filial=filial)['jami'][2] or 0, 'eng_band_kunlar': eng_band}


class RahbarDashbordView(APIView):
    """Rahbar dashbordi (6.5): bugun, tasdiq kutmoqda, shu oy, ogohlantirishlar."""
    permission_classes = [IsRahbar]

    def get(self, request):
        from apps.cash.models import Smena
        salon, bugun = request.salon, timezone.localdate()
        davr = request.query_params.get('davr', 'oy')
        if davr not in ('bugun', 'hafta', 'oy', 'yil'):
            raise ValidationError({'davr': "bugun, hafta, oy yoki yil bo'lishi kerak."})
        # ?filial= — «Bugun», davr va «Oldinda» bloklari shu filial bo'yicha (tasdiqlar va ogohlantirishlar butun salon bo'yicha qoladi)
        filial = request.query_params.get('filial', '')
        if filial:
            from apps.tenants.models import Filial
            if not filial.isdigit() or not Filial.objects.filter(salon=salon, id=int(filial)).exists():
                raise ValidationError({'filial': 'Filial topilmadi.'})
        filial = int(filial) if filial else None
        zf = {'filial_id': filial} if filial else {}
        # FT-13.3: doimiy xarajat qoralamalari dashbord ochilganda ham yaratiladi — rahbar oy davomida «Xarajatlar»
        # sahifasini ochmasa, ijara/oylik shu oy hisobotidan va «tasdiq kutmoqda» ro'yxatidan tushib qolardi
        if salon_yoza_oladimi(salon):
            from apps.finance.moddalar import doimiy_qoralamalarni_yarat
            doimiy_qoralamalarni_yarat(salon)
        # Ochiq smenalar: filial bo'yicha yoki butun salon (filial kassalari yoqilgan bo'lsa bir nechta bo'ladi)
        ochiq_smenalar = list(Smena.objects.filter(salon=salon, yopilgan__isnull=True, **({'filial_id': filial} if filial else {})))
        smena = ochiq_smenalar[0] if ochiq_smenalar else None
        bugungi = Tolov.objects.filter(reports.tolov_filiali(filial), Tolov.HAQIQIY, salon=salon, vaqt__date=bugun,
                                       tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA])
        by_usul = {r['usul']: r['s'] for r in bugungi.values('usul').annotate(s=Sum('summa'))}
        kutilayotgan = reports.kutilayotgan_daromad(salon, bugun, filial)
        berilgan = Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.BERILDI, **zf)
        # FT-15.3: qoplamagan va uzoq bo'sh turgan liboslar dashbordda (sozlamada yoq-o'ch + kun)
        from apps.finance.statistika import bosh_liboslar
        from apps.tenants.models import sozlama
        soz = sozlama(salon)
        qoplamagan = None
        if soz.qoplamagan_royxat:
            qatorlar = bosh_liboslar(salon, bugun, bugun)['qatorlar']
            qoplamagan = {'kun': soz.qoplamagan_kun, 'soni': len(qatorlar),
                          'liboslar': [{'nomi': q[0], 'bosh_kun': q[2], 'tushum': q[3], 'tannarx': q[4]} for q in qatorlar[:5]]}
        from datetime import timedelta
        from apps.cash.models import Smena
        from apps.orders.models import Promokod
        davr_dan = {'bugun': bugun, 'hafta': bugun - timedelta(days=bugun.weekday()), 'oy': bugun.replace(day=1),
                   'yil': bugun.replace(month=1, day=1)}[davr]
        shu_oy = _davr_bloki(salon, davr_dan, bugun, filial)  # FT-19.2: tanlangan davr
        # kutilayotgan daromad davrga bog'liq emas: bu bugungi holat (avans olingan, qoldiq to'lanmagan)
        shu_oy.update(kutilayotgan_daromad=kutilayotgan['jami'], olingan_avans=kutilayotgan['olingan_avans'],
                      qolgan_summa=kutilayotgan['qolgan_summa'], kelgusi_avanslar=reports.kelgusi_avanslar(salon, filial))
        # Tasdiq kutayotgan xarajat foydaga kirmaydi, lekin kassadan chiqqan bo'lishi mumkin — foyda yonida alohida ko'rsatiladi
        shu_oy['tasdiqlanmagan_xarajat'] = Xarajat.objects.filter(
            salon=salon, holat=Xarajat.Holat.KUTILMOQDA, sana__range=(davr_dan, bugun), **zf).aggregate(s=Sum('summa'))['s'] or 0
        oxirgi_smena = Smena.objects.filter(salon=salon, yopilgan__isnull=False).order_by('-yopilgan').first()
        from apps.cash.nazorat import dashbord_nazorati
        # Kanvas Dashboard (egasining savollari): «Bu oy qancha ishladim» — o'tgan oyning xuddi shu kunlarigacha foyda bilan;
        # «Qarzdorlar» — QarzdorlarView bilan bir xil ta'rif; «Xodimlar» — davrda kim kassaga qancha pul qabul qildi
        oldingi_oy_foyda = None
        if davr == 'oy':
            o_oxiri = davr_dan - timedelta(days=1)
            o_boshi = o_oxiri.replace(day=1)
            oldingi_oy_foyda = _davr_bloki(salon, o_boshi, o_boshi.replace(day=min(bugun.day, o_oxiri.day)), filial)['taxminiy_sof_foyda']
        from django.db.models import Min
        qz = Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.QAYTARILDI, qaytarish_akti__qarz__gt=0, **zf).aggregate(
            soni=Count('id'), jami=Sum('qaytarish_akti__qarz'), eng_eski=Min('qaytarish_akti__sana'))
        xodimlar_kassasi = [{'ism': r['xodim__ism'], 'summa': r['s']} for r in Tolov.objects.filter(
            reports.tolov_filiali(filial), Tolov.HAQIQIY, salon=salon, vaqt__date__range=(davr_dan, bugun),
            tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA]).values('xodim__ism').annotate(s=Sum('summa')).order_by('-s')[:5]]
        # FT-19.5: o'chirilgan funksiya ko'rsatkichi chiqmaydi
        tugayotgan = (Promokod.objects.filter(salon=salon, holat=Promokod.Holat.FAOL, tugash__gte=bugun,
                                              tugash__lte=bugun + timedelta(days=7)).count()
                      if soz.promokodlar_bolimi else 0)
        return Response({
            'davr': {'kalit': davr, 'dan': davr_dan, 'gacha': bugun},
            'filial': filial,
            'oldinda': {**_oldinda(salon, bugun, filial=filial), 'avanslar_portfeli': kutilayotgan['olingan_avans']},
            'bugun': {
                'tushum': by_usul, 'tushum_jami': sum(by_usul.values()),
                # bekor qilingan zakazlarga bugun qaytarilgan avanslar — «tushum_jami» ichida hisoblangan, shundan ayriladi
                'qaytarilgan': Tolov.objects.filter(reports.tolov_filiali(filial), salon=salon, vaqt__date=bugun,
                                                    tur=Tolov.Tur.VOZVRAT).aggregate(s=Sum('summa'))['s'] or 0,
                'smena_ochiq': bool(smena),
                'ochiq_smenalar': Smena.objects.filter(salon=salon, yopilgan__isnull=True).count(),
                'hisobdagi_qoldiq': sum(kassa_hisobot(s)['hisobdagi_qoldiq'] for s in ochiq_smenalar) if ochiq_smenalar else None,
                # A-10: Zakazlar «bugun olib ketadi» chipi va bosh ekran bilan bir xil ta'rif
                'olib_ketiladi': BUGUN_FILTRLARI['bugun_olib'](Zakaz.objects.filter(salon=salon, **zf)).count(),
                'qaytariladi': berilgan.filter(qaytarish=bugun).count(),
                'kechikkan': berilgan.filter(qaytarish__lt=bugun).count(),
            },
            'qoplamagan': qoplamagan,
            'tasdiq_kutmoqda': {
                'chegirmalar': ChegirmaSorovi.objects.filter(
                    salon=salon, holat=ChegirmaSorovi.Holat.KUTILMOQDA).count(),
                'liboslar': Libos.objects.filter(salon=salon, holat=Libos.Holat.TASDIQ_KUTILMOQDA).count(),
                'xarajatlar': Xarajat.objects.filter(salon=salon, holat=Xarajat.Holat.KUTILMOQDA).count(),
                'otkazmalar': Tolov.objects.filter(salon=salon, tasdiq=Tolov.Tasdiq.KUTILMOQDA).count(),
            },
            'shu_oy': shu_oy,
            'oldingi_oy_foyda': oldingi_oy_foyda,
            'qarz': {'soni': qz['soni'], 'jami': qz['jami'] or 0, 'eng_eski_kun': (bugun - qz['eng_eski']).days if qz['eng_eski'] else None},
            'xodimlar_kassasi': xodimlar_kassasi,
            'nazorat': dashbord_nazorati(salon, bugun),  # egasining uch savoli: kamomad, diqqat, liboslar joyidami
            'ogohlantirishlar': {
                'tannarxsiz_liboslar': Libos.objects.filter(salon=salon, tannarx__isnull=True,
                                                            holat__in=reports.FAOL_LIBOS_HOLATLARI).count(),
                'kechikish_jarimasi_yoqilgan': soz.kechikish_jarimasi,
                'tugayotgan_promokodlar': tugayotgan,
                'kassa_farqi': oxirgi_smena.farq if oxirgi_smena and oxirgi_smena.farq else 0,
                'kassa_farqi_sana': oxirgi_smena.sana if oxirgi_smena and oxirgi_smena.farq else None,
                'qarzdorlar': Zakaz.objects.filter(salon=salon, holat=Zakaz.Holat.QAYTARILDI).count(),
                'saqlanayotgan_zaloglar': Zalog.objects.filter(
                    salon=salon, holat__in=[Zalog.Holat.SAQLANMOQDA, Zalog.Holat.USHLAB_QOLINDI]
                ).exclude(turi=Zalog.Turi.PUL).count(),
            },
        })


class HujjatView(APIView):
    """GET /api/zakazlar/<id>/hujjat/?tur=shartnoma|kvitansiya|dalolatnoma — chop etish uchun ma'lumot."""
    permission_classes = [IsStaff]

    def get(self, request, pk):
        zakaz = (Zakaz.objects.filter(salon=request.salon, id=pk)
                 .select_related('salon', 'mijoz', 'sotuvchi').first())
        if not zakaz:
            raise NotFound('Zakaz topilmadi.')
        fn = hujjatlar.TURLAR.get(request.query_params.get('tur', 'shartnoma'))
        if not fn:
            return Response({'detail': "Hujjat turi noto'g'ri."}, status=400)
        try:
            return Response(fn(zakaz))
        except hujjatlar.HujjatXatosi as e:
            return Response({'detail': str(e)}, status=409)


class OflaynToplamView(APIView):
    """GET /api/oflayn-toplam/ — internet uzilganda ko'rsatish uchun qurilmada keshlanadigan ma'lumot (7-bo'lim).

    Faqat bugungi va ertangi bronlar, ularning mijoz telefonlari va salonda saqlanayotgan zaloglar. Narx, tannarx,
    to'lovlar va boshqa mijozlar kirmaydi — keshda imkon qadar kam shaxsiy ma'lumot qoladi.
    """
    permission_classes = [IsStaff]

    def get(self, request):
        from datetime import timedelta
        bugun = timezone.localdate()
        ertaga = bugun + timedelta(days=1)
        faol = [Zakaz.Holat.VAQTINCHALIK, Zakaz.Holat.CHEGIRMA_KUTILMOQDA, Zakaz.Holat.BRON, Zakaz.Holat.BERILDI]
        zakazlar = (_zakazlar(request.salon).filter(holat__in=faol)
                    .filter(Q(olib_ketish__in=[bugun, ertaga]) | Q(qaytarish__in=[bugun, ertaga])
                            | Q(qaytarish__lt=bugun, holat=Zakaz.Holat.BERILDI))
                    .annotate(tolangan_s=TOLANGAN).order_by('olib_ketish', 'raqam'))
        zaloglar = (Zalog.objects.filter(salon=request.salon,
                                         holat__in=[Zalog.Holat.SAQLANMOQDA, Zalog.Holat.USHLAB_QOLINDI])
                    .select_related('zakaz__mijoz').order_by('zakaz__raqam'))
        return Response({
            'olingan': timezone.now(), 'bugun': bugun, 'ertaga': ertaga,
            # C-22: olinadigan qoldiq — qog'oz kvitansiya yozish uchun (jami va to'lovlar ro'yxati keshga tushmaydi)
            'bronlar': [{'raqam': z.raqam, 'holat': z.holat, 'mijoz': z.mijoz.fio, 'telefon': z.mijoz.telefon,
                         'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish, 'qoldiq': max(0, z.jami - z.tolangan_s),
                         'liboslar': [f'{p.libos.artikul} {p.libos.nomi}' for p in z.pozitsiyalar.all()],
                         'aksessuarlar': [a.dona.yorliq for a in z.aksessuarlar.all()]} for z in zakazlar],
            'zaloglar': [{'yorliq': g.yorliq, 'turi': g.get_turi_display(), 'zakaz': g.zakaz.raqam,
                          'mijoz': g.zakaz.mijoz.fio, 'telefon': g.zakaz.mijoz.telefon,
                          'holat': g.get_holat_display()} for g in zaloglar],
        })


class BoglandimView(APIView):
    """FT-14.2: sotuvchi «Bog'landim» bosadi, natija (izoh) zakaz tarixiga yoziladi.

    C-12: «faqat ko'rish» salonida yopiq — bu boshlangan zakazni yakunlash emas (`faqat_korishda_ruxsat` yo'q).
    """
    permission_classes = [IsStaff]

    def post(self, request, pk):
        if (rad := yozish_taqiqi(request, self)):
            return rad
        zakaz = Zakaz.objects.filter(salon=request.salon, id=pk).first()
        if not zakaz:
            raise NotFound('Zakaz topilmadi.')
        tur = str(request.data.get('tur', ''))[:30]
        izoh = str(request.data.get('izoh', '')).strip()[:300]
        ZakazTarixi.objects.create(salon=request.salon, zakaz=zakaz, xodim=request.user, harakat='boglandi',
                                   eski=tur, yangi=izoh or "Mijoz bilan bog'lanildi")
        return Response({'ok': True}, status=201)


class QarzdorlarView(APIView):
    """FT-12.13: ikki alohida ro'yxat — «Qarzdorlar» (qaytarishdan keyin to'lanmagan jarima/zarar) va
    «Qoldiq kutilmoqda» (avans olingan, libos hali berilmagan; bu qarz emas). Faqat rahbar."""
    permission_classes = [IsRahbar]

    def get(self, request):
        # Jadval qatori bosh ekrandagi boshqa tablar bilan bir xil (A-28): rasm, to'langan, qoldiq
        qarzdorlar = [
            {**_jadval_qatori(request, zk), 'qarz': zk.qaytarish_akti.qarz, 'qaytarilgan': zk.qaytarish_akti.sana}
            for zk in _jadval_qs(_zakazlar(request.salon).filter(holat=Zakaz.Holat.QAYTARILDI, qaytarish_akti__qarz__gt=0)
                                 .select_related('qaytarish_akti')).order_by('qaytarish_akti__sana')]
        kutilmoqda = []
        for zk in _jadval_qs(_zakazlar(request.salon).filter(holat=Zakaz.Holat.BRON)).order_by('olib_ketish'):
            qator = _jadval_qatori(request, zk)
            if qator['qoldiq'] > 0:
                kutilmoqda.append({**qator, 'avans': qator['tolangan']})
        return Response({
            'qarzdorlar': qarzdorlar, 'qarz_jami': sum(q['qarz'] for q in qarzdorlar),
            'qoldiq_kutilmoqda': kutilmoqda, 'qoldiq_jami': sum(k['qoldiq'] for k in kutilmoqda),
        })


def _tuzatsa_boladimi(t):
    """`cash.services.tolov_tuzatish` shartlari: avans/qoldiq, smena ochiq, xodim pulini topshirmagan, o'tkazma tasdiqlanmagan."""
    return (t.tur in (Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ) and t.summa > 0 and t.smena is not None and not t.smena.yopilgan
            and t.tasdiq not in (Tolov.Tasdiq.KELDI, Tolov.Tasdiq.KELMADI)
            and not t.smena.ishtirokchilar.filter(xodim_id=t.xodim_id, chiqqan__isnull=False).exists())


class TolovHavolaView(APIView):
    """GET /api/zakazlar/<id>/tolov-havola/?summa= — Click/Payme havolalari (merchant ma'lumotlari kiritilgan bo'lsa)."""
    permission_classes = [IsStaff]

    def get(self, request, pk):
        from .tolov_havola import havolalar
        z = Zakaz.objects.filter(salon=request.salon, id=pk).first()
        if not z:
            raise NotFound('Zakaz topilmadi.')
        qoldiq = z.jami - tolangan_summa(z)
        summa = request.query_params.get('summa', '')
        summa = int(summa) if summa.isdigit() else qoldiq
        if summa <= 0 or summa > qoldiq:
            return Response({'detail': "Summa 0 dan katta va qoldiqdan oshmasligi kerak."}, status=400)
        return Response({'summa': summa, 'havolalar': havolalar(z, summa)})

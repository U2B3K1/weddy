"""Ro'yxat va dashbord endpointlari: zakazlar, sotuvchi bosh ekrani (FT-1.2), rahbar dashbordi (6.5)."""
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cash.models import Tolov
from apps.cash.services import kassa_hisobot, ochiq_smena, tolangan_summa
from apps.catalog.models import Libos
from apps.finance import reports
from apps.finance.models import Xarajat
from apps.tenants.models import Xodim
from apps.tenants.permissions import IsRahbar, IsStaff, salon_yoza_oladimi

from . import hujjatlar
from .changes import muddati_otganlarni_bekor_qil
from .models import ChegirmaSorovi, Zakaz, ZakazTarixi, Zalog


def _qisqa(z):
    return {'id': z.id, 'raqam': z.raqam, 'holat': z.holat, 'mijoz': z.mijoz.fio or z.mijoz.telefon,
            'telefon': z.mijoz.telefon, 'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish,
            'jami': z.jami, 'filial': z.filial_id, 'liboslar': [p.libos.nomi for p in z.pozitsiyalar.all()],
            'aksessuarlar': [f'{a.dona.aksessuar.nomi} ({a.dona.yorliq})' for a in z.aksessuarlar.all()]}


def _zakazlar(salon):
    return (Zakaz.objects.filter(salon=salon).select_related('mijoz')
            .prefetch_related('pozitsiyalar__libos', 'aksessuarlar__dona__aksessuar'))


def eslatmalar(salon, bugun):
    """Sotuvchiga eslatmalar (4.14): mijozga emas, sotuvchiga chiqadi — u mijoz bilan o'zi bog'lanadi.

    Bugun «Bog'landim» bosilgan eslatma `boglangan=True` bo'lib qaytadi (FT-14.2).
    """
    from datetime import timedelta
    from apps.bookings.models import Bron

    ertaga = bugun + timedelta(days=1)
    asos = Zakaz.objects.filter(salon=salon).select_related('mijoz')
    natija = []

    def qosh(tur, zakaz, matn):
        natija.append({'tur': tur, 'zakaz_id': zakaz.id, 'raqam': zakaz.raqam, 'mijoz': zakaz.mijoz.fio,
                       'telefon': zakaz.mijoz.telefon, 'matn': matn})

    for zk in asos.filter(olib_ketish=ertaga, holat__in=[Zakaz.Holat.BRON, Zakaz.Holat.VAQTINCHALIK]):
        qosh('olib_ketish_ertaga', zk, "Ertaga libosni olib ketadi. Mijoz bilan bog'laning, qoldiq to'lovni eslating.")
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


class ZakazlarRoyxatiView(APIView):
    """GET /api/zakazlar/royxat/?holat=&q=  (q: raqam yoki telefon/F.I.O.)"""
    permission_classes = [IsStaff]

    def get(self, request):
        if salon_yoza_oladimi(request.salon):  # «faqat ko'rish» salonida GET hech narsa yozmaydi; cron baribir ishlaydi
            muddati_otganlarni_bekor_qil(request.salon)
        qs = _zakazlar(request.salon)
        holat = request.query_params.get('holat')
        if holat:
            qs = qs.filter(holat=holat)
        filial = request.query_params.get('filial', '')
        if filial.isdigit():
            qs = qs.filter(filial_id=int(filial))
        q = request.query_params.get('q', '').strip()
        if q:
            f = Q(mijoz__telefon__icontains=q) | Q(mijoz__fio__icontains=q)
            if q.isdigit():
                f |= Q(raqam=int(q))
            qs = qs.filter(f)
        return Response([_qisqa(z) for z in qs.order_by('-raqam')[:100]])


class ZakazTafsilotView(APIView):
    """Zakaz kartasi (ekran 8): pozitsiyalar, to'lovlar, zalog, qarz, tarix."""
    permission_classes = [IsStaff]

    def get(self, request, pk):
        z = _zakazlar(request.salon).filter(id=pk).first()
        if not z:
            raise NotFound('Zakaz topilmadi.')
        tolangan = tolangan_summa(z)
        akt = getattr(z, 'qaytarish_akti', None)
        return Response({
            **_qisqa(z), 'asosiy_narx': z.asosiy_narx, 'ustama': z.ustama, 'ustama_foiz': z.ustama_foiz, 'chegirma': z.chegirma,
            'tolangan': tolangan, 'qoldiq': z.jami - tolangan,
            'tolovlar': [{'tur': t.tur, 'summa': t.summa, 'usul': t.usul, 'xodim': t.xodim.ism,
                          'vaqt': t.vaqt} for t in z.tolovlar.select_related('xodim')],
            'zaloglar': [{'id': g.id, 'turi': g.turi, 'holat': g.holat, 'summa': g.summa,
                          'tavsif': g.tavsif, 'yorliq': g.yorliq} for g in z.zaloglar.all()],
            'aksessuar_qatorlari': [{'id': a.id, 'nomi': a.dona.aksessuar.nomi, 'yorliq': a.dona.yorliq,
                                     'narx': a.narx} for a in z.aksessuarlar.all()],
            'libos_qatorlari': [{'id': p.libos_id, 'artikul': p.libos.artikul, 'nomi': p.libos.nomi, 'narx': p.narx}
                                for p in z.pozitsiyalar.all()],
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
        })


class BoshEkranView(APIView):
    """Sotuvchi bosh ekrani: bugun olib ketiladigan va qaytariladigan liboslar, smena holati (FT-1.2)."""
    permission_classes = [IsStaff]

    def get(self, request):
        if salon_yoza_oladimi(request.salon):  # FT-2.5: cron ishlamay qolsa ham bron osilib qolmaydi
            muddati_otganlarni_bekor_qil(request.salon)
        bugun = timezone.localdate()
        faol = Zakaz.objects.filter(salon=request.salon).exclude(
            holat__in=[Zakaz.Holat.BEKOR, Zakaz.Holat.YOPILDI])
        z = lambda qs: [_qisqa(x) for x in qs.select_related('mijoz').prefetch_related('pozitsiyalar__libos')]
        from apps.cash.services import xodim_smenasi
        from apps.cash.views import _filial
        smena = xodim_smenasi(request.salon, request.user) or ochiq_smena(request.salon, _filial(request))
        return Response({
            'eslatmalar': eslatmalar(request.salon, bugun),
            'olib_ketiladi': z(faol.filter(olib_ketish=bugun, holat=Zakaz.Holat.BRON)),
            'qaytariladi': z(faol.filter(qaytarish=bugun, holat=Zakaz.Holat.BERILDI)),
            'kechikkan': z(faol.filter(qaytarish__lt=bugun, holat=Zakaz.Holat.BERILDI)),
            'smena': {'ochiq': bool(smena), 'id': smena.id if smena else None},
        })


def _davr_bloki(salon, dan, gacha, filial=None):
    """Bugun/hafta uchun «davr» ko'rsatkichlari (FT-19.2): to'liq to'langan zakazlar va tasdiqlangan xarajatlar.

    Sof foyda bu yerda hisoblanmaydi — soliq oylik hisoblanadi.
    """
    f = {'filial_id': filial} if filial else {}
    zakazlar = reports.tushum_zakazlari(salon, dan, gacha, f)  # P&L bilan bir xil: avvalgi davr zakazi bekor bo'lsa storno
    daromad = ((zakazlar.aggregate(s=Sum('jami'))['s'] or 0)
               - (reports.storno_zakazlari(salon, dan, gacha, f).aggregate(s=Sum('jami'))['s'] or 0))
    soni = zakazlar.count()
    xarajat = Xarajat.objects.filter(salon=salon, holat=Xarajat.Holat.TASDIQLANDI,
                                     sana__range=(dan, gacha), **f).aggregate(s=Sum('summa'))['s'] or 0
    return {'hozirgi_daromad': daromad, 'xarajatlar': xarajat, 'taxminiy_sof_foyda': None, 'zakazlar_soni': soni,
            'ortacha_chek': daromad // soni if soni else 0}


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
        if davr not in ('bugun', 'hafta', 'oy'):
            davr = 'oy'
        # ?filial= — «Bugun», davr va «Oldinda» bloklari shu filial bo'yicha (tasdiqlar va ogohlantirishlar butun salon bo'yicha qoladi)
        filial = request.query_params.get('filial', '')
        filial = int(filial) if filial.isdigit() else None
        zf = {'filial_id': filial} if filial else {}
        smena = ochiq_smena(salon) if not filial else Smena.objects.filter(salon=salon, yopilgan__isnull=True, filial_id=filial).first()
        bugungi = Tolov.objects.filter(salon=salon, vaqt__date=bugun,
                                       tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.JARIMA],
                                       **({'smena__filial_id': filial} if filial else {}))
        by_usul = {r['usul']: r['s'] for r in bugungi.values('usul').annotate(s=Sum('summa'))}
        pnl = reports.foyda_zarar(salon, bugun.year, bugun.month, filial=filial)
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
        shu_oy = {
            'hozirgi_daromad': pnl['tushum'],
            'xarajatlar': pnl['togridan_togri_xarajat'] + pnl['operatsion_xarajat'],
            'taxminiy_sof_foyda': pnl['sof_foyda'], 'zakazlar_soni': pnl['zakazlar_soni'],
            'ortacha_chek': pnl['tushum'] // pnl['zakazlar_soni'] if pnl['zakazlar_soni'] else 0,
        }
        davr_dan = {'bugun': bugun, 'hafta': bugun - timedelta(days=bugun.weekday()), 'oy': bugun.replace(day=1)}[davr]
        if davr != 'oy':  # FT-19.2: «Shu oy» bloki tanlangan davrga moslashadi
            shu_oy = _davr_bloki(salon, davr_dan, bugun, filial)
        # kutilayotgan daromad davrga bog'liq emas: bu bugungi holat (avans olingan, qoldiq to'lanmagan)
        shu_oy.update(kutilayotgan_daromad=kutilayotgan['jami'], olingan_avans=kutilayotgan['olingan_avans'],
                      qolgan_summa=kutilayotgan['qolgan_summa'])
        oxirgi_smena = Smena.objects.filter(salon=salon, yopilgan__isnull=False).order_by('-yopilgan').first()
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
                'smena_ochiq': bool(smena),
                'ochiq_smenalar': Smena.objects.filter(salon=salon, yopilgan__isnull=True).count(),
                'hisobdagi_qoldiq': kassa_hisobot(smena)['hisobdagi_qoldiq'] if smena else None,
                'olib_ketiladi': Zakaz.objects.filter(salon=salon, olib_ketish=bugun,
                                                      holat=Zakaz.Holat.BRON, **zf).count(),
                'qaytariladi': berilgan.filter(qaytarish=bugun).count(),
                'kechikkan': berilgan.filter(qaytarish__lt=bugun).count(),
            },
            'qoplamagan': qoplamagan,
            'tasdiq_kutmoqda': {
                'chegirmalar': ChegirmaSorovi.objects.filter(
                    salon=salon, holat=ChegirmaSorovi.Holat.KUTILMOQDA).count(),
                'liboslar': Libos.objects.filter(salon=salon, holat=Libos.Holat.TASDIQ_KUTILMOQDA).count(),
                'xarajatlar': Xarajat.objects.filter(salon=salon, holat=Xarajat.Holat.KUTILMOQDA).count(),
            },
            'shu_oy': shu_oy,
            'ogohlantirishlar': {
                'tannarxsiz_liboslar': pnl['tannarxsiz_liboslar'],
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
                    .order_by('olib_ketish', 'raqam'))
        zaloglar = (Zalog.objects.filter(salon=request.salon,
                                         holat__in=[Zalog.Holat.SAQLANMOQDA, Zalog.Holat.USHLAB_QOLINDI])
                    .select_related('zakaz__mijoz').order_by('zakaz__raqam'))
        return Response({
            'olingan': timezone.now(), 'bugun': bugun, 'ertaga': ertaga,
            'bronlar': [{'raqam': z.raqam, 'holat': z.holat, 'mijoz': z.mijoz.fio, 'telefon': z.mijoz.telefon,
                         'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish,
                         'liboslar': [f'{p.libos.artikul} {p.libos.nomi}' for p in z.pozitsiyalar.all()],
                         'aksessuarlar': [a.dona.yorliq for a in z.aksessuarlar.all()]} for z in zakazlar],
            'zaloglar': [{'yorliq': g.yorliq, 'turi': g.get_turi_display(), 'zakaz': g.zakaz.raqam,
                          'mijoz': g.zakaz.mijoz.fio, 'telefon': g.zakaz.mijoz.telefon,
                          'holat': g.get_holat_display()} for g in zaloglar],
        })


class BoglandimView(APIView):
    """FT-14.2: sotuvchi «Bog'landim» bosadi, natija (izoh) zakaz tarixiga yoziladi."""
    permission_classes = [IsStaff]

    def post(self, request, pk):
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
        qarzdorlar = [
            {**_qisqa(zk), 'qarz': zk.qaytarish_akti.qarz, 'qaytarilgan': zk.qaytarish_akti.sana}
            for zk in _zakazlar(request.salon).filter(holat=Zakaz.Holat.QAYTARILDI, qaytarish_akti__qarz__gt=0)
            .select_related('qaytarish_akti').order_by('qaytarish_akti__sana')]
        kutilmoqda = []
        for zk in _zakazlar(request.salon).filter(holat=Zakaz.Holat.BRON).order_by('olib_ketish'):
            tolangan = tolangan_summa(zk)
            if tolangan < zk.jami:
                kutilmoqda.append({**_qisqa(zk), 'avans': tolangan, 'qoldiq': zk.jami - tolangan})
        return Response({
            'qarzdorlar': qarzdorlar, 'qarz_jami': sum(q['qarz'] for q in qarzdorlar),
            'qoldiq_kutilmoqda': kutilmoqda, 'qoldiq_jami': sum(k['qoldiq'] for k in kutilmoqda),
        })


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

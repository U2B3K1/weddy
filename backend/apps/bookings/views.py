from datetime import date

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Libos
from apps.tenants.permissions import SalonYozishRuxsati

from .models import Bron
from .services import BandlikXatosi, bosh_aksessuarlar, bosh_liboslar, bron_qilish, qulflash


def _sana(value, nom):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({nom: 'Sana YYYY-OY-KUN ko\'rinishida bo\'lishi kerak.'})


def _sanalar(request):
    """`dan`/`gacha` juftligi. Teskari tartib Postgres oralig'ida 500 berardi — oldindan 400."""
    dan = _sana(request.query_params.get('dan'), 'dan')
    gacha = _sana(request.query_params.get('gacha'), 'gacha')
    if gacha < dan:
        raise ValidationError({'gacha': "Qaytarish sanasi olib ketishdan oldin bo'lishi mumkin emas."})
    return dan, gacha


def _manekin(request, libos):
    """Manekin qatlami prefetch keshidan (qo'shimcha so'rovsiz)."""
    r = next((x for x in libos.rasmlar.all() if x.id == libos.manekin_rasm_id and x.fonsiz), None)
    if r is None:
        return None
    return {'rasm': request.build_absolute_uri(r.fonsiz.url), 'x': libos.manekin_x, 'y': libos.manekin_y,
            'kattalik': libos.manekin_kattalik}


def _birinchi_rasm(request, libos, katta=False):
    r = next(iter(libos.rasmlar.all()), None)  # prefetch keshidan
    return request.build_absolute_uri((r.katta if katta else r.kichik).url) if r else None


class BoshLiboslarView(APIView):
    """GET /api/bronlar/bosh/?dan=2026-11-10&gacha=2026-11-12[&bandlarni_korsat=1]"""

    def get(self, request):
        dan, gacha = _sanalar(request)
        korsat = request.query_params.get('bandlarni_korsat') == '1'
        q = request.query_params.get('q', '').strip()
        natija = bosh_liboslar(request.salon, dan, gacha, korsat, request.user, q=q)
        # filial filtri: filialga biriktirilmagan libos hamma filialda ko'rinadi
        filial = request.query_params.get('filial', '')
        filialda = (lambda l: l.filial_id in (None, int(filial))) if filial.isdigit() else (lambda l: True)
        natija = [(l, band) for l, band in natija if filialda(l)]
        # Band libos o'rniga taklif: shu kategoriyadagi (iloji bo'lsa shu o'lchamdagi) bo'sh liboslar (FT-2.2).
        # Takliflar ham shu filialdan; qidiruvsiz so'rovda bo'sh liboslar natijaning o'zida bor — qayta hisoblanmaydi.
        if not any(band for _, band in natija):
            boshlar = []
        elif q:
            boshlar = [l for l, band in bosh_liboslar(request.salon, dan, gacha, False, request.user)
                       if not l.qulflangan and filialda(l)]
        else:
            boshlar = [l for l, band in natija if not band and not l.qulflangan]

        def oxshashlar(libos):
            nomzodlar = [b for b in boshlar if b.kategoriya_id == libos.kategoriya_id and b.id != libos.id]
            nomzodlar.sort(key=lambda b: (b.olcham != libos.olcham, abs(b.ijara_narxi - libos.ijara_narxi)))
            return [{'id': b.id, 'artikul': b.artikul, 'nomi': b.nomi} for b in nomzodlar[:3]]

        from apps.tenants.models import sozlama
        manekin_yoq = sozlama(request.salon).manekin  # 4.16: o'chirilgan bo'lsa zakaz ekranida chiqmaydi
        return Response([
            {'id': l.id, 'artikul': l.artikul, 'nomi': l.nomi, 'kategoriya': l.kategoriya.nomi,
             'olcham': l.olcham, 'rang': l.rang, 'ijara_narxi': l.ijara_narxi,
             'zalog': l.zalog, 'band': band, 'qulflangan': l.qulflangan, 'eng_yaqin_bosh': l.eng_yaqin_bosh,
             'oxshashlar': oxshashlar(l) if band else [],
             'kategoriya_id': l.kategoriya_id, 'filial': l.filial_id,
             'rasm': _birinchi_rasm(request, l), 'rasm_katta': _birinchi_rasm(request, l, katta=True),
             'rasmlar': [request.build_absolute_uri(r.katta.url) for r in l.rasmlar.all()],
             'manekin': _manekin(request, l) if manekin_yoq else None}
            for l, band in natija
        ])


class BronYaratishSerializer(serializers.Serializer):
    libos = serializers.IntegerField()
    dan = serializers.DateField()
    gacha = serializers.DateField()

    def validate(self, d):
        if d['gacha'] < d['dan']:
            raise serializers.ValidationError({'gacha': "Qaytarish sanasi olib ketishdan oldin bo'lishi mumkin emas."})
        return d


class BronYaratishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = BronYaratishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            libos = Libos.objects.select_related('kategoriya').get(salon=request.salon, id=d['libos'])
        except Libos.DoesNotExist:
            raise ValidationError({'libos': 'Topilmadi.'})
        try:
            bron = bron_qilish(salon=request.salon, libos=libos, olib_ketish=d['dan'],
                               qaytarish=d['gacha'], xodim=request.user)
        except BandlikXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response({'id': bron.id, 'turi': bron.turi, 'muddati': bron.muddati}, status=201)


class QulflashView(APIView):
    """Libos zakazga qo'shilganda 15 daqiqaga qulflanadi (FT-2.7)."""
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = BronYaratishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            libos = Libos.objects.get(salon=request.salon, id=d['libos'])
        except Libos.DoesNotExist:
            raise ValidationError({'libos': 'Topilmadi.'})
        try:
            q = qulflash(salon=request.salon, libos=libos, olib_ketish=d['dan'],
                         qaytarish=d['gacha'], xodim=request.user)
        except BandlikXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response({'tugaydi': q.tugaydi}, status=201)


class BoshAksessuarlarView(APIView):
    """GET /api/bronlar/bosh-aksessuarlar/?dan=&gacha= — sanalarda kamida bitta bo'sh donasi bor aksessuarlar."""

    def get(self, request):
        dan, gacha = _sanalar(request)
        from apps.catalog.manekin import aksessuar_manekin_json
        from apps.tenants.models import sozlama
        manekin_yoq = sozlama(request.salon).manekin
        return Response([
            {'id': a.id, 'nomi': a.nomi, 'kod': a.kod, 'kategoriya': a.kategoriya.nomi,
             'ijara_narxi': a.ijara_narxi, 'bosh_soni': soni,
             'manekin': aksessuar_manekin_json(a, request) if manekin_yoq else None}
            for a, soni in bosh_aksessuarlar(request.salon, dan, gacha)])


class KalendarView(APIView):
    """GET /api/bronlar/kalendar/?dan=&gacha= — libos bo'yicha bandlik (FT-2.6): kun, hafta, oy ko'rinishi uchun.

    Har bir bron uchun zakaz sanalari va bufer bilan band oraliq qaytadi; muddati o'tgan vaqtinchalik bronlar chiqmaydi.
    """

    def get(self, request):
        dan = _sana(request.query_params.get('dan'), 'dan')
        gacha = _sana(request.query_params.get('gacha'), 'gacha')
        if gacha < dan or (gacha - dan).days > 92:
            raise ValidationError({'gacha': "Oraliq noto'g'ri yoki 3 oydan uzun."})
        from datetime import timedelta
        from psycopg.types.range import Range
        bronlar = (Bron.faol().filter(salon=request.salon, oraliq__overlap=Range(dan, gacha, '[]'))
                   .select_related('zakaz__mijoz'))
        by_libos = {}
        for b in bronlar:
            z = b.zakaz
            by_libos.setdefault(b.libos_id, []).append({
                'dan': z.olib_ketish if z else b.oraliq.lower,
                'gacha': z.qaytarish if z else b.oraliq.upper - timedelta(days=1),
                'band_gacha': b.oraliq.upper - timedelta(days=1),  # bufer kun bilan (oxirgi band kun)
                'turi': b.turi, 'zakaz_id': z.id if z else None, 'zakaz_raqami': z.raqam if z else None,
                'holat': z.holat if z else None,
                'mijoz': (z.mijoz.fio or z.mijoz.telefon) if z else None,
            })
        # FT-2.8: primerka kuni kalendarda ko'rinadi (zakazdagi har bir libos qatorida)
        from apps.orders.models import Primerka, Zakaz
        from django.utils import timezone
        primerkalar = {}
        for p in (Primerka.objects.filter(salon=request.salon, holat=Primerka.Holat.REJALASHTIRILGAN,
                                          vaqt__date__range=(dan, gacha))
                  .exclude(zakaz__holat=Zakaz.Holat.BEKOR).select_related('zakaz__mijoz')
                  .prefetch_related('zakaz__pozitsiyalar')):
            mahalliy = timezone.localtime(p.vaqt)
            for poz in p.zakaz.pozitsiyalar.all():
                primerkalar.setdefault(poz.libos_id, []).append({
                    'sana': mahalliy.date(), 'vaqt': f'{mahalliy:%H:%M}', 'zakaz_id': p.zakaz_id,
                    'zakaz_raqami': p.zakaz.raqam, 'mijoz': p.zakaz.mijoz.fio or p.zakaz.mijoz.telefon})
        liboslar = (Libos.objects.filter(salon=request.salon)
                    .exclude(holat__in=[Libos.Holat.SOTILDI, Libos.Holat.HISOBDAN_CHIQARILDI, Libos.Holat.ARXIV,
                                        Libos.Holat.TASDIQ_KUTILMOQDA])
                    .select_related('kategoriya').order_by('kategoriya__tartib', 'artikul'))
        return Response([
            {'id': l.id, 'artikul': l.artikul, 'nomi': l.nomi, 'kategoriya': l.kategoriya.nomi, 'holat': l.holat,
             'bronlar': sorted(by_libos.get(l.id, []), key=lambda x: x['dan']),
             'primerkalar': primerkalar.get(l.id, [])}
            for l in liboslar])

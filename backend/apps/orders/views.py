from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.services import BandlikXatosi
from apps.cash.services import KassaXatosi
from apps.catalog.models import Libos
from apps.tenants.permissions import SalonYozishRuxsati

from apps.tenants.views_filial import joriy_filial
from .models import Mijoz, Zakaz
from .rental import BerishXatosi, libos_berish, libos_qaytarish, qarzni_tolash, tozalash_tugadi
from .services import zakaz_yaratish


def zakaz_json(z):
    return {
        'id': z.id, 'raqam': z.raqam, 'holat': z.holat, 'mijoz': z.mijoz.telefon,
        'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish,
        'asosiy_narx': z.asosiy_narx, 'ustama': z.ustama, 'ustama_foiz': z.ustama_foiz,
        'chegirma': z.chegirma, 'jami': z.jami,
        'promokod': z.promokod.kod if z.promokod_id else None, 'promokod_chegirma': z.promokod_chegirma,
        'liboslar': [p.libos_id for p in z.pozitsiyalar.all()],
        'aksessuarlar': [a.dona.yorliq for a in z.aksessuarlar.all()],
    }


class MijozQidirishView(APIView):
    """FT-2.9: telefon bo'yicha mijoz, tarixi va qora ro'yxat belgisi. Faqat o'z salon mijozi."""

    def get(self, request):
        telefon = request.query_params.get('telefon', '').strip()
        mijoz = Mijoz.objects.filter(salon=request.salon, telefon=telefon).first()
        if not mijoz:
            raise NotFound('Yangi mijoz.')
        tarix = (mijoz.zakazlar.prefetch_related('pozitsiyalar__libos')
                 .exclude(holat=Zakaz.Holat.BEKOR)[:10])
        return Response({
            'id': mijoz.id, 'fio': mijoz.fio, 'telefon': mijoz.telefon, 'toy_sanasi': mijoz.toy_sanasi,
            'olchamlar': {o: getattr(mijoz, o) for o in ('kokrak', 'bel', 'son', 'boy', 'oyoq_olchami')},
            'kiyim_olchami': mijoz.kiyim_olchami,
            'qora_royxat': mijoz.qora_royxat, 'qora_royxat_sabab': mijoz.qora_royxat_sabab,
            'tarix': [{'raqam': z.raqam, 'olib_ketish': z.olib_ketish,
                       'liboslar': [p.libos.nomi for p in z.pozitsiyalar.all()]} for z in tarix],
        })


class ZakazYaratishSerializer(serializers.Serializer):
    telefon = serializers.CharField(max_length=20)
    fio = serializers.CharField(required=False, allow_blank=True, default='')
    dan = serializers.DateField()
    gacha = serializers.DateField()
    liboslar = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    # takrorlangan id = shuncha dona: [5, 5, 7] — 2 ta fata va 1 ta toj
    aksessuarlar = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    salonchi = serializers.IntegerField(required=False, allow_null=True)
    manba = serializers.ChoiceField(choices=Mijoz.Manba.choices, required=False)


class ZakazlarView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = ZakazYaratishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if d['gacha'] < d['dan']:
            return Response({'detail': "Qaytarish sanasi olib ketishdan oldin bo'lishi mumkin emas."}, status=400)
        salonchi = None
        if d.get('salonchi'):
            from .models import Salonchi
            salonchi = Salonchi.objects.filter(salon=request.salon, id=d['salonchi'], faol=True).first()
            if not salonchi:
                return Response({'salonchi': ['Topilmadi.']}, status=400)
        try:
            zakaz = zakaz_yaratish(salon=request.salon, xodim=request.user, telefon=d['telefon'],
                                   salonchi=salonchi, manba=d.get('manba'), filial=joriy_filial(request),
                                   fio=d['fio'], olib_ketish=d['dan'], qaytarish=d['gacha'],
                                   libos_idlari=d['liboslar'], aksessuar_idlari=d['aksessuarlar'])
        except BandlikXatosi as e:
            return Response({'detail': str(e)}, status=409)
        except IntegrityError:
            return Response({'detail': 'Zakaz raqami to\'qnashdi, qayta urinib ko\'ring.'}, status=409)
        return Response(zakaz_json(zakaz), status=201)


def _zakaz(request, pk):
    zakaz = Zakaz.objects.filter(salon=request.salon, id=pk).first()
    if not zakaz:
        raise NotFound('Zakaz topilmadi.')
    return zakaz


def _bajar(fn, **kw):
    try:
        return fn(**kw), None
    except (BerishXatosi, KassaXatosi) as e:
        return None, Response({'detail': str(e)}, status=409)


class ZalogSerializer(serializers.Serializer):
    turi = serializers.ChoiceField(choices=['pul', 'hujjat', 'tillo'])
    summa = serializers.IntegerField(min_value=0, required=False, default=0)
    tavsif = serializers.CharField(required=False, allow_blank=True, default='')
    hujjat_turi = serializers.CharField(required=False, allow_blank=True, default='')
    hujjat_raqami = serializers.CharField(required=False, allow_blank=True, default='')
    ogirlik_gr = serializers.DecimalField(max_digits=7, decimal_places=2, required=False)


class BerishSerializer(serializers.Serializer):
    zaloglar = ZalogSerializer(many=True)


class BerishView(APIView):
    """Libosni berish: qoldiq to'liq to'langan, zalog olingan bo'lishi shart (ekran 9)."""
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        ser = BerishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        zakaz, err = _bajar(libos_berish, salon=request.salon, xodim=request.user,
                            zakaz=_zakaz(request, pk), zaloglar=ser.validated_data['zaloglar'])
        return err or Response(zakaz_json(zakaz))


class QaytarishSerializer(serializers.Serializer):
    tekshiruv = serializers.ChoiceField(choices=['butun', 'dog', 'yirtiq', 'aksessuar_yoq'], default='butun')
    jarima = serializers.IntegerField(min_value=0, default=0)
    jarima_tolandi = serializers.IntegerField(min_value=0, default=0)
    tortilgan_gr = serializers.DecimalField(max_digits=7, decimal_places=2, required=False)
    baho = serializers.IntegerField(required=False)
    izoh = serializers.CharField(required=False, allow_blank=True, default='', max_length=300)


class QaytarishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        ser = QaytarishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        zakaz, err = _bajar(libos_qaytarish, salon=request.salon, xodim=request.user,
                            zakaz=_zakaz(request, pk), **ser.validated_data)
        if err:
            return err
        akt = zakaz.qaytarish_akti
        return Response({**zakaz_json(zakaz), 'jarima': akt.jarima, 'ushlab_qolingan': akt.ushlab_qolingan,
                         'qarz': akt.qarz, 'kechikish_kunlari': akt.kechikish_kunlari})


class QarzTolashView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        summa = serializers.IntegerField(min_value=1).run_validation(request.data.get('summa'))
        zakaz, err = _bajar(qarzni_tolash, salon=request.salon, xodim=request.user,
                            zakaz=_zakaz(request, pk), summa=summa)
        return err or Response(zakaz_json(zakaz))


class TozalandiView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        libos = Libos.objects.filter(salon=request.salon, id=pk).first()
        if not libos:
            raise NotFound('Libos topilmadi.')
        _, err = _bajar(tozalash_tugadi, salon=request.salon, libos=libos)
        return err or Response({'holat': 'bosh'})

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.services import BandlikXatosi
from apps.cash.services import KassaXatosi
from apps.catalog.models import Aksessuar, Libos
from apps.tenants.permissions import IsStaff, SalonYozishRuxsati

from .changes import (OzgartirishXatosi, libosni_almashtirish, sanani_kochirish, zakazdan_aksessuarni_olish,
                      zakazga_aksessuar_qoshish, zakazni_bekor_qilish)
from .models import Zakaz
from .views import zakaz_json


def _zakaz(request, pk):
    zakaz = Zakaz.objects.filter(salon=request.salon, id=pk).first()
    if not zakaz:
        raise NotFound('Zakaz topilmadi.')
    return zakaz


def _bajar(fn, **kw):
    try:
        return fn(**kw), None
    except (OzgartirishXatosi, BandlikXatosi, KassaXatosi) as e:
        return None, Response({'detail': str(e)}, status=409)


class KochirishSerializer(serializers.Serializer):
    dan = serializers.DateField()
    gacha = serializers.DateField()
    sabab = serializers.CharField(required=False, allow_blank=True, default='')


class SanaKochirishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        ser = KochirishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        zakaz, err = _bajar(sanani_kochirish, salon=request.salon, xodim=request.user,
                            zakaz=_zakaz(request, pk), olib_ketish=d['dan'], qaytarish=d['gacha'],
                            sabab=d['sabab'])
        return err or Response(zakaz_json(zakaz))


class AlmashtirishSerializer(serializers.Serializer):
    eski = serializers.IntegerField()
    yangi = serializers.IntegerField()
    sabab = serializers.CharField(required=False, allow_blank=True, default='')


class LibosAlmashtirishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        ser = AlmashtirishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        eski = Libos.objects.filter(salon=request.salon, id=d['eski']).first()
        yangi = Libos.objects.filter(salon=request.salon, id=d['yangi']).first()
        if not eski or not yangi:
            raise NotFound('Libos topilmadi.')
        zakaz, err = _bajar(libosni_almashtirish, salon=request.salon, xodim=request.user,
                            zakaz=_zakaz(request, pk), eski_libos=eski, yangi_libos=yangi,
                            sabab=d['sabab'])
        return err or Response(zakaz_json(zakaz))


class BekorSerializer(serializers.Serializer):
    sabab = serializers.CharField(allow_blank=False)
    qaytariladigan_foiz = serializers.IntegerField(required=False, min_value=0, max_value=100)


class BekorQilishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        ser = BekorSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        zakaz, err = _bajar(zakazni_bekor_qilish, salon=request.salon, xodim=request.user,
                            zakaz=_zakaz(request, pk), sabab=d['sabab'],
                            qaytariladigan_foiz_override=d.get('qaytariladigan_foiz'))
        if err:
            return err
        return Response({**zakaz_json(zakaz), 'qaytarilgan_avans': zakaz.qaytarilgan_avans,
                         'ushlab_qolingan_avans': zakaz.ushlab_qolingan_avans})


class ZakazTarixiView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, pk):
        zakaz = _zakaz(request, pk)
        return Response([
            {'harakat': t.harakat, 'eski': t.eski, 'yangi': t.yangi, 'sabab': t.sabab,
             'xodim': t.xodim.ism if t.xodim else None, 'vaqt': t.vaqt}
            for t in zakaz.tarix.select_related('xodim')])


class ZakazAksessuarView(APIView):
    """POST /api/zakazlar/<id>/aksessuar/ {aksessuar, soni} — saqlangan zakazga aksessuar qo'shish."""
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        class S(serializers.Serializer):
            aksessuar = serializers.IntegerField()
            soni = serializers.IntegerField(min_value=1, max_value=20, default=1)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        a = (Aksessuar.objects.select_related('kategoriya')
             .filter(salon=request.salon, id=ser.validated_data['aksessuar']).first())
        if not a:
            raise NotFound('Aksessuar topilmadi.')
        zakaz, err = _bajar(zakazga_aksessuar_qoshish, salon=request.salon, xodim=request.user,
                            zakaz=_zakaz(request, pk), aksessuar=a, soni=ser.validated_data['soni'])
        return err or Response(zakaz_json(zakaz))


class ZakazAksessuarOchirishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def delete(self, request, pk, qator_id):
        zakaz, err = _bajar(zakazdan_aksessuarni_olish, salon=request.salon, xodim=request.user,
                            zakaz=_zakaz(request, pk), qator_id=qator_id)
        return err or Response(zakaz_json(zakaz))

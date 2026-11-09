"""Yetkazib beruvchilar API (faqat rahbar — tannarx va qarz rahbarga ko'rinadi)."""
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.permissions import IsRahbar, SalonYozishRuxsati

from .models import AksessuarPartiya, Libos, YetkazibBeruvchi, YetkazibBeruvchiTolov
from .yetkazib import (YetkazibXatosi, holati, partiya_json, saqlash, tolov_qilish, tolovni_ochirish,
                       yetkazib_beruvchi_json)


class _Ruxsat:
    def get_permissions(self):
        return [IsRahbar()] + ([] if self.request.method == 'GET' else [SalonYozishRuxsati()])


def _yb(request, pk):
    yb = YetkazibBeruvchi.objects.filter(salon=request.salon, id=pk).first()
    if not yb:
        raise NotFound('Yetkazib beruvchi topilmadi.')
    return yb


class YbSerializer(serializers.Serializer):
    nomi = serializers.CharField(max_length=120)
    telefon = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    izoh = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')


class YetkazibBeruvchilarView(_Ruxsat, APIView):
    def get(self, request):
        h = holati(request.salon)
        return Response([yetkazib_beruvchi_json(yb, h.get(yb.id))
                         for yb in YetkazibBeruvchi.objects.filter(salon=request.salon)])

    def post(self, request):
        ser = YbSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            yb = saqlash(salon=request.salon, rahbar=request.user, **ser.validated_data)
        except YetkazibXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(yetkazib_beruvchi_json(yb), status=201)


class YetkazibBeruvchiView(_Ruxsat, APIView):
    def get(self, request, pk):
        yb = _yb(request, pk)
        d = yetkazib_beruvchi_json(yb, holati(request.salon, [yb.id]).get(yb.id))
        from apps.bookings.views import _birinchi_rasm  # kanvas: libos eskizi bilan
        d['liboslar'] = [{'id': l.id, 'artikul': l.artikul, 'nomi': l.nomi, 'tannarx': l.tannarx, 'holat': l.holat,
                          'holat_nomi': l.get_holat_display(), 'sana': l.yaratilgan.date(), 'rasm': _birinchi_rasm(request, l)}
                         for l in Libos.objects.filter(salon=request.salon, yetkazib_beruvchi=yb)
                         .prefetch_related('rasmlar').order_by('-yaratilgan')]
        d['aksessuarlar'] = [{**partiya_json(p), 'aksessuar_id': p.aksessuar_id, 'kod': p.aksessuar.kod,
                              'nomi': p.aksessuar.nomi}
                             for p in AksessuarPartiya.objects.filter(salon=request.salon, yetkazib_beruvchi=yb)
                             .select_related('aksessuar').order_by('-sana', '-id')]
        d['tolovlar'] = [{'id': t.id, 'sana': t.sana, 'summa': t.summa, 'izoh': t.izoh,
                          'kiritgan': t.kiritgan.ism if t.kiritgan_id else None}
                         for t in yb.tolovlar.select_related('kiritgan')]
        return Response(d)

    def patch(self, request, pk):
        yb = _yb(request, pk)
        ser = YbSerializer(data={'nomi': yb.nomi, 'telefon': yb.telefon, 'izoh': yb.izoh, **request.data})
        ser.is_valid(raise_exception=True)
        try:
            yb = saqlash(salon=request.salon, rahbar=request.user, yb=yb, **ser.validated_data)
        except YetkazibXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(yetkazib_beruvchi_json(yb, holati(request.salon, [yb.id]).get(yb.id)))


class YbTolovlarView(_Ruxsat, APIView):
    def post(self, request, pk):
        class S(serializers.Serializer):
            summa = serializers.IntegerField(min_value=1)
            sana = serializers.DateField(required=False)
            izoh = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            t = tolov_qilish(salon=request.salon, rahbar=request.user, yb=_yb(request, pk), **ser.validated_data)
        except YetkazibXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response({'id': t.id, 'sana': t.sana, 'summa': t.summa}, status=201)


class YbTolovView(_Ruxsat, APIView):
    def delete(self, request, pk):
        t = YetkazibBeruvchiTolov.objects.filter(salon=request.salon, id=pk).select_related('yetkazib_beruvchi').first()
        if not t:
            raise NotFound("To'lov topilmadi.")
        tolovni_ochirish(salon=request.salon, rahbar=request.user, tolov=t)
        return Response(status=204)

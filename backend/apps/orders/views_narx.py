"""Mavsumiy narx qoidalari (FT-15.2): rahbar boshqaradi, sotuvchi ustamani ekranda ko'radi."""
from datetime import date
from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import jurnalga_yoz, sozlama
from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati

from .models import MavsumiyNarx
from .pricing import mavsumiy_qoida


def qoida_json(q):
    return {'id': q.id, 'nomi': q.nomi, 'boshlanish': q.boshlanish, 'tugash': q.tugash,
            'hafta_kunlari': q.hafta_kunlari, 'foiz': q.foiz, 'faol': q.faol}


class QoidaSerializer(serializers.Serializer):
    nomi = serializers.CharField(max_length=100)
    boshlanish = serializers.DateField(required=False, allow_null=True)
    tugash = serializers.DateField(required=False, allow_null=True)
    hafta_kunlari = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), required=False,
                                          allow_null=True, allow_empty=False)
    foiz = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0.01'), max_value=500)
    faol = serializers.BooleanField(required=False)

    def validate_hafta_kunlari(self, v):
        return sorted(set(v)) if v is not None else None

    def validate(self, d):
        b, t = d.get('boshlanish'), d.get('tugash')
        if (b is None) != (t is None) and not self.partial:
            raise serializers.ValidationError("Boshlanish va tugash sanasini birga kiriting (yoki ikkalasini bo'sh qoldiring).")
        if b and t and t < b:
            raise serializers.ValidationError("Tugash sanasi boshlanishdan oldin bo'lishi mumkin emas.")
        if not self.partial and b is None and d.get('hafta_kunlari') is None:
            raise serializers.ValidationError("Sanalar oralig'i yoki hafta kunlaridan kamida bittasini kiriting.")
        return d


class MavsumiyNarxlarView(APIView):
    permission_classes = [IsRahbar]

    def get(self, request):
        return Response({'yoqilgan': sozlama(request.salon).mavsumiy_narx,
                         'qoidalar': [qoida_json(q) for q in MavsumiyNarx.objects.filter(salon=request.salon)]})

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = QoidaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        q = MavsumiyNarx.objects.create(salon=request.salon, **ser.validated_data)
        jurnalga_yoz(request.salon, request.user, 'mavsumiy_narx_qoshildi', q.nomi, '', f'{q.foiz:g}%')
        return Response(qoida_json(q), status=201)


class MavsumiyNarxView(APIView):
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def _qoida(self, request, pk):
        q = MavsumiyNarx.objects.filter(salon=request.salon, id=pk).first()
        if not q:
            raise NotFound('Qoida topilmadi.')
        return q

    def patch(self, request, pk):
        q = self._qoida(request, pk)
        ser = QoidaSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        eski = f'{q.foiz:g}% {"faol" if q.faol else "o\'chirilgan"}'
        for nom, qiymat in ser.validated_data.items():
            setattr(q, nom, qiymat)
        if q.boshlanish and q.tugash and q.tugash < q.boshlanish:
            raise ValidationError("Tugash sanasi boshlanishdan oldin bo'lishi mumkin emas.")
        q.save()
        jurnalga_yoz(request.salon, request.user, 'mavsumiy_narx_ozgardi', q.nomi, eski,
                     f'{q.foiz:g}% {"faol" if q.faol else "o\'chirilgan"}')
        return Response(qoida_json(q))

    def delete(self, request, pk):
        q = self._qoida(request, pk)
        jurnalga_yoz(request.salon, request.user, 'mavsumiy_narx_ochirildi', q.nomi, f'{q.foiz:g}%', '')
        q.delete()  # saqlangan zakazlar narxi o'zgarmaydi: ustama foizi zakazning o'zida yozilgan
        return Response(status=204)


class UstamaView(APIView):
    """GET /api/narx/ustama/?sana=2026-09-12 — sotuvchi ustamani zakaz saqlashdan oldin ko'radi."""
    permission_classes = [IsStaff]

    def get(self, request):
        try:
            sana = date.fromisoformat(request.query_params.get('sana', ''))
        except ValueError:
            raise ValidationError({'sana': "YYYY-OY-KUN ko'rinishida bo'lishi kerak."})
        q = mavsumiy_qoida(request.salon, sana)
        return Response({'foiz': q.foiz if q else 0, 'nomi': q.nomi if q else None})

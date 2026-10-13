"""Primerka API (FT-2.8)."""
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.permissions import IsStaff, SalonYozishRuxsati

from .models import Primerka, Zakaz
from .primerka import PrimerkaXatosi, primerka_belgilash, primerka_json, primerka_ozgartirish


class PrimerkaSerializer(serializers.Serializer):
    vaqt = serializers.DateTimeField(required=False)
    natija = serializers.CharField(max_length=300, required=False, allow_blank=True)
    moslash_narxi = serializers.IntegerField(min_value=0, max_value=100_000_000, required=False)
    holat = serializers.ChoiceField(choices=Primerka.Holat.choices, required=False)


class ZakazPrimerkaView(APIView):
    """POST /api/zakazlar/<id>/primerka/ {vaqt} — zakazga primerka sanasi va vaqtini qo'shadi."""
    permission_classes = [IsStaff, SalonYozishRuxsati]

    def post(self, request, pk):
        zakaz = Zakaz.objects.filter(salon=request.salon, id=pk).first()
        if not zakaz:
            raise NotFound('Zakaz topilmadi.')
        ser = PrimerkaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if 'vaqt' not in ser.validated_data:
            return Response({'vaqt': ['Sana va vaqtni kiriting.']}, status=400)
        try:
            p = primerka_belgilash(salon=request.salon, xodim=request.user, zakaz=zakaz, vaqt=ser.validated_data['vaqt'])
        except PrimerkaXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(primerka_json(p), status=201)


class PrimerkaView(APIView):
    permission_classes = [IsStaff, SalonYozishRuxsati]

    def patch(self, request, pk):
        p = Primerka.objects.filter(salon=request.salon, id=pk).first()
        if not p:
            raise NotFound('Primerka topilmadi.')
        ser = PrimerkaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            p = primerka_ozgartirish(salon=request.salon, xodim=request.user, primerka=p, **ser.validated_data)
        except PrimerkaXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(primerka_json(p))

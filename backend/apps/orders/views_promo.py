"""Promokodlar API (4.18): rahbar boshqaradi, sotuvchi zakazga qo'llaydi."""
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Aksessuar, Kategoriya
from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati

from . import promo
from .models import Promokod, Salonchi, Zakaz
from .views import zakaz_json


def _xato(e):
    return Response({'detail': str(e)}, status=409)


class PromokodSerializer(serializers.Serializer):
    kod = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    turi = serializers.ChoiceField(choices=Promokod.Turi.choices, default=Promokod.Turi.KOP_MARTALIK)
    chegirma_turi = serializers.ChoiceField(choices=Promokod.ChegirmaTuri.choices, default=Promokod.ChegirmaTuri.FOIZ)
    qiymat = serializers.IntegerField(min_value=0, default=0)
    aksessuar = serializers.IntegerField(required=False, allow_null=True)
    boshlanish = serializers.DateField(required=False, allow_null=True)
    tugash = serializers.DateField(required=False, allow_null=True)
    muddat_oy = serializers.ChoiceField(choices=[1, 3, 6], required=False, allow_null=True)
    limit = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    bir_mijozga = serializers.IntegerField(min_value=1, max_value=100, default=1)
    min_summa = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    maks_chegirma = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    kategoriyalar = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    hafta_kunlari = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), required=False,
                                          allow_null=True)
    salonchi = serializers.IntegerField(required=False, allow_null=True)
    manba = serializers.ChoiceField(choices=Promokod.Manba.choices, default=Promokod.Manba.AKSIYA)
    izoh = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')
    soni = serializers.IntegerField(min_value=1, max_value=500, default=1)
    prefiks = serializers.CharField(max_length=10, required=False, allow_blank=True, default='')


class PromokodlarView(APIView):
    """Ro'yxat statistika bilan (FT-21.11, FT-21.12) va yangi kod(lar) yaratish (FT-21.1)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        return Response(promo.statistika(request.salon))

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = PromokodSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data)
        salon = request.salon
        if d.get('aksessuar'):
            d['aksessuar'] = Aksessuar.objects.filter(salon=salon, id=d['aksessuar']).first()
            if not d['aksessuar']:
                raise NotFound('Aksessuar topilmadi.')
        if d.get('salonchi'):
            d['salonchi'] = Salonchi.objects.filter(salon=salon, id=d['salonchi']).first()
            if not d['salonchi']:
                raise NotFound('Salonchi topilmadi.')
        idlar = d.pop('kategoriyalar')
        d['kategoriyalar'] = list(Kategoriya.objects.filter(salon=salon, id__in=idlar))
        if len(d['kategoriyalar']) != len(set(idlar)):
            raise NotFound('Kategoriya topilmadi.')
        try:
            kodlar = promo.promokod_yaratish(salon=salon, rahbar=request.user, **d)
        except promo.PromokodXatosi as e:
            return _xato(e)
        return Response({'kodlar': [p.kod for p in kodlar]}, status=201)


class PromokodOzgartirishSerializer(serializers.Serializer):
    holat = serializers.ChoiceField(choices=Promokod.Holat.choices, required=False)
    tugash = serializers.DateField(required=False)
    limit = serializers.IntegerField(min_value=1, required=False)


class PromokodView(APIView):
    """To'xtatish, qayta yoqish, arxivlash, muddat/limitni uzaytirish (FT-21.10). O'chirish yo'q."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def patch(self, request, pk):
        p = Promokod.objects.filter(salon=request.salon, id=pk).first()
        if not p:
            raise NotFound('Kod topilmadi.')
        ser = PromokodOzgartirishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            p = promo.promokodni_ozgartirish(salon=request.salon, rahbar=request.user, promokod=p, **ser.validated_data)
        except promo.PromokodXatosi as e:
            return _xato(e)
        return Response({'id': p.id, 'holat': promo.hisoblangan_holat(p), 'tugash': p.tugash, 'limit': p.limit})


class ZakazPromokodView(APIView):
    """Sotuvchi kodni kiritadi — darhol tekshiriladi (FT-21.5); DELETE — kodni olib tashlash."""
    permission_classes = [IsStaff, SalonYozishRuxsati]

    def _zakaz(self, request, pk):
        zakaz = Zakaz.objects.filter(salon=request.salon, id=pk).first()
        if not zakaz:
            raise NotFound('Zakaz topilmadi.')
        return zakaz

    def post(self, request, pk):
        kod = str(request.data.get('kod', ''))
        if not kod.strip():
            return Response({'detail': 'Kodni kiriting.'}, status=400)
        try:
            zakaz, ish = promo.promokod_qollash(salon=request.salon, xodim=request.user,
                                                zakaz=self._zakaz(request, pk), kod=kod)
        except promo.PromokodXatosi as e:
            return _xato(e)
        return Response({'zakaz': zakaz_json(zakaz), 'chegirma': ish.summa,
                         'tasdiq_kutilmoqda': zakaz.holat == Zakaz.Holat.CHEGIRMA_KUTILMOQDA}, status=201)

    def delete(self, request, pk):
        try:
            zakaz = promo.promokodni_olib_tashlash(salon=request.salon, xodim=request.user, zakaz=self._zakaz(request, pk))
        except promo.PromokodXatosi as e:
            return _xato(e)
        return Response({'zakaz': zakaz_json(zakaz)})

"""Salonchilar bazasi (4.6, ekran 15)."""
import re

from django.db.models import Count, Q, Sum
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Xodim
from apps.tenants.permissions import IsStaff, SalonYozishRuxsati

from .models import Salonchi, Zakaz


def instagram_havola(qiymat):
    """`@nomi`, `nomi` yoki to'liq havolani xavfsiz instagram.com havolasiga keltiradi; boshqa saytga havola qabul qilinmaydi."""
    q = (qiymat or '').strip()
    if not q:
        return ''
    m = re.fullmatch(r'(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9._]{1,30})/?(?:\?.*)?', q)
    nomi = m.group(1) if m else q.lstrip('@')
    if not re.fullmatch(r'[A-Za-z0-9._]{1,30}', nomi):
        raise serializers.ValidationError("Instagram: foydalanuvchi nomi yoki instagram.com havolasi bo'lishi kerak.")
    return f'https://www.instagram.com/{nomi}/'


class SalonchiSerializer(serializers.Serializer):
    ism = serializers.CharField(max_length=200)
    telefon = serializers.CharField(max_length=20, required=False, allow_blank=True)
    instagram = serializers.CharField(max_length=200, required=False, allow_blank=True)
    salon_nomi = serializers.CharField(max_length=200, required=False, allow_blank=True)
    manzil = serializers.CharField(max_length=300, required=False, allow_blank=True)
    izoh = serializers.CharField(max_length=300, required=False, allow_blank=True)
    faol = serializers.BooleanField(required=False)

    def validate_instagram(self, v):
        return instagram_havola(v)


def salonchi_json(s, rahbar):
    d = {'id': s.id, 'ism': s.ism, 'telefon': s.telefon, 'instagram': s.instagram, 'salon_nomi': s.salon_nomi,
         'manzil': s.manzil, 'izoh': s.izoh, 'faol': s.faol}
    if rahbar:  # FT-6.4: statistika faqat rahbarga (tushum — Ilova B)
        d['mijozlar_soni'] = getattr(s, 'mijozlar_soni', 0)
        d['tushum'] = getattr(s, 'tushum', None) or 0
    return d


class SalonchilarView(APIView):
    """Ro'yxat va qo'shish. Sotuvchi ham zakaz ichidan tezda qo'sha oladi (FT-6.3)."""
    permission_classes = [IsStaff]

    def get(self, request):
        rahbar = request.user.rol == Xodim.Rol.RAHBAR
        qs = Salonchi.objects.filter(salon=request.salon)
        if request.query_params.get('hammasi') != '1' or not rahbar:
            qs = qs.filter(faol=True)
        if rahbar:
            hisobda = ~Q(zakazlar__holat=Zakaz.Holat.BEKOR)
            qs = qs.annotate(
                mijozlar_soni=Count('zakazlar__mijoz', filter=hisobda, distinct=True),
                # tushum: faqat to'liq to'langan zakazlar (6.1)
                tushum=Sum('zakazlar__jami', filter=hisobda & Q(zakazlar__tolangan_sana__isnull=False)))
        return Response([salonchi_json(s, rahbar) for s in qs])

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = SalonchiSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        d.pop('faol', None)
        s = Salonchi.objects.create(salon=request.salon, **d)
        return Response(salonchi_json(s, False), status=201)


class SalonchiView(APIView):
    permission_classes = [IsStaff, SalonYozishRuxsati]

    def patch(self, request, pk):
        s = Salonchi.objects.filter(salon=request.salon, id=pk).first()
        if not s:
            raise NotFound('Salonchi topilmadi.')
        ser = SalonchiSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        for nom, qiymat in ser.validated_data.items():
            setattr(s, nom, qiymat)
        s.save()
        return Response(salonchi_json(s, False))


class ZakazSalonchiView(APIView):
    """Saqlangan zakazga salonchini belgilash yoki olib tashlash."""
    permission_classes = [IsStaff, SalonYozishRuxsati]

    def post(self, request, pk):
        zakaz = Zakaz.objects.filter(salon=request.salon, id=pk).first()
        if not zakaz:
            raise NotFound('Zakaz topilmadi.')
        sid = request.data.get('salonchi')
        salonchi = None
        if sid:
            salonchi = Salonchi.objects.filter(salon=request.salon, id=sid).first()
            if not salonchi:
                raise NotFound('Salonchi topilmadi.')
        zakaz.salonchi = salonchi
        zakaz.save(update_fields=['salonchi'])
        return Response({'salonchi': salonchi.ism if salonchi else None})

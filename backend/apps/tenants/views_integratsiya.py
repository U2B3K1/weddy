"""Tashqi xizmatlar sozlamalari (admin panel → «Integratsiyalar»). Faqat rahbar.

Hamma maydon ixtiyoriy: hech biri kiritilmagan bo'lsa ham tizim to'liq ishlaydi (Telegram va SMS yuborilmaydi,
to'lov havolasi chiqmaydi, soliq standart foizda hisoblanadi).
Maxfiy qiymatlar (Eskiz paroli) API orqali hech qachon qaytarilmaydi — faqat «kiritilgan/kiritilmagan».

Telegram bu yerda **sozlanmaydi**: butun platformaga bitta Libosa boti xizmat qiladi (FT-4.14), tokenini
platforma egasi o'z panelida kiritadi (`platforma/sozlamalar/`). Bu sahifada faqat holat ko'rsatiladi.
"""
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Integratsiya, integratsiya, jurnalga_yoz
from .permissions import IsRahbar, SalonYozishRuxsati

MAXFIY = ('eskiz_parol',)
OCHIQ = ('eskiz_email', 'eskiz_from', 'sms_shablon_olib_ketish', 'sms_shablon_qaytarish',
         'click_service_id', 'click_merchant_id', 'payme_merchant_id', 'soliq_foizi', 'soliq_izohi',
         'manekin_fon_farqi', 'instagram', 'fiskal_eslatma', 'fiskal_izoh')


def integratsiya_json(i):
    from django.conf import settings

    from apps.notify import sms, telegram
    d = {m: getattr(i, m) for m in OCHIQ}
    d.update({f'{m}_kiritilgan': bool(getattr(i, m)) for m in MAXFIY})
    d['holat'] = {
        # Telegram: bitta platforma boti (salonda sozlanmaydi)
        'telegram': 'platforma' if telegram.sozlangan() else 'yoq',
        'sms': 'salon' if (i.eskiz_email and i.eskiz_parol) else 'platforma' if (settings.ESKIZ_EMAIL and settings.ESKIZ_PASSWORD) else 'yoq',
        'click': bool(i.click_service_id and i.click_merchant_id),
        'payme': bool(i.payme_merchant_id),
        'soliq_foizi': i.soliq_foizi if i.soliq_foizi is not None else settings.SOLIQ_FOIZI,
    }
    d['standart'] = {'sms_shablon_olib_ketish': sms.SHABLONLAR['olib_ketish_ertaga'], 'sms_shablon_qaytarish': sms.SHABLONLAR['qaytarish_ertaga'],
                     'soliq_foizi': settings.SOLIQ_FOIZI, 'manekin_fon_farqi': Integratsiya._meta.get_field('manekin_fon_farqi').default}
    del telegram
    return d


class IntegratsiyaSerializer(serializers.Serializer):
    eskiz_email = serializers.EmailField(required=False, allow_blank=True)
    eskiz_parol = serializers.CharField(max_length=200, required=False, allow_blank=True)
    eskiz_from = serializers.CharField(max_length=20, required=False, allow_blank=True)
    sms_shablon_olib_ketish = serializers.CharField(max_length=300, required=False, allow_blank=True)
    sms_shablon_qaytarish = serializers.CharField(max_length=300, required=False, allow_blank=True)
    click_service_id = serializers.RegexField(r'^\d{0,12}$', required=False, allow_blank=True)
    click_merchant_id = serializers.RegexField(r'^\d{0,12}$', required=False, allow_blank=True)
    payme_merchant_id = serializers.RegexField(r'^[0-9a-fA-F]{0,32}$', required=False, allow_blank=True)
    soliq_foizi = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100, required=False, allow_null=True)
    soliq_izohi = serializers.CharField(max_length=500, required=False, allow_blank=True)
    manekin_fon_farqi = serializers.IntegerField(min_value=8, max_value=120, required=False)
    instagram = serializers.CharField(max_length=200, required=False, allow_blank=True)
    fiskal_eslatma = serializers.BooleanField(required=False)
    fiskal_izoh = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate_instagram(self, v):
        from apps.orders.views_salonchi import instagram_havola
        return instagram_havola(v)

    def validate(self, d):
        from apps.notify import sms
        for maydon, tur in (('sms_shablon_olib_ketish', 'olib_ketish_ertaga'), ('sms_shablon_qaytarish', 'qaytarish_ertaga')):
            if d.get(maydon):
                try:  # shablonda faqat ma'lum o'zgaruvchilar bo'lishi mumkin
                    d[maydon].format(salon='S', sana='01.01', tel='T', qoldiq='0')
                except (KeyError, IndexError, ValueError):
                    raise serializers.ValidationError({maydon: "Shablonda faqat {salon}, {sana}, {tel}, {qoldiq} ishlatiladi."})
        del sms
        return d


class IntegratsiyaView(APIView):
    permission_classes = [IsRahbar]

    def get(self, request):
        return Response(integratsiya_json(integratsiya(request.salon)))

    def patch(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = IntegratsiyaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        i = integratsiya(request.salon)
        for nom, qiymat in ser.validated_data.items():
            eski = getattr(i, nom)
            if eski != qiymat:
                # maxfiy qiymatlar jurnalga yozilmaydi — faqat o'zgargani
                jurnalga_yoz(request.salon, request.user, 'integratsiya_ozgardi', nom,
                             '***' if nom in MAXFIY and eski else ('' if nom in MAXFIY else eski),
                             '***' if nom in MAXFIY and qiymat else ('' if nom in MAXFIY else qiymat))
                setattr(i, nom, qiymat)
        i.save()
        return Response(integratsiya_json(i))

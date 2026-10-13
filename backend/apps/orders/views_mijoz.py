"""Mijozlar (ekran 14; FT-8.2, FT-8.3, FT-8.4; 7.4).

Mijozlarning to'liq ro'yxatini faqat rahbar ko'radi (Ilova B). Sotuvchi faqat qidiradi: telefon yoki ismning kamida
4 ta belgisi bilan, shunda u butun bazani varaqlab chiqa olmaydi. Ro'yxatni fayl qilib yuklab olish yo'q (7.4).
"""
from django.db.models import Count, Q
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Xodim, jurnalga_yoz
from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati

from .models import Mijoz, Zakaz

OLCHAMLAR = ('kokrak', 'bel', 'son', 'boy', 'oyoq_olchami')
QIDIRUV_MIN = 4


def mijoz_json(m, tolik=False):
    d = {'id': m.id, 'fio': m.fio, 'telefon': m.telefon, 'qora_royxat': m.qora_royxat,
         'zakazlar_soni': getattr(m, 'zakazlar_soni', None)}
    if tolik:
        d.update({'qoshimcha_telefon': m.qoshimcha_telefon, 'toy_sanasi': m.toy_sanasi, 'manba': m.manba,
                  'qora_royxat_sabab': m.qora_royxat_sabab, 'izoh': m.izoh, 'kiyim_olchami': m.kiyim_olchami,
                  **{o: getattr(m, o) for o in OLCHAMLAR}})
    return d


class MijozlarView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        rahbar = request.user.rol == Xodim.Rol.RAHBAR
        if not rahbar and len(q) < QIDIRUV_MIN:
            return Response({'detail': f"Qidirish uchun telefon yoki ismning kamida {QIDIRUV_MIN} ta belgisini kiriting."},
                            status=400)
        qs = Mijoz.objects.filter(salon=request.salon).annotate(
            zakazlar_soni=Count('zakazlar', filter=~Q(zakazlar__holat=Zakaz.Holat.BEKOR)))
        if q:
            qs = qs.filter(Q(telefon__icontains=q) | Q(fio__icontains=q) | Q(qoshimcha_telefon__icontains=q))
        if request.query_params.get('qora_royxat') == '1':
            qs = qs.filter(qora_royxat=True)
        return Response([mijoz_json(m) for m in qs.order_by('fio', 'telefon')[:50 if not rahbar else 200]])


class MijozSerializer(serializers.Serializer):
    fio = serializers.CharField(max_length=200, required=False, allow_blank=True)
    qoshimcha_telefon = serializers.CharField(max_length=20, required=False, allow_blank=True)
    toy_sanasi = serializers.DateField(required=False, allow_null=True)
    manba = serializers.ChoiceField(choices=Mijoz.Manba.choices, required=False)
    izoh = serializers.CharField(max_length=300, required=False, allow_blank=True)
    kiyim_olchami = serializers.CharField(max_length=20, required=False, allow_blank=True)
    kokrak = serializers.IntegerField(min_value=40, max_value=200, required=False, allow_null=True)
    bel = serializers.IntegerField(min_value=30, max_value=200, required=False, allow_null=True)
    son = serializers.IntegerField(min_value=40, max_value=220, required=False, allow_null=True)
    boy = serializers.IntegerField(min_value=100, max_value=230, required=False, allow_null=True)
    oyoq_olchami = serializers.IntegerField(min_value=28, max_value=50, required=False, allow_null=True)


class MijozView(APIView):
    """Mijoz kartasi: ma'lumot, o'lchamlar, zakazlar tarixi. Tahrirlashni sotuvchi ham qila oladi (FT-8.1)."""
    permission_classes = [IsStaff]

    def _mijoz(self, request, pk):
        m = Mijoz.objects.filter(salon=request.salon, id=pk).first()
        if not m:
            raise NotFound('Mijoz topilmadi.')
        return m

    def get(self, request, pk):
        m = self._mijoz(request, pk)
        tarix = m.zakazlar.prefetch_related('pozitsiyalar__libos').order_by('-raqam')[:30]
        return Response({**mijoz_json(m, tolik=True), 'tarix': [
            {'id': z.id, 'raqam': z.raqam, 'holat': z.holat, 'olib_ketish': z.olib_ketish, 'jami': z.jami,
             'liboslar': [p.libos.nomi for p in z.pozitsiyalar.all()]} for z in tarix]})

    def patch(self, request, pk):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = MijozSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        m = self._mijoz(request, pk)
        for nom, qiymat in ser.validated_data.items():
            setattr(m, nom, qiymat)
        m.save()
        return Response(mijoz_json(m, tolik=True))


class QoraRoyxatView(APIView):
    """FT-8.3: qora ro'yxatga faqat rahbar qo'shadi yoki chiqaradi; sabab majburiy va jurnalga yoziladi."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request, pk):
        m = Mijoz.objects.filter(salon=request.salon, id=pk).first()
        if not m:
            raise NotFound('Mijoz topilmadi.')
        yoq = serializers.BooleanField().run_validation(request.data.get('qora_royxat'))
        sabab = str(request.data.get('sabab', '')).strip()[:300]
        if yoq and not sabab:
            return Response({'detail': "Qora ro'yxatga qo'shish sababi majburiy."}, status=400)
        jurnalga_yoz(request.salon, request.user, 'qora_royxat', f'mijoz {m.telefon}', m.qora_royxat,
                     f'{yoq}: {sabab}' if yoq else yoq)
        m.qora_royxat, m.qora_royxat_sabab = yoq, (sabab if yoq else '')
        m.save(update_fields=['qora_royxat', 'qora_royxat_sabab'])
        return Response(mijoz_json(m, tolik=True))

from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Xodim
from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati

from .discounts import ChegirmaXatosi, chegirma_qarori, chegirma_sorash, tayyor_chegirma_qollash
from .models import ChegirmaSorovi, TayyorChegirma, Zakaz
from .views import zakaz_json


def _zakaz(request, pk):
    zakaz = Zakaz.objects.filter(salon=request.salon, id=pk).first()
    if not zakaz:
        raise NotFound('Zakaz topilmadi.')
    return zakaz


def _bajar(fn, **kw):
    try:
        return fn(**kw), None
    except ChegirmaXatosi as e:
        return None, Response({'detail': str(e)}, status=409)


def sorov_json(s):
    return {'id': s.id, 'zakaz': s.zakaz_id, 'zakaz_raqami': s.zakaz.raqam,
            'sotuvchi': s.sotuvchi.ism if s.sotuvchi else None, 'foiz': s.foiz, 'summa': s.summa,
            'sabab': s.sabab, 'sabab_nomi': s.get_sabab_display(), 'izoh': s.izoh, 'holat': s.holat,
            'mijoz': s.zakaz.mijoz.fio or s.zakaz.mijoz.telefon, 'zakaz_jami': s.zakaz.jami,
            'tasdiqlangan_summa': s.tasdiqlangan_summa,
            'rahbar': s.rahbar.ism if s.rahbar else None, 'rahbar_izohi': s.rahbar_izohi}


class ChegirmaSerializer(serializers.Serializer):
    tayyor = serializers.IntegerField(required=False)
    foiz = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0, max_value=100)
    summa = serializers.IntegerField(required=False, min_value=0)
    sabab = serializers.ChoiceField(choices=ChegirmaSorovi.Sabab.choices, default='boshqa')
    izoh = serializers.CharField(required=False, allow_blank=True, default='', max_length=300)


class ChegirmaView(APIView):
    """Tayyor chegirma darhol qo'llanadi; boshqasi rahbar tasdig'iga ketadi (FT-11.2, FT-11.7)."""
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        ser = ChegirmaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        zakaz = _zakaz(request, pk)
        if 'tayyor' in d:
            tayyor = TayyorChegirma.objects.filter(salon=request.salon, id=d['tayyor']).first()
            if not tayyor:
                raise NotFound('Tayyor chegirma topilmadi.')
            sorov, err = _bajar(tayyor_chegirma_qollash, salon=request.salon, xodim=request.user,
                                zakaz=zakaz, tayyor=tayyor)
        else:
            sorov, err = _bajar(chegirma_sorash, salon=request.salon, xodim=request.user, zakaz=zakaz,
                                sabab=d['sabab'], foiz=d.get('foiz'), summa=d.get('summa'),
                                izoh=d['izoh'])
        if err:
            return err
        zakaz.refresh_from_db()
        return Response({'sorov': sorov_json(sorov), 'zakaz': zakaz_json(zakaz)}, status=201)


class ChegirmaSorovlariView(APIView):
    """Rahbar uchun: tasdiq kutayotgan so'rovlar (dashbordning «Tasdiq kutmoqda» bloki)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        holat = request.query_params.get('holat', 'kutilmoqda')
        qs = (ChegirmaSorovi.objects.filter(salon=request.salon, holat=holat)
              .select_related('zakaz__mijoz', 'sotuvchi', 'rahbar').order_by('-yaratilgan'))
        return Response([sorov_json(s) for s in qs])


class QarorSerializer(serializers.Serializer):
    qaror = serializers.ChoiceField(choices=['tasdiq', 'rad'])
    # manfiy chegirma bazadagi musbat maydonda 500 berardi; 100% dan ortig'i jimgina kesilardi
    foiz = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=0, max_value=100)
    summa = serializers.IntegerField(required=False, min_value=0)
    izoh = serializers.CharField(required=False, allow_blank=True, default='', max_length=300)


class ChegirmaQarorView(APIView):
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request, pk):
        ser = QarorSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        sorov = ChegirmaSorovi.objects.filter(salon=request.salon, id=pk).first()
        if not sorov:
            raise NotFound("So'rov topilmadi.")
        sorov, err = _bajar(chegirma_qarori, salon=request.salon, rahbar=request.user, sorov=sorov,
                            tasdiqlash=d['qaror'] == 'tasdiq', foiz=d.get('foiz'),
                            summa=d.get('summa'), izoh=d['izoh'])
        return err or Response(sorov_json(sorov))


class TayyorChegirmaSerializer(serializers.Serializer):
    nomi = serializers.CharField(max_length=100)
    foiz = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=Decimal('0.01'), max_value=100)
    summa = serializers.IntegerField(min_value=1, required=False)

    def validate(self, d):
        if ('foiz' in d) == ('summa' in d):
            raise serializers.ValidationError('Foiz yoki summadan faqat bittasini kiriting.')
        return d


def tayyor_json(t):
    return {'id': t.id, 'nomi': t.nomi, 'foiz': t.foiz, 'summa': t.summa, 'faol': t.faol}


class TayyorChegirmalarView(APIView):
    def get_permissions(self):
        return [(IsRahbar if self.request.method == 'POST' else IsStaff)()]

    def get(self, request):
        qs = TayyorChegirma.objects.filter(salon=request.salon)
        if request.query_params.get('hammasi') != '1' or request.user.rol != Xodim.Rol.RAHBAR:
            qs = qs.filter(faol=True)
        return Response([tayyor_json(t) for t in qs.order_by('-faol', 'nomi')])

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = TayyorChegirmaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        t = TayyorChegirma.objects.create(salon=request.salon, **ser.validated_data)
        return Response(tayyor_json(t), status=201)


class TayyorChegirmaView(APIView):
    """Tayyor chegirmani o'zgartirish yoki nofaol qilish. O'chirilmaydi — qo'llangan zakazlar tarixi saqlanadi."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def patch(self, request, pk):
        class S(serializers.Serializer):
            nomi = serializers.CharField(max_length=100, required=False)
            foiz = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal('0.01'), max_value=100,
                                            required=False, allow_null=True)
            summa = serializers.IntegerField(min_value=1, required=False, allow_null=True)
            faol = serializers.BooleanField(required=False)

        t = TayyorChegirma.objects.filter(salon=request.salon, id=pk).first()
        if not t:
            raise NotFound('Tayyor chegirma topilmadi.')
        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        for nom, qiymat in ser.validated_data.items():
            setattr(t, nom, qiymat)
        if (t.foiz is None) == (t.summa is None):
            return Response({'detail': 'Foiz yoki summadan faqat bittasini kiriting.'}, status=409)
        t.save()
        return Response(tayyor_json(t))

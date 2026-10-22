from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati

from .dona_tamir import dona_tamir_json, dona_tamirini_tugatish, donani_tamirga_berish
from .manekin import (aksessuar_joylashuvi, aksessuar_manekin_json, aksessuar_qatlami,
                      aksessuar_qatlamini_ochirish)
from .models import Aksessuar, AksessuarDona, DonaTamiri, Kategoriya
from .services import (KatalogXatosi, aksessuar_qoshish, aksessuarni_ozgartirish,
                       aksessuarni_tasdiqlash, donalar_qoshish)
from .views import _bajar, _rahbar


def aksessuar_json(request, a, rahbar, donalar=False):
    """Tannarx faqat rahbarga ko'rinadi (FT-3.5)."""
    d = a.donalar.all()
    j = {'id': a.id, 'nomi': a.nomi, 'kod': a.kod, 'kategoriya': a.kategoriya.nomi,
         'kategoriya_id': a.kategoriya_id, 'ijara_narxi': a.ijara_narxi, 'holat': a.holat,
         'donalar_soni': len(d), 'yaroqli_donalar': sum(1 for x in d if x.holat == AksessuarDona.Holat.BOSH),
         'qoshgan': a.qoshgan.ism if a.qoshgan else None,
         'manekin': aksessuar_manekin_json(a, request)}
    if donalar:
        ochiq = {t.dona_id: t for t in DonaTamiri.objects.filter(dona__in=d, tugagan__isnull=True)}
        j['donalar'] = [{'id': x.id, 'yorliq': x.yorliq, 'holat': x.holat, 'filial': x.filial_id,
                         'tamir': dona_tamir_json(ochiq[x.id]) if x.id in ochiq else None} for x in d]
    if rahbar:
        j['tannarx'] = a.tannarx
    return j


def _aksessuar(request, pk):
    a = (Aksessuar.objects.select_related('kategoriya', 'qoshgan').prefetch_related('donalar')
         .filter(salon=request.salon, id=pk).first())
    if not a:
        raise NotFound('Aksessuar topilmadi.')
    return a


class AksessuarYaratSerializer(serializers.Serializer):
    nomi = serializers.CharField(max_length=200)
    kod = serializers.RegexField(r'^[A-Za-z0-9]{1,10}$', error_messages={'invalid': "Kod 1–10 ta harf yoki raqam."})
    kategoriya = serializers.IntegerField()
    ijara_narxi = serializers.IntegerField(min_value=0, default=0)
    tannarx = serializers.IntegerField(min_value=0, required=False)
    soni = serializers.IntegerField(min_value=1, max_value=200, default=1)


class AksessuarlarView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        qs = (Aksessuar.objects.filter(salon=request.salon).select_related('kategoriya', 'qoshgan')
              .prefetch_related('donalar'))
        if not _rahbar(request) or request.query_params.get('faol') == '1':
            qs = qs.exclude(holat=Aksessuar.Holat.ARXIV)
        rahbar = _rahbar(request)
        return Response([aksessuar_json(request, a, rahbar) for a in qs])

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = AksessuarYaratSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        kat = Kategoriya.objects.filter(salon=request.salon, id=d.pop('kategoriya')).first()
        if not kat:
            return Response({'kategoriya': ['Topilmadi.']}, status=400)
        a, err = _bajar(aksessuar_qoshish, salon=request.salon, xodim=request.user, kategoriya=kat, **d)
        return err or Response(aksessuar_json(request, _aksessuar(request, a.id), _rahbar(request)), status=201)


class AksessuarTafsilotView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, pk):
        return Response(aksessuar_json(request, _aksessuar(request, pk), _rahbar(request), donalar=True))

    def patch(self, request, pk):
        if not _rahbar(request):
            return Response({'detail': "Narx va tannarxni faqat rahbar o'zgartiradi."}, status=403)

        class S(serializers.Serializer):
            ijara_narxi = serializers.IntegerField(min_value=0, required=False)
            tannarx = serializers.IntegerField(min_value=0, required=False)
            holat = serializers.ChoiceField(choices=['faol', 'arxiv'], required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        a, err = _bajar(aksessuarni_ozgartirish, salon=request.salon, rahbar=request.user,
                        aksessuar=_aksessuar(request, pk), **ser.validated_data)
        return err or Response(aksessuar_json(request, _aksessuar(request, a.id), True, donalar=True))


class AksessuarTasdiqView(APIView):
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request, pk):
        class S(serializers.Serializer):
            ijara_narxi = serializers.IntegerField(min_value=0)
            tannarx = serializers.IntegerField(min_value=0)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        a, err = _bajar(aksessuarni_tasdiqlash, salon=request.salon, rahbar=request.user,
                        aksessuar=_aksessuar(request, pk), **ser.validated_data)
        return err or Response(aksessuar_json(request, _aksessuar(request, a.id), True))


class AksessuarManekinView(APIView):
    """Aksessuarning manekin qatlami (FT-5.2): POST — rasm yuklash (multipart «rasm»), PATCH — joylashuv, DELETE — olib tashlash."""
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsStaff, SalonYozishRuxsati]

    def post(self, request, pk):
        fayl = request.FILES.get('rasm')
        if not fayl:
            raise ValidationError({'rasm': ['Rasm faylini yuboring.']})
        a, err = _bajar(aksessuar_qatlami, salon=request.salon, aksessuar=_aksessuar(request, pk), fayl=fayl)
        return err or Response({'manekin': aksessuar_manekin_json(a, request)}, status=201)

    def patch(self, request, pk):
        class S(serializers.Serializer):
            x = serializers.FloatField()
            y = serializers.FloatField()
            kattalik = serializers.FloatField()

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        a, err = _bajar(aksessuar_joylashuvi, salon=request.salon, aksessuar=_aksessuar(request, pk), **ser.validated_data)
        return err or Response({'manekin': aksessuar_manekin_json(a, request)})

    def delete(self, request, pk):
        aksessuar_qatlamini_ochirish(salon=request.salon, aksessuar=_aksessuar(request, pk))
        return Response(status=204)


class DonalarView(APIView):
    """Rahbar yangi donalar qo'shadi (yorliqlar ketma-ket beriladi)."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request, pk):
        soni = serializers.IntegerField(min_value=1, max_value=200).run_validation(request.data.get('soni'))
        _, err = _bajar(donalar_qoshish, salon=request.salon, aksessuar=_aksessuar(request, pk), soni=soni)
        return err or Response(aksessuar_json(request, _aksessuar(request, pk), True, donalar=True), status=201)


class DonaView(APIView):
    """Donani ta'mirga yoki «yo'qolgan»ga o'tkazish; band bronlari bor donani yo'qolgan qilib bo'lmaydi."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def patch(self, request, pk):
        dona = AksessuarDona.objects.filter(salon=request.salon, id=pk).first()
        if not dona:
            raise NotFound('Dona topilmadi.')
        # Avval hamma narsa tekshiriladi, keyin saqlanadi: holat rad etilsa filial ham o'zgarmay qolsin
        filial = dona.filial
        if 'filial' in request.data:  # donani filialga ko'chirish (null — biriktirilmagan)
            from apps.tenants.views_filial import sorovdagi_filial
            filial = sorovdagi_filial(request)
        holat = dona.holat
        if 'holat' in request.data:
            holat = serializers.ChoiceField(choices=AksessuarDona.Holat.values).run_validation(request.data.get('holat'))
        if holat != dona.holat:
            # Ta'mir faqat ta'mir jurnali orqali: aks holda ochiq yozuv qolib ketadi yoki xarajat yozilmaydi
            if dona.holat == AksessuarDona.Holat.TAMIRDA:
                return Response({'detail': "Dona ta'mirda: avval ta'mirni tugating."}, status=409)
            if holat == AksessuarDona.Holat.TAMIRDA:
                return Response({'detail': "Ta'mirga «Ta'mirga berish» orqali yuboring."}, status=409)
            from apps.bookings.models import AksessuarBron
            if holat != AksessuarDona.Holat.BOSH and AksessuarBron.kelgusi().filter(dona=dona).exists():
                return Response({'detail': 'Bu donada kelgusi bronlar bor; avval bronlarni boshqa donaga o\'tkazing.'},
                                status=409)
            from apps.tenants.models import jurnalga_yoz
            jurnalga_yoz(request.salon, request.user, 'dona_holati', f'dona {dona.yorliq}', dona.holat, holat)
        dona.holat, dona.filial = holat, filial
        dona.save(update_fields=['holat', 'filial'])
        return Response({'id': dona.id, 'yorliq': dona.yorliq, 'holat': dona.holat, 'filial': dona.filial_id})


class DonaTamirView(APIView):
    """Dona ta'mir jurnali: GET — ro'yxat, POST — ta'mirga berish."""
    permission_classes = [IsStaff]

    def _dona(self, request, pk):
        dona = AksessuarDona.objects.filter(salon=request.salon, id=pk).first()
        if not dona:
            raise NotFound('Dona topilmadi.')
        return dona

    def get(self, request, pk):
        return Response([dona_tamir_json(t) for t in self._dona(request, pk).tamirlar.select_related('xarajat')])

    def post(self, request, pk):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)

        class S(serializers.Serializer):
            ish_turi = serializers.CharField(max_length=300)
            kim = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        t, err = _bajar(donani_tamirga_berish, salon=request.salon, xodim=request.user, dona=self._dona(request, pk),
                        **ser.validated_data)
        return err or Response(dona_tamir_json(t), status=201)


class DonaTamirTugatishView(APIView):
    permission_classes = [IsStaff, SalonYozishRuxsati]

    def post(self, request, pk):
        yozuv = DonaTamiri.objects.filter(salon=request.salon, id=pk).first()
        if not yozuv:
            raise NotFound("Ta'mir yozuvi topilmadi.")

        class S(serializers.Serializer):
            narx = serializers.IntegerField(min_value=0, default=0)
            kassadan = serializers.BooleanField(required=False)
            usul = serializers.ChoiceField(choices=['naqd', 'karta', 'click', 'payme'], default='naqd')

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        t, err = _bajar(dona_tamirini_tugatish, salon=request.salon, xodim=request.user, yozuv=yozuv, **ser.validated_data)
        return err or Response(dona_tamir_json(t))

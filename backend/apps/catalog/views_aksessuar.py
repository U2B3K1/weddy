from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati, yozish_taqiqi

from .dona_tamir import dona_tamir_json, dona_tamirini_tugatish, donani_tamirga_berish
from .manekin import (aksessuar_joylashuvi, aksessuar_manekin_json, aksessuar_qatlami,
                      aksessuar_qatlamini_ochirish)
from .models import Aksessuar, AksessuarDona, AksessuarPartiya, DonaTamiri, Kategoriya, YetkazibBeruvchi
from .rasm import aksessuar_rasmi, aksessuar_rasmini_ochirish
from .services import (KatalogXatosi, aksessuar_qoshish, aksessuarni_ozgartirish,
                       aksessuarni_tasdiqlash, donalar_qoshish)
from .views import _bajar, _rahbar
from .yetkazib import YetkazibXatosi, aksessuar_xaridi_yoz, partiya_json, partiyani_ozgartirish


def aksessuar_rasm_json(a, request):
    """Kartochka rasmi: kichik — ro'yxat va yangi zakaz, katta — mijozga ko'rsatish."""
    def url(f):
        return request.build_absolute_uri(f.url) if f else None
    return {'rasm': url(a.rasm_kichik), 'rasm_katta': url(a.rasm)}


def dona_bandligi(donalar):
    """Har dona hozir kimda: {dona_id: {'turi': 'mijozda'|'bron', 'zakaz': raqam, 'mijoz': fio, 'sana': boshlanish}}.
    Mijozga berilgan zakaz (BERILDI) ustun; aks holda eng yaqin kelgusi bron. Yakunlangan zakazlar hisobga olinmaydi."""
    from apps.bookings.models import AksessuarBron
    natija = {}
    for b in (AksessuarBron.kelgusi().filter(dona__in=donalar).select_related('zakaz__mijoz').order_by('oraliq')):
        mijozda = b.zakaz_id and b.zakaz.holat == 'berildi'
        if b.dona_id in natija and not (mijozda and natija[b.dona_id]['turi'] != 'mijozda'):
            continue
        natija[b.dona_id] = {'turi': 'mijozda' if mijozda else 'bron', 'zakaz': b.zakaz.raqam if b.zakaz_id else None,
                             'mijoz': (b.zakaz.mijoz.fio or b.zakaz.mijoz.telefon) if b.zakaz_id else '', 'sana': b.oraliq.lower}
    return natija


def dona_holati(x, band):
    """Ro'yxatdagi rangli katak uchun: ta'mir/yo'qolgan/arxiv — dona holati; bo'sh dona band bo'lsa — bron yoki mijozda."""
    if x.holat != AksessuarDona.Holat.BOSH:
        return x.holat
    return band[x.id]['turi'] if x.id in band else 'bosh'


def aksessuar_json(request, a, rahbar, donalar=False, band=None):
    """Tannarx faqat rahbarga ko'rinadi (FT-3.5). `band` — dona_bandligi() natijasi (ro'yxatda hamma aksessuar uchun bitta so'rov)."""
    d = a.donalar.all()
    if band is None:
        band = dona_bandligi(list(d))
    j = {'id': a.id, 'nomi': a.nomi, 'kod': a.kod, 'kategoriya': a.kategoriya.nomi,
         'kategoriya_id': a.kategoriya_id, 'ijara_narxi': a.ijara_narxi, 'holat': a.holat,
         'donalar_soni': len(d), 'yaroqli_donalar': sum(1 for x in d if x.holat == AksessuarDona.Holat.BOSH),
         # kanvas: har dona rangli katak — bo'sh, bron, mijozda, ta'mirda, yo'qolgan (arxiv ko'rsatilmaydi)
         'dona_holatlari': [dona_holati(x, band) for x in d if x.holat != AksessuarDona.Holat.ARXIV],
         'qoshgan': a.qoshgan.ism if a.qoshgan else None,
         **aksessuar_rasm_json(a, request),
         'manekin': aksessuar_manekin_json(a, request)}
    if donalar:
        ochiq = {t.dona_id: t for t in DonaTamiri.objects.filter(dona__in=d, tugagan__isnull=True)}
        j['donalar'] = [{'id': x.id, 'yorliq': x.yorliq, 'holat': x.holat, 'filial': x.filial_id,
                         'band': band.get(x.id),
                         'tamir': dona_tamir_json(ochiq[x.id]) if x.id in ochiq else None} for x in d]
    if donalar:  # kanvas tafsiloti: shu yil necha marta ijaraga berilgan (bekor va tasdiqsiz zakazlarsiz)
        from django.utils import timezone

        from apps.orders.models import Zakaz, ZakazAksessuar
        H = Zakaz.Holat
        j['bu_yil_berildi'] = ZakazAksessuar.objects.filter(
            dona__aksessuar=a, zakaz__holat__in=[H.BRON, H.BERILDI, H.QAYTARILDI, H.YOPILDI],
            zakaz__olib_ketish__year=timezone.localdate().year).count()
    if rahbar:
        j['tannarx'] = a.tannarx
        if donalar:  # qaysi donalar kimdan va necha pulga olingani
            j['partiyalar'] = [partiya_json(p) for p in a.partiyalar.all()]
    return j


def _xarid_maydonlari(request, yb_id, tolandi, jami):
    """Yetkazib beruvchi va hozir to'langan summani tekshiradi: (yb, xato javobi). Sotuvchi ularni kiritmaydi."""
    if not yb_id or not _rahbar(request):
        return None, None
    yb = YetkazibBeruvchi.objects.filter(salon=request.salon, id=yb_id).first()
    if not yb:
        return None, Response({'yetkazib_beruvchi': ['Topilmadi.']}, status=400)
    if tolandi is not None and tolandi > jami:
        return None, Response({'tolandi': ["Bir dona narxi × donalar sonidan ko'p bo'lishi mumkin emas."]}, status=400)
    return yb, None


def _aksessuar(request, pk):
    a = (Aksessuar.objects.select_related('kategoriya', 'qoshgan').prefetch_related('donalar', 'partiyalar')
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
    # faqat rahbar: qayerdan olingan va hozir qancha to'langan (berilmasa — tannarx × soni to'liq; qolgani qarz)
    yetkazib_beruvchi = serializers.IntegerField(required=False, allow_null=True)
    tolandi = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class AksessuarlarView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        qs = (Aksessuar.objects.filter(salon=request.salon).select_related('kategoriya', 'qoshgan')
              .prefetch_related('donalar'))
        if not _rahbar(request) or request.query_params.get('faol') == '1':
            qs = qs.exclude(holat=Aksessuar.Holat.ARXIV)
        rahbar = _rahbar(request)
        qs = list(qs)
        band = dona_bandligi([x for a in qs for x in a.donalar.all()])
        return Response([aksessuar_json(request, a, rahbar, band=band) for a in qs])

    def post(self, request):
        if (rad := yozish_taqiqi(request, self)):  # o'zbekcha sabab bilan (C-12)
            return rad
        ser = AksessuarYaratSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        kat = Kategoriya.objects.filter(salon=request.salon, id=d.pop('kategoriya')).first()
        if not kat:
            return Response({'kategoriya': ['Topilmadi.']}, status=400)
        tolandi = d.pop('tolandi', None)
        yb, err = _xarid_maydonlari(request, d.pop('yetkazib_beruvchi', None), tolandi, (d.get('tannarx') or 0) * d['soni'])
        if err:
            return err
        with transaction.atomic():
            a, err = _bajar(aksessuar_qoshish, salon=request.salon, xodim=request.user, kategoriya=kat, **d)
            if yb and a is not None:
                aksessuar_xaridi_yoz(salon=request.salon, rahbar=request.user, partiya=a.partiyalar.get(), yb=yb,
                                     tolandi=tolandi)
        return err or Response(aksessuar_json(request, _aksessuar(request, a.id), _rahbar(request), donalar=True),
                               status=201)


class AksessuarTafsilotView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, pk):
        return Response(aksessuar_json(request, _aksessuar(request, pk), _rahbar(request), donalar=True))

    def patch(self, request, pk):
        if (rad := yozish_taqiqi(request, self)):  # «faqat ko'rish»da katalog yopiq (QA-15)
            return rad
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


class AksessuarRasmView(APIView):
    """Kartochka rasmi: POST — yuklash yoki almashtirish (multipart «rasm», har bir xodim, libos rasmi kabi),
    DELETE — olib tashlash (faqat rahbar)."""
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsStaff, SalonYozishRuxsati]

    def post(self, request, pk):
        fayl = request.FILES.get('rasm')
        if not fayl:
            raise ValidationError({'rasm': ['Rasm faylini yuboring.']})
        a, err = _bajar(aksessuar_rasmi, salon=request.salon, aksessuar=_aksessuar(request, pk), fayl=fayl)
        return err or Response(aksessuar_rasm_json(a, request), status=201)

    def delete(self, request, pk):
        if not _rahbar(request):
            return Response({'detail': "Rasmni faqat rahbar olib tashlaydi."}, status=403)
        aksessuar_rasmini_ochirish(salon=request.salon, aksessuar=_aksessuar(request, pk))
        return Response(status=204)


class DonalarView(APIView):
    """Rahbar yangi donalar qo'shadi (yorliqlar ketma-ket beriladi)."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request, pk):
        class S(serializers.Serializer):
            soni = serializers.IntegerField(min_value=1, max_value=200)
            narx = serializers.IntegerField(min_value=0, required=False, allow_null=True)  # bir dona; bo'sh — tannarx
            yetkazib_beruvchi = serializers.IntegerField(required=False, allow_null=True)
            tolandi = serializers.IntegerField(min_value=0, required=False, allow_null=True)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d, a = ser.validated_data, _aksessuar(request, pk)
        narx = a.tannarx if d.get('narx') is None else d['narx']
        yb, err = _xarid_maydonlari(request, d.get('yetkazib_beruvchi'), d.get('tolandi'), (narx or 0) * d['soni'])
        if err:
            return err
        with transaction.atomic():
            p, err = _bajar(donalar_qoshish, salon=request.salon, aksessuar=a, soni=d['soni'], narx=narx, xodim=request.user)
            if yb and p is not None:
                aksessuar_xaridi_yoz(salon=request.salon, rahbar=request.user, partiya=p, yb=yb, tolandi=d.get('tolandi'))
        return err or Response(aksessuar_json(request, _aksessuar(request, pk), True, donalar=True), status=201)


class PartiyaView(APIView):
    """Rahbar partiyaga yetkazib beruvchini keyin biriktiradi yoki bir dona narxini tuzatadi."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def patch(self, request, pk):
        p = AksessuarPartiya.objects.filter(salon=request.salon, id=pk).select_related('aksessuar').first()
        if not p:
            raise NotFound('Partiya topilmadi.')

        class S(serializers.Serializer):
            yetkazib_beruvchi = serializers.IntegerField(required=False, allow_null=True)
            narx = serializers.IntegerField(min_value=0, required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = dict(ser.validated_data)
        if d.get('yetkazib_beruvchi') is not None:
            d['yetkazib_beruvchi'] = YetkazibBeruvchi.objects.filter(salon=request.salon, id=d['yetkazib_beruvchi']).first()
            if not d['yetkazib_beruvchi']:
                return Response({'yetkazib_beruvchi': ['Topilmadi.']}, status=400)
        try:
            p = partiyani_ozgartirish(salon=request.salon, rahbar=request.user, partiya=p, **d)
        except YetkazibXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(partiya_json(p))


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
        if (rad := yozish_taqiqi(request, self)):  # o'zbekcha sabab bilan (C-12)
            return rad

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

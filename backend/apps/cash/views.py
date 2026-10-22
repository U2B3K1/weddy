from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Zakaz
from apps.tenants.permissions import IsStaff, SalonYozishRuxsati

from . import services, tekshiruv
from .models import Tolov
from .services import KassaXatosi


def xato(e):
    return Response({'detail': str(e)}, status=409)


def _filial(request):
    """Shu qurilma kassasi: filial kassasi yoqilgan bo'lsa qurilma filiali, aks holda umumiy kassa (None)."""
    from apps.tenants.models import sozlama
    from apps.tenants.views_filial import joriy_filial
    return joriy_filial(request) if sozlama(request.salon).filial_kassasi else None


class SmenaHolatiView(APIView):
    """Joriy smena, hisobot va kimlar ishlayotgani."""
    permission_classes = [IsStaff]

    def get(self, request):
        filial = _filial(request)
        smena = services.xodim_smenasi(request.salon, request.user) or services.ochiq_smena(request.salon, filial)
        if not smena:
            return Response({'ochiq': False, 'filial': filial.nomi if filial else None})
        return Response({
            'ochiq': True, 'id': smena.id, 'filial': smena.filial.nomi if smena.filial_id else None,
            'ishtirokchilar': [i.xodim.ism for i in
                               smena.ishtirokchilar.filter(chiqqan=None).select_related('xodim')],
            'hisobot': services.kassa_hisobot(smena),
            'zalog_tekshirilmagan': tekshiruv.tekshirilmaganlar_soni(smena),
        })


class SmenaOchishSerializer(serializers.Serializer):
    boshlangich_qoldiq = serializers.IntegerField(min_value=0)


class SmenaOchishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = SmenaOchishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            s = services.smena_ochish(salon=request.salon, xodim=request.user, filial=_filial(request), **ser.validated_data)
        except KassaXatosi as e:
            return xato(e)
        return Response({'id': s.id}, status=201)


class SmenaQoshilishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        try:
            s = services.smenaga_qoshilish(salon=request.salon, xodim=request.user, filial=_filial(request))
        except KassaXatosi as e:
            return xato(e)
        return Response({'id': s.id})


class SanashSerializer(serializers.Serializer):
    summa = serializers.IntegerField(min_value=0)
    izoh = serializers.CharField(required=False, allow_blank=True, default='', max_length=300)


class SmenaChiqishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = SanashSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ish = services.smena_chiqish(salon=request.salon, xodim=request.user,
                                         sanalgan_summa=ser.validated_data['summa'], filial=_filial(request))
        except KassaXatosi as e:
            return xato(e)
        return Response({'farq': ish.farq})


class SmenaYopishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = SanashSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            s = services.smena_yopish(salon=request.salon, xodim=request.user,
                                      fakt_qoldiq=ser.validated_data['summa'],
                                      izoh=ser.validated_data['izoh'], filial=_filial(request))
        except KassaXatosi as e:
            return xato(e)
        return Response({'farq': s.farq})


class TolovSerializer(serializers.Serializer):
    # To'g'ridan-to'g'ri kiritiladigan turlar. Qolgan chiqimlar o'z jarayoni orqali: xarajat — rahbar tasdig'i
    # bilan (finance), vozvrat — zakazni bekor qilishda, zalog/jarima — berish va qaytarishda. Aks holda
    # sotuvchi kassadan xarajat yoki «vozvrat» deb pulni hisobsiz olib chiqa olardi.
    tur = serializers.ChoiceField(choices=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ, Tolov.Tur.INKASSATSIYA])
    summa = serializers.IntegerField(min_value=1)
    usul = serializers.ChoiceField(choices=Tolov.Usul.choices, default=Tolov.Usul.NAQD)
    zakaz = serializers.IntegerField(required=False)
    izoh = serializers.CharField(required=False, allow_blank=True, default='', max_length=300)


class TolovView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = TolovSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        zakaz = None
        if 'zakaz' in d:
            zakaz = Zakaz.objects.filter(salon=request.salon, id=d['zakaz']).first()
            if not zakaz:
                return Response({'zakaz': 'Topilmadi.'}, status=400)
        try:
            t = services.tolov_qabul(salon=request.salon, xodim=request.user, tur=d['tur'],
                                     summa=d['summa'], usul=d['usul'], zakaz=zakaz, izoh=d['izoh'])
        except KassaXatosi as e:
            return xato(e)
        return Response({'id': t.id}, status=201)


class ZaloglarView(APIView):
    """Kunlik zalog tekshiruvi (FT-12.5): GET — saqlanayotgan hujjat/tillo zaloglar; POST — «joyida» / «yo'q»."""
    permission_classes = [IsStaff]

    def _smena(self, request):
        return services.xodim_smenasi(request.salon, request.user) or services.ochiq_smena(request.salon, _filial(request))

    def get(self, request):
        smena = self._smena(request)
        if not smena:
            return Response({'ochiq': False, 'zaloglar': []})
        return Response({'ochiq': True, 'zaloglar': tekshiruv.zalog_royxati(smena)})

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        from apps.orders.models import Zalog

        class S(serializers.Serializer):
            zalog = serializers.IntegerField()
            joyida = serializers.BooleanField()
            izoh = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        smena = self._smena(request)
        zalog = Zalog.objects.filter(salon=request.salon, id=d['zalog']).select_related('zakaz').first()
        if not smena or not zalog:
            return Response({'detail': 'Ochiq smena yoki zalog topilmadi.'}, status=404)
        try:
            tekshiruv.zalogni_belgilash(salon=request.salon, xodim=request.user, smena=smena, zalog=zalog,
                                        joyida=d['joyida'], izoh=d['izoh'])
        except KassaXatosi as e:
            return xato(e)
        return Response({'zaloglar': tekshiruv.zalog_royxati(smena)})


class SmenalarView(APIView):
    """Rahbar oxirgi smenalarni ko'radi."""

    def get_permissions(self):
        from apps.tenants.permissions import IsRahbar
        return [IsRahbar()]

    def get(self, request):
        from .models import Smena
        qs = Smena.objects.filter(salon=request.salon).select_related('ochgan', 'filial').order_by('-id')[:40]
        return Response([tekshiruv.smena_json(s) for s in qs])


class SmenaTuzatishView(APIView):
    """PATCH — yopilgan smenaning fakt qoldig'i va izohini faqat rahbar o'zgartiradi (FT-12.11)."""

    def get_permissions(self):
        from apps.tenants.permissions import IsRahbar
        return [IsRahbar(), SalonYozishRuxsati()]

    def patch(self, request, pk):
        from .models import Smena

        class S(serializers.Serializer):
            fakt_qoldiq = serializers.IntegerField(min_value=0, required=False)
            izoh = serializers.CharField(max_length=300, required=False, allow_blank=True)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        smena = Smena.objects.filter(salon=request.salon, id=pk).first()
        if not smena:
            return Response({'detail': 'Smena topilmadi.'}, status=404)
        try:
            smena = tekshiruv.smenani_tuzatish(salon=request.salon, rahbar=request.user, smena=smena, **ser.validated_data)
        except KassaXatosi as e:
            return xato(e)
        return Response(tekshiruv.smena_json(Smena.objects.select_related('ochgan', 'filial').get(id=smena.id)))

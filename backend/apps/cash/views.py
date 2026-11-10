from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Zakaz
from apps.tenants.models import Xodim, sozlama
from apps.tenants.permissions import IsStaff, SalonYozishRuxsati

from . import services, tekshiruv
from .models import KassaTopshirish, Tolov
from .services import KassaXatosi, xato_tanasi


def xato(e):
    return Response(xato_tanasi(e), status=409)


def _xodim(request, pk, nom):
    """So'rovdagi xodim (pul topshiriladigan kishi): shu salonning faol xodimi bo'lishi shart."""
    if pk is None:
        return None
    x = Xodim.objects.filter(salon=request.salon, id=pk, faol=True).first()
    if not x:
        raise ValidationError({nom: ['Xodim topilmadi.']})
    return x


def _filial(request):
    """Shu qurilma kassasi: filial kassasi yoqilgan bo'lsa qurilma filiali, aks holda umumiy kassa (None)."""
    from apps.tenants.views_filial import joriy_filial
    return joriy_filial(request) if sozlama(request.salon).filial_kassasi else None


class SmenaHolatiView(APIView):
    """Joriy smena, hisobot va kimlar ishlayotgani."""
    permission_classes = [IsStaff]

    def get(self, request):
        filial = _filial(request)
        smena = services.xodim_smenasi(request.salon, request.user) or services.ochiq_smena(request.salon, filial)
        men = request.user
        umumiy = {
            'kassa_rejimi': sozlama(request.salon).kassa_rejimi,
            'pul_oladi': services.pul_oladimi(request.salon, men),
            # menga topshirilgan, hali qabul qilinmagan pul (rahbarga — yopilgan smenadan ham)
            'kutayotgan': [services.topshiriq_json(t) for t in KassaTopshirish.objects.filter(
                salon=request.salon, kimga=men, holat=KassaTopshirish.Holat.KUTILMOQDA).select_related('kimdan', 'kimga')],
            'rahbarlar': [{'id': x.id, 'ism': x.ism} for x in Xodim.objects.filter(
                salon=request.salon, rol=Xodim.Rol.RAHBAR, faol=True).exclude(id=men.id).order_by('ism')],
            # inkassatsiya: pul berish mumkin bo'lgan hamkasblar (smenada bo'lmasa — berilganda qo'shiladi)
            'hamkasblar': [{'id': x.id, 'ism': x.ism} for x in Xodim.objects.filter(salon=request.salon, faol=True)
                           .exclude(rol=Xodim.Rol.RAHBAR).exclude(id=men.id).order_by('ism')
                           if services.pul_oladimi(request.salon, x)],
            # rahbarga: hisobiga kelganini tasdiqlashi kerak bo'lgan o'tkazma, Click, Payme to'lovlari
            'otkazmalar': [otkazma_json(t) for t in Tolov.objects.filter(
                salon=request.salon, tasdiq=Tolov.Tasdiq.KUTILMOQDA).select_related('xodim', 'zakaz__mijoz').order_by('vaqt')]
            if men.rol == Xodim.Rol.RAHBAR else [],
        }
        if not smena:
            return Response({'ochiq': False, 'filial': filial.nomi if filial else None,
                             'seyfda': services.seyf_qoldigi(request.salon, filial), **umumiy})
        faol = list(smena.ishtirokchilar.filter(chiqqan=None).select_related('xodim'))
        men_ishtirokchi = any(i.xodim_id == men.id for i in faol)
        return Response({
            'ochiq': True, 'id': smena.id, 'filial': smena.filial.nomi if smena.filial_id else None,
            'ishtirokchilar': [i.xodim.ism for i in faol],
            'xodimlar': [{'id': i.xodim_id, 'ism': i.xodim.ism} for i in faol if i.xodim_id != men.id],  # pul topshirish uchun
            'men_ishtirokchi': men_ishtirokchi,
            'mening_hisobim': services.xodim_qoldigi(smena, men) if men_ishtirokchi else None,
            'yuborilgan': [services.topshiriq_json(t) for t in smena.topshiriqlar.filter(
                kimdan=men, holat=KassaTopshirish.Holat.KUTILMOQDA).select_related('kimdan', 'kimga')],
            'hisobot': services.kassa_hisobot(smena),
            'usullar': services.smena_usullari(smena),  # tushum to'lov usullari bo'yicha (panelda Terminal, O'tkazma)
            # sverka o'chirilgan bo'lsa 0 — yopish oynasida terminal maydoni chiqmaydi
            'terminal_tizimda': services.terminal_tizimda(smena) if sozlama(request.salon).terminal_sverkasi else 0,
            'zalog_tekshirilmagan': tekshiruv.tekshirilmaganlar_soni(smena),
            # kanvas: «smena 09:02 dan», «Pul harakatlari», «Bugungi topshirish» (mening so'rovlarim, holati bilan)
            'ochilgan': smena.ochilgan, 'ochgan': smena.ochgan.ism,
            'harakatlar': services.smena_harakatlari(smena),
            'topshiriqlarim': [services.topshiriq_json(t) for t in smena.topshiriqlar.filter(
                kimdan=men, smena_yopishda=False).select_related('kimdan', 'kimga').order_by('-yaratilgan')[:5]],
            **umumiy,
        })


class SmenaOchishSerializer(serializers.Serializer):
    boshlangich_qoldiq = serializers.IntegerField(min_value=0)
    izoh = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')  # C-11: seyf farqi sababi


class SmenaOchishView(APIView):
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi
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
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi
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
    kimga = serializers.IntegerField(required=False)   # chiqish: kimga topshiriladi
    rahbar = serializers.IntegerField(required=False)  # yopish (seyf o'rniga) va inkassatsiya: qaysi rahbarga
    terminal = serializers.IntegerField(min_value=0, required=False)  # yopish: terminal sverkasidagi summa


class SmenaChiqishView(APIView):
    """POST {summa, kimga?} — qo'ldagi naqdni smenada qolayotgan xodimga yoki rahbarga topshirib chiqish."""
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = SanashSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        kimga = _xodim(request, ser.validated_data.get('kimga'), 'kimga')
        try:
            ish = services.smena_chiqish(salon=request.salon, xodim=request.user, kimga=kimga,
                                         sanalgan_summa=ser.validated_data['summa'], filial=_filial(request))
        except KassaXatosi as e:
            return xato(e)
        return Response({'farq': ish.farq, 'kimga': ish.topshirish.kimga.ism})


class SmenaYopishView(APIView):
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = SanashSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            s = services.smena_yopish(salon=request.salon, xodim=request.user,
                                      fakt_qoldiq=ser.validated_data['summa'], izoh=ser.validated_data['izoh'],
                                      filial=_filial(request), rahbar=_xodim(request, ser.validated_data.get('rahbar'), 'rahbar'),
                                      terminal=ser.validated_data.get('terminal'))
        except KassaXatosi as e:
            return xato(e)
        return Response({'farq': s.farq})


def otkazma_json(t):
    return {'id': t.id, 'summa': t.summa, 'usul': t.usul, 'usul_nomi': t.get_usul_display(), 'tur_nomi': t.get_tur_display(),
            'xodim': t.xodim.ism, 'vaqt': t.vaqt, 'zakaz': t.zakaz.raqam if t.zakaz_id else None,
            'mijoz': (t.zakaz.mijoz.fio or t.zakaz.mijoz.telefon) if t.zakaz_id else None}


class OtkazmaTasdiqView(APIView):
    """POST {keldi: true|false} — rahbar o'tkazma (Click, Payme) hisobiga kelganini tasdiqlaydi."""
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi

    def get_permissions(self):
        from apps.tenants.permissions import IsRahbar
        return [IsRahbar(), SalonYozishRuxsati()]

    def post(self, request, pk):
        t = Tolov.objects.filter(salon=request.salon, id=pk).first()
        if not t:
            return Response({'detail': "To'lov topilmadi."}, status=404)
        keldi = serializers.BooleanField().run_validation(request.data.get('keldi'))
        try:
            t = services.otkazma_tasdiqlash(salon=request.salon, rahbar=request.user, tolov=t, keldi=keldi)
        except KassaXatosi as e:
            return xato(e)
        return Response({'id': t.id, 'tasdiq': t.tasdiq})


class TolovTuzatishView(APIView):
    """POST {usul?, summa?, sabab} — rahbar xato yozilgan avans/qoldiqni tuzatadi (smena ochiq paytda)."""
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi

    def get_permissions(self):
        from apps.tenants.permissions import IsRahbar
        return [IsRahbar(), SalonYozishRuxsati()]

    def post(self, request, pk):
        t = Tolov.objects.filter(salon=request.salon, id=pk).first()
        if not t:
            return Response({'detail': "To'lov topilmadi."}, status=404)
        d = request.data
        usul = serializers.CharField(required=False).run_validation(d['usul']) if d.get('usul') else None
        summa = serializers.IntegerField(min_value=1).run_validation(d['summa']) if d.get('summa') not in (None, '') else None
        sabab = serializers.CharField(max_length=200, allow_blank=True).run_validation(d.get('sabab', ''))
        try:
            t = services.tolov_tuzatish(salon=request.salon, rahbar=request.user, tolov=t, usul=usul, summa=summa, sabab=sabab)
        except KassaXatosi as e:
            return xato(e)
        return Response({'id': t.id, 'usul': t.usul, 'summa': t.summa, 'tasdiq': t.tasdiq})


class InkassatsiyaView(APIView):
    """POST {summa, rahbar | kimga, izoh?} — naqdning bir qismini topshirish: rahbarga (kassadan chiqadi) yoki
    smenadagi hamkasbga (`kimga`, pul kassada qoladi). Qabul qiluvchi Telegramda yoki ilovada tasdiqlaydi."""
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = SanashSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if 'rahbar' not in d and 'kimga' not in d:
            raise ValidationError({'rahbar': ['Kimga topshirilishini tanlang.']})
        try:
            if 'rahbar' in d:
                t = services.inkassatsiya(salon=request.salon, xodim=request.user, rahbar=_xodim(request, d['rahbar'], 'rahbar'),
                                          summa=d['summa'], izoh=d['izoh'])
            else:
                t = services.hamkasbga_berish(salon=request.salon, xodim=request.user, kimga=_xodim(request, d['kimga'], 'kimga'),
                                              summa=d['summa'], izoh=d['izoh'])
        except KassaXatosi as e:
            return xato(e)
        return Response(services.topshiriq_json(t), status=201)


class TopshiriqQabulView(APIView):
    """POST {summa?} — menga topshirilgan pulni sanab qabul qilish (summasiz — topshiruvchi aytgan summa)."""
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        t = KassaTopshirish.objects.filter(salon=request.salon, id=pk).first()
        if not t:
            return Response({'detail': 'Topshiriq topilmadi.'}, status=404)
        summa = request.data.get('summa')
        if summa is not None:
            summa = serializers.IntegerField(min_value=0).run_validation(summa)
        try:
            t = services.topshiriqni_qabul(salon=request.salon, xodim=request.user, topshirish=t, summa=summa)
        except KassaXatosi as e:
            return xato(e)
        return Response(services.topshiriq_json(t))


class TolovSerializer(serializers.Serializer):
    # To'g'ridan-to'g'ri kiritiladigan turlar. Qolgan chiqimlar o'z jarayoni orqali: xarajat — rahbar tasdig'i
    # bilan (finance), vozvrat — zakazni bekor qilishda, zalog/jarima — berish va qaytarishda. Aks holda
    # sotuvchi kassadan xarajat yoki «vozvrat» deb pulni hisobsiz olib chiqa olardi.
    # Inkassatsiya — faqat /inkassatsiya/ orqali (kimga topshirilgani va rahbar tasdig'i bilan)
    tur = serializers.ChoiceField(choices=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ])
    summa = serializers.IntegerField(min_value=0)  # 0 — faqat to'liq bepul zakaz bronini tasdiqlash (tolov_qabul tekshiradi)
    usul = serializers.ChoiceField(choices=Tolov.Usul.choices, default=Tolov.Usul.NAQD)
    zakaz = serializers.IntegerField(required=False)
    izoh = serializers.CharField(required=False, allow_blank=True, default='', max_length=300)


class TolovView(APIView):
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi
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
    """Kunlik garov tekshiruvi (FT-12.5): GET — saqlanayotgan hujjat/tillo garovlar; POST — «joyida» / «yo'q»."""
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi
    permission_classes = [IsStaff]

    def _smena(self, request):
        return services.xodim_smenasi(request.salon, request.user) or services.ochiq_smena(request.salon, _filial(request))

    def get(self, request):
        smena = self._smena(request)
        if not smena:
            return Response({'ochiq': False, 'zaloglar': []})
        return Response({'ochiq': True, 'zaloglar': tekshiruv.zalog_royxati(smena), 'pul': tekshiruv.pul_zaloglar(smena)})

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
            return Response({'detail': 'Ochiq smena yoki garov topilmadi.'}, status=404)
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
        """?farqli=1 — faqat kassa, terminal yoki seyf (ochishdagi) farqi bor smenalar (egasi kamomadni ko'radi)."""
        from django.db.models import Q

        from .models import Smena
        qs = Smena.objects.filter(salon=request.salon)
        if request.query_params.get('farqli') == '1':
            qs = qs.filter(Q(farq__lt=0) | Q(farq__gt=0) | Q(terminal_farq__lt=0) | Q(terminal_farq__gt=0)
                           | Q(seyf_farq__lt=0) | Q(seyf_farq__gt=0))
        qs = qs.select_related('ochgan', 'filial').order_by('-id')[:40]
        return Response([tekshiruv.smena_json(s) for s in qs])


class SmenaTuzatishView(APIView):
    """PATCH — yopilgan smenaning fakt qoldig'i va izohini faqat rahbar o'zgartiradi (FT-12.11)."""
    faqat_korishda_ruxsat = True  # C-12: obuna tugaganda ham boshlangan ish yakunlanadi

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

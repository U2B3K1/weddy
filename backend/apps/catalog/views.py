from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Jurnal, Xodim, jurnalga_yoz, sozlama
from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati, yozish_taqiqi

from apps.cash.services import KassaXatosi, xato_tanasi
from apps.finance.services import XarajatXatosi

from .models import AksessuarDona, Kategoriya, Libos, Rasm, Sanoq, TamirYozuvi, YetkazibBeruvchi
from .manekin import joylashuvni_saqlash, manekin_json, qatlam_yaratish
from .rasm import rasm_yuklash, rasmni_ochirish
from .sanoq import belgilash, ochiq_sanoq, qator_json, sanoq_bekor, sanoq_boshlash, sanoq_json, sanoq_yakunlash
from .tamir import tamirga_berish, tamirni_tugatish
from .yetkazib import YetkazibXatosi, libos_xaridi_yoz
from .services import (KatalogXatosi, QOLDA_HOLATLAR, keyingi_artikul, tozalashni_yakunla, libos_qoshish,
                       libosni_ozgartirish, libosni_rad_etish, libosni_tasdiqlash)


def rasm_json(r, request):
    # ochira_oladi — «×» faqat ruxsat bo'lsa ko'rsatiladi (rahbar yoki rasmni yuklagan xodim, RasmOchirishView bilan bir xil)
    return {'id': r.id, 'katta': request.build_absolute_uri(r.katta.url),
            'kichik': request.build_absolute_uri(r.kichik.url), 'standart': r.standart,
            'fonsiz': request.build_absolute_uri(r.fonsiz.url) if r.fonsiz else None,
            'ochira_oladi': _rahbar(request) or r.yuklagan_id == request.user.id}


def mijozdagi_liboslar(salon, liboslar=None):
    """Hozir mijozda turgan liboslar: {libos_id: qaytish sanasi} — berilgan («berildi») zakazdagi pozitsiyalar
    (sanoqdagi `_joylar` bilan bir xil ta'rif). Libos holati berishda o'zgarmaydi («bo'sh» qoladi), shuning uchun
    katalog «mijozda»ni shu yerdan biladi."""
    from apps.orders.models import Zakaz, ZakazPozitsiya
    qs = ZakazPozitsiya.objects.filter(salon=salon, zakaz__holat=Zakaz.Holat.BERILDI)
    if liboslar is not None:
        qs = qs.filter(libos__in=liboslar)
    return dict(qs.order_by('zakaz__qaytarish').values_list('libos_id', 'zakaz__qaytarish'))


def ijara_korsatkichlari(salon):
    """Kanvas libos kartasi: shu oyda necha marta ijaraga chiqqan (olib ketish sanasi shu oyda, bekor va tasdiqsiz
    bronlar kirmaydi) va eng yaqin kelgusi bron sanasi: ({libos_id: son}, {libos_id: sana})."""
    from django.db.models import Count, Min
    from django.utils import timezone

    from apps.finance.reports import oy_chegaralari
    from apps.orders.models import Zakaz, ZakazPozitsiya
    H = Zakaz.Holat
    bugun = timezone.localdate()
    qs = ZakazPozitsiya.objects.filter(salon=salon)
    bu_oy = dict(qs.filter(zakaz__holat__in=[H.BRON, H.BERILDI, H.QAYTARILDI, H.YOPILDI],
                           zakaz__olib_ketish__range=oy_chegaralari(bugun.year, bugun.month))
                 .values_list('libos_id').annotate(n=Count('id')))
    keyingi = dict(qs.filter(zakaz__holat__in=[H.VAQTINCHALIK, H.CHEGIRMA_KUTILMOQDA, H.BRON], zakaz__olib_ketish__gte=bugun)
                   .values_list('libos_id').annotate(s=Min('zakaz__olib_ketish')))
    return bu_oy, keyingi


def libos_json(l, rahbar, request=None, rasmlar=False, mijozda=None):
    """Tannarx faqat rahbarga ko'rinadi (FT-3.5, 3-bo'lim). `mijozda` — `mijozdagi_liboslar()` natijasi (berilmasa
    shu libos uchun so'raladi): mijozda bo'lsa `mijozda: true` va `qaytish` — kelishilgan qaytarish sanasi."""
    if mijozda is None:
        mijozda = mijozdagi_liboslar(l.salon_id, [l.id])
    d = {'id': l.id, 'artikul': l.artikul, 'nomi': l.nomi, 'kategoriya': l.kategoriya.nomi,
         'kategoriya_id': l.kategoriya_id, 'olcham': l.olcham, 'rang': l.rang, 'holat': l.holat,
         'ijara_narxi': l.ijara_narxi, 'zalog': l.zalog, 'filial': l.filial_id,
         'qoshgan': l.qoshgan.ism if l.qoshgan else None,
         'mijozda': l.id in mijozda, 'qaytish': mijozda.get(l.id)}
    if request is not None:
        r = list(l.rasmlar.all())  # prefetch qilingan bo'lsa qo'shimcha so'rov yo'q
        d['rasm'] = request.build_absolute_uri(r[0].kichik.url) if r else None
        d['rasmlar_soni'] = len(r)
        if rasmlar:
            d['rasmlar'] = [rasm_json(x, request) for x in r]
            d['manekin'] = manekin_json(l, request)
        if rahbar:
            d['standart_emas'] = sum(1 for x in r if not x.standart)
    if rahbar:
        d.update(tannarx=l.tannarx, bufer_kun=l.bufer_kun, yetkazib_beruvchi=l.yetkazib_beruvchi_id)
    return d


def _rahbar(request):
    return request.user.rol == Xodim.Rol.RAHBAR


def _libos(request, pk):
    libos = (Libos.objects.select_related('kategoriya', 'qoshgan').prefetch_related('rasmlar')
             .filter(salon=request.salon, id=pk).first())
    if not libos:
        raise NotFound('Libos topilmadi.')
    return libos


def _bajar(fn, **kw):
    try:
        return fn(**kw), None
    except (KatalogXatosi, KassaXatosi, XarajatXatosi, YetkazibXatosi) as e:
        return None, Response(xato_tanasi(e), status=409)


class LibosYaratSerializer(serializers.Serializer):
    artikul = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')  # avto sozlamada bo'sh bo'lishi mumkin
    nomi = serializers.CharField(max_length=200)
    kategoriya = serializers.IntegerField()
    olcham = serializers.CharField(required=False, allow_blank=True, default='')
    rang = serializers.CharField(required=False, allow_blank=True, default='')
    ijara_narxi = serializers.IntegerField(min_value=0, default=0)
    zalog = serializers.IntegerField(min_value=0, default=0)
    tannarx = serializers.IntegerField(min_value=0, required=False)
    # faqat rahbar: qayerdan olingan va hozir qancha to'langan (berilmasa — tannarx to'liq to'langan; qolgani qarz)
    yetkazib_beruvchi = serializers.IntegerField(required=False, allow_null=True)
    tolandi = serializers.IntegerField(min_value=0, required=False, allow_null=True)


class KeyingiArtikulView(APIView):
    """GET — libos qo'shish formasi uchun: prefiks va keyingi avto artikul (avto o'chirilgan bo'lsa null)."""
    permission_classes = [IsStaff]

    def get(self, request):
        soz = sozlama(request.salon)
        return Response({'prefiks': soz.artikul_prefiks,
                         'artikul': keyingi_artikul(request.salon, soz) if soz.artikul_avto else None})


class LiboslarView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        tozalashni_yakunla(request.salon)  # bufer kuni o'tgan «tozalashda» liboslar bo'sh bo'ladi
        qs = (Libos.objects.filter(salon=request.salon).select_related('kategoriya', 'qoshgan')
              .prefetch_related('rasmlar'))
        p = request.query_params
        if p.get('holat'):
            qs = qs.filter(holat=p['holat'])
        elif not _rahbar(request) or p.get('faol') == '1':
            qs = qs.exclude(holat__in=[Libos.Holat.SOTILDI, Libos.Holat.HISOBDAN_CHIQARILDI, Libos.Holat.ARXIV])
        if p.get('kategoriya'):
            qs = qs.filter(kategoriya_id=p['kategoriya'])
        if p.get('filial', '').isdigit():
            qs = qs.filter(filial_id=int(p['filial']))
        if p.get('q'):
            qs = qs.filter(artikul__icontains=p['q']) | qs.filter(nomi__icontains=p['q'])
        rahbar = _rahbar(request)
        mijozda = mijozdagi_liboslar(request.salon)  # bitta so'rov butun ro'yxat uchun
        bu_oy, keyingi = ijara_korsatkichlari(request.salon)
        return Response([{**libos_json(l, rahbar, request, mijozda=mijozda), 'bu_oy': bu_oy.get(l.id, 0),
                          'keyingi_bron': keyingi.get(l.id)} for l in qs.order_by('artikul')[:300]])

    def post(self, request):
        if (rad := yozish_taqiqi(request, self)):  # o'zbekcha sabab bilan (C-12)
            return rad
        ser = LibosYaratSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        kat = Kategoriya.objects.filter(salon=request.salon, id=d.pop('kategoriya')).first()
        if not kat:
            return Response({'kategoriya': ['Topilmadi.']}, status=400)
        if _rahbar(request):  # tannarxsiz yoki narxsiz libos katalogga chiqmaydi (foyda va qoplash noto'g'ri hisoblanardi)
            yoq = {}
            if not d.get('ijara_narxi'):
                yoq['ijara_narxi'] = ['Ijara narxini kiriting.']
            if d.get('tannarx') is None:
                yoq['tannarx'] = ["Tannarxni kiriting — libos qanchaga olingan. Busiz foyda noto'g'ri hisoblanadi."]
            if yoq:
                return Response(yoq, status=400)
        yb_id, tolandi = d.pop('yetkazib_beruvchi', None), d.pop('tolandi', None)
        yb = None
        if yb_id and _rahbar(request):  # sotuvchi tannarx kabi yetkazib beruvchini ham kiritmaydi
            yb = YetkazibBeruvchi.objects.filter(salon=request.salon, id=yb_id).first()
            if not yb:
                return Response({'yetkazib_beruvchi': ['Topilmadi.']}, status=400)
            if tolandi is not None and tolandi > (d.get('tannarx') or 0):
                return Response({'tolandi': ["Tannarxdan ko'p bo'lishi mumkin emas."]}, status=400)
        with transaction.atomic():
            libos, err = _bajar(libos_qoshish, salon=request.salon, xodim=request.user, kategoriya=kat, **d)
            if yb and libos is not None:
                libos_xaridi_yoz(salon=request.salon, rahbar=request.user, libos=libos, yb=yb, tolandi=tolandi)
        if libos is not None:
            from apps.tenants.views_filial import joriy_filial
            filial = joriy_filial(request)
            if filial:
                libos.filial = filial
                libos.save(update_fields=['filial'])
        return err or Response(libos_json(libos, _rahbar(request), request), status=201)


class LibosTafsilotView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, pk):
        return Response(libos_json(_libos(request, pk), _rahbar(request), request, rasmlar=True))

    def patch(self, request, pk):
        if (rad := yozish_taqiqi(request, self)):  # «faqat ko'rish»da katalog yopiq (QA-15)
            return rad
        if not _rahbar(request):
            return Response({'detail': "Narx va tannarxni faqat rahbar o'zgartiradi."}, status=403)

        class S(serializers.Serializer):
            ijara_narxi = serializers.IntegerField(min_value=0, required=False)
            tannarx = serializers.IntegerField(min_value=0, required=False)
            zalog = serializers.IntegerField(min_value=0, required=False)
            bufer_kun = serializers.IntegerField(min_value=0, max_value=30, required=False)
            holat = serializers.ChoiceField(choices=[h.value for h in QOLDA_HOLATLAR], required=False)
            # B-05: libos ma'lumoti (xato kiritilgan o'lcham filtrni buzadi — arxivlab qayta qo'shish shart emas)
            artikul = serializers.CharField(max_length=50, required=False)
            nomi = serializers.CharField(max_length=200, required=False)
            kategoriya = serializers.IntegerField(required=False)
            olcham = serializers.CharField(max_length=20, required=False, allow_blank=True)
            rang = serializers.CharField(max_length=50, required=False, allow_blank=True)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        if 'kategoriya' in ser.validated_data:
            kat = Kategoriya.objects.filter(salon=request.salon, id=ser.validated_data['kategoriya'],
                                            turi=Kategoriya.Turi.LIBOS).first()
            if not kat:
                return Response({'kategoriya': ['Kategoriya topilmadi.']}, status=400)
            ser.validated_data['kategoriya'] = kat
        yb_ozgaradi, yb = 'yetkazib_beruvchi' in request.data, None
        if yb_ozgaradi and request.data['yetkazib_beruvchi']:
            yb = YetkazibBeruvchi.objects.filter(salon=request.salon, id=request.data['yetkazib_beruvchi']).first()
            if not yb:
                return Response({'yetkazib_beruvchi': ['Topilmadi.']}, status=400)
        filial_ozgaradi, filial = 'filial' in request.data, None
        if filial_ozgaradi:  # libosni filialga ko'chirish (null — biriktirilmagan)
            from apps.tenants.views_filial import sorovdagi_filial
            filial = sorovdagi_filial(request)
        # Filial va qolgan maydonlar bitta tranzaksiyada: holat rad etilsa filial ham o'zgarmay qoladi
        with transaction.atomic():
            libos, err = _bajar(libosni_ozgartirish, salon=request.salon, rahbar=request.user,
                                libos=_libos(request, pk), **ser.validated_data)
            if not err and filial_ozgaradi and libos.filial_id != (filial.id if filial else None):
                jurnalga_yoz(request.salon, request.user, 'libos_filiali', libos.artikul, libos.filial_id or '',
                             filial.id if filial else '')
                libos.filial = filial
                libos.save(update_fields=['filial'])
            if not err and yb_ozgaradi and libos.yetkazib_beruvchi_id != (yb.id if yb else None):
                # keyin biriktirilsa to'lov yozilmaydi — tannarx qarzga qo'shiladi, to'lov yetkazib beruvchi sahifasida
                jurnalga_yoz(request.salon, request.user, 'libos_yetkazib_beruvchisi', libos.artikul,
                             libos.yetkazib_beruvchi_id or '', yb.id if yb else '')
                libos.yetkazib_beruvchi = yb
                libos.save(update_fields=['yetkazib_beruvchi'])
        return err or Response(libos_json(libos, True, request))


class LibosRadView(APIView):
    """POST {sabab?} — rahbar tasdiq kutayotgan libosni rad etadi (arxivga, jurnalga; C-25)."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request, pk):
        sabab = str(request.data.get('sabab') or '')[:300]
        libos, err = _bajar(libosni_rad_etish, salon=request.salon, rahbar=request.user, libos=_libos(request, pk), sabab=sabab)
        return err or Response(libos_json(libos, True, request))


class LibosPasportView(APIView):
    """GET — libos pasporti: hozir kimda va qachon qaytadi, kelgusi bronlar; rahbarga — samaradorlik (faqat o'qish)."""
    permission_classes = [IsStaff]

    def get(self, request, pk):
        from .pasport import libos_pasporti
        return Response(libos_pasporti(request.salon, _libos(request, pk), rahbar=_rahbar(request)))


class LibosTasdiqView(APIView):
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request, pk):
        class S(serializers.Serializer):
            ijara_narxi = serializers.IntegerField(min_value=0)
            tannarx = serializers.IntegerField(min_value=0)
            zalog = serializers.IntegerField(min_value=0, required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        libos, err = _bajar(libosni_tasdiqlash, salon=request.salon, rahbar=request.user,
                            libos=_libos(request, pk), **ser.validated_data)
        return err or Response(libos_json(libos, True, request))


class KategoriyalarView(APIView):
    def get_permissions(self):
        # yaratish — rahbar va salon yozishga ochiq bo'lsa («faqat ko'rish»da katalog yopiq, QA-15)
        return [IsRahbar(), SalonYozishRuxsati()] if self.request.method == 'POST' else [IsStaff()]

    def get(self, request):
        qs = Kategoriya.objects.filter(salon=request.salon)
        return Response([{'id': k.id, 'nomi': k.nomi, 'turi': k.turi, 'bufer_kun': k.bufer_kun} for k in qs])

    def post(self, request):
        class S(serializers.Serializer):
            nomi = serializers.CharField(max_length=100)
            turi = serializers.ChoiceField(choices=['libos', 'aksessuar'], default='libos')
            bufer_kun = serializers.IntegerField(min_value=0, max_value=30, required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        if Kategoriya.objects.filter(salon=request.salon, nomi=ser.validated_data['nomi'],
                                     turi=ser.validated_data['turi']).exists():
            return Response({'detail': 'Bunday kategoriya bor.'}, status=409)
        k = Kategoriya.objects.create(salon=request.salon, tartib=Kategoriya.objects.filter(
            salon=request.salon).count(), **ser.validated_data)
        return Response({'id': k.id, 'nomi': k.nomi}, status=201)


class KategoriyaView(APIView):
    """PATCH — nom va bufer kunini o'zgartirish; DELETE — faqat bo'sh kategoriyani o'chirish."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def _kategoriya(self, request, pk):
        k = Kategoriya.objects.filter(salon=request.salon, id=pk).first()
        if not k:
            raise NotFound('Kategoriya topilmadi.')
        return k

    def patch(self, request, pk):
        class S(serializers.Serializer):
            nomi = serializers.CharField(max_length=100, required=False)
            bufer_kun = serializers.IntegerField(min_value=0, max_value=30, required=False, allow_null=True)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        k = self._kategoriya(request, pk)
        if 'nomi' in d and d['nomi'] != k.nomi:
            if Kategoriya.objects.filter(salon=request.salon, nomi=d['nomi'], turi=k.turi).exclude(id=k.id).exists():
                return Response({'detail': 'Bunday kategoriya bor.'}, status=409)
            jurnalga_yoz(request.salon, request.user, 'kategoriya_ozgardi', f'kategoriya {k.nomi}', k.nomi, d['nomi'])
            k.nomi = d['nomi']
        if 'bufer_kun' in d:
            k.bufer_kun = d['bufer_kun']
        k.save()
        return Response({'id': k.id, 'nomi': k.nomi, 'turi': k.turi, 'bufer_kun': k.bufer_kun})

    def delete(self, request, pk):
        from .models import Aksessuar
        k = self._kategoriya(request, pk)
        soni = Libos.objects.filter(kategoriya=k).count() + Aksessuar.objects.filter(kategoriya=k).count()
        if soni:
            return Response({'detail': f"Kategoriyada {soni} ta mahsulot bor (arxivdagilar ham hisobda) — o'chirib bo'lmaydi."},
                            status=409)
        jurnalga_yoz(request.salon, request.user, 'kategoriya_ochirildi', f'kategoriya {k.nomi}')
        k.delete()
        return Response(status=204)


class JurnalView(APIView):
    """Faqat rahbar jurnalni ko'radi (Ilova B)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        qs = Jurnal.objects.filter(salon=request.salon).select_related('xodim')[:200]
        return Response([{'harakat': j.harakat, 'obyekt': j.obyekt, 'eski': j.eski, 'yangi': j.yangi,
                          'xodim': j.xodim.ism if j.xodim else None, 'vaqt': j.vaqt} for j in qs])


class SanoqView(APIView):
    """GET — ochiq sanoq (qatorlari bilan) va oxirgi yakunlanganlar; POST {filial?} — yangi sanoq boshlash;
    DELETE — ochiq sanoqni bekor qilish (tasodifan boshlangan bo'lsa: hech kimga xabar yuborilmaydi, tarixda qolmaydi)."""

    def get_permissions(self):
        return [IsStaff()] if self.request.method == 'GET' else [SalonYozishRuxsati()]

    def get(self, request):
        ochiq = ochiq_sanoq(request.salon)
        tarix = (Sanoq.objects.filter(salon=request.salon, yakunlangan__isnull=False)
                 .select_related('filial', 'boshlagan', 'yakunlagan')[:20])
        return Response({'ochiq': sanoq_json(ochiq, qatorlar=True, request=request) if ochiq else None,
                         'tarix': [sanoq_json(s) for s in tarix]})

    def post(self, request):
        from apps.tenants.views_filial import sorovdagi_filial
        filial = sorovdagi_filial(request) if request.data.get('filial') else None
        s, err = _bajar(sanoq_boshlash, salon=request.salon, xodim=request.user, filial=filial)
        return err or Response(sanoq_json(s, qatorlar=True, request=request), status=201)

    def delete(self, request):
        sanoq = ochiq_sanoq(request.salon)
        if not sanoq:
            raise NotFound("Ochiq sanoq yo'q.")
        _, err = _bajar(sanoq_bekor, salon=request.salon, xodim=request.user, sanoq=sanoq)
        return err or Response(status=204)


class SanoqBelgilashSerializer(serializers.Serializer):
    artikul = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    libos = serializers.IntegerField(required=False)
    dona = serializers.IntegerField(required=False)  # aksessuar donasi (yorliqli)
    topildi = serializers.BooleanField(default=True)


class SanoqBelgilashView(APIView):
    """POST {artikul} (libos artikuli yoki dona yorlig'i — skaner yoki qo'lda) yoki {libos|dona, topildi} (ro'yxatdan)."""
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        ser = SanoqBelgilashSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if not d['artikul'].strip() and 'libos' not in d and 'dona' not in d:
            raise ValidationError({'artikul': ['Artikul yoki yorliqni kiriting.']})
        sanoq = ochiq_sanoq(request.salon)
        if not sanoq:
            raise NotFound("Ochiq sanoq yo'q.")
        libos = dona = None
        if 'libos' in d:
            libos = Libos.objects.filter(salon=request.salon, id=d['libos']).first()
            if not libos:
                raise NotFound('Libos topilmadi.')
        elif 'dona' in d:
            dona = AksessuarDona.objects.filter(salon=request.salon, id=d['dona']).first()
            if not dona:
                raise NotFound('Aksessuar donasi topilmadi.')
        q, err = _bajar(belgilash, salon=request.salon, xodim=request.user, sanoq=sanoq, topildi=d['topildi'],
                        libos=libos, dona=dona, artikul=d['artikul'])
        return err or Response(qator_json(q, request))


class SanoqYakunlashView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request):
        sanoq = ochiq_sanoq(request.salon)
        if not sanoq:
            raise NotFound("Ochiq sanoq yo'q.")
        izoh = str(request.data.get('izoh') or '')[:300]
        s, err = _bajar(sanoq_yakunlash, salon=request.salon, xodim=request.user, sanoq=sanoq, izoh=izoh)
        return err or Response(sanoq_json(s, qatorlar=True, request=request))


class RasmlarView(APIView):
    """POST /api/liboslar/<id>/rasmlar/ (multipart, maydon: «rasm»). Har bir xodim yuklay oladi (FT-3.5)."""
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        libos = _libos(request, pk)
        fayl = request.FILES.get('rasm')
        if not fayl:
            raise ValidationError({'rasm': ['Rasm faylini yuboring.']})
        r, err = _bajar(rasm_yuklash, salon=request.salon, xodim=request.user, libos=libos, fayl=fayl)
        return err or Response(rasm_json(r, request), status=201)


class RasmFonsizView(APIView):
    """POST /api/rasmlar/<id>/fonsiz/ — manekin uchun fonsiz qatlam tayyorlaydi va libosning manekin rasmi qiladi."""
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        rasm = Rasm.objects.filter(salon=request.salon, id=pk).first()
        if not rasm:
            raise NotFound('Rasm topilmadi.')
        r, err = _bajar(qatlam_yaratish, salon=request.salon, rasm=rasm)
        return err or Response({**rasm_json(r, request), 'manekin': manekin_json(_libos(request, r.libos_id), request)}, status=201)


class ManekinSerializer(serializers.Serializer):
    x = serializers.FloatField()
    y = serializers.FloatField()
    kattalik = serializers.FloatField()


class ManekinView(APIView):
    """GET — qatlam va saqlangan joylashuv; PATCH — sotuvchi to'g'rilagan holatni saqlash (FT-5.3)."""
    permission_classes = [SalonYozishRuxsati]

    def get(self, request, pk):
        return Response({'manekin': manekin_json(_libos(request, pk), request)})

    def patch(self, request, pk):
        ser = ManekinSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        l, err = _bajar(joylashuvni_saqlash, salon=request.salon, libos=_libos(request, pk), **ser.validated_data)
        return err or Response({'manekin': manekin_json(l, request)})


class RasmOchirishView(APIView):
    """Rasmni rahbar yoki uni yuklagan xodim o'chiradi."""
    permission_classes = [SalonYozishRuxsati]

    def delete(self, request, pk):
        rasm = Rasm.objects.filter(salon=request.salon, id=pk).first()
        if not rasm:
            raise NotFound('Rasm topilmadi.')
        if not _rahbar(request) and rasm.yuklagan_id != request.user.id:
            return Response({'detail': "Rasmni faqat rahbar yoki yuklagan xodim o'chiradi."}, status=403)
        rasmni_ochirish(rasm)
        return Response(status=204)


def tamir_json(t):
    return {'id': t.id, 'ish_turi': t.ish_turi, 'kim': t.kim, 'boshlangan': t.boshlangan,
            'tugagan': t.tugagan, 'narx': t.narx, 'kunlar': t.kunlar(), 'ochiq': t.tugagan is None,
            'kiritgan': t.kiritgan.ism if t.kiritgan else None}


class TamirlarView(APIView):
    """Libos kartasidagi ta'mir jurnali (FT-3.10): ro'yxat va ta'mirga berish."""
    permission_classes = [IsStaff]

    def get(self, request, pk):
        libos = _libos(request, pk)
        return Response([tamir_json(t) for t in libos.tamirlar.select_related('kiritgan')])

    def post(self, request, pk):
        if (rad := yozish_taqiqi(request, self)):  # o'zbekcha sabab bilan (C-12)
            return rad

        class S(serializers.Serializer):
            ish_turi = serializers.CharField(max_length=300)
            kim = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
            sana = serializers.DateField(required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        t, err = _bajar(tamirga_berish, salon=request.salon, xodim=request.user,
                        libos=_libos(request, pk), **ser.validated_data)
        return err or Response(tamir_json(t), status=201)


class TamirTugatishView(APIView):
    permission_classes = [SalonYozishRuxsati]

    def post(self, request, pk):
        yozuv = TamirYozuvi.objects.filter(salon=request.salon, id=pk).first()
        if not yozuv:
            raise NotFound("Ta'mir yozuvi topilmadi.")

        class S(serializers.Serializer):
            narx = serializers.IntegerField(min_value=0, default=0)
            sana = serializers.DateField(required=False)
            kassadan = serializers.BooleanField(required=False)
            usul = serializers.ChoiceField(choices=['naqd', 'karta', 'click', 'payme'], default='naqd')

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        t, err = _bajar(tamirni_tugatish, salon=request.salon, xodim=request.user, yozuv=yozuv,
                        **ser.validated_data)
        return err or Response(tamir_json(t))

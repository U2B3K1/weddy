from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Jurnal, Xodim, jurnalga_yoz
from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati

from apps.cash.services import KassaXatosi
from apps.finance.services import XarajatXatosi

from .models import Kategoriya, Libos, Rasm, TamirYozuvi
from .manekin import joylashuvni_saqlash, manekin_json, qatlam_yaratish
from .rasm import rasm_yuklash, rasmni_ochirish
from .tamir import tamirga_berish, tamirni_tugatish
from .services import (KatalogXatosi, QOLDA_HOLATLAR, libos_qoshish, libosni_ozgartirish,
                       libosni_tasdiqlash)


def rasm_json(r, request):
    return {'id': r.id, 'katta': request.build_absolute_uri(r.katta.url),
            'kichik': request.build_absolute_uri(r.kichik.url), 'standart': r.standart,
            'fonsiz': request.build_absolute_uri(r.fonsiz.url) if r.fonsiz else None}


def libos_json(l, rahbar, request=None, rasmlar=False):
    """Tannarx faqat rahbarga ko'rinadi (FT-3.5, 3-bo'lim)."""
    d = {'id': l.id, 'artikul': l.artikul, 'nomi': l.nomi, 'kategoriya': l.kategoriya.nomi,
         'kategoriya_id': l.kategoriya_id, 'olcham': l.olcham, 'rang': l.rang, 'holat': l.holat,
         'ijara_narxi': l.ijara_narxi, 'zalog': l.zalog, 'filial': l.filial_id,
         'qoshgan': l.qoshgan.ism if l.qoshgan else None}
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
        d.update(tannarx=l.tannarx, bufer_kun=l.bufer_kun)
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
    except (KatalogXatosi, KassaXatosi, XarajatXatosi) as e:
        return None, Response({'detail': str(e)}, status=409)


class LibosYaratSerializer(serializers.Serializer):
    artikul = serializers.CharField(max_length=50)
    nomi = serializers.CharField(max_length=200)
    kategoriya = serializers.IntegerField()
    olcham = serializers.CharField(required=False, allow_blank=True, default='')
    rang = serializers.CharField(required=False, allow_blank=True, default='')
    ijara_narxi = serializers.IntegerField(min_value=0, default=0)
    zalog = serializers.IntegerField(min_value=0, default=0)
    tannarx = serializers.IntegerField(min_value=0, required=False)


class LiboslarView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
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
        return Response([libos_json(l, rahbar, request) for l in qs.order_by('artikul')[:300]])

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = LibosYaratSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        kat = Kategoriya.objects.filter(salon=request.salon, id=d.pop('kategoriya')).first()
        if not kat:
            return Response({'kategoriya': ['Topilmadi.']}, status=400)
        libos, err = _bajar(libos_qoshish, salon=request.salon, xodim=request.user, kategoriya=kat, **d)
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
        if not _rahbar(request):
            return Response({'detail': "Narx va tannarxni faqat rahbar o'zgartiradi."}, status=403)

        class S(serializers.Serializer):
            ijara_narxi = serializers.IntegerField(min_value=0, required=False)
            tannarx = serializers.IntegerField(min_value=0, required=False)
            zalog = serializers.IntegerField(min_value=0, required=False)
            bufer_kun = serializers.IntegerField(min_value=0, max_value=30, required=False)
            holat = serializers.ChoiceField(choices=[h.value for h in QOLDA_HOLATLAR], required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        if 'filial' in request.data:  # libosni filialga ko'chirish (null — biriktirilmagan)
            from apps.tenants.models import Filial, jurnalga_yoz
            fid = request.data.get('filial')
            filial = Filial.objects.filter(salon=request.salon, id=fid, faol=True).first() if fid else None
            if fid and not filial:
                raise NotFound('Filial topilmadi.')
            l = _libos(request, pk)
            if l.filial_id != (filial.id if filial else None):
                jurnalga_yoz(request.salon, request.user, 'libos_filiali', l.artikul, l.filial_id or '', filial.id if filial else '')
                l.filial = filial
                l.save(update_fields=['filial'])
        libos, err = _bajar(libosni_ozgartirish, salon=request.salon, rahbar=request.user,
                            libos=_libos(request, pk), **ser.validated_data)
        return err or Response(libos_json(libos, True, request))


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
        return [(IsRahbar if self.request.method == 'POST' else IsStaff)()]

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
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)

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

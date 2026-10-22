from datetime import date

from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cash.services import KassaXatosi
from apps.tenants.models import Xodim
from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati, salon_yoza_oladimi
from django.utils import timezone

from . import reports
from .models import Xarajat, YopilganOy
from .services import (XarajatXatosi, bank_holati, bank_solishtirish, oy_yopilgan, oyni_ochish, oyni_yopish, xarajat_kiritish,
                       xarajat_qarori, xarajatni_bekor_qilish, xarajatni_tuzatish)


def xarajat_json(x, nomlar=None):
    if nomlar is None:
        from .moddalar import modda_nomlari
        nomlar = modda_nomlari(x.salon_id)
    return {'id': x.id, 'sana': x.sana, 'modda': x.modda, 'modda_nomi': nomlar.get(x.modda, x.modda), 'doimiy': x.doimiy_id is not None, 'summa': x.summa, 'usul': x.usul,
            'izoh': x.izoh, 'holat': x.holat, 'kiritgan': x.kiritgan.ism if x.kiritgan else None,
            'kassadan': x.tolov_id is not None, 'filial': x.filial_id}


class XarajatSerializer(serializers.Serializer):
    modda = serializers.CharField(max_length=12)  # standart yoki salon moddasi; servis tekshiradi
    summa = serializers.IntegerField(min_value=1)
    sana = serializers.DateField(required=False)
    usul = serializers.ChoiceField(choices=['naqd', 'karta', 'click', 'payme'], default='naqd')
    izoh = serializers.CharField(required=False, allow_blank=True, default='', max_length=300)
    kassadan = serializers.BooleanField(required=False)


class XarajatlarView(APIView):
    """Sotuvchi o'zi kiritganini, rahbar hammasini ko'radi (Ilova B)."""
    permission_classes = [IsStaff]

    def get(self, request):
        from .moddalar import doimiy_qoralamalarni_yarat, modda_nomlari
        # FT-13.3: joriy oy qoralamalari rahbar ro'yxatni ochganda paydo bo'ladi («faqat ko'rish» salonida yozilmaydi)
        if request.user.rol == Xodim.Rol.RAHBAR and salon_yoza_oladimi(request.salon):
            doimiy_qoralamalarni_yarat(request.salon)
        qs = Xarajat.objects.filter(salon=request.salon).select_related('kiritgan')
        if request.user.rol != Xodim.Rol.RAHBAR:
            qs = qs.filter(kiritgan=request.user)
        if request.query_params.get('holat'):
            qs = qs.filter(holat=request.query_params['holat'])
        oy = request.query_params.get('oy', '')
        if len(oy) == 7 and oy[:4].isdigit() and oy[5:].isdigit():
            qs = qs.filter(sana__year=int(oy[:4]), sana__month=int(oy[5:]))
        nomlar = modda_nomlari(request.salon)
        return Response([xarajat_json(x, nomlar) for x in qs.order_by('-sana', '-id')[:200]])

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        ser = XarajatSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            from apps.tenants.views_filial import joriy_filial
            x = xarajat_kiritish(salon=request.salon, xodim=request.user, filial=joriy_filial(request), **ser.validated_data)
        except (XarajatXatosi, KassaXatosi) as e:
            return Response({'detail': str(e)}, status=409)
        return Response(xarajat_json(x), status=201)


class XarajatView(APIView):
    """PATCH — rahbar kiritilgan xarajatni tuzatadi; DELETE — bekor qiladi (yozuv «rad etildi» bo'lib qoladi)."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def _xarajat(self, request, pk):
        x = Xarajat.objects.filter(salon=request.salon, id=pk).first()
        if not x:
            raise NotFound('Xarajat topilmadi.')
        return x

    def patch(self, request, pk):
        class S(serializers.Serializer):
            modda = serializers.CharField(max_length=12, required=False)
            summa = serializers.IntegerField(min_value=1, required=False)
            sana = serializers.DateField(required=False)
            izoh = serializers.CharField(max_length=300, required=False, allow_blank=True)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            x = xarajatni_tuzatish(salon=request.salon, rahbar=request.user, xarajat=self._xarajat(request, pk),
                                   **ser.validated_data)
        except XarajatXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(xarajat_json(x))

    def delete(self, request, pk):
        try:
            x = xarajatni_bekor_qilish(salon=request.salon, rahbar=request.user, xarajat=self._xarajat(request, pk))
        except XarajatXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(xarajat_json(x))


class XarajatQarorView(APIView):
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request, pk):
        x = Xarajat.objects.filter(salon=request.salon, id=pk).first()
        if not x:
            raise NotFound('Xarajat topilmadi.')
        qaror = request.data.get('qaror')
        if qaror not in ('tasdiq', 'rad'):
            raise ValidationError({'qaror': "«tasdiq» yoki «rad» bo'lishi kerak."})
        try:
            summa = request.data.get('summa')
            if summa is not None and (isinstance(summa, bool) or not isinstance(summa, int)):
                raise ValidationError({'summa': 'Butun son kiriting.'})
            x = xarajat_qarori(salon=request.salon, rahbar=request.user, xarajat=x,
                               tasdiqlash=qaror == 'tasdiq', summa=summa)
        except XarajatXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(xarajat_json(x))


class FoydaZararView(APIView):
    """GET /api/hisobotlar/pnl/?oy=2026-10 — faqat rahbar (Ilova B)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        oy = request.query_params.get('oy') or timezone.localdate().strftime('%Y-%m')
        try:
            yil, m = (int(p) for p in oy.split('-'))
            date(yil, m, 1)
        except ValueError:
            raise ValidationError({'oy': 'YYYY-OY ko\'rinishida bo\'lishi kerak.'})
        filial = request.query_params.get('filial', '')
        filial = int(filial) if filial.isdigit() else None  # filial natijasi (umumiy xarajatlarsiz)
        return Response({**reports.foyda_zarar(request.salon, yil, m, filial=filial),
                         'yopilgan': oy_yopilgan(request.salon, yil, m),
                         'taqqos': reports.taqqoslash(request.salon, yil, m, filial)})


def _filial_param(request):
    filial = request.query_params.get('filial', '')
    return int(filial) if filial.isdigit() else None


def _davr_va_filtrlar(request, nomlar):
    """Hisobot so'rovidagi `dan`/`gacha` (standart: joriy oy) va raqamli filtrlar."""
    bugun = timezone.localdate()
    try:
        dan = date.fromisoformat(request.query_params.get('dan') or str(bugun.replace(day=1)))
        gacha = date.fromisoformat(request.query_params.get('gacha') or str(bugun))
    except ValueError:
        raise ValidationError({'dan': "Sana YYYY-OY-KUN ko'rinishida bo'lishi kerak."})
    if gacha < dan or (gacha - dan).days > 366:
        raise ValidationError({'gacha': "Davr noto'g'ri yoki 1 yildan uzun."})
    filtrlar = {}
    for nomi in nomlar:
        qiymat = request.query_params.get(nomi)
        if qiymat:
            if not qiymat.isdigit():
                raise ValidationError({nomi: "Noto'g'ri qiymat."})
            filtrlar[nomi] = int(qiymat)
    return dan, gacha, filtrlar


class HisobotTafsilotView(APIView):
    """GET /api/hisobotlar/h/<nom>/tafsilot/?kalit=&dan=&gacha= — qatorni tashkil qilgan zakazlar (FT-18.2)."""
    permission_classes = [IsRahbar]

    def get(self, request, nom):
        from .statistika import tafsilot
        dan, gacha, filtrlar = _davr_va_filtrlar(request, ('sotuvchi', 'filial'))  # HisobotView bilan bir xil
        natija = tafsilot(request.salon, nom, request.query_params.get('kalit', ''), dan, gacha, **filtrlar)
        if natija is None:
            raise ValidationError({'kalit': "Bu hisobot yoki qator uchun tafsilot yo'q."})
        return Response(natija)


class PnlTafsilotView(APIView):
    """GET /api/hisobotlar/pnl/tafsilot/?oy=2026-10&qator=tushum — qatorni tashkil qilgan yozuvlar (FT-18.2)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        oy = request.query_params.get('oy') or timezone.localdate().strftime('%Y-%m')
        try:
            yil, m = (int(p) for p in oy.split('-'))
            date(yil, m, 1)
        except ValueError:
            raise ValidationError({'oy': 'YYYY-OY ko\'rinishida bo\'lishi kerak.'})
        natija = reports.pnl_tafsilot(request.salon, yil, m, request.query_params.get('qator', ''), _filial_param(request))
        if natija is None:
            raise ValidationError({'qator': f"Quyidagilardan biri: {', '.join(reports.PNL_QATORLARI)}."})
        return Response(natija)


class BonusView(APIView):
    """GET /api/hisobotlar/bonus/?oy=2026-10 — har bir sotuvchi uchun tayyor summa (FT-15.1)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        oy = request.query_params.get('oy') or timezone.localdate().strftime('%Y-%m')
        try:
            yil, m = (int(p) for p in oy.split('-'))
            date(yil, m, 1)
        except ValueError:
            raise ValidationError({'oy': 'YYYY-OY ko\'rinishida bo\'lishi kerak.'})
        return Response(reports.sotuvchi_bonuslari(request.salon, yil, m))


class KutilayotganView(APIView):
    permission_classes = [IsRahbar]

    def get(self, request):
        try:
            sana = date.fromisoformat(request.query_params.get('sana') or str(timezone.localdate()))
        except ValueError:
            raise ValidationError({'sana': 'YYYY-OY-KUN ko\'rinishida bo\'lishi kerak.'})
        return Response(reports.kutilayotgan_daromad(request.salon, sana))


def _oy(qiymat):
    try:
        yil, m = (int(p) for p in str(qiymat).split('-'))
        date(yil, m, 1)
        return yil, m
    except (ValueError, TypeError):
        raise ValidationError({'oy': "YYYY-OY ko'rinishida bo'lishi kerak."})


class OyniYopishView(APIView):
    """FT-18.4: POST — oyni yopish, DELETE — qayta ochish, GET — yopilgan oylar. Faqat rahbar."""
    permission_classes = [IsRahbar]

    def get(self, request):
        return Response([{'oy': f'{y.yil}-{y.oy:02d}', 'yopilgan': y.yopilgan,
                          'yopgan': y.yopgan.ism if y.yopgan else None, 'sof_foyda': y.hisobot.get('sof_foyda')}
                         for y in YopilganOy.objects.filter(salon=request.salon).select_related('yopgan')])

    def _bajar(self, request, fn, qiymat):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        yil, m = _oy(qiymat)
        try:
            fn(salon=request.salon, rahbar=request.user, yil=yil, oy=m)
        except XarajatXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response({'oy': f'{yil}-{m:02d}', 'yopilgan': oy_yopilgan(request.salon, yil, m)})

    def post(self, request):
        return self._bajar(request, oyni_yopish, request.data.get('oy'))

    def delete(self, request):
        return self._bajar(request, oyni_ochish, request.query_params.get('oy'))


class HisobotlarRoyxatiView(APIView):
    """Mavjud hisobotlar (6.6). Faqat rahbar (FT-20.2)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        from .statistika import HISOBOTLAR, SARLAVHALAR
        from apps.tenants.models import sozlama
        yashirin = set() if sozlama(request.salon).qoplamagan_royxat else {'bosh-liboslar'}  # 4.16: yoq-o'ch
        return Response([{'kalit': 'pnl', 'sarlavha': 'Foyda va zarar (P&L)'}]
                        + [{'kalit': k, 'sarlavha': SARLAVHALAR[k]} for k in HISOBOTLAR if k not in yashirin])


class HisobotView(APIView):
    """GET /api/hisobotlar/h/<nom>/?dan=&gacha= — standart davr: joriy oy. Faqat sahifada ko'rsatiladi (FT-18.3)."""
    permission_classes = [IsRahbar]

    def get(self, request, nom):
        from .statistika import HISOBOTLAR
        fn = HISOBOTLAR.get(nom)
        if not fn:
            return Response({'detail': "Bunday hisobot yo'q."}, status=404)
        from .statistika import FILTRLAR
        # FT-20.1: faqat shu hisobotga tegishli filtrlar qo'llanadi
        dan, gacha, filtrlar = _davr_va_filtrlar(request, FILTRLAR.get(nom, ()))
        return Response({**fn(request.salon, dan, gacha, **filtrlar), 'dan': dan, 'gacha': gacha,
                         'filtrlar': list(FILTRLAR.get(nom, ()))})


class OylikQatorView(APIView):
    """GET /api/hisobotlar/oylik/ — oxirgi 12 oy tushumi va sof foydasi (dashbord grafigi, 6.5)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        b = timezone.localdate()
        return Response(reports.oylik_qator(request.salon, b.year, b.month, filial=_filial_param(request)))


class BankView(APIView):
    """FT-12.12: GET ?oy=YYYY-OY — tizim va bank ko'chirmasi farqi; POST — ko'chirma summasi va komissiyani kiritish."""
    permission_classes = [IsRahbar]

    def get(self, request):
        yil, m = _oy(request.query_params.get('oy') or timezone.localdate().strftime('%Y-%m'))
        return Response({'oy': f'{yil}-{m:02d}', 'usullar': bank_holati(request.salon, yil, m)})

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)

        class S(serializers.Serializer):
            oy = serializers.CharField()
            usul = serializers.ChoiceField(choices=['karta', 'click', 'payme'])
            kochirma_summa = serializers.IntegerField(min_value=0)
            komissiya = serializers.IntegerField(min_value=0, default=0)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        yil, m = _oy(d['oy'])
        try:
            bank_solishtirish(salon=request.salon, rahbar=request.user, yil=yil, oy=m, usul=d['usul'],
                              kochirma_summa=d['kochirma_summa'], komissiya=d['komissiya'])
        except XarajatXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response({'oy': f'{yil}-{m:02d}', 'usullar': bank_holati(request.salon, yil, m)})


class ModdalarView(APIView):
    """Xarajat moddalari (FT-13.1): GET — hamma xodim (forma uchun); POST — rahbar yangi modda qo'shadi."""

    def get_permissions(self):
        return [IsStaff()] if self.request.method == 'GET' else [IsRahbar(), SalonYozishRuxsati()]

    def get(self, request):
        from .moddalar import moddalar
        rahbar = request.user.rol == Xodim.Rol.RAHBAR
        return Response(moddalar(request.salon, faqat_faol=not (rahbar and request.query_params.get('hammasi') == '1')))

    def post(self, request):
        from .models import XarajatModdasi

        class S(serializers.Serializer):
            nomi = serializers.CharField(max_length=100)
            togridan = serializers.BooleanField(default=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        nomi = ser.validated_data['nomi'].strip()
        if XarajatModdasi.objects.filter(salon=request.salon, nomi__iexact=nomi).exists() or \
                nomi.lower() in [n.lower() for _k, n in Xarajat.Modda.choices]:
            return Response({'detail': 'Bunday modda bor.'}, status=409)
        m = XarajatModdasi.objects.create(salon=request.salon, nomi=nomi, togridan=ser.validated_data['togridan'])
        return Response({'kod': f'm{m.id}', 'id': m.id, 'nomi': m.nomi, 'togridan': m.togridan, 'standart': False, 'faol': True}, status=201)


class ModdaView(APIView):
    """Salon moddasini nofaol qilish yoki qayta yoqish. Turi (to'g'ridan-to'g'ri/operatsion) o'zgartirilmaydi —
    aks holda o'tgan oylar hisoboti o'zgarib ketadi."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def patch(self, request, pk):
        from .models import XarajatModdasi
        m = XarajatModdasi.objects.filter(salon=request.salon, id=pk).first()
        if not m:
            raise NotFound('Modda topilmadi.')
        if isinstance(request.data.get('faol'), bool):
            m.faol = request.data['faol']
            m.save(update_fields=['faol'])
        if isinstance(request.data.get('nomi'), str):  # nom o'zgarsa eski xarajatlar ham yangi nom bilan ko'rinadi
            nomi = request.data['nomi'].strip()[:100]
            if not nomi:
                raise ValidationError({'nomi': "Nom bo'sh bo'lmasin."})
            if XarajatModdasi.objects.filter(salon=request.salon, nomi__iexact=nomi).exclude(id=m.id).exists() or \
                    nomi.lower() in [n.lower() for _k, n in Xarajat.Modda.choices]:
                return Response({'detail': 'Bunday modda bor.'}, status=409)
            m.nomi = nomi
            m.save(update_fields=['nomi'])
        return Response({'kod': f'm{m.id}', 'id': m.id, 'nomi': m.nomi, 'togridan': m.togridan, 'standart': False, 'faol': m.faol})


def _doimiy_json(d, nomlar):
    return {'id': d.id, 'modda': d.modda, 'modda_nomi': nomlar.get(d.modda, d.modda), 'summa': d.summa, 'izoh': d.izoh,
            'faol': d.faol, 'filial': d.filial_id}


class DoimiyXarajatlarView(APIView):
    """Doimiy oylik xarajatlar (FT-13.3): har oy avtomatik qoralama yaratiladi, rahbar tasdiqlaydi."""
    permission_classes = [IsRahbar]

    def get(self, request):
        from .moddalar import modda_nomlari
        from .models import DoimiyXarajat
        nomlar = modda_nomlari(request.salon)
        return Response([_doimiy_json(d, nomlar) for d in DoimiyXarajat.objects.filter(salon=request.salon)])

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        from apps.tenants.models import Filial

        from .moddalar import modda_bormi, modda_nomlari
        from .models import DoimiyXarajat

        class S(serializers.Serializer):
            modda = serializers.CharField(max_length=12)
            summa = serializers.IntegerField(min_value=1)
            izoh = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')
            filial = serializers.IntegerField(required=False, allow_null=True)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if not modda_bormi(request.salon, d['modda']):
            return Response({'detail': "Xarajat moddasi noto'g'ri."}, status=409)
        filial = None
        if d.get('filial'):
            filial = Filial.objects.filter(salon=request.salon, id=d['filial'], faol=True).first()
            if not filial:
                raise NotFound('Filial topilmadi.')
        x = DoimiyXarajat.objects.create(salon=request.salon, modda=d['modda'], summa=d['summa'], izoh=d['izoh'], filial=filial)
        return Response(_doimiy_json(x, modda_nomlari(request.salon)), status=201)


class DoimiyXarajatView(APIView):
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def patch(self, request, pk):
        from .moddalar import modda_nomlari
        from .models import DoimiyXarajat
        d = DoimiyXarajat.objects.filter(salon=request.salon, id=pk).first()
        if not d:
            raise NotFound('Topilmadi.')

        class S(serializers.Serializer):
            summa = serializers.IntegerField(min_value=1, required=False)
            izoh = serializers.CharField(max_length=300, required=False, allow_blank=True)
            faol = serializers.BooleanField(required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        for nom, qiymat in ser.validated_data.items():
            setattr(d, nom, qiymat)
        d.save()
        return Response(_doimiy_json(d, modda_nomlari(request.salon)))

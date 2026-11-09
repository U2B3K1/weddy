"""Mijozlar (ekran 14; FT-8.2, FT-8.3, FT-8.4; 7.4).

Mijozlarning to'liq ro'yxatini faqat rahbar ko'radi (Ilova B). Sotuvchi faqat qidiradi: telefon yoki ismning kamida
4 ta belgisi bilan, shunda u butun bazani varaqlab chiqa olmaydi. Ro'yxatni fayl qilib yuklab olish yo'q (7.4).
"""
from datetime import timedelta

from django.db.models import Count, F, Max, Min, Q, Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.models import Xodim, jurnalga_yoz
from apps.tenants.permissions import IsRahbar, IsStaff, SalonYozishRuxsati, yozish_taqiqi

from .models import Mijoz, Zakaz

OLCHAMLAR = ('kokrak', 'bel', 'son', 'boy', 'oyoq_olchami')
QIDIRUV_MIN = 4
DAVR = 30  # «yangi mijoz» va «yaqin to'y» — shuncha kun


def _qarzdor_q():
    """Libosni qaytargan, lekin jarima/zararni to'lamagan (Qarzdorlar ro'yxati bilan bir xil ta'rif)."""
    return Q(zakazlar__holat=Zakaz.Holat.QAYTARILDI, zakazlar__qaytarish_akti__qarz__gt=0)


def mijoz_filtri(qs, tur):
    """Rahbar ko'rsatkich kartalari filtri: yangi (birinchi zakazi oxirgi 30 kunda), toy (to'yi 30 kun ichida), qarzdor."""
    bugun = timezone.localdate()
    if tur == 'yangi':
        return qs.annotate(birinchi=Min('zakazlar__yaratilgan')).filter(birinchi__date__gte=bugun - timedelta(days=DAVR - 1))
    if tur == 'toy':
        return qs.filter(toy_sanasi__range=(bugun, bugun + timedelta(days=DAVR)))
    if tur == 'qarzdor':
        return qs.filter(id__in=Mijoz.objects.filter(_qarzdor_q()).values('id'))
    return qs


def mijoz_json(m, tolik=False):
    d = {'id': m.id, 'fio': m.fio, 'telefon': m.telefon, 'qora_royxat': m.qora_royxat, 'toy_sanasi': m.toy_sanasi,
         'zakazlar_soni': getattr(m, 'zakazlar_soni', None),
         # ro'yxat jadvali uchun: bekor qilinmagan zakazlar jami va oxirgi olib ketish sanasi
         'jami_summa': getattr(m, 'jami_summa', None) or 0, 'oxirgi_zakaz': getattr(m, 'oxirgi_zakaz', None)}
    if tolik:
        d.update({'qoshimcha_telefon': m.qoshimcha_telefon, 'toy_sanasi': m.toy_sanasi, 'manba': m.manba,
                  'qora_royxat_sabab': m.qora_royxat_sabab, 'izoh': m.izoh, 'kiyim_olchami': m.kiyim_olchami,
                  **{o: getattr(m, o) for o in OLCHAMLAR}})
    return d


def _oxirgi_va_qoldiq(mijoz_idlari):
    """Kanvas jadvali: har mijozning oxirgi zakazi (raqam, holat, libos) va to'lanmagan qoldig'i — sahifa uchun bitta so'rov."""
    from .views_royxat import TOLANGAN
    zs = (Zakaz.objects.filter(mijoz_id__in=mijoz_idlari).exclude(holat=Zakaz.Holat.BEKOR).annotate(tolangan_s=TOLANGAN)
          .prefetch_related('pozitsiyalar__libos').order_by('mijoz_id', '-olib_ketish', '-id'))
    oxirgi, qoldiq = {}, {}
    for z in zs:
        if z.mijoz_id not in oxirgi:
            poz = next(iter(z.pozitsiyalar.all()), None)
            oxirgi[z.mijoz_id] = {'id': z.id, 'raqam': z.raqam, 'holat': z.holat, 'olib_ketish': z.olib_ketish,
                                  'libos': poz.libos.nomi if poz else None}
        qoldiq[z.mijoz_id] = qoldiq.get(z.mijoz_id, 0) + max(0, z.jami - (z.tolangan_s or 0))
    return oxirgi, qoldiq


class MijozlarView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        rahbar = request.user.rol == Xodim.Rol.RAHBAR
        if not rahbar and len(q) < QIDIRUV_MIN:
            return Response({'detail': f"Qidirish uchun telefon yoki ismning kamida {QIDIRUV_MIN} ta belgisini kiriting."},
                            status=400)
        faol = ~Q(zakazlar__holat=Zakaz.Holat.BEKOR)
        qs = Mijoz.objects.filter(salon=request.salon).annotate(
            zakazlar_soni=Count('zakazlar', filter=faol), jami_summa=Sum('zakazlar__jami', filter=faol),
            oxirgi_zakaz=Max('zakazlar__olib_ketish', filter=faol))
        if q:
            qs = qs.filter(Q(telefon__icontains=q) | Q(fio__icontains=q) | Q(qoshimcha_telefon__icontains=q))
        if request.query_params.get('qora_royxat') == '1':
            qs = qs.filter(qora_royxat=True)
        if rahbar:
            qs = mijoz_filtri(qs, request.query_params.get('tur'))
        # B-32: tartib — oxirgi zakaz sanasi (jadvaldagi «Oxirgi zakaz» ustuni) bo'yicha, zakazsizlar oxirida
        qs = qs.order_by(F('oxirgi_zakaz').desc(nulls_last=True), 'fio', 'telefon')
        kesim = 50 if not rahbar else 200
        if request.query_params.get('sahifa'):  # {natija, jami}: «200 tadan ko'p» xabari va «Yana» uchun
            limit = _butun(request.query_params.get('limit'), kesim, 1, kesim)
            offset = _butun(request.query_params.get('offset'), 0)
            sahifa = list(qs[offset:offset + limit])
            oxirgi, qoldiq = _oxirgi_va_qoldiq([m.id for m in sahifa])
            return Response({'natija': [{**mijoz_json(m), 'oxirgi': oxirgi.get(m.id), 'qoldiq': qoldiq.get(m.id, 0)} for m in sahifa],
                             'jami': qs.count()})
        return Response([mijoz_json(m) for m in qs[:kesim]])


class MijozSonlariView(APIView):
    """GET /api/mijozlar/sonlar/ — Mijozlar sahifasidagi ko'rsatkich kartalari (faqat rahbar; sotuvchi ro'yxatni ko'rmaydi)."""
    permission_classes = [IsRahbar]

    def get(self, request):
        qs = Mijoz.objects.filter(salon=request.salon)
        qarz = (Zakaz.objects.filter(salon=request.salon, holat=Zakaz.Holat.QAYTARILDI, qaytarish_akti__qarz__gt=0)
                .aggregate(s=Sum('qaytarish_akti__qarz'))['s'] or 0)
        return Response({'jami': qs.count(), 'yangi': mijoz_filtri(qs, 'yangi').count(), 'toy': mijoz_filtri(qs, 'toy').count(),
                         'qarzdor': mijoz_filtri(qs, 'qarzdor').count(), 'qarz_jami': qarz,
                         'qora': qs.filter(qora_royxat=True).count(), 'davr': DAVR})


def _butun(qiymat, standart, kichik=0, katta=None):
    try:
        n = int(qiymat)
    except (TypeError, ValueError):
        return standart
    n = max(kichik, n)
    return min(n, katta) if katta is not None else n


MANBA_XATO = {'invalid_choice': "«{input}» — noma'lum manba. Ro'yxatdan tanlang."}


class MijozSerializer(serializers.Serializer):
    fio = serializers.CharField(max_length=200, required=False, allow_blank=True)
    qoshimcha_telefon = serializers.CharField(max_length=20, required=False, allow_blank=True)
    toy_sanasi = serializers.DateField(required=False, allow_null=True)
    # bo'sh qiymat — «ko'rsatilmagan» (B-12)
    manba = serializers.ChoiceField(choices=Mijoz.Manba.choices, required=False, allow_blank=True, error_messages=MANBA_XATO)
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
        from .views_royxat import TOLANGAN, _libos_rasmi
        tarix = (m.zakazlar.annotate(tolangan_s=TOLANGAN).prefetch_related('pozitsiyalar__libos__rasmlar')
                 .select_related('sotuvchi').order_by('-raqam')[:30])
        birinchi = m.zakazlar.order_by('yaratilgan').select_related('sotuvchi').first()

        def qator(z):
            poz = next(iter(z.pozitsiyalar.all()), None)
            tolangan = z.tolangan_s or 0
            # kanvas jadvali: libos surati va o'lchami, ijara muddati, to'langan va qoldiq
            return {'id': z.id, 'raqam': z.raqam, 'holat': z.holat, 'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish,
                    'jami': z.jami, 'tolangan': tolangan, 'qoldiq': 0 if z.holat == Zakaz.Holat.BEKOR else max(0, z.jami - tolangan),
                    'liboslar': [p.libos.nomi for p in z.pozitsiyalar.all()],
                    'olcham': poz.libos.olcham if poz else None, 'rasm': _libos_rasmi(request, poz.libos) if poz else None}
        return Response({**mijoz_json(m, tolik=True), 'tarix': [qator(z) for z in tarix],
                         # kanvas «Profil haqida»: qachon va kim qo'shgan (birinchi zakaz bo'yicha)
                         'qoshilgan': birinchi.yaratilgan if birinchi else None,
                         'qoshgan': birinchi.sotuvchi.ism if birinchi and birinchi.sotuvchi_id else None})

    def patch(self, request, pk):
        if (rad := yozish_taqiqi(request, self)):  # o'zbekcha sabab bilan (C-12)
            return rad
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

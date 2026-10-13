"""Filiallar (F1, FT-22.8): salon ichida bir nechta filial; soni tarif limiti bilan cheklanadi.

Birinchi versiya: filial — libos qayerda turgani, zakaz qayerda rasmiylashtirilgani va qurilma qaysi filialda ekanini
bildiradi. Kassa (smena) hozircha salon bo'yicha bitta.
"""
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Filial, IshonchliQurilma, jurnalga_yoz
from .permissions import IsRahbar, IsStaff, SalonYozishRuxsati


def joriy_filial(request):
    """So'rov kelgan qurilmaning filiali (qurilma filialga biriktirilmagan bo'lsa None)."""
    qid = getattr(request, 'qurilma_id', None)
    if not qid:
        return None
    q = IshonchliQurilma.objects.select_related('filial').filter(id=qid, salon=request.salon).first()
    return q.filial if q and q.filial_id and q.filial.faol else None


def filial_json(f):
    return {'id': f.id, 'nomi': f.nomi, 'manzil': f.manzil, 'faol': f.faol}


class FilialSerializer(serializers.Serializer):
    nomi = serializers.CharField(max_length=100)
    manzil = serializers.CharField(max_length=300, required=False, allow_blank=True)
    faol = serializers.BooleanField(required=False)


def _limit_xatosi(salon, qoshiladi=1):
    """Tarifdagi filiallar limiti (FT-22.8). Tarifsiz salon (demo) cheklanmaydi."""
    if salon.tarif_id is None:
        return None
    faol = Filial.objects.filter(salon=salon, faol=True).count()
    if faol + qoshiladi > salon.tarif.filial_limit:
        return Response({'detail': f"Tarif bo'yicha {salon.tarif.filial_limit} tadan ortiq filial ochib bo'lmaydi."}, status=409)
    return None


class FiliallarView(APIView):
    """GET — har bir xodim (filtr va tanlov uchun); POST — rahbar."""

    def get_permissions(self):
        return [IsStaff()] if self.request.method == 'GET' else [IsRahbar(), SalonYozishRuxsati()]

    def get(self, request):
        qs = Filial.objects.filter(salon=request.salon)
        if request.user.rol != 'rahbar' or request.query_params.get('hammasi') != '1':
            qs = qs.filter(faol=True)
        joriy = joriy_filial(request)
        return Response({'filiallar': [filial_json(f) for f in qs], 'joriy': joriy.id if joriy else None})

    def post(self, request):
        ser = FilialSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        xato = _limit_xatosi(request.salon)
        if xato:
            return xato
        d = ser.validated_data
        if Filial.objects.filter(salon=request.salon, nomi__iexact=d['nomi'].strip()).exists():
            return Response({'detail': 'Bunday nomli filial bor.'}, status=409)
        f = Filial.objects.create(salon=request.salon, nomi=d['nomi'].strip(), manzil=d.get('manzil', ''))
        jurnalga_yoz(request.salon, request.user, 'filial_qoshildi', f.nomi)
        return Response(filial_json(f), status=201)


class FilialView(APIView):
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def patch(self, request, pk):
        f = Filial.objects.filter(salon=request.salon, id=pk).first()
        if not f:
            raise NotFound('Filial topilmadi.')
        ser = FilialSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if d.get('faol') is True and not f.faol:
            xato = _limit_xatosi(request.salon)
            if xato:
                return xato
        if 'nomi' in d and Filial.objects.filter(salon=request.salon, nomi__iexact=d['nomi'].strip()).exclude(id=f.id).exists():
            return Response({'detail': 'Bunday nomli filial bor.'}, status=409)
        for nom, qiymat in d.items():
            setattr(f, nom, qiymat.strip() if nom == 'nomi' else qiymat)
        f.save()
        jurnalga_yoz(request.salon, request.user, 'filial_ozgardi', f.nomi, '', 'faol' if f.faol else 'nofaol')
        return Response(filial_json(f))

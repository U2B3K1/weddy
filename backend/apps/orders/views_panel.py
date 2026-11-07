"""Rahbar dashbordining ko'rsatkichlar paneli: kunlik tushum dinamikasi, eng ko'p ijaraga berilgan liboslar, yaqin bronlar,
liboslar holati va filiallar — bitta so'rovda (sahifa bir martada chiziladi).

Raqamlarning ta'rifi hisobotlar bilan bir xil: tushum — kassa usuli (`reports.foyda` dagi kabi: avans + qoldiq − mijozga
qaytarilgan − «kelmadi» o'tkazma), «yangi zakaz» — birinchi to'lovi davrda olingan zakaz. Taqqoslash halol: tanlangan davr
undan oldingi xuddi shuncha kun bilan solishtiriladi (oyning 7 kuni o'tgan oyning to'liq oyi bilan emas).
"""
from datetime import timedelta

from django.db.models import Count, Min, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cash.models import Tolov
from apps.catalog.models import Libos
from apps.finance import reports
from apps.tenants.permissions import IsRahbar

from .models import Mijoz, Zakaz, ZakazPozitsiya
from .views_royxat import _libos_rasmi

KUNLAR = (7, 30, 90)
# Ijara hisoblanadigan zakazlar: bron qilingan va undan keyingi holatlar (vaqtinchalik va bekor qilingan — yo'q)
IJARA_HOLATLARI = (Zakaz.Holat.BRON, Zakaz.Holat.BERILDI, Zakaz.Holat.QAYTARILDI, Zakaz.Holat.YOPILDI)
YAQIN_HOLATLAR = (Zakaz.Holat.VAQTINCHALIK, Zakaz.Holat.CHEGIRMA_KUTILMOQDA, Zakaz.Holat.BRON)


def _kunlik_tushum(salon, boshi, oxiri, filial):
    """Har kun uchun tushum (kassa usuli) — kunlar yig'indisi `reports.foyda(...)['tushum']` ga teng."""
    T = Tolov.Tur
    q = Tolov.objects.filter(reports.tolov_filiali(filial), salon=salon)
    kun = {}
    for r in (q.filter(vaqt__date__range=(boshi, oxiri)).annotate(k=TruncDate('vaqt')).values('k')
              .annotate(kirim=Sum('summa', filter=Q(tur__in=[T.AVANS, T.QOLDIQ])),
                        vozvrat=Sum('summa', filter=Q(tur=T.VOZVRAT)))):
        kun[r['k']] = (r['kirim'] or 0) - (r['vozvrat'] or 0)
    for r in (q.filter(tasdiq=Tolov.Tasdiq.KELMADI, tur__in=[T.AVANS, T.QOLDIQ], tasdiq_vaqti__date__range=(boshi, oxiri))
              .annotate(k=TruncDate('tasdiq_vaqti')).values('k').annotate(s=Sum('summa'))):
        kun[r['k']] = kun.get(r['k'], 0) - (r['s'] or 0)
    n = (oxiri - boshi).days + 1
    return [kun.get(boshi + timedelta(days=i), 0) for i in range(n)]


def _foiz(hozir, oldin):
    """O'zgarish foizi; oldingi davr 0 bo'lsa — None (foiz ma'nosiz, «yangi» deb ko'rsatiladi)."""
    return round((hozir - oldin) * 100 / oldin) if oldin else None


def _yangi_mijozlar(salon, boshi, oxiri, filial):
    """Birinchi zakazi shu davrda ochilgan mijozlar soni."""
    zf = Q(zakazlar__filial_id=filial) if filial else Q()
    return (Mijoz.objects.filter(zf, salon=salon).annotate(birinchi=Min('zakazlar__yaratilgan'))
            .filter(birinchi__date__range=(boshi, oxiri)).count())


class DashbordPanelView(APIView):
    """GET /api/dashbord/panel/?kun=7|30|90&filial= — rahbar bosh sahifasidagi ko'rsatkichlar va kartalar."""
    permission_classes = [IsRahbar]

    def get(self, request):
        salon, bugun = request.salon, timezone.localdate()
        try:
            kun = int(request.query_params.get('kun', 30))
        except ValueError:
            kun = 0
        if kun not in KUNLAR:
            raise ValidationError({'kun': "7, 30 yoki 90 bo'lishi kerak."})
        filial = request.query_params.get('filial', '')
        if filial:
            from apps.tenants.models import Filial
            if not filial.isdigit() or not Filial.objects.filter(salon=salon, id=int(filial)).exists():
                raise ValidationError({'filial': 'Filial topilmadi.'})
        filial = int(filial) if filial else None
        zf = {'filial_id': filial} if filial else {}

        boshi = bugun - timedelta(days=kun - 1)
        oldin_oxiri = boshi - timedelta(days=1)
        oldin_boshi = oldin_oxiri - timedelta(days=kun - 1)
        hozir_kunlar = _kunlik_tushum(salon, boshi, bugun, filial)
        oldin_kunlar = _kunlik_tushum(salon, oldin_boshi, oldin_oxiri, filial)
        hozir_f = reports.foyda(salon, boshi, bugun, filial)
        oldin_f = reports.foyda(salon, oldin_boshi, oldin_oxiri, filial)

        # Liboslar holati (faol liboslar): mijozda — berilgan zakazdagi, bo'sh — qolgan «bo'sh» holatdagilar
        from apps.catalog.views import mijozdagi_liboslar
        faol = Libos.objects.filter(salon=salon, holat__in=reports.FAOL_LIBOS_HOLATLARI, **zf)
        holatlar = dict(faol.values_list('holat').annotate(n=Count('id')))
        mijozda = len(mijozdagi_liboslar(salon.id, list(faol.values_list('id', flat=True))))
        tozalashda = holatlar.get(Libos.Holat.TOZALASHDA, 0)
        tamirda = holatlar.get(Libos.Holat.TAMIRDA, 0)
        bosh = max(0, holatlar.get(Libos.Holat.BOSH, 0) - mijozda)

        # Eng ko'p ijaraga berilgan liboslar (butun vaqt): necha zakazda bo'lgan va ijara narxi bo'yicha jami
        top = list(ZakazPozitsiya.objects.filter(salon=salon, zakaz__holat__in=IJARA_HOLATLARI,
                                                 **({'zakaz__filial_id': filial} if filial else {}))
                   .values('libos').annotate(n=Count('zakaz', distinct=True), s=Sum('narx')).order_by('-n', '-s')[:5])
        liboslar = {l.id: l for l in Libos.objects.filter(id__in=[t['libos'] for t in top]).prefetch_related('rasmlar')}
        top_liboslar = [{'id': t['libos'], 'artikul': liboslar[t['libos']].artikul, 'nomi': liboslar[t['libos']].nomi,
                         'ijara_narxi': liboslar[t['libos']].ijara_narxi, 'ijara_soni': t['n'], 'tushum': t['s'] or 0,
                         'rasm': _libos_rasmi(request, liboslar[t['libos']])} for t in top if t['libos'] in liboslar]

        # Yaqin bronlar: olib ketish bugundan boshlab, eng yaqini birinchi
        yaqin = (Zakaz.objects.filter(salon=salon, holat__in=YAQIN_HOLATLAR, olib_ketish__gte=bugun, **zf)
                 .select_related('mijoz').prefetch_related('pozitsiyalar__libos__rasmlar')
                 .annotate(tolangan_s=Sum('tolovlar__summa', filter=~Q(tolovlar__tasdiq=Tolov.Tasdiq.KELMADI) & Q(
                     tolovlar__tur__in=[Tolov.Tur.AVANS, Tolov.Tur.QOLDIQ]))).order_by('olib_ketish', 'raqam'))
        jami_yaqin = yaqin.count()
        bronlar = []
        for z in yaqin[:6]:
            poz = next(iter(z.pozitsiyalar.all()), None)
            bronlar.append({'id': z.id, 'raqam': z.raqam, 'holat': z.holat, 'mijoz': z.mijoz.fio or z.mijoz.telefon,
                            'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish, 'jami': z.jami,
                            'qoldiq': max(0, z.jami - (z.tolangan_s or 0)),
                            'libos': poz.libos.nomi if poz else None, 'rasm': _libos_rasmi(request, poz.libos) if poz else None})

        # Filiallar (faqat salon filiallarga bo'lingan bo'lsa va butun salon ko'rinishida)
        filiallar = []
        if not filial:
            from apps.tenants.models import Filial
            for f in Filial.objects.filter(salon=salon, faol=True).order_by('nomi'):
                h, o = reports.foyda(salon, boshi, bugun, f.id), reports.foyda(salon, oldin_boshi, oldin_oxiri, f.id)
                filiallar.append({'id': f.id, 'nomi': f.nomi, 'zakazlar': h['zakazlar_soni'], 'tushum': h['tushum'],
                                  'ozgarish_foiz': _foiz(h['tushum'], o['tushum'])})

        mijoz_q = Mijoz.objects.filter(salon=salon, **({'zakazlar__filial_id': filial} if filial else {})).distinct()
        yangi_m, oldin_m = (_yangi_mijozlar(salon, boshi, bugun, filial),
                            _yangi_mijozlar(salon, oldin_boshi, oldin_oxiri, filial))
        return Response({
            'kun': kun, 'dan': boshi, 'gacha': bugun, 'oldingi': {'dan': oldin_boshi, 'gacha': oldin_oxiri},
            'tushum': {'kunlar': [{'sana': boshi + timedelta(days=i), 'summa': s, 'oldingi': oldin_kunlar[i]}
                                  for i, s in enumerate(hozir_kunlar)],
                       'jami': hozir_f['tushum'], 'oldingi_jami': oldin_f['tushum'],
                       'ozgarish_foiz': _foiz(hozir_f['tushum'], oldin_f['tushum'])},
            'zakazlar': {'soni': hozir_f['zakazlar_soni'], 'oldingi': oldin_f['zakazlar_soni'],
                         'ozgarish_foiz': _foiz(hozir_f['zakazlar_soni'], oldin_f['zakazlar_soni'])},
            'mijozlar': {'jami': mijoz_q.count(), 'yangi': yangi_m, 'oldingi_yangi': oldin_m,
                         'ozgarish_foiz': _foiz(yangi_m, oldin_m)},
            'liboslar': {'jami': bosh + mijozda + tozalashda + tamirda, 'bosh': bosh, 'mijozda': mijozda,
                         'tozalashda': tozalashda, 'tamirda': tamirda},
            'top_liboslar': top_liboslar,
            'yaqin_bronlar': {'jami': jami_yaqin, 'royxat': bronlar},
            'filiallar': filiallar,
        })

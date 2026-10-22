"""Zakazni o'zgartirish va bekor qilish (4.17)."""
from django.db import transaction
from django.db.models import Min, Sum
from django.utils import timezone

from apps.bookings.models import AksessuarBron, Bron
from apps.bookings.services import BandlikXatosi, aksessuar_bron_qilish, bron_qilish
from apps.cash.models import Tolov
from apps.cash.services import tolangan_summa, tolov_qabul
from apps.catalog.models import Libos
from apps.tenants.models import Xodim, sozlama

from .models import ChegirmaSorovi, Zakaz, ZakazAksessuar, ZakazPozitsiya, ZakazTarixi
from .pricing import mavsumiy_foiz, narx_hisobla

# FT-17.4: standart qoida — (to'ygacha qolgan kun, avansdan qaytariladigan %), kattasidan kichigiga
STANDART_QOIDA = ((30, 100), (7, 50), (0, 0))

OZGARTIRILADI = (Zakaz.Holat.VAQTINCHALIK, Zakaz.Holat.CHEGIRMA_KUTILMOQDA, Zakaz.Holat.BRON)


class OzgartirishXatosi(Exception):
    pass


def qaytariladigan_foiz(qolgan_kun, qoida=STANDART_QOIDA):
    for chegara, foiz in qoida:
        if qolgan_kun >= chegara:
            return foiz
    return 0


RAHBARGA_XABAR = {'sana_kochirildi': "sanasi ko'chirildi", 'libos_almashtirildi': 'libosi almashtirildi',
                  'bekor_qilindi': 'bekor qilindi', 'avtomatik_bekor': "avtomatik bekor bo'ldi"}


def _log(zakaz, xodim, harakat, eski='', yangi='', sabab=''):
    ZakazTarixi.objects.create(salon=zakaz.salon, zakaz=zakaz, xodim=xodim, harakat=harakat,
                               eski=str(eski), yangi=str(yangi), sabab=sabab)
    if harakat in RAHBARGA_XABAR:  # FT-17.5: har bir o'zgartirish va bekor qilish haqida rahbarga xabar
        from apps.notify.services import rahbarlarga
        rahbarlarga(zakaz.salon, 'zakaz_ozgardi',
                    f"Zakaz #{zakaz.raqam} {RAHBARGA_XABAR[harakat]}"
                    f"{' (' + xodim.ism + ')' if xodim else ''}.\n{eski} → {yangi}"
                    f"{chr(10) + 'Sabab: ' + sabab if sabab else ''}")


def _ochiq_zakaz(salon, zakaz):
    zakaz = Zakaz.objects.select_for_update().get(id=zakaz.id, salon=salon)
    if zakaz.holat not in OZGARTIRILADI:
        raise OzgartirishXatosi(
            "«Berildi» holatidan keyin zakazni o'zgartirib yoki bekor qilib bo'lmaydi "
            "(faqat muddatidan oldin qaytarish mumkin).")
    return zakaz


def _qayta_hisobla(zakaz, xato=None):
    """Narxni qayta hisoblaydi va to'lov holatini moslaydi — ikkalasi doim birga, biri unutilib qolmasin."""
    asosiy = (sum(p.narx for p in zakaz.pozitsiyalar.all())
              + sum(a.narx for a in zakaz.aksessuarlar.all()) + zakaz.xizmatlar)
    h = narx_hisobla(asosiy, zakaz.ustama_foiz, chegirma=zakaz.chegirma)
    zakaz.asosiy_narx, zakaz.ustama, zakaz.chegirma, zakaz.jami = (
        h['asosiy_narx'], h['ustama'], h['chegirma'], h['jami'])
    zakaz.promokod_chegirma = min(zakaz.promokod_chegirma, zakaz.chegirma)
    tolov_holatini_mosla(zakaz, xato)


def tolov_holatini_mosla(zakaz, xato=None):
    """Narx o'zgargach to'lov holati (6.1). `_qayta_hisobla` oxirida chaqiriladi.

    To'langan summa jamidan oshsa — amal to'xtatiladi (ortiqcha pul jimgina qolib ketmasin). Qoldiq paydo bo'lsa
    `tolangan_sana` tozalanadi (qoldiq to'langach daromad qayta tan olinadi); narx tushib to'langan summaga
    tenglashsa — zakaz bugun to'liq to'langan hisoblanadi (aks holda daromadga hech qachon kirmasdi).
    """
    tolangan = tolangan_summa(zakaz)
    if tolangan > zakaz.jami:
        raise (xato or OzgartirishXatosi)("To'langan summa yangi jamidan oshib ketadi. "
                                          "Avval zakazni bekor qilib, avansni qaytaring.")
    if zakaz.tolangan_sana and tolangan < zakaz.jami:
        from apps.finance.services import oy_yopilgan
        s = zakaz.tolangan_sana
        if oy_yopilgan(zakaz.salon_id, s.year, s.month):  # yopilgan oy tushumi jimgina o'zgarib qolmasin
            raise (xato or OzgartirishXatosi)(f"Zakaz {s:%m.%Y} da to'liq to'langan, u oy yopilgan: narxni oshirib bo'lmaydi.")
        zakaz.tolangan_sana = None
    elif not zakaz.tolangan_sana and tolangan and tolangan == zakaz.jami:
        zakaz.tolangan_sana = timezone.localdate()


def _bronlash(zakaz, xodim, olib_ketish, qaytarish):
    avans_bor = zakaz.holat == Zakaz.Holat.BRON
    for p in zakaz.pozitsiyalar.select_related('libos__kategoriya'):
        bron_qilish(salon=zakaz.salon, libos=p.libos, olib_ketish=olib_ketish, qaytarish=qaytarish,
                    xodim=xodim, avans_bor=avans_bor, zakaz=zakaz, qayta=True)
    # Aksessuarlar: har bir turdan shuncha dona yangi sanalarga qayta band qilinadi (boshqa dona chiqishi mumkin).
    # Narx zakazdagi narx bo'yicha qoladi — katalog narxi keyin o'zgargan bo'lsa ham, sana ko'chirish narxni o'zgartirmaydi.
    qatorlar = list(zakaz.aksessuarlar.select_related('dona__aksessuar__kategoriya'))
    zakaz.aksessuarlar.all().delete()
    narxlar = {}
    for q in qatorlar:
        narxlar.setdefault(q.dona.aksessuar, []).append(q.narx)
    for a, n in narxlar.items():
        for dona, narx in zip(aksessuar_bron_qilish(salon=zakaz.salon, aksessuar=a, soni=len(n), olib_ketish=olib_ketish,
                                                    qaytarish=qaytarish, avans_bor=avans_bor, zakaz=zakaz), n):
            ZakazAksessuar.objects.create(salon=zakaz.salon, zakaz=zakaz, dona=dona, narx=narx)


@transaction.atomic
def sanani_kochirish(*, salon, xodim, zakaz, olib_ketish, qaytarish, sabab=''):
    """Yangi sanalarga libos bo'sh bo'lsa zakaz ko'chadi, to'lovlar saqlanadi (FT-17.1).

    Band bo'lsa BandlikXatosi ko'tariladi va hamma narsa (eski bronlar ham) joyida qoladi.
    """
    zakaz = _ochiq_zakaz(salon, zakaz)
    if qaytarish < olib_ketish:
        raise OzgartirishXatosi("Qaytarish sanasi olib ketishdan oldin bo'lishi mumkin emas.")
    if olib_ketish < timezone.localdate():
        raise OzgartirishXatosi("O'tgan sanaga ko'chirib bo'lmaydi.")
    eski = f'{zakaz.olib_ketish} – {zakaz.qaytarish}'
    # Avanssiz bron muddati ko'chirishda uzaymaydi: aks holda har kuni ko'chirib libosni avanssiz ushlab turish mumkin (FT-2.5)
    eski_muddat = Bron.objects.filter(zakaz=zakaz, turi=Bron.Turi.VAQTINCHALIK).aggregate(m=Min('muddati'))['m']
    Bron.objects.filter(zakaz=zakaz).delete()  # o'z bronlari yangi sanalarni to'smasligi uchun
    AksessuarBron.objects.filter(zakaz=zakaz).delete()
    _bronlash(zakaz, xodim, olib_ketish, qaytarish)
    if eski_muddat:
        Bron.objects.filter(zakaz=zakaz, turi=Bron.Turi.VAQTINCHALIK).update(muddati=eski_muddat)
        AksessuarBron.objects.filter(zakaz=zakaz, turi=Bron.Turi.VAQTINCHALIK).update(muddati=eski_muddat)
    zakaz.olib_ketish, zakaz.qaytarish = olib_ketish, qaytarish
    if sozlama(salon).mavsumiy_narx:  # FT-17.1: mavsumiy ustama yangi sanaga qarab qayta hisoblanadi
        zakaz.ustama_foiz = mavsumiy_foiz(salon, olib_ketish)
    _qayta_hisobla(zakaz)
    zakaz.save()
    _log(zakaz, xodim, 'sana_kochirildi', eski, f'{olib_ketish} – {qaytarish}', sabab)
    return zakaz


@transaction.atomic
def libosni_almashtirish(*, salon, xodim, zakaz, eski_libos, yangi_libos, sabab=''):
    """Narx farqi jamiga qo'shiladi yoki qoldiq to'lovdan ayiriladi (FT-17.2)."""
    zakaz = _ochiq_zakaz(salon, zakaz)
    poz = zakaz.pozitsiyalar.select_related('libos').filter(libos_id=eski_libos.id).first()
    if not poz:
        raise OzgartirishXatosi('Bu libos zakazda yo\'q.')
    yangi = Libos.objects.select_related('kategoriya').filter(salon=salon, id=yangi_libos.id).first()
    if not yangi:
        raise OzgartirishXatosi('Yangi libos topilmadi.')
    if zakaz.pozitsiyalar.filter(libos=yangi).exists():
        raise OzgartirishXatosi('Bu libos zakazda allaqachon bor.')

    Bron.objects.filter(zakaz=zakaz, libos=poz.libos).delete()
    avans_bor = zakaz.holat == Zakaz.Holat.BRON
    bron_qilish(salon=salon, libos=yangi, olib_ketish=zakaz.olib_ketish, qaytarish=zakaz.qaytarish,
                xodim=xodim, avans_bor=avans_bor, zakaz=zakaz)
    poz.libos, poz.narx, poz.zalog = yangi, yangi.ijara_narxi, yangi.zalog
    poz.save()
    eski_jami = zakaz.jami
    _qayta_hisobla(zakaz)  # qimmatroq libos: qoldiq paydo bo'lsa daromad sanasi tozalanadi
    zakaz.save()
    _log(zakaz, xodim, 'libos_almashtirildi', f'{eski_libos.artikul} (jami {eski_jami})',
         f'{yangi.artikul} (jami {zakaz.jami})', sabab)
    return zakaz


@transaction.atomic
def zakazni_bekor_qilish(*, salon, xodim, zakaz, sabab, qaytariladigan_foiz_override=None,
                         qoida=None, usul=Tolov.Usul.NAQD):
    """Avansning qaytariladigan qismi olib ketishgacha qolgan kunga qarab hisoblanadi (FT-17.3).

    Qaytarilmagan qism «boshqa daromad»ga yoziladi. Libos shu sanalar uchun darhol bo'shaydi.
    Qoidadan tashqari foizni faqat rahbar belgilaydi (Ilova B).
    """
    if not sabab.strip():
        raise OzgartirishXatosi('Bekor qilish sababi majburiy.')
    zakaz = _ochiq_zakaz(salon, zakaz)
    if qoida is None:  # admin paneldagi qoida (FT-17.4)
        qoida = sozlama(salon).qaytarish_qoidasi
    qolgan = (zakaz.olib_ketish - timezone.localdate()).days
    foiz = qaytariladigan_foiz(qolgan, qoida)
    if qaytariladigan_foiz_override is not None:
        if xodim.rol != Xodim.Rol.RAHBAR:
            raise OzgartirishXatosi("Qoidadan tashqari qaytarishni faqat rahbar belgilaydi.")
        if not 0 <= qaytariladigan_foiz_override <= 100:
            raise OzgartirishXatosi("Foiz 0 dan 100 gacha bo'lishi kerak.")
        foiz = qaytariladigan_foiz_override

    # Qoida faqat avansga qo'llanadi (FT-17.3): oldindan to'langan qoldiq to'liq qaytariladi
    tolangan = tolangan_summa(zakaz)
    avans = zakaz.tolovlar.filter(tur=Tolov.Tur.AVANS).aggregate(s=Sum('summa'))['s'] or 0
    qaytariladi = avans * foiz // 100 + (tolangan - avans)
    if qaytariladi:
        tolov_qabul(salon=salon, xodim=xodim, tur=Tolov.Tur.VOZVRAT, summa=qaytariladi,
                    usul=usul, zakaz=zakaz, izoh=f'Zakaz #{zakaz.raqam} bekor qilindi')

    Bron.objects.filter(zakaz=zakaz).delete()  # libos darhol bo'shaydi
    AksessuarBron.objects.filter(zakaz=zakaz).delete()
    zakaz.promokod_ishlatilishlari.filter(bekor=False).update(bekor=True)  # FT-21.9: kod qayta bo'shaydi
    zakaz.chegirma_sorovlari.filter(holat=ChegirmaSorovi.Holat.KUTILMOQDA).update(
        holat=ChegirmaSorovi.Holat.RAD, rahbar_izohi='Zakaz bekor qilindi')
    eski_holat = zakaz.holat
    zakaz.holat, zakaz.bekor_sabab, zakaz.bekor_vaqti = Zakaz.Holat.BEKOR, sabab, timezone.now()
    zakaz.qaytarilgan_avans, zakaz.ushlab_qolingan_avans = qaytariladi, tolangan - qaytariladi
    zakaz.save()
    _log(zakaz, xodim, 'bekor_qilindi', eski_holat,
         f"to'langan {tolangan} (avans {avans}): qaytarildi {qaytariladi} (avansning {foiz}%), "
         f'ushlab qolindi {tolangan - qaytariladi}', sabab)
    return zakaz


@transaction.atomic
def zakazga_aksessuar_qoshish(*, salon, xodim, zakaz, aksessuar, soni=1):
    """Saqlangan zakazga aksessuar qo'shadi: donalar band qilinadi, narx jamiga qo'shiladi (FT-4.3)."""
    zakaz = _ochiq_zakaz(salon, zakaz)
    eski_jami = zakaz.jami
    for dona in aksessuar_bron_qilish(salon=salon, aksessuar=aksessuar, soni=soni, olib_ketish=zakaz.olib_ketish,
                                      qaytarish=zakaz.qaytarish, avans_bor=zakaz.holat == Zakaz.Holat.BRON,
                                      zakaz=zakaz):
        ZakazAksessuar.objects.create(salon=salon, zakaz=zakaz, dona=dona, narx=aksessuar.ijara_narxi)
    _qayta_hisobla(zakaz)
    zakaz.save()
    _log(zakaz, xodim, 'aksessuar_qoshildi', f'jami {eski_jami}', f'{aksessuar.nomi} × {soni} (jami {zakaz.jami})')
    return zakaz


@transaction.atomic
def zakazdan_aksessuarni_olish(*, salon, xodim, zakaz, qator_id, sabab=''):
    """Aksessuarni zakazdan olib tashlaydi: dona bo'shaydi, narx kamayadi."""
    zakaz = _ochiq_zakaz(salon, zakaz)
    qator = zakaz.aksessuarlar.select_related('dona__aksessuar').filter(id=qator_id).first()
    if not qator:
        raise OzgartirishXatosi("Bu aksessuar zakazda yo'q.")
    eski_jami = zakaz.jami
    AksessuarBron.objects.filter(zakaz=zakaz, dona=qator.dona).delete()
    nomi = f'{qator.dona.aksessuar.nomi} ({qator.dona.yorliq})'
    qator.delete()
    # «Bepul aksessuar» promokodi shu aksessuar uchun bo'lsa va zakazda u qolmasa — chegirma ham olib tashlanadi
    p = zakaz.promokod
    if (p and p.chegirma_turi == p.ChegirmaTuri.AKSESSUAR and p.aksessuar_id == qator.dona.aksessuar_id
            and not zakaz.aksessuarlar.filter(dona__aksessuar_id=p.aksessuar_id).exists()):
        zakaz.promokod_ishlatilishlari.filter(bekor=False).update(bekor=True)
        zakaz.chegirma = max(0, zakaz.chegirma - zakaz.promokod_chegirma)
        zakaz.promokod, zakaz.promokod_chegirma = None, 0
    _qayta_hisobla(zakaz)
    zakaz.save()
    _log(zakaz, xodim, 'aksessuar_olib_tashlandi', f'{nomi} (jami {eski_jami})', f'jami {zakaz.jami}', sabab)
    return zakaz


BRON_TUGADI_SABAB = 'Avans kiritilmadi: vaqtinchalik bron muddati tugadi'


@transaction.atomic
def muddati_otganlarni_bekor_qil(salon=None, zakaz_idlar=None):
    """Avanssiz bron muddati (standart 24 soat) o'tgan zakazlarni avtomatik bekor qiladi (FT-2.5, S04).

    Libos bo'shaydi, zakaz «Bekor qilingan» holatiga o'tadi, tarixga yoziladi. Bekor qilingan zakazlar sonini qaytaradi.
    `zakaz_idlar` berilsa — faqat shu zakazlar (bron_qilish muddati o'tgan bronni boshqa zakazga berishdan oldin chaqiradi).
    """
    if zakaz_idlar is None:
        muddati_otgan = Bron.objects.filter(turi=Bron.Turi.VAQTINCHALIK, muddati__lt=timezone.now(), zakaz__isnull=False)
        if salon is not None:
            muddati_otgan = muddati_otgan.filter(salon=salon)
        zakaz_idlar = set(muddati_otgan.values_list('zakaz_id', flat=True))
    soni = 0
    for zakaz in (Zakaz.objects.select_for_update()
                  .filter(id__in=zakaz_idlar, holat__in=[Zakaz.Holat.VAQTINCHALIK, Zakaz.Holat.CHEGIRMA_KUTILMOQDA])):
        if tolangan_summa(zakaz) > 0:
            continue  # pul olingan zakaz hech qachon o'zi bekor bo'lmaydi
        Bron.objects.filter(zakaz=zakaz).delete()
        AksessuarBron.objects.filter(zakaz=zakaz).delete()
        zakaz.promokod_ishlatilishlari.filter(bekor=False).update(bekor=True)
        zakaz.chegirma_sorovlari.filter(holat=ChegirmaSorovi.Holat.KUTILMOQDA).update(
            holat=ChegirmaSorovi.Holat.RAD, rahbar_izohi='Bron muddati tugadi')
        eski = zakaz.holat
        zakaz.holat, zakaz.bekor_sabab, zakaz.bekor_vaqti = Zakaz.Holat.BEKOR, BRON_TUGADI_SABAB, timezone.now()
        zakaz.save(update_fields=['holat', 'bekor_sabab', 'bekor_vaqti'])
        _log(zakaz, None, 'avtomatik_bekor', eski, Zakaz.Holat.BEKOR, BRON_TUGADI_SABAB)
        soni += 1
    return soni

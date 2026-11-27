"""Agent uchun salonning jonli ma'lumoti: savol beruvchining o'z saloni bazasidan, faqat kod hisoblagan faktlar.

Egasi qarori (2026-11-27): «15-zakazni nega bera olmayapman?» kabi savolga bot o'sha salonning zakazini ko'rib aniq
javob bersin. Qoidalar:
- Faqat murojaat qilgan xodimning o'z saloni (salon va xodim aniq, xodim shu salonniki) — boshqa salon ko'rinmaydi.
- Model bazaga o'zi so'rov yubormaydi: savoldagi zakaz raqamlari va savol beruvchining kassa holati shu yerda
  hisoblanadi, model faqat matnga aylantiradi.
- Yuborilmaydi: mijoz ismi va telefoni, garov hujjati raqami, tillo buyum tavsifi, boshqa xodimlar ismi.
"""
import re

from django.utils import timezone

ZAKAZ_MAKS = 3
_ZAKAZ = re.compile(r'(?:#|№)\s*(\d{1,7})\b'
                    r'|\b(\d{1,7})\s*-?\s*(?:raqamli\s+)?(?:zakaz|buyurtma|заказ)'
                    r'|(?:zakaz|buyurtma|заказ)\w*\s*(?:#|№|raqami?\s*)?(\d{1,7})\b', re.I)


def _som(n):
    return f'{n or 0:,}'.replace(',', ' ') + " so'm"


def zakaz_raqamlari(savol):
    """Savoldagi zakaz raqamlari (takrorsiz, ko'pi bilan `ZAKAZ_MAKS`): «#15», «15-zakaz», «zakaz 15», «buyurtma №15»."""
    raqamlar = []
    for m in _ZAKAZ.finditer(savol or ''):
        r = int(next(g for g in m.groups() if g))
        if r and r not in raqamlar:
            raqamlar.append(r)
    return raqamlar[:ZAKAZ_MAKS]


def _zakaz_matni(salon, raqam):
    from apps.bookings.models import Bron
    from apps.cash.models import Tolov
    from apps.cash.services import _bronlar_joyida, tolangan_summa
    from apps.orders.models import ChegirmaSorovi, Zakaz, Zalog
    z = Zakaz.objects.filter(salon=salon, raqam=raqam).select_related('mijoz').first()
    if not z:
        return f'Zakaz #{raqam}: bu salonda bunday raqamli zakaz yo\'q.'
    H = Zakaz.Holat
    qatorlar = [f'Zakaz #{z.raqam}:', f'- holati: {z.get_holat_display()}',
                f"- olib ketish: {z.olib_ketish:%d.%m.%Y}, qaytarish: {z.qaytarish:%d.%m.%Y}"]
    liboslar = [f"{p.libos.artikul} «{p.libos.nomi}» (libos holati: {p.libos.get_holat_display().lower()})"
                for p in z.pozitsiyalar.select_related('libos')]
    if liboslar:
        qatorlar.append('- liboslar: ' + '; '.join(liboslar))
    tolangan = tolangan_summa(z)
    qatorlar.append(f'- jami: {_som(z.jami)}, to\'langan: {_som(tolangan)}, qoldiq: {_som(max(z.jami - tolangan, 0))}')
    if z.holat not in (H.BEKOR, H.YOPILDI):
        kutilgan = z.tolovlar.filter(tasdiq=Tolov.Tasdiq.KUTILMOQDA)
        if kutilgan.exists():
            qatorlar.append(f"- rahbar «Keldi» deb tasdiqlashini kutayotgan o'tkazma: {kutilgan.count()} ta "
                            f"({_som(sum(kutilgan.values_list('summa', flat=True)))})")
        if ChegirmaSorovi.objects.filter(zakaz=z, holat=ChegirmaSorovi.Holat.KUTILMOQDA).exists():
            qatorlar.append("- chegirma so'rovi rahbar qarorini kutmoqda")
        garov = [f"{g.get_turi_display().lower()} ({g.get_holat_display().lower()})" for g in z.zaloglar.all()]
        qatorlar.append('- garov: ' + ('; '.join(garov) if garov else 'olinmagan'))
    if z.holat == H.VAQTINCHALIK:
        if not _bronlar_joyida(z):
            qatorlar.append('- avanssiz bron muddati o\'tib, libos (yoki aksessuar) boshqa zakazga berilgan')
        else:
            muddat = (Bron.objects.filter(zakaz=z, turi=Bron.Turi.VAQTINCHALIK, muddati__isnull=False)
                      .order_by('muddati').values_list('muddati', flat=True).first())
            if muddat:
                holat = "o'tgan" if muddat < timezone.now() else 'tugaydi'
                qatorlar.append(f"- avanssiz bron muddati: {timezone.localtime(muddat):%d.%m.%Y %H:%M} ({holat})")
    if z.mijoz.qora_royxat:
        qatorlar.append("- mijoz qora ro'yxatda")
    if z.holat == H.BEKOR and z.bekor_sabab:
        qatorlar.append(f'- bekor qilish sababi: {z.bekor_sabab[:200]}')
    return '\n'.join(qatorlar)


def _xodim_matni(salon, xodim):
    from apps.cash.models import KassaTopshirish
    from apps.cash.services import ochiq_smena, xodim_qoldigi, xodim_smenasi
    qatorlar = ['Savol beruvchining hozirgi holati:']
    smena = xodim_smenasi(salon, xodim)
    if smena:
        kassa = smena.filial.nomi if smena.filial_id else 'umumiy kassa'
        qatorlar.append(f'- ochiq smenada ishlayapti ({kassa}, {timezone.localtime(smena.ochilgan):%d.%m %H:%M} da ochilgan)')
        qatorlar.append(f"- uning qo'lidagi naqd (tizim bo'yicha): {_som(xodim_qoldigi(smena, xodim))}")
    else:
        qatorlar.append('- ochiq smenada emas; salonda ochiq smena: ' + ('bor' if ochiq_smena(salon) else "yo'q"))
    kut = KassaTopshirish.objects.filter(salon=salon, kimga=xodim, holat=KassaTopshirish.Holat.KUTILMOQDA)
    if kut.exists():
        qatorlar.append(f"- unga topshirilgan, qabul qilinishi kutilayotgan pul: {kut.count()} ta "
                        f"({_som(sum(kut.values_list('summa', flat=True)))})")
    if xodim.bloklangan_gacha and xodim.bloklangan_gacha > timezone.now():
        qatorlar.append(f'- PIN ko\'p marta xato kiritilgani uchun kirish {timezone.localtime(xodim.bloklangan_gacha):%H:%M} '
                        'gacha to\'xtatilgan')
    return '\n'.join(qatorlar)


def jonli_malumot(murojaat, savol):
    """Modelga beriladigan blok (bo'sh bo'lishi mumkin) va egaga ko'rsatiladigan qisqa izoh («zakaz #15, kassa holati»)."""
    salon, xodim = murojaat.salon, murojaat.xodim
    if not salon or not xodim or xodim.salon_id != salon.id:
        return '', ''
    raqamlar = zakaz_raqamlari(savol)
    bloklar = [_xodim_matni(salon, xodim)] + [_zakaz_matni(salon, r) for r in raqamlar]
    izoh = ', '.join([f'zakaz #{r}' for r in raqamlar] + ['kassa holati'])
    return ("Salon bazasidagi jonli ma'lumot (hozirgi holat, faqat shu salon):\n" + '\n\n'.join(bloklar) + '\n\n'), izoh

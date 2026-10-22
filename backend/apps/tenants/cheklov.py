"""Login parolini tanlab topishga qarshi cheklov — IP bo'yicha, akkaunt bo'yicha emas.

Avval 5 ta xatodan keyin salonning o'zi 15 daqiqaga bloklanardi: loginni bilgan istalgan kishi (sobiq xodim,
raqobatchi) xato parol terib, butun salonni kirolmaydigan qilib qo'ya olardi. Endi faqat xato terayotgan
IP to'xtatiladi: shu IP dan shu loginga 5 ta xato (15 daqiqa ichida) yoki istalgan loginlarga soatiga 30 ta xato —
oxirgi xatodan boshlab 15 daqiqa blok.
"""
import ipaddress
import random
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import KirishUrinishi

IP_JAMI_SOATIGA = 30  # bitta IP dan har xil loginlarni sinab chiqishga qarshi
LOGIN_TURLARI = ('salon', 'platforma', 'admin')  # qurilmadagi PIN ('qurilma_pin') salon bo'yicha alohida hisoblanadi


def mijoz_ip(request):
    """Mijoz IP manzili. Gunicorn faqat 127.0.0.1 da tinglaydi va oldida nginx turadi — `X-Real-IP` ni nginx o'zi
    qo'yadi. Sarlavhaga faqat so'rov loopback'dan kelganda ishoniladi, aks holda uni mijoz soxtalashtira olardi."""
    ip = request.META.get('REMOTE_ADDR') or '0.0.0.0'
    try:
        loopback = ipaddress.ip_address(ip).is_loopback
    except ValueError:
        loopback = False
    if loopback:
        haqiqiy = (request.META.get('HTTP_X_REAL_IP') or '').strip()
        try:
            ipaddress.ip_address(haqiqiy)
            return haqiqiy
        except ValueError:
            pass
    return ip


def _toplam_blokda(qs, soni, oyna, hozir):
    """Oxirgi `soni` ta xato `oyna` ichida terilgan bo'lsa — eng oxirgisidan boshlab 15 daqiqa blok."""
    vaqtlar = list(qs.order_by('-vaqt').values_list('vaqt', flat=True)[:soni])
    return (len(vaqtlar) == soni and vaqtlar[0] - vaqtlar[-1] <= oyna
            and vaqtlar[0] > hozir - timedelta(minutes=settings.PIN_LOCK_MINUTES))


def bloklanganmi(request, tur, login):
    """5-xatodan keyin shu IP shu loginga 15 daqiqa kira olmaydi; blok paytidagi urinishlar yozilmaydi,
    ya'ni muddat uzaymaydi. Istalgan loginlarga soatiga 30 ta xato — IP butunlay 15 daqiqaga."""
    ip, hozir = mijoz_ip(request), timezone.now()
    qs = KirishUrinishi.objects.filter(ip=ip)
    return (_toplam_blokda(qs.filter(tur=tur, login=login), settings.PIN_MAX_ATTEMPTS,
                           timedelta(minutes=settings.PIN_LOCK_MINUTES), hozir)
            or _toplam_blokda(qs.filter(tur__in=LOGIN_TURLARI), IP_JAMI_SOATIGA, timedelta(hours=1), hozir))


def sutkalik_oshdimi(tur, kalit, soni):
    """IP dan qat'i nazar `kalit` bo'yicha oxirgi sutkadagi xatolar `soni` ga yetdimi (qurilmadagi PIN — salon bo'yicha)."""
    return KirishUrinishi.objects.filter(tur=tur, login=kalit, vaqt__gt=timezone.now() - timedelta(days=1))[:soni].count() >= soni


def xato_yoz(request, tur, login):
    if random.random() < 0.02:  # eski qatorlarni vaqti-vaqti bilan tozalash — har xatoda emas
        KirishUrinishi.objects.filter(vaqt__lt=timezone.now() - timedelta(days=1)).delete()
    KirishUrinishi.objects.create(tur=tur, login=login[:150], ip=mijoz_ip(request))


def tozala(request, tur, login):
    """Muvaffaqiyatli kirish — shu IP ning shu logindagi xatolari unutiladi."""
    KirishUrinishi.objects.filter(tur=tur, login=login, ip=mijoz_ip(request)).delete()


def admin_kirish(asl_login):
    """Django admin (`/adminaka/`) login sahifasiga ham xuddi shu IP cheklovi."""
    from django.http import HttpResponse

    def login(request, extra_context=None):
        if request.method != 'POST':
            return asl_login(request, extra_context)
        nomi = request.POST.get('username', '')
        if bloklanganmi(request, 'admin', nomi):
            return HttpResponse("Parol ko'p marta xato kiritildi: kirish 15 daqiqaga to'xtatildi.", status=429)
        javob = asl_login(request, extra_context)
        (tozala if request.user.is_authenticated else xato_yoz)(request, 'admin', nomi)
        return javob
    return login

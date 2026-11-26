"""Telegram ichidagi kichik ilova (Mini App): «Bugun», «Sozlamalar», «To'lov» — botdagi xabarlarning chiroyli ko'rinishi.

Kirish Telegramning o'zi orqali: ilova ochilganda Telegram `initData` beradi (foydalanuvchi id si + bot tokeni bilan
imzo). Server imzoni tekshiradi va akkauntni botdagi kabi aniqlaydi (`bot_menyu.xodimlar`). Bu yerda faqat bot shu
akkauntga baribir ko'rsatadigan narsalar bor: xodim tokeni berilmaydi, zakaz, kassa va to'lov kiritish yo'q — ular
asosiy ilovada ishonchli qurilma va PIN bilan himoyalangan.
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied
from rest_framework.response import Response

from apps.tenants.models import Xodim, platforma_sozlama
from apps.tenants.views import OchiqView

from . import bot_menyu, telegram
from .services import som

INITDATA_MUDDATI = 24 * 3600  # soniya: ilova ochilgandan keyin imzo shuncha vaqt yaroqli
R = Xodim.Rol.RAHBAR


def initdata_tekshir(init_data, token, hozir=None):
    """Telegram imzosini tekshiradi (core.telegram.org/bots/webapps — «Validating data») → foydalanuvchi id si yoki None."""
    if not init_data or not token or len(init_data) > 4096:
        return None
    try:
        juftlar = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    imzo = juftlar.pop('hash', '')
    tekst = '\n'.join(f'{k}={v}' for k, v in sorted(juftlar.items()))
    kalit = hmac.new(b'WebAppData', token.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(hmac.new(kalit, tekst.encode(), hashlib.sha256).hexdigest().encode(), imzo.encode()):
        return None
    hozir = hozir or time.time()
    try:
        vaqt = int(juftlar.get('auth_date', ''))
        uid = int(json.loads(juftlar.get('user', '')).get('id'))
    except (ValueError, TypeError, AttributeError):
        return None
    if not (hozir - INITDATA_MUDDATI <= vaqt <= hozir + 60):
        return None
    return uid


def foydalanuvchi(request):
    """`Authorization: tma <initData>` → Telegram foydalanuvchi id si. Akademiya manzilida ishlamaydi."""
    from apps.akademiya.host import akademiya_hostmi
    if akademiya_hostmi(request):
        raise NotFound()
    sarlavha = request.headers.get('Authorization', '')
    uid = initdata_tekshir(sarlavha[4:], telegram.token_ol()) if sarlavha.startswith('tma ') else None
    if uid is None:
        raise AuthenticationFailed("Ilovani Telegram ichidan qayta oching.")
    return uid


def _xodim(uid, xodim_id):
    x = next((x for x in bot_menyu.xodimlar(uid) if str(x.id) == str(xodim_id)), None)
    if x is None:
        raise PermissionDenied("Bu amal sizga ruxsat etilmagan.")
    return x


def _tolov(x):
    from .vidjet import tolov_malumot
    malumot = platforma_sozlama().tolov_malumoti.strip()
    kutilmoqda, oxirgi = bot_menyu.tolov_holati(x.salon)
    d = json.loads(tolov_malumot(x, malumot, oxirgi, kutilmoqda))
    d['bor'] = bool(malumot)  # to'lov ma'lumoti kiritilmagan bo'lsa ilova «egasi bilan bog'laning» deydi
    return d


def xodim_holati(x):
    """Bitta salon uchun ilova ko'radigan hamma narsa. Kalitlar vidjetlardagi bilan bir xil (vidjet.py)."""
    from .vidjet import bugun_malumot, sozlama_malumot
    rahbar = x.rol == R
    return {'id': x.id, 'ism': x.ism, 'rol': x.rol, 'salon': x.salon.nomi, 'salon_id': x.salon_id,
            'bugun': json.loads(bugun_malumot(x.salon, x.id)) if rahbar else None,
            'kun': None if rahbar else bot_menyu.bugun_xabari(x)[0],  # sotuvchi/kassir: botdagi «Bugun» matni
            'sozlama': json.loads(sozlama_malumot(x)),
            'tolov': _tolov(x) if rahbar else None}


class TgHolatView(OchiqView):
    """GET — shu Telegram akkauntiga ulangan salonlar va har birining holati."""
    def get(self, request):
        uid = foydalanuvchi(request)
        ega = bot_menyu.egami(uid)
        return Response({'xodimlar': [xodim_holati(x) for x in bot_menyu.xodimlar(uid)],
                         'ega': ega, 'platforma': platforma_holati() if ega else None})


class TgSozlamaView(OchiqView):
    """POST {xodim, bolim, qiymat} — botdagi sozlama tugmasi bilan bir xil tekshiriladi va saqlanadi."""
    def post(self, request):
        uid = foydalanuvchi(request)
        x = _xodim(uid, request.data.get('xodim'))
        bolim, qiymat = str(request.data.get('bolim', '')), str(request.data.get('qiymat', ''))
        if not bolim or not qiymat or ':' in bolim + qiymat:
            raise PermissionDenied("Bu amal sizga ruxsat etilmagan.")
        javob, sahifa, _ = bot_menyu.sozlama_tugma(uid, f's:{x.id}:{bolim}:{qiymat}')
        if sahifa is None:
            raise PermissionDenied(javob)
        x.refresh_from_db()
        from .vidjet import sozlama_malumot
        return Response({'javob': javob, 'sozlama': json.loads(sozlama_malumot(x))})


class TgTolovView(OchiqView):
    """POST {xodim, amal: 'chek'} — bot chatda chek rasmini so'raydi (rasm yoki PDF chatda yuboriladi, egaga boradi)."""
    def post(self, request):
        uid = foydalanuvchi(request)
        x = _xodim(uid, request.data.get('xodim'))
        if x.rol != R:
            raise PermissionDenied("Bu amal faqat salon rahbariga ruxsat etilgan.")
        if request.data.get('amal') != 'chek':  # «To'ladim (cheksiz)» olib tashlangan — to'lov faqat chek bilan
            raise PermissionDenied("Noma'lum amal.")
        ((matn, belgi),) = bot_menyu.chek_tugma(uid, f'tc:{x.id}')
        if not _chatga(uid, matn, belgi):
            return Response({'detail': "Bot xabar yubora olmadi. Birozdan keyin qayta urinib ko'ring."}, status=503)
        return Response({'javob': "Chatga qayting: bot chek rasmini so'radi."})


class TgYordamView(OchiqView):
    """POST {xodim?} — qo'llab-quvvatlash: botdagi «/yordam» bilan bir xil rejim yoqiladi, savol chatda yoziladi
    (matn, skrinshot, ovozli xabar) va platforma egasiga boradi; javob ham shu chatga keladi."""
    def post(self, request):
        from . import yordam
        uid = foydalanuvchi(request)
        if bot_menyu.egami(uid):
            raise PermissionDenied("Siz platforma egasisiz: murojaatlar sizga keladi.")
        xid = request.data.get('xodim')
        x = _xodim(uid, xid) if xid else None
        ((matn, _),) = yordam.boshlash(uid, x)
        if matn != yordam.SAVOL_MATNI:  # ega manzili yo'q va h.k.
            return Response({'detail': matn}, status=503)
        if not _chatga(uid, matn):
            yordam.tugat(uid)
            return Response({'detail': "Bot xabar yubora olmadi. Birozdan keyin qayta urinib ko'ring."}, status=503)
        return Response({'javob': "Chatga qayting va savolingizni yozing."})


def _chatga(uid, matn, belgi=None):
    try:
        telegram.api('sendMessage', chat_id=uid, text=matn, **({'reply_markup': belgi} if belgi else {}))
        return True
    except telegram.TelegramXatosi:
        return False


# ---------- platforma egasi ----------

def _sana(d):
    return f'{timezone.localtime(d):%d.%m.%Y %H:%M}' if d else ''


def salon_holati(s, bugun):
    """Salon kartasi: holat, obuna, tarif, rahbarlar, oxirgi to'lov va to'lov kiritish takliflari (1/3/6/12 oy)."""
    from apps.tenants import obuna
    from apps.tenants.models import ObunaTolovi
    muddat = s.obuna_muddati()
    oxirgi = ObunaTolovi.objects.filter(salon=s, holat=ObunaTolovi.Holat.QABUL).order_by('-qaror_vaqt').first()
    return {
        'id': s.id, 'nomi': s.nomi, 'holat': s.holat, 'holat_nomi': s.get_holat_display(),
        'obuna': bot_menyu.obuna_holati_matni(s, bugun), 'qolgan': (muddat - bugun).days if muddat else None,
        'tarif': s.tarif.nomi if s.tarif_id else '', 'narx': s.tarif.oylik_narx if s.tarif_id else 0,
        'rahbarlar': [{'ism': x.ism, 'tg': bool(x.telegram_id)}
                      for x in Xodim.objects.filter(salon=s, rol=R, faol=True).order_by('id')[:3]],
        'telefon': s.rahbar_telefon, 'xodimlar': Xodim.objects.filter(salon=s, faol=True).count(),
        'oxirgi': (f"{timezone.localtime(oxirgi.qaror_vaqt):%d.%m.%Y} — {oxirgi.oylar} oy"
                   + (f', {som(oxirgi.summa)}' if oxirgi.summa else '')) if oxirgi else '',
        'kutilmoqda': ObunaTolovi.objects.filter(salon=s, holat=ObunaTolovi.Holat.KUTILMOQDA).exists(),
        'kod': bot_menyu._muddat_kodi(s),  # tasdiq paytida obuna o'zgargan bo'lsa — ikki marta uzaymaydi
        'takliflar': [{'oy': oy, 'summa': obuna.standart_summa(s, oy), 'yangi': f'{obuna.keyingi_muddat(s, oy):%d.%m.%Y}'}
                      for oy in bot_menyu.TOLOV_OYLARI],
    }


def _holat():
    """Statistika paneli: fon vazifalari, zaxira nusxa, xabar navbati, bot tugmalari (30 kun)."""
    h = bot_menyu.holat_malumoti()
    return {'vazifalar': [{'nom': v['nom'], 'vaqt': _soat(v['vaqt']), 'toxtagan': v['toxtagan']} for v in h['vazifalar']],
            'zaxira': _sana(h['zaxira']), 'zaxira_eski': h['zaxira_eski'], 'navbat': h['navbat'], 'xato': h['xato'],
            'tugmalar': h['tugmalar'], 'muammo': h['muammo'], 'vaqt': _soat(h['hozir'])}


def _soat(d):
    """Bugun bo'lsa «14:32», aks holda «26.11 14:32»."""
    if not d:
        return ''
    d = timezone.localtime(d)
    return f'{d:%H:%M}' if d.date() == timezone.localdate() else f'{d:%d.%m %H:%M}'


def platforma_holati():
    """Ega ko'radigan hamma narsa: botdagi «🏢 Platforma» xabari va uning tugmalari ortidagi ma'lumot."""
    from datetime import timedelta

    from django.db.models import Sum

    from apps.tenants.models import Ariza, ObunaTolovi

    from . import yurak
    from .yordam import javobsizlar
    bugun = timezone.localdate()
    salonlar = list(bot_menyu._platforma_salonlari().select_related('tarif')[:bot_menyu.SALON_ROYXAT_MAKS])
    oy = ObunaTolovi.objects.filter(holat=ObunaTolovi.Holat.QABUL, qaror_vaqt__year=bugun.year,
                                    qaror_vaqt__month=bugun.month)
    kutayotgan = (ObunaTolovi.objects.filter(holat=ObunaTolovi.Holat.KUTILMOQDA)
                  .select_related('salon', 'xodim').order_by('id')[:10])
    arizalar = list(Ariza.objects.filter(korilgan=False).order_by('id')[:bot_menyu.ARIZA_MAKS])
    return {
        'toxtagan': [sarlavha for _, sarlavha, _, _ in yurak.toxtaganlar()],
        'holat': _holat(),
        'salonlar': [salon_holati(s, bugun) for s in salonlar],
        'yaqin': len(bot_menyu.obuna_qatorlari(bugun, bugun, bugun + timedelta(days=7))),
        'tugagan': len(bot_menyu.obuna_qatorlari(bugun, None, bugun - timedelta(days=1))),
        'oy_soni': oy.count(), 'oy_summa': oy.aggregate(s=Sum('summa'))['s'] or 0,
        'kutayotgan': [{'salon_id': t.salon_id, 'salon': t.salon.nomi, 'vaqt': _sana(t.yaratilgan),
                        'chek': bool(t.chek_fayl), 'xodim': t.xodim.ism if t.xodim_id else ''} for t in kutayotgan],
        'arizalar': [{'id': a.id, 'vaqt': _sana(a.yaratilgan), 'tur': a.get_tur_display(), 'ism': a.ism,
                      'telefon': a.telefon, 'salon': a.salon_nomi, 'xabar': a.xabar[:300]} for a in arizalar],
        'arizalar_soni': Ariza.objects.filter(korilgan=False).count(),
        'javobsiz': javobsizlar(),
        'tolov_malumoti': platforma_sozlama().tolov_malumoti,
    }


class TgEgaView(OchiqView):
    """POST {amal, ...} — faqat platforma egasi: obuna to'lovi kiritish, so'rovlarni ko'rildi qilish, to'lov ma'lumoti."""
    def post(self, request):
        uid = foydalanuvchi(request)
        if not bot_menyu.egami(uid):
            raise PermissionDenied("Bu amal faqat platforma egasiga ruxsat etilgan.")
        d, amal = request.data, request.data.get('amal')
        if amal == 'tolov':  # botdagi «✅ Ha, N oy kiritish» bilan bir xil: muddat kodi mos kelmasa — «tasdiq eskirgan»
            try:
                salon, oylar, kod = int(d.get('salon')), int(d.get('oylar')), int(d.get('kod'))
            except (TypeError, ValueError):
                raise PermissionDenied("Noma'lum amal.")
            ((javob, _),) = bot_menyu._tolov_kirit(salon, oylar, kod)
        elif amal == 'ariza_ok':
            from apps.tenants.models import Ariza
            gacha = str(d.get('gacha', ''))
            if not gacha.isdigit():
                raise PermissionDenied("Noma'lum amal.")
            n = Ariza.objects.filter(korilgan=False, id__lte=int(gacha)).update(korilgan=True)
            javob = f"{n} ta so'rov ko'rildi deb belgilandi."
        elif amal == 'tolov_malumoti':
            matn = str(d.get('matn') or '').strip()
            if matn:
                ((javob, _),) = bot_menyu.tolov_malumotini_saqla(matn)
                javob = 'Saqlandi' if javob.startswith('✅') else javob  # xato bo'lsa (juda uzun) — sababi
            else:
                s = platforma_sozlama()
                s.tolov_malumoti = ''
                s.save(update_fields=['tolov_malumoti'])
                javob = "To'lov ma'lumoti o'chirildi."
        else:
            raise PermissionDenied("Noma'lum amal.")
        return Response({'javob': javob, 'platforma': platforma_holati()})


def ilova_manzili():
    """Mini App manzili (https shart): asosiy sayt + `/tg`. Lokalda https yo'q — '' (menyu tugmasi qo'yilmaydi)."""
    from django.conf import settings
    sayt = next((o for o in settings.CORS_ALLOWED_ORIGINS if o.startswith('https://') and 'academy.' not in o), '')
    return f'{sayt}/tg' if sayt else ''


def menyu_tugmasi():
    """Chatdagi «Menu» tugmasi o'rniga «Libosa» — Telegram ichidagi ilovani ochadi (barcha chatlar uchun)."""
    manzil = ilova_manzili()
    if not manzil:
        return None
    return {'type': 'web_app', 'text': 'Libosa', 'web_app': {'url': manzil}}

"""Akademiya: bir martalik kirish, o'quv saloni, darsni boshlash va tekshirish."""
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from apps.cash.services import pul_oladimi
from apps.tenants.arxiv import salon_qatorlarini_ochir
from apps.tenants.models import Salon, SalonSozlamalari, Xodim, sozlama

from .darslar import BOBLAR, DARS, DARSLAR, PERSONAJLAR, REJA, YONALISHLAR, Muhit, daraja
from .darslar.asos import savol_json
from .models import DarsNatija, KirishKodi, Oquvchi, kod_xeshi

KOD_MUDDATI = timedelta(seconds=60)
ESKIRISH_KUN = 30  # shuncha kun ochilmagan o'quv saloni o'chiriladi (oquv_tozalash)
# Mehmon rejimi (kirmasdan sinab ko'rish): uchta ochiq dars, vaqtinchalik o'quv saloni
MEHMON_DARSLAR = ('S1', 'S4', 'S8')   # bo'sh libosni topish → zakaz yaratish → libosni topshirish
MEHMON_MUDDATI = timedelta(hours=24)  # shundan keyin mehmon saloni tozalashda o'chadi
MEHMON_CHEGARA = 300                  # bir vaqtda yashaydigan mehmon salonlari (suiiste'moldan himoya)

# O'quv salonidagi ikkinchi xodim — personaj: o'quvchi sotuvchi/kassir bo'lsa rahbar Nodira, rahbar bo'lsa sotuvchi Madina
PERSONAJ = {Xodim.Rol.RAHBAR: ('Madina', Xodim.Rol.SOTUVCHI)}
PERSONAJ_STANDART = ('Nodira', Xodim.Rol.RAHBAR)


# Darslar ketma-ket ochiladi: navbatdagi dars — bajarilmaganlarining birinchisi (boblar tartibida); bajarilgani doim ochiq.
# Testlar alohida darsni to'g'ridan-to'g'ri boshlashi uchun o'chirib qo'yadi.
KETMA_KET = True


class AkademiyaXatosi(Exception):
    pass


# ---------- kirish ----------

def havola_yarat(xodim):
    """Haqiqiy xodim uchun akademiyaga o'tish havolasi. Kod bir marta ishlaydi va bir daqiqada eskiradi.
    Kod manzilning `#` qismida: brauzer uni serverga yubormaydi, nginx jurnaliga tushmaydi."""
    KirishKodi.objects.filter(xodim=xodim).delete()
    kod = secrets.token_urlsafe(32)
    KirishKodi.objects.create(xesh=kod_xeshi(kod), xodim=xodim, tugaydi=timezone.now() + KOD_MUDDATI)
    return f'{settings.AKADEMIYA_URL}/#akademiya={kod}'


@transaction.atomic
def kirish(kod):
    """Kodni o'quv salonidagi xodimga almashtiradi. Kod noto'g'ri, eskirgan yoki ishlatilgan bo'lsa — xato."""
    k = (KirishKodi.objects.select_for_update().select_related('xodim__salon')
         .filter(xesh=kod_xeshi(kod or ''), tugaydi__gt=timezone.now()).first())
    if not k:
        raise AkademiyaXatosi("Havola eskirgan. Libosa ilovasidagi «Akademiya» tugmasini qayta bosing.")
    xodim = k.xodim
    k.delete()
    if not xodim.faol or xodim.salon.oquv or xodim.salon.holat == Salon.Holat.BLOKLANGAN:
        raise AkademiyaXatosi("Akademiyaga kirib bo'lmadi.")
    oquvchi, _ = Oquvchi.objects.select_for_update().get_or_create(xodim=xodim)
    oquv_salonni_tayyorla(oquvchi)
    oquvchi.oxirgi_kirish = timezone.now()
    oquvchi.save(update_fields=['oxirgi_kirish'])
    return oquvchi


@transaction.atomic
def mehmon_kirish():
    """Ro'yxatdan o'tmagan odam uchun vaqtinchalik o'quvchi va o'quv saloni. Haqiqiy salon bilan bog'lanmaydi."""
    if Oquvchi.objects.filter(mehmon=True).count() >= MEHMON_CHEGARA:
        # muddati o'tgan sinov salonlari tungi tozalashni kutib joy band qilib turmasin — shu yerning o'zida o'chadi
        muddati_otgan_mehmonlarni_ochir()
        if Oquvchi.objects.filter(mehmon=True).count() >= MEHMON_CHEGARA:
            raise AkademiyaXatosi("Hozir sinov salonlari band. Birozdan keyin qayta urinib ko'ring.")
    oquvchi = Oquvchi.objects.create(mehmon=True, oxirgi_kirish=timezone.now())
    oquv_salonni_tayyorla(oquvchi)
    return oquvchi


def _mos(oquvchi, d):
    """Dars shu o'quvchiga ochiqmi: roli va kassa rejimiga mos, mehmonga esa faqat ochiq darslar."""
    return d.mos(oquvchi.oquv_salon, oquvchi.oquv_xodim) and (not oquvchi.mehmon or d.kod in MEHMON_DARSLAR)


# ---------- o'quv saloni ----------

def oquv_salonni_tayyorla(oquvchi):
    """O'quv saloni yo'q bo'lsa yaratadi; bor bo'lsa o'quvchining ismi, roli va kassa rejimini haqiqiysiga moslaydi
    (rahbar xodimning rolini yoki kassa tartibini o'zgartirgan bo'lishi mumkin — darslar shunga qarab beriladi)."""
    haqiqiy = oquvchi.xodim
    # mehmonning haqiqiy xodimi yo'q: u o'quv salonida «Mehmon» ismli sotuvchi, ustozi — rahbar Nodira
    ism, rol = ('Mehmon', Xodim.Rol.SOTUVCHI) if oquvchi.mehmon else (haqiqiy.ism, haqiqiy.rol)
    salon, x = oquvchi.oquv_salon, oquvchi.oquv_xodim
    if salon is None or x is None:
        if salon is not None:  # yarim qolgan holat: boshidan
            oquv_salonni_ochir(salon)
        salon = Salon.objects.create(nomi="O'quv saloni", login=f'oquv-{uuid.uuid4().hex}', parol=make_password(None),
                                     holat=Salon.Holat.FAOL, oquv=True, boshlash_yopilgan=True)
        x = Xodim.objects.create(salon=salon, ism=ism, rol=rol, pin=make_password(None))
        p_ism, p_rol = PERSONAJ.get(rol, PERSONAJ_STANDART)
        Xodim.objects.create(salon=salon, ism=p_ism, rol=p_rol, pin=make_password(None))
        oquvchi.oquv_salon, oquvchi.oquv_xodim, oquvchi.joriy_dars, oquvchi.dars_holati = salon, x, '', {}
        oquvchi.save(update_fields=['oquv_salon', 'oquv_xodim', 'joriy_dars', 'dars_holati'])
    else:
        if (x.ism, x.rol) != (ism, rol):
            x.ism, x.rol = ism, rol
            x.save(update_fields=['ism', 'rol'])
        # Personaj (ikkinchi xodim) ham darslar kutgan holatga qaytariladi: o'quvchining roli o'zgargan bo'lishi mumkin
        # (sotuvchi rahbar bo'ldi — personaj endi sotuvchi Madina), yoki rahbar-o'quvchi uni darsda o'chirib, rolini
        # almashtirib qo'ygan. Aks holda urug'dagi «boshqa xodim qilgan» ishlar noto'g'ri rol nomidan yozilardi.
        p_ism, p_rol = PERSONAJ.get(rol, PERSONAJ_STANDART)
        p = Xodim.objects.filter(salon=salon).exclude(id=x.id).order_by('id').first()
        if p is None:
            Xodim.objects.create(salon=salon, ism=p_ism, rol=p_rol, pin=make_password(None))
        elif (p.ism, p.rol, p.faol) != (p_ism, p_rol, True):
            p.ism, p.rol, p.faol = p_ism, p_rol, True
            p.save(update_fields=['ism', 'rol', 'faol'])
    if oquvchi.mehmon:
        return salon  # mehmonda haqiqiy salon yo'q — kassa rejimi standart qoladi
    rejim = sozlama(haqiqiy.salon).kassa_rejimi
    s = sozlama(salon)
    if s.kassa_rejimi != rejim:
        s.kassa_rejimi = rejim
        s.save(update_fields=['kassa_rejimi'])
    return salon


def _fayllarni_ochir(fayllar):
    transaction.on_commit(lambda: [f.storage.delete(f.name) for f in fayllar])


@transaction.atomic
def oquv_salonni_tozala(salon):
    """Xodimlar va sozlamalardan boshqa hamma narsani o'chiradi — darsning boshlang'ich holati uchun toza salon."""
    if not salon.oquv:
        raise AkademiyaXatosi("Bu o'quv saloni emas.")  # haqiqiy salon hech qachon tozalanmaydi
    _fayllarni_ochir(salon_qatorlarini_ochir(salon, saqlanadi=(Xodim, SalonSozlamalari)))


@transaction.atomic
def oquv_salonni_ochir(salon):
    if not salon.oquv:
        raise AkademiyaXatosi("Bu o'quv saloni emas.")
    _fayllarni_ochir(salon_qatorlarini_ochir(salon))
    salon.delete()


def eskirganlarni_ochir(hozir=None):
    """Egasiz qolgan (xodim o'chirilgan) va uzoq ochilmagan o'quv salonlari hamda eskirgan kirish kodlari. Soni qaytadi."""
    hozir = hozir or timezone.now()
    KirishKodi.objects.filter(tugaydi__lt=hozir).delete()
    egali = Oquvchi.objects.filter(oquv_salon__isnull=False)
    eskilar = list(Salon.objects.filter(oquv=True).exclude(id__in=egali.values('oquv_salon_id')))
    for o in egali.filter(mehmon=False, oxirgi_kirish__lt=hozir - timedelta(days=ESKIRISH_KUN)).select_related('oquv_salon'):
        eskilar.append(o.oquv_salon)
    for salon in eskilar:
        oquv_salonni_ochir(salon)
    return len(eskilar) + muddati_otgan_mehmonlarni_ochir(hozir)


def muddati_otgan_mehmonlarni_ochir(hozir=None):
    """Mehmonlar: yaratilganiga bir sutka bo'lgan sinov saloni ham, o'quvchi yozuvi ham o'chadi. O'chirilgan salonlar soni."""
    hozir = hozir or timezone.now()
    mehmonlar = Oquvchi.objects.filter(mehmon=True, yaratilgan__lt=hozir - MEHMON_MUDDATI)
    salonlar = [o.oquv_salon for o in mehmonlar.filter(oquv_salon__isnull=False).select_related('oquv_salon')]
    for salon in salonlar:
        oquv_salonni_ochir(salon)
    mehmonlar.delete()
    return len(salonlar)


# ---------- darslar ----------

YORDAM = '_yordam'  # dars holatidagi kalit: shu urinishda ochilgan yordam darajasi (0 — ochilmagan)


def oquvchi_ol(xodim):
    """So'rov yuborgan o'quv xodimidan o'quvchini topadi."""
    o = Oquvchi.objects.select_related('oquv_salon', 'oquv_xodim').filter(oquv_xodim=xodim).first()
    if not o:
        raise AkademiyaXatosi("O'quvchi topilmadi. Libosa ilovasidagi «Akademiya» tugmasi orqali qayta kiring.")
    return o


def _qulfla(oquvchi):
    return Oquvchi.objects.select_for_update(of=('self',)).select_related('oquv_salon', 'oquv_xodim').get(id=oquvchi.id)


def _dars(oquvchi, kod):
    d = DARS.get(kod)
    if not d or not _mos(oquvchi, d):
        raise AkademiyaXatosi('Dars topilmadi.')
    return d


def _tartib(oquvchi):
    """Shu o'quvchining darslari o'tiladigan tartibda: boblar bo'yicha (bosh sahifadagi yo'l), bobga kirmagani — oxirida."""
    bobda = [DARS[k] for *_, kodlar in BOBLAR for k in kodlar if k in DARS]
    return [d for d in bobda + [x for x in DARSLAR if x not in bobda] if _mos(oquvchi, d)]


def _navbat(oquvchi, bajarilgan):
    """Navbatdagi dars — tartibdagi birinchi bajarilmagani (hammasi bajarilgan bo'lsa None)."""
    return next((d for d in _tartib(oquvchi) if d.kod not in bajarilgan), None)


def _bajarilganlar(oquvchi):
    return set(oquvchi.natijalar.filter(bajarilgan__isnull=False).values_list('dars', flat=True))


def _ochiqmi(oquvchi, d, bajarilgan):
    if not KETMA_KET or d.kod in bajarilgan:
        return True
    return _navbat(oquvchi, bajarilgan) == d


def _yordam(d, holat):
    """Ochilgan darajagacha bo'lgan yordam matnlari va yana daraja qolgan-qolmagani."""
    daraja = holat.get(YORDAM, 0)
    qadamlar = d.qadamlar(holat)
    mavjud = sum(1 for x in (d.ishora, qadamlar) if x)  # 1 — ishora, 2 — aniq qadamlar
    return {'daraja': daraja, 'ishora': d.ishora if daraja >= 1 else None,
            'qadamlar': qadamlar if daraja >= 2 else None, 'yana': daraja < mavjud}


def _joriy(d, holat):
    """Boshlangan darsning o'quvchiga ko'rinadigan qismi: topshiriq, savol (bo'lsa) va ochilgan yordam."""
    # savollar: bitta savolli dars (`savol`) ham ro'yxat bo'lib beriladi — panel ikkalasini bir xil ko'rsatadi
    savollar = savol_json(d.savollar(holat)) if d.savollar else ([d.savol(holat)] if d.savol else [])
    return {'topshiriq': d.topshiriq(holat), 'savollar': savollar, 'sahna': d.sahna(holat) if d.sahna else [],
            'bilim': d.bilim(holat) if d.bilim else [],
            'yordam': _yordam(d, holat), 'yol': d.yol(holat)}


def _ball(o, bajarilgan):
    """O'quvchining reytingdagi balli: (jami, darslar, haftalik). Kurs qayta boshlangan bo'lsa — rekord kabi: kattasi
    ko'rinadi; haftalik ballga faqat rekorddan oshgan qismi qo'shiladi (qayta o'tib, eski ballni ikkinchi marta yig'ib
    bo'lmaydi), qayta boshlash paytidagi haftalik ball esa yana 7 kun turadi."""
    hafta_boshi = timezone.now() - timedelta(days=7)
    joriy = sum(DARS[n.dars].xp for n in bajarilgan)
    hafta = sum(DARS[n.dars].xp for n in bajarilgan if n.bajarilgan >= hafta_boshi)
    yangi = max(0, joriy - max(o.rekord_xp, joriy - hafta))
    eski = o.rekord_hafta if o.rekord_vaqt and o.rekord_vaqt >= hafta_boshi else 0
    return max(o.rekord_xp, joriy), max(o.rekord_darslar, len(bajarilgan)), eski + yangi


def reyting(oquvchi):
    """Jamoa reytingi: o'quvchining HAQIQIY salonidagi hamkasblari (akademiyaga kirganlari) — shu haftada va jami
    to'plangan ball bo'yicha. Faqat ism, lavozim va ball beriladi. Tartib: haftalik ball, keyin jami ball, keyin ism."""
    if oquvchi.mehmon:
        return []  # mehmonning saloni ham, hamkasblari ham yo'q
    qatorlar = []
    hamkasblar = (Oquvchi.objects.filter(xodim__salon_id=oquvchi.xodim.salon_id, xodim__faol=True)
                  .select_related('xodim').prefetch_related('natijalar'))
    for o in hamkasblar:
        # rahbarning natijasi faqat o'ziga ko'rinadi — xodimlar ro'yxatida u yo'q
        if o.xodim.rol == Xodim.Rol.RAHBAR and o.id != oquvchi.id:
            continue
        xp, darslar, hafta = _ball(o, [n for n in o.natijalar.all() if n.bajarilgan and n.dars in DARS])
        qatorlar.append({'ism': o.xodim.ism, 'lavozim': o.xodim.get_rol_display(), 'darslar': darslar, 'xp': xp,
                         'hafta': hafta, 'men': o.id == oquvchi.id})
    qatorlar.sort(key=lambda q: (-q['hafta'], -q['xp'], q['ism']))
    return qatorlar


def darslar_royxati(oquvchi):
    """Bosqichlar xaritasi: yo'nalishlar bo'yicha guruhlangan, shu o'quvchiga mos darslar."""
    natijalar = {n.dars: n for n in oquvchi.natijalar.all()}
    bajarilganlar = {k for k, n in natijalar.items() if n.bajarilgan}
    guruhlar = {k: {'kalit': k, 'nomi': nomi, 'darslar': []} for k, nomi in YONALISHLAR}
    for d in DARSLAR:
        if not _mos(oquvchi, d):
            # Mehmon to'liq dasturni ko'radi (ega talabi, 2026-11-15): bepul bo'lmagan darslar ro'yxatda qulf bilan turadi,
            # bosilganda panel kirishni so'raydi. Boshlab bo'lmaydi (`_dars` rad etadi), mazmuni ham berilmaydi.
            if oquvchi.mehmon:
                guruhlar[d.yonalish]['darslar'].append({
                    'kod': d.kod, 'nomi': d.nomi, 'natija': d.natija, 'xp': d.xp, 'tayyor': True, 'ochiq': False,
                    'kirish_kerak': True, 'bajarilgan': False, 'yordam_bilan': False, 'joriy': False,
                    'personaj': {'kalit': d.personaj, **PERSONAJLAR[d.personaj]}})
            continue
        n = natijalar.get(d.kod)
        joriy = oquvchi.joriy_dars == d.kod
        guruhlar[d.yonalish]['darslar'].append({
            'kod': d.kod, 'nomi': d.nomi, 'natija': d.natija, 'vaziyat': d.vaziyat, 'sahifa': d.sahifa, 'xp': d.xp,
            'tayyor': True, 'ochiq': _ochiqmi(oquvchi, d, bajarilganlar),
            'personaj': {'kalit': d.personaj, **PERSONAJLAR[d.personaj]},
            'bajarilgan': bool(n and n.bajarilgan), 'yordam_bilan': bool(n and n.bajarilgan and n.yordam),
            'joriy': joriy, **(_joriy(d, oquvchi.dars_holati) if joriy else {})})
    hammasi = [x for g in guruhlar.values() for x in g['darslar']]
    # To'liq yo'l: hali yozilmagan darslar ham ko'rinadi («Tez orada») — o'quvchi va ega oldinda nima borligini biladi.
    # Rahbar bo'limi faqat rahbarga; pul bo'limi — pul bilan ishlaydiganlarga (kassa rejimi).
    rahbar = oquvchi.oquv_xodim.rol == Xodim.Rol.RAHBAR
    pul = pul_oladimi(oquvchi.oquv_salon, oquvchi.oquv_xodim)
    for kod, nomi, y in REJA:
        if not oquvchi.mehmon and ((y == 'rahbar' and not rahbar) or (y == 'pul' and not pul)):
            continue
        guruhlar[y]['darslar'].append({'kod': kod, 'nomi': nomi, 'tayyor': False})
    yonalishlar = [g for g in guruhlar.values() if g['darslar']]
    xp = sum(x['xp'] for x in hammasi if x['bajarilgan'])
    # Boblar: xuddi shu darslar hikoyali bo'laklarga ajratilgan (bosh sahifadagi yo'l); bo'sh qolgan bob ko'rinmaydi
    kod_boyicha = {x['kod']: x for x in hammasi}
    boblar = [{'kalit': kalit, 'nomi': nomi, 'shior': shior, 'izoh': izoh, 'voqea': voqea,
               'darslar': [kod_boyicha[k] for k in kodlar if k in kod_boyicha]}
              for kalit, nomi, shior, izoh, voqea, kodlar in BOBLAR]
    # Eslatma-varaq — bob mukofoti: bobning hamma darsi bajarilgach ochiladi. Mazmuni — o'sha darslarning xulosalari
    # (haqiqiy ishda nima qilinadi), ya'ni tekshirilgan matn; ochilmagan bobga mazmun berilmaydi.
    for b in boblar:
        ochiq = bool(b['darslar']) and all(x['bajarilgan'] for x in b['darslar'])
        b['varaq'] = [{'kod': x['kod'], 'nomi': x['nomi'], 'xulosa': DARS[x['kod']].xulosa} for x in b['darslar']] if ochiq else None
    return {'yonalishlar': yonalishlar, 'boblar': [b for b in boblar if b['darslar']], 'reyting': reyting(oquvchi),
            'rekord': oquvchi.rekord_xp, 'mehmon': oquvchi.mehmon, 'jami': len(hammasi), 'bajarilgan': sum(x['bajarilgan'] for x in hammasi),
            'xp': xp, 'daraja': daraja(xp, sum(x['xp'] for x in hammasi)), 'rejada': sum(not x['tayyor'] for g in yonalishlar for x in g['darslar'])}


@transaction.atomic
def dars_boshla(oquvchi, kod):
    """O'quv salonini tozalab, darsning boshlang'ich holatini yaratadi. «Qayta boshlash» ham shu."""
    oquvchi = _qulfla(oquvchi)
    d = _dars(oquvchi, kod)
    bajarilgan = _bajarilganlar(oquvchi)
    if not _ochiqmi(oquvchi, d, bajarilgan):
        raise AkademiyaXatosi(f"Bu dars hali yopiq. Avval «{_navbat(oquvchi, bajarilgan).nomi}» darsini tugating.")
    oquv_salonni_tozala(oquvchi.oquv_salon)
    # Rahbar darslari sozlamalarni o'zgartiradi va xodim qo'shadi — har dars toza salondan boshlansin: sozlamalar
    # standartga qaytadi (kassa tartibi haqiqiy salondan qayta olinadi), darsda qo'shilgan xodimlar o'chadi.
    personaj = Xodim.objects.filter(salon=oquvchi.oquv_salon).exclude(id=oquvchi.oquv_xodim_id).order_by('id').first()
    Xodim.objects.filter(salon=oquvchi.oquv_salon).exclude(id__in=[oquvchi.oquv_xodim_id, getattr(personaj, 'id', 0)]).delete()
    SalonSozlamalari.objects.filter(salon=oquvchi.oquv_salon).delete()
    # salonning o'zidagi maydonlar ham standartga: boshlash ro'yxati yopiq, rekvizitlar bo'sh (R1 ularni o'zi ochadi)
    Salon.objects.filter(id=oquvchi.oquv_salon_id).update(boshlash_yopilgan=True, yuridik_nom='', manzil='')
    oquvchi.oquv_salon.refresh_from_db()
    oquv_salonni_tayyorla(oquvchi)
    holat = d.urug(Muhit(oquvchi.oquv_salon, oquvchi.oquv_xodim, {}))
    oquvchi.joriy_dars, oquvchi.dars_holati = d.kod, holat
    oquvchi.save(update_fields=['joriy_dars', 'dars_holati'])
    DarsNatija.objects.get_or_create(oquvchi=oquvchi, dars=d.kod)
    return {'kod': d.kod, **_joriy(d, holat)}


def _joriy_dars(oquvchi, kod):
    d = _dars(oquvchi, kod)
    if oquvchi.joriy_dars != d.kod:
        raise AkademiyaXatosi("Avval darsni boshlang.")
    return d


@transaction.atomic
def dars_yordam(oquvchi, kod):
    """Keyingi yordam darajasini ochadi (ishora → aniq qadamlar). Ochilgani dars natijasida «yordam bilan» deb qoladi."""
    oquvchi = _qulfla(oquvchi)
    d = _joriy_dars(oquvchi, kod)
    holat = oquvchi.dars_holati
    if _yordam(d, holat)['yana']:
        holat[YORDAM] = holat.get(YORDAM, 0) + 1
        oquvchi.save(update_fields=['dars_holati'])
    return _yordam(d, holat)


@transaction.atomic
def dars_tekshir(oquvchi, kod, javob=None):
    oquvchi = _qulfla(oquvchi)
    d = _joriy_dars(oquvchi, kod)
    mezonlar = d.tekshir(Muhit(oquvchi.oquv_salon, oquvchi.oquv_xodim, oquvchi.dars_holati), javob)
    bajarildi = all(m['ok'] for m in mezonlar)
    n, _ = DarsNatija.objects.get_or_create(oquvchi=oquvchi, dars=d.kod)
    n.urinishlar += 1
    yangi = bajarildi and not n.bajarilgan
    if yangi:  # birinchi marta bajarilgandagi yordam darajasi saqlanadi
        n.bajarilgan, n.yordam = timezone.now(), oquvchi.dars_holati.get(YORDAM, 0)
    n.save(update_fields=['urinishlar', 'bajarilgan', 'yordam'])
    # tajriba bali faqat birinchi marta bajarilganda beriladi (qayta o'tish ball qo'shmaydi)
    return {'bajarildi': bajarildi, 'mezonlar': mezonlar, 'keyingi': _keyingi(oquvchi, d) if bajarildi else None,
            'xp': d.xp if yangi else 0, 'xulosa': d.xulosa if bajarildi else ''}


def _keyingi(oquvchi, d):
    """Shu darsdan keyingi, hali bajarilmagan va o'quvchiga mos dars (o'tish tartibida)."""
    bajarilgan = _bajarilganlar(oquvchi) | {d.kod}
    tartib = _tartib(oquvchi)
    keyin = tartib[tartib.index(d) + 1:] + tartib[:tartib.index(d)]
    k = next((x for x in keyin if x.kod not in bajarilgan), None)
    return {'kod': k.kod, 'nomi': k.nomi} if k else None


@transaction.atomic
def kursni_qayta_boshla(oquvchi):
    """Kursni boshidan: natijalar o'chadi va darslar yana birinchisidan ketma-ket ochiladi. To'plangan ball yo'qolmaydi —
    rekord bo'lib qoladi (reytingda rekord va yangi natijaning kattasi ko'rinadi)."""
    oquvchi = _qulfla(oquvchi)
    if oquvchi.mehmon:
        raise AkademiyaXatosi("Sinov rejimida kurs qayta boshlanmaydi.")
    xp, darslar, hafta = _ball(oquvchi, [n for n in oquvchi.natijalar.all() if n.bajarilgan and n.dars in DARS])
    oquvchi.rekord_xp, oquvchi.rekord_darslar = xp, darslar
    oquvchi.rekord_hafta, oquvchi.rekord_vaqt = hafta, timezone.now()
    oquvchi.joriy_dars, oquvchi.dars_holati = '', {}
    oquvchi.save(update_fields=['rekord_xp', 'rekord_darslar', 'rekord_hafta', 'rekord_vaqt', 'joriy_dars', 'dars_holati'])
    oquvchi.natijalar.all().delete()
    oquv_salonni_tozala(oquvchi.oquv_salon)
    return darslar_royxati(oquvchi)

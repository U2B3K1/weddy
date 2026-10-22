"""Platforma egasi paneli (4.19): salonlarni ulash, bloklash, tarif va obuna.

Egasi faqat umumiy faollikni ko'radi — zakazlar soni, faol xodimlar, oxirgi kirish, obuna holati (FT-22.5).
Bu API salon mijozlari, zakazlari, kassasi yoki foydasini hech qayerda qaytarmaydi.
"""
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from . import arxiv, cheklov
from .auth import PlatformTokenAuthentication, make_platform_token
from .models import (Ariza, IshonchliQurilma, PlatformaAdmini, Salon, Tarif, Xodim, YordamRuxsati, jurnalga_yoz,
                     platforma_sozlama, sozlama)

SINOV_KUN = 14  # FT-22.8

# Yangi salon tayyor shablon bilan yaratiladi (FT-22.7)
SHABLON_KATEGORIYALAR = [('Milliy', 'libos'), ("Oq ko'ylak", 'libos'), ('Pachka', 'libos'),
                         ('Fata', 'aksessuar'), ('Toj', 'aksessuar'), ("Qo'lqop", 'aksessuar'),
                         ('Tufli', 'aksessuar'), ('Sumka', 'aksessuar')]


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.user, PlatformaAdmini)


class PlatformaView(APIView):
    authentication_classes = [PlatformTokenAuthentication]
    permission_classes = [IsPlatformAdmin]


class PlatformaLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def get_authenticate_header(self, request):
        return 'Bearer'

    def post(self, request):
        login, parol = str(request.data.get('login', '')), str(request.data.get('parol', ''))
        # parolni tanlab topishga qarshi — IP bo'yicha (cheklov.py), egasining o'zi bloklanib qolmaydi
        if cheklov.bloklanganmi(request, 'platforma', login):
            raise PermissionDenied("Parol ko'p marta xato kiritildi: kirish 15 daqiqaga to'xtatildi.")
        admin = PlatformaAdmini.objects.filter(login=login, faol=True).first()
        if not admin or not admin.check_parol(parol):
            cheklov.xato_yoz(request, 'platforma', login)
            raise AuthenticationFailed("Login yoki parol noto'g'ri.")
        cheklov.tozala(request, 'platforma', login)
        return Response({'token': make_platform_token(admin), 'ism': admin.ism or admin.login})


def salon_json(s):
    holat, qolgan = s.obuna_holati()
    return {
        'id': s.id, 'nomi': s.nomi, 'login': s.login, 'manzil': s.manzil, 'rahbar_telefon': s.rahbar_telefon,
        'holat': holat, 'tarif': s.tarif.nomi if s.tarif else None, 'tarif_id': s.tarif_id,
        'sinov_tugaydi': s.sinov_tugaydi, 'obuna_tugaydi': s.obuna_tugaydi,
        'faqat_korishgacha_kun': qolgan if holat != Salon.Holat.FAQAT_KORISH else None,
        # faqat umumiy faollik (FT-22.5)
        'zakazlar_soni': getattr(s, 'zakazlar_soni', 0), 'faol_xodimlar': getattr(s, 'faol_xodimlar', 0),
        'oxirgi_kirish': s.oxirgi_kirish, 'yaratilgan': s.yaratilgan,
        'yordam_ruxsati': bool(YordamRuxsati.amaldagi(s)),
        'chiqish_sanasi': s.chiqish_sanasi, 'chiqish_izohi': s.chiqish_izohi, 'ochiriladi': arxiv.ochiriladigan_sana(s),
    }


def _salonlar():
    from apps.orders.models import Zakaz
    zakazlar = dict(Zakaz.objects.values_list('salon_id').annotate(n=Count('id')))
    xodimlar = dict(Xodim.objects.filter(faol=True).values_list('salon_id').annotate(n=Count('id')))
    natija = []
    for s in Salon.objects.select_related('tarif').order_by('nomi'):
        s.zakazlar_soni, s.faol_xodimlar = zakazlar.get(s.id, 0), xodimlar.get(s.id, 0)
        natija.append(s)
    return natija


class SalonYaratSerializer(serializers.Serializer):
    nomi = serializers.CharField(max_length=200)
    manzil = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')
    rahbar_telefon = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    login = serializers.RegexField(r'^[a-z0-9_-]{3,64}$',
                                   error_messages={'invalid': "Login: 3–64 ta kichik lotin harfi, raqam, - yoki _."})
    parol = serializers.CharField(min_length=8, max_length=128)
    rahbar_ismi = serializers.CharField(max_length=200)
    rahbar_pin = serializers.RegexField(r'^\d{4,6}$', error_messages={'invalid': "PIN 4–6 ta raqam bo'lishi kerak."})
    tarif = serializers.IntegerField(required=False)


class PlatformaSalonlarView(PlatformaView):
    def get(self, request):
        return Response([salon_json(s) for s in _salonlar()])

    @transaction.atomic
    def post(self, request):
        """Yangi salon: login va boshlang'ich parol, rahbar, shablon kategoriyalar, 14 kunlik sinov (FT-22.1, FT-22.7)."""
        from apps.catalog.models import Kategoriya

        ser = SalonYaratSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        tarif = None
        if 'tarif' in d:
            tarif = Tarif.objects.filter(id=d['tarif'], faol=True).first()
            if not tarif:
                return Response({'tarif': ['Topilmadi.']}, status=400)
        salon = Salon(nomi=d['nomi'], login=d['login'], manzil=d['manzil'], rahbar_telefon=d['rahbar_telefon'],
                      tarif=tarif, holat=Salon.Holat.SINOV,
                      sinov_tugaydi=timezone.localdate() + timedelta(days=SINOV_KUN))
        salon.set_parol(d['parol'])
        try:
            with transaction.atomic():
                salon.save()
        except IntegrityError:
            return Response({'detail': 'Bu login band.'}, status=409)
        rahbar = Xodim(salon=salon, ism=d['rahbar_ismi'].strip(), telefon=d['rahbar_telefon'], rol=Xodim.Rol.RAHBAR)
        rahbar.set_pin(d['rahbar_pin'])
        rahbar.save()
        Kategoriya.objects.bulk_create([Kategoriya(salon=salon, nomi=n, turi=t, tartib=i)
                                        for i, (n, t) in enumerate(SHABLON_KATEGORIYALAR)])
        sozlama(salon)  # standart sozlamalar
        return Response(salon_json(salon), status=201)


class PlatformaSalonView(PlatformaView):
    def _salon(self, pk):
        s = Salon.objects.select_related('tarif').filter(id=pk).first()
        if not s:
            raise NotFound('Salon topilmadi.')
        return s

    @transaction.atomic
    def patch(self, request, pk):
        """Bloklash/ochish, tarif, parolni tiklash, sinov/obuna sanasini o'zgartirish."""
        class S(serializers.Serializer):
            bloklangan = serializers.BooleanField(required=False)
            tarif = serializers.IntegerField(required=False, allow_null=True)
            parol = serializers.CharField(min_length=8, max_length=128, required=False)
            sinov_tugaydi = serializers.DateField(required=False, allow_null=True)
            obuna_tugaydi = serializers.DateField(required=False, allow_null=True)
            qurilmalarni_tozala = serializers.BooleanField(required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        s = self._salon(pk)
        if 'tarif' in d:
            tarif = Tarif.objects.filter(id=d['tarif'], faol=True).first() if d['tarif'] else None
            if d['tarif'] and not tarif:
                return Response({'tarif': ['Topilmadi.']}, status=400)
            s.tarif = tarif
        if 'parol' in d:
            s.set_parol(d['parol'])
        if 'sinov_tugaydi' in d:
            s.sinov_tugaydi = d['sinov_tugaydi']
        if 'obuna_tugaydi' in d:
            s.obuna_tugaydi = d['obuna_tugaydi']
        if d.get('qurilmalarni_tozala'):
            # Rahbar yagona ishonchli qurilmani yo'qotsa: keyingi kirgan qurilma yana birinchi (ishonchli) bo'ladi
            IshonchliQurilma.objects.filter(salon=s, faol=True).update(faol=False)
        if d.get('bloklangan') is True:
            s.holat = Salon.Holat.BLOKLANGAN
        elif d.get('bloklangan') is False and s.chiqish_sanasi:
            return Response({'detail': "Salon platformadan chiqqan: avval chiqishni bekor qiling."}, status=409)
        elif d.get('bloklangan') is False and s.holat == Salon.Holat.BLOKLANGAN:
            s.holat = Salon.Holat.FAOL  # quyida sanalarga ko'ra aniqlashtiriladi
        s.save()
        s.obunani_yangila()
        return Response(salon_json(s))


class PlatformaChiqishView(PlatformaView):
    """FT-22.10: salon platformadan chiqdi (rahbarning yozma so'rovi bilan) yoki chiqish bekor qilindi."""

    def post(self, request, pk):
        s = Salon.objects.filter(id=pk).first()
        if not s:
            raise NotFound('Salon topilmadi.')
        try:
            s = arxiv.salon_chiqdi(s, str(request.data.get('izoh', '')))
        except arxiv.ArxivXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(salon_json(s))

    def delete(self, request, pk):
        s = Salon.objects.filter(id=pk).first()
        if not s:
            raise NotFound('Salon topilmadi.')
        try:
            s = arxiv.chiqishni_bekor_qilish(s)
        except arxiv.ArxivXatosi as e:
            return Response({'detail': str(e)}, status=409)
        return Response(salon_json(s))


class PlatformaArxivView(PlatformaView):
    """Chiqqan salon ma'lumotlari JSON arxiv sifatida (rahbarga topshirish uchun)."""

    def get(self, request, pk):
        s = Salon.objects.filter(id=pk).first()
        if not s:
            raise NotFound('Salon topilmadi.')
        try:
            malumot = arxiv.salon_arxivi(s)
        except arxiv.ArxivXatosi as e:
            return Response({'detail': str(e)}, status=409)
        javob = JsonResponse(malumot, json_dumps_params={'ensure_ascii': False, 'indent': 1})
        javob['Content-Disposition'] = f'attachment; filename="libosa-{s.login}-arxiv.json"'
        return javob


class PlatformaTolovView(PlatformaView):
    """Obuna to'lovini qo'lda belgilash (FT-22.9: 1-bosqichda avtomatik qabul yo'q)."""

    @transaction.atomic
    def post(self, request, pk):
        oylar = serializers.IntegerField(min_value=1, max_value=24).run_validation(request.data.get('oylar'))
        s = Salon.objects.select_for_update().filter(id=pk).first()
        if not s:
            raise NotFound('Salon topilmadi.')
        # Muddat hali tugamagan bo'lsa undan, tugagan bo'lsa bugundan boshlab uzaytiriladi
        asos = max(s.obuna_muddati() or timezone.localdate(), timezone.localdate())
        yil, oy = asos.year + (asos.month - 1 + oylar) // 12, (asos.month - 1 + oylar) % 12 + 1
        import calendar
        s.obuna_tugaydi = asos.replace(year=yil, month=oy, day=min(asos.day, calendar.monthrange(yil, oy)[1]))
        s.save(update_fields=['obuna_tugaydi'])
        s.obunani_yangila()
        return Response(salon_json(Salon.objects.select_related('tarif').get(id=s.id)))


class PlatformaTariflarView(PlatformaView):
    def get(self, request):
        return Response([{'id': t.id, 'nomi': t.nomi, 'oylik_narx': t.oylik_narx, 'xodim_limit': t.xodim_limit,
                          'filial_limit': t.filial_limit}
                         for t in Tarif.objects.filter(faol=True).annotate(n=Count('salonlar')).order_by('oylik_narx')])

    def post(self, request):
        class S(serializers.Serializer):
            nomi = serializers.CharField(max_length=100)
            oylik_narx = serializers.IntegerField(min_value=0)
            xodim_limit = serializers.IntegerField(min_value=1, max_value=50)
            filial_limit = serializers.IntegerField(min_value=1, max_value=10, default=1)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        if Tarif.objects.filter(nomi=ser.validated_data['nomi']).exists():
            return Response({'detail': 'Bunday tarif bor.'}, status=409)
        t = Tarif.objects.create(**ser.validated_data)
        return Response({'id': t.id, 'nomi': t.nomi}, status=201)


class PlatformaTarifView(PlatformaView):
    """Tarifni o'zgartirish yoki yopish. Salon ulangan tarif yopilmaydi; limit kamaysa mavjud xodim/filiallar
    qoladi, faqat yangisini qo'shish cheklanadi."""

    def patch(self, request, pk):
        class S(serializers.Serializer):
            nomi = serializers.CharField(max_length=100, required=False)
            oylik_narx = serializers.IntegerField(min_value=0, required=False)
            xodim_limit = serializers.IntegerField(min_value=1, max_value=50, required=False)
            filial_limit = serializers.IntegerField(min_value=1, max_value=10, required=False)
            faol = serializers.BooleanField(required=False)

        t = Tarif.objects.filter(id=pk).first()
        if not t:
            raise NotFound('Tarif topilmadi.')
        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if 'nomi' in d and Tarif.objects.filter(nomi=d['nomi']).exclude(id=t.id).exists():
            return Response({'detail': 'Bunday tarif bor.'}, status=409)
        if d.get('faol') is False and t.salonlar.exists():
            return Response({'detail': f"Tarifda {t.salonlar.count()} ta salon bor — avval ularni boshqa tarifga o'tkazing."},
                            status=409)
        for nom, qiymat in d.items():
            setattr(t, nom, qiymat)
        t.save()
        return Response({'id': t.id, 'nomi': t.nomi, 'oylik_narx': t.oylik_narx, 'xodim_limit': t.xodim_limit,
                         'filial_limit': t.filial_limit, 'faol': t.faol})


def ariza_json(a):
    return {'id': a.id, 'tur': a.tur, 'ism': a.ism, 'telefon': a.telefon, 'salon_nomi': a.salon_nomi,
            'xabar': a.xabar, 'yaratilgan': a.yaratilgan, 'korilgan': a.korilgan}


class PlatformaArizalarView(PlatformaView):
    """Bosh sahifadan kelgan so'rovlar: avval ko'rilmaganlari."""

    def get(self, request):
        return Response([ariza_json(a) for a in Ariza.objects.all()[:200]])


class PlatformaArizaView(PlatformaView):
    def patch(self, request, pk):
        a = Ariza.objects.filter(id=pk).first()
        if not a:
            raise NotFound('So\'rov topilmadi.')
        if isinstance(request.data.get('korilgan'), bool):
            a.korilgan = request.data['korilgan']
            a.save(update_fields=['korilgan'])
        return Response(ariza_json(a))

    def delete(self, request, pk):
        Ariza.objects.filter(id=pk).delete()
        return Response(status=204)


class PlatformaYordamView(PlatformaView):
    """Salon ichidagi ma'lumot — faqat rahbar bergan, muddati o'tmagan yordam ruxsati bilan (FT-22.5).

    Faqat o'qish. Har bir kirish salon jurnaliga yoziladi, rahbar uni ko'radi.
    """

    def get(self, request, pk):
        from apps.finance import reports
        from apps.orders.models import Zakaz

        salon = Salon.objects.filter(id=pk).first()
        if not salon:
            raise NotFound('Salon topilmadi.')
        ruxsat = YordamRuxsati.amaldagi(salon)
        if not ruxsat:
            raise PermissionDenied("Salon rahbari yordam ruxsatini bermagan yoki muddati tugagan.")
        jurnalga_yoz(salon, None, 'platforma_yordam_kirishi', f'platforma admini {request.user.login}')
        bugun = timezone.localdate()
        zakazlar = (Zakaz.objects.filter(salon=salon).select_related('mijoz', 'sotuvchi').order_by('-raqam')[:50])
        return Response({
            'salon': salon.nomi, 'ruxsat_tugaydi': ruxsat.tugaydi,
            'zakazlar': [{'raqam': z.raqam, 'holat': z.holat, 'mijoz': z.mijoz.fio or z.mijoz.telefon,
                          'olib_ketish': z.olib_ketish, 'qaytarish': z.qaytarish, 'jami': z.jami,
                          'sotuvchi': z.sotuvchi.ism if z.sotuvchi else None} for z in zakazlar],
            'shu_oy': reports.foyda_zarar(salon, bugun.year, bugun.month),
        })


def platforma_sozlama_json():
    """Platforma sozlamalari holati. Token **hech qachon** qaytarilmaydi — faqat qayerdan olinayotgani."""
    from apps.notify import telegram

    s = platforma_sozlama()
    return {
        'telegram_kiritilgan': bool(s.telegram_token),
        'telegram_bot_nomi': s.telegram_bot_nomi or settings.TELEGRAM_BOT_NAME,
        # 'panel' — egasi kiritgan token, 'env' — .env dagi zaxira, 'yoq' — bot umuman yoqilmagan
        'telegram_manba': 'panel' if s.telegram_token else ('env' if settings.TELEGRAM_BOT_TOKEN else 'yoq'),
        'telegram_ulangan': telegram.sozlangan(),
        'telegram_ega_ulangan': bool(s.telegram_chat_id),  # egasi botga ulanganmi (a'zo bo'lish so'rovlari shu chatga boradi)
    }


class PlatformaSozlamaSerializer(serializers.Serializer):
    telegram_token = serializers.RegexField(
        r'^(\d{5,20}:[A-Za-z0-9_-]{20,60})?$', required=False, allow_blank=True,
        error_messages={'invalid': "Bot tokeni «123456:ABC...» ko'rinishida bo'ladi (BotFather beradi)."})
    telegram_bot_nomi = serializers.RegexField(r'^@?[A-Za-z0-9_]{0,32}$', required=False, allow_blank=True)

    def validate_telegram_bot_nomi(self, v):
        return v.lstrip('@')


class PlatformaSozlamaView(PlatformaView):
    """Platforma darajasidagi sozlamalar (4.19) — hozircha Telegram boti.

    Butun platformaga **bitta** Libosa boti xizmat qiladi (FT-4.14): 100 salon o'z botini yuritsa, 100 ta
    jarayon navbat bilan bitta akkaunt limitidan foydalanardi. Tokenni shu yerdan faqat platforma egasi
    kiritadi; u bazada ochiq saqlanadi (serverning o'zi ishlatadi), lekin API orqali qaytarilmaydi.

    Saqlashdan oldin token Telegram'da tekshiriladi (`getMe`) — xato token bilan butun platforma botsiz
    qolib ketmasligi uchun. Bot nomi o'sha javobdan olinadi: egasi havola uchun @nom kiritib o'tirmaydi.
    """

    def get(self, request):
        return Response(platforma_sozlama_json())

    def patch(self, request):
        from apps.notify import telegram

        ser = PlatformaSozlamaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        s = platforma_sozlama()
        if 'telegram_token' in d:
            token = (d['telegram_token'] or '').strip()
            if token and token != s.telegram_token:
                try:  # getMe: token haqiqiy va bot tirik ekanini tasdiqlaydi
                    nomi = telegram.tekshir(token).get('username', '')
                except telegram.TelegramXatosi as e:
                    return Response({'telegram_token': f'Token tekshirilmadi: {e}'}, status=400)
                s.telegram_token = token
                s.telegram_bot_nomi = nomi[:32]  # nomni botdan olamiz
            elif not token:
                s.telegram_token, s.telegram_bot_nomi = '', ''
        if 'telegram_bot_nomi' in d and d['telegram_bot_nomi']:  # qo'lda tuzatish uchun
            s.telegram_bot_nomi = d['telegram_bot_nomi'][:32]
        s.save()
        return Response(platforma_sozlama_json())


class PlatformaTelegramUlashView(PlatformaView):
    """Platforma egasini botga ulash: bir martalik kod (`/start <kod>`, 15 daqiqa) yoki ulanishni uzish (FT-4.14)."""

    def post(self, request):
        from apps.notify import telegram
        from apps.notify.services import platforma_ulash_kodi

        if not telegram.sozlangan():
            return Response({'detail': "Avval bot tokenini kiriting."}, status=400)
        kod = platforma_ulash_kodi()
        bot = telegram.bot_nomi()
        return Response({'kod': kod, 'havola': f'https://t.me/{bot}' if bot else None})

    def delete(self, request):
        s = platforma_sozlama()
        s.telegram_chat_id = None
        s.telegram_ulash_kod = ''
        s.telegram_ulash_tugaydi = None
        s.save(update_fields=['telegram_chat_id', 'telegram_ulash_kod', 'telegram_ulash_tugaydi'])
        return Response(platforma_sozlama_json())

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, NotFound, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import make_device_token, make_staff_token, qurilma_holati
from .models import Ariza, IshonchliQurilma, Jurnal, Salon, Xodim, jurnalga_yoz


class OchiqView(APIView):
    """Tokensiz kiriladigan endpointlar; xato bo'lsa 403 emas, 401 qaytaradi."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return 'Bearer'


ARIZA_TELEFONGA_KUNIGA = 3     # bitta raqamdan sutkasiga
ARIZA_JAMI_KUNIGA = 200        # hamma raqamdan sutkasiga — forma to'ldirib tashlanishiga qarshi


class ArizaView(OchiqView):
    """Bosh sahifadagi «A'zo bo'lish» va «Bog'lanish» formalari. Hisob yaratmaydi — so'rov platforma egasiga tushadi."""

    def post(self, request):
        class S(serializers.Serializer):
            tur = serializers.ChoiceField(choices=Ariza.Tur.choices, default=Ariza.Tur.AZO)
            ism = serializers.CharField(max_length=200)
            telefon = serializers.RegexField(r'^\+?[0-9 ()\-]{7,20}$', error_messages={'invalid': "Telefon raqami noto'g'ri."})
            salon_nomi = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
            xabar = serializers.CharField(max_length=1000, required=False, allow_blank=True, default='')
            sayt = serializers.CharField(required=False, allow_blank=True, default='')  # odamga ko'rinmaydigan tuzoq maydon

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if d.pop('sayt'):  # bot to'ldirgan: muvaffaqiyat ko'rsatiladi, lekin saqlanmaydi
            return Response({'qabul': True}, status=201)
        kecha = timezone.now() - timedelta(days=1)
        yangi = Ariza.objects.filter(yaratilgan__gte=kecha)
        if yangi.filter(telefon=d['telefon']).count() >= ARIZA_TELEFONGA_KUNIGA or yangi.count() >= ARIZA_JAMI_KUNIGA:
            return Response({'detail': "So'rovingiz qabul qilingan — tez orada bog'lanamiz."}, status=429)
        a = Ariza.objects.create(**d)
        # Platforma egasi botga ulagan bo'lsa — yangi so'rov haqida Telegram xabari (FT-4.14).
        from apps.notify.services import platforma_arizasi
        transaction.on_commit(lambda: platforma_arizasi(a))
        return Response({'qabul': True}, status=201)


class SalonLoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    parol = serializers.CharField()
    qurilma_nomi = serializers.CharField(default='Planshet')
    qurilma_modeli = serializers.CharField(required=False, allow_blank=True, default='')


class SalonLoginView(OchiqView):
    """1-qadam: salon logini va paroli qurilmada bir marta kiritiladi (FT-1.1, FT-22.2)."""
    def post(self, request):
        ser = SalonLoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        salon = Salon.objects.filter(login=d['login']).first()
        if salon and salon.kirish_blok_gacha and salon.kirish_blok_gacha > timezone.now():
            raise PermissionDenied("Parol ko'p marta xato kiritildi. Keyinroq urinib ko'ring.")
        if not salon or not salon.check_parol(d['parol']) or salon.holat == Salon.Holat.BLOKLANGAN:
            if salon and salon.holat != Salon.Holat.BLOKLANGAN:
                salon.kirish_xato += 1
                if salon.kirish_xato >= settings.PIN_MAX_ATTEMPTS:
                    salon.kirish_blok_gacha = timezone.now() + timedelta(minutes=settings.PIN_LOCK_MINUTES)
                    salon.kirish_xato = 0
                salon.save(update_fields=['kirish_xato', 'kirish_blok_gacha'])
            raise AuthenticationFailed("Login yoki parol noto'g'ri.")
        if salon.kirish_xato:
            salon.kirish_xato = 0
            salon.save(update_fields=['kirish_xato'])
        # Birinchi qurilma darhol ishonchli; keyingilari rahbar ruxsatini kutadi (FT-22.2).
        # Demo/sinov salonida (qurilma_avto_tasdiq) har bir qurilma darhol ishonchli bo'ladi.
        birinchi = salon.qurilma_avto_tasdiq or not IshonchliQurilma.objects.filter(
            salon=salon, faol=True, tasdiqlangan=True).exists()
        qurilma = IshonchliQurilma.objects.create(salon=salon, nomi=d['qurilma_nomi'][:100],
                                                  modeli=d['qurilma_modeli'][:200], tasdiqlangan=birinchi)
        if not birinchi:  # rahbarlarga «Ruxsat / Rad» tugmali xabar (xato kirishni buzmaydi)
            from apps.notify.services import qurilma_kutmoqda_xabari
            transaction.on_commit(lambda: qurilma_kutmoqda_xabari(qurilma))
        return Response({'qurilma_token': make_device_token(salon, qurilma), 'kutilmoqda': not birinchi,
                         'salon': {'nomi': salon.nomi, 'rang': salon.rang}})


def _device(request):
    h = qurilma_holati(request.headers.get('X-Device-Token', ''))
    if not h:
        raise AuthenticationFailed('Qurilma ishonchli emas, salon logini bilan qayta kiring.')
    if h[0] == 'kutilmoqda':
        # 401 emas: klient qurilma tokenini saqlab, ruxsatni kutadi
        raise PermissionDenied({'detail': 'Qurilma rahbar ruxsatini kutmoqda.', 'kod': 'qurilma_kutilmoqda'})
    return h[1], h[2]


QURILMA_PIN_XATO_SUTKADA = 5  # kutayotgan qurilmalardan rahbar PIN ini taxmin qilishga salon bo'yicha sutkalik chegara


class QurilmaTasdiqView(OchiqView):
    """Ruxsat kutayotgan qurilmaning o'zidan tasdiqlash yo'llari (FT-22.2).

    GET — Telegram havolasi (rahbar bosib, botda «Ha, bu men» desa qurilma ochiladi), uning muddati va
    PIN bilan tasdiqlay oladigan rahbarlar.
    POST {xodim_id, pin} — Telegramdan foydalana olmaydigan rahbar shu qurilmada o'z PIN i bilan tasdiqlaydi:
    aks holda yagona rahbar yangi qurilmada qotib qolardi. Bu yo'l ishonchsiz qurilmaga PIN taxmin qilish
    imkonini beradi, shu sabab salon bo'yicha sutkada 5 ta xato bilan cheklangan (4 xonali PIN ~5 yilda).
    """

    def _kutayotgan(self, request):
        h = qurilma_holati(request.headers.get('X-Device-Token', ''))
        if not h:
            raise AuthenticationFailed('Qurilma ishonchli emas, salon logini bilan qayta kiring.')
        return h

    @staticmethod
    def _pin_rahbarlar(salon):
        """Telegram ulamagan rahbarlar; bot umuman sozlanmagan bo'lsa — barcha rahbarlar (havola ishlamaydi)."""
        from apps.notify import telegram
        qs = Xodim.objects.filter(salon=salon, rol=Xodim.Rol.RAHBAR, faol=True)
        return qs if not telegram.sozlangan() else qs.filter(telegram_id__isnull=True)

    def get(self, request):
        holat, salon, qurilma = self._kutayotgan(request)
        if holat == 'ok':
            return Response({'tasdiqlangan': True})
        from apps.notify.services import qurilma_tasdiq_havolasi
        havola, tugaydi = qurilma_tasdiq_havolasi(qurilma)
        return Response({'tasdiqlangan': False, 'tg_havola': havola, 'tg_tugaydi': tugaydi,
                         'rahbarlar': [{'id': x.id, 'ism': x.ism} for x in self._pin_rahbarlar(salon).order_by('ism')]})

    def post(self, request):
        holat, salon, qurilma = self._kutayotgan(request)
        if holat == 'ok':
            return Response({'tasdiqlangan': True})
        from apps.notify.services import QURILMA_FAQAT_KORISH, qurilma_ozgartirsa_boladi, qurilma_tasdiqla
        if not qurilma_ozgartirsa_boladi(salon):
            raise PermissionDenied(QURILMA_FAQAT_KORISH)
        xid = str(request.data.get('xodim_id', ''))
        xodim = self._pin_rahbarlar(salon).filter(id=int(xid)).first() if xid.isdigit() else None
        if not xodim:
            raise NotFound('Rahbar topilmadi.')
        if Jurnal.objects.filter(salon=salon, harakat='qurilma_pin_xato',
                                 vaqt__gt=timezone.now() - timedelta(days=1)).count() >= QURILMA_PIN_XATO_SUTKADA:
            raise PermissionDenied("Bugun PIN ko'p marta xato kiritildi. Rahbar Telegramni ulab ruxsat bersin "
                                   "yoki platforma egasiga murojaat qiling.")
        try:
            pin_tekshir(xodim, str(request.data.get('pin', '')))
        except AuthenticationFailed:
            jurnalga_yoz(salon, xodim, 'qurilma_pin_xato', f'qurilma {qurilma.nomi}')
            # 401 emas: klient 401 ni «qurilma chiqarilgan» deb tushunadi
            return Response({'detail': "PIN noto'g'ri."}, status=400)
        qurilma_tasdiqla(qurilma, xodim, 'qurilmada PIN')
        return Response({'tasdiqlangan': True})


class XodimlarRoyxatiView(OchiqView):
    """2-qadam: ro'yxatdan ismni tanlash. Faqat ishonchli qurilmadan."""
    def get(self, request):
        salon, _ = _device(request)
        xodimlar = Xodim.objects.filter(salon=salon, faol=True).order_by('ism')
        return Response([{'id': x.id, 'ism': x.ism, 'rol': x.rol} for x in xodimlar])


def pin_tekshir(xodim, pin):
    """PIN ni tekshiradi; 5 marta xato bo'lsa 15 daqiqaga bloklaydi (FT-1.7). Xatoda istisno ko'taradi."""
    if xodim.bloklangan:
        raise PermissionDenied("PIN ko'p marta xato kiritildi. Keyinroq urinib ko'ring.")
    if not xodim.check_pin(pin):
        xodim.xato_urinish += 1
        if xodim.xato_urinish >= settings.PIN_MAX_ATTEMPTS:
            xodim.bloklangan_gacha = timezone.now() + timedelta(minutes=settings.PIN_LOCK_MINUTES)
            xodim.xato_urinish = 0
            from apps.notify.services import rahbarlarga  # FT-1.7: rahbarga xabar boradi
            rahbarlarga(xodim.salon, 'pin_bloklandi',
                        f"{xodim.ism} PIN kodi 5 marta xato kiritildi va 15 daqiqaga bloklandi.")
        xodim.save(update_fields=['xato_urinish', 'bloklangan_gacha'])
        raise AuthenticationFailed("PIN noto'g'ri.")
    if xodim.xato_urinish:
        xodim.xato_urinish = 0
        xodim.save(update_fields=['xato_urinish'])


class PinLoginView(OchiqView):
    """Xodim shaxsiy PIN bilan kiradi; 5 marta xato bo'lsa 15 daqiqa bloklanadi (FT-1.7)."""
    def post(self, request):
        salon, qurilma = _device(request)
        pin = str(request.data.get('pin', ''))
        try:
            xodim = Xodim.objects.get(salon=salon, id=request.data.get('xodim_id'), faol=True)
        except (Xodim.DoesNotExist, ValueError, TypeError):
            raise NotFound('Xodim topilmadi.')
        pin_tekshir(xodim, pin)
        from apps.notify import services as notify
        # FT-1.1, FT-22.3: rahbar kirishi Telegram kod bilan tasdiqlanadi. Qurilmani hozirgina Telegramdan
        # o'zi tasdiqlagan bo'lsa — shaxsi Telegram orqali allaqachon tasdiqlangan, ikkinchi kod so'ralmaydi.
        if notify.kirish_kodi_kerak(xodim) and not notify.tg_tasdiq_kodsiz_kirish(xodim, qurilma):
            kod = str(request.data.get('telegram_kod', '')).strip()
            if not kod:
                if not notify.kirish_kodi_yubor(xodim):
                    return Response({'detail': "Telegram kodni yuborib bo'lmadi. Birozdan keyin urinib ko'ring."},
                                    status=503)
                return Response({'telegram_kod_kerak': True}, status=202)
            if not notify.kirish_kodini_tekshir(xodim, kod):
                raise AuthenticationFailed("Telegram kod noto'g'ri yoki muddati o'tgan.")
        Salon.objects.filter(id=salon.id).update(oxirgi_kirish=timezone.now())  # platforma egasi uchun faollik
        yangi = {'oxirgi_kirish': timezone.now()}
        modeli = str(request.data.get('qurilma_modeli') or '')[:200]
        if modeli:  # faqat to'liq kirgandan keyin; eski qurilmalar ham modelini shu yo'l bilan oladi
            yangi['modeli'] = modeli
        IshonchliQurilma.objects.filter(id=qurilma.id).update(**yangi)
        return Response({'token': make_staff_token(xodim, qurilma),
                         'xodim': {'id': xodim.id, 'ism': xodim.ism, 'rol': xodim.rol}})


class MeView(APIView):
    def get(self, request):
        holat, qolgan = request.salon.obuna_holati()
        return Response({'id': request.user.id, 'ism': request.user.ism,
                         'rol': request.user.rol, 'salon': request.salon.nomi,
                         'salon_holati': holat,
                         # muddat o'tgan: shuncha kundan keyin «faqat ko'rish» (FT-22.8)
                         'obuna_ogohlantirish_kun': qolgan if holat != Salon.Holat.FAQAT_KORISH else None})


class PinTekshirView(APIView):
    """Kirgan xodim PIN ini qayta tasdiqlaydi — «Mijozga ko'rsatish» rejimidan chiqish uchun (FT-23.1)."""

    def post(self, request):
        try:
            pin_tekshir(request.user, str(request.data.get('pin', '')))
        except AuthenticationFailed as e:
            # 401 emas: aks holda klient sessiyani tugagan deb hisoblaydi
            return Response({'detail': str(e.detail)}, status=400)
        return Response({'ok': True})

"""Admin panel: salon sozlamalari (4.16) va xodimlarni boshqarish (FT-22.3). Faqat rahbar o'zgartiradi (Ilova B)."""
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from datetime import timedelta

from django.utils import timezone

from apps.notify import telegram
from apps.notify.services import ulash_kodi_yarat

from .models import IshonchliQurilma, Xodim, YordamRuxsati, jurnalga_yoz, sozlama
from .permissions import IsRahbar, IsStaff, SalonYozishRuxsati

SOZLAMA_MAYDONLARI = ('bufer_kun', 'vaqtinchalik_bron_soat', 'zalog_pul', 'zalog_hujjat', 'zalog_tillo',
                      'kechikish_jarimasi', 'kechikish_kunlik_summa', 'qaytarish_qoidasi', 'libos_tasdigi',
                      'promokod_tasdiqsiz', 'promokod_chegirma_birga', 'salonchi_kodlari',
                      'mavsumiy_narx', 'sotuvchi_bonusi', 'bonus_foiz', 'primerka', 'mijoz_bahosi',
                      'qulf_daqiqa', 'sotuvchi_libos_qoshadi', 'qoplamagan_royxat',
                      'qoplamagan_kun', 'kunlik_hisobot', 'kunlik_hisobot_vaqti', 'promokodlar_bolimi', 'manekin', 'shartnoma_bandlari', 'filial_kassasi', 'sms_eslatma')


def sozlama_json(s):
    return {m: getattr(s, m) for m in SOZLAMA_MAYDONLARI}


class ShartnomaBandiSerializer(serializers.Serializer):
    sarlavha = serializers.CharField(max_length=100)
    matn = serializers.CharField(max_length=2000)


class SozlamaSerializer(serializers.Serializer):
    shartnoma_bandlari = ShartnomaBandiSerializer(many=True, required=False, max_length=15)
    bufer_kun = serializers.IntegerField(min_value=0, max_value=30, required=False)
    vaqtinchalik_bron_soat = serializers.IntegerField(min_value=1, max_value=168, required=False)
    zalog_pul = serializers.BooleanField(required=False)
    zalog_hujjat = serializers.BooleanField(required=False)
    zalog_tillo = serializers.BooleanField(required=False)
    kechikish_jarimasi = serializers.BooleanField(required=False)
    kechikish_kunlik_summa = serializers.IntegerField(min_value=0, required=False)
    qaytarish_qoidasi = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField(), min_length=2, max_length=2),
        min_length=1, max_length=10, required=False)
    libos_tasdigi = serializers.BooleanField(required=False)
    promokod_tasdiqsiz = serializers.BooleanField(required=False)
    promokod_chegirma_birga = serializers.BooleanField(required=False)
    salonchi_kodlari = serializers.BooleanField(required=False)
    mavsumiy_narx = serializers.BooleanField(required=False)
    primerka = serializers.BooleanField(required=False)
    mijoz_bahosi = serializers.BooleanField(required=False)
    qulf_daqiqa = serializers.IntegerField(min_value=1, max_value=120, required=False)
    sotuvchi_libos_qoshadi = serializers.BooleanField(required=False)
    qoplamagan_royxat = serializers.BooleanField(required=False)
    qoplamagan_kun = serializers.IntegerField(min_value=1, max_value=730, required=False)
    kunlik_hisobot = serializers.BooleanField(required=False)
    kunlik_hisobot_vaqti = serializers.TimeField(required=False)
    promokodlar_bolimi = serializers.BooleanField(required=False)
    manekin = serializers.BooleanField(required=False)
    filial_kassasi = serializers.BooleanField(required=False)
    sms_eslatma = serializers.BooleanField(required=False)
    sotuvchi_bonusi = serializers.BooleanField(required=False)
    bonus_foiz = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100, required=False)

    def validate_qaytarish_qoidasi(self, qoida):
        """[[kun, foiz], ...]: kunlar kamayib boradi va 0 bilan tugaydi, foiz 0–100 va kamayib boradi."""
        kunlar = [k for k, _ in qoida]
        foizlar = [f for _, f in qoida]
        if kunlar != sorted(set(kunlar), reverse=True) or kunlar[-1] != 0:
            raise serializers.ValidationError("Kunlar takrorlanmasdan kamayib borishi va 0 bilan tugashi kerak.")
        if any(not 0 <= f <= 100 for f in foizlar):
            raise serializers.ValidationError("Foiz 0 dan 100 gacha bo'lishi kerak.")
        if foizlar != sorted(foizlar, reverse=True):
            raise serializers.ValidationError("To'yga yaqinlashgan sari qaytariladigan foiz oshmasligi kerak.")
        return qoida


class SozlamalarView(APIView):
    """GET — har bir xodim (forma qaysi zalog turlarini ko'rsatishni bilishi uchun); PATCH — faqat rahbar."""

    def get_permissions(self):
        return [IsStaff()] if self.request.method == 'GET' else [IsRahbar(), SalonYozishRuxsati()]

    def get(self, request):
        from .models import integratsiya
        i = integratsiya(request.salon)
        return Response({**sozlama_json(sozlama(request.salon)),
                         # integratsiyalardan xodimga kerakli, maxfiy bo'lmagan belgilar
                         'fiskal_eslatma': i.fiskal_eslatma, 'fiskal_izoh': i.fiskal_izoh,
                         'tolov_havolasi': bool((i.click_service_id and i.click_merchant_id) or i.payme_merchant_id)})

    @transaction.atomic
    def patch(self, request):
        ser = SozlamaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        s = sozlama(request.salon)
        yangi = {**sozlama_json(s), **ser.validated_data}
        if not (yangi['zalog_pul'] or yangi['zalog_hujjat'] or yangi['zalog_tillo']):
            return Response({'detail': 'Kamida bitta zalog turi yoqilgan bo\'lishi kerak.'}, status=400)
        if yangi['kechikish_jarimasi'] and yangi['kechikish_kunlik_summa'] <= 0:
            return Response({'detail': 'Kechikish jarimasi yoqilsa, kunlik summa kiritilishi kerak.'}, status=400)
        for nom, qiymat in ser.validated_data.items():
            eski = getattr(s, nom)
            if eski != qiymat:  # har bir o'zgarish jurnalga yoziladi (4.16)
                jurnalga_yoz(request.salon, request.user, 'sozlama_ozgardi', nom, eski, qiymat)
                setattr(s, nom, qiymat)
        s.save()
        return Response(sozlama_json(s))


# --- Xodimlar (FT-22.3) ---

PIN = serializers.RegexField(r'^\d{4,6}$', error_messages={'invalid': 'PIN 4–6 ta raqam bo\'lishi kerak.'})


def xodim_json(x):
    return {'id': x.id, 'ism': x.ism, 'telefon': x.telefon, 'rol': x.rol, 'faol': x.faol,
            'bloklangan': x.bloklangan, 'telegram_ulangan': bool(x.telegram_id)}


def _xodim_limiti_tolgan(salon, chiqarib=None):
    """Tarifdagi xodimlar limiti to'lganmi (tarif belgilanmagan bo'lsa cheklov yo'q)."""
    if not salon.tarif_id:
        return False
    qs = Xodim.objects.filter(salon=salon, faol=True)
    if chiqarib is not None:
        qs = qs.exclude(id=chiqarib.id)
    return qs.count() >= salon.tarif.xodim_limit


def _oxirgi_rahbar(salon, xodim):
    """Salonda kamida bitta faol rahbar qolishi shart — aks holda hech kim sozlamalarga kira olmaydi."""
    return (xodim.rol == Xodim.Rol.RAHBAR and xodim.faol
            and not Xodim.objects.filter(salon=salon, rol=Xodim.Rol.RAHBAR, faol=True).exclude(id=xodim.id).exists())


class XodimlarBoshqaruvView(APIView):
    permission_classes = [IsRahbar]

    def get(self, request):
        qs = Xodim.objects.filter(salon=request.salon).order_by('-faol', 'ism')
        return Response([xodim_json(x) for x in qs])

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)

        class S(serializers.Serializer):
            ism = serializers.CharField(max_length=200)
            telefon = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
            rol = serializers.ChoiceField(choices=Xodim.Rol.choices, default=Xodim.Rol.SOTUVCHI)
            pin = PIN

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        if _xodim_limiti_tolgan(request.salon):
            return Response({'detail': f"Tarif bo'yicha xodimlar limiti ({request.salon.tarif.xodim_limit}) to'lgan."},
                            status=409)
        if Xodim.objects.filter(salon=request.salon, ism__iexact=d['ism'].strip(), faol=True).exists():
            return Response({'detail': 'Bu ismli faol xodim bor — kirish ekranida adashtiriladi.'}, status=409)
        x = Xodim(salon=request.salon, ism=d['ism'].strip(), telefon=d['telefon'], rol=d['rol'])
        x.set_pin(d['pin'])
        x.save()
        jurnalga_yoz(request.salon, request.user, 'xodim_qoshildi', f'xodim {x.ism}', '', x.rol)
        return Response(xodim_json(x), status=201)


class XodimBoshqaruvView(APIView):
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def _xodim(self, request, pk):
        x = Xodim.objects.filter(salon=request.salon, id=pk).first()
        if not x:
            raise NotFound('Xodim topilmadi.')
        return x

    @transaction.atomic
    def patch(self, request, pk):
        class S(serializers.Serializer):
            ism = serializers.CharField(max_length=200, required=False)
            telefon = serializers.CharField(max_length=20, required=False, allow_blank=True)
            rol = serializers.ChoiceField(choices=Xodim.Rol.choices, required=False)
            faol = serializers.BooleanField(required=False)
            pin = serializers.RegexField(r'^\d{4,6}$', required=False,
                                         error_messages={'invalid': 'PIN 4–6 ta raqam bo\'lishi kerak.'})
            blokdan_chiqar = serializers.BooleanField(required=False)

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        x = self._xodim(request, pk)
        if 'ism' in d:
            d['ism'] = d['ism'].strip()
            if d['ism'].lower() != x.ism.lower() and Xodim.objects.filter(
                    salon=request.salon, ism__iexact=d['ism'], faol=True).exclude(id=x.id).exists():
                return Response({'detail': 'Bu ismli faol xodim bor — kirish ekranida adashtiriladi.'}, status=409)
        if _oxirgi_rahbar(request.salon, x) and (d.get('faol') is False or d.get('rol', x.rol) != Xodim.Rol.RAHBAR):
            return Response({'detail': 'Salonda kamida bitta faol rahbar qolishi kerak.'}, status=409)
        if d.get('faol') is True and not x.faol and _xodim_limiti_tolgan(request.salon, chiqarib=x):
            return Response({'detail': "Tarif bo'yicha xodimlar limiti to'lgan."}, status=409)
        for nom in ('ism', 'telefon', 'rol', 'faol'):
            if nom in d and getattr(x, nom) != d[nom]:
                jurnalga_yoz(request.salon, request.user, f'xodim_{nom}_ozgardi', f'xodim {x.ism}',
                             getattr(x, nom), d[nom])
                setattr(x, nom, d[nom])
        if 'pin' in d:  # rahbar PIN ni tiklaydi; eski PIN ko'rinmaydi va jurnalga yozilmaydi (FT-1.7)
            x.set_pin(d['pin'])
            x.xato_urinish, x.bloklangan_gacha = 0, None
            jurnalga_yoz(request.salon, request.user, 'xodim_pin_tiklandi', f'xodim {x.ism}')
        if d.get('blokdan_chiqar'):
            x.xato_urinish, x.bloklangan_gacha = 0, None
        x.save()
        return Response(xodim_json(x))


class XodimTelegramUlashView(APIView):
    """Rahbar istalgan xodim uchun Telegram ulash kodini yaratadi (FT-4.14).

    Kodni xodimning o'zi emas, rahbar olaveradi — chunki xodimning ilovasida ham shu
    «Telegramni ulash» bor, lekin yangi xodim hali kirish ma'lumotini olmagan bo'lishi mumkin.
    """
    permission_classes = [IsRahbar]

    def post(self, request, pk):
        x = Xodim.objects.filter(salon=request.salon, id=pk).first()
        if not x:
            raise NotFound('Xodim topilmadi.')
        u = ulash_kodi_yarat(x)
        bot = telegram.bot_nomi(request.salon)
        return Response({'kod': u.kod, 'tugaydi': u.tugaydi, 'bot': bot,
                         'havola': f'https://t.me/{bot}?start={u.kod}' if bot else None}, status=201)


class SalonRekvizitView(APIView):
    """Salon brendi va shartnoma rekvizitlari (FT-22.6). O'qish — har bir xodim, o'zgartirish — rahbar."""
    MAYDONLAR = ('nomi', 'yuridik_nom', 'stir', 'manzil', 'telefon', 'rang')

    def get_permissions(self):
        return [IsStaff()] if self.request.method == 'GET' else [IsRahbar(), SalonYozishRuxsati()]

    def get(self, request):
        return Response({m: getattr(request.salon, m) for m in self.MAYDONLAR})

    def patch(self, request):
        class S(serializers.Serializer):
            nomi = serializers.CharField(max_length=200, required=False)
            yuridik_nom = serializers.CharField(max_length=200, required=False, allow_blank=True)
            stir = serializers.RegexField(r'^\d{9}$|^$', required=False,
                                          error_messages={'invalid': "STIR 9 ta raqam bo'lishi kerak."})
            manzil = serializers.CharField(max_length=300, required=False, allow_blank=True)
            telefon = serializers.CharField(max_length=20, required=False, allow_blank=True)
            rang = serializers.RegexField(r'^#[0-9a-fA-F]{6}$', required=False,
                                          error_messages={'invalid': "Rang #RRGGBB ko'rinishida bo'lishi kerak."})

        ser = S(data=request.data)
        ser.is_valid(raise_exception=True)
        salon = request.salon
        for nom, qiymat in ser.validated_data.items():
            if getattr(salon, nom) != qiymat:
                jurnalga_yoz(salon, request.user, 'salon_rekvizit_ozgardi', nom, getattr(salon, nom), qiymat)
                setattr(salon, nom, qiymat)
        salon.save()
        return Response({m: getattr(salon, m) for m in self.MAYDONLAR})


# --- Ishonchli qurilmalar (FT-22.2) ---

def qurilma_json(q):
    return {'id': q.id, 'nomi': q.nomi, 'modeli': q.modeli, 'qoshilgan': q.qoshilgan, 'tasdiqlangan': q.tasdiqlangan,
            'oxirgi_kirish': q.oxirgi_kirish, 'filial': q.filial_id}


class QurilmalarView(APIView):
    """Rahbar ishonchli qurilmalarni ko'radi: ruxsat kutayotganlar va faollar."""
    permission_classes = [IsRahbar]

    def get(self, request):
        qs = IshonchliQurilma.objects.filter(salon=request.salon, faol=True).order_by('tasdiqlangan', '-qoshilgan')
        return Response([qurilma_json(q) for q in qs])


class QurilmaView(APIView):
    """PATCH {tasdiq: true} — ruxsat berish; DELETE — qurilmani ro'yxatdan chiqarish (sessiyalari ham yopiladi)."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def _q(self, request, pk):
        q = IshonchliQurilma.objects.filter(salon=request.salon, id=pk, faol=True).first()
        if not q:
            raise NotFound('Qurilma topilmadi.')
        return q

    def patch(self, request, pk):
        q = self._q(request, pk)
        if request.data.get('tasdiq') is True and not q.tasdiqlangan:
            from apps.notify.services import qurilma_tasdiqla  # Telegram havolasi tokenini ham bekor qiladi
            qurilma_tasdiqla(q, request.user)
        if 'filial' in request.data:  # qurilmani filialga biriktirish (yoki null — biriktirmaslik)
            from .models import Filial
            fid = request.data.get('filial')
            filial = Filial.objects.filter(salon=request.salon, id=fid, faol=True).first() if fid else None
            if fid and not filial:
                raise NotFound('Filial topilmadi.')
            q.filial = filial
            q.save(update_fields=['filial'])
        return Response(qurilma_json(q))

    def delete(self, request, pk):
        from apps.notify.services import qurilma_chiqar  # Telegram tugmasi bilan bir xil qoida va qulf
        xato = qurilma_chiqar(self._q(request, pk), request.user)
        if xato:
            return Response({'detail': xato}, status=409)
        return Response(status=204)


class SalonParolView(APIView):
    """Rahbar salon parolini o'zgartiradi (FT-22.2). Yangi qurilmalar yangi parol bilan kiradi."""
    permission_classes = [IsRahbar, SalonYozishRuxsati]

    def post(self, request):
        parol = serializers.CharField(min_length=8, max_length=128).run_validation(request.data.get('parol'))
        request.salon.set_parol(parol)
        request.salon.save(update_fields=['parol'])
        jurnalga_yoz(request.salon, request.user, 'salon_paroli_ozgardi', 'salon')
        return Response({'ok': True})


# --- Yordam ruxsati (FT-22.5) ---

class YordamRuxsatiView(APIView):
    """Rahbar platforma egasiga muddatli ko'rish ruxsatini beradi yoki bekor qiladi."""
    permission_classes = [IsRahbar]

    def get(self, request):
        r = YordamRuxsati.amaldagi(request.salon)
        return Response({'amalda': bool(r), 'tugaydi': r.tugaydi if r else None})

    def post(self, request):
        if not SalonYozishRuxsati().has_permission(request, self):
            return Response({'detail': "Salon «faqat ko'rish» rejimida."}, status=403)
        soat = serializers.IntegerField(min_value=1, max_value=72).run_validation(request.data.get('soat'))
        YordamRuxsati.objects.filter(salon=request.salon, bekor_qilingan=False).update(bekor_qilingan=True)
        r = YordamRuxsati.objects.create(salon=request.salon, bergan=request.user,
                                         tugaydi=timezone.now() + timedelta(hours=soat))
        jurnalga_yoz(request.salon, request.user, 'yordam_ruxsati_berildi', 'platforma egasi', '', f'{soat} soat')
        return Response({'amalda': True, 'tugaydi': r.tugaydi}, status=201)

    def delete(self, request):
        n = YordamRuxsati.objects.filter(salon=request.salon, bekor_qilingan=False).update(bekor_qilingan=True)
        if n:
            jurnalga_yoz(request.salon, request.user, 'yordam_ruxsati_bekor_qilindi', 'platforma egasi')
        return Response({'amalda': False, 'tugaydi': None})


# --- Boshlash ro'yxati (FT-22.7, soddalashtirilgan sozlash ustasi) ---

class BoshlashView(APIView):
    """Yangi salon rahbari uchun qadamlar: brend/rekvizit, xodimlar, kategoriyalar, birinchi liboslar."""
    permission_classes = [IsRahbar]

    def get(self, request):
        from apps.catalog.models import Kategoriya, Libos
        s = request.salon
        qadamlar = [
            {'kalit': 'rekvizit', 'nomi': 'Salon rekvizitlarini kiriting (shartnoma uchun)',
             'bajarildi': bool(s.yuridik_nom and s.manzil), 'bolim': 'sozlamalar'},
            {'kalit': 'xodimlar', 'nomi': "Sotuvchilarni qo'shing va PIN bering",
             'bajarildi': Xodim.objects.filter(salon=s, faol=True).count() > 1, 'bolim': 'sozlamalar'},
            {'kalit': 'kategoriyalar', 'nomi': 'Kategoriyalarni tekshiring',
             'bajarildi': Kategoriya.objects.filter(salon=s).exists(), 'bolim': 'katalog'},
            {'kalit': 'liboslar', 'nomi': "Birinchi liboslarni rasmi va tannarxi bilan qo'shing",
             'bajarildi': Libos.objects.filter(salon=s).exists(), 'bolim': 'katalog'},
        ]
        return Response({'korsatilsin': not s.boshlash_yopilgan and not all(q['bajarildi'] for q in qadamlar),
                         'qadamlar': qadamlar})

    def post(self, request):
        request.salon.boshlash_yopilgan = True
        request.salon.save(update_fields=['boshlash_yopilgan'])
        return Response({'korsatilsin': False})

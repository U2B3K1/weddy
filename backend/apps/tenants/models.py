import datetime
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class Tarif(models.Model):
    """Obuna tarifi: xodimlar va filiallar soni bo'yicha limit (FT-22.8)."""
    nomi = models.CharField(max_length=100, unique=True)
    oylik_narx = models.PositiveIntegerField(default=0)
    xodim_limit = models.PositiveSmallIntegerField(default=10)
    filial_limit = models.PositiveSmallIntegerField(default=1)
    faol = models.BooleanField(default=True)

    def __str__(self):
        return self.nomi


class PlatformaAdmini(models.Model):
    """Platforma egasi: salonlarni ulaydi va obunani boshqaradi; salon ichidagi ma'lumotni ko'rmaydi (FT-22.5)."""
    login = models.CharField(max_length=64, unique=True)
    parol = models.CharField(max_length=128)
    ism = models.CharField(max_length=200, blank=True)
    faol = models.BooleanField(default=True)
    xato_urinish = models.PositiveSmallIntegerField(default=0)
    bloklangan_gacha = models.DateTimeField(null=True, blank=True)

    is_authenticated = True

    def set_parol(self, raw):
        self.parol = make_password(raw)

    def check_parol(self, raw):
        return check_password(raw, self.parol)


class Ariza(models.Model):
    """Bosh sahifadan qoldirilgan so'rov: salonni ulash («a'zo bo'lish») yoki oddiy xabar. Platforma egasi ko'radi."""
    class Tur(models.TextChoices):
        AZO = 'azo', "A'zo bo'lish"
        ALOQA = 'aloqa', "Bog'lanish"

    tur = models.CharField(max_length=8, choices=Tur.choices, default=Tur.AZO)
    ism = models.CharField(max_length=200)
    telefon = models.CharField(max_length=20)
    salon_nomi = models.CharField(max_length=200, blank=True)
    xabar = models.CharField(max_length=1000, blank=True)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    korilgan = models.BooleanField(default=False)

    class Meta:
        ordering = ['korilgan', '-yaratilgan']


class PlatformaSozlama(models.Model):
    """Platforma darajasidagi umumiy sozlamalar (bitta qator).

    Telegram: butun platformaga **bitta** Libosa boti xizmat qiladi (FT-4.14) — har bir salon o'z botini
    yuritishi kerak emas (100 salon = 100 bot navbat bilan tinglanadi, BotFather ham akkauntga ~20 bot beradi).
    Tokenni platforma egasi panel orqali kiritadi; bo'sh bo'lsa `settings.TELEGRAM_BOT_TOKEN` (.env) ishlatiladi.

    Integratsiya kabi token bazada ochiq saqlanadi (serverning o'zi ishlatadi), lekin API orqali qaytarilmaydi
    va jurnalga yozilmaydi. Salon FK yo'q — shu sababli salon arxivi va o'chirishga tushmaydi (arxiv.py).
    """
    telegram_token = models.CharField(max_length=100, blank=True)
    telegram_bot_nomi = models.CharField(max_length=32, blank=True)
    # Platforma egasining botga ulangan Telegram akkaunti: a'zo bo'lish so'rovlari shu chatga boradi.
    telegram_chat_id = models.BigIntegerField(null=True, blank=True)
    # Egasini botga ulash uchun bir martalik kod (`/start <kod>`); muddati o'tgach yaroqsiz.
    telegram_ulash_kod = models.CharField(max_length=16, blank=True)
    telegram_ulash_tugaydi = models.DateTimeField(null=True, blank=True)


def platforma_sozlama():
    """Platforma sozlamalari (bitta qator); hali yaratilmagan bo'lsa bo'sh holda yaratiladi."""
    return PlatformaSozlama.objects.get_or_create(id=1)[0]


class Salon(models.Model):
    class Holat(models.TextChoices):
        SINOV = 'sinov', 'Sinov'
        FAOL = 'faol', 'Faol'
        FAQAT_KORISH = 'faqat_korish', "Faqat ko'rish"
        BLOKLANGAN = 'bloklangan', 'Bloklangan'

    nomi = models.CharField(max_length=200)
    login = models.CharField(max_length=64, unique=True)
    parol = models.CharField(max_length=128)
    manzil = models.CharField(max_length=300, blank=True)
    rang = models.CharField(max_length=9, default='#8b5e83')
    # Shartnoma rekvizitlari (FT-22.6)
    yuridik_nom = models.CharField(max_length=200, blank=True)
    stir = models.CharField(max_length=20, blank=True)
    telefon = models.CharField(max_length=20, blank=True)
    holat = models.CharField(max_length=16, choices=Holat.choices, default=Holat.SINOV)
    yaratilgan = models.DateTimeField(auto_now_add=True)
    # Obuna (FT-22.8). Ikkala sana ham bo'sh bo'lsa muddat cheklanmagan (masalan, demo salon).
    tarif = models.ForeignKey(Tarif, null=True, blank=True, on_delete=models.SET_NULL, related_name='salonlar')
    sinov_tugaydi = models.DateField(null=True, blank=True)
    obuna_tugaydi = models.DateField(null=True, blank=True)
    rahbar_telefon = models.CharField(max_length=20, blank=True)
    oxirgi_kirish = models.DateTimeField(null=True, blank=True)
    # Salon parolini tanlab topishga qarshi (PIN bilan bir xil qoida)
    kirish_xato = models.PositiveSmallIntegerField(default=0)
    kirish_blok_gacha = models.DateTimeField(null=True, blank=True)
    boshlash_yopilgan = models.BooleanField(default=False)  # boshlash ro'yxati yashirilgan (FT-22.7)
    # Demo/ishtirokchi salonlar uchun: yoqilgan bo'lsa yangi qurilmalar rahbar ruxsatisiz darhol ishonchli bo'ladi
    # (FT-22.2 ni chetlab o'tadi — faqat demo_ezaz kabi sinov salonlarida yoqiladi).
    qurilma_avto_tasdiq = models.BooleanField(default=False)
    # Platformadan chiqish (FT-22.10): shu kundan 90 kun o'tgach ma'lumotlar o'chiriladi
    chiqish_sanasi = models.DateField(null=True, blank=True)
    chiqish_izohi = models.CharField(max_length=300, blank=True)

    OGOHLANTIRISH_KUN = 7  # muddat o'tgach shuncha kun ogohlantirish, keyin «faqat ko'rish»

    def set_parol(self, raw):
        self.parol = make_password(raw)

    def check_parol(self, raw):
        return check_password(raw, self.parol)

    def obuna_muddati(self):
        """To'langan (yoki sinov) davrning oxirgi kuni; cheklanmagan bo'lsa None."""
        sanalar = [d for d in (self.sinov_tugaydi, self.obuna_tugaydi) if d]
        return max(sanalar) if sanalar else None

    def obuna_holati(self, bugun=None):
        """Sanalarga ko'ra holat (FT-22.8): sinov -> faol -> 7 kun ogohlantirish -> faqat ko'rish.

        Bloklangan salonga tegilmaydi. Qaytadi: (holat, ogohlantirishgacha/ko'rishgacha qolgan kun yoki None).
        """
        from datetime import timedelta
        if self.holat == self.Holat.BLOKLANGAN:
            return self.holat, None
        muddat = self.obuna_muddati()
        if muddat is None:
            return self.holat, None
        bugun = bugun or timezone.localdate()
        if bugun <= muddat:
            sinovda = self.obuna_tugaydi is None  # hali birorta to'lov qilinmagan
            return (self.Holat.SINOV if sinovda else self.Holat.FAOL), None
        chegara = muddat + timedelta(days=self.OGOHLANTIRISH_KUN)
        if bugun <= chegara:
            return self.Holat.FAOL, (chegara - bugun).days  # ogohlantirish davri: hali ishlaydi
        return self.Holat.FAQAT_KORISH, 0

    def obunani_yangila(self):
        """Holatni sanalarga moslaydi; o'zgargan bo'lsa saqlaydi. (holat, qolgan_kun) qaytaradi."""
        holat, qolgan = self.obuna_holati()
        if holat != self.holat:
            self.holat = holat
            self.save(update_fields=['holat'])
        return holat, qolgan

    def __str__(self):
        return self.nomi


class SalonModel(models.Model):
    """Barcha salon ma'lumotlari uchun asos: salon identifikatori majburiy (FT-22.4)."""
    salon = models.ForeignKey(Salon, on_delete=models.PROTECT, related_name='+')

    class Meta:
        abstract = True


class Xodim(SalonModel):
    class Rol(models.TextChoices):
        RAHBAR = 'rahbar', 'Rahbar'
        SOTUVCHI = 'sotuvchi', 'Sotuvchi'

    ism = models.CharField(max_length=200)
    telefon = models.CharField(max_length=20, blank=True)
    rol = models.CharField(max_length=16, choices=Rol.choices, default=Rol.SOTUVCHI)
    pin = models.CharField(max_length=128)
    faol = models.BooleanField(default=True)
    xato_urinish = models.PositiveSmallIntegerField(default=0)
    bloklangan_gacha = models.DateTimeField(null=True, blank=True)
    telegram_id = models.BigIntegerField(null=True, blank=True)  # botga ulangan akkaunt (4.14)

    is_authenticated = True  # DRF uchun

    def set_pin(self, raw):
        self.pin = make_password(raw)

    def check_pin(self, raw):
        return check_password(raw, self.pin)

    @property
    def bloklangan(self):
        return bool(self.bloklangan_gacha and self.bloklangan_gacha > timezone.now())

    def __str__(self):
        return self.ism


class Filial(SalonModel):
    """Salon filiali (F1). Soni tarifdagi `filial_limit` bilan cheklanadi (FT-22.8)."""
    nomi = models.CharField(max_length=100)
    manzil = models.CharField(max_length=300, blank=True)
    faol = models.BooleanField(default=True)

    class Meta:
        ordering = ['nomi']

    def __str__(self):
        return self.nomi


class IshonchliQurilma(SalonModel):
    """Salon logini kiritilgan qurilma. Salonning birinchi qurilmasi darhol ishonchli; keyingilari rahbar
    ruxsat bermaguncha kutadi (FT-22.2)."""
    nomi = models.CharField(max_length=100)
    qoshilgan = models.DateTimeField(auto_now_add=True)
    faol = models.BooleanField(default=True)
    tasdiqlangan = models.BooleanField(default=True)
    tasdiqlagan = models.ForeignKey('Xodim', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    oxirgi_kirish = models.DateTimeField(null=True, blank=True)
    # Qurilma (planshet) qaysi filialda turadi: yangi zakaz va libos shu filialga yoziladi
    filial = models.ForeignKey(Filial, null=True, blank=True, on_delete=models.SET_NULL, related_name='qurilmalar')


class YordamRuxsati(SalonModel):
    """Salon rahbari platforma egasiga beradigan muddatli ko'rish ruxsati (FT-22.5)."""
    bergan = models.ForeignKey('Xodim', null=True, on_delete=models.SET_NULL, related_name='+')
    boshlangan = models.DateTimeField(auto_now_add=True)
    tugaydi = models.DateTimeField()
    bekor_qilingan = models.BooleanField(default=False)

    @classmethod
    def amaldagi(cls, salon):
        return cls.objects.filter(salon=salon, bekor_qilingan=False, tugaydi__gt=timezone.now()).first()


class Jurnal(SalonModel):
    """Muhim harakatlar jurnali: kim, qachon, nima o'zgardi (3-bo'lim, FT-3.7, FT-3.8)."""
    xodim = models.ForeignKey(Xodim, null=True, on_delete=models.SET_NULL, related_name='+')
    harakat = models.CharField(max_length=40)
    obyekt = models.CharField(max_length=100)
    eski = models.CharField(max_length=300, blank=True)
    yangi = models.CharField(max_length=300, blank=True)
    vaqt = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-vaqt', '-id']


def jurnalga_yoz(salon, xodim, harakat, obyekt, eski='', yangi=''):
    return Jurnal.objects.create(salon=salon, xodim=xodim, harakat=harakat, obyekt=obyekt,
                                 eski=str(eski)[:300], yangi=str(yangi)[:300])  # uzun qiymat (masalan, shartnoma bandlari) kesiladi


def standart_qaytarish_qoidasi():
    # (olib ketishgacha qolgan kun, avansdan qaytariladigan %), kattasidan kichigiga (FT-17.4)
    return [[30, 100], [7, 50], [0, 0]]


class SalonSozlamalari(models.Model):
    """Admin panel sozlamalari (4.16). 1-bosqichda oltita sozlama ochiq; qolganlari standart qiymatda qotirilgan."""
    salon = models.OneToOneField(Salon, on_delete=models.CASCADE, related_name='sozlamalar')
    bufer_kun = models.PositiveSmallIntegerField(default=1)                 # tozalash uchun (FT-2.4)
    vaqtinchalik_bron_soat = models.PositiveSmallIntegerField(default=24)   # FT-2.5
    zalog_pul = models.BooleanField(default=True)                           # FT-7.1
    zalog_hujjat = models.BooleanField(default=True)
    zalog_tillo = models.BooleanField(default=True)
    kechikish_jarimasi = models.BooleanField(default=False)                 # FT-9.3
    kechikish_kunlik_summa = models.PositiveIntegerField(default=0)
    qaytarish_qoidasi = models.JSONField(default=standart_qaytarish_qoidasi)  # FT-17.4
    libos_tasdigi = models.BooleanField(default=True)                       # FT-3.6
    # Promokodlar (4.18); 3-bosqich sozlamalari
    promokod_tasdiqsiz = models.BooleanField(default=True)        # o'chirilsa promokod ham rahbar tasdig'iga boradi (FT-21.7)
    promokod_chegirma_birga = models.BooleanField(default=False)  # promokod ustiga qo'shimcha chegirma (FT-11.6)
    salonchi_kodlari = models.BooleanField(default=True)          # FT-21.8
    mavsumiy_narx = models.BooleanField(default=False)            # FT-15.2: qoidalar orders.MavsumiyNarx da
    sotuvchi_bonusi = models.BooleanField(default=False)          # FT-15.1
    bonus_foiz = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    primerka = models.BooleanField(default=False)                 # FT-2.8
    mijoz_bahosi = models.BooleanField(default=True)              # FT-9.5, FT-15.4
    # 4.16 ning qolgan sozlamalari
    qulf_daqiqa = models.PositiveSmallIntegerField(default=15)    # libosni qulflash vaqti (FT-2.7)
    sotuvchi_libos_qoshadi = models.BooleanField(default=True)    # libos qo'shish huquqi: ikkalasi / faqat rahbar
    qoplamagan_royxat = models.BooleanField(default=True)         # FT-15.3
    qoplamagan_kun = models.PositiveSmallIntegerField(default=60)
    kunlik_hisobot = models.BooleanField(default=True)            # FT-15.5
    kunlik_hisobot_vaqti = models.TimeField(default=datetime.time(21, 0))
    promokodlar_bolimi = models.BooleanField(default=True)        # 4.18
    manekin = models.BooleanField(default=True)                   # 4.5 raqamli manekin
    # Shartnoma shabloni (4.16): avtomatik bandlardan keyin chiqadigan salonning o'z bandlari [{sarlavha, matn}]
    shartnoma_bandlari = models.JSONField(default=list, blank=True)
    # Har filialda alohida kassa (smena). O'chirilgan bo'lsa salonda bitta umumiy smena (FT-12.7)
    filial_kassasi = models.BooleanField(default=False)
    sms_eslatma = models.BooleanField(default=False)  # mijozga SMS: ertaga olib ketish / qaytarish

    def zalog_turlari(self):
        return [t for t, yoq in (('pul', self.zalog_pul), ('hujjat', self.zalog_hujjat),
                                 ('tillo', self.zalog_tillo)) if yoq]


def sozlama(salon):
    """Salon sozlamalari; hali yaratilmagan bo'lsa standart qiymatlar bilan yaratiladi."""
    s, _ = SalonSozlamalari.objects.get_or_create(salon_id=salon.id if hasattr(salon, 'id') else salon)
    return s


class Integratsiya(models.Model):
    """Salonning tashqi xizmatlari (admin panel → «Integratsiyalar»). Hammasi ixtiyoriy: bo'sh bo'lsa tizim ularsiz ishlaydi.

    Eskiz paroli bazada ochiq saqlanadi (serverning o'zi ishlatishi kerak), lekin API orqali qaytarilmaydi,
    jurnalga va salon arxiviga yozilmaydi.

    Telegram endi bu yerda emas: butun platformaga bitta bot xizmat qiladi — `PlatformaSozlama`.
    """
    salon = models.OneToOneField(Salon, on_delete=models.CASCADE, related_name='integratsiya')
    # SMS (Eskiz.uz): salonning o'z hisobi; bo'sh bo'lsa platforma hisobi (.env)
    eskiz_email = models.CharField(max_length=200, blank=True)
    eskiz_parol = models.CharField(max_length=200, blank=True)
    eskiz_from = models.CharField(max_length=20, blank=True)
    sms_shablon_olib_ketish = models.CharField(max_length=300, blank=True)  # bo'sh — standart shablon
    sms_shablon_qaytarish = models.CharField(max_length=300, blank=True)
    # To'lov havolalari (Click, Payme): faqat ochiq identifikatorlar
    click_service_id = models.CharField(max_length=12, blank=True)
    click_merchant_id = models.CharField(max_length=12, blank=True)
    payme_merchant_id = models.CharField(max_length=32, blank=True)
    # Soliq: buxgalter xulosasi bo'yicha foiz; bo'sh — standart (settings.SOLIQ_FOIZI)
    soliq_foizi = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    soliq_izohi = models.CharField(max_length=500, blank=True)
    # Manekin: fonni ajratish sezgirligi (salon rasmlariga moslash uchun, FT-5.6)
    manekin_fon_farqi = models.PositiveSmallIntegerField(default=38)
    instagram = models.CharField(max_length=200, blank=True)
    # Onlayn kassa / 1C bilan ulanish yo'q: yoqilsa, to'lovdan keyin sotuvchiga fiskal chek haqida eslatma chiqadi
    fiskal_eslatma = models.BooleanField(default=False)
    fiskal_izoh = models.CharField(max_length=300, blank=True)


def integratsiya(salon):
    """Salon integratsiya sozlamalari (birinchi murojaatda bo'sh holda yaratiladi)."""
    salon_id = getattr(salon, 'id', salon)
    return Integratsiya.objects.get_or_create(salon_id=salon_id)[0]

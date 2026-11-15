"""R3B — Qurilmalar va salon paroli (rahbar). Salonga faqat rahbar ruxsat bergan qurilmadan kiriladi.
Urug': uchta qurilma — asosiy planshet, ishdan ketgan xodimning telefoni va ruxsat kutayotgan yangi planshet.
Salon parolini almashtirish o'quv salonida yopiq (host.py), shuning uchun u ko'rsatiladi va vaziyat so'raladi.
Qoidalar kod bilan solishtirilgan: views_admin.QurilmaView, SalonParolView (parol faqat yangi qurilma ulashda kerak)."""
from datetime import timedelta

from django.utils import timezone

from apps.tenants.models import IshonchliQurilma

from .asos import Dars, faqat_rahbar, mezon, nav, savollarni_tekshir, sozlama_qatori

ASOSIY, ESKI, YANGI = 'Kassa plansheti', 'Dilnoza telefoni', 'Yangi planshet'
QATOR = '.soz-qurilma'

SAVOLLAR = [
    {'matn': "Dilnoza ishdan ketdi, telefonini ro'yxatdan chiqardingiz. Lekin u salon logini va parolini biladi. Yana nima qilasiz?",
     'variantlar': [
         ('hech', "Hech narsa — telefoni chiqarildi, shu yetarli", False,
          "Yetarli emas: u parolni biladi va boshqa telefondan kirishga so'rov yubora oladi. Ruxsatingizsiz kira olmaydi, "
          "lekin parolni almashtirib, uni xodimlar ro'yxatida ham o'chirib qo'yish kerak."),
         ('parol', "Salon parolini almashtiraman va Dilnozani xodimlar ro'yxatida o'chirib qo'yaman", True,
          "To'g'ri: eski parol bilan endi so'rov ham yuborib bo'lmaydi, PIN kodi esa ishlamaydi."),
         ('hamma', "Hamma qurilmalarni chiqarib, boshidan ulayman", False,
          "Shart emas: boshqa qurilmalar xavf ostida emas. Parolni almashtirish va xodimni o'chirish kifoya."),
     ]},
    {'matn': "Salon parolini almashtirdingiz. Kassadagi planshet va xodimlarning PIN kodlari bilan nima bo'ladi?",
     'variantlar': [
         ('chiqadi', "Hamma qurilmalar tizimdan chiqib ketadi", False,
          "Chiqmaydi: ruxsat berilgan qurilmalar ishlayveradi. Salon paroli faqat yangi qurilmani ulashda so'raladi."),
         ('ishlaydi', "Hech narsa: ulangan qurilmalar ishlayveradi, PIN kodlar o'zgarmaydi", True,
          "To'g'ri: salon paroli faqat yangi qurilmani ulash uchun. Uni xodimlarga aytish ham shart emas — yangi qurilmani o'zingiz ulaysiz."),
         ('pin', "Xodimlarning PIN kodlari ham bekor bo'ladi", False,
          "PIN — har xodimning o'ziniki, salon paroliga bog'liq emas. Ulangan qurilmalar ham ishlayveradi."),
     ]},
]


def urug(m):
    hozir = timezone.now()

    def q(nomi, modeli, **kw):
        return IshonchliQurilma.objects.create(salon=m.salon, nomi=nomi, modeli=modeli, **kw)

    q(ASOSIY, 'Samsung SM-T505 · Android 13 · Chrome', oxirgi_kirish=hozir)
    eski = q(ESKI, 'Xiaomi Redmi Note 11 · Android 12 · Chrome', oxirgi_kirish=hozir - timedelta(days=40))
    yangi = q(YANGI, 'Samsung SM-X200 · Android 14 · Chrome', tasdiqlangan=False)
    return {'eski': eski.id, 'yangi': yangi.id}


def topshiriq(h):
    return (f"Bugun salonga yangi planshet oldingiz va unga salon loginini kiritdingiz — u ruxsat kutyapti. Unga ruxsat bering. "
            f"«{ESKI}» esa ishdan ketgan xodimniki — uni ro'yxatdan chiqaring.")


def tekshir(m, javob=None):
    yangi = IshonchliQurilma.objects.filter(salon=m.salon, id=m.holat.get('yangi')).first()
    eski = IshonchliQurilma.objects.filter(salon=m.salon, id=m.holat.get('eski')).first()
    if not yangi or not eski:
        return [mezon(False, '', "Qurilmalar topilmadi. Darsni qayta boshlang.")]
    natija = [
        mezon(yangi.faol and yangi.tasdiqlangan, f"«{YANGI}» ga ruxsat berildi — endi xodimlar undan PIN bilan kira oladi.",
              f"«{YANGI}» rad etilgan. U sizning qurilmangiz edi — darsni qayta boshlab, «Ruxsat berish» ni bosing." if not yangi.faol
              else f"«{YANGI}» hali ruxsat kutyapti. «Ruxsat berish» ni bosing."),
        mezon(not eski.faol, f"«{ESKI}» ro'yxatdan chiqarildi — undan endi kirib bo'lmaydi.",
              f"«{ESKI}» hali ro'yxatda. Shu qatordagi «Chiqarish» ni bosing."),
    ]
    if not IshonchliQurilma.objects.filter(salon=m.salon, nomi=ASOSIY, faol=True).exists():
        natija.append(mezon(False, '', f"«{ASOSIY}» ham chiqarib yuborilgan — u salonning ishlab turgan qurilmasi edi. Darsni qayta boshlang."))
    return natija + savollarni_tekshir(SAVOLLAR, javob)


def qadamlar(h):
    return ["Menyuda «Sozlama» ni oching va «Qurilmalar va parol» bo'limiga kiring.",
            f"«{YANGI} — yangi qurilma» qatoridagi «Ruxsat berish» ni bosing.",
            f"«{ESKI}» qatoridagi «Chiqarish» ni bosing va «Ha, chiqarish» bilan tasdiqlang.",
            "Pastdagi ikki savolga javob bering."]


def yol(h):
    return [nav('Sozlama'), sozlama_qatori('Qurilmalar va parol'),
            {'matn': f"«{YANGI} — yangi qurilma» ruxsat kutyapti. Uni bugun o'zingiz ulagansiz — «Ruxsat berish» ni bosing.",
             'amal': 'bos', 'nishon': {'css': f'{QATOR} button', 'matn': 'Ruxsat berish'},
             'tayyor': {'css': '.soz-xabar', 'ichida': 'ruxsat berildi'}},
            {'matn': f"«{ESKI}» — ishdan ketgan xodimniki, 40 kundan beri kirilmagan. Shu qatordagi «Chiqarish» ni bosing.",
             'amal': 'bos', 'nishon': {'css': QATOR, 'ichida': ESKI}, 'ichki': {'css': 'button', 'matn': 'Chiqarish'},
             'tayyor': {'css': '[role=alertdialog]'}},
            {'matn': "Tizim qayta so'raydi: bu qurilmadagi ochiq sessiyalar darhol yopiladi. «Ha, chiqarish» ni bosing.",
             'amal': 'bos', 'nishon': {'css': '[role=alertdialog] button', 'matn': 'Ha, chiqarish'},
             'tayyor': {'css': '.soz-xabar', 'ichida': 'chiqarildi'}},
            {'matn': "Pastda «Salon paroli» turibdi: yangi qurilma salon logini va shu parol bilan so'rov yuboradi. "
                     "Endi ikki savolga javob bering.", 'amal': 'kor', 'nishon': {'css': '.soz-qator', 'ichida': 'Salon paroli'}}]


def bilim(h):
    return [
        "Salon paroli faqat yangi qurilmani ulash uchun kerak. U almashtirilsa, ulangan qurilmalar ishlayveradi va xodimlarning "
        "PIN kodlari o'zgarmaydi.",
        "Xodim ishdan ketsa, uch ish qilinadi: qurilmasi ro'yxatdan chiqariladi, salon paroli almashtiriladi (u parolni biladi) va "
        "o'zi xodimlar ro'yxatida o'chirib qo'yiladi — PIN kodi ishlamasin.",
    ]


DARS = Dars(
    kod='R3B', nomi='Qurilmalar va salon paroli', yonalish='rahbar', personaj='nodira',
    sahifa='Sozlama → Qurilmalar va parol',
    vaziyat="Saloningizga kim kira olishini PIN'dan ham oldin qurilma hal qiladi: ro'yxatda yo'q planshet yoki telefondan "
            "hech kim — hatto PIN'ni bilsa ham — kira olmaydi. Bu ro'yxatni faqat siz yuritasiz.",
    natija="Yangi qurilmaga ruxsat bera olasiz, keraksizini chiqara olasiz va salon parolini qachon almashtirishni bilasiz.",
    xulosa="Qoida uchta: yangi qurilma — faqat o'zingiz ulagan bo'lsangiz ruxsat; xodim ketdi yoki qurilma yo'qoldi — darhol "
           "ro'yxatdan chiqarish (undagi sessiyalar o'sha zahoti yopiladi); parolni begona bilib qoldi — «Salon paroli → "
           "O'zgartirish» (kamida 8 belgi). Parol almashsa, ulangan qurilmalar ishlayveradi. Oxirgi ishonchli qurilmani "
           "tizim chiqartirmaydi — aks holda salonga hech kim kira olmay qolardi.",
    tekshirilgan='2026-11-14 · ishchi nusxa',
    bilim=bilim, urug=urug, topshiriq=topshiriq, tekshir=tekshir, savollar=lambda h: SAVOLLAR, mos=faqat_rahbar,
    ishora="Qurilmalar ro'yxati «Sozlama» ning «Xavfsizlik» guruhida. Ruxsat kutayotgan qurilma ro'yxat boshida turadi.",
    qadamlar=qadamlar, yol=yol, xp=60,
)

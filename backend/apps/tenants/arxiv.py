"""Salon platformadan chiqishi (FT-22.10): ma'lumotlar arxivi va 90 kundan keyin o'chirish."""
from datetime import timedelta

from django.apps import apps
from django.core import serializers
from django.db import models, transaction
from django.db.models.deletion import ProtectedError, RestrictedError
from django.utils import timezone

from .models import Salon

OCHIRISH_KUN = 90
# Arxivga chiqmaydigan maydonlar: parol/PIN xeshlari, kirish kodlari va qurilma belgilari
MAXFIY = {'parol', 'pin', 'kod', 'token', 'belgi', 'kalit', 'telegram_token', 'eskiz_parol'}


class ArxivXatosi(Exception):
    pass


def salon_modellari():
    """`salon` ga bog'langan barcha modellar (SalonModel vorislari va sozlamalar)."""
    natija = []
    for m in apps.get_models():
        if m is Salon:
            continue
        try:
            f = m._meta.get_field('salon')
        except Exception:  # noqa: BLE001 — bunday maydon yo'q
            continue
        if getattr(f, 'related_model', None) is Salon:
            natija.append(m)
    return natija


def ochiriladigan_sana(salon):
    return salon.chiqish_sanasi + timedelta(days=OCHIRISH_KUN) if salon.chiqish_sanasi else None


@transaction.atomic
def salon_chiqdi(salon, izoh=''):
    """Rahbarning yozma so'rovi bilan: salon bloklanadi va 90 kunlik sanoq boshlanadi."""
    salon = Salon.objects.select_for_update().get(id=salon.id)
    if salon.chiqish_sanasi:
        raise ArxivXatosi('Salon allaqachon chiqqan deb belgilangan.')
    if not izoh.strip():
        raise ArxivXatosi("Asosni kiriting (rahbarning yozma so'rovi: sana, kim).")
    salon.chiqish_sanasi, salon.chiqish_izohi, salon.holat = timezone.localdate(), izoh.strip(), Salon.Holat.BLOKLANGAN
    salon.save(update_fields=['chiqish_sanasi', 'chiqish_izohi', 'holat'])
    return salon


@transaction.atomic
def chiqishni_bekor_qilish(salon):
    salon = Salon.objects.select_for_update().get(id=salon.id)
    if not salon.chiqish_sanasi:
        raise ArxivXatosi('Salon chiqqan deb belgilanmagan.')
    salon.chiqish_sanasi, salon.chiqish_izohi, salon.holat = None, '', Salon.Holat.FAOL
    salon.save(update_fields=['chiqish_sanasi', 'chiqish_izohi', 'holat'])
    salon.obunani_yangila()
    return salon


def salon_arxivi(salon):
    """Salonning barcha ma'lumotlari — JSON ga yoziladigan lug'at. Faqat chiqqan salon uchun beriladi."""
    if not salon.chiqish_sanasi:
        raise ArxivXatosi("Arxiv faqat platformadan chiqqan salon uchun beriladi (FT-22.5: egasi salon ma'lumotini ko'rmaydi).")

    def qatorlar(qs):
        natija = []
        for q in serializers.serialize('python', qs):
            maydonlar = {k: v for k, v in q['fields'].items() if k not in MAXFIY}
            natija.append({'id': q['pk'], **maydonlar})
        return natija

    jadvallar = {}
    for m in sorted(salon_modellari(), key=lambda m: m._meta.label):
        jadvallar[m._meta.label] = qatorlar(m.objects.filter(salon=salon).order_by('pk'))
    return {
        'salon': {'id': salon.id, 'nomi': salon.nomi, 'login': salon.login, 'manzil': salon.manzil,
                  'yuridik_nom': salon.yuridik_nom, 'stir': salon.stir, 'telefon': salon.telefon},
        'chiqish_sanasi': salon.chiqish_sanasi, 'ochiriladi': ochiriladigan_sana(salon),
        'yaratilgan': timezone.now(), 'jadvallar': jadvallar,
        'izoh': "Rasmlar fayllari alohida beriladi (media/ papkasi). Parol va PIN xeshlari arxivga kiritilmagan.",
    }


def muddati_otganlar(bugun=None):
    bugun = bugun or timezone.localdate()
    return Salon.objects.filter(chiqish_sanasi__isnull=False, chiqish_sanasi__lte=bugun - timedelta(days=OCHIRISH_KUN))


@transaction.atomic
def salonni_ochirish(salon, bugun=None):
    """Chiqqaniga 90 kun bo'lgan salonni barcha ma'lumoti va fayllari bilan butunlay o'chiradi. Qaytarib bo'lmaydi."""
    bugun = bugun or timezone.localdate()
    sana = ochiriladigan_sana(salon)
    if sana is None or bugun < sana:
        raise ArxivXatosi(f"Salonni o'chirish mumkin emas: chiqqanidan keyin {OCHIRISH_KUN} kun o'tishi kerak.")
    modellar = salon_modellari()
    fayllar = []
    for m in modellar:
        fayl_maydonlari = [f.name for f in m._meta.fields if isinstance(f, models.FileField)]
        if fayl_maydonlari:
            for obj in m.objects.filter(salon=salon):
                fayllar += [getattr(obj, n) for n in fayl_maydonlari if getattr(obj, n)]
    # PROTECT bog'lanishlar tufayli tartib oldindan ma'lum emas: o'chirilmaganlari keyingi aylanishda qayta uriniladi
    kutmoqda = list(modellar)
    for _ in range(len(modellar) + 1):
        qolgan = []
        for m in kutmoqda:
            try:
                with transaction.atomic():
                    m.objects.filter(salon=salon).delete()
            except (ProtectedError, RestrictedError):
                qolgan.append(m)
        if not qolgan:
            break
        kutmoqda = qolgan
    else:
        raise ArxivXatosi("Salon ma'lumotlarini o'chirib bo'lmadi: " + ', '.join(m._meta.label for m in kutmoqda))
    nomi = salon.nomi
    salon.delete()
    # Fayllar baza muvaffaqiyatli tozalangach o'chiriladi
    transaction.on_commit(lambda: [f.storage.delete(f.name) for f in fayllar])
    return nomi

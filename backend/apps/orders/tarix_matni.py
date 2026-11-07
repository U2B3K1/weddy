"""Zakaz o'zgarishlar tarixini odam tilidagi matnga aylantirish (A-18).

Bazada yozuvlar o'zgarmaydi (eski/yangi — xom qiymatlar, rahbarga Telegram xabari ham shulardan); ekranga chiqadigan
matn shu yerda yig'iladi: summalar «2 500 000 so'm», sanalar «24.11.2026», holat va eslatma kodlari — nomi bilan.
"""
import re

from .models import Zakaz

NOMLAR = {
    'sana_kochirildi': "Sana ko'chirildi", 'libos_almashtirildi': 'Libos almashtirildi',
    'aksessuar_qoshildi': "Aksessuar qo'shildi", 'aksessuar_olib_tashlandi': 'Aksessuar olib tashlandi',
    'moslash_narxi': 'Moslash narxi', 'bekor_qilindi': 'Bekor qilindi', 'avtomatik_bekor': "O'zi bekor bo'ldi",
    'boglandi': "Mijoz bilan bog'lanildi", 'tolov_tuzatildi': "To'lov tuzatildi",
    # C-05 (R3): pul va qaror harakatlari ham tarixda
    'chegirma_soraldi': "Chegirma so'raldi", 'chegirma_qarori': 'Chegirma', 'promokod': 'Promokod',
    'berildi': 'Libos berildi', 'qaytarildi': 'Libos qaytarildi', 'qarz_tolandi': "Qarz to'landi",
    'otkazma_kelmadi': "O'tkazma kelmadi", 'salonchi': 'Salonchi', 'chegirma_olib_tashlandi': 'Chegirma olib tashlandi',
}
ESLATMA_TURLARI = {
    'olib_ketish_ertaga': 'ertaga olib ketish', 'qaytarish_bugun': 'bugun qaytarish', 'kechikdi': 'kechikkan qaytarish',
    'primerka_bugun': 'bugungi primerka', 'primerka_ertaga': 'ertangi primerka', 'bron_tugayapti': 'bron tugayapti',
}


def _som(n):
    return f'{int(n):,}'.replace(',', ' ') + " so'm"


def _sanalar(s):
    """2026-11-24 → 24.11.2026"""
    return re.sub(r'\b(\d{4})-(\d{2})-(\d{2})\b', r'\3.\2.\1', s)


def _summalar(s):
    """Uzun xom sonlar → «2 500 000 so'm». QA-14: so'z ichidagi raqam (pasport «AA1234567», artikul), telefon («+998…»),
    sana qismi va kasr pul emas — o'zgarmaydi."""
    return re.sub(r'(?<![\w.+\-])(\d{4,})(?![\w.\-])', lambda m: _som(m.group(1)), _sanalar(s))


def _zalog_matni(s):
    """Berish tarixi «zalog: pul 1000000; hujjat pasport 1234567; tillo uzuk 5.00 g» — summa faqat pul zalogida;
    hujjat raqami (faqat raqamlardan iborat bo'lsa ham) va tillo og'irligi xom qoladi (QA-14)."""
    boshi, _, qismlar = s.partition('zalog: ')
    if not _:
        return _summalar(s)
    return boshi + 'zalog: ' + '; '.join(_summalar(q) if q.startswith('pul ') else q for q in qismlar.split('; '))


def _holat(kod):
    try:
        return Zakaz.Holat(kod).label
    except ValueError:
        return kod


def _jami(s):
    """«L021 (jami 2500000)» → («L021», 2500000); jami bo'lmasa (s, None)."""
    m = re.match(r'^(.*?)\s*\(?jami (\d+)\)?$', s.strip())
    return (m.group(1).strip(), int(m.group(2))) if m else (s, None)


def tarix_matni(harakat, eski, yangi):
    """(nomi, matn) — «Sana ko'chirildi», «24.11.2026 – 25.11.2026 → 26.11.2026 – 27.11.2026»."""
    nomi = NOMLAR.get(harakat, harakat.replace('_', ' ').capitalize())
    eski, yangi = str(eski or ''), str(yangi or '')
    if harakat == 'bekor_qilindi':
        m = re.search(r'qaytarildi (\d+) \((\d+)%\), ushlab qolindi (\d+)', yangi)
        if m:
            qaytdi, foiz, ushlab = int(m.group(1)), m.group(2), int(m.group(3))
            if not qaytdi and not ushlab:
                return nomi, f"{_holat(eski)} edi; to'lov olinmagan"
            return nomi, f"{_holat(eski)} edi; mijozga qaytarildi {_som(qaytdi)} ({foiz}%), ushlab qolindi {_som(ushlab)}"
        return nomi, f'{_holat(eski)} edi'
    if harakat == 'avtomatik_bekor':
        return nomi, "Avans muddatida olinmadi — bron o'zi bekor bo'ldi"
    if harakat == 'boglandi':
        tur = ESLATMA_TURLARI.get(eski)
        return nomi, f"{yangi}{f' ({tur} eslatmasi)' if tur else ''}"
    if harakat == 'chegirma_soraldi':
        miqdor = yangi if yangi.endswith('%') else _summalar(yangi)
        _, jami = _jami(eski)
        return nomi, f"{miqdor} so'raldi" + (f' (jami {_som(jami)})' if jami is not None else '')
    if harakat == 'chegirma_qarori' and (not eski or eski.startswith('jami')):  # tayyor chegirma — so'rovsiz
        return nomi, _summalar(yangi)
    if harakat == 'berildi':
        return nomi, _zalog_matni(yangi) + (f'; {_summalar(eski)}' if eski else '')
    if harakat == 'qarz_tolandi':
        return nomi, _summalar(yangi) + (f' ({_summalar(eski)} edi)' if eski else '')
    if harakat == 'promokod' and eski:  # kod olib tashlandi
        return nomi, f'{eski} {_summalar(yangi)}'
    if harakat == 'salonchi':
        if eski and not yangi:
            return nomi, f'{eski} olib tashlandi'
        return nomi, f'{eski} → {yangi}' if eski else yangi
    if harakat == 'otkazma_kelmadi':
        return nomi, f'{_summalar(eski)} hisobdan chiqdi; {_summalar(yangi)}'
    if harakat == 'moslash_narxi':
        try:
            return nomi, f'{_som(eski or 0)} → {_som(yangi or 0)}'
        except ValueError:
            pass
    if harakat in ('libos_almashtirildi', 'aksessuar_qoshildi', 'aksessuar_olib_tashlandi'):
        (e_nom, e_jami), (y_nom, y_jami) = _jami(eski), _jami(yangi)
        if e_jami is not None and y_jami is not None:
            if harakat == 'libos_almashtirildi':
                qism = f'{e_nom} → {y_nom}'
            else:
                qism = y_nom or e_nom  # qo'shilganda nomi yangida, olib tashlanganda eskida
            narx = f'jami {_som(e_jami)} → {_som(y_jami)}' if e_jami != y_jami else f"jami o'zgarmadi ({_som(y_jami)})"
            return nomi, f'{qism}; {narx}'
    if eski and yangi:
        return nomi, f'{_summalar(eski)} → {_summalar(yangi)}'
    return nomi, _summalar(yangi or eski)

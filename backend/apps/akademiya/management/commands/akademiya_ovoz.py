"""Akademiya bob voqealarini ovozga aylantiradi (Narakeet matndan-nutqqa API) va `frontend/public/akademiya/bob-<kalit>.mp3`
ga yozadi. Matn `BOBLAR` dan olinadi — ekrandagi voqea bilan so'zma-so'z bir xil.

Kalit: `NARAKEET_API_KEY` muhit o'zgaruvchisi (Windows'da foydalanuvchi muhitidan ham o'qiladi). Kalit faqat pullik
(Top-Up yoki hisoblagichli) Narakeet hisobida beriladi; u kodga, faylga va jurnalga yozilmaydi.
API: qisqa matn (1 KB gacha) — bitta so'rov, javob tanasi tayyor MP3 (`accept: application/octet-stream`).
Hujjat: https://www.narakeet.com/docs/automating/text-to-speech-api/

    python manage.py akademiya_ovoz --sinov              # hech narsa yubormaydi: matnlar va hajmini ko'rsatadi
    python manage.py akademiya_ovoz                      # ovozi yo'q boblar uchun yaratadi
    python manage.py akademiya_ovoz --bob kassa --qayta  # bitta bobni qayta yozadi
    python manage.py akademiya_ovoz --film --qayta       # kirish filmi ovozi (matn Kino.jsx dagi subtitrlardan)

Ega tanlagan ovoz (2026-11-14): Narakeet «Shavkat» — bob voqealari ham, kirish filmi ham shu ovozda.
ffmpeg o'rnatilgan bo'lsa, fayl 64 kbit/s mono ga ixchamlanadi (sahifa yengil bo'lishi uchun).
"""
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.akademiya.darslar import BOBLAR

MANZIL = 'https://api.narakeet.com/text-to-speech/mp3'
MAKS_BAYT = 1024  # qisqa matn API chegarasi


def kalit():
    k = os.environ.get('NARAKEET_API_KEY')
    if not k and os.name == 'nt':  # Windows: «setx» bilan qo'yilgan o'zgaruvchi yangi terminal ochilmaguncha ko'rinmaydi
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
                k = winreg.QueryValueEx(h, 'NARAKEET_API_KEY')[0]
        except OSError:
            k = None
    if not k:
        raise CommandError("NARAKEET_API_KEY topilmadi. Narakeet hisobida API kalit yarating va uni muhit o'zgaruvchisiga qo'ying.")
    return k


def ovoz_yarat(matn, ovoz, tezlik, api_kalit):
    """Matnni MP3 ga aylantiradi: (baytlar, davomiyligi soniyada). Xato bo'lsa — CommandError (kalit matnga tushmaydi)."""
    tana = matn.encode('utf-8')
    if len(tana) > MAKS_BAYT:
        raise CommandError(f"Matn {len(tana)} bayt — qisqa matn API chegarasi {MAKS_BAYT} bayt.")
    sorov = urllib.request.Request(
        f'{MANZIL}?{urllib.parse.urlencode({"voice": ovoz, "voice-speed": tezlik})}', data=tana, method='POST',
        headers={'Content-Type': 'text/plain', 'x-api-key': api_kalit, 'accept': 'application/octet-stream'})
    try:
        with urllib.request.urlopen(sorov, timeout=60) as j:
            return j.read(), j.headers.get('x-duration-seconds')
    except urllib.error.HTTPError as e:
        tana = e.read().decode('utf-8', 'replace')
        try:
            xabar = json.loads(tana).get('message') or tana
        except ValueError:
            xabar = tana
        raise CommandError(f'Narakeet {e.code}: {xabar[:300]}') from None
    except urllib.error.URLError as e:
        raise CommandError(f"Narakeet bilan aloqa bo'lmadi: {e.reason}") from None


class Command(BaseCommand):
    help = "Akademiya bob voqealari uchun ovoz yaratadi (Narakeet)."

    def add_arguments(self, p):
        p.add_argument('--ovoz', default='shavkat', help="Narakeet ovozi (o'zbekcha: shavkat, zulfiya, dilnoza, odina, gulnora)")
        p.add_argument('--film', action='store_true', help="Bob voqealari o'rniga kirish filmi matnlari (kino-N.mp3)")
        p.add_argument('--tezlik', default='1', help="O'qish tezligi, masalan 0.95 yoki 1.1")
        p.add_argument('--bob', action='append', help="Faqat shu bob(lar) kaliti; ko'rsatilmasa — hammasi")
        p.add_argument('--qayta', action='store_true', help="Fayli bor bobni ham qayta yozadi")
        p.add_argument('--sinov', action='store_true', help="Hech narsa yubormaydi: qaysi matn yuborilishini ko'rsatadi")
        p.add_argument('--papka', default=str(Path(settings.BASE_DIR).parent / 'frontend' / 'public' / 'akademiya'))

    def handle(self, *a, **o):
        papka = Path(o['papka'])
        kalitlar = {b[0] for b in BOBLAR}
        if o['bob'] and set(o['bob']) - kalitlar:
            raise CommandError(f"Noma'lum bob: {', '.join(sorted(set(o['bob']) - kalitlar))}. Bor: {', '.join(b[0] for b in BOBLAR)}")
        if o['film']:
            # film matnlari bitta joyda — subtitr sifatida Kino.jsx da; ovoz o'sha matndan yoziladi
            manba = (Path(settings.BASE_DIR).parent / 'frontend' / 'src' / 'akademiya' / 'Kino.jsx').read_text(encoding='utf-8')
            matnlar = re.findall(r'matn: "([^"]+)"', manba)  # sahna matnlari qo'shtirnoqda, ichida qo'shtirnoq yo'q
            if not matnlar:
                raise CommandError("Kino.jsx dan film matnlari topilmadi.")
            hammasi = [(f'kino-{n}', m) for n, m in enumerate(matnlar, 1)]
        else:
            hammasi = [(f'bob-{kalit_}', voqea) for kalit_, _n, _s, _i, voqea, _k in BOBLAR if not o['bob'] or kalit_ in o['bob']]
        ishlar = [(nom, m) for nom, m in hammasi if o['qayta'] or not (papka / f'{nom}.mp3').exists()]
        if not ishlar:
            self.stdout.write("Hammasining ovozi bor. Qayta yozish uchun --qayta.")
            return
        if o['sinov']:
            for k, voqea in ishlar:
                self.stdout.write(f'{k}.mp3 ← {len(voqea.encode("utf-8"))} bayt: {voqea}')
            self.stdout.write(f"Jami {len(ishlar)} ta so'rov, ovoz «{o['ovoz']}». Hech narsa yuborilmadi (--sinov).")
            return
        api_kalit = kalit()
        papka.mkdir(parents=True, exist_ok=True)
        for k, voqea in ishlar:
            baytlar, soniya = ovoz_yarat(voqea, o['ovoz'], o['tezlik'], api_kalit)
            fayl = papka / f'{k}.mp3'
            fayl.write_bytes(baytlar)
            if shutil.which('ffmpeg'):  # ixchamlash: 64 kbit/s mono
                vaqtincha = fayl.with_suffix('.tmp.mp3')
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(fayl), '-ac', '1', '-b:a', '64k', str(vaqtincha)], check=True)
                vaqtincha.replace(fayl)
            self.stdout.write(f'{k}.mp3 — {soniya or "?"} s, {fayl.stat().st_size // 1024} KB')
        self.stdout.write("Tayyor. Yangi boblar kalitini frontend/src/akademiya/DarsPaneli.jsx dagi OVOZ_BOR ga qo'shing.")

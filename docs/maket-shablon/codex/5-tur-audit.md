39 artboard skrinshoti, HTML manbalari va qoidalarni ko‘rdim. Asosiy muammolar — hisoblash izohi, ekranlar orasidagi ziddiyatlar va kichik boshqaruvlar. Fayllar o‘zgartirilmadi. Quyidagi fayllar `docs/maket-shablon/project/` ichida.

1. **Yuqori — bonus va kassa usuli zid tushuntirilgan.** `SozlamaBolim.dc.html` → «Sotuvchi bonusi»: «Foydadan o‘zi ayiriladi» deyiladi. `HisobotBonus.dc.html` → KPI: 315 000 hisoblangan, hali to‘lanmagan; `Foyda.dc.html` esa pul chiqqan kundagi hisobni va’da qiladi. Avtomatik ayirish **bonus to‘langanida** bo‘lishini aniq yozish kerak; aks holda egasi «qancha ishladim»ga ikki xil javob oladi.

2. **Yuqori — avans foizi bir xil emas.** `SozlamaZakaz.dc.html` → «Avans miqdori»: **20%**. `YangiZakaz.dc.html` va `YangiZakazMijoz.dc.html` → xulosa: **30%, 600 000**. Mira uchun sozlamadagi qiymat bilan 400 000 chiqishi kerak.

3. **O‘rta — mavjud liboslar soni qadamlar orasida o‘zgaradi.** `YangiZakazSana.dc.html` → 22–23 noyabr xulosasi: **6 ta bo‘sh**; `YangiZakaz.dc.html` → sarlavha: **5 ta**. Zarina «21-noyabrgacha band» bo‘lsa ham tanlab bo‘lmaydi. Tozalash buferi sabab bo‘lsa, keyingi bo‘sh sanani ko‘rsating.

4. **O‘rta — amaldagi sana filtri grafikda aniq emas.** `HisobotGrafik.dc.html` → KPI davri noyabr 2025–oktabr 2026, sarlavha «Oxirgi 12 oy»; `Foyda.dc.html` → noyabr ham mavjud. «Oxirgi 12 **yopilgan** oy» yorlig‘i to‘liq va joriy oylarni adashtirmaydi.

5. **O‘rta — tegish maydonlari kichik.** `SozlamaBolim.dc.html` → `.qadam button`: **34×34 px**, `.switch`: **46×26 px**, ichki menyu: **32 px** balandlik. `LibosQoshish.dc.html` → o‘lcham va kategoriya tanlovlari ham ixcham. Ayniqsa sensorli qurilmada bosiladigan hududlarni kamida 44 px qiling; ko‘rinadigan ikonka kichik qolishi mumkin.

6. **O‘rta — rang faqat holat uchun ishlatilmagan.** `HisobotBonus.dc.html` → «Bonus stavkasi» binafsha; `HisobotXarajat.dc.html` → «Doimiy» ko‘k. Bular holat emas. `Liboslar.dc.html` → «Bugun beriladi» tilla, `Bandlik.dc.html` → «Beriladi/Qaytadi» raqamlari tilla/ko‘k: 2-qoidaga zid. Harakatni rangsiz, bronni alohida holat sifatida ko‘rsating.

7. **O‘rta — tasdiqlangan xarajat ortiqcha ajratilgan.** `KassaBolim.dc.html` → «Bugungi xarajatlar», «Tasdiqlangan» yashil nishon. `HisobotXarajat.dc.html`da shu holat rangsiz. 13-qoidaga muvofiq oddiy tasdiq rangsiz, «kutilmoqda» ajratilgan bo‘lsin.

8. **O‘rta — donalar holatini rangdan ajratish qiyin.** `LibosBolim.dc.html` → «Donalar»: bo‘sh/bron/mijozda kvadratlari shaklan bir xil. `title` va `aria-label` bor, lekin sensorli ekranda tooltipga tayanib bo‘lmaydi. Ta’mir va yo‘qolishdagi naqsh yechimini boshqa holatlarga ham kengaytiring.

9. **O‘rta — jadvalda qiymat noto‘g‘ri tekislangan.** `SozlamaNarx.dc.html` → promokodlar, «Chegirma» ustunidagi 10%, 200 000 so‘m, 15% chapga tekislangan. O‘ngga tekislash summalarni tez solishtirishga yordam beradi.

10. **Past — ritm va qisqarish.** `LibosBolim.dc.html` → KPI: 14 px oraliq, 18 px yon padding; sanoq panelida 20 px oraliq — 11-qoidaga mos emas. `Bandlik.dc.html` → Bella katagidagi «#14 Ma…» nomni kesadi; tanlanganda to‘liq tafsilot chiqishi bu muammoni yumshatadi.

**Tegmaslik kerak:**

- `Main.dc.html`: uch asosiy savol → «Hozir» → «Davr bo‘yicha» tartibi.
- `ZakazKarta.dc.html`: olinadigan qoldiq yonidagi bitta asosiy to‘lov tugmasi.
- `LibosSanoq.dc.html`: topilmaganlar, boshqa joydagilar va oxirgi belgilanganlarni ajratish.

**Yakuniy shrift tavsiyam — Manrope.** Matn, jadval va KPI’larda Manrope, sarlavhalarda Forum, qisqa urg‘ularda Cormorant kursiv qolsin. `Shrift.png`dagi 390 px namunada Manrope 13–14 px matn va summalarni tezroq skanerlashga yordam beradi; o‘zbekcha apostroflar ham ravshan. Raqamlarga `tabular-nums` qo‘llang; apostrof belgilarini loyiha bo‘ylab birxillashtiring. Hashamat tuyg‘usini Forum, Cormorant va mavjud ranglar yetarlicha beradi.
import { useEffect, useState } from 'react'
import { integratsiyaSaqla, integratsiyalar, xatoMatni } from '../api'

const MANBA = { salon: 'ulangan (salon hisobi)', platforma: 'ulangan (platforma hisobi)', yoq: 'ulanmagan' }

// Tashqi xizmatlar: hammasi ixtiyoriy. Hech biri kiritilmasa ham tizim to'liq ishlaydi —
// faqat Telegram/SMS yuborilmaydi, to'lov havolasi chiqmaydi, soliq standart foizda hisoblanadi.
export default function Integratsiyalar() {
  const [d, setD] = useState(null)
  const [f, setF] = useState({})
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  useEffect(() => { integratsiyalar().then(setD).catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [])
  if (!d) return <p className="malumot">{xabar.matn || 'Yuklanmoqda…'}</p>

  const q = (k) => f[k] ?? d[k] ?? ''
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const saqla = async (maydonlar) => {
    setXabar({ turi: '', matn: '' })
    const tana = {}
    for (const k of maydonlar) if (k in f) tana[k] = f[k] === '' && k === 'soliq_foizi' ? null : f[k]
    if (Object.keys(tana).length === 0) return setXabar({ turi: 'ok', matn: "O'zgarish yo'q." })
    try {
      setD(await integratsiyaSaqla(tana))
      setF((eski) => Object.fromEntries(Object.entries(eski).filter(([k]) => !maydonlar.includes(k))))
      setXabar({ turi: 'ok', matn: 'Saqlandi.' })
    } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) }
  }
  const tozala = async (k, nom) => {
    try { setD(await integratsiyaSaqla({ [k]: '' })); setXabar({ turi: 'ok', matn: `${nom} olib tashlandi.` }) } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) })
    }
  }
  const saqlashTugma = (maydonlar) => <button type="button" className="ikkinchi" onClick={() => saqla(maydonlar)}>Saqlash</button>

  return (
    <section className="blok stack">
      <h3>Integratsiyalar</h3>
      <p className="malumot">
        Hammasi ixtiyoriy. Kiritilmagan xizmat shunchaki ishlamaydi — qolgan tizim to'liq ishlayveradi. Maxfiy qiymatlar
        (bot tokeni, parol) saqlangach qayta ko'rsatilmaydi.
      </p>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}

      <details className="amal">
        <summary>Telegram bot · {MANBA[d.holat.telegram]}</summary>
        <div className="stack">
          <p className="malumot">
            Butun platformaga <b>bitta</b> Libosa boti xizmat qiladi, shuning uchun bu yerda sozlanmaydi — token uni
            platforma egasi o'z panelida kiritadi. Xodim «Telegramni ulash» tugmasini bosib, shu bot orqali ulanadi.
          </p>
          <p className="malumot">
            Bot ishlamayotgan bo'lsa platforma egasiga murojaat qiling: ulanguncha xabarlar faqat ilova ichida ko'rinadi,
            rahbar esa faqat PIN bilan kiradi.
          </p>
        </div>
      </details>

      <details className="amal">
        <summary>SMS (Eskiz.uz) · {MANBA[d.holat.sms]}</summary>
        <div className="stack">
          <p className="malumot">Mijozga eslatma SMS lari. Yoqish — yuqoridagi «Mijozga SMS eslatma» blokida. Shablonlarni Eskiz kabinetida tasdiqlatish kerak.</p>
          <label>Eskiz email<input type="email" autoComplete="off" value={q('eskiz_email')} onChange={set('eskiz_email')} /></label>
          <label>Eskiz paroli {d.eskiz_parol_kiritilgan && '(kiritilgan)'}
            <input type="password" autoComplete="new-password" value={f.eskiz_parol ?? ''} onChange={set('eskiz_parol')} />
          </label>
          <label>Yuboruvchi nomi (bo'sh — 4546)<input value={q('eskiz_from')} maxLength={20} onChange={set('eskiz_from')} /></label>
          <label>«Ertaga olib ketish» shabloni
            <textarea rows={3} maxLength={300} placeholder={d.standart.sms_shablon_olib_ketish} value={q('sms_shablon_olib_ketish')} onChange={set('sms_shablon_olib_ketish')} />
          </label>
          <label>«Ertaga qaytarish» shabloni
            <textarea rows={3} maxLength={300} placeholder={d.standart.sms_shablon_qaytarish} value={q('sms_shablon_qaytarish')} onChange={set('sms_shablon_qaytarish')} />
          </label>
          <p className="malumot">O'zgaruvchilar: {'{salon}'}, {'{sana}'}, {'{tel}'}, {'{qoldiq}'}. Bo'sh qoldirilsa standart matn ishlatiladi.</p>
          <div className="qator">
            {saqlashTugma(['eskiz_email', 'eskiz_parol', 'eskiz_from', 'sms_shablon_olib_ketish', 'sms_shablon_qaytarish'])}
            {d.eskiz_parol_kiritilgan && <button type="button" className="ikkinchi" onClick={() => tozala('eskiz_parol', 'Eskiz paroli')}>Parolni olib tashlash</button>}
          </div>
        </div>
      </details>

      <details className="amal">
        <summary>Click va Payme · {d.holat.click || d.holat.payme ? [d.holat.click && 'Click', d.holat.payme && 'Payme'].filter(Boolean).join(', ') : 'ulanmagan'}</summary>
        <div className="stack">
          <p className="malumot">
            Kiritilsa, to'lov oynasida mijozga beriladigan to'lov havolasi chiqadi. To'lov tushganini merchant kabinetida tekshirib,
            kassada odatdagidek (usul: Click yoki Payme) qabul qilasiz — avtomatik tasdiqlash yo'q.
          </p>
          <div className="qator keng">
            <label>Click service ID<input inputMode="numeric" value={q('click_service_id')} onChange={set('click_service_id')} /></label>
            <label>Click merchant ID<input inputMode="numeric" value={q('click_merchant_id')} onChange={set('click_merchant_id')} /></label>
          </div>
          <label>Payme merchant ID<input value={q('payme_merchant_id')} maxLength={32} onChange={set('payme_merchant_id')} /></label>
          {saqlashTugma(['click_service_id', 'click_merchant_id', 'payme_merchant_id'])}
        </div>
      </details>

      <details className="amal">
        <summary>Soliq · {Number(d.holat.soliq_foizi)}%</summary>
        <div className="stack">
          <label>Aylanmadan soliq, % (bo'sh — standart {d.standart.soliq_foizi}%)
            <input type="number" min="0" max="100" step="0.1" value={q('soliq_foizi')} onChange={set('soliq_foizi')} />
          </label>
          <label>Izoh (buxgalter xulosasi: sana, asos)
            <textarea rows={2} maxLength={500} value={q('soliq_izohi')} onChange={set('soliq_izohi')} />
          </label>
          <p className="malumot">Foyda va zarar hisobotidagi «Soliq» qatori shu foiz bilan hisoblanadi (o'tgan oylar ham qayta hisoblanadi).</p>
          {saqlashTugma(['soliq_foizi', 'soliq_izohi'])}
        </div>
      </details>

      <details className="amal">
        <summary>Manekin: fonni ajratish</summary>
        <div className="stack">
          <label>Sezgirlik: {q('manekin_fon_farqi')} (standart {d.standart.manekin_fon_farqi})
            <input type="range" min="8" max="120" value={q('manekin_fon_farqi')} onChange={(e) => setF({ ...f, manekin_fon_farqi: Number(e.target.value) })} />
          </label>
          <p className="malumot">
            Libos chetlari kesilib ketsa — kamaytiring; fon qoldiqlari qolsa — oshiring. O'zgartirgach rasmda «Manekinga» ni qayta bosing.
          </p>
          {saqlashTugma(['manekin_fon_farqi'])}
        </div>
      </details>

      <details className="amal">
        <summary>Instagram, onlayn kassa va 1C</summary>
        <div className="stack">
          <label>Salon Instagram sahifasi (@nomi yoki havola)<input value={q('instagram')} maxLength={200} onChange={set('instagram')} /></label>
          <label className="qator">
            <input type="checkbox" checked={!!q('fiskal_eslatma')} onChange={set('fiskal_eslatma')} />
            To'lovdan keyin sotuvchiga fiskal chek haqida eslatma
          </label>
          <label>Eslatma matni (masalan: «Chekni onlayn kassada uring»)
            <input value={q('fiskal_izoh')} maxLength={300} onChange={set('fiskal_izoh')} />
          </label>
          <p className="malumot">
            Onlayn kassa va 1C bilan avtomatik almashinuv yo'q: fiskal chek alohida uriladi, buxgalteriya uchun raqamlar «Hisobot» bo'limidan olinadi.
          </p>
          {saqlashTugma(['instagram', 'fiskal_eslatma', 'fiskal_izoh'])}
        </div>
      </details>
    </section>
  )
}

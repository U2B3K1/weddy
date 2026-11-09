import { useEffect, useState } from 'react'
import { integratsiyaSaqla, integratsiyalar, xatoMatni } from '../api'
import NavIkona from './NavIkona'
import { SPanel, SQator, Yorliq } from './SozlamaUI'

const MANBA = { salon: 'ulangan (salon hisobi)', platforma: 'ulangan (platforma hisobi)', yoq: 'ulanmagan' }

// Tashqi xizmatlar: hammasi ixtiyoriy. Hech biri kiritilmasa ham tizim to'liq ishlaydi —
// faqat Telegram/SMS yuborilmaydi, to'lov havolasi chiqmaydi.
export default function Integratsiyalar() {
  const [d, setD] = useState(null)
  const [f, setF] = useState({})
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [ochiq, setOchiq] = useState(null)  // ochilgan xizmat sozlamasi

  useEffect(() => { integratsiyalar().then(setD).catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [])
  if (!d) return <SPanel id="integratsiyalar" ikon="vilka" nomi="Integratsiyalar"><p className="soz-izoh">{xabar.matn || 'Yuklanmoqda…'}</p></SPanel>

  const q = (k) => f[k] ?? d[k] ?? ''
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })
  const saqla = async (maydonlar) => {
    setXabar({ turi: '', matn: '' })
    const tana = {}
    for (const k of maydonlar) if (k in f) tana[k] = f[k]
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
  const saqlashTugma = (maydonlar) => <button type="button" className="kichik" onClick={() => saqla(maydonlar)}>Saqlash</button>
  // Kanvas: to'rtta xizmat kartasi (holat yorlig'i, qisqa izoh, «Sozlash →»); bosilgan kartaning sozlamasi kartalar ostida ochiladi
  const KARTALAR = [
    { k: 'telegram', nomi: 'Telegram bot', ikon: 'xabar', ulangan: d.holat.telegram !== 'yoq', izoh: 'Xodimlarga tasdiqlar, eslatmalar, kunlik hisobot', holat: MANBA[d.holat.telegram] },
    { k: 'sms', nomi: 'Eskiz SMS', ikon: 'telefon', ulangan: d.holat.sms !== 'yoq', izoh: 'Mijozga eslatma va to\'lov kvitansiyasi', holat: MANBA[d.holat.sms] },
    { k: 'tolov', nomi: 'Click', ikon: 'kassa', ulangan: !!d.holat.click, izoh: "Mijoz havola orqali onlayn to'laydi", holat: d.holat.click ? 'ulangan' : 'ulanmagan' },
    { k: 'tolov', nomi: 'Payme', ikon: 'kassa', ulangan: !!d.holat.payme, izoh: "Mijoz havola orqali onlayn to'laydi", holat: d.holat.payme ? 'ulangan' : 'ulanmagan' },
  ]
  const forma = (k, sarlavha, mazmun) => ochiq === k && (
    <div className="soz-tahrir soz-int-forma" role="region" aria-label={`${sarlavha} sozlamasi`}>
      <h4 className="r2-kichik-sarlavha">{sarlavha}</h4>
      <div className="stack">{mazmun}</div>
    </div>
  )

  return (
    <SPanel id="integratsiyalar" ikon="vilka" nomi="Integratsiyalar" izoh="Tashqi xizmatlar — har biri o'z kaliti bilan ulanadi. Hammasi ixtiyoriy">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'soz-izoh'}>{xabar.matn}</p>}
      <div className="soz-int-tor">
        {KARTALAR.map((x) => (
          <button key={x.nomi} type="button" className={`soz-int${x.ulangan ? ' ulangan' : ''}${ochiq === x.k ? ' ochiq' : ''}`} aria-expanded={ochiq === x.k}
            onClick={() => setOchiq(ochiq === x.k ? null : x.k)}>
            <span className="soz-int-bosh">
              <span className="soz-plitka kichik" aria-hidden="true"><NavIkona nom={x.ikon} className="tugma-ikon" /></span>
              <span><b>{x.nomi}</b><Yorliq tur={x.ulangan ? 'yashil' : 'yopiq'}>{x.ulangan ? 'Ulangan' : 'Ulanmagan'}</Yorliq></span>
            </span>
            <small>{x.izoh}</small>
            <span className="soz-int-havola">{x.ulangan ? 'Sozlash' : 'Ulash'} →</span>
          </button>
        ))}
      </div>

      {forma('telegram', 'Telegram bot', (
        <>
          <p className="malumot">
            Butun platformaga <b>bitta</b> Libosa boti xizmat qiladi, shuning uchun bu yerda sozlanmaydi — token uni
            platforma egasi o'z panelida kiritadi. Xodim «Telegramni ulash» tugmasini bosib, shu bot orqali ulanadi.
          </p>
          <p className="malumot">
            Bot ishlamayotgan bo'lsa platforma egasiga murojaat qiling: ulanguncha xabarlar faqat ilova ichida ko'rinadi,
            rahbar esa faqat PIN bilan kiradi.
          </p>
        </>
      ))}

      {forma('sms', 'Eskiz SMS', (
        <>
          <p className="malumot">Mijozga eslatma SMS lari. Yoqish — pastdagi «Mijozga SMS» panelida. Shablonlarni Eskiz kabinetida tasdiqlatish kerak.</p>
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
          <p className="malumot">To'lov kvitansiyasi uchun Eskiz kabinetida shu shablonni tasdiqlating: «{d.standart.sms_shablon_kvitansiya}»</p>
          <div className="soz-tugmalar">
            {saqlashTugma(['eskiz_email', 'eskiz_parol', 'eskiz_from', 'sms_shablon_olib_ketish', 'sms_shablon_qaytarish'])}
            {d.eskiz_parol_kiritilgan && <button type="button" className="ikkinchi kichik" onClick={() => tozala('eskiz_parol', 'Eskiz paroli')}>Parolni olib tashlash</button>}
          </div>
        </>
      ))}

      {forma('tolov', 'Click va Payme', (
        <>
          <p className="malumot">
            Kiritilsa, to'lov oynasida mijozga beriladigan to'lov havolasi chiqadi. To'lov tushganini merchant kabinetida tekshirib,
            kassada odatdagidek (usul: Click yoki Payme) qabul qilasiz — avtomatik tasdiqlash yo'q.
          </p>
          <div className="qator keng">
            <label>Click service ID<input inputMode="numeric" value={q('click_service_id')} onChange={set('click_service_id')} /></label>
            <label>Click merchant ID<input inputMode="numeric" value={q('click_merchant_id')} onChange={set('click_merchant_id')} /></label>
          </div>
          <label>Payme merchant ID<input value={q('payme_merchant_id')} maxLength={32} onChange={set('payme_merchant_id')} /></label>
          <div className="soz-tugmalar">{saqlashTugma(['click_service_id', 'click_merchant_id', 'payme_merchant_id'])}</div>
        </>
      ))}

      {/* Kartalarga sig'magan ikki sozlama — oddiy qatorlar */}
      <SQator nomi="Manekin: fonni ajratish" izoh={`Sezgirlik ${q('manekin_fon_farqi')} (standart ${d.standart.manekin_fon_farqi}). Libos chetlari kesilsa — kamaytiring, fon qolsa — oshiring.`}>
        <button type="button" className="havola" aria-expanded={ochiq === 'manekin'} onClick={() => setOchiq(ochiq === 'manekin' ? null : 'manekin')}>Sozlash</button>
      </SQator>
      {forma('manekin', 'Manekin: fonni ajratish', (
        <>
          <label>Sezgirlik: {q('manekin_fon_farqi')} (standart {d.standart.manekin_fon_farqi})
            <input type="range" min="8" max="120" value={q('manekin_fon_farqi')} onChange={(e) => setF({ ...f, manekin_fon_farqi: Number(e.target.value) })} />
          </label>
          <p className="malumot">O'zgartirgach rasmda «Manekinga» ni qayta bosing.</p>
          <div className="soz-tugmalar">{saqlashTugma(['manekin_fon_farqi'])}</div>
        </>
      ))}
      <SQator nomi="Instagram, onlayn kassa va 1C" izoh="Salon Instagram sahifasi va to'lovdan keyin fiskal chek eslatmasi. 1C bilan avtomatik almashinuv yo'q.">
        <button type="button" className="havola" aria-expanded={ochiq === 'boshqa'} onClick={() => setOchiq(ochiq === 'boshqa' ? null : 'boshqa')}>Sozlash</button>
      </SQator>
      {forma('boshqa', 'Instagram, onlayn kassa va 1C', (
        <>
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
          <div className="soz-tugmalar">{saqlashTugma(['instagram', 'fiskal_eslatma', 'fiskal_izoh'])}</div>
        </>
      ))}
    </SPanel>
  )
}

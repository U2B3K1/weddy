import { useCallback, useEffect, useRef, useState } from 'react'
import Hujjat from '../components/Hujjat'
import LibosSiluet from '../components/LibosSiluet'
import Oyna from '../components/Oyna'
import Tasdiq from '../components/Tasdiq'
import SmenaTugma from '../components/SmenaTugma'
import {
  inkassatsiyaQil, kassaZaloglar, smenaChiqish, smenaHolati, smenaOchish, smenaQoshilish, smenaTuzat, smenaYopish, smenalar, som, sozlamalar,
  tolovQabul, topshiriqQabul, xarajatModdalari, xarajatYarat, xatoMatni, zakazlarRoyxat, zalogBelgila,
  guruhla, sanaMatni,
} from '../api'
import SummaInput from '../components/SummaInput'

// Sotuvchi kassadan to'laydigan kundalik xarajatlar; salonning o'z moddalari ham chiqadi (FT-13.1)
const KASSA_MODDALARI = ['tozalash', 'tamir', 'transport', 'kommunal', 'reklama', 'boshqa']
const USULLAR = [['naqd', 'Naqd'], ['karta', 'Karta'], ['click', 'Click'], ['payme', 'Payme']]
// Smena ochiq bo'lishini talab qiladigan bo'limlar (yangi zakaz va tarix — talab qilmaydi)
const SMENA_KERAK = ['tolov', 'xarajat', 'inkassatsiya', 'zalog', 'hisobot']

// 4.12: Kassa — POS ish joyi. Tepada smena paneli (holat, kim ishlayapti, kassadagi naqd, smena amallari),
// ostida ichki bo'limlar (App'dagi segment): yangi zakaz, to'lov qabul qilish, xarajat, inkassatsiya, zaloglar,
// smena hisoboti, tarix. Summalar raqamli klaviaturadan kiritiladi — planshetda barmoq bilan qulay.
export default function Kassa({ rahbar, bolim, onBolim, onHolatOzgardi, yangiZakaz, tolovZakaz }) {
  const [s, setS] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [oyna, setOyna] = useState(null) // 'ochish' | 'chiqish' | 'yopish'

  // Smena holati App'dagi qo'ng'iroqcha va boshqa joylarga ham kerak: yuklangach onHolatOzgardi chaqiriladi.
  const yukla = useCallback(() => smenaHolati().then((r) => { setS(r); onHolatOzgardi?.() }), [onHolatOzgardi])
  useEffect(() => { yukla() }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try {
      const r = await fn()
      setXabar({ turi: 'ok', matn: typeof ok === 'function' ? ok(r) : ok, bolim })
      await yukla()
      return true
    } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e), kod: e.response?.data?.kod, bolim })
      return false
    }
  }
  const oynada = (fn, ok) => async (...a) => { const r = await bajar(() => fn(...a), ok); if (r) setOyna(null); return r }

  if (!s) return <p className="malumot">Yuklanmoqda…</p>
  const smenaYoq = !s.ochiq && SMENA_KERAK.includes(bolim)
  const kutayotgan = <Kutayotgan royxat={s.kutayotgan} onQabul={(t, summa) => bajar(() => topshiriqQabul(t.id, summa), (r) => `Qabul qilindi: ${som(r.qabul_summa)}.`)} />

  // «Alohida kassir» rejimida sotuvchi pul olmaydi: faqat zakaz rasmiylashtiradi, mijozni kassaga yuboradi
  if (!s.pul_oladi) {
    return (
      <div className="pos">
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot pos-xabar'}>{xabar.matn}</p>}
        {kutayotgan}
        {bolim === 'yangi' ? yangiZakaz : (
          <section className="blok pos-bosh">
            <h3>Pulni kassir qabul qiladi</h3>
            <p className="malumot">Bu salonda siz zakaz olasiz, to'lovni esa kassir qabul qiladi — mijozni kassaga yuboring.
              Zakazingizga kirgan pul statistikada sizning nomingizga yoziladi.</p>
          </section>
        )}
      </div>
    )
  }

  return (
    <div className="pos">
      <SmenaPaneli s={s} onOch={() => setOyna('ochish')} onQoshil={() => bajar(smenaQoshilish, "Smenaga qo'shildingiz.")}
        onChiq={() => setOyna('chiqish')} onYop={() => setOyna('yopish')} onHisobot={() => onBolim('hisobot')} />
      {kutayotgan}
      {xabar.matn && xabar.bolim === bolim && (  // eski xabar boshqa bo'limga o'tganda qolib ketmasin
        <p className={xabar.turi === 'xato' ? 'xato' : 'malumot pos-xabar'}>
          {xabar.matn}{' '}
          {xabar.turi === 'xato' && (
            <SmenaTugma kod={xabar.kod} onKassa={() => setOyna('ochish')}
              onTayyor={() => { setXabar({ turi: 'ok', matn: "Smenaga qo'shildingiz. Amalni qayta bajaring.", bolim }); yukla() }} />
          )}
        </p>
      )}

      {smenaYoq ? (
        <section className="blok pos-bosh">
          <h3>Smena yopiq</h3>
          <p className="malumot">To'lov, xarajat va inkassatsiya uchun avval smenani oching — kassadagi naqd pul sanaladi.</p>
          <button onClick={() => setOyna('ochish')}>Smenani ochish</button>
        </section>
      ) : (
        <>
          {bolim === 'yangi' && yangiZakaz}
          {bolim === 'tolov' && <TolovPOS key={tolovZakaz?.n} boshZakaz={tolovZakaz?.id} onTolandi={yukla} onSmenaOchish={() => setOyna('ochish')} />}
          {bolim === 'xarajat' && (
            <XarajatPOS onYuborish={(b) => bajar(() => xarajatYarat({ ...b, kassadan: true }), rahbar ? 'Xarajat kassadan yozildi.' : "Xarajat kassadan yozildi (rahbar tasdig'ini kutadi).")} />
          )}
          {bolim === 'inkassatsiya' && (
            <InkassatsiyaPOS rahbarlar={s.rahbarlar}
              onYuborish={(summa, izoh, rahbar) => bajar(() => inkassatsiyaQil({ summa, izoh, rahbar }), "Inkassatsiya yozildi — rahbar Telegramda tasdiqlaydi.")} />
          )}
          {bolim === 'zalog' && <ZalogTekshiruvi onOzgardi={yukla} />}
          {bolim === 'hisobot' && <Hisobot h={s.hisobot} />}
          {bolim === 'tarix' && rahbar && <YopilganSmenalar />}
        </>
      )}

      {oyna === 'ochish' && (
        <Oyna sarlavha="Smenani ochish" onYop={() => setOyna(null)}>
          {s.seyfda != null && <p className="malumot">Oldingi smena yopilganda seyfda <b>{som(s.seyfda)}</b> qolgan. Sanab, haqiqiy summani kiriting — farq bo'lsa rahbarga xabar boradi.</p>}
          <SummaForma yorliq="Boshlang'ich qoldiq — seyfdagi naqd pul" tugma="Smenani ochish" nolRuxsat
            onYuborish={oynada((q) => smenaOchish(q), 'Smena ochildi.')} />
        </Oyna>
      )}
      {oyna === 'chiqish' && (
        <Oyna sarlavha="Pulni topshirib chiqish" onYop={() => setOyna(null)}>
          <PulTopshirish s={s} onYuborish={oynada((summa, kimga) => smenaChiqish(summa, kimga),
            (r) => `Chiqdingiz. Pul ${r.kimga}ga topshirildi — u tasdiqlaydi.${r.farq ? ` Farq: ${som(r.farq)}` : ''}`)} />
        </Oyna>
      )}
      {oyna === 'yopish' && (
        <Oyna sarlavha="Smenani yopish" onYop={() => setOyna(null)}>
          <SmenaYopish hisobda={s.mening_hisobim ?? s.hisobot.hisobdagi_qoldiq} tekshirilmagan={s.zalog_tekshirilmagan} rahbarlar={s.rahbarlar}
            onYuborish={oynada((summa, izoh, rahbar) => smenaYopish(summa, izoh, rahbar), (r) => `Smena yopildi. Farq: ${som(r.farq)}`)} />
        </Oyna>
      )}
    </div>
  )
}

// Smena paneli: POS'dagi «kassir chizig'i» — har bo'limda tepada
function SmenaPaneli({ s, onOch, onQoshil, onChiq, onYop, onHisobot }) {
  if (!s.ochiq) {
    return (
      <div className="smena-panel yopiq">
        <span className="smena-holat"><i aria-hidden="true" />Smena yopiq{s.filial ? ` · ${s.filial}` : ''}</span>
        <span className="malumot">To'lov qabul qilish uchun smenani oching</span>
        <button className="kichik" onClick={onOch}>Smenani ochish</button>
      </div>
    )
  }
  return (
    <div className="smena-panel">
      <span className="smena-holat ochiq"><i aria-hidden="true" />Smena ochiq{s.filial ? ` · ${s.filial}` : ''}</span>
      <span className="smena-kim">{s.ishtirokchilar.join(', ')}
        {s.yuborilgan?.map((t) => <small key={t.id} className="malumot"> · {t.kimga} {som(t.summa)} ni hali tasdiqlamadi</small>)}</span>
      {s.men_ishtirokchi ? (
        <button type="button" className="smena-naqd" onClick={onHisobot} title="Siz javob beradigan naqd. Bosing — smena hisoboti">
          <small>Sizda naqd</small><b>{som(s.mening_hisobim)}</b>
        </button>
      ) : (
        <button type="button" className="smena-naqd" onClick={onHisobot} title="Smena hisobotini ochish">
          <small>Kassada naqd</small><b>{som(s.hisobot.hisobdagi_qoldiq)}</b>
        </button>
      )}
      <div className="smena-amallar">
        {!s.men_ishtirokchi && <button className="kichik" onClick={onQoshil}>Smenaga qo'shilish</button>}
        {s.men_ishtirokchi && s.ishtirokchilar.length > 1 && <button className="ikkinchi kichik" onClick={onChiq}>Pulni topshirib chiqish</button>}
        <button className="ikkinchi kichik" onClick={onYop}>Smenani yopish</button>
      </div>
    </div>
  )
}

// Server vaqti UTC da keladi — qurilmaning mahalliy vaqtida «01.11.2026 01:15»
const mahalliyVaqt = (v) => { const d = new Date(v); return `${sanaMatni(d.toLocaleDateString('sv-SE'))} ${d.toTimeString().slice(0, 5)}` }

// Menga topshirilgan, hali qabul qilinmagan pul: sanab «Qabul qildim» yoki boshqa summani kiritish.
// Telegramdagi tugmalar bilan bir xil — qaysi biri birinchi bosilsa, o'sha hisoblanadi.
function Kutayotgan({ royxat, onQabul }) {
  const [boshqa, setBoshqa] = useState({})
  if (!royxat?.length) return null
  return (
    <section className="blok jadval-panel">
      <div className="jadval-asboblar"><h3 className="panel-nom">Sizga topshirilgan pul</h3>
        <span className="malumot">Sanab tasdiqlang: shundan keyin bu pulga siz javob berasiz</span></div>
      {royxat.map((t) => (
        <div key={t.id} className="tasdiq-qator">
          <div className="tasdiq-matn">
            <b>{t.kimdan} · {som(t.summa)}{t.rahbarga && ' · inkassatsiya'}</b>
            <small>{mahalliyVaqt(t.vaqt)}{t.izoh && ` · ${t.izoh}`}</small>
          </div>
          <div className="tasdiq-tugmalar">
            {boshqa[t.id] !== undefined ? (
              <>
                <SummaInput aria-label="Sanalgan summa" value={boshqa[t.id]} onChange={(e) => setBoshqa({ ...boshqa, [t.id]: e.target.value })} />
                <button className="kichik" disabled={boshqa[t.id] === ''} onClick={() => onQabul(t, Number(boshqa[t.id]))}>Shu summani qabul qilish</button>
              </>
            ) : (
              <>
                <button className="ikkinchi kichik" onClick={() => setBoshqa({ ...boshqa, [t.id]: '' })}>Boshqa summa</button>
                <button className="kichik" onClick={() => onQabul(t)}>{som(t.summa)} qabul qildim</button>
              </>
            )}
          </div>
        </div>
      ))}
    </section>
  )
}

// Smenadan chiqish: qo'ldagi naqd sanaladi va smenada qolayotgan xodimga yoki rahbarga beriladi; u tasdiqlaydi.
function PulTopshirish({ s, onYuborish }) {
  const qolganlar = s.xodimlar || []  // smenadagi boshqa xodimlar (o'zim kirmayman)
  const variantlar = [...qolganlar.map((x) => ({ ...x, izoh: 'smenada qoladi' })), ...s.rahbarlar.filter((r) => !qolganlar.some((x) => x.id === r.id)).map((r) => ({ ...r, izoh: 'rahbar' }))]
  const [kimga, setKimga] = useState('')
  const [summa, setSumma] = useState('')
  const farq = summa === '' ? null : Number(summa) - s.mening_hisobim
  return (
    <div className="stack">
      <p className="malumot">Tizim bo'yicha sizda: <b>{som(s.mening_hisobim)}</b>. Pulni sanang va kimga berayotganingizni tanlang —
        u Telegramda (yoki ilovada) tasdiqlaydi. Farq bo'lsa faqat sizga yoziladi.</p>
      <label>Kimga
        <select value={kimga} onChange={(e) => setKimga(e.target.value)}>
          <option value="">— tanlang —</option>
          {variantlar.map((x) => <option key={x.id} value={x.id}>{x.ism} ({x.izoh})</option>)}
        </select>
      </label>
      <Summa qiymat={summa} izoh={farq === null ? null : farq === 0 ? "Farq yo'q" : `Farq: ${som(farq)}`} />
      <Klaviatura qiymat={summa} onOzgar={setSumma} />
      <button className="pos-tugma" disabled={summa === '' || !kimga} onClick={() => onYuborish(Number(summa), Number(kimga))}>Topshirib chiqish</button>
    </div>
  )
}

// Raqamli klaviatura: barmoq bilan summa kiritish (kompyuter klaviaturasi ham ishlaydi — maydon fokusda bo'lmasa)
function Klaviatura({ qiymat, onOzgar }) {
  const joy = useRef(null)
  const bos = (k) => {
    if (k === '⌫') return onOzgar(qiymat.slice(0, -1))
    if (k === 'C') return onOzgar('')
    const yangi = (qiymat + k).replace(/^0+(?=\d)/, '')
    if (yangi.length <= 10) onOzgar(yangi)
  }
  useEffect(() => {
    const h = (e) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
      // oyna ochiq bo'lsa — faqat oyna ichidagi klaviatura tinglaydi (orqadagi ekran summasi o'zgarmasin)
      const oyna = document.querySelector('.oyna')
      if (oyna && !oyna.contains(joy.current)) return
      if (/^\d$/.test(e.key)) bos(e.key)
      else if (e.key === 'Backspace') bos('⌫')
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  })
  return (
    <div className="klaviatura" role="group" aria-label="Raqamli klaviatura" ref={joy}>
      {['1', '2', '3', '4', '5', '6', '7', '8', '9', '000', '0', '⌫'].map((k) => (
        <button key={k} type="button" className="ikkinchi" aria-label={k === '⌫' ? "O'chirish" : k} onClick={() => bos(k)}>{k}</button>
      ))}
    </div>
  )
}

const Summa = ({ qiymat, izoh }) => (
  <div className="pos-summa" aria-live="polite">
    <b>{guruhla(qiymat)}</b><span>so'm</span>
    {izoh && <small>{izoh}</small>}
  </div>
)

// Bitta summa kiritadigan forma (smena ochish, chiqish, inkassatsiya)
function SummaForma({ yorliq, tugma, onYuborish, nolRuxsat, izohYorliq }) {
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const tayyor = summa !== '' && (nolRuxsat || Number(summa) > 0)
  return (
    <div className="stack">
      <span className="malumot">{yorliq}</span>
      <Summa qiymat={summa} />
      <Klaviatura qiymat={summa} onOzgar={setSumma} />
      {izohYorliq && <label>{izohYorliq}<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>}
      <button className="pos-tugma" disabled={!tayyor} onClick={() => onYuborish(Number(summa), izoh).then((ok) => ok && (setSumma(''), setIzoh('')))}>{tugma}</button>
    </div>
  )
}

function SmenaYopish({ hisobda, tekshirilmagan, rahbarlar, onYuborish }) {
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const [surov, setSurov] = useState(false)
  const [rahbar, setRahbar] = useState('')  // bo'sh — pul seyfda qoladi
  const farq = summa === '' ? null : Number(summa) - hisobda
  return (
    <div className="stack">
      <p className="malumot">Sizda (tizim bo'yicha): <b>{som(hisobda)}</b>. Qo'lingizdagi naqd pulni sanab kiriting.</p>
      <label>Pul qayerda qoladi
        <select value={rahbar} onChange={(e) => setRahbar(e.target.value)}>
          <option value="">Seyfda — ertaga ochgan xodim sanab qabul qiladi</option>
          {rahbarlar.map((r) => <option key={r.id} value={r.id}>Rahbarga topshiraman: {r.ism}</option>)}
        </select>
      </label>
      {tekshirilmagan > 0 && <p className="ogohlantirish">{tekshirilmagan} ta zalog tekshirilmagan — yopishdan oldin «Zaloglar» bo'limida belgilang.</p>}
      <Summa qiymat={summa} izoh={farq === null ? null : farq === 0 ? 'Farq yo\'q' : `Farq: ${som(farq)}`} />
      <Klaviatura qiymat={summa} onOzgar={setSumma} />
      {farq !== null && farq !== 0 && <label>Izoh (farq sababi — majburiy)<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>}
      <button className="pos-tugma" disabled={summa === '' || (farq !== 0 && !izoh.trim())} onClick={() => setSurov(true)}>Smenani yopish</button>
      {surov && (
        <Tasdiq sarlavha="Smenani yopasizmi?" tugma="Smenani yopish"
          matn={`Smena yopiladi, keyin to'lov qabul qilib bo'lmaydi. Sanalgan naqd: ${som(Number(summa))}${rahbar ? ` — ${rahbarlar.find((r) => String(r.id) === rahbar)?.ism}ga topshiriladi, u Telegramda tasdiqlaydi` : ' — seyfda qoladi'}.`}
          onYop={() => setSurov(false)} onTasdiq={() => { setSurov(false); onYuborish(Number(summa), izoh, rahbar ? Number(rahbar) : undefined) }} />
      )}
    </div>
  )
}

// To'lov qabul qilish — POS ekrani: chapda to'lov kutayotgan zakazlar, o'ngda chek (summa, klaviatura, usul)
function TolovPOS({ boshZakaz, onTolandi, onSmenaOchish }) {
  const [royxat, setRoyxat] = useState(null)
  const [q, setQ] = useState('')
  const [tanlangan, setTanlangan] = useState(boshZakaz || null)
  const [summa, setSumma] = useState('')
  const [usul, setUsul] = useState('naqd')
  const [xato, setXato] = useState('')
  const [xatoKod, setXatoKod] = useState('')  // serverdan: smena_qoshilish | smena_yoq — xato yonida mos tugma
  const [qoshildi, setQoshildi] = useState(false)
  const [band, setBand] = useState(false)
  const [tolandi, setTolandi] = useState(null) // { zakaz, summa }
  const [chek, setChek] = useState(null)
  const [soz, setSoz] = useState(null)
  useEffect(() => { sozlamalar().then(setSoz).catch(() => {}) }, [])

  const yukla = useCallback(() => Promise.all([zakazlarRoyxat({ holat: 'vaqtinchalik', q: q || undefined }), zakazlarRoyxat({ holat: 'bron', q: q || undefined })])
    .then(([a, b]) => setRoyxat([...a, ...b].filter((z) => z.jami - z.tolangan > 0)
      .sort((x, y) => String(x.olib_ketish).localeCompare(String(y.olib_ketish)))))
    .catch((e) => setXato(xatoMatni(e))), [q])
  useEffect(() => { const t = setTimeout(yukla, q ? 300 : 0); return () => clearTimeout(t) }, [yukla, q])

  const z = royxat?.find((x) => x.id === tanlangan)
  const qoldiq = z ? z.jami - z.tolangan : 0
  const avans = z?.holat === 'vaqtinchalik'
  const tanla = (id) => { setTanlangan(id); setSumma(''); setXato(''); setXatoKod(''); setQoshildi(false); setTolandi(null) }
  const qabul = async () => {
    setXato(''); setXatoKod(''); setQoshildi(false); setBand(true)
    try {
      await tolovQabul({ zakaz: z.id, tur: avans ? 'avans' : 'qoldiq', summa: Number(summa), usul })
      setTolandi({ zakaz: z, summa: Number(summa), usul })
      setTanlangan(null); setSumma('')
      await Promise.all([yukla(), onTolandi?.()])
    } catch (e) { setXato(xatoMatni(e)); setXatoKod(e.response?.data?.kod || '') } finally { setBand(false) }
  }

  if (chek) return <Hujjat zakazId={chek} tur="kvitansiya" onYop={() => setChek(null)} />

  return (
    <div className="pos-ish">
      <section className="blok pos-royxat">
        <div className="pos-royxat-bosh">
          <h3>To'lov kutayotgan zakazlar</h3>
          <input type="search" placeholder="Raqam, telefon yoki ism" aria-label="Zakaz qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        {royxat === null && <p className="malumot">Yuklanmoqda…</p>}
        {royxat && royxat.length === 0 && <p className="malumot">{q ? 'Topilmadi.' : "To'lov kutayotgan zakaz yo'q."}</p>}
        <div className="pos-zakazlar">
          {royxat?.map((x) => (
            <button key={x.id} type="button" className={`pos-zakaz${x.id === tanlangan ? ' tanlandi' : ''}`} aria-pressed={x.id === tanlangan} onClick={() => tanla(x.id)}>
              <span className="zakaz-eskiz">{x.rasm ? <img src={x.rasm} alt="" loading="lazy" /> : <LibosSiluet />}</span>
              <span className="zakaz-nom"><b>#{x.raqam} {x.mijoz}</b><small>{x.liboslar.join(', ')} · {sanaMatni(x.olib_ketish)}{x.sotuvchi && ` · sotuvchi: ${x.sotuvchi}`}</small></span>
              <span className="pos-zakaz-summa"><b>{som(x.jami - x.tolangan)}</b><small>{x.holat === 'vaqtinchalik' ? 'avans' : 'qoldiq'}</small></span>
            </button>
          ))}
        </div>
      </section>

      <section className="blok pos-chek" aria-label="To'lov">
        {tolandi && !z && (
          <div className="pos-tayyor">
            <span className="pos-tayyor-belgi" aria-hidden="true">✓</span>
            <h3>To'lov qabul qilindi</h3>
            <p>#{tolandi.zakaz.raqam} {tolandi.zakaz.mijoz} · <b>{som(tolandi.summa)}</b> · {USULLAR.find(([k]) => k === tolandi.usul)?.[1]}</p>
            {soz?.fiskal_eslatma && <p className="ogohlantirish">{soz.fiskal_izoh || 'Fiskal chekni urishni unutmang.'}</p>}
            <div className="qator">
              <button className="ikkinchi" onClick={() => setChek(tolandi.zakaz.id)}>Kvitansiya</button>
              <button onClick={() => setTolandi(null)}>Keyingi to'lov</button>
            </div>
          </div>
        )}
        {!z && !tolandi && <p className="malumot pos-bosh-matn">Chapdagi ro'yxatdan zakazni tanlang — to'lov shu yerda qabul qilinadi.</p>}
        {z && (
          <>
            <div className="pos-chek-bosh">
              <b>#{z.raqam} {z.mijoz}</b>
              <span className="malumot">{z.liboslar.join(', ')} · {sanaMatni(z.olib_ketish)} – {sanaMatni(z.qaytarish)}</span>
            </div>
            <table className="jadval pos-hisob"><tbody>
              <tr><td>Jami</td><td>{som(z.jami)}</td></tr>
              <tr><td>To'langan</td><td>{som(z.tolangan)}</td></tr>
              <tr><td><b>{avans ? 'Avans (qoldiq)' : 'Qoldiq'}</b></td><td><b>{som(qoldiq)}</b></td></tr>
            </tbody></table>
            <Summa qiymat={summa} izoh={Number(summa) > qoldiq ? `Qoldiqdan oshib ketdi (${som(qoldiq)})` : null} />
            <div className="pos-tez">
              <button type="button" className="ikkinchi kichik" onClick={() => setSumma(String(qoldiq))}>To'liq: {som(qoldiq)}</button>
              {avans && [50, 30].map((f) => (
                <button key={f} type="button" className="ikkinchi kichik" onClick={() => setSumma(String(Math.round((qoldiq * f) / 100 / 1000) * 1000))}>{f}%</button>
              ))}
            </div>
            <Klaviatura qiymat={summa} onOzgar={setSumma} />
            <div className="pos-usullar" role="radiogroup" aria-label="To'lov usuli">
              {USULLAR.map(([k, nom]) => (
                <button key={k} type="button" role="radio" aria-checked={usul === k} className={usul === k ? 'tanlandi' : ''} onClick={() => setUsul(k)}>{nom}</button>
              ))}
            </div>
            {xato && (
              <p className="xato">
                {xato}{' '}
                <SmenaTugma kod={xatoKod} onKassa={onSmenaOchish}
                  onTayyor={() => { setXato(''); setXatoKod(''); setQoshildi(true); onTolandi?.() }} />
              </p>
            )}
            {qoshildi && <p className="malumot">Smenaga qo'shildingiz — «Qabul qilish» ni qayta bosing.</p>}
            <button className="pos-tugma" disabled={band || !(Number(summa) > 0) || Number(summa) > qoldiq} onClick={qabul}>
              {band ? 'Qabul qilinmoqda…' : `Qabul qilish${Number(summa) > 0 ? ` · ${som(Number(summa))}` : ''}`}
            </button>
          </>
        )}
      </section>
    </div>
  )
}

function Hisobot({ h }) {
  const qatorlar = [
    ['Kun boshidagi qoldiq', h.kun_boshidagi_qoldiq], ['Tushum (avans + qoldiq + jarima)', h.tushum],
    ['Olingan pul zaloglar', h.olingan_zaloglar], ['Qaytarilgan zaloglar', -h.qaytarilgan_zaloglar],
    ['Xarajatlar', -h.xarajatlar], ['Pulni qaytarish va inkassatsiya', -h.vozvrat_va_inkassatsiya],
  ]
  return (
    <section className="blok pos-tor">
      <h3>Naqd pul hisobi</h3>
      <table className="jadval"><tbody>
        {qatorlar.map(([n, v]) => <tr key={n}><td>{n}</td><td>{som(v)}</td></tr>)}
        <tr><td><b>Hisobdagi qoldiq</b></td><td><b>{som(h.hisobdagi_qoldiq)}</b></td></tr>
      </tbody></table>
      {Object.keys(h.sotuvchilar).length > 0 && (
        <p className="malumot">Kirimlar: {Object.entries(h.sotuvchilar).map(([k, v]) => `${k} — ${som(v)}`).join('; ')}</p>
      )}
    </section>
  )
}

// Xarajat: modda — katta plitkalar, summa — klaviatura (POS uslubi)
function XarajatPOS({ onYuborish }) {
  const [modda, setModda] = useState('transport')
  const [moddalar, setModdalar] = useState([])
  useEffect(() => {
    xarajatModdalari().then((m) => setModdalar(m.filter((x) => !x.standart || KASSA_MODDALARI.includes(x.kod)))).catch(() => {})
  }, [])
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  return (
    <div className="pos-ish">
      <section className="blok">
        <h3>Xarajat moddasi</h3>
        <div className="pos-plitkalar" role="radiogroup" aria-label="Xarajat moddasi">
          {moddalar.map((m) => (
            <button key={m.kod} type="button" role="radio" aria-checked={modda === m.kod} className={modda === m.kod ? 'tanlandi' : ''} onClick={() => setModda(m.kod)}>{m.nomi}</button>
          ))}
        </div>
        <label>Izoh<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>
      </section>
      <section className="blok pos-chek">
        <span className="malumot">Kassadan chiqim</span>
        <Summa qiymat={summa} />
        <Klaviatura qiymat={summa} onOzgar={setSumma} />
        <button className="pos-tugma" disabled={!(Number(summa) > 0)}
          onClick={() => onYuborish({ modda, summa: Number(summa), izoh }).then((ok) => ok && (setSumma(''), setIzoh('')))}>
          Xarajatni yozish
        </button>
      </section>
    </div>
  )
}

// FT-12.6: rahbarga topshirilgan naqd pul — alohida chiqim, tushum va xarajatga kirmaydi. Rahbar Telegramda tasdiqlaydi.
function InkassatsiyaPOS({ rahbarlar, onYuborish }) {
  const [rahbar, setRahbar] = useState(rahbarlar.length === 1 ? String(rahbarlar[0].id) : '')
  if (!rahbarlar.length) return <section className="blok pos-tor"><p className="malumot">Salonda boshqa faol rahbar yo'q.</p></section>
  return (
    <section className="blok pos-tor">
      <h3>Inkassatsiya — naqd pulni rahbarga topshirish</h3>
      <label>Kimga
        <select value={rahbar} onChange={(e) => setRahbar(e.target.value)}>
          <option value="">— tanlang —</option>
          {rahbarlar.map((r) => <option key={r.id} value={r.id}>{r.ism}</option>)}
        </select>
      </label>
      <SummaForma yorliq="Topshiriladigan summa" tugma="Inkassatsiyani yozish" izohYorliq="Izoh"
        onYuborish={(summa, izoh) => (rahbar ? onYuborish(summa, izoh, Number(rahbar)) : Promise.resolve(false))} />
    </section>
  )
}

// FT-12.5: kun oxirida salonda saqlanayotgan hujjat va tillo zaloglar «joyida» deb belgilanadi.
function ZalogTekshiruvi({ onOzgardi }) {
  const [royxat, setRoyxat] = useState(null)
  const [izoh, setIzoh] = useState({})
  const [xato, setXato] = useState('')
  useEffect(() => { kassaZaloglar().then((r) => setRoyxat(r.zaloglar)).catch((e) => setXato(xatoMatni(e))) }, [])
  const belgila = async (z, joyida) => {
    setXato('')
    try { setRoyxat((await zalogBelgila({ zalog: z.id, joyida, izoh: izoh[z.id] || '' })).zaloglar); onOzgardi?.() } catch (e) { setXato(xatoMatni(e)) }
  }
  return (
    <section className="blok jadval-panel">
      <div className="jadval-asboblar"><h3 className="panel-nom">Saqlanayotgan zaloglar</h3>
        <span className="malumot">Smenani yopishdan oldin har birini seyfdan tekshirib belgilang</span></div>
      {xato && <p className="xato jadval-bosh">{xato}</p>}
      {royxat === null && !xato && <p className="malumot jadval-bosh">Yuklanmoqda…</p>}
      {royxat && royxat.length === 0 && <p className="malumot jadval-bosh">Salonda saqlanayotgan hujjat yoki tillo zalog yo'q.</p>}
      {royxat?.map((z) => (
        <div key={z.id} className="tasdiq-qator">
          <div className="tasdiq-matn">
            <b>{z.yorliq} · {z.tavsif}</b>
            <small>zakaz #{z.zakaz_raqami} ({z.mijoz}){z.joyida === true && ' · joyida'}{z.joyida === false && ' · JOYIDA EMAS'}</small>
          </div>
          <div className="tasdiq-tugmalar">
            <input placeholder="Yo'q bo'lsa izoh" aria-label="Izoh" value={izoh[z.id] || ''} maxLength={300} onChange={(e) => setIzoh({ ...izoh, [z.id]: e.target.value })} />
            <button className="ikkinchi kichik" disabled={!(izoh[z.id] || '').trim()} onClick={() => belgila(z, false)}>Yo'q</button>
            <button className={z.joyida === true ? 'kichik' : 'ikkinchi kichik'} onClick={() => belgila(z, true)}>Joyida</button>
          </div>
        </div>
      ))}
    </section>
  )
}

// FT-12.11: yopilgan smenani faqat rahbar o'zgartiradi (qayta sanash natijasi); o'zgarish jurnalga yoziladi.
function YopilganSmenalar() {
  const [royxat, setRoyxat] = useState(null)
  const [f, setF] = useState({})
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const yukla = () => smenalar().then(setRoyxat).catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) }))
  useEffect(() => { yukla() }, [])
  const saqla = async (s) => {
    setXabar({ turi: '', matn: '' })
    try {
      await smenaTuzat(s.id, { fakt_qoldiq: Number(f[`${s.id}_q`] ?? s.fakt_qoldiq), izoh: f[`${s.id}_i`] ?? s.izoh })
      setF({}); setXabar({ turi: 'ok', matn: 'Smena tuzatildi.' }); await yukla()
    } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) }
  }
  return (
    <section className="blok jadval-panel">
      <div className="jadval-asboblar"><h3 className="panel-nom">Smenalar tarixi</h3></div>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato jadval-bosh' : 'malumot jadval-bosh'}>{xabar.matn}</p>}
      {royxat && royxat.length === 0 && <p className="malumot jadval-bosh">Smena yo'q.</p>}
      {royxat?.map((s) => (
        <div key={s.id} className="tasdiq-qator">
          <div className="tasdiq-matn">
            <b>{sanaMatni(s.sana)}{s.filial ? ` · ${s.filial}` : ''} · {s.ochgan}</b>
            <small>{s.yopilgan
              ? <>hisobda {som(s.hisobdagi_qoldiq)}, sanaldi {som(s.fakt_qoldiq)}, farq <b className={s.farq ? 'qizil' : ''}>{som(s.farq)}</b></>
              : 'ochiq'}
              {s.zalog_tekshirilmagan > 0 && <span className="qizil"> · {s.zalog_tekshirilmagan} ta zalog tekshirilmagan</span>}
              {s.zalog_yoq > 0 && <b className="qizil"> · {s.zalog_yoq} ta zalog joyida emas</b>}
              {s.izoh && ` · ${s.izoh}`}</small>
          </div>
          {s.yopilgan && (
            <div className="tasdiq-tugmalar">
              <SummaInput aria-label="Fakt qoldiq" value={f[`${s.id}_q`] ?? s.fakt_qoldiq} onChange={(e) => setF({ ...f, [`${s.id}_q`]: e.target.value })} />
              <input placeholder="Izoh" aria-label="Izoh" value={f[`${s.id}_i`] ?? s.izoh} onChange={(e) => setF({ ...f, [`${s.id}_i`]: e.target.value })} />
              <button className="ikkinchi kichik" onClick={() => saqla(s)}>Tuzatish</button>
            </div>
          )}
        </div>
      ))}
    </section>
  )
}

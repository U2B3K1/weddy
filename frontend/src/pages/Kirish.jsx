import { useEffect, useRef, useState } from 'react'
import Logo from '../components/Logo'
import { pinLogin, salonLogin, saqlangan, tarmoqXatosi, xodimlar } from '../api'

// FT-1.1: avval salon logini (qurilmada bir marta), keyin xodim ismi va shaxsiy PIN.
export default function Kirish({ onKirdi }) {
  const [qurilma, setQurilma] = useState(saqlangan.qurilma())
  const [xato, setXato] = useState('')

  return (
    <main className="kirish">
      <div className="kirish-panel">
        <Logo className="kirish-logo" />
        {xato && <p className="xato" role="alert">{xato}</p>}
        {qurilma ? (
          <XodimTanlash setXato={setXato} onKirdi={onKirdi}
            onQurilmaOchirildi={() => { saqlangan.qurilmaOchir(); setQurilma(null) }} />
        ) : (
          <SalonKirish setXato={setXato} onTayyor={(t) => { saqlangan.qurilmaSaqla(t); setQurilma(t) }} />
        )}
      </div>
    </main>
  )
}

function SalonKirish({ setXato, onTayyor }) {
  const [login, setLogin] = useState('')
  const [parol, setParol] = useState('')

  const yuborish = async (e) => {
    e.preventDefault()
    setXato('')
    try {
      const r = await salonLogin(login, parol)
      onTayyor(r.qurilma_token)
    } catch {
      setXato("Login yoki parol noto'g'ri.")
    }
  }

  return (
    <form onSubmit={yuborish}>
      <p className="kirish-sarlavha">Salonga <em>kirish</em></p>
      <label>Salon logini<input value={login} onChange={(e) => setLogin(e.target.value)} autoFocus /></label>
      <label>Parol<input type="password" value={parol} onChange={(e) => setParol(e.target.value)} /></label>
      <button type="submit">Davom etish</button>
    </form>
  )
}

function XodimTanlash({ setXato, onKirdi, onQurilmaOchirildi }) {
  const [royxat, setRoyxat] = useState([])
  const [tanlangan, setTanlangan] = useState(null)
  const [pin, setPin] = useState('')
  const [kutilmoqda, setKutilmoqda] = useState(false)
  const [kodKerak, setKodKerak] = useState(false)
  const [tgKod, setTgKod] = useState('')
  const kutishRef = useRef(false)
  kutishRef.current = kutilmoqda

  useEffect(() => {
    // Faqat server «qurilma ishonchli emas» desa qurilma unutiladi; internet uzilganda emas.
    const yukla = () => xodimlar().then((r) => { setRoyxat(r); setKutilmoqda(false); setXato('') })
      .catch((e) => {
        if (tarmoqXatosi(e)) return setXato("Internet yo'q. Kirish uchun aloqa kerak.")
        // FT-22.2: yangi qurilma rahbar ruxsatini kutadi; token saqlanadi va holat tekshirib turiladi
        if (e.response?.data?.kod === 'qurilma_kutilmoqda') return setKutilmoqda(true)
        return onQurilmaOchirildi()
      })
    yukla()
    const t = setInterval(() => { if (kutishRef.current) yukla() }, 5000)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const yuborish = async (e, pinQiymat = pin) => {
    e?.preventDefault()
    setXato('')
    try {
      const r = await pinLogin(tanlangan.id, pinQiymat, kodKerak ? tgKod : undefined)
      if (r.telegram_kod_kerak) { setKodKerak(true); return }
      saqlangan.tokenSaqla(r.token)
      saqlangan.xodimSaqla(r.xodim)
      onKirdi(r.xodim)
    } catch (err) {
      if (tarmoqXatosi(err)) return setXato("Internet yo'q. Kirish uchun aloqa kerak.")
      if (kodKerak) { setTgKod(''); return setXato(err.response?.data?.detail || "Telegram kod noto'g'ri.") }
      setPin('')
      if (err.response?.status === 503) return setXato(err.response.data.detail)
      setXato(err.response?.status === 403
        ? "PIN ko'p marta xato kiritildi. 15 daqiqadan keyin urinib ko'ring."
        : "PIN noto'g'ri.")
    }
  }

  // PIN klaviaturasi: 6 raqam terilganda o'zi yuboriladi; 4–5 raqamli PIN uchun «Kirish» tugmasi.
  const raqam = (d) => {
    if (kodKerak || pin.length >= 6) return
    const r = pin + d
    setPin(r)
    if (r.length === 6) yuborish(null, r)
  }
  const ochir = () => { if (!kodKerak) setPin(pin.slice(0, -1)) }
  const orqaga = () => { setTanlangan(null); setPin(''); setKodKerak(false); setTgKod('') }

  // Kompyuter klaviaturasi ham ishlaydi (matn maydonida yozilayotganda bo'lmasa)
  const amallar = useRef(null)
  amallar.current = { raqam, ochir }
  useEffect(() => {
    if (!tanlangan) return undefined
    const h = (e) => {
      if (e.target.tagName === 'INPUT') return
      if (/^[0-9]$/.test(e.key)) amallar.current.raqam(e.key)
      else if (e.key === 'Backspace') amallar.current.ochir()
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [tanlangan])

  if (kutilmoqda) {
    return (
      <div className="xodimlar">
        <p className="ogohlantirish">Bu qurilma hali ishonchli emas. Rahbar o'z qurilmasida «Sozlama → Qurilmalar» bo'limida ruxsat berishi kerak. Ruxsat berilgach sahifa o'zi ochiladi.</p>
        <button className="ikkinchi" onClick={onQurilmaOchirildi}>Bekor qilish</button>
      </div>
    )
  }

  if (!tanlangan) {
    return (
      <div className="xodimlar">
        <p className="kirish-sarlavha">Kim <em>kirmoqda?</em></p>
        <div className="xodim-kartalar">
          {royxat.map((x) => (
            <button key={x.id} type="button" className="xodim-karta" onClick={() => setTanlangan(x)}>
              <span className="xodim-harf" aria-hidden="true">{(x.ism || '?').trim().charAt(0).toUpperCase()}</span>
              <span className="xodim-karta-ism">{x.ism}</span>
            </button>
          ))}
        </div>
        <button type="button" className="havola-tugma kirish-chiqish" onClick={onQurilmaOchirildi}>Chiqish</button>
      </div>
    )
  }
  return (
    <form onSubmit={yuborish} className="pin-forma">
      <p className="kirish-sarlavha"><em>{tanlangan.ism},</em> PIN kodingizni kiriting</p>
      <div className="pin-nuqtalar" role="img" aria-label={`${pin.length} ta raqam kiritildi`}>
        {Array.from({ length: 6 }).map((_, i) => <i key={i} className={i < pin.length ? 'to-liq' : ''} />)}
      </div>
      {kodKerak && (
        <label>Telegramga yuborilgan 6 raqamli kod
          <input inputMode="numeric" maxLength={6} value={tgKod} onChange={(e) => setTgKod(e.target.value)} autoFocus />
        </label>
      )}
      <div className="pin-klaviatura">
        {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((d) => (
          <button key={d} type="button" className="ikkinchi pin-tugma" disabled={kodKerak} onClick={() => raqam(d)}>{d}</button>
        ))}
        <button type="button" className="ikkinchi pin-tugma" aria-label="Orqaga" onClick={orqaga}>‹</button>
        <button type="button" className="ikkinchi pin-tugma" disabled={kodKerak} onClick={() => raqam('0')}>0</button>
        <button type="button" className="ikkinchi pin-tugma" aria-label="Oxirgi raqamni o'chirish" disabled={kodKerak} onClick={ochir}>⌫</button>
      </div>
      <button type="submit" disabled={kodKerak ? tgKod.length < 6 : pin.length < 4}>Kirish</button>
    </form>
  )
}

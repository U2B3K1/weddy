import { useEffect, useRef, useState } from 'react'
import { pinLogin, salonLogin, saqlangan, tarmoqXatosi, xodimlar } from '../api'

// FT-1.1: avval salon logini (qurilmada bir marta), keyin xodim ismi va shaxsiy PIN.
export default function Kirish({ onKirdi }) {
  const [qurilma, setQurilma] = useState(saqlangan.qurilma())
  const [xato, setXato] = useState('')

  return (
    <main className="kirish">
      <h1>Libosa</h1>
      {xato && <p className="xato">{xato}</p>}
      {qurilma ? (
        <XodimTanlash setXato={setXato} onKirdi={onKirdi}
          onQurilmaOchirildi={() => { saqlangan.qurilmaOchir(); setQurilma(null) }} />
      ) : (
        <SalonKirish setXato={setXato} onTayyor={(t) => { saqlangan.qurilmaSaqla(t); setQurilma(t) }} />
      )}
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

  const yuborish = async (e) => {
    e.preventDefault()
    setXato('')
    try {
      const r = await pinLogin(tanlangan.id, pin, kodKerak ? tgKod : undefined)
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
        <p>Ismingizni tanlang</p>
        {royxat.map((x) => (
          <button key={x.id} onClick={() => setTanlangan(x)}>{x.ism}</button>
        ))}
        <button className="ikkinchi" onClick={onQurilmaOchirildi}>Boshqa salon</button>
      </div>
    )
  }
  return (
    <form onSubmit={yuborish}>
      <p>{tanlangan.ism}, PIN kodingizni kiriting</p>
      <input type="password" inputMode="numeric" pattern="[0-9]{4,6}" maxLength={6}
        value={pin} onChange={(e) => setPin(e.target.value)} autoFocus disabled={kodKerak} />
      {kodKerak && (
        <label>Telegramga yuborilgan 6 raqamli kod
          <input inputMode="numeric" maxLength={6} value={tgKod} onChange={(e) => setTgKod(e.target.value)} autoFocus />
        </label>
      )}
      <button type="submit">Kirish</button>
      <button type="button" className="ikkinchi"
        onClick={() => { setTanlangan(null); setPin(''); setKodKerak(false); setTgKod('') }}>Orqaga</button>
    </form>
  )
}

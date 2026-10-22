import { useEffect, useRef, useState } from 'react'
import Logo from '../components/Logo'
import { pinLogin, qurilmaPinTasdiq, qurilmaTasdiqHolati, salonLogin, saqlangan, tarmoqXatosi, xodimlar } from '../api'

const QAYTA_URINISH = 15 * 1000         // holat olinmasa shuncha vaqtdan keyin qayta so'raladi
const HAVOLA_ZAXIRA = 2.5 * 60 * 1000   // server havolani tugashiga 2 daqiqa qolganda almashtiradi — biroz oldinroq so'raymiz

// FT-22.2: yangi qurilma ruxsat kutadi. Rahbar Telegramdagi havolani bosib (yoki QR ni telefonida skanerlab)
// botda «Ha, bu men» desa, qurilma o'zi ochiladi. Telegramdan foydalana olmaydigan rahbar shu yerda PIN bilan tasdiqlaydi.
function QurilmaKutish({ setXato, onTasdiqlandi, onBekor }) {
  const [holat, setHolat] = useState(null)
  const [qr, setQr] = useState('')
  const [rahbar, setRahbar] = useState(null)
  const [pin, setPin] = useState('')

  useEffect(() => {
    let tirik = true
    let taymer
    const ol = () => {
      clearTimeout(taymer)
      qurilmaTasdiqHolati().then(async (d) => {
        if (!tirik) return
        if (d.tasdiqlangan) return onTasdiqlandi()
        setHolat(d)
        // Havola muddati tugashidan oldin yangisini so'raymiz (server o'sha havolani qaytaradi, eskisi buzilmaydi)
        if (d.tg_tugaydi) taymer = setTimeout(ol, Math.max(QAYTA_URINISH, new Date(d.tg_tugaydi) - Date.now() - HAVOLA_ZAXIRA))
        if (!d.tg_havola) return setQr('')
        try {
          const { default: QRCode } = await import('qrcode')  // faqat shu ekranda kerak — umumiy yuklamaga qo'shilmaydi
          const rasm = await QRCode.toDataURL(d.tg_havola, { margin: 1, width: 220 })
          if (tirik) setQr(rasm)
        } catch { if (tirik) setQr('') }
      }).catch((e) => {
        if (!tirik) return
        if (e.response?.status === 401) return onBekor()  // qurilma rad etilgan — salon logini sahifasiga
        taymer = setTimeout(ol, QAYTA_URINISH)
      })
    }
    // Uxlagan planshetda taymerlar to'xtaydi: ekran yonganda eskirgan QR o'rniga yangisini olamiz
    const korindi = () => { if (document.visibilityState === 'visible') ol() }
    ol()
    document.addEventListener('visibilitychange', korindi)
    return () => { tirik = false; clearTimeout(taymer); document.removeEventListener('visibilitychange', korindi) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const pinBilan = async (e) => {
    e.preventDefault()
    setXato('')
    try {
      await qurilmaPinTasdiq(rahbar.id, pin)
      onTasdiqlandi()
    } catch (err) {
      if (tarmoqXatosi(err)) return setXato("Internet yo'q. Kirish uchun aloqa kerak.")
      setPin('')
      const s = err.response.status
      if (s === 401) return onBekor()  // qurilma shu orada rad etilgan
      // 404: rahbar shu orada Telegram uladi yoki o'chirildi; 403: PIN bloki, sutkalik chegara yoki «faqat ko'rish»
      if (s === 404) { setRahbar(null); return setXato(err.response.data?.detail || 'Rahbar topilmadi.') }
      if (s === 400) return setXato("PIN noto'g'ri.")
      setXato(err.response.data?.detail || "Ruxsat berib bo'lmadi. Birozdan keyin urinib ko'ring.")
    }
  }

  if (rahbar) {
    return (
      <form onSubmit={pinBilan}>
        <p className="kirish-sarlavha"><em>{rahbar.ism},</em> qurilmaga ruxsat bering</p>
        <label>Shaxsiy PIN kodingiz
          <input type="password" inputMode="numeric" maxLength={6} value={pin} onChange={(e) => setPin(e.target.value)} autoFocus />
        </label>
        <button type="submit" disabled={pin.length < 4}>Ruxsat berish</button>
        <button type="button" className="havola-tugma kirish-chiqish" onClick={() => { setRahbar(null); setPin('') }}>‹ Orqaga</button>
      </form>
    )
  }

  return (
    <div className="xodimlar qurilma-kutish">
      <p className="kirish-sarlavha">Qurilma <em>ruxsat kutmoqda</em></p>
      {!holat ? (
        <p className="malumot">Yuklanmoqda…</p>
      ) : holat.tg_havola ? (
        <>
          <p className="malumot">Rahbar Telegram orqali ruxsat beradi. Bu rahbarning telefoni bo'lsa — tugmani bosing,
            planshet yoki kompyuter bo'lsa — QR kodni rahbar telefonida skanerlang. Botda «Ha, bu men» ni bosing.</p>
          <a className="tugma-havola" href={holat.tg_havola} target="_blank" rel="noopener noreferrer">Telegram orqali tasdiqlash</a>
          {qr && <img className="qurilma-qr" src={qr} alt="Telegram tasdiq havolasi QR kodi" width="220" height="220" />}
        </>
      ) : (
        <p className="malumot">Rahbar o'z qurilmasida «Sozlama → Qurilmalar» bo'limida ruxsat berishi kerak.</p>
      )}
      {holat?.rahbarlar?.length > 0 && (
        <>
          <p className="malumot">Siz rahbarmisiz? Shu yerda PIN kodingiz bilan ruxsat bering:</p>
          <div className="xodim-kartalar">
            {holat.rahbarlar.map((x) => (
              <button key={x.id} type="button" className="xodim-karta" onClick={() => setRahbar(x)}>
                <span className="xodim-harf" aria-hidden="true">{(x.ism || '?').trim().charAt(0).toUpperCase()}</span>
                <span className="xodim-karta-ism">{x.ism}</span>
              </button>
            ))}
          </div>
        </>
      )}
      <p className="malumot">Ruxsat berilgach sahifa o'zi ochiladi.</p>
      <button type="button" className="havola-tugma kirish-chiqish" onClick={onBekor}>Bekor qilish</button>
    </div>
  )
}

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
    } catch (err) {
      if (tarmoqXatosi(err)) return setXato("Internet yo'q. Kirish uchun aloqa kerak.")
      // 403: parol ko'p marta xato kiritilgan — to'g'ri parol ham vaqtincha o'tmaydi
      setXato(err.response.status === 403 ? err.response.data?.detail || "Keyinroq urinib ko'ring." : "Login yoki parol noto'g'ri.")
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

  // Faqat server «qurilma ishonchli emas» desa qurilma unutiladi; internet uzilganda emas.
  const yukla = () => xodimlar().then((r) => { setRoyxat(r); setKutilmoqda(false); setXato('') })
    .catch((e) => {
      if (tarmoqXatosi(e)) return setXato("Internet yo'q. Kirish uchun aloqa kerak.")
      // FT-22.2: yangi qurilma rahbar ruxsatini kutadi; token saqlanadi va holat tekshirib turiladi
      if (e.response?.data?.kod === 'qurilma_kutilmoqda') return setKutilmoqda(true)
      return onQurilmaOchirildi()
    })
  useEffect(() => {
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

  if (kutilmoqda) return <QurilmaKutish setXato={setXato} onTasdiqlandi={yukla} onBekor={onQurilmaOchirildi} />


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

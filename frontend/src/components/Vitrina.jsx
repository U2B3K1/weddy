import { useState } from 'react'
import { pinTekshir, som, xatoMatni } from '../api'

// FT-23.1: «Mijozga ko'rsatish» — planshet mijozga buriladi. Faqat katta rasmlar, libos nomi va ijara narxi;
// menyular, boshqa mijozlar va ichki ma'lumot yashirin. Chiqish faqat xodim PIN kodi bilan.
export default function Vitrina({ liboslar, onChiqish }) {
  const [indeks, setIndeks] = useState(0)
  const [rakurs, setRakurs] = useState(0)
  const [pinOyna, setPinOyna] = useState(false)
  const [pin, setPin] = useState('')
  const [xato, setXato] = useState('')

  const l = liboslar[indeks]
  const rasmlar = l.rasmlar?.length ? l.rasmlar : (l.rasm_katta ? [l.rasm_katta] : [])
  const otish = (d) => { setIndeks((indeks + d + liboslar.length) % liboslar.length); setRakurs(0) }

  const chiqish = async (e) => {
    e.preventDefault()
    setXato('')
    try {
      await pinTekshir(pin)
      onChiqish()
    } catch (err) {
      setPin('')
      setXato(xatoMatni(err, "PIN noto'g'ri."))
    }
  }

  return (
    <div className="vitrina">
      <button type="button" className="vitrina-chiqish" aria-label="Rejimdan chiqish" onClick={() => setPinOyna(true)}>×</button>

      <div className="vitrina-rasm">
        {rasmlar.length > 0
          ? <img src={rasmlar[rakurs]} alt={l.nomi} onClick={() => setRakurs((rakurs + 1) % rasmlar.length)} />
          : <div className="vitrina-rasmsiz">Rasm yo'q</div>}
        {rasmlar.length > 1 && (
          <div className="vitrina-nuqtalar">
            {rasmlar.map((_, i) => <span key={i} className={i === rakurs ? 'faol' : ''} />)}
          </div>
        )}
      </div>

      <div className="vitrina-malumot">
        <h2>{l.nomi}</h2>
        <p className="vitrina-kategoriya">{l.kategoriya}{l.olcham ? ` · o'lcham ${l.olcham}` : ''}</p>
        <p className="vitrina-narx">{som(l.ijara_narxi)}</p>
      </div>

      {liboslar.length > 1 && (
        <div className="vitrina-nav">
          <button type="button" onClick={() => otish(-1)}>‹ Oldingi</button>
          <span>{indeks + 1} / {liboslar.length}</span>
          <button type="button" onClick={() => otish(1)}>Keyingi ›</button>
        </div>
      )}

      {pinOyna && (
        <form className="vitrina-pin" onSubmit={chiqish}>
          <p>Xodim PIN kodi</p>
          <input type="password" inputMode="numeric" maxLength={6} autoFocus value={pin}
            onChange={(e) => setPin(e.target.value)} />
          {xato && <p className="xato">{xato}</p>}
          <div className="qator">
            <button type="submit" disabled={!pin}>Chiqish</button>
            <button type="button" className="ikkinchi" onClick={() => { setPinOyna(false); setPin(''); setXato('') }}>Bekor</button>
          </div>
        </form>
      )}
    </div>
  )
}

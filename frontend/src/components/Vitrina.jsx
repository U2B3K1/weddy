import { useEffect, useRef, useState } from 'react'
import { pinTekshir, som, xatoMatni } from '../api'
import LibosSiluet from './LibosSiluet'

// FT-23.1: «Mijozga ko'rsatish» — planshet mijozga buriladi. Faqat katta rasmlar, libos nomi va ijara narxi;
// menyular, boshqa mijozlar va ichki ma'lumot yashirin. Xodim rejimiga qaytish faqat o'sha xodimning PIN kodi bilan.
// Varaqlash: tugmalar, klaviatura strelkalari yoki barmoq bilan surish; rasm bosilsa keyingi rakurs.
export default function Vitrina({ liboslar, onChiqish }) {
  const [indeks, setIndeks] = useState(0)
  const [rakurs, setRakurs] = useState(0)
  const [pinOyna, setPinOyna] = useState(false)
  const [pin, setPin] = useState('')
  const [xato, setXato] = useState('')
  const [tekshirilmoqda, setTekshirilmoqda] = useState(false)
  const surish = useRef(null)

  const l = liboslar[indeks]
  const rasmlar = l.rasmlar?.length ? l.rasmlar : (l.rasm_katta ? [l.rasm_katta] : [])
  const kop = liboslar.length > 1
  const otish = (d) => { if (!kop) return; setIndeks((i) => (i + d + liboslar.length) % liboslar.length); setRakurs(0) }
  const pinniYop = () => { setPinOyna(false); setPin(''); setXato('') }

  // Strelkalar — varaqlash; Escape — PIN oynasini yopish
  useEffect(() => {
    const h = (e) => {
      if (pinOyna) { if (e.key === 'Escape') { setPinOyna(false); setPin(''); setXato('') } return }
      const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key]
      if (d && liboslar.length > 1) { setIndeks((i) => (i + d + liboslar.length) % liboslar.length); setRakurs(0) }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [pinOyna, liboslar.length])

  const chiqish = async (e) => {
    e.preventDefault()
    if (tekshirilmoqda) return
    setXato('')
    setTekshirilmoqda(true)
    try {
      await pinTekshir(pin)
      onChiqish()
    } catch (err) {
      setPin('')
      setXato(xatoMatni(err, "PIN noto'g'ri."))
    } finally {
      setTekshirilmoqda(false)
    }
  }

  return (
    <div className="vitrina" role="dialog" aria-modal="true" aria-label="Mijozga ko'rsatish rejimi">
      <div className="vitrina-yuqori">
        {kop && <span className="vitrina-hisob" aria-live="polite">{indeks + 1} / {liboslar.length}</span>}
        <button type="button" className="ikkinchi kichik vitrina-chiqish" onClick={() => setPinOyna(true)}>
          Xodim rejimiga qaytish
        </button>
      </div>

      <div className="vitrina-sahna"
        onTouchStart={(e) => { surish.current = e.touches[0].clientX }}
        onTouchEnd={(e) => {
          if (surish.current === null) return
          const farq = e.changedTouches[0].clientX - surish.current
          surish.current = null
          if (Math.abs(farq) > 50) otish(farq < 0 ? 1 : -1)
        }}>
        {kop && <button type="button" className="vitrina-strelka chap" aria-label="Oldingi libos" onClick={() => otish(-1)}>‹</button>}
        <div className="vitrina-rasm">
          {rasmlar.length > 0
            ? <img key={rasmlar[rakurs]} src={rasmlar[rakurs]} alt={l.nomi}
              onClick={() => setRakurs((rakurs + 1) % rasmlar.length)} />
            : <LibosSiluet className="vitrina-siluet" />}
          {rasmlar.length > 1 && (
            <div className="vitrina-nuqtalar" aria-label={`Rakurs ${rakurs + 1} / ${rasmlar.length}`}>
              {rasmlar.map((r, i) => (
                <button key={r} type="button" className={i === rakurs ? 'faol' : ''} aria-label={`${i + 1}-rakurs`} onClick={() => setRakurs(i)} />
              ))}
            </div>
          )}
        </div>
        {kop && <button type="button" className="vitrina-strelka ong" aria-label="Keyingi libos" onClick={() => otish(1)}>›</button>}
      </div>

      <div className="vitrina-malumot">
        <h2>{l.nomi}</h2>
        <p className="vitrina-kategoriya">{l.kategoriya}{l.olcham ? `, o'lcham ${l.olcham}` : ''}</p>
        <p className="vitrina-narx">{som(l.ijara_narxi)}</p>
      </div>

      {pinOyna && (
        <div className="vitrina-pin-parda" onClick={(e) => { if (e.target === e.currentTarget) pinniYop() }}>
          <form className="vitrina-pin" onSubmit={chiqish}>
            <h3>Xodim rejimiga qaytish</h3>
            <p className="malumot">Zakazni rasmiylashtirayotgan xodimning PIN kodini kiriting.</p>
            <input type="password" inputMode="numeric" autoComplete="off" maxLength={6} autoFocus value={pin}
              aria-label="PIN kod" onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))} />
            {xato && <p className="xato">{xato}</p>}
            <div className="vitrina-pin-tugmalar">
              <button type="button" className="ikkinchi" onClick={pinniYop}>Bekor qilish</button>
              <button type="submit" disabled={pin.length < 4 || tekshirilmoqda}>{tekshirilmoqda ? 'Tekshirilmoqda…' : 'Qaytish'}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

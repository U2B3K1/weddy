import { useEffect, useRef, useState } from 'react'
import NavIkona from './NavIkona'

// Xodim menyusi: belgi (profil rasmi yoki ismning bosh harfi) bosilsa — salon nomi, profil rasmi va «Chiqish».
// Kompyuterda yuqori panelda ism va rol bilan; telefonda (`ixcham`) shapkada faqat doira belgi.
export default function XodimMenyu({ xodim, rol, onChiqish, onRasm, onRasmOchir, ixcham = false }) {
  const [ochiq, setOchiq] = useState(false)
  const [rasmXato, setRasmXato] = useState('')
  const [yuklanmoqda, setYuklanmoqda] = useState(false)
  const joy = useRef(null)
  const fayl = useRef(null)
  useEffect(() => {
    if (!ochiq) return undefined
    const yop = (e) => { if (!joy.current?.contains(e.target)) setOchiq(false) }
    const esc = (e) => { if (e.key === 'Escape') setOchiq(false) }
    document.addEventListener('pointerdown', yop)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('pointerdown', yop); document.removeEventListener('keydown', esc) }
  }, [ochiq])

  const rasmTanla = async (e) => {
    const f = e.target.files?.[0]
    e.target.value = ''  // shu faylni qayta tanlasa ham ishlasin
    if (!f) return
    setRasmXato(''); setYuklanmoqda(true)
    try { await onRasm(f); setOchiq(false) } catch (err) { setRasmXato(err.message) } finally { setYuklanmoqda(false) }
  }
  const harf = (xodim.ism || '?').trim().charAt(0).toUpperCase()

  return (
    <div className="ustki-joy" ref={joy}>
      <button type="button" className={ixcham ? 'shapka-xodim' : 'ustki-xodim'} aria-expanded={ochiq} aria-haspopup="menu"
        aria-label={ixcham ? `${xodim.ism}: profil va chiqish` : undefined} onClick={() => setOchiq(!ochiq)}>
        <span className="xodim-chip">
          <XodimBelgi xodim={xodim} harf={harf} />
          {!ixcham && <span><b>{xodim.ism}</b>{xodim.ism?.trim() !== rol && <small>{rol}</small>}</span>}
        </span>
        {!ixcham && <NavIkona nom="ong" className="tugma-ikon pastga" />}
      </button>
      {ochiq && (
        <div className="ustki-menyu" role="menu">
          <p className="malumot">{ixcham && <><b>{xodim.ism}</b>{xodim.ism?.trim() !== rol && ` · ${rol}`}<br /></>}{xodim.salon}</p>
          {/* profil rasmi — kirish ekranidagi kartochkada va shapkada ko'rinadi */}
          <button type="button" role="menuitem" disabled={yuklanmoqda} onClick={() => fayl.current?.click()}>
            <NavIkona nom="kamera" className="tugma-ikon" />
            {yuklanmoqda ? 'Yuklanmoqda…' : xodim.rasm ? 'Profil rasmini almashtirish' : 'Profil rasmini yuklash'}
          </button>
          <input ref={fayl} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={rasmTanla} />
          {xodim.rasm && (
            <button type="button" role="menuitem" onClick={() => onRasmOchir().catch((err) => setRasmXato(err.message))}>
              <NavIkona nom="yop" className="tugma-ikon" />Rasmni olib tashlash
            </button>
          )}
          {rasmXato && <p className="xato ustki-menyu-xato" role="alert">{rasmXato}</p>}
          {/* xodim ilovadan chiqadi (PIN ekrani); salon logini qurilmada qoladi — keyingi xodim o'z PIN'i bilan kiradi */}
          <button type="button" role="menuitem" onClick={onChiqish}><NavIkona nom="chiqish" className="tugma-ikon" />Chiqish</button>
        </div>
      )}
    </div>
  )
}

// Xodim belgisi: profil rasmi, bo'lmasa ismning bosh harfi
export function XodimBelgi({ xodim, harf }) {
  return <i aria-hidden="true">{xodim.rasm ? <img src={xodim.rasm} alt="" /> : harf}</i>
}

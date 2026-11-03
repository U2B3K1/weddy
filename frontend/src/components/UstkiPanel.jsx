import { useEffect, useRef, useState } from 'react'
import NavIkona from './NavIkona'

// Kontent ustidagi yuqori panel (barcha sahifalarda): chapda sahifa nomi, o'ngda zakaz qidiruvi,
// bildirishnomalar (rahbarga: qaror kutayotganlar va ogohlantirishlar) va xodim menyusi.
export default function UstkiPanel({ sarlavha, izoh, xodim, rahbar, xabarlar, onQidir, onBolim, onChiqish, onRasm, onRasmOchir }) {
  const [q, setQ] = useState('')
  const [ochiq, setOchiq] = useState(null) // 'xabar' | 'xodim' | null
  const joy = useRef(null)
  const fayl = useRef(null)
  const [rasmXato, setRasmXato] = useState('')
  const [yuklanmoqda, setYuklanmoqda] = useState(false)
  const rasmTanla = async (e) => {
    const f = e.target.files?.[0]
    e.target.value = ''  // shu faylni qayta tanlasa ham ishlasin
    if (!f) return
    setRasmXato(''); setYuklanmoqda(true)
    try { await onRasm(f); setOchiq(null) } catch (err) { setRasmXato(err.message) } finally { setYuklanmoqda(false) }
  }
  useEffect(() => {
    if (!ochiq) return undefined
    const yop = (e) => { if (!joy.current?.contains(e.target)) setOchiq(null) }
    const esc = (e) => { if (e.key === 'Escape') setOchiq(null) }
    document.addEventListener('pointerdown', yop)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('pointerdown', yop); document.removeEventListener('keydown', esc) }
  }, [ochiq])

  const harf = (xodim.ism || '?').trim().charAt(0).toUpperCase()
  const rol = rahbar ? 'Rahbar' : xodim.rol === 'kassir' ? 'Kassir' : 'Sotuvchi'
  const soni = xabarlar.reduce((s, x) => s + x.soni, 0)
  const bor = (k) => () => { setOchiq(null); onBolim(k) }

  return (
    <header className="ustki" ref={joy}>
      <div className="ustki-nom">
        <h1>{sarlavha}</h1>
        {izoh && <p>{izoh}</p>}
      </div>
      <form className="qidiruv-maydon ustki-qidiruv" role="search"
        onSubmit={(e) => { e.preventDefault(); if (q.trim()) { onQidir(q.trim()); setQ('') } }}>
        <NavIkona nom="qidiruv" className="tugma-ikon" />
        <input type="search" placeholder="Zakaz: raqam, telefon yoki ism" aria-label="Zakaz qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
      </form>
      {rahbar && (
        <div className="ustki-joy">
          <button type="button" className="ustki-tugma" aria-label={`Bildirishnomalar: ${soni}`} aria-expanded={ochiq === 'xabar'}
            onClick={() => setOchiq(ochiq === 'xabar' ? null : 'xabar')}>
            <svg className="tugma-ikon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
            {soni > 0 && <span className="ustki-son">{soni > 99 ? '99+' : soni}</span>}
          </button>
          {ochiq === 'xabar' && (
            <div className="ustki-menyu xabar-menyu" role="menu">
              <b>Bildirishnomalar</b>
              {xabarlar.length === 0 && <p className="malumot">Hozircha hammasi joyida.</p>}
              {xabarlar.map((x) => (
                <button key={x.matn} type="button" role="menuitem" onClick={bor(x.bolim)}>
                  <i className={`nuqta ${x.tur}`} aria-hidden="true" />{x.matn}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      <div className="ustki-joy">
        <button type="button" className="ustki-xodim" aria-expanded={ochiq === 'xodim'} aria-haspopup="menu" onClick={() => setOchiq(ochiq === 'xodim' ? null : 'xodim')}>
          <span className="xodim-chip"><XodimBelgi xodim={xodim} harf={harf} /><span><b>{xodim.ism}</b>{xodim.ism?.trim() !== rol && <small>{rol}</small>}</span></span>
          <NavIkona nom="ong" className="tugma-ikon pastga" />
        </button>
        {ochiq === 'xodim' && (
          <div className="ustki-menyu" role="menu">
            <p className="malumot">{xodim.salon}</p>
            {/* profil rasmi — kirish ekranidagi kartochkada va shu yerda ko'rinadi */}
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
    </header>
  )
}

// Xodim belgisi (shapkada): profil rasmi, bo'lmasa ismning bosh harfi
export function XodimBelgi({ xodim, harf }) {
  return <i aria-hidden="true">{xodim.rasm ? <img src={xodim.rasm} alt="" /> : harf}</i>
}

import { useEffect, useRef, useState } from 'react'
import NavIkona from './NavIkona'
import XodimMenyu from './XodimMenyu'

// Kontent ustidagi yuqori panel (barcha sahifalarda): chapda sahifa nomi, o'ngda zakaz qidiruvi,
// bildirishnomalar (rahbarga: qaror kutayotganlar va ogohlantirishlar) va xodim menyusi.
export default function UstkiPanel({ sarlavha, izoh, xodim, rahbar, xabarlar, onQidir, onBolim, onChiqish, onRasm, onRasmOchir }) {
  const [q, setQ] = useState('')
  const [ochiq, setOchiq] = useState(null) // 'xabar' | null
  const joy = useRef(null)
  useEffect(() => {
    if (!ochiq) return undefined
    const yop = (e) => { if (!joy.current?.contains(e.target)) setOchiq(null) }
    const esc = (e) => { if (e.key === 'Escape') setOchiq(null) }
    document.addEventListener('pointerdown', yop)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('pointerdown', yop); document.removeEventListener('keydown', esc) }
  }, [ochiq])

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
      <XodimMenyu xodim={xodim} rol={rol} onChiqish={onChiqish} onRasm={onRasm} onRasmOchir={onRasmOchir} />
    </header>
  )
}


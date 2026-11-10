import { useState } from 'react'

// Uzun ro'yxatlarni sahifalash (mijoz tomonida, ro'yxat allaqachon yuklangan): sahifa cho'zilib ketmasin
// (Smenalar tarixi, Qurilmalar, Jurnal, Xarajatlar, Garovlar, Zakazlar…).
// <Sahifali royxat={...} hajm={10} kalit={filtr}>{(qism) => qism.map(...)}</Sahifali>
// `kalit` o'zgarsa (qidiruv, filtr) — 1-sahifaga qaytadi. Bitta sahifaga sig'sa — tugmalar ko'rinmaydi.
export default function Sahifali({ royxat, hajm = 10, kalit = '', nomi = 'ta', children }) {
  const [h, setH] = useState({ sahifa: 1, kalit })
  if (h.kalit !== kalit) setH({ sahifa: 1, kalit })  // render vaqtida tiklash (effekt va qo'shimcha chizishsiz)
  const jami = royxat?.length || 0
  const sahifalar = Math.max(1, Math.ceil(jami / hajm))
  const sahifa = Math.min(h.kalit === kalit ? h.sahifa : 1, sahifalar)
  const qism = (royxat || []).slice((sahifa - 1) * hajm, sahifa * hajm)
  return (
    <>
      {children(qism)}
      {sahifalar > 1 && <Sahifalash sahifa={sahifa} sahifalar={sahifalar} jami={jami} hajm={hajm} nomi={nomi}
        onTanla={(s) => setH({ sahifa: s, kalit })} />}
    </>
  )
}

// Sahifa raqamlari: 1 … joriy atrofi … oxirgi; «‹ ›» — oldingi/keyingi. Sahifa almashganda ro'yxat boshi ko'rinadi.
// Server sahifalaydigan ro'yxatlar (Zakazlar) to'g'ridan-to'g'ri shuni ishlatadi.
export function Sahifalash({ sahifa, sahifalar, jami, hajm, nomi, onTanla }) {
  const raqamlar = []
  for (let i = 1; i <= sahifalar; i++) {
    if (i === 1 || i === sahifalar || Math.abs(i - sahifa) <= 1) raqamlar.push(i)
    else if (raqamlar[raqamlar.length - 1] !== '…') raqamlar.push('…')
  }
  const dan = (sahifa - 1) * hajm + 1
  const gacha = Math.min(sahifa * hajm, jami)
  const tanla = (s, e) => {
    onTanla(s)
    const blok = e.currentTarget.closest('.blok, section')
    if (blok && blok.getBoundingClientRect().top < 0) {
      blok.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
    }
  }
  return (
    <nav className="sahifalash" aria-label="Sahifalar">
      <span className="sahifalash-izoh">{jami} {nomi}dan {dan}–{gacha}</span>
      <button type="button" className="sahifalash-tugma" aria-label="Oldingi sahifa" disabled={sahifa === 1} onClick={(e) => tanla(sahifa - 1, e)}>‹</button>
      {raqamlar.map((r, i) => (r === '…'
        ? <span key={`b${i}`} className="sahifalash-bosh" aria-hidden="true">…</span>
        : (
          <button key={r} type="button" className={`sahifalash-tugma${r === sahifa ? ' faol' : ''}`} aria-label={`${r}-sahifa`}
            aria-current={r === sahifa ? 'page' : undefined} onClick={(e) => tanla(r, e)}>{r}</button>
        )))}
      <button type="button" className="sahifalash-tugma" aria-label="Keyingi sahifa" disabled={sahifa === sahifalar} onClick={(e) => tanla(sahifa + 1, e)}>›</button>
    </nav>
  )
}

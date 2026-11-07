import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

// Xavfli amallar uchun tasdiq oynasi: telefonda pastdan chiqadi, keng ekranda markazda turadi.
// `matn` — amal natijasi aytiladi («Zakaz #124 bekor qilinadi, 450 000 so'm qaytariladi»).
// `bekorMatn` / `onBekor` (ixtiyoriy) — chap tugma boshqa ish qilsa (masalan, «Chiqish»); Escape va fon bosilsa — `onYop`.
// `fokus` — boshlang'ich fokus: 'bekor' (standart, xavfli amalda tasodifiy tasdiq bo'lmasin) yoki 'tasdiq'.
export default function Tasdiq({ sarlavha, matn, tugma = 'Tasdiqlash', xavfli = true, onTasdiq, onYop,
  bekorMatn = "Yo'q, qaytish", onBekor, fokus = 'bekor' }) {
  const bekorRef = useRef(null)
  const tasdiqRef = useRef(null)
  const yopRef = useRef(onYop)
  useEffect(() => { yopRef.current = onYop }, [onYop])
  // fokus faqat ochilganda (oyna ichida sanoq kabi qayta render bo'lsa ham foydalanuvchi tanlagan tugmada qoladi)
  useEffect(() => {
    (fokus === 'tasdiq' ? tasdiqRef : bekorRef).current?.focus()
    const esc = (e) => { if (e.key === 'Escape') yopRef.current() }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [fokus])
  // body'ga chiqariladi: shisha (backdrop-filter) bloklar ichida `position: fixed` ota blokka bog'lanib, oyna kichrayib qolardi
  return createPortal(
    <div className="oyna-parda" onClick={onYop}>
      <div className="oyna" role="alertdialog" aria-modal="true" aria-label={sarlavha} onClick={(e) => e.stopPropagation()}>
        <h3>{sarlavha}</h3>
        <p className="malumot">{matn}</p>
        <div className="oyna-tugmalar">
          <button type="button" className="ikkinchi" ref={bekorRef} onClick={onBekor || onYop}>{bekorMatn}</button>
          <button type="button" className={xavfli ? 'xavfli' : ''} ref={tasdiqRef} onClick={onTasdiq}>{tugma}</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

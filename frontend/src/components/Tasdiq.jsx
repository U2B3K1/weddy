import { useEffect, useRef } from 'react'

// Xavfli amallar uchun tasdiq oynasi: telefonda pastdan chiqadi, keng ekranda markazda turadi.
// `matn` — amal natijasi aytiladi («Zakaz #124 bekor qilinadi, 450 000 so'm qaytariladi»).
export default function Tasdiq({ sarlavha, matn, tugma = 'Tasdiqlash', xavfli = true, onTasdiq, onYop }) {
  const ref = useRef(null)
  useEffect(() => {
    ref.current?.focus()
    const esc = (e) => { if (e.key === 'Escape') onYop() }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onYop])
  return (
    <div className="oyna-parda" onClick={onYop}>
      <div className="oyna" role="alertdialog" aria-modal="true" aria-label={sarlavha} onClick={(e) => e.stopPropagation()}>
        <h3>{sarlavha}</h3>
        <p className="malumot">{matn}</p>
        <div className="oyna-tugmalar">
          <button type="button" className="ikkinchi" ref={ref} onClick={onYop}>Yo'q, qaytish</button>
          <button type="button" className={xavfli ? 'xavfli' : ''} onClick={onTasdiq}>{tugma}</button>
        </div>
      </div>
    </div>
  )
}

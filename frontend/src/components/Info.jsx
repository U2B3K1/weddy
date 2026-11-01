import { useEffect, useRef, useState } from 'react'

// Maydon yoki sarlavha yonidagi «i»: bosilganda qisqa tushuntirish chiqadi. Tashqariga bosilsa, fokus boshqa maydonga
// o'tsa (Tab) yoki Esc — yopiladi.
// Forma maydoni (label) ichida tepa o'ng burchakda turadi, matn yonida esa qator ichida. Label ichida inputdan KEYIN
// qo'yiladi: aks holda label birinchi tugmaga bog'lanib qoladi (yorliq bosilganda kursor maydonga tushmaydi).
export default function Info({ nom, children }) {
  const [ochiq, setOchiq] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    if (!ochiq) return
    const tashqi = (e) => { if (!ref.current?.contains(e.target)) setOchiq(false) }
    const esc = (e) => { if (e.key === 'Escape') { e.stopPropagation(); setOchiq(false) } }
    document.addEventListener('pointerdown', tashqi)
    document.addEventListener('focusin', tashqi)
    document.addEventListener('keydown', esc, true)
    return () => {
      document.removeEventListener('pointerdown', tashqi); document.removeEventListener('focusin', tashqi)
      document.removeEventListener('keydown', esc, true)
    }
  }, [ochiq])
  return (
    <span className="info" ref={ref}>
      <button type="button" className="info-tugma" aria-label="Izoh" title={`${nom} haqida`} aria-expanded={ochiq}
        onClick={(e) => { e.preventDefault(); setOchiq(!ochiq) }}>i</button>
      {ochiq && <span className="info-matn" role="note" onClick={(e) => e.preventDefault()}>{children}</span>}
    </span>
  )
}

import { useEffect, useRef, useState } from 'react'
import NavIkona from './NavIkona'

const FOKUSLANADI = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

// Forma oynasi (qo'shish, boshqarish): telefonda pastdan chiqadi, keng ekranda markazda.
// Sahifa ichidagi yig'iladigan «details» formalar o'rniga — ro'yxat va asboblar paneli toza qoladi.
// Yopish: «×» — darhol; fon yoki Escape — formaga biror narsa kiritilgan bo'lsa avval so'raydi («Kiritilganlar o'chadi»),
// aks holda tasodifiy bosish to'ldirilgan formani yo'qotardi. Fokus oyna ichida aylanadi (Tab), yopilgach uni ochgan
// tugmaga qaytadi. Props (sarlavha, onYop, children, keng) o'zgarmagan — boshqa bo'limlar ham shu oynani ishlatadi.
export default function Oyna({ sarlavha, onYop, children, keng = false }) {
  const ref = useRef(null)
  const ozgardi = useRef(false)  // oyna ichidagi maydonga biror narsa kiritildimi (input/change hodisalari)
  const [soraladi, setSoraladi] = useState(false)
  const yopRef = useRef(onYop)
  useEffect(() => { yopRef.current = onYop })

  // Fon yoki Escape: o'zgarish bo'lsa — so'rov qatori, bo'lmasa — darhol yopiladi
  const ehtiyotYop = () => { if (ozgardi.current) setSoraladi(true); else yopRef.current() }
  const ehtiyotRef = useRef(ehtiyotYop)
  useEffect(() => { ehtiyotRef.current = ehtiyotYop })

  // Faqat ochilganda: birinchi maydonga fokus, yopilganda — ochgan elementga qaytish. (Avval har qayta chizishda
  // birinchi maydonga qaytib o'tardi: onYop har safar yangi funksiya bo'lgani uchun effekt qayta ishlardi.)
  useEffect(() => {
    const oldingi = document.activeElement
    ref.current?.querySelector('input, select, textarea, button:not(.oyna-yop)')?.focus()
    return () => { if (oldingi && document.contains(oldingi)) oldingi.focus?.() }
  }, [])

  useEffect(() => {
    const tugma = (e) => {
      // Ichidagi tasdiq oynasi (Tasdiq, alertdialog) ochiq bo'lsa — Escape va Tab o'shaniki
      if (document.querySelector('[role="alertdialog"]')) return
      if (e.key === 'Escape') {
        e.preventDefault()
        if (soraladi) setSoraladi(false)
        else ehtiyotRef.current()
        return
      }
      if (e.key !== 'Tab' || !ref.current) return
      const el = [...ref.current.querySelectorAll(FOKUSLANADI)].filter((x) => x.offsetParent !== null || x === document.activeElement)
      if (!el.length) return
      const birinchi = el[0], oxirgi = el[el.length - 1]
      if (!ref.current.contains(document.activeElement)) { e.preventDefault(); birinchi.focus() }
      else if (e.shiftKey && document.activeElement === birinchi) { e.preventDefault(); oxirgi.focus() }
      else if (!e.shiftKey && document.activeElement === oxirgi) { e.preventDefault(); birinchi.focus() }
    }
    window.addEventListener('keydown', tugma)
    return () => window.removeEventListener('keydown', tugma)
  }, [soraladi])

  // So'rov qatori chiqqanda fokus «Yo'q, davom etish» tugmasiga
  const davomRef = useRef(null)
  useEffect(() => { if (soraladi) davomRef.current?.focus() }, [soraladi])

  return (
    <div className="oyna-parda" onClick={ehtiyotYop}>
      <div className={`oyna${keng ? ' oyna-keng' : ''}`} role="dialog" aria-modal="true" aria-label={sarlavha} ref={ref}
        onClick={(e) => e.stopPropagation()}
        onInput={() => { ozgardi.current = true }} onChange={() => { ozgardi.current = true }}>
        <div className="oyna-bosh">
          <h3>{sarlavha}</h3>
          <button type="button" className="ikkinchi kichik oyna-yop" aria-label="Yopish" onClick={() => yopRef.current()}><NavIkona nom="yop" className="tugma-ikon" /></button>
        </div>
        {soraladi && (
          <div className="oyna-soroq" role="alert">
            <span>Kiritilganlar o'chadi. Yopilsinmi?</span>
            <div className="qator">
              <button type="button" className="ikkinchi kichik" ref={davomRef} onClick={() => setSoraladi(false)}>Yo'q, davom etish</button>
              <button type="button" className="xavfli kichik" onClick={() => yopRef.current()}>Ha, yopish</button>
            </div>
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

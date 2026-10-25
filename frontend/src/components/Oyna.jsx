import { useEffect, useRef } from 'react'
import NavIkona from './NavIkona'

// Forma oynasi (qo'shish, boshqarish): telefonda pastdan chiqadi, keng ekranda markazda. Escape va fon bosilsa yopiladi.
// Sahifa ichidagi yig'iladigan «details» formalar o'rniga — ro'yxat va asboblar paneli toza qoladi.
export default function Oyna({ sarlavha, onYop, children, keng = false }) {
  const ref = useRef(null)
  useEffect(() => {
    ref.current?.querySelector('input, select, textarea, button:not(.oyna-yop)')?.focus()
    const esc = (e) => { if (e.key === 'Escape') onYop() }
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onYop])
  return (
    <div className="oyna-parda" onClick={onYop}>
      <div className={`oyna${keng ? ' oyna-keng' : ''}`} role="dialog" aria-modal="true" aria-label={sarlavha} ref={ref} onClick={(e) => e.stopPropagation()}>
        <div className="oyna-bosh">
          <h3>{sarlavha}</h3>
          <button type="button" className="ikkinchi kichik oyna-yop" aria-label="Yopish" onClick={onYop}><NavIkona nom="yop" className="tugma-ikon" /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

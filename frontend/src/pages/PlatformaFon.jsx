// Platforma ichki sahifalarining orqa foni — "Kelinlar" bo'limidagi qasr rasmi va tepadan
// tushayotgan tilla harflar yomg'iri. Qatlam kontent ORTIDA qolishi uchun z-index: -1 bilan
// tushiriladi; kontentga z-index berilmaydi — ichidagi position:fixed modallar (vitrina,
// rasm-oyna, hujjat, manekin) o'z z-indexlari bilan ishlashda davom etadi.
import { useEffect, useRef } from 'react'
import { yomgirYarat } from './yomgir'
import './platforma-fon.css'

// bezak=false (ichki ish ekranlari): rasm va yomg'irsiz, faqat tun foni + tilla nur — matn kontrasti bir xil bo'ladi.
export default function PlatformaFon({ bezak = true }) {
  const yomgir = useRef(null)
  useEffect(() => (bezak ? yomgirYarat(yomgir.current) : undefined), [bezak])
  if (!bezak) return <div className="platforma-fon ichki" aria-hidden="true" />
  return (
    <div className="platforma-fon" aria-hidden="true">
      <img src="/kelinlar/saroy.jpg" alt="" />
      <i className="pf-aura" />
      <canvas ref={yomgir} />
    </div>
  )
}

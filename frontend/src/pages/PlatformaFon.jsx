// Platforma ichki sahifalarining orqa foni — "Kelinlar" bo'limidagi qasr rasmi va tepadan
// tushayotgan tilla harflar yomg'iri. Qatlam kontent ORTIDA qolishi uchun z-index: -1 bilan
// tushiriladi; kontentga z-index berilmaydi — ichidagi position:fixed modallar (vitrina,
// rasm-oyna, hujjat, manekin) o'z z-indexlari bilan ishlashda davom etadi.
import { useEffect, useRef } from 'react'
import { yomgirYarat } from './yomgir'
import './platforma-fon.css'

export default function PlatformaFon() {
  const yomgir = useRef(null)
  useEffect(() => yomgirYarat(yomgir.current), [])
  return (
    <div className="platforma-fon" aria-hidden="true">
      <img src="/kelinlar/saroy.jpg" alt="" />
      <i className="pf-aura" />
      <canvas ref={yomgir} />
    </div>
  )
}

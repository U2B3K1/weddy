import { useRef } from 'react'
import NavIkona from './NavIkona'

// Rasm qo'shish: «Galereyadan» (bir nechtasini birdan) va «Kamera bilan» (telefonda orqa kamera to'g'ridan-to'g'ri ochiladi).
// Faqat JPEG/PNG/WebP so'raladi — iPhone HEIC rasmini o'zi JPEG ga o'giradi. Kompyuterda kamera tugmasi yashirin
// (u yerda ham oddiy fayl oynasi ochilardi).
export default function RasmTanlash({ onTanla, band = false, matn = "Rasm qo'shish" }) {
  const galereya = useRef(null)
  const kamera = useRef(null)
  const tanlandi = (e) => {
    const fayllar = Array.from(e.target.files || [])
    e.target.value = ''  // shu rasmni qayta tanlasa ham ishlasin
    if (fayllar.length) onTanla(fayllar)
  }
  return (
    <div className="rasm-tanlash" role="group" aria-label={matn}>
      <input ref={galereya} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={tanlandi} />
      <input ref={kamera} type="file" accept="image/jpeg,image/png,image/webp" capture="environment" hidden onChange={tanlandi} />
      <button type="button" className="ikkinchi" disabled={band} onClick={() => galereya.current.click()}>
        <NavIkona nom="galereya" className="tugma-ikon" />{band ? 'Yuklanmoqda…' : 'Galereyadan'}
      </button>
      <button type="button" className="ikkinchi rasm-kamera" disabled={band} onClick={() => kamera.current.click()}>
        <NavIkona nom="kamera" className="tugma-ikon" />Kamera bilan
      </button>
    </div>
  )
}

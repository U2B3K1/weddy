import { useCallback, useEffect, useRef, useState } from 'react'
import Manekin from './Manekin'
import NavIkona from './NavIkona'
import RasmTanlash from './RasmTanlash'
import Tasdiq from './Tasdiq'
import { libosTafsilot, manekinSaqla, rasmFonsiz, rasmOchir, rasmYukla, sozlamalar, xatoMatni } from '../api'

// 7.3: libos rasmlari salonda standart sharoitda olinadi; tizim ularni o'zi 800×1200 va 300×450 WebP ga keltiradi.
export default function RasmBlok({ libosId, rahbar, onOzgardi }) {
  const [rasmlar, setRasmlar] = useState([])
  const [yuklanmoqda, setYuklanmoqda] = useState(false)
  const [xato, setXato] = useState('')
  const [kattaRasm, setKattaRasm] = useState(null)
  const [ochirSurov, setOchirSurov] = useState(null)
  // 4.5: raqamli manekin — fonsiz qatlam shu libosning bitta rasmidan tayyorlanadi
  const [libos, setLibos] = useState(null)
  const [manekinYoq, setManekinYoq] = useState(false)
  const [manekinOyna, setManekinOyna] = useState(false)
  const [tayyorlanmoqda, setTayyorlanmoqda] = useState(null)
  useEffect(() => { sozlamalar().then((s) => setManekinYoq(s.manekin !== false)).catch(() => {}) }, [])

  const yukla = useCallback(
    () => libosTafsilot(libosId).then((d) => { setRasmlar(d.rasmlar || []); setLibos(d) }),
    [libosId],
  )

  const manekinga = async (rasmId) => {
    setXato('')
    setTayyorlanmoqda(rasmId)
    try { await rasmFonsiz(rasmId); await yukla(); setManekinOyna(true) } catch (err) { setXato(xatoMatni(err)) }
    setTayyorlanmoqda(null)
  }
  useEffect(() => { yukla().catch((e) => setXato(xatoMatni(e))) }, [yukla])

  const tanlandi = async (fayllar) => {
    setXato('')
    setYuklanmoqda(true)
    const xatolar = []
    for (const f of fayllar) { // ketma-ket: tartib saqlanadi, server qayta ishlash yuki bir tekis
      try { await rasmYukla(libosId, f) } catch (err) { xatolar.push(`${f.name}: ${xatoMatni(err)}`) }
    }
    setYuklanmoqda(false)
    if (xatolar.length) setXato(xatolar.join(' '))
    await yukla()
    onOzgardi?.()
  }

  const ochir = async (id) => {
    setXato('')
    try { await rasmOchir(id); await yukla(); onOzgardi?.() } catch (err) { setXato(xatoMatni(err)) }
  }

  return (
    <div className="stack">
      <div className="rasm-tor">
        {rasmlar.map((r) => (
          <figure key={r.id} className="rasm-katak">
            {/* Klaviatura bilan ham ochiladi (B-27) */}
            <button type="button" className="r2-rasm-tugma" aria-label="Rasmni kattalashtirish" onClick={() => setKattaRasm(r.katta)}>
              <img src={r.kichik} alt="Libos rasmi" />
            </button>
            {rahbar && !r.standart && <figcaption className="belgi" title="Tik (2:3) rasm eng yaxshi ko'rinadi; bu rasm chetlaridan kesilishi mumkin">nisbati 2:3 emas</figcaption>}
            {/* «×» faqat ruxsat bo'lsa: rahbar yoki rasmni yuklagan xodim (B-28); o'chirish tasdiq bilan (B-07) */}
            {(r.ochira_oladi ?? rahbar) && <button type="button" className="rasm-ochir" aria-label="Rasmni o'chirish" onClick={() => setOchirSurov(r.id)}>×</button>}
            {manekinYoq && (
              <button type="button" className="ikkinchi kichik rasm-manekin" disabled={tayyorlanmoqda !== null} onClick={() => manekinga(r.id)}>
                {tayyorlanmoqda === r.id ? 'Tayyorlanmoqda…' : libos?.manekin?.rasm_id === r.id ? 'Manekin ✓' : 'Manekinga'}
              </button>
            )}
          </figure>
        ))}
        {rasmlar.length === 0 && <p className="malumot">Rasm yo'q</p>}
      </div>
      <RasmTanlash onTanla={tanlandi} band={yuklanmoqda} />
      <p className="malumot">
        Har bir libos uchun 3–5 ta rasm yuklang (old, yon, orqa, tafsilot). Tik (2:3) rasm eng yaxshi ko'rinadi.
        Telefon rasmini to'g'ridan-to'g'ri yuklash mumkin — tizim o'zi kichraytiradi.
      </p>
      {manekinYoq && libos?.manekin && (
        <button type="button" className="ikkinchi" onClick={() => setManekinOyna(true)}>Manekinda ko'rish va to'g'rilash</button>
      )}
      {manekinYoq && rasmlar.length > 0 && (
        <p className="malumot">«Manekinga» — tizim rasm fonini olib tashlab, libosni manekin ustiga qo'yadi. Old tomondan, bir xil rangli fonda olingan rasmni tanlang.</p>
      )}
      {xato && <p className="xato">{xato}</p>}
      {manekinOyna && libos?.manekin && (
        <Manekin sarlavha={libos.nomi} faylNomi={libos.artikul} onYopish={() => setManekinOyna(false)}
          qatlamlar={[{ kalit: 'libos', nomi: 'Libos', standart: { x: 0, y: 0.08, k: 0.8 }, ...libos.manekin, saqla: (b) => manekinSaqla(libos.id, b) }]}
          onSaqlandi={([q]) => setLibos({ ...libos, manekin: { ...libos.manekin, x: q.x, y: q.y, kattalik: q.kattalik } })} />
      )}
      {kattaRasm && <KattaRasm src={kattaRasm} onYop={() => setKattaRasm(null)} />}
      {ochirSurov && (
        <Tasdiq sarlavha="Rasm o'chirilsinmi?" tugma="Ha, o'chirish" matn="Rasm butunlay o'chadi — qaytarib bo'lmaydi."
          onYop={() => setOchirSurov(null)} onTasdiq={() => { const id = ochirSurov; setOchirSurov(null); ochir(id) }} />
      )}
    </div>
  )
}

// Katta rasm: Escape yoki «×» bilan yopiladi, fokus yopish tugmasida; yopilgach — bosilgan rasmga qaytadi (B-27)
function KattaRasm({ src, onYop }) {
  const yopRef = useRef(null)
  const onYopRef = useRef(onYop)
  useEffect(() => { onYopRef.current = onYop })
  useEffect(() => {
    const oldingi = document.activeElement
    yopRef.current?.focus()
    const esc = (e) => { if (e.key === 'Escape') { e.preventDefault(); onYopRef.current() } else if (e.key === 'Tab') { e.preventDefault(); yopRef.current?.focus() } }
    window.addEventListener('keydown', esc)
    return () => { window.removeEventListener('keydown', esc); if (oldingi && document.contains(oldingi)) oldingi.focus?.() }
  }, [])
  return (
    <div className="rasm-oyna" onClick={onYop} role="dialog" aria-modal="true" aria-label="Katta rasm">
      <img src={src} alt="Libos rasmi, katta" />
      <button type="button" className="ikkinchi r2-rasm-yop" ref={yopRef} aria-label="Yopish" onClick={onYop}><NavIkona nom="yop" className="tugma-ikon" /></button>
    </div>
  )
}

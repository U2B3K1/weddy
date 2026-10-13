import { useCallback, useEffect, useRef, useState } from 'react'
import Manekin from './Manekin'
import { libosTafsilot, manekinSaqla, rasmFonsiz, rasmOchir, rasmYukla, sozlamalar, xatoMatni } from '../api'

// 7.3: libos rasmlari salonda standart sharoitda olinadi; tizim ularni o'zi 800×1200 va 300×450 WebP ga keltiradi.
export default function RasmBlok({ libosId, rahbar, onOzgardi }) {
  const [rasmlar, setRasmlar] = useState([])
  const [yuklanmoqda, setYuklanmoqda] = useState(false)
  const [xato, setXato] = useState('')
  const [kattaRasm, setKattaRasm] = useState(null)
  const input = useRef(null)
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

  const tanlandi = async (e) => {
    const fayllar = Array.from(e.target.files || [])
    e.target.value = ''
    if (fayllar.length === 0) return
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
            <img src={r.kichik} alt="Libos rasmi" onClick={() => setKattaRasm(r.katta)} />
            {rahbar && !r.standart && <figcaption className="belgi">standart emas</figcaption>}
            <button type="button" className="rasm-ochir" aria-label="Rasmni o'chirish" onClick={() => ochir(r.id)}>×</button>
            {manekinYoq && (
              <button type="button" className="ikkinchi kichik rasm-manekin" disabled={tayyorlanmoqda !== null} onClick={() => manekinga(r.id)}>
                {tayyorlanmoqda === r.id ? 'Tayyorlanmoqda…' : libos?.manekin?.rasm_id === r.id ? 'Manekin ✓' : 'Manekinga'}
              </button>
            )}
          </figure>
        ))}
        {rasmlar.length === 0 && <p className="malumot">Rasm yo'q</p>}
      </div>
      <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={tanlandi} />
      <button type="button" className="ikkinchi" disabled={yuklanmoqda} onClick={() => input.current.click()}>
        {yuklanmoqda ? 'Yuklanmoqda…' : "Rasm qo'shish"}
      </button>
      <p className="malumot">
        Bitta manekin, bitta fon va yorug'lik; har bir libos 3–5 rakursda (old, yon, orqa, tafsilot). Rasm tik (2:3) bo'lsin.
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
      {kattaRasm && (
        <div className="rasm-oyna" onClick={() => setKattaRasm(null)} role="presentation">
          <img src={kattaRasm} alt="Katta rasm" />
        </div>
      )}
    </div>
  )
}

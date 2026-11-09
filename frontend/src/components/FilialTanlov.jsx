import { useEffect, useState } from 'react'
import { filiallar, joriyFilial, xatoMatni } from '../api'
import NavIkona from './NavIkona'

// Yuqori paneldagi «Filial: …» (salon nomi o'rnida, foydalanuvchi so'rovi): shu qurilma ishlayotgan filial.
// Rahbar shu yerning o'zida almashtiradi — Sozlama → Qurilmalar'dagi biriktirish bilan bir xil (kassa, yangi zakaz va libos
// filiali shunga bog'liq). Boshqa xodimga — faqat ko'rsatiladi. Salonda filial bo'lmasa — umuman chiqmaydi.
// `ochiq`/`onOch` — UstkiPanel'ning umumiy menyu holati (tashqariga bosish va Escape bilan yopiladi).
export default function FilialTanlov({ rahbar, ochiq, onOch, onOzgardi }) {
  const [d, setD] = useState(null) // { filiallar, joriy }
  const [band, setBand] = useState(false)
  const [xato, setXato] = useState('')
  useEffect(() => { filiallar().then(setD).catch(() => {}) }, [])
  if (!d || d.filiallar.length === 0) return null
  const joriy = d.filiallar.find((f) => f.id === d.joriy)
  const yorliq = joriy ? `Filial: ${joriy.nomi}` : 'Filial tanlanmagan'

  if (!rahbar) {
    return <span className="ustki-pill filial-pill" title="Shu qurilma ishlayotgan filial"><NavIkona nom="joy" />{yorliq}</span>
  }
  const tanla = async (id) => {
    if (id === d.joriy) { onOch(false); return }
    setBand(true); setXato('')
    try {
      const r = await joriyFilial(id)
      setD((x) => ({ ...x, joriy: r.joriy }))
      onOch(false)
      onOzgardi?.()
    } catch (e) { setXato(xatoMatni(e)) } finally { setBand(false) }
  }
  const variantlar = [...d.filiallar.map((f) => [f.id, f.nomi, f.manzil]), [null, 'Filialsiz', 'umumiy kassa']]
  return (
    <div className="ustki-joy filial-joy">
      <button type="button" className="ustki-pill filial-pill" aria-haspopup="menu" aria-expanded={ochiq} onClick={() => onOch(!ochiq)}
        title="Shu qurilma ishlayotgan filial — almashtirish">
        <NavIkona nom="joy" />{yorliq}<NavIkona nom="ong" className="filial-belgi" />
      </button>
      {ochiq && (
        <div className="ustki-menyu filial-menyu" role="menu" aria-label="Filialni almashtirish">
          <b>Shu qurilma filiali</b>
          {variantlar.map(([id, n, izoh]) => (
            <button key={id ?? 'yoq'} type="button" role="menuitemradio" aria-checked={id === d.joriy} disabled={band} onClick={() => tanla(id)}>
              <span><b>{n}</b>{izoh && <small>{izoh}</small>}</span>
              {id === d.joriy && <NavIkona nom="bajarildi" className="tugma-ikon" />}
            </button>
          ))}
          <p className="malumot">Kassa, yangi zakaz va libos filiali shu tanlovga bog'liq.</p>
          {xato && <p className="xato" role="alert">{xato}</p>}
        </div>
      )}
    </div>
  )
}

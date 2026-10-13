import { useEffect, useState } from 'react'
import TelegramBlok from '../components/TelegramBlok'
import { boglandim, boshEkran, som, xatoMatni } from '../api'

// FT-1.2: bugun olib ketiladigan va qaytariladigan liboslar, kechikkanlar, smena holati.
export default function BoshEkran({ onZakaz, onYangi, onKassa, rahbar }) {
  const [d, setD] = useState(null)
  const [xato, setXato] = useState('')

  const yukla = () => boshEkran().then(setD).catch((e) => setXato(xatoMatni(e)))
  useEffect(() => { yukla() }, [])

  if (xato) return <p className="xato">{xato}</p>
  if (!d) return <p className="malumot">Yuklanmoqda…</p>

  return (
    <div className="stack">
      <button onClick={onYangi}>Yangi zakaz</button>
      {!d.smena.ochiq && (
        <div className="ogohlantirish">
          Smena ochiq emas — to'lov qabul qilib bo'lmaydi.{' '}
          <button className="ikkinchi kichik" onClick={onKassa}>Kassaga o'tish</button>
        </div>
      )}
      {d.eslatmalar.length > 0 && (
        <section className="blok">
          <h3>Eslatmalar ({d.eslatmalar.filter((e) => !e.boglangan).length})</h3>
          {d.eslatmalar.map((e) => (
            <Eslatma key={`${e.tur}-${e.zakaz_id}`} e={e} onZakaz={onZakaz} onBajarildi={yukla} />
          ))}
        </section>
      )}
      <Blok sarlavha="Kechikkan qaytarishlar" royxat={d.kechikkan} onZakaz={onZakaz} ogohlantirish />
      <Blok sarlavha="Bugun olib ketiladi" royxat={d.olib_ketiladi} onZakaz={onZakaz} />
      <Blok sarlavha="Bugun qaytariladi" royxat={d.qaytariladi} onZakaz={onZakaz} />
      <TelegramBlok rahbar={rahbar} />
    </div>
  )
}

function Blok({ sarlavha, royxat, onZakaz, ogohlantirish }) {
  if (royxat.length === 0 && ogohlantirish) return null
  return (
    <section className="blok">
      <h3>{sarlavha} ({royxat.length})</h3>
      {royxat.length === 0 && <p className="malumot">Yo'q</p>}
      {royxat.map((z) => (
        <button key={z.id} className={`qator-btn ${ogohlantirish ? 'qizil' : ''}`} onClick={() => onZakaz(z.id)}>
          <b>#{z.raqam}</b> {z.mijoz} · {z.liboslar.join(', ')}
          <span>{som(z.jami)}</span>
        </button>
      ))}
    </section>
  )
}

// 4.14: eslatma sotuvchiga chiqadi; u mijoz bilan o'zi bog'lanadi va natijani yozadi (FT-14.2).
function Eslatma({ e, onZakaz, onBajarildi }) {
  const [izoh, setIzoh] = useState('')
  const [ochiq, setOchiq] = useState(false)
  return (
    <div className={`tasdiq ${e.boglangan ? 'bajarilgan' : ''}`}>
      <span>
        <button className="havola" onClick={() => onZakaz(e.zakaz_id)}>#{e.raqam}</button> {e.mijoz || 'Mijoz'} ·{' '}
        <a href={`tel:${e.telefon}`}>{e.telefon}</a><br />{e.matn}
      </span>
      {e.boglangan ? <span className="malumot">✓ Bog'lanildi</span> : ochiq ? (
        <div className="qator">
          <input placeholder="Natija (ixtiyoriy)" value={izoh} onChange={(ev) => setIzoh(ev.target.value)} />
          <button onClick={() => boglandim(e.zakaz_id, e.tur, izoh).then(onBajarildi)}>Saqlash</button>
        </div>
      ) : <button className="ikkinchi kichik" onClick={() => setOchiq(true)}>Bog'landim</button>}
    </div>
  )
}

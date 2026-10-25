import { useEffect, useMemo, useState } from 'react'
import { kalendar, xatoMatni } from '../api'

const KUNLAR = { kun: 1, hafta: 7, oy: 31 }
const HAFTA = ['Ya', 'Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh']

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const qosh = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x }

// FT-2.6: bandlik kalendari — kun, hafta, oy ko'rinishi; libos bo'yicha bandlik.
export default function Kalendar({ onZakaz }) {
  const [korinish, setKorinish] = useState('hafta')
  const [bosh, setBosh] = useState(() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d })
  const [qatorlar, setQatorlar] = useState([])
  const [xato, setXato] = useState('')
  const [bugun] = useState(() => iso(new Date()))

  const kunlar = useMemo(
    () => Array.from({ length: KUNLAR[korinish] }, (_, i) => qosh(bosh, i)),
    [bosh, korinish],
  )
  const dan = iso(kunlar[0])
  // Sana klaviaturadan terilganda yil oraliq qiymatlardan o'tadi (0002, 0020…): maydon matni alohida saqlanadi,
  // kalendar esa faqat to'liq sana kiritilgach siljiydi.
  const [sanaMatn, setSanaMatn] = useState(dan)
  const siljit = (d) => { setBosh(d); setSanaMatn(iso(d)) }
  const sanaTer = (v) => {
    setSanaMatn(v)
    if (v >= '2000-01-01' && v <= '2100-12-31') setBosh(new Date(`${v}T00:00:00`))
  }
  const gacha = iso(kunlar[kunlar.length - 1])

  useEffect(() => {
    let bekor = false
    const yukla = () => kalendar(dan, gacha)
      .then((d) => { if (!bekor) { setQatorlar(d); setXato('') } })
      .catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    yukla()
    const t = setInterval(yukla, 5000) // FT-1.4: bandlik o'zgarishi 5 soniyadan kam vaqtda ko'rinadi
    return () => { bekor = true; clearInterval(t) }
  }, [dan, gacha])

  const holat = (l, kun) => {
    const k = iso(kun)
    for (const b of l.bronlar) {
      if (k >= b.dan && k <= b.gacha) return { turi: b.turi === 'mustahkam' ? 'band' : 'vaqtinchalik', b }
      if (k > b.gacha && k <= b.band_gacha) return { turi: 'bufer', b }
    }
    return null
  }

  return (
    <div className="stack kalendar-sahifa">
      {/* Ko'rinish va sana — bitta ixcham qatorda (sahifa tepasida zakazlar segmenti allaqachon bor) */}
      <div className="kalendar-asboblar">
        <div className="segment kalendar-korinish" role="group" aria-label="Ko'rinish">
          {Object.keys(KUNLAR).map((k) => (
            <button key={k} className={korinish === k ? '' : 'ikkinchi'} aria-pressed={korinish === k} onClick={() => setKorinish(k)}>
              {k === 'kun' ? 'Kun' : k === 'hafta' ? 'Hafta' : 'Oy'}
            </button>
          ))}
        </div>
        <div className="qator kalendar-nav">
          <button className="ikkinchi kichik" aria-label="Oldingi davr" onClick={() => siljit(qosh(bosh, -KUNLAR[korinish]))}>‹</button>
          <input type="date" aria-label="Boshlanish sanasi" value={sanaMatn} min="2000-01-01" max="2100-12-31" onChange={(e) => sanaTer(e.target.value)} />
          <button className="ikkinchi kichik" aria-label="Keyingi davr" onClick={() => siljit(qosh(bosh, KUNLAR[korinish]))}>›</button>
          <button className="ikkinchi kichik" onClick={() => siljit((() => { const d = new Date(); d.setHours(0, 0, 0, 0); return d })())}>Bugun</button>
        </div>
      </div>
      {xato && <p className="xato">{xato}</p>}
      <div className="kalendar-ora">
        <table className="kalendar">
          <thead>
            <tr>
              <th className="kalendar-libos">Libos</th>
              {kunlar.map((k) => (
                <th key={iso(k)} className={iso(k) === bugun ? 'bugun' : ''}>
                  {k.getDate()}<small>{HAFTA[k.getDay()]}</small>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {qatorlar.map((l) => (
              <tr key={l.id}>
                <th className="kalendar-libos">
                  {l.artikul} <small>{l.nomi}{l.holat !== 'bosh' ? ` · ${l.holat === 'tamirda' ? "ta'mirda" : 'tozalashda'}` : ''}</small>
                </th>
                {kunlar.map((k) => {
                  const h = holat(l, k)
                  const p = (l.primerkalar || []).find((x) => x.sana === iso(k))  // FT-2.8
                  return (
                    <td key={iso(k)} className={`${h ? `k-${h.turi}` : ''} ${p ? 'k-primerka' : ''}`}
                      title={[h ? `#${h.b.zakaz_raqami ?? ''} ${h.b.mijoz ?? ''}${h.turi === 'bufer' ? ' · tozalash' : ''}` : "Bo'sh",
                        p ? `Primerka ${p.vaqt}: #${p.zakaz_raqami} ${p.mijoz}` : ''].filter(Boolean).join(' · ')}
                      onClick={() => { const id = h?.b.zakaz_id || p?.zakaz_id; if (id) onZakaz(id) }}>
                      {h && h.turi !== 'bufer' && korinish !== 'oy' ? `#${h.b.zakaz_raqami}` : ''}
                      {p && <span className="primerka-belgi">P{korinish !== 'oy' ? ` ${p.vaqt}` : ''}</span>}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="malumot kalendar-izoh">
        <span className="k-band" /> bron (avans olingan) <span className="k-vaqtinchalik" /> vaqtinchalik bron
        <span className="k-bufer" /> tozalash (bufer kun)
        <span className="primerka-belgi">P</span> primerka
      </p>
    </div>
  )
}

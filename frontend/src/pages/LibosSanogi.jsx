import { useCallback, useEffect, useRef, useState } from 'react'
import { filiallar, sanaMatni, sanoq, sanoqBelgila, sanoqBoshla, sanoqYakunla, xatoMatni } from '../api'

const JOY = { mijozda: 'tizimda: mijozda', tamirda: "ta'mirda", tozalashda: 'tozalashda' }
// Qator libos yoki aksessuar donasi (FT-01) bo'ladi — kalit va belgilash shunga qarab
const qatorKaliti = (q) => `${q.tur}-${q.libos ?? q.dona}`
const qatorId = (q) => (q.libos ? { libos: q.libos } : { dona: q.dona })
const joySinfi = (j) => ({ mijozda: 'qarz', tamirda: 'vaqtinchalik', tozalashda: 'vaqtinchalik' }[j] || 'bron')

// Libos sanog'i: javondagi liboslar artikul (skaner) yoki ro'yxatdan belgilanadi; yakunda «salonda bo'lishi
// kerak edi, lekin yo'q» liboslar chiqadi — zakazsiz ijarani yoki yo'qolgan libosni ushlaydi. Natija rahbarga Telegramda.
export default function LibosSanogi() {
  const [d, setD] = useState(null)
  const [fil, setFil] = useState([])
  const [filial, setFilial] = useState('')
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [natija, setNatija] = useState(null)

  const yukla = useCallback(() => sanoq().then(setD).catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })), [])
  useEffect(() => { yukla(); filiallar().then((r) => setFil(r.filiallar)).catch(() => {}) }, [yukla])

  const boshla = async () => {
    setXabar({ turi: '', matn: '' }); setNatija(null)
    try { const s = await sanoqBoshla(filial ? { filial: Number(filial) } : {}); setD((x) => ({ ...x, ochiq: s })) } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) })
    }
  }

  if (!d) return <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn || 'Yuklanmoqda…'}</p>
  if (d.ochiq) {
    return <OchiqSanoq s={d.ochiq} onYangila={(s) => setD({ ...d, ochiq: s })}
      onYakun={(s) => { setNatija(s); yukla() }} />
  }
  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {natija && <Natija s={natija} />}
      <section className="blok">
        <h3>Libos sanog'i</h3>
        <p className="malumot">Javondagi har bir libos va aksessuar donasini (fata, toj — yorlig'i bilan) belgilang. Tizim «salonda bo'lishi kerak edi, lekin yo'q» liboslarni
          ko'rsatadi — zakazsiz berilgan yoki yo'qolgan libos shunday topiladi. Natija rahbarga Telegramda boradi.</p>
        <div className="qator">
          {fil.length > 0 && (
            <select className="kichik-tanlov" value={filial} aria-label="Filial" onChange={(e) => setFilial(e.target.value)}>
              <option value="">Barcha liboslar</option>
              {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
            </select>
          )}
          <button onClick={boshla}>Sanoqni boshlash</button>
        </div>
      </section>
      {d.tarix.length > 0 && (
        <section className="blok jadval-panel">
          <div className="jadval-asboblar"><h3 className="panel-nom">Oldingi sanoqlar</h3></div>
          {d.tarix.map((s) => (
            <div key={s.id} className="tasdiq-qator">
              <div className="tasdiq-matn">
                <b>{sanaMatni(s.yakunlangan)}{s.filial ? ` · ${s.filial}` : ''} · {s.yakunlagan}</b>
                <small>salonda bo'lishi kerak {s.kutilgan}, joyida {s.topilgan}
                  {s.yoq > 0 && <b className="qizil"> · {s.yoq} ta yo'q</b>}
                  {s.ortiqcha > 0 && <span className="qizil"> · {s.ortiqcha} ta qaytgani kiritilmagan</span>}
                  {s.izoh && ` · ${s.izoh}`}</small>
              </div>
            </div>
          ))}
        </section>
      )}
    </div>
  )
}

function OchiqSanoq({ s, onYangila, onYakun }) {
  const [artikul, setArtikul] = useState('')
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [hammasi, setHammasi] = useState(false)
  const [izoh, setIzoh] = useState('')
  const [band, setBand] = useState(false)
  const kiritish = useRef(null)

  const qatorniYangila = (r) => onYangila({ ...s, qatorlar: s.qatorlar.map((q) => (qatorKaliti(q) === qatorKaliti(r) ? { ...q, topildi: r.topildi } : q)) })
  const belgila = async (body) => {
    setXabar({ turi: '', matn: '' })
    try {
      const r = await sanoqBelgila(body)
      qatorniYangila(r)
      if (body.artikul) setXabar({ turi: 'ok', matn: `✓ ${r.artikul} ${r.nomi}${r.joy === 'mijozda' ? ' — tizimda mijozda turibdi!' : ''}` })
      return true
    } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false }
  }
  const skaner = async (e) => {
    e.preventDefault()
    if (!artikul.trim()) return
    if (await belgila({ artikul })) setArtikul('')
    kiritish.current?.focus()
  }
  const yakunla = async () => {
    setBand(true)
    try { onYakun(await sanoqYakunla({ izoh })) } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) } finally { setBand(false) }
  }

  const salonda = s.qatorlar.filter((q) => q.joy === 'salonda')
  const topildi = salonda.filter((q) => q.topildi).length
  const korinadi = hammasi ? s.qatorlar : s.qatorlar.filter((q) => !q.topildi)
  return (
    <div className="stack">
      <div className="stat-qator">
        <div className="stat"><span>Salonda bo'lishi kerak</span><b>{salonda.length}</b></div>
        <div className="stat"><span>Topildi</span><b>{topildi}</b></div>
        <div className="stat"><span>Hali topilmagan</span><b>{salonda.length - topildi}</b></div>
        <div className="stat"><span>Mijozda / ta'mirda / tozalashda</span><b>{s.qatorlar.length - salonda.length}</b></div>
      </div>
      <section className="blok">
        <form className="sanoq-kiritish" onSubmit={skaner}>
          <input ref={kiritish} autoFocus value={artikul} onChange={(e) => setArtikul(e.target.value)}
            placeholder="Artikul yoki yorliq (FT-01) — kiriting yoki skanerlang" aria-label="Artikul" maxLength={50} />
          <button type="submit">Topildi</button>
        </form>
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        <small className="malumot">Boshladi: {s.boshlagan}{s.filial ? ` · ${s.filial}` : ''}. Sanoqni bir necha kishi birga davom ettirishi mumkin.</small>
      </section>
      <section className="blok jadval-panel">
        <div className="jadval-asboblar">
          <h3 className="panel-nom">{hammasi ? 'Barcha liboslar' : 'Hali topilmaganlar'}</h3>
          <label className="malumot"><input type="checkbox" checked={hammasi} onChange={(e) => setHammasi(e.target.checked)} /> topilganlarni ham ko'rsatish</label>
        </div>
        {korinadi.length === 0 && <p className="malumot jadval-bosh">Hammasi belgilandi.</p>}
        {korinadi.map((q) => (
          <div key={qatorKaliti(q)} className={`tasdiq-qator${q.topildi ? ' bajarilgan' : ''}`}>
            <div className="tasdiq-matn">
              <b>{q.artikul} · {q.nomi}</b>
              <small>{q.kategoriya}{q.olcham && ` · ${q.olcham}`}
                {JOY[q.joy] && <> · <span className={`holat ${joySinfi(q.joy)}`}>{JOY[q.joy]}</span></>}
                {q.topildi && q.xodim && ` · belgiladi: ${q.xodim}`}</small>
            </div>
            <div className="tasdiq-tugmalar">
              {q.topildi
                ? <button className="ikkinchi kichik" onClick={() => belgila({ ...qatorId(q), topildi: false })}>Bekor</button>
                : <button className="kichik" onClick={() => belgila({ ...qatorId(q), topildi: true })}>Topildi</button>}
            </div>
          </div>
        ))}
      </section>
      <section className="blok">
        <h3>Sanoqni yakunlash</h3>
        {salonda.length - topildi > 0 && <p className="ogohlantirish">{salonda.length - topildi} ta libos hali topilmagan — yakunlasangiz «yo'q» deb rahbarga yuboriladi.</p>}
        <div className="qator">
          <input value={izoh} onChange={(e) => setIzoh(e.target.value)} placeholder="Izoh (ixtiyoriy)" aria-label="Izoh" maxLength={300} />
          <button onClick={yakunla} disabled={band}>Yakunlash</button>
        </div>
      </section>
    </div>
  )
}

function Natija({ s }) {
  const yoq = s.qatorlar.filter((q) => q.joy === 'salonda' && !q.topildi)
  const ortiqcha = s.qatorlar.filter((q) => q.joy === 'mijozda' && q.topildi)
  return (
    <section className="blok">
      <h3>Sanoq yakunlandi</h3>
      <p>Salonda bo'lishi kerak: <b>{s.kutilgan}</b>, joyida: <b>{s.topilgan}</b>.{!yoq.length && !ortiqcha.length && ' Hammasi joyida.'}</p>
      {yoq.length > 0 && <p className="ogohlantirish">Yo'q ({yoq.length}): {yoq.map((q) => `${q.artikul} ${q.nomi}`).join(', ')}</p>}
      {ortiqcha.length > 0 && <p className="ogohlantirish">Tizimda mijozda, lekin javonda ({ortiqcha.length}): {ortiqcha.map((q) => q.artikul).join(', ')} — qaytarilgani kiritilmagan.</p>}
      <small className="malumot">Natija rahbarga Telegramda yuborildi.</small>
    </section>
  )
}

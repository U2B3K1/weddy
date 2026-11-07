import { useCallback, useEffect, useRef, useState } from 'react'
import Tasdiq from '../components/Tasdiq'
import { filiallar, sanaMatni, sanoq, sanoqBekor, sanoqBelgila, sanoqBoshla, sanoqYakunla, xatoMatni } from '../api'

const JOY = { mijozda: 'tizimda: mijozda', tamirda: "ta'mirda", tozalashda: 'tozalashda' }
// Qator libos yoki aksessuar donasi (FT-01) bo'ladi — kalit va belgilash shunga qarab
const qatorKaliti = (q) => `${q.tur}-${q.libos ?? q.dona}`
const qatorId = (q) => (q.libos ? { libos: q.libos } : { dona: q.dona })
// Server vaqti mahalliy vaqt bilan keladi: «07.11.2026 02:10»
const vaqtMatni = (s) => (s ? `${sanaMatni(s)} ${String(s).slice(11, 16)}` : '')
const joySinfi = (j) => ({ mijozda: 'qarz', tamirda: 'vaqtinchalik', tozalashda: 'vaqtinchalik' }[j] || 'bron')

// Terilgan qismga mos buyumlar: artikul boshidan mos kelgani oldin, keyin ichida uchragani, keyin nomi bo'yicha;
// hali topilmaganlari oldinda. Raqamning bir qismini terib, ro'yxatdan bosish — to'liq artikulni yozishdan tez.
function takliflar(qatorlar, matn, soni = 6) {
  const t = matn.trim().toLowerCase()
  if (!t) return []
  const daraja = (q) => {
    const a = q.artikul.toLowerCase()
    if (a.startsWith(t)) return 0
    if (a.includes(t)) return 1
    return (q.nomi || '').toLowerCase().includes(t) ? 2 : -1
  }
  return qatorlar.map((q) => [daraja(q), q]).filter(([d]) => d >= 0)
    .sort(([d1, a], [d2, b]) => (a.topildi - b.topildi) || (d1 - d2) || a.artikul.localeCompare(b.artikul, undefined, { numeric: true }))
    .slice(0, soni).map(([, q]) => q)
}

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
      onYakun={(s) => { setNatija(s); yukla() }}
      onBekor={() => { setXabar({ turi: 'ok', matn: "Sanoq bekor qilindi — hech kimga xabar yuborilmadi." }); yukla() }} />
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
              <option value="">Barcha filiallar</option>
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
                <b>{vaqtMatni(s.yakunlangan)}{s.filial ? ` · ${s.filial}` : ''} · {s.yakunlagan}</b>
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

function OchiqSanoq({ s, onYangila, onYakun, onBekor }) {
  const [artikul, setArtikul] = useState('')
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [hammasi, setHammasi] = useState(false)
  const [izoh, setIzoh] = useState('')
  const [band, setBand] = useState(false)
  const [surov, setSurov] = useState(null)  // 'yakun' | 'bekor' — tasdiq oynasi
  const [aktiv, setAktiv] = useState(-1)  // klaviatura (↑/↓) bilan tanlangan taklif; -1 — Enter terilganini yuboradi (skaner)
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
  const taklif = takliflar(s.qatorlar, artikul)
  const tanla = async (q) => {
    if (q.topildi) {
      setXabar({ turi: 'ok', matn: `${q.artikul} ${q.nomi} allaqachon belgilangan.` })
    } else if (await belgila({ ...qatorId(q), topildi: true })) {
      setXabar({ turi: 'ok', matn: `✓ ${q.artikul} ${q.nomi}${q.joy === 'mijozda' ? ' — tizimda mijozda turibdi!' : ''}` })
    }
    setArtikul(''); setAktiv(-1)
    kiritish.current?.focus()
  }
  const skaner = async (e) => {
    e.preventDefault()
    if (aktiv >= 0 && taklif[aktiv]) return tanla(taklif[aktiv])
    if (!artikul.trim()) return
    if (await belgila({ artikul })) setArtikul('')
    kiritish.current?.focus()
  }
  const strelka = (e) => {
    if (!taklif.length) return
    if (e.key === 'ArrowDown') { e.preventDefault(); setAktiv((a) => (a + 1) % taklif.length) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setAktiv((a) => (a <= 0 ? taklif.length - 1 : a - 1)) }
    else if (e.key === 'Escape') { setArtikul(''); setAktiv(-1) }
  }
  const yakunla = async () => {
    setSurov(null); setBand(true)
    try { onYakun(await sanoqYakunla({ izoh })) } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) } finally { setBand(false) }
  }
  // Tasodifan boshlangan sanoq: Telegramga «N ta yo'q» degan yolg'on signal ketmasin (B-24)
  const bekorQil = async () => {
    setSurov(null); setBand(true)
    try { await sanoqBekor(); onBekor() } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }) } finally { setBand(false) }
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
          <div className="sanoq-maydon">
            <input ref={kiritish} autoFocus value={artikul} onChange={(e) => { setArtikul(e.target.value); setAktiv(-1) }} onKeyDown={strelka}
              placeholder="Raqamini tering yoki skanerlang, masalan: L-0012" aria-label="Artikul" maxLength={50} autoComplete="off"
              role="combobox" aria-expanded={taklif.length > 0} aria-controls="sanoq-takliflar" aria-autocomplete="list"
              aria-activedescendant={aktiv >= 0 ? `taklif-${aktiv}` : undefined} />
            {taklif.length > 0 && (
              <ul id="sanoq-takliflar" className="sanoq-takliflar" role="listbox" aria-label="Mos buyumlar">
                {taklif.map((q, i) => (
                  <li key={qatorKaliti(q)} id={`taklif-${i}`} role="option" aria-selected={i === aktiv}
                    className={`${i === aktiv ? 'aktiv' : ''} ${q.topildi ? 'topilgan' : ''}`}
                    onMouseDown={(e) => e.preventDefault()} onClick={() => tanla(q)}>
                    <b>{q.artikul}</b>
                    <span>{q.nomi}{q.olcham && ` · ${q.olcham}`}</span>
                    <small>{q.topildi ? '✓ belgilangan' : JOY[q.joy] || 'salonda'}</small>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button type="submit">Topildi</button>
        </form>
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        <small className="malumot">Boshladi: {s.boshlagan}{s.filial ? ` · ${s.filial}` : ''}. Sanoqni bir necha kishi birga davom ettirishi mumkin.</small>
      </section>
      <section className="blok jadval-panel">
        <div className="jadval-asboblar">
          <h3 className="panel-nom">{hammasi ? 'Hammasi' : 'Hali topilmaganlar'}</h3>
          <label className="qator malumot"><input type="checkbox" checked={hammasi} onChange={(e) => setHammasi(e.target.checked)} /> topilganlarni ham ko'rsatish</label>
        </div>
        {korinadi.length === 0 && <p className="malumot jadval-bosh">Hammasi belgilandi.</p>}
        {/* Avval salonda turishi kerak bo'lganlar; keyin alohida — ta'mirda, tozalashda, mijozda (topilmasa ham xato emas) */}
        {[korinadi.filter((q) => q.joy === 'salonda'), korinadi.filter((q) => q.joy !== 'salonda')].map((guruh, gi) => guruh.length > 0 && (
          <div key={gi} className="sanoq-guruh">
            <h4 className="sanoq-guruh-nom">{gi === 0
              ? <>Salonda bo'lishi kerak <span className="tab-son">{guruh.length}</span></>
              : <>Ta'mirda, tozalashda, mijozda <span className="tab-son">{guruh.length}</span><small>javonda bo'lsa belgilang — bo'lmasa ham xato emas</small></>}</h4>
            {guruh.map((q) => (
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
                : <button className="ikkinchi kichik" onClick={() => belgila({ ...qatorId(q), topildi: true })}>Topildi</button>}
            </div>
          </div>
            ))}
          </div>
        ))}
      </section>
      <section className="blok stack">
        <h3>Sanoqni yakunlash</h3>
        {salonda.length - topildi > 0 && <p className="ogohlantirish">{salonda.length - topildi} ta buyum hali topilmagan — yakunlasangiz «yo'q» deb rahbarga yuboriladi.</p>}
        <label>Izoh (ixtiyoriy)
          <input value={izoh} onChange={(e) => setIzoh(e.target.value)} placeholder="masalan: A-2 kimyoviy tozalashda" maxLength={300} />
        </label>
        <div className="qator r2-sanoq-tugmalar">
          <button onClick={() => setSurov('yakun')} disabled={band}>Yakunlash</button>
          <button className="ikkinchi" onClick={() => setSurov('bekor')} disabled={band}>Sanoqni bekor qilish</button>
        </div>
        <p className="malumot">Tasodifan boshlangan bo'lsa — bekor qiling: natija saqlanmaydi va hech kimga yuborilmaydi.</p>
      </section>
      {surov === 'yakun' && (
        <Tasdiq sarlavha="Sanoq yakunlansinmi?" tugma="Ha, yakunlash" xavfli={false}
          matn={salonda.length - topildi > 0
            ? `${salonda.length - topildi} ta buyum topilmagan — rahbarga Telegramda «yo'q» deb yuboriladi. Yakunlangan sanoqqa qayta belgilab bo'lmaydi.`
            : "Hammasi topildi. Natija rahbarga Telegramda yuboriladi."}
          onYop={() => setSurov(null)} onTasdiq={yakunla} />
      )}
      {surov === 'bekor' && (
        <Tasdiq sarlavha="Sanoq bekor qilinsinmi?" tugma="Ha, bekor qilish"
          matn={`Belgilangan ${s.qatorlar.filter((q) => q.topildi).length} ta buyum o'chadi, natija hech kimga yuborilmaydi. Qaytarib bo'lmaydi.`}
          onYop={() => setSurov(null)} onTasdiq={bekorQil} />
      )}
    </div>
  )
}

function Natija({ s }) {
  const yoq = s.qatorlar.filter((q) => q.joy === 'salonda' && !q.topildi)
  const ortiqcha = s.qatorlar.filter((q) => q.joy === 'mijozda' && q.topildi)
  return (
    <section className="blok stack">
      <h3>Sanoq yakunlandi</h3>
      <p>Salonda bo'lishi kerak: <b>{s.kutilgan}</b>, joyida: <b>{s.topilgan}</b>.{!yoq.length && !ortiqcha.length && ' Hammasi joyida.'}</p>
      {yoq.length > 0 && <NatijaJadval sarlavha={`Yo'q (${yoq.length})`} izoh="salonda bo'lishi kerak edi, lekin topilmadi" qatorlar={yoq} />}
      {ortiqcha.length > 0 && <NatijaJadval sarlavha={`Tizimda mijozda, lekin javonda (${ortiqcha.length})`} izoh="qaytarilgani tizimga kiritilmagan" qatorlar={ortiqcha} />}
      <small className="malumot">Natija rahbarga Telegramda yuborildi.</small>
    </section>
  )
}

// Sanoq natijasidagi ro'yxat — kichik jadval (bitta qizil paragraf o'rniga, B-24)
function NatijaJadval({ sarlavha, izoh, qatorlar }) {
  return (
    <div className="r2-sanoq-natija">
      <p className="qizil"><b>{sarlavha}</b> <span className="malumot">— {izoh}</span></p>
      <div className="jadval-ora">
        <table className="hisobot">
          <thead><tr><th>Artikul</th><th>Nomi</th><th>Kategoriya</th><th>O'lcham</th></tr></thead>
          <tbody>
            {qatorlar.map((q) => (
              <tr key={qatorKaliti(q)}><td><b>{q.artikul}</b></td><td>{q.nomi}</td><td>{q.kategoriya}</td><td>{q.olcham || '—'}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

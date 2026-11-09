import { useCallback, useEffect, useRef, useState } from 'react'
import Tasdiq from '../components/Tasdiq'
import KpiFiltr from '../components/KpiFiltr'
import NavIkona from '../components/NavIkona'
import { Belgi } from '../components/ZakazQatorlari'
import { OYLAR, bugunIso } from '../components/kalendar/sana'
import { filiallar, sanoq, sanoqBekor, sanoqBelgila, sanoqBoshla, sanoqYakunla, xatoMatni } from '../api'

const JOY = { mijozda: 'tizimda: mijozda', tamirda: "ta'mirda", tozalashda: 'tozalashda' }
// Qator libos yoki aksessuar donasi (FT-01) bo'ladi — kalit va belgilash shunga qarab
const qatorKaliti = (q) => `${q.tur}-${q.libos ?? q.dona}`
const qatorId = (q) => (q.libos ? { libos: q.libos } : { dona: q.dona })

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

// Libos sanog'i (kanvas LibosSanoqShisha): javondagi liboslar artikul (skaner) yoki ro'yxatdan belgilanadi; yakunda «salonda bo'lishi
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
    return <OchiqSanoq s={d.ochiq} tarix={d.tarix} onYangila={(s) => setD({ ...d, ochiq: s })}
      onYakun={(s) => { setNatija(s); yukla() }}
      onBekor={() => { setXabar({ turi: 'ok', matn: "Sanoq bekor qilindi — hech kimga xabar yuborilmadi." }); yukla() }} />
  }
  return (
    <div className="stack sanoq-sahifa">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {natija && <Natija s={natija} />}
      <section className="sanoq-holat">
        <span className="sanoq-nuqta yopiq" aria-hidden="true" />
        <div className="sanoq-holat-matn">
          <b>Sanoq ochiq emas</b>
          <small>Javondagi har bir libos va aksessuar donasini (fata, toj — yorlig'i bilan) belgilang: «salonda bo'lishi kerak edi, lekin yo'q»
            buyum shunday topiladi. Natija rahbarga Telegramda boradi.</small>
        </div>
        {fil.length > 0 && (
          <select className="kichik-tanlov" value={filial} aria-label="Filial" onChange={(e) => setFilial(e.target.value)}>
            <option value="">Barcha filiallar</option>
            {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
          </select>
        )}
        <button type="button" className="bosh-tugma" onClick={boshla}><NavIkona nom="raqam" className="tugma-ikon" />Sanoqni boshlash</button>
      </section>
      <OldingiSanoqlar tarix={d.tarix} />
    </div>
  )
}

// Oldingi sanoqlar: sana · kim yakunlagan, «N tadan M tasi joyida», o'ngda natija yorlig'i
function OldingiSanoqlar({ tarix }) {
  if (!tarix?.length) return null
  return (
    <section className="blok sanoq-panel" aria-label="Oldingi sanoqlar">
      <h3 className="sanoq-panel-nom"><NavIkona nom="tarix" className="tugma-ikon" />Oldingi sanoqlar</h3>
      {tarix.map((s) => (
        <div key={s.id} className="sanoq-tarix-q">
          <span className="soz-matn">
            <b>{kunOy(s.yakunlangan)} · {s.yakunlagan}{s.filial ? ` · ${s.filial}` : ''}</b>
            <small>{s.kutilgan} tadan {s.topilgan} tasi joyida{s.izoh ? ` · ${s.izoh}` : ''}</small>
          </span>
          <span className="sanoq-yorliqlar">
            {s.yoq > 0 && <span className="soz-holat qizil">{s.yoq} ta yo'q</span>}
            {s.ortiqcha > 0 && <span className="soz-holat ogoh">{s.ortiqcha} ta kiritilmagan</span>}
            {!s.yoq && !s.ortiqcha && <span className="soz-holat yashil">hammasi joyida</span>}
          </span>
        </div>
      ))}
    </section>
  )
}

const HOZIR_KUN = bugunIso()
const kunOy = (s) => {
  if (!s) return ''
  const [y, m, k] = String(s).slice(0, 10).split('-')
  return `${y}-${m}-${k}` === HOZIR_KUN ? 'bugun' : `${Number(k)} ${OYLAR[Number(m) - 1].toLowerCase()}`
}
const soat = (s) => (s ? String(s).slice(11, 16) : '')
const PANEL_SONI = 5  // «Hali topilmaganlar» guruhida birinchi ko'rinadiganlar; qolgani «hammasini ko'rsatish»

function OchiqSanoq({ s, tarix, onYangila, onYakun, onBekor }) {
  const [artikul, setArtikul] = useState('')
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [hammasi, setHammasi] = useState(false)
  const [toliq, setToliq] = useState(false)
  const [izoh, setIzoh] = useState('')
  const [band, setBand] = useState(false)
  const [surov, setSurov] = useState(null)  // 'yakun' | 'bekor' — tasdiq oynasi
  const [aktiv, setAktiv] = useState(-1)  // klaviatura (↑/↓) bilan tanlangan taklif; -1 — Enter terilganini yuboradi (skaner)
  const kiritish = useRef(null)

  const qatorniYangila = (r) => onYangila({ ...s, qatorlar: s.qatorlar.map((q) => (qatorKaliti(q) === qatorKaliti(r) ? { ...q, topildi: r.topildi, xodim: r.xodim, vaqt: r.vaqt } : q)) })
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
  const boshqa = s.qatorlar.filter((q) => q.joy !== 'salonda')
  const topildi = salonda.filter((q) => q.topildi).length
  const qolgan = salonda.length - topildi
  const turlar = (r) => [r.filter((q) => q.tur === 'libos').length, r.filter((q) => q.tur !== 'libos').length]
  const [sl, sa] = turlar(salonda)
  const [bl, ba] = turlar(boshqa)
  const korinadi = hammasi ? s.qatorlar : s.qatorlar.filter((q) => !q.topildi)
  const oxirgilar = s.qatorlar.filter((q) => q.topildi && q.vaqt).sort((a, b) => String(b.vaqt).localeCompare(String(a.vaqt))).slice(0, 6)
  const foiz = salonda.length ? Math.round((topildi * 100) / salonda.length) : 100
  const guruhlar = [
    ['salonda', "Salonda bo'lishi kerak", korinadi.filter((q) => q.joy === 'salonda')],
    ['boshqa', "Ta'mirda, tozalashda, mijozda", korinadi.filter((q) => q.joy !== 'salonda')],
  ]
  return (
    <div className="stack sanoq-sahifa">
      <section className="sanoq-holat" aria-label="Sanoq holati">
        <span className="sanoq-nuqta" aria-hidden="true" />
        <div className="sanoq-holat-matn">
          <b>Sanoq ochiq · boshladi {s.boshlagan}, {kunOy(s.boshlangan)} {soat(s.boshlangan)}{s.filial ? ` · ${s.filial}` : ''}</b>
          <span className="sanoq-chiziq" role="progressbar" aria-label="Belgilangan" aria-valuenow={topildi} aria-valuemin={0} aria-valuemax={salonda.length}>
            <i style={{ width: `${foiz}%` }} />
          </span>
        </div>
        <b className="sanoq-son">{topildi} / {salonda.length}</b>
        <small className="sanoq-holat-izoh">bir necha kishi birga davom ettirishi mumkin</small>
      </section>

      <section className="dash-kpi libos-kpi" aria-label="Sanoq ko'rsatkichlari">
        <KpiFiltr nom="Salonda bo'lishi kerak" son={salonda.length} ikon="libos" rang="tilla" izoh={`${sl} libos · ${sa} dona aksessuar`} />
        <KpiFiltr nom="Topildi" son={topildi} ikon="bajarildi" rang="yashil" izoh="javonda belgilandi" />
        <KpiFiltr nom="Hali topilmagan" son={qolgan} ikon="filtr" rang="sariq" izoh={qolgan ? 'izlash davom etmoqda' : 'hammasi topildi'} />
        <KpiFiltr nom="Boshqa joyda" son={boshqa.length} ikon="mijoz" rang="kok" izoh={`${bl} libos · ${ba} aksessuar`} />
      </section>

      <div className="sanoq-ikki">
        <div className="sanoq-ustun">
          <section className="blok sanoq-panel" aria-label="Belgilash">
            <div className="sanoq-panel-bosh">
              <h3 className="sanoq-panel-nom"><NavIkona nom="raqam" className="tugma-ikon" />Belgilash</h3>
              <small>skaner yoki qo'lda</small>
            </div>
            <form className="sanoq-kiritish" onSubmit={skaner}>
              <div className="sanoq-maydon">
                <NavIkona nom="raqam" className="tugma-ikon" />
                <input ref={kiritish} autoFocus value={artikul} onChange={(e) => { setArtikul(e.target.value); setAktiv(-1) }} onKeyDown={strelka}
                  placeholder="Raqamini tering yoki skanerlang, masalan: L-0012" aria-label="Artikul" maxLength={50} autoComplete="off"
                  role="combobox" aria-expanded={taklif.length > 0} aria-controls="sanoq-takliflar" aria-autocomplete="list"
                  aria-activedescendant={aktiv >= 0 ? `taklif-${aktiv}` : undefined} />
              </div>
              <button type="submit" className="ikkinchi">Topildi</button>
            </form>
            {taklif.length > 0 && (
              <ul id="sanoq-takliflar" className="sanoq-takliflar" role="listbox" aria-label="Mos buyumlar">
                {taklif.map((q, i) => (
                  <li key={qatorKaliti(q)} id={`taklif-${i}`} role="option" aria-selected={i === aktiv}
                    className={`${i === aktiv ? 'aktiv' : ''} ${q.topildi ? 'topilgan' : ''}`}
                    onMouseDown={(e) => e.preventDefault()} onClick={() => tanla(q)}>
                    <b>{q.artikul}</b>
                    <span>{q.nomi}{q.olcham && ` · ${q.olcham}`}</span>
                    <small className={`soz-holat ${q.topildi ? 'yashil' : q.joy === 'mijozda' ? 'kok' : 'yopiq'}`}>{q.topildi ? '✓ belgilangan' : JOY[q.joy] || 'salonda'}</small>
                  </li>
                ))}
              </ul>
            )}
            {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot sanoq-xabar'}>{xabar.matn}</p>}
          </section>

          {oxirgilar.length > 0 && (
            <section className="blok sanoq-panel" aria-label="Oxirgi belgilanganlar">
              <h3 className="sanoq-panel-nom"><NavIkona nom="tarix" className="tugma-ikon" />Oxirgi belgilanganlar</h3>
              {oxirgilar.map((q) => (
                <div key={qatorKaliti(q)} className="sanoq-oxirgi-q">
                  <span className="soz-mute">{soat(q.vaqt)}</span>
                  <b>{q.artikul}</b>
                  <span>{q.nomi}</span>
                  <span className="soz-mute">{q.xodim}</span>
                </div>
              ))}
            </section>
          )}
          <OldingiSanoqlar tarix={tarix} />
        </div>

        <section className="blok sanoq-panel" aria-label={hammasi ? 'Hammasi' : 'Hali topilmaganlar'}>
          <div className="sanoq-panel-bosh">
            <h3 className="sanoq-panel-nom"><NavIkona nom="qidiruv" className="tugma-ikon" />{hammasi ? 'Hammasi' : 'Hali topilmaganlar'}</h3>
            <label className="sanoq-hammasi"><input type="checkbox" checked={hammasi} onChange={(e) => setHammasi(e.target.checked)} />topilganlar ham</label>
          </div>
          {korinadi.length === 0 && <p className="malumot jadval-bosh">Hammasi belgilandi.</p>}
          {/* Avval salonda turishi kerak bo'lganlar; keyin alohida — ta'mirda, tozalashda, mijozda (topilmasa ham xato emas) */}
          {guruhlar.map(([k, nom, guruh]) => guruh.length > 0 && (
            <div key={k} className="sanoq-guruh">
              <h4 className="sanoq-guruh-nom">{nom} <span className="tab-son">{guruh.length}</span>
                {k === 'boshqa' && <small>Javonda bo'lsa belgilang — bo'lmasa ham xato emas.</small>}</h4>
              {(toliq ? guruh : guruh.slice(0, PANEL_SONI)).map((q) => (
                <div key={qatorKaliti(q)} className={`sanoq-q${q.topildi ? ' bajarilgan' : ''}`}>
                  {q.rasm ? <img className="sanoq-rasm" src={q.rasm} alt="" /> : (
                    <span className="sanoq-plitka" aria-hidden="true"><Belgi nom={q.tur === 'libos' ? 'libos' : 'toj'} className="tugma-ikon" /></span>
                  )}
                  <span className="soz-matn">
                    <b>{q.artikul} · {q.nomi}</b>
                    <small>{q.kategoriya}{q.olcham && ` · ${q.olcham}`}{q.topildi && q.xodim && ` · belgiladi: ${q.xodim}`}</small>
                  </span>
                  {q.topildi
                    ? <button type="button" className="ikkinchi kichik" onClick={() => belgila({ ...qatorId(q), topildi: false })}>Bekor</button>
                    : q.joy === 'salonda'
                      ? <button type="button" className="ikkinchi kichik" onClick={() => belgila({ ...qatorId(q), topildi: true })}>Topildi</button>
                      : (
                        <span className="sanoq-joy">
                          <span className={`soz-holat ${q.joy === 'mijozda' ? 'kok' : 'ogoh'}`}>{JOY[q.joy]?.replace('tizimda: ', '')}</span>
                          <button type="button" className="havola" onClick={() => belgila({ ...qatorId(q), topildi: true })}>javonda</button>
                        </span>
                      )}
                </div>
              ))}
              {!toliq && guruh.length > PANEL_SONI && (
                <p className="sanoq-yana">yana {guruh.length - PANEL_SONI} ta · <button type="button" className="havola" onClick={() => setToliq(true)}>hammasini ko'rsatish</button></p>
              )}
            </div>
          ))}
        </section>
      </div>

      <section className="sanoq-yakun" aria-label="Sanoqni yakunlash">
        <div className="sanoq-yakun-matn">
          <b>{qolgan > 0 ? `${qolgan} ta buyum hali topilmagan` : 'Hammasi topildi'}</b>
          <small>{qolgan > 0 ? "Yakunlansa, topilmaganlar «yo'q» deb rahbarga Telegramda boradi; keyin qayta belgilab bo'lmaydi." : 'Yakunlang — natija rahbarga Telegramda boradi.'}</small>
        </div>
        <input value={izoh} onChange={(e) => setIzoh(e.target.value)} placeholder="Izoh: masalan, A-2 kimyoviy tozalashda" aria-label="Izoh (ixtiyoriy)" maxLength={300} />
        <button type="button" className="ikkinchi" onClick={() => setSurov('bekor')} disabled={band}>Bekor qilish</button>
        <button type="button" className="bosh-tugma" onClick={() => setSurov('yakun')} disabled={band}><NavIkona nom="bajarildi" className="tugma-ikon" />Sanoqni yakunlash</button>
      </section>
      {surov === 'yakun' && (
        <Tasdiq sarlavha="Sanoq yakunlansinmi?" tugma="Ha, yakunlash" xavfli={false}
          matn={qolgan > 0
            ? `${qolgan} ta buyum topilmagan — rahbarga Telegramda «yo'q» deb yuboriladi. Yakunlangan sanoqqa qayta belgilab bo'lmaydi.`
            : "Hammasi topildi. Natija rahbarga Telegramda yuboriladi."}
          onYop={() => setSurov(null)} onTasdiq={yakunla} />
      )}
      {surov === 'bekor' && (
        <Tasdiq sarlavha="Sanoq bekor qilinsinmi?" tugma="Ha, bekor qilish"
          matn={`Belgilangan ${s.qatorlar.filter((q) => q.topildi).length} ta buyum o'chadi, natija hech kimga yuborilmaydi. Tasodifan boshlangan bo'lsa — shu.`}
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

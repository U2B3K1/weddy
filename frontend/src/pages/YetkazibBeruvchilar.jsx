import { useCallback, useEffect, useState } from 'react'
import SummaInput from '../components/SummaInput'
import Tasdiq from '../components/Tasdiq'
import Oyna from '../components/Oyna'
import NavIkona from '../components/NavIkona'
import KpiFiltr from '../components/KpiFiltr'
import { BoshAmal } from '../components/BoshJoy'
import { Belgi } from '../components/ZakazQatorlari'
import { OYLAR } from '../components/kalendar/sana'
import {
  guruhla, som, xatoMatni, yetkazibBeruvchi, yetkazibBeruvchilar, yetkazibOzgartir, yetkazibTolov, yetkazibTolovOchir,
  yetkazibYarat,
} from '../api'

// «12 avg 2026» (kanvas jadvallari)
const sanaQisqa = (s) => { if (!s) return ''; const [y, m, d] = String(s).slice(0, 10).split('-'); return `${Number(d)} ${OYLAR[Number(m) - 1].slice(0, 3).toLowerCase()} ${y}` }
const HOLAT_RANG = { bosh: 'yashil', tamirda: 'ogoh', tozalashda: 'ogoh', tasdiq_kutilmoqda: 'ogoh', arxiv: 'yopiq', sotildi: 'yopiq', hisobdan_chiqarildi: 'qizil' }
const SONI = { libos: 4, tolov: 3 }  // tafsilotda birinchi ko'rinadiganlar; qolgani «hammasini ko'rsatish»

// Libos va aksessuar qayerdan olingani va yetkazib beruvchiga qolgan qarz (faqat rahbar). Kanvas (LibosYetkazibShisha):
// 3 ko'rsatkich; chapda «Kimdan olamiz» (qarzi kattasi tepada), o'ngda tanlangani — olingan, to'langan, qarz, to'lov yozish va tarix.
// Qarz = undan olingan liboslar tannarxi + aksessuarlar (dona tannarxi × soni) − unga to'langan pul. To'lov kassadan emas va foydaga kirmaydi.
export default function YetkazibBeruvchilar() {
  const [royxat, setRoyxat] = useState(null)
  const [ochiq, setOchiq] = useState(null)  // tanlangan yetkazib beruvchi id
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [oyna, setOyna] = useState(false)
  const [keng, setKeng] = useState(() => window.matchMedia('(min-width: 1024px)').matches)
  useEffect(() => {
    const m = window.matchMedia('(min-width: 1024px)'); const h = (e) => setKeng(e.matches)
    m.addEventListener('change', h); return () => m.removeEventListener('change', h)
  }, [])

  const yukla = useCallback(() => yetkazibBeruvchilar().then(setRoyxat), [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }
  const tartib = [...(royxat || [])].sort((a, b) => b.qarz - a.qarz || a.nomi.localeCompare(b.nomi))
  const qarzdor = tartib.filter((y) => y.qarz > 0)
  const jamiQarz = qarzdor.reduce((s, y) => s + y.qarz, 0)
  const oxirgi = tartib.filter((y) => y.oxirgi_tolov).sort((a, b) => String(b.oxirgi_tolov.sana).localeCompare(String(a.oxirgi_tolov.sana)))[0]
  const jamiLibos = tartib.reduce((s, y) => s + y.liboslar_soni, 0)
  const jamiDona = tartib.reduce((s, y) => s + y.aksessuar_donalar, 0)
  const joriyId = ochiq ?? (keng ? tartib[0]?.id ?? null : null)

  return (
    <div className="stack yb-sahifa">
      <BoshAmal>
        <button type="button" className="bosh-tugma" onClick={() => setOyna(true)}><NavIkona nom="qosh" className="tugma-ikon" />Yetkazib beruvchi qo'shish</button>
      </BoshAmal>
      {xabar.matn && joriyId == null && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      <section className="dash-kpi libos-kpi yb-kpi" aria-label="Yetkazib beruvchilar ko'rsatkichlari">
        <KpiFiltr nom="Yetkazib beruvchilar" son={royxat?.length ?? '—'} ikon="yuk" rang="tilla" izoh={`${jamiLibos} libos · ${jamiDona} dona aksessuar`} />
        <KpiFiltr nom="Ularga qarzimiz" son={guruhla(jamiQarz)} ikon="hamyon" rang="pushti" xavf={jamiQarz > 0} izoh={qarzdor.length ? `${qarzdor.length} tasiga` : "hech kimga qarz yo'q"} />
        <KpiFiltr nom="Oxirgi to'lov" son={oxirgi ? guruhla(oxirgi.oxirgi_tolov.summa) : '—'} ikon="bajarildi" rang="yashil"
          izoh={oxirgi ? `${sanaQisqa(oxirgi.oxirgi_tolov.sana)} · ${oxirgi.nomi}` : "hali to'lov yo'q"} />
      </section>

      {oyna && (
        <Oyna sarlavha="Yetkazib beruvchi qo'shish" onYop={() => setOyna(false)}>
          <YangiForma onYuborish={async (b) => { const ok = await bajar(() => yetkazibYarat(b), "Yetkazib beruvchi qo'shildi."); if (ok) setOyna(false); return ok }} />
        </Oyna>
      )}

      <div className={`yb-ikki${joriyId == null ? ' bitta' : ''}`}>
        <section className="blok yb-royxat" aria-label="Kimdan olamiz">
          <div className="sanoq-panel-bosh">
            <h3 className="sanoq-panel-nom"><Belgi nom="yuk" className="tugma-ikon" />Kimdan olamiz</h3>
            <small>qarzi kattasi tepada</small>
          </div>
          {royxat && royxat.length === 0 && (
            <p className="malumot jadval-bosh">Hali yo'q. Qo'shgach, libos va aksessuar qo'shishda «Qayerdan olingan» va «Hozir to'landi» maydonlari chiqadi.</p>
          )}
          {tartib.map((y) => (
            <div key={y.id} className={`yetkazib-qator${joriyId === y.id ? ' tanlangan' : ''}`}>
              <button type="button" className="yb-tugma" aria-pressed={joriyId === y.id} onClick={() => { setOchiq(y.id); setXabar({ turi: '', matn: '' }) }}>
                <span className="aks-plitka" aria-hidden="true"><Belgi nom={y.aksessuar_donalar && !y.liboslar_soni ? 'toj' : 'libos'} className="tugma-ikon" /></span>
                <span className="soz-matn"><b>{y.nomi}</b><small>{[y.izoh, y.telefon].filter(Boolean).join(' · ') || '—'}</small></span>
                <span className="yb-qarz">
                  <b className={y.qarz > 0 ? 'qizil' : ''}>{y.qarz > 0 ? guruhla(y.qarz) : y.qarz < 0 ? `oldindan ${guruhla(-y.qarz)}` : "qarz yo'q"}</b>
                  <small>{[y.liboslar_soni && `${y.liboslar_soni} libos`, y.aksessuar_donalar && `${y.aksessuar_donalar} dona`].filter(Boolean).join(' · ') || 'xarid yo\'q'}</small>
                </span>
              </button>
            </div>
          ))}
          <p className="aks-t-izoh"><NavIkona nom="yordam" className="tugma-ikon" />Bu bo'limni faqat rahbar ko'radi. Qarz = olingan liboslar va aksessuarlar tannarxi − ularga to'langan pul.</p>
        </section>
        {joriyId != null && <Tafsilot key={joriyId} id={joriyId} bajar={bajar} xabar={xabar} onYop={keng ? null : () => setOchiq(null)} />}
      </div>
    </div>
  )
}

function Tafsilot({ id, bajar, xabar, onYop }) {
  const [d, setD] = useState(null)
  const [f, setF] = useState({ summa: '', izoh: '' })
  const [xato, setXato] = useState('')
  const [ochirSurov, setOchirSurov] = useState(null)
  const [tahrir, setTahrir] = useState(false)
  const [toliq, setToliq] = useState({})
  const yukla = useCallback(() => yetkazibBeruvchi(id).then(setD), [id])
  // Xato jimgina yutilmasin: aks holda «Yuklanmoqda…» abadiy turardi (B-35)
  useEffect(() => { yukla().catch((e) => setXato(xatoMatni(e))) }, [yukla])
  const amal = async (fn, ok) => { const r = await bajar(fn, ok); if (r) await yukla(); return r }
  if (!d) return <section className="blok yb-tafsilot">{xato ? <p className="xato">{xato}</p> : <p className="malumot">Yuklanmoqda…</p>}</section>
  const liboslar = toliq.libos ? d.liboslar : d.liboslar.slice(0, SONI.libos)
  const qolganLibos = d.liboslar.slice(SONI.libos)
  const tolovlar = toliq.tolov ? d.tolovlar : d.tolovlar.slice(0, SONI.tolov)
  return (
    <section className="blok yb-tafsilot" aria-label={`${d.nomi} hisobi`}>
      {xabar.matn && <p className={`aks-xabar ${xabar.turi === 'xato' ? 'xato' : 'malumot'}`} role="status">{xabar.matn}</p>}
      <div className="aks-t-bosh">
        <span className="aks-plitka katta" aria-hidden="true"><Belgi nom="libos" className="tugma-ikon" /></span>
        <div>
          <h3>{d.nomi}</h3>
          <p>{[d.izoh, d.telefon].filter(Boolean).join(' · ') || "izoh va telefon kiritilmagan"}</p>
        </div>
        <button type="button" className="havola yb-tahrir-tugma" aria-expanded={tahrir} onClick={() => setTahrir(!tahrir)}>Tahrirlash</button>
        {onYop && <button type="button" className="ikon-tugma" aria-label="Yopish" onClick={onYop}><NavIkona nom="yop" className="tugma-ikon" /></button>}
      </div>
      {tahrir && <Tahrir d={d} onSaqla={(b) => amal(() => yetkazibOzgartir(id, b), 'Saqlandi.').then((ok) => ok && setTahrir(false))} />}
      <div className="yb-uch">
        <div><span>Olingan</span><b>{guruhla(d.xarid)}</b></div>
        <div><span>To'langan</span><b>{guruhla(d.tolangan)}</b></div>
        <div className={d.qarz > 0 ? 'qarz' : ''}><span>{d.qarz < 0 ? 'Oldindan to\'langan' : 'Qarz'}</span><b>{guruhla(Math.abs(d.qarz))}</b></div>
      </div>
      <div className="yb-tolov">
        <div className="yb-tolov-q">
          <label>To'lov summasi<SummaInput placeholder={d.qarz > 0 ? `qarz: ${guruhla(d.qarz)}` : ''} value={f.summa}
            onChange={(e) => setF({ ...f, summa: e.target.value })} /></label>
          <label>Izoh<input maxLength={300} value={f.izoh} placeholder="masalan: Oq ko'ylak — 3-qism" onChange={(e) => setF({ ...f, izoh: e.target.value })} /></label>
          <button type="button" className="ikkinchi" disabled={!(Number(f.summa) > 0)}
            onClick={() => amal(() => yetkazibTolov(id, { summa: Number(f.summa), izoh: f.izoh }).then(() => setF({ summa: '', izoh: '' })), "To'lov yozildi.")}>
            To'lov yozish
          </button>
        </div>
        {d.qarz > 0 && (
          <small>Qisman ham yozish mumkin · <button type="button" className="havola" onClick={() => setF({ ...f, summa: String(d.qarz) })}>qarzni to'liq yopish</button></small>
        )}
      </div>
      <p className="aks-t-izoh"><NavIkona nom="yordam" className="tugma-ikon" />Bu to'lov kassadan chiqmaydi va oylik foydaga kirmaydi — libos sarmoya, u ijaradan o'zini qaytaradi.</p>

      <div className="yb-bolim-bosh"><h4>Olingan liboslar</h4><small>{d.liboslar.length} ta</small></div>
      {d.liboslar.length === 0 ? <p className="soz-izoh">Libos qo'shishda yoki libos kartasida «Qayerdan olingan» ni tanlang.</p> : (
        <table className="soz-jadval yb-jadval">
          <thead><tr><th>Sana</th><th>Libos</th><th>Hozir</th><th className="ong">Tannarx</th></tr></thead>
          <tbody>
            {liboslar.map((l) => (
              <tr key={l.id}>
                <td className="soz-mute">{sanaQisqa(l.sana)}</td>
                <td><span className="yb-libos">
                  {l.rasm ? <img src={l.rasm} alt="" /> : <span className="sanoq-plitka" aria-hidden="true"><Belgi nom="libos" className="tugma-ikon" /></span>}
                  <span className="soz-matn"><b>{l.nomi}</b><small>{l.artikul}</small></span>
                </span></td>
                <td><span className={`soz-holat ${HOLAT_RANG[l.holat] || 'yopiq'}`}>{l.holat_nomi}</span></td>
                <td className="ong">{l.tannarx == null ? <span className="soz-mute">kiritilmagan</span> : guruhla(l.tannarx)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!toliq.libos && qolganLibos.length > 0 && (
        <p className="sanoq-yana">yana {qolganLibos.length} ta libos · {guruhla(qolganLibos.reduce((s, l) => s + (l.tannarx || 0), 0))} ·{' '}
          <button type="button" className="havola" onClick={() => setToliq({ ...toliq, libos: true })}>hammasini ko'rsatish</button></p>
      )}
      {d.aksessuarlar.length > 0 && (
        <>
          <div className="yb-bolim-bosh"><h4>Olingan aksessuarlar</h4><small>{d.aksessuarlar.length} partiya</small></div>
          <table className="soz-jadval yb-jadval">
            <thead><tr><th>Sana</th><th>Aksessuar</th><th className="ong">Soni</th><th className="ong">Narx</th><th className="ong">Jami</th></tr></thead>
            <tbody>
              {d.aksessuarlar.map((a) => (
                <tr key={a.id}>
                  <td className="soz-mute">{sanaQisqa(a.sana)}</td><td><b>{a.kod}</b> {a.nomi}</td><td className="ong">{a.soni}</td>
                  <td className="ong">{a.narx == null ? <span className="soz-mute">kiritilmagan</span> : som(a.narx)}</td>
                  <td className="ong">{a.narx == null ? '—' : som(a.jami)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      <div className="yb-bolim-bosh"><h4>To'lovlar</h4><small>{d.tolovlar.length} ta{d.tolovlar.length > SONI.tolov && !toliq.tolov ? ` · oxirgi ${SONI.tolov} tasi` : ''}</small></div>
      {d.tolovlar.length === 0 ? <p className="soz-izoh">Hali to'lov yozilmagan.</p> : (
        <table className="soz-jadval yb-jadval">
          <thead><tr><th>Sana</th><th className="ong">Summa</th><th>Izoh</th><th aria-label="Amallar" /></tr></thead>
          <tbody>
            {tolovlar.map((t) => (
              <tr key={t.id}>
                <td className="soz-mute">{sanaQisqa(t.sana)}</td><td className="ong"><b>{guruhla(t.summa)}</b></td><td>{t.izoh || '—'}</td>
                <td className="ong"><button type="button" className="havola soz-mute-havola" onClick={() => setOchirSurov(t)}>O'chirish</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!toliq.tolov && d.tolovlar.length > SONI.tolov && (
        <p className="sanoq-yana"><button type="button" className="havola" onClick={() => setToliq({ ...toliq, tolov: true })}>hamma to'lovlar ({d.tolovlar.length})</button></p>
      )}
      {ochirSurov && (
        <Tasdiq sarlavha="To'lov o'chirilsinmi?" tugma="Ha, o'chirish"
          matn={`${sanaQisqa(ochirSurov.sana)}dagi ${som(ochirSurov.summa)} to'lov o'chadi — yetkazib beruvchiga qarz shuncha oshadi. Qaytarib bo'lmaydi.`}
          onYop={() => setOchirSurov(null)}
          onTasdiq={() => { const t = ochirSurov; setOchirSurov(null); amal(() => yetkazibTolovOchir(t.id), "To'lov o'chirildi.") }} />
      )}
    </section>
  )
}

function Tahrir({ d, onSaqla }) {
  const [f, setF] = useState({ nomi: d.nomi, telefon: d.telefon, izoh: d.izoh })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="soz-tahrir stack">
      <label>Nomi<input value={f.nomi} maxLength={120} onChange={set('nomi')} /></label>
      <label>Telefon<input inputMode="tel" value={f.telefon} maxLength={30} onChange={set('telefon')} /></label>
      <label>Izoh (shahar, nima olinadi)<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
      <div className="soz-tugmalar"><button type="button" className="kichik" disabled={!f.nomi.trim()} onClick={() => onSaqla(f)}>Saqlash</button></div>
    </div>
  )
}

function YangiForma({ onYuborish }) {
  const [f, setF] = useState({ nomi: '', telefon: '', izoh: '' })
  return (
    <div className="stack">
      <label>Nomi *<input value={f.nomi} maxLength={120} placeholder="masalan: Istanbul Bridal" onChange={(e) => setF({ ...f, nomi: e.target.value })} /></label>
      <label>Telefon<input inputMode="tel" value={f.telefon} maxLength={30} onChange={(e) => setF({ ...f, telefon: e.target.value })} /></label>
      <label>Izoh<input value={f.izoh} maxLength={300} placeholder="masalan: Istanbul · to'y liboslari" onChange={(e) => setF({ ...f, izoh: e.target.value })} /></label>
      <button disabled={!f.nomi.trim()} onClick={async () => { if (await onYuborish(f)) setF({ nomi: '', telefon: '', izoh: '' }) }}>Qo'shish</button>
    </div>
  )
}

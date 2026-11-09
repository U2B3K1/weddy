import { useCallback, useEffect, useRef, useState } from 'react'
import NavIkona from '../components/NavIkona'
import Tasma from '../components/Tasma'
import Oyna from '../components/Oyna'
import { guruhla, salonchi, salonchiOzgartir, salonchiQosh, salonchilar, xatoMatni } from '../api'
import KpiFiltr from '../components/KpiFiltr'
import { BoshAmal } from '../components/BoshJoy'
import { Belgi } from '../components/ZakazQatorlari'
import { OYLAR } from '../components/kalendar/sana'

// 4.6: salonchilar (makiyaj ustalari) bazasi. Komissiya berilmaydi — faqat statistika.
// Kanvas (MijozSalonchiShisha): rahbarga — 3 ko'rsatkich, chapda «Kim ko'p mijoz olib keladi» reytingi, o'ngda tanlangan salonchi
// (statistika, aloqa, olib kelgan mijozlari). Sotuvchiga — faqat ro'yxat; bosilsa tahrir oynasi. Qo'shish va tahrir — `Oyna` da.
const telefonMatni = (t) => { const m = /^\+998(\d{2})(\d{3})(\d{2})(\d{2})$/.exec(t || ''); return m ? `+998 ${m[1]} ${m[2]} ${m[3]} ${m[4]}` : (t || '') }
const BOSH_FORMA = { ism: '', telefon: '', instagram: '', salon_nomi: '', manzil: '', izoh: '' }
const boshHarf = (ism) => String(ism || '?').trim().split(/\s+/).slice(0, 2).map((s) => s.charAt(0).toUpperCase()).join('')
const kunOy = (s) => { if (!s) return '—'; const [, m, d] = String(s).split('-'); return `${Number(d)} ${OYLAR[Number(m) - 1].slice(0, 3).toLowerCase()}` }
const oraliq = (a, b) => { if (!a) return ''; const [, m1, d1] = a.split('-'); const [, m2, d2] = (b || a).split('-'); return m1 === m2 ? `${Number(d1)} – ${Number(d2)} ${OYLAR[Number(m1) - 1].slice(0, 3).toLowerCase()}` : `${kunOy(a)} – ${kunOy(b)}` }
const instagramNomi = (h) => { const m = /instagram\.com\/([^/?]+)/.exec(h || ''); return m ? `@${m[1]}` : h }

export default function Salonchilar({ rahbar }) {
  const [royxat, setRoyxat] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [q, setQ] = useState('')
  const [oyna, setOyna] = useState(null)  // 'yangi' | salonchi (tahrir)
  const [tanlangan, setTanlangan] = useState(null)
  const [keng, setKeng] = useState(() => window.matchMedia('(min-width: 1024px)').matches)
  useEffect(() => {
    const m = window.matchMedia('(min-width: 1024px)'); const h = (e) => setKeng(e.matches)
    m.addEventListener('change', h); return () => m.removeEventListener('change', h)
  }, [])
  const [tYangi, setTYangi] = useState(0)  // tafsilotni qayta yuklash belgisi

  const yukla = useCallback(() => salonchilar(rahbar ? { hammasi: 1 } : {}).then(setRoyxat), [rahbar])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); setTYangi((n) => n + 1); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }
  const t = q.trim().toLowerCase()
  // reyting: ko'p mijoz olib kelgani tepada (rahbar), nofaollar oxirida
  const tartib = [...(royxat || [])].sort((a, b) => (b.faol - a.faol) || ((b.mijozlar_soni || 0) - (a.mijozlar_soni || 0)) || ((b.tushum || 0) - (a.tushum || 0)) || a.ism.localeCompare(b.ism))
  const korinadi = tartib.filter((x) => !t || [x.ism, x.salon_nomi, x.telefon, x.instagram].some((v) => String(v || '').toLowerCase().includes(t)))
  const maks = Math.max(1, ...tartib.map((x) => x.mijozlar_soni || 0))
  const faollar = tartib.filter((x) => x.faol).length
  const jamiMijoz = tartib.reduce((s, x) => s + (x.mijozlar_soni || 0), 0)
  const jamiSumma = tartib.reduce((s, x) => s + (x.tushum || 0), 0)
  const joriyId = rahbar ? (tanlangan ?? (keng ? korinadi[0]?.id ?? null : null)) : null
  const bos = (x) => (rahbar ? setTanlangan(x.id) : setOyna(x))

  return (
    <div className="stack salonchi-sahifa">
      <BoshAmal>
        <button type="button" className="bosh-tugma" onClick={() => setOyna('yangi')}><NavIkona nom="qosh" className="tugma-ikon" />Salonchi qo'shish</button>
      </BoshAmal>
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'} role="status">{xabar.matn}</p>}
      {rahbar && (
        <section className="dash-kpi libos-kpi yb-kpi" aria-label="Salonchilar ko'rsatkichlari">
          <KpiFiltr nom="Salonchilar" son={tartib.length} ikon="foiz" rang="tilla" izoh={`${faollar} faol · ${tartib.length - faollar} nofaol`} />
          <KpiFiltr nom="Ular olib kelgan mijozlar" son={jamiMijoz} ikon="mijoz" rang="kok" izoh="zakazda salonchi belgilangan" />
          <KpiFiltr nom="Shu mijozlar zakazlari" son={guruhla(jamiSumma)} ikon="tushum" rang="yashil" izoh="komissiya berilmaydi" />
        </section>
      )}
      <div className={`yb-ikki salonchi-ikki${joriyId == null ? ' bitta' : ''}`}>
        <section className="blok salonchi-royxat" aria-label="Salonchilar ro'yxati">
          <div className="sanoq-panel-bosh">
            <h3 className="sanoq-panel-nom"><Belgi nom="foiz" className="tugma-ikon" />{rahbar ? "Kim ko'p mijoz olib keladi" : 'Salonchilar'}</h3>
            <label className="qidiruv-maydon">
              <NavIkona nom="qidiruv" className="tugma-ikon" />
              <input type="search" className="jadval-qidiruv" aria-label="Salonchi qidirish" placeholder="Ism, salon yoki telefon" value={q} onChange={(e) => setQ(e.target.value)} />
            </label>
          </div>
          {royxat && royxat.length === 0 && (
            <div className="jadval-bosh r2s-bosh">
              <p>Hali salonchi yo'q. Salonchi — mijoz olib keladigan makiyaj ustasi yoki boshqa salon. Zakazda belgilansa, kim qancha mijoz olib kelgani shu yerda ko'rinadi.</p>
            </div>
          )}
          {royxat && royxat.length > 0 && korinadi.length === 0 && <p className="malumot jadval-bosh">Bu qidiruv bo'yicha salonchi yo'q.</p>}
          {korinadi.length > 0 && (
            <Tasma className="jadval-ora" pastki={48}>
              <table className="r2s-jadval salonchi-jadval">
                <thead>
                  <tr><th>Salonchi</th><th className="tor-yashir">Telefon</th>
                    {rahbar && <><th>Mijozlar</th><th className="ong">Zakazlar</th></>}</tr>
                </thead>
                <tbody>
                  {korinadi.map((x, i) => (
                    <tr key={x.id} className={`${x.faol ? '' : 'r2s-nofaol'}${joriyId === x.id ? ' tanlangan' : ''}`} onClick={() => bos(x)}>
                      <td>
                        <button type="button" className="salonchi-nom" aria-pressed={rahbar ? joriyId === x.id : undefined} onClick={(e) => { e.stopPropagation(); bos(x) }}>
                          {rahbar && <span className={`salonchi-orin o${i + 1}`} aria-label={`${i + 1}-o'rin`}>{i + 1}</span>}
                          <span className="soz-avatar" aria-hidden="true">{boshHarf(x.ism)}</span>
                          <span className="soz-matn"><b>{x.ism}{!x.faol && <span className="soz-holat yopiq salonchi-holat">Nofaol</span>}</b>
                            <small>{[x.salon_nomi, x.manzil].filter(Boolean).join(' · ') || '—'}</small></span>
                        </button>
                      </td>
                      <td className="tor-yashir">{x.telefon ? <a href={`tel:${x.telefon}`} onClick={(e) => e.stopPropagation()}>{telefonMatni(x.telefon)}</a> : <span className="soz-mute">—</span>}</td>
                      {rahbar && (
                        <>
                          <td><span className="salonchi-bar"><i style={{ width: `${Math.round(((x.mijozlar_soni || 0) * 100) / maks)}%` }} /></span><b className="salonchi-son">{x.mijozlar_soni}</b></td>
                          <td className="ong"><b>{guruhla(x.tushum)}</b></td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Tasma>
          )}
          <p className="aks-t-izoh"><NavIkona nom="yordam" className="tugma-ikon" />Salonchi — mijoz olib keladigan makiyaj ustasi yoki boshqa salon. Zakazda belgilansa, shu yerda hisoblanadi.
            {rahbar && ' Mijozlar davrdan qat\'i nazar; summa — to\'liq to\'langan zakazlar; komissiya berilmaydi — faqat statistika.'}</p>
        </section>
        {joriyId != null && (
          <SalonchiTafsilot key={`${joriyId}-${tYangi}`} id={joriyId} onTahrir={(s) => setOyna(s)} onYop={keng ? null : () => setTanlangan(null)}
            onFaol={(s) => bajar(() => salonchiOzgartir(s.id, { faol: !s.faol }), s.faol ? 'Nofaol qilindi.' : 'Faollashtirildi.')} />
        )}
      </div>
      {oyna === 'yangi' && (
        <Oyna sarlavha="Salonchi qo'shish" onYop={() => setOyna(null)}>
          <SalonchiMaydonlar boshlangich={BOSH_FORMA} tugma="Qo'shish"
            onSaqla={(b) => bajar(() => salonchiQosh(b), "Salonchi qo'shildi.").then((ok) => { if (ok) setOyna(null); return ok })} />
        </Oyna>
      )}
      {oyna && oyna !== 'yangi' && (
        <Oyna sarlavha={oyna.ism} onYop={() => setOyna(null)}>
          <SalonchiMaydonlar tugma="Saqlash"
            boshlangich={{ ism: oyna.ism, telefon: oyna.telefon || '', instagram: oyna.instagram || '', salon_nomi: oyna.salon_nomi || '', manzil: oyna.manzil || '', izoh: oyna.izoh || '' }}
            onSaqla={(b) => bajar(() => salonchiOzgartir(oyna.id, b), 'Salonchi saqlandi.').then((ok) => { if (ok) setOyna(null); return ok })} />
          <div className="qator r2s-qoshimcha">
            {oyna.instagram && <a className="tugma-havola" href={oyna.instagram} target="_blank" rel="noreferrer">Instagram</a>}
            <button type="button" className="ikkinchi kichik"
              onClick={() => bajar(() => salonchiOzgartir(oyna.id, { faol: !oyna.faol }), oyna.faol ? 'Nofaol qilindi.' : 'Faollashtirildi.').then((ok) => ok && setOyna(null))}>
              {oyna.faol ? 'Nofaol qilish' : 'Faollashtirish'}
            </button>
          </div>
          {oyna.faol && <p className="malumot">Nofaol salonchi yangi zakazda tanlanmaydi; statistikasi saqlanadi.</p>}
        </Oyna>
      )}
    </div>
  )
}

// O'ng panel (faqat rahbar): statistika, aloqa va shu salonchi olib kelgan mijozlarning zakazlari
function SalonchiTafsilot({ id, onTahrir, onFaol, onYop }) {
  const [d, setD] = useState(null)
  const [xato, setXato] = useState('')
  const [toliq, setToliq] = useState(false)
  useEffect(() => { salonchi(id).then(setD).catch((e) => setXato(xatoMatni(e))) }, [id])
  if (!d) return <section className="blok yb-tafsilot">{xato ? <p className="xato">{xato}</p> : <p className="malumot">Yuklanmoqda…</p>}</section>
  const zz = toliq ? d.zakazlar : d.zakazlar.slice(0, 3)
  return (
    <section className="blok yb-tafsilot salonchi-tafsilot" aria-label={`${d.ism} tafsiloti`}>
      <div className="aks-t-bosh">
        <span className="soz-avatar katta" aria-hidden="true">{boshHarf(d.ism)}</span>
        <div>
          <h3>{d.ism}</h3>
          <p>{[d.salon_nomi, d.manzil].filter(Boolean).join(' · ') || 'salon nomi kiritilmagan'}</p>
          <span className="salonchi-yorliqlar">
            <span className={`soz-holat ${d.faol ? 'yashil' : 'yopiq'}`}>{d.faol ? 'Faol' : 'Nofaol'}</span>
            {d.izoh && <span className="soz-holat yopiq">{d.izoh}</span>}
          </span>
        </div>
        {onYop && <button type="button" className="ikon-tugma" aria-label="Yopish" onClick={onYop}><NavIkona nom="yop" className="tugma-ikon" /></button>}
      </div>
      <div className="yb-uch salonchi-uch">
        <div><span>Mijozlar</span><b>{d.mijozlar_soni}</b></div>
        <div><span>Zakazlar</span><b>{guruhla(d.tushum)}</b></div>
        <div><span>Oxirgisi</span><b>{kunOy(d.oxirgi)}</b></div>
      </div>
      <div className="aks-t-qatorlar">
        <div className="aks-t-q"><span>Telefon</span><b>{d.telefon ? <a href={`tel:${d.telefon}`}>{telefonMatni(d.telefon)}</a> : '—'}</b></div>
        <div className="aks-t-q"><span>Instagram</span><b>{d.instagram ? <a className="salonchi-insta" href={d.instagram} target="_blank" rel="noreferrer">{instagramNomi(d.instagram)}</a> : '—'}</b></div>
        <div className="aks-t-q"><span>Manzil</span><b>{d.manzil || '—'}</b></div>
      </div>
      <div className="yb-bolim-bosh"><h4>Olib kelgan mijozlari</h4><small>{d.zakazlar.length ? 'oxirgilari' : ''}</small></div>
      {d.zakazlar.length === 0 ? <p className="soz-izoh">Hali zakazda belgilanmagan.</p> : (
        <div className="salonchi-zakazlar">
          {zz.map((z) => (
            <div key={z.id} className="salonchi-z">
              <span className="soz-avatar" aria-hidden="true">{boshHarf(z.mijoz)}</span>
              <span className="soz-matn"><b>{z.mijoz}</b><small>#{z.raqam}{z.liboslar ? ` · ${z.liboslar}` : ''} · {oraliq(z.olib_ketish, z.qaytarish)}</small></span>
              <b className="salonchi-z-summa">{guruhla(z.jami)}</b>
            </div>
          ))}
        </div>
      )}
      {!toliq && d.zakazlar.length > 3 && (
        <p className="sanoq-yana">yana {d.zakazlar.length - 3} ta zakaz · <button type="button" className="havola" onClick={() => setToliq(true)}>hammasini ko'rsatish</button></p>
      )}
      <div className="salonchi-amallar">
        <button type="button" className="ikkinchi kichik" onClick={() => onTahrir(d)}>Tahrirlash</button>
        <button type="button" className="havola" onClick={() => onFaol(d)}>{d.faol ? 'Nofaol qilish' : 'Faollashtirish'}</button>
      </div>
      <p className="soz-izoh">Nofaol salonchi yangi zakazda tanlanmaydi; statistikasi saqlanadi.</p>
    </section>
  )
}

function SalonchiMaydonlar({ boshlangich, tugma, onSaqla }) {
  const [f, setF] = useState(boshlangich)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="stack">
      <label>Ism *<input value={f.ism} maxLength={200} onChange={set('ism')} /></label>
      <div className="libos-narxlar">
        <label>Telefon<input inputMode="tel" value={f.telefon} placeholder="masalan: +998 90 123 45 67" onChange={set('telefon')} /></label>
        <label>Instagram (@nomi yoki havola)<input value={f.instagram} onChange={set('instagram')} /></label>
      </div>
      <div className="libos-narxlar">
        <label>Salon nomi<input value={f.salon_nomi} onChange={set('salon_nomi')} /></label>
        <label>Manzil<input value={f.manzil} onChange={set('manzil')} /></label>
      </div>
      <label>Izoh<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
      <button disabled={!f.ism.trim()} onClick={() => onSaqla({ ...f, ism: f.ism.trim() })}>{tugma}</button>
      {!f.ism.trim() && <p className="malumot">To'ldiring: Ism</p>}
    </div>
  )
}

// onYuborish: true/false qaytaradi yoki xato otadi — xato forma ichida ko'rsatiladi
// (yangi zakazda forma sahifa pastida, tepadagi xabar ko'rinmay qolardi).
export function SalonchiForma({ onYuborish, ochiq }) {
  const [f, setF] = useState({})
  const [yuborilmoqda, setYuborilmoqda] = useState(false)
  const [xato, setXato] = useState('')
  const quti = useRef(null)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const yubor = async () => {
    setXato(''); setYuborilmoqda(true)
    try {
      if (await onYuborish({ ...f, ism: f.ism.trim() })) { setF({}); if (!ochiq && quti.current) quti.current.open = false }
    } catch (e) { setXato(xatoMatni(e)) } finally { setYuborilmoqda(false) }
  }
  return (
    <details ref={quti} className="blok amal" open={ochiq}>
      <summary>Salonchi qo'shish</summary>
      <div className="stack">
        <label>Ism *<input value={f.ism || ''} onChange={set('ism')} /></label>
        <label>Telefon<input inputMode="tel" value={f.telefon || ''} onChange={set('telefon')} /></label>
        <label>Instagram (@nomi yoki havola)<input value={f.instagram || ''} onChange={set('instagram')} /></label>
        <label>Salon nomi<input value={f.salon_nomi || ''} onChange={set('salon_nomi')} /></label>
        <label>Manzil<input value={f.manzil || ''} onChange={set('manzil')} /></label>
        {xato && <p className="xato">{xato}</p>}
        <button type="button" disabled={!f.ism?.trim() || yuborilmoqda} onClick={yubor}>
          {yuborilmoqda ? "Qo'shilmoqda…" : "Qo'shish"}
        </button>
      </div>
    </details>
  )
}

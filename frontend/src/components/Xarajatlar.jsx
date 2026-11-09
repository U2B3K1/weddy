import { useCallback, useEffect, useState } from 'react'
import {
  doimiyXarajatOzgartir, doimiyXarajatQosh, doimiyXarajatlar, filiallar, hisobot, moddaOzgartir, moddaQosh, som, xarajatModdalari,
  xarajatBekor, xarajatQaror, xarajatTuzat, xarajatYarat, xarajatlar, xatoMatni,
  sanaMatni, guruhla,
} from '../api'
import KpiFiltr from './KpiFiltr'
import { BoshAmal } from './BoshJoy'
import { Belgi } from './ZakazQatorlari'
import NavIkona from './NavIkona'
import Oyna from './Oyna'
import OyTanlash from './OyTanlash'
import Sahifali from './Sahifalash'
import SummaInput from './SummaInput'
import Tasdiq from './Tasdiq'

const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const oyOraligi = (oy) => { const [y, m] = oy.split('-').map(Number); return [`${oy}-01`, iso(new Date(y, m, 0))] }
const oldingiOy = (oy) => { const [y, m] = oy.split('-').map(Number); const d = new Date(y, m - 2, 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}` }

// Rahbar uchun xarajatlar (4.13). Kanvas (HisobotXarajatShisha): 4 ko'rsatkich; chapda oy jadvali (modda bo'yicha chiplar,
// tasdiq kutayotganlar tepada, pastda jami), o'ngda «Taqsimot» halqasi (turlar bo'yicha, faqat tasdiqlangan) va doimiy xarajatlar.
// «Xarajat kiritish» — tablar qatori o'ngida, oynada. Xarajat turlari (FT-13.1) — chap ustun ostida.
const RANGLAR = ['#F3BF70', '#79A9F2', '#62D4A3', '#B79CF2', '#F08FB8', '#F2C46D', '#7FD1D9', '#C9CCD4']
const kunOy = (s) => { const [, m, d] = String(s).split('-'); return `${Number(d)} ${OYLAR_QISQA[Number(m) - 1]}` }
const OYLAR_QISQA = ['yan', 'fev', 'mar', 'apr', 'may', 'iyun', 'iyul', 'avg', 'sen', 'okt', 'noy', 'dek']
const mln = (n) => (n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1).replace('.', ',').replace(',0', '')} mln` : guruhla(n))

export default function Xarajatlar() {
  const [oy, setOy] = useState(() => OyTanlash.joriy())
  const [royxat, setRoyxat] = useState([])
  const [moddalar, setModdalar] = useState([])
  const [doimiy, setDoimiy] = useState([])
  const [fil, setFil] = useState([])
  const [turlar, setTurlar] = useState(null)  // [{nom, bu, otgan}]
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [oyna, setOyna] = useState(null)  // 'yangi' | xarajat (tuzatish)
  const [radSurov, setRadSurov] = useState(null)
  const [filtr, setFiltr] = useState('')

  const yukla = useCallback(async () => {
    const [a, b, c, bu, otgan] = await Promise.all([xarajatlar({ oy }), xarajatModdalari(true), doimiyXarajatlar(),
      hisobot('xarajat', ...oyOraligi(oy)), hisobot('xarajat', ...oyOraligi(oldingiOy(oy)))])
    setRoyxat(a); setModdalar(b); setDoimiy(c)
    // Turlar bo'yicha jamlanma: faqat tasdiqlangan (foydaga kirgan) summalar
    const nomlar = [...new Set([...bu.qatorlar, ...otgan.qatorlar].map((q) => q[0]))]
    const summa = (h, nom) => h.qatorlar.find((q) => q[0] === nom)?.[1] || 0
    setTurlar(nomlar.map((nom) => ({ nom, bu: summa(bu, nom), otgan: summa(otgan, nom) }))
      .filter((t) => t.bu || t.otgan).sort((x, y) => y.bu - x.bu || y.otgan - x.otgan))
  }, [oy])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])
  useEffect(() => { filiallar().then((r) => setFil(r.filiallar)).catch(() => {}) }, [])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }
  const faol = moddalar.filter((m) => m.faol)
  // Tasdiq kutayotganlar tepada (ajratilgan), qolgani sana bo'yicha
  const tartib = [...royxat].sort((a, b) => (a.holat === 'kutilmoqda' ? 0 : 1) - (b.holat === 'kutilmoqda' ? 0 : 1) || (b.sana > a.sana ? 1 : b.sana < a.sana ? -1 : 0))
  const korinadi = filtr ? tartib.filter((x) => x.modda_nomi === filtr) : tartib
  const kutayotgan = royxat.filter((x) => x.holat === 'kutilmoqda')
  const tasdiqlangan = royxat.filter((x) => x.holat === 'tasdiqlandi')
  const jami = tasdiqlangan.reduce((s, x) => s + x.summa, 0)
  const doimiySumma = tasdiqlangan.filter((x) => x.doimiy).reduce((s, x) => s + x.summa, 0)
  const doimiyNomlar = [...new Set(tasdiqlangan.filter((x) => x.doimiy).map((x) => x.modda_nomi))]
  const ozgaruvchanNomlar = [...new Set(tasdiqlangan.filter((x) => !x.doimiy).map((x) => x.modda_nomi))]
  const filtrNomlar = [...new Set(royxat.map((x) => x.modda_nomi))]
  const koringanJami = korinadi.filter((x) => x.holat === 'tasdiqlandi').reduce((s, x) => s + x.summa, 0)
  const qisqa = (r) => r.slice(0, 2).join(', ').toLowerCase() + (r.length > 2 ? ' va boshqalar' : '')

  return (
    <div className="stack xarajat-sahifa">
      <BoshAmal>
        <button type="button" className="bosh-tugma" onClick={() => setOyna('yangi')}><NavIkona nom="qosh" className="tugma-ikon" />Xarajat kiritish</button>
      </BoshAmal>
      <section className="dash-kpi libos-kpi" aria-label="Xarajat ko'rsatkichlari">
        <KpiFiltr nom="Jami xarajat" son={guruhla(jami)} ikon="chiqdi" rang="pushti" izoh={`${tasdiqlangan.length} ta tasdiqlangan yozuv`} />
        <KpiFiltr nom="Doimiy" son={guruhla(doimiySumma)} ikon="kun" rang="kok" izoh={doimiyNomlar.length ? qisqa(doimiyNomlar) : "bu oy hali yo'q"} />
        <KpiFiltr nom="O'zgaruvchan" son={guruhla(jami - doimiySumma)} ikon="tushum" rang="tilla" izoh={ozgaruvchanNomlar.length ? qisqa(ozgaruvchanNomlar) : "bu oy hali yo'q"} />
        <KpiFiltr nom="Tasdiq kutmoqda" son={guruhla(kutayotgan.reduce((s, x) => s + x.summa, 0))} ikon="soat" rang="sariq"
          izoh={kutayotgan.length ? `${kutayotgan.length} ta · jamiga kirmagan` : "kutayotgani yo'q"} />
      </section>
      {xabar.matn && <p className={`${xabar.turi === 'xato' ? 'xato' : 'malumot'} r2-xabar`} role="status">{xabar.matn}</p>}

      <div className="xarajat-ikki">
        <div className="sanoq-ustun">
          <section className="blok xarajat-panel r2-xarajat" aria-label="Xarajatlar ro'yxati">
            <div className="sanoq-panel-bosh">
              <h3 className="sanoq-panel-nom"><Belgi nom="filtr" className="tugma-ikon" />Xarajatlar</h3>
              <OyTanlash value={oy} onChange={(v) => { setOy(v); setFiltr('') }} />
            </div>
            {filtrNomlar.length > 1 && (
              <div className="hisobot-chiplar xarajat-chiplar" role="group" aria-label="Xarajat turi bo'yicha">
                {['', ...filtrNomlar].map((n) => (
                  <button key={n || 'hammasi'} type="button" className={filtr === n ? 'faol' : ''} aria-pressed={filtr === n} onClick={() => setFiltr(n)}>{n || 'Hammasi'}</button>
                ))}
              </div>
            )}
            {royxat.length === 0 ? <p className="malumot jadval-bosh">Bu oyda xarajat yo'q.</p> : (
              <Sahifali royxat={korinadi} hajm={15} kalit={`${oy}-${filtr}`}>{(qism) => (
                <table className="soz-jadval r2-xarajat-jadval">
                  <thead>
                    <tr><th>Sana</th><th>Modda</th><th>Izoh · kim yozdi</th><th className="ong">Summa</th><th>Holat</th><th aria-label="Amallar" /></tr>
                  </thead>
                  <tbody>
                    {qism.map((x) => (
                      <XarajatQator key={`${x.id}-${x.summa}-${x.holat}`} x={x} bajar={bajar}
                        onTuzat={() => setOyna(x)} onRad={() => setRadSurov(x)} />
                    ))}
                  </tbody>
                  <tfoot>
                    <tr><td>Jami</td><td colSpan={2} className="soz-mute">{kutayotgan.length ? 'tasdiq kutayotgan jamiga kirmaydi' : 'tasdiqlangan xarajatlar'}</td>
                      <td className="ong">−{guruhla(koringanJami)}</td><td colSpan={2} /></tr>
                  </tfoot>
                </table>
              )}</Sahifali>
            )}
          </section>
          <ModdalarBloki moddalar={moddalar} bajar={bajar} />
        </div>

        <div className="sanoq-ustun">
          <Taqsimot turlar={turlar} oy={oy} />
          <section className="blok xarajat-panel" aria-label="Doimiy xarajatlar">
            <DoimiyBlok doimiy={doimiy} royxat={royxat} moddalar={faol} fil={fil} oy={oy} bajar={bajar} />
          </section>
        </div>
      </div>

      {oyna === 'yangi' && (
        <Oyna sarlavha="Xarajat qo'shish" onYop={() => setOyna(null)}>
          <Forma moddalar={faol} onYuborish={(b) => bajar(() => xarajatYarat(b), 'Xarajat yozildi.').then((ok) => { if (ok) setOyna(null); return ok })} />
        </Oyna>
      )}
      {oyna && oyna !== 'yangi' && (
        <Oyna sarlavha={`Xarajatni tuzatish · ${sanaMatni(oyna.sana)}`} onYop={() => setOyna(null)}>
          <XarajatTahrir x={oyna} moddalar={faol}
            bajar={(fn, ok) => bajar(fn, ok).then((r) => { if (r) setOyna(null); return r })} />
        </Oyna>
      )}
      {radSurov && (
        <Tasdiq sarlavha="Xarajat rad etilsinmi?" tugma="Ha, rad etish"
          matn={`${som(radSurov.summa)} kassadan chiqib bo'lgan: rad etilsa, bu summa ${radSurov.kiritgan || 'xodim'}ning kamomadi bo'ladi.`}
          onYop={() => setRadSurov(null)}
          onTasdiq={() => { const x = radSurov; setRadSurov(null); bajar(() => xarajatQaror(x.id, 'rad'), `Rad etildi — ${som(x.summa)} ${x.kiritgan || 'xodim'}ning kamomadi.`) }} />
      )}
    </div>
  )
}

// «Taqsimot» — halqa diagramma: tasdiqlangan xarajatlar turlar bo'yicha; ostida ro'yxat (summa va ulush), o'tgan oy bilan farq
function Taqsimot({ turlar, oy }) {
  const bor = (turlar || []).filter((t) => t.bu > 0)
  const jami = bor.reduce((s, t) => s + t.bu, 0)
  const otgan = (turlar || []).reduce((s, t) => s + t.otgan, 0)
  const R = 54, C = 2 * Math.PI * R
  // har bo'lak boshlanishi — oldingilar uzunligi yig'indisi (render ichida o'zgaruvchi qayta yozilmasin)
  const boshlar = bor.map((_, i) => bor.slice(0, i).reduce((s, t) => s + (t.bu / jami) * C, 0))
  return (
    <section className="blok xarajat-panel" aria-label="Taqsimot">
      <h3 className="sanoq-panel-nom"><NavIkona nom="foiz" className="tugma-ikon" />Taqsimot</h3>
      {!jami ? <p className="soz-izoh">Bu oy tasdiqlangan xarajat yo'q.</p> : (
        <>
          <div className="taqsimot-halqa">
            <svg viewBox="0 0 140 140" role="img" aria-label={`Xarajatlar taqsimoti: ${bor.map((t) => `${t.nom} ${Math.round((t.bu * 100) / jami)}%`).join(', ')}`}>
              <circle cx="70" cy="70" r={R} fill="none" stroke="rgba(255,255,255,.07)" strokeWidth="16" />
              {bor.map((t, i) => (
                <circle key={t.nom} cx="70" cy="70" r={R} fill="none" stroke={RANGLAR[i % RANGLAR.length]} strokeWidth="16"
                  strokeDasharray={`${Math.max((t.bu / jami) * C - 2, 0.5)} ${C}`} strokeDashoffset={-boshlar[i]} transform="rotate(-90 70 70)" />
              ))}
            </svg>
            <span className="taqsimot-markaz"><b>{mln(jami)}</b><small>{OyTanlash.nomi(oy)}</small></span>
          </div>
          <ul className="taqsimot-royxat">
            {bor.map((t, i) => (
              <li key={t.nom}>
                <i style={{ background: RANGLAR[i % RANGLAR.length] }} aria-hidden="true" />
                <span>{t.nom}</span><b>{guruhla(t.bu)}</b><small>{Math.round((t.bu * 100) / jami)}%</small>
              </li>
            ))}
          </ul>
          {otgan > 0 && (
            <p className="soz-izoh">O'tgan oy jami: {guruhla(otgan)} ({jami >= otgan ? '+' : '−'}{Math.abs(Math.round(((jami - otgan) * 100) / otgan))}%).</p>
          )}
        </>
      )}
    </section>
  )
}

// Doimiy xarajatlar (FT-13.3): har oy boshida qoralama yaratiladi — rahbar summani tekshirib tasdiqlaydi yoki rad etadi.
// Holat: shu oyda shu turdagi doimiy xarajat tasdiqlangan bo'lsa — «to'landi», aks holda — «kutilmoqda».
function DoimiyBlok({ doimiy, royxat, moddalar, fil, oy, bajar }) {
  const [forma, setForma] = useState(false)
  const holati = (d) => {
    const bu = royxat.filter((x) => x.doimiy && x.modda === d.modda)
    return bu.some((x) => x.holat === 'tasdiqlandi') ? ['yashil', "to'landi"] : ['yopiq', 'kutilmoqda']
  }
  return (
    <>
      <div className="sanoq-panel-bosh">
        <h3 className="sanoq-panel-nom"><Belgi nom="kun" className="tugma-ikon" />Doimiy xarajatlar</h3>
        <small>{OyTanlash.nomi(oy).split(' ')[0].toLowerCase()}</small>
      </div>
      {doimiy.length === 0 && <p className="soz-izoh">Doimiy xarajat yo'q. Qo'shilsa, har oy boshida qoralama yaratiladi — siz tasdiqlaysiz yoki rad etasiz.</p>}
      {doimiy.map((d) => <DoimiyQator key={d.id} d={d} holat={holati(d)} bajar={bajar} />)}
      <button type="button" className="ikkinchi kichik xarajat-doimiy-qosh" aria-expanded={forma} onClick={() => setForma(!forma)}>
        {forma ? 'Yopish' : "+ Doimiy xarajat"}
      </button>
      {forma && (
        <div className="soz-tahrir">
          <Forma moddalar={moddalar} doimiy fil={fil} tugma="Doimiy xarajat qo'shish"
            onYuborish={(b) => bajar(() => doimiyXarajatQosh(b), "Doimiy xarajat qo'shildi.").then((ok) => { if (ok) setForma(false); return ok })} />
        </div>
      )}
    </>
  )
}

function XarajatQator({ x, bajar, onTuzat, onRad }) {
  const [summa, setSumma] = useState(x.summa)
  const kutmoqda = x.holat === 'kutilmoqda'
  return (
    <tr className={`${kutmoqda ? 'r2-kutmoqda' : ''} ${x.holat === 'rad' ? 'r2-rad' : ''}`}>
      <td><b>{kunOy(x.sana)}</b></td>
      <td>{x.modda_nomi}{x.doimiy && <small className="r2-belgi">doimiy</small>}{x.kassadan && <small className="r2-belgi">kassadan</small>}</td>
      <td><span className="soz-matn xarajat-izoh"><span>{x.izoh || '—'}</span><small>{x.kiritgan || '—'}</small></span></td>
      <td className="ong">{kutmoqda && !x.kassadan
        ? <SummaInput value={summa} aria-label="Tasdiqlanadigan summa" className="r2-summa" onChange={(e) => setSumma(e.target.value)} />
        : <b className="xarajat-summa">−{guruhla(x.summa)}</b>}</td>
      <td>{kutmoqda ? <span className="soz-holat ogoh">kutilmoqda</span> : x.holat === 'rad' ? <span className="soz-holat qizil">Rad etilgan</span> : <span className="soz-mute">tasdiqlangan</span>}</td>
      <td className="r2-amallar"><div>
        {kutmoqda && (
          <>
            <button type="button" className="kichik" disabled={!x.kassadan && !(Number(summa) > 0)}
              onClick={() => bajar(() => xarajatQaror(x.id, 'tasdiq', x.kassadan ? undefined : Number(summa)), 'Tasdiqlandi.')}>Tasdiqlash</button>
            {/* kassadan to'langan pul chiqib bo'lgan — rad etilsa kiritgan xodimning kamomadi bo'ladi (tasdiq oynasi bilan) */}
            <button type="button" className="ikkinchi kichik" title={x.kassadan ? `Rad etilsa — ${x.kiritgan || 'xodim'} kamomadi` : undefined}
              onClick={() => (x.kassadan ? onRad() : bajar(() => xarajatQaror(x.id, 'rad'), 'Rad etildi.'))}>Rad etish</button>
          </>
        )}
        {x.holat !== 'rad' && <button type="button" className="havola" onClick={onTuzat}>Tuzatish</button>}
      </div></td>
    </tr>
  )
}

// Rahbar xatoni tuzatadi yoki xarajatni bekor qiladi. Kassadan to'langanida summa va sana o'zgarmaydi.
function XarajatTahrir({ x, moddalar, bajar }) {
  const [f, setF] = useState({ modda: x.modda, summa: x.summa, sana: x.sana, izoh: x.izoh || '' })
  const [bekorSurov, setBekorSurov] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const tana = () => ({
    modda: f.modda, izoh: f.izoh,
    ...(x.kassadan ? {} : { summa: Number(f.summa), sana: f.sana }),
  })
  return (
    <div className="stack">
      <label>Xarajat turi
        <select value={f.modda} onChange={set('modda')}>
          {!moddalar.some((m) => m.kod === x.modda) && <option value={x.modda}>{x.modda_nomi}</option>}
          {moddalar.map((m) => <option key={m.kod} value={m.kod}>{m.nomi}</option>)}
        </select>
      </label>
      {x.kassadan ? <p className="malumot">Kassadan to'langan: summa va sana o'zgartirilmaydi, bekor ham qilinmaydi.</p> : (
        <div className="libos-narxlar">
          <label>Summa, so'm<SummaInput value={f.summa} onChange={set('summa')} /></label>
          <label>Sana<input type="date" value={f.sana} onChange={set('sana')} /></label>
        </div>
      )}
      <label>Izoh<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
      <div className="qator">
        <button disabled={!x.kassadan && !(Number(f.summa) > 0)}
          onClick={() => bajar(() => xarajatTuzat(x.id, tana()), 'Xarajat tuzatildi.')}>Saqlash</button>
        {!x.kassadan && x.holat === 'tasdiqlandi' && (
          <button className="xavfli" onClick={() => setBekorSurov(true)}>Bekor qilish</button>
        )}
      </div>
      {bekorSurov && (
        <Tasdiq sarlavha="Xarajat bekor qilinsinmi?" tugma="Ha, bekor qilish"
          matn={`${x.modda_nomi}, ${som(x.summa)} — endi foydadan ayirilmaydi. Yozuv «rad etilgan» bo'lib qoladi; qaytarib bo'lmaydi.`}
          onYop={() => setBekorSurov(false)}
          onTasdiq={() => { setBekorSurov(false); bajar(() => xarajatBekor(x.id), 'Xarajat bekor qilindi.') }} />
      )}
    </div>
  )
}

function DoimiyQator({ d, holat, bajar }) {
  const [summa, setSumma] = useState(d.summa)
  const [izoh, setIzoh] = useState(d.izoh || '')
  const [ochiq, setOchiq] = useState(false)
  return (
    <div className={`tasdiq doimiy-q ${d.faol ? '' : 'bajarilgan'}`}>
      <div className="doimiy-q-bosh">
        <span className="soz-matn"><b>{d.modda_nomi}</b><small>{[d.izoh, d.filial_nomi, !d.faol && "o'chirilgan"].filter(Boolean).join(' · ') || 'har oy'}</small></span>
        <b className="doimiy-summa">{som(d.summa)}</b>
        {d.faol && <span className={`soz-holat ${holat[0]}`}>{holat[1]}</span>}
        <button type="button" className="havola" aria-expanded={ochiq} onClick={() => setOchiq(!ochiq)}>Tahrirlash</button>
      </div>
      {ochiq && (
        <div className="soz-tahrir">
          <div className="soz-tugmalar">
            <SummaInput value={summa} aria-label="Summa" onChange={(e) => setSumma(e.target.value)} />
            <input value={izoh} maxLength={300} placeholder="Izoh" aria-label="Izoh" onChange={(e) => setIzoh(e.target.value)} />
          </div>
          <div className="soz-tugmalar">
            <button className="kichik" disabled={!(Number(summa) > 0) || (Number(summa) === d.summa && izoh === (d.izoh || ''))}
              onClick={() => bajar(() => doimiyXarajatOzgartir(d.id, { summa: Number(summa), izoh }), 'Doimiy xarajat saqlandi.')}>Saqlash</button>
            <button className="ikkinchi kichik" onClick={() => bajar(() => doimiyXarajatOzgartir(d.id, { faol: !d.faol }), d.faol ? "O'chirildi." : 'Yoqildi.')}>
              {d.faol ? "O'chirish" : 'Yoqish'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ModdaQator({ m, bajar }) {
  const [nomi, setNomi] = useState(m.nomi)
  return (
    <div className={`tasdiq ${m.faol ? '' : 'bajarilgan'}`}>
      {!m.faol && <span className="malumot">nofaol</span>}
      <input value={nomi} maxLength={100} aria-label="Xarajat turi nomi" onChange={(e) => setNomi(e.target.value)} />
      <div className="qator">
        <button className="ikkinchi kichik" disabled={!nomi.trim() || nomi.trim() === m.nomi}
          onClick={() => bajar(() => moddaOzgartir(m.id, { nomi: nomi.trim() }), "Nomi o'zgartirildi.")}>Nomini saqlash</button>
        <button className="ikkinchi kichik" onClick={() => bajar(() => moddaOzgartir(m.id, { faol: !m.faol }), m.faol ? 'Nofaol qilindi.' : 'Faollashtirildi.')}>
          {m.faol ? 'Nofaol qilish' : 'Faollashtirish'}
        </button>
      </div>
    </div>
  )
}

// Majburiy maydonlar « *» bilan; tugma o'chiq bo'lsa ostida nima yetishmayotgani yoziladi (B-29)
function Forma({ moddalar, onYuborish, doimiy, fil = [], tugma = 'Xarajat kiritish' }) {
  const [f, setF] = useState(() => ({ modda: '', summa: '', izoh: '', sana: iso(new Date()), filial: '' }))
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const yetishmaydi = [!f.modda && 'Xarajat turi', !(Number(f.summa) > 0) && 'Summa'].filter(Boolean)
  const yubor = () => {
    const b = { modda: f.modda, summa: Number(f.summa), izoh: f.izoh }
    if (doimiy) { if (f.filial) b.filial = Number(f.filial) } else b.sana = f.sana
    return onYuborish(b).then((ok) => ok && setF({ ...f, summa: '', izoh: '' }))
  }
  return (
    <div className="stack">
      <label>Xarajat turi *
        <select value={f.modda} onChange={set('modda')} aria-label="Xarajat turi">
          <option value="">Tanlang</option>
          {moddalar.map((m) => <option key={m.kod} value={m.kod}>{m.nomi}</option>)}
        </select>
      </label>
      <div className="libos-narxlar">
        <label>Summa, so'm *<SummaInput value={f.summa} onChange={set('summa')} /></label>
        {!doimiy && <label>Sana<input type="date" value={f.sana} onChange={set('sana')} /></label>}
      </div>
      {doimiy && fil.length > 0 && (
        <label>Filial
          <select value={f.filial} onChange={set('filial')}>
            <option value="">Butun salon uchun (umumiy)</option>
            {fil.map((x) => <option key={x.id} value={x.id}>Filial: {x.nomi}</option>)}
          </select>
        </label>
      )}
      <label>Izoh<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
      <button className={doimiy ? 'ikkinchi' : undefined} disabled={yetishmaydi.length > 0} onClick={yubor}>{tugma}</button>
      {yetishmaydi.length > 0 && <p className="malumot r2-sabab">To'ldiring: {yetishmaydi.join(', ')}</p>}
    </div>
  )
}

// Xarajat turlari (avvalgi «moddalar»). Ichki «to'g'ridan-to'g'ri / operatsion» bo'linishi foyda hisobotida alohida
// qator bo'lib ko'rinmaydi — tanlovi UI dan olib tashlandi (yangi tur oddiy xarajat bo'ladi).
function ModdalarBloki({ moddalar, bajar }) {
  const [nomi, setNomi] = useState('')
  const oz = moddalar.filter((m) => !m.standart)
  return (
    <details className="blok amal">
      <summary>Xarajat turlari</summary>
      <div className="stack">
        <p className="malumot">Tayyor turlar: {moddalar.filter((m) => m.standart).map((m) => m.nomi).join(', ')}.</p>
        {oz.map((m) => <ModdaQator key={`${m.kod}-${m.nomi}`} m={m} bajar={bajar} />)}
        <label>Yangi xarajat turi<input value={nomi} maxLength={100} placeholder="masalan: Gul bezak" onChange={(e) => setNomi(e.target.value)} /></label>
        <button className="ikkinchi" disabled={!nomi.trim()}
          onClick={() => bajar(() => moddaQosh({ nomi, togridan: false }), "Xarajat turi qo'shildi.").then((ok) => ok && setNomi(''))}>Qo'shish</button>
      </div>
    </details>
  )
}

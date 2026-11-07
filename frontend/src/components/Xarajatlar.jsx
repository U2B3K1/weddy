import { useCallback, useEffect, useState } from 'react'
import {
  doimiyXarajatOzgartir, doimiyXarajatQosh, doimiyXarajatlar, filiallar, hisobot, moddaOzgartir, moddaQosh, som, xarajatModdalari,
  xarajatBekor, xarajatQaror, xarajatTuzat, xarajatYarat, xarajatlar, xatoMatni,
  sanaMatni,
} from '../api'
import NavIkona from './NavIkona'
import Oyna from './Oyna'
import OyTanlash from './OyTanlash'
import SummaInput from './SummaInput'
import Tasdiq from './Tasdiq'

const HOLAT = { kutilmoqda: ['Tasdiq kutmoqda', 'vaqtinchalik'], tasdiqlandi: ['Tasdiqlangan', 'bron'], rad: ['Rad etilgan', 'qarz'] }
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const oyOraligi = (oy) => { const [y, m] = oy.split('-').map(Number); return [`${oy}-01`, iso(new Date(y, m, 0))] }
const oldingiOy = (oy) => { const [y, m] = oy.split('-').map(Number); const d = new Date(y, m - 2, 1); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}` }

// Rahbar uchun xarajatlar (4.13): oy bo'yicha jadval (tasdiq kutayotganlar tepada), «+ Xarajat» oynasi,
// turlar bo'yicha «bu oy / o'tgan oy» jamlanmasi («pul qayerga ketyapti?»), doimiy oylik xarajatlar (FT-13.3) va turlari (FT-13.1).
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
  const kutayotgan = royxat.filter((x) => x.holat === 'kutilmoqda').length
  const tasdiqlangan = royxat.filter((x) => x.holat === 'tasdiqlandi').reduce((s, x) => s + x.summa, 0)

  return (
    <div className="stack">
      <section className="blok jadval-panel r2-xarajat">
        <div className="jadval-asboblar">
          <h3 className="panel-nom">Xarajatlar</h3>
          <OyTanlash value={oy} onChange={setOy} />
          <button type="button" className="kichik r2-oxirgi" onClick={() => setOyna('yangi')}><NavIkona nom="qosh" className="tugma-ikon" />Xarajat</button>
        </div>
        {xabar.matn && <p className={`${xabar.turi === 'xato' ? 'xato' : 'malumot'} jadval-bosh r2-xabar`} role="status">{xabar.matn}</p>}
        {royxat.length === 0 ? <p className="malumot jadval-bosh">Bu oyda xarajat yo'q.</p> : (
          <div className="jadval-ora">
            <table className="zakaz-jadval r2-xarajat-jadval">
              <thead>
                <tr><th>Sana</th><th>Turi</th><th className="ong">Summa</th><th className="tor-yashir">Kim kiritdi</th><th>Holat</th><th aria-label="Amallar" /></tr>
              </thead>
              <tbody>
                {tartib.map((x) => (
                  <XarajatQator key={`${x.id}-${x.summa}-${x.holat}`} x={x} bajar={bajar}
                    onTuzat={() => setOyna(x)} onRad={() => setRadSurov(x)} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        {royxat.length > 0 && (
          <p className="r2-jami jadval-bosh">
            <span>Tasdiqlangan jami: <b>{som(tasdiqlangan)}</b></span>
            {kutayotgan > 0 && <span className="malumot"> · {kutayotgan} ta tasdiq kutmoqda (foydaga hali kirmagan)</span>}
          </p>
        )}
      </section>

      {turlar && turlar.length > 0 && (
        <section className="blok jadval-panel">
          <div className="jadval-asboblar"><h3 className="panel-nom">Turlar bo'yicha</h3></div>
          <div className="jadval-ora">
            <table className="hisobot r2-turlar">
              <thead><tr><th>Xarajat turi</th><th className="ong">{OyTanlash.nomi(oy)}</th><th className="ong">{OyTanlash.nomi(oldingiOy(oy))}</th></tr></thead>
              <tbody>
                {turlar.map((t) => (
                  <tr key={t.nom}><td>{t.nom}</td><td className="ong">{som(t.bu)}</td><td className="ong">{t.otgan ? som(t.otgan) : '—'}</td></tr>
                ))}
              </tbody>
              <tfoot><tr><td>Jami</td><td className="ong">{som(turlar.reduce((s, t) => s + t.bu, 0))}</td><td className="ong">{som(turlar.reduce((s, t) => s + t.otgan, 0))}</td></tr></tfoot>
            </table>
          </div>
          <p className="malumot jadval-bosh r2-izoh">Faqat tasdiqlangan xarajatlar — foydadan ayirilgan summa.</p>
        </section>
      )}

      <details className="blok amal">
        <summary>Doimiy oylik xarajatlar ({doimiy.filter((d) => d.faol).length})</summary>
        <div className="stack">
          <p className="malumot">Har oy boshida shu ro'yxatdan qoralama yaratiladi — siz summani tekshirib tasdiqlaysiz yoki rad etasiz.</p>
          {doimiy.map((d) => <DoimiyQator key={`${d.id}-${d.summa}-${d.izoh}`} d={d} bajar={bajar} />)}
          <Forma moddalar={faol} doimiy fil={fil} tugma="Doimiy xarajat qo'shish"
            onYuborish={(b) => bajar(() => doimiyXarajatQosh(b), "Doimiy xarajat qo'shildi.")} />
        </div>
      </details>

      <ModdalarBloki moddalar={moddalar} bajar={bajar} />

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

function XarajatQator({ x, bajar, onTuzat, onRad }) {
  const [summa, setSumma] = useState(x.summa)
  const [nom, sinf] = HOLAT[x.holat] || [x.holat, 'qaytarildi']
  const kutmoqda = x.holat === 'kutilmoqda'
  return (
    <tr className={`${kutmoqda ? 'r2-kutmoqda' : ''} ${x.holat === 'rad' ? 'r2-rad' : ''}`}>
      <td>
        <span className="zakaz-nom">
          <b>{sanaMatni(x.sana)}</b>
          {x.izoh && <small>{x.izoh}</small>}
        </span>
      </td>
      <td>{x.modda_nomi}{x.doimiy && <small className="r2-belgi">doimiy</small>}{x.kassadan && <small className="r2-belgi">kassadan</small>}</td>
      <td className="ong">{kutmoqda && !x.kassadan
        ? <SummaInput value={summa} aria-label="Tasdiqlanadigan summa" className="r2-summa" onChange={(e) => setSumma(e.target.value)} />
        : <b>{som(x.summa)}</b>}</td>
      <td className="tor-yashir">{x.kiritgan || '—'}</td>
      <td><span className={`holat ${sinf}`}>{nom}</span></td>
      <td className="r2-amallar"><div>
        {kutmoqda && (
          <>
            <button type="button" className="kichik" disabled={!x.kassadan && !(Number(summa) > 0)}
              onClick={() => bajar(() => xarajatQaror(x.id, 'tasdiq', x.kassadan ? undefined : Number(summa)), 'Tasdiqlandi.')}>Tasdiqlash</button>
            {/* kassadan to'langan pul chiqib bo'lgan — rad etilsa kiritgan xodimning kamomadi bo'ladi (tasdiq oynasi bilan) */}
            <button type="button" className="ikkinchi kichik"
              onClick={() => (x.kassadan ? onRad() : bajar(() => xarajatQaror(x.id, 'rad'), 'Rad etildi.'))}>
              {x.kassadan ? `Rad etish — ${x.kiritgan || 'xodim'} kamomadi` : 'Rad etish'}
            </button>
          </>
        )}
        {x.holat !== 'rad' && <button type="button" className="ikkinchi kichik" onClick={onTuzat}>Tuzatish</button>}
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

function DoimiyQator({ d, bajar }) {
  const [summa, setSumma] = useState(d.summa)
  const [izoh, setIzoh] = useState(d.izoh || '')
  return (
    <div className={`tasdiq ${d.faol ? '' : 'bajarilgan'}`}>
      <span><b>{d.modda_nomi}</b> · {som(d.summa)}{d.izoh ? ` · ${d.izoh}` : ''}{d.faol ? '' : " · o'chirilgan"}</span>
      <div className="qator">
        <SummaInput value={summa} aria-label="Summa" onChange={(e) => setSumma(e.target.value)} />
        <input value={izoh} maxLength={300} placeholder="Izoh" aria-label="Izoh" onChange={(e) => setIzoh(e.target.value)} />
      </div>
      <div className="qator">
        <button className="ikkinchi kichik" disabled={!(Number(summa) > 0) || (Number(summa) === d.summa && izoh === (d.izoh || ''))}
          onClick={() => bajar(() => doimiyXarajatOzgartir(d.id, { summa: Number(summa), izoh }), 'Doimiy xarajat saqlandi.')}>Saqlash</button>
        <button className="ikkinchi kichik" onClick={() => bajar(() => doimiyXarajatOzgartir(d.id, { faol: !d.faol }), d.faol ? "O'chirildi." : 'Yoqildi.')}>
          {d.faol ? "O'chirish" : 'Yoqish'}
        </button>
      </div>
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

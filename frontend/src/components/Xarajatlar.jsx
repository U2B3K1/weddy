import { useCallback, useEffect, useState } from 'react'
import {
  doimiyXarajatOzgartir, doimiyXarajatQosh, doimiyXarajatlar, filiallar, moddaOzgartir, moddaQosh, som, xarajatModdalari,
  xarajatBekor, xarajatQaror, xarajatTuzat, xarajatYarat, xarajatlar, xatoMatni,
  sanaMatni,
} from '../api'
import SummaInput from './SummaInput'

const HOLAT = { kutilmoqda: 'tasdiq kutmoqda', tasdiqlandi: 'tasdiqlangan', rad: 'rad etilgan' }
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

// Rahbar uchun xarajatlar (4.13): kiritish, oy bo'yicha ro'yxat, doimiy oylik xarajatlar (FT-13.3) va moddalar (FT-13.1).
export default function Xarajatlar() {
  const [oy, setOy] = useState(() => iso(new Date()).slice(0, 7))
  const [royxat, setRoyxat] = useState([])
  const [moddalar, setModdalar] = useState([])
  const [doimiy, setDoimiy] = useState([])
  const [fil, setFil] = useState([])
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(async () => {
    const [a, b, c] = await Promise.all([xarajatlar({ oy }), xarajatModdalari(true), doimiyXarajatlar()])
    setRoyxat(a); setModdalar(b); setDoimiy(c)
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
  const tasdiqlangan = royxat.filter((x) => x.holat === 'tasdiqlandi').reduce((s, x) => s + x.summa, 0)

  return (
    <details className="blok amal" open>
      <summary>Xarajatlar</summary>
      <div className="stack">
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
        <Forma moddalar={faol} onYuborish={(b) => bajar(() => xarajatYarat(b), 'Xarajat yozildi.')} />

        <input type="month" value={oy} onChange={(e) => e.target.value && setOy(e.target.value)} aria-label="Oy" />
        {royxat.length === 0 && <p className="malumot">Bu oyda xarajat yo'q.</p>}
        {royxat.map((x) => <Qator key={`${x.id}-${x.summa}-${x.sana}-${x.modda}-${x.izoh}`} x={x} bajar={bajar} moddalar={faol} />)}
        {royxat.length > 0 && <p><b>Tasdiqlangan jami: {som(tasdiqlangan)}</b></p>}

        <details className="amal">
          <summary>Doimiy oylik xarajatlar ({doimiy.filter((d) => d.faol).length})</summary>
          <div className="stack">
            <p className="malumot">Har oy boshida shu ro'yxatdan qoralama yaratiladi — siz summani tekshirib tasdiqlaysiz yoki rad etasiz.</p>
            {doimiy.map((d) => <DoimiyQator key={`${d.id}-${d.summa}-${d.izoh}`} d={d} bajar={bajar} />)}
            <Forma moddalar={faol} doimiy fil={fil} tugma="Doimiy xarajat qo'shish"
              onYuborish={(b) => bajar(() => doimiyXarajatQosh(b), "Doimiy xarajat qo'shildi.")} />
          </div>
        </details>

        <ModdalarBloki moddalar={moddalar} bajar={bajar} />
      </div>
    </details>
  )
}

function Qator({ x, bajar, moddalar }) {
  const [summa, setSumma] = useState(x.summa)
  return (
    <div className={`tasdiq ${x.holat === 'rad' ? 'bajarilgan' : ''}`}>
      <span>
        {sanaMatni(x.sana)} · <b>{x.modda_nomi}</b> · {som(x.summa)} · {HOLAT[x.holat]}
        {x.doimiy && ' · doimiy'}{x.kassadan && ' · kassadan'}{x.kiritgan ? ` · ${x.kiritgan}` : ''}{x.izoh ? ` · ${x.izoh}` : ''}
      </span>
      {x.holat === 'kutilmoqda' && (
        <div className="qator">
          {!x.kassadan && <SummaInput value={summa} aria-label="Summa" onChange={(e) => setSumma(e.target.value)} />}
          <button className="kichik" onClick={() => bajar(() => xarajatQaror(x.id, 'tasdiq', x.kassadan ? undefined : Number(summa)), 'Tasdiqlandi.')}>Tasdiqlash</button>
          {/* kassadan to'langan pul chiqib bo'lgan — rad etilmaydi, faqat tasdiqlanadi */}
          {!x.kassadan && <button className="ikkinchi kichik" onClick={() => bajar(() => xarajatQaror(x.id, 'rad'), 'Rad etildi.')}>Rad etish</button>}
        </div>
      )}
      {x.holat !== 'rad' && <XarajatTahrir x={x} moddalar={moddalar} bajar={bajar} />}
    </div>
  )
}

// Rahbar xatoni tuzatadi yoki xarajatni bekor qiladi. Kassadan to'langanida summa va sana o'zgarmaydi.
function XarajatTahrir({ x, moddalar, bajar }) {
  const [f, setF] = useState({ modda: x.modda, summa: x.summa, sana: x.sana, izoh: x.izoh || '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const tana = () => ({
    modda: f.modda, izoh: f.izoh,
    ...(x.kassadan ? {} : { summa: Number(f.summa), sana: f.sana }),
  })
  return (
    <details className="amal">
      <summary>Tuzatish</summary>
      <div className="stack">
        <select value={f.modda} onChange={set('modda')} aria-label="Modda">
          {!moddalar.some((m) => m.kod === x.modda) && <option value={x.modda}>{x.modda_nomi}</option>}
          {moddalar.map((m) => <option key={m.kod} value={m.kod}>{m.nomi}</option>)}
        </select>
        {x.kassadan ? <p className="malumot">Kassadan to'langan: summa va sana o'zgartirilmaydi, bekor ham qilinmaydi.</p> : (
          <>
            <label>Summa, so'm<SummaInput value={f.summa} onChange={set('summa')} /></label>
            <label>Sana<input type="date" value={f.sana} onChange={set('sana')} /></label>
          </>
        )}
        <label>Izoh<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
        <div className="qator">
          <button className="ikkinchi kichik" disabled={!x.kassadan && !(Number(f.summa) > 0)}
            onClick={() => bajar(() => xarajatTuzat(x.id, tana()), 'Xarajat tuzatildi.')}>Saqlash</button>
          {!x.kassadan && x.holat === 'tasdiqlandi' && (
            <button className="xavfli kichik" onClick={() => bajar(() => xarajatBekor(x.id), 'Xarajat bekor qilindi.')}>Bekor qilish</button>
          )}
        </div>
      </div>
    </details>
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
      <span>{m.togridan ? "to'g'ridan-to'g'ri" : 'operatsion'}{m.faol ? '' : ' · nofaol'}</span>
      <input value={nomi} maxLength={100} aria-label="Modda nomi" onChange={(e) => setNomi(e.target.value)} />
      <div className="qator">
        <button className="ikkinchi kichik" disabled={!nomi.trim() || nomi.trim() === m.nomi}
          onClick={() => bajar(() => moddaOzgartir(m.id, { nomi: nomi.trim() }), "Modda nomi o'zgartirildi.")}>Nomini saqlash</button>
        <button className="ikkinchi kichik" onClick={() => bajar(() => moddaOzgartir(m.id, { faol: !m.faol }), m.faol ? 'Nofaol qilindi.' : 'Faollashtirildi.')}>
          {m.faol ? 'Nofaol qilish' : 'Faollashtirish'}
        </button>
      </div>
    </div>
  )
}

function Forma({ moddalar, onYuborish, doimiy, fil = [], tugma = 'Xarajat kiritish' }) {
  const [f, setF] = useState(() => ({ modda: '', summa: '', izoh: '', sana: iso(new Date()), filial: '' }))
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const yubor = () => {
    const b = { modda: f.modda, summa: Number(f.summa), izoh: f.izoh }
    if (doimiy) { if (f.filial) b.filial = Number(f.filial) } else b.sana = f.sana
    return onYuborish(b).then((ok) => ok && setF({ ...f, summa: '', izoh: '' }))
  }
  return (
    <div className="stack">
      <select value={f.modda} onChange={set('modda')} aria-label="Modda">
        <option value="">Moddani tanlang</option>
        {moddalar.map((m) => <option key={m.kod} value={m.kod}>{m.nomi}</option>)}
      </select>
      <label>Summa, so'm<SummaInput value={f.summa} onChange={set('summa')} /></label>
      {!doimiy && <label>Sana<input type="date" value={f.sana} onChange={set('sana')} /></label>}
      {doimiy && fil.length > 0 && (
        <select value={f.filial} onChange={set('filial')} aria-label="Filial">
          <option value="">Butun salon uchun (umumiy)</option>
          {fil.map((x) => <option key={x.id} value={x.id}>Filial: {x.nomi}</option>)}
        </select>
      )}
      <label>Izoh<input value={f.izoh} maxLength={300} onChange={set('izoh')} /></label>
      <button className="ikkinchi" disabled={!f.modda || !(Number(f.summa) > 0)} onClick={yubor}>{tugma}</button>
    </div>
  )
}

function ModdalarBloki({ moddalar, bajar }) {
  const [nomi, setNomi] = useState('')
  const [togridan, setTogridan] = useState(false)
  const oz = moddalar.filter((m) => !m.standart)
  return (
    <details className="amal">
      <summary>Xarajat moddalari</summary>
      <div className="stack">
        <p className="malumot">Standart: {moddalar.filter((m) => m.standart).map((m) => m.nomi).join(', ')}.</p>
        {oz.map((m) => <ModdaQator key={`${m.kod}-${m.nomi}`} m={m} bajar={bajar} />)}
        <label>Yangi modda nomi<input value={nomi} maxLength={100} onChange={(e) => setNomi(e.target.value)} /></label>
        <label className="qator">
          <input type="checkbox" checked={togridan} onChange={(e) => setTogridan(e.target.checked)} />
          To'g'ridan-to'g'ri xarajat (libosga bog'liq: tozalash, ta'mir kabi)
        </label>
        <button className="ikkinchi" disabled={!nomi.trim()}
          onClick={() => bajar(() => moddaQosh({ nomi, togridan }), "Modda qo'shildi.").then((ok) => ok && setNomi(''))}>Modda qo'shish</button>
        <p className="malumot">Modda turi keyin o'zgartirilmaydi — aks holda o'tgan oylar hisoboti o'zgarib ketadi.</p>
      </div>
    </details>
  )
}

import { useCallback, useEffect, useState } from 'react'
import {
  aksessuarlar, kategoriyalar, promokodOzgartir, promokodYarat, promokodlar, salonchilar, som, xatoMatni,
} from '../api'
import SummaInput from '../components/SummaInput'

const HOLAT = {
  faol: 'Faol', rejalashtirilgan: 'Rejalashtirilgan', muddati_otgan: "Muddati o'tgan", limiti_tugagan: 'Limiti tugagan',
  toxtatilgan: "To'xtatilgan", arxiv: 'Arxiv',
}
const KUNLAR = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']

const qiymatMatni = (p) => {
  if (p.chegirma_turi === 'foiz') return `${p.qiymat}%`
  if (p.chegirma_turi === 'summa') return som(p.qiymat)
  return `bepul: ${p.aksessuar || 'aksessuar'}`
}

// 4.18: promokodlar — faqat rahbar yaratadi va boshqaradi; har kod bo'yicha statistika (FT-21.11).
export default function Promokodlar() {
  const [royxat, setRoyxat] = useState([])
  const [filtr, setFiltr] = useState('faol')
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(() => promokodlar().then(setRoyxat), [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try {
      const r = await fn()
      setXabar({ turi: 'ok', matn: typeof ok === 'function' ? ok(r) : ok })
      await yukla()
      return true
    } catch (e) { setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false }
  }

  const korinadigan = royxat.filter((p) => (filtr === 'hammasi' ? p.holat !== 'arxiv' : p.holat === filtr))

  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      <PromokodForma onYuborish={(b) => bajar(() => promokodYarat(b),
        (r) => (r.kodlar.length === 1 ? `Kod yaratildi: ${r.kodlar[0]}` : `${r.kodlar.length} ta kod yaratildi: ${r.kodlar.join(', ')}`))} />
      <select value={filtr} onChange={(e) => setFiltr(e.target.value)}>
        <option value="hammasi">Hammasi (arxivsiz)</option>
        {Object.entries(HOLAT).map(([k, nom]) => <option key={k} value={k}>{nom}</option>)}
      </select>
      {korinadigan.length === 0 && <p className="malumot">Bu holatda kod yo'q.</p>}
      {korinadigan.map((p) => (
        <div key={p.id} className={`blok stack ${['faol', 'rejalashtirilgan'].includes(p.holat) ? '' : 'bajarilgan'}`}>
          <div>
            <b>{p.kod}</b> · {qiymatMatni(p)} · {HOLAT[p.holat]}
            {p.tugashiga_kun !== null && p.holat === 'faol' && ` · tugashiga ${p.tugashiga_kun} kun`}
          </div>
          <p className="malumot">
            {p.turi === 'bir_martalik' ? 'Bir martalik' : `Ko'p martalik${p.limit ? `, limit ${p.limit}` : ''}`}
            {p.boshlanish || p.tugash ? ` · ${p.boshlanish || '…'} – ${p.tugash || 'muddatsiz'}` : ' · muddatsiz'}
            {p.min_summa ? ` · min. ${som(p.min_summa)}` : ''}
            {p.maks_chegirma ? ` · maks. ${som(p.maks_chegirma)}` : ''}
            {p.kategoriyalar.length > 0 ? ` · ${p.kategoriyalar.join(', ')}` : ''}
            {p.hafta_kunlari ? ` · ${p.hafta_kunlari.map((k) => KUNLAR[k]).join(', ')}` : ''}
            {p.salonchi ? ` · salonchi: ${p.salonchi}` : ''}
          </p>
          <p className="malumot">
            Ishlatilgan: {p.ishlatilgan} · chegirma: {som(p.chegirma_jami)} · tushum: {som(p.tushum)}
            {' '}· yangi mijoz: {p.yangi_mijozlar} · qaytgan: {p.qaytgan_mijozlar}
            {p.sotuvchilar.length > 0 && ` · ${p.sotuvchilar.join(', ')}`}
          </p>
          {p.izoh && <p className="malumot">{p.izoh}</p>}
          <div className="qator">
            {p.holat === 'toxtatilgan' || p.holat === 'arxiv' ? (
              <button className="ikkinchi kichik" onClick={() => bajar(() => promokodOzgartir(p.id, { holat: 'faol' }), 'Kod yoqildi.')}>Yoqish</button>
            ) : (
              <button className="ikkinchi kichik" onClick={() => bajar(() => promokodOzgartir(p.id, { holat: 'toxtatilgan' }), "Kod to'xtatildi.")}>To'xtatish</button>
            )}
            {p.holat !== 'arxiv' && (
              <button className="ikkinchi kichik" onClick={() => bajar(() => promokodOzgartir(p.id, { holat: 'arxiv' }), 'Kod arxivlandi.')}>Arxivlash</button>
            )}
            <Uzaytirish p={p} bajar={bajar} />
          </div>
        </div>
      ))}
    </div>
  )
}

function Uzaytirish({ p, bajar }) {
  const [sana, setSana] = useState('')
  const [limit, setLimit] = useState('')
  if (p.holat === 'arxiv') return null
  return (
    <>
      {p.turi !== 'bir_martalik' && (
        <>
          <input type="number" min="1" value={limit} placeholder={p.limit ? `Limit: ${p.limit}` : 'Limit'} aria-label="Yangi limit"
            onChange={(e) => setLimit(e.target.value)} />
          <button className="ikkinchi kichik" disabled={!(Number(limit) > 0)}
            onClick={() => bajar(() => promokodOzgartir(p.id, { limit: Number(limit) }), 'Limit yangilandi.').then((ok) => ok && setLimit(''))}>
            Limitni o'zgartirish
          </button>
        </>
      )}
      <input type="date" value={sana} min={p.boshlanish || undefined} onChange={(e) => setSana(e.target.value)} aria-label="Yangi tugash sanasi" />
      <button className="ikkinchi kichik" disabled={!sana}
        onClick={() => bajar(() => promokodOzgartir(p.id, { tugash: sana }), 'Muddat yangilandi.').then((ok) => ok && setSana(''))}>
        Muddatni o'zgartirish
      </button>
    </>
  )
}

const BOSH = { kod: '', turi: 'kop_martalik', chegirma_turi: 'foiz', qiymat: '', muddat: '', manba: 'aksiya', soni: 1, bir_mijozga: 1 }

function PromokodForma({ onYuborish }) {
  const [f, setF] = useState(BOSH)
  const [kats, setKats] = useState([])
  const [aks, setAks] = useState([])
  const [sal, setSal] = useState([])
  const [tanKat, setTanKat] = useState([])
  const [kunlar, setKunlar] = useState([])
  useEffect(() => {
    kategoriyalar().then((k) => setKats(k.filter((x) => x.turi === 'libos'))).catch(() => {})
    aksessuarlar().then(setAks).catch(() => {})
    salonchilar().then(setSal).catch(() => {})
  }, [])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const almash = (royxat, setRoyxat, v) => setRoyxat(royxat.includes(v) ? royxat.filter((x) => x !== v) : [...royxat, v])
  const kop = Number(f.soni) > 1
  const tayyor = f.chegirma_turi === 'aksessuar' ? !!f.aksessuar : Number(f.qiymat) > 0

  const yubor = () => {
    const b = {
      kod: kop ? '' : f.kod, prefiks: kop ? f.kod : '', soni: Number(f.soni) || 1,
      turi: f.turi, chegirma_turi: f.chegirma_turi, qiymat: f.chegirma_turi === 'aksessuar' ? 0 : Number(f.qiymat),
      manba: f.manba, izoh: f.izoh || '', bir_mijozga: Number(f.bir_mijozga) || 1, kategoriyalar: tanKat,
    }
    if (f.chegirma_turi === 'aksessuar') b.aksessuar = Number(f.aksessuar)
    if (f.boshlanish) b.boshlanish = f.boshlanish
    if (['1', '3', '6'].includes(f.muddat)) b.muddat_oy = Number(f.muddat)
    else if (f.muddat === 'sana' && f.tugash) b.tugash = f.tugash
    for (const k of ['limit', 'min_summa', 'maks_chegirma', 'salonchi']) if (f[k]) b[k] = Number(f[k])
    if (kunlar.length > 0) b.hafta_kunlari = [...kunlar].sort()
    return onYuborish(b).then((ok) => { if (ok) { setF(BOSH); setTanKat([]); setKunlar([]) } })
  }

  return (
    <details className="blok amal">
      <summary>Promokod yaratish</summary>
      <div className="stack">
        <label>Nechta kod
          <input type="number" min="1" max="500" value={f.soni} onChange={set('soni')} />
        </label>
        <label>{kop ? 'Kod boshi (ixtiyoriy, masalan TOY-)' : "Kod (bo'sh qoldirilsa tizim o'zi yaratadi)"}
          <input value={f.kod} maxLength={kop ? 10 : 30} onChange={(e) => setF({ ...f, kod: e.target.value.toUpperCase() })} />
        </label>
        {kop ? <p className="malumot">Bir yo'la yaratilgan kodlarning har biri noyob va bir martalik bo'ladi.</p> : (
          <select value={f.turi} onChange={set('turi')}>
            <option value="kop_martalik">Ko'p martalik</option>
            <option value="bir_martalik">Bir martalik</option>
          </select>
        )}
        <select value={f.chegirma_turi} onChange={set('chegirma_turi')}>
          <option value="foiz">Foiz chegirma</option>
          <option value="summa">Summa chegirma (so'm)</option>
          <option value="aksessuar">Bepul aksessuar</option>
        </select>
        {f.chegirma_turi === 'aksessuar' ? (
          <select value={f.aksessuar || ''} onChange={set('aksessuar')}>
            <option value="">Aksessuarni tanlang</option>
            {aks.map((a) => <option key={a.id} value={a.id}>{a.nomi}</option>)}
          </select>
        ) : (
          <label>{f.chegirma_turi === 'foiz' ? 'Foiz (1–100)' : "Summa, so'm"}
            {f.chegirma_turi === 'foiz'
              ? <input type="number" min="1" max="100" value={f.qiymat} onChange={set('qiymat')} />
              : <SummaInput value={f.qiymat} onChange={set('qiymat')} />}
          </label>
        )}
        <label>Boshlanish (bo'sh — bugundan)
          <input type="date" value={f.boshlanish || ''} onChange={set('boshlanish')} />
        </label>
        <select value={f.muddat} onChange={set('muddat')}>
          <option value="">Muddatsiz</option>
          <option value="1">1 oy</option><option value="3">3 oy</option><option value="6">6 oy</option>
          <option value="sana">Tugash sanasini tanlash</option>
        </select>
        {f.muddat === 'sana' && <input type="date" value={f.tugash || ''} min={f.boshlanish || undefined} onChange={set('tugash')} aria-label="Tugash sanasi" />}
        {!kop && f.turi === 'kop_martalik' && (
          <div className="qator keng">
            <label>Umumiy limit<input type="number" min="1" placeholder="cheksiz" value={f.limit || ''} onChange={set('limit')} /></label>
            <label>Bitta mijozga<input type="number" min="1" value={f.bir_mijozga} onChange={set('bir_mijozga')} /></label>
          </div>
        )}
        <div className="qator keng">
          <label>Minimal summa<SummaInput value={f.min_summa || ''} onChange={set('min_summa')} /></label>
          <label>Maks. chegirma<SummaInput value={f.maks_chegirma || ''} onChange={set('maks_chegirma')} /></label>
        </div>
        {kats.length > 0 && (
          <fieldset className="guruh stack">
            <legend>Faqat shu kategoriyalar (belgilanmasa — hammasi)</legend>
            {kats.map((k) => (
              <label key={k.id} className="qator">
                <input type="checkbox" checked={tanKat.includes(k.id)} onChange={() => almash(tanKat, setTanKat, k.id)} />{k.nomi}
              </label>
            ))}
          </fieldset>
        )}
        <fieldset className="guruh">
          <legend>Olib ketish kuni (belgilanmasa — istalgan kun)</legend>
          <div className="qator kunlar">
            {KUNLAR.map((nom, i) => (
              <label key={nom}><input type="checkbox" checked={kunlar.includes(i)} onChange={() => almash(kunlar, setKunlar, i)} />{nom}</label>
            ))}
          </div>
        </fieldset>
        <select value={f.salonchi || ''} onChange={set('salonchi')}>
          <option value="">Salonchiga bog'lanmagan</option>
          {sal.map((s) => <option key={s.id} value={s.id}>Salonchi: {s.ism}</option>)}
        </select>
        {!f.salonchi && (
          <select value={f.manba} onChange={set('manba')}>
            <option value="aksiya">Manba: aksiya</option>
            <option value="instagram">Manba: Instagram</option>
            <option value="telegram">Manba: Telegram</option>
          </select>
        )}
        <label>Izoh<input value={f.izoh || ''} maxLength={300} onChange={set('izoh')} /></label>
        <button disabled={!tayyor} onClick={yubor}>Yaratish</button>
      </div>
    </details>
  )
}

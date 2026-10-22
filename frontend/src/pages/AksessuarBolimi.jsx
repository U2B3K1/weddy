import { useCallback, useEffect, useRef, useState } from 'react'
import Manekin from '../components/Manekin'
import {
  aksessuarManekinOchir, aksessuarManekinSaqla, aksessuarManekinYukla, aksessuarOzgartir, aksessuarTafsilot, aksessuarTasdiq, aksessuarYarat, aksessuarlar, donaFilial, donaHolati, filiallar, donaTamirTugat, donaTamirga, donalarQosh,
  kategoriyalar, som, xatoMatni,
} from '../api'

const DONA_HOLAT = { bosh: "Bo'sh", tamirda: "Ta'mirda", yoqolgan: "Yo'qolgan", arxiv: 'Arxiv' }

// 4.4: aksessuarlar faqat ijaraga; har bir dona alohida raqamli yorliq bilan hisobga olinadi.
export default function AksessuarBolimi({ rahbar }) {
  const [royxat, setRoyxat] = useState([])
  const [kats, setKats] = useState([])
  const [ochiq, setOchiq] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(async () => {
    const [a, k] = await Promise.all([aksessuarlar(), kategoriyalar()])
    setRoyxat(a); setKats(k.filter((x) => x.turi === 'aksessuar'))
  }, [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }

  const kutayotgan = royxat.filter((a) => a.holat === 'tasdiq_kutilmoqda')

  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {kats.length === 0 && (
        <p className="ogohlantirish">Aksessuar kategoriyasi yo'q{rahbar ? ": «Libosler» bo'limida «Kategoriya qo'shish» orqali turi «aksessuar» bo'lgan kategoriya yarating." : '. Rahbar kategoriya yaratishi kerak.'}</p>
      )}

      {rahbar && kutayotgan.length > 0 && (
        <section className="blok ogohlantirish-blok">
          <h3>Tasdiq kutmoqda ({kutayotgan.length})</h3>
          {kutayotgan.map((a) => (
            <Tasdiq key={a.id} a={a}
              onYuborish={(b) => bajar(() => aksessuarTasdiq(a.id, b), `${a.nomi} tasdiqlandi.`)} />
          ))}
        </section>
      )}

      {kats.length > 0 && (
        <Forma kats={kats} rahbar={rahbar}
          onYuborish={(b) => bajar(() => aksessuarYarat(b), rahbar ? "Aksessuar qo'shildi." : "Aksessuar rahbar tasdig'iga yuborildi.")} />
      )}

      {royxat.filter((a) => a.holat !== 'tasdiq_kutilmoqda').map((a) => (
        <div key={a.id} className="blok">
          <button className="qator-btn" onClick={() => setOchiq(ochiq === a.id ? null : a.id)}>
            <span><b>{a.kod}</b> {a.nomi} · {a.kategoriya}</span>
            <span>{som(a.ijara_narxi)} · {a.yaroqli_donalar}/{a.donalar_soni} dona{a.holat === 'arxiv' ? ' · arxiv' : ''}</span>
          </button>
          {ochiq === a.id && <Tafsilot id={a.id} rahbar={rahbar} bajar={bajar} />}
        </div>
      ))}
      {royxat.length === 0 && <p className="malumot">Aksessuar yo'q.</p>}
    </div>
  )
}

function Tafsilot({ id, rahbar, bajar }) {
  const [a, setA] = useState(null)
  const [narx, setNarx] = useState('')
  const [soni, setSoni] = useState('1')
  const yukla = useCallback(() => aksessuarTafsilot(id).then((d) => { setA(d); setNarx(d.ijara_narxi) }), [id])
  useEffect(() => { yukla() }, [yukla])
  const amal = async (fn, ok) => { const r = await bajar(fn, ok); if (r) await yukla(); return r }
  const fayl = useRef(null)
  const [fil, setFil] = useState([])
  useEffect(() => { filiallar().then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  const [manekinOyna, setManekinOyna] = useState(false)
  if (!a) return <p className="malumot">Yuklanmoqda…</p>
  return (
    <div className="stack" style={{ marginTop: 10 }}>
      <div className="dona-tor">
        {a.donalar.map((d) => (
          <span key={d.id} className={`dona ${d.holat !== 'bosh' ? 'dona-yaroqsiz' : ''}`}>
            {d.yorliq}
            {rahbar ? (
              // Ta'mirga berish va undan qaytarish faqat pastdagi «Ta'mir» bo'limi orqali (xarajat va jurnal yoziladi)
              <select value={d.holat} disabled={d.holat === 'tamirda'} title={d.holat === 'tamirda' ? "Avval ta'mirni tugating" : undefined}
                onChange={(e) => amal(() => donaHolati(d.id, e.target.value), `${d.yorliq}: holat o'zgardi.`)}>
                {Object.entries(DONA_HOLAT).filter(([k]) => k !== 'tamirda' || d.holat === 'tamirda')
                  .map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            ) : <small>{DONA_HOLAT[d.holat]}</small>}
            {fil.length > 0 && (rahbar ? (
              <select value={d.filial || ''} aria-label={`${d.yorliq} filiali`}
                onChange={(e) => amal(() => donaFilial(d.id, e.target.value ? Number(e.target.value) : null), `${d.yorliq}: filial saqlandi.`)}>
                <option value="">filialsiz</option>
                {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
              </select>
            ) : d.filial && <small>{fil.find((f) => f.id === d.filial)?.nomi}</small>)}
          </span>
        ))}
      </div>
      <DonaTamir a={a} rahbar={rahbar} amal={amal} />
      {/* FT-5.2: aksessuarning fonsiz rasmi manekinda libos ustidan qo'yiladi */}
      <div className="qator">
        <input ref={fayl} type="file" accept="image/jpeg,image/png,image/webp" hidden
          onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) amal(() => aksessuarManekinYukla(id, f), 'Manekin rasmi tayyor.') }} />
        <button type="button" className="ikkinchi kichik" onClick={() => fayl.current.click()}>
          {a.manekin ? 'Manekin rasmini almashtirish' : 'Manekin uchun rasm yuklash'}
        </button>
        {a.manekin && <button type="button" className="ikkinchi kichik" onClick={() => setManekinOyna(true)}>Manekinda joylash</button>}
        {a.manekin && <button type="button" className="ikkinchi kichik" onClick={() => amal(() => aksessuarManekinOchir(id), 'Manekin rasmi olib tashlandi.')}>Olib tashlash</button>}
      </div>
      {!a.manekin && <p className="malumot">Aksessuarni bir xil rangli fonda suratga oling — tizim fonni o'zi olib tashlaydi.</p>}
      {manekinOyna && a.manekin && (
        <Manekin sarlavha={a.nomi} faylNomi={a.kod} onYopish={() => setManekinOyna(false)}
          qatlamlar={[{ kalit: 'aksessuar', nomi: a.nomi, ...a.manekin, saqla: (b) => aksessuarManekinSaqla(id, b) }]}
          onSaqlandi={() => yukla()} />
      )}
      {rahbar && (
        <>
          <label>Ijara narxi<input type="number" value={narx} onChange={(e) => setNarx(e.target.value)} /></label>
          <button onClick={() => amal(() => aksessuarOzgartir(id, { ijara_narxi: Number(narx) }), "Narx saqlandi.")}>Narxni saqlash</button>
          <div className="qator">
            <input type="number" min="1" max="200" value={soni} onChange={(e) => setSoni(e.target.value)} />
            <button className="ikkinchi" onClick={() => amal(() => donalarQosh(id, Number(soni)), "Donalar qo'shildi.")}>Dona qo'shish</button>
          </div>
          <button className="ikkinchi" onClick={() => amal(() => aksessuarOzgartir(id, { holat: a.holat === 'arxiv' ? 'faol' : 'arxiv' }), 'Holat o\'zgardi.')}>
            {a.holat === 'arxiv' ? 'Arxivdan chiqarish' : 'Arxivga'}
          </button>
          {a.tannarx != null && <p className="malumot">Tannarx: {som(a.tannarx)}</p>}
        </>
      )}
    </div>
  )
}

// Dona ta'mir jurnali: ta'mirga berish va tugatish (narx «ta'mirlash» xarajatiga tushadi)
function DonaTamir({ a, rahbar, amal }) {
  const [dona, setDona] = useState('')
  const [ish, setIsh] = useState('')
  const [kim, setKim] = useState('')
  const [narx, setNarx] = useState({})
  const tamirda = a.donalar.filter((d) => d.tamir)
  const boshlar = a.donalar.filter((d) => d.holat === 'bosh')
  return (
    <details className="amal">
      <summary>Ta'mir ({tamirda.length})</summary>
      <div className="stack">
        {tamirda.map((d) => (
          <div key={d.id} className="tasdiq">
            <span><b>{d.yorliq}</b> · {d.tamir.ish_turi}{d.tamir.kim ? ` · ${d.tamir.kim}` : ''} · {d.tamir.kunlar} kun</span>
            <div className="qator">
              <input type="number" min="0" placeholder="Narxi, so'm" value={narx[d.id] ?? ''} onChange={(e) => setNarx({ ...narx, [d.id]: e.target.value })} />
              <button className="ikkinchi kichik" onClick={() => amal(
                () => donaTamirTugat(d.tamir.id, { narx: Number(narx[d.id]) || 0, ...(rahbar ? {} : { kassadan: true }) }),
                `${d.yorliq}: ta'mir tugadi.`)}>Tugatish</button>
            </div>
          </div>
        ))}
        {boshlar.length > 0 ? (
          <>
            <select value={dona} onChange={(e) => setDona(e.target.value)} aria-label="Dona">
              <option value="">Donani tanlang</option>
              {boshlar.map((d) => <option key={d.id} value={d.id}>{d.yorliq}</option>)}
            </select>
            <label>Nima qilinadi<input value={ish} maxLength={300} onChange={(e) => setIsh(e.target.value)} /></label>
            <label>Usta yoki ustaxona<input value={kim} maxLength={200} onChange={(e) => setKim(e.target.value)} /></label>
            <button className="ikkinchi" disabled={!dona || !ish.trim()}
              onClick={() => amal(() => donaTamirga(Number(dona), { ish_turi: ish, kim }), "Dona ta'mirga berildi.").then((ok) => { if (ok) { setDona(''); setIsh(''); setKim('') } })}>
              Ta'mirga berish
            </button>
          </>
        ) : <p className="malumot">Bo'sh dona yo'q.</p>}
        {!rahbar && <p className="malumot">Narx kassadan chiqim bo'ladi (ochiq smena kerak) va rahbar tasdig'ini kutadi.</p>}
      </div>
    </details>
  )
}

function Tasdiq({ a, onYuborish }) {
  const [narx, setNarx] = useState(a.ijara_narxi || '')
  const [tannarx, setTannarx] = useState('')
  return (
    <div className="tasdiq">
      <span><b>{a.kod}</b> {a.nomi} · {a.donalar_soni} dona ({a.qoshgan} qo'shdi, narx {som(a.ijara_narxi)})</span>
      <div className="qator">
        <input type="number" placeholder="Ijara narxi" value={narx} onChange={(e) => setNarx(e.target.value)} />
        <input type="number" placeholder="Tannarx" value={tannarx} onChange={(e) => setTannarx(e.target.value)} />
      </div>
      <button disabled={narx === '' || tannarx === ''}
        onClick={() => onYuborish({ ijara_narxi: Number(narx), tannarx: Number(tannarx) })}>Tasdiqlash</button>
    </div>
  )
}

function Forma({ kats, rahbar, onYuborish }) {
  const [f, setF] = useState({ soni: '1' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const yubor = async () => {
    const body = {
      nomi: f.nomi, kod: f.kod, kategoriya: Number(f.kategoriya || kats[0].id), soni: Number(f.soni || 1),
      ijara_narxi: Number(f.ijara_narxi || 0), ...(rahbar && f.tannarx ? { tannarx: Number(f.tannarx) } : {}),
    }
    if (await onYuborish(body)) setF({ soni: '1' })
  }
  return (
    <details className="blok amal">
      <summary>Aksessuar qo'shish</summary>
      <div className="stack">
        <label>Nomi<input value={f.nomi || ''} onChange={set('nomi')} /></label>
        <label>Kod (yorliq prefiksi, masalan FT → FT-01, FT-02)<input maxLength={10} value={f.kod || ''} onChange={set('kod')} /></label>
        <label>Kategoriya
          <select value={f.kategoriya || kats[0].id} onChange={set('kategoriya')}>
            {kats.map((k) => <option key={k.id} value={k.id}>{k.nomi}</option>)}
          </select>
        </label>
        <label>Ijara narxi<input type="number" value={f.ijara_narxi || ''} onChange={set('ijara_narxi')} /></label>
        <label>Dona soni<input type="number" min="1" max="200" value={f.soni} onChange={set('soni')} /></label>
        {rahbar && <label>Tannarx<input type="number" value={f.tannarx || ''} onChange={set('tannarx')} /></label>}
        <button disabled={!f.nomi || !f.kod} onClick={yubor}>Qo'shish</button>
      </div>
    </details>
  )
}

import { useCallback, useEffect, useState } from 'react'
import RasmBlok from '../components/RasmBlok'
import TamirBlok from '../components/TamirBlok'
import AksessuarBolimi from './AksessuarBolimi'
import {
  filiallar, kategoriyalar, kategoriyaOchir, kategoriyaOzgartir, kategoriyaYarat, libosOzgartir, libosTasdiq, libosYarat, liboslar, som, xatoMatni,
} from '../api'

const HOLAT = {
  bosh: "Bo'sh", tasdiq_kutilmoqda: 'Tasdiq kutilmoqda', tozalashda: 'Tozalashda', tamirda: "Ta'mirda",
  sotildi: 'Sotildi', hisobdan_chiqarildi: 'Hisobdan chiqarildi', arxiv: 'Arxiv',
}

// 4.3: katalog. Tannarx faqat rahbarga ko'rinadi; sotuvchi qo'shgan libos rahbar tasdig'ini kutadi (FT-3.6).
export default function Katalog({ rahbar, bolim }) {
  return (
    <div className="stack">
      {bolim === 'liboslar' ? <Liboslar rahbar={rahbar} /> : <AksessuarBolimi rahbar={rahbar} />}
    </div>
  )
}

function Liboslar({ rahbar }) {
  const [royxat, setRoyxat] = useState([])
  const [kats, setKats] = useState([])
  const [q, setQ] = useState('')
  const [tanlangan, setTanlangan] = useState(null)
  const [fil, setFil] = useState([])
  const [filial, setFilial] = useState('')
  useEffect(() => { filiallar().then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  const [xabar, setXabar] = useState({ turi: '', matn: '' })

  const yukla = useCallback(async () => {
    const [l, k] = await Promise.all([liboslar({ q: q || undefined, filial: filial || undefined }), kategoriyalar()])
    setRoyxat(l); setKats(k)
  }, [q, filial])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try {
      await fn()
      setXabar({ turi: 'ok', matn: ok })
      await yukla()
      return true
    } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) })
      return false
    }
  }

  const kutayotgan = royxat.filter((l) => l.holat === 'tasdiq_kutilmoqda')
  const libosKats = kats.filter((k) => k.turi === 'libos')

  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}

      {fil.length > 0 && (
        <select value={filial} aria-label="Filial" onChange={(e) => setFilial(e.target.value)}>
          <option value="">Barcha filiallar</option>
          {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
        </select>
      )}
      {rahbar && kutayotgan.length > 0 && (
        <section className="blok ogohlantirish-blok">
          <h3>Tasdiq kutmoqda ({kutayotgan.length})</h3>
          {kutayotgan.map((l) => (
            <TasdiqForma key={l.id} libos={l} rahbar={rahbar} onRasm={yukla}
              onYuborish={(b) => bajar(() => libosTasdiq(l.id, b), `${l.artikul} katalogga chiqdi.`)} />
          ))}
        </section>
      )}

      <LibosForma kats={libosKats} rahbar={rahbar}
        onYuborish={(b) => bajar(() => libosYarat(b), rahbar ? "Libos katalogga qo'shildi." : "Libos rahbar tasdig'iga yuborildi.")} />
      {rahbar && <KategoriyaForma onYuborish={(b) => bajar(() => kategoriyaYarat(b), "Kategoriya qo'shildi.")} />}
      {rahbar && kats.length > 0 && (
        <details className="blok amal">
          <summary>Kategoriyalar ({kats.length})</summary>
          <div className="stack">
            {kats.map((k) => (
              <KategoriyaQator key={`${k.id}-${k.nomi}`} k={k}
                onSaqla={(nomi) => bajar(() => kategoriyaOzgartir(k.id, { nomi }), "Kategoriya nomi o'zgartirildi.")}
                onOchir={() => bajar(() => kategoriyaOchir(k.id), "Kategoriya o'chirildi.")} />
            ))}
            <p className="malumot">Ichida libos yoki aksessuar bor kategoriya o'chirilmaydi.</p>
          </div>
        </details>
      )}

      <input placeholder="Artikul yoki nom bo'yicha qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
      {royxat.length === 0 && <p className="malumot">Libos topilmadi.</p>}
      {royxat.filter((l) => l.holat !== 'tasdiq_kutilmoqda').map((l) => (
        <div key={l.id} className="blok">
          <button className="qator-btn qator-rasm" onClick={() => setTanlangan(tanlangan === l.id ? null : l.id)}>
            {l.rasm ? <img className="eskiz" src={l.rasm} alt="" /> : <span className="eskiz bosh-eskiz">Rasm yo'q</span>}
            <span className="matn-ustun">
              <span><b>{l.artikul}</b> {l.nomi} · {l.kategoriya}</span>
              <span>{som(l.ijara_narxi)} · {HOLAT[l.holat]}</span>
              {rahbar && l.standart_emas > 0 && <span className="belgi">{l.standart_emas} ta rasm standart emas</span>}
            </span>
          </button>
          {tanlangan === l.id && (
            <Tafsilot l={l} rahbar={rahbar} fil={fil} onRasm={yukla}
              onSaqla={(b) => bajar(() => libosOzgartir(l.id, b), "O'zgartirildi.")} />
          )}
        </div>
      ))}
    </div>
  )
}

function Tafsilot({ l, rahbar, onSaqla, onRasm, fil = [] }) {
  const [f, setF] = useState({ ijara_narxi: l.ijara_narxi, zalog: l.zalog, tannarx: l.tannarx ?? '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="stack" style={{ marginTop: 10 }}>
      <p className="malumot">
        O'lcham: {l.olcham || '—'} · Rang: {l.rang || '—'} · Qo'shgan: {l.qoshgan || '—'}
        {fil.length > 0 && !rahbar && ` · Filial: ${fil.find((f) => f.id === l.filial)?.nomi || 'biriktirilmagan'}`}
      </p>
      {rahbar && fil.length > 0 && (
        <select value={l.filial || ''} aria-label="Libos filiali" onChange={(e) => onSaqla({ filial: e.target.value ? Number(e.target.value) : null })}>
          <option value="">Filialga biriktirilmagan (hamma filialda ko'rinadi)</option>
          {fil.map((f) => <option key={f.id} value={f.id}>Filial: {f.nomi}</option>)}
        </select>
      )}
      <RasmBlok libosId={l.id} rahbar={rahbar} onOzgardi={onRasm} />
      <TamirBlok libosId={l.id} rahbar={rahbar} onOzgardi={onRasm} />
      {rahbar ? (
        <>
          <label>Ijara narxi<input type="number" value={f.ijara_narxi} onChange={set('ijara_narxi')} /></label>
          <label>Zalog<input type="number" value={f.zalog} onChange={set('zalog')} /></label>
          <label>Tannarx<input type="number" value={f.tannarx} onChange={set('tannarx')} /></label>
          <button onClick={() => onSaqla({
            ijara_narxi: Number(f.ijara_narxi), zalog: Number(f.zalog),
            ...(f.tannarx !== '' ? { tannarx: Number(f.tannarx) } : {}),
          })}>Saqlash</button>
          <select value={l.holat} onChange={(e) => onSaqla({ holat: e.target.value })}>
            {['bosh', 'sotildi', 'hisobdan_chiqarildi', 'arxiv'].map((h) => (
              <option key={h} value={h}>{HOLAT[h]}</option>
            ))}
            {!['bosh', 'sotildi', 'hisobdan_chiqarildi', 'arxiv'].includes(l.holat) && (
              <option value={l.holat}>{HOLAT[l.holat]}</option>
            )}
          </select>
        </>
      ) : (
        <p>Zalog: {som(l.zalog)}</p>
      )}
    </div>
  )
}

function TasdiqForma({ libos, onYuborish, rahbar, onRasm }) {
  const [narx, setNarx] = useState(libos.ijara_narxi || '')
  const [tannarx, setTannarx] = useState('')
  return (
    <div className="tasdiq">
      <span><b>{libos.artikul}</b> {libos.nomi} ({libos.qoshgan} qo'shdi, narx {som(libos.ijara_narxi)})</span>
      <RasmBlok libosId={libos.id} rahbar={rahbar} onOzgardi={onRasm} />
      <div className="qator">
        <input type="number" placeholder="Ijara narxi" value={narx} onChange={(e) => setNarx(e.target.value)} />
        <input type="number" placeholder="Tannarx" value={tannarx} onChange={(e) => setTannarx(e.target.value)} />
      </div>
      <button disabled={narx === '' || tannarx === ''}
        onClick={() => onYuborish({ ijara_narxi: Number(narx), tannarx: Number(tannarx) })}>Tasdiqlash</button>
    </div>
  )
}

function LibosForma({ kats, rahbar, onYuborish }) {
  const [f, setF] = useState({ kategoriya: '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const tayyor = f.artikul && f.nomi && (f.kategoriya || kats[0])
  const yubor = async () => {
    const body = {
      artikul: f.artikul, nomi: f.nomi, kategoriya: Number(f.kategoriya || kats[0].id), olcham: f.olcham || '',
      rang: f.rang || '', ijara_narxi: Number(f.ijara_narxi || 0), zalog: Number(f.zalog || 0),
      ...(rahbar && f.tannarx ? { tannarx: Number(f.tannarx) } : {}),
    }
    if (await onYuborish(body)) setF({ kategoriya: '' })
  }
  return (
    <details className="blok amal">
      <summary>Libos qo'shish</summary>
      <div className="stack">
        <label>Artikul<input value={f.artikul || ''} onChange={set('artikul')} /></label>
        <label>Nomi<input value={f.nomi || ''} onChange={set('nomi')} /></label>
        <label>Kategoriya
          <select value={f.kategoriya || kats[0]?.id || ''} onChange={set('kategoriya')}>
            {kats.map((k) => <option key={k.id} value={k.id}>{k.nomi}</option>)}
          </select>
        </label>
        <div className="qator">
          <input placeholder="O'lcham" value={f.olcham || ''} onChange={set('olcham')} />
          <input placeholder="Rang" value={f.rang || ''} onChange={set('rang')} />
        </div>
        <label>Ijara narxi<input type="number" value={f.ijara_narxi || ''} onChange={set('ijara_narxi')} /></label>
        <label>Tavsiya etilgan zalog<input type="number" value={f.zalog || ''} onChange={set('zalog')} /></label>
        {rahbar && <label>Tannarx<input type="number" value={f.tannarx || ''} onChange={set('tannarx')} /></label>}
        {!rahbar && <p className="malumot">Libos rahbar narx va tannarxni tasdiqlagach katalogga chiqadi.</p>}
        <button disabled={!tayyor} onClick={yubor}>Qo'shish</button>
      </div>
    </details>
  )
}

function KategoriyaQator({ k, onSaqla, onOchir }) {
  const [nomi, setNomi] = useState(k.nomi)
  return (
    <div className="tasdiq">
      <span>{k.turi === 'aksessuar' ? 'Aksessuar' : 'Libos'} kategoriyasi</span>
      <input value={nomi} maxLength={100} aria-label="Kategoriya nomi" onChange={(e) => setNomi(e.target.value)} />
      <div className="qator">
        <button className="ikkinchi kichik" disabled={!nomi.trim() || nomi.trim() === k.nomi} onClick={() => onSaqla(nomi.trim())}>Nomini saqlash</button>
        <button className="xavfli kichik" onClick={onOchir}>O'chirish</button>
      </div>
    </div>
  )
}

function KategoriyaForma({ onYuborish }) {
  const [nomi, setNomi] = useState('')
  const [turi, setTuri] = useState('libos')
  return (
    <details className="blok amal">
      <summary>Kategoriya qo'shish</summary>
      <div className="stack">
        <input placeholder="Masalan: Kuyov kostyumi" value={nomi} onChange={(e) => setNomi(e.target.value)} />
        <select value={turi} onChange={(e) => setTuri(e.target.value)}>
          <option value="libos">Libos kategoriyasi</option>
          <option value="aksessuar">Aksessuar kategoriyasi</option>
        </select>
        <button disabled={!nomi.trim()} onClick={() => onYuborish({ nomi: nomi.trim(), turi }).then((ok) => ok && setNomi(''))}>Qo'shish</button>
      </div>
    </details>
  )
}

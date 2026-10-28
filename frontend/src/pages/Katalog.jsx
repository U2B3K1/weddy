import { Fragment, useCallback, useEffect, useState } from 'react'
import NavIkona from '../components/NavIkona'
import Oyna from '../components/Oyna'
import RasmBlok from '../components/RasmBlok'
import TamirBlok from '../components/TamirBlok'
import AksessuarBolimi from './AksessuarBolimi'
import {
  filiallar, kategoriyalar, kategoriyaOchir, kategoriyaOzgartir, kategoriyaYarat, libosOzgartir, libosTasdiq, libosYarat, liboslar, som, xatoMatni,
} from '../api'
import SummaInput from '../components/SummaInput'
import LibosSiluet from '../components/LibosSiluet'

// Ro'yxatda odatda faqat ishlaydigan liboslar; sotilgan/arxiv — holat filtri bilan
const NOFAOL = ['sotildi', 'hisobdan_chiqarildi', 'arxiv']
const HOLAT_FILTR = [['', 'Faol liboslar'], ['bosh', "Bo'sh"], ['tamirda', "Ta'mirda"], ['tozalashda', 'Tozalashda'],
  ['sotildi', 'Sotilgan'], ['arxiv', 'Arxiv'], ['hammasi', 'Hammasi']]
const holatSinfi = (h) => ({ bosh: 'bron', tamirda: 'qarz', tozalashda: 'vaqtinchalik', tasdiq_kutilmoqda: 'vaqtinchalik' }[h] || 'qaytarildi')
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
  const [kat, setKat] = useState('')
  const [holat, setHolat] = useState('')
  const [oyna, setOyna] = useState(null) // 'yangi' | 'kategoriya' | null
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
  const katalogda = royxat.filter((l) => l.holat !== 'tasdiq_kutilmoqda')
  const faol = katalogda.filter((l) => !NOFAOL.includes(l.holat))
  const korinadi = katalogda.filter((l) => (!kat || l.kategoriya === kat)
    && (holat === 'hammasi' || (holat ? l.holat === holat : !NOFAOL.includes(l.holat))))
  const ortacha = faol.length ? Math.round(faol.reduce((s, l) => s + l.ijara_narxi, 0) / faol.length) : 0
  const katNomlari = [...new Set(katalogda.map((l) => l.kategoriya))].sort()

  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}

      {/* Katalog holati bir qarashda (Point uslubidagi kichik ko'rsatkichlar) */}
      <div className="stat-qator">
        <div className="stat"><span>Faol liboslar</span><b>{faol.length}</b></div>
        <div className="stat"><span>Ijaraga tayyor</span><b>{faol.filter((l) => l.holat === 'bosh').length}</b></div>
        <div className="stat"><span>Ta'mir va tozalashda</span><b>{faol.filter((l) => ['tamirda', 'tozalashda'].includes(l.holat)).length}</b></div>
        <div className="stat"><span>O'rtacha ijara narxi</span><b>{som(ortacha)}</b></div>
      </div>

      {rahbar && kutayotgan.length > 0 && (
        <section className="blok diqqat-blok">
          <h3>Tasdiq kutmoqda ({kutayotgan.length})</h3>
          {kutayotgan.map((l) => (
            <TasdiqForma key={l.id} libos={l} rahbar={rahbar} onRasm={yukla}
              onYuborish={(b) => bajar(() => libosTasdiq(l.id, b), `${l.artikul} katalogga chiqdi.`)} />
          ))}
        </section>
      )}

      {oyna === 'yangi' && (
        <Oyna sarlavha="Libos qo'shish" onYop={() => setOyna(null)}>
          <LibosForma kats={libosKats} rahbar={rahbar}
            onYuborish={async (b) => {
              const ok = await bajar(() => libosYarat(b), rahbar ? "Libos katalogga qo'shildi." : "Libos rahbar tasdig'iga yuborildi.")
              if (ok) setOyna(null)
              return ok
            }} />
        </Oyna>
      )}
      {rahbar && oyna === 'kategoriya' && (
        <Oyna sarlavha={`Kategoriyalar (${kats.length})`} onYop={() => setOyna(null)}>
          <div className="stack">
            <KategoriyaForma onYuborish={(b) => bajar(() => kategoriyaYarat(b), "Kategoriya qo'shildi.")} />
            {kats.map((k) => (
              <KategoriyaQator key={`${k.id}-${k.nomi}`} k={k}
                onSaqla={(nomi) => bajar(() => kategoriyaOzgartir(k.id, { nomi }), "Kategoriya nomi o'zgartirildi.")}
                onOchir={() => bajar(() => kategoriyaOchir(k.id), "Kategoriya o'chirildi.")} />
            ))}
            <p className="malumot">Ichida libos yoki aksessuar bor kategoriya o'chirilmaydi.</p>
          </div>
        </Oyna>
      )}

      <section className="blok jadval-panel">
        {/* Asboblar paneli: kategoriya tablari, holat, qidiruv va amallar — bitta qatorda */}
        <div className="jadval-asboblar">
          <h3 className="panel-nom">Liboslar</h3>
          <div className="tezkor-tablar" role="tablist" aria-label="Kategoriya">
            {[['', 'Hammasi'], ...katNomlari.map((k) => [k, k])].map(([k, nom]) => (
              <button key={k || 'hammasi'} type="button" role="tab" aria-selected={kat === k} className={kat === k ? 'faol' : ''} onClick={() => setKat(k)}>{nom}</button>
            ))}
          </div>
          <select className="kichik-tanlov" value={holat} aria-label="Holat" onChange={(e) => setHolat(e.target.value)}>
            {HOLAT_FILTR.map(([k, nom]) => <option key={k} value={k}>{nom}</option>)}
          </select>
          {fil.length > 0 && (
            <select className="kichik-tanlov" value={filial} aria-label="Filial" onChange={(e) => setFilial(e.target.value)}>
              <option value="">Barcha filiallar</option>
              {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
            </select>
          )}
          <label className="qidiruv-maydon">
            <NavIkona nom="qidiruv" className="tugma-ikon" />
            <input type="search" className="jadval-qidiruv" placeholder="Artikul yoki nom" aria-label="Libos qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          {rahbar && <button type="button" className="ikkinchi kichik" onClick={() => setOyna('kategoriya')}>Kategoriyalar</button>}
          <button type="button" className="kichik" onClick={() => setOyna('yangi')}><NavIkona nom="qosh" className="tugma-ikon" />Libos qo'shish</button>
        </div>
        {korinadi.length === 0 && <p className="malumot jadval-bosh">{q || kat || holat ? 'Bu filtr bo\'yicha libos yo\'q.' : "Katalog bo'sh — birinchi libosni qo'shing."}</p>}
      {/* Butik javoni: libos fotosi tabiatan vertikal — kartochka 2:3. Tanlangan libos tafsiloti o'z qatoridan keyin butun kenglikda */}
      <div className="libos-tor panel-ichi">
        {korinadi.map((l) => (
          <Fragment key={l.id}>
            <button type="button" className={`libos-karta ${tanlangan === l.id ? 'tanlandi' : ''}`} aria-expanded={tanlangan === l.id}
              onClick={() => setTanlangan(tanlangan === l.id ? null : l.id)}>
              <span className="libos-foto">
                {l.rasm ? <img src={l.rasm} alt="" loading="lazy" /> : <LibosSiluet />}
                {/* «Bo'sh» — odatiy holat, har kartochkada yozilmaydi; faqat ijaraga chiqmaydigan holat ko'rsatiladi */}
                {l.holat !== 'bosh' && <span className={`holat ${holatSinfi(l.holat)} libos-holat`}>{HOLAT[l.holat]}</span>}
              </span>
              <span className="libos-matn">
                <span className="libos-nom"><b>{l.artikul}</b> {l.nomi}</span>
                <span className="libos-kat">{l.kategoriya}{l.olcham ? `, ${l.olcham}` : ''}</span>
                <span className="libos-narx">{som(l.ijara_narxi)}</span>
                {rahbar && l.standart_emas > 0 && <span className="belgi">{l.standart_emas} ta rasm standart emas</span>}
              </span>
            </button>
            {tanlangan === l.id && (
              <div className="blok libos-tafsilot">
                <div className="libos-tafsilot-bosh">
                  <h3>{l.artikul} {l.nomi}</h3>
                  <button type="button" className="ikkinchi kichik" onClick={() => setTanlangan(null)}>Yopish</button>
                </div>
                <Tafsilot l={l} rahbar={rahbar} fil={fil} onRasm={yukla}
                  onSaqla={(b) => bajar(() => libosOzgartir(l.id, b), "O'zgartirildi.")} />
              </div>
            )}
          </Fragment>
        ))}
      </div>
      </section>
    </div>
  )
}

function Tafsilot({ l, rahbar, onSaqla, onRasm, fil = [] }) {
  const [f, setF] = useState({ ijara_narxi: l.ijara_narxi, zalog: l.zalog, tannarx: l.tannarx ?? '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  return (
    <div className="stack">
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
          <div className="libos-narxlar">
            <label>Ijara narxi<SummaInput value={f.ijara_narxi} onChange={set('ijara_narxi')} /></label>
            <label>Zalog<SummaInput value={f.zalog} onChange={set('zalog')} /></label>
            <label>Tannarx<SummaInput value={f.tannarx} onChange={set('tannarx')} /></label>
          </div>
          <button onClick={() => onSaqla({
            ijara_narxi: Number(f.ijara_narxi), zalog: Number(f.zalog),
            ...(f.tannarx !== '' ? { tannarx: Number(f.tannarx) } : {}),
          })}>Narxlarni saqlash</button>
          <label>Holati (darhol saqlanadi)
          <select value={l.holat} onChange={(e) => onSaqla({ holat: e.target.value })}>
            {['bosh', 'sotildi', 'hisobdan_chiqarildi', 'arxiv'].map((h) => (
              <option key={h} value={h}>{HOLAT[h]}</option>
            ))}
            {!['bosh', 'sotildi', 'hisobdan_chiqarildi', 'arxiv'].includes(l.holat) && (
              <option value={l.holat}>{HOLAT[l.holat]}</option>
            )}
          </select>
          </label>
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
        <SummaInput placeholder="Ijara narxi" value={narx} onChange={(e) => setNarx(e.target.value)} />
        <SummaInput placeholder="Tannarx" value={tannarx} onChange={(e) => setTannarx(e.target.value)} />
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
    <div className="stack">
        <label>Artikul<input value={f.artikul || ''} onChange={set('artikul')} /></label>
        <label>Nomi<input value={f.nomi || ''} onChange={set('nomi')} /></label>
        <label>Kategoriya
          <select value={f.kategoriya || kats[0]?.id || ''} onChange={set('kategoriya')}>
            {kats.map((k) => <option key={k.id} value={k.id}>{k.nomi}</option>)}
          </select>
        </label>
        <div className="libos-narxlar">
          <label>O'lcham<input placeholder="44" value={f.olcham || ''} onChange={set('olcham')} /></label>
          <label>Rang<input placeholder="oq" value={f.rang || ''} onChange={set('rang')} /></label>
        </div>
        <div className="libos-narxlar">
          <label>Ijara narxi<SummaInput value={f.ijara_narxi || ''} onChange={set('ijara_narxi')} /></label>
          <label>Tavsiya etilgan zalog<SummaInput value={f.zalog || ''} onChange={set('zalog')} /></label>
          {rahbar && <label>Tannarx<SummaInput value={f.tannarx || ''} onChange={set('tannarx')} /></label>}
        </div>
        {!rahbar && <p className="malumot">Libos rahbar narx va tannarxni tasdiqlagach katalogga chiqadi.</p>}
        <button disabled={!tayyor} onClick={yubor}>Qo'shish</button>
    </div>
  )
}

function KategoriyaQator({ k, onSaqla, onOchir }) {
  const [nomi, setNomi] = useState(k.nomi)
  return (
    <div className="kategoriya-qator">
      <input value={nomi} maxLength={100} aria-label="Kategoriya nomi" onChange={(e) => setNomi(e.target.value)} />
      <span className="malumot">{k.turi === 'aksessuar' ? 'Aksessuar' : 'Libos'}</span>
      <button className="ikkinchi kichik" disabled={!nomi.trim() || nomi.trim() === k.nomi} onClick={() => onSaqla(nomi.trim())}>Saqlash</button>
      <button className="xavfli kichik" onClick={onOchir}>O'chirish</button>
    </div>
  )
}

function KategoriyaForma({ onYuborish }) {
  const [nomi, setNomi] = useState('')
  const [turi, setTuri] = useState('libos')
  return (
    <div className="kategoriya-forma">
        <input placeholder="Yangi kategoriya, masalan: Kuyov kostyumi" aria-label="Kategoriya nomi" value={nomi} onChange={(e) => setNomi(e.target.value)} />
        <select value={turi} aria-label="Kategoriya turi" onChange={(e) => setTuri(e.target.value)}>
          <option value="libos">Libos kategoriyasi</option>
          <option value="aksessuar">Aksessuar kategoriyasi</option>
        </select>
        <button className="kichik" disabled={!nomi.trim()} onClick={() => onYuborish({ nomi: nomi.trim(), turi }).then((ok) => ok && setNomi(''))}>Qo'shish</button>
    </div>
  )
}

import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import Manekin from '../components/Manekin'
import NavIkona from '../components/NavIkona'
import Oyna from '../components/Oyna'
import {
  aksessuarManekinOchir, aksessuarManekinSaqla, aksessuarManekinYukla, aksessuarOzgartir, aksessuarRasmOchir, aksessuarRasmYukla, aksessuarTafsilot, aksessuarTasdiq, aksessuarYarat, aksessuarlar, donaFilial, donaHolati, filiallar, donaTamirTugat, donaTamirga, donalarQosh, partiyaOzgartir,
  kategoriyalar, sanaMatni, som, xatoMatni, yetkazibBeruvchilar,
} from '../api'
import SummaInput from '../components/SummaInput'

// «i» matni: partiya va yangi aksessuar formalarida bir xil
const TOLANDI_INFO = "Yetkazib beruvchiga hozir berilgan pul. Bo'sh qoldirsangiz — to'liq to'langan deb yoziladi; kamroq yozsangiz, qolgani unga qarz bo'lib turadi. Bu pul kassadan chiqmaydi."

const DONA_HOLAT = { bosh: "Bo'sh", tamirda: "Ta'mirda", yoqolgan: "Yo'qolgan", arxiv: 'Arxiv' }

// 4.4: aksessuarlar faqat ijaraga; har bir dona alohida raqamli yorliq bilan hisobga olinadi.
// Ko'rinish liboslar bilan bir xil (Point uslubi): kichik ko'rsatkichlar, bitta asboblar paneli, ustunli jadval,
// qator bosilganda tafsilot shu joyda ochiladi; qo'shish — oynada.
export default function AksessuarBolimi({ rahbar }) {
  const [royxat, setRoyxat] = useState([])
  const [kats, setKats] = useState([])
  const [ochiq, setOchiq] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [kat, setKat] = useState('')
  const [holat, setHolat] = useState('faol')
  const [q, setQ] = useState('')
  const [oyna, setOyna] = useState(false)

  const yukla = useCallback(async () => {
    const [a, k] = await Promise.all([aksessuarlar(), kategoriyalar()])
    setRoyxat(a); setKats(k.filter((x) => x.turi === 'aksessuar'))
  }, [])
  useEffect(() => { yukla().catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })) }, [yukla])
  const [ybs, setYbs] = useState([])  // yetkazib beruvchilar (faqat rahbar)
  useEffect(() => { if (rahbar) yetkazibBeruvchilar().then(setYbs).catch(() => {}) }, [rahbar])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try { await fn(); setXabar({ turi: 'ok', matn: ok }); await yukla(); return true } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e) }); return false
    }
  }

  const kutayotgan = royxat.filter((a) => a.holat === 'tasdiq_kutilmoqda')
  const katalogda = royxat.filter((a) => a.holat !== 'tasdiq_kutilmoqda')
  const faol = katalogda.filter((a) => a.holat !== 'arxiv')
  const s = q.trim().toLowerCase()
  const korinadi = katalogda.filter((a) => (!kat || a.kategoriya === kat)
    && (holat === 'hammasi' || (holat === 'arxiv' ? a.holat === 'arxiv' : a.holat !== 'arxiv'))
    && (!s || a.nomi.toLowerCase().includes(s) || a.kod.toLowerCase().includes(s)))
  const katNomlari = [...new Set(katalogda.map((a) => a.kategoriya))].sort()
  const jamiDona = faol.reduce((n, a) => n + a.donalar_soni, 0)
  const yaroqli = faol.reduce((n, a) => n + a.yaroqli_donalar, 0)

  return (
    <div className="stack">
      {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {kats.length === 0 && (
        <p className="ogohlantirish">Aksessuar kategoriyasi yo'q{rahbar ? ": «Liboslar» bo'limidagi «Kategoriyalar» tugmasi orqali turi «Aksessuar» bo'lgan kategoriya yarating." : '. Rahbar kategoriya yaratishi kerak.'}</p>
      )}

      <div className="stat-qator">
        <div className="stat"><span>Aksessuar turlari</span><b>{faol.length}</b></div>
        <div className="stat"><span>Jami donalar</span><b>{jamiDona}</b></div>
        <div className="stat"><span>Ijaraga yaroqli</span><b>{yaroqli}</b></div>
        <div className="stat"><span>Ta'mirda yoki yo'qolgan</span><b>{jamiDona - yaroqli}</b></div>
      </div>

      {rahbar && kutayotgan.length > 0 && (
        <section className="blok diqqat-blok">
          <h3>Tasdiq kutmoqda ({kutayotgan.length})</h3>
          {kutayotgan.map((a) => (
            <Tasdiq key={a.id} a={a}
              onYuborish={(b) => bajar(() => aksessuarTasdiq(a.id, b), `${a.nomi} tasdiqlandi.`)} />
          ))}
        </section>
      )}

      {oyna && kats.length > 0 && (
        <Oyna sarlavha="Aksessuar qo'shish" onYop={() => setOyna(false)}>
          <Forma kats={kats} rahbar={rahbar} ybs={ybs}
            onYuborish={async (b) => {
              const ok = await bajar(() => aksessuarYarat(b), rahbar ? "Aksessuar qo'shildi." : "Aksessuar rahbar tasdig'iga yuborildi.")
              if (ok) setOyna(false)
              return ok
            }} />
        </Oyna>
      )}

      <section className="blok jadval-panel">
        <div className="jadval-asboblar">
          <h3 className="panel-nom">Aksessuarlar</h3>
          <div className="tezkor-tablar" role="tablist" aria-label="Kategoriya">
            {[['', 'Hammasi'], ...katNomlari.map((k) => [k, k])].map(([k, nom]) => (
              <button key={k || 'hammasi'} type="button" role="tab" aria-selected={kat === k} className={kat === k ? 'faol' : ''} onClick={() => setKat(k)}>{nom}</button>
            ))}
          </div>
          <select className="kichik-tanlov" value={holat} aria-label="Holat" onChange={(e) => setHolat(e.target.value)}>
            <option value="faol">Faol</option><option value="arxiv">Arxiv</option><option value="hammasi">Hammasi</option>
          </select>
          <label className="qidiruv-maydon">
            <NavIkona nom="qidiruv" className="tugma-ikon" />
            <input type="search" className="jadval-qidiruv" placeholder="Nom yoki kod" aria-label="Aksessuar qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          <button type="button" className="kichik" disabled={kats.length === 0} onClick={() => setOyna(true)}>
            <NavIkona nom="qosh" className="tugma-ikon" />Aksessuar qo'shish
          </button>
        </div>
        {korinadi.length === 0 ? (
          <p className="malumot jadval-bosh">{royxat.length === 0 ? "Hali aksessuar yo'q — birinchisini qo'shing." : "Bu filtr bo'yicha aksessuar yo'q."}</p>
        ) : (
          <div className="jadval-ora">
            <table className="zakaz-jadval aks-jadval">
              <thead>
                <tr><th>Aksessuar</th><th className="tor-yashir">Kategoriya</th><th>Donalar</th><th className="ong">Ijara narxi</th></tr>
              </thead>
              <tbody>
                {korinadi.map((a) => {
                  const foiz = a.donalar_soni ? Math.round((a.yaroqli_donalar / a.donalar_soni) * 100) : 0
                  return (
                    <Fragment key={a.id}>
                      <tr className={ochiq === a.id ? 'ochiq' : ''} onClick={() => setOchiq(ochiq === a.id ? null : a.id)}>
                        <td>
                          <button type="button" className="zakaz-katak" aria-expanded={ochiq === a.id}>
                            {a.rasm ? <img className="aks-eskiz" src={a.rasm} alt="" /> : <span className="kod-belgi">{a.kod}</span>}
                            <span className="zakaz-nom"><b>{a.nomi}</b>{a.holat === 'arxiv' && <small>Arxivda</small>}</span>
                          </button>
                        </td>
                        <td className="tor-yashir">{a.kategoriya}</td>
                        <td>
                          <span className="tolov-progress" title={`${a.yaroqli_donalar} ta dona ijaraga yaroqli`}>
                            <i style={{ '--foiz': `${foiz}%` }} className={foiz >= 100 ? 'toliq' : ''} />
                            <small>{a.yaroqli_donalar} / {a.donalar_soni}</small>
                          </span>
                        </td>
                        <td className="ong"><b>{som(a.ijara_narxi)}</b></td>
                      </tr>
                      {ochiq === a.id && (
                        <tr className="tafsilot-qator"><td colSpan={4}><Tafsilot id={a.id} rahbar={rahbar} bajar={bajar} ybs={ybs} /></td></tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function Tafsilot({ id, rahbar, bajar, ybs = [] }) {
  const [a, setA] = useState(null)
  const [narx, setNarx] = useState('')
  const yukla = useCallback(() => aksessuarTafsilot(id).then((d) => { setA(d); setNarx(d.ijara_narxi) }), [id])
  useEffect(() => { yukla() }, [yukla])
  const amal = async (fn, ok) => { const r = await bajar(fn, ok); if (r) await yukla(); return r }
  const fayl = useRef(null)
  const rasmFayl = useRef(null)
  const [fil, setFil] = useState([])
  useEffect(() => { filiallar().then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  const [manekinOyna, setManekinOyna] = useState(false)
  if (!a) return <p className="malumot">Yuklanmoqda…</p>
  return (
    <div className="aks-tafsilot">
      <div className="stack">
      <h4>Donalar</h4>
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
      </div>
      <div className="stack">
      <h4>Rasm</h4>
      {/* Yangi zakazda aksessuar shu rasm bilan ko'ylaklar qatori kartochka bo'lib chiqadi */}
      <div className="aks-rasm-qator">
        {a.rasm_katta
          ? <img className="aks-rasm" src={a.rasm_katta} alt={a.nomi} />
          : <span className="aks-rasm aks-rasm-bosh" aria-hidden="true">{a.kod}</span>}
        <div className="stack">
          <input ref={rasmFayl} type="file" accept="image/jpeg,image/png,image/webp" hidden
            onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) amal(() => aksessuarRasmYukla(id, f), 'Rasm saqlandi.') }} />
          <button type="button" className="ikkinchi kichik" onClick={() => rasmFayl.current.click()}>
            {a.rasm ? 'Rasmni almashtirish' : 'Rasm yuklash'}
          </button>
          {a.rasm && rahbar && (
            <button type="button" className="ikkinchi kichik" onClick={() => amal(() => aksessuarRasmOchir(id), 'Rasm olib tashlandi.')}>Rasmni olib tashlash</button>
          )}
          {!a.rasm && <p className="malumot">Yangi zakazda aksessuar ko'ylaklar kabi rasm bilan ko'rinadi. Oq yoki och fonda, tik holatda suratga oling.</p>}
        </div>
      </div>
      <h4>Manekin va sozlamalar</h4>
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
          <div className="ixcham-forma">
            <label>Ijara narxi<SummaInput value={narx} onChange={(e) => setNarx(e.target.value)} /></label>
            <button className="kichik" onClick={() => amal(() => aksessuarOzgartir(id, { ijara_narxi: Number(narx) }), "Narx saqlandi.")}>Saqlash</button>
          </div>
          <DonaQoshish a={a} ybs={ybs} onYuborish={(b) => amal(() => donalarQosh(id, b), "Donalar qo'shildi.")} />
          <div className="qator">
            <button className="ikkinchi kichik" onClick={() => amal(() => aksessuarOzgartir(id, { holat: a.holat === 'arxiv' ? 'faol' : 'arxiv' }), 'Holat o\'zgardi.')}>
              {a.holat === 'arxiv' ? 'Arxivdan chiqarish' : 'Arxivga'}
            </button>
            {a.tannarx != null && <span className="malumot">Tannarx: {som(a.tannarx)} (1 dona)</span>}
          </div>
          <Partiyalar a={a} ybs={ybs} amal={amal} />
        </>
      )}
      </div>
    </div>
  )
}

// Yangi donalar — alohida partiya: o'z narxi va yetkazib beruvchisi bilan (eski donalar qarzi o'zgarmaydi)
function DonaQoshish({ a, ybs, onYuborish }) {
  const [f, setF] = useState({ soni: '1', narx: '', yb: '', tolandi: '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const jami = Number(f.narx || a.tannarx || 0) * Number(f.soni || 0)
  return (
    <details className="amal">
      <summary>Dona qo'shish</summary>
      <div className="stack">
        <div className="qator">
          <label>Soni<input type="number" min="1" max="200" value={f.soni} onChange={set('soni')} /></label>
          <label>Bir dona narxi<SummaInput placeholder={a.tannarx != null ? som(a.tannarx) : ''} value={f.narx} onChange={set('narx')} /><Info nom="Bir dona narxi">Shu partiyadagi bir donaning xarid narxi. Har partiya o'z narxi bilan saqlanadi — keyingi xarid qimmatroq bo'lsa, eskilari o'zgarmaydi. Bo'sh qoldirilsa, aksessuarning odatiy tannarxi olinadi.</Info></label>
        </div>
        {ybs.length > 0 && (
          <div className="qator">
            <label>Qayerdan olingan
              <select value={f.yb} onChange={set('yb')}>
                <option value="">Ko'rsatilmagan</option>
                {ybs.map((y) => <option key={y.id} value={y.id}>{y.nomi}</option>)}
              </select>
            </label>
            {f.yb && <label>Hozir to'landi<SummaInput placeholder={`to'liq: ${som(jami)}`} value={f.tolandi} onChange={set('tolandi')} /><Info nom="Hozir to'landi">{TOLANDI_INFO}</Info></label>}
          </div>
        )}
        {f.yb && f.tolandi !== '' && Number(f.tolandi) < jami && (
          <p className="malumot">Yetkazib beruvchiga qarz: <b>{som(jami - Number(f.tolandi))}</b></p>
        )}
        <button className="ikkinchi" disabled={!(Number(f.soni) >= 1)} onClick={async () => {
          const ok = await onYuborish({
            soni: Number(f.soni), ...(f.narx !== '' ? { narx: Number(f.narx) } : {}),
            // bo'sh qoldirilsa — to'liq to'langan; kami — yetkazib beruvchiga qarz
            ...(f.yb ? { yetkazib_beruvchi: Number(f.yb), ...(f.tolandi !== '' ? { tolandi: Number(f.tolandi) } : {}) } : {}),
          })
          if (ok) setF({ soni: '1', narx: '', yb: '', tolandi: '' })
        }}>Qo'shish</button>
      </div>
    </details>
  )
}

// Har partiya kimdan va necha pulga olingani; yetkazib beruvchini keyin biriktirish mumkin (to'lov yozilmaydi — qarz)
function Partiyalar({ a, ybs, amal }) {
  const p = a.partiyalar || []
  if (!p.length) return null
  return (
    <details className="amal">
      <summary>Partiyalar ({p.length})</summary>
      <div className="stack">
        {p.map((x) => (
          <div key={x.id} className="qator">
            <span className="qator-matn">{sanaMatni(x.sana)} · {x.soni} dona × {x.narx == null ? 'narx kiritilmagan' : `${som(x.narx)} = ${som(x.jami)}`}</span>
            {ybs.length > 0 && (
              <select aria-label={`${x.soni} donalik partiya yetkazib beruvchisi`} value={x.yetkazib_beruvchi || ''}
                onChange={(e) => amal(() => partiyaOzgartir(x.id, { yetkazib_beruvchi: e.target.value ? Number(e.target.value) : null }), 'Saqlandi.')}>
                <option value="">Ko'rsatilmagan</option>
                {ybs.map((y) => <option key={y.id} value={y.id}>{y.nomi}</option>)}
              </select>
            )}
          </div>
        ))}
      </div>
    </details>
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
              <SummaInput placeholder="Narxi, so'm" value={narx[d.id] ?? ''} onChange={(e) => setNarx({ ...narx, [d.id]: e.target.value })} />
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
        <SummaInput placeholder="Ijara narxi" value={narx} onChange={(e) => setNarx(e.target.value)} />
        <SummaInput placeholder="Tannarx" value={tannarx} onChange={(e) => setTannarx(e.target.value)} />
      </div>
      <button disabled={narx === '' || tannarx === ''}
        onClick={() => onYuborish({ ijara_narxi: Number(narx), tannarx: Number(tannarx) })}>Tasdiqlash</button>
    </div>
  )
}

function Forma({ kats, rahbar, ybs = [], onYuborish }) {
  const [f, setF] = useState({ soni: '1' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const yubor = async () => {
    const body = {
      nomi: f.nomi, kod: f.kod, kategoriya: Number(f.kategoriya || kats[0].id), soni: Number(f.soni || 1),
      ijara_narxi: Number(f.ijara_narxi || 0), ...(rahbar && f.tannarx ? { tannarx: Number(f.tannarx) } : {}),
      // bo'sh qoldirilsa — tannarx × soni to'liq to'langan; kami — yetkazib beruvchiga qarz
      ...(rahbar && f.yetkazib_beruvchi ? { yetkazib_beruvchi: Number(f.yetkazib_beruvchi), ...(f.tolandi ? { tolandi: Number(f.tolandi) } : {}) } : {}),
    }
    if (await onYuborish(body)) setF({ soni: '1' })
  }
  return (
    <div className="stack">
        <label>Nomi<input value={f.nomi || ''} onChange={set('nomi')} /></label>
        <label>Kod<input placeholder="FT" maxLength={10} value={f.kod || ''} onChange={set('kod')} /><Info nom="Kod">Aksessuar turining qisqa kodi. Har donaning yorlig'i shu koddan yasaladi: FT → FT-01, FT-02… Salonda takrorlanmaydi.</Info></label>
        <label>Kategoriya
          <select value={f.kategoriya || kats[0].id} onChange={set('kategoriya')}>
            {kats.map((k) => <option key={k.id} value={k.id}>{k.nomi}</option>)}
          </select>
        </label>
        <div className="libos-narxlar">
          <label>Ijara narxi<SummaInput value={f.ijara_narxi || ''} onChange={set('ijara_narxi')} /></label>
          <label>Dona soni<input type="number" min="1" max="200" value={f.soni} onChange={set('soni')} /></label>
          {rahbar && <label>Tannarx (1 dona)<SummaInput value={f.tannarx || ''} onChange={set('tannarx')} /><Info nom="Tannarx">Bir donani sotib olishga ketgan pul. Faqat rahbarga ko'rinadi. Keyin qo'shiladigan donalar uchun ham odatiy narx bo'ladi.</Info></label>}
        </div>
        {rahbar && ybs.length > 0 && (
          <div className="libos-narxlar">
            <label>Qayerdan olingan
              <select value={f.yetkazib_beruvchi || ''} onChange={set('yetkazib_beruvchi')}>
                <option value="">Ko'rsatilmagan</option>
                {ybs.map((y) => <option key={y.id} value={y.id}>{y.nomi}</option>)}
              </select>
            </label>
            {f.yetkazib_beruvchi && (
              <label>Hozir to'landi<SummaInput placeholder={f.tannarx ? `to'liq: ${som(Number(f.tannarx) * Number(f.soni || 1))}` : ''} value={f.tolandi || ''} onChange={set('tolandi')} /><Info nom="Hozir to'landi">{TOLANDI_INFO}</Info></label>
            )}
          </div>
        )}
        {rahbar && f.yetkazib_beruvchi && f.tolandi && Number(f.tolandi) < Number(f.tannarx || 0) * Number(f.soni || 1) && (
          <p className="malumot">Yetkazib beruvchiga qarz: <b>{som(Number(f.tannarx) * Number(f.soni || 1) - Number(f.tolandi))}</b></p>
        )}
        <button disabled={!f.nomi || !f.kod} onClick={yubor}>Qo'shish</button>
    </div>
  )
}

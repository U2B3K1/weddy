import TasdiqOyna from '../components/Tasdiq'
import { useCallback, useEffect, useRef, useState } from 'react'
import KpiFiltr from '../components/KpiFiltr'
import { BoshAmal } from '../components/BoshJoy'
import Info from '../components/Info'
import Manekin from '../components/Manekin'
import NavIkona from '../components/NavIkona'
import Tasma from '../components/Tasma'
import { OYLAR } from '../components/kalendar/sana'
import { Belgi } from '../components/ZakazQatorlari'
import Oyna from '../components/Oyna'
import {
  aksessuarManekinOchir, aksessuarManekinSaqla, aksessuarManekinYukla, aksessuarOzgartir, aksessuarRasmOchir, aksessuarRasmYukla, aksessuarTafsilot, aksessuarTasdiq, aksessuarYarat, aksessuarlar, donaFilial, donaHolati, filiallar, donaTamirTugat, donaTamirga, donalarQosh, partiyaOzgartir,
  kategoriyalar, sanaMatni, som, guruhla, xatoMatni, yetkazibBeruvchilar,
} from '../api'
import SummaInput from '../components/SummaInput'

// «i» matni: partiya va yangi aksessuar formalarida bir xil
const TOLANDI_INFO = "Yetkazib beruvchiga hozir berilgan pul. Bo'sh qoldirsangiz — to'liq to'langan deb yoziladi; kamroq yozsangiz, qolgani unga qarz bo'lib turadi. Bu pul kassadan chiqmaydi."

const DONA_HOLAT = { bosh: "Bo'sh", tamirda: "Ta'mirda", yoqolgan: "Yo'qolgan", arxiv: 'Arxiv' }

// 4.4: aksessuarlar faqat ijaraga; har bir dona alohida raqamli yorliq bilan hisobga olinadi.
// Ko'rinish liboslar bilan bir xil (Point uslubi): kichik ko'rsatkichlar, bitta asboblar paneli, ustunli jadval,
// qator bosilganda tafsilot shu joyda ochiladi; qo'shish — oynada.
// Kanvas (LibosBolimShisha, «Aksessuarlar»): 4 ko'rsatkich, tasdiq kutayotganlar qatori; chapda ro'yxat — har dona rangli katak,
// o'ngda tanlangan aksessuar: narx, donalar kimda, ta'mir va dona qo'shish. Keng ekranda birinchisi o'zi tanlanadi.
const BU_YIL = new Date().getFullYear()
const RANG = { bosh: "Bo'sh", bron: 'Bron', mijozda: 'Mijozda', tamirda: "Ta'mirda", yoqolgan: "Yo'qolgan" }
const sanaQisqa = (s) => { const [, m, d] = String(s).split('-'); return `${Number(d)} ${OYLAR[Number(m) - 1].toLowerCase()}` }

export default function AksessuarBolimi({ rahbar }) {
  const [royxat, setRoyxat] = useState([])
  const [kats, setKats] = useState(null)  // null — hali yuklanmagan (ogohlantirish yuklanayotganda chiqmasin)
  const [ochiq, setOchiq] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [kat, setKat] = useState('')
  const [holat, setHolat] = useState('faol')
  const [q, setQ] = useState('')
  const [oyna, setOyna] = useState(false)
  const [tasdiqOchiq, setTasdiqOchiq] = useState(false)
  const [keng, setKeng] = useState(() => window.matchMedia('(min-width: 1024px)').matches)
  useEffect(() => {
    const m = window.matchMedia('(min-width: 1024px)'); const h = (e) => setKeng(e.matches)
    m.addEventListener('change', h); return () => m.removeEventListener('change', h)
  }, [])

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
  const hol = faol.flatMap((a) => a.dona_holatlari || [])
  const sana = (h) => hol.filter((x) => x === h).length
  const joriyId = ochiq ?? (keng ? korinadi[0]?.id ?? null : null)

  return (
    <div className="stack aks-sahifa">
      {/* «Aksessuar qo'shish» — tablar qatorining o'ng tomonida (kanvas) */}
      <BoshAmal>
        <button type="button" className="bosh-tugma" disabled={!kats?.length} onClick={() => setOyna(true)}>
          <NavIkona nom="qosh" className="tugma-ikon" />Aksessuar qo'shish
        </button>
      </BoshAmal>
      {/* aksessuar ochiq bo'lsa xabar uning ichida chiqadi */}
      {xabar.matn && joriyId == null && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}
      {kats?.length === 0 && (
        <p className="ogohlantirish">Aksessuar kategoriyasi yo'q{rahbar ? ": «Liboslar» bo'limidagi «Kategoriyalar» tugmasi orqali turi «Aksessuar» bo'lgan kategoriya yarating." : '. Rahbar kategoriya yaratishi kerak.'}</p>
      )}

      <section className="dash-kpi libos-kpi" aria-label="Aksessuar ko'rsatkichlari">
        <KpiFiltr nom="Jami donalar" son={hol.length} ikon="toj" rang="tilla" izoh={`${faol.length} tur aksessuar`} />
        <KpiFiltr nom="Ijaraga tayyor" son={sana('bosh')} ikon="bajarildi" rang="yashil" izoh="hozir javonda, bo'sh" />
        <KpiFiltr nom="Band" son={sana('bron') + sana('mijozda')} ikon="mijoz" rang="kok" izoh={`${sana('bron')} bron · ${sana('mijozda')} mijozda`} />
        <KpiFiltr nom="Ta'mirda yoki yo'qolgan" son={sana('tamirda') + sana('yoqolgan')} ikon="tamir" rang="pushti"
          izoh={`${sana('tamirda')} ta'mirda · ${sana('yoqolgan')} yo'qolgan`} />
      </section>

      {rahbar && kutayotgan.length > 0 && (
        <div className="aks-tasdiq-qator">
          <NavIkona nom="soat" className="tugma-ikon" />
          <p><b>Tasdiq kutmoqda:</b> {kutayotgan.map((a) => `${a.nomi} (${a.kod}) · ${a.donalar_soni} dona${a.qoshgan ? ` · ${a.qoshgan} qo'shdi` : ''}`).join('; ')} — narx va tannarxni tasdiqlagach ijaraga chiqadi.</p>
          <button type="button" className="havola" aria-expanded={tasdiqOchiq} onClick={() => setTasdiqOchiq(!tasdiqOchiq)}>{tasdiqOchiq ? 'Yopish' : 'Tasdiqlash →'}</button>
        </div>
      )}
      {rahbar && tasdiqOchiq && kutayotgan.length > 0 && (
        <section className="blok diqqat-blok">
          <h3>Tasdiq kutmoqda ({kutayotgan.length})</h3>
          {kutayotgan.map((a) => (
            <Tasdiq key={a.id} a={a} onYuborish={(b) => bajar(() => aksessuarTasdiq(a.id, b), `${a.nomi} tasdiqlandi.`)} />
          ))}
        </section>
      )}

      {oyna && kats?.length > 0 && (
        <Oyna sarlavha="Aksessuar qo'shish" onYop={() => setOyna(false)}>
          <Forma kats={kats} rahbar={rahbar} ybs={ybs}
            onYuborish={async (b) => {
              const ok = await bajar(() => aksessuarYarat(b), rahbar ? "Aksessuar qo'shildi." : "Aksessuar rahbar tasdig'iga yuborildi.")
              if (ok) setOyna(false)
              return ok
            }} />
        </Oyna>
      )}

      <div className={`aks-ikki${joriyId == null ? ' bitta' : ''}`}>
        <section className="blok aks-royxat" aria-label="Aksessuarlar ro'yxati">
          <div className="aks-asbob">
            <label className="qidiruv-maydon">
              <NavIkona nom="qidiruv" className="tugma-ikon" />
              <input type="search" className="jadval-qidiruv" placeholder="Nomi yoki kodi: FT, TJ…" aria-label="Aksessuar qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
            </label>
            {katNomlari.length > 1 && (
              <select className="kichik-tanlov" value={kat} aria-label="Kategoriya" onChange={(e) => setKat(e.target.value)}>
                <option value="">Hamma turlar</option>
                {katNomlari.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
            )}
            <select className="kichik-tanlov" value={holat} aria-label="Holat" onChange={(e) => setHolat(e.target.value)}>
              <option value="faol">Faol</option><option value="arxiv">Arxiv</option><option value="hammasi">Hammasi</option>
            </select>
            <span className="aks-maslahat">bosing — o'ngda donalari</span>
          </div>
          {korinadi.length === 0 ? (
            <p className="malumot jadval-bosh">{royxat.length === 0 ? "Hali aksessuar yo'q — birinchisini qo'shing." : "Bu filtr bo'yicha aksessuar yo'q."}</p>
          ) : (
            <Tasma className="jadval-ora" pastki={48}>
              <table className="aks-jadval">
                <thead><tr><th>Aksessuar</th><th>Donalar</th><th className="ong">Tayyor</th><th className="ong">Ijara narxi</th><th aria-hidden="true" /></tr></thead>
                <tbody>
                  {korinadi.map((a) => {
                    const band = (a.dona_holatlari || []).filter((h) => h === 'bron' || h === 'mijozda').length
                    return (
                      <tr key={a.id} className={joriyId === a.id ? 'tanlangan' : ''} onClick={() => { setOchiq(a.id); setXabar({ turi: '', matn: '' }) }}>
                        <td>
                          <button type="button" className="zakaz-katak" aria-pressed={joriyId === a.id}>
                            {a.rasm ? <img className="aks-eskiz" src={a.rasm} alt="" /> : <span className="aks-plitka" aria-hidden="true">{a.kod}</span>}
                            <span className="zakaz-nom"><b>{a.nomi}</b><small>{a.kod} · {a.donalar_soni} dona{a.holat === 'arxiv' ? ' · arxivda' : ''}</small></span>
                          </button>
                        </td>
                        <td>
                          <span className="aks-katakchalar" role="img" aria-label={(a.dona_holatlari || []).map((h) => RANG[h]).join(', ') || "dona yo'q"}>
                            {(a.dona_holatlari || []).map((h, i) => <i key={i} className={`aks-k ${h}`} />)}
                          </span>
                        </td>
                        <td className="ong"><b>{Math.max(0, a.yaroqli_donalar - band)} / {a.donalar_soni}</b></td>
                        <td className="ong">{guruhla(a.ijara_narxi)}</td>
                        <td className="aks-chevron" aria-hidden="true"><NavIkona nom="ong" className="tugma-ikon" /></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </Tasma>
          )}
          <div className="aks-izohlar" aria-hidden="true">
            {Object.entries(RANG).map(([k, nom]) => <span key={k}><i className={`aks-k ${k}`} />{nom}</span>)}
          </div>
        </section>
        {joriyId != null && (
          <Tafsilot key={joriyId} id={joriyId} rahbar={rahbar} bajar={bajar} ybs={ybs} xabar={xabar}
            onYop={keng ? null : () => setOchiq(null)} />
        )}
      </div>
    </div>
  )
}

function Tafsilot({ id, rahbar, bajar, ybs = [], xabar, onYop }) {
  const [a, setA] = useState(null)
  const [narx, setNarx] = useState('')
  const [narxOchiq, setNarxOchiq] = useState(false)
  const [forma, setForma] = useState(null)  // 'tamir' | 'dona' — panel pastidagi ikki tugma ochadigan forma
  const [donaOchiq, setDonaOchiq] = useState(null)
  const yukla = useCallback(() => aksessuarTafsilot(id).then((d) => { setA(d); setNarx(d.ijara_narxi) }), [id])
  const [yuklashXato, setYuklashXato] = useState('')
  // Xato jimgina yutilmasin: aks holda «Yuklanmoqda…» abadiy turardi (B-35)
  useEffect(() => { yukla().catch((e) => setYuklashXato(xatoMatni(e))) }, [yukla])
  // Qaytarib bo'lmaydigan amallar tasdiq bilan (B-07): donani «Yo'qolgan»/«Arxiv» qilish, aksessuarni arxivlash
  const [surov, setSurov] = useState(null)  // { sarlavha, matn, tugma, fn, ok }
  const amal = async (fn, ok) => { const r = await bajar(fn, ok); if (r) await yukla(); return r }
  const fayl = useRef(null)
  const rasmFayl = useRef(null)
  const [fil, setFil] = useState([])
  useEffect(() => { filiallar().then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  const [manekinOyna, setManekinOyna] = useState(false)
  if (!a) return <section className="blok aks-tafsilot">{yuklashXato ? <p className="xato">{yuklashXato}</p> : <p className="malumot">Yuklanmoqda…</p>}</section>
  const donaMatni = (d) => {
    if (d.tamir) return `${d.tamir.ish_turi}${d.tamir.kim ? ` · ${d.tamir.kim}` : ''} · ${d.tamir.kunlar} kundan beri`
    if (d.holat === 'yoqolgan') return "Sanoqda topilmagan"
    if (d.holat === 'arxiv') return 'Arxivda'
    if (d.band?.turi === 'mijozda') return `#${d.band.zakaz} ${d.band.mijoz}`
    if (d.band?.turi === 'bron') return `Javonda · bron #${d.band.zakaz}, ${sanaQisqa(d.band.sana)}`
    return "Javonda"
  }
  const donaYorliq = (d) => (d.tamir || d.holat === 'tamirda' ? ['ogoh', "Ta'mirda"] : d.holat === 'yoqolgan' ? ['qizil', "Yo'qolgan"]
    : d.holat === 'arxiv' ? ['yopiq', 'Arxiv'] : d.band?.turi === 'mijozda' ? ['kok', 'Mijozda'] : d.band?.turi === 'bron' ? ['tilla', 'Bron'] : ['yashil', "Bo'sh"])
  return (
    <section className="blok aks-tafsilot" aria-label={`${a.nomi} tafsiloti`}>
      {surov && (
        <TasdiqOyna sarlavha={surov.sarlavha} matn={surov.matn} tugma={surov.tugma}
          onYop={() => setSurov(null)} onTasdiq={() => { const x = surov; setSurov(null); amal(x.fn, x.ok) }} />
      )}
      {xabar.matn && <p className={`aks-xabar ${xabar.turi === 'xato' ? 'xato' : 'malumot'}`} role="status">{xabar.matn}</p>}
      <div className="aks-t-bosh">
        {a.rasm_katta ? <img className="aks-rasm" src={a.rasm_katta} alt={a.nomi} /> : <span className="aks-plitka katta" aria-hidden="true">{a.kod}</span>}
        <div>
          <h3>{a.nomi}</h3>
          <p>{a.kod} · {a.donalar.length} dona · {a.kategoriya}{a.holat === 'arxiv' ? ' · arxivda' : ''}</p>
        </div>
        {onYop && <button type="button" className="ikon-tugma" aria-label="Yopish" onClick={onYop}><NavIkona nom="yop" className="tugma-ikon" /></button>}
      </div>
      <div className="aks-t-qatorlar">
        <div className="aks-t-q">
          <span>Ijara narxi{rahbar && <> · <button type="button" className="havola" aria-expanded={narxOchiq} onClick={() => setNarxOchiq(!narxOchiq)}>o'zgartirish</button></>}</span>
          <b>{som(a.ijara_narxi)}</b>
        </div>
        {rahbar && narxOchiq && (
          <div className="ixcham-forma r2a-narx">
            <label>Ijara narxi<SummaInput value={narx} onChange={(e) => setNarx(e.target.value)} /></label>
            <button className="kichik" onClick={() => amal(() => aksessuarOzgartir(id, { ijara_narxi: Number(narx) }), 'Narx saqlandi.').then((ok) => ok && setNarxOchiq(false))}>Saqlash</button>
          </div>
        )}
        {rahbar && a.tannarx != null && <div className="aks-t-q"><span>Tannarx, 1 dona · <small>faqat rahbarga</small></span><b className="soz-mute">{som(a.tannarx)}</b></div>}
        <div className="aks-t-q"><span>{BU_YIL} yilda ijaraga berildi</span><b>{a.bu_yil_berildi ?? 0} marta</b></div>
      </div>

      <div className="aks-donalar" role="list" aria-label="Donalar">
        {a.donalar.map((d) => {
          const [tur, nom] = donaYorliq(d)
          return (
            <div key={d.id} role="listitem" className={`dona aks-dona-q${d.holat !== 'bosh' ? ' dona-yaroqsiz' : ''}`}>
              <b>{d.yorliq}</b>
              <span className="aks-dona-matn">{donaMatni(d)}{fil.length > 0 && d.filial ? ` · ${fil.find((f) => f.id === d.filial)?.nomi || ''}` : ''}</span>
              {rahbar ? (
                <button type="button" className={`soz-holat ${tur}`} aria-expanded={donaOchiq === d.id} title="Holat va filialni o'zgartirish"
                  onClick={() => setDonaOchiq(donaOchiq === d.id ? null : d.id)}>{nom}</button>
              ) : <span className={`soz-holat ${tur}`}>{nom}</span>}
              {rahbar && donaOchiq === d.id && (
                <div className="aks-dona-amal">
                  {/* Ta'mirga berish va undan qaytarish faqat «Ta'mirga berish» orqali (xarajat va jurnal yoziladi) */}
                  <select value={d.holat} disabled={d.holat === 'tamirda'} title={d.holat === 'tamirda' ? "Avval ta'mirni tugating" : undefined}
                    aria-label={`${d.yorliq} holati`}
                    onChange={(e) => {
                      const h = e.target.value
                      const fn = () => donaHolati(d.id, h)
                      if (h === 'yoqolgan' || h === 'arxiv') {
                        setSurov({ sarlavha: `${d.yorliq} «${DONA_HOLAT[h]}» deb belgilansinmi?`, tugma: `Ha, ${DONA_HOLAT[h].toLowerCase()}`, fn, ok: `${d.yorliq}: holat o'zgardi.`,
                          matn: "Dona ijaraga chiqmaydi va sanoqda hisobga olinmaydi. Topilsa, holatini qaytadan «Bo'sh» qilasiz." })
                      } else amal(fn, `${d.yorliq}: holat o'zgardi.`)
                    }}>
                    {Object.entries(DONA_HOLAT).filter(([k]) => k !== 'tamirda' || d.holat === 'tamirda')
                      .map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                  {fil.length > 0 && (
                    <select value={d.filial || ''} aria-label={`${d.yorliq} filiali`}
                      onChange={(e) => amal(() => donaFilial(d.id, e.target.value ? Number(e.target.value) : null), `${d.yorliq}: filial saqlandi.`)}>
                      <option value="">filialsiz</option>
                      {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
                    </select>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
      <DonaTamir a={a} rahbar={rahbar} amal={amal} ochiq={forma === 'tamir'} />

      <div className="aks-t-tugmalar">
        <button type="button" className="ikkinchi kichik" aria-expanded={forma === 'tamir'} onClick={() => setForma(forma === 'tamir' ? null : 'tamir')}>
          <Belgi nom="tamir" className="tugma-ikon" />Ta'mirga berish
        </button>
        {rahbar && (
          <button type="button" className="ikkinchi kichik" aria-expanded={forma === 'dona'} onClick={() => setForma(forma === 'dona' ? null : 'dona')}>
            <NavIkona nom="qosh" className="tugma-ikon" />Dona qo'shish
          </button>
        )}
      </div>
      {rahbar && forma === 'dona' && <DonaQoshish a={a} ybs={ybs} onYuborish={(b) => amal(() => donalarQosh(id, b), "Donalar qo'shildi.")} />}
      <p className="aks-t-izoh"><NavIkona nom="yordam" className="tugma-ikon" />Har dona yorlig'idagi kod bilan yuradi — zakazda qaysi biri berilgani, sanoqda qaysi biri yo'qligi shu koddan ko'rinadi.</p>

      {/* Kam ishlatiladigan amallar: rasm va manekin (yangi zakaz kartochkasi uchun), partiyalar, arxiv */}
      <div className="aks-t-boshqa">
        <input ref={rasmFayl} type="file" accept="image/jpeg,image/png,image/webp" hidden
          onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) amal(() => aksessuarRasmYukla(id, f), 'Rasm saqlandi.') }} />
        <input ref={fayl} type="file" accept="image/jpeg,image/png,image/webp" hidden
          onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) amal(() => aksessuarManekinYukla(id, f), 'Manekin rasmi tayyor.') }} />
        <div className="soz-tugmalar">
          <button type="button" className="havola" onClick={() => rasmFayl.current.click()}>{a.rasm ? 'Rasmni almashtirish' : 'Rasm yuklash'}</button>
          {/* FT-5.2: fonsiz rasm manekinda libos ustidan qo'yiladi */}
          <button type="button" className="havola" onClick={() => fayl.current.click()}>{a.manekin ? 'Manekin rasmini almashtirish' : 'Manekin uchun rasm'}</button>
          {a.manekin && <button type="button" className="havola" onClick={() => setManekinOyna(true)}>Manekinda joylash</button>}
          {a.rasm && rahbar && <button type="button" className="havola soz-mute-havola" onClick={() => amal(() => aksessuarRasmOchir(id), 'Rasm olib tashlandi.')}>Rasmni olib tashlash</button>}
          {a.manekin && <button type="button" className="havola soz-mute-havola" onClick={() => amal(() => aksessuarManekinOchir(id), 'Manekin rasmi olib tashlandi.')}>Manekin rasmini olib tashlash</button>}
        </div>
        {rahbar && <Partiyalar a={a} ybs={ybs} amal={amal} />}
        {rahbar && (
          <button type="button" className="havola soz-mute-havola" onClick={() => (a.holat === 'arxiv'
            ? amal(() => aksessuarOzgartir(id, { holat: 'faol' }), "Holat o'zgardi.")
            : setSurov({ sarlavha: `${a.nomi} arxivga o'tkazilsinmi?`, tugma: 'Ha, arxivga', ok: "Holat o'zgardi.",
              fn: () => aksessuarOzgartir(id, { holat: 'arxiv' }),
              matn: "Aksessuar ro'yxatdan yashiriladi va yangi zakazga tanlanmaydi. Keyin «Arxivdan chiqarish» mumkin." }))}>
            {a.holat === 'arxiv' ? 'Arxivdan chiqarish' : "Arxivga o'tkazish"}
          </button>
        )}
      </div>
      {manekinOyna && a.manekin && (
        <Manekin sarlavha={a.nomi} faylNomi={a.kod} onYopish={() => setManekinOyna(false)}
          qatlamlar={[{ kalit: 'aksessuar', nomi: a.nomi, ...a.manekin, saqla: (b) => aksessuarManekinSaqla(id, b) }]}
          onSaqlandi={() => yukla()} />
      )}
    </section>
  )
}

// Yangi donalar — alohida partiya: o'z narxi va yetkazib beruvchisi bilan (eski donalar qarzi o'zgarmaydi)
function DonaQoshish({ a, ybs, onYuborish }) {
  const [f, setF] = useState({ soni: '1', narx: '', yb: '', tolandi: '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const jami = Number(f.narx || a.tannarx || 0) * Number(f.soni || 0)
  return (
    <div className="aks-forma soz-tahrir" role="region" aria-label="Dona qo'shish">
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
    </div>
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
function DonaTamir({ a, rahbar, amal, ochiq }) {
  const [dona, setDona] = useState('')
  const [ish, setIsh] = useState('')
  const [kim, setKim] = useState('')
  const [narx, setNarx] = useState({})
  const tamirda = a.donalar.filter((d) => d.tamir)
  const boshlar = a.donalar.filter((d) => d.holat === 'bosh')
  if (!ochiq && tamirda.length === 0) return null
  return (
    <div className="aks-forma soz-tahrir" role="region" aria-label="Ta'mir">
      <div className="stack">
        {tamirda.length > 0 && <h4 className="r2-kichik-sarlavha">Ta'mirda ({tamirda.length})</h4>}
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
        {!ochiq ? null : boshlar.length > 0 ? (
          <>
            <select value={dona} onChange={(e) => setDona(e.target.value)} aria-label="Dona">
              <option value="">Donani tanlang</option>
              {boshlar.map((d) => <option key={d.id} value={d.id}>{d.yorliq}</option>)}
            </select>
            <label>Nima qilinadi<input value={ish} maxLength={300} onChange={(e) => setIsh(e.target.value)} /></label>
            <label>Usta yoki ustaxona<input value={kim} maxLength={200} onChange={(e) => setKim(e.target.value)} /></label>
            <button className="ikkinchi" disabled={!dona || !ish.trim()}
              onClick={() => amal(() => donaTamirga(Number(dona), { ish_turi: ish, kim }), "Dona ta'mirga berildi.").then((ok) => { if (ok) { setDona(''); setIsh(''); setKim('') } })}>
              Ta'mirga yuborish
            </button>
          </>
        ) : <p className="malumot">Bo'sh dona yo'q.</p>}
        {!rahbar && ochiq && <p className="malumot">Narx kassadan chiqim bo'ladi (ochiq smena kerak) va rahbar tasdig'ini kutadi.</p>}
      </div>
    </div>
  )
}

function Tasdiq({ a, onYuborish }) {
  const [narx, setNarx] = useState(a.ijara_narxi || '')
  const [tannarx, setTannarx] = useState('')
  return (
    <div className="tasdiq">
      <span><b>{a.kod}</b> {a.nomi} · {a.donalar_soni} dona ({a.qoshgan} qo'shdi, narx {som(a.ijara_narxi)})</span>
      <div className="libos-narxlar">
        <label>Ijara narxi *<SummaInput value={narx} onChange={(e) => setNarx(e.target.value)} /></label>
        <label>Tannarx, 1 dona *<SummaInput value={tannarx} onChange={(e) => setTannarx(e.target.value)} /></label>
      </div>
      <button disabled={narx === '' || tannarx === ''}
        onClick={() => onYuborish({ ijara_narxi: Number(narx), tannarx: Number(tannarx) })}>Tasdiqlash</button>
      {(narx === '' || tannarx === '') && <p className="malumot r2-sabab">To'ldiring: {[narx === '' && 'Ijara narxi', tannarx === '' && 'Tannarx'].filter(Boolean).join(', ')}</p>}
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
        <label>Nomi *<input value={f.nomi || ''} placeholder="masalan: Fata klassik" onChange={set('nomi')} /></label>
        <label>Kod *<input placeholder="masalan: FT" maxLength={10} value={f.kod || ''} onChange={set('kod')} /><Info nom="Kod">Aksessuar turining qisqa kodi. Har donaning yorlig'i shu koddan yasaladi: FT → FT-01, FT-02… Salonda takrorlanmaydi.</Info></label>
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
        {(!f.nomi || !f.kod) && <p className="malumot r2-sabab">To'ldiring: {[!f.nomi && 'Nomi', !f.kod && 'Kod'].filter(Boolean).join(', ')}</p>}
    </div>
  )
}

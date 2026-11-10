import { Fragment, useCallback, useEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import NavIkona from '../components/NavIkona'
import Oyna from '../components/Oyna'
import RasmBlok from '../components/RasmBlok'
import Tasdiq from '../components/Tasdiq'
import RasmTanlash from '../components/RasmTanlash'
import TamirBlok from '../components/TamirBlok'
import AksessuarBolimi from './AksessuarBolimi'
import LibosSanogi from './LibosSanogi'
import YetkazibBeruvchilar from './YetkazibBeruvchilar'
import {
  filiallar, kategoriyalar, kategoriyaOchir, kategoriyaOzgartir, kategoriyaYarat, keyingiArtikul, libosOzgartir, libosPasport, libosRad, libosTasdiq, libosYarat, liboslar, rasmYukla, som, xatoMatni, yetkazibBeruvchilar, guruhla,
} from '../api'
import { OYLAR, bugunIso, kunlarSoni } from '../components/kalendar/sana'
import SummaInput from '../components/SummaInput'
import LibosSiluet from '../components/LibosSiluet'
import KpiFiltr from '../components/KpiFiltr'
import { Belgi } from '../components/ZakazQatorlari'
import { BoshAmal, BoshXulosa } from '../components/BoshJoy'

// Ro'yxatda odatda faqat ishlaydigan liboslar; sotilgan/arxiv — holat filtri bilan
const NOFAOL = ['sotildi', 'hisobdan_chiqarildi', 'arxiv']
// «Bo'sh» — ijaraga tayyor: holati bo'sh va hozir mijozda emas. «Mijozda» — berilgan zakazda (B-02)
const HOLAT_FILTR = [['', 'Faol liboslar'], ['bosh', 'Ijaraga tayyor'], ['mijozda', 'Mijozda'], ['xizmatda', "Ta'mir yoki tozalashda"],
  ['tamirda', "Ta'mirda"], ['tozalashda', 'Tozalashda'], ['sotildi', 'Sotilgan'], ['arxiv', 'Arxiv'], ['hammasi', 'Hammasi']]
// Faqat rahbarga: kamchiligi bor liboslar (tannarx yo'q, rasm nisbati mos emas)
const RAHBAR_FILTR = [['tannarxsiz', 'Tannarxi kiritilmagan'], ['rasm', "Rasmi 2:3 emas"]]
const mosHolat = (l, holat) => {
  if (holat === 'hammasi') return true
  if (holat === 'mijozda') return l.mijozda
  if (holat === 'bosh') return l.holat === 'bosh' && !l.mijozda
  if (holat === 'xizmatda') return ['tamirda', 'tozalashda'].includes(l.holat)
  if (holat === 'tannarxsiz') return l.tannarx == null && !NOFAOL.includes(l.holat)
  if (holat === 'rasm') return l.standart_emas > 0 && !NOFAOL.includes(l.holat)
  return holat ? l.holat === holat : !NOFAOL.includes(l.holat)
}
const mlnQisqa = (n) => (n >= 1e6 ? `${(n / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} mln` : som(n))
const kunOy = (s) => (s ? String(s).slice(5, 10).split('-').reverse().join('.') : '')
// Kanvas saralashlari: artikul (standart), ko'p ijaraga berilgan (shu oy), narx, eng yaqin bron
const TARTIBLAR = [['artikul', 'Artikul bo\'yicha'], ['kop', "Ko'p ijaraga berilgan"], ['narx', 'Narxi qimmatdan'], ['bron', 'Yaqin bron']]
function saralash(royxat, tartib) {
  if (tartib === 'kop') return [...royxat].sort((a, b) => (b.bu_oy || 0) - (a.bu_oy || 0))
  if (tartib === 'narx') return [...royxat].sort((a, b) => b.ijara_narxi - a.ijara_narxi)
  if (tartib === 'bron') return [...royxat].sort((a, b) => String(a.keyingi_bron || '9999').localeCompare(String(b.keyingi_bron || '9999')))
  return royxat
}
// «bugun», «ertaga» yoki «15 noyabr»
function kunMatni(sana) {
  const d = kunlarSoni(bugunIso(), sana)
  if (d === 0) return 'bugun'
  if (d === 1) return 'ertaga'
  const [, m, k] = String(sana).split('-').map(Number)
  return `${k} ${OYLAR[m - 1].toLowerCase()}`
}
// kartada «Bron» belgisi — bron bugun yoki ertaga bo'lsa (sotuvchi libosni boshqaga va'da qilmasin)
const yaqinBron = (sana) => Boolean(sana) && kunlarSoni(bugunIso(), sana) <= 1
// O'lchamlar: raqamlilari o'sish tartibida, keyin harfli (S, M, L…)
const olchamTartib = (a, b) => (Number.isNaN(+a) - Number.isNaN(+b)) || (+a - +b) || a.localeCompare(b)
// «i» matnlari: qo'shish va tahrirlash formalarida bir xil
const ZALOG_INFO = "Libos berilganda mijozdan olinadigan garov. Berishda pul garovi summasiga shu son o'zi qo'yiladi. Libos butun qaytsa, garov to'liq qaytariladi; jarima bo'lsa, avval shundan ushlanadi."
const TANNARX_INFO = "Libosni sotib olishga ketgan pul. Faqat rahbarga ko'rinadi. «Libos samaradorligi» hisobotidagi qoplash (tushum ÷ tannarx) va yetkazib beruvchiga qarz shundan hisoblanadi."
const TOLANDI_INFO = "Yetkazib beruvchiga hozir berilgan pul. Bo'sh qoldirsangiz — tannarx to'liq to'langan deb yoziladi; kamroq yozsangiz, qolgani unga qarz bo'lib turadi. Bu pul kassadan chiqmaydi."
const holatSinfi = (h) => ({ bosh: 'bron', tamirda: 'qarz', tozalashda: 'vaqtinchalik', tasdiq_kutilmoqda: 'vaqtinchalik' }[h] || 'qaytarildi')
const HOLAT = {
  bosh: "Bo'sh", tasdiq_kutilmoqda: 'Tasdiq kutilmoqda', tozalashda: 'Tozalashda', tamirda: "Ta'mirda",
  sotildi: 'Sotildi', hisobdan_chiqarildi: 'Hisobdan chiqarildi', arxiv: 'Arxiv',
}

// 4.3: katalog. Tannarx faqat rahbarga ko'rinadi; sotuvchi qo'shgan libos rahbar tasdig'ini kutadi (FT-3.6).
// `onZakaz` (ixtiyoriy) — pasportdagi «#98» zakaz kartasini ochadi; berilmasa raqam oddiy matn
// `yangiOch` — Dashboard «Tezkor amallar»dan kelinganda «Libos qo'shish» oynasi ochiq boshlanadi; oyna yopilgach
// `onYangiYopildi` App'dagi belgini tozalaydi (ichki bo'lim almashib Liboslar qayta yaratilganda qayta ochilmasin)
export default function Katalog({ rahbar, bolim, onZakaz, yangiOch, onYangiYopildi }) {
  return (
    <div className="stack">
      {bolim === 'liboslar' ? <Liboslar rahbar={rahbar} onZakaz={onZakaz} yangiOch={yangiOch} onYangiYopildi={onYangiYopildi} /> : bolim === 'sanoq' ? <LibosSanogi />
        : bolim === 'yetkazib' && rahbar ? <YetkazibBeruvchilar /> : <AksessuarBolimi rahbar={rahbar} />}
    </div>
  )
}

// Keng ekranda (≥1024 px) blok ekranning qolgan balandligiga cheklanadi va ichidan suriladi — sahifa joyida turadi,
// liboslar ro'yxat kabi yuqoriga suriladi (foydalanuvchi so'rovi). Torroq ekranda — oddiy sahifa.
function useEkrangaSigdir(ref, deps) {
  useEffect(() => {
    const hisobla = () => {
      const el = ref.current
      if (!el) return
      if (window.innerWidth < 1024) { el.style.maxHeight = ''; return }
      const tepa = el.getBoundingClientRect().top + window.scrollY
      el.style.maxHeight = `${Math.max(320, window.innerHeight - tepa - 28)}px`
    }
    hisobla()
    window.addEventListener('resize', hisobla)
    return () => window.removeEventListener('resize', hisobla)
  }, deps)  // eslint-disable-line react-hooks/exhaustive-deps
}

function Liboslar({ rahbar, onZakaz, yangiOch, onYangiYopildi }) {
  const torRef = useRef(null)
  const filtrRef = useRef(null)
  const [royxat, setRoyxat] = useState([])
  const [kats, setKats] = useState([])
  const [q, setQ] = useState('')
  const [tanlangan, setTanlangan] = useState(null)
  const [fil, setFil] = useState([])
  const [filial, setFilial] = useState('')
  const [kat, setKat] = useState('')
  const [holat, setHolat] = useState('')
  const [tartib, setTartib] = useState('artikul')  // kanvas: «Ko'p ijaraga berilgan» va boshqa saralashlar
  const [olcham, setOlcham] = useState('')
  const [oyna, setOyna] = useState(yangiOch ? 'yangi' : null) // 'yangi' | 'kategoriya' | null
  useEffect(() => { if (yangiOch && oyna !== 'yangi') onYangiYopildi?.(false) }, [yangiOch, oyna, onYangiYopildi])
  useEffect(() => { filiallar().then((r) => setFil(r.filiallar)).catch(() => {}) }, [])
  const [ybs, setYbs] = useState([])  // yetkazib beruvchilar (faqat rahbar)
  useEffect(() => { if (rahbar) yetkazibBeruvchilar().then(setYbs).catch(() => {}) }, [rahbar])
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

  useEkrangaSigdir(torRef, [royxat.length, xabar.matn])
  useEkrangaSigdir(filtrRef, [royxat.length, xabar.matn])
  const kutayotgan = royxat.filter((l) => l.holat === 'tasdiq_kutilmoqda')
  const libosKats = kats.filter((k) => k.turi === 'libos')
  const katalogda = royxat.filter((l) => l.holat !== 'tasdiq_kutilmoqda')
  const faol = katalogda.filter((l) => !NOFAOL.includes(l.holat))
  const korinadi = saralash(katalogda.filter((l) => (!kat || l.kategoriya === kat) && (!olcham || l.olcham === olcham) && mosHolat(l, holat)), tartib)
  const ortacha = faol.length ? Math.round(faol.reduce((s, l) => s + l.ijara_narxi, 0) / faol.length) : 0
  const katNomlari = [...new Set(katalogda.map((l) => l.kategoriya))].sort()
  const olchamlar = [...new Set(faol.map((l) => (l.olcham || '').trim()).filter(Boolean))].sort(olchamTartib)
  const mijozda = faol.filter((l) => l.mijozda).length
  const tayyor = faol.filter((l) => l.holat === 'bosh' && !l.mijozda).length
  const tamirda = faol.filter((l) => l.holat === 'tamirda').length
  const tozalashda = faol.filter((l) => l.holat === 'tozalashda').length
  const yaqinQaytish = faol.filter((l) => l.mijozda && l.qaytish).map((l) => l.qaytish).sort()[0]
  // Filtr ustuni sonlari — boshqa tanlangan filtrlar hisobga olingan holda (kategoriya: holat+o'lcham; holat: kategoriya+o'lcham)
  const katSoni = (k) => katalogda.filter((l) => (!k || l.kategoriya === k) && (!olcham || l.olcham === olcham) && mosHolat(l, holat)).length
  const holatSoni = (h) => katalogda.filter((l) => (!kat || l.kategoriya === kat) && (!olcham || l.olcham === olcham) && mosHolat(l, h)).length
  const holatFiltrlari = [...HOLAT_FILTR, ...(rahbar ? RAHBAR_FILTR : [])]
  const kpiBos = (h) => setHolat(holat === h ? '' : h)
  const tannarxsiz = rahbar ? faol.filter((l) => l.tannarx == null).length : 0
  const rasmiMosEmas = rahbar ? faol.filter((l) => l.standart_emas > 0).length : 0

  return (
    <div className="stack libos-sahifa">
      {/* Bo'lim boshidagi xulosa (kanvas «25 ta libos · bugun 14 tasi bo'sh») */}
      {faol.length > 0 && <BoshXulosa>{`${faol.length} ta libos · ${tayyor} tasi ijaraga tayyor${mijozda ? `, ${mijozda} tasi mijozda` : ''}`}</BoshXulosa>}
      {/* libos ochiq bo'lsa xabar uning ichida chiqadi — tugmalar pastda, tepadagi xabar ko'rinmay qolardi */}
      {xabar.matn && tanlangan === null && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'}>{xabar.matn}</p>}

      {/* Katalog holati bir qarashda (maket uslubi): kartalar — holat filtri, yana bosilsa «Faol liboslar» */}
      <section className="dash-kpi libos-kpi kpi-filtrlar" aria-label="Liboslar ko'rsatkichlari">
        <KpiFiltr nom="Faol liboslar" son={faol.length} ikon="libos" rang="tilla" izoh={`o'rtacha ijara ${mlnQisqa(ortacha)}`}
          tanlangan={holat === ''} onBos={() => setHolat('')} />
        <KpiFiltr nom="Ijaraga tayyor" son={tayyor} ikon="bajarildi" rang="yashil" tanlangan={holat === 'bosh'} onBos={() => kpiBos('bosh')}
          izoh={faol.length ? `faollarning ${Math.round((tayyor * 100) / faol.length)}%` : "hali libos yo'q"} />
        <KpiFiltr nom="Mijozda" son={mijozda} ikon="mijoz" rang="kok" tanlangan={holat === 'mijozda'} onBos={() => kpiBos('mijozda')}
          izoh={yaqinQaytish ? `eng yaqin qaytishi ${kunOy(yaqinQaytish)}` : 'hammasi salonda'} />
        <KpiFiltr nom="Ta'mir va tozalashda" son={tamirda + tozalashda} ikon="tamir" rang="pushti" tanlangan={holat === 'xizmatda'}
          onBos={() => kpiBos('xizmatda')} izoh={`ta'mir ${tamirda} · tozalash ${tozalashda}`} />
      </section>
      {/* Kamchiliklar kartochkalarda emas — statlar ostida bitta qator (B-13, B-17) */}
      {(tannarxsiz > 0 || rasmiMosEmas > 0) && (
        <p className="malumot r2-katalog-eslatma">
          {tannarxsiz > 0 && <span>{tannarxsiz} ta libosning tannarxi kiritilmagan <button type="button" className="havola" onClick={() => setHolat('tannarxsiz')}>Ko'rsatish</button></span>}
          {rasmiMosEmas > 0 && <span>{rasmiMosEmas} ta libosning rasmini tik (2:3) qilib qayta olish kerak <button type="button" className="havola" onClick={() => setHolat('rasm')}>Ko'rsatish</button></span>}
        </p>
      )}

      {/* C-25: sotuvchi ham ko'radi — o'zi qo'shgan libos «yo'qolib qolmaydi» va takror qo'shilmaydi; rahbarda — tasdiq yoki rad */}
      {kutayotgan.length > 0 && (rahbar ? (
        <section className="blok diqqat-blok">
          <h3>Tasdiq kutmoqda ({kutayotgan.length})</h3>
          {kutayotgan.map((l) => (
            <TasdiqForma key={l.id} libos={l} rahbar={rahbar} onRasm={yukla}
              onYuborish={(b) => bajar(() => libosTasdiq(l.id, b), `${l.artikul} katalogga chiqdi.`)}
              onRad={(sabab) => bajar(() => libosRad(l.id, sabab), `${l.artikul} rad etildi — arxivga o'tdi.`)} />
          ))}
        </section>
      ) : (
        <section className="blok diqqat-blok r3k-kutayotgan">
          <h3>Rahbar tasdig'ini kutmoqda ({kutayotgan.length})</h3>
          <p className="malumot">Bu liboslar rahbar narx va tannarxni tasdiqlagach katalogga chiqadi. Qayta qo'shmang.</p>
          <ul>
            {kutayotgan.map((l) => (
              <li key={l.id}><b>{l.artikul}</b> {l.nomi}<span className="malumot"> · {l.kategoriya}{l.olcham ? `, ${l.olcham}` : ''} · {l.qoshgan || '—'} qo'shdi</span></li>
            ))}
          </ul>
        </section>
      ))}

      {oyna === 'yangi' && (
        <Oyna sarlavha="Libos qo'shish" onYop={() => setOyna(null)} yon ikon="katalog"
          izoh={rahbar ? "Rahbar qo'shgani darhol katalogga chiqadi" : "Rahbar narx va tannarxni tasdiqlagach katalogga chiqadi"}>
          <LibosForma kats={libosKats} rahbar={rahbar} ybs={ybs} onBekor={() => setOyna(null)}
            olchamlar={[...new Set(royxat.map((l) => l.olcham).filter(Boolean))].sort((a, b) => (Number(a) || 999) - (Number(b) || 999) || a.localeCompare(b)).slice(0, 8)}
            onYuborish={async (b, rasmlar) => {
              // libos saqlangach tanlangan rasmlar ketma-ket yuklanadi; birortasi o'tmasa — libos qoladi, xabarda aytiladi
              let otmadi = 0
              const ok = await bajar(async () => {
                const l = await libosYarat(b)
                for (const f of rasmlar) { try { await rasmYukla(l.id, f) } catch { otmadi++ } }
              }, rahbar ? "Libos katalogga qo'shildi." : "Libos rahbar tasdig'iga yuborildi.")
              if (ok && otmadi) setXabar({ turi: 'xato', matn: `Libos qo'shildi, lekin ${otmadi} ta rasm yuklanmadi — libosni ochib qayta qo'shing.` })
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

      <div className="libos-joy">
      {/* Keng ekranda chapda filtr ustuni (maket: kategoriya, o'lcham, holat — yonida soni); torroqda — asboblar panelidagi tablar */}
      <aside className="blok libos-filtr" aria-label="Filtrlar" ref={filtrRef}>
        <div className="libos-filtr-guruh">
          <h4>Kategoriya</h4>
          <ul>
            {[['', 'Hammasi'], ...katNomlari.map((k) => [k, k])].map(([k, nom]) => (
              <li key={k || 'hammasi'}>
                <button type="button" className="filtr-qator" aria-pressed={kat === k} onClick={() => setKat(k)}>
                  <span>{nom}</span><small>{katSoni(k)}</small>
                </button>
              </li>
            ))}
          </ul>
        </div>
        {olchamlar.length > 1 && (
          <div className="libos-filtr-guruh">
            <h4>O'lcham</h4>
            <div className="r2-olcham-chiplar" role="group" aria-label="O'lcham">
              {['', ...olchamlar].map((o) => (
                <button key={o || 'hammasi'} type="button" className={`r2-chip${olcham === o ? ' faol' : ''}`} aria-pressed={olcham === o}
                  onClick={() => setOlcham(o)}>{o || 'Hammasi'}</button>
              ))}
            </div>
          </div>
        )}
        <div className="libos-filtr-guruh">
          <h4>Holat</h4>
          <ul>
            {/* soni 0 bo'lganlar yashirin (tanlangani va «Faol»/«Hammasi»dan tashqari); «Ta'mir yoki tozalashda» — faqat kartada */}
            {holatFiltrlari.filter(([k]) => k !== 'xizmatda' && (k === holat || k === '' || k === 'hammasi' || holatSoni(k) > 0)).map(([k, nom]) => (
              <li key={k || 'faol'}>
                <button type="button" className="filtr-qator" aria-pressed={holat === k} onClick={() => setHolat(k)}>
                  <span>{nom}</span><small>{holatSoni(k)}</small>
                </button>
              </li>
            ))}
          </ul>
        </div>
        {(kat || olcham || holat) && (
          <button type="button" className="havola libos-filtr-tozala" onClick={() => { setKat(''); setOlcham(''); setHolat('') }}>
            <Belgi nom="filtr" className="tugma-ikon" />Filtrlarni tozalash
          </button>
        )}
      </aside>
      <section className="blok jadval-panel">
        {/* Asboblar paneli: qidiruv va amallar; kategoriya tablari, holat va o'lcham — faqat filtr ustuni yo'q (tor) ekranda */}
        <div className="jadval-asboblar">
          <div className="tezkor-tablar tor-filtr" role="tablist" aria-label="Kategoriya">
            {[['', 'Hammasi'], ...katNomlari.map((k) => [k, k])].map(([k, nom]) => (
              <button key={k || 'hammasi'} type="button" role="tab" aria-selected={kat === k} className={kat === k ? 'faol' : ''} onClick={() => setKat(k)}>{nom}</button>
            ))}
          </div>
          <select className="kichik-tanlov tor-filtr" value={holat} aria-label="Holat" onChange={(e) => setHolat(e.target.value)}>
            {holatFiltrlari.map(([k, nom]) => <option key={k} value={k}>{nom}</option>)}
          </select>
          {fil.length > 0 && (
            <select className="kichik-tanlov" value={filial} aria-label="Filial" onChange={(e) => setFilial(e.target.value)}>
              <option value="">Barcha filiallar</option>
              {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
            </select>
          )}
          <label className="qidiruv-maydon libos-qidiruv">
            <NavIkona nom="qidiruv" className="tugma-ikon" />
            <input type="search" className="jadval-qidiruv" placeholder="Libos nomi yoki artikul" aria-label="Libos qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          <select className="kichik-tanlov" value={tartib} aria-label="Saralash" onChange={(e) => setTartib(e.target.value)}>
            {TARTIBLAR.map(([k, nom]) => <option key={k} value={k}>{nom}</option>)}
          </select>
          {rahbar && <button type="button" className="ikkinchi kichik" onClick={() => setOyna('kategoriya')}>Kategoriyalar</button>}
          {/* «Libos qo'shish» — kanvasdagidek bo'lim boshida, tablar qatorining o'ngida (BoshAmal) */}
          <BoshAmal><button type="button" className="bosh-tugma" onClick={() => setOyna('yangi')}><NavIkona nom="qosh" className="tugma-ikon" />Libos qo'shish</button></BoshAmal>
        </div>
        {/* O'lcham chiplari: «44 o'lchamda nima bor?» — bir bosishda (2 va undan ko'p o'lcham bo'lsa) */}
        {olchamlar.length > 1 && (
          <div className="r2-olcham-chiplar tor-filtr" role="group" aria-label="O'lcham">
            <span className="malumot">O'lcham</span>
            {['', ...olchamlar].map((o) => (
              <button key={o || 'hammasi'} type="button" className={`r2-chip${olcham === o ? ' faol' : ''}`} aria-pressed={olcham === o}
                onClick={() => setOlcham(o)}>{o || 'Hammasi'}</button>
            ))}
          </div>
        )}
        {korinadi.length === 0 && <p className="malumot jadval-bosh">{q || kat || holat || olcham ? 'Bu filtr bo\'yicha libos yo\'q.' : "Hali libos yo'q — birinchi libosni qo'shing."}</p>}
      {/* Butik javoni: tanlangan libos tafsiloti o'z qatoridan keyin butun kenglikda.
          Foydalanuvchi so'rovi: sahifa joyida turadi — keng ekranda kartalar ro'yxat kabi o'z oynasi ichida yuqoriga suriladi (CSS) */}
      <div className="libos-tor panel-ichi" ref={torRef}>
        {korinadi.map((l) => (
          <Fragment key={l.id}>
            <button type="button" className={`libos-karta ${tanlangan === l.id ? 'tanlandi' : ''}`} aria-expanded={tanlangan === l.id}
              onClick={() => { setTanlangan(tanlangan === l.id ? null : l.id); setXabar({ turi: '', matn: '' }) }}>
              <span className="libos-foto">
                {l.rasm ? <img src={l.rasm} alt="" loading="lazy" /> : <LibosSiluet />}
              </span>
              {/* Shisha uslubi: surat chapda (yuz ochiq — belgi suratda emas), o'ngda artikul · kategoriya, nom, xususiyatlar,
                  ijara narxi va holat belgisi */}
              <span className="libos-matn">
                <span className="libos-kat">{l.artikul} · {l.kategoriya}</span>
                <span className="libos-nom">{l.nomi}</span>
                <span className="libos-qatorlar">
                  <span className="libos-qator"><span>O'lcham</span><b>{l.olcham || '—'}</b></span>
                  <span className="libos-qator"><span>Ijara narxi</span><b>{guruhla(l.ijara_narxi)}</b></span>
                  <span className="libos-qator"><span>Bu oy</span><b>{l.bu_oy ? `${l.bu_oy} marta` : '—'}</b></span>
                  <span className="libos-qator"><span>Keyingi bron</span><b>{l.keyingi_bron ? kunMatni(l.keyingi_bron) : '—'}</b></span>
                </span>
                {/* «Bo'sh» — odatiy holat, har kartochkada yozilmaydi; faqat ijaraga chiqmaydigan holat ko'rsatiladi.
                    Mijozdagi libos holati «bo'sh» qoladi — shuning uchun alohida belgi (sotuvchi va'da berib qo'ymasin) */}
                {l.holat !== 'bosh'
                  ? <span className={`holat ${holatSinfi(l.holat)} libos-holat`}>{HOLAT[l.holat]}</span>
                  : l.mijozda ? <span className="holat berildi libos-holat">Mijozda{l.qaytish ? ` · ${kunOy(l.qaytish)} gacha` : ''}</span>
                    : yaqinBron(l.keyingi_bron) && <span className="holat bron libos-holat">Bron · {kunMatni(l.keyingi_bron)}</span>}
              </span>
            </button>
            {tanlangan === l.id && (
              <div className="blok libos-tafsilot varaq">
                <div className="libos-tafsilot-bosh">
                  <h3><b>{l.artikul}</b> {l.nomi}</h3>
                  <button type="button" className="ikkinchi kichik" onClick={() => setTanlangan(null)}>Yopish</button>
                </div>
                {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'} role="status">{xabar.matn}</p>}
                <Tafsilot key={l.id}
                  l={l} rahbar={rahbar} fil={fil} ybs={ybs} kats={libosKats} onRasm={yukla} onZakaz={onZakaz}
                  onSaqla={(b, ok = "O'zgartirildi.") => bajar(() => libosOzgartir(l.id, b), ok)}
                  onYashirildi={(ok) => { setTanlangan(null); setXabar({ turi: 'ok', matn: ok }) }} />
              </div>
            )}
          </Fragment>
        ))}
      </div>
      </section>
      </div>
    </div>
  )
}

function Tafsilot({ l, rahbar, onSaqla, onRasm, onYashirildi, onZakaz, fil = [], ybs = [], kats = [] }) {
  const [f, setF] = useState({ ijara_narxi: l.ijara_narxi, zalog: l.zalog, tannarx: l.tannarx ?? '' })
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  // Joyi va holati — bitta «Saqlash» bilan (avval har select darhol saqlanardi, B-06)
  const [j, setJ] = useState({ filial: l.filial || '', yetkazib_beruvchi: l.yetkazib_beruvchi || '', holat: l.holat })
  // Saqlangach (yoki ta'mirdan keyin) server qiymati o'zgarsa — forma unga moslanadi. Tafsilotni qayta yaratmaymiz:
  // aks holda ichidagi ta'mir/rasm bloklarining xabari («Libos ta'mirga berildi.») o'chib ketardi
  const jAsl = `${l.filial}|${l.yetkazib_beruvchi}|${l.holat}`
  const [jOldin, setJOldin] = useState(jAsl)
  if (jOldin !== jAsl) { setJOldin(jAsl); setJ({ filial: l.filial || '', yetkazib_beruvchi: l.yetkazib_beruvchi || '', holat: l.holat }) }
  const [holatSurov, setHolatSurov] = useState(false)
  const jOzgardi = String(j.filial) !== String(l.filial || '') || String(j.yetkazib_beruvchi) !== String(l.yetkazib_beruvchi || '') || j.holat !== l.holat
  const jTana = () => ({
    ...(String(j.filial) !== String(l.filial || '') ? { filial: j.filial ? Number(j.filial) : null } : {}),
    ...(String(j.yetkazib_beruvchi) !== String(l.yetkazib_beruvchi || '') ? { yetkazib_beruvchi: j.yetkazib_beruvchi ? Number(j.yetkazib_beruvchi) : null } : {}),
    ...(j.holat !== l.holat ? { holat: j.holat } : {}),
  })
  const jSaqla = async () => {
    setHolatSurov(false)
    const yashirinadi = j.holat !== l.holat && NOFAOL.includes(j.holat)
    const filtr = { sotildi: 'Sotilgan', arxiv: 'Arxiv', hisobdan_chiqarildi: 'Hammasi' }[j.holat]
    const ok = yashirinadi ? `${l.artikul} «${HOLAT[j.holat]}» deb belgilandi — endi holat filtridagi «${filtr}» ro'yxatida.` : 'Saqlandi.'
    if (await onSaqla(jTana(), ok) && yashirinadi) onYashirildi?.(ok)
  }
  return (
    <div className="stack">
      <p className="malumot">
        O'lcham: {l.olcham || '—'} · Rang: {l.rang || '—'} · Qo'shgan: {l.qoshgan || '—'}
        {fil.length > 0 && !rahbar && ` · Filial: ${fil.find((x) => x.id === l.filial)?.nomi || 'biriktirilmagan'}`}
      </p>
      <Pasport l={l} rahbar={rahbar} onZakaz={onZakaz} />
      <RasmBlok libosId={l.id} rahbar={rahbar} onOzgardi={onRasm} />
      <TamirBlok libosId={l.id} rahbar={rahbar} onOzgardi={onRasm} />
      {rahbar ? (
        <>
          <div className="libos-narxlar">
            <label>Ijara narxi<SummaInput value={f.ijara_narxi} onChange={set('ijara_narxi')} /></label>
            <label>Garov<SummaInput value={f.zalog} onChange={set('zalog')} /><Info nom="Garov">{ZALOG_INFO}</Info></label>
            <label>Tannarx<SummaInput value={f.tannarx} onChange={set('tannarx')} /><Info nom="Tannarx">{TANNARX_INFO}</Info></label>
          </div>
          <button onClick={() => onSaqla({
            ijara_narxi: Number(f.ijara_narxi), zalog: Number(f.zalog),
            ...(f.tannarx !== '' ? { tannarx: Number(f.tannarx) } : {}),
          })}>Narxlarni saqlash</button>
          <fieldset className="guruh r2-joy-holat">
            <legend>Joyi va holati</legend>
            <div className="libos-narxlar">
              {fil.length > 0 && (
                <label>Filial
                  <select value={j.filial} onChange={(e) => setJ({ ...j, filial: e.target.value })}>
                    <option value="">Biriktirilmagan (hamma filialda)</option>
                    {fil.map((x) => <option key={x.id} value={x.id}>{x.nomi}</option>)}
                  </select>
                </label>
              )}
              {ybs.length > 0 && (
                <label>Qayerdan olingan
                  <select value={j.yetkazib_beruvchi} onChange={(e) => setJ({ ...j, yetkazib_beruvchi: e.target.value })}>
                    <option value="">Ko'rsatilmagan</option>
                    {ybs.map((y) => <option key={y.id} value={y.id}>{y.nomi}</option>)}
                  </select>
                </label>
              )}
              <label>Holati
                <select value={j.holat} onChange={(e) => setJ({ ...j, holat: e.target.value })}>
                  {['bosh', 'sotildi', 'hisobdan_chiqarildi', 'arxiv'].map((h) => (
                    <option key={h} value={h}>{HOLAT[h]}</option>
                  ))}
                  {!['bosh', 'sotildi', 'hisobdan_chiqarildi', 'arxiv'].includes(l.holat) && (
                    <option value={l.holat}>{HOLAT[l.holat]}</option>
                  )}
                </select>
              </label>
            </div>
            <div className="qator">
              <button className="ikkinchi" disabled={!jOzgardi}
                onClick={() => (j.holat !== l.holat && NOFAOL.includes(j.holat) ? setHolatSurov(true) : jSaqla())}>Saqlash</button>
              {jOzgardi && <button type="button" className="havola" onClick={() => setJ({ filial: l.filial || '', yetkazib_beruvchi: l.yetkazib_beruvchi || '', holat: l.holat })}>Bekor qilish</button>}
            </div>
          </fieldset>
          {holatSurov && (
            <Tasdiq sarlavha={`${l.artikul} «${HOLAT[j.holat]}» deb belgilansinmi?`} tugma={`Ha, ${HOLAT[j.holat].toLowerCase()}`}
              matn="Libos faol ro'yxatdan yashiriladi va yangi zakazga tanlanmaydi. Keyin holatni qaytadan «Bo'sh» qilish mumkin."
              onYop={() => setHolatSurov(false)} onTasdiq={jSaqla} />
          )}
          <MalumotTahrir key={`${l.artikul}|${l.nomi}|${l.kategoriya_id}|${l.olcham}|${l.rang}`} l={l} kats={kats}
            onSaqla={(b) => onSaqla(b, "Libos ma'lumoti saqlandi.")} />
        </>
      ) : (
        <p>Garov: {som(l.zalog)}</p>
      )}
    </div>
  )
}

const sanaMatniQisqa = (s) => String(s).slice(0, 10).split('-').reverse().join('.')

// B-05: rahbar libos ma'lumotini tuzatadi (xato o'lcham filtrni buzadi; arxivlab qayta qo'shish — tarix yo'qoladi).
// Har o'zgarish jurnalga yoziladi; artikul salonda takrorlanmaydi (server tekshiradi).
function MalumotTahrir({ l, kats, onSaqla }) {
  const asl = { artikul: l.artikul, nomi: l.nomi, kategoriya: String(l.kategoriya_id), olcham: l.olcham || '', rang: l.rang || '' }
  const [f, setF] = useState(asl)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const ozgargan = Object.keys(asl).filter((k) => f[k].trim() !== asl[k])
  const yetishmaydi = [!f.artikul.trim() && 'Artikul', !f.nomi.trim() && 'Nomi'].filter(Boolean)
  return (
    <details className="amal">
      <summary>Ma'lumotni tahrirlash</summary>
      <div className="stack">
        <div className="libos-narxlar">
          <label>Artikul *<input value={f.artikul} maxLength={50} onChange={set('artikul')} /></label>
          <label>Nomi *<input value={f.nomi} maxLength={200} onChange={set('nomi')} /></label>
        </div>
        <label>Kategoriya
          <select value={f.kategoriya} onChange={set('kategoriya')}>
            {!kats.some((k) => String(k.id) === asl.kategoriya) && <option value={asl.kategoriya}>{l.kategoriya}</option>}
            {kats.map((k) => <option key={k.id} value={k.id}>{k.nomi}</option>)}
          </select>
        </label>
        <div className="libos-narxlar">
          <label>O'lcham<input value={f.olcham} maxLength={20} placeholder="masalan: 44" onChange={set('olcham')} /></label>
          <label>Rang<input value={f.rang} maxLength={50} placeholder="masalan: oq" onChange={set('rang')} /></label>
        </div>
        <button className="ikkinchi" disabled={!ozgargan.length || yetishmaydi.length > 0}
          onClick={() => onSaqla(Object.fromEntries(ozgargan.map((k) => [k, k === 'kategoriya' ? Number(f[k]) : f[k].trim()])))}>
          Saqlash
        </button>
        {yetishmaydi.length > 0 && <p className="malumot r2-sabab">To'ldiring: {yetishmaydi.join(', ')}</p>}
        <p className="malumot">O'zgarishlar jurnalga yoziladi (kim, qachon, eski va yangi qiymat).</p>
      </div>
    </details>
  )
}

function TasdiqForma({ libos, onYuborish, onRad, rahbar, onRasm }) {
  const [narx, setNarx] = useState(libos.ijara_narxi || '')
  const [tannarx, setTannarx] = useState('')
  const [radOyna, setRadOyna] = useState(false)
  const [sabab, setSabab] = useState('')
  return (
    <div className="tasdiq">
      <span><b>{libos.artikul}</b> {libos.nomi} ({libos.qoshgan} qo'shdi, narx {som(libos.ijara_narxi)})</span>
      <RasmBlok libosId={libos.id} rahbar={rahbar} onOzgardi={onRasm} />
      <div className="libos-narxlar">
        <label>Ijara narxi *<SummaInput value={narx} onChange={(e) => setNarx(e.target.value)} /></label>
        <label>Tannarx *<SummaInput value={tannarx} onChange={(e) => setTannarx(e.target.value)} /><Info nom="Tannarx">{TANNARX_INFO}</Info></label>
      </div>
      <div className="qator r3k-tugmalar">
        <button disabled={narx === '' || tannarx === ''}
          onClick={() => onYuborish({ ijara_narxi: Number(narx), tannarx: Number(tannarx) })}>Tasdiqlash</button>
        {onRad && <button type="button" className="ikkinchi" onClick={() => setRadOyna(true)}>Rad etish</button>}
      </div>
      {(narx === '' || tannarx === '') && <p className="malumot r2-sabab">To'ldiring: {[narx === '' && 'Ijara narxi', tannarx === '' && 'Tannarx'].filter(Boolean).join(', ')}</p>}
      {radOyna && (
        <Oyna sarlavha={`${libos.artikul} rad etilsinmi?`} onYop={() => setRadOyna(false)}>
          <div className="stack">
            <p className="malumot">Xato yoki takror yozuv katalogga chiqmaydi: libos arxivga o'tadi, jurnalga yoziladi. {libos.qoshgan || 'Xodim'} buni ro'yxatda ko'rmaydi.</p>
            <label>Sabab (ixtiyoriy)<input value={sabab} maxLength={300} placeholder="masalan: takror yozuv — L012 bilan bir xil" onChange={(e) => setSabab(e.target.value)} /></label>
            <div className="qator">
              <button type="button" className="xavfli" onClick={async () => { if (await onRad(sabab)) setRadOyna(false) }}>Ha, rad etish</button>
              <button type="button" className="ikkinchi" onClick={() => setRadOyna(false)}>Yo'q, qaytish</button>
            </div>
          </div>
        </Oyna>
      )}
    </div>
  )
}

function LibosForma({ kats, rahbar, ybs = [], onYuborish, onBekor, olchamlar = [] }) {
  const [f, setF] = useState({ kategoriya: '' })
  // Rasmlar libos saqlangach yuklanadi; oldindan ko'rish uchun brauzer ichidagi vaqtinchalik manzil
  const [rasmlar, setRasmlar] = useState([])
  const rasmQosh = (fayllar) => setRasmlar((r) => [...r, ...fayllar.map((fayl) => ({ fayl, url: URL.createObjectURL(fayl) }))])
  const rasmOl = (i) => setRasmlar((r) => { URL.revokeObjectURL(r[i].url); return r.filter((_, j) => j !== i) })
  // Sozlama → «Libos artikuli»: avto bo'lsa keyingi raqam ko'rsatiladi, bo'lmasa maydon prefiks bilan boshlanadi
  const [art, setArt] = useState({ prefiks: '', artikul: null })
  useEffect(() => {
    keyingiArtikul().then((a) => {
      setArt(a)
      if (!a.artikul && a.prefiks) setF((x) => (x.artikul ? x : { ...x, artikul: a.prefiks }))
    }).catch(() => {})
  }, [])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const artikul = (f.artikul || '').trim()
  // rahbar qo'shgani darhol katalogga chiqadi — narx va tannarxsiz bo'lmasin (sotuvchinikini rahbar tasdiqlashda to'ldiradi)
  const tannarxBor = f.tannarx !== undefined && f.tannarx !== ''
  const yetishmaydi = [!(art.artikul || (artikul && artikul !== art.prefiks)) && 'Artikul', !f.nomi?.trim() && 'Nomi',
    !(f.kategoriya || kats[0]) && 'Kategoriya', rahbar && !(Number(f.ijara_narxi) > 0) && 'Ijara narxi',
    rahbar && !tannarxBor && 'Tannarx'].filter(Boolean)
  const tayyor = yetishmaydi.length === 0
  const yubor = async () => {
    const body = {
      artikul, nomi: f.nomi, kategoriya: Number(f.kategoriya || kats[0].id), olcham: f.olcham || '',
      rang: f.rang || '', ijara_narxi: Number(f.ijara_narxi || 0), zalog: Number(f.zalog || 0),
      ...(rahbar && tannarxBor ? { tannarx: Number(f.tannarx) } : {}),
      // bo'sh qoldirilsa — tannarx to'liq to'langan; kami — yetkazib beruvchiga qarz
      ...(rahbar && f.yetkazib_beruvchi ? { yetkazib_beruvchi: Number(f.yetkazib_beruvchi), ...(f.tolandi !== undefined && f.tolandi !== '' ? { tolandi: Number(f.tolandi) } : {}) } : {}),
    }
    if (await onYuborish(body, rasmlar.map((r) => r.fayl))) { setF({ kategoriya: '' }); setRasmlar([]) }
  }
  // Kanvas (LibosQoshishShisha): tepada «katalogda shunday ko'rinadi», keyin Asosiy / Narx / Qayerdan olingan / Rasmlar bo'limlari,
  // pastda yopishib turadigan «Bekor qilish» va «Qo'shish»
  const katId = String(f.kategoriya || kats[0]?.id || '')
  const katNomi = kats.find((k) => String(k.id) === katId)?.nomi
  const qoplash = rahbar && Number(f.tannarx) > 0 && Number(f.ijara_narxi) > 0 ? Math.ceil(Number(f.tannarx) / Number(f.ijara_narxi)) : null
  return (
    <div className="stack libos-forma">
      <div className="lf-korinish">
        {rasmlar[0] ? <img src={rasmlar[0].url} alt="" /> : <span className="aks-plitka katta" aria-hidden="true"><NavIkona nom="katalog" className="tugma-ikon" /></span>}
        <span className="lf-korinish-matn">
          <small>Katalogda shunday ko'rinadi</small>
          <b>{f.nomi?.trim() || 'Libos nomi'}</b>
          <small>{[artikul || art.artikul || 'artikul', katNomi, f.olcham].filter(Boolean).join(' · ')}</small>
        </span>
        {Number(f.ijara_narxi) > 0 && <span className="lf-narx">{som(Number(f.ijara_narxi))} · ijara</span>}
      </div>
      <fieldset className="lf-bolim">
        <legend>Asosiy</legend>
        <div className="libos-narxlar">
          <label>Nomi *
            <input value={f.nomi || ''} placeholder="masalan: Oq atlas, uzun shleyf" onChange={set('nomi')} />
            <Info nom="Nomi">Sotuvchi ro'yxatda darrov tanishi uchun qisqa tavsif: «Oq atlas, uzun shleyf». Takrorlanishi mumkin.</Info>
          </label>
          <label>Artikul{art.artikul ? '' : ' *'}
            <input value={f.artikul || ''} placeholder={art.artikul ? `avtomatik: ${art.artikul}` : 'masalan: L-0001'} maxLength={50} onChange={set('artikul')} />
            <Info nom="Artikul">
              Libosning salondagi takrorlanmas kodi — yorlig'iga yoziladi. Zakazda libosni tez topish, sanoqda skanerlash va
              hisobotlar shu kod bilan ishlaydi. Ikki libosning artikuli bir xil bo'lolmaydi.
              {art.artikul
                ? <> Bo'sh qoldirsangiz, tizim keyingi raqamni o'zi beradi: <b>{art.artikul}</b>. O'zingiz yozsangiz, yozganingiz qoladi.</>
                : <> Avtomatik raqamlashni Sozlama → «Libos artikuli» da yoqasiz.</>}
            </Info>
          </label>
        </div>
        <div className="lf-qator">
          <div className="lf-maydon">
            <span className="forma-yorliq" id="lf-kat">Kategoriya</span>
            <div className="hisobot-chiplar" role="radiogroup" aria-labelledby="lf-kat">
              {kats.map((k) => (
                <button key={k.id} type="button" role="radio" aria-checked={katId === String(k.id)} className={katId === String(k.id) ? 'faol' : ''}
                  onClick={() => setF({ ...f, kategoriya: String(k.id) })}>{k.nomi}</button>
              ))}
            </div>
          </div>
          <label>Rang<input placeholder="masalan: oq (ivory)" value={f.rang || ''} onChange={set('rang')} /></label>
        </div>
        <div className="lf-maydon">
          <label>O'lcham<input placeholder="masalan: 44" value={f.olcham || ''} onChange={set('olcham')} /></label>
          {olchamlar.length > 0 && (
            <div className="hisobot-chiplar lf-olchamlar" role="group" aria-label="Tez tanlash: o'lcham">
              {olchamlar.map((o) => (
                <button key={o} type="button" className={f.olcham === o ? 'faol' : ''} aria-pressed={f.olcham === o} onClick={() => setF({ ...f, olcham: o })}>{o}</button>
              ))}
            </div>
          )}
        </div>
      </fieldset>
      <fieldset className="lf-bolim">
        <legend>Narx</legend>
        <div className="libos-narxlar">
          <label>Ijara narxi{rahbar ? ' *' : ''}<SummaInput value={f.ijara_narxi || ''} onChange={set('ijara_narxi')} /></label>
          <label>Tavsiya etilgan garov<SummaInput value={f.zalog || ''} onChange={set('zalog')} /><Info nom="Garov">{ZALOG_INFO}</Info></label>
          {rahbar && (
            <label className="lf-tannarx">Tannarx *<SummaInput value={f.tannarx ?? ''} onChange={set('tannarx')} /><Info nom="Tannarx">{TANNARX_INFO}</Info>
              <small className="soz-mute">faqat rahbar ko'radi</small>
            </label>
          )}
        </div>
        {qoplash != null && (
          <p className="lf-qoplash"><Belgi nom="tushum" className="tugma-ikon" />O'zini oqlashi: taxminan {qoplash} ta ijarada (tannarx ÷ ijara narxi)</p>
        )}
      </fieldset>
      {rahbar && ybs.length > 0 && (
        <fieldset className="lf-bolim">
          <legend>Qayerdan olingan</legend>
          <div className="libos-narxlar">
            <label>Qayerdan olingan
              <select value={f.yetkazib_beruvchi || ''} onChange={set('yetkazib_beruvchi')}>
                <option value="">Ko'rsatilmagan</option>
                {ybs.map((y) => <option key={y.id} value={y.id}>{y.nomi}</option>)}
              </select>
            </label>
            {f.yetkazib_beruvchi && (
              <label>Hozir to'landi<SummaInput placeholder={f.tannarx ? `to'liq: ${som(Number(f.tannarx))}` : ''} value={f.tolandi ?? ''} onChange={set('tolandi')} /><Info nom="Hozir to'landi">{TOLANDI_INFO}</Info>
                <small className="soz-mute">bo'sh — to'liq to'langan</small>
              </label>
            )}
          </div>
          {f.yetkazib_beruvchi && f.tolandi !== undefined && f.tolandi !== '' && Number(f.tolandi) < Number(f.tannarx || 0) && (
            <p className="malumot">Yetkazib beruvchiga qarz: <b>{som(Number(f.tannarx) - Number(f.tolandi))}</b></p>
          )}
        </fieldset>
      )}
      <fieldset className="lf-bolim">
        <legend>Rasmlar</legend>
        {rasmlar.length > 0 && (
          <div className="rasm-tor">
            {rasmlar.map((r, i) => (
              <figure key={r.url} className="rasm-katak">
                <img src={r.url} alt={`Tanlangan rasm ${i + 1}`} />
                <button type="button" className="rasm-ochir" aria-label="Rasmni olib tashlash" onClick={() => rasmOl(i)}>×</button>
              </figure>
            ))}
          </div>
        )}
        <RasmTanlash onTanla={rasmQosh} />
        <p className="malumot">Old, yon, orqa va tafsilot — 3–5 ta rasm. Tik (2:3) rasm eng yaxshi ko'rinadi; tizim o'zi kichraytiradi.</p>
      </fieldset>
      {!rahbar && <p className="malumot">Libos rahbar narx va tannarxni tasdiqlagach katalogga chiqadi.</p>}
      <div className="lf-past">
        {!tayyor && <p className="malumot r2-sabab">To'ldiring: {yetishmaydi.join(', ')}</p>}
        <div className="lf-tugmalar">
          {onBekor && <button type="button" className="ikkinchi" onClick={onBekor}>Bekor qilish</button>}
          <button type="button" className="pos-tugma" disabled={!tayyor} onClick={yubor}>
            <NavIkona nom="bajarildi" className="tugma-ikon" />Qo'shish{rasmlar.length > 0 && ` · ${rasmlar.length} ta rasm bilan`}
          </button>
        </div>
      </div>
    </div>
  )
}

function KategoriyaQator({ k, onSaqla, onOchir }) {
  const [nomi, setNomi] = useState(k.nomi)
  const [surov, setSurov] = useState(false)
  return (
    <div className="kategoriya-qator">
      <input value={nomi} maxLength={100} aria-label="Kategoriya nomi" onChange={(e) => setNomi(e.target.value)} />
      <span className="malumot">{k.turi === 'aksessuar' ? 'Aksessuar' : 'Libos'}</span>
      <button className="ikkinchi kichik" disabled={!nomi.trim() || nomi.trim() === k.nomi} onClick={() => onSaqla(nomi.trim())}>Saqlash</button>
      <button className="xavfli kichik" onClick={() => setSurov(true)}>O'chirish</button>
      {surov && (
        <Tasdiq sarlavha={`«${k.nomi}» kategoriyasi o'chirilsinmi?`} tugma="Ha, o'chirish"
          matn="Qaytarib bo'lmaydi. Ichida libos yoki aksessuar bo'lsa, o'chirilmaydi."
          onYop={() => setSurov(false)} onTasdiq={() => { setSurov(false); onOchir() }} />
      )}
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

// Libos pasporti (R2): «libos qachon bo'sh?» va «o'zini oqlayaptimi?» — tafsilot tepasida bir qarashda.
// Hozir kimda va qachon qaytadi; kelgusi bronlar; rahbarga — necha marta berilgan, ijara narxi bo'yicha jami va tannarxni qoplash.
const ZAKAZ_KORINADI = 4
function Pasport({ l, rahbar, onZakaz }) {
  const [p, setP] = useState(null)
  const [xato, setXato] = useState('')
  const [hammasi, setHammasi] = useState(false)
  // libos holati yoki joyi o'zgarsa (berish, qaytarish, ta'mir) — qayta o'qiladi
  const belgi = `${l.id}|${l.holat}|${l.mijozda}|${l.qaytish}`
  useEffect(() => {
    let bekor = false
    libosPasport(l.id).then((d) => { if (!bekor) { setP(d); setXato('') } }).catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    return () => { bekor = true }
  }, [l.id, belgi])
  if (xato) return <p className="xato">{xato}</p>
  if (!p) return <div className="r2p-pasport" aria-busy="true"><p className="malumot">Pasport yuklanmoqda…</p></div>
  const zakaz = (z) => (onZakaz
    ? <button type="button" className="havola" onClick={() => onZakaz(z.zakaz_id)}>#{z.raqam}</button>
    : <span>#{z.raqam}</span>)
  const kelgusi = hammasi ? p.kelgusi : p.kelgusi.slice(0, ZAKAZ_KORINADI)
  const s = p.samaradorlik
  return (
    <section className="r2p-pasport" aria-label="Libos pasporti">
      <div className="r2p-band">
        <h4>Hozir</h4>
        {p.hozir ? (
          <p>
            <span className={`holat ${p.hozir.kechikkan ? 'qarz' : 'berildi'}`}>{p.hozir.kechikkan ? 'Kechikmoqda' : 'Mijozda'}</span>{' '}
            {zakaz(p.hozir)} · {p.hozir.mijoz}
            <small>{sanaMatniQisqa(p.hozir.qaytarish)} da qaytishi kerak</small>
          </p>
        ) : <p>{l.holat === 'bosh' ? 'Salonda — ijaraga tayyor' : `Salonda · ${HOLAT[l.holat] || l.holat}`}</p>}
      </div>
      <div className="r2p-band">
        <h4>Kelgusi bronlar{p.kelgusi.length > 0 && <span className="tab-son">{p.kelgusi.length}</span>}</h4>
        {p.kelgusi.length === 0 ? <p className="malumot">Bron yo'q — istalgan sanaga berish mumkin.</p> : (
          <ul className="r2p-bronlar">
            {kelgusi.map((z) => (
              <li key={z.zakaz_id}>
                <b>{sanaMatniQisqa(z.olib_ketish).slice(0, 5)}–{sanaMatniQisqa(z.qaytarish).slice(0, 5)}</b> {zakaz(z)} <span className="malumot">{z.mijoz}</span>
              </li>
            ))}
          </ul>
        )}
        {p.kelgusi.length > ZAKAZ_KORINADI && (
          <button type="button" className="havola" onClick={() => setHammasi(!hammasi)}>
            {hammasi ? 'Kamroq' : `Yana ${p.kelgusi.length - ZAKAZ_KORINADI} ta`}
          </button>
        )}
      </div>
      {rahbar && s && (
        <div className="r2p-band">
          <h4>O'zini oqlashi</h4>
          <p>{s.berilgan > 0 ? `${s.berilgan} marta berilgan` : 'Hali berilmagan'}
            {s.oxirgi_berilgan && <small>oxirgi marta {sanaMatniQisqa(s.oxirgi_berilgan)}</small>}</p>
          <p>Ijara narxi bo'yicha jami: <b>{som(s.ijara_jami)}</b>
            <small>{s.qoplash_foiz == null ? "tannarx kiritilmagan — qoplash hisoblanmaydi" : `tannarxning ${s.qoplash_foiz} foizi qoplangan`}</small></p>
          {s.qoplash_foiz != null && (
            <div className="r2p-qoplash" role="img" aria-label={`Tannarx ${s.qoplash_foiz}% qoplangan`}>
              <i style={{ '--foiz': `${Math.min(100, s.qoplash_foiz)}%` }} />
            </div>
          )}
        </div>
      )}
    </section>
  )
}

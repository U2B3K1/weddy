import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import Hujjat from '../components/Hujjat'
import CalendarPage from '../components/kalendar/CalendarPage'
import Tasdiq from '../components/Tasdiq'
import SmenaTugma from '../components/SmenaTugma'
import LibosSiluet from '../components/LibosSiluet'
import NavIkona from '../components/NavIkona'
import Tasma from '../components/Tasma'
import TolovTanlov, { UsulTanlov } from '../components/TolovTanlov'
import { IjaraSana, Muhr } from '../components/Varaq'
import {
  bekorHisobi, bekorQilish, berish, chegirmaMiqdori, chegirmaOlibTashla, chegirmaSora, mijozOzgartir, primerkaBelgila, primerkaOzgartir, promokodOlibTashla, promokodQolla, qarzTolash, qaytarish, sanaKochirish, som, sozlamalar, tayyorChegirmalar,
  saqlangan, tolovQabul, tolovTuzat, xatoMatni, zakazAksessuarOchir, zakazAksessuarQosh, zakazSonlari, zakazTafsilot, zakazTarixi, zakazlarSahifa,
  boshAksessuarlar, boshLiboslar, libosAlmashtirish, salonchilar, zakazSalonchi,
  sanaMatni,
} from '../api'
import SummaInput from '../components/SummaInput'
import KpiFiltr from '../components/KpiFiltr'
import { Sahifalash } from '../components/Sahifalash'
import { Belgi, Qatorlar } from '../components/ZakazQatorlari'
import { BoshAmal, BoshXulosa } from '../components/BoshJoy'

// Bo'lim boshidagi bir qatorli xulosa (kanvas «9 ta faol zakaz · bugun 3 ta beriladi, 1 tasi qaytadi»)
function zakazXulosa(s) {
  const olib = s.bugun_olib || 0, qaytar = s.bugun_qaytar || 0
  const bugun = olib || qaytar
    ? `bugun ${[olib && `${olib} ta beriladi`, qaytar && `${qaytar} tasi qaytadi`].filter(Boolean).join(', ')}`
    : 'bugun berish va qaytarish yo\'q'
  return `${s.faol || 0} ta faol zakaz · ${bugun}`
}
import { TARIX_HARAKATLARI, ZAKAZ_HOLATLARI } from '../nomlar'
import { HAFTA, OYLAR, bugunIso } from '../components/kalendar/sana'

// Zakaz yo'li: 4 qadam (A-26); joriy — hozir kutilayotgani (ostida bir qator: qoldiq, muddat). Nomlar qisqa —
// telefonda ham hammasi sig'adi. «yopildi» — hammasi o'tilgan, «bekor» — ip chiqmaydi.
const QADAMLAR = ['Bron', "To'lov", 'Berildi', 'Qaytdi']
const bosHarflar = (ism) => (ism || '?').trim().split(/\s+/).slice(0, 2).map((x) => x[0]).join('').toUpperCase()
function qadamIndeksi(z) {
  const h = z.holat
  if (h === 'yopildi') return 4
  if (h === 'qaytarildi') return 3
  if (h === 'berildi') return 3
  if (h === 'bron') return z.qoldiq > 0 ? 1 : 2
  return 0  // vaqtinchalik, chegirma kutilmoqda — avans hali olinmagan
}
// Joriy qadam ostidagi bir qator: endi nima kerak (A-26)
function qadamIzohi(z) {
  const h = z.holat
  if (h === 'vaqtinchalik' || h === 'chegirma_kutilmoqda') return 'avans kutilmoqda'  // muddat — sarlavha ostida (QA-05)
  if (h === 'bron') return z.qoldiq > 0 ? `qoldiq ${som(z.qoldiq)}` : "to'langan"
  if (h === 'berildi') return muddat(z, bugunIso())?.[0] || null  // «bugun qaytaradi», «2 kun kechikdi»
  if (h === 'qaytarildi' && z.qarz > 0) return `qarz ${som(z.qarz)}`
  return null
}
// Vaqtinchalik bron muddati (A-17): bugun bo'lsa «02:06», boshqa kun — «08.11 02:06»
const ikki = (n) => String(n).padStart(2, '0')
function muddatVaqti(iso) {
  const d = new Date(iso)
  const soat = `${ikki(d.getHours())}:${ikki(d.getMinutes())}`
  return d.toDateString() === new Date().toDateString() ? soat : `${ikki(d.getDate())}.${ikki(d.getMonth() + 1)} ${soat}`
}
// To'lov va tarix qatorlari uchun: «07.11 14:30»
const qisqaVaqt = (iso) => { const d = new Date(iso); return `${ikki(d.getDate())}.${ikki(d.getMonth() + 1)} ${ikki(d.getHours())}:${ikki(d.getMinutes())}` }
// Holatga qarab bitta katta asosiy tugma matni (yo'riqnoma 8.1)
function asosiyTugma(z) {
  const h = z.holat
  if (h === 'vaqtinchalik' && z.qoldiq > 0) return 'Avans qabul qilish'
  if (h === 'bron' && z.qoldiq > 0) return 'Qoldiqni qabul qilish'
  if (h === 'bron') return 'Libosni berish'
  if (h === 'berildi') return 'Qaytarib olish'
  if (h === 'qaytarildi' && z.qarz > 0) return 'Qarzni yopish'
  if (h === 'qaytarildi' && z.qoldiq > 0) return 'Qoldiqni qabul qilish'  // C-03: o'tkazma kelmagan
  return null
}
// Avans olingach (bron tasdiqlangach) zakaz varaqasiga muhr bosiladi; vaqtinchalik bronda — bo'sh joy
const MUHRLI = ['bron', 'berildi', 'qaytarildi', 'yopildi']
// «Bekor qilingan» — xira (A-27): qizil «Qarz bor» bilan bir xil signal bermasin
const holatSinfi = (h) => ({ vaqtinchalik: 'vaqtinchalik', chegirma_kutilmoqda: 'vaqtinchalik', bron: 'bron', berildi: 'berildi', qaytarildi: 'qarz', yopildi: 'qaytarildi', bekor: 'bekor' }[h] || 'bron')

// Tezkor holat tablari (A-02): standart — «Faol» (ish davom etayotganlar), «Hammasi» oxirida.
// Chegirma tasdig'idagilar «Faol» va «Hammasi» ichida ko'rinadi.
const HOLAT_TABLARI = [['faol', 'Faol'], ['vaqtinchalik', 'Vaqtinchalik'], ['bron', 'Bron'], ['berildi', 'Berildi'],
  ['qaytarildi', 'Qarz bor'], ['yopildi', 'Yopilgan'], ['bekor', 'Bekor'], ['', 'Hammasi']]
// Tepadagi ko'rsatkich kartalari (maket uslubi) — holat emas, bugungi ish: bosilsa ro'yxat shu bo'yicha filtrlanadi,
// yana bosilsa «Faol»ga qaytadi. Olib ketish/qaytarishda pastki qator — ertangisi (u ham filtr).
const KORSATKICHLAR = [
  { k: 'bugun_olib', nom: 'Bugun olib ketadi', ikon: 'chiqdi', rang: 'tilla', ertaga: 'ertaga_olib' },
  { k: 'bugun_qaytar', nom: 'Bugun qaytaradi', ikon: 'qaytdi', rang: 'kok', ertaga: 'ertaga_qaytar' },
  { k: 'kechikkan', nom: 'Kechikkan', ikon: 'soat', rang: 'pushti', izoh: (n) => (n > 0 ? "mijozga qo'ng'iroq qiling" : 'hammasi vaqtida') },
  { k: 'tolov_kutmoqda', nom: "To'lov kutmoqda", ikon: 'kassa', rang: 'yashil', izoh: () => 'avans yoki qoldiq' },
]
const SAHIFA = 20  // ro'yxat sahifasi (raqamli sahifalar, Ndiz)
// «Bugun» ustuni (o'ngda) faqat keng ekranda — torroqda jadval ustunlari sig'maydi, ko'rsatkich kartalari shu ishni qiladi
const UCH_USTUN = '(min-width: 1440px)'
// Mijoz bilan gaplashish kerak bo'ladigan holatlar — qatorda qo'ng'iroq tugmasi
const QONGIROQ = ['vaqtinchalik', 'chegirma_kutilmoqda', 'bron', 'berildi', 'qaytarildi']
const kunFarqi = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000)
// Sotuvchi uchun eng muhim savol — «qachon?»: olib ketishgacha yoki qaytarishgacha qancha qoldi, kechikdimi
function muddat(z, bugun) {
  if (['vaqtinchalik', 'chegirma_kutilmoqda', 'bron'].includes(z.holat)) {
    const d = kunFarqi(bugun, z.olib_ketish)
    if (d < 0) return ["olib ketish kuni o'tdi", 'kech']
    if (d === 0) return ['bugun olib ketadi', 'bugun']
    if (d === 1) return ['ertaga olib ketadi', 'bugun']
    return [`${d} kun qoldi`, '']
  }
  if (z.holat === 'berildi') {
    const d = kunFarqi(bugun, z.qaytarish)
    if (d < 0) return [`${-d} kun kechikdi`, 'kech']
    if (d === 0) return ['bugun qaytaradi', 'bugun']
    if (d === 1) return ['ertaga qaytaradi', 'bugun']
    return [`mijozda, yana ${d} kun`, '']
  }
  return null
}

// Zakazlar jadvali — kanvas (ZakazlarShisha) ustunlari: Zakaz (surat, raqam, libos) │ Mijoz (ism, telefon) │
// Ijara muddati (sana + «qachon?» belgisi) │ Holat (avanssiz bronda muddati) │ To'lov / jami (summa va chiziq).
const mlnSon = (n) => (n / 1e6).toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
export function ZakazJadvali({ royxat, onOch }) {
  const bugun = bugunIso()
  return (
    <Tasma className="jadval-ora" pastki={84}>
      <table className="zakaz-jadval">
        <thead>
          <tr><th>Zakaz</th><th>Mijoz</th><th>Ijara muddati</th><th>Holat</th><th className="ong">To'lov / jami</th></tr>
        </thead>
        <tbody>
          {royxat.map((z) => {
            const foiz = z.jami ? Math.min(100, Math.round((z.tolangan / z.jami) * 100)) : 100
            const m = muddat(z, bugun)
            const avanssiz = ['vaqtinchalik', 'chegirma_kutilmoqda'].includes(z.holat) && !(z.tolangan > 0)
            return (
              <tr key={z.id} onClick={() => onOch(z.id)} className={m?.[1] === 'kech' ? 'kechikkan' : ''}>
                <td>
                  {/* tugma — klaviatura uchun; bosish hodisasi qatorga ko'tariladi */}
                  <button type="button" className="zakaz-katak" aria-label={`Zakaz #${z.raqam}, ${z.mijoz}`}>
                    <span className="zakaz-eskiz">{z.rasm ? <img src={z.rasm} alt="" loading="lazy" /> : <LibosSiluet />}</span>
                    <span className="zakaz-nom"><b>#{z.raqam}</b><small>{z.liboslar.join(', ')}</small></span>
                  </button>
                </td>
                <td className="mijoz-katak">
                  <b>{z.mijoz}</b>
                  {/* qatorni bosish kartani ochadi; telefon — alohida, telefon ilovasiga (faol zakazda) */}
                  {z.telefon && (QONGIROQ.includes(z.holat) ? (
                    <a className="qongiroq-matn" href={`tel:${z.telefon}`} aria-label={`${z.mijoz} — qo'ng'iroq qilish`}
                      onClick={(e) => e.stopPropagation()}><NavIkona nom="telefon" />{z.telefon}</a>
                  ) : <small>{z.telefon}</small>)}
                </td>
                <td className="ijara-katak">
                  <IjaraSana dan={z.olib_ketish} gacha={z.qaytarish} />
                  {m && <small className={`muddat ${m[1]}`}>{m[0]}</small>}
                </td>
                <td className="holat-katak">
                  <span className={`holat ${holatSinfi(z.holat)}`}>{ZAKAZ_HOLATLARI[z.holat]}</span>
                  {/* A-17: avans olinmasa bron qachon o'zi bekor bo'ladi */}
                  {z.bron_muddati && <small className="bron-muddat">avans {muddatVaqti(z.bron_muddati)} gacha</small>}
                </td>
                <td className="ong tolov-katak" title={`${som(z.tolangan)} to'langan, jami ${som(z.jami)}`}>
                  {z.holat === 'bekor' ? <span className="malumot">—</span> : (
                    <span className="tolov-progress">
                      <small>{foiz >= 100 ? `To'liq · ${mlnSon(z.jami)} mln` : `${mlnSon(z.tolangan)} / ${mlnSon(z.jami)} mln`}{avanssiz && z.jami > 0 && ' · avans yo\'q'}</small>
                      <i style={{ '--foiz': `${foiz}%` }} className={foiz >= 100 ? 'toliq' : ''} />
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </Tasma>
  )
}

export default function Zakazlar({ tanlangan, onTanla, onYangi, onKassa, boshQ, boshHolat, amal, yangiYopiq }) {
  // boshQ — yuqori paneldagi qidiruv matni, boshHolat — qo'ng'iroqchadan kelgan filtr (masalan, «kechikkan»);
  // har yangi qidiruvda App komponentni key bilan qayta ochadi
  const [q, setQ] = useState(boshQ || '')
  const [qKech, setQKech] = useState((boshQ || '').trim())  // A-35: har harfda emas, 300 ms to'xtagach so'raladi
  // A-02: standart — «Faol»; qidiruvda — «Hammasi» (yopilgan zakaz ham raqami bilan topilsin)
  const [holat, setHolat] = useState(boshHolat ?? (boshQ ? '' : 'faol'))
  const [royxat, setRoyxat] = useState(null)
  const [jami, setJami] = useState(0)
  const [sonlar, setSonlar] = useState({})
  const [xato, setXato] = useState('')
  const [sahifa, setSahifa] = useState(1)  // raqamli sahifa (20 tadan); kartadan qaytganda shu sahifa qayta yuklanadi
  const skroll = useRef(null)
  const uchUstun = useMedia(UCH_USTUN)

  useEffect(() => {
    const t = setTimeout(() => setQKech(q.trim()), 300)
    return () => clearTimeout(t)
  }, [q])
  useEffect(() => {
    if (tanlangan) return undefined
    let bekor = false
    zakazlarSahifa({ q: qKech || undefined, holat: holat || undefined, limit: SAHIFA, offset: (sahifa - 1) * SAHIFA })
      .then((d) => { if (!bekor) { setRoyxat(d.natija); setJami(d.jami); setXato('') } })
      .catch((e) => { if (!bekor) setXato(xatoMatni(e)) })
    return () => { bekor = true }
  }, [qKech, holat, tanlangan, sahifa])
  useEffect(() => {
    if (tanlangan) return
    zakazSonlari({ q: qKech || undefined }).then(setSonlar).catch(() => {})
  }, [qKech, tanlangan])
  // A-38: kartadan «‹» bilan qaytganda ro'yxat avvalgi joyida ochiladi
  useLayoutEffect(() => {
    if (!tanlangan && skroll.current != null) { window.scrollTo(0, skroll.current); skroll.current = null }
  }, [tanlangan])

  if (tanlangan) return <Karta key={tanlangan} id={tanlangan} amal={amal} onOrqaga={() => onTanla(null)} onKassa={onKassa} />

  const filtr = (k) => { setSahifa(1); setHolat(k) }
  const qidir = (v) => {
    setSahifa(1)
    setQ(v)
    if (v.trim() && holat === 'faol') setHolat('')  // raqam bo'yicha qidiruv yopilgan zakazni ham topsin
  }
  const och = (id) => { skroll.current = window.scrollY; onTanla(id); window.scrollTo(0, 0) }
  return (
    <div className="zakaz-sahifa">
      {/* Bo'lim boshidagi xulosa (kanvas): «47 ta faol zakaz · bugun 2 ta beriladi, 2 tasi qaytadi» */}
      {sonlar.faol != null && <BoshXulosa>{zakazXulosa(sonlar)}</BoshXulosa>}
      <section className="dash-kpi zakaz-kpi kpi-filtrlar" aria-label="Zakazlar ko'rsatkichlari">
        {KORSATKICHLAR.map((c) => (
          <Korsatkich key={c.k} c={c} son={sonlar[c.k]} ertaga={c.ertaga ? sonlar[c.ertaga] : null}
            tanlangan={holat} onFiltr={(k) => filtr(holat === k ? 'faol' : k)} />
        ))}
      </section>
      <div className="zakaz-tor">
        <section className="blok jadval-panel">
          {/* Asboblar paneli: tepada holat tablari (yonida soni), o'ngda qidiruv va asosiy amal — hammasi bir joyda, ixcham.
              Sahifa nomi yuqori panelda — bu yerda takrorlanmaydi (A-37) */}
          <div className="jadval-asboblar">
            <div className="tezkor-tablar" role="tablist" aria-label="Holat bo'yicha">
              {HOLAT_TABLARI.map(([k, nom]) => (
                <button key={k || 'hammasi'} type="button" role="tab" aria-selected={holat === k}
                  className={holat === k ? 'faol' : ''} onClick={() => filtr(k)}>
                  {nom}{sonlar[k] > 0 && <span className="tab-son">{sonlar[k]}</span>}
                </button>
              ))}
            </div>
            {/* QA-06: qidiruv va asosiy amal birga — tablar ko'p bo'lsa ham bir qatorda, o'ngda */}
            <div className="zakaz-asboblar-ong">
              <label className="qidiruv-maydon zakaz-qidiruv">
                <NavIkona nom="qidiruv" className="tugma-ikon" />
                <input type="search" className="jadval-qidiruv" placeholder="Raqam, telefon yoki ism" aria-label="Zakaz qidirish"
                  value={q} onChange={(e) => qidir(e.target.value)} />
              </label>
              {/* kanvas: qidiruv yonida topilgan zakazlar soni */}
              {royxat && <span className="zakaz-son" aria-live="polite">{jami} ta zakaz</span>}
              {/* «Yangi zakaz» — kanvasdagidek bo'lim boshida, tablar qatorining o'ngida (BoshAmal) */}
              {onYangi && (
                <BoshAmal>
                  <button type="button" className="bosh-tugma" onClick={onYangi} disabled={Boolean(yangiYopiq)} title={yangiYopiq || undefined}>
                    <NavIkona nom="qosh" className="tugma-ikon" />Yangi zakaz
                  </button>
                </BoshAmal>
              )}
            </div>
          </div>
          {xato && <p className="xato jadval-bosh">{xato}</p>}
          {royxat === null ? null : royxat.length === 0 ? (
            <p className="malumot jadval-bosh">{qKech ? `«${qKech}» bo'yicha zakaz topilmadi.` : "Bu filtr bo'yicha zakaz yo'q."}</p>
          ) : (
            <>
              <ZakazJadvali royxat={royxat} onOch={och} />
              {/* sahifa cho'zilib ketmasin: 20 tadan, raqamli sahifalar (server sahifalaydi) */}
              {jami > SAHIFA && (
                <Sahifalash sahifa={sahifa} sahifalar={Math.ceil(jami / SAHIFA)} jami={jami} hajm={SAHIFA} nomi="ta" onTanla={setSahifa} />
              )}
            </>
          )}
        </section>
        {uchUstun && <BugunUstuni onOch={och} />}
      </div>
    </div>
  )
}

// Ko'rsatkich kartasi-filtr; olib ketish/qaytarishda «ertaga — N ta» — alohida kichik tugma ustida
function Korsatkich({ c, son, ertaga, tanlangan, onFiltr }) {
  return (
    <KpiFiltr nom={c.nom} son={son} ikon={c.ikon} rang={c.rang} tanlangan={tanlangan === c.k} xavf={c.k === 'kechikkan' && son > 0}
      onBos={() => onFiltr(c.k)} izoh={c.izoh?.(son)}
      pastki={c.ertaga && (
        <button type="button" className="kpi-ertaga" aria-pressed={tanlangan === c.ertaga}
          aria-label={`${c.nom.replace('Bugun', 'Ertaga')}: ${ertaga ?? 0}`} onClick={() => onFiltr(c.ertaga)}>
          ertaga — {ertaga ?? 0} ta
        </button>
      )} />
  )
}

function useMedia(sorov) {
  const [mos, setMos] = useState(() => Boolean(window.matchMedia?.(sorov).matches))
  useEffect(() => {
    const mq = window.matchMedia?.(sorov)
    if (!mq) return undefined
    const ozgardi = () => setMos(mq.matches)
    mq.addEventListener('change', ozgardi)
    return () => mq.removeEventListener('change', ozgardi)
  }, [sorov])
  return mos
}

// «9 noyabr, yakshanba» — kanvasdagi «Bugun» paneli sarlavhasi uchun
function bugunSarlavha(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return `${d} ${OYLAR[m - 1].toLowerCase()}, ${HAFTA[(new Date(y, m - 1, d).getDay() + 6) % 7][1].toLowerCase()}`
}

// O'ng ustun — bugungi kun tartibi bir qarashda: kim olib ketadi (qoldig'i bilan), kim qaytaradi, kim kechikdi.
// Qator bosilsa zakaz kartasi; ro'yxatning o'zi esa o'z filtrida qoladi.
function BugunUstuni({ onOch }) {
  const [d, setD] = useState(null)
  useEffect(() => {
    let bekor = false
    Promise.all(['bugun_olib', 'bugun_qaytar', 'kechikkan'].map((h) => zakazlarSahifa({ holat: h, limit: 20, offset: 0 }).then((r) => r.natija)))
      .then(([olib, qaytar, kech]) => { if (!bekor) setD({ olib, qaytar, kech }) })
      .catch(() => { if (!bekor) setD({ olib: [], qaytar: [], kech: [] }) })
    return () => { bekor = true }
  }, [])
  const bugun = bugunIso()
  const guruhlar = d ? [
    { k: 'olib', nom: 'Olib ketadi', ikon: 'chiqdi', royxat: d.olib,
      ong: (z) => (z.qoldiq > 0 ? <><b>{som(z.qoldiq)}</b><span className="holat-pill vaqt">qoldiq</span></> : <span className="holat-pill bron">To'langan</span>) },
    { k: 'qaytar', nom: 'Qaytaradi', ikon: 'qaytdi', royxat: d.qaytar, ong: () => <span className="holat-pill kok">mijozda</span> },
    { k: 'kech', nom: 'Kechikkan', ikon: 'soat', royxat: d.kech,
      ong: (z) => <span className="holat-pill qarz">{Math.max(1, kunFarqi(z.qaytarish, bugun))} kun</span> },
  ].filter((g) => g.royxat.length > 0) : []
  return (
    <aside className="blok dash-karta zakaz-bugun" aria-label="Bugun">
      <div className="dash-karta-bosh"><h3><Belgi nom="kun" />Bugun</h3><span className="malumot">{bugunSarlavha(bugun)}</span></div>
      {!d ? <p className="malumot">Yuklanmoqda…</p> : guruhlar.length === 0 ? (
        <p className="zakaz-bugun-bosh"><Belgi nom="bajarildi" />Bugun olib ketish ham, qaytarish ham yo'q.</p>
      ) : guruhlar.map((g) => (
        <section key={g.k} className={`zakaz-bugun-guruh${g.k === 'kech' ? ' xavf' : ''}`} aria-label={`${g.nom}: ${g.royxat.length}`}>
          <h4><Belgi nom={g.ikon} />{g.nom}<span className="ish-son">{g.royxat.length}</span></h4>
          <Qatorlar royxat={g.royxat} onZakaz={onOch} ong={g.ong} kop={5} />
        </section>
      ))}
    </aside>
  )
}

function Karta({ id, amal, onOrqaga, onKassa }) {
  const [z, setZ] = useState(null)
  const [tarix, setTarix] = useState(null)
  const [tarixOchiq, setTarixOchiq] = useState(false)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [soz, setSoz] = useState(null)
  const [chop, setChop] = useState(null)
  useEffect(() => { sozlamalar().then(setSoz).catch(() => {}) }, [])
  // «Alohida kassir» rejimida sotuvchi pul qabul qilmaydi — to'lov tugmalari o'rniga eslatma
  const kassirda = soz?.kassa_rejimi === 'kassir' && saqlangan.xodim()?.rol === 'sotuvchi'
  const rahbar = saqlangan.xodim()?.rol === 'rahbar'

  const yukla = useCallback(() => zakazTafsilot(id).then((d) => { setZ(d); return d }), [id])
  useEffect(() => { yukla() }, [yukla])
  const [muhrBosildi, setMuhrBosildi] = useState(false)  // shu kartada avans olinib bron tasdiqlandi — muhr ko'z oldida bosiladi
  // R2: Kassadan «Libosni berish →» — karta yuklangach asosiy amal (berish formasi) ochilib ko'rinadigan joyga suriladi
  const yuklandi = Boolean(z)
  useEffect(() => {
    if (amal !== 'berish' || !yuklandi) return undefined
    const t = setTimeout(() => {
      const d = document.getElementById('asosiy-amal')
      if (d) { d.open = true; d.scrollIntoView({ behavior: 'smooth', block: 'center' }) }
    }, 150)
    return () => clearTimeout(t)
  }, [amal, yuklandi])

  // Har bir amal: muvaffaqiyatda kartani yangilaydi, xatoni ko'rsatadi. `ok` — matn yoki server javobidan matn (A-16).
  // `ok` — matn yoki (javob, yangiKarta, eskiKarta) => matn
  const bajar = async (fn, ok = 'Bajarildi.') => {
    setXabar({ turi: '', matn: '' })
    const oldingi = z
    let javob
    try {
      javob = await fn()
    } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e), kod: e.response?.data?.kod })
      return false
    }
    setTarix(null); setTarixOchiq(false)
    let yangi = null
    try { yangi = await yukla() } catch { /* amal bajarildi, karta keyingi ochilishda yangilanadi */ }
    setXabar({ turi: 'ok', matn: typeof ok === 'function' ? ok(javob, yangi, oldingi) : ok })
    if (!MUHRLI.includes(oldingi?.holat) && MUHRLI.includes(yangi?.holat)) setMuhrBosildi(true)
    return true
  }
  // C-07, C-17, C-31: narxga ta'sir qiladigan amal natijasi — eski → yangi jami, qoldiq, mijozga qaytariladigan pul
  const narxXabari = (boshi) => (javob, yangi, oldingi) => {
    const jami = javob?.yangi_jami ?? yangi?.jami
    const qoldiq = javob?.qoldiq ?? yangi?.qoldiq
    let m = boshi
    if (oldingi && jami != null && jami !== oldingi.jami) m += ` Jami ${som(oldingi.jami)} → ${som(jami)}`
    if (qoldiq != null && (jami !== oldingi?.jami || qoldiq !== oldingi?.qoldiq)) m += `${m.endsWith('.') ? ' Q' : ', q'}oldiq ${som(qoldiq)}`
    if (javob?.qaytariladi > 0) m += `. Mijozga ${som(javob.qaytariladi)} qaytaring`
    return m.endsWith('.') ? m : `${m}.`
  }
  // A-18: tarix tugmasi ochadi va yopadi; birinchi ochilishda yuklanadi
  const tarixniAlmashtir = () => {
    if (tarixOchiq) { setTarixOchiq(false); return }
    setTarixOchiq(true)
    if (!tarix) zakazTarixi(id).then(setTarix).catch(() => setTarix([]))
  }

  if (chop) return <Hujjat zakazId={id} tur={chop} onYop={() => setChop(null)} />
  if (!z) return <p className="malumot">Yuklanmoqda…</p>
  const h = z.holat
  const q = qadamIndeksi(z)
  const izoh = qadamIzohi(z)
  // Kassadan mijozga qaytariladigan pul zalog (A-16)
  const pulZalog = z.zaloglar.filter((g) => g.turi === 'pul' && g.holat === 'saqlanmoqda').reduce((s, g) => s + g.summa, 0)
  // Zalog to'lovlari alohida qator bo'lib takrorlanmaydi — zalog o'z qatorida holati bilan (A-30)
  const tolovlar = z.tolovlar.filter((t) => !['zalog', 'zalog_qaytarish'].includes(t.tur))
  const qaytarishXabari = (r) => {
    const qismlar = ['Qaytarish rasmiylashtirildi.']
    if (r?.mijozga_qaytariladi > 0) qismlar.push(`Mijozga ${som(r.mijozga_qaytariladi)} qaytaring.`)
    if (r?.ushlab_qolingan > 0) qismlar.push(`Zalogdan jarimaga ushlab qolindi: ${som(r.ushlab_qolingan)}.`)
    if (r?.qarz > 0) qismlar.push(`Mijoz qarzi: ${som(r.qarz)}.`)
    return qismlar.join(' ')
  }

  // «Boshqa amallar» — faqat shu holatda mavjud bandlar (A-21): bo'sh bo'lsa chiqmaydi, bitta bo'lsa ichma-ich ochilmaydi
  const ochiqZakaz = ['vaqtinchalik', 'chegirma_kutilmoqda', 'bron'].includes(h)
  const amallar = [
    h === 'vaqtinchalik' && z.tolangan === 0 && (soz?.promokodlar_bolimi !== false || z.promokod) && <PromokodForma key="promokod" z={z} bajar={bajar} />,
    h === 'vaqtinchalik' && <ChegirmaForma key="chegirma" zakazId={z.id} z={z} bajar={bajar} />,
    ['vaqtinchalik', 'bron'].includes(h) && <AksessuarForma key="aksessuar" z={z} bajar={bajar} narxXabari={narxXabari} />,
    ochiqZakaz && <LibosAlmashtirishForma key="libos" z={z} bajar={bajar} narxXabari={narxXabari} />,
    h !== 'bekor' && <SalonchiTanlash key="salonchi" z={z} bajar={bajar} />,
    (soz?.primerka || z.primerkalar.length > 0) && (
      <PrimerkaForma key="primerka" z={z} bajar={bajar} ochiq={ochiqZakaz && !!soz?.primerka} />
    ),
    ochiqZakaz && <KochirishForma key={`kochirish-${z.olib_ketish}-${z.qaytarish}`} z={z}
      onYuborish={(b) => bajar(() => sanaKochirish(z.id, b), narxXabari("Sana ko'chirildi."))} />,
    ochiqZakaz && (kassirda && z.tolangan > 0
      ? <div key="bekor" className="blok"><p className="malumot">To'lov qilingan zakazni kassir bekor qiladi — mijozga pul qaytarish kassada.</p></div>
      : <BekorForma key="bekor" soz={soz} z={z} rahbar={rahbar} onYuborish={(b) => bajar(() => bekorQilish(z.id, b), (r) => (
        `Zakaz bekor qilindi.${r?.qaytarilgan_avans > 0 ? ` Mijozga ${som(r.qaytarilgan_avans)} qaytaring` : ''}`
        + `${r?.ushlab_qolingan_avans > 0 ? `${r?.qaytarilgan_avans > 0 ? ', u' : ' U'}shlab qolindi ${som(r.ushlab_qolingan_avans)}` : ''}${r?.qaytarilgan_avans > 0 || r?.ushlab_qolingan_avans > 0 ? '.' : ''}`))} />),
  ].filter(Boolean)

  return (
    <div className="stack karta">
      <div className="karta-bosh">
        <button className="ikkinchi karta-orqaga" aria-label="Zakazlar ro'yxatiga qaytish" onClick={onOrqaga}><NavIkona nom="chap" className="tugma-ikon" /></button>
        <h2>Zakaz #{z.raqam}</h2>
        <span className={`holat ${holatSinfi(h)}`}>{ZAKAZ_HOLATLARI[h]}</span>
        {/* kanvas: sarlavha ostida kim va qachon yaratgan, o'ngda «Chop etish» (shartnoma) */}
        {z.yaratilgan && <p className="karta-bosh-izoh">Yaratildi {qisqaVaqt(z.yaratilgan)}{z.sotuvchi ? ` · ${z.sotuvchi}` : ''}</p>}
        {!['chegirma_kutilmoqda', 'bekor'].includes(h) && (
          <button type="button" className="ikkinchi kichik karta-chop" onClick={() => setChop('shartnoma')}>
            <NavIkona nom="hujjat" className="tugma-ikon" />Chop etish
          </button>
        )}
        {/* A-17: avanssiz bron qachon o'zi bekor bo'lishi — sotuvchi mijozga aniq vaqtni aytadi */}
        {z.bron_muddati && (
          <p className="bron-muddat-izoh">{h === 'chegirma_kutilmoqda'
            ? `Rahbar ${muddatVaqti(z.bron_muddati)} gacha qaror qilmasa, bron o'zi bekor bo'ladi`
            : `${muddatVaqti(z.bron_muddati)} gacha avans olinmasa, bron o'zi bekor bo'ladi`}</p>
        )}
      </div>
      {h !== 'bekor' && (
        <ol className="zakaz-ip holat-ip qadam-ip" aria-label="Zakaz bosqichlari">
          {QADAMLAR.map((n, i) => (
            <li key={n} className={i < q ? 'otdi' : i === q ? 'joriy' : ''} aria-current={i === q ? 'step' : undefined}>
              <span>
                <span className="ip-tugun" aria-hidden="true">{i < q ? '✓' : i + 1}</span>
                <span className="ip-matn"><span className="ip-nom">{n}</span>{i === q && izoh && <small className="ip-izoh">{izoh}</small>}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
      {/* QA-02: telefonda joriy qadam izohi ip ichida qo'shni qadam ustiga chiqardi — u yerda alohida qatorda */}
      {h !== 'bekor' && izoh && <p className="qadam-izoh-tel"><b>{QADAMLAR[Math.min(q, QADAMLAR.length - 1)]}:</b> {izoh}</p>}
      {asosiyTugma(z) && (
        <button className="asosiy-tugma" onClick={() => {
          const d = document.getElementById('asosiy-amal')
          if (d) { d.open = true; d.scrollIntoView({ behavior: 'smooth', block: 'center' }) }
        }}>{asosiyTugma(z)}</button>
      )}
      {/* Zakaz varaqasi — «Yangi zakaz» dagi bilan bir xil qog'oz: mijoz, sanalar, liboslar, hisob.
          Muhr: bron tasdiqlangan (avans olingan) zakazda; vaqtinchalikda bo'sh joy; bekorda — shtamp */}
      <section className={`varaq karta-asosiy${h === 'bekor' ? ' varaq-bekor' : ''}`} aria-label="Zakaz ma'lumotlari">
        {MUHRLI.includes(h) ? <Muhr raqam={z.raqam} bosildi={muhrBosildi} className="muhr-karta" />
          : h === 'bekor' ? <span className="shtamp" aria-hidden="true">Bekor qilindi</span>
          : <span className="muhr-joy" aria-hidden="true" />}
        {/* Kanvas (ZakazKartaShisha): mijoz qatori — bosh harflar doirasi, ism, telefon · to'y · manba */}
        <div className="km-mijoz">
          <span className="km-avatar" aria-hidden="true">{bosHarflar(z.mijoz)}</span>
          <div className="km-mijoz-matn">
            {z.mijoz !== z.telefon && <p className="varaq-kimga">{z.mijoz}</p>}
            <span className="km-meta">
              <a className="varaq-telefon" href={`tel:${z.telefon}`}>{z.telefon}</a>
              {z.toy_sanasi && <span>to'y {sanaMatni(z.toy_sanasi)}</span>}
              {z.manba && <span>{z.manba}</span>}
            </span>
          </div>
        </div>
        {/* Libos: surat, nom, artikul va o'lcham, ijara narxi — sotuvchi qaysi libos haqida gaplashayotganini bir qarashda ko'radi */}
        <div className="karta-liboslar">
          {z.libos_qatorlari.map((p) => (
            <figure key={p.id} className="karta-libos">
              <span className="karta-libos-foto">{p.rasm ? <img src={p.rasm} alt="" /> : <LibosSiluet />}</span>
              <figcaption><b>{p.nomi}</b><small>{p.artikul}{p.olcham ? ` · o'lcham ${p.olcham}` : ''}</small>
                <span className="km-narx"><span>Ijara narxi</span><b>{som(p.narx)}</b></span></figcaption>
            </figure>
          ))}
        </div>
        {/* uchta quti: olib ketish, qaytarish, muddat */}
        <div className="km-sanalar">
          <div><small>Olib ketish</small><b>{sanaMatni(z.olib_ketish)}</b></div>
          <div><small>Qaytarish</small><b>{sanaMatni(z.qaytarish)}</b></div>
          <div><small>Muddat</small><b>{kunFarqi(z.olib_ketish, z.qaytarish) + 1} kun</b></div>
        </div>
        <dl className="varaq-hisob">
          {z.aksessuarlar.length > 0 && <div className="varaq-hisob-matn"><dt>Aksessuarlar</dt><dd>{z.aksessuarlar.join(', ')}</dd></div>}
          {z.salonchi && (
            <div className="varaq-hisob-matn"><dt>Salonchi</dt><dd>{z.salonchi.ism}
              {z.salonchi.instagram && <>, <a href={z.salonchi.instagram} target="_blank" rel="noreferrer">Instagram</a></>}
            </dd></div>
          )}
          <div><dt>Asosiy narx</dt><dd>{som(z.asosiy_narx - z.xizmatlar)}</dd></div>
          {z.xizmatlar > 0 && <div><dt>Moslash xizmati</dt><dd>{som(z.xizmatlar)}</dd></div>}
          {z.ustama > 0 && <div><dt>Mavsumiy ustama ({Number(z.ustama_foiz)}%)</dt><dd>{som(z.ustama)}</dd></div>}
          {z.chegirma - z.promokod_chegirma > 0 && <div><dt>Chegirma</dt><dd>−{som(z.chegirma - z.promokod_chegirma)}</dd></div>}
          {z.promokod && <div><dt>Promokod {z.promokod}</dt><dd>−{som(z.promokod_chegirma)}</dd></div>}
        </dl>
        <div className="varaq-jami"><span>Jami</span><b>{som(z.jami)}</b></div>
        <dl className="varaq-hisob">
          <div><dt>To'langan</dt><dd>{som(z.tolangan)}</dd></div>
          {h !== 'bekor' && <div className={z.qoldiq > 0 ? 'varaq-qoldiq' : ''}><dt>Qoldiq</dt><dd>{som(z.qoldiq)}</dd></div>}
          {z.qarz > 0 && <div className="varaq-qarz"><dt>Jarima qarzi</dt><dd>{som(z.qarz)}</dd></div>}
        </dl>
        {z.bekor_sabab && <p className="varaq-izoh">Bekor sababi: {z.bekor_sabab}</p>}
        <div className="qator hujjat-havolalar">
          {!['chegirma_kutilmoqda', 'bekor'].includes(h) && (
            <button className="ikkinchi kichik" onClick={() => setChop('shartnoma')}>Shartnoma</button>
          )}
          {z.tolovlar.length > 0 && h !== 'chegirma_kutilmoqda' && (
            <button className="ikkinchi kichik" onClick={() => setChop('kvitansiya')}>Kvitansiya</button>
          )}
          {z.zaloglar.length > 0 && (
            <button className="ikkinchi kichik" onClick={() => setChop('dalolatnoma')}>Zalog dalolatnomasi</button>
          )}
        </div>
        {h === 'chegirma_kutilmoqda' && <p className="varaq-izoh">Chegirma tasdiqlanmaguncha shartnoma chop etilmaydi.</p>}
      </section>
      <div className="karta-ong">
      {xabar.matn && (
        <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'} role={xabar.turi === 'xato' ? 'alert' : 'status'}>
          {xabar.matn}{' '}
          {xabar.turi === 'xato' && (
            <SmenaTugma kod={xabar.kod} onKassa={onKassa}
              onTayyor={() => setXabar({ turi: 'ok', matn: "Smenaga qo'shildingiz. Amalni qayta bajaring." })} />
          )}
        </p>
      )}

      {h === 'chegirma_kutilmoqda' && z.chegirma_sorovi?.holat === 'kutilmoqda' && (
        <ChegirmaKutilmoqda z={z} bajar={bajar} />
      )}
      {kassirda && (((h === 'vaqtinchalik' || h === 'bron' || h === 'berildi' || h === 'qaytarildi') && z.qoldiq > 0) || (h === 'qaytarildi' && z.qarz > 0)) && (
        <p className="malumot">To'lovni kassir qabul qiladi — mijozni kassaga yuboring (zakaz #{z.raqam}).</p>
      )}
      {!kassirda && (h === 'vaqtinchalik' || h === 'bron') && z.qoldiq > 0 && (
        <TolovForma key={`tolov-${z.qoldiq}`} sarlavha={h === 'bron' ? "Qoldiq to'lov" : 'Avans qabul qilish'} maks={z.qoldiq} foizlar={h !== 'bron'}
          onYuborish={(summa, usul) => bajar(
            () => tolovQabul({ zakaz: z.id, tur: h === 'bron' ? 'qoldiq' : 'avans', summa, usul }),
            `To'lov qabul qilindi.${soz?.fiskal_eslatma ? ` ${soz.fiskal_izoh || 'Fiskal chekni urishni unutmang.'}` : ''}`)} />
      )}
      {!kassirda && (h === 'berildi' || h === 'qaytarildi') && z.qoldiq > 0 && (
        <TolovForma key={`qoldiq-${z.qoldiq}`} sarlavha="Qoldiq to'lov (o'tkazma kelmagan)" maks={z.qoldiq}
          id={h === 'qaytarildi' && !(z.qarz > 0) ? 'asosiy-amal' : null}
          izoh={`To'lov hisobdan chiqqani uchun ${som(z.qoldiq)} mijozdan qayta olinadi.`}
          onYuborish={(summa, usul) => bajar(() => tolovQabul({ zakaz: z.id, tur: 'qoldiq', summa, usul }), "To'lov qabul qilindi.")} />
      )}
      {!kassirda && h === 'vaqtinchalik' && z.jami === 0 && (
        <button onClick={() => bajar(() => tolovQabul({ zakaz: z.id, tur: 'avans', summa: 0, usul: 'naqd' }), 'Bron tasdiqlandi.')}>
          Bronni tasdiqlash (to'liq chegirma — to'lov yo'q)
        </button>
      )}
      {h === 'bron' && z.qoldiq === 0 && <BerishForma soz={soz} pulsiz={kassirda} libosZalogi={z.libos_zalogi} olibKetish={z.olib_ketish}
        kutilayotgan={z.tolovlar.filter((t) => t.tasdiq === 'kutilmoqda').reduce((s, t) => s + t.summa, 0)}
        onYuborish={(zaloglar, erta) => bajar(() => berish(z.id, zaloglar, erta), 'Libos berildi.')} />}
      {h === 'berildi' && kassirda && pulZalog > 0 && (
        <p className="malumot">Pul zalogni kassir qaytaradi — libos qaytarilishini kassir rasmiylashtiradi (zakaz #{z.raqam}).</p>
      )}
      {h === 'berildi' && !(kassirda && pulZalog > 0) && <QaytarishForma pulsiz={kassirda} pulZalog={pulZalog} aksessuarlar={z.aksessuar_qatorlari} qaytarish={z.qaytarish} kechikishJarimasi={soz ? (soz.kechikish_jarimasi ? soz.kechikish_kunlik_summa : 0) : null} tillo={z.zaloglar.some((g) => g.turi === 'tillo')} onYuborish={(b) => bajar(() => qaytarish(z.id, b), qaytarishXabari)} />}
      {!kassirda && h === 'qaytarildi' && z.qarz > 0 && (
        <TolovForma key={`qarz-${z.qarz}`} sarlavha="Jarima qarzini to'lash" maks={z.qarz}
          onYuborish={(summa, usul) => bajar(() => qarzTolash(z.id, summa, usul), "Qarz to'landi.")} />
      )}
      {amallar.length === 1 && amallar[0]}
      {amallar.length > 1 && (
        <details className="boshqa-amallar">
          <summary className="havola-tugma">Boshqa amallar</summary>
          {amallar}
        </details>
      )}
      </div>
      <section className="blok karta-tolovlar">
        <h3>To'lovlar</h3>
        {tolovlar.length === 0 && z.zaloglar.length === 0 && <p className="malumot">Hali to'lov yo'q.</p>}
        {tolovlar.map((t) => (
          <div key={t.id} className={`tolov-qator${t.tasdiq === 'kelmadi' ? ' kelmadi' : ''}`}>
            <span className="tolov-nom">
              <b>{t.tur_nomi}</b>
              {/* A-30: qachon va kim — «07.11 14:30 · Naqd, Malika» */}
              <small><time dateTime={t.vaqt}>{qisqaVaqt(t.vaqt)}</time> · {t.usul_nomi}, {t.xodim}</small>
              {t.tasdiq === 'kutilmoqda' && <small className="tolov-kutish">Rahbar tasdig'i kutilmoqda</small>}
              {t.tasdiq === 'kelmadi' && <small className="qizil">Kelmadi — hisobga olinmagan</small>}
            </span>
            <b className="tolov-summa">{['vozvrat'].includes(t.tur) ? '−' : ''}{som(t.summa)}</b>
            {rahbar && t.tuzatsa_boladi && <TolovTuzatish t={t} onYuborish={(tana) => bajar(() => tolovTuzat(t.id, tana), "To'lov tuzatildi.")} />}
          </div>
        ))}
        {z.zaloglar.map((g) => (
          <div key={g.id} className="tolov-qator">
            <span className="tolov-nom"><b>Zalog {g.yorliq}</b><small>{g.turi_nomi}{g.tavsif ? `, ${g.tavsif}` : ''}</small></span>
            <span className="tolov-summa zalog-holat">{g.turi === 'pul' && g.summa ? `${som(g.summa)}, ` : ''}{g.holat_nomi.toLowerCase()}</span>
          </div>
        ))}
        <button type="button" className="ikkinchi kichik" aria-expanded={tarixOchiq} onClick={tarixniAlmashtir}>
          {tarixOchiq ? "Tarixni yopish" : "O'zgarishlar tarixi"}
        </button>
        {tarixOchiq && (
          tarix === null ? <p className="malumot">Yuklanmoqda…</p>
            : tarix.length === 0 ? <p className="malumot">O'zgarish yo'q.</p>
              : (
                <ol className="tarix-royxat">
                  {tarix.map((t, i) => (
                    <li key={i}>
                      <small className="tarix-kim"><time dateTime={t.vaqt}>{qisqaVaqt(t.vaqt)}</time> · {t.xodim || 'Tizim'}</small>
                      <span><b>{t.nomi || TARIX_HARAKATLARI[t.harakat] || t.harakat}</b>{t.matn ? ` — ${t.matn}` : ''}</span>
                      {t.sabab && <small className="tarix-sabab">Sabab: {t.sabab}</small>}
                    </li>
                  ))}
                </ol>
              )
        )}
      </section>
    </div>
  )
}

// Saqlangan zakazga aksessuar qo'shish yoki olib tashlash; narx va bandlik serverda qayta hisoblanadi.
function AksessuarForma({ z, bajar, narxXabari }) {
  const [bosh, setBosh] = useState([])
  const [tanlov, setTanlov] = useState('')
  const [usul, setUsul] = useState('naqd')  // C-07: olib tashlansa va to'langan jamidan oshsa — farq shu usulda qaytariladi
  const ortiqcha = (q) => z.tolangan > z.jami - q.narx
  const qatorlar = z.aksessuar_qatorlari
  useEffect(() => {
    boshAksessuarlar(z.olib_ketish, z.qaytarish).then(setBosh).catch(() => {})
  }, [z.olib_ketish, z.qaytarish, qatorlar.length])
  const id = tanlov || bosh[0]?.id
  return (
    <Amal sarlavha={`Aksessuarlar (${qatorlar.length})`}>
      {qatorlar.map((q) => (
        <div key={q.id} className="qator aks-qator">
          <span className="matn-ustun">{q.nomi} ({q.yorliq}) · {som(q.narx)}</span>
          <button className="ikkinchi kichik"
            onClick={() => bajar(() => zakazAksessuarOchir(z.id, q.id, ortiqcha(q) ? usul : undefined), narxXabari('Aksessuar olib tashlandi.'))}>Olib tashlash</button>
        </div>
      ))}
      {qatorlar.some(ortiqcha) && <UsulTanlov usul={usul} onUsul={setUsul} yorliq="Ortiqcha to'lov qanday qaytariladi" />}
      {bosh.length > 0 ? (
        <div className="qator">
          <select value={id} aria-label="Qo'shiladigan aksessuar" onChange={(e) => setTanlov(e.target.value)}>
            {bosh.map((a) => <option key={a.id} value={a.id}>{a.nomi} · {som(a.ijara_narxi)} · bo'sh {a.bosh_soni}</option>)}
          </select>
          <button className="ikkinchi" onClick={() => bajar(() => zakazAksessuarQosh(z.id, Number(id)), narxXabari("Aksessuar qo'shildi."))}>Qo'shish</button>
        </div>
      ) : <p className="malumot">Bu sanalarga bo'sh aksessuar yo'q.</p>}
    </Amal>
  )
}

// FT-17.2: zakazdagi libosni shu sanalarga bo'sh boshqa libosga almashtirish; narx farqi serverda hisoblanadi.
function LibosAlmashtirishForma({ z, bajar, narxXabari }) {
  const [bosh, setBosh] = useState(null)
  const [eski, setEski] = useState('')
  const [yangi, setYangi] = useState('')
  const [sabab, setSabab] = useState('')
  const [xato, setXato] = useState('')
  const qatorlar = z.libos_qatorlari || []
  const och = (e) => {
    if (!e.target.open || bosh) return
    boshLiboslar(z.olib_ketish, z.qaytarish).then(setBosh).catch((x) => setXato(xatoMatni(x)))
  }
  const mavjud = (bosh || []).filter((l) => !l.band && !l.qulflangan && !qatorlar.some((q) => q.id === l.id))
  const eskiId = eski || qatorlar[0]?.id
  const eskiNarx = qatorlar.find((q) => String(q.id) === String(eskiId))?.narx || 0
  const yangiL = mavjud.find((l) => String(l.id) === String(yangi))
  const [usul, setUsul] = useState('naqd')  // C-07: arzonroq libos va to'langan summa yangi jamidan oshsa — farq qaytariladi
  const farq = (l) => l.ijara_narxi - eskiNarx
  const qaytadi = yangiL ? Math.max(0, z.tolangan - (z.jami + farq(yangiL))) : 0
  return (
    <details className="blok amal" onToggle={och}>
      <summary>Libosni almashtirish</summary>
      <div className="stack">
        {xato && <p className="xato">{xato}</p>}
        <label>Qaysi libos
          <select value={eskiId} onChange={(e) => setEski(e.target.value)}>
            {qatorlar.map((q) => <option key={q.id} value={q.id}>{q.artikul} {q.nomi} · {som(q.narx)}</option>)}
          </select>
        </label>
        {bosh && mavjud.length === 0 && <p className="malumot">Bu sanalarga bo'sh boshqa libos yo'q.</p>}
        {mavjud.length > 0 && (
          <label>Yangi libos
            <select value={yangi} onChange={(e) => setYangi(e.target.value)}>
              <option value="">Tanlang</option>
              {mavjud.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.artikul} {l.nomi}{l.olcham ? ` · ${l.olcham}` : ''} · {som(l.ijara_narxi)}{farq(l) ? ` (${farq(l) > 0 ? '+' : '−'}${som(Math.abs(farq(l)))})` : ''}
                </option>
              ))}
            </select>
          </label>
        )}
        {yangiL && <p className="malumot">Jami {som(z.jami)} → {som(z.jami + farq(yangiL))}{qaytadi > 0 ? `; mijozga ${som(qaytadi)} qaytariladi` : ''}.</p>}
        {qaytadi > 0 && <UsulTanlov usul={usul} onUsul={setUsul} yorliq="Farq qanday qaytariladi" />}
        <label>Sabab<input value={sabab} onChange={(e) => setSabab(e.target.value)} /></label>
        <button className="ikkinchi" disabled={!eskiId || !yangi}
          onClick={() => bajar(() => libosAlmashtirish(z.id, { eski: Number(eskiId), yangi: Number(yangi), sabab, ...(qaytadi > 0 ? { usul } : {}) }), narxXabari('Libos almashtirildi.'))
            .then((ok) => { if (ok) { setYangi(''); setEski(''); setSabab(''); setBosh(null) } })}>Almashtirish</button>
      </div>
    </details>
  )
}

// Saqlangan zakazga salonchini belgilash yoki olib tashlash (FT-6.3).
function SalonchiTanlash({ z, bajar }) {
  const [royxat, setRoyxat] = useState(null)
  const [tanlov, setTanlov] = useState(z.salonchi?.id || '')
  const och = (e) => e.target.open && !royxat && salonchilar().then(setRoyxat).catch(() => setRoyxat([]))
  return (
    <details className="blok amal" onToggle={och}>
      <summary>Salonchi{z.salonchi ? `: ${z.salonchi.ism}` : ''}</summary>
      <div className="stack">
        {royxat && royxat.length === 0 && !z.salonchi && <p className="malumot">Salonchi yo'q — «Mijozlar» → «Salonchilar» bo'limida qo'shing.</p>}
        <select value={tanlov} onChange={(e) => setTanlov(e.target.value)} aria-label="Salonchi">
          <option value="">Salonchisiz</option>
          {z.salonchi && !(royxat || []).some((s) => s.id === z.salonchi.id) && <option value={z.salonchi.id}>{z.salonchi.ism}</option>}
          {(royxat || []).map((s) => <option key={s.id} value={s.id}>{s.ism}{s.salon_nomi ? ` · ${s.salon_nomi}` : ''}</option>)}
        </select>
        <button className="ikkinchi" disabled={String(tanlov) === String(z.salonchi?.id || '')}
          onClick={() => bajar(() => zakazSalonchi(z.id, tanlov ? Number(tanlov) : null), tanlov ? 'Salonchi belgilandi.' : 'Salonchi olib tashlandi.')}>Saqlash</button>
      </div>
    </details>
  )
}

// Keng ekranda asosiy amal o'ng panelda ochiq turadi (katta tugma yashirin — ichki.css dagi 768px bilan bir xil);
// telefonda tugma shu blokka olib boradi. Ekran burilib kengaysa blok ochiladi, aks holda tugmasiz yopiq qolardi.
const KENG = '(min-width: 768px)'

function Amal({ sarlavha, children, id }) {
  const ref = useRef(null)
  useEffect(() => {
    if (id !== 'asosiy-amal' || !window.matchMedia) return undefined
    const mq = window.matchMedia(KENG)
    const och = () => { if (mq.matches && ref.current) ref.current.open = true }
    och()
    mq.addEventListener?.('change', och)
    return () => mq.removeEventListener?.('change', och)
  }, [id])
  return (
    <details className="blok amal" id={id} ref={ref}>
      <summary>{sarlavha}</summary>
      <div className="stack">{children}</div>
    </details>
  )
}

// To'lov formasi (A-12): summa standart — to'liq qoldiq (bir bosishda qabul), «To'liq / 50% / 30%», usul — tugmalar.
// Click/Payme havolasi bloki olib tashlandi (A-36): bu usullar 2026-11-01 dan tanlovda yo'q edi.
function TolovForma({ sarlavha, maks, onYuborish, usulsiz, foizlar, id = 'asosiy-amal', izoh }) {
  const [summa, setSumma] = useState(String(maks))
  const [usul, setUsul] = useState('naqd')
  const n = Number(summa)
  return (
    <Amal sarlavha={sarlavha} id={id || undefined}>
      {izoh && <p className="ogohlantirish">{izoh}</p>}
      <TolovTanlov maks={maks} summa={summa} onSumma={setSumma} usul={usul} onUsul={setUsul} usulsiz={usulsiz} foizlar={foizlar} />
      <button disabled={!(n > 0) || n > maks} onClick={() => onYuborish(n, usul)}>
        Qabul qilish
      </button>
    </Amal>
  )
}

// FT-21.5: sotuvchi kodni kiritadi — tizim darhol qo'llaydi yoki sababini ko'rsatadi.
function PromokodForma({ z, bajar }) {
  const [kod, setKod] = useState('')
  if (z.promokod) {
    return (
      <Amal sarlavha={`Promokod: ${z.promokod}`}>
        <p className="malumot">Chegirma: {som(z.promokod_chegirma)}</p>
        <button className="ikkinchi" onClick={() => bajar(() => promokodOlibTashla(z.id), 'Promokod olib tashlandi.')}>Olib tashlash</button>
      </Amal>
    )
  }
  return (
    <Amal sarlavha="Promokod">
      <label>Kod
        <input value={kod} maxLength={30} autoCapitalize="characters" onChange={(e) => setKod(e.target.value.toUpperCase())} />
      </label>
      <button disabled={!kod.trim()}
        onClick={() => bajar(() => promokodQolla(z.id, kod), "Promokod qabul qilindi.").then((ok) => ok && setKod(''))}>
        Qo'llash
      </button>
    </Amal>
  )
}

// C-06/C-15: chegirmani olib tashlash va so'rovni qaytarib olish — `DELETE /api/zakazlar/<id>/chegirma/` (D3).
// Olib tashlanadi faqat tayyor chegirma (rahbar tasdiqlagani bu yo'l bilan olinmaydi) va avans olinguncha
const CHEGIRMA_OLIB_TASHLASH = true

// C-06: chegirma so'rovi kutilayotganda — nima va qancha so'ralgani, kim so'ragani; so'rovni qaytarib olish (avans olish uchun)
function ChegirmaKutilmoqda({ z, bajar }) {
  const c = z.chegirma_sorovi
  const [surov, setSurov] = useState(false)
  const miqdor = chegirmaMiqdori(z, c)
  const vaqt = new Date(c.yaratilgan)
  const soat = `${String(vaqt.getHours()).padStart(2, '0')}:${String(vaqt.getMinutes()).padStart(2, '0')}`
  return (
    <section className="blok chegirma-kutilmoqda" aria-label="Chegirma so'rovi">
      <p><b>{c.sotuvchi || 'Sotuvchi'}</b> {soat} da {c.foiz != null ? `${Number(c.foiz)}% (${som(miqdor)})` : som(miqdor)} chegirma so'radi — {c.nomi.toLowerCase()}. Rahbar qarori kutilmoqda.</p>
      <p className="malumot">Tasdiqlansa yangi jami {som(z.asosiy_narx + z.ustama - (z.promokod_chegirma || 0) - miqdor)}. Qaror kelguncha avans olinmaydi.</p>
      {CHEGIRMA_OLIB_TASHLASH && <button type="button" className="ikkinchi kichik" onClick={() => setSurov(true)}>So'rovni qaytarib olish</button>}
      {surov && (
        <Tasdiq sarlavha="So'rov qaytarib olinsinmi?" tugma="Ha, qaytarib olish" xavfli={false}
          matn={`Zakaz chegirmasiz narxda (${som(z.jami)}) davom etadi — avans qabul qilish mumkin bo'ladi.`}
          onYop={() => setSurov(false)} onTasdiq={() => { setSurov(false); bajar(() => chegirmaOlibTashla(z.id), "So'rov qaytarib olindi.") }} />
      )}
    </section>
  )
}

// C-15: tayyor chegirma tugmasida summa, qo'llashdan oldin tasdiq; qo'llangach forma o'rnida — qaysi chegirma va «Olib tashlash»
function ChegirmaForma({ zakazId, z, bajar }) {
  const [tayyor, setTayyor] = useState([])
  const [foiz, setFoiz] = useState('')
  const [tur, setTur] = useState('foiz')
  const [tanlangan, setTanlangan] = useState(null)  // tasdiq kutayotgan tayyor chegirma
  const [olibSurov, setOlibSurov] = useState(false)
  // chegirma ustama qo'shilgan summadan hisoblanadi (FT-4.3); promokod chegirmasi saqlanadi
  const asos = z.asosiy_narx + z.ustama - (z.promokod_chegirma || 0)
  const miqdor = chegirmaMiqdori(z, tur === 'foiz' ? { foiz: Number(foiz || 0) } : { summa: Number(foiz || 0) })
  const [sabab, setSabab] = useState('doimiy_mijoz')
  useEffect(() => { tayyorChegirmalar().then(setTayyor).catch(() => {}) }, [])
  const bor = z.chegirma - (z.promokod_chegirma || 0)
  if (bor > 0) {
    const c = z.chegirma_sorovi
    const olinadi = CHEGIRMA_OLIB_TASHLASH && c?.holat === 'tayyor'
    return (
      <Amal sarlavha={`Chegirma: −${som(bor)}`}>
        <p className="malumot">{c?.nomi ? `«${c.nomi}», ` : ''}−{som(bor)}{c?.holat === 'tasdiqlandi' && c.rahbar ? `, tasdiqladi: ${c.rahbar}` : ''}.{olinadi ? ' Avans olinguncha olib tashlash mumkin.' : ''}</p>
        {olinadi && <button type="button" className="ikkinchi" onClick={() => setOlibSurov(true)}>Olib tashlash</button>}
        {olibSurov && (
          <Tasdiq sarlavha="Chegirma olib tashlansinmi?" tugma="Ha, olib tashlash"
            matn={`Jami ${som(z.jami)} → ${som(z.jami + bor)}.`}
            onYop={() => setOlibSurov(false)}
            onTasdiq={() => { setOlibSurov(false); bajar(() => chegirmaOlibTashla(zakazId), `Chegirma olib tashlandi. Yangi jami ${som(z.jami + bor)}.`) }} />
        )}
      </Amal>
    )
  }
  const tMiqdor = (t) => chegirmaMiqdori(z, t)
  return (
    <Amal sarlavha="Chegirma">
      {tayyor.map((t) => (
        <button key={t.id} type="button" className="ikkinchi" onClick={() => setTanlangan(t)}>
          {t.nomi}: −{som(tMiqdor(t))}
        </button>
      ))}
      {tanlangan && (
        <Tasdiq sarlavha={`«${tanlangan.nomi}» qo'llansinmi?`} tugma="Ha, qo'llash" xavfli={false}
          matn={`Chegirma ${som(tMiqdor(tanlangan))}: jami ${som(z.jami)} → ${som(asos - tMiqdor(tanlangan))}. Rahbar tasdig'i kerak emas.`}
          onYop={() => setTanlangan(null)}
          onTasdiq={() => {
            const t = tanlangan
            setTanlangan(null)
            bajar(() => chegirmaSora(zakazId, { tayyor: t.id }), `Chegirma qo'llandi: −${som(tMiqdor(t))}. Yangi jami ${som(asos - tMiqdor(t))}.`)
          }} />
      )}
      <div className="segment">
        <button type="button" className={tur === 'foiz' ? '' : 'ikkinchi'} onClick={() => { setTur('foiz'); setFoiz('') }}>Foizda</button>
        <button type="button" className={tur === 'summa' ? '' : 'ikkinchi'} onClick={() => { setTur('summa'); setFoiz('') }}>Summada</button>
      </div>
      <label>{tur === 'foiz' ? 'Boshqa chegirma, %' : "Boshqa chegirma, so'm"}
        {tur === 'foiz'
          ? <input type="number" min="1" max="100" value={foiz} onChange={(e) => setFoiz(e.target.value)} />
          : <SummaInput value={foiz} onChange={(e) => setFoiz(e.target.value)} />}
      </label>
      {Number(foiz) > 0 && (
        <p className="malumot">Chegirma: {som(miqdor)} · yangi jami: <b>{som(asos - miqdor)}</b> (rahbar tasdiqlasa)</p>
      )}
      <label>Sabab
        <select value={sabab} onChange={(e) => setSabab(e.target.value)}>
          <option value="doimiy_mijoz">Doimiy mijoz</option>
          <option value="nuqson">Libosda kichik nuqson</option>
          <option value="boshqa">Boshqa</option>
        </select>
      </label>
      <button disabled={!(Number(foiz) > 0)}
        onClick={() => bajar(() => chegirmaSora(zakazId, tur === 'foiz' ? { foiz, sabab } : { summa: Number(foiz), sabab }), "Rahbar tasdig'iga yuborildi.")}>
        Rahbardan so'rash
      </button>
    </Amal>
  )
}

// Rahbar xato yozilgan to'lovni tuzatadi (naqd «Terminal» deb yoki summa xato) — faqat smena ochiq paytda
function TolovTuzatish({ t, onYuborish }) {
  const [usul, setUsul] = useState(t.usul)
  const [summa, setSumma] = useState(String(t.summa))
  const [sabab, setSabab] = useState('')
  const ozgardi = usul !== t.usul || Number(summa) !== t.summa
  return (
    <details className="tolov-tuzatish">
      <summary className="havola-tugma">Tuzatish</summary>
      <div className="stack">
        <label>To'lov usuli
          <select value={usul} onChange={(e) => setUsul(e.target.value)}>
            <option value="naqd">Naqd</option><option value="karta">Terminal</option><option value="otkazma">O'tkazma</option>
          </select>
        </label>
        <label>Summa<SummaInput value={summa} onChange={(e) => setSumma(e.target.value)} /></label>
        <label>Sabab<input value={sabab} maxLength={200} placeholder="masalan: naqd edi, terminal deb yozilgan" onChange={(e) => setSabab(e.target.value)} /></label>
        <button className="kichik" disabled={!ozgardi || !sabab.trim() || !(Number(summa) > 0)}
          onClick={() => onYuborish({ usul, summa: Number(summa), sabab })}>Tuzatishni saqlash</button>
      </div>
    </details>
  )
}

// C-18: avval forma tekshiruvi (to'ldirilmaguncha tugma o'chiq, sababi ostida), keyin erta berish tasdig'i.
// C-03(4): rahbar tasdig'ini kutayotgan o'tkazma bo'lsa — ogohlantirish (pul kelmasa qoldiq qayta olinadi)
function BerishForma({ onYuborish, soz, libosZalogi, olibKetish, pulsiz, kutilayotgan = 0 }) {
  const TURLAR = [['pul', 'Pul', 'zalog_pul'], ['hujjat', 'Hujjat', 'zalog_hujjat'], ['tillo', 'Tillo buyum', 'zalog_tillo']]
    .filter(([t, , k]) => (!soz || soz[k]) && !(pulsiz && t === 'pul'))  // admin panelda yoqilgan turlar (FT-7.1); kassir rejimida sotuvchi pul olmaydi
  const [tanlov, setTuri] = useState('')
  const turi = TURLAR.some(([t]) => t === tanlov) ? tanlov : TURLAR[0]?.[0]
  const [f, setF] = useState({})
  const [surov, setSurov] = useState(false)  // olib ketish sanasidan oldin berish tasdig'i
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const ertaMi = () => Boolean(olibKetish) && olibKetish > new Date().toLocaleDateString('sv-SE')  // YYYY-MM-DD, mahalliy sana
  const pulSumma = f.summa ?? (libosZalogi ? String(libosZalogi) : '')  // standart — libos(lar)ning zalog summasi
  const zalog = turi === 'pul'
    ? { turi, summa: Number(pulSumma || 0) }
    : turi === 'hujjat'
      ? { turi, hujjat_turi: f.hujjat_turi, hujjat_raqami: f.hujjat_raqami }
      : { turi, tavsif: f.tavsif, ogirlik_gr: f.ogirlik_gr, summa: Number(f.summa || 0) }
  // backend (rental.libos_berish) talablari bilan bir xil
  const yetmaydi = turi === 'pul' ? [!(Number(pulSumma) > 0) && 'zalog summasi']
    : turi === 'hujjat' ? [!f.hujjat_turi?.trim() && 'hujjat turi', !f.hujjat_raqami?.trim() && 'hujjat raqami']
      : [!f.tavsif?.trim() && 'tavsif', !(Number(f.ogirlik_gr) > 0) && "og'irligi"]
  const kerak = yetmaydi.filter(Boolean)
  return (
    <Amal sarlavha="Libosni berish (zalog)" id="asosiy-amal">
      {kutilayotgan > 0 && <p className="ogohlantirish">{som(kutilayotgan)} o'tkazma rahbar tasdig'ini kutmoqda — pul kelmasa, qoldiq mijozdan qayta olinadi.</p>}
      <label>Zalog turi
        <select value={turi} onChange={(e) => { setTuri(e.target.value); setF({}) }}>
          {TURLAR.map(([t, nom]) => <option key={t} value={t}>{nom}</option>)}
        </select>
      </label>
      {turi === 'pul' && <label>Zalog summasi *<SummaInput value={pulSumma} onChange={set('summa')} /></label>}
      {turi === 'hujjat' && (<>
        <label>Hujjat turi *<input placeholder="pasport" value={f.hujjat_turi || ''} onChange={set('hujjat_turi')} /></label>
        <label>Raqami *<input value={f.hujjat_raqami || ''} onChange={set('hujjat_raqami')} /></label>
      </>)}
      {turi === 'tillo' && (<>
        <label>Tavsif *<input placeholder="uzuk" value={f.tavsif || ''} onChange={set('tavsif')} /></label>
        <label>Og'irligi, g *<input type="number" step="0.01" value={f.ogirlik_gr || ''} onChange={set('ogirlik_gr')} /></label>
        <label>Taxminiy qiymat<SummaInput onChange={set('summa')} /></label>
      </>)}
      <button disabled={kerak.length > 0} onClick={() => (ertaMi() ? setSurov(true) : onYuborish([zalog], false))}>Zalogni qabul qilib berish</button>
      {kerak.length > 0 && <p className="malumot tugma-sabab">To'ldiring: {kerak.join(', ')}.</p>}
      {surov && (
        <Tasdiq sarlavha="Libos oldinroq beriladimi?" tugma="Ha, hozir berish" xavfli={false}
          matn={`Olib ketish sanasi ${sanaMatni(olibKetish)} — hali kelmagan. Libos hozir berilsa, bron bugundan boshlanadi (shu kunlarda libos boshqa zakazda band bo'lsa, berib bo'lmaydi).`}
          onYop={() => setSurov(false)} onTasdiq={() => { setSurov(false); onYuborish([zalog], true) }} />
      )}
    </Amal>
  )
}

// C-19, C-20, C-10: qaytarish — zalogdan ushlanadigan, mijozga qaytadigan va qo'shimcha to'lanadigan summa jonli;
// qo'shimchani mijoz hozir to'lasa — belgi va usul; «aksessuar yo'q» — qaysi dona yo'qligi; yirtiq/dog' — libos ta'mirga
function QaytarishForma({ onYuborish, tillo, qaytarish, kechikishJarimasi, pulsiz, pulZalog = 0, aksessuarlar = [] }) {
  const [f, setF] = useState({ tekshiruv: 'butun' })
  const [usul, setUsul] = useState('naqd')
  const [tolandi, setTolandi] = useState(false)
  const [yoqolgan, setYoqolgan] = useState([])
  const [bugun] = useState(() => new Date().toLocaleDateString('sv-SE'))  // YYYY-MM-DD, mahalliy sana
  // Kechikkan qaytarish: jarima avtomatik hisoblanishi yoki o'chirilgani (jim nol jarima bo'lmasin)
  const kechikkan = qaytarish && qaytarish < bugun ? Math.round((new Date(bugun) - new Date(qaytarish)) / 86400000) : 0
  const kechJarima = kechikkan > 0 && kechikishJarimasi > 0 ? kechikkan * kechikishJarimasi : 0
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  // backend (rental.libos_qaytarish) hisobi: jarima avval pul zalogidan ushlanadi, ortig'i — qo'shimcha to'lov yoki qarz
  const jarimaJami = Number(f.jarima || 0) + kechJarima
  const ushlanadi = Math.min(jarimaJami, pulZalog)
  const qoshimcha = jarimaJami - ushlanadi
  const mijozga = pulZalog - ushlanadi
  const aksYoq = f.tekshiruv === 'aksessuar_yoq'
  const body = {
    tekshiruv: f.tekshiruv, jarima: Number(f.jarima || 0), jarima_tolandi: tolandi && !pulsiz ? qoshimcha : 0,
    ...(tolandi && qoshimcha > 0 ? { usul } : {}),
    ...(aksYoq ? { yoqolgan_donalar: yoqolgan } : {}),
    ...(f.tortilgan_gr ? { tortilgan_gr: f.tortilgan_gr } : {}),
    izoh: f.izoh || '',
  }
  return (
    <Amal sarlavha="Qaytarish" id="asosiy-amal">
      {/* A-16: kassadan pul chiqadigan joy — qancha qaytishi oldindan ko'rinadi */}
      {pulZalog > 0 && !pulsiz && jarimaJami === 0 && (
        <p className="zalog-qaytadi">Pul zalog <b>{som(pulZalog)}</b> — mijozga qaytariladi.</p>
      )}
      {kechikkan > 0 && kechikishJarimasi > 0 && (
        <p className="malumot">Kechikish: {kechikkan} kun · avtomatik jarima {som(kechJarima)} ({som(kechikishJarimasi)} × {kechikkan}).</p>
      )}
      {kechikkan > 0 && kechikishJarimasi === 0 && (
        <p className="ogohlantirish">
          Mijoz {kechikkan} kun kechikdi, lekin kechikish jarimasi o'chirilgan — jarima hisoblanmaydi.
          Kerak bo'lsa pastdagi «Jarima» maydoniga qo'lda kiriting yoki Sozlama → Kechikish jarimasi bo'limida yoqing.
        </p>
      )}
      <label>Holat tekshiruvi
        <select value={f.tekshiruv} onChange={(e) => { set('tekshiruv')(e); setYoqolgan([]) }}>
          <option value="butun">Butun</option><option value="dog">Dog'</option>
          <option value="yirtiq">Yirtiq</option><option value="aksessuar_yoq">Aksessuar yo'q</option>
        </select>
      </label>
      {(f.tekshiruv === 'yirtiq' || f.tekshiruv === 'dog') && (
        <p className="malumot">Libos «ta'mirda» holatiga o'tadi — ta'mirlanmaguncha ijaraga chiqmaydi.</p>
      )}
      {aksYoq && aksessuarlar.length > 0 && (
        <fieldset className="yoqolgan-donalar">
          <legend>Qaysi aksessuar qaytmadi?</legend>
          {aksessuarlar.map((a) => (
            <label key={a.dona_id} className="belgi-qator">
              <input type="checkbox" checked={yoqolgan.includes(a.dona_id)}
                onChange={(e) => setYoqolgan(e.target.checked ? [...yoqolgan, a.dona_id] : yoqolgan.filter((x) => x !== a.dona_id))} />
              {a.nomi} ({a.yorliq})
            </label>
          ))}
        </fieldset>
      )}
      <label>Jarima<SummaInput onChange={set('jarima')} /><Info nom="Jarima">Libosga yetgan zarar uchun summa: dog', yirtiq, yo'qolgan aksessuar. Avval pul zalogidan ushlanadi; zalog yetmasa, qolgani mijoz qarzi bo'ladi. Kechikish jarimasi (yoqilgan bo'lsa) bunga o'zi qo'shiladi.</Info></label>
      {jarimaJami > 0 && (
        <dl className="qaytarish-hisob" aria-live="polite">
          {pulZalog > 0 && <div><dt>Zalogdan ushlanadi</dt><dd>{som(ushlanadi)}</dd></div>}
          {pulZalog > 0 && !pulsiz && <div><dt>Mijozga qaytariladi</dt><dd>{som(mijozga)}</dd></div>}
          {qoshimcha > 0 && <div className="qarz"><dt>Mijoz qo'shimcha to'laydi</dt><dd>{som(qoshimcha)}</dd></div>}
        </dl>
      )}
      {qoshimcha > 0 && !pulsiz && (
        <>
          <label className="belgi-qator">
            <input type="checkbox" checked={tolandi} onChange={(e) => setTolandi(e.target.checked)} />
            {som(qoshimcha)} hozir to'landi
          </label>
          {tolandi ? <UsulTanlov usul={usul} onUsul={setUsul} yorliq="Jarima to'lov usuli" />
            : <p className="malumot">Belgilanmasa, {som(qoshimcha)} mijoz qarzi bo'lib qoladi.</p>}
        </>
      )}
      {tillo && <label>Tillo qayta tortildi, g<input type="number" step="0.01" onChange={set('tortilgan_gr')} /><Info nom="Tillo og'irligi">Zalogga olingan tillo buyumni qaytarishdan oldin qayta torting. Berilgandagi og'irlikdan farq qilsa, qaytarish to'xtatiladi — buyum almashtirilmaganiga ishonch hosil qilish uchun.</Info></label>}
      <button disabled={aksYoq && aksessuarlar.length > 0 && yoqolgan.length === 0} onClick={() => onYuborish(body)}>Qaytarishni rasmiylashtirish</button>
      {aksYoq && aksessuarlar.length > 0 && yoqolgan.length === 0 && <p className="malumot tugma-sabab">Qaysi aksessuar qaytmaganini belgilang.</p>}
    </Amal>
  )
}

// C-04: tasdiqda va natijada aniq summa — backend oldindan hisobi (`GET .../bekor/`, bitta haqiqat manbai);
// C-20: qaytarim usuli (standart — asl to'lov usuli), rahbarga qoidadan boshqa foiz
function BekorForma({ onYuborish, soz, z, rahbar }) {
  const qoida = (soz?.qaytarish_qoidasi || [[30, 100], [7, 50], [0, 0]])
    .map(([kun, foiz]) => (kun > 0 ? `${kun}+ kun — ${foiz}%` : `undan kam — ${foiz}%`)).join(', ')
  const [sabab, setSabab] = useState('')
  const [foizQolda, setFoizQolda] = useState('')
  const aslUsul = z.tolovlar.find((t) => ['avans', 'qoldiq'].includes(t.tur) && t.tasdiq !== 'kelmadi')?.usul
  const [usul, setUsul] = useState(['naqd', 'karta', 'otkazma'].includes(aslUsul) ? aslUsul : 'naqd')
  const [surov, setSurov] = useState(false)
  const [h, setH] = useState(null)
  const [hXato, setHXato] = useState('')
  const pulBor = z.tolangan > 0
  useEffect(() => {
    if (!pulBor) return undefined
    const foiz = rahbar && foizQolda !== '' ? Number(foizQolda) : undefined
    const t = setTimeout(() => {
      bekorHisobi(z.id, foiz).then((r) => { setH(r); setHXato('') }).catch((e) => setHXato(xatoMatni(e)))
    }, foiz === undefined ? 0 : 300)
    return () => clearTimeout(t)
  }, [z.id, z.tolangan, pulBor, rahbar, foizQolda])
  const avansNomi = soz?.qaytarish_asosi === 'tolangan' ? "To'langan" : 'Avans'
  const hisob = !pulBor ? "To'lov olinmagan — pul qaytarilmaydi."
    : !h ? '' : `${avansNomi} ${som(h.avans)}, olib ketishgacha ${h.qolgan_kun} kun — ${h.foiz}% qaytadi.`
      + (h.oldindan > 0 ? ` Avansdan ortiq ${som(h.oldindan)} to'liq qaytadi.` : '')
      + ` Mijozga ${som(h.qaytariladi)} qaytariladi, ${som(h.ushlab_qolinadi)} ushlab qolinadi.`
  const tayyor = !pulBor || Boolean(h)
  return (
    <Amal sarlavha="Zakazni bekor qilish">
      <p className="malumot">Qaytarish qoidasi: {qoida}.</p>
      {pulBor && (h ? <p className="bekor-hisob" aria-live="polite">{hisob}</p> : !hXato && <p className="malumot">Hisoblanmoqda…</p>)}
      {hXato && <p className="xato" role="alert">{hXato}</p>}
      {pulBor && rahbar && (
        <label>Qaytariladigan foiz (qoidadan boshqa bo'lsa)
          <input type="number" min="0" max="100" value={foizQolda} placeholder={h && foizQolda === '' ? String(h.foiz) : ''}
            onChange={(e) => setFoizQolda(e.target.value)} />
        </label>
      )}
      {pulBor && h?.qaytariladi > 0 && <UsulTanlov usul={usul} onUsul={setUsul} yorliq="Pul qanday qaytariladi" />}
      <label>Sabab<input value={sabab} onChange={(e) => setSabab(e.target.value)} /></label>
      <button className="xavfli" disabled={!sabab.trim() || !tayyor || Boolean(hXato)} onClick={() => setSurov(true)}>Bekor qilish</button>
      {surov && (
        <Tasdiq sarlavha="Zakazni bekor qilasizmi?" tugma="Ha, bekor qilish"
          matn={`Zakaz #${z.raqam} bekor qilinadi (sabab: ${sabab.trim()}). ${hisob} Bu amalni qaytarib bo'lmaydi.`}
          onYop={() => setSurov(false)}
          onTasdiq={() => {
            setSurov(false)
            onYuborish({ sabab, ...(pulBor && h?.qaytariladi > 0 ? { usul } : {}),
              ...(rahbar && foizQolda !== '' ? { qaytariladigan_foiz: Number(foizQolda) } : {}) })
          }} />
      )}
    </Amal>
  )
}

const PRIMERKA_HOLAT = { rejalashtirilgan: 'rejalashtirilgan', otkazildi: "o'tkazildi", bekor: 'bekor qilingan' }
const vaqtMatni = (v) => new Date(v).toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })

const OLCHAMLAR = [['kokrak', "Ko'krak"], ['bel', 'Bel'], ['son', 'Son'], ['boy', "Bo'y"], ['oyoq_olchami', 'Oyoq kiyim']]

// FT-8.4: mijoz o'lchamlari primerkada yangilanadi (keyingi safar libos tanlashda o'lcham filtriga qo'yiladi)
function OlchamForma({ z, bajar }) {
  const [f, setF] = useState({})
  const q = (k) => f[k] ?? z.olchamlar?.[k] ?? ''
  const tana = () => {
    const b = { kiyim_olchami: String(q('kiyim_olchami')) }
    for (const [k] of OLCHAMLAR) b[k] = q(k) === '' ? null : Number(q(k))
    return b
  }
  return (
    <details className="amal">
      <summary>Mijoz o'lchamlari</summary>
      <div className="stack">
        <div className="qator keng olcham-qator">
          {OLCHAMLAR.map(([k, nom]) => (
            <label key={k}>{nom}<input type="number" min="0" value={q(k)} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></label>
          ))}
        </div>
        <label>Kiyim o'lchami (masalan, 44 yoki M)
          <input value={q('kiyim_olchami')} maxLength={20} onChange={(e) => setF({ ...f, kiyim_olchami: e.target.value })} />
        </label>
        <button type="button" className="ikkinchi" disabled={Object.keys(f).length === 0}
          onClick={() => bajar(() => mijozOzgartir(z.mijoz_id, tana()), "O'lchamlar saqlandi.").then((ok) => ok && setF({}))}>
          O'lchamlarni saqlash
        </button>
      </div>
    </details>
  )
}

// FT-2.8: primerka sanasi va vaqti; moslash kerak bo'lsa narxi zakazga qo'shiladi.
function PrimerkaForma({ z, bajar, ochiq }) {
  const [vaqt, setVaqt] = useState('')
  const [f, setF] = useState({})
  const qiymat = (p, k) => f[`${p.id}_${k}`] ?? p[k] ?? ''
  const set = (p, k) => (e) => setF({ ...f, [`${p.id}_${k}`]: e.target.value })
  return (
    <Amal sarlavha={`Primerka (${z.primerkalar.filter((p) => p.holat !== 'bekor').length})`}>
      {z.primerkalar.map((p) => (
        <div key={p.id} className={`tasdiq ${p.holat === 'bekor' ? 'bajarilgan' : ''}`}>
          <span>
            <b>{vaqtMatni(p.vaqt)}</b> · {PRIMERKA_HOLAT[p.holat]}
            {p.moslash_narxi > 0 && ` · moslash ${som(p.moslash_narxi)}`}
            {p.natija && ` · ${p.natija}`}
          </span>
          {ochiq && p.holat !== 'bekor' && (
            <>
              <label>Natija<input value={qiymat(p, 'natija')} maxLength={300} onChange={set(p, 'natija')} /></label>
              <label>Moslash narxi, so'm (kerak bo'lmasa 0)
                <SummaInput value={qiymat(p, 'moslash_narxi')} onChange={set(p, 'moslash_narxi')} />
              </label>
              <div className="qator">
                <button className="ikkinchi kichik" onClick={() => bajar(() => primerkaOzgartir(p.id, {
                  natija: String(qiymat(p, 'natija')), moslash_narxi: Number(qiymat(p, 'moslash_narxi')) || 0, holat: 'otkazildi',
                }), 'Primerka natijasi saqlandi.').then((ok) => ok && setF({}))}>O'tkazildi — saqlash</button>
                <button className="ikkinchi kichik" onClick={() => bajar(() => primerkaOzgartir(p.id, { holat: 'bekor' }), 'Primerka bekor qilindi.')}>Bekor qilish</button>
              </div>
            </>
          )}
        </div>
      ))}
      {ochiq && <OlchamForma z={z} bajar={bajar} />}
      {ochiq && (
        <>
          <label>Sana va vaqt
            <input type="datetime-local" value={vaqt} max={`${z.olib_ketish}T23:59`} onChange={(e) => setVaqt(e.target.value)} />
          </label>
          <button disabled={!vaqt}
            onClick={() => bajar(() => primerkaBelgila(z.id, new Date(vaqt).toISOString()), 'Primerka belgilandi.').then((ok) => ok && setVaqt(''))}>
            Primerka belgilash
          </button>
        </>
      )}
    </Amal>
  )
}

// Yangi zakazdagi kalendar: o'tgan kun tanlanmaydi, oraliq oldindan ko'rinadi. Joriy sanalar tanlangan holda ochiladi.
function KochirishForma({ z, onYuborish }) {
  const [dan, setDan] = useState(z.olib_ketish)
  const [gacha, setGacha] = useState(z.qaytarish)
  const [sabab, setSabab] = useState('')
  const [surov, setSurov] = useState(false)
  const ozgardi = dan && gacha && (dan !== z.olib_ketish || gacha !== z.qaytarish)
  return (
    <Amal sarlavha="Sanani ko'chirish">
      <CalendarPage dan={dan} gacha={gacha} onTanla={(d, g) => { setDan(d); setGacha(g) }} />
      <label>Sabab (rahbarga xabarda ko'rinadi)<input value={sabab} onChange={(e) => setSabab(e.target.value)} /></label>
      <button disabled={!ozgardi} onClick={() => setSurov(true)}>Ko'chirish</button>
      {surov && (
        <Tasdiq sarlavha="Sanani ko'chirasizmi?" tugma="Ha, ko'chirish"
          matn={`${sanaMatni(z.olib_ketish)} – ${sanaMatni(z.qaytarish)} → ${sanaMatni(dan)} – ${sanaMatni(gacha)}. `
            + "Mavsumiy ustama va promokod chegirmasi yangi sanaga qarab qayta hisoblanadi; "
            + "narx to'langan summadan pastga tushmaydi."}
          onYop={() => setSurov(false)}
          onTasdiq={() => { setSurov(false); onYuborish({ dan, gacha, sabab: sabab.trim() }) }} />
      )}
    </Amal>
  )
}

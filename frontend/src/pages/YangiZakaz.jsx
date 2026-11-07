import { useEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import Vitrina from '../components/Vitrina'
import NavIkona from '../components/NavIkona'
import LibosSiluet from '../components/LibosSiluet'
import { SalonchiForma } from './Salonchilar'
import Manekin from '../components/Manekin'
import CalendarPage from '../components/kalendar/CalendarPage'
import { Bezak, Muhr, VaraqSana } from '../components/Varaq'
import { aksessuarManekinSaqla, boshAksessuarlar, filiallar, boshLiboslar, kategoriyalar, mijozQidir, qulf, qulfOchir, manekinSaqla, salonchiQosh, salonchilar, saqlangan, som, ustamaFoiz, zakazYarat } from '../api'
import SummaInput from '../components/SummaInput'

// Yangi zakaz: 1) sana, 2) libos tanlash, 3) mijoz va saqlash (4-bo'lim). O'ngda (telefonda pastda) zakaz
// varaqasi tanlangan sari to'ladi; saqlangach unga muhr bosiladi.
// C-13: qoralama xodimga bog'langan — planshetga boshqa xodim kirsa, oldingining sana va mijozi unda ochilmaydi
// (aks holda zakaz va bonus boshqa xodimga yozilib ketardi). Eski umumiy kalit bir marta tozalanadi.
const QORALAMA = 'libosa.yangi_zakaz'
const qoralamaKaliti = () => `${QORALAMA}.${saqlangan.xodim()?.id ?? 'nomalum'}`
const bugunIso = () => { const t = new Date(); return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}` }
const qoralamaOl = () => {
  let q
  try { sessionStorage.removeItem(QORALAMA); q = JSON.parse(sessionStorage.getItem(qoralamaKaliti())) || {} } catch { return {} }
  // Kecha qoldirilgan qoralama: o'tgan sana bilan davom etib bo'lmaydi (server rad etadi) — sana qaytadan tanlanadi
  if (q.dan && q.dan < bugunIso()) q = { ...q, dan: '', gacha: '', qadam: 1 }
  // Tanlangan liboslar qoralamada saqlanmaydi — 3-qadamga libossiz qaytib qolmaslik uchun libos tanloviga
  return { ...q, qadam: Math.min(q.qadam || 1, 2) }
}
// Telefondagi raqamlar soni: 9 (90 123 45 67) yoki 12 (998 90 123 45 67) — to'liq raqam
const telefonRaqamlari = (t) => t.replace(/\D/g, '').length
const faqatRaqam = (t) => t.replace(/\D/g, '')
// Raqam to'liq terildimi: mahalliy 9 xona yoki +998 bilan 12 xona — shunda mijoz o'zi qidiriladi
// («+998 90 1234» kabi chala raqam bo'yicha «yangi mijoz» chiqib ketmasin)
const toliqRaqam = (t) => { const r = faqatRaqam(t); return r.startsWith('998') ? r.length === 12 : r.length === 9 }
// Shundan uzoq ijara odatda kalendarda adashib bosilgan bo'ladi — sotuvchi ogohlantiriladi
const UZOQ_IJARA_KUN = 7
// Server vaqti UTC da keladi — mahalliy vaqtda «25.10.2026 14:30»
const vaqtMatni = (s) => {
  const t = new Date(s), n = (x) => String(x).padStart(2, '0')
  return `${n(t.getDate())}.${n(t.getMonth() + 1)}.${t.getFullYear()} ${n(t.getHours())}:${n(t.getMinutes())}`
}
const kunlar = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000) + 1
const QADAMLAR = ['Sana', 'Libos', 'Mijoz']
// Bron muddati: «bugun 21:06», «ertaga 21:06» yoki «03.11.2026 21:06»
const muddatMatni = (s) => {
  const t = new Date(s), n = (x) => String(x).padStart(2, '0'), soat = `${n(t.getHours())}:${n(t.getMinutes())}`
  const kunFarqi = Math.round((new Date(t.getFullYear(), t.getMonth(), t.getDate()) - new Date().setHours(0, 0, 0, 0)) / 86400000)
  return kunFarqi === 0 ? `bugun ${soat}` : kunFarqi === 1 ? `ertaga ${soat}` : vaqtMatni(s)
}

// Zakaz varaqasi: to'y taklifnomasidek — sana, kimga, liboslar va jami tanlangan sari yozilib boradi.
// Saqlangach (muhr bilan) shu varaq zakazning yakuniy ko'rinishi bo'ladi.
function VaraqRoyxat({ liboslar, aksessuarlar, aksSoni, ustama, ustamaSumma }) {
  const aks = aksessuarlar.filter((a) => aksSoni[a.id] > 0)
  if (liboslar.length === 0 && aks.length === 0) return null
  return (
    <ul className="varaq-royxat">
      {liboslar.map((l) => (
        <li key={l.id}>
          {l.rasm ? <img src={l.rasm} alt="" /> : <span className="varaq-siluet"><LibosSiluet /></span>}
          <span><b>{l.artikul}</b> {l.nomi}</span>
          <span className="varaq-narx">{som(l.ijara_narxi)}</span>
        </li>
      ))}
      {aks.map((a) => (
        <li key={`a${a.id}`} className="varaq-aks">
          <span>{a.nomi} × {aksSoni[a.id]}</span>
          <span className="varaq-narx">{som(a.ijara_narxi * aksSoni[a.id])}</span>
        </li>
      ))}
      {ustama.foiz > 0 && (
        <li className="varaq-aks">
          <span>Ustama {ustama.foiz}% ({ustama.nomi || 'mavsumiy'})</span>
          <span className="varaq-narx">{som(ustamaSumma)}</span>
        </li>
      )}
    </ul>
  )
}

// Tashqaridan ochilganda (Kalendar katagi, Mijoz kartasi) — `boshlangich` = { n, dan?, gacha?, libos_id?, mijoz?: { telefon, fio } }.
// Har yangi `n` bir marta qo'llanadi va sessiya qoralamasi ustidan yoziladi; bo'limga keyin qaytilganda qoralama davom etadi
// (qo'llangan `n` modulda eslab qolinadi — App eski `boshlangich` ni uzatib tursa ham ish qayta tozalanmaydi. Sahifa yangilansa
// App dagi `n` hisobi ham, bu qiymat ham noldan boshlanadi — shuning uchun sessionStorage emas).
let qollanganN = null
const yangiBoshlangich = (b) => Boolean(b?.n) && b.n !== qollanganN
// Boshlang'ich qiymatlar: o'tgan sana olinmaydi; sana va libos bo'lsa — 2-qadam (libos yuklangach tanlanadi)
const boshlangichdan = (b) => {
  const sana = Boolean(b.dan && b.gacha && b.gacha >= b.dan && b.dan >= bugunIso())
  return { qadam: sana && b.libos_id ? 2 : 1, dan: sana ? b.dan : '', gacha: sana ? b.gacha : '',
    telefon: b.mijoz?.telefon || '', fio: b.mijoz?.fio || '', salonchi: '' }
}

export default function YangiZakaz({ boshlangich, ...props }) {
  const [faolN, setFaolN] = useState(() => (yangiBoshlangich(boshlangich) ? boshlangich.n : null))
  // ochiq turganda yangi `n` kelsa — forma yangidan (avvalgi render ma'lumotidan holat: React tavsiya qilgan usul)
  if (boshlangich?.n && boshlangich.n !== faolN && yangiBoshlangich(boshlangich)) setFaolN(boshlangich.n)
  useEffect(() => { if (faolN) qollanganN = faolN }, [faolN])
  return <YangiZakazForma key={faolN ?? 'qoralama'} boshlangich={faolN && boshlangich?.n === faolN ? boshlangich : null} {...props} />
}

function YangiZakazForma({ onTayyor, onTolov, boshlangich }) {
  const q0 = useState(() => (boshlangich ? boshlangichdan(boshlangich) : qoralamaOl()))[0]
  // Kalendardan kelgan libos — ro'yxat yuklangach tanlanadi (bir marta)
  const kutilganLibos = useRef(q0.qadam === 2 ? boshlangich?.libos_id : null)
  // Mijoz kartasidan kelgan ism faqat o'sha raqamga tegishli — raqam almashtirilsa (o'zgartirilmagan) ism ham tozalanadi
  const boshMijoz = useRef(boshlangich?.mijoz || null)
  const [qadam, setQadam] = useState(q0.qadam || 1) // 1 Sana → 2 Libos → 3 Mijoz
  const [dan, setDan] = useState(q0.dan || '')
  const [gacha, setGacha] = useState(q0.gacha || '')
  const [telefon, setTelefon] = useState(q0.telefon || '')
  const [mijoz, setMijoz] = useState(null)
  const [fio, setFio] = useState(q0.fio || '')
  const [saqlanmoqda, setSaqlanmoqda] = useState(false)
  const [manba, setManba] = useState('boshqa')
  const [salonchiRoyxat, setSalonchiRoyxat] = useState([])
  const [salonchi, setSalonchi] = useState(q0.salonchi || '')
  useEffect(() => { salonchilar().then(setSalonchiRoyxat).catch(() => {}) }, [])
  const tanlanganSalonchi = salonchiRoyxat.find((s) => String(s.id) === String(salonchi))
  const [bandlar, setBandlar] = useState(false)
  // Telefonda o'lcham, rang, narx, filial va «Bandlar ham» — «Filtr» tugmasi ortida (ro'yxat birinchi ekranda ko'rinsin)
  const [filtrOchiq, setFiltrOchiq] = useState(false)
  // Kategoriya tablari Sozlamadagi tartibda (alifbo emas): salonning asosiy kategoriyasi birinchi ochiladi
  const [katTartib, setKatTartib] = useState([])
  useEffect(() => { kategoriyalar().then((r) => setKatTartib(r.filter((k) => k.turi !== 'aksessuar').map((k) => k.nomi))).catch(() => {}) }, [])
  const [liboslar, setLiboslar] = useState(null)
  const [tanlangan, setTanlangan] = useState([])
  // Sahifadan chiqib ketilsa yoki sana o'zgarsa qulflar bo'shatiladi — boshqa sotuvchi 15 daqiqa kutmasin
  const qulflangan = useRef([])
  useEffect(() => { qulflangan.current = tanlangan.map((l) => l.id) }, [tanlangan])
  const qulflarniOchir = () => { qulflangan.current.forEach(qulfOchir); qulflangan.current = [] }
  useEffect(() => qulflarniOchir, [])
  const [aksessuarlar, setAksessuarlar] = useState([])
  const [aksSoni, setAksSoni] = useState({})
  const [xabar, setXabar] = useState('')
  const [zakaz, setZakaz] = useState(null)
  const [vitrina, setVitrina] = useState(false)
  // Saqlangach fokus sarlavhaga: ekran o'quvchi va klaviatura «Zakaz #N saqlandi» dan boshlaydi
  const sarlavha = useRef(null)
  useEffect(() => { if (zakaz) sarlavha.current?.focus() }, [zakaz])
  const [manekin, setManekin] = useState(null) // 4.5: tanlangan libos manekinda
  // FT-3.2: kategoriya, o'lcham, rang, narx bo'yicha filtr; qidiruvda band libos ham chiqadi (FT-2.2)
  const [filtr, setFiltr] = useState({ kat: '', olcham: '', rang: '', narx: '', q: '', filial: '' })
  // Filiallar: standart — shu qurilma filiali; biriktirilmagan libos hamma filialda ko'rinadi
  const [fil, setFil] = useState([])
  useEffect(() => {
    filiallar().then((r) => { setFil(r.filiallar); if (r.joriy) setFiltr((f) => ({ ...f, filial: String(r.joriy) })) }).catch(() => {})
  }, [])

  // Qoralama: 10 daqiqa harakatsizlikdan keyin chiqib ketilsa yoki sahifa yangilansa yarim zakaz yo'qolmaydi.
  useEffect(() => {
    try { sessionStorage.setItem(qoralamaKaliti(), JSON.stringify({ qadam, dan, gacha, telefon, fio, salonchi })) } catch { /* xotira yopiq */ }
  }, [qadam, dan, gacha, telefon, fio, salonchi])

  const aksJami = aksessuarlar.reduce((s, a) => s + a.ijara_narxi * (aksSoni[a.id] || 0), 0)
  const asosiy = tanlangan.reduce((s, l) => s + l.ijara_narxi, 0) + aksJami
  // FT-15.2: mavsumiy ustama olib ketish kuniga qarab; yakuniy narxni server hisoblaydi
  const [ustama, setUstama] = useState({ foiz: 0, nomi: null })
  useEffect(() => {
    let bekor = false
    const nol = { foiz: 0, nomi: null }
    const so = dan ? ustamaFoiz(dan).then((r) => ({ foiz: Number(r.foiz), nomi: r.nomi })).catch(() => nol) : Promise.resolve(nol)
    so.then((r) => { if (!bekor) setUstama(r) })
    return () => { bekor = true }
  }, [dan])
  const ustamaSumma = Math.round((asosiy * ustama.foiz) / 100)
  const jami = asosiy + ustamaSumma

  // Mijoz qidiruvi: to'liq raqam terilganda o'zi (300 ms dan keyin), chala raqamda — maydondan chiqqanda.
  // Natija qaysi raqamga tegishliligi eslab qolinadi: raqam o'zgarsa eski mijoz (yoki «yangi mijoz») hisobga olinmaydi.
  const [qidirilgan, setQidirilgan] = useState('')
  const sorov = useRef(0)
  const mijozniTekshir = async () => {
    const r = faqatRaqam(telefon)
    if (!r || r === qidirilgan) return
    const n = ++sorov.current
    setQidirilgan(r); setMijoz(null)
    let m
    try {
      const javob = await mijozQidir(telefon)
      m = javob?.topildi === false ? { yangi: true } : javob  // A-39: topilmasa 200 { topildi: false }
    } catch { m = { yangi: true } }  // eski backend 404 qaytaradi (o'tish davri); tarmoq xatosida ham — saqlashda server raqam bo'yicha topadi
    if (n === sorov.current) setMijoz(m)  // orada boshqa raqam qidirilgan bo'lsa — eski javob yozilmaydi
  }
  useEffect(() => {
    if (!toliqRaqam(telefon)) return undefined
    const t = setTimeout(mijozniTekshir, 300)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [telefon])
  const joriyMijoz = faqatRaqam(telefon) === qidirilgan ? mijoz : null
  // Yangi mijoz ismsiz yaratilmaydi: ro'yxat, eslatma va qo'ng'iroqlarda ism o'rnida raqam chiqib qolardi
  const ismKerak = Boolean(joriyMijoz?.yangi && !fio.trim())

  // Kalendardan kelgan libos: bo'sh bo'lsa qulf bilan tanlanadi va o'z kategoriyasi ochiladi; bo'lmasa — sababi bilan xabar
  const boshLibosniTanla = async (id, royxat) => {
    const libos = royxat.find((x) => x.id === id)
    if (libos && !libos.band && !libos.qulflangan) {
      try {
        await qulf(libos.id, dan, gacha)
        setTanlangan([libos])
        setFiltr((f) => ({ ...f, kat: libos.kategoriya, filial: libos.filial == null || String(libos.filial) === f.filial ? f.filial : '' }))
      } catch (e) { setXabar(e.response?.data?.detail || "Libosni tanlab bo'lmadi — ro'yxatdan boshqasini tanlang.") }
      return
    }
    let b = libos  // bo'shlar ro'yxatida yo'q — band yoki boshqa sotuvchi rasmiylashtiryapti: nomi va eng yaqin bo'sh sanasi uchun
    if (!b) { try { b = (await boshLiboslar(dan, gacha, true)).find((x) => x.id === id) } catch { /* xabar umumiy bo'ladi */ } }
    setXabar(!b ? "Tanlangan libos bu sanalarda bo'sh emas — ro'yxatdan boshqasini tanlang."
      : `${b.artikul} ${b.nomi} bu sanalarda ${b.qulflangan ? 'boshqa sotuvchi rasmiylashtiryapti'
        : `band${b.eng_yaqin_bosh ? ` (eng yaqin bo'sh sana: ${b.eng_yaqin_bosh})` : ''}`} — ro'yxatdan boshqasini tanlang.`)
  }

  const telefonOzgar = (t) => {
    setTelefon(t)
    const b = boshMijoz.current
    if (b && faqatRaqam(t) !== faqatRaqam(b.telefon || '')) { boshMijoz.current = null; if (fio === (b.fio || '')) setFio('') }
  }

  const tanlash = async (l) => {
    setXabar('')
    if (tanlangan.some((t) => t.id === l.id)) {
      qulfOchir(l.id)
      return setTanlangan(tanlangan.filter((t) => t.id !== l.id))
    }
    try {
      await qulf(l.id, dan, gacha) // 15 daqiqaga boshqa sotuvchidan yashiriladi
      setTanlangan([...tanlangan, l])
    } catch (e) {
      setXabar(e.response?.data?.detail || 'Libosni tanlab bo\'lmadi.')
      setLiboslar(await boshLiboslar(dan, gacha, bandlar, filtr.q))
    }
  }

  const saqlash = async () => {
    setXabar('')
    if (!telefon) return setXabar('Mijoz telefonini kiriting.')
    if (telefonRaqamlari(telefon) < 9) return setXabar("Telefon raqami to'liq emas: masalan, +998 90 123 45 67.")
    if (!joriyMijoz || ismKerak) return undefined  // tugma o'chiq bo'ladi; sababi tugma ostida yozilgan
    if (saqlanmoqda) return undefined // ikki marta bosilsa ikkinchi so'rov yuborilmaydi
    setSaqlanmoqda(true)
    try {
      const yaratildi = await zakazYarat({ telefon, fio: joriyMijoz.yangi ? fio.trim() : '', manba: joriyMijoz.yangi && !salonchi ? manba : undefined,
        salonchi: salonchi ? Number(salonchi) : undefined, dan, gacha, liboslar: tanlangan.map((l) => l.id),
        aksessuarlar: Object.entries(aksSoni).flatMap(([id, n]) => Array(n).fill(Number(id))) })
      try { sessionStorage.removeItem(qoralamaKaliti()) } catch { /* xotira yopiq */ }
      qulflangan.current = [] // server qulflarni o'zi olib tashladi
      setZakaz(yaratildi)
    } catch (e) {
      setXabar(e.response?.data?.detail || 'Zakazni saqlab bo\'lmadi.')
      // Faqat band bo'lib qolgan liboslar tanlovdan chiqadi; qolganlari (va mijoz ma'lumotlari) saqlanadi
      try {
        const l = await boshLiboslar(dan, gacha, bandlar, filtr.q)
        setLiboslar(l)
        setTanlangan((eski) => eski.filter((t) => l.some((x) => x.id === t.id && !x.band && !x.qulflangan)))
      } catch { /* tarmoq: tanlov o'zgarmaydi */ }
    } finally {
      setSaqlanmoqda(false)
    }
  }

  const yangi = () => {
    setZakaz(null); setLiboslar(null); setTanlangan([]); setMijoz(null); setQidirilgan(''); setAksessuarlar([]); setAksSoni({})
    setDan(''); setGacha(''); setTelefon(''); setFio(''); setSalonchi(''); setManba('boshqa'); setQadam(1)
  }

  // Sanalar to'lishi bilan libos ro'yxati o'zi yangilanadi («Liboslarni ko'rsatish» tugmasi kerak emas).
  useEffect(() => {
    if (!dan || !gacha || gacha < dan || zakaz) return undefined
    let bekor = false
    qulflarniOchir() // eski sanalar uchun olingan qulflar endi kerak emas — tanlov baribir tozalanadi
    Promise.all([boshLiboslar(dan, gacha, bandlar, filtr.q), boshAksessuarlar(dan, gacha)]).then(([l, a]) => {
      if (bekor) return
      setLiboslar(l); setAksessuarlar(a); setTanlangan([]); setAksSoni({})
      const id = kutilganLibos.current
      if (id) { kutilganLibos.current = null; boshLibosniTanla(id, l) }
    }).catch(() => {})
    return () => { bekor = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dan, gacha])

  // FT-1.4: boshqa sotuvchi libosni band qilsa yoki qulflasa, ro'yxat sahifani yangilamasdan o'zgaradi.
  const royxatOchiq = liboslar !== null && !zakaz
  useEffect(() => {
    if (!royxatOchiq || !dan || !gacha) return undefined
    const t = setInterval(async () => {
      try {
        const [l, a] = await Promise.all([boshLiboslar(dan, gacha, bandlar, filtr.q), boshAksessuarlar(dan, gacha)])
        setLiboslar(l)
        setAksessuarlar(a)
        // Aksessuar donasi orada boshqa zakazga ketgan bo'lsa, tanlangan soni bo'sh donalardan oshmasin
        setAksSoni((eski) => {
          const yangiSon = Object.fromEntries(Object.entries(eski).map(([id, n]) => [id, Math.min(n, a.find((x) => String(x.id) === id)?.bosh_soni || 0)]))
          return Object.keys(eski).some((id) => yangiSon[id] !== eski[id]) ? yangiSon : eski
        })
        // tanlangan libos orada band bo'lib qolgan bo'lsa (masalan, qulf muddati o'tib), tanlovdan chiqariladi
        setTanlangan((eski) => {
          const mavjud = eski.filter((t2) => l.some((x) => x.id === t2.id && !x.band && !x.qulflangan))
          if (mavjud.length !== eski.length) setXabar("Tanlangan libos band bo'lib qoldi va ro'yxatdan chiqarildi.")
          return mavjud.length === eski.length ? eski : mavjud
        })
      } catch { /* tarmoq uzilsa keyingi urinishda yangilanadi */ }
    }, 4000)
    return () => clearInterval(t)
  }, [royxatOchiq, dan, gacha, bandlar, filtr.q])

  // Qidiruv matni yoki «Bandlar ham» o'zgarsa ro'yxat (300 ms kechikish bilan) qayta olinadi — tanlangan liboslar saqlanadi
  useEffect(() => {
    if (!royxatOchiq || !dan || !gacha) return undefined
    const t = setTimeout(() => boshLiboslar(dan, gacha, bandlar, filtr.q).then(setLiboslar).catch(() => {}), 300)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtr.q, bandlar])

  const noyob = (kalit) => [...new Set((liboslar || []).map((l) => l[kalit]).filter(Boolean))].sort()
  // Kategoriya tablari: libos kategoriyasi — faqat o'sha liboslar, «Aksessuarlar» — faqat aksessuarlar.
  // «Hammasi» yo'q: boshida birinchi kategoriya (Sozlamadagi tartib bo'yicha) ochiq. Qidiruv esa hamma kategoriya va
  // aksessuarlar bo'ylab (artikul terilganda u qaysi tabda ekanini bilish shart emas)
  const AKS = '__aksessuar'
  const katOrni = (k) => { const i = katTartib.indexOf(k); return i < 0 ? katTartib.length : i }
  const katlar = [...new Set((liboslar || []).map((l) => l.kategoriya).filter(Boolean))]
    .sort((a, b) => katOrni(a) - katOrni(b) || a.localeCompare(b))
  const tablar = [...katlar.map((k) => [k, k]), ...(aksessuarlar.length > 0 ? [[AKS, 'Aksessuarlar']] : [])]
  // Telefonda «Filtr» tugmasidagi son: nechta qo'shimcha filtr yoqilgan
  const filtrSoni = [filtr.olcham, filtr.rang, filtr.narx, bandlar].filter(Boolean).length
  const qidirilmoqda = filtr.q.trim() !== ''
  const kat = qidirilmoqda ? '' : tablar.some(([k]) => k === filtr.kat) ? filtr.kat : tablar[0]?.[0] ?? ''
  const libosKorinadi = kat !== AKS
  const aksKorinadi = !kat || kat === AKS
  const qAks = filtr.q.trim().toLowerCase()
  const aksKorinadigan = aksessuarlar.filter((a) => (!qAks || a.nomi.toLowerCase().includes(qAks) || a.kod.toLowerCase().includes(qAks))
    && (!filtr.narx || a.ijara_narxi <= Number(filtr.narx)))
  const korinadi = (liboslar || []).filter((l) => (!kat || l.kategoriya === kat)
    && (!filtr.olcham || l.olcham === filtr.olcham) && (!filtr.rang || l.rang === filtr.rang)
    && (!filtr.narx || l.ijara_narxi <= Number(filtr.narx))
    && (!filtr.filial || l.filial == null || l.filial === Number(filtr.filial)))

  const korsatiladigan = tanlangan.length > 0 ? tanlangan : (liboslar || []).filter((l) => !l.band && !l.qulflangan)
  if (vitrina && korsatiladigan.length > 0) {
    return <Vitrina liboslar={korsatiladigan} onChiqish={() => setVitrina(false)} />
  }

  const mijozNomi = (joriyMijoz?.yangi ? fio : joriyMijoz?.fio || '').trim()
  const royxat = <VaraqRoyxat liboslar={tanlangan} aksessuarlar={aksessuarlar} aksSoni={aksSoni} ustama={ustama} ustamaSumma={ustamaSumma} />

  if (zakaz) {
    return (
      <section className="muhr-sahna" aria-labelledby="muhr-sarlavha">
        <div className="varaq varaq-yakun">
          <Muhr raqam={zakaz.raqam} />
          <h2 id="muhr-sarlavha" ref={sarlavha} tabIndex={-1}>Zakaz #{zakaz.raqam} saqlandi</h2>
          {mijozNomi && <p className="varaq-kimga">{mijozNomi}</p>}
          <Bezak />
          <VaraqSana dan={dan} gacha={gacha} />
          {royxat}
          <div className="varaq-jami"><span>Jami</span><b>{som(zakaz.jami)}</b></div>
          <p className="varaq-izoh">
            {zakaz.bron_muddati ? `Bron ${muddatMatni(zakaz.bron_muddati)} gacha turadi.` : 'Bron vaqtinchalik.'} Avans olinmasa, bron o'zi bekor bo'ladi.
          </p>
        </div>
        <div className="muhr-tugmalar">
          {onTolov && zakaz.jami > 0 && <button onClick={() => onTolov(zakaz.id)}>Avans qabul qilish</button>}
          <button className={onTolov ? 'ikkinchi' : ''} onClick={() => onTayyor(zakaz.id)}>Zakaz kartasini ochish</button>
          <button className="ikkinchi" onClick={yangi}>Yangi zakaz</button>
        </div>
      </section>
    )
  }

  const sanaTayyor = dan && gacha && gacha >= dan
  const davom = qadam === 2 ? () => { setXabar(''); setQadam(3) } : saqlash
  return (
    <div className="stack">
      {xabar && <p className="xato">{xabar}</p>}

      <div className="zakaz-joy">
        <div className="stack">
          {qadam === 1 && (
            <section className="blok">
              <CalendarPage dan={dan} gacha={gacha} onTanla={(d, g) => { setDan(d); setGacha(g) }} />
              {sanaTayyor && kunlar(dan, gacha) > UZOQ_IJARA_KUN && (
                <p className="ogohlantirish">Ijara {kunlar(dan, gacha)} kun — odatdagidan uzoq. Qaytarish kuni to'g'ri tanlanganini tekshiring.</p>
              )}
            </section>
          )}

          {qadam === 2 && liboslar && (<>
            {/* Filtrlar — Katalogdagi asboblar qatori bilan bir xil: kategoriya tablari, ixcham tanlovlar, ikonali qidiruv */}
            <section className="blok jadval-panel libos-filtr" aria-label="Libos filtrlari">
              <div className="jadval-asboblar">
                <div className="tezkor-tablar" role="tablist" aria-label="Kategoriya">
                  {tablar.map(([k, nom]) => (
                    <button key={k} type="button" role="tab" aria-selected={kat === k}
                      className={kat === k ? 'faol' : ''} onClick={() => setFiltr({ ...filtr, kat: k, q: '' })}>
                      {nom}{k === AKS && <span className="tab-son">{aksessuarlar.length}</span>}
                    </button>
                  ))}
                </div>
                {korsatiladigan.length > 0 && (
                  <span className="filtr-amal">
                    <button type="button" className="ikkinchi kichik" onClick={() => setVitrina(true)}
                      title={tanlangan.length > 0 ? 'Tanlangan liboslar' : "Shu sanalardagi bo'sh liboslar"}>
                      Mijozga ko'rsatish
                    </button>
                  </span>
                )}
              </div>
              <div className="jadval-asboblar">
                <label className="qidiruv-maydon" title="Qidiruvda band libos ham chiqadi">
                  <NavIkona nom="qidiruv" className="tugma-ikon" />
                  <input type="search" className="jadval-qidiruv" aria-label="Libos qidirish" placeholder="Artikul yoki nom" value={filtr.q}
                    onChange={(e) => setFiltr({ ...filtr, q: e.target.value })} />
                </label>
                {/* faqat telefonda ko'rinadi; keng ekranda filtrlar doim ochiq */}
                <button type="button" className="ikkinchi kichik filtr-tugma" aria-expanded={filtrOchiq} aria-controls="libos-filtrlari"
                  onClick={() => setFiltrOchiq(!filtrOchiq)}>
                  Filtr{filtrSoni > 0 && <span className="tab-son">{filtrSoni}</span>}
                </button>
                <div id="libos-filtrlari" className={`filtr-qoshimcha${filtrOchiq ? ' ochiq' : ''}`}>
                  {fil.length > 0 && (
                    <select className="kichik-tanlov" value={filtr.filial} aria-label="Filial" onChange={(e) => setFiltr({ ...filtr, filial: e.target.value })}>
                      <option value="">Barcha filiallar</option>
                      {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
                    </select>
                  )}
                  {libosKorinadi && (<>
                    <select className="kichik-tanlov" value={filtr.olcham} aria-label="O'lcham" onChange={(e) => setFiltr({ ...filtr, olcham: e.target.value })}>
                      <option value="">O'lcham</option>
                      {noyob('olcham').map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                    <select className="kichik-tanlov" value={filtr.rang} aria-label="Rang" onChange={(e) => setFiltr({ ...filtr, rang: e.target.value })}>
                      <option value="">Rang</option>
                      {noyob('rang').map((o) => <option key={o} value={o}>{o}</option>)}
                    </select>
                  </>)}
                  <SummaInput className="narx-filtr" aria-label="Narx gacha" placeholder="Narx gacha" value={filtr.narx}
                    onChange={(e) => setFiltr({ ...filtr, narx: e.target.value })} />
                  {libosKorinadi && (
                    <button type="button" className="bugun-chip" aria-pressed={bandlar} onClick={() => setBandlar(!bandlar)}
                      title="Band liboslar ham ro'yxatda — eng yaqin bo'sh sanasi va o'xshash bo'sh liboslar bilan">Bandlar ham</button>
                  )}
                </div>
              </div>
            </section>
            {libosKorinadi && <ul className="liboslar libos-grid">
              {korinadi.length === 0 && (
                <li className="libos-bosh">
                  {liboslar.length === 0 ? (<>
                    Bu sanalarga bo'sh libos yo'q. Boshqa sanani tanlang yoki band liboslarni ham ko'ring.{' '}
                    {!bandlar && <button type="button" className="ikkinchi kichik" onClick={() => setBandlar(true)}>Bandlarni ko'rsatish</button>}
                  </>) : 'Filtrga mos libos topilmadi.'}
                </li>
              )}
              {korinadi.map((l) => {
                const tanlandi = tanlangan.some((t) => t.id === l.id)
                const yopiq = l.band || l.qulflangan
                return (
                  <li key={l.id} className={`${yopiq ? 'band' : ''} ${tanlandi ? 'tanlandi' : ''}`}>
                    <span className="libos-rasm">
                      {l.rasm ? <img className="eskiz" src={l.rasm} alt="" /> : <span className="eskiz bosh-eskiz"><LibosSiluet /></span>}
                      {tanlandi && <span className="tanlov-belgi" aria-hidden="true">✓</span>}
                    </span>
                    <span className="matn-ustun">
                      <span className="libos-nom"><b>{l.artikul}</b> {l.nomi}</span>
                      <span className="libos-narx">{som(l.ijara_narxi)}</span>
                      <span className="malumot">{[l.kategoriya, l.olcham, l.rang].filter(Boolean).join(', ')}</span>
                    </span>
                    {l.qulflangan && <em>Hozir boshqa sotuvchi rasmiylashtiryapti</em>}
                    {l.band && (
                      <em>
                        Band{l.eng_yaqin_bosh ? `, eng yaqin bo'sh sana: ${l.eng_yaqin_bosh}` : ''}
                        {l.oxshashlar?.length > 0 && `. O'xshash bo'sh: ${l.oxshashlar.map((o) => `${o.artikul} ${o.nomi}`).join(', ')}`}
                      </em>
                    )}
                    {l.manekin && (
                      <button type="button" className="ikkinchi kichik" onClick={() => setManekin(l)}>Manekinda</button>
                    )}
                    {!yopiq && (
                      <button className={`kichik ${tanlandi ? '' : 'ikkinchi'}`} onClick={() => tanlash(l)}>
                        {tanlandi ? 'Olib tashlash' : "Qo'shish"}
                      </button>
                    )}
                  </li>
                )
              })}
            </ul>}
            {aksKorinadi && aksessuarlar.length > 0 && (
              <section className="stack aks-bolim">
                {libosKorinadi && <h3>Aksessuarlar</h3>}
                {aksKorinadigan.length === 0 && <p className="malumot">Qidiruvga mos aksessuar topilmadi.</p>}
                {/* Ko'ylaklar bilan bir xil kartochka: rasm (Katalog → Aksessuarlar → Rasm), nomi, narxi, shu sanalarga
                    nechta bor. Tanlanmagan — «Qo'shish», tanlangan — soni va hisob (2 × 300 000 = 600 000) */}
                <ul className="liboslar libos-grid aks-kartalar">
                  {aksKorinadigan.map((a) => {
                    const n = aksSoni[a.id] || 0
                    const o = (d) => setAksSoni({ ...aksSoni, [a.id]: Math.max(0, Math.min(a.bosh_soni, n + d)) })
                    return (
                      <li key={a.id} className={n > 0 ? 'tanlandi' : ''}>
                        <span className="libos-rasm">
                          {a.rasm ? <img className="eskiz" src={a.rasm} alt="" /> : <span className="eskiz bosh-eskiz" aria-hidden="true">{a.kod}</span>}
                          {n > 0 && <span className="tanlov-belgi" aria-hidden="true">{n}</span>}
                        </span>
                        <span className="matn-ustun">
                          <span className="libos-nom"><b>{a.kod}</b> {a.nomi}</span>
                          <span className="libos-narx">{som(a.ijara_narxi)} <small>/ dona</small></span>
                          <span className="malumot">Shu sanalarga {a.bosh_soni} dona bor</span>
                        </span>
                        {n === 0 ? (
                          <button type="button" className="ikkinchi kichik" onClick={() => o(1)}>Qo'shish</button>
                        ) : (<>
                          <div className="aks-son" role="group" aria-label={`${a.nomi} soni`}>
                            <button type="button" className="ikkinchi kichik" aria-label={`${a.nomi}: bittaga kamaytirish`} onClick={() => o(-1)}>−</button>
                            <output aria-live="polite">{n} dona</output>
                            <button type="button" className="ikkinchi kichik" aria-label={`${a.nomi}: bittaga ko'paytirish`} onClick={() => o(1)} disabled={n >= a.bosh_soni}>+</button>
                          </div>
                          <span className="aks-jami">{n} × {som(a.ijara_narxi)} = <b>{som(n * a.ijara_narxi)}</b></span>
                        </>)}
                      </li>
                    )
                  })}
                </ul>
              </section>
            )}
          </>)}

          {qadam === 3 && (
            <section className="blok">
              <h3>Mijoz</h3>
              <label>Mijoz telefoni
                <input value={telefon} inputMode="tel" placeholder="+998 90 123 45 67"
                  onChange={(e) => telefonOzgar(e.target.value)} onBlur={mijozniTekshir} />
              </label>
              {telefon && telefonRaqamlari(telefon) < 9 && <p className="malumot">Raqam to'liq emas: masalan, +998 90 123 45 67.</p>}
              {joriyMijoz?.yangi && (
                <label><span>Yangi mijoz — F.I.O. <span className="majburiy" aria-hidden="true">*</span></span>
                  <input value={fio} required aria-invalid={ismKerak || undefined} autoComplete="off" onChange={(e) => setFio(e.target.value)} />
                </label>
              )}
              {joriyMijoz && !joriyMijoz.yangi && (
                <div className={joriyMijoz.qora_royxat ? 'ogohlantirish' : 'malumot'}>
                  {joriyMijoz.qora_royxat && <b>Qora ro'yxat: {joriyMijoz.qora_royxat_sabab}. </b>}
                  {joriyMijoz.fio}, oldingi zakazlar: {joriyMijoz.tarix.length}
                  {joriyMijoz.olchamlar && Object.values(joriyMijoz.olchamlar).some((v) => v != null) && (
                    <>. O'lchamlar: {[joriyMijoz.olchamlar.kokrak, joriyMijoz.olchamlar.bel, joriyMijoz.olchamlar.son].map((v) => v ?? '—').join('/')}{joriyMijoz.olchamlar.boy ? `, bo'y ${joriyMijoz.olchamlar.boy}` : ''}</>
                  )}
                </div>
              )}
              {joriyMijoz?.yangi && !salonchi && (
                <label>Mijoz qayerdan keldi
                  <select value={manba} onChange={(e) => setManba(e.target.value)}>
                    <option value="instagram">Instagram</option><option value="tavsiya">Tavsiya</option><option value="boshqa">Boshqa</option>
                  </select>
                </label>
              )}
              <label>Salonchi (makiyaj ustasi)
                <select value={salonchi} onChange={(e) => setSalonchi(e.target.value)}>
                  <option value="">— yo'q —</option>
                  {salonchiRoyxat.map((s) => <option key={s.id} value={s.id}>{s.ism}{s.salon_nomi ? `, ${s.salon_nomi}` : ''}</option>)}
                </select>
                <Info nom="Salonchi">Mijozni olib kelgan yoki tavsiya qilgan makiyaj ustasi. Unga komissiya hisoblanmaydi — faqat «Salonchilar» hisobotida kim qancha mijoz olib kelgani ko'rinadi.</Info>
              </label>
              {tanlanganSalonchi?.instagram && (
                <a className="tugma-havola" href={tanlanganSalonchi.instagram} target="_blank" rel="noreferrer">
                  {tanlanganSalonchi.ism} ishlarini Instagramda ko'rish
                </a>
              )}
              <SalonchiForma onYuborish={async (b) => {
                const yangiS = await salonchiQosh(b)  // xato bo'lsa forma o'zi ko'rsatadi
                setSalonchiRoyxat(await salonchilar()); setSalonchi(String(yangiS.id)); setXabar('')
                return true
              }} />
            </section>
          )}
          {manekin && (
            <Manekin sarlavha={manekin.nomi} faylNomi={manekin.artikul} onYopish={() => setManekin(null)}
              qatlamlar={[
                { kalit: 'libos', nomi: 'Libos', standart: { x: 0, y: 0.08, k: 0.8 }, ...manekin.manekin, saqla: (b) => manekinSaqla(manekin.id, b) },
                // FT-5.2: zakazga tanlangan (soni > 0) va manekin rasmi bor aksessuarlar libos ustidan qo'yiladi
                ...aksessuarlar.filter((a) => a.manekin && aksSoni[a.id] > 0)
                  .map((a) => ({ kalit: `a${a.id}`, nomi: a.nomi, ...a.manekin, saqla: (b) => aksessuarManekinSaqla(a.id, b) })),
              ]}
              onSaqlandi={(q) => {
                const yangi = (eski, kalit) => { const v = q.find((x) => x.kalit === kalit); return v ? { ...eski, x: v.x, y: v.y, kattalik: v.kattalik } : eski }
                setLiboslar(liboslar.map((x) => (x.id === manekin.id ? { ...x, manekin: yangi(x.manekin, 'libos') } : x)))
                setAksessuarlar(aksessuarlar.map((a) => (a.manekin ? { ...a, manekin: yangi(a.manekin, `a${a.id}`) } : a)))
                setManekin({ ...manekin, manekin: yangi(manekin.manekin, 'libos') })
              }} />
          )}
        </div>
        <aside className="zakaz-jami varaq" aria-label="Zakaz varaqasi">
          {/* Qadamlar — varaq tepasida, tilla ip ustidagi tugunlar; o'tilgan qadamga bosib qaytiladi */}
          <ol className="zakaz-ip" aria-label="Qadamlar">
            {QADAMLAR.map((n, i) => {
              const q = i + 1
              const ichi = <><span className="ip-tugun" aria-hidden="true">{q < qadam ? '✓' : q}</span>{n}</>
              return (
                <li key={n} className={q === qadam ? 'joriy' : q < qadam ? 'otdi' : ''} aria-current={q === qadam ? 'step' : undefined}>
                  {q < qadam ? <button type="button" onClick={() => { setXabar(''); setQadam(q) }}>{ichi}</button> : <span>{ichi}</span>}
                </li>
              )
            })}
          </ol>
          {mijozNomi && qadam === 3 && <p className="varaq-kimga">{mijozNomi}</p>}
          <VaraqSana dan={dan} gacha={gacha} />
          {qadam >= 2 && (<>
            <Bezak />
            {royxat || <p className="varaq-izoh">Libos hali tanlanmagan.</p>}
            <div className="varaq-jami"><span>Jami{tanlangan.length > 0 ? `, ${tanlangan.length} ta libos` : ''}</span><b>{som(jami)}</b></div>
          </>)}
          <div className="zakaz-tugmalar">
            {qadam === 1 ? (
              <button disabled={!sanaTayyor} onClick={() => { setXabar(''); setQadam(2) }}>Davom etish — liboslarni tanlash</button>
            ) : (<>
              <button className="ikkinchi" onClick={() => setQadam(qadam - 1)}>Orqaga</button>
              <button onClick={davom} disabled={saqlanmoqda || tanlangan.length === 0
                || (qadam === 3 && (!telefon || !joriyMijoz || joriyMijoz.qora_royxat || ismKerak))}>
                {qadam === 2 ? 'Davom etish' : saqlanmoqda ? 'Saqlanmoqda…' : 'Zakazni saqlash'}
              </button>
            </>)}
          </div>
          {/* o'chiq «Zakazni saqlash» sababi — tugma ostida */}
          {qadam === 3 && ismKerak && <p className="zakaz-sabab" role="status">Yangi mijozning ismini yozing</p>}
          {qadam === 3 && telefon && !joriyMijoz && telefonRaqamlari(telefon) >= 9 && (
            <p className="zakaz-sabab" role="status">{toliqRaqam(telefon) || faqatRaqam(telefon) === qidirilgan ? 'Mijoz tekshirilmoqda…' : 'Mijozni tekshirish uchun telefon maydonidan chiqing'}</p>
          )}
        </aside>
      </div>
    </div>
  )
}

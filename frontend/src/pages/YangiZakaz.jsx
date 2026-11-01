import { useEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import Vitrina from '../components/Vitrina'
import LibosSiluet from '../components/LibosSiluet'
import { SalonchiForma } from './Salonchilar'
import Manekin from '../components/Manekin'
import CalendarPage from '../components/kalendar/CalendarPage'
import { Bezak, Muhr, VaraqSana } from '../components/Varaq'
import { aksessuarManekinSaqla, boshAksessuarlar, filiallar, boshLiboslar, mijozQidir, qulf, qulfOchir, manekinSaqla, salonchiQosh, salonchilar, som, ustamaFoiz, zakazYarat } from '../api'
import SummaInput from '../components/SummaInput'

// Yangi zakaz: 1) sana, 2) libos tanlash, 3) mijoz va saqlash (4-bo'lim). O'ngda (telefonda pastda) zakaz
// varaqasi tanlangan sari to'ladi; saqlangach unga muhr bosiladi.
const QORALAMA = 'libosa.yangi_zakaz'
const bugunIso = () => { const t = new Date(); return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}` }
const qoralamaOl = () => {
  let q
  try { q = JSON.parse(sessionStorage.getItem(QORALAMA)) || {} } catch { return {} }
  // Kecha qoldirilgan qoralama: o'tgan sana bilan davom etib bo'lmaydi (server rad etadi) — sana qaytadan tanlanadi
  if (q.dan && q.dan < bugunIso()) q = { ...q, dan: '', gacha: '', qadam: 1 }
  // Tanlangan liboslar qoralamada saqlanmaydi — 3-qadamga libossiz qaytib qolmaslik uchun libos tanloviga
  return { ...q, qadam: Math.min(q.qadam || 1, 2) }
}
// Telefondagi raqamlar soni: 9 (90 123 45 67) yoki 12 (998 90 123 45 67) — to'liq raqam
const telefonRaqamlari = (t) => t.replace(/\D/g, '').length
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

export default function YangiZakaz({ onTayyor, onTolov }) {
  const q0 = useState(qoralamaOl)[0]
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
    try { sessionStorage.setItem(QORALAMA, JSON.stringify({ qadam, dan, gacha, telefon, fio, salonchi })) } catch { /* xotira yopiq */ }
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

  const mijozniTekshir = async () => {
    setMijoz(null)
    if (!telefon) return
    try {
      setMijoz(await mijozQidir(telefon))
    } catch {
      setMijoz({ yangi: true })
    }
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
    if (saqlanmoqda) return undefined // ikki marta bosilsa ikkinchi so'rov yuborilmaydi
    setSaqlanmoqda(true)
    try {
      const yaratildi = await zakazYarat({ telefon, fio: mijoz?.yangi ? fio : '', manba: mijoz?.yangi && !salonchi ? manba : undefined,
        salonchi: salonchi ? Number(salonchi) : undefined, dan, gacha, liboslar: tanlangan.map((l) => l.id),
        aksessuarlar: Object.entries(aksSoni).flatMap(([id, n]) => Array(n).fill(Number(id))) })
      try { sessionStorage.removeItem(QORALAMA) } catch { /* xotira yopiq */ }
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
    setZakaz(null); setLiboslar(null); setTanlangan([]); setMijoz(null); setAksessuarlar([]); setAksSoni({})
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
    }).catch(() => {})
    return () => { bekor = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dan, gacha, bandlar])

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

  // Qidiruv matni o'zgarsa ro'yxat darhol (300 ms kechikish bilan) qayta olinadi.
  useEffect(() => {
    if (!royxatOchiq || !dan || !gacha) return undefined
    const t = setTimeout(() => boshLiboslar(dan, gacha, bandlar, filtr.q).then(setLiboslar).catch(() => {}), 300)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtr.q])

  const noyob = (kalit) => [...new Set((liboslar || []).map((l) => l[kalit]).filter(Boolean))].sort()
  const korinadi = (liboslar || []).filter((l) => (!filtr.kat || l.kategoriya === filtr.kat)
    && (!filtr.olcham || l.olcham === filtr.olcham) && (!filtr.rang || l.rang === filtr.rang)
    && (!filtr.narx || l.ijara_narxi <= Number(filtr.narx))
    && (!filtr.filial || l.filial == null || l.filial === Number(filtr.filial)))

  const korsatiladigan = tanlangan.length > 0 ? tanlangan : (liboslar || []).filter((l) => !l.band && !l.qulflangan)
  if (vitrina && korsatiladigan.length > 0) {
    return <Vitrina liboslar={korsatiladigan} onChiqish={() => setVitrina(false)} />
  }

  const mijozNomi = (mijoz?.yangi ? fio : mijoz?.fio || '').trim()
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
      {/* Qadamlar — tilla ip ustidagi tugunlar; o'tilgan qadamga bosib qaytiladi */}
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
      {xabar && <p className="xato">{xabar}</p>}

      <div className="zakaz-joy">
        <div className="stack">
          {qadam === 1 && (
            <section className="blok">
              <CalendarPage dan={dan} gacha={gacha} onTanla={(d, g) => { setDan(d); setGacha(g) }} />
              {sanaTayyor && kunlar(dan, gacha) > UZOQ_IJARA_KUN && (
                <p className="ogohlantirish">Ijara {kunlar(dan, gacha)} kun — odatdagidan uzoq. Qaytarish kuni to'g'ri tanlanganini tekshiring.</p>
              )}
              <label className="qator">
                <input type="checkbox" checked={bandlar} onChange={(e) => setBandlar(e.target.checked)} />
                Bandlarni ham ko'rsatish
              </label>
            </section>
          )}

          {qadam === 2 && liboslar && (<>
            <section className="stack filtrlar">
              <div className="filtr-bosh">
                <input type="search" aria-label="Libos qidirish" placeholder="Artikul yoki nom (band libos ham chiqadi)" value={filtr.q}
                  onChange={(e) => setFiltr({ ...filtr, q: e.target.value })} />
                {korsatiladigan.length > 0 && (
                  <button className="ikkinchi kichik" onClick={() => setVitrina(true)}>
                    Mijozga ko'rsatish ({tanlangan.length > 0 ? 'tanlanganlar' : "bo'sh liboslar"})
                  </button>
                )}
              </div>
              <div className="chiplar">
                <button className={filtr.kat ? 'ikkinchi kichik' : 'kichik'} onClick={() => setFiltr({ ...filtr, kat: '' })}>Hammasi</button>
                {noyob('kategoriya').map((k) => (
                  <button key={k} className={filtr.kat === k ? 'kichik' : 'ikkinchi kichik'} onClick={() => setFiltr({ ...filtr, kat: k })}>{k}</button>
                ))}
              </div>
              <div className="qator">
                {fil.length > 0 && (
                  <select value={filtr.filial} aria-label="Filial" onChange={(e) => setFiltr({ ...filtr, filial: e.target.value })}>
                    <option value="">Barcha filiallar</option>
                    {fil.map((f) => <option key={f.id} value={f.id}>{f.nomi}</option>)}
                  </select>
                )}
                <select value={filtr.olcham} aria-label="O'lcham" onChange={(e) => setFiltr({ ...filtr, olcham: e.target.value })}>
                  <option value="">O'lcham</option>
                  {noyob('olcham').map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
                <select value={filtr.rang} aria-label="Rang" onChange={(e) => setFiltr({ ...filtr, rang: e.target.value })}>
                  <option value="">Rang</option>
                  {noyob('rang').map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
                <SummaInput className="narx-filtr" aria-label="Narx gacha" placeholder="Narx gacha" value={filtr.narx}
                  onChange={(e) => setFiltr({ ...filtr, narx: e.target.value })} />
              </div>
            </section>
            <ul className="liboslar libos-grid">
              {korinadi.length === 0 && (
                <li className="libos-bosh">
                  {liboslar.length === 0 ? "Bu sanalarga bo'sh libos yo'q. Boshqa sanani tanlang yoki «Bandlarni ham ko'rsatish» ni yoqing." : 'Filtrga mos libos topilmadi.'}
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
            </ul>
            {aksessuarlar.length > 0 && (
              <section className="stack aks-bolim">
                <h3>Aksessuarlar</h3>
                {/* Ko'ylaklar bilan bir xil kartochka: rasm (Katalog → Aksessuarlar → Rasm), nomi, narxi, shu sanalarga
                    nechta bor. Tanlanmagan — «Qo'shish», tanlangan — soni va hisob (2 × 300 000 = 600 000) */}
                <ul className="liboslar libos-grid aks-kartalar">
                  {aksessuarlar.map((a) => {
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
                  onChange={(e) => setTelefon(e.target.value)} onBlur={mijozniTekshir} />
              </label>
              {telefon && telefonRaqamlari(telefon) < 9 && <p className="malumot">Raqam to'liq emas: masalan, +998 90 123 45 67.</p>}
              {mijoz?.yangi && (
                <label>Yangi mijoz — F.I.O.<input value={fio} onChange={(e) => setFio(e.target.value)} /></label>
              )}
              {mijoz && !mijoz.yangi && (
                <div className={mijoz.qora_royxat ? 'ogohlantirish' : 'malumot'}>
                  {mijoz.qora_royxat && <b>Qora ro'yxat: {mijoz.qora_royxat_sabab}. </b>}
                  {mijoz.fio}, oldingi zakazlar: {mijoz.tarix.length}
                  {mijoz.olchamlar && Object.values(mijoz.olchamlar).some((v) => v != null) && (
                    <>. O'lchamlar: {[mijoz.olchamlar.kokrak, mijoz.olchamlar.bel, mijoz.olchamlar.son].map((v) => v ?? '—').join('/')}{mijoz.olchamlar.boy ? `, bo'y ${mijoz.olchamlar.boy}` : ''}</>
                  )}
                </div>
              )}
              {mijoz?.yangi && !salonchi && (
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
              <button onClick={davom} disabled={saqlanmoqda || tanlangan.length === 0 || (qadam === 3 && (!telefon || mijoz?.qora_royxat))}>
                {qadam === 2 ? 'Davom etish' : saqlanmoqda ? 'Saqlanmoqda…' : 'Zakazni saqlash'}
              </button>
            </>)}
          </div>
        </aside>
      </div>
    </div>
  )
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { akademiyaDarslar, akademiyaQayta, darsBoshla, darsTekshir, darsYordam, saqlangan, xatoMatni } from '../api'
import Kino from './Kino.jsx'
import { ASOSIY_MANZIL, SAYT_MANZIL } from './host'
import { yurit } from './yoritgich'

const TANLANGAN = 'weddy.akademiya_dars'
const KINO = 'weddy.akademiya_kino'    // kirish filmi shu qurilmada ko'rilgan (yoki o'tkazib yuborilgan)
const QADAM = 'weddy.akademiya_qadam'  // «<kod>:<qadam>» — sahifa yangilansa mashq o'sha joydan davom etadi

const Belgi = ({ d }) => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
)
const HA = 'M5 12.5l4.5 4.5L19 7.5'
const YOQ = 'M6 6l12 12M18 6L6 18'
const ORQAGA = 'M15 5l-7 7 7 7'
const QULF = 'M7 11V8a5 5 0 0110 0v3M6 11h12v9H6z'

// Tasvirlar (frontend/public/akademiya/): har bobning sahna-banneri, ustoz portreti va avatari — bitta salon, ikki qahramon
const bobRasmi = (kalit) => `/akademiya/bob-${kalit}.jpg`
const avatar = (kalit) => `/akademiya/avatar-${kalit}.jpg`
// O'sadigan qahramon: har darajada ustozning boshqa sahnasi (1–3-daraja — `daraja-<ustoz>-N.jpg`, 4-daraja — `hero-<ustoz>`)
// Fayli tayyor daraja sahnalari; ro'yxatda yo'q bo'lsa — ustozning asosiy sahnasi (`hero-<ustoz>`) ko'rsatiladi
const DARAJA_BOR = new Set(['daraja-madina-1', 'daraja-madina-2', 'daraja-madina-3', 'daraja-nodira-1', 'daraja-nodira-2', 'daraja-nodira-3'])
const darajaRasmi = (ustoz, raqam) => (raqam < 4 && DARAJA_BOR.has(`daraja-${ustoz}-${raqam}`) ? `daraja-${ustoz}-${raqam}` : `hero-${ustoz}`)
const DARAJA_SOZI = {
  2: "Birinchi qadamlar ortda qoldi: asosiy ishlarni endi o'zingiz boshlay olasiz.",
  3: "Yo'lning yarmidan o'tdingiz: kundalik ishning ko'p qismini yordamsiz bajarasiz.",
  4: "Deyarli hammasini o'zlashtirdingiz — endi yangi kelganlarga o'zingiz o'rgata olasiz.",
}
// Bob voqeasining ovozi tayyor boblar (`bob-<kalit>.mp3`); qolganlarida voqea faqat matn bo'lib chiqadi
const OVOZ_BOR = new Set(['birinchi-kun', 'mijoz-keldi', 'tanlov', 'toy-kuni', 'kassa', 'salon', 'libos', 'kelishuv', 'yakun', 'nazorat'])
const OVOZ = 'weddy.akademiya_ovoz'  // '0' — o'quvchi ovozni o'chirib qo'ygan

// «Jonli» sahna: rasm ustida shu sahnaning qisqa, ovozsiz, uzluksiz aylanadigan videosi. Harakatni kamaytirish yoki
// trafikni tejash yoqilgan bo'lsa ko'rsatilmaydi; fayl bo'lmasa ham rasmning o'zi qoladi.
const JONLI = typeof window !== 'undefined' && !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches && !navigator.connection?.saveData
// `muted` ni brauzer avtomatik ijro uchun xossa sifatida ko'rishi kerak (React uni atribut qilib yozmaydi) — shuning uchun
// element paydo bo'lganda ovoz o'chiriladi va ijro qo'lda boshlanadi; brauzer rad etsa — rasm qoladi.
const jonliBoshla = (v) => { if (v) { v.muted = true; v.play?.().catch(() => {}) } }
// Videosi tayyor sahnalar (frontend/public/akademiya/<nom>.mp4). Yangi video qo'shilganda nomi shu ro'yxatga yoziladi —
// yo'q faylga so'rov ketmaydi.
const JONLI_BOR = new Set(['hero-nodira', 'hero-madina', 'bob-birinchi-kun', 'bob-mijoz-keldi', 'bob-tanlov', 'bob-toy-kuni',
  'bob-kassa', 'bob-salon', 'bob-libos', 'bob-kelishuv', 'bob-yakun', 'bob-nazorat'])
const Jonli = ({ nom }) => JONLI && JONLI_BOR.has(nom) && (
  <video ref={jonliBoshla} className="ak-jonli" src={`/akademiya/${nom}.mp4`} muted loop playsInline autoPlay preload="auto" aria-hidden="true" tabIndex={-1} />
)

const saqlanganQadam = (kod) => {
  const [k, i] = (sessionStorage.getItem(QADAM) || '').split(':')
  return k === kod ? Number(i) || 0 : 0
}

// Dars paneli: bosqichlar xaritasi va tanlangan dars. Mashq yo'naltirilgan: bir vaqtda bitta qadam ko'rsatiladi va
// ilova ekranida faqat shu qadamga kerakli joy ochiq turadi (yoritgich.js) — o'quvchi boshqa joyni bosib adashmaydi.
// Keng ekranda panel doim chapda; tor ekranda «Dars / Mashq» tugmasi bilan almashadi (`rejim`).
export default function DarsPaneli({ rejim, onRejim, onIlovaYangila, oynaOl, onMashq }) {
  const [xarita, setXarita] = useState(null)
  const [tanlangan, setTanlanganXom] = useState(() => sessionStorage.getItem(TANLANGAN) || '')
  const [natija, setNatija] = useState(null)   // { kod, bajarildi, mezonlar, keyingi, xp }
  const [javob, setJavob] = useState([])        // savollarga tanlangan javoblar (savol tartibida)
  const [band, setBand] = useState('')         // qaysi amal ketyapti: 'boshla' | 'tekshir' | 'yordam'
  const [xato, setXato] = useState('')
  const [qadam, setQadamXom] = useState(0)     // joriy darsdagi yo'naltirilgan qadam (yol.length — hammasi bajarilgan)
  const [joy, setJoy] = useState('')           // yoritgich holati: topildi | muqobil | topilmadi
  // shu sahifada boshlangan dars kodi: avval bajarilgan darsni qayta o'tishda ham u natija chiqquncha ochiq turadi
  // (qadamlari tugagan yoki umuman qadamsiz — faqat savollardan iborat dars kirish sahifasiga qaytib ketmasin)
  const [savolKutadi, setSavolKutadi] = useState('')
  // «Avval bilib oling»: savollar shu darsning qoidalari o'qilgandan keyingina ochiladi (test — o'rgatishdan keyin)
  const [oqildi, setOqildi] = useState('')
  const [darsQayta, setDarsQayta] = useState(false)  // dars ichidagi «Darsni boshidan boshlash» so'rovi ochiqmi

  const setTanlangan = useCallback((kod) => {
    sessionStorage.setItem(TANLANGAN, kod)
    setTanlanganXom(kod); setNatija(null); setJavob([]); setXato(''); setOqildi(''); setDarsQayta(false)
  }, [])
  const yukla = useCallback(() => akademiyaDarslar().then((x) => { setXarita(x); return x }).catch((e) => {
    // sessiya tugagan (token 12 soat, mehmon saloni 24 soat yashaydi): panelda qotib qolmasin — bosh sahifaga qaytadi
    if (e?.response?.status === 401) { saqlangan.chiqish(); window.location.replace('/'); return }
    setXato(xatoMatni(e))
  }), [])
  // Daraja oshgani: tekshiruvdan oldingi daraja bilan yangisi solishtiriladi — oshgan bo'lsa alohida ekran chiqadi
  const darajaRef = useRef(null)
  const [yangiDaraja, setYangiDaraja] = useState(null)
  const [ovozYoq, setOvozYoq] = useState(() => localStorage.getItem(OVOZ) !== '0')
  useEffect(() => { yukla() }, [yukla])

  const darslar = useMemo(() => xarita?.yonalishlar.flatMap((g) => g.darslar).filter((x) => x.tayyor) || [], [xarita])
  const joriy = darslar.find((d) => d.joriy)
  const dars = darslar.find((d) => d.kod === tanlangan)
  const yol = joriy?.yol || []
  const joriyKod = joriy?.kod

  const setQadam = useCallback((kod, i) => { sessionStorage.setItem(QADAM, `${kod}:${i}`); setQadamXom(i); setJoy('') }, [])
  // Joriy dars ma'lum bo'lganda (sahifa yangilangan bo'lishi mumkin) saqlangan qadamdan davom etadi
  const tiklangan = useRef('')
  useEffect(() => {
    if (!joriyKod || tiklangan.current === joriyKod) return
    tiklangan.current = joriyKod
    setQadamXom(saqlanganQadam(joriyKod))
  }, [joriyKod])

  const bajar = (nom, ish) => { setBand(nom); setXato(''); return ish().catch((e) => setXato(xatoMatni(e))).finally(() => setBand('')) }
  const tekshir = useCallback((kod, j) => bajar('tekshir', async () => {
    const n = await darsTekshir(kod, j?.length ? j.join('|') : undefined)
    setNatija({ kod, ...n })
    if (n.bajarildi) setQadam(kod, 999)  // dars tugadi: yo'naltirish to'xtaydi, ilova yopiladi (savolli darsda ham)
    const eski = darajaRef.current
    const x = await yukla()
    if (n.bajarildi && eski && x?.daraja?.raqam > eski) setYangiDaraja(x.daraja)
    onRejim('dars')  // natija panelda — tor ekranda ham ko'rinsin
  }), [yukla, onRejim, setQadam])
  const boshla = (kod) => bajar('boshla', async () => {
    await darsBoshla(kod)
    setNatija(null); setJavob([]); setSavolKutadi(kod); setOqildi('')
    tiklangan.current = kod
    setQadam(kod, 0)
    await yukla()
    // Oldingi urinishdan qolgan zakaz qoralamasi (sana, mijoz) yangi darsga o'tib ketmasin — salon boshidan tayyorlandi
    Object.keys(sessionStorage).filter((k) => k.startsWith('libosa.yangi_zakaz')).forEach((k) => sessionStorage.removeItem(k))
    onIlovaYangila()
    onRejim('mashq')
  })
  const yordam = (kod) => bajar('yordam', async () => { await darsYordam(kod); await yukla() })
  // Kursni boshidan boshlash: natijalar o'chadi (darslar yana birinchisidan ochiladi), ball rekord bo'lib qoladi
  const [qaytaSoraldi, setQaytaSoraldi] = useState(false)
  const kursQayta = () => bajar('qayta', async () => {
    const x = await akademiyaQayta()
    sessionStorage.removeItem(QADAM); setQadamXom(0); setNatija(null); setJavob([]); setSavolKutadi(''); setQaytaSoraldi(false); setXarita(x)
  })

  // Yoritgich: joriy qadamning nishonini ilova ekranida ochiq qoldiradi; qadam bajarilsa keyingisiga o'tadi.
  // Oxirgi qadamdan keyin savolsiz dars o'zi tekshiriladi.
  const qadamTarifi = joriy && qadam < yol.length ? yol[qadam] : null
  const qadamKaliti = qadamTarifi ? `${joriyKod}:${qadam}` : ''
  const tarifRef = useRef(null)
  useEffect(() => { darajaRef.current = xarita?.daraja?.raqam ?? null; tarifRef.current = { qadamTarifi, joriyKod, qadam, soni: yol.length, savol: !!joriy?.savollar?.length, oldingilar: yol.slice(0, qadam) } })
  useEffect(() => {
    if (!qadamKaliti) return undefined
    const t = tarifRef.current
    return yurit(oynaOl, t.qadamTarifi, {
      onHolat: setJoy,
      oldingilar: t.oldingilar,
      onTugadi: () => {
        const keyingi = t.qadam + 1
        setQadam(t.joriyKod, keyingi)
        if (keyingi >= t.soni) { if (t.savol) setSavolKutadi(t.joriyKod); else tekshir(t.joriyKod) }
      },
    })
  }, [qadamKaliti, oynaOl, setQadam, tekshir])

  // Ilova faqat yo'naltirilgan qadam bor paytda ochiq (Akademiya.jsx dagi parda)

  const otkaz = () => {  // nishon ekranda topilmasa — o'quvchi qotib qolmaydi
    const keyingi = qadam + 1
    setQadam(joriyKod, keyingi)
    if (keyingi >= yol.length) { if (joriy.savollar?.length) setSavolKutadi(joriyKod); else tekshir(joriyKod) }
  }

  const d = xarita?.daraja
  // Bosh sahifa: boblar yo'li. Navbatdagi dars — davom etayotgani, bo'lmasa birinchi bajarilmagani
  const boblar = xarita?.boblar || []
  const navbat = darslar.find((x) => x.joriy && qadam < yol.length) || darslar.find((x) => x.ochiq && !x.bajarilgan) || darslar.find((x) => !x.bajarilgan && !x.kirish_kerak)
  const bobi = (x) => boblar.find((b) => b.darslar.some((y) => y.kod === x?.kod))
  const navbatBob = bobi(navbat)
  // Kabinet bo'limlari (chap menyu) va bob sahifasi: bob banneri bosilsa — shu bobning o'z sahifasi ochiladi
  const [bolim, setBolim] = useState('kabinet')   // kabinet | varaqlar | reyting
  const [ochiqBob, setOchiqBob] = useState('')
  const bobSahifa = bolim === 'kabinet' ? boblar.find((b) => b.kalit === ochiqBob) : undefined
  const [salom] = useState(() => {  // sahifa ochilgan paytdagi soat bo'yicha, qayta chizishda o'zgarmaydi
    const soat = new Date().getHours()
    return soat < 5 ? 'Xayrli tun' : soat < 12 ? 'Xayrli tong' : soat < 18 ? 'Xayrli kun' : 'Xayrli kech'
  })
  // rahbar yo'lini Nodira, xodim yo'lini Madina olib boradi — shaxsiy ish kartasida o'sha ustoz
  const ustoz = boblar.some((b) => b.kalit === 'salon') ? 'nodira' : 'madina'
  const ism = saqlangan.xodim()?.ism || ''
  // Kirish filmi: yangi o'quvchiga birinchi ochilishda o'zi chiqadi; keyin — bosh sahifadagi tugma orqali
  const [kinoKorilgan, setKinoKorilgan] = useState(() => !!localStorage.getItem(KINO))
  const [kinoQolda, setKino] = useState(false)   // tugma bilan ochilgan
  const yangiOquvchi = !!xarita && xarita.bajarilgan === 0 && !darslar.some((x) => x.joriy)
  const kino = kinoQolda || (!kinoKorilgan && yangiOquvchi)
  // Eslatma-varaq: tugatilgan bobning mukofoti — shu bob darslarining xulosalari bir varaqda (chop etsa bo'ladi)
  const [varaqBob, setVaraqBob] = useState('')
  // Qulflangan dars bosilganda: mehmonga yopiq dars — kirish so'rovi oynasi; navbati kelmagan dars — qaysi darsni tugatish kerakligi
  const [kirishSorov, setKirishSorov] = useState(false)
  const [qulfXabar, setQulfXabar] = useState('')
  const qatorBos = (x) => {
    if (x.kirish_kerak) setKirishSorov(true)
    else if (!x.ochiq) setQulfXabar(navbat ? `Avval «${navbat.nomi}» darsini tugating — darslar ketma-ket ochiladi.` : 'Bu dars hali yopiq.')
    else setTanlangan(x.kod)
  }
  const varaq = boblar.find((b) => b.kalit === varaqBob && b.varaq)
  const ochiqVaraqlar = boblar.filter((b) => b.varaq).length
  const kinoYop = useCallback(() => { localStorage.setItem(KINO, '1'); setKinoKorilgan(true); setKino(false) }, [])
  const darajaFoiz = d ? (d.keyingi ? Math.min(100, ((xarita.xp - d.boshi) / (d.keyingi - d.boshi)) * 100) : 100) : 0
  const mashqda = !!dars?.joriy && qadam < yol.length                 // yo'naltirilgan qadamlar ketyapti
  // yoritgich qadamning nishonini emas, unga olib boradigan joyni yoritgan bo'lsa — o'quvchiga sababi
  const joyIzoh = !mashqda ? '' : {
    muqobil: yol[qadam].muqobil_matn || "Kerakli joy hozir ekranda yo'q. Avval yoritilgan tugmani bosing.",
    ochish: "Kerakli tugma yopiq bo'lim ichida. Avval yoritilgan bo'lim nomini bosib, uni oching.",
    qaytish: "Bu qadam boshqa sahifada. Avval ekranda yoritilgan joyni bosing — kerakli sahifaga qaytamiz.",
  }[joy] || ''
  const faqatKor = mashqda && yol[qadam].amal === 'kor'              // yoritilgan joy faqat ko'rsatiladi (bosilmaydi)
  const korish = faqatKor && qadam === yol.length - 1                // oxirgi qadam: ko'rib, savolga javob berish
  const tugadi = !!natija && !!dars && natija.kod === dars.kod && natija.bajarildi
  const savolli = !!dars?.savollar?.length
  const savolVaqti = savolli && (korish || qadam >= yol.length)       // savollar ko'rinadigan payt
  const bilim = dars?.bilim || []
  const bilimKutadi = savolVaqti && bilim.length > 0 && oqildi !== dars.kod   // qoidalar hali o'qilmagan — savollar yopiq
  const savolOchiq = savolVaqti && !bilimKutadi
  const javobYetmaydi = savolli && dars.savollar.some((_, i) => !javob[i])
  // Dars «ochiq» — hozir shu dars o'tilyapti. Avval bajarilgan darsning qadamlari tugagan va natija ekrani yopilgan bo'lsa
  // (sahifa yangilangan), u yana hikoya ko'rinishida chiqadi («Qayta o'tish»), yarim holatda qolmaydi
  const ochiq = !!dars?.joriy && !(qadam >= yol.length && natija?.kod !== dars.kod && dars.bajarilgan && savolKutadi !== dars.kod)
  // Ilova qachon ko'rinadi: yo'naltirilgan qadam paytida; savolsiz darsda qadamlar tugab, natija hali to'g'ri chiqmaganda
  // (o'quvchi ilovada tuzatib, «Natijani tekshirish» ni bosadi — ilova yashirinsa tuzatib bo'lmasdi); natija («Topshiriq
  // bajarildi») chap panelda turganda esa parda ostida (ega talabi, 2026-11-15). Tor ekranda natija uchun «Dars» ochiladi.
  const tuzatish = ochiq && !savolli && yol.length > 0 && qadam >= yol.length && !tugadi
  useEffect(() => { onMashq(qadamKaliti || tuzatish ? true : tugadi ? 'yakun' : false) }, [qadamKaliti, tuzatish, tugadi, onMashq])
  useEffect(() => { if (tugadi) onRejim('dars') }, [tugadi, onRejim])

  return (
    <>
      <aside className="ak-panel" aria-label="Libosa Academy darslari">
        <header className="ak-bosh">
          <p className="ak-yorliq">Libosa Academy</p>
          {d && (
            <div className="ak-daraja" role="img" aria-label={`Daraja: ${d.nomi}, ${xarita.xp} ball`}>
              <b>{d.nomi}</b>
              <span><i style={{ width: `${darajaFoiz}%` }} /></span>
              <small>{xarita.xp} XP</small>
            </div>
          )}
        </header>
        {xato && <p className="ak-xato" role="alert">{xato}</p>}
        {!xarita && !xato && <p className="ak-xira">Yuklanmoqda…</p>}

        {xarita && !dars && (
          <div className="ak-kabinet">
            {/* Chap menyu: kabinet bo'limlari; pastida ustoz mo'ralab turadi */}
            <nav className="ak-yon" aria-label="Akademiya bo'limlari">
              <p className="ak-yon-nom">Libosa <i>/</i> Academy</p>
              {/* kirish filmi — yo'lning boshi: birinchi kirishda o'zi chiqadi, keyin shu yerdan qayta ko'riladi */}
              <button type="button" onClick={() => setKino(true)}>▶ Kirish filmi</button>
              {[['kabinet', 'Shaxsiy kabinet'], ['varaqlar', 'Varaqlarim'], ['reyting', 'Reyting']].filter(([k]) => !(xarita.mehmon && k === 'reyting')).map(([k, nom]) => (
                <button key={k} type="button" aria-current={bolim === k ? 'page' : undefined} onClick={() => { setBolim(k); setOchiqBob('') }}>{nom}</button>
              ))}
              {/* kursni boshidan boshlash — faqat kirgan o'quvchiga, menyuda (ega talabi, 2026-11-15); so'rov shaxsiy ish kartasida chiqadi */}
              {!xarita.mehmon && xarita.bajarilgan > 0 && (
                <button type="button" onClick={() => { setBolim('kabinet'); setOchiqBob(''); setQaytaSoraldi(true) }}>↻ Qayta boshlash</button>
              )}
              <img className="ak-yon-ustoz" src={avatar(ustoz)} alt="" />
            </nav>

            <div className="ak-xarita">
              <header className="ak-salom">
                <p className="ak-mono"><b>{salom}{ism ? ` // ${ism}` : ''}</b></p>
                <p className="ak-mono">Yangi dars // yangi ko'nikma</p>
              </header>

              {bolim === 'kabinet' && !bobSahifa && (
                <>
                  {/* 1. Shaxsiy ish: daraja, tajriba va bajarilgan darslar — ustoz sahnasi ustida */}
                  {d && (
                    <section className="ak-shaxsiy" style={{ '--rasm': `url(/akademiya/${darajaRasmi(ustoz, d.raqam)}.jpg)` }}>
                      <Jonli nom={darajaRasmi(ustoz, d.raqam)} />
                      <p className="ak-mono"><b>{ism || 'Xodim'}</b> // shaxsiy ish</p>
                      <div className="ak-raqamlar">
                        <div><small>Daraja {d.raqam} / 4</small><b>{d.nomi}</b></div>
                        <div className="ak-energiya">
                          <small>Tajriba (XP)</small>
                          <span><i style={{ width: `${darajaFoiz}%` }} /></span>
                          <em>{xarita.xp}{d.keyingi ? ` / ${d.keyingi}` : ''}</em>
                        </div>
                        <div><small>Darslar</small><b>{xarita.bajarilgan} / {xarita.jami}</b></div>
                        {/* mehmon: kirish va a'zo bo'lish — raqamlar yonidagi bo'sh katakda (ega talabi, 2026-11-15) */}
                        {xarita.mehmon && (
                          <div className="ak-raqam-kirish">
                            <a className="ak-tugma" href={ASOSIY_MANZIL}>Kirish</a>
                            <a className="ak-tugma ikkinchi" href={SAYT_MANZIL}>A'zo bo'lish</a>
                          </div>
                        )}
                      </div>
                      {/* Davom etish — shu kartaning chap pastida, ixcham (ega talabi, 2026-11-15: alohida tablo kerak emas) */}
                      <div className="ak-davom">
                        {navbat ? (
                          <>
                            <button type="button" className="ak-tugma" onClick={() => setTanlangan(navbat.kod)}>
                              {xarita.bajarilgan || navbat.joriy ? 'Davom etish' : 'Boshlash'} →
                            </button>
                            <p><small className="ak-mono"><b>{navbatBob?.nomi}</b> · {navbat.joriy && qadam < yol.length ? 'davom etyapti' : xarita.bajarilgan ? 'navbatdagi dars' : 'birinchi dars'}</small>{navbat.nomi}</p>
                          </>
                        ) : xarita.mehmon ? (
                          <>
                            {/* keng ekranda tugmalar shu yerda (avvalgi tartib); tor ekranda — raqamlar yonidagi katakda */}
                            <a className="ak-tugma ak-keng-faqat" href={ASOSIY_MANZIL}>Kirish</a>
                            <a className="ak-tugma ikkinchi ak-keng-faqat" href={SAYT_MANZIL}>A'zo bo'lish</a>
                            <p><small className="ak-mono"><b>Bepul darslar bajarildi</b></small>Qolgan darslar uchun kirishni amalga oshiring</p>
                          </>
                        ) : (
                          <p><small className="ak-mono"><b>Yo'l tugadi</b> · {xarita.jami} dars</small>Barcha darslar bajarildi — istalganini qayta o'tishingiz mumkin</p>
                        )}
                      </div>
                      {/* kursni boshidan: ball yo'qolmaydi — rekord bo'lib qoladi, reytingda kattasi turadi */}
                      {!xarita.mehmon && (xarita.bajarilgan > 0 || xarita.rekord > 0) && (
                        <p className="ak-qayta">
                          {xarita.rekord > 0 && <span className="ak-mono">Rekord: <b>{xarita.rekord} XP</b></span>}
                          {qaytaSoraldi && (
                            <span className="ak-qayta-sorov">
                              Darslar yana birinchisidan ochiladi. {xarita.xp} XP rekord bo'lib qoladi — reytingda kattasi turadi.
                              <button type="button" className="ak-tugma" disabled={!!band} onClick={kursQayta}>{band === 'qayta' ? 'Tozalanmoqda…' : 'Ha, boshidan'}</button>
                              <button type="button" className="ak-tugma ikkinchi" disabled={!!band} onClick={() => setQaytaSoraldi(false)}>Yo'q</button>
                            </span>
                          )}
                        </p>
                      )}
                    </section>
                  )}


                  {/* 3. Yo'l: raqamlangan boblar; bob bosilsa o'z sahifasi ochiladi */}
                  <header className="ak-yol-bosh">
                    <p className="ak-mono"><b>Yo'lingiz</b></p>
                    <p className="ak-mono">Birinchi kundan {ustoz === 'nodira' ? 'salonni boshqarishgacha' : 'mustaqil ishlashgacha'} // {boblar.length} bob</p>
                  </header>
                  <ol className="ak-yol">
                    {boblar.map((b, bi) => {
                      const bajarilgan = b.darslar.filter((x) => x.bajarilgan).length
                      const tugagan = bajarilgan === b.darslar.length
                      const shu = b === navbatBob
                      return (
                        <li key={b.kalit} className={`ak-bob${shu ? ' shu' : ''}${tugagan ? ' tugagan' : ''}`}>
                          <span className="ak-bob-raqam" aria-hidden="true">{tugagan ? <Belgi d={HA} /> : bi + 1}</span>
                          <button type="button" className="ak-bob-banner" style={{ backgroundImage: `url(${bobRasmi(b.kalit)})` }} onClick={() => setOchiqBob(b.kalit)}>
                            {/* faqat joriy bob «jonlanadi» — o'nta video birdan yuklanmaydi */}
                            {shu && <Jonli nom={`bob-${b.kalit}`} />}
                            <span className="ak-bob-ust">
                              <span className="ak-mono">{bi + 1}-qism{shu && <em>Siz shu yerdasiz</em>}</span>
                              <span className="ak-mono">{tugagan ? 'Bajarildi' : `${bajarilgan} / ${b.darslar.length} dars`}</span>
                            </span>
                            <span className="ak-bob-nom"><b>{b.nomi}</b><i>// {b.shior}</i></span>
                            <span className="ak-bob-izoh">{b.izoh}</span>
                          </button>
                        </li>
                      )
                    })}
                  </ol>
                </>
              )}

              {/* Bob sahifasi: sahna, voqea va darslar ro'yxati */}
              {bobSahifa && (
                <section className="ak-bob-sahifa">
                  <button type="button" className="ak-orqaga" onClick={() => setOchiqBob('')}><Belgi d={ORQAGA} />Yo'lga qaytish</button>
                  <div className="ak-bob-banner katta" style={{ backgroundImage: `url(${bobRasmi(bobSahifa.kalit)})` }}>
                    <Jonli nom={`bob-${bobSahifa.kalit}`} />
                    <span className="ak-mono">{boblar.indexOf(bobSahifa) + 1}-qism · {bobSahifa.shior}</span>
                    <span className="ak-bob-nom"><b>{bobSahifa.nomi}</b></span>
                  </div>
                  {/* bob voqeasi: hikoya bobdan bobga davom etadi — shu bobni olib boradigan ustoz nomidan */}
                  <p className="ak-bob-voqea"><img className="ak-avatar" src={avatar(bobSahifa.darslar[0].personaj.kalit)} alt="" /><span>{bobSahifa.voqea}</span></p>
                  {/* voqea ovozi: bob ochilganda o'zi boshlanadi (bob banneri bosilgani — ruxsat); o'chirib qo'ysa — eslab qoladi */}
                  {OVOZ_BOR.has(bobSahifa.kalit) && (
                    <p className="ak-bob-ovoz">
                      {ovozYoq && <audio key={bobSahifa.kalit} src={`/akademiya/bob-${bobSahifa.kalit}.mp3`} autoPlay />}
                      <button type="button" className="ak-kino-ochish" aria-pressed={ovozYoq}
                        onClick={() => { localStorage.setItem(OVOZ, ovozYoq ? '0' : '1'); setOvozYoq(!ovozYoq) }}>
                        {ovozYoq ? "Ovozni o'chirish" : '▶ Voqeani tinglash'}
                      </button>
                    </p>
                  )}
                  <header className="ak-yol-bosh">
                    <p className="ak-mono"><b>Bob darslari</b></p>
                    <p className="ak-mono">{bobSahifa.darslar.filter((x) => x.bajarilgan).length} / {bobSahifa.darslar.length}</p>
                  </header>
                  {qulfXabar && <p className="ak-qulf-xabar" role="status">{qulfXabar}</p>}
                  <ol className="ak-bob-darslar">
                    {bobSahifa.darslar.map((x, n) => {
                      const ketyapti = x.joriy && qadam < yol.length
                      return (
                        <li key={x.kod}>
                          <button type="button" className={`ak-qator${ketyapti ? ' joriy' : ''}${x.bajarilgan ? ' bajarilgan' : ''}${x.ochiq ? '' : ' yopiq'}`} aria-disabled={!x.ochiq} onClick={() => qatorBos(x)}>
                            <span className="ak-doira" aria-hidden="true">{x.bajarilgan ? <Belgi d={HA} /> : x.ochiq ? n + 1 : <Belgi d={QULF} />}</span>
                            <span className="ak-qator-matn"><b>{x.nomi}</b><small>{x.natija}</small></span>
                            <span className="ak-qator-holat">{ketyapti ? 'Davom etish →' : x.bajarilgan ? (x.yordam_bilan ? 'Bajarildi · yordam bilan' : 'Bajarildi') : x.ochiq ? `Ochish → +${x.xp} XP` : x.kirish_kerak ? 'Kirishni amalga oshiring' : 'Oldingi darsdan keyin'}</span>
                          </button>
                        </li>
                      )
                    })}
                  </ol>
                </section>
              )}

              {/* Varaqlarim: har bob tugagach bittasi ochiladi */}
              {bolim === 'varaqlar' && (
                <>
                  <header className="ak-sahifa-bosh">
                    <h1>Varaqlarim</h1>
                    <p>Har bobni tugatsangiz, uning eslatma-varag'i ochiladi: shu bob darslarining asosiy qoidalari bir joyda. Ochildi: {ochiqVaraqlar} / {boblar.length}.</p>
                  </header>
                  <ul className="ak-varaqlar">
                    {boblar.map((b, bi) => (
                      <li key={b.kalit}>
                        <button type="button" className={`ak-varaq${b.varaq ? ' ochiq' : ''}`} disabled={!b.varaq} onClick={() => setVaraqBob(b.kalit)}>
                          <span className="ak-mono">{bi + 1}-qism</span>
                          <b>{b.nomi}</b>
                          <small>{b.varaq ? `${b.varaq.length} ta qoida · ochish →` : <><Belgi d={QULF} />{b.darslar.filter((x) => !x.bajarilgan).length} ta dars qoldi</>}</small>
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {/* Reyting: shu salondagi hamkasblar, oxirgi 7 kundagi ball bo'yicha */}
              {bolim === 'reyting' && (
                <>
                  <header className="ak-sahifa-bosh">
                    <h1>Reyting</h1>
                    <p>Saloningiz xodimlari oxirgi 7 kunda to'plagan ball bo'yicha. Kurs qayta boshlansa, eng yaxshi natija (rekord) qoladi: yangi ball faqat rekorddan oshganda qo'shiladi.</p>
                  </header>
                  <ol className="ak-reyting">
                    {xarita.reyting.map((q, n) => (
                      <li key={`${q.ism}-${n}`} className={q.men ? 'men' : undefined}>
                        <span className="ak-reyting-orin">{n + 1}</span>
                        <span className="ak-qator-matn"><b>{q.ism}{q.men ? ' (siz)' : ''}</b><small>{q.lavozim} · {q.darslar} dars</small></span>
                        <span className="ak-reyting-ball"><b>+{q.hafta}</b><small>jami {q.xp} XP</small></span>
                      </li>
                    ))}
                  </ol>
                  {xarita.reyting.length < 2 && <p className="ak-xira ak-reyting-izoh">Hamkasblaringiz akademiyani boshlaganda shu yerda ko'rinadi.</p>}
                </>
              )}
            </div>
          </div>
        )}

        {dars && (
          <article className={`ak-dars${!ochiq ? ' tanishuv' : tugadi ? ' yakun-holat' : savolVaqti && yol.length === 0 ? ' savol-holat' : ''}`}>
            <button type="button" className="ak-orqaga" onClick={() => setTanlangan('')}><Belgi d={ORQAGA} />Darslar</button>
            <h2>{dars.nomi}</h2>

            {/* 1. Hikoya: dars boshlanmagan — personaj vaziyatni aytadi */}
            {!ochiq && (
              <>
                <div className="ak-muqova" style={{ backgroundImage: `url(${bobRasmi(bobi(dars)?.kalit)})` }} aria-hidden="true">
                  <Jonli nom={`bob-${bobi(dars)?.kalit}`} />
                </div>
                <div className="ak-personaj katta">
                  <img className="ak-avatar" src={avatar(dars.personaj.kalit)} alt="" />
                  <div>
                    <p className="ak-kim"><b>{dars.personaj.ism}</b> · {dars.personaj.lavozim}</p>
                    <p className="ak-vaziyat">{dars.vaziyat}</p>
                  </div>
                </div>
                <dl className="ak-malumot">
                  <div><dt>Dars oxirida</dt><dd>{dars.natija}</dd></div>
                  <div><dt>Mukofot</dt><dd>+{dars.xp} XP{dars.bajarilgan ? ' (olingan)' : ''}</dd></div>
                </dl>
                {joriy && joriy.kod !== dars.kod && qadam < yol.length && <p className="ak-xira">Hozir «{joriy.nomi}» darsi ochiq. Bu darsni boshlasangiz, o'quv saloni shu dars uchun qayta tayyorlanadi.</p>}
                {!dars.ochiq && <p className="ak-xira">Bu dars hali yopiq: darslar ketma-ket ochiladi.{navbat ? ` Avval «${navbat.nomi}» darsini tugating.` : ''}</p>}
                <button type="button" className="ak-tugma keng" disabled={!!band || !dars.ochiq} onClick={() => boshla(dars.kod)}>
                  {band === 'boshla' ? 'Tayyorlanmoqda…' : dars.bajarilgan ? "Qayta o'tish" : 'Boshlash'}
                </button>
              </>
            )}

            {/* 2. Mashq: bir vaqtda bitta qadam; ekranda faqat kerakli joy yoritilgan */}
            {ochiq && !tugadi && (
              <>
                {mashqda && (
                  <section className="ak-qadam" aria-live="polite">
                    <h3>{qadam + 1}-qadam / {yol.length}</h3>
                    <p>{yol[qadam].matn}</p>
                    {joyIzoh && <p className="ak-izoh">{joyIzoh}</p>}
                    {/* tor ekranda savollar va ilova bir vaqtda ko'rinmaydi: javobni ekrandan qayta ko'rish uchun yo'l */}
                    {korish && joy !== 'topilmadi' && (
                      <p className="ak-izoh ak-tor">
                        Javoblar ilovadagi yoritilgan joyda.
                        <button type="button" className="ak-matn-tugma ichki" onClick={() => onRejim('mashq')}>Ekranni yana ko'rish</button>
                      </p>
                    )}
                    {/* dars o'rtasidagi «ko'rib oling» qadami: ekranda bosiladigan joy yo'q — davom etish shu yerda */}
                    {faqatKor && !korish && joy !== 'topilmadi' && (
                      // tor ekranda bu tugma «Dars» ko'rinishida — bosilgach o'quvchi yana ilovaga qaytadi
                      <button type="button" className="ak-tugma keng" onClick={() => { otkaz(); onRejim('mashq') }}>Ko'rdim — davom etamiz</button>
                    )}
                    {joy === 'topilmadi' && (
                      <p className="ak-izoh">
                        Bu joy ekranda ko'rinmayapti. O'ng tomondagi ilovada shu qadamni o'zingiz bajaring yoki o'tkazib yuboring.
                        <button type="button" className="ak-matn-tugma ichki" onClick={otkaz}>Qadamni o'tkazib yuborish</button>
                      </p>
                    )}
                  </section>
                )}

                {/* vaziyat matni — qadam blokidan keyin (ega talabi, 2026-11-15): avval nima qilish, keyin nega */}
                <p className="ak-topshiriq-qisqa">{dars.topshiriq}</p>
                {/* qadam nuqtalari — yozuvlar ostida (ega talabi) */}
                {yol.length > 0 && (
                  <div className="ak-nuqtalar" role="img" aria-label={`${yol.length} qadamdan ${Math.min(qadam, yol.length)} tasi bajarildi`}>
                    {yol.map((_, i) => <i key={i} className={i < qadam ? 'otgan' : i === qadam ? 'hozir' : undefined} />)}
                  </div>
                )}

                {dars.yordam.ishora && (
                  <section className="ak-yordam">
                    <h3>Ishora</h3>
                    <p>{dars.yordam.ishora}</p>
                  </section>
                )}

                {/* Ko'rgazma: ilovada mashq qilib bo'lmaydigan narsa (bot xabari, kirish ekrani) shu yerda ko'rsatiladi */}
                {savolVaqti && dars.sahna.map((b, i) => (
                  <figure key={i} className={`ak-sahna ${b.tur}`}>
                    <figcaption>{b.sarlavha}</figcaption>
                    <p>{b.matn}</p>
                    {b.tugmalar?.length > 0 && <div className="ak-sahna-tugmalar" aria-hidden="true">{b.tugmalar.map((t) => <span key={t}>{t}</span>)}</div>}
                  </figure>
                ))}

                {/* Avval o'rgatiladi, keyin so'raladi: savollarning javobi shu qoidalarda (va qadam matnlarida) */}
                {savolVaqti && bilim.length > 0 && (
                  <section className="ak-bilim">
                    <h3>Avval bilib oling</h3>
                    <ul>{bilim.map((b, i) => <li key={i}>{b}</li>)}</ul>
                    {bilimKutadi && (
                      <button type="button" className="ak-tugma keng" onClick={() => setOqildi(dars.kod)}>Tushundim — savollarga o'tish</button>
                    )}
                  </section>
                )}

                {/* Savollar: javob shu yerda tanlanadi (yo'naltirilgan darsda — oxirgi qadamda, ro'yxat faqat ko'rish uchun yoritiladi) */}
                {savolOchiq && dars.savollar.map((sv, si) => (
                  <fieldset key={si} className="ak-savol">
                    <legend>{dars.savollar.length > 1 ? `${si + 1}. ` : ''}{sv.matn}</legend>
                    {sv.variantlar.map((v) => (
                      <label key={v.id} className={javob[si] === v.id ? 'tanlangan' : undefined}>
                        <input type="radio" name={`ak-javob-${si}`} value={v.id} checked={javob[si] === v.id}
                          onChange={() => { const j = [...javob]; j[si] = v.id; setJavob(j); setNatija(null) }} />
                        {v.matn}
                      </label>
                    ))}
                  </fieldset>
                ))}

                {natija?.kod === dars.kod && (
                  <ul className="ak-mezonlar" aria-live="polite">
                    {natija.mezonlar.map((m, i) => (
                      <li key={i} className={m.ok ? 'ok' : 'yoq'}><Belgi d={m.ok ? HA : YOQ} />{m.matn}</li>
                    ))}
                  </ul>
                )}

                <div className="ak-tugmalar">
                  {savolli ? savolOchiq && (
                    <button type="button" className="ak-tugma keng" disabled={!!band || javobYetmaydi} onClick={() => tekshir(dars.kod, javob)}>
                      {band === 'tekshir' ? 'Tekshirilmoqda…' : 'Javobni tekshirish'}
                    </button>
                  ) : !mashqda && (
                    // qadamlar tugagan, lekin natija to'g'ri chiqmagan: ilova ochiq — tuzatib, qayta tekshiradi
                    <button type="button" className="ak-tugma keng" disabled={!!band} onClick={() => tekshir(dars.kod)}>
                      {band === 'tekshir' ? 'Tekshirilmoqda…' : 'Natijani tekshirish'}
                    </button>
                  )}
                  {dars.yordam.daraja === 0 && (
                    <button type="button" className="ak-tugma ikkinchi keng" disabled={!!band} onClick={() => yordam(dars.kod)}>Yordam</button>
                  )}
                  {/* darsni boshidan: yordam qatorida, kichik; qadamlar yo'qolmasligi uchun avval so'raydi.
                      Menyudagi «Qayta boshlash» — butun kurs; bu — faqat shu dars (nomi ham shunga qarab boshqa). */}
                  {darsQayta ? (
                    <p className="ak-dars-qayta" role="alertdialog" aria-label="Darsni boshidan boshlash">
                      Qadamlar boshidan boshlanadi — davom etamizmi?
                      <span>
                        <button type="button" className="ak-tugma" disabled={!!band} onClick={() => { setDarsQayta(false); boshla(dars.kod) }}>Ha, boshidan</button>
                        <button type="button" className="ak-tugma ikkinchi" disabled={!!band} onClick={() => setDarsQayta(false)}>Yo'q</button>
                      </span>
                    </p>
                  ) : (
                    <button type="button" className="ak-matn-tugma kichik" disabled={!!band} onClick={() => setDarsQayta(true)}>Darsni boshidan boshlash</button>
                  )}
                </div>
              </>
            )}

            {/* 3. Yakun: mukofot va keyingi dars */}
            {tugadi && (
              <div className="ak-yakun">
                <span className="ak-yakun-belgi" aria-hidden="true"><Belgi d={HA} /></span>
                <b>Topshiriq bajarildi</b>
                {natija.xp > 0 && <p className="ak-xp">+{natija.xp} XP</p>}
                {/* hozir nima qilindi va haqiqiy ishda bundan keyin nima keladi — dars yolg'on ko'nikma qoldirmasin */}
                {natija.xulosa && <p className="ak-xulosa">{natija.xulosa}</p>}
                {d && <p className="ak-xira">Darajangiz: {d.nomi} · {xarita.xp} XP</p>}
                {/* bobning oxirgi darsi birinchi marta bajarildi — mukofot ochildi */}
                {natija.xp > 0 && bobi(dars)?.varaq && (
                  <button type="button" className="ak-tugma ikkinchi keng" onClick={() => setVaraqBob(bobi(dars).kalit)}>
                    Yangi eslatma-varaq ochildi: «{bobi(dars).nomi}»
                  </button>
                )}
                <ul className="ak-mezonlar">
                  {natija.mezonlar.map((m, i) => <li key={i} className="ok"><Belgi d={HA} />{m.matn}</li>)}
                </ul>
                {natija.keyingi
                  ? <button type="button" className="ak-tugma keng" onClick={() => setTanlangan(natija.keyingi.kod)}>Keyingi dars: {natija.keyingi.nomi}</button>
                  : <button type="button" className="ak-tugma keng" onClick={() => setTanlangan('')}>Barcha darslar bajarildi</button>}
              </div>
            )}
          </article>
        )}
      </aside>

      {kino && <Kino onYop={kinoYop} />}

      {yangiDaraja && (
        <div className="ak-kino" role="dialog" aria-modal="true" aria-label={`Yangi daraja: ${yangiDaraja.nomi}`}>
          <div className="ak-kino-tasvir" style={{ backgroundImage: `url(/akademiya/${darajaRasmi(ustoz, yangiDaraja.raqam)}.jpg)` }} />
          <div className="ak-kino-boshi">
            <p className="ak-mono"><b>Yangi daraja</b> // {yangiDaraja.raqam} / 4</p>
            <h1>{yangiDaraja.nomi}</h1>
            <p>{DARAJA_SOZI[yangiDaraja.raqam]}</p>
            <div className="ak-kino-tugmalar">
              <button type="button" className="ak-tugma" autoFocus onClick={() => setYangiDaraja(null)}>Davom etish →</button>
            </div>
          </div>
        </div>
      )}

      {kirishSorov && (
        <div className="ak-kir-oyna" role="dialog" aria-modal="true" aria-label="Kirish kerak" onClick={(e) => { if (e.target === e.currentTarget) setKirishSorov(false) }}>
          <article>
            <p className="ak-mono"><b>Bu dars uchun kirishni amalga oshiring</b></p>
            <h2>Davom etish uchun kiring</h2>
            <p>Darslarning hammasi bepul. To'liq ochilishi uchun saloningiz Libosa'da bo'lishi kerak: saloningiz bo'lsa — kiring, bo'lmasa — ulang.</p>
            <div className="ak-kirish-sorov">
              <a className="ak-tugma" href={ASOSIY_MANZIL}>Kirish</a>
              <a className="ak-tugma ikkinchi" href={SAYT_MANZIL}>A'zo bo'lish</a>
            </div>
            <button type="button" className="ak-matn-tugma" onClick={() => setKirishSorov(false)}>Yopish</button>
          </article>
        </div>
      )}
      {varaq && (
        <div className="ak-varaq-oyna" role="dialog" aria-modal="true" aria-label={`${varaq.nomi} — eslatma-varaq`}>
          <article>
            <p className="ak-mono"><b>Libosa Academy</b> // eslatma-varaq</p>
            <h2>{varaq.nomi}</h2>
            <p className="ak-xira">{varaq.izoh}</p>
            <ol>
              {varaq.varaq.map((x) => <li key={x.kod}><b>{x.nomi}</b><span>{x.xulosa}</span></li>)}
            </ol>
            <div className="ak-kino-tugmalar">
              <button type="button" className="ak-tugma" onClick={() => window.print()}>Chop etish</button>
              <button type="button" className="ak-tugma ikkinchi" autoFocus onClick={() => setVaraqBob('')}>Yopish</button>
            </div>
          </article>
        </div>
      )}

      {/* Tor ekran: mashq paytida joriy qadam tepada ko'rinib turadi; pastda «Dars / Mashq» almashtirgichi */}
      {joriy && rejim === 'mashq' && (
        <button type="button" className="ak-tasma" onClick={() => {
          // o'rtadagi «ko'rib oling» qadami: tasmaning o'zi «davom etish» — «Dars» ga o'tib yana bir tugma bosish shart emas
          if (faqatKor && !korish && joy !== 'topilmadi') { otkaz(); return }
          setTanlangan(joriy.kod); onRejim('dars')
        }}>
          <b>{qadam < yol.length ? `${qadam + 1}/${yol.length}` : joriy.nomi}</b>
          {/* telefonda panel yopiq: yoritilgan joy qadamning o'zi bo'lmasa (menyu, yopiq bo'lim) — nega aynan u, shu yerda */}
          <span>{qadam < yol.length ? joyIzoh || yol[qadam].matn : joriy.topshiriq}</span>
          {/* «ko'rib oling» qadami: ilovada bosiladigan joy yo'q — davom etish tugmasi «Dars» ko'rinishida */}
          {/* oxirgi «ko'rib oling» qadami: savollar ham «Dars» ko'rinishida — tasma qayerga bosishni aytadi */}
          {faqatKor && <em>{korish ? 'Savollar →' : 'Davom etish →'}</em>}
        </button>
      )}
      <div className="ak-almash" role="tablist" aria-label="Ko'rinish">
        <button type="button" role="tab" aria-selected={rejim === 'dars'} onClick={() => onRejim('dars')}>Dars</button>
        <button type="button" role="tab" aria-selected={rejim === 'mashq'} onClick={() => onRejim('mashq')}>Mashq</button>
      </div>
    </>
  )
}

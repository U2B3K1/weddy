import { useCallback, useEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import Hujjat from '../components/Hujjat'
import LibosSiluet from '../components/LibosSiluet'
import NavIkona from '../components/NavIkona'
import { Bezak, IjaraSana, Muhr } from '../components/Varaq'
import Oyna from '../components/Oyna'
import Tasdiq from '../components/Tasdiq'
import SmenaTugma from '../components/SmenaTugma'
import {
  inkassatsiyaQil, kassaZaloglar, smenaChiqish, smenaHolati, smenaOchishIzoh, smenaQoshilish, smenaTuzat, smenaYopish, smenalarRoyxat, som, sozlamalar,
  otkazmaTasdiq, tolovQabul, topshiriqQabul, xarajatModdalari, xarajatYarat, tolovKutayotganlar, xatoMatni, zalogBelgila,
  guruhla, sanaMatni,
} from '../api'
import SummaInput from '../components/SummaInput'
import KpiFiltr from '../components/KpiFiltr'

// Sotuvchi kassadan to'laydigan kundalik xarajatlar; salonning o'z moddalari ham chiqadi (FT-13.1)
const KASSA_MODDALARI = ['tozalash', 'tamir', 'transport', 'kommunal', 'reklama', 'boshqa']
// Click/Payme hozircha ishlatilmaydi (2026-11-01) — kerak bo'lsa ro'yxatga qaytariladi, server ularni qabul qiladi
const USULLAR = [['naqd', 'Naqd'], ['karta', 'Terminal'], ['otkazma', "O'tkazma"]]
const USUL_NOMI = { ...Object.fromEntries(USULLAR), click: 'Click', payme: 'Payme' }
// Smena ochiq bo'lishini talab qiladigan bo'limlar (yangi zakaz va tarix — talab qilmaydi)
const SMENA_KERAK = ['tolov', 'xarajat', 'inkassatsiya', 'zalog', 'hisobot']

// 4.12: Kassa — POS ish joyi. Tepada smena paneli (holat, kim ishlayapti, kassadagi naqd, smena amallari),
// ostida ichki bo'limlar (App'dagi segment): yangi zakaz, to'lov qabul qilish, xarajat, inkassatsiya, zaloglar,
// smena hisoboti, tarix. Summalar raqamli klaviaturadan kiritiladi — planshetda barmoq bilan qulay.
// `onZakaz(id, amal)` (ixtiyoriy, App) — to'lovdan keyin zakaz kartasini ochish; amal 'berish' — berish formasiga
export default function Kassa({ rahbar, bolim, onBolim, onHolatOzgardi, yangiZakaz, tolovZakaz, onZakaz }) {
  const [s, setS] = useState(null)
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const [oyna, setOyna] = useState(null) // 'ochish' | 'chiqish' | 'yopish'
  // Oyna ichidagi amal xatosi: oyna ochiq qoladi, xato tugma ustida (sahifaga — parda ortiga — yozilmaydi)
  const [oynaXato, setOynaXato] = useState('')
  const yopOyna = useCallback(() => setOyna(null), [])

  // Smena holati App'dagi qo'ng'iroqcha va boshqa joylarga ham kerak: yuklangach onHolatOzgardi chaqiriladi.
  const yukla = useCallback(() => smenaHolati().then((r) => { setS(r); onHolatOzgardi?.() }), [onHolatOzgardi])
  useEffect(() => { yukla() }, [yukla])

  const bajar = async (fn, ok) => {
    setXabar({ turi: '', matn: '' })
    try {
      const r = await fn()
      setXabar({ turi: 'ok', matn: typeof ok === 'function' ? ok(r) : ok, bolim })
      await yukla()
      return true
    } catch (e) {
      setXabar({ turi: 'xato', matn: xatoMatni(e), kod: e.response?.data?.kod, bolim })
      return false
    }
  }
  const ochOyna = (n) => { setOynaXato(''); setOyna(n) }
  // Muvaffaqiyatda oyna yopiladi, natija sahifada; xatoda oyna ochiq qoladi va xato oyna ichida ko'rinadi
  const oynada = (fn, ok) => async (...a) => {
    setOynaXato('')
    try {
      const r = await fn(...a)
      setOyna(null)
      setXabar({ turi: 'ok', matn: typeof ok === 'function' ? ok(r) : ok, bolim })
      await yukla()
      return true
    } catch (e) {
      setOynaXato(xatoMatni(e))
      return false
    }
  }

  if (!s) return <p className="malumot">Yuklanmoqda…</p>
  const smenaYoq = !s.ochiq && SMENA_KERAK.includes(bolim)
  const kutayotgan = (
    <>
      <Kutayotgan royxat={s.kutayotgan} onQabul={(t, summa) => bajar(() => topshiriqQabul(t.id, summa), (r) => `Qabul qilindi: ${som(r.qabul_summa)}.`)} />
      <Otkazmalar royxat={s.otkazmalar} onTasdiq={(t, keldi) => bajar(() => otkazmaTasdiq(t.id, keldi),
        keldi ? 'Tasdiqlandi: pul keldi.' : "Kelmadi deb belgilandi: to'lov hisobdan chiqarildi, xodimga xabar ketdi.")} />
    </>
  )

  // «Alohida kassir» rejimida sotuvchi pul olmaydi: faqat zakaz rasmiylashtiradi, mijozni kassaga yuboradi
  if (!s.pul_oladi) {
    return (
      <div className="pos">
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot pos-xabar'}>{xabar.matn}</p>}
        {kutayotgan}
        {bolim === 'yangi' ? yangiZakaz : (
          <section className="blok pos-bosh">
            <h3>Pulni kassir qabul qiladi</h3>
            <p className="malumot">Bu salonda siz zakaz olasiz, to'lovni esa kassir qabul qiladi — mijozni kassaga yuboring.
              Zakazingizga kirgan pul statistikada sizning nomingizga yoziladi.</p>
          </section>
        )}
      </div>
    )
  }

  return (
    <div className="pos">
      {/* «Yangi zakaz»da smena — ikkinchi darajali: telefonda bir qator (holat va naqd). «Smena hisoboti»da amallar «Kun yakuni»da. */}
      <SmenaPaneli s={s} rahbar={rahbar} ixcham={bolim === 'yangi'} amalsiz={bolim === 'hisobot' && s.men_ishtirokchi}
        ochishTugmasi={!smenaYoq} onOch={() => ochOyna('ochish')} onQoshil={() => bajar(smenaQoshilish, "Smenaga qo'shildingiz.")}
        onChiq={() => ochOyna('chiqish')} onYop={() => ochOyna('yopish')} onHisobot={() => onBolim('hisobot')} />
      {kutayotgan}
      {xabar.matn && xabar.bolim === bolim && (  // eski xabar boshqa bo'limga o'tganda qolib ketmasin
        <p className={xabar.turi === 'xato' ? 'xato' : 'malumot pos-xabar'}>
          {xabar.matn}{' '}
          {xabar.turi === 'xato' && (
            <SmenaTugma kod={xabar.kod} onKassa={() => ochOyna('ochish')}
              onTayyor={() => { setXabar({ turi: 'ok', matn: "Smenaga qo'shildingiz. Amalni qayta bajaring.", bolim }); yukla() }} />
          )}
        </p>
      )}

      {smenaYoq ? (
        <section className="blok pos-bosh varaq">
          <h3>Smena yopiq</h3>
          <Bezak />
          <p className="varaq-izoh">To'lov, xarajat va inkassatsiya uchun avval smenani oching — kassadagi naqd pul sanaladi.</p>
          <button onClick={() => ochOyna('ochish')}>Smenani ochish</button>
        </section>
      ) : (
        <>
          {bolim === 'yangi' && yangiZakaz}
          {bolim === 'tolov' && <TolovPOS key={tolovZakaz?.n} boshZakaz={tolovZakaz?.id} onTolandi={yukla} onSmenaOchish={() => ochOyna('ochish')} onZakaz={onZakaz} />}
          {bolim === 'xarajat' && (
            <XarajatPOS onYuborish={(b) => bajar(() => xarajatYarat({ ...b, kassadan: true }), rahbar ? 'Xarajat kassadan yozildi.' : "Xarajat kassadan yozildi (rahbar tasdig'ini kutadi).")} />
          )}
          {bolim === 'inkassatsiya' && (
            <InkassatsiyaPOS rahbarlar={s.rahbarlar} hamkasblar={s.hamkasblar || []} smenada={(s.xodimlar || []).map((x) => x.id)}
              onYuborish={(summa, izoh, k) => bajar(() => inkassatsiyaQil(k.rahbar ? { summa, izoh, rahbar: k.id } : { summa, izoh, kimga: k.id }),
                k.rahbar ? 'Inkassatsiya yozildi — rahbar Telegramda tasdiqlaydi.' : `Pul ${k.ism}ga topshirildi — u sanab, «Qabul qildim»ni bosadi.`)} />
          )}
          {bolim === 'zalog' && <ZalogTekshiruvi onOzgardi={yukla} />}
          {bolim === 'hisobot' && <SmenaKorsatkichlari s={s} />}
          {bolim === 'hisobot' && (
            <div className="kassa-hisobot">
              <KunYakuni s={s} onBolim={onBolim} onChiq={() => ochOyna('chiqish')} onYop={() => ochOyna('yopish')} />
              <Hisobot h={s.hisobot} />
            </div>
          )}
          {bolim === 'tarix' && rahbar && <YopilganSmenalar />}
        </>
      )}

      {oyna === 'ochish' && (
        <Oyna sarlavha="Smenani ochish" onYop={yopOyna}>
          <SmenaOchish seyfda={s.seyfda} xato={oynaXato}
            onYuborish={oynada((q, izoh) => smenaOchishIzoh(q, izoh), 'Smena ochildi.')} />
        </Oyna>
      )}
      {oyna === 'chiqish' && (
        <Oyna sarlavha="Pulni topshirib chiqish" onYop={yopOyna}>
          <PulTopshirish s={s} xato={oynaXato} onYuborish={oynada((summa, kimga) => smenaChiqish(summa, kimga),
            (r) => `Chiqdingiz. Pul ${r.kimga}ga topshirildi — u tasdiqlaydi.${r.farq ? ` Farq: ${som(r.farq)}` : ''}`)} />
        </Oyna>
      )}
      {oyna === 'yopish' && (
        <Oyna sarlavha="Smenani yopish" onYop={yopOyna}>
          <SmenaYopish hisobda={s.mening_hisobim ?? s.hisobot.hisobdagi_qoldiq} tekshirilmagan={s.zalog_tekshirilmagan} rahbarlar={s.rahbarlar}
            terminalda={s.terminal_tizimda} xato={oynaXato}
            onYuborish={oynada((summa, izoh, rahbar, terminal) => smenaYopish(summa, izoh, rahbar, terminal), (r) => `Smena yopildi. Farq: ${som(r.farq)}`)} />
        </Oyna>
      )}
    </div>
  )
}

// Oyna ichidagi amal xatosi — yuboradigan tugma ustida; ekran o'quvchi darhol o'qiydi
const OynaXato = ({ matn }) => (matn ? <p className="xato oyna-xato" role="alert">{matn}</p> : null)

// Smenani yopish faqat oxirgi qolgan ishtirokchiga mumkin (backend ham shuni tekshiradi)
const yolgizmi = (s) => s.men_ishtirokchi && s.ishtirokchilar.length === 1

// Smena paneli: POS'dagi «kassir chizig'i» — har bo'limda tepada. Faqat bajarib bo'ladigan amal tugmasi chiqadi:
// yolg'iz ishtirokchiga — «Smenani yopish», hamkasbi bor ishtirokchiga — «Pulni topshirib chiqish», smenada yo'qqa — «Smenaga qo'shilish».
// `ixcham` — «Yangi zakaz»da telefonda bir qator; `amalsiz` — amallar sahifaning o'zida («Kun yakuni»);
// `ochishTugmasi` — smena yopiq va sahifada «Smena yopiq» varaqasi (o'z tugmasi bilan) bo'lmasa.
function SmenaPaneli({ s, rahbar, ixcham, amalsiz, ochishTugmasi, onOch, onQoshil, onChiq, onYop, onHisobot }) {
  if (!s.ochiq) {
    return (
      <div className={`smena-panel yopiq${ixcham ? ' ixcham' : ''}`}>
        <span className="smena-holat"><i aria-hidden="true" />Smena yopiq{s.filial ? ` · ${s.filial}` : ''}</span>
        {ochishTugmasi && (<>
          <span className="malumot">To'lov qabul qilish uchun smenani oching</span>
          {/* «Yangi zakaz»da smena shart emas — tugma zakaz tugmalari bilan raqobat qilmasin */}
          <button className={ixcham ? 'ikkinchi kichik' : 'kichik'} onClick={onOch}>Smenani ochish</button>
        </>)}
      </div>
    )
  }
  const yolgiz = yolgizmi(s)
  return (
    <div className={`smena-panel${ixcham ? ' ixcham' : ''}`}>
      <span className="smena-holat ochiq"><i aria-hidden="true" />Smena ochiq{s.filial ? ` · ${s.filial}` : ''}</span>
      <span className="smena-kim">{s.ishtirokchilar.join(', ')}
        {s.yuborilgan?.map((t) => <small key={t.id} className="malumot"> · {t.kimga} {som(t.summa)} ni hali tasdiqlamadi</small>)}</span>
      {s.men_ishtirokchi ? (
        <button type="button" className="smena-naqd" onClick={onHisobot} title="Siz javob beradigan naqd. Bosing — smena hisoboti">
          <small>Sizda naqd</small><b className={s.mening_hisobim < 0 ? 'qizil' : undefined}>{som(s.mening_hisobim)}</b>
        </button>
      ) : (
        <button type="button" className="smena-naqd" onClick={onHisobot} title="Smena hisobotini ochish">
          <small>Kassada naqd</small><b>{som(s.hisobot.hisobdagi_qoldiq)}</b>
        </button>
      )}
      {!amalsiz && (
        <div className="smena-amallar">
          {/* rahbar odatda kuzatuvchi — qo'shilish unga ikkinchi darajali */}
          {!s.men_ishtirokchi && <button className={rahbar ? 'ikkinchi kichik' : 'kichik'} onClick={onQoshil}>Smenaga qo'shilish</button>}
          {s.men_ishtirokchi && !yolgiz && (<>
            <small className="smena-izoh">Smenani oxirgi qolgan xodim yopadi</small>
            <button className="ikkinchi kichik" onClick={onChiq}>Pulni topshirib chiqish</button>
          </>)}
          {yolgiz && <button className="ikkinchi kichik" onClick={onYop}>Smenani yopish</button>}
        </div>
      )}
    </div>
  )
}

// Kun yakuni: smenani yopishdan oldingi tekshiruvlar bir joyda — har birining yonida o'sha ishni ochadigan tugma.
// Yangi qoida yo'q: backend yopishda tekshiradigan narsalar oldindan ko'rinadi (yopishda tiqilib qolmaslik uchun).
function KunYakuni({ s, onBolim, onChiq, onYop }) {
  if (!s.men_ishtirokchi) return null
  const qolganlar = (s.xodimlar || []).map((x) => x.ism)
  const qatorlar = [
    s.kutayotgan?.length > 0 && { nom: 'Sizga topshirilgan pulni qabul qiling', izoh: "Yuqoridagi «Sizga topshirilgan pul»da sanab tasdiqlang — shundan keyin yopiladi" },
    s.zalog_tekshirilmagan > 0
      ? { nom: `${s.zalog_tekshirilmagan} ta zalog tekshirilmagan`, izoh: 'Seyfdagi hujjat va tillo zaloglarni joyida deb belgilang', tugma: ['Zaloglarni tekshirish', () => onBolim('zalog')] }
      : { tayyor: true, nom: 'Zaloglar tekshirilgan' },
    qolganlar.length > 0
      ? { nom: `Smenada yana: ${qolganlar.join(', ')}`, izoh: "Smenani oxirgi qolgan xodim yopadi. Siz ketayotgan bo'lsangiz — pulni topshirib chiqing", tugma: ['Pulni topshirib chiqish', onChiq] }
      : { tayyor: true, nom: 'Smenada faqat siz qoldingiz' },
    s.terminal_tizimda > 0 && { nom: `Terminal hisoboti — tizimda ${som(s.terminal_tizimda)}`, izoh: "Terminaldan kun yakuni chekini chiqaring: undagi summa smenani yopishda kiritiladi" },
  ].filter(Boolean)
  return (
    <section className="blok jadval-panel pos-tor kun-yakuni" aria-labelledby="kun-yakuni-nom">
      <div className="jadval-asboblar"><h3 className="panel-nom" id="kun-yakuni-nom">Kun yakuni</h3>
        <span className="malumot">smenani yopishdan oldin</span></div>
      {qatorlar.map((q) => (
        <div key={q.nom} className={`tasdiq-qator${q.tayyor ? ' tayyor' : ''}`}>
          <div className="kun-yakuni-band">
            <NavIkona nom={q.tayyor ? 'bajarildi' : 'doira'} className="tugma-ikon" />
            <div className="tasdiq-matn"><b>{q.nom}</b>{q.izoh && <small>{q.izoh}</small>}</div>
          </div>
          {q.tugma && <div className="tasdiq-tugmalar"><button className="ikkinchi kichik" onClick={q.tugma[1]}>{q.tugma[0]}</button></div>}
        </div>
      ))}
      {yolgizmi(s) && (
        <div className="kun-yakuni-oxir">
          <span className="malumot">Sizda <b>{som(s.mening_hisobim)}</b> — pulni sanab, smenani yoping</span>
          <button onClick={onYop}>Smenani yopish</button>
        </div>
      )}
    </section>
  )
}

// Rahbarga: o'tkazma bilan olingan pul hisobiga tushdimi — bank SMS i bilan solishtirib belgilanadi.
// Telegramdagi «Keldi / Kelmadi» tugmalari bilan bir xil.
// «Kelmadi» qaytarib bo'lmaydi: to'lov hisobdan chiqadi va mijozdan qayta olinadi — avval Tasdiq (C-03)
function Otkazmalar({ royxat, onTasdiq }) {
  const [kelmadi, setKelmadi] = useState(null)
  if (!royxat?.length) return null
  return (
    <section className="blok jadval-panel">
      {kelmadi && (
        <Tasdiq sarlavha="O'tkazma kelmadimi?" tugma="Ha, kelmadi"
          matn={`${kelmadi.zakaz ? `Zakaz #${kelmadi.zakaz} bo'yicha` : "Bu"} ${som(kelmadi.summa)} hisobdan chiqadi — mijozdan qayta olinadi `
            + `(${kelmadi.zakaz ? "zakazda qarz bo'lib turadi" : "to'lov hisobga olinmaydi"}), ${kelmadi.xodim}ga xabar boradi. Buni qaytarib bo'lmaydi.`}
          onYop={() => setKelmadi(null)} onTasdiq={() => { const t = kelmadi; setKelmadi(null); onTasdiq(t, false) }} />
      )}
      <div className="jadval-asboblar"><h3 className="panel-nom">O'tkazmalar — hisobingizga keldimi?</h3>
        <span className="malumot">Bank SMS i bilan solishtiring</span></div>
      {royxat.map((t) => (
        <div key={t.id} className="tasdiq-qator">
          <div className="tasdiq-matn">
            <b>{t.usul_nomi} · {som(t.summa)}{t.zakaz && ` · zakaz #${t.zakaz}`}</b>
            <small>{t.tur_nomi}{t.mijoz && ` · ${t.mijoz}`} · qabul qildi: {t.xodim} · {mahalliyVaqt(t.vaqt)}</small>
          </div>
          <div className="tasdiq-tugmalar">
            <button className="ikkinchi kichik" onClick={() => setKelmadi(t)}>Kelmadi</button>
            <button className="kichik" onClick={() => onTasdiq(t, true)}>Keldi</button>
          </div>
        </div>
      ))}
    </section>
  )
}

// Bugungi sana qurilma vaqtida («2026-11-07») — olib ketish sanasi bilan solishtirish uchun
const bugunIso = () => new Date().toLocaleDateString('sv-SE')

// Server vaqti UTC da keladi — qurilmaning mahalliy vaqtida «01.11.2026 01:15»
const mahalliyVaqt = (v) => { const d = new Date(v); return `${sanaMatni(d.toLocaleDateString('sv-SE'))} ${d.toTimeString().slice(0, 5)}` }

// Menga topshirilgan, hali qabul qilinmagan pul: sanab «Qabul qildim» yoki boshqa summani kiritish.
// Telegramdagi tugmalar bilan bir xil — qaysi biri birinchi bosilsa, o'sha hisoblanadi.
function Kutayotgan({ royxat, onQabul }) {
  const [boshqa, setBoshqa] = useState({})
  if (!royxat?.length) return null
  return (
    <section className="blok jadval-panel">
      <div className="jadval-asboblar"><h3 className="panel-nom">Sizga topshirilgan pul</h3>
        <span className="malumot">Sanab tasdiqlang: shundan keyin bu pulga siz javob berasiz</span></div>
      {royxat.map((t) => (
        <div key={t.id} className="tasdiq-qator">
          <div className="tasdiq-matn">
            <b>{t.kimdan} · {som(t.summa)}{t.rahbarga && ' · inkassatsiya'}</b>
            <small>{mahalliyVaqt(t.vaqt)}{t.izoh && ` · ${t.izoh}`}</small>
          </div>
          <div className="tasdiq-tugmalar">
            {boshqa[t.id] !== undefined ? (
              <>
                <SummaInput aria-label="Sanalgan summa" value={boshqa[t.id]} onChange={(e) => setBoshqa({ ...boshqa, [t.id]: e.target.value })} />
                <button className="kichik" disabled={boshqa[t.id] === ''} onClick={() => onQabul(t, Number(boshqa[t.id]))}>Shu summani qabul qilish</button>
              </>
            ) : (
              <>
                <button className="ikkinchi kichik" onClick={() => setBoshqa({ ...boshqa, [t.id]: '' })}>Boshqa summa</button>
                <button className="kichik" onClick={() => onQabul(t)}>{som(t.summa)} qabul qildim</button>
              </>
            )}
          </div>
        </div>
      ))}
    </section>
  )
}

// Smenadan chiqish: qo'ldagi naqd sanaladi va smenada qolayotgan xodimga yoki rahbarga beriladi; u tasdiqlaydi.
function PulTopshirish({ s, xato, onYuborish }) {
  const qolganlar = s.xodimlar || []  // smenadagi boshqa xodimlar (o'zim kirmayman)
  const variantlar = [...qolganlar.map((x) => ({ ...x, izoh: 'smenada qoladi' })), ...s.rahbarlar.filter((r) => !qolganlar.some((x) => x.id === r.id)).map((r) => ({ ...r, izoh: 'rahbar' }))]
  const [kimga, setKimga] = useState('')
  const [summa, setSumma] = useState('')
  const farq = summa === '' ? null : Number(summa) - s.mening_hisobim
  return (
    <div className="stack">
      <p className="malumot">Tizim bo'yicha sizda: <b>{som(s.mening_hisobim)}</b>. Pulni sanang va kimga berayotganingizni tanlang —
        u Telegramda (yoki ilovada) tasdiqlaydi. Farq bo'lsa faqat sizga yoziladi.</p>
      <label>Kimga
        <select value={kimga} onChange={(e) => setKimga(e.target.value)}>
          <option value="">— tanlang —</option>
          {variantlar.map((x) => <option key={x.id} value={x.id}>{x.ism} ({x.izoh})</option>)}
        </select>
      </label>
      <Summa qiymat={summa} />
      <Farq farq={farq} />
      <Klaviatura qiymat={summa} onOzgar={setSumma} />
      <OynaXato matn={xato} />
      <button className="pos-tugma" disabled={summa === '' || !kimga} onClick={() => onYuborish(Number(summa), Number(kimga))}>Topshirib chiqish</button>
    </div>
  )
}

// Farq — pul sanashdagi eng muhim raqam: yirik, kamomad qizil, ortiqcha sariq, farqsiz yashil
function Farq({ farq }) {
  if (farq === null) return null
  return (
    <p className={`pos-farq ${farq < 0 ? 'kam' : farq > 0 ? 'ortiq' : 'teng'}`} aria-live="polite">
      {farq === 0 ? "Farq yo'q" : <>Farq: <b>{som(farq)}</b></>}
    </p>
  )
}

// Raqamli klaviatura: barmoq bilan summa kiritish (kompyuter klaviaturasi ham ishlaydi — maydon fokusda bo'lmasa)
function Klaviatura({ qiymat, onOzgar }) {
  const joy = useRef(null)
  const bos = (k) => {
    if (k === '⌫') return onOzgar(qiymat.slice(0, -1))
    if (k === 'C') return onOzgar('')
    const yangi = (qiymat + k).replace(/^0+(?=\d)/, '')
    if (yangi.length <= 10) onOzgar(yangi)
  }
  useEffect(() => {
    const h = (e) => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
      // oyna ochiq bo'lsa — faqat oyna ichidagi klaviatura tinglaydi (orqadagi ekran summasi o'zgarmasin)
      const oyna = document.querySelector('.oyna')
      if (oyna && !oyna.contains(joy.current)) return
      if (/^\d$/.test(e.key)) bos(e.key)
      else if (e.key === 'Backspace') bos('⌫')
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  })
  return (
    <div className="klaviatura" role="group" aria-label="Raqamli klaviatura" ref={joy}>
      {['1', '2', '3', '4', '5', '6', '7', '8', '9', '000', '0', '⌫'].map((k) => (
        <button key={k} type="button" className="ikkinchi" aria-label={k === '⌫' ? "O'chirish" : k} onClick={() => bos(k)}>{k}</button>
      ))}
    </div>
  )
}

const Summa = ({ qiymat, izoh }) => (
  <div className="pos-summa" aria-live="polite">
    <b>{guruhla(qiymat)}</b><span>so'm</span>
    {izoh && <small>{izoh}</small>}
  </div>
)

// Smenani ochish (C-11): seyfdagi naqd sanaladi; oldingi smena qoldirgan summadan farq jonli ko'rinadi,
// farq bo'lsa sababi yoziladi (smenada saqlanadi, hisobotlarda va rahbar xabarida chiqadi)
function SmenaOchish({ seyfda, xato, onYuborish }) {
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const farq = summa === '' || seyfda == null ? null : Number(summa) - seyfda
  return (
    <div className="stack">
      <span className="malumot">{seyfda != null
        ? <>Oldingi smena yopilganda seyfda <b>{som(seyfda)}</b> qolgan. Seyfdagi naqd pulni sanab kiriting.</>
        : "Boshlang'ich qoldiq — seyfdagi naqd pul"}</span>
      <Summa qiymat={summa} />
      <Farq farq={farq} />
      <Klaviatura qiymat={summa} onOzgar={setSumma} />
      {!!farq && <label>Izoh (farq sababi — majburiy)<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>}
      <OynaXato matn={xato} />
      <button className="pos-tugma" disabled={summa === '' || (!!farq && !izoh.trim())}
        onClick={() => onYuborish(Number(summa), farq ? izoh.trim() : '')}>Smenani ochish</button>
    </div>
  )
}

function SmenaYopish({ hisobda, tekshirilmagan, rahbarlar, terminalda, xato, onYuborish }) {
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const [surov, setSurov] = useState(false)
  const [rahbar, setRahbar] = useState('')  // bo'sh — pul seyfda qoladi
  const [terminal, setTerminal] = useState('')  // terminal hisobotidagi (kun yakuni chekidagi) summa (terminal orqali to'lov bo'lsa majburiy)
  const farq = summa === '' ? null : Number(summa) - hisobda
  const tFarq = terminal === '' ? null : Number(terminal) - terminalda
  const izohKerak = (farq !== null && farq !== 0) || (tFarq !== null && tFarq !== 0)
  return (
    <div className="stack">
      <p className="malumot">Sizda (tizim bo'yicha): <b>{som(hisobda)}</b>. Qo'lingizdagi naqd pulni sanab kiriting.</p>
      <label>Pul qayerda qoladi
        <select value={rahbar} onChange={(e) => setRahbar(e.target.value)}>
          <option value="">Seyfda</option>
          {rahbarlar.map((r) => <option key={r.id} value={r.id}>Rahbarga: {r.ism}</option>)}
        </select>
        <small className="malumot">{rahbar ? 'Rahbar Telegramda (yoki ilovada) qabul qilganini tasdiqlaydi.' : 'Ertaga smenani ochgan xodim sanab qabul qiladi.'}</small>
      </label>
      {tekshirilmagan > 0 && <p className="ogohlantirish">{tekshirilmagan} ta zalog tekshirilmagan — yopishdan oldin «Zaloglar» bo'limida belgilang.</p>}
      <Summa qiymat={summa} />
      <Farq farq={farq} />
      <Klaviatura qiymat={summa} onOzgar={setSumma} />
      {terminalda > 0 && (
        <label>Terminal hisoboti — kun yakuni chekidagi summa (tizimda {som(terminalda)})
          <SummaInput aria-label="Terminal hisoboti" value={terminal} onChange={(e) => setTerminal(e.target.value)} />
          <Info nom="Terminal hisoboti">Kun oxirida terminaldan chiqariladigan yakuniy chekdagi jami summa. Tizimga yozilgan karta to'lovlari bilan
            solishtiriladi: farq bo'lsa — terminaldan o'tgan, lekin tizimga yozilmagan (yoki aksincha) to'lov bor.</Info>
          {tFarq !== null && <small className={tFarq ? 'qizil' : 'malumot'}>{tFarq ? `Terminal farqi: ${som(tFarq)}` : "Terminal bo'yicha farq yo'q"}</small>}
        </label>
      )}
      {izohKerak && <label>Izoh (farq sababi — majburiy)<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>}
      <OynaXato matn={xato} />
      <button className="pos-tugma" disabled={summa === '' || (terminalda > 0 && terminal === '') || (izohKerak && !izoh.trim())} onClick={() => setSurov(true)}>Smenani yopish</button>
      {surov && (
        <Tasdiq sarlavha="Smenani yopasizmi?" tugma="Smenani yopish"
          matn={`Smena yopiladi, keyin to'lov qabul qilib bo'lmaydi. Sanalgan naqd: ${som(Number(summa))}${rahbar ? ` — ${rahbarlar.find((r) => String(r.id) === rahbar)?.ism}ga topshiriladi, u Telegramda tasdiqlaydi` : ' — seyfda qoladi'}.`}
          onYop={() => setSurov(false)} onTasdiq={() => { setSurov(false); onYuborish(Number(summa), izoh, rahbar ? Number(rahbar) : undefined, terminal === '' ? undefined : Number(terminal)) }} />
      )}
    </div>
  )
}

// To'lov qabul qilish — POS ekrani: chapda to'lov kutayotgan zakazlar, o'ngda chek (summa, klaviatura, usul)
function TolovPOS({ boshZakaz, onTolandi, onSmenaOchish, onZakaz }) {
  const [royxat, setRoyxat] = useState(null)
  const [q, setQ] = useState('')
  const [tanlangan, setTanlangan] = useState(boshZakaz || null)
  const [summa, setSumma] = useState('')
  const [usul, setUsul] = useState('naqd')
  const [xato, setXato] = useState('')
  const [xatoKod, setXatoKod] = useState('')  // serverdan: smena_qoshilish | smena_yoq — xato yonida mos tugma
  const [qoshildi, setQoshildi] = useState(false)
  const [band, setBand] = useState(false)
  const [tolandi, setTolandi] = useState(null) // { zakaz, summa, usul, berish }
  const [chek, setChek] = useState(null)
  const [soz, setSoz] = useState(null)
  useEffect(() => { sozlamalar().then(setSoz).catch(() => {}) }, [])
  const chekRef = useRef(null)

  // Bitta so'rov, kesimsiz: vaqtinchalik va bron, qoldig'i bor (yoki 0 so'mlik vaqtinchalik — kassir uni «to'lovsiz»
  // tasdiqlaydi), olib ketish sanasi bo'yicha — filtr va tartib serverda
  const yukla = useCallback(() => tolovKutayotganlar(q).then(setRoyxat)
    .catch((e) => setXato(xatoMatni(e))), [q])
  useEffect(() => { const t = setTimeout(yukla, q ? 300 : 0); return () => clearTimeout(t) }, [yukla, q])

  const z = royxat?.find((x) => x.id === tanlangan)
  const qoldiq = z ? z.jami - z.tolangan : 0
  const avans = z?.holat === 'vaqtinchalik'
  const tanla = (id) => { setTanlangan(id); setSumma(''); setXato(''); setXatoKod(''); setQoshildi(false); setTolandi(null) }
  // Bir ustunli ekranda (telefon, planshet) chek ro'yxat ostida: zakaz tanlansa yoki to'lov o'tsa ro'yxat yig'iladi
  // (faqat tanlangan qator qoladi) va chek ko'rinadigan joyga suriladi
  const yigilgan = Boolean(z || tolandi)
  useEffect(() => {
    if (!yigilgan || !window.matchMedia('(max-width: 1023px)').matches) return
    const harakat = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
    chekRef.current?.scrollIntoView({ block: 'start', behavior: harakat })
  }, [yigilgan, z?.id])
  const qabul = async () => {
    setXato(''); setXatoKod(''); setQoshildi(false); setBand(true)
    try {
      await tolovQabul({ zakaz: z.id, tur: avans ? 'avans' : 'qoldiq', summa: Number(summa), usul })
      // To'liq to'landi va olib ketish kuni keldi — zakaz endi bron, keyingi qadam libosni berish
      // QA-16: faqat hali berilmagan zakaz (to'lovdan keyin «Bron»: vaqtinchalik avans bilan bronga o'tadi);
      // berilgan/qaytarilgan zakazning qoldig'i («kelmadi» o'tkazma) to'langanda berish yo'q
      setTolandi({ zakaz: z, summa: Number(summa), usul,
        berish: ['vaqtinchalik', 'bron'].includes(z.holat) && qoldiq - Number(summa) === 0 && String(z.olib_ketish) <= bugunIso() })
      setTanlangan(null); setSumma('')
      await Promise.all([yukla(), onTolandi?.()])
    } catch (e) { setXato(xatoMatni(e)); setXatoKod(e.response?.data?.kod || '') } finally { setBand(false) }
  }

  if (chek) return <Hujjat zakazId={chek} tur="kvitansiya" onYop={() => setChek(null)} />

  return (
    <div className="pos-ish">
      <section className={`blok jadval-panel pos-royxat${yigilgan ? ' yigilgan' : ''}`}>
        <div className="jadval-asboblar">
          <h3 className="panel-nom">To'lov kutayotgan zakazlar{royxat?.length > 0 && <span className="tab-son">{royxat.length}</span>}</h3>
          <label className="qidiruv-maydon">
            <NavIkona nom="qidiruv" className="tugma-ikon" />
            <input type="search" className="jadval-qidiruv" placeholder="Raqam, telefon yoki ism" aria-label="Zakaz qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
          {/* faqat bir ustunli ekranda: yig'ilgan ro'yxatni qayta ochadi */}
          {z && <button type="button" className="ikkinchi kichik pos-boshqa" onClick={() => tanla(null)}>Boshqa zakaz</button>}
        </div>
        {royxat === null && <p className="malumot jadval-bosh">Yuklanmoqda…</p>}
        {royxat && royxat.length === 0 && <p className="malumot jadval-bosh">{q ? `«${q}» bo'yicha zakaz topilmadi.` : "To'lov kutayotgan zakaz yo'q."}</p>}
        {royxat?.length > 0 && (
          <div className="pos-zakazlar">
            {royxat.map((x) => (
              <button key={x.id} type="button" className={`pos-zakaz${x.id === tanlangan ? ' tanlandi' : ''}`} aria-pressed={x.id === tanlangan} onClick={() => tanla(x.id)}>
                <span className="zakaz-eskiz">{x.rasm ? <img src={x.rasm} alt="" loading="lazy" /> : <LibosSiluet />}</span>
                <span className="zakaz-nom"><b>#{x.raqam} {x.mijoz}</b><small>{x.liboslar.join(', ')}{x.sotuvchi && ` · sotuvchi: ${x.sotuvchi}`}</small></span>
                <span className="pos-zakaz-sana"><IjaraSana dan={x.olib_ketish} gacha={x.qaytarish} /></span>
                <span className="pos-zakaz-summa"><b>{som(x.jami - x.tolangan)}</b><small>{x.holat === 'vaqtinchalik' ? 'avans' : 'qoldiq'}</small></span>
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Chek — zakaz varaqasi uslubida: mijoz ismi qo'lyozmada, hisob va summa serif raqamlarda; to'langach muhr bosiladi */}
      {/* tanlanmaguncha bo'sh: bir ustunli ekranda yashirin (ro'yxat ostida ma'nosiz) */}
      <section className={`blok pos-chek varaq${!z && !tolandi ? ' bosh' : ''}`} aria-label="To'lov" ref={chekRef}>
        {tolandi && !z && (
          <div className="pos-tayyor">
            <Muhr raqam={tolandi.zakaz.raqam} />
            <h3>To'lov qabul qilindi</h3>
            <p>#{tolandi.zakaz.raqam} {tolandi.zakaz.mijoz} · <b>{som(tolandi.summa)}</b> · {USUL_NOMI[tolandi.usul]}</p>
            {/* C-03: o'tkazma rahbar «keldi» demaguncha hisobga olingan, lekin tasdiqlanmagan */}
            {tolandi.usul === 'otkazma' && soz?.otkazma_tasdigi !== false && (
              <p className="ogohlantirish">{som(tolandi.summa)} o'tkazma rahbar tasdig'ini kutmoqda.</p>
            )}
            {soz?.fiskal_eslatma && <p className="ogohlantirish">{soz.fiskal_izoh || 'Fiskal chekni urishni unutmang.'}</p>}
            {onZakaz && tolandi.berish && (
              <button className="pos-tugma" onClick={() => onZakaz(tolandi.zakaz.id, 'berish')}>Libosni berish →</button>
            )}
            <div className="qator">
              <button className="ikkinchi" onClick={() => setChek(tolandi.zakaz.id)}>Kvitansiya</button>
              <button className={onZakaz && tolandi.berish ? 'ikkinchi' : ''} onClick={() => setTolandi(null)}>Keyingi to'lov</button>
            </div>
          </div>
        )}
        {!z && !tolandi && (
          <div className="pos-bosh-matn">
            <Bezak />
            <p className="varaq-izoh">Ro'yxatdan zakazni tanlang — to'lov shu yerda qabul qilinadi.</p>
          </div>
        )}
        {z && (
          <>
            <div className="pos-chek-bosh">
              <small>#{z.raqam} · {avans ? 'avans' : "qoldiq to'lovi"}</small>
              <p className="varaq-kimga">{z.mijoz}</p>
              <span>{z.liboslar.join(', ')} · <IjaraSana dan={z.olib_ketish} gacha={z.qaytarish} /></span>
            </div>
            <table className="pos-hisob"><tbody>
              <tr><td>Jami</td><td>{som(z.jami)}</td></tr>
              <tr><td>To'langan</td><td>{som(z.tolangan)}</td></tr>
              <tr><td><b>{avans ? 'Avans (qoldiq)' : 'Qoldiq'}</b></td><td><b>{som(qoldiq)}</b></td></tr>
            </tbody></table>
            {z.jami === 0 ? (
              <button className="pos-tugma" disabled={band} onClick={async () => {
                setXato(''); setBand(true)
                try { await tolovQabul({ zakaz: z.id, tur: 'avans', summa: 0, usul: 'naqd' }); setTanlangan(null); await Promise.all([yukla(), onTolandi?.()]) } catch (e) { setXato(xatoMatni(e)) } finally { setBand(false) }
              }}>Bronni tasdiqlash (to'liq chegirma — to'lov yo'q)</button>
            ) : null}
            {z.jami === 0 && xato && <p className="xato">{xato}</p>}
            {z.jami !== 0 && (<>
            <Summa qiymat={summa} izoh={Number(summa) > qoldiq ? `Qoldiqdan oshib ketdi (${som(qoldiq)})` : null} />
            <div className="pos-tez">
              <button type="button" className="ikkinchi kichik" onClick={() => setSumma(String(qoldiq))}>To'liq: {som(qoldiq)}</button>
              {avans && [50, 30].map((f) => (
                <button key={f} type="button" className="ikkinchi kichik" onClick={() => setSumma(String(Math.round((qoldiq * f) / 100 / 1000) * 1000))}>{f}%</button>
              ))}
            </div>
            <Klaviatura qiymat={summa} onOzgar={setSumma} />
            <div className="pos-usullar" role="radiogroup" aria-label="To'lov usuli">
              {USULLAR.map(([k, nom]) => (
                <button key={k} type="button" role="radio" aria-checked={usul === k} className={usul === k ? 'tanlandi' : ''} onClick={() => setUsul(k)}>{nom}</button>
              ))}
            </div>
            {xato && (
              <p className="xato">
                {xato}{' '}
                <SmenaTugma kod={xatoKod} onKassa={onSmenaOchish}
                  onTayyor={() => { setXato(''); setXatoKod(''); setQoshildi(true); onTolandi?.() }} />
              </p>
            )}
            {qoshildi && <p className="malumot">Smenaga qo'shildingiz — «Qabul qilish» ni qayta bosing.</p>}
            <button className="pos-tugma" disabled={band || !(Number(summa) > 0) || Number(summa) > qoldiq} onClick={qabul}>
              {band ? 'Qabul qilinmoqda…' : `Qabul qilish${Number(summa) > 0 ? ` · ${som(Number(summa))}` : ''}`}
            </button>
            </>)}
          </>
        )}
      </section>
    </div>
  )
}

// Smena hisoboti tepasida — maket uslubidagi 4 ko'rsatkich (bosilmaydi): batafsili ostidagi «Naqd pul hisobi»da.
// Kassada summa yaxlitlanmaydi («2 mln» 1 990 000 ni yashirardi) — so'mgacha aniq
function SmenaKorsatkichlari({ s }) {
  const h = s.hisobot
  const chiqim = h.xarajatlar + h.vozvrat_va_inkassatsiya
  return (
    <section className="dash-kpi kpi-filtrlar smena-kpi" aria-label="Smena ko'rsatkichlari">
      <KpiFiltr nom="Kassada naqd" son={som(h.hisobdagi_qoldiq)} ikon="kassa" rang="tilla" izoh={`kun boshida ${som(h.kun_boshidagi_qoldiq)}`} />
      <KpiFiltr nom="Kirgan naqd" son={som(h.tushum)} ikon="tushum" rang="yashil" izoh="avans + qoldiq + jarima" />
      <KpiFiltr nom="Terminal" son={som(s.terminal_tizimda || 0)} ikon="terminal" rang="kok" izoh="chek bilan solishtiring" />
      <KpiFiltr nom="Chiqim" son={som(chiqim)} ikon="hamyon" rang="pushti"
        izoh={chiqim ? `xarajat ${som(h.xarajatlar)} · topshirildi ${som(h.vozvrat_va_inkassatsiya)}` : "bugun chiqim yo'q"} />
    </section>
  )
}

function Hisobot({ h }) {
  const qatorlar = [
    ['Kun boshidagi qoldiq', h.kun_boshidagi_qoldiq], ['Kirgan pul (avans + qoldiq + jarima)', h.tushum],
    ['Olingan pul zaloglar', h.olingan_zaloglar], ['Qaytarilgan zaloglar', -h.qaytarilgan_zaloglar],
    ['Xarajatlar', -h.xarajatlar], ['Pulni qaytarish va inkassatsiya', -h.vozvrat_va_inkassatsiya],
  ]
  return (
    <section className="blok jadval-panel pos-tor">
      <div className="jadval-asboblar"><h3 className="panel-nom">Naqd pul hisobi</h3><span className="malumot">kassadagi naqd — tizim bo'yicha</span></div>
      <table className="kassa-hisob"><tbody>
        {qatorlar.map(([n, v]) => <tr key={n} className={v < 0 ? 'chiqim' : v === 0 ? 'nol' : ''}><td>{n}</td><td>{som(v)}</td></tr>)}
      </tbody></table>
      <div className="kassa-hisob-jami"><span>Hisobdagi qoldiq</span><b>{som(h.hisobdagi_qoldiq)}</b></div>
      {Object.keys(h.sotuvchilar).length > 0 && (
        <p className="kassa-kirimlar">Kirimlar: {Object.entries(h.sotuvchilar).map(([k, v]) => <span key={k}>{k} <b>{som(v)}</b></span>)}</p>
      )}
    </section>
  )
}

// Xarajat: modda — katta plitkalar, summa — klaviatura (POS uslubi)
function XarajatPOS({ onYuborish }) {
  const [modda, setModda] = useState('transport')
  const [moddalar, setModdalar] = useState([])
  useEffect(() => {
    xarajatModdalari().then((m) => setModdalar(m.filter((x) => !x.standart || KASSA_MODDALARI.includes(x.kod)))).catch(() => {})
  }, [])
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  return (
    <div className="pos-ish">
      <section className="blok jadval-panel">
        <div className="jadval-asboblar"><h3 className="panel-nom">Xarajat turi</h3><span className="malumot">nimaga to'landi?</span></div>
        <div className="pos-ich">
          <div className="pos-plitkalar" role="radiogroup" aria-label="Xarajat turi">
            {moddalar.map((m) => (
              <button key={m.kod} type="button" role="radio" aria-checked={modda === m.kod} className={modda === m.kod ? 'tanlandi' : ''} onClick={() => setModda(m.kod)}>{m.nomi}</button>
            ))}
          </div>
          <label>Izoh<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>
        </div>
      </section>
      <section className="blok pos-chek varaq" aria-label="Xarajat">
        <div className="pos-chek-bosh">
          <small>kassadan chiqim</small>
          <p className="chek-nom">{moddalar.find((m) => m.kod === modda)?.nomi || 'Xarajat'}</p>
        </div>
        <Summa qiymat={summa} />
        <Klaviatura qiymat={summa} onOzgar={setSumma} />
        <button className="pos-tugma" disabled={!(Number(summa) > 0)}
          onClick={() => onYuborish({ modda, summa: Number(summa), izoh }).then((ok) => ok && (setSumma(''), setIzoh('')))}>
          Xarajatni yozish
        </button>
      </section>
    </div>
  )
}

// FT-12.6: rahbarga topshirilgan naqd pul — alohida chiqim, tushum va xarajatga kirmaydi. Rahbar Telegramda tasdiqlaydi.
// Smenadagi hamkasbga ham berish mumkin: pul kassada qoladi, faqat uning hisobiga o'tadi (u sanab qabul qiladi).
function InkassatsiyaPOS({ rahbarlar, hamkasblar, smenada, onYuborish }) {
  const rahbarIdlar = new Set(rahbarlar.map((r) => r.id))
  const tanlov = [...rahbarlar.map((r) => ({ ...r, rahbar: true, kalit: `r:${r.id}` })),
    ...hamkasblar.filter((x) => !rahbarIdlar.has(x.id)).map((x) => ({ ...x, rahbar: false, kalit: `x:${x.id}` }))]
  // bitta rahbar bo'lsa — odatdagidek o'zi tanlangan (inkassatsiya)
  const [kalit, setKalit] = useState(rahbarlar.length === 1 ? `r:${rahbarlar[0].id}` : tanlov.length === 1 ? tanlov[0].kalit : '')
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const kimga = tanlov.find((t) => t.kalit === kalit)
  if (!tanlov.length) return <section className="blok pos-tor"><p className="malumot">Pul topshiradigan rahbar yoki smenadagi hamkasb yo'q.</p></section>
  return (
    <div className="pos-ish">
      <section className="blok jadval-panel">
        <div className="jadval-asboblar"><h3 className="panel-nom">Kimga topshirasiz?</h3></div>
        <div className="pos-ich">
          <div className="pos-plitkalar kimga-plitkalar" role="radiogroup" aria-label="Kimga">
            {tanlov.map((t) => (
              <button key={t.kalit} type="button" role="radio" aria-checked={kalit === t.kalit} className={kalit === t.kalit ? 'tanlandi' : ''}
                onClick={() => setKalit(t.kalit)}>
                <b>{t.ism}</b><small>{t.rahbar ? 'rahbar · kassadan chiqadi' : smenada.includes(t.id) ? 'smenada · kassada qoladi' : "kassada qoladi · smenaga qo'shiladi"}</small>
              </button>
            ))}
          </div>
          {kimga && (
            <p className="malumot">{kimga.rahbar
              ? "Pul kassadan chiqadi — rahbar sanab, Telegramda tasdiqlaydi."
              : `Pul kassada qoladi: sizning hisobingizdan ${kimga.ism}ning hisobiga o'tadi${smenada.includes(kimga.id) ? '' : ` (${kimga.ism} smenaga qo'shiladi)`}. ${kimga.ism} sanab, «Qabul qildim»ni bosadi.`}</p>
          )}
          <label>Izoh<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>
        </div>
      </section>
      <section className="blok pos-chek varaq" aria-label="Inkassatsiya">
        <div className="pos-chek-bosh">
          <small>{kimga ? (kimga.rahbar ? 'inkassatsiya' : 'hamkasbga') : 'kimga — tanlang'}</small>
          <p className="chek-nom">{kimga?.ism || '—'}</p>
        </div>
        <Summa qiymat={summa} />
        <Klaviatura qiymat={summa} onOzgar={setSumma} />
        <button className="pos-tugma" disabled={!kimga || !(Number(summa) > 0)}
          onClick={() => onYuborish(Number(summa), izoh, kimga).then((ok) => ok && (setSumma(''), setIzoh('')))}>
          {/* C-27: hamkasbga berish inkassatsiya emas — pul kassada qoladi */}
          {!kimga ? 'Topshirish' : kimga.rahbar ? 'Rahbarga topshirish' : `${kimga.ism}ga berish`}
        </button>
      </section>
    </div>
  )
}

// FT-12.5: kun oxirida salonda saqlanayotgan hujjat va tillo zaloglar «joyida» deb belgilanadi.
function ZalogTekshiruvi({ onOzgardi }) {
  const [royxat, setRoyxat] = useState(null)
  const [izoh, setIzoh] = useState({})
  const [xato, setXato] = useState('')
  useEffect(() => { kassaZaloglar().then((r) => setRoyxat(r.zaloglar)).catch((e) => setXato(xatoMatni(e))) }, [])
  const belgila = async (z, joyida) => {
    setXato('')
    try { setRoyxat((await zalogBelgila({ zalog: z.id, joyida, izoh: izoh[z.id] || '' })).zaloglar); onOzgardi?.() } catch (e) { setXato(xatoMatni(e)) }
  }
  return (
    <section className="blok jadval-panel">
      <div className="jadval-asboblar"><h3 className="panel-nom">Saqlanayotgan zaloglar</h3>
        <span className="malumot">Smenani yopishdan oldin har birini seyfdan tekshirib belgilang</span></div>
      {xato && <p className="xato jadval-bosh">{xato}</p>}
      {royxat === null && !xato && <p className="malumot jadval-bosh">Yuklanmoqda…</p>}
      {royxat && royxat.length === 0 && <p className="malumot jadval-bosh">Salonda saqlanayotgan hujjat yoki tillo zalog yo'q.</p>}
      {royxat?.map((z) => (
        <div key={z.id} className="tasdiq-qator">
          <div className="tasdiq-matn">
            <b>{z.yorliq} · {z.tavsif}</b>
            <small>zakaz #{z.zakaz_raqami} ({z.mijoz}){z.joyida === true && ' · joyida'}{z.joyida === false && ' · JOYIDA EMAS'}</small>
          </div>
          <div className="tasdiq-tugmalar">
            <input placeholder="Yo'q bo'lsa izoh" aria-label="Izoh" value={izoh[z.id] || ''} maxLength={300} onChange={(e) => setIzoh({ ...izoh, [z.id]: e.target.value })} />
            <button className="ikkinchi kichik" disabled={!(izoh[z.id] || '').trim()} onClick={() => belgila(z, false)}>Yo'q</button>
            <button className={z.joyida === true ? 'kichik' : 'ikkinchi kichik'} onClick={() => belgila(z, true)}>Joyida</button>
          </div>
        </div>
      ))}
    </section>
  )
}

// FT-12.11: yopilgan smenani faqat rahbar o'zgartiradi (qayta sanash natijasi); o'zgarish jurnalga yoziladi.
// Qatorda faqat ma'lumot, tuzatish — oynada. «Faqat farqlilar» — kassa yoki terminal farqi bilan yopilgan smenalar (serverda).
function YopilganSmenalar() {
  const [royxat, setRoyxat] = useState(null)
  const [farqli, setFarqli] = useState(false)
  const [tuzat, setTuzat] = useState(null)  // oynada tuzatilayotgan smena
  const [xabar, setXabar] = useState({ turi: '', matn: '' })
  const yukla = useCallback(() => smenalarRoyxat(farqli ? { farqli: 1 } : undefined).then(setRoyxat)
    .catch((e) => setXabar({ turi: 'xato', matn: xatoMatni(e) })), [farqli])
  useEffect(() => { yukla() }, [yukla])
  const yopTuzat = useCallback(() => setTuzat(null), [])
  const saqla = async (s, body) => {
    await smenaTuzat(s.id, body)  // xato bo'lsa oyna o'zi ko'rsatadi
    setTuzat(null); setXabar({ turi: 'ok', matn: 'Smena tuzatildi.' }); await yukla()
  }
  return (
    <>
      <section className="blok jadval-panel">
        <div className="jadval-asboblar"><h3 className="panel-nom">Smenalar tarixi</h3>
          <button type="button" className="bugun-chip" aria-pressed={farqli} onClick={() => { setXabar({ turi: '', matn: '' }); setFarqli(!farqli) }}>Faqat farqlilar</button>
        </div>
        {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato jadval-bosh' : 'malumot jadval-bosh'}>{xabar.matn}</p>}
        {royxat && royxat.length === 0 && <p className="malumot jadval-bosh">{farqli ? "Farq bilan yopilgan smena yo'q." : "Smena yo'q."}</p>}
        {royxat?.map((s) => (
          <div key={s.id} className="tasdiq-qator">
            <div className="tasdiq-matn">
              <b>{sanaMatni(s.sana)}{s.filial ? ` · ${s.filial}` : ''} · {s.ochgan}</b>
              <small>{s.yopilgan ? <>hisobda {som(s.hisobdagi_qoldiq)}, sanaldi {som(s.fakt_qoldiq)}</> : 'ochiq'}
                {s.zalog_tekshirilmagan > 0 && <span className="qizil"> · {s.zalog_tekshirilmagan} ta zalog tekshirilmagan</span>}
                {s.zalog_yoq > 0 && <b className="qizil"> · {s.zalog_yoq} ta zalog joyida emas</b>}
                {!!s.terminal_farq && <b className="qizil"> · terminal farqi {som(s.terminal_farq)}</b>}
                {s.izoh && ` · ${s.izoh}`}</small>
            </div>
            {s.yopilgan && (
              <div className="tasdiq-tugmalar">
                <span className={`tarix-farq ${s.farq < 0 ? 'kam' : s.farq > 0 ? 'ortiq' : 'teng'}`}>{s.farq ? som(s.farq) : "farq yo'q"}</span>
                <button className="ikkinchi kichik" onClick={() => setTuzat(s)}>Tuzatish</button>
              </div>
            )}
          </div>
        ))}
      </section>
      {tuzat && (
        <Oyna sarlavha={`Smenani tuzatish · ${sanaMatni(tuzat.sana)}`} onYop={yopTuzat}>
          <SmenaTuzatish s={tuzat} onSaqla={(body) => saqla(tuzat, body)} />
        </Oyna>
      )}
    </>
  )
}

// Yopilgan smenaning qayta sanash natijasi: sanalgan summa va izoh; farq jonli ko'rinadi
function SmenaTuzatish({ s, onSaqla }) {
  const [fakt, setFakt] = useState(String(s.fakt_qoldiq ?? ''))
  const [izoh, setIzoh] = useState(s.izoh || '')
  const [xato, setXato] = useState('')
  const [band, setBand] = useState(false)
  const farq = fakt === '' ? null : Number(fakt) - s.hisobdagi_qoldiq
  const ozgardi = Number(fakt) !== s.fakt_qoldiq || izoh.trim() !== (s.izoh || '').trim()
  const saqla = async () => {
    setXato(''); setBand(true)
    try { await onSaqla({ fakt_qoldiq: Number(fakt), izoh: izoh.trim() }) } catch (e) { setXato(xatoMatni(e)); setBand(false) }
  }
  return (
    <div className="stack">
      <p className="malumot">{s.ochgan} ochgan smena. Tizim bo'yicha kassada: <b>{som(s.hisobdagi_qoldiq)}</b>, yopishda sanalgan: <b>{som(s.fakt_qoldiq)}</b>.
        Pul qayta sanalgan bo'lsa — yangi summani kiriting, o'zgarish jurnalga yoziladi.</p>
      <label>Sanalgan summa<SummaInput value={fakt} onChange={(e) => setFakt(e.target.value)} /></label>
      <Farq farq={farq} />
      <label>Izoh{farq ? ' (farq sababi — majburiy)' : ''}<input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} /></label>
      <OynaXato matn={xato} />
      <button className="pos-tugma" disabled={band || fakt === '' || !ozgardi || (!!farq && !izoh.trim())} onClick={saqla}>
        {band ? 'Saqlanmoqda…' : 'Tuzatishni saqlash'}
      </button>
    </div>
  )
}

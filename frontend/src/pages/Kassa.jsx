import { useCallback, useEffect, useRef, useState } from 'react'
import Info from '../components/Info'
import Hujjat from '../components/Hujjat'
import LibosSiluet from '../components/LibosSiluet'
import NavIkona from '../components/NavIkona'
import Tasma from '../components/Tasma'
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
import { OYLAR } from '../components/kalendar/sana'
import Sahifali from '../components/Sahifalash'
import KpiFiltr from '../components/KpiFiltr'

// Sotuvchi kassadan to'laydigan kundalik xarajatlar; salonning o'z moddalari ham chiqadi (FT-13.1)
const KASSA_MODDALARI = ['tozalash', 'tamir', 'transport', 'kommunal', 'reklama', 'boshqa']
// Click/Payme hozircha ishlatilmaydi (2026-11-01) — kerak bo'lsa ro'yxatga qaytariladi, server ularni qabul qiladi
const USULLAR = [['naqd', 'Naqd'], ['karta', 'Terminal'], ['otkazma', "O'tkazma"]]
const USUL_NOMI = { ...Object.fromEntries(USULLAR), click: 'Click', payme: 'Payme' }
// To'lov usuli ikonkalari (shisha maketidagidek): naqd — pul, terminal — karta, o'tkazma — ikki yo'nalish
const USUL_IKON = {
  naqd: 'M2 6h20v12H2zM12 9.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 1 0 0-5',
  karta: 'M3 5h18v14H3zM3 10h18M7 15h4',
  otkazma: 'M4 8h14l-3-3M20 16H6l3 3',
}
// To'lov kutayotganlar guruhlari: bugun (olib ketish kuni kelgan yoki o'tgan bron), oldindan to'lov, qarzi bor (berilgan/qaytarilgan)
const POS_GURUHLAR = [['bugun', 'Bugun'], ['oldin', "Oldindan to'lov"], ['qarz', 'Qarzi bor']]
const POS_HOLAT = { vaqtinchalik: 'avanssiz', chegirma_kutilmoqda: 'chegirma kutilmoqda', bron: 'bron', berildi: 'mijozda', qaytarildi: 'qaytarilgan' }
const OY_QISQA = ['yan', 'fev', 'mar', 'apr', 'may', 'iyun', 'iyul', 'avg', 'sen', 'okt', 'noy', 'dek']
const sanaQisqa = (iso) => { const [, m, d] = String(iso).split('-').map(Number); return `${d} ${OY_QISQA[m - 1]}` }
// Maket: telefon kassa ekranida qisman yashirin (+998 90 *** ** 67) — mijoz yonida turgan bo'lishi mumkin
const telefonYashir = (t) => { const r = String(t || '').replace(/\D/g, ''); return r.length === 12 && r.startsWith('998') ? `+998 ${r.slice(3, 5)} *** ** ${r.slice(10)}` : (t || '') }
// Libos ustunidagi ikkinchi qator (maket): avanssiz bron qachon bo'shashi, qarzdorda — kechikish yoki qaytgan sana; aks holda ijara sanasi
function posIzoh(x, g, bugun, hozir) {
  if (x.holat === 'vaqtinchalik' && x.bron_muddati) {
    const soat = Math.ceil((new Date(x.bron_muddati).getTime() - hozir) / 3600000)
    const qachon = soat <= 1 ? '1 soat ichida' : soat < 48 ? `${soat} soatda` : `${Math.round(soat / 24)} kunda`
    return { matn: `avanssiz · ${qachon} bo'shaydi`, tur: 'ogoh' }
  }
  if (g === 'qarz') {
    if (x.holat === 'berildi' && String(x.qaytarish) < bugun) {
      const kun = Math.round((new Date(bugun).getTime() - new Date(x.qaytarish).getTime()) / 86400000)
      return { matn: `${kun} kun kechikdi`, tur: 'qizil' }
    }
    if (x.holat === 'qaytarildi') return { matn: `qaytardi ${sanaQisqa(x.qaytarish)}` }
    return { matn: `mijozda · ${sanaQisqa(x.qaytarish)} gacha` }
  }
  return { bugun: String(x.olib_ketish) === bugun }
}
const posGuruhi = (x, bugun) => (!['vaqtinchalik', 'bron'].includes(x.holat) ? 'qarz' : String(x.olib_ketish) <= bugun ? 'bugun' : 'oldin')
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
            <XarajatPOS s={s} rahbar={rahbar} onYuborish={(b) => bajar(() => xarajatYarat({ ...b, kassadan: true }), rahbar ? 'Xarajat kassadan yozildi.' : "Xarajat kassadan yozildi (rahbar tasdig'ini kutadi).")} />
          )}
          {bolim === 'inkassatsiya' && (
            <InkassatsiyaPOS s={s} rahbarlar={s.rahbarlar} hamkasblar={s.hamkasblar || []} smenada={(s.xodimlar || []).map((x) => x.id)}
              onYuborish={(summa, izoh, k) => bajar(() => inkassatsiyaQil(k.rahbar ? { summa, izoh, rahbar: k.id } : { summa, izoh, kimga: k.id }),
                k.rahbar ? 'Inkassatsiya yozildi — rahbar Telegramda tasdiqlaydi.' : `Pul ${k.ism}ga topshirildi — u sanab, «Qabul qildim»ni bosadi.`)} />
          )}
          {bolim === 'zalog' && <ZalogTekshiruvi onOzgardi={yukla} onZakaz={onZakaz} />}
          {bolim === 'hisobot' && <SmenaKorsatkichlari s={s} />}
          {/* kanvas: chapda «Naqd pul hisobi», o'ngda «Pul harakatlari»; ostida «Kun yakuni» (yopishdan oldingi tekshiruvlar) */}
          {bolim === 'hisobot' && (
            <div className="kassa-smena-tor">
              <Hisobot h={s.hisobot} ochilgan={s.ochilgan} />
              <PulHarakatlari royxat={s.harakatlar || []} />
            </div>
          )}
          {bolim === 'hisobot' && <KunYakuni s={s} onBolim={onBolim} onChiq={() => ochOyna('chiqish')} onYop={() => ochOyna('yopish')} />}
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
        <Oyna sarlavha="Smenani yopish" onYop={yopOyna} keng>
          <SmenaYopish hisobda={s.mening_hisobim ?? s.hisobot.hisobdagi_qoldiq} tekshirilmagan={s.zalog_tekshirilmagan} rahbarlar={s.rahbarlar}
            terminalda={s.terminal_tizimda} xato={oynaXato} onQaytish={yopOyna}
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
      {/* Maket (KassaShisha): «Smena ochiq · Malika │ Naqd … Terminal … O'tkazma … │ amal» */}
      <span className="smena-holat ochiq"><i aria-hidden="true" />Smena ochiq · {s.ishtirokchilar.join(', ')}{s.filial ? ` · ${s.filial}` : ''}</span>
      {s.yuborilgan?.length > 0 && <span className="smena-kim">
        {s.yuborilgan.map((t) => <small key={t.id} className="malumot">{t.kimga} {som(t.summa)} ni hali tasdiqlamadi</small>)}</span>}
      <span className="smena-ajratgich" aria-hidden="true" />
      {s.men_ishtirokchi ? (
        <button type="button" className="smena-naqd" onClick={onHisobot} title="Sizdagi naqd (siz javob beradigan). Bosing — smena hisoboti">
          <small>Naqd</small><b className={s.mening_hisobim < 0 ? 'qizil' : undefined}>{som(s.mening_hisobim)}</b>
        </button>
      ) : (
        <button type="button" className="smena-naqd" onClick={onHisobot} title="Kassadagi naqd (tizim bo'yicha). Bosing — smena hisoboti">
          <small>Naqd</small><b>{som(s.hisobot.hisobdagi_qoldiq)}</b>
        </button>
      )}
      {!ixcham && (
        <span className="smena-usullar" title="Shu smenada kirgan pul">
          <span><small>Terminal</small><b>{som(s.usullar?.karta || 0)}</b></span>
          <span><small>O'tkazma</small><b>{som(s.usullar?.otkazma || 0)}</b></span>
          {['click', 'payme'].filter((u) => s.usullar?.[u] > 0).map((u) => <span key={u}><small>{USUL_NOMI[u]}</small><b>{som(s.usullar[u])}</b></span>)}
        </span>
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

// Kanvas (KassaYopishShisha): chapda tizimdagi summa, sanalgan naqd, farq, «Pul qayerda qoladi?», izoh;
// o'ngda raqamli klaviatura va «Smenani yopish» / «Qaytish». Yopilgan smenani faqat rahbar «Smenalar tarixi»da tuzatadi.
function SmenaYopish({ hisobda, tekshirilmagan, rahbarlar, terminalda, xato, onYuborish, onQaytish }) {
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const [surov, setSurov] = useState(false)
  const [rahbar, setRahbar] = useState('')  // bo'sh — pul seyfda qoladi
  const [terminal, setTerminal] = useState('')  // terminal hisobotidagi (kun yakuni chekidagi) summa (terminal orqali to'lov bo'lsa majburiy)
  const farq = summa === '' ? null : Number(summa) - hisobda
  const tFarq = terminal === '' ? null : Number(terminal) - terminalda
  const izohKerak = (farq !== null && farq !== 0) || (tFarq !== null && tFarq !== 0)
  const joylar = [['', 'Seyfda — ertangi smenaga'], ...rahbarlar.map((r) => [String(r.id), `Rahbarga: ${r.ism}`])]
  return (
    <div className="smena-yopish">
      <div className="smena-yopish-chap">
        <div className="sy-tizim"><span>Tizim bo'yicha kassada</span><b>{som(hisobda)}</b></div>
        <div className="sy-maydon">
          <span className="sy-yorliq">Sanalgan naqd</span>
          <div className="sy-summa" aria-live="polite"><b>{summa === '' ? '0' : guruhla(summa)}</b><span>so'm</span></div>
        </div>
        {farq !== null && (
          <p className={`sy-farq ${farq < 0 ? 'kam' : farq > 0 ? 'ortiq' : 'teng'}`} aria-live="polite">
            <span>Farq</span><b>{farq === 0 ? "Farq yo'q" : som(farq)}</b>
          </p>
        )}
        {tekshirilmagan > 0 && <p className="ogohlantirish">{tekshirilmagan} ta zalog tekshirilmagan — yopishdan oldin «Zaloglar» bo'limida belgilang.</p>}
        <div className="sy-maydon">
          <span className="sy-yorliq" id="sy-joy">Pul qayerda qoladi?</span>
          <div className="sy-joylar" role="radiogroup" aria-labelledby="sy-joy">
            {joylar.map(([v, nom]) => (
              <label key={v || 'seyf'} className={`sy-joy${rahbar === v ? ' on' : ''}`}>
                <input type="radio" className="ustki-input" name="sy-joy" checked={rahbar === v} onChange={() => setRahbar(v)} />{nom}
              </label>
            ))}
          </div>
          <small className="soz-mute">{rahbar ? 'Rahbar Telegramda (yoki ilovada) qabul qilganini tasdiqlaydi.' : 'Ertaga smenani ochgan xodim sanab qabul qiladi.'}</small>
        </div>
        {terminalda > 0 && (
          <label className="sy-maydon">
            <span className="sy-yorliq">Terminal hisoboti — kun yakuni chekidagi summa (tizimda {som(terminalda)})
              <Info nom="Terminal hisoboti">Kun oxirida terminaldan chiqariladigan yakuniy chekdagi jami summa. Tizimga yozilgan karta to'lovlari bilan
                solishtiriladi: farq bo'lsa — terminaldan o'tgan, lekin tizimga yozilmagan (yoki aksincha) to'lov bor.</Info></span>
            <SummaInput aria-label="Terminal hisoboti" value={terminal} onChange={(e) => setTerminal(e.target.value)} />
            {tFarq !== null && <small className={tFarq ? 'qizil' : 'soz-mute'}>{tFarq ? `Terminal farqi: ${som(tFarq)}` : "Terminal bo'yicha farq yo'q"}</small>}
          </label>
        )}
        <label className="sy-maydon">
          <span className="sy-yorliq">{izohKerak ? 'Izoh (farq sababi — majburiy)' : 'Izoh (ixtiyoriy)'}</span>
          <textarea rows={2} value={izoh} maxLength={300} placeholder="Masalan: 50 000 — taksi, chek seyfda" onChange={(e) => setIzoh(e.target.value)} />
        </label>
      </div>
      <div className="smena-yopish-ong">
        <Klaviatura qiymat={summa} onOzgar={setSumma} />
        <OynaXato matn={xato} />
        <div className="sy-tugmalar">
          <button className="pos-tugma" disabled={summa === '' || (terminalda > 0 && terminal === '') || (izohKerak && !izoh.trim())} onClick={() => setSurov(true)}>
            <NavIkona nom="chiqish" className="tugma-ikon" />Smenani yopish
          </button>
          {onQaytish && <button type="button" className="ikkinchi sy-qaytish" onClick={onQaytish}>Qaytish</button>}
        </div>
      </div>
      <p className="sy-izoh">Yopilgan smenani o'zgartirib bo'lmaydi — farqni faqat rahbar «Smenalar tarixi»da izoh bilan tuzatadi.</p>
      {surov && (
        <Tasdiq sarlavha="Smenani yopasizmi?" tugma="Smenani yopish"
          matn={`Smena yopiladi, keyin to'lov qabul qilib bo'lmaydi. Sanalgan naqd: ${som(Number(summa))}${rahbar ? ` — ${rahbarlar.find((r) => String(r.id) === rahbar)?.ism}ga topshiriladi, u Telegramda tasdiqlaydi` : ' — seyfda qoladi'}.`}
          onYop={() => setSurov(false)} onTasdiq={() => { setSurov(false); onYuborish(Number(summa), izoh.trim(), rahbar ? Number(rahbar) : undefined, terminal === '' ? undefined : Number(terminal)) }} />
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
  const [hozir] = useState(() => Date.now())  // avanssiz bron «N soatda bo'shaydi» hisobi uchun (render ichida Date.now emas)
  useEffect(() => { sozlamalar().then(setSoz).catch(() => {}) }, [])
  const chekRef = useRef(null)

  // Bitta so'rov, kesimsiz: vaqtinchalik va bron, qoldig'i bor (yoki 0 so'mlik vaqtinchalik — kassir uni «to'lovsiz»
  // tasdiqlaydi), olib ketish sanasi bo'yicha — filtr va tartib serverda
  const yukla = useCallback(() => tolovKutayotganlar(q).then(setRoyxat)
    .catch((e) => setXato(xatoMatni(e))), [q])
  useEffect(() => { const t = setTimeout(yukla, q ? 300 : 0); return () => clearTimeout(t) }, [yukla, q])

  // Kanvas: keng ekranda ro'yxatdagi birinchi zakaz (ko'rinish tartibida) o'zi tanlangan — chek darhol to'la turadi.
  // Telefon va planshetda tanlanmaydi: u yerda chek ro'yxat ostida va tanlov ro'yxatni yig'ib qo'yadi.
  const [keng, setKeng] = useState(() => window.matchMedia('(min-width: 1024px)').matches)
  useEffect(() => {
    const m = window.matchMedia('(min-width: 1024px)')
    const h = (e) => setKeng(e.matches)
    m.addEventListener('change', h)
    return () => m.removeEventListener('change', h)
  }, [])
  const birinchi = royxat && POS_GURUHLAR.flatMap(([g]) => royxat.filter((x) => posGuruhi(x, bugunIso()) === g))[0]
  const joriyId = tanlangan ?? (keng && !tolandi ? birinchi?.id : null)
  const z = royxat?.find((x) => x.id === joriyId)
  const qoldiq = z ? z.jami - z.tolangan : 0
  const avans = z?.holat === 'vaqtinchalik'
  // Maket: zakaz tanlanganda summa qoldiq bilan to'ldirilgan turadi (`avto`); klaviaturadagi birinchi raqam uni almashtiradi
  const [avto, setAvto] = useState(true)
  const kiritilgan = avto ? (qoldiq > 0 ? String(qoldiq) : '') : summa
  const yoz = (v) => { setAvto(false); setSumma(v) }
  const tanla = (id) => { setTanlangan(id); setSumma(''); setAvto(true); setXato(''); setXatoKod(''); setQoshildi(false); setTolandi(null) }
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
      await tolovQabul({ zakaz: z.id, tur: avans ? 'avans' : 'qoldiq', summa: Number(kiritilgan), usul })
      // To'liq to'landi va olib ketish kuni keldi — zakaz endi bron, keyingi qadam libosni berish
      // QA-16: faqat hali berilmagan zakaz (to'lovdan keyin «Bron»: vaqtinchalik avans bilan bronga o'tadi);
      // berilgan/qaytarilgan zakazning qoldig'i («kelmadi» o'tkazma) to'langanda berish yo'q
      setTolandi({ zakaz: z, summa: Number(kiritilgan), usul,
        berish: ['vaqtinchalik', 'bron'].includes(z.holat) && qoldiq - Number(kiritilgan) === 0 && String(z.olib_ketish) <= bugunIso() })
      setTanlangan(null); setSumma(''); setAvto(true)
      await Promise.all([yukla(), onTolandi?.()])
    } catch (e) { setXato(xatoMatni(e)); setXatoKod(e.response?.data?.kod || '') } finally { setBand(false) }
  }

  if (chek) return <Hujjat zakazId={chek} tur="kvitansiya" onYop={() => setChek(null)} />

  return (
    <div className="pos-ish">
      <section className={`blok jadval-panel pos-royxat${yigilgan ? ' yigilgan' : ''}`}>
        {/* Maket (KassaShisha): sarlavha belgi bilan, ostida butun enli qidiruv; ustunlar — Zakaz, Mijoz, Libos, Qoldiq */}
        <div className="jadval-asboblar pos-asboblar">
          <h3 className="panel-nom"><NavIkona nom="katalog" className="tugma-ikon" />To'lov kutayotgan zakazlar{royxat?.length > 0 && <span className="tab-son">{royxat.length}</span>}</h3>
          {/* faqat bir ustunli ekranda: yig'ilgan ro'yxatni qayta ochadi */}
          {z && <button type="button" className="ikkinchi kichik pos-boshqa" onClick={() => tanla(null)}>Boshqa zakaz</button>}
          <label className="qidiruv-maydon pos-qidiruv">
            <NavIkona nom="qidiruv" className="tugma-ikon" />
            <input type="search" className="jadval-qidiruv" placeholder="Zakaz raqami, mijoz ismi yoki telefon bo'yicha qidirish…" aria-label="Zakaz qidirish" value={q} onChange={(e) => setQ(e.target.value)} />
          </label>
        </div>
        {royxat === null && <p className="malumot jadval-bosh">Yuklanmoqda…</p>}
        {royxat && royxat.length === 0 && <p className="malumot jadval-bosh">{q ? `«${q}» bo'yicha zakaz topilmadi.` : "To'lov kutayotgan zakaz yo'q."}</p>}
        {royxat?.length > 0 && (
          <Tasma className="pos-zakazlar" pastki={40}>
            <div className="pos-jadval-bosh" aria-hidden="true"><span>Zakaz</span><span>Mijoz</span><span>Libos</span><span>Qoldiq</span></div>
            {POS_GURUHLAR.map(([g, nom]) => {
              const qatorlar = royxat.filter((x) => posGuruhi(x, bugunIso()) === g)
              if (!qatorlar.length) return null
              return (
                <div key={g} className="pos-guruh" role="group" aria-label={nom}>
                  <p className="pos-guruh-nom">{nom}<span className="tab-son">{qatorlar.length}</span></p>
                  {qatorlar.map((x) => {
                    const iz = posIzoh(x, g, bugunIso(), hozir)
                    return (
                      <button key={x.id} type="button" className={`pos-zakaz${x.id === joriyId ? ' tanlandi' : ''}${g === 'qarz' ? ' qarz' : ''}`} aria-pressed={x.id === joriyId} onClick={() => tanla(x.id)}
                        title={x.sotuvchi ? `Sotuvchi: ${x.sotuvchi}` : undefined}>
                        <span className="pos-zakaz-raqam">#{x.raqam}</span>
                        <span className="pos-zakaz-mijoz"><b>{x.mijoz}</b><small>{telefonYashir(x.telefon)}</small></span>
                        <span className="pos-zakaz-libos">
                          <span className="zakaz-eskiz">{x.rasm ? <img src={x.rasm} alt="" loading="lazy" /> : <LibosSiluet />}</span>
                          <span><b>{x.liboslar.join(', ') || '—'}</b>
                            <small className={iz.tur || undefined}>{iz.matn ?? <><IjaraSana dan={x.olib_ketish} gacha={x.qaytarish} />{iz.bugun && ' · bugun'}</>}</small></span>
                        </span>
                        <span className={`pos-zakaz-summa${g === 'qarz' ? ' qarz' : ''}`}><small>{x.holat === 'vaqtinchalik' ? 'Avans kerak' : g === 'qarz' ? 'Qarz' : 'Qoldiq'}</small><b>{som(x.jami - x.tolangan)}</b></span>
                      </button>
                    )
                  })}
                </div>
              )
            })}
          </Tasma>
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
            {/* Maket: «#13 · Ism» serif sarlavha, ostida artikul, keyin libos · o'lcham · holat */}
            <div className="pos-chek-bosh">
              <span className="pos-chek-rasm" aria-hidden="true">{z.rasm ? <img src={z.rasm} alt="" /> : <LibosSiluet />}</span>
              <div className="pos-chek-matn">
                <p className="varaq-kimga">#{z.raqam} · {z.mijoz}</p>
                {z.artikul && <small>{z.artikul}</small>}
                <span>{[z.liboslar.join(', '), z.olcham && `${z.olcham} o'lcham`, POS_HOLAT[z.holat] || z.holat].filter(Boolean).join(' · ')}</span>
              </div>
            </div>
            <table className="pos-hisob"><tbody>
              <tr><td>Ijara summasi:</td><td>{som(z.jami)}</td></tr>
              <tr><td>To'langan:</td><td>{som(z.tolangan)}</td></tr>
              <tr><td><b>{avans ? 'Avans (qoldiq):' : 'Qoldiq:'}</b></td><td><b>{som(qoldiq)}</b></td></tr>
            </tbody></table>
            {z.jami === 0 ? (
              <button className="pos-tugma" disabled={band} onClick={async () => {
                setXato(''); setBand(true)
                try { await tolovQabul({ zakaz: z.id, tur: 'avans', summa: 0, usul: 'naqd' }); setTanlangan(null); await Promise.all([yukla(), onTolandi?.()]) } catch (e) { setXato(xatoMatni(e)) } finally { setBand(false) }
              }}>Bronni tasdiqlash (to'liq chegirma — to'lov yo'q)</button>
            ) : null}
            {z.jami === 0 && xato && <p className="xato">{xato}</p>}
            {z.jami !== 0 && (<>
            {/* summa va «To'liq» bir qatorda (maket) */}
            <div className="pos-summa-qator">
              <Summa qiymat={kiritilgan} izoh={Number(kiritilgan) > qoldiq ? `Qoldiqdan oshib ketdi (${som(qoldiq)})` : null} />
              <div className="pos-tez">
                <button type="button" className="ikkinchi kichik" onClick={() => yoz(String(qoldiq))}>To'liq {guruhla(String(qoldiq))}</button>
                {avans && [50, 30].map((f) => (
                  <button key={f} type="button" className="ikkinchi kichik" onClick={() => yoz(String(Math.round((qoldiq * f) / 100 / 1000) * 1000))}>{f}%</button>
                ))}
              </div>
            </div>
            {/* oldindan to'ldirilgan summa ustiga yozilmaydi: birinchi raqam yangi summani boshlaydi */}
            <Klaviatura qiymat={avto ? '' : summa} onOzgar={yoz} />
            <p className="pos-yorliq" id="tolov-usuli-nom">To'lov usuli</p>
            <div className="pos-usullar" role="radiogroup" aria-labelledby="tolov-usuli-nom">
              {USULLAR.map(([k, nom]) => (
                <button key={k} type="button" role="radio" aria-checked={usul === k} className={usul === k ? 'tanlandi' : ''} onClick={() => setUsul(k)}>
                  <svg className="tugma-ikon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={USUL_IKON[k]} /></svg>{nom}
                </button>
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
            <button className="pos-tugma" disabled={band || !(Number(kiritilgan) > 0) || Number(kiritilgan) > qoldiq} onClick={qabul}>
              {!band && Number(kiritilgan) > 0 && <svg className="tugma-ikon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>}
              {band ? 'Qabul qilinmoqda…' : Number(kiritilgan) > 0 ? `${som(Number(kiritilgan))} qabul qilish` : 'Qabul qilish'}
            </button>
            <p className="pos-chek-izoh"><NavIkona nom="hujjat" className="tugma-ikon" />Qabul qilingach kvitansiya yaratiladi</p>
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
  // izoh ikki qatorga o'tsa summa o'rtasidan bo'linmasin («4 050 / 000 so'm») — summa ichida bo'linmaydigan bo'shliq
  const butun = (n) => som(n).replace(/ /g, ' ')
  return (
    <section className="dash-kpi kpi-filtrlar smena-kpi" aria-label="Smena ko'rsatkichlari">
      <KpiFiltr nom="Kassada naqd" son={som(h.hisobdagi_qoldiq)} ikon="kassa" rang="tilla" izoh={`kun boshida ${butun(h.kun_boshidagi_qoldiq)}`} />
      <KpiFiltr nom="Kirgan naqd" son={som(h.tushum)} ikon="tushum" rang="yashil" izoh="avans + qoldiq + jarima" />
      <KpiFiltr nom="Terminal" son={som(s.terminal_tizimda || 0)} ikon="terminal" rang="kok" izoh="chek bilan solishtiring" />
      <KpiFiltr nom="Chiqim" son={som(chiqim)} ikon="hamyon" rang="pushti"
        izoh={chiqim ? `xarajat ${butun(h.xarajatlar)} · topshirildi ${butun(h.vozvrat_va_inkassatsiya)}` : "bugun chiqim yo'q"} />
    </section>
  )
}

// Kanvas «Naqd pul hisobi»: har qator + yoki − belgisi bilan, kirim yashil, chiqim qizil; pastda «Hisobdagi qoldiq»
function Hisobot({ h, ochilgan }) {
  const qatorlar = [
    ['Kun boshidagi qoldiq', h.kun_boshidagi_qoldiq, ''],
    ['+ Kirgan pul (avans, qoldiq, jarima)', h.tushum, '+'], ['+ Olingan pul zaloglar', h.olingan_zaloglar, '+'],
    ['− Qaytarilgan zaloglar', h.qaytarilgan_zaloglar, '−'], ['− Xarajatlar', h.xarajatlar, '−'],
    ['− Pulni qaytarish va topshirish', h.vozvrat_va_inkassatsiya, '−'],
  ]
  return (
    <section className="blok kassa-panel kassa-daftar" aria-label="Naqd pul hisobi">
      <div className="kassa-panel-bosh"><h3><NavIkona nom="hujjat" className="tugma-ikon" />Naqd pul hisobi</h3>
        {ochilgan && <span className="malumot">smena {soatMatni(ochilgan)} dan</span>}</div>
      {qatorlar.map(([n, v, b]) => (
        <div key={n} className="kassa-satr"><span>{n}</span>
          <span className={v && b === '+' ? 'kassa-kirim' : v && b === '−' ? 'kassa-chiqim' : undefined}>{v && b ? `${b}${guruhla(v)}` : guruhla(v)}</span></div>
      ))}
      <div className="kassa-final"><span>Hisobdagi qoldiq</span><b>{som(h.hisobdagi_qoldiq)}</b></div>
      {Object.keys(h.sotuvchilar).length > 0 && (
        <p className="kassa-kirimlar">Kirimlar: {Object.entries(h.sotuvchilar).map(([k, v]) => <span key={k}>{k} <b>{som(v)}</b></span>)}</p>
      )}
      <p className="malumot">Terminal va o'tkazma kassadagi naqdga kirmaydi — ular bank orqali keladi.</p>
    </section>
  )
}

// Kanvas «Pul harakatlari»: smenadagi har bir to'lov — vaqt, tavsif (kim, holat), usul, summa (+ kirim / − chiqim)
function PulHarakatlari({ royxat }) {
  return (
    <section className="blok kassa-panel" aria-label="Pul harakatlari">
      <div className="kassa-panel-bosh"><h3><NavIkona nom="almashtir" className="tugma-ikon" />Pul harakatlari</h3><span className="malumot">{royxat.length} ta</span></div>
      {royxat.length === 0 ? <p className="malumot">Bu smenada hali pul harakati yo'q.</p> : (
        <Sahifali royxat={royxat} hajm={8}>{(qism) => (
          <div className="hisobot-ora">
            <table className="kassa-jadval harakat-jadval">
              <thead><tr><th>Vaqt</th><th>Tavsif</th><th>Turi</th><th className="ong">Summa</th></tr></thead>
              <tbody>
                {qism.map((x) => (
                  <tr key={x.id}>
                    <td><b>{soatMatni(x.vaqt)}</b></td>
                    <td><span className="kassa-ikki-qator"><span>{x.tavsif}</span><small>{x.xodim}{x.holat ? ` · ${x.holat}` : ''}</small></span></td>
                    <td><span className="kassa-tur">{x.usul_nomi}</span></td>
                    <td className={`ong ${x.usul === 'naqd' ? (x.summa < 0 ? 'kassa-chiqim' : 'kassa-kirim') : ''}`}><b>{x.summa > 0 ? '+' : '−'}{guruhla(Math.abs(x.summa))}</b></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}</Sahifali>
      )}
    </section>
  )
}

// Xarajat moddalari belgilari (kanvas): tozalash — tomchi, ta'mir — kalit, kommunal — chaqmoq, reklama — karnay,
// transport — yuk mashinasi, boshqa — uch nuqta; salonning o'z moddasi — yorliq
const MODDA_IKON = {
  tozalash: 'M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11Z',
  tamir: 'M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9Z',
  kommunal: 'M13 2 4 14h7l-1 8 9-12h-7l1-8Z',
  reklama: 'M3 11v2a1 1 0 0 0 1 1h2l5 4V6l-5 4H4a1 1 0 0 0-1 1ZM15 9a3 3 0 0 1 0 6M18 6a7 7 0 0 1 0 12',
  transport: 'M3 6h11v9H3zM14 9h4l3 3v3h-7M7 19a1.5 1.5 0 1 0 0-3a1.5 1.5 0 0 0 0 3M17 19a1.5 1.5 0 1 0 0-3a1.5 1.5 0 0 0 0 3',
  boshqa: 'M6 12h.01M12 12h.01M18 12h.01',
}
const ModdaBelgi = ({ kod }) => (
  <svg className="modda-belgi" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={MODDA_IKON[kod] || 'M3 12V4h8l10 10-8 8ZM7.5 7.5h.01'} />
  </svg>
)
const soatMatni = (v) => (v ? new Date(v).toTimeString().slice(0, 5) : '')
const bosHarf = (ism) => String(ism || '?').trim().split(/\s+/).slice(0, 2).map((x) => x[0]).join('').toUpperCase()
// Kanvas «hisob» bloki: chapda nom, o'ngda summa; oxirgisi tilla
function HisobSatrlari({ qatorlar }) {
  return (
    <div className="kassa-hisob">
      {qatorlar.map(([nom, v, urg], i) => (
        <div key={nom} className="kassa-satr"><span>{nom}</span>{urg || i === qatorlar.length - 1 ? <b className="kassa-tilla">{som(v)}</b> : <span>{som(v)}</span>}</div>
      ))}
    </div>
  )
}

// Xarajat (kanvas): chapda modda plitkalari (belgi bilan) va izoh; o'ngda summa, klaviatura, «kassada naqd → yozilgandan keyin»;
// ostida bugungi xarajatlar. Summa kassadagi naqddan oshsa — yozib bo'lmaydi.
function XarajatPOS({ s, rahbar, onYuborish }) {
  const [modda, setModda] = useState('transport')
  const [moddalar, setModdalar] = useState([])
  useEffect(() => {
    xarajatModdalari().then((m) => setModdalar(m.filter((x) => !x.standart || KASSA_MODDALARI.includes(x.kod)))).catch(() => {})
  }, [])
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const naqd = s.mening_hisobim ?? s.hisobot.hisobdagi_qoldiq
  const n = Number(summa) || 0
  const kop = n > naqd
  const nom = moddalar.find((m) => m.kod === modda)?.nomi || 'Xarajat'
  const bugungi = (s.harakatlar || []).filter((h) => h.tur === 'xarajat')
  return (
    <>
      <div className="kassa-ikki">
        <section className="blok kassa-panel" aria-label="Xarajat moddasi">
          <div className="kassa-panel-bosh"><h3><NavIkona nom="hujjat" className="tugma-ikon" />Xarajat moddasi</h3><span className="malumot">bittasini tanlang</span></div>
          <div className="kassa-moddalar" role="radiogroup" aria-label="Xarajat turi">
            {moddalar.map((m) => (
              <button key={m.kod} type="button" role="radio" aria-checked={modda === m.kod} className={modda === m.kod ? 'tanlandi' : ''} onClick={() => setModda(m.kod)}>
                <ModdaBelgi kod={m.kod} />{m.nomi}
              </button>
            ))}
          </div>
          <label className="kassa-yorliq">Izoh
            <textarea className="kassa-maydon" value={izoh} maxLength={300} placeholder="Nima uchun? Masalan: Bella ustaxonaga olib borildi" onChange={(e) => setIzoh(e.target.value)} />
          </label>
        </section>
        <section className="blok kassa-panel" aria-label="Xarajat">
          <div className="kassa-panel-bosh"><h3><ModdaBelgi kod={modda} />{nom}</h3><span className="holat vaqtinchalik">kassadan chiqadi</span></div>
          <Summa qiymat={summa} />
          <Klaviatura qiymat={summa} onOzgar={setSumma} />
          <HisobSatrlari qatorlar={[['Kassada naqd', naqd], ['Yozilgandan keyin', naqd - n]]} />
          {kop && <p className="xato">Kassadagi naqddan ko'p bo'lishi mumkin emas.</p>}
          <button className="pos-tugma" disabled={!(n > 0) || kop}
            onClick={() => onYuborish({ modda, summa: n, izoh }).then((ok) => ok && (setSumma(''), setIzoh('')))}>
            {n > 0 ? `${guruhla(n)} so'm xarajatni yozish` : 'Xarajatni yozish'}
          </button>
          {!rahbar && <p className="izoh-q"><NavIkona nom="yordam" className="tugma-ikon" /><span>Xodim yozgan xarajat rahbar tasdiqlaguncha «kutilmoqda» bo'lib turadi.</span></p>}
        </section>
      </div>
      {bugungi.length > 0 && (
        <section className="blok kassa-panel" aria-label="Bugungi xarajatlar">
          <div className="kassa-panel-bosh"><h3><NavIkona nom="tarix" className="tugma-ikon" />Bugungi xarajatlar</h3>
            <span className="malumot">jami {som(bugungi.reduce((a, h) => a - h.summa, 0))}</span></div>
          <div className="hisobot-ora">
            <table className="kassa-jadval">
              <thead><tr><th>Vaqt</th><th>Modda</th><th>Izoh</th><th>Kim</th><th className="ong">Summa</th><th>Holat</th></tr></thead>
              <tbody>
                {bugungi.map((h) => (
                  <tr key={h.id}>
                    <td><b>{soatMatni(h.vaqt)}</b></td>
                    <td>{h.tavsif.replace(/^Xarajat · /, '')}</td>
                    <td className="kassa-kesik">{h.izoh || '—'}</td>
                    <td>{h.xodim}</td>
                    <td className="ong"><b>{guruhla(-h.summa)}</b></td>
                    <td><span className={`holat ${h.holat === 'tasdiqlandi' ? 'bron' : h.holat.startsWith('rad') ? 'qarz' : 'vaqtinchalik'}`}>{h.holat || '—'}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  )
}

// FT-12.6: rahbarga topshirilgan naqd pul — alohida chiqim, tushum va xarajatga kirmaydi. Rahbar Telegramda tasdiqlaydi.
// Smenadagi hamkasbga ham berish mumkin: pul kassada qoladi, faqat uning hisobiga o'tadi (u sanab qabul qiladi).
// Kanvas: qabul qiluvchilar avatar va roli bilan ro'yxatda; o'ngda «Hammasi» tugmasi va «Sizda / Topshiriladi / Keyin sizda»;
// ostida oxirgi topshirishning qadamlari (so'rov → sanaldi → tasdiqlandi).
function InkassatsiyaPOS({ s, rahbarlar, hamkasblar, smenada, onYuborish }) {
  const rahbarIdlar = new Set(rahbarlar.map((r) => r.id))
  const tanlov = [...rahbarlar.map((r) => ({ ...r, rahbar: true, kalit: `r:${r.id}` })),
    ...hamkasblar.filter((x) => !rahbarIdlar.has(x.id)).map((x) => ({ ...x, rahbar: false, kalit: `x:${x.id}` }))]
  // bitta rahbar bo'lsa — odatdagidek o'zi tanlangan (inkassatsiya)
  const [kalit, setKalit] = useState(rahbarlar.length === 1 ? `r:${rahbarlar[0].id}` : tanlov.length === 1 ? tanlov[0].kalit : '')
  const [summa, setSumma] = useState('')
  const [izoh, setIzoh] = useState('')
  const kimga = tanlov.find((t) => t.kalit === kalit)
  const sizda = s.mening_hisobim ?? s.hisobot.hisobdagi_qoldiq
  const n = Number(summa) || 0
  const kop = n > sizda
  if (!tanlov.length) return <section className="blok pos-tor"><p className="malumot">Pul topshiradigan rahbar yoki smenadagi hamkasb yo'q.</p></section>
  const oxirgi = s.topshiriqlarim?.[0]
  return (
    <>
      <div className="kassa-ikki">
        <section className="blok kassa-panel" aria-label="Kimga topshirasiz">
          <div className="kassa-panel-bosh"><h3><NavIkona nom="mijozlar" className="tugma-ikon" />Kimga topshirasiz?</h3></div>
          <div className="kassa-oluvchilar" role="radiogroup" aria-label="Kimga">
            {tanlov.map((t) => (
              <button key={t.kalit} type="button" role="radio" aria-checked={kalit === t.kalit} className={`oluvchi${kalit === t.kalit ? ' tanlandi' : ''}`}
                onClick={() => setKalit(t.kalit)}>
                <span className="oluvchi-radio" aria-hidden="true" />
                <span className="oluvchi-avatar" aria-hidden="true">{bosHarf(t.ism)}</span>
                <span className="oluvchi-matn"><b>{t.ism}</b>
                  <small>{t.rahbar ? 'Rahbar · Telegram orqali tasdiqlaydi' : smenada.includes(t.id) ? 'Smenada · pul kassada qoladi' : "Hamkasb · berilganda smenaga qo'shiladi"}</small></span>
              </button>
            ))}
          </div>
          {kimga && (
            <p className="izoh-q"><NavIkona nom="yordam" className="tugma-ikon" /><span>{kimga.rahbar
              ? "Pul kassadan chiqadi — rahbar sanab, Telegramda tasdiqlaydi; shundan keyin smenangizdan ayiriladi."
              : `Pul kassada qoladi: sizning hisobingizdan ${kimga.ism}ning hisobiga o'tadi${smenada.includes(kimga.id) ? '' : ` (${kimga.ism} smenaga qo'shiladi)`}. ${kimga.ism} sanab, «Qabul qildim»ni bosadi.`}</span></p>
          )}
          <label className="kassa-yorliq">Izoh
            <textarea className="kassa-maydon kichik" value={izoh} maxLength={300} placeholder="Masalan: kunduzgi naqdni rahbarga topshirish" onChange={(e) => setIzoh(e.target.value)} />
          </label>
        </section>
        <section className="blok kassa-panel" aria-label="Topshiriladigan summa">
          <div className="kassa-panel-bosh"><h3><NavIkona nom="almashtir" className="tugma-ikon" />Topshiriladigan summa</h3>
            {sizda > 0 && <button type="button" className="ikkinchi kichik" onClick={() => setSumma(String(sizda))}>Hammasi · {guruhla(sizda)}</button>}</div>
          <Summa qiymat={summa} />
          <Klaviatura qiymat={summa} onOzgar={setSumma} />
          <HisobSatrlari qatorlar={[['Sizda', sizda], ['Topshiriladi', n], ['Keyin sizda', sizda - n]]} />
          {kop && <p className="xato">Sizdagi naqddan ko'p topshirib bo'lmaydi.</p>}
          <button className="pos-tugma" disabled={!kimga || !(n > 0) || kop}
            onClick={() => onYuborish(n, izoh, kimga).then((ok) => ok && (setSumma(''), setIzoh('')))}>
            {/* C-27: hamkasbga berish inkassatsiya emas — pul kassada qoladi */}
            {!kimga ? 'Topshirish' : kimga.rahbar ? `${kimga.ism}ga topshirish so'rovini yuborish` : `${kimga.ism}ga berish`}
          </button>
        </section>
      </div>
      {oxirgi && (
        <section className="blok kassa-panel" aria-label="Oxirgi topshirish">
          <div className="kassa-panel-bosh"><h3><NavIkona nom="bajarildi" className="tugma-ikon" />Oxirgi topshirish</h3>
            <span className="malumot">{som(oxirgi.summa)} · {oxirgi.kimga}ga</span></div>
          <ol className="kassa-qadamlar">
            <li className="bajarildi"><span className="qadam-doira" aria-hidden="true"><NavIkona nom="xabar" /></span>
              <span><b>So'rov</b><small>{oxirgi.kimdan} yubordi · {soatMatni(oxirgi.vaqt)}</small></span></li>
            <li className={oxirgi.holat === 'qabul' ? 'bajarildi' : ''}><span className="qadam-doira" aria-hidden="true"><NavIkona nom="kassa" /></span>
              <span><b>Sanaldi</b><small>{oxirgi.holat === 'qabul' ? `${oxirgi.kimga}: ${som(oxirgi.qabul_summa)}` : `${oxirgi.kimga} sanamoqda`}</small></span></li>
            <li className={oxirgi.holat === 'qabul' ? 'bajarildi' : ''}><span className="qadam-doira" aria-hidden="true"><NavIkona nom="bajarildi" /></span>
              <span><b>Tasdiqlandi</b><small>{oxirgi.holat === 'qabul' ? 'smenangizdan ayirildi' : 'kutilmoqda'}</small></span></li>
          </ol>
        </section>
      )}
    </>
  )
}

// FT-12.5: kun oxirida salonda saqlanayotgan hujjat va tillo zaloglar «joyida» deb belgilanadi.
// Kanvas: tepada 3 ko'rsatkich (pul, hujjat, buyum), chapda jadval (belgilash katakchasi, zakaz, zalog, qaytarish sharti,
// tekshiruv), o'ngda tanlangan zalog tafsiloti va «joyida emas» (izoh bilan).
const ZALOG_TEKSHIRUV = { true: ['joyida ✓', 'yashil'], false: ['joyida emas', 'qizil'], null: ['tekshirilmagan', 'ogoh'] }
function ZalogTekshiruvi({ onOzgardi, onZakaz }) {
  const [royxat, setRoyxat] = useState(null)
  const [pul, setPul] = useState(null)
  const [tanlangan, setTanlangan] = useState(null)
  const [izoh, setIzoh] = useState('')
  const [xato, setXato] = useState('')
  useEffect(() => { kassaZaloglar().then((r) => { setRoyxat(r.zaloglar); setPul(r.pul || null) }).catch((e) => setXato(xatoMatni(e))) }, [])
  const belgila = async (z, joyida) => {
    setXato('')
    try {
      setRoyxat((await zalogBelgila({ zalog: z.id, joyida, izoh: joyida ? '' : izoh })).zaloglar)
      if (!joyida) setIzoh('')
      onOzgardi?.()
    } catch (e) { setXato(xatoMatni(e)) }
  }
  const hujjat = (royxat || []).filter((z) => z.turi === 'hujjat')
  const tillo = (royxat || []).filter((z) => z.turi === 'tillo')
  const tekshirildi = (royxat || []).filter((z) => z.joyida === true).length
  const z = (royxat || []).find((x) => x.id === tanlangan) || royxat?.[0]
  const tekshiruv = (x) => ZALOG_TEKSHIRUV[String(x.joyida ?? null)]
  return (
    <>
      <section className="dash-kpi kpi-filtrlar zalog-kpi" aria-label="Zalog ko'rsatkichlari">
        <KpiFiltr nom="Pul zaloglar" son={som(pul?.jami || 0)} ikon="hamyon" rang="tilla" izoh={`${pul?.soni || 0} ta · seyfda`} />
        <KpiFiltr nom="Hujjatlar" son={hujjat.length} ikon="hujjat" rang="kok" izoh="pasport, guvohnoma" />
        <KpiFiltr nom="Buyumlar" son={tillo.length} ikon="uzuk" rang="pushti" izoh="tillo buyumlar" />
      </section>
      <div className={`kassa-asosiy${z ? '' : ' bitta'}`}>
        <section className="blok kassa-panel" aria-label="Saqlanayotgan zaloglar">
          <div className="kassa-panel-bosh"><h3><NavIkona nom="qalqon" className="tugma-ikon" />Saqlanayotgan zaloglar</h3>
            {royxat?.length > 0 && <span className={`holat ${tekshirildi === royxat.length ? 'bron' : 'vaqtinchalik'}`}>joyida tekshirildi: {tekshirildi} / {royxat.length}</span>}</div>
          {xato && <p className="xato">{xato}</p>}
          {royxat === null && !xato && <p className="malumot">Yuklanmoqda…</p>}
          {royxat && royxat.length === 0 && <p className="malumot">Salonda saqlanayotgan hujjat yoki tillo zalog yo'q.</p>}
          {royxat?.length > 0 && (
            <Sahifali royxat={royxat} hajm={10}>{(qism) => (
              <div className="hisobot-ora">
                <table className="kassa-jadval zalog-jadval">
                  <thead><tr><th><span className="sr-only">Joyida</span></th><th>Zakaz · mijoz</th><th>Zalog</th><th>Qaytarish sharti</th><th>Tekshirildi</th></tr></thead>
                  <tbody>
                    {qism.map((x) => (
                      <tr key={x.id} className={z?.id === x.id ? 'tanlandi' : undefined}>
                        <td><input type="checkbox" className="zalog-belgi" checked={x.joyida === true} aria-label={`#${x.zakaz_raqami} ${x.mijoz} — joyida`}
                          onChange={() => (x.joyida === true ? setTanlangan(x.id) : belgila(x, true))} /></td>
                        <td><button type="button" className="zalog-tugma" onClick={() => setTanlangan(x.id)}><b>#{x.zakaz_raqami}</b><span>{x.mijoz}</span></button></td>
                        <td><span className="kassa-ikki-qator"><span>{x.turi_nomi || x.turi}</span><small>{x.tavsif}</small></span></td>
                        <td className="zalog-shart">{x.shart}</td>
                        <td><span className={`zalog-tek ${tekshiruv(x)[1]}`}>{tekshiruv(x)[0]}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}</Sahifali>
          )}
          <p className="izoh-q"><NavIkona nom="yordam" className="tugma-ikon" /><span>Smena yopilishidan oldin har bir zalogni seyfda ko'rib, «joyida» deb belgilang.
            Zalog ijara tushumiga kirmaydi — u mijozning puli yoki buyumi.</span></p>
        </section>
        {z && (
          <section className="blok kassa-panel" aria-label="Zalog tafsiloti">
            <div className="kassa-panel-bosh"><h3><NavIkona nom="qalqon" className="tugma-ikon" />#{z.zakaz_raqami} zalog</h3>
              <span className={`zalog-tek ${tekshiruv(z)[1]}`}>{tekshiruv(z)[0]}</span></div>
            <div className="kassa-satr"><span>Mijoz</span><span>{z.mijoz}</span></div>
            <div className="kassa-satr"><span>Turi</span><span>{z.turi_nomi || z.turi}</span></div>
            <div className="kassa-satr"><span>Tavsif</span><span>{z.tavsif}</span></div>
            {z.olingan && <div className="kassa-satr"><span>Olingan</span><span>{mahalliyVaqt(z.olingan)}</span></div>}
            <div className="kassa-satr"><span>Saqlanadi</span><span>{z.yorliq ? `Seyf · ${z.yorliq}` : 'Seyf (kassa)'}</span></div>
            <div className="kassa-ajratgich" role="separator" />
            <div className="kassa-satr"><span>Qaytarish sharti</span><span>{z.shart}</span></div>
            <div className="zalog-amallar">
              <button type="button" className={z.joyida === true ? 'kichik' : 'ikkinchi kichik'} onClick={() => belgila(z, true)}>Joyida</button>
              <input placeholder="Yo'q bo'lsa izoh" aria-label="Yo'q bo'lsa izoh" value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} />
              <button type="button" className="ikkinchi kichik" disabled={!izoh.trim()} onClick={() => belgila(z, false)}>Yo'q</button>
            </div>
            {onZakaz && <button type="button" className="ikkinchi kassa-toliq" onClick={() => onZakaz(z.zakaz_id)}>Zakazni ochish</button>}
          </section>
        )}
      </div>
    </>
  )
}

// FT-12.11: yopilgan smenani faqat rahbar o'zgartiradi (qayta sanash natijasi); o'zgarish jurnalga yoziladi.
// Kanvas: chapda jadval (sana, xodim, vaqt, hisobda, sanaldi, farq, holat), o'ngda tanlangan smena tafsiloti va «Tuzatish».
// «Faqat farqlilar» — kassa, terminal yoki seyf farqi bilan yopilgan smenalar (serverda); xodim bo'yicha — sahifada.
const farqBelgi = (f) => (f == null ? ['—', ''] : f === 0 ? ["Farq yo'q", 'yashil'] : f < 0 ? [som(f), 'qizil'] : [`+${som(f)}`, 'ogoh'])
// «7 noyabr» (shu yil), «30 dekabr 2025» (boshqa yil)
const kunOyMatni = (iso) => { const [y, m, d] = String(iso).split('-').map(Number); return `${d} ${OYLAR[m - 1].toLowerCase()}${y !== new Date().getFullYear() ? ` ${y}` : ''}` }
function YopilganSmenalar() {
  const [royxat, setRoyxat] = useState(null)
  const [farqli, setFarqli] = useState(false)
  const [xodim, setXodim] = useState('')
  const [tanlangan, setTanlangan] = useState(null)
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
  const xodimlar = [...new Set((royxat || []).map((s) => s.ochgan))]
  const korinadi = (royxat || []).filter((s) => !xodim || s.ochgan === xodim)
  const t = korinadi.find((s) => s.id === tanlangan) || korinadi.find((s) => s.yopilgan) || korinadi[0]
  return (
    <>
      <div className="kassa-asosiy">
        <section className="blok kassa-panel" aria-label="Smenalar tarixi">
          <div className="kassa-panel-bosh"><h3><NavIkona nom="tarix" className="tugma-ikon" />Smenalar</h3>
            <div className="kassa-filtr">
              <button type="button" className="bugun-chip" aria-pressed={farqli} onClick={() => { setXabar({ turi: '', matn: '' }); setFarqli(!farqli) }}>Faqat farqlilar</button>
              {xodimlar.length > 1 && (
                <select className="kichik-tanlov" aria-label="Xodim" value={xodim} onChange={(e) => setXodim(e.target.value)}>
                  <option value="">Xodim: hammasi</option>
                  {xodimlar.map((x) => <option key={x} value={x}>{x}</option>)}
                </select>
              )}
            </div>
          </div>
          {xabar.matn && <p className={xabar.turi === 'xato' ? 'xato' : 'malumot'} role="status">{xabar.matn}</p>}
          {royxat && korinadi.length === 0 && <p className="malumot">{farqli ? "Farq bilan yopilgan smena yo'q." : "Smena yo'q."}</p>}
          {korinadi.length > 0 && (
            <Sahifali royxat={korinadi} hajm={10} kalit={`${farqli}|${xodim}`}>{(qism) => (
              <div className="hisobot-ora">
                <table className="kassa-jadval tarix-jadval">
                  <thead><tr><th>Sana</th><th>Xodim</th><th>Vaqt</th><th className="ong">Hisobda</th><th className="ong">Sanaldi</th><th>Farq</th><th>Holat</th></tr></thead>
                  <tbody>
                    {qism.map((s) => {
                      const [fm, fc] = farqBelgi(s.yopilgan ? s.farq : null)
                      return (
                        <tr key={s.id} className={`bosiladi${t?.id === s.id ? ' tanlandi' : ''}`} onClick={() => setTanlangan(s.id)}>
                          <td><button type="button" className="tarix-sana" aria-pressed={t?.id === s.id}>{kunOyMatni(s.sana)}</button></td>
                          <td>{s.ochgan}{s.filial ? <small className="malumot"> · {s.filial}</small> : ''}</td>
                          <td className="malumot">{soatMatni(s.ochilgan)} – {s.yopilgan ? soatMatni(s.yopilgan) : ''}</td>
                          <td className="ong">{s.hisobdagi_qoldiq == null ? '—' : guruhla(s.hisobdagi_qoldiq)}</td>
                          <td className="ong">{s.fakt_qoldiq == null ? '—' : guruhla(s.fakt_qoldiq)}</td>
                          <td>{fc ? <span className={`kassa-pill ${fc}`}>{fm}</span> : <span className="malumot">—</span>}</td>
                          <td><span className={`holat ${s.yopilgan ? 'yopilgan' : 'vaqtinchalik'}`}>{s.yopilgan ? 'Yopilgan' : 'Ochiq'}</span></td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}</Sahifali>
          )}
        </section>
        {t && (
          <section className="blok kassa-panel" aria-label="Smena tafsiloti">
            <div className="kassa-panel-bosh"><h3><NavIkona nom="kalendar" className="tugma-ikon" />{kunOyMatni(t.sana)} · {t.ochgan}</h3>
              <span className={`holat ${t.yopilgan ? 'yopilgan' : 'vaqtinchalik'}`}>{t.yopilgan ? 'Yopilgan' : 'Ochiq'}</span></div>
            <div className="kassa-satr"><span>Vaqt</span><b>{soatMatni(t.ochilgan)} – {t.yopilgan ? soatMatni(t.yopilgan) : 'hozir'}</b></div>
            <div className="kassa-satr"><span>Kun boshida</span><b>{som(t.boshlangich_qoldiq)}</b></div>
            {t.yopilgan && <>
              <div className="kassa-satr"><span>Hisobda</span><b>{som(t.hisobdagi_qoldiq)}</b></div>
              <div className="kassa-satr"><span>Sanaldi</span><b>{som(t.fakt_qoldiq)}</b></div>
              <div className="kassa-satr"><span>Farq</span><b className={t.farq < 0 ? 'kassa-chiqim' : t.farq > 0 ? 'kassa-ogoh' : 'kassa-kirim'}>{t.farq ? som(t.farq) : "farq yo'q"}</b></div>
            </>}
            {!!t.terminal_farq && <div className="kassa-satr"><span>Terminal farqi</span><b className="kassa-chiqim">{som(t.terminal_farq)}</b></div>}
            {!!t.seyf_farq && <div className="kassa-satr"><span>Seyf farqi (ochishda)</span><b className="kassa-chiqim">{som(t.seyf_farq)}</b></div>}
            {t.zalog_tekshirilmagan > 0 && <div className="kassa-satr"><span>Zalog tekshirilmagan</span><b className="kassa-ogoh">{t.zalog_tekshirilmagan} ta</b></div>}
            {t.zalog_yoq > 0 && <div className="kassa-satr"><span>Zalog joyida emas</span><b className="kassa-chiqim">{t.zalog_yoq} ta</b></div>}
            {(t.izoh || t.ochish_izohi) && (
              <p className="izoh-q kassa-izoh-blok"><NavIkona nom="yordam" className="tugma-ikon" /><span>{t.izoh}{t.izoh && t.ochish_izohi ? ' · ' : ''}{t.ochish_izohi && `ochishda: ${t.ochish_izohi}`}</span></p>
            )}
            {t.yopilgan
              ? <button type="button" className="ikkinchi kassa-toliq" onClick={() => setTuzat(t)}>Tuzatish</button>
              : <p className="malumot">Smena hali ochiq — yopilganda sanalgan summa va farq shu yerda chiqadi.</p>}
            {t.yopilgan && <p className="malumot">Tuzatish — qayta sanash natijasi; har o'zgarish jurnalda qayd etiladi.</p>}
          </section>
        )}
      </div>
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

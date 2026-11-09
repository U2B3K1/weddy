import { useCallback, useEffect, useState } from 'react'
import Tasdiq from '../components/Tasdiq'
import { boglandim, boshEkran, chegirmaMiqdori, chegirmaQaror, guruhla, qarzdorlar, sanaMatni, som, xarajatQaror, xatoMatni, zakazlarRoyxat, zakazTafsilot } from '../api'
import SummaInput from '../components/SummaInput'
import { Belgi, Qatorlar } from '../components/ZakazQatorlari'
import KpiFiltr from '../components/KpiFiltr'
import NavIkona from '../components/NavIkona'
import { BoshAmal, BoshXulosa } from '../components/BoshJoy'

// FT-1.2: bosh sahifa. «Bugungi ishlar» — har tur alohida karta (qarorlar, bugun olib ketadi, qaytaradi, kechikkan,
// qo'ng'iroq, qarzdorlar, qoldiq): faqat ish bor bo'lsa chiqadi; xuddi shu turlar qo'ng'iroqchada ham (A-08, A-09).
// `yuqori` — rahbar dashbordi: (bugungiIshlar) => <Dashbord orta={…} />, panel kun varaqasi va grafiklar orasiga qo'yiladi.
// `tab` — qo'ng'iroqchadan kelgan tur ({ tab, n }): o'sha karta belgilanadi va unga suriladi (A-09).
export default function BoshEkran({ onZakaz, onKassa, onBolim, rahbar, yuqori, tab: boshTab, pulOladi = true }) {
  const [d, setD] = useState(null)
  const [xato, setXato] = useState('')
  const [qarz, setQarz] = useState(null)
  const [qoldiqlar, setQoldiqlar] = useState([])

  // Rahbarga — qarorlar va qarzdorlar; xodimlarga — kundalik ishlar (olib ketish, qaytarish, qo'ng'iroq, qoldiq)
  const yukla = useCallback(() => {
    if (rahbar) {
      qarzdorlar().then((q) => { setQarz(q); setD((eski) => eski || {}) }).catch((e) => setXato(xatoMatni(e)))
    } else {
      boshEkran().then(setD).catch((e) => setXato(xatoMatni(e)))
      // avans olingan, libos hali berilmagan — qolgan summa libos berilganda olinadi (Kassa «To'lov qabul» bilan bir xil manba)
      zakazlarRoyxat({ holat: 'tolov_kutmoqda' })
        .then((r) => setQoldiqlar(r.filter((z) => z.holat === 'bron' && z.qoldiq > 0))).catch(() => {})
    }
  }, [rahbar])
  useEffect(() => { yukla() }, [yukla])
  // Qo'ng'iroqchadan: kerakli tab (App komponentni key bilan qayta ochadi) va panel ko'z oldida — sahifa tepasida qolib ketmasin
  const tanlanganTur = boshTab?.tab || null
  useEffect(() => {
    if (!tanlanganTur) return undefined
    const t = setTimeout(() => (document.getElementById(`ish-${tanlanganTur}`) || document.querySelector('.bugungi-ishlar'))
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 400)
    return () => clearTimeout(t)
  }, [tanlanganTur])
  const [bugunMs] = useState(() => Date.now())  // kechikkan kunlarini sanash uchun (render ichida Date chaqirilmasin)

  if (!rahbar) {
    return <XodimBosh d={d} xato={xato} qoldiqlar={qoldiqlar} pulOladi={pulOladi} onZakaz={onZakaz} onKassa={onKassa} onBolim={onBolim}
      onYangila={yukla} boshTab={boshTab} bugunMs={bugunMs} />
  }

  // Bugungi ishlar — har tur alohida karta (faqat ish bor bo'lsa chiqadi). Qo'ng'iroqchadagi xabarlar ham shu turlar.
  const eslatmaSoni = d?.eslatmalar ? d.eslatmalar.filter((e) => !e.boglangan).length : 0
  const kun = (iso) => Math.max(1, Math.floor((bugunMs - new Date(`${iso}T00:00:00`).getTime()) / 864e5))
  const kartalar = (!d ? [] : rahbar ? [
    // rahbar qarorlari («Qaroringiz kerak») — dashboardda emas, qo'ng'iroqchada (UstkiPanel) va Telegramda
    (qarz?.qarzdorlar.length || 0) > 0 && {
      k: 'qarz', nom: 'Qarzdorlar', ikon: 'hamyon', soni: qarz.qarzdorlar.length, xavf: true,
      izoh: "Libosni qaytargan, lekin jarima yoki zarar summasini to'lamagan mijozlar.",
      ichi: <Qatorlar royxat={qarz.qarzdorlar} onZakaz={onZakaz} ong={(z) => <b className="qizil">{som(z.qarz)}</b>} />,
    },
  ] : [
    d.olib_ketiladi.length > 0 && {
      k: 'olib', nom: 'Bugun olib ketadi', ikon: 'chiqdi', soni: d.olib_ketiladi.length,
      izoh: 'Mijoz kelganda zakazni oching: qoldiqni oling, zalog yozing va libosni bering.',
      ichi: <Qatorlar royxat={d.olib_ketiladi} onZakaz={onZakaz}
        ong={(z) => (z.qoldiq > 0 ? <><b>{som(z.qoldiq)}</b><span className="holat-pill vaqt">qoldiq</span></> : <span className="holat-pill bron">To'langan</span>)} />,
    },
    d.qaytariladi.length > 0 && {
      k: 'qaytar', nom: 'Bugun qaytaradi', ikon: 'qaytdi', soni: d.qaytariladi.length,
      izoh: 'Libos kelganda zakazni ochib, qaytarishni yozing.',
      ichi: <Qatorlar royxat={d.qaytariladi} onZakaz={onZakaz} ong={() => <span className="holat-pill kok">mijozda</span>} />,
    },
    d.kechikkan.length > 0 && {
      k: 'kech', nom: 'Kechikkan', ikon: 'soat', soni: d.kechikkan.length, xavf: true,
      izoh: "Qaytarish kuni o'tgan, libos hali mijozda. Mijozga qo'ng'iroq qiling.",
      ichi: <Qatorlar royxat={d.kechikkan} onZakaz={onZakaz} ong={(z) => <span className="holat-pill qarz">{kun(z.qaytarish)} kun</span>} />,
    },
    eslatmaSoni > 0 && {
      k: 'eslatma', nom: "Qo'ng'iroq qilish", ikon: 'telefon', soni: eslatmaSoni,
      izoh: "Ertaga olib ketadiganlar (qoldiq), bugun qaytaradiganlar va kechikkanlar. Gaplashgach «Bog'landim»ni bosing.",
      ichi: <div className="eslatmalar">{d.eslatmalar.map((e) => <Eslatma key={`${e.tur}-${e.zakaz_id}`} e={e} onZakaz={onZakaz} onBajarildi={yukla} />)}</div>,
    },
    qoldiqlar.length > 0 && {
      k: 'qoldiq', nom: "Qoldiq to'lanmagan", ikon: 'kassa', soni: qoldiqlar.length,
      izoh: 'Avans olingan, libos hali berilmagan zakazlar — qolgan summa libos berilayotganda olinadi. Bu qarz emas.',
      ichi: <Qatorlar royxat={qoldiqlar} onZakaz={onZakaz}
        ong={(z) => <><b>{som(z.qoldiq)}</b><small>{sanaQisqa(z.olib_ketish)}</small></>} />,
    },
  ]).filter(Boolean)

  // Rahbarda qaror ham, qarzdor ham bo'lmasa blok umuman chiqmaydi (dashboard toza qoladi)
  const bugungiIshlar = rahbar && kartalar.length === 0 ? null : (
    <>
      {d?.smena && !d.smena.ochiq && (
        <div className="ogohlantirish qator-ogoh">
          <span>Smena ochiq emas — to'lov qabul qilib bo'lmaydi.</span>
          <button className="ikkinchi kichik" onClick={onKassa}>Kassaga o'tish</button>
        </div>
      )}
      <section className="bugungi-ishlar" aria-label="Bugungi ishlar">
        {xato && <p className="xato">{xato}</p>}
        {!d && !xato && !rahbar && <div className="blok dash-karta ish-yuklanmoqda"><p className="malumot">Yuklanmoqda…</p></div>}
        {d && !rahbar && kartalar.length === 0 && (
          <div className="blok ish-bosh"><Belgi nom="bajarildi" /><span><b>Bugun shoshilinch ish yo'q.</b> Olib ketish, qaytarish, qaror va qo'ng'iroqlar paydo bo'lsa shu yerda va qo'ng'iroqchada chiqadi.</span></div>
        )}
        {kartalar.length > 0 && (
          <div className="ishlar-tor">
            {kartalar.map((c) => (
              <section key={c.k} id={`ish-${c.k}`} className={`blok dash-karta ish-karta${c.xavf ? ' xavf' : ''}${boshTab?.tab === c.k ? ' belgilangan' : ''}`}
                aria-label={`${c.nom}: ${c.soni}`}>
                <div className="dash-karta-bosh" title={c.izoh}>
                  <h3><Belgi nom={c.ikon} />{c.nom}</h3>
                  <span className="ish-son">{c.soni}</span>
                </div>
                <p className="ish-izoh">{c.izoh}</p>
                {c.ichi}
              </section>
            ))}
          </div>
        )}
      </section>
    </>
  )

  return (
    <div className="bosh-sahifa">
      {yuqori ? yuqori(bugungiIshlar) : bugungiIshlar}
    </div>
  )
}

// Rahbar qarorini kutayotganlar: chegirma so'rovi va xarajat shu yerning o'zida hal qilinadi (A-31);
// yangi libos — katalogga havola (rasm va narxni ko'rish kerak).
export function Tasdiqlar({ sorovlar, xarajat, soni, onZakaz, onBolim, onOzgardi }) {
  const [xato, setXato] = useState('')
  const [band, setBand] = useState(null)
  const [radSorov, setRadSorov] = useState(null)  // kassadan to'langan xarajatni rad etish — tasdiq bilan
  const bajar = async (kalit, fn) => {
    setXato(''); setBand(kalit)
    try { await fn(); onOzgardi() } catch (e) { setXato(xatoMatni(e)) } finally { setBand(null) }
  }
  const xarajatRad = (x) => bajar(`x${x.id}`, () => xarajatQaror(x.id, 'rad'))
  const boshqa = [
    soni?.liboslar > 0 && [`${soni.liboslar} ta yangi libos katalogga chiqishini kutmoqda — ko'rish`, 'katalog:liboslar'],
  ].filter(Boolean)
  if (sorovlar.length === 0 && xarajat.length === 0 && boshqa.length === 0) return <p className="malumot jadval-bosh">Qaror kutayotgan narsa yo'q.</p>
  return (
    <div className="tasdiq-royxat">
      {xato && <p className="xato" role="alert">{xato}</p>}
      {sorovlar.map((c) => (
        <ChegirmaQarori key={`c${c.id}`} c={c} band={band === `c${c.id}`} onZakaz={onZakaz}
          onQaror={(tana) => bajar(`c${c.id}`, () => chegirmaQaror(c.id, tana))} />
      ))}
      {xarajat.map((x) => (
        <div key={`x${x.id}`} className="tasdiq-qator">
          <div className="tasdiq-matn">
            <b>Xarajat: {x.modda_nomi} — {som(x.summa)}</b>
            <small>
              {sanaMatni(x.sana).slice(0, 5)}{x.kiritgan ? ` · kiritdi: ${x.kiritgan}` : ''}{x.kassadan ? ' · kassadan olingan' : ''}
              {x.doimiy ? ' · doimiy xarajat' : ''}{x.izoh ? ` · «${x.izoh}»` : ''}
            </small>
          </div>
          <div className="tasdiq-tugmalar">
            <button type="button" className="ikkinchi kichik" disabled={band === `x${x.id}`}
              onClick={() => (x.kassadan ? setRadSorov(x) : xarajatRad(x))}>Rad etish</button>
            <button type="button" className="kichik" disabled={band === `x${x.id}`} onClick={() => bajar(`x${x.id}`, () => xarajatQaror(x.id, 'tasdiq'))}>Tasdiqlash</button>
          </div>
        </div>
      ))}
      {boshqa.map(([t, b]) => (
        <button key={t} type="button" className="tasdiq-qator havola-qator" onClick={() => onBolim(b)}>{t}</button>
      ))}
      {radSorov && (
        <Tasdiq sarlavha="Xarajat rad etilsinmi?" tugma="Ha, rad etish"
          matn={`${radSorov.modda_nomi}, ${som(radSorov.summa)} — pul kassadan olingan. Rad etilsa, bu summa ${radSorov.kiritgan || 'kiritgan xodim'}ning kamomadi hisoblanadi.`}
          onYop={() => setRadSorov(null)} onTasdiq={() => { const x = radSorov; setRadSorov(null); xarajatRad(x) }} />
      )}
    </div>
  )
}

// C-16: chegirma so'rovi — summa va yangi jami tayyor hisoblangan; rad etishda sabab (sotuvchiga boradi),
// ikkinchi darajali «Boshqa summa» — so'ralganidan boshqa summada tasdiqlash (FT-11.4)
function ChegirmaQarori({ c, band, onZakaz, onQaror }) {
  const [z, setZ] = useState(null)
  const [rejim, setRejim] = useState(null)  // null | 'rad' | 'summa'
  const [izoh, setIzoh] = useState('')
  const [summa, setSumma] = useState('')
  useEffect(() => { zakazTafsilot(c.zakaz).then(setZ).catch(() => {}) }, [c.zakaz])
  // so'rov kutilayotganda zakazda boshqa chegirma yo'q: asos = asosiy narx + ustama − promokod
  const asos = z ? z.asosiy_narx + z.ustama - (z.promokod_chegirma || 0) : c.zakaz_jami
  const miqdor = z ? chegirmaMiqdori(z, c) : null
  const yangi = Number(summa) > 0 ? Math.min(Number(summa), asos) : 0
  return (
    <div className="tasdiq-qator chegirma-qaror">
      <div className="tasdiq-matn">
        <b><button type="button" className="havola" onClick={() => onZakaz(c.zakaz)}>#{c.zakaz_raqami}</button> {c.mijoz} — chegirma{' '}
          {c.foiz ? `${Number(c.foiz)}%` : ''}{miqdor != null ? `${c.foiz ? ' = ' : ''}${som(miqdor)} → yangi jami ${som(asos - miqdor)}` : (c.foiz ? '' : som(c.summa))}</b>
        <small>{som(asos)} dan · {c.sabab_nomi}{c.sotuvchi ? ` · so'radi: ${c.sotuvchi}` : ''}{c.izoh ? ` · «${c.izoh}»` : ''}</small>
        {rejim === 'rad' && (
          <label className="qaror-maydon">Rad etish sababi (ixtiyoriy — sotuvchiga boradi)
            <input value={izoh} maxLength={300} onChange={(e) => setIzoh(e.target.value)} placeholder="masalan: bu libosga chegirma yo'q" />
          </label>
        )}
        {rejim === 'summa' && (
          <label className="qaror-maydon">Chegirma summasi, so'm
            <SummaInput value={summa} onChange={(e) => setSumma(e.target.value)} />
            {yangi > 0 && <small>Yangi jami {som(asos - yangi)}</small>}
          </label>
        )}
      </div>
      <div className="tasdiq-tugmalar">
        {rejim === null && (<>
          <button type="button" className="ikkinchi kichik" disabled={band} onClick={() => setRejim('rad')}>Rad etish</button>
          <button type="button" className="havola" disabled={band} onClick={() => setRejim('summa')}>Boshqa summa</button>
          <button type="button" className="kichik" disabled={band} onClick={() => onQaror({ qaror: 'tasdiq' })}>Tasdiqlash</button>
        </>)}
        {rejim === 'rad' && (<>
          <button type="button" className="ikkinchi kichik" disabled={band} onClick={() => { setRejim(null); setIzoh('') }}>Qaytish</button>
          <button type="button" className="kichik xavfli" disabled={band} onClick={() => onQaror({ qaror: 'rad', izoh: izoh.trim() })}>Rad etish</button>
        </>)}
        {rejim === 'summa' && (<>
          <button type="button" className="ikkinchi kichik" disabled={band} onClick={() => { setRejim(null); setSumma('') }}>Qaytish</button>
          <button type="button" className="kichik" disabled={band || !(yangi > 0)} onClick={() => onQaror({ qaror: 'tasdiq', summa: yangi })}>
            {yangi > 0 ? `${som(yangi)} bilan tasdiqlash` : 'Tasdiqlash'}
          </button>
        </>)}
      </div>
    </div>
  )
}

// 4.14: eslatma sotuvchiga chiqadi; u mijoz bilan o'zi bog'lanadi va natijani yozadi (FT-14.2).
function Eslatma({ e, onZakaz, onBajarildi }) {
  const [izoh, setIzoh] = useState('')
  const [ochiq, setOchiq] = useState(false)
  return (
    <div className={`tasdiq-qator ${e.boglangan ? 'bajarilgan' : ''}`}>
      <div className="tasdiq-matn">
        <b><button className="havola" onClick={() => onZakaz(e.zakaz_id)}>#{e.raqam}</button> {e.mijoz || 'Mijoz'} · <a href={`tel:${e.telefon}`}>{e.telefon}</a></b>
        <small>{e.matn}</small>
      </div>
      <div className="tasdiq-tugmalar">
        {e.boglangan ? <span className="malumot">Bog'lanildi</span> : ochiq ? (
          <>
            <input placeholder="Natija (ixtiyoriy)" aria-label="Natija" value={izoh} onChange={(ev) => setIzoh(ev.target.value)} />
            <button className="kichik" onClick={() => boglandim(e.zakaz_id, e.tur, izoh).then(onBajarildi)}>Saqlash</button>
          </>
        ) : <button className="ikkinchi kichik" onClick={() => setOchiq(true)}>Bog'landim</button>}
      </div>
    </div>
  )
}

const OYQ = ['yan', 'fev', 'mar', 'apr', 'may', 'iyn', 'iyl', 'avg', 'sen', 'okt', 'noy', 'dek']
const sanaQisqa = (iso) => { const [, m, d] = String(iso).split('-').map(Number); return `${d} ${OYQ[m - 1]}` }

// Xodim bosh sahifasi (kanvas SotuvchiShisha / SotuvchiKassirShisha): 4 ko'rsatkich; chapda «Bugungi ishlar» jadvali
// (beriladi, qaytadi, kechikdi — har qatorda keyingi amal), o'ngda «Ertaga» va «Qo'ng'iroq qilish».
// Alohida kassir rejimida sotuvchi pul olmaydi: qoldiqli zakazda «To'lov kutilmoqda» — mijoz kassaga boradi.
const KUNLAR = ['Yakshanba', 'Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma', 'Shanba']
const OYLAR_T = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr']
const HOLAT_RANG = { vaqtinchalik: ['ogoh', 'vaqtinchalik'], chegirma_kutilmoqda: ['ogoh', 'chegirma kutilmoqda'], bron: ['tilla', 'bron'], berildi: ['kok', 'mijozda'] }

function XodimBosh({ d, xato, qoldiqlar, pulOladi, onZakaz, onKassa, onBolim, onYangila, boshTab, bugunMs }) {
  const hozir = new Date(bugunMs)
  const kun = (iso) => Math.max(1, Math.floor((bugunMs - new Date(`${iso}T00:00:00`).getTime()) / 864e5))
  const ishlar = d ? [
    ...d.olib_ketiladi.map((z) => ({ z, tur: 'olib' })),
    ...d.qaytariladi.map((z) => ({ z, tur: 'qaytar' })),
    ...d.kechikkan.map((z) => ({ z, tur: 'kech' })),
  ] : []
  const ertaga = d ? [...(d.ertaga_olib || []).map((z) => ({ z, tur: 'olib' })), ...(d.ertaga_qaytar || []).map((z) => ({ z, tur: 'qaytar' }))] : []
  const eslatmaSoni = d?.eslatmalar ? d.eslatmalar.filter((e) => !e.boglangan).length : 0
  const qoldiqli = d ? d.olib_ketiladi.filter((z) => z.qoldiq > 0) : []
  const birinchi = (r) => r[0]?.mijoz || ''
  const amal = ({ z, tur }) => {
    if (tur === 'kech') return ['Qo\'ng\'iroq', false]
    if (tur === 'qaytar') return ['Qabul qilish', false]
    if (z.qoldiq > 0) return pulOladi ? (z.holat === 'bron' ? ['To\'lov va berish', false] : ['Avans olish', false]) : ['To\'lov kutilmoqda', true]
    return ['Libosni berish', false]
  }
  return (
    <div className="bosh-sahifa xodim-bosh">
      <BoshAmal>
        <button type="button" className="bosh-tugma" onClick={() => onBolim?.('yangi')}><NavIkona nom="qosh" className="tugma-ikon" />Yangi zakaz</button>
      </BoshAmal>
      <BoshXulosa>{`${KUNLAR[hozir.getDay()]}, ${hozir.getDate()} ${OYLAR_T[hozir.getMonth()]}${d ? ` · bugun ${ishlar.length} ta ish` : ''}`}</BoshXulosa>
      {!pulOladi && (
        <p className="xodim-kassir-izoh"><NavIkona nom="yordam" className="tugma-ikon" /><span><b>Bu salonda pulni kassir qabul qiladi.</b> To'lov kerak bo'lgan
          zakazlar «To'lov kutilmoqda» deb turadi — mijozni kassaga yo'naltiring. To'lov tushgach, libosni bera olasiz.</span></p>
      )}
      {d?.smena && !d.smena.ochiq && pulOladi && (
        <div className="ogohlantirish qator-ogoh">
          <span>Smena ochiq emas — to'lov qabul qilib bo'lmaydi.</span>
          <button className="ikkinchi kichik" onClick={onKassa}>Kassaga o'tish</button>
        </div>
      )}
      {d && (
        <section className="dash-kpi libos-kpi" aria-label="Bugungi ko'rsatkichlar">
          <KpiFiltr nom="Bugun beriladi" son={d.olib_ketiladi.length} ikon="chiqdi" rang="tilla" izoh={d.olib_ketiladi.length ? `birinchisi: ${birinchi(d.olib_ketiladi)}` : "bugun yo'q"} />
          <KpiFiltr nom="Bugun qaytadi" son={d.qaytariladi.length} ikon="qaytdi" rang="kok" izoh={d.qaytariladi.length ? (d.qaytariladi[0].liboslar || [])[0] || birinchi(d.qaytariladi) : "bugun yo'q"} />
          <KpiFiltr nom="Kechikkan" son={d.kechikkan.length} ikon="soat" rang="pushti" xavf={d.kechikkan.length > 0} izoh={d.kechikkan.length ? "qo'ng'iroq qiling" : "kechikkan yo'q"} />
          {pulOladi
            ? <KpiFiltr nom="Olinadigan qoldiq" son={guruhla(qoldiqli.reduce((s, z) => s + z.qoldiq, 0))} ikon="kassa" rang="sariq" izoh={qoldiqli.length ? `${qoldiqli.length} ta zakazda · bugun` : "bugun qoldiq yo'q"} />
            : <KpiFiltr nom="To'lov kutilmoqda" son={qoldiqli.length} ikon="kassa" rang="sariq" izoh="mijoz kassaga boradi" />}
        </section>
      )}
      <section className="bugungi-ishlar xodim-ishlar" aria-label="Bugungi ishlar">
        {xato && <p className="xato">{xato}</p>}
        {!d && !xato && <div className="blok dash-karta ish-yuklanmoqda"><p className="malumot">Yuklanmoqda…</p></div>}
        {d && ishlar.length === 0 && ertaga.length === 0 && eslatmaSoni === 0 && (
          <div className="blok ish-bosh"><Belgi nom="bajarildi" /><span><b>Bugun shoshilinch ish yo'q.</b> Olib ketish, qaytarish va qo'ng'iroqlar paydo bo'lsa shu yerda va qo'ng'iroqchada chiqadi.</span></div>
        )}
        {d && (ishlar.length > 0 || ertaga.length > 0 || eslatmaSoni > 0) && (
          <div className="xodim-tor">
            {ishlar.length > 0 ? (
              <section id="ish-bugun" className={`blok ish-karta xodim-jadval${['olib', 'qaytar', 'kech'].includes(boshTab?.tab) ? ' belgilangan' : ''}`} aria-label={`Bugungi ishlar jadvali: ${ishlar.length}`}>
                <h3 className="sanoq-panel-nom"><Belgi nom="kun" className="tugma-ikon" />Bugungi ishlar</h3>
                <table className="soz-jadval xodim-ish-jadval">
                  <thead><tr><th>Ish</th><th>Mijoz</th><th>Libos</th><th className="ong">Qoldiq</th><th className="ong">Amal</th></tr></thead>
                  <tbody>
                    {ishlar.map((ish) => {
                      const { z, tur } = ish
                      const [hr, hn] = tur === 'kech' ? ['qizil', `${kun(z.qaytarish)} kun kechikdi`] : HOLAT_RANG[z.holat] || ['yopiq', z.holat_nomi || z.holat]
                      const [tugma, kutish] = amal(ish)
                      return (
                        <tr key={`${tur}-${z.id}`} className={tur === 'kech' ? 'kech' : ''}>
                          <td>
                            <b className="xodim-vaqt">{tur === 'kech' ? kunOyQisqa(z.qaytarish) : 'Bugun'}</b>
                            <small className="xodim-tur"><Belgi nom={tur === 'olib' ? 'chiqdi' : tur === 'qaytar' ? 'qaytdi' : 'soat'} className="tugma-ikon" />{tur === 'olib' ? 'Beriladi' : tur === 'qaytar' ? 'Qaytadi' : 'Kechikdi'}</small>
                          </td>
                          <td><span className="soz-matn"><b>{z.mijoz}</b><small>#{z.raqam} · <span className={`xodim-holat ${hr}`}>{hn}</span></small></span></td>
                          <td>
                            <span className="xodim-libos">
                              {z.rasm ? <img src={z.rasm} alt="" loading="lazy" /> : <span className="sanoq-plitka" aria-hidden="true"><Belgi nom="libos" className="tugma-ikon" /></span>}
                              <span className="soz-matn"><b>{(z.liboslar || [])[0] || '—'}</b>{z.olcham && <small>o'lcham {z.olcham}</small>}</span>
                            </span>
                          </td>
                          <td className="ong">{z.qoldiq > 0 ? <b className={tur === 'kech' ? 'qizil' : 'tilla-matn'}>{guruhla(z.qoldiq)}</b> : <span className="soz-mute">to'liq</span>}</td>
                          <td className="ong">{kutish
                            ? <span className="soz-holat ogoh">{tugma}</span>
                            : <button type="button" className="ikkinchi kichik xodim-amal" onClick={() => onZakaz(z.id)}>{tugma}</button>}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </section>
            ) : <div className="blok ish-bosh"><Belgi nom="bajarildi" /><span><b>Bugun berish va qaytarish yo'q.</b></span></div>}
            <div className="xodim-ong">
              {ertaga.length > 0 && (
                <section className="blok ish-karta xodim-panel" aria-label={`Ertaga: ${ertaga.length}`}>
                  <div className="sanoq-panel-bosh"><h3 className="sanoq-panel-nom"><Belgi nom="kun" className="tugma-ikon" />Ertaga</h3><small>{ertaga.length} ta</small></div>
                  {ertaga.map(({ z, tur }) => (
                    <button key={`${tur}-${z.id}`} type="button" className="xodim-ertaga" onClick={() => onZakaz(z.id)}>
                      {z.rasm ? <img src={z.rasm} alt="" loading="lazy" /> : <span className="sanoq-plitka" aria-hidden="true"><Belgi nom="libos" className="tugma-ikon" /></span>}
                      <span className="soz-matn"><b>{z.mijoz}</b><small>{tur === 'olib' ? 'olib ketadi' : 'qaytaradi'} · {(z.liboslar || [])[0] || '—'}</small></span>
                      <span className="soz-holat yopiq">#{z.raqam}</span>
                    </button>
                  ))}
                </section>
              )}
              {eslatmaSoni > 0 && (
                <section id="ish-eslatma" className={`blok ish-karta xodim-panel${boshTab?.tab === 'eslatma' ? ' belgilangan' : ''}`} aria-label={`Qo'ng'iroq qilish: ${eslatmaSoni}`}>
                  <div className="sanoq-panel-bosh"><h3 className="sanoq-panel-nom"><Belgi nom="telefon" className="tugma-ikon" />Qo'ng'iroq qilish</h3><small>{eslatmaSoni} ta</small></div>
                  <div className="eslatmalar">{d.eslatmalar.map((e) => <Eslatma key={`${e.tur}-${e.zakaz_id}`} e={e} onZakaz={onZakaz} onBajarildi={onYangila} />)}</div>
                </section>
              )}
              {qoldiqlar.length > 0 && pulOladi && (
                <p className="xodim-qoldiq-izoh">Yana {qoldiqlar.length} ta zakazda qoldiq bor — libos berilayotganda olinadi.{' '}
                  <button type="button" className="havola" onClick={() => onBolim?.('zakazlar')}>Zakazlar →</button></p>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
const kunOyQisqa = (iso) => { const [, m, d] = String(iso).split('-').map(Number); return `${d} ${OYQ[m - 1]}` }

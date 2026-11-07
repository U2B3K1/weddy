import { useCallback, useEffect, useState } from 'react'
import Tasdiq from '../components/Tasdiq'
import { boglandim, boshEkran, chegirmaMiqdori, chegirmaQaror, qarzdorlar, sanaMatni, som, xarajatQaror, xatoMatni, zakazlarRoyxat, zakazTafsilot } from '../api'
import SummaInput from '../components/SummaInput'
import { Belgi, Qatorlar } from '../components/ZakazQatorlari'

// FT-1.2: bosh sahifa. «Bugungi ishlar» — har tur alohida karta (qarorlar, bugun olib ketadi, qaytaradi, kechikkan,
// qo'ng'iroq, qarzdorlar, qoldiq): faqat ish bor bo'lsa chiqadi; xuddi shu turlar qo'ng'iroqchada ham (A-08, A-09).
// `yuqori` — rahbar dashbordi: (bugungiIshlar) => <Dashbord orta={…} />, panel kun varaqasi va grafiklar orasiga qo'yiladi.
// `tab` — qo'ng'iroqchadan kelgan tur ({ tab, n }): o'sha karta belgilanadi va unga suriladi (A-09).
export default function BoshEkran({ onZakaz, onKassa, rahbar, yuqori, tab: boshTab }) {
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

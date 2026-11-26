import { useCallback, useEffect, useState } from 'react'
import { tgEga, tgHolat, tgSozla, tgTolov, tgYordam } from '../api'
import Platforma, { PLATFORMA_BOLIMLARI } from './Platforma'
import { initData, nusxala, tanlovTitrash, tayyor, titrat, yop } from './telegram'

// Telegram ichidagi ilova (botdagi «Libosa» tugmasi): rahbar — Bugun, Sozlamalar, To'lov; boshqa xodim — Sozlamalar.
// Ma'lumot kalitlari backend'dagi vidjet bilan bir xil (backend/apps/notify/vidjet.py *_malumot).

const OYLAR = ['yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun', 'iyul', 'avgust', 'sentabr', 'oktabr', 'noyabr', 'dekabr']
const RANGLAR = ['#F3BF70', '#79A9F2', '#62D4A3', '#C79BE8', '#F08089']
const som = (n) => `${Math.round(n || 0).toLocaleString('ru-RU').replace(/,/g, ' ')}`
const soat = (h) => `${String(h).padStart(2, '0')}:00`
const sana = (s) => {
  const [k, o, y] = String(s || '').split('.')
  return OYLAR[o - 1] ? `${+k} ${OYLAR[o - 1]}, ${y}` : s
}
const xatoMatni = (e, zaxira) => e?.response?.data?.detail || (e?.response ? zaxira : "Internet yo'q. Qayta urinib ko'ring.")

function Belgi({ d, o = 18 }) {
  return (
    <svg width={o} height={o} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
  )
}

// ---------- Bugun ----------

function Bugun({ d, yangila, yuklanmoqda }) {
  const jami = d.t || 0
  const usullar = [['Naqd', d.n], ...(d.u || [])].filter((u) => u[1] > 0)
  const kassa = d.o ? ['ok', 'Smena ochiq'] : d.f == null ? ['', 'Bugun smena yopilmagan']
    : d.f === 0 ? ['ok', 'Kassa farqsiz'] : ['xato', `Kassa farqi: ${som(d.f)} so'm`]
  return (
    <>
      <section className="tg-karta tg-tushum">
        <p className="tg-izoh">Bugungi tushum · {d.v} holatiga</p>
        <p className="tg-katta">{som(jami)} <small>so'm</small></p>
        {jami > 0 && usullar.length > 0 ? (
          <>
            <div className="tg-chiziq" role="img" aria-label="To'lov usullari ulushi">
              {usullar.map((u, i) => <i key={u[0]} style={{ width: `${(u[1] / jami) * 100}%`, background: RANGLAR[i % 5] }} />)}
            </div>
            <ul className="tg-qatorlar">
              {usullar.map((u, i) => (
                <li key={u[0]}><i className="tg-nuqta" style={{ background: RANGLAR[i % 5] }} />{u[0]}<b>{som(u[1])}</b></li>
              ))}
            </ul>
          </>
        ) : <p className="tg-izoh">Bugun hali tushum yo'q.</p>}
      </section>
      <section className="tg-karta">
        <h2>Zakaz va libos</h2>
        <ul className="tg-qatorlar tg-katta-qator">
          <li><span className="tg-doira" style={{ background: '#62D4A3' }}><Belgi d="M12 5v14M5 12h14" o={13} /></span>Yangi bron<b>{d.y}</b></li>
          <li><span className="tg-doira" style={{ background: '#79A9F2' }}><Belgi d="M7 17 17 7M8 7h9v9" o={13} /></span>Berildi<b>{d.b}</b></li>
          <li><span className="tg-doira" style={{ background: '#F3BF70' }}><Belgi d="M17 7 7 17M16 17H7V8" o={13} /></span>Qaytdi<b>{d.q}</b></li>
        </ul>
      </section>
      <div className="tg-past">
        <span className={`tg-holat ${kassa[0]}`}>{kassa[1]}</span>
        <button type="button" className="tg-tugma" onClick={yangila} disabled={yuklanmoqda}>
          <Belgi d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5" o={15} />{yuklanmoqda ? 'Yangilanmoqda…' : 'Yangilash'}
        </button>
      </div>
    </>
  )
}

// ---------- Sozlamalar ----------

function Kalit({ yoqilgan, nom, izoh, bos, band }) {
  return (
    <button type="button" className="tg-kalit" role="switch" aria-checked={yoqilgan} onClick={bos} disabled={band}>
      <span>{nom}{izoh && <small>{izoh}</small>}</span>
      <span className={`tg-sw${yoqilgan ? ' on' : ''}`}><i /></span>
    </button>
  )
}

function Sozlamalar({ d, sozla, band }) {
  return (
    <>
      <section className="tg-karta">
        <h2>Qaysi xabarlar kelsin</h2>
        {d.g.map(([k, nom, on]) => (
          <Kalit key={k} nom={nom} yoqilgan={on} band={band} bos={() => sozla('tur', k)} />
        ))}
        <p className="tg-izoh">Qaror va pul bilan bog'liq xabarlar, yangi zakaz doim keladi.</p>
      </section>
      <section className="tg-karta">
        <h2>Eslatma vaqti</h2>
        <p className="tg-izoh">Kunlik eslatmalar (olib ketadi, qaytaradi, kechikdi) ertalab soat nechada kelsin?</p>
        <div className="tg-chiplar">
          {d.h.map((h) => (
            <button type="button" key={h} className={h === d.e ? 'on' : ''} aria-pressed={h === d.e} disabled={band}
              onClick={() => h !== d.e && sozla('esl', h)}>{soat(h)}</button>
          ))}
        </div>
        <Kalit nom="Primerkadan 1 soat oldin ham" yoqilgan={d.p} band={band} bos={() => sozla('esl', 'p')} />
      </section>
      <section className="tg-karta">
        <h2>Maxfiylik</h2>
        <p className="tg-izoh">Telefon ekranida xabar qanday ko'rinsin?</p>
        {[[0, "To'liq matn", "Xabar chatda darhol o'qiladi"],
          [1, 'Yashirin', 'Chatda faqat «yangi xabar» chiqadi, mazmuni bosilganda ochiladi']].map(([q, nom, izoh]) => {
          const tanlangan = (d.z ? 1 : 0) === q
          return (
            <button type="button" key={q} className={`tg-variant${tanlangan ? ' on' : ''}`} aria-pressed={tanlangan}
              disabled={band} onClick={() => !tanlangan && sozla('maxfiy', q)}>
              <b>{nom}</b><span>{izoh}</span>
            </button>
          )
        })}
      </section>
    </>
  )
}

// ---------- To'lov ----------

const kartaTuri = (k) => (/^(8600|5614)/.test(k) ? 'UZCARD' : /^9860/.test(k) ? 'HUMO' : /^4/.test(k) ? 'VISA'
  : /^(5[1-5]|2[2-7])/.test(k) ? 'MASTERCARD' : '')
const guruhla = (k) => k.replace(/(\d{4})(?=\d)/g, '$1 ')

function Tolov({ d, amal, band }) {
  const [nusxa, setNusxa] = useState('')
  const nusxalash = async () => {
    const ok = await nusxala(d.k)
    setNusxa(ok ? 'ok' : 'xato')
    if (ok) titrat()
  }
  return (
    <>
      {!d.bor ? (
        <section className="tg-karta"><p>To'lov ma'lumoti hali kiritilmagan. Platforma egasi bilan bog'laning.</p></section>
      ) : d.k ? (
        <>
          <div className="tg-bank">
            <div className="tg-bank-ust"><span className="tg-brend">LIBOSA</span><span className="tg-bank-tur">{kartaTuri(d.k)}</span></div>
            <div className="tg-chip" aria-hidden="true" />
            <p className="tg-raqam">{guruhla(d.k)}</p>
            {d.i && <p className="tg-egasi">Karta egasi<b>{d.i}</b></p>}
          </div>
          <button type="button" className="tg-asosiy" onClick={nusxalash}>
            <Belgi d="M9 9h11v11H9zM5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" o={17} />
            {nusxa === 'ok' ? 'Nusxalandi' : 'Karta raqamini nusxalash'}
          </button>
          {nusxa === 'xato' && <p className="tg-izoh tg-markaz">Nusxalanmadi: raqamni bosib turib nusxalang.</p>}
        </>
      ) : null}
      <section className="tg-karta">
        {d.w && <p className="tg-holat kut">To'lovingiz tekshirilmoqda — tasdiqlangach xabar keladi</p>}
        <p className={`tg-holat ${d.r ? 'xato' : 'ok'}`}>{d.o}</p>
        {d.n && <p className="tg-holat">{d.n}</p>}
        {d.l && <p className="tg-holat">{d.l}</p>}
        {d.bor && !d.k && d.z && <p className="tg-matn">{d.z}</p>}
        {d.k && d.z && <p className="tg-izoh tg-matn">{d.z}</p>}
      </section>
      {d.bor && (
        <section className="tg-karta">
          <h2>To'lagach</h2>
          <p className="tg-izoh">Chek rasmini (skrinshot) yoki PDF faylini yuboring — platforma egasiga boradi va tekshirilgach obuna uzaytiriladi.</p>
          <button type="button" className="tg-tugma tg-toliq tg-ost" disabled={band} onClick={() => amal('chek')}>
            <Belgi d="M6 2h12v20l-3-2-3 2-3-2-3 2zM9 7h6M9 11h6M9 15h4" o={16} />Chek yuborish
          </button>
        </section>
      )}
    </>
  )
}

// ---------- Qo'llab-quvvatlash ----------

function Yordam({ boshla, band }) {
  return (
    <section className="tg-karta">
      <h2>Savol yoki muammo</h2>
      <p>Libosa jamoasiga yozing: matn, skrinshot yoki ovozli xabar. Javob shu bot chatiga keladi.</p>
      <ol className="tg-qadamlar">
        <li>«Savol yozish» ni bosing — ilova yopiladi.</li>
        <li>Chatda savolingizni yuboring.</li>
        <li>Tugatish — /bekor.</li>
      </ol>
      <button type="button" className="tg-asosiy" disabled={band} onClick={boshla}>
        <Belgi d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z" o={18} />Savol yozish
      </button>
    </section>
  )
}

// ---------- Ilova ----------

const RAHBAR_BOLIMLARI = [['bugun', 'Bugun'], ['sozlama', 'Sozlamalar'], ['tolov', "To'lov"], ['yordam', 'Yordam']]
const XODIM_BOLIMLARI = [['bugun', 'Bugun'], ['sozlama', 'Sozlamalar'], ['yordam', 'Yordam']]
// Pastki panel belgilari (24×24, bitta yo'l)
const BELGILAR = {
  bugun: 'M3 3v18h18M7 15l4-4 3 3 5-6',
  sozlama: 'M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0',
  tolov: 'M2 5h20v14H2zM2 10h20M6 15h4',
  umumiy: 'M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z',
  salonlar: 'M3 9l1.5-5h15L21 9M4 9v11h16V9M3 9h18M9 20v-6h6v6',
  yordam: 'M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z',
}

export default function TgIlova() {
  const [kirish] = useState(initData)
  const [holat, setHolat] = useState(null)
  const [xato, setXato] = useState('')
  const [tanlangan, setTanlangan] = useState(null)
  const [bolim, setBolim] = useState('bugun')
  const [egaBolim, setEgaBolim] = useState('umumiy')
  const [band, setBand] = useState(false)
  const [xabar, setXabar] = useState(null)

  const yukla = useCallback(() => {
    if (!kirish) return Promise.resolve()
    setBand(true)
    return tgHolat(kirish).then((h) => { setHolat(h); setXato('') })
      .catch((e) => setXato(xatoMatni(e, "Ma'lumot ochilmadi. Ilovani botdan qayta oching.")))
      .finally(() => setBand(false))
  }, [kirish])

  useEffect(() => { tayyor(); yukla() }, [yukla])
  useEffect(() => {
    if (!xabar) return undefined
    const t = setTimeout(() => setXabar(null), 2600)
    return () => clearTimeout(t)
  }, [xabar])

  // Tanlov: 'ega' (platforma) yoki xodim id si. Bir akkaunt ham ega, ham salon xodimi bo'lishi mumkin — tepada almashtiriladi
  const p = holat?.platforma
  const egami = p && (tanlangan === 'ega' || !holat.xodimlar.length)
  const x = egami ? null : holat?.xodimlar.find((v) => v.id === tanlangan) || holat?.xodimlar[0]
  const rahbar = x && x.bugun
  // Ega o'zi salon xodimi ham bo'lsa — «Yordam» yo'q: murojaatlar unga keladi
  const bolimlar = egami ? PLATFORMA_BOLIMLARI
    : (rahbar ? RAHBAR_BOLIMLARI : XODIM_BOLIMLARI).filter(([k]) => !(k === 'yordam' && holat?.ega))
  const joriy = egami ? egaBolim : bolimlar.some(([k]) => k === bolim) ? bolim : 'bugun'
  const yangi = (qism) => setHolat((h) => ({ ...h, xodimlar: h.xodimlar.map((v) => (v.id === x.id ? { ...v, ...qism } : v)) }))
  const tanlovlar = holat ? [...(p ? [['ega', 'Platforma']] : []), ...holat.xodimlar.map((v) => [v.id, v.salon])] : []

  const yordamBoshla = () => {
    setBand(true)
    tgYordam(kirish, x.id)
      .then((r) => { setXabar(['ok', r.javob]); titrat(); setTimeout(yop, 1200) })   // savol chatda yoziladi
      .catch((e) => setXabar(['xato', xatoMatni(e, "Bajarilmadi. Qayta urinib ko'ring.")]))
      .finally(() => setBand(false))
  }
  const egaAmal = (malumot, keyin) => {
    setBand(true)
    tgEga(kirish, malumot)
      .then((r) => { setHolat((h) => ({ ...h, platforma: r.platforma })); setXabar(['ok', r.javob]); titrat(); keyin?.() })
      .catch((e) => setXabar(['xato', xatoMatni(e, "Bajarilmadi. Qayta urinib ko'ring.")]))
      .finally(() => setBand(false))
  }

  const sozla = (b, q) => {
    setBand(true)
    tgSozla(kirish, x.id, b, String(q))
      .then((r) => { yangi({ sozlama: r.sozlama }); setXabar(['ok', r.javob || 'Saqlandi']); titrat() })
      .catch((e) => setXabar(['xato', xatoMatni(e, 'Saqlanmadi. Qayta bosing.')]))
      .finally(() => setBand(false))
  }
  const amal = (a) => {
    setBand(true)
    tgTolov(kirish, x.id, a)
      .then((r) => {
        if (r.tolov) yangi({ tolov: r.tolov })
        setXabar(['ok', r.javob])
        titrat()
        if (a === 'chek') setTimeout(yop, 1200)   // chek rasmi chatda yuboriladi — bot so'rovi shu yerda kutadi
      })
      .catch((e) => setXabar(['xato', xatoMatni(e, "Bajarilmadi. Qayta urinib ko'ring.")]))
      .finally(() => setBand(false))
  }

  let ichi
  if (!kirish) {
    ichi = <section className="tg-karta"><h2>Telegram ilovasi</h2><p>Bu sahifa Libosa botidagi «Libosa» tugmasi orqali ochiladi.</p></section>
  } else if (xato && !holat) {
    ichi = (
      <section className="tg-karta"><p>{xato}</p>
        <button type="button" className="tg-tugma" onClick={yukla} disabled={band}>Qayta urinish</button></section>
    )
  } else if (!holat) {
    ichi = <p className="tg-izoh tg-markaz" aria-live="polite">Yuklanmoqda…</p>
  } else if (!x && !egami) {
    ichi = (
      <section className="tg-karta">
        <p>Bu Telegram akkaunt hali salonga ulanmagan. Libosa ilovasida «Telegramni ulash» tugmasini bosing.</p>
      </section>
    )
  } else {
    ichi = (
      <>
        {egami && <Platforma p={p} bolim={joriy} setBolim={setEgaBolim} amal={egaAmal} band={band} />}
        {!egami && joriy === 'bugun' && (rahbar
          ? <Bugun d={x.bugun} yangila={yukla} yuklanmoqda={band} />
          : (
            <>
              <section className="tg-karta"><p className="tg-matn tg-kun-matn">{x.kun}</p></section>
              <div className="tg-past tg-ong">
                <button type="button" className="tg-tugma" onClick={yukla} disabled={band}>{band ? 'Yangilanmoqda…' : 'Yangilash'}</button>
              </div>
            </>
          ))}
        {!egami && joriy === 'sozlama' && <Sozlamalar d={x.sozlama} sozla={sozla} band={band} />}
        {!egami && joriy === 'tolov' && x.tolov && <Tolov d={x.tolov} amal={amal} band={band} />}
        {!egami && joriy === 'yordam' && <Yordam boshla={yordamBoshla} band={band} />}
      </>
    )
  }

  // Sarlavha va izoh — mobil ilovadagi kabi: katta sarlavha, ostida kichik izoh
  const [sarlavha, izoh] = egami
    ? { umumiy: ['Platforma', `${p.salonlar.length} ta salon`], salonlar: ['Salonlar', 'Obuna va to\'lov kiritish'],
      tolov: ["To'lov ma'lumoti", 'Rahbarlar ko\'radigan matn'] }[joriy]
    : !x ? ['Libosa', '']
      : joriy === 'bugun' ? ['Bugun', rahbar ? sana(x.bugun.d) : x.salon]
        : joriy === 'tolov' ? ["To'lov", 'Obuna']
          : joriy === 'yordam' ? ["Qo'llab-quvvatlash", 'Libosa jamoasi bilan aloqa'] : ['Sozlamalar', 'Bot xabarlari qachon va qanday kelsin']
  const joriyTanlov = egami ? 'ega' : x?.id
  const panel = holat && (egami || x)
  const bolimTanla = (k) => {
    if (k === joriy) return
    tanlovTitrash()
    if (egami) setEgaBolim(k); else setBolim(k)
    window.scrollTo(0, 0)
  }
  return (
    <div className={`tg${panel ? ' tg-panelli' : ''}`}>
      <div className="tg-fon" aria-hidden="true" />
      <header className="tg-shapka">
        <div className="tg-shapka-ust">
          <span className="tg-brend">LIBOSA</span>
          {tanlovlar.length <= 1 && x && <span className="tg-salon-belgi">{x.salon}</span>}
        </div>
        <h1>{sarlavha}</h1>
        {izoh && <p className="tg-izoh-sarlavha">{izoh}</p>}
        {tanlovlar.length > 1 && (
          <div className="tg-salonlar" role="group" aria-label="Salon">
            {tanlovlar.map(([k, nom]) => (
              <button type="button" key={k} className={k === joriyTanlov ? 'on' : ''} aria-pressed={k === joriyTanlov}
                onClick={() => { setTanlangan(k); window.scrollTo(0, 0) }}>{nom}</button>
            ))}
          </div>
        )}
      </header>
      <main className="tg-ichi" key={`${joriyTanlov}-${joriy}`}>{ichi}</main>
      {xabar && <p className={`tg-xabar ${xabar[0]}`} role="status">{xabar[1]}</p>}
      {panel && (
        <nav className="tg-pastki" aria-label="Bo'limlar">
          {bolimlar.map(([k, nom]) => (
            <button type="button" key={k} className={k === joriy ? 'on' : ''} aria-current={k === joriy ? 'page' : undefined}
              onClick={() => bolimTanla(k)}>
              <span className="tg-pastki-belgi"><Belgi d={BELGILAR[k]} o={22} /></span>
              <span>{nom}</span>
            </button>
          ))}
        </nav>
      )}
    </div>
  )
}

import { useState } from 'react'

// Platforma egasi (Telegram ichidagi ilova): umumiy holat, salonlar (karta va obuna to'lovini kiritish), to'lov ma'lumoti.
// Ma'lumot — backend/apps/notify/miniilova.py `platforma_holati`; amallar `TgEgaView` orqali.

const som = (n) => `${Math.round(n || 0).toLocaleString('ru-RU').replace(/,/g, ' ')} so'm`
const FILTRLAR = [['hammasi', 'Hammasi'], ['yaqin', 'Yaqin 7 kun'], ['tugagan', 'Tugagan'], ['tekshir', 'Tekshirish']]
const mos = (s, f) => (f === 'yaqin' ? s.qolgan != null && s.qolgan >= 0 && s.qolgan <= 7
  : f === 'tugagan' ? s.qolgan != null && s.qolgan < 0 : f === 'tekshir' ? s.kutilmoqda : true)
const kunYorliq = (s) => (s.qolgan == null ? '' : s.qolgan < 0 ? 'tugagan' : s.qolgan === 0 ? 'bugun' : `${s.qolgan} kun`)

function Umumiy({ p, ochSalon, ochRoyxat, amal, band }) {
  const plitalar = [['hammasi', 'Salonlar', p.salonlar.length], ['yaqin', 'Yaqin 7 kunda tugaydi', p.yaqin],
    ['tugagan', 'Muddati tugagan', p.tugagan], ['tekshir', "To'lovi tekshirilishi kerak", p.kutayotgan.length]]
  return (
    <>
      <section className="tg-karta">
        <p className={`tg-holat ${p.toxtagan.length ? 'xato' : 'ok'}`}>
          {p.toxtagan.length ? `To'xtagan: ${p.toxtagan.join(', ')}` : 'Platforma: hammasi joyida'}
        </p>
        {p.javobsiz > 0 && <p className="tg-holat kut">Javobsiz murojaatlar: {p.javobsiz} — javob botda, xabarga «reply»</p>}
        <p className="tg-holat">Shu oy: {p.oy_soni} ta to'lov, {som(p.oy_summa)}</p>
      </section>
      <div className="tg-plitalar">
        {plitalar.map(([f, nom, n]) => (
          <button type="button" key={f} className={`tg-plita${f !== 'hammasi' && n > 0 ? ' urgu' : ''}`} onClick={() => ochRoyxat(f)}>
            <b>{n}</b><span>{nom}</span>
          </button>
        ))}
      </div>
      {p.kutayotgan.length > 0 && (
        <section className="tg-karta">
          <h2>Tekshirilishi kerak</h2>
          {p.kutayotgan.map((t, i) => (
            <button type="button" key={i} className="tg-qator-tugma" onClick={() => ochSalon(t.salon_id)}>
              <span>{t.salon}<small>{t.vaqt} · {t.chek ? 'chek yuborilgan' : 'cheksiz'}{t.xodim && ` · ${t.xodim}`}</small></span>
              <span className="tg-kursor" aria-hidden="true">›</span>
            </button>
          ))}
          <p className="tg-izoh">Pul kelganini tekshirib, salon kartasida to'lovni kiriting.</p>
        </section>
      )}
      {p.arizalar.length > 0 && (
        <section className="tg-karta">
          <h2>Ko'rilmagan so'rovlar · {p.arizalar_soni}</h2>
          {p.arizalar.map((a) => (
            <div key={a.id} className="tg-ariza">
              <p><b>{a.ism}</b> · <a href={`tel:${a.telefon}`}>{a.telefon}</a></p>
              <p className="tg-izoh">{a.vaqt} · {a.tur}{a.salon && ` · ${a.salon}`}</p>
              {a.xabar && <p className="tg-matn">{a.xabar}</p>}
            </div>
          ))}
          <button type="button" className="tg-tugma tg-toliq" disabled={band}
            onClick={() => amal({ amal: 'ariza_ok', gacha: p.arizalar[p.arizalar.length - 1].id })}>Ko'rildi deb belgilash</button>
        </section>
      )}
      <TizimHolati h={p.holat} />
    </>
  )
}

// Bot tugmalari statistikasi (TugmaBosish.nom): «menyu:sozlama» → «Sozlamalar · menyu»
const TUGMA_JOYI = { menyu: 'pastki menyu', tugma: 'xabar ostida', ega: 'sizning menyu', eski: 'eski menyu' }
const TUGMA_NOMI = {
  sozlama: 'Sozlamalar', platforma: 'Platforma', tolov: "To'lov", qaror: 'Qarorlar', bugun: 'Bugun', kassa: 'Kassa',
  ertaga: 'Ertaga', holat: 'Holat', ob_tugagan: 'Tugagan obunalar', ob_yaqin: 'Yaqin 7 kun', ob_tekshir: 'Tekshirish kerak',
  tolov_yoz: "To'lov ma'lumotini yozish", tolov_och: "To'lov ma'lumotini o'chirish", sl: 'Salonlar', s: 'Salon kartasi',
  to: "To'lov oyi", tq: "To'lov tasdig'i", ar: "So'rovlar", ar_ok: "So'rov ko'rildi", soz_matn: "Oddiy ko'rinish",
  vidjet_yoq: 'Vidjet yoqish', vidjet_och: "Vidjet o'chirish", tolov_ega: "To'lov ma'lumoti",
}
const tugmaNomi = (n) => {
  const [joy, ...qolgan] = String(n).split(':')
  const k = qolgan.join(':')
  return TUGMA_JOYI[joy] ? `${TUGMA_NOMI[k] || k} · ${TUGMA_JOYI[joy]}` : n
}

function TizimHolati({ h }) {
  const eng = Math.max(1, ...h.tugmalar.map((t) => t[1]))
  return (
    <>
      <div className="tg-bolim-sarlavha">
        <h2>Tizim holati</h2>
        <span className={`tg-kun${h.muammo ? ' xato' : ''}`}>{h.muammo ? `${h.muammo} ta muammo` : 'hammasi joyida'}</span>
      </div>
      <div className="tg-vazifalar">
        <div className="tg-vazifa">
          <span className="tg-vazifa-nom">Baza</span>
          <span className="tg-vazifa-holat ok">ishlayapti</span>
        </div>
        {h.vazifalar.map((v) => (
          <div key={v.nom} className={`tg-vazifa${v.toxtagan ? ' xato' : ''}`}>
            <span className="tg-vazifa-nom">{v.nom}</span>
            <span className={`tg-vazifa-holat ${!v.vaqt ? '' : v.toxtagan ? 'xato' : 'ok'}`}>
              {!v.vaqt ? "ma'lumot yo'q" : v.toxtagan ? `to'xtagan · ${v.vaqt}` : `ishlayapti · ${v.vaqt}`}
            </span>
          </div>
        ))}
      </div>
      <div className="tg-plitalar">
        <div className={`tg-plita${h.zaxira_eski || !h.zaxira ? ' ogoh' : ''}`}>
          <b className="tg-plita-kichik">{h.zaxira || "yo'q"}</b>
          <span>Zaxira nusxa{h.zaxira_eski ? ' — 36 soatdan eski' : ''}</span>
        </div>
        <div className={`tg-plita${h.xato ? ' ogoh' : ''}`}>
          <b>{h.navbat}</b>
          <span>Xabar navbatida{h.xato ? ` · 24 soatda ${h.xato} tasi yetmadi` : ''}</span>
        </div>
      </div>
      {h.tugmalar.length > 0 && (
        <section className="tg-karta">
          <h2>Bot tugmalari · 30 kun</h2>
          <p className="tg-izoh">Oxirgi 30 kunda botda qaysi tugma necha marta bosilgani. Kam bosilgani — kam kerak bo'lgani.</p>
          <ul className="tg-ustunlar">
            {h.tugmalar.map(([nom, soni]) => (
              <li key={nom}>
                <span className="tg-ustun-nom">{tugmaNomi(nom)}</span>
                <span className="tg-ustun-yol" aria-hidden="true"><i style={{ width: `${(soni / eng) * 100}%` }} /></span>
                <b>{soni}</b>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="tg-izoh tg-markaz">Tekshirildi · {h.vaqt}</p>
    </>
  )
}

// Bilim bazasi: agent savolga faqat shu maqolalar asosida javob yozadi; javob ega «Yuborish» ni bosgandagina ketadi.
// Faqat «yoqilgan» maqolalar ishlatiladi; dasturchi tayyorlagan qoralamalarni tekshirib yoqasiz.
const MANBA = { qoralama: 'qoralama — tekshiring', ega: 'sizning javobingizdan', qolda: "qo'lda yozilgan" }

function MaqolaShakli({ m, saqla, bekor, ochir, band }) {
  const [savol, setSavol] = useState(m?.savol || '')
  const [javob, setJavob] = useState(m?.javob || '')
  const [faol, setFaol] = useState(m ? m.faol : true)
  return (
    <section className="tg-karta">
      <h2>{m ? 'Maqolani tahrirlash' : 'Yangi maqola'}</h2>
      <label className="tg-yorliq" htmlFor="tg-bilim-savol">Savol (xodim qanday so'raydi)</label>
      <input id="tg-bilim-savol" className="tg-matn-maydon" maxLength={300} value={savol}
        placeholder="Masalan: PIN kodim esimdan chiqdi" onChange={(e) => setSavol(e.target.value)} />
      <label className="tg-yorliq" htmlFor="tg-bilim-javob">Javob (agent shu ma'lumotdan foydalanadi)</label>
      <textarea id="tg-bilim-javob" className="tg-matn-maydon" rows={6} maxLength={2000} value={javob}
        onChange={(e) => setJavob(e.target.value)} />
      <button type="button" className="tg-kalit" role="switch" aria-checked={faol} onClick={() => setFaol(!faol)}>
        <span>Yoqilgan<small>Yoqilgan maqoladan agent javob taklif qiladi</small></span>
        <span className={`tg-sw${faol ? ' on' : ''}`}><i /></span>
      </button>
      <div className="tg-amallar tg-ost">
        <button type="button" className="tg-asosiy" disabled={band || !savol.trim() || !javob.trim()}
          onClick={() => saqla({ id: m?.id, savol, javob, faol })}>Saqlash</button>
        <button type="button" className="tg-tugma" disabled={band} onClick={bekor}>Bekor qilish</button>
        {m && <button type="button" className="tg-havola tg-xavfli" disabled={band} onClick={() => ochir(m.id)}>Maqolani o'chirish</button>}
      </div>
    </section>
  )
}

function Bilim({ p, amal, band }) {
  const [tahrir, setTahrir] = useState(null)   // null — ro'yxat, 'yangi' — yangi maqola, aks holda maqola
  const faol = p.bilim.filter((m) => m.faol).length
  const qoralama = p.bilim.filter((m) => !m.faol && m.manba === 'qoralama').length
  if (tahrir) {
    return (
      <MaqolaShakli key={tahrir === 'yangi' ? 'yangi' : tahrir.id} m={tahrir === 'yangi' ? null : tahrir} band={band}
        bekor={() => setTahrir(null)}
        saqla={(d) => amal({ amal: 'bilim_saqla', ...d }, () => setTahrir(null))}
        ochir={(id) => amal({ amal: 'bilim_ochir', id }, () => setTahrir(null))} />
    )
  }
  return (
    <>
      <section className="tg-karta">
        <p className={`tg-holat ${p.agent.yoqilgan ? 'ok' : ''}`}>
          Agent: {p.agent.yoqilgan ? 'yoqilgan (tasdiq rejimi)' : "o'chiq"}{!p.agent.kalit && ' · AI kaliti kiritilmagan'}
        </p>
        <p className="tg-holat">{faol} ta yoqilgan, {p.bilim.length - faol} ta o'chiq maqola</p>
        <p className="tg-izoh tg-ost">Agent savolga faqat yoqilgan maqolalar asosida javob yozadi va sizga taklif qiladi — «Yuborish» ni bossangizgina ketadi.
          Bazada javob bo'lmasa, savol sizga o'tadi. Yoqish va sinash — botda /agent.</p>
      </section>
      <button type="button" className="tg-asosiy" onClick={() => setTahrir('yangi')}>Yangi maqola</button>
      {qoralama > 0 && (
        <button type="button" className="tg-tugma" disabled={band} onClick={() => amal({ amal: 'bilim_qoralamalar' })}>
          {qoralama} ta qoralamani yoqish
        </button>
      )}
      <section className="tg-karta tg-royxat">
        {p.bilim.length === 0 && <p className="tg-izoh">Hali maqola yo'q.</p>}
        {p.bilim.map((m) => (
          <button type="button" key={m.id} className="tg-qator-tugma" onClick={() => setTahrir(m)}>
            <span>{m.savol}<small>{MANBA[m.manba] || m.manba}</small></span>
            <span className={`tg-kun${m.faol ? '' : ' kut'}`}>{m.faol ? 'yoqilgan' : "o'chiq"}</span>
          </button>
        ))}
      </section>
    </>
  )
}

function SalonKartasi({ s, orqaga, amal, band }) {
  const [tanlov, setTanlov] = useState(null)
  return (
    <>
      <button type="button" className="tg-havola tg-orqaga" onClick={orqaga}>‹ Salonlar</button>
      <section className="tg-karta">
        <h2>{s.nomi}</h2>
        <p className={`tg-holat ${s.qolgan != null && s.qolgan < 0 ? 'xato' : s.qolgan != null && s.qolgan <= 7 ? 'kut' : 'ok'}`}>{s.obuna}</p>
        <p className="tg-holat">Holat: {s.holat_nomi}</p>
        <p className="tg-holat">{s.tarif ? `Tarif: ${s.tarif}${s.narx ? ` — oyiga ${som(s.narx)}` : ''}` : 'Tarif belgilanmagan'}</p>
        {s.rahbarlar.map((r, i) => (
          <p key={i} className="tg-holat">Rahbar: {r.ism}{!r.tg && ' (Telegram ulanmagan)'}</p>
        ))}
        {s.telefon && <p className="tg-holat">Tel: <a href={`tel:${s.telefon}`}>{s.telefon}</a></p>}
        <p className="tg-holat">Xodimlar: {s.xodimlar} ta</p>
        {s.oxirgi && <p className="tg-holat">Oxirgi to'lov: {s.oxirgi}</p>}
        {s.kutilmoqda && <p className="tg-holat kut">Rahbar to'lov qilganini bildirgan</p>}
      </section>
      <section className="tg-karta">
        <h2>To'lov kiritish</h2>
        {!tanlov ? (
          <>
            <p className="tg-izoh">Necha oyga? Pul kelganini tekshirib oling.</p>
            <div className="tg-chiplar">
              {s.takliflar.map((t) => (
                <button type="button" key={t.oy} className="tg-oy" disabled={band} onClick={() => setTanlov(t)}>
                  {t.oy} oy{t.summa ? <small>{som(t.summa)}</small> : null}
                </button>
              ))}
            </div>
          </>
        ) : (
          <div className="tg-tasdiq">
            <p><b>{tanlov.oy} oylik to'lov kiritilsinmi?</b></p>
            <p className="tg-holat">Summa: {tanlov.summa ? som(tanlov.summa) : "tarifda narx yo'q — keyin panelda kiritasiz"}</p>
            <p className="tg-holat ok">Kiritilgach: {tanlov.yangi} gacha</p>
            <p className="tg-izoh">Xato kiritilsa — panelda «bekor qilish» bor. Rahbarga to'lov cheki boradi.</p>
            <div className="tg-amallar">
              <button type="button" className="tg-asosiy" disabled={band}
                onClick={() => amal({ amal: 'tolov', salon: s.id, oylar: tanlov.oy, kod: s.kod }, () => setTanlov(null))}>
                Ha, {tanlov.oy} oy kiritish
              </button>
              <button type="button" className="tg-tugma" disabled={band} onClick={() => setTanlov(null)}>Bekor qilish</button>
            </div>
          </div>
        )}
      </section>
    </>
  )
}

function Salonlar({ p, filtr, setFiltr, salonId, setSalonId, amal, band }) {
  const s = p.salonlar.find((v) => v.id === salonId)
  if (s) return <SalonKartasi key={s.id} s={s} orqaga={() => setSalonId(null)} amal={amal} band={band} />
  const royxat = p.salonlar.filter((v) => mos(v, filtr))
  return (
    <>
      <div className="tg-filtrlar" role="group" aria-label="Saralash">
        {FILTRLAR.map(([k, nom]) => (
          <button type="button" key={k} className={k === filtr ? 'on' : ''} aria-pressed={k === filtr} onClick={() => setFiltr(k)}>{nom}</button>
        ))}
      </div>
      <section className="tg-karta tg-royxat">
        {royxat.length === 0 && <p className="tg-izoh">Bu ro'yxatda salon yo'q.</p>}
        {royxat.map((v) => (
          <button type="button" key={v.id} className="tg-qator-tugma" onClick={() => setSalonId(v.id)}>
            <span>{v.nomi}<small>{v.holat_nomi}{v.kutilmoqda && ' · to\'lov kutmoqda'}</small></span>
            <span className={`tg-kun${v.qolgan != null && v.qolgan < 0 ? ' xato' : v.qolgan != null && v.qolgan <= 7 ? ' kut' : ''}`}>{kunYorliq(v)}</span>
          </button>
        ))}
      </section>
    </>
  )
}

function TolovMalumoti({ p, amal, band }) {
  const [matn, setMatn] = useState(p.tolov_malumoti)
  return (
    <section className="tg-karta">
      <h2>To'lov ma'lumoti</h2>
      <p className="tg-izoh">Salon rahbarlari «To'lov» bo'limida shuni ko'radi. Karta raqami va ism-familiyani alohida qatorga yozing.</p>
      <label className="tg-yorliq" htmlFor="tg-tolov-matn">Matn</label>
      <textarea id="tg-tolov-matn" className="tg-matn-maydon" rows={5} maxLength={1000} value={matn}
        placeholder={'8600 1234 5678 9012\nIsm Familiya\nTel: +998 …'} onChange={(e) => setMatn(e.target.value)} />
      <div className="tg-amallar">
        <button type="button" className="tg-asosiy" disabled={band || !matn.trim() || matn.trim() === p.tolov_malumoti.trim()}
          onClick={() => amal({ amal: 'tolov_malumoti', matn })}>Saqlash</button>
        {p.tolov_malumoti && (
          <button type="button" className="tg-tugma" disabled={band}
            onClick={() => { setMatn(''); amal({ amal: 'tolov_malumoti', matn: '' }) }}>O'chirish</button>
        )}
      </div>
    </section>
  )
}

export const PLATFORMA_BOLIMLARI = [['umumiy', 'Umumiy'], ['salonlar', 'Salonlar'], ['bilim', 'Bilim'], ['tolov', "To'lov"]]

export default function Platforma({ p, bolim, setBolim, amal, band }) {
  const [filtr, setFiltr] = useState('hammasi')
  const [salonId, setSalonId] = useState(null)
  const ochRoyxat = (f) => { setFiltr(f); setSalonId(null); setBolim('salonlar') }
  const ochSalon = (id) => { setSalonId(id); setBolim('salonlar') }
  if (bolim === 'salonlar') {
    return <Salonlar p={p} filtr={filtr} setFiltr={setFiltr} salonId={salonId} setSalonId={setSalonId} amal={amal} band={band} />
  }
  if (bolim === 'bilim') return <Bilim p={p} amal={amal} band={band} />
  if (bolim === 'tolov') return <TolovMalumoti p={p} amal={amal} band={band} />
  return <Umumiy p={p} ochSalon={ochSalon} ochRoyxat={ochRoyxat} amal={amal} band={band} />
}

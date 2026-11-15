import { useCallback, useEffect, useRef, useState } from 'react'

// Kirish filmi (ega talabi, 2026-11-14: akademiya hikoya bilan boshlansin). Besh sahna: har birida ovozsiz aylanadigan
// video, hikoyachi ovozi (Narakeet «Shavkat», `kino-N.mp3` — `manage.py akademiya_ovoz --film`) va subtitr. Ovoz faqat foydalanuvchi «Ko'rish» ni bosgandan keyin
// yoqiladi (brauzer avtomatik ovozga ruxsat bermaydi); salonda ovoz o'chiq bo'lsa ham subtitr bilan tushunarli.
// Matnlar ovoz fayllaridagi bilan so'zma-so'z bir xil (ovoz qayta yozilsa — shu yer ham yangilanadi).
const SAHNALAR = [
  { tasvir: 'kino-tong', matn: "Bu — bizning salon. Har kuni bu yerga kimdir hayotidagi eng muhim kun uchun libos izlab keladi." },
  { tasvir: 'bob-mijoz-keldi', matn: "Madina bugun birinchi marta ishga keldi. Mijozlar ko'p, liboslar undan ham ko'p." },
  { tasvir: 'kino-daftar', matn: "Ilgari hammasi daftarda edi. Bitta chalkash yozuv — va bir libos ikki kelinga va'da qilinib qolardi." },
  { tasvir: 'bob-birinchi-kun', matn: "Endi unday emas. Kalit bilan birga Nodira opa Madinaga Libosa tizimini ham topshirdi: har bir libos, har bir sana va har bir so'm o'z joyida." },
  { tasvir: 'hero-madina', matn: "Endi navbat sizda. Birinchi kundan boshlab qadam-baqadam o'rganasiz. Xato qilishdan qo'rqmang." },
]
const NOM = 'Nafislik tartibdan boshlanadi'   // film nomi — Libosa shiori
const OVOZSIZ_VAQT = 7000  // ovoz o'chiq bo'lsa sahna shuncha turadi (subtitrni o'qish uchun)
const HARAKATSIZ = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// onTugadi — oxirgi sahnadagi «Boshlash» (berilmasa — onYop): ochiq bosh sahifada film tugagach to'g'ri darslarga olib kiradi
export default function Kino({ onYop, onTugadi }) {
  const [i, setI] = useState(-1)        // -1 — boshlash ekrani
  const [ovoz, setOvoz] = useState(true)
  const audio = useRef(null)
  const oxirgi = i === SAHNALAR.length - 1
  const sahna = SAHNALAR[Math.max(i, 0)]

  const keyingi = useCallback(() => setI((x) => Math.min(x + 1, SAHNALAR.length - 1)), [])

  // Sahna almashganda uning ovozi boshlanadi; ovoz tugagach (yoki ovozsiz rejimda vaqt o'tgach) keyingi sahna.
  // Oxirgi sahna o'zi yopilmaydi — o'quvchi «Boshlash» ni bosadi.
  useEffect(() => {
    if (i < 0) return undefined
    const a = audio.current
    let t
    const otish = () => { if (i < SAHNALAR.length - 1) t = setTimeout(keyingi, 700) }
    if (ovoz && a) {
      a.currentTime = 0
      a.addEventListener('ended', otish)
      // brauzer ovozga ruxsat bermadi (sahifa hali bosilmagan): ovoz «o'chiq» holatga o'tadi — film subtitr vaqti bilan ketadi,
      // «Ovozni yoqish» bir bosishda yoqadi
      a.play().catch(() => setOvoz(false))
    } else if (i < SAHNALAR.length - 1) {
      t = setTimeout(keyingi, OVOZSIZ_VAQT)
    }
    return () => { clearTimeout(t); a?.removeEventListener('ended', otish); a?.pause() }
  }, [i, ovoz, keyingi])

  // Afisha: film nomi harfma-harf «bosib» yoziladi, tugagach film o'zi boshlanadi (ega talabi, 2026-11-15; «ijro» tugmasi yo'q).
  // Brauzer ovozga ruxsat bermasa (sahifa bosilmagan bo'lsa) — film subtitr vaqti bilan ketadi.
  const [yozildi, setYozildi] = useState(HARAKATSIZ ? NOM.length : 0)
  useEffect(() => {
    if (i >= 0 || HARAKATSIZ) return undefined
    let n = 0, t
    const yoz = () => {
      n += 1; setYozildi(n)
      t = n < NOM.length ? setTimeout(yoz, NOM[n - 1] === ' ' ? 190 : 75) : setTimeout(() => setI(0), 1500)
    }
    t = setTimeout(yoz, 1000)
    return () => clearTimeout(t)
  }, [i])

  useEffect(() => {
    const bos = (e) => { if (e.key === 'Escape') onYop() }
    window.addEventListener('keydown', bos)
    return () => window.removeEventListener('keydown', bos)
  }, [onYop])

  return (
    <div className={`ak-kino${i < 0 ? ' afisha' : ''}`} role="dialog" aria-modal="true" aria-label="Libosa Academy — kirish filmi">
      {/* tasvir: avval rasm (poster), ustida shu sahnaning videosi; video bo'lmasa rasmning o'zi qoladi */}
      <div key={sahna.tasvir} className="ak-kino-tasvir" style={{ backgroundImage: `url(/akademiya/${sahna.tasvir}.jpg)` }}>
        {/* afishada ham kadr jonli: film to'xtab turgan rasm emas, boshlanishga tayyor sahna */}
        {!HARAKATSIZ && (
          <video src={`/akademiya/${sahna.tasvir}.mp4`} muted loop playsInline autoPlay preload="auto" aria-hidden="true" tabIndex={-1}
            ref={(v) => { if (v) { v.muted = true; v.play?.().catch(() => {}) } }} />
        )}
      </div>
      {i >= 0 && <audio ref={audio} src={`/akademiya/kino-${i + 1}.mp3`} preload="auto" />}

      {i < 0 ? (
        // Afisha: kino kabi — tepada-pastda qora tasmalar, o'rtada film nomi va katta «ijro» tugmasi (ega: «filmga o'xshamayapti»)
        <div className="ak-kino-boshi">
          <p className="ak-mono"><b>Libosa Academy</b> taqdim etadi</p>
          <h1 aria-label={NOM}><span aria-hidden="true">{NOM.slice(0, yozildi)}</span><i aria-hidden="true" /></h1>
          {/* harakat o'chirilgan qurilmada film o'zi boshlanmaydi — tugma bilan */}
          {HARAKATSIZ && <button type="button" className="ak-tugma" autoFocus onClick={() => setI(0)}>Ko'rish →</button>}
          <p className="ak-mono">Kirish filmi · {SAHNALAR.length} sahna · 36 soniya · ovoz va subtitr bilan</p>
          <button type="button" className="ak-matn-tugma" onClick={onYop}>O'tkazib yuborish →</button>
        </div>
      ) : (
        <div className="ak-kino-past">
          <div className="ak-kino-yol" role="img" aria-label={`${SAHNALAR.length} sahnadan ${i + 1}-si`}>
            {SAHNALAR.map((s, n) => <i key={s.tasvir} className={n < i ? 'otgan' : n === i ? 'hozir' : undefined} />)}
          </div>
          <p key={i} className="ak-kino-matn" aria-live="polite">{sahna.matn}</p>
          <div className="ak-kino-tugmalar">
            <button type="button" className="ak-tugma ikkinchi" aria-pressed={ovoz} onClick={() => setOvoz((x) => !x)}>
              {ovoz ? "Ovozni o'chirish" : 'Ovozni yoqish'}
            </button>
            {oxirgi
              ? <button type="button" className="ak-tugma" onClick={onTugadi || onYop}>Boshlash →</button>
              : <button type="button" className="ak-tugma" onClick={keyingi}>Keyingi →</button>}
            {!oxirgi && <button type="button" className="ak-matn-tugma" onClick={onYop}>O'tkazib yuborish</button>}
          </div>
        </div>
      )}
    </div>
  )
}

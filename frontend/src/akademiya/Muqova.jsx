import { useEffect, useRef, useState } from 'react'
import Kino from './Kino.jsx'
import { ASOSIY_MANZIL } from './host'

// Akademiyaning ochiq bosh sahifasi (ega talabi, 2026-11-15: «vau effekt beradigan video», kirish so'ralmasin).
// To'liq ekranli kino: to'rt sahna ustma-ust turadi, sahifa aylantirilganda keyingisi parda kabi pastdan ochilib chiqadi
// (chegarada ingichka tilla chiziq), har sahnaning yozuvi pastdan ko'tarilib chiqadi.
// «Boshlash» — mehmon sifatida ichkariga (uchta bepul dars); kirish o'sha darslar tugaganda so'raladi.
// joy — tor (tik) ekranda kadrning qaysi qismi ko'rinsin (qahramon yuzi kesilib qolmasin)
const SAHNALAR = [
  { tasvir: 'muqova-1', joy: '62%', matn: 'Nafislik tartibdan boshlanadi' },
  { tasvir: 'muqova-2', joy: '80%', matn: "Nodira opa — salon egasi. Ishni sizga u o'rgatadi" },
  { tasvir: 'muqova-3', joy: '74%', matn: 'Madina bugun birinchi kun ishda. Siz u bilan birga boshlaysiz' },
  { tasvir: 'muqova-4', joy: '50%', matn: '' },   // oxirgi sahnada yozuv o'rnida sarlavha va «Boshlash»
]
const N = SAHNALAR.length
const KINO = 'weddy.akademiya_kino'   // kirish filmi shu qurilmada ko'rilgan (DarsPaneli.jsx dagi bilan bir xil kalit)
const HARAKATSIZ = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const chekla = (v) => Math.min(1, Math.max(0, v))
// VAQTINCHA: ega yozuv uslubini tanlayapti — `?yozuv=b|c|d|k` boshqa variantni ko'rsatadi (standart — qalin tekis; k — eski kursiv); tanlangach olib tashlanadi
const YOZUV = new URLSearchParams(window.location.search).get('yozuv') || ''

export default function Muqova({ xato, band, onBoshla }) {
  const ildiz = useRef(null)
  // Kirish filmi akademiya ochilishi bilan chiqadi (ega talabi, 2026-11-15) — shu qurilmada birinchi marta. Oxiridagi
  // «Boshlash» to'g'ri darslarga olib kiradi; «O'tkazib yuborish» — shu bosh sahifaga.
  const [kino, setKino] = useState(() => { try { return !localStorage.getItem(KINO) } catch { return false } })
  const kinoYop = () => { try { localStorage.setItem(KINO, '1') } catch { /* saqlanmasa — keyingi safar yana chiqadi */ } setKino(false) }

  useEffect(() => {
    if (HARAKATSIZ) return undefined
    const el = ildiz.current
    const sahnalar = [...el.querySelectorAll('.ak-mq-sahna')]
    const yozuvlar = [...el.querySelectorAll('.ak-mq-yozuv')]
    while (yozuvlar.length < N) yozuvlar.push(null)
    const chokEl = el.querySelector('.ak-mq-chok')
    let kadr
    const chiz = () => {
      const yol = el.scrollHeight - window.innerHeight
      const p = yol > 0 ? chekla(window.scrollY / yol) : 0   // 0..1 — butun sahifa bo'ylab
      const o = p * (N - 1)                                   // 0..N-1 — sahnalar o'qi
      let chok = -1                                           // ochilayotgan sahna chegarasi (ekran balandligidan ulush)
      sahnalar.forEach((s, i) => {
        const m = Math.abs(o - i)                              // shu sahnadan masofa
        // Sahna almashuvi — parda: keyingi sahna pastdan tepaga ochilib chiqadi (erish ham, yaqinlashish ham yo'q —
        // ega talabi, 2026-11-15). t: 0 — hali yopiq, 1 — to'liq ochilgan.
        const t = i === 0 ? 1 : chekla((o - i + 0.75) / 0.5)
        const keyingi = i === N - 1 ? 0 : chekla((o - i - 0.25) / 0.5)   // ustidagi sahna qanchalik ochilgan
        s.style.clipPath = t >= 1 ? 'none' : `inset(${((1 - t) * 100).toFixed(2)}% 0 0 0)`
        if (t > 0 && t < 1) chok = 1 - t
        const v = s.querySelector('video')
        if (v) { if (t > 0 && keyingi < 1) { if (v.paused) v.play?.().catch(() => {}) } else if (!v.paused) v.pause() }
        // yozuv: sahna markaziga yaqinlashganda pastdan ko'tarilib chiqadi, uzoqlashganda tepaga ketadi
        const y = yozuvlar[i]
        if (y) {
          const k = chekla(1.7 - m * 3.4)
          y.style.opacity = k
          y.style.transform = `translateY(${((1 - k) * (o < i ? 44 : -44)).toFixed(1)}px)`
        }
      })
      chokEl.style.opacity = chok < 0 ? 0 : 1
      chokEl.style.top = `${(Math.max(chok, 0) * 100).toFixed(2)}%`
      el.style.setProperty('--p', p.toFixed(4))
      kadr = requestAnimationFrame(chiz)
    }
    kadr = requestAnimationFrame(chiz)
    return () => cancelAnimationFrame(kadr)
  }, [])

  const pastga = () => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })

  return (
    <div className={`ak-kirish ak-mq${HARAKATSIZ ? ' tinch' : ''}${YOZUV ? ` yozuv-${YOZUV}` : ''}`} ref={ildiz}>
      <header className="ak-mq-tepa">
        <span className="ak-mono"><i aria-hidden="true" /><b>Libosa Academy</b></span>
        <nav aria-label="Akademiyaga kirish">
          <button type="button" className="ak-tugma" disabled={band} onClick={onBoshla}>{band ? 'Tayyorlanmoqda…' : 'Boshlash →'}</button>
          <a className="ak-tugma ikkinchi" href={ASOSIY_MANZIL}>Kirish</a>
        </nav>
      </header>

      <div className="ak-mq-ekran">
        {SAHNALAR.map((s, i) => (
          <div key={s.tasvir} className="ak-mq-sahna" style={{ backgroundImage: `url(/akademiya/${s.tasvir}.jpg)`, clipPath: i && !HARAKATSIZ ? 'inset(100% 0 0 0)' : undefined, opacity: HARAKATSIZ && i ? 0 : 1, '--joy': s.joy }}>
            {!HARAKATSIZ && (
              <video src={`/akademiya/${s.tasvir}.mp4`} muted loop playsInline autoPlay={i === 0} preload={i < 2 ? 'auto' : 'metadata'}
                aria-hidden="true" tabIndex={-1} ref={(v) => { if (v) v.muted = true }} />
            )}
          </div>
        ))}
        <i className="ak-mq-chok" aria-hidden="true" />
        <div className="ak-mq-parda" aria-hidden="true" />
        {SAHNALAR.map((s, i) => s.matn && (
          <p key={s.tasvir} className="ak-mq-yozuv" style={{ opacity: i ? 0 : 1 }}>
            <small className="ak-mono">{`0${i + 1} / 0${N}`}</small>{s.matn}
          </p>
        ))}
        <div className="ak-mq-yakun">
          <h1>Salon ishini haqiqiy ilovaning o'zida o'rganing</h1>
          <p>Hikoya ichida, qadam-baqadam. Darslar bepul — hoziroq boshlang.</p>
          <button type="button" className="ak-tugma katta" disabled={band} onClick={onBoshla}>{band ? 'Tayyorlanmoqda…' : 'Boshlash →'}</button>
        </div>
        <button type="button" className="ak-mq-pastga" aria-label="Pastga" onClick={pastga}><i aria-hidden="true" />↓</button>
      </div>
      {kino && <Kino onYop={kinoYop} onTugadi={() => { kinoYop(); onBoshla() }} />}
      {/* xato sahifaning qayerida bo'lsa ham ko'rinadi («Boshlash» tepada ham, oxirida ham bor) */}
      {xato && <p className="ak-mq-xato" role="alert">{xato}</p>}
    </div>
  )
}

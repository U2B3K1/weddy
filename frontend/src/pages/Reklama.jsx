import { useEffect, useRef, useState } from 'react'
import { arizaYubor, xatoMatni } from '../api'
import { sahnaYarat } from './reklamaSahna'
import { BELGI_D } from './ezazBelgi'
import './reklama.css'
import './reklama-qasr.css'
import { QasrVideo } from './QasrVideo'
import { Kelinlar } from './Kelinlar'
import { Tashvishlar } from './Tashvishlar'
import { Yakun } from './Yakun'

// Bosh sahifa: loyihaning taqdimoti (lusion.co/about ruhida). Fon va zarracha shakllari WebGL'da chiziladi (reklamaSahna.js),
// arka sahnasida libos videosi ochiladi; bu fayl matn sahnalari, aylantirishga bog'liq harakat, kursor, ovoz va formalarni boshqaradi.

const KORILDI = 'weddy.reklama_korildi'
const tinch = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
// Faqat dev: ?sinov=0.35 — yuklanish ekranisiz, sahifaning shu ulushiga aylantirilgan holda ochadi (skrinshot bilan tekshirish uchun)
const SINOV = import.meta.env.DEV ? new URLSearchParams(window.location.search).get('sinov') : null
const chekla = (v, a, b) => Math.min(b, Math.max(a, v))

const YIL = new Date().getFullYear()   // futerdagi yil
const MENYU = [['imkoniyatlar', 'Imkoniyatlar'], ['azo', "A'zo bo'lish"]]

export default function Reklama({ onKirish }) {
  const ildiz = useRef(null)
  const tuval = useRef(null)
  const sahna = useRef(null)
  const aylantir = useRef(null)      // silliq aylantirish: (y) => void; yo'q bo'lsa oddiy scrollTo
  const menyuOchiq = useRef(false)
  const tovush = useRef(null)
  const [ochiq, setOchiq] = useState(() => { try { return SINOV !== null || !!sessionStorage.getItem(KORILDI) || tinch() } catch { return true } })
  const [menyu, setMenyu] = useState(false)
  const [ovoz, setOvoz] = useState(false)
  const [jonli, setJonli] = useState(() => !tinch())

  // WebGL sahnasi: bo'lmasa (yoki harakat kamaytirilgan bo'lsa) sahifa oddiy gradient fonda ishlaydi.
  useEffect(() => {
    if (tinch()) return undefined
    const s = sahnaYarat(tuval.current)
    if (!s) { setJonli(false); return undefined }
    sahna.current = s
    if (import.meta.env.DEV) window.__sahna = s   // brauzer konsolidan sahnani sinash uchun
    return () => { s.yop(); sahna.current = null }
  }, [])

  // Aylantirishga bog'liq harakat: har sahnaga 0..1 oralig'idagi --p, bosh kadr uchun --bp, fondagi shakl uchun T, tezlik --tez.
  useEffect(() => {
    const el = ildiz.current
    if (!el || !ochiq) return undefined
    const sahnalar = [...el.querySelectorAll('[data-sahna]')]
    const langarlar = [...el.querySelectorAll('[data-t]')].map((x) => ({ x, t: Number(x.dataset.t) }))
    const bosh = el.querySelector('.rk-bosh')
    const kirlar = [...el.querySelectorAll('[data-kir]')]   // ekranni to'liq egallamaguncha qorong'i turadigan bo'limlar (a'zo, kelinlar, imkoniyatlar, yakun) — hammasida bir xil kirish
    let kadr = 0, oldingiY = window.scrollY, tinchlanish = 0
    const hisobla = () => {
      kadr = 0
      const vh = window.innerHeight
      const jami = document.documentElement.scrollHeight - vh
      el.style.setProperty('--jami', jami > 0 ? (window.scrollY / jami).toFixed(4) : '0')
      el.classList.toggle('rk-aylandi', window.scrollY > 40)
      // Aylantirish tezligi: lentalar shunga qarab qiyshayadi, to'xtaganda qaytadi
      el.style.setProperty('--tez', chekla((window.scrollY - oldingiY) / 60, -1, 1).toFixed(3))
      oldingiY = window.scrollY
      clearTimeout(tinchlanish)
      tinchlanish = setTimeout(() => el.style.setProperty('--tez', '0'), 140)
      sahnalar.forEach((s) => {
        const r = s.getBoundingClientRect()
        const yol = r.height - vh
        // baland sahna — ichidagi yo'l; qolgani — ekrandan o'tishi
        const xom = yol > 0 ? -r.top / yol : (vh - r.top) / (vh + r.height)
        const p = chekla(xom, 0, 1)
        s.style.setProperty('--p', p.toFixed(4))
        if (s === bosh) el.style.setProperty('--bp', p.toFixed(4))
      })
      kirlar.forEach((k) => k.style.setProperty('--kir', chekla(1 - k.getBoundingClientRect().top / (vh * .3), 0, 1).toFixed(3)))
      // Fondagi shakl: ekran markaziga eng yaqin ikki langar orasida silliq o'tadi
      const m = langarlar.map((l) => { const r = l.x.getBoundingClientRect(); return { t: l.t, c: r.top + r.height / 2 - vh / 2 } })
      let T = m[0].t
      for (let i = 0; i < m.length; i++) {
        if (m[i].c > 0) break
        const k = m[i + 1]
        T = k && k.c > m[i].c ? m[i].t + (k.t - m[i].t) * Math.min(1, -m[i].c / (k.c - m[i].c)) : m[i].t
      }
      sahna.current?.sahnaga(T)
    }
    const aylan = () => { if (!kadr) kadr = requestAnimationFrame(hisobla) }
    const kuzat = new IntersectionObserver((yozuvlar) => {
      yozuvlar.forEach((y) => { if (y.isIntersecting) { y.target.classList.add('rk-koring'); kuzat.unobserve(y.target) } })
    }, { threshold: 0.15 })
    el.querySelectorAll('.rk-ochil').forEach((x) => kuzat.observe(x))
    hisobla()
    if (import.meta.env.DEV) window.__hisobla = hisobla
    let sinov = 0
    if (SINOV !== null) {
      sinov = setTimeout(() => {
        window.scrollTo(0, Number(SINOV) * (document.documentElement.scrollHeight - window.innerHeight))
        hisobla()
        if (sahna.current) sahna.current.darhol(sahna.current.holat().maqsad)
        el.querySelectorAll('.rk-ochil').forEach((x) => x.classList.add('rk-koring'))
      }, 400)
    }
    window.addEventListener('scroll', aylan, { passive: true })
    window.addEventListener('resize', aylan)
    return () => {
      window.removeEventListener('scroll', aylan); window.removeEventListener('resize', aylan)
      kuzat.disconnect(); cancelAnimationFrame(kadr); clearTimeout(tinchlanish); clearTimeout(sinov)
    }
  }, [ochiq])

  // Silliq aylantirish: g'ildirak maqsadni suradi, sahifa unga inersiya bilan yetib oladi. Brauzerning o'z aylantirishi saqlanadi
  // (klaviatura, teginish, aylantirish chizig'i ishlayveradi), shuning uchun yopishqoq sahnalar buzilmaydi.
  useEffect(() => {
    if (!ochiq || tinch()) return undefined
    let maqsad = window.scrollY, joriy = maqsad, kadr = 0
    const chegara = () => document.documentElement.scrollHeight - window.innerHeight
    const qadam = () => {
      joriy += (maqsad - joriy) * 0.11
      if (Math.abs(maqsad - joriy) < 0.5) { joriy = maqsad; kadr = 0 } else kadr = requestAnimationFrame(qadam)
      window.scrollTo(0, joriy)
    }
    const gildirak = (e) => {
      if (e.ctrlKey || e.target.closest?.('textarea')) return
      e.preventDefault()
      if (menyuOchiq.current) return
      const d = e.deltaMode === 1 ? e.deltaY * 32 : e.deltaMode === 2 ? e.deltaY * window.innerHeight : e.deltaY
      maqsad = chekla(maqsad + d, 0, chegara())
      if (!kadr) kadr = requestAnimationFrame(qadam)
    }
    // Boshqa yo'l bilan aylantirilsa (klaviatura, chiziq, teginish) — maqsad shu joyga tenglashadi
    const aylandi = () => { if (!kadr) maqsad = joriy = window.scrollY }
    aylantir.current = (y) => { maqsad = chekla(y, 0, chegara()); joriy = window.scrollY; if (!kadr) kadr = requestAnimationFrame(qadam) }
    window.addEventListener('wheel', gildirak, { passive: false })
    window.addEventListener('scroll', aylandi, { passive: true })
    return () => { cancelAnimationFrame(kadr); aylantir.current = null; window.removeEventListener('wheel', gildirak); window.removeEventListener('scroll', aylandi) }
  }, [ochiq])

  // Menyu: Esc bilan yopiladi, ochiq paytda sahifa aylanmaydi
  useEffect(() => {
    menyuOchiq.current = menyu
    if (!menyu) return undefined
    const tugma = (e) => { if (e.key === 'Escape') setMenyu(false) }
    window.addEventListener('keydown', tugma)
    return () => window.removeEventListener('keydown', tugma)
  }, [menyu])

  useEffect(() => () => { tovush.current?.yop() }, [])

  const ot = (id) => (e) => {
    e?.preventDefault(); setMenyu(false)
    const nishon = document.getElementById(id)
    if (!nishon) return
    const y = nishon.getBoundingClientRect().top + window.scrollY
    if (aylantir.current) aylantir.current(y); else window.scrollTo(0, y)
  }
  const kirdi = () => { try { sessionStorage.setItem(KORILDI, '1') } catch { /* saqlanmasa ham ishlaydi */ } setOchiq(true) }
  // Ovoz standart holatda o'chiq; birinchi bosishda (foydalanuvchi harakati) WebAudio yaratiladi
  const ovozAlmash = () => {
    if (!tovush.current) tovush.current = tovushYarat()
    if (!tovush.current) return
    tovush.current.yoq(!ovoz); setOvoz(!ovoz)
  }

  return (
    <div className={`rk ${ochiq ? 'rk-ochiq' : 'rk-yopiq'} ${jonli ? '' : 'rk-statik'} ${menyu ? 'rk-menyuli' : ''}`} ref={ildiz}>
      <canvas className="rk-sahna" ref={tuval} aria-hidden="true" />
      {jonli && <QasrVideo />}
      <span className="rk-soya" aria-hidden="true" />
      <span className="rk-tor" aria-hidden="true"><i /><i /><i /><i /><i /></span>
      {jonli && <Iz tovush={tovush} />}
      {!ochiq && <Yuklanish onTayyor={kirdi} />}

      <div className="rk-nav">
        <a className="rk-logo" href="#bosh" onClick={ot('bosh')}><Belgi /><span>LIBOSA</span></a>
        <div className="rk-nav-ong">
          <button className={`rk-dumaloq ${ovoz ? 'rk-ovozli' : ''}`} aria-label={ovoz ? "Ovozni o'chirish" : 'Ovozni yoqish'} aria-pressed={ovoz}
            onClick={ovozAlmash} data-magnit><i /><i /><i /></button>
          <a className="rk-pill rk-pill-toq" href="#azo" onClick={ot('azo')} data-magnit>A'zo bo'lish<b>•</b></a>
          <button className="rk-pill" aria-expanded={menyu} aria-controls="rk-menyu" onClick={() => setMenyu(!menyu)} data-magnit>
            {menyu ? 'Yopish' : 'Menyu'}<b>••</b>
          </button>
        </div>
      </div>

      <div className="rk-menyu" id="rk-menyu" aria-hidden={!menyu} inert={!menyu}>
        <div className="rk-menyu-havolalar">
          {MENYU.map(([id, nom], i) => (
            <a key={id} href={`#${id}`} onClick={ot(id)} style={{ '--i': i }}><span><small>{`0${i + 1}`}</small>{nom}</span></a>
          ))}
          <button onClick={() => { setMenyu(false); onKirish() }} style={{ '--i': MENYU.length }}><span><small>→</small>Kirish</span></button>
        </div>
        <p className="rk-menyu-oyoq">Libosa — kelin liboslari salonlari uchun ijara tizimi</p>
      </div>
      <span className="rk-yol-chizigi" aria-hidden="true"><i /></span>

      {/* 1-sahna: bosh kadr. Ulkan so'z-belgi harflari aylantirganda qayrilib ketadi, ortidan bayonot qatorma-qator chiqadi. */}
      <div className="rk-bosh" id="bosh" data-sahna data-t="0">
        <div className="rk-bosh-sahna">
          <p className="rk-bosh-ustki">Kelin liboslari salonlari uchun<br />ijara tizimi</p>
          <div className="rk-bayonot">
            <div className="rk-bayonot-chap">
              <h1>
                <Qator j={0}>Kelin liboslari</Qator><Qator j={1}>salonlari uchun</Qator><Qator j={2}>ijara tizimi</Qator>
              </h1>
              <div className="rk-amallar">
                <a className="rk-tugma" href="#azo" onClick={ot('azo')} data-magnit><span>A'zo bo'lish</span></a>
                <button className="rk-tugma rk-tugma-chiziq" onClick={onKirish} data-magnit><span>Kirish</span></button>
              </div>
            </div>
            <p className="rk-bayonot-ong">
              <Qator j={3}>Har bir libos qayerda,</Qator><Qator j={4}>kimda va qachon qaytadi</Qator>
            </p>
          </div>
          <div className="rk-sozbelgi" aria-hidden="true">
            {[...'LIBOSA'].map((h, i) => <span key={i} style={{ '--i': i }}><b>{h}</b></span>)}
          </div>
          <a className="rk-pastga" href="#sahnalar" onClick={ot('sahnalar')}>Pastga aylantiring<i /></a>
        </div>
      </div>

      {/* 2-sahna: kelin obrazlari gologrammasi (Lusion TEAM uslubida), keyin «Imkoniyatlar» slayderi (Orano "Innovation"
          uslubida: tilla sim-karkas fonlar va milliy libosdagi tilla kelinlar). Slayder avvalgi «Uch tashvish» va
          «Imkoniyatlar» o'yin kartalarini birlashtiradi — menyudagi #imkoniyatlar shu yerga olib keladi. */}
      <div id="sahnalar" style={{ position: 'relative' }}>
        {/* fondagi zarrachalar shu oraliqda tinch "chang" shaklida turadi (kartalar ortida ko'rinadi) */}
        <i className="rk-langar" data-t="1" style={{ top: 0 }} />
        <i className="rk-langar" data-t="1" style={{ bottom: 0 }} />
        <Kelinlar />
        <Tashvishlar />
      </div>

      {/* 3-sahna: yakuniy qism (jjettas.com + atlasmotion.com uslubida) — «Imkoniyatlar» slaydidan keyin
          uchta yopishqoq sahna: Chaqiriq («Saloningiz Libosaga tayyormi?») → Raqamlar (gologramma guldasta)
          → Kirish (to'liq ekranli video). Yakun.jsx da. */}
      <Yakun onAzo={ot('azo')} />

      {/* 7-sahna: a'zo bo'lish */}
      <div className="rk-azo-yol">
      <div className="rk-azo" id="azo" data-kir>
        {/* fon: anime uslubidagi yomg'irli bog' (public/yakun/bog.mp4 — 2026-10-11 da Kie'da yaratilgan, uzluksiz aylanadi) */}
        <video className="rk-azo-video" src="/yakun/bog.mp4" poster="/yakun/bog.jpg" muted autoPlay loop playsInline preload="metadata" aria-hidden="true" />
        <div className="rk-azo-matn rk-ochil">
          <p className="rk-ustki">A'zo bo'lish</p>
          <h2 className="rk-h2">Saloningizni <em>Libosada</em> ko'ring</h2>
          <p className="rk-lid">So'rov qoldiring — siz bilan bog'lanib, salon uchun login ochib beramiz. Yangi salon 14 kun bepul sinov bilan ulanadi.</p>
          <ul className="rk-belgilar">
            <li>Liboslaringizni o'zingiz kiritasiz</li>
            <li>Planshet, telefon yoki kompyuterdan ishlaydi</li>
            <li>Tizimga faqat siz ruxsat bergan qurilmadan kiriladi</li>
          </ul>
        </div>
        <ArizaForma tur="azo" />
      </div>
      </div>

      {/* Oyoq: ixcham — logo, katta «Tizimga kirish» va ingichka pastki tasma */}
      <footer className="rk-oyoq">
        <span className="rk-oyoq-brend"><Belgi /><b>LIBOSA</b></span>
        <button className="rk-keyingi" onClick={onKirish} data-kursor="Kirish" data-magnit>
          <b>Tizimga kirish</b>
          <span className="rk-keyingi-yol"><i />→</span>
        </button>
        <div className="rk-oyoq-past">
          <span>© {YIL} Libosa</span>
          <button className="rk-tepaga" aria-label="Tepaga" onClick={ot('bosh')} data-magnit>↑</button>
        </div>
      </footer>
    </div>
  )
}

// Libos videosi (arka ichida). Sahna ekrandan chiqsa to'xtaydi; harakat kamaytirilgan bo'lsa faqat harakatsiz surat ko'rsatiladi.
function BoshVideo({ jonli }) {
  const ref = useRef(null)
  const [tor] = useState(() => window.matchMedia('(max-aspect-ratio: 11/10)').matches)
  const nom = tor ? 'bosh_tor' : 'bosh_keng'
  useEffect(() => {
    const v = ref.current, bosh = v?.closest('.rk-arka')
    if (!v || !bosh || !jonli) return undefined
    const kuzat = new IntersectionObserver(([y]) => { if (y.isIntersecting) v.play().catch(() => {}); else v.pause() })
    kuzat.observe(bosh)
    return () => kuzat.disconnect()
  }, [jonli])
  if (!jonli) return <img className="rk-video" src={`/video/${nom}.jpg`} alt="" aria-hidden="true" />
  return (
    <video className="rk-video" ref={ref} poster={`/video/${nom}.jpg`} muted loop playsInline autoPlay preload="metadata" aria-hidden="true">
      <source src={`/video/${nom}.webm`} type="video/webm" />
      <source src={`/video/${nom}.mp4`} type="video/mp4" />
    </video>
  )
}

// Bayonot qatori: niqob ichidan ko'tariladi (bosh kadr yo'liga bog'langan, --j — navbati).
function Qator({ j, children }) {
  return <span className="rk-qator" style={{ '--j': j }}><span>{children}</span></span>
}

// Imkoniyat kartalari: kursor ustida karta 3D'da egiladi. Pastida nomi teskari yozilgan — o'yin kartasi kabi.
// Yuklanish ekrani: foiz sanaladi, tugma bosilgach ekran tuman bo'lib erib ketadi.
function Yuklanish({ onTayyor }) {
  const [foiz, setFoiz] = useState(0)
  const [ketmoqda, setKetmoqda] = useState(false)
  const video = useRef(null)
  useEffect(() => {
    // Foiz fon videosining vaqtiga bog'lanadi: osmon.mp4 da bulutlar tarqalib saroy
    // ~8.5 soniyada to'liq ko'rinadi — o'sha lahzagacha ekran «tayyor» bo'lmaydi.
    const REVEAL = 8.5
    const v = video.current
    let yakun = false, zaxira = null, taymer = null
    const bitir = () => {
      if (yakun) return
      yakun = true
      setFoiz(100); v?.pause()   // saroy kadrida qotib qoladi
      if (taymer) clearInterval(taymer)
      if (zaxira) clearTimeout(zaxira)
    }
    const surish = () => {
      if (yakun || !v?.duration) return
      const p = Math.min(1, v.currentTime / REVEAL)
      setFoiz(Math.round((1 - (1 - p) ** 3) * 100))
      if (p >= 1) bitir()
    }
    // Zaxira: video yuklanmasa/ishlamasa 2.5 s ichida eski usuldagi taymerga o'tib, sahifa osilib qolmaydi
    const taymerli = () => {
      if (yakun) return
      const bosh = performance.now()
      taymer = setInterval(() => {
        const p = Math.min(1, (performance.now() - bosh) / 1600)
        setFoiz(Math.round((1 - (1 - p) ** 3) * 100))
        if (p >= 1) bitir()
      }, 30)
    }
    v?.addEventListener('timeupdate', surish)
    v?.addEventListener('error', () => { if (zaxira) clearTimeout(zaxira); taymerli() })
    v?.play?.().catch(() => {})
    zaxira = setTimeout(taymerli, 2500)
    return () => {
      if (zaxira) clearTimeout(zaxira)
      if (taymer) clearInterval(taymer)
      v?.removeEventListener('timeupdate', surish)
      v?.removeEventListener('error', () => {})
    }
  }, [])
  const kir = () => { setKetmoqda(true); setTimeout(onTayyor, 1100) }
  return (
    <div className={`rk-yuklanish ${ketmoqda ? 'rk-ketmoqda' : ''}`}>
      {/* fon: tilla bulutli osmon (osmon.mp4) — «Xush kelibsiz» ekrani sarg'ish pardada; bulutlar tarqalib saroy ko'ringanda to'xtaydi */}
      <video ref={video} className="rk-yuklanish-video" src="/yakun/osmon.mp4" poster="/yakun/osmon.jpg" muted autoPlay playsInline preload="auto" aria-hidden="true" />
      <div className="rk-yuklanish-ichki">
        <Belgi />
        <p className="rk-foiz">{foiz}%</p>
        <span className="rk-foiz-chiziq"><i style={{ transform: `scaleX(${foiz / 100})` }} /></span>
        <p className="rk-foiz-matn">{foiz < 100 ? 'Tayyorlanmoqda' : 'Tayyor'}</p>
        <button className="rk-kirish-btn" disabled={foiz < 100} onClick={kir}>
          <b>Xush kelibsiz</b><span>Sahifani ochish</span>
        </button>
      </div>
    </div>
  )
}

// EZAZ malika belgisi; atrofidagi nuqtali halqa sekin aylanadi.
function Belgi() {
  return (
    <svg className="rk-belgi" viewBox="-60 -40 640 640" aria-hidden="true">
      <circle className="rk-belgi-halqa" cx="260" cy="280" r="300" fill="none" stroke="currentColor" strokeWidth="10" strokeDasharray="20 52" />
      <path d={BELGI_D} fill="currentColor" />
    </svg>
  )
}

// Ovoz (ixtiyoriy, standart o'chiq): WebAudio'da sintez qilingan yumshoq akkord va tugma ustidagi qisqa «chink».
function tovushYarat() {
  const Sinf = window.AudioContext || window.webkitAudioContext
  if (!Sinf) return null
  const c = new Sinf()
  const asosiy = c.createGain(); asosiy.gain.value = 0; asosiy.connect(c.destination)
  const filtr = c.createBiquadFilter(); filtr.type = 'lowpass'; filtr.frequency.value = 850; filtr.connect(asosiy)
  ;[110, 164.81, 220.4, 329.63].forEach((chastota, i) => {
    const o = c.createOscillator(); o.type = i % 2 ? 'triangle' : 'sine'; o.frequency.value = chastota
    const g = c.createGain(); g.gain.value = 0.05
    const tebr = c.createOscillator(); tebr.frequency.value = 0.07 + i * 0.03
    const tg = c.createGain(); tg.gain.value = 0.03
    tebr.connect(tg); tg.connect(g.gain); o.connect(g); g.connect(filtr); o.start(); tebr.start()
  })
  let yoniq = false
  return {
    yoq: (b) => { yoniq = b; if (b) c.resume(); asosiy.gain.setTargetAtTime(b ? 0.55 : 0, c.currentTime, 0.5) },
    chink: () => {
      if (!yoniq) return
      const o = c.createOscillator(), g = c.createGain(), t = c.currentTime
      o.type = 'sine'; o.frequency.setValueAtTime(1320, t); o.frequency.exponentialRampToValueAtTime(1980, t + 0.09)
      g.gain.setValueAtTime(0.045, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.22)
      o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + 0.24)
    },
    yop: () => { c.close().catch(() => {}) },
  }
}

// Kursor: nuqta, yulduzcha uchqun izi, magnitli tugmalar (faqat sichqoncha bor qurilmada).
function Iz({ tovush }) {
  const tuval = useRef(null)
  const nuqta = useRef(null)
  useEffect(() => {
    const c = tuval.current
    if (!c || !window.matchMedia('(pointer: fine)').matches) return undefined
    const x = c.getContext('2d')
    const uchqunlar = []
    let kadr = 0, w = 0, h = 0, mx = -100, my = -100, oldingi = null, magnit = null, ustida = null
    const olcham = () => {
      const d = Math.min(window.devicePixelRatio || 1, 2)
      w = window.innerWidth; h = window.innerHeight
      c.width = w * d; c.height = h * d; x.setTransform(d, 0, 0, d, 0, 0)
    }
    olcham()
    const yulduz = (u) => {
      const s = u.o * u.umr
      x.save(); x.translate(u.x, u.y); x.rotate(u.a); x.globalAlpha = u.umr; x.fillStyle = u.rang
      x.beginPath()
      for (let i = 0; i < 8; i++) { const rad = i % 2 ? s * 0.28 : s, th = (i / 8) * Math.PI * 2; x.lineTo(Math.cos(th) * rad, Math.sin(th) * rad) }
      x.closePath(); x.fill(); x.restore()
    }
    const chiz = () => {
      kadr = 0
      x.clearRect(0, 0, w, h)
      for (let i = uchqunlar.length - 1; i >= 0; i--) {
        const u = uchqunlar[i]
        u.umr -= 0.022; u.x += u.vx; u.y += u.vy; u.vy += 0.03; u.a += 0.05
        if (u.umr <= 0) uchqunlar.splice(i, 1); else yulduz(u)
      }
      if (uchqunlar.length) kadr = requestAnimationFrame(chiz)
    }
    const qoyib = () => { if (magnit) { magnit.style.transform = ''; magnit = null } }
    const surildi = (e) => {
      mx = e.clientX; my = e.clientY
      if (nuqta.current) { nuqta.current.style.transform = `translate3d(${mx}px, ${my}px, 0)`; nuqta.current.style.opacity = '1' }
      const nishon = e.target instanceof Element ? e.target : null
      // Magnit: tugma kursorga 14 px gacha tortiladi
      const m = nishon?.closest('[data-magnit]') || null
      if (m !== magnit) qoyib()
      if (m) {
        const r = m.getBoundingClientRect()
        const dx = chekla((mx - r.left - r.width / 2) * 0.32, -14, 14), dy = chekla((my - r.top - r.height / 2) * 0.32, -14, 14)
        m.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px)`
        magnit = m
      }
      // Tugma ustiga kirgandagi ovoz
      const faol = nishon?.closest('a, button, [data-magnit], .rk-karta, input, textarea') || null
      if (faol !== ustida) { ustida = faol; if (faol?.matches('a, button')) tovush.current?.chink() }
      const yol = oldingi ? Math.hypot(mx - oldingi[0], my - oldingi[1]) : 0
      if (yol > 14 && uchqunlar.length < 70) {
        oldingi = [mx, my]
        uchqunlar.push({
          x: mx + (Math.random() - 0.5) * 14, y: my + (Math.random() - 0.5) * 14, vx: (Math.random() - 0.5) * 1.2, vy: -Math.random() * 1.1,
          o: 4 + Math.random() * 7, umr: 1, a: Math.random() * 3, rang: Math.random() < 0.6 ? '#e4c196' : '#fbf6ee',
        })
      } else if (!oldingi) oldingi = [mx, my]
      if (!kadr) kadr = requestAnimationFrame(chiz)
    }
    const chiqdi = () => { qoyib(); if (nuqta.current) nuqta.current.style.opacity = '0' }
    window.addEventListener('resize', olcham)
    window.addEventListener('pointermove', surildi, { passive: true })
    document.documentElement.addEventListener('pointerleave', chiqdi)
    return () => {
      cancelAnimationFrame(kadr); qoyib()
      window.removeEventListener('resize', olcham); window.removeEventListener('pointermove', surildi)
      document.documentElement.removeEventListener('pointerleave', chiqdi)
    }
  }, [tovush])
  return (
    <>
      <canvas className="rk-iz" ref={tuval} aria-hidden="true" />
      <span className="rk-nuqta" ref={nuqta} aria-hidden="true" />
    </>
  )
}

function ArizaForma({ tur }) {
  const azo = tur === 'azo'
  const [f, setF] = useState({ ism: '', telefon: '', salon_nomi: '', xabar: '', sayt: '' })
  const [holat, setHolat] = useState({ turi: '', matn: '' })
  const [yuborilmoqda, setYuborilmoqda] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const tayyor = f.ism.trim() && /^\+?[0-9 ()-]{7,20}$/.test(f.telefon.trim()) && (azo || f.xabar.trim())
  const yubor = async (e) => {
    e.preventDefault()
    setYuborilmoqda(true); setHolat({ turi: '', matn: '' })
    try {
      await arizaYubor({ ...f, tur, ism: f.ism.trim(), telefon: f.telefon.trim() })
      setHolat({ turi: 'ok', matn: azo ? "So'rovingiz qabul qilindi. Tez orada bog'lanamiz." : 'Xabaringiz yuborildi. Rahmat!' })
      setF({ ism: '', telefon: '', salon_nomi: '', xabar: '', sayt: '' })
    } catch (x) {
      setHolat({ turi: 'xato', matn: xatoMatni(x, "Yuborib bo'lmadi. Keyinroq urinib ko'ring.") })
    } finally { setYuborilmoqda(false) }
  }
  return (
    <form className="rk-forma rk-ochil" onSubmit={yubor} noValidate>
      <label>Ismingiz<input value={f.ism} maxLength={200} autoComplete="name" onChange={set('ism')} /></label>
      <label>Telefon<input value={f.telefon} maxLength={20} inputMode="tel" autoComplete="tel" placeholder="+998 90 123 45 67" onChange={set('telefon')} /></label>
      {azo && <label>Salon nomi<input value={f.salon_nomi} maxLength={200} onChange={set('salon_nomi')} /></label>}
      <label>{azo ? "Qo'shimcha (ixtiyoriy)" : 'Xabar'}
        <textarea value={f.xabar} maxLength={1000} rows={azo ? 2 : 4} onChange={set('xabar')} />
      </label>
      <input className="rk-tuzoq" tabIndex={-1} autoComplete="off" aria-hidden="true" value={f.sayt} onChange={set('sayt')} />
      <button className="rk-tugma" type="submit" disabled={!tayyor || yuborilmoqda}>
        <span>{yuborilmoqda ? 'Yuborilmoqda…' : azo ? "So'rov qoldirish" : 'Yuborish'}</span>
      </button>
      {holat.matn && <p className={`rk-forma-holat ${holat.turi}`} role="status">{holat.matn}</p>}
    </form>
  )
}

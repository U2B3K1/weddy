// "Kartalar" bo'limi — Lusion /about sahifasidagi "Area of Expertise" kartalari uslubida.
// Kino bo'limidagi uch ma'lumot (Bron, Zalog, Foyda) uchta o'yin kartasiga joylangan:
// boshida kartalar dasta bo'lib turadi (orqa tomoni — tilla naqsh va arkada kelin libosi),
// aylantirganda yelpig'ichdek yoyiladi, orqadan tilla lenta chiziladi, keyin kartalar birin-ketin
// ag'darilib, old tomonidagi ma'lumot ochiladi. Kursor karta ustida — karta unga qarab egiladi;
// kartani bossangiz qo'lda ag'darib ko'rish mumkin.
//
// Qayerga: src/pages/Kartalar.jsx (kartalar.css shu papkada). Rasmlar: public/kelinlar/1–3.jpg.
// Reklama.jsx da kino bo'limi (<div className="rk-kino">…</div>) o'rniga:  <Kartalar />
import { useEffect, useRef } from 'react'
import './kartalar.css'

const KARTALAR = [
  { nom: 'Bron', harf: 'B', rasm: '/kelinlar/1.jpg', shior: 'Bitta libos — ikki kelin emas',
    qatorlar: ['Daftarda sana chalkashadi.', "Libosada band libosni ikkinchi marta bron qilib bo'lmaydi.", "Buni tizimning o'zi tekshiradi."] },
  { nom: 'Zalog', harf: 'Z', rasm: '/kelinlar/2.jpg', shior: 'Zalog kimda qolgani',
    qatorlar: ['Pul, hujjat yoki tillo —', 'har biri yorliq bilan yoziladi', "va kun oxirida «joyida» deb belgilanadi."] },
  { nom: 'Foyda', harf: 'F', rasm: '/kelinlar/3.jpg', shior: 'Oy oxirida foyda qancha',
    qatorlar: ['Tushum va xarajat,', "bonuslar yig'iladi —", "foyda-zarar o'zi chiqadi."] },
]

// Lusion'dagi blokli bosh harf — 5×7 piksel
const PIKSEL = {
  B: ['11110', '10001', '10001', '11110', '10001', '10001', '11110'],
  Z: ['11111', '00001', '00010', '00100', '01000', '10000', '11111'],
  F: ['11111', '10000', '10000', '11110', '10000', '10000', '10000'],
}
function Belgi({ harf }) {
  return (
    <svg className="rk-okarta-belgi" viewBox="0 0 50 70" aria-hidden="true">
      {PIKSEL[harf].flatMap((q, y) => [...q].map((b, x) => b === '1' && <rect key={x + '-' + y} x={x * 10} y={y * 10} width="10" height="10" fill="currentColor" />))}
    </svg>
  )
}

// Orqa tomon naqshi — o'yin kartasining art-deko ramkasi, tilla chiziqlar
const NURLAR = Array.from({ length: 40 }, (_, k) => { const a = (k / 40) * Math.PI * 2; return [125 + Math.cos(a) * 260, 175 + Math.sin(a) * 260] })
function Naqsh({ id }) {
  return (
    <svg viewBox="0 0 250 350" preserveAspectRatio="none" aria-hidden="true">
      <defs><clipPath id={'kq' + id}><rect x="20" y="20" width="210" height="310" rx="6" /></clipPath></defs>
      <g stroke="#e4c196" fill="none">
        <g clipPath={`url(#kq${id})`} strokeOpacity=".28" strokeWidth=".8">
          {NURLAR.map(([x, y], k) => <line key={k} x1="125" y1="175" x2={x} y2={y} />)}
        </g>
        <rect x="11" y="11" width="228" height="328" rx="9" strokeWidth="1.4" />
        <rect x="20" y="20" width="210" height="310" rx="6" strokeOpacity=".6" />
        <polygon points="125,44 222,175 125,306 28,175" strokeOpacity=".7" />
        {[[20, 20, 0], [230, 20, 90], [230, 330, 180], [20, 330, 270]].map(([x, y, r], k) => (
          <path key={k} d="M0,34 A34,34 0 0 0 34,0 M0,22 A22,22 0 0 0 22,0" transform={`translate(${x},${y}) rotate(${r})`} strokeOpacity=".8" />
        ))}
        {[32, 318].map((y) => <circle key={y} cx="125" cy={y} r="8" fill="#142338" strokeWidth="1.2" />)}
        {Array.from({ length: 8 }, (_, k) => 92 + k * 24).flatMap((y) => [<circle key={'a' + y} cx="31" cy={y} r="2" />, <circle key={'b' + y} cx="219" cy={y} r="2" />])}
      </g>
      <g fill="#e4c196" fontFamily="'Casagrande Deco', Forum, Georgia, serif" fontSize="9" textAnchor="middle">
        <text x="125" y="35.5">W</text><text x="125" y="321.5" transform="rotate(180 125 318)">W</text>
      </g>
    </svg>
  )
}

const qisq = (x, a, b) => Math.min(1, Math.max(0, (x - a) / (b - a)))
const silliq = (x, a, b) => { const t = qisq(x, a, b); return t * t * (3 - 2 * t) }

export function OyinKartalar() {
  const bolim = useRef(null), kartalar = useRef([]), qolda = useRef([0, 0, 0])

  useEffect(() => {
    const B = bolim.current
    if (!matchMedia('(min-width: 900px) and (min-aspect-ratio: 11/10)').matches) return
    let kadr = 0
    const olch = () => {
      kadr = 0
      const r = B.getBoundingClientRect(), yol = r.height - innerHeight
      const p = Math.min(1, Math.max(0, -r.top / yol))
      B.style.setProperty('--fan', silliq(p, .10, .40).toFixed(4))
      B.style.setProperty('--tek', silliq(p, .70, .88).toFixed(4))
      B.style.setProperty('--sarl', silliq(p, .08, .26).toFixed(4))
      B.style.setProperty('--lenta', silliq(p, .15, .80).toFixed(4))
      B.style.setProperty('--ket', silliq(p, .93, 1).toFixed(4))
      kartalar.current.forEach((k, i) => {
        const f = silliq(p, .40 + i * .1, .56 + i * .1)
        k.style.setProperty('--flip', (qolda.current[i] ? 1 - f : f).toFixed(4))
      })
    }
    const surish = () => { if (!kadr) kadr = requestAnimationFrame(olch) }
    addEventListener('scroll', surish, { passive: true }); addEventListener('resize', surish); olch()
    return () => { cancelAnimationFrame(kadr); removeEventListener('scroll', surish); removeEventListener('resize', surish) }
  }, [])

  // Kursor egilishi: karta markaziga nisbatan -0.5..0.5
  const egil = (e, i) => {
    const k = kartalar.current[i], r = k.getBoundingClientRect()
    k.style.setProperty('--mx', ((e.clientX - r.left) / r.width - .5).toFixed(3))
    k.style.setProperty('--my', ((e.clientY - r.top) / r.height - .5).toFixed(3))
  }
  const tekis = (i) => { const k = kartalar.current[i]; k.style.setProperty('--mx', 0); k.style.setProperty('--my', 0) }
  const agdar = (i) => {
    qolda.current[i] ^= 1
    const k = kartalar.current[i], f = parseFloat(k.style.getPropertyValue('--flip') || 0)
    k.style.setProperty('--flip', (1 - f).toFixed(4))
  }

  return (
    <div className="rk-kartalar" ref={bolim} id="tashvishlar" data-sahna>
      <div className="rk-kar-yopishqoq">
        <h2 className="rk-kar-sarlavha">Uch tashvish —<br /><em>bitta tizim</em></h2>
        <p className="rk-kar-izoh">Bron, zalog va foyda — salonning uch og'riqli nuqtasi, Libosada bir joyda
          <br /><i /><i /><i />
        </p>

        <svg className="rk-kar-lenta" viewBox="0 0 1600 900" preserveAspectRatio="none" aria-hidden="true">
          <defs>
            <linearGradient id="rk-lenta-g" x1="0" x2="1" y1="1" y2="0">
              <stop offset="0" stopColor="#b08a5a" /><stop offset=".5" stopColor="#e4c196" /><stop offset="1" stopColor="#fbf6ee" />
            </linearGradient>
          </defs>
          <path d="M-40,760 C260,700 360,420 640,430 C920,440 980,300 1180,180 C1320,96 1460,40 1660,-60" pathLength="1" stroke="rgba(228,193,150,.18)" strokeWidth="46" />
          <path d="M-40,760 C260,700 360,420 640,430 C920,440 980,300 1180,180 C1320,96 1460,40 1660,-60" pathLength="1" stroke="url(#rk-lenta-g)" strokeWidth="22" />
        </svg>

        <div className="rk-kar-sahna">
          {KARTALAR.map((k, i) => (
            <div key={k.nom} className="rk-okarta" style={{ '--i': i }} ref={(el) => { kartalar.current[i] = el }}
              onPointerMove={(e) => egil(e, i)} onPointerLeave={() => tekis(i)} onClick={() => agdar(i)}>
              <div className="rk-okarta-tomon rk-okarta-orqa" aria-hidden="true">
                <Naqsh id={i} />
                <div className="rk-okarta-arka"><img src={k.rasm} alt="" loading="lazy" /></div>
              </div>
              <article className="rk-okarta-tomon rk-okarta-yuz">
                <div className="rk-okarta-bosh">
                  <div><small>0{i + 1}</small><h3>{k.nom}</h3></div>
                  <Belgi harf={k.harf} />
                </div>
                <p className="rk-okarta-shior">{k.shior}</p>
                <ul>{k.qatorlar.map((q) => <li key={q}>{q}</li>)}</ul>
                <div className="rk-okarta-oyoq" aria-hidden="true"><span>{k.nom}</span><Belgi harf={k.harf} /></div>
              </article>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

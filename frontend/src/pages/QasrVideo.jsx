// Bosh kadr foni — Lusion uslubidagi "kamera orqaga chekinishi". Ikki alohida qatlamdan iborat:
//   1) VIDEO (qasr.mp4, Seedance 2.5): saroy zali, nur, gulbarg girdobi va kamera chekinishi — "suratga olingan" qism.
//      Video o'zi ijro etilmaydi: sahifa aylantirilgan sari uning vaqti (currentTime) aylantirishga bog'lanadi.
//   2) WEBGL (gulbargSahna.js): video ustidagi shaffof tuvalda jonli gulbarglar — kursor ularni tarqatadi,
//      ular yana girdobga qaytadi. Bu qism videoda bo'lishi mumkin emas, chunki u foydalanuvchiga javob beradi.
//
// Qayerga: src/pages/QasrVideo.jsx (gulbargSahna.js shu papkada bo'lsin).
// Ishlatish: Reklama.jsx da  import { QasrVideo } from './QasrVideo'  va
//            <canvas className="rk-sahna" … /> dan KEYIN  <QasrVideo />  qo'yiladi.
import { useEffect, useRef } from 'react'
import { gulbargYarat } from './gulbargSahna'

// Video shu soniyadan boshlab ishlatiladi: undan oldingi qism (girdob ichi) tashlab yuboriladi.
// 4.3 s — gulbarglar kameraga otilib chiqayotgan kadr; sahifa ochilganda LIBOSA yozuvi aynan shu kadr ustida turadi.
const BOSHLANISH = 4.3

export function QasrVideo() {
  const qobiq = useRef(null)
  const video = useRef(null)
  const tuval = useRef(null)

  useEffect(() => {
    const v = video.current, w = qobiq.current
    const bosh = document.querySelector('.rk-bosh')       // bosh kadr bloki — aylantirish shu blok bo'yicha o'lchanadi
    if (!v || !w || !bosh) return undefined

    // WebGL qatlam: harakat kamaytirilgan rejimda yoqilmaydi
    const tinch = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const g = tinch ? null : gulbargYarat(tuval.current)

    // Video fayli topilmasa (yoki brauzer o'qiy olmasa) qatlam yashiriladi — sayt eski WebGL bosh kadri bilan qoladi
    const xato = () => { w.style.display = 'none'; g?.yop() }
    v.addEventListener('error', xato)

    let maqsad = 0, joriy = 0, kadr
    const olch = () => {
      const H = window.innerHeight
      // 0 — sahifa tepasida (girdob ichida), 1 — video to'liq so'nadigan nuqta (zal uzoqdan, kelin nuqtadek).
      // Oxiri bosh kadr tugagan joyda emas, undan keyingi 0.8 ekranda: matnlar yuqoriga ketayotganda ham
      // kamera chekinishda davom etadi — aks holda so'zlar qimirlab, video qotib turgandek ko'rinadi.
      const oxir = bosh.offsetHeight - H + H * 0.8
      maqsad = Math.min(1, Math.max(0, window.scrollY / oxir))
      // gulbarglar ham video bilan birga "uzoqlashadi" — ular ham videoning BOSHLANISH nuqtasidan start oladi
      const d = v.duration || 15
      g?.sur(BOSHLANISH / d + maqsad * (1 - BOSHLANISH / d))
      // Bosh kadrdan chiqqanda saroy butunlay yo'qolmaydi: ko'k rangga bo'yalib (.rk-qasr-tus), xiralashib,
      // keyingi bo'limlar ortida yarim shaffof fon bo'lib qoladi. --chiq: 0 — bosh kadr ichida, 1 — undan keyin.
      const chiq = Math.min(1, Math.max(0, (window.scrollY - bosh.offsetHeight + H) / (H * 0.8)))
      w.style.setProperty('--chiq', chiq.toFixed(3))
      w.style.opacity = String(1 - chiq * 0.3)            // keyingi bo'limlarda saroy 70% ko'rinadi
      if (tuval.current) tuval.current.style.opacity = String(1 - chiq)   // jonli gulbarglar esa to'liq so'nadi
    }
    // Silliqlash: video vaqti aylantirishga darhol sakramaydi, yumshoq yetib boradi
    const sil = () => {
      joriy += (maqsad - joriy) * 0.12
      // Oldingi kadrga o'tish (seek) tugamaguncha yangisini so'ramaymiz — aks holda so'rovlar navbatga
      // yig'ilib, video sakrab-sakrab yuradi. Shu bitta shart harakatni silliq qiladi.
      if (v.duration && !v.seeking) {
        const t = BOSHLANISH + joriy * (v.duration - BOSHLANISH - 0.05)
        if (Math.abs(v.currentTime - t) > 0.03) v.currentTime = t
      }
      kadr = requestAnimationFrame(sil)
    }

    window.addEventListener('scroll', olch, { passive: true })
    window.addEventListener('resize', olch)
    olch(); kadr = requestAnimationFrame(sil)
    return () => {
      window.removeEventListener('scroll', olch)
      window.removeEventListener('resize', olch)
      cancelAnimationFrame(kadr)
      v.removeEventListener('error', xato)
      g?.yop()
    }
  }, [])

  return (
    <div ref={qobiq} className="rk-qasr" aria-hidden="true">
      <video ref={video} src="/video/qasr.mp4" poster="/video/qasr-poster.jpg" muted playsInline preload="auto" />
      <i className="rk-qasr-vinyetka" />
      <canvas ref={tuval} className="rk-gulbarg" />
      {/* sarlavhalar chiqishidan oldin saroyni qoraytirib, blur beradigan parda (reklama-qasr.css) */}
      <i className="rk-qasr-xira" />
      {/* bosh kadrdan keyin saroyni EZAZ ko'k rangiga bo'yaydigan qatlam (reklama-qasr.css) */}
      <i className="rk-qasr-tus" />
      {/* gumbazdan tushayotgan tilla nur — fonni yoritadi */}
      <i className="rk-qasr-nur" />
    </div>
  )
}

import { useEffect, useRef } from 'react'

// Uzun ro'yxat «tasmasi» (foydalanuvchi so'rovi: «mijozlar kabi uzun ro'yxatlar sahifadan chiqib ketmasin»):
// keng ekranda (≥1024 px) blok ekranning qolgan balandligiga (kamida 55% iga) cheklanadi va ichidan aylanadi — sahifa cho'zilmaydi,
// jadval sarlavhasi tepada qotib turadi (CSS: .tasma thead th). Torroq ekranda — oddiy sahifa (butun sahifa suriladi).
// Tepadagi bloklar keyin yuklanib balandligi o'zgarsa ham qayta hisoblanadi (ResizeObserver). `pastki` — ekran pastidan bo'shliq.
export default function Tasma({ className = '', pastki = 28, children, ...rest }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return undefined
    let kadr = 0
    const hisobla = () => {
      cancelAnimationFrame(kadr)
      kadr = requestAnimationFrame(() => {
        if (window.innerWidth < 1024) { el.style.maxHeight = ''; return }
        const tepa = el.getBoundingClientRect().top + window.scrollY
        // tepasi baland sahifada qolgan joy oz bo'lsa ham tasma ekranning kamida 55% i — ro'yxat qisilib qolmasin
        el.style.maxHeight = `${Math.max(320, Math.round(window.innerHeight * 0.55), window.innerHeight - tepa - pastki)}px`
      })
    }
    hisobla()
    const kuzatuvchi = new ResizeObserver(hisobla)
    kuzatuvchi.observe(document.body)
    window.addEventListener('resize', hisobla)
    return () => { cancelAnimationFrame(kadr); kuzatuvchi.disconnect(); window.removeEventListener('resize', hisobla) }
  }, [pastki])
  return <div ref={ref} className={`tasma ${className}`.trim()} {...rest}>{children}</div>
}

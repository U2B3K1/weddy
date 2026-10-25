// Rasmi yo'q libos uchun: bo'sh kulrang to'rtburchak yoki «Rasm yo'q» yozuvi o'rniga libos silueti
// (katalog, yangi zakazdagi tanlov va mijozga ko'rsatish rejimida bir xil).
export default function LibosSiluet({ className = 'libos-siluet' }) {
  return (
    <svg className={className} viewBox="0 0 60 90" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" aria-hidden="true">
      <path d="M24 6c2 3 4 4 6 4s4-1 6-4M24 6l-2 6 4 14h8l4-14-2-6" />
      <path d="M26 26c-2 8-8 22-16 56 6 3 14 4 20 4s14-1 20-4c-8-34-14-48-16-56" />
      <path d="M26 26h8" />
    </svg>
  )
}

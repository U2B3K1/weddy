// Navigatsiya belgilari — ixcham stroke SVG (Lucide uslubi), yangi bog'liqlik talab qilmaydi.
const YOLLAR = {
  dashbord: (<><rect x="3" y="3" width="7" height="9" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="16" width="7" height="5" rx="1" /></>),
  // Dashboard — kataklar (avval «uy» edi; bo'lim nomi Dashboard bo'ldi)
  bosh: (<><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></>),
  yangi: (<><circle cx="12" cy="12" r="9" /><path d="M12 8v8M8 12h8" /></>),
  zakazlar: (<><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 0 1-8 0" /></>),
  mijozlar: (<><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.2a6.5 6.5 0 0 1 3.5 5.8" /></>),
  kalendar: (<><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></>),
  // Katalog — yotgan yopiq kitob (muqova, qalinlik va varaq qatlami); chiziq oralig'i qalinlikdan katta — 22px'da qo'shilib ketmaydi
  katalog: (<><path d="M3.2 8.6 11.4 4.6a1.4 1.4 0 0 1 1.2 0l8.2 4a.6.6 0 0 1 0 1.1l-8.2 4a1.4 1.4 0 0 1-1.2 0l-8.2-4a.6.6 0 0 1 0-1.1Z" fill="currentColor" fillOpacity=".16" /><path d="M3 9.2v3.4c0 .3.2.6.4.7l8 3.9a1.4 1.4 0 0 0 1.2 0l8-3.9c.3-.1.4-.4.4-.7V9.2" /><path d="M3 16.4l8.4 4.1a1.4 1.4 0 0 0 1.2 0l8.4-4.1" /><path d="M9 9.4l5-2.5" /><path d="M10.6 10.5l3.8-1.9" /></>),
  kassa: (<><path d="M2 8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2Z" /><circle cx="12" cy="12" r="2" /></>),
  hisobotlar: (<><path d="M3 3v18h18" /><path d="M7 15l4-4 3 3 5-6" /></>),
  sozlamalar: (<><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" /></>),
  koproq: (<><circle cx="5" cy="12" r="1.2" /><circle cx="12" cy="12" r="1.2" /><circle cx="19" cy="12" r="1.2" /></>),
  // Interfeys ikonkalari — matnli belgilar (✓ ○ ‹ › +) o'rniga
  bajarildi: (<><circle cx="12" cy="12" r="9" /><path d="m8.5 12.5 2.5 2.5 4.5-5" /></>),
  doira: (<circle cx="12" cy="12" r="9" />),
  chap: (<path d="m15 6-6 6 6 6" />),
  ong: (<path d="m9 6 6 6-6 6" />),
  qosh: (<path d="M12 5v14M5 12h14" />),
  qidiruv: (<><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>),
  yop: (<path d="M6 6l12 12M18 6 6 18" />),
  // Sozlama bo'limlari — asosiy menyudagidek har birining o'z belgisi
  qalqon: (<path d="M12 3 20 6v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6Z" />),
  soat: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  qaytar: (<><path d="M9 14 4 9l5-5" /><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11" /></>),
  chizgich: (<><path d="M3 16.5 16.5 3 21 7.5 7.5 21Z" /><path d="m7.5 12 2 2M10.5 9l2 2M13.5 6l2 2" /></>),
  hujjat: (<><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z" /><path d="M14 3v6h6M8 13h8M8 17h5" /></>),
  quyosh: (<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>),
  yorliq: (<><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z" /><circle cx="7.5" cy="7.5" r="1.2" /></>),
  foiz: (<><path d="M19 5 5 19" /><circle cx="6.5" cy="6.5" r="2.5" /><circle cx="17.5" cy="17.5" r="2.5" /></>),
  sovga: (<><path d="M3 8h18v4H3ZM5 12v9h14v-9M12 8v13" /><path d="M12 8S10.5 3.5 8 3.5a2.25 2.25 0 0 0 0 4.5M12 8s1.5-4.5 4-4.5a2.25 2.25 0 0 1 0 4.5" /></>),
  xabar: (<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" />),
  vilka: (<><path d="M9 2v5M15 2v5M6 7h12v4a6 6 0 0 1-12 0Z" /><path d="M12 17v5" /></>),
  joy: (<><path d="M12 21s7-6.2 7-11.5a7 7 0 0 0-14 0C5 14.8 12 21 12 21Z" /><circle cx="12" cy="9.5" r="2.5" /></>),
  bino: (<><path d="M4 21V6l8-3 8 3v15M2 21h20" /><path d="M9 21v-5h6v5M8 9h1M15 9h1M8 12.5h1M15 12.5h1" /></>),
  qurilma: (<><rect x="5" y="2.5" width="14" height="19" rx="2" /><path d="M11 18h2" /></>),
  yordam: (<><circle cx="12" cy="12" r="9" /><path d="M9.2 9.3a3 3 0 0 1 5.6 1.2c0 2-2.8 2.6-2.8 4M12 17.5h.01" /></>),
  // Hisobot bo'limlari
  tarozi: (<><path d="M12 3v18M7 21h10M5 7h14" /><path d="m5 7-3 6a3 3 0 0 0 6 0ZM19 7l-3 6a3 3 0 0 0 6 0Z" /></>),
  hamyon: (<><path d="M19 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3" /><path d="M21 9h-5a3 3 0 0 0 0 6h5Z" /><path d="M3 7h16" /></>),
  bank: (<><path d="M3 10 12 4l9 6M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 21h18" /></>),
  ustun: (<><path d="M3 21h18" /><rect x="5" y="11" width="3" height="7" rx="1" /><rect x="10.5" y="6" width="3" height="12" rx="1" /><rect x="16" y="9" width="3" height="9" rx="1" /></>),
  seyf: (<><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="12" cy="12" r="3.5" /><path d="M12 8.5V10M12 14v1.5M7 20v1.5M17 20v1.5" /></>),
  tarix: (<><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7.5V12l3 2" /></>),
  almashtir: (<><path d="M16 3h5v5" /><path d="M21 3l-7 7" /><path d="M8 21H3v-5" /><path d="M3 21l7-7" /></>),
}

export default function NavIkona({ nom, className = 'nav-ikon' }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {YOLLAR[nom] || YOLLAR.koproq}
    </svg>
  )
}

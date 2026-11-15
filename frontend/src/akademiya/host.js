// Akademiya alohida manzilda ishlaydi (academy.libosa.uz; ishlab chiqishda academy.localhost).
// Shu manzilda ilova faqat o'quv saloni bilan ishlaydi — server ham buni host bo'yicha tekshiradi.
export const AKADEMIYA = /^academy\./.test(window.location.hostname)

// Haqiqiy ilova manzili: «academy.» olib tashlanadi (academy.libosa.uz → libosa.uz). `?akademiya=1` — ilovaga belgi:
// odam akademiya kirish sahifasidan keldi, kirgach Dashboard emas, yana akademiya ochilsin (App.jsx).
export const ASOSIY_MANZIL = `${window.location.protocol}//${window.location.host.replace(/^academy\./, '')}/?akademiya=1#kirish`
// Libosa saytining bosh sahifasi (salonni ulash arizasi shu yerda) — mehmonga «Saloningizni ulang» havolasi
export const SAYT_MANZIL = `${window.location.protocol}//${window.location.host.replace(/^academy\./, '')}/`

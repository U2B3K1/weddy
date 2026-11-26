// Telegram bilan aloqa — tashqi `telegram-web-app.js` skriptisiz (sayt CSP si begona skriptga ruxsat bermaydi).
// Telegram ilovani ochganda manzil oxiriga `#tgWebAppData=…` qo'shadi: shu imzolangan qator serverga yuboriladi.
// Hodisalar (tayyor, yopish, rang) Telegramning ochiq protokoli bo'yicha: core.telegram.org/api/web-events

const KALIT = 'weddy.tg_initdata'

export function initData() {
  const xesh = new URLSearchParams(window.location.hash.slice(1)).get('tgWebAppData')
  if (xesh) {
    try { sessionStorage.setItem(KALIT, xesh) } catch { /* saqlanmasa ham shu ochilishda ishlaydi */ }
    return xesh
  }
  try { return sessionStorage.getItem(KALIT) || '' } catch { return '' }
}

export function tgHodisa(tur, malumot) {
  try {
    if (window.TelegramWebviewProxy?.postEvent) {   // Android, iOS
      window.TelegramWebviewProxy.postEvent(tur, malumot === undefined ? '' : JSON.stringify(malumot))
    } else if (window.external && 'notify' in window.external) {   // Windows Phone / eski desktop
      window.external.notify(JSON.stringify({ eventType: tur, eventData: malumot }))
    } else if (window.parent !== window) {   // Telegram Web (ramka ichida)
      window.parent.postMessage(JSON.stringify({ eventType: tur, eventData: malumot }), 'https://web.telegram.org')
    }
  } catch { /* Telegram tashqarisida — jim */ }
}

export const tayyor = () => {
  tgHodisa('web_app_set_header_color', { color: '#0D1320' })
  tgHodisa('web_app_set_background_color', { color: '#0D1320' })
  tgHodisa('web_app_set_bottom_bar_color', { color: '#0D1320' })
  tgHodisa('web_app_setup_swipe_behavior', { allow_vertical_swipe: false })   // ro'yxatni aylantirganda ilova yopilib ketmasin
  tgHodisa('web_app_ready')
  tgHodisa('web_app_expand')
}
export const yop = () => tgHodisa('web_app_close')
export const tanlovTitrash = () => tgHodisa('web_app_trigger_haptic_feedback', { type: 'selection_change' })
export const titrat = (tur = 'success') => tgHodisa('web_app_trigger_haptic_feedback', { type: 'notification', notification_type: tur })

// Nusxalash: zamonaviy usul, bo'lmasa eski usul. Ikkalasi ham ishlamasa — false (raqam ekranda belgilanadigan bo'lib turadi)
export async function nusxala(matn) {
  try { await navigator.clipboard.writeText(matn); return true } catch { /* pastdagi usul */ }
  const t = document.createElement('textarea')
  t.value = matn
  t.setAttribute('readonly', '')
  t.style.cssText = 'position:fixed;top:0;left:0;opacity:0'
  document.body.appendChild(t)
  t.select()
  let ok = false
  try { ok = document.execCommand('copy') } catch { /* — */ }
  t.remove()
  return ok
}

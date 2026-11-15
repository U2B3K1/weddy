// Yoritgich: yo'naltirilgan mashqda ilova ekranida faqat bitta joyni ochiq qoldiradi.
// Ilova ichki oynada (iframe, shu manzil) ishlaydi — uning hujjatiga to'rtta to'siq va oltin hoshiya qo'yiladi:
// to'siqlar nishon atrofini yopadi (bosilmaydi), nishonning o'zi ochiq qoladi. Ilova kodi o'zgarmaydi.
// Qadam ta'rifi serverdan keladi (backend/apps/akademiya/darslar/asos.py dagi izohga qarang).

const ID = 'ak-yoritgich'
const CHET = 6             // nishon atrofidagi bo'sh joy, px
const TOPILMADI_MS = 4000  // shuncha vaqt nishon ko'rinmasa — o'quvchi qotib qolmasin, panel yo'l ko'rsatadi

const korinadi = (el) => {
  const r = el.getBoundingClientRect()
  if (r.width < 2 || r.height < 2) return false
  const s = el.ownerDocument.defaultView.getComputedStyle(el)
  return s.visibility !== 'hidden' && s.display !== 'none'
}
// Bosib bo'ladimi: o'chirilgan tugma nishon bo'la olmaydi (o'quvchi berk ko'chaga kirib qoladi)
const faol = (el) => !!el && !el.disabled && el.getAttribute('aria-disabled') !== 'true'
const tozaMatn = (el) => (el.textContent || '').replace(/\s+/g, ' ').trim()

// Element ta'rifi bo'yicha ekrandagi birinchi ko'rinadigan elementni topadi. Ta'rif ro'yxat bo'lishi mumkin — bir xil
// amalning turli ekran kengligidagi joylari (masalan, keng ekranda chap menyu, telefonda pastki panel): birinchi topilgani olinadi
export function top(doc, t, ildiz = doc) {
  if (!t) return null
  if (Array.isArray(t)) { for (const x of t) { const el = top(doc, x, ildiz); if (el) return el } return null }
  const matn = tozaMatn
  let nomzodlar
  try { nomzodlar = [...ildiz.querySelectorAll(t.css || 'button, [role=tab], a, input')] } catch { return null }
  return nomzodlar.find((el) => {
    if (t.matn != null && matn(el) !== t.matn) return false
    if (t.boshi != null && !matn(el).startsWith(t.boshi)) return false
    if (t.ichida != null && !matn(el).includes(t.ichida)) return false
    if (t.label != null && !(el.getAttribute('aria-label') || '').startsWith(t.label)) return false
    if (t.placeholder != null && !(el.getAttribute('placeholder') || '').includes(t.placeholder)) return false
    if (t.qiymat != null && String(el.value ?? '') !== t.qiymat) return false  // maydon qiymati (masalan, son tanlagich)
    return korinadi(el)
  }) || null
}

const kutilganmi = (qiymat, kutilgan) => {
  const [tur, q] = (kutilgan || '').split(':')
  if (tur === 'raqam') return qiymat.replace(/\D/g, '').endsWith(q)
  if (tur === 'uzunlik') return qiymat.trim().length >= Number(q)
  if (tur === 'matn') return qiymat.toLowerCase().includes(q)  // matnda shu bo'lak bor (masalan, qidiruv so'zi)
  return qiymat.trim().length > 0
}

function qatlam(doc) {
  let q = doc.getElementById(ID)
  if (q) return q
  q = doc.createElement('div')
  q.id = ID
  q.setAttribute('aria-hidden', 'true')
  const toSiq = 'position:fixed;z-index:2147483000;background:rgba(6,9,16,.74);pointer-events:auto;'
  q.innerHTML = [0, 1, 2, 3].map(() => `<div data-t style="${toSiq}"></div>`).join('')
    + '<div data-h style="position:fixed;z-index:2147483001;pointer-events:none;border:2px solid #F3BF70;border-radius:14px;'
    + 'box-shadow:0 0 0 4px rgba(243,191,112,.22),0 0 28px rgba(243,191,112,.45)"></div>'
    + `<div data-p style="${toSiq}background:transparent;display:none"></div>`  // «faqat ko'rish» qadamida nishon ustidagi parda
  doc.body.appendChild(q)
  return q
}

function joyla(doc, el, faqatKor) {
  const q = qatlam(doc)
  const w = doc.defaultView.innerWidth, h = doc.defaultView.innerHeight
  const r = el.getBoundingClientRect()
  const x0 = Math.max(0, r.left - CHET), y0 = Math.max(0, r.top - CHET)
  const x1 = Math.min(w, r.right + CHET), y1 = Math.min(h, r.bottom + CHET)
  const [ust, past, chap, ong] = q.querySelectorAll('[data-t]')
  const qoy = (e, l, t, wd, ht) => { e.style.left = `${l}px`; e.style.top = `${t}px`; e.style.width = `${Math.max(0, wd)}px`; e.style.height = `${Math.max(0, ht)}px` }
  qoy(ust, 0, 0, w, y0); qoy(past, 0, y1, w, h - y1); qoy(chap, 0, y0, x0, y1 - y0); qoy(ong, x1, y0, w - x1, y1 - y0)
  qoy(q.querySelector('[data-h]'), x0, y0, x1 - x0, y1 - y0)
  const parda = q.querySelector('[data-p]')
  parda.style.display = faqatKor ? 'block' : 'none'
  if (faqatKor) qoy(parda, x0, y0, x1 - x0, y1 - y0)
}

export const ochir = (doc) => { try { doc?.getElementById(ID)?.remove() } catch { /* hujjat almashgan */ } }

// Bitta qadamni yuritadi. `oynaOl()` — ichki oyna (iframe) elementi; `onTugadi()` — qadam bajarildi;
// `onHolat('topildi' | 'muqobil' | 'topilmadi')` — panel uchun. To'xtatuvchi funksiyani qaytaradi.
// `oldingilar` — shu darsning oldingi qadamlari: nishon ekranda bo'lmasa (sahifa yangilangan, o'quvchi boshqa joyga
// o'tib qolgan) eng yaqin oldingi qadam yoritiladi va o'quvchi kerakli sahifaga qaytadi.
export function yurit(oynaOl, qadam, { onTugadi, onHolat, oldingilar = [] }) {
  let tugadi = false, holat = '', kutish = Date.now(), suruldi = null, yozTaymer = null
  let qi = null, qaytishEl = null  // qaytish paytida yoritilgan oldingi qadam (indeksi va elementi)
  let qiVaqt = 0                    // `qi` oxirgi marta surilgan payt
  let otilgan = 0                   // qaytishda bosib o'tilgan qadamlar chegarasi: undan orqaga qaytilmaydi (aylanib qolmasin)
  let oxirgiSurish = 0              // o'quvchi sahifani oxirgi marta surgan payt
  // Maydonda eski qiymat tursa («0», «21:00»), yozilgani uning yoniga qo'shilib qoladi («50») — shuning uchun eski qiymat
  // belgilab qo'yiladi (o'quvchi o'zi yoza boshlaguncha — bosganda ham): yozishi bilan u almashadi
  let belgilandi = false, yozaBoshladi = false
  const belgila = (el, bosildi = false) => {
    if (yozaBoshladi || (belgilandi && !bosildi) || !el || el.tagName !== 'INPUT' || !el.value || kutilganmi(el.value, qadam.kutilgan)) return
    belgilandi = true
    try { el.select() } catch { /* bu turdagi maydon belgilanmaydi */ }
  }
  const bitdi = () => { if (!tugadi) { tugadi = true; toxta(); onTugadi() } }
  const holatBer = (h) => { if (h !== holat) { holat = h; onHolat?.(h) } }
  const doc = () => { try { return oynaOl()?.contentDocument || null } catch { return null } }

  const bosildi = (e) => {
    if (qaytishEl && qi != null && qaytishEl.contains(e.target)) {  // qaytish qadami bosildi — keyingisiga
      const o = oldingilar[qi]
      if (o.amal !== 'bos') return  // maydon: bosish emas, to'ldirish kutiladi (yozildi)
      const t = o.ichki ? e.target.closest(o.ichki.css || 'button') : qaytishEl
      if (t && (!o.ichki || o.ichki.matn == null || tozaMatn(t) === o.ichki.matn)) { otilgan = qi + 1; qi = qi + 1 < oldingilar.length ? qi + 1 : null; qiVaqt = Date.now() }
      return
    }
    const d = doc(); if (!d) return
    if (qadam.amal === 'yoz') { const m = top(d, qadam.nishon); if (m && e.target === m) belgila(m, true); return }
    if (qadam.amal !== 'bos') return
    const nishon = top(d, qadam.nishon)
    if (!nishon || !nishon.contains(e.target)) return
    if (qadam.ichki) {  // nishon — maydon; qadam undagi aniq tugma bosilganda tugaydi (qaysi biri — o'quvchi tanlaydi)
      const t = e.target.closest(qadam.ichki.css || 'button')
      if (!t || !nishon.contains(t)) return
      if (qadam.ichki.matn != null && tozaMatn(t) !== qadam.ichki.matn) return
    }
    if (!qadam.tayyor) setTimeout(bitdi, 350)  // ilova bosishga javob berib ulgursin
  }
  const yozildi = (e) => {
    // qaytishda bo'sh qolgan maydon to'ldirildi — keyingi qadamga
    if (qaytishEl && qi != null && e.target === qaytishEl && oldingilar[qi].amal === 'yoz') {
      clearTimeout(yozTaymer)
      const shu = qi
      if (kutilganmi(qaytishEl.value, oldingilar[shu].kutilgan)) yozTaymer = setTimeout(() => {
        if (qi === shu) { otilgan = shu + 1; qi = shu + 1 < oldingilar.length ? shu + 1 : null; qiVaqt = Date.now() }
      }, 900)
      return
    }
    const d = doc(); if (!d || qadam.amal !== 'yoz') return
    const nishon = top(d, qadam.nishon)
    if (!nishon || e.target !== nishon) return
    yozaBoshladi = true
    clearTimeout(yozTaymer)
    if (kutilganmi(nishon.value, qadam.kutilgan)) yozTaymer = setTimeout(bitdi, 900)  // yozib bo'lishini kutadi
  }

  const surildi = () => { oxirgiSurish = Date.now(); tik() }
  let ulangan = null
  const ula = (d) => {
    if (ulangan === d) return
    uz()
    d.addEventListener('click', bosildi, true); d.addEventListener('input', yozildi, true)
    // sahifa surilganda hoshiya darhol ergashadi (taymerni kutmaydi)
    d.addEventListener('scroll', surildi, true); d.defaultView.addEventListener('resize', surildi)
    ulangan = d
  }
  const uz = () => {
    try {
      ulangan?.removeEventListener('click', bosildi, true); ulangan?.removeEventListener('input', yozildi, true)
      ulangan?.removeEventListener('scroll', surildi, true); ulangan?.defaultView?.removeEventListener('resize', surildi)
    } catch { /* hujjat almashgan */ }
    ulangan = null
  }

  function tik() {
    if (tugadi) return
    const d = doc()
    if (!d?.body) return
    ula(d)
    if (qadam.tayyor && top(d, qadam.tayyor)) { bitdi(); return }
    // maydon oldindan to'g'ri to'ldirilgan bo'lsa (qoralama) — qadam bajarilgan
    let el = top(d, qadam.nishon)
    if (el && qadam.amal === 'yoz' && d.activeElement !== el && kutilganmi(el.value, qadam.kutilgan)) { bitdi(); return }
    // nishon o'chirilgan (masalan, libos olib tashlangan — «Davom etish» bosilmaydi): oldingi qadamga qaytariladi
    if (el && qadam.amal === 'bos' && !qadam.ichki && !faol(el)) el = null
    let muqobil = false
    if (!el && qadam.muqobil) { el = top(d, qadam.muqobil); muqobil = !!el }
    // Qaytish: nishon ekranda yo'q — oldingi qadamlar qayta yuriladi. Tartib muhim (avval olib ketish kuni, keyin
    // qaytarish kuni), shuning uchun ekranda ko'rinib turgan ketma-ket qadamlarning eng birinchisidan boshlanadi va
    // har bosishda bittaga oldinga suriladi (`qi`).
    let qaytish = false
    if (!el) {
      const nomzod = (j) => {
        const o = oldingilar[j]
        if (!o) return null
        // Natijasi ekranda turgan qadam qayta yurilmaydi (masalan, zakaz kartasi ochiq). Natija yo'qolgan bo'lsa (sahifa
        // yangilangan — ilova bosh sahifaga qaytgan) qadam qayta bajariladi: aks holda o'quvchi menyu bilan ro'yxat orasida qolib ketardi
        if (o.tayyor && top(d, o.tayyor)) return null
        const n = top(d, o.nishon)
        // to'ldirilishi kerak bo'lgan maydon bo'sh qolgan (forma qayta ochilgan) — o'sha maydonga qaytariladi;
        // yozilayotgan maydon to'lib bo'lguncha (yozildi) o'z o'rnida turadi
        if (o.amal === 'yoz') return n && (!kutilganmi(n.value, o.kutilgan) || (j === qi && d.activeElement === n)) ? n : null
        if (o.amal !== 'bos') return null
        return n && (o.ichki || faol(n)) ? n : null  // o'chirilgan tugma nishon bo'lmaydi
      }
      // bosilgandan keyin ilova keyingi tugmani darhol ochmaydi (masalan, libos qulflanguncha «Davom etish» o'chiq) —
      // biroz kutiladi; shunda ham ochilmasa, qaytadan hisoblanadi
      if (qi != null && !nomzod(qi) && Date.now() - qiVaqt > 2500) qi = null
      if (qi == null) {
        let j = oldingilar.length - 1
        while (j >= 0 && !nomzod(j)) j--
        if (j >= 0) { while (j > otilgan && nomzod(j - 1)) j--; qi = j; if (j < otilgan) otilgan = j }
      }
      if (qi != null) { el = nomzod(qi); qaytish = !!el }
    }
    // Nishon yopiq bo'lim (<details>, telefonda zakaz kartasidagi amallar shunday): ichidagi tugma ko'rinmaydi —
    // avval bo'lim sarlavhasi yoritiladi, ochilgach qadam o'z joyidan davom etadi
    let ochish = false
    if (el && el.tagName === 'DETAILS' && !el.open && !qaytish) {
      const sar = el.querySelector(':scope > summary')
      if (sar) { el = sar; ochish = true }
    }
    qaytishEl = qaytish ? el : null
    if (!el) {
      if (Date.now() - kutish > TOPILMADI_MS) { ochir(d); holatBer('topilmadi') }
      return
    }
    kutish = Date.now()
    holatBer(qaytish ? 'qaytish' : muqobil ? 'muqobil' : ochish ? 'ochish' : 'topildi')
    if (suruldi !== el) {  // nishon ekrandan tashqarida bo'lsa — bir marta ko'rinadigan joyga suriladi
      suruldi = el
      // nishon ichidagi aniq tugma bosilishi kerak bo'lsa — o'sha tugma ko'rinsin (katta blokning o'rtasi emas):
      // telefonda zakaz kartasidagi amal tugmasi pastki menyu ostida qolib ketadi
      const ichki = qadam.ichki && !ochish && !qaytish && !muqobil
        ? [...el.querySelectorAll(qadam.ichki.css || 'button')].find((x) => korinadi(x) && (qadam.ichki.matn == null || tozaMatn(x) === qadam.ichki.matn))
        : null
      const kor = ichki || el
      const r = kor.getBoundingClientRect(), oyna = d.defaultView
      // yon tomonga ham: tor ekranda bo'lim tablari gorizontal suriladigan qatorda turadi (oxirgilari ekrandan tashqarida).
      // Ekran ichida bo'lsa ham ustini qotirilgan panel (telefonda pastki menyu) yopib turgan bo'lsa — o'rtaga suriladi
      const q = d.getElementById(ID)
      if (q) q.style.display = 'none'  // o'z to'siqlarimiz hisobga olinmasin
      // o'rtasi, kichik blokda — tepasi va pasti ham (telefonda kassa klaviaturasining pastki qatori menyu ostida qoladi)
      const x = r.left + r.width / 2
      const nuqtalar = [r.top + r.height / 2, ...(r.height < oyna.innerHeight * 0.7 ? [r.top + 6, r.bottom - 6] : [])]
        .filter((y) => y > 0 && y < oyna.innerHeight)
      const yopiq = nuqtalar.some((y) => {
        const ust = d.elementFromPoint(x, y)
        return ust && !kor.contains(ust) && !ust.contains(kor)
      })
      if (q) q.style.display = ''
      // ekrandan baland blok (masalan, telefonda «Integratsiyalar») — o'rtasidan emas, boshidan ko'rsatiladi
      if (yopiq || r.top < 0 || r.bottom > oyna.innerHeight || r.left < 0 || r.right > oyna.innerWidth) kor.scrollIntoView({ block: r.height > oyna.innerHeight ? 'start' : 'center', inline: 'center' })
      if (qadam.amal === 'yoz' && !muqobil && !qaytish) { el.focus({ preventScroll: true }); belgila(el) }
    } else if (Date.now() - oxirgiSurish > 1500) {
      // O'quvchi sahifani surib, yoritilgan joyni ekrandan butunlay chiqarib yuborgan: hamma joy xira va bosilmaydi,
      // qayerga qarashni bilib bo'lmaydi. Surish to'xtagach nishon yana ko'rinadigan joyga qaytariladi.
      const r = el.getBoundingClientRect(), oyna = d.defaultView
      if (r.bottom < 8 || r.top > oyna.innerHeight - 8) el.scrollIntoView({ block: r.height > oyna.innerHeight ? 'start' : 'center', inline: 'nearest' })
    }
    joyla(d, el, qadam.amal === 'kor' && !qaytish)
  }
  const taymer = setInterval(tik, 140)
  tik()
  function toxta() { clearInterval(taymer); clearTimeout(yozTaymer); uz(); ochir(doc()) }
  return toxta
}

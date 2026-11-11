// R3 (D1 UI ↔ D3 backend): zakaz kartasidagi pul oqimlari — narx kamayganda farq qaytarimi (C-07, C-17, C-20),
// bekor qilish oldindan hisobi (C-04), tayyor chegirma va so'rovni qaytarib olish (C-15, C-06), o'tkazma «kelmadi» →
// berilgan zakazda qoldiq (C-03) va sotuvchi qo'ng'iroqchasi (C-24). Har test o'z libosini API orqali yaratadi (boshqa
// testlar qoldirgan «tozalashda»/band holatga bog'liq emas) va uzoq sanalarda ishlaydi.
import { expect, test } from '@playwright/test'
import { bolimga, QURILMA_HOLATI, kirish, xatolarniKuzat } from './yordam.js'

const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }
const som = (n) => `${String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')} so'm`
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

async function smenada(page) {
  const s = await apiSorov(page, 'GET', '/kassa/smena/')
  if (!s.ochiq) await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  else if (!s.men_ishtirokchi) await apiSorov(page, 'POST', '/kassa/smena/qoshilish/')
}
async function kartaOch(page, raqam) {
  await bolimga(page, 'Zakazlar')
  await page.locator('input.jadval-qidiruv').fill(String(raqam))
  await page.locator('.zakaz-katak', { hasText: `#${raqam} ` }).first().click()
  await expect(page.getByRole('heading', { name: `Zakaz #${raqam}` })).toBeVisible()
}
async function boshqaAmallar(page) {
  const b = page.locator('details.boshqa-amallar')
  if (await b.count() && !(await b.evaluate((d) => d.open))) await b.locator('> summary').click()
}
// `<details>` bandini ochadi (ochiq bo'lsa tegmaydi — amaldan keyin React o'sha elementni qayta ishlatadi va u ochiq qoladi)
async function bandOch(page, sarlavha) {
  const d = page.locator('details', { has: page.locator(':scope > summary', { hasText: sarlavha }) }).last()
  if (!(await d.evaluate((x) => x.open))) await d.locator(':scope > summary').click()
  return d
}
// Har test o'z libosini yaratadi (rahbar): boshqa testlar qoldirgan holatga («tozalashda», band) bog'liq bo'lmasin
async function libosYarat(rahbar, artikul, narx) {
  const kat = (await apiSorov(rahbar, 'GET', '/kategoriyalar/')).find((k) => k.nomi === 'Milliy')
  const l = await apiSorov(rahbar, 'POST', '/liboslar/', { artikul, nomi: `Libos ${artikul}`, kategoriya: kat.id, ijara_narxi: narx, tannarx: narx * 3 })
  expect(l.id, JSON.stringify(l)).toBeTruthy()
  return { ...l, artikul, ijara_narxi: narx }
}
async function rahbarOch(browser) {
  const ctx = await browser.newContext({ storageState: QURILMA_HOLATI })
  const rahbar = await ctx.newPage()
  await kirish(rahbar, 'Rahbar', '1111')
  return { ctx, rahbar }
}

test.describe.configure({ mode: 'serial' })
test.setTimeout(120_000)

test("narx kamaysa farq qaytariladi, bekor qilishda backend hisobi (C-07, C-17, C-20, C-04)", async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize({ width: 1280, height: 860 })
  const { ctx, rahbar } = await rahbarOch(browser)
  const qimmat = await libosYarat(rahbar, 'R3-QIMMAT', 2_000_000)
  const arzon = await libosYarat(rahbar, 'R3-ARZON', 1_000_000)
  await ctx.close()
  await kirish(page, 'Sotuvchi', '2222')
  await smenada(page)
  const [dan, gacha] = [iso(270), iso(271)]
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770077', fio: 'Pul Sinov', dan, gacha, liboslar: [qimmat.id] })
  const t = await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', usul: 'naqd', summa: 2_000_000 })
  expect(t.detail, JSON.stringify(t)).toBeUndefined()

  await test.step('arzonroq libosga almashtirish: farq oldindan ko\'rinadi, usul tanlanadi, natijada yangi jami', async () => {
    await kartaOch(page, z.raqam)
    await boshqaAmallar(page)
    await page.locator('summary', { hasText: /^Libosni almashtirish$/ }).click()
    const forma = page.locator('summary', { hasText: /^Libosni almashtirish$/ }).locator('..')
    await expect(forma.getByLabel('Yangi libos').locator('option', { hasText: arzon.artikul })).toContainText(`(−${som(1_000_000)})`)
    await forma.getByLabel('Yangi libos').selectOption(String(arzon.id))
    await expect(forma).toContainText(`Jami ${som(2_000_000)} → ${som(1_000_000)}; mijozga ${som(1_000_000)} qaytariladi.`)
    await forma.getByRole('radiogroup', { name: 'Farq qanday qaytariladi' }).getByRole('radio', { name: 'Terminal' }).click()
    await forma.getByRole('button', { name: 'Almashtirish' }).click()
    await expect(page.getByText(`Libos almashtirildi. Jami ${som(2_000_000)} → ${som(1_000_000)}`)).toBeVisible()
    await expect(page.getByText(`Mijozga ${som(1_000_000)} qaytaring`)).toBeVisible()
    // to'langan — qaytarim ayirilgan (VOZVRAT): kartada 1 000 000, qoldiq 0
    await expect(page.locator('.karta-asosiy')).toContainText(`To'langan${som(1_000_000)}`)
    const tolovlar = page.locator('.karta-tolovlar')
    await expect(tolovlar.locator('.tolov-qator', { hasText: 'Pulni qaytarish' })).toContainText(`−${som(1_000_000)}`)
    await expect(tolovlar.locator('.tolov-qator', { hasText: 'Pulni qaytarish' })).toContainText('Terminal')
  })

  await test.step('bekor qilish: tasdiqdagi raqamlar backend oldindan hisobidan, natijada qaytariladigan summa', async () => {
    const h = await apiSorov(page, 'GET', `/zakazlar/${z.id}/bekor/`)
    expect(h.qaytariladi, JSON.stringify(h)).toBeGreaterThan(0)
    await boshqaAmallar(page)
    await page.locator('summary', { hasText: 'Zakazni bekor qilish' }).click()
    const forma = page.locator('summary', { hasText: 'Zakazni bekor qilish' }).locator('..')
    await expect(forma.locator('.bekor-hisob')).toContainText(`Mijozga ${som(h.qaytariladi)} qaytariladi, ${som(h.ushlab_qolinadi)} ushlab qolinadi.`)
    await expect(forma.getByRole('radio', { name: 'Naqd' })).toHaveAttribute('aria-checked', 'true')  // asl to'lov usuli
    await forma.locator('label', { hasText: /^Sabab/ }).locator('input').fill('Mijoz voz kechdi')
    await forma.getByRole('button', { name: 'Bekor qilish' }).click()
    const oyna = page.getByRole('alertdialog', { name: 'Zakazni bekor qilasizmi?' })
    await expect(oyna).toContainText(`Mijozga ${som(h.qaytariladi)} qaytariladi`)
    await oyna.getByRole('button', { name: 'Ha, bekor qilish' }).click()
    await expect(page.getByText(`Zakaz bekor qilindi. Mijozga ${som(h.qaytariladi)} qaytaring`)).toBeVisible()
    await expect(page.locator('.karta-bosh .holat')).toHaveText('Bekor qilingan')
  })
  expect(xatolar).toEqual([])
})

test("tayyor chegirma: summa, tasdiq, olib tashlash; so'rovni qaytarib olish (C-15, C-06)", async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize({ width: 1280, height: 860 })
  const { ctx, rahbar } = await rahbarOch(browser)
  const tc = await apiSorov(rahbar, 'POST', '/tayyor-chegirmalar/', { nomi: 'R3 Sinov', summa: 50_000 })
  const libos = await libosYarat(rahbar, 'R3-CHEG', 1_000_000)
  expect(tc.id, JSON.stringify(tc)).toBeTruthy()
  await kirish(page, 'Sotuvchi', '2222')
  const [dan, gacha] = [iso(280), iso(281)]
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770088', fio: 'Chegirma Sinov', dan, gacha, liboslar: [libos.id] })
  try {
    await kartaOch(page, z.raqam)
    await test.step("tayyor chegirma: tugmada summa, qo'llashdan oldin tasdiq", async () => {
      await boshqaAmallar(page)
      await bandOch(page, /^Chegirma$/)
      await page.getByRole('button', { name: `R3 Sinov: −${som(50_000)}` }).click()
      const oyna = page.getByRole('alertdialog', { name: "«R3 Sinov» qo'llansinmi?" })
      await expect(oyna).toContainText(`jami ${som(1_000_000)} → ${som(950_000)}`)
      await oyna.getByRole('button', { name: "Ha, qo'llash" }).click()
      await expect(page.getByText(`Chegirma qo'llandi: −${som(50_000)}. Yangi jami ${som(950_000)}.`)).toBeVisible()
    })
    await test.step('qo\'llangan tayyor chegirmani olib tashlash', async () => {
      await boshqaAmallar(page)
      const blok = await bandOch(page, `Chegirma: −${som(50_000)}`)
      await expect(blok).toContainText('«R3 Sinov»')
      await blok.getByRole('button', { name: 'Olib tashlash' }).click()
      await page.getByRole('alertdialog', { name: 'Chegirma olib tashlansinmi?' }).getByRole('button', { name: 'Ha, olib tashlash' }).click()
      await expect(page.getByText(`Chegirma olib tashlandi. Yangi jami ${som(1_000_000)}.`)).toBeVisible()
    })
    await test.step("so'ralgan chegirma kartada ko'rinadi va qaytarib olinadi", async () => {
      await boshqaAmallar(page)
      await bandOch(page, /^Chegirma$/)
      await page.getByRole('button', { name: 'Summada' }).click()
      await page.getByLabel("Boshqa chegirma, so'm").fill('100000')
      await page.getByRole('button', { name: "Rahbardan so'rash" }).click()
      await expect(page.getByText("Rahbar tasdig'iga yuborildi.")).toBeVisible()
      const sorov = page.locator('.chegirma-kutilmoqda')
      await expect(sorov).toContainText(`${som(100_000)} chegirma so'radi`)
      await expect(sorov).toContainText(`Tasdiqlansa yangi jami ${som(900_000)}`)
      await expect(page.locator('.bron-muddat-izoh')).toContainText('Rahbar')
      await sorov.getByRole('button', { name: "So'rovni qaytarib olish" }).click()
      await page.getByRole('alertdialog', { name: "So'rov qaytarib olinsinmi?" }).getByRole('button', { name: 'Ha, qaytarib olish' }).click()
      await expect(page.getByText("So'rov qaytarib olindi.")).toBeVisible()
      await expect(page.locator('.karta-bosh .holat')).toHaveText('Vaqtinchalik bron')
    })
  } finally {
    await apiSorov(page, 'POST', `/zakazlar/${z.id}/bekor/`, { sabab: 'E2E sinov' })
    await apiSorov(rahbar, 'PATCH', `/tayyor-chegirmalar/${tc.id}/`, { faol: false })
    await ctx.close()
  }
  expect(xatolar).toEqual([])
})

test("o'tkazma tasdiqlanmaguncha libos berilmaydi; kelmadi — sotuvchiga bildirishnoma (C-18, C-24)", async ({ page, browser }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize({ width: 1280, height: 860 })
  const { ctx, rahbar } = await rahbarOch(browser)
  const libos = await libosYarat(rahbar, 'R3-PUL', 1_000_000)  // bugun bo'sh bo'lishi aniq — o'z libosi
  // 2026-11-11: o'tkazma tasdig'i standart o'chiq — bu test ixtiyoriy nazoratni sinaydi, shu uchun yoqib oladi
  await apiSorov(rahbar, 'PATCH', '/sozlamalar/', { otkazma_tasdigi: true })

  await kirish(page, 'Sotuvchi', '2222')
  await smenada(page)
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: '+998907770099', fio: "O'tkazma Sinov", dan: iso(0), gacha: iso(1), liboslar: [libos.id] })
  const t = await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', usul: 'otkazma', summa: 1_000_000 })
  expect(t.id, JSON.stringify(t)).toBeTruthy()  // o'tkazma — rahbar tasdig'ini kutadi

  await test.step("berish formasi: tasdiq kutayotgan o'tkazma haqida qator; tasdiqlanmaguncha libos berilmaydi", async () => {
    await kartaOch(page, z.raqam)
    const forma = page.locator('#asosiy-amal')
    await expect(forma).toContainText(`${som(1_000_000)} o'tkazma rahbar tasdig'ini kutmoqda`)
    await forma.getByLabel('Garov turi').selectOption({ label: 'Hujjat' })
    await expect(forma.getByRole('button', { name: 'Garovni qabul qilib berish' })).toBeDisabled()
    await expect(forma).toContainText("To'ldiring: hujjat turi, hujjat raqami.")
    await forma.locator('label', { hasText: /^Hujjat turi/ }).locator('input').fill('pasport')
    await forma.locator('label', { hasText: /^Raqami/ }).locator('input').fill('AA7770099')
    // Foydalanuvchi qarori 2026-11-10: pul kelgani tasdiqlangandan keyingina libos beriladi — tugma o'chiq, sababi yozilgan
    await expect(forma.getByRole('button', { name: 'Garovni qabul qilib berish' })).toBeDisabled()
    await expect(forma).toContainText("O'tkazma tasdiqlanmaguncha libos berilmaydi.")
    // server ham rad etadi (tugmani chetlab o'tib bo'lmaydi)
    const rad = await apiSorov(page, 'POST', `/zakazlar/${z.id}/berish/`, { zaloglar: [{ turi: 'hujjat', hujjat_turi: 'pasport', hujjat_raqami: 'AA7770099' }] })
    expect(JSON.stringify(rad)).toContain("O'tkazma hali tasdiqlanmagan")
    expect((await apiSorov(page, 'GET', `/zakazlar/${z.id}/`)).holat).toBe('bron')
  })

  await test.step("rahbar «kelmadi» deydi → sotuvchiga xabar, zakaz yana avanssiz bron (libos pulsiz band qolmaydi)", async () => {
    const q = await apiSorov(rahbar, 'POST', `/kassa/tolovlar/${t.id}/tasdiq/`, { keldi: false })
    expect(q.tasdiq, JSON.stringify(q)).toBe('kelmadi')
    await page.reload()
    expect((await apiSorov(page, 'GET', `/zakazlar/${z.id}/`)).holat).toBe('vaqtinchalik')
    const tugma = page.getByRole('button', { name: /^Bildirishnomalar/ })
    await tugma.click()
    await expect(page.getByRole('menuitem', { name: new RegExp(`#${z.raqam} .*o'tkazma kelmadi`) })).toBeVisible()
    await page.keyboard.press('Escape')
    // pul naqd qayta olinadi → bron yana mustahkam, endi libos beriladi
    const t2 = await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', usul: 'naqd', summa: 1_000_000 })
    expect(t2.id, JSON.stringify(t2)).toBeTruthy()
    const b = await apiSorov(page, 'POST', `/zakazlar/${z.id}/berish/`, { zaloglar: [{ turi: 'hujjat', hujjat_turi: 'pasport', hujjat_raqami: 'AA7770099' }] })
    expect(b.holat, JSON.stringify(b)).toBe('berildi')
  })
  await apiSorov(rahbar, 'PATCH', '/sozlamalar/', { otkazma_tasdigi: false })
  await ctx.close()
  expect(xatolar).toEqual([])
})

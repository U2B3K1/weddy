// R2 (Kassa davomi): to'lovdan keyin «Libosni berish →» → zakaz kartasida berish formasi; Yangi zakaz oldindan to'ldirilgan holda —
// Bandlik kalendarining bo'sh katagidan (sana + libos tanlangan) va mijoz kartasidan (telefon, mavjud mijoz o'zi topiladi).
// Smena shu testning o'zida ochilib yopiladi, zakaz bekor qilinadi — keyingi testlar (kassa-topshirish: smena yopiq) buzilmaydi.
// Suratlar: test-results/kassa-davomi/*.png
import { expect, test } from '@playwright/test'
import { bolimga, kirish, xatolarniKuzat } from './yordam.js'

const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }
const TELEFON = { width: 390, height: 844 }
const KENG = { width: 1280, height: 860 }
const rasm = (page, nom) => page.screenshot({ path: `test-results/kassa-davomi/${nom}.png`, animations: 'disabled' })
const apiSorov = (page, usul, yol, tana) => page.evaluate(async ([usul, yol, tana]) => {
  const r = await fetch(`http://127.0.0.1:8001/api${yol}`, {
    method: usul, body: tana ? JSON.stringify(tana) : undefined,
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': localStorage.getItem('weddy.qurilma_token'),
               Authorization: `Bearer ${sessionStorage.getItem('weddy.token')}` },
  })
  return r.json()
}, [usul, yol, tana])

async function kunniBos(page, sana) {
  const kun = page.locator(`.kuz-kun[data-kun="${sana}"]`)
  for (let i = 0; i < 3 && await kun.count() === 0; i++) await page.getByRole('button', { name: 'Keyingi oy' }).click()
  await kun.click()
}

test("to'lovdan keyin «Libosni berish →» — zakaz kartasida berish formasi", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize(KENG)
  await kirish(page, 'Sotuvchi', '2222')
  const smena = await apiSorov(page, 'GET', '/kassa/smena/')
  expect(smena.ochiq, 'oldingi testlar smenani yopiq qoldiradi').toBe(false)
  await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  // bugun olib ketiladigan zakaz (avans olinmagan) — to'liq to'langach berish navbati keladi
  const bosh = await apiSorov(page, 'GET', `/bronlar/bosh/?dan=${iso(0)}&gacha=${iso(1)}`)
  const libos = bosh.find((l) => !l.band && !l.qulflangan && l.ijara_narxi > 0)
  expect(libos, JSON.stringify(bosh)).toBeTruthy()
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: `+99897${String(Date.now()).slice(-7)}`, fio: 'Berish Sinov',
    dan: iso(0), gacha: iso(1), liboslar: [libos.id] })
  expect(z.id, JSON.stringify(z)).toBeTruthy()
  try {
    await bolimga(page, 'Kassa')
    await expect(page.getByRole('tab', { name: "To'lov qabul", exact: true })).toHaveAttribute('aria-selected', 'true')
    // telefonda zakaz tanlanmaguncha bo'sh chek kartasi yo'q (keng ekranda — bor)
    await expect(page.getByRole('region', { name: "To'lov" })).toBeVisible()
    await page.setViewportSize(TELEFON)
    await expect(page.getByRole('region', { name: "To'lov" })).toBeHidden()
    await page.setViewportSize(KENG)

    await page.locator('.pos-zakaz', { hasText: 'Berish Sinov' }).click()
    const chek = page.getByRole('region', { name: "To'lov" })
    await chek.getByRole('button', { name: /^To'liq \d/ }).click()
    // terminal orqali: seyfga naqd qolmaydi — keyingi test (kassa-topshirish) smenani farqsiz ochadi
    await chek.getByRole('radio', { name: 'Terminal' }).click()
    await chek.getByRole('button', { name: / so'm qabul qilish$/ }).click()
    await expect(chek.getByText("To'lov qabul qilindi")).toBeVisible()
    const berish = chek.getByRole('button', { name: 'Libosni berish →' })
    await expect(berish).toBeVisible()
    await rasm(page, '1-tolovdan-keyin-keng')
    await page.setViewportSize(TELEFON)
    await expect(berish).toBeInViewport()
    await rasm(page, '1-tolovdan-keyin-telefon')
    await page.setViewportSize(KENG)

    await berish.click()
    await expect(page.getByRole('heading', { name: `Zakaz #${z.raqam}` })).toBeVisible()
    const forma = page.locator('#asosiy-amal')
    await expect(forma.getByRole('button', { name: 'Garovni qabul qilib berish' })).toBeInViewport()
    await rasm(page, '2-karta-berish-formasi')
  } finally {  // bron bekor (libos bo'shaydi), smena hisobdagi summa bilan farqsiz yopiladi
    await apiSorov(page, 'POST', `/zakazlar/${z.id}/bekor/`, { sabab: 'E2E: kassa davomi' })
    const s = await apiSorov(page, 'GET', '/kassa/smena/')
    if (s.ochiq) await apiSorov(page, 'POST', '/kassa/smena/yopish/', { summa: s.mening_hisobim, izoh: '', terminal: s.terminal_tizimda })
  }
  expect(xatolar).toEqual([])
})

test("QA-16: qaytarilgan zakaz qoldig'i to'langanda «Libosni berish →» yo'q", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize(KENG)
  await kirish(page, 'Rahbar', '1111')
  expect((await apiSorov(page, 'GET', '/kassa/smena/')).ochiq, 'oldingi test smenani yopadi').toBe(false)
  await apiSorov(page, 'POST', '/kassa/smena/ochish/', { boshlangich_qoldiq: 0 })
  // Tayyorlov (API): avans terminal, qoldiq o'tkazma → libos berildi → rahbar «kelmadi» → qaytarildi (qoldiq bilan).
  // O'z libosi — umumiy E2E-1/E2E-2 ning bugungi bandligi keyingi testlarga (zakaz-oqimi erta berishi, zz-amallar) tegmasin
  const kat = (await apiSorov(page, 'GET', '/kategoriyalar/')).find((k) => k.nomi === 'Milliy')
  const libos = await apiSorov(page, 'POST', '/liboslar/', { artikul: 'QA16', nomi: 'Libos QA16', kategoriya: kat.id,
    ijara_narxi: 1_000_000, tannarx: 3_000_000 })
  expect(libos.id, JSON.stringify(libos)).toBeTruthy()
  const z = await apiSorov(page, 'POST', '/zakazlar/', { telefon: `+99895${String(Date.now()).slice(-7)}`, fio: 'Qaytgan Sinov',
    dan: iso(0), gacha: iso(1), liboslar: [libos.id] })
  expect(z.id, JSON.stringify(z)).toBeTruthy()
  try {
    await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'avans', summa: z.jami - 100_000, usul: 'karta' })
    const otk = await apiSorov(page, 'POST', '/kassa/tolovlar/', { zakaz: z.id, tur: 'qoldiq', summa: 100_000, usul: 'otkazma' })
    await apiSorov(page, 'POST', `/zakazlar/${z.id}/berish/`, { zaloglar: [{ turi: 'hujjat', hujjat_turi: 'pasport', hujjat_raqami: 'AA16' }] })
    await apiSorov(page, 'POST', `/kassa/tolovlar/${otk.id}/tasdiq/`, { keldi: false })
    const q = await apiSorov(page, 'POST', `/zakazlar/${z.id}/qaytarish/`, {})
    expect(q.holat, JSON.stringify(q)).toBe('qaytarildi')  // C-03: qoldiq 100 000 hali olinmagan

    await bolimga(page, 'Kassa')
    await page.locator('.pos-zakaz', { hasText: 'Qaytgan Sinov' }).click()
    const chek = page.getByRole('region', { name: "To'lov" })
    await chek.getByRole('button', { name: /^To'liq \d/ }).click()
    await chek.getByRole('radio', { name: 'Terminal' }).click()
    await chek.getByRole('button', { name: / so'm qabul qilish$/ }).click()
    await expect(chek.getByText("To'lov qabul qilindi")).toBeVisible()
    await expect(chek.getByRole('button', { name: 'Libosni berish →' })).toHaveCount(0)  // libos allaqachon qaytgan
    await rasm(page, '5-qaytgan-zakaz-qoldiq-tolandi')
    expect((await apiSorov(page, 'GET', `/zakazlar/${z.id}/`)).holat).toBe('yopildi')
  } finally {  // libos keyingi testlar uchun bo'sh, smena farqsiz yopiladi (naqd yo'q — terminal)
    await apiSorov(page, 'POST', `/liboslar/${libos.id}/tozalandi/`)
    const s = await apiSorov(page, 'GET', '/kassa/smena/')
    if (s.ochiq) await apiSorov(page, 'POST', '/kassa/smena/yopish/', { summa: s.mening_hisobim, izoh: '', terminal: s.terminal_tizimda })
  }
  // erta qaytgan, yopilgan zakaz broni (bufer bilan) libosni arxivga o'tkazishni to'smaydi; vaqtinchalik libos keyingi testlarga
  // (sanoq «yo'q» ro'yxati) tushmaydi
  const arxiv = await apiSorov(page, 'PATCH', `/liboslar/${libos.id}/`, { holat: 'arxiv' })
  expect(arxiv.holat, JSON.stringify(arxiv)).toBe('arxiv')
  expect(xatolar).toEqual([])
})

test("Yangi zakaz oldindan to'ldirilgan: kalendar bo'sh katagi va mijoz kartasi", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize(KENG)
  await kirish(page, 'Rahbar', '1111')

  await test.step("kalendar: bo'sh katak → sana va libos tanlangan 2-qadam", async () => {
    await bolimga(page, 'Zakazlar')
    await page.getByRole('tab', { name: 'Bandlik kalendari' }).click()
    const katak = page.getByRole('button', { name: /^E2E-2 .*yangi zakaz$/ }).last()  // ko'rinib turgan oxirgi kun
    await katak.click()
    await expect(page.getByRole('tab', { name: 'Yangi zakaz', exact: true })).toHaveAttribute('aria-selected', 'true')
    await expect(page.locator('.zakaz-ip [aria-current="step"]')).toContainText('Libos')
    await expect(page.locator('.varaq-royxat li')).toHaveCount(1)
    await expect(page.locator('.varaq-royxat li')).toContainText('E2E-2')
    await expect(page.getByRole('button', { name: 'Davom etish', exact: true })).toBeEnabled()
    await rasm(page, '3-kalendardan-yangi-zakaz')
    // bo'limga qaytilganda boshlang'ich qayta qo'llanmaydi — sessiya qoralamasi davom etadi (sana saqlangan, libos qulfi bo'shagan)
    await bolimga(page, 'Dashboard')
    await bolimga(page, 'Kassa')
    await page.getByRole('tab', { name: 'Yangi zakaz', exact: true }).click()
    await expect(page.locator('.zakaz-ip [aria-current="step"]')).toContainText('Libos')
    await expect(page.locator('.varaq-royxat li')).toHaveCount(0)
  })

  await test.step("mijoz kartasi: «Yangi zakaz» → 3-qadamda telefon to'ldirilgan, mavjud mijoz o'zi topiladi", async () => {
    await bolimga(page, 'Mijozlar')
    await page.locator('.mijoz-jadval tbody tr', { hasText: 'Storno Mijoz' }).click()
    await expect(page.getByRole('heading', { name: 'Storno Mijoz' })).toBeVisible()
    await page.getByRole('main').getByRole('button', { name: 'Yangi zakaz', exact: true }).click()
    await expect(page.getByRole('tab', { name: 'Yangi zakaz', exact: true })).toHaveAttribute('aria-selected', 'true')
    // yangi `n` — oldingi qoralama (kalendar sanasi) ustidan yozildi: 1-qadam, sana tanlanmagan
    await expect(page.locator('.zakaz-ip [aria-current="step"]')).toContainText('Sana')
    await kunniBos(page, iso(70))
    await kunniBos(page, iso(71))
    await page.getByRole('button', { name: 'Davom etish — liboslarni tanlash' }).click()
    await page.locator('ul.liboslar li').filter({ has: page.getByRole('button', { name: "Qo'shish" }) }).first()
      .getByRole('button', { name: "Qo'shish" }).click()
    await page.getByRole('button', { name: 'Davom etish', exact: true }).click()
    await expect(page.getByLabel('Mijoz telefoni')).toHaveValue('+998900000001')
    await expect(page.locator('.yz-mavjud')).toContainText('Storno Mijoz')  // mavjud mijoz kartasi (kanvas)
    await expect(page.locator('.yz-mavjud')).toContainText('Mavjud mijoz')
    await expect(page.getByLabel('Yangi mijoz — F.I.O.')).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Zakazni saqlash' })).toBeEnabled()
    await rasm(page, '4-mijozdan-yangi-zakaz')
  })

  await test.step('yangi raqam: qidiruv xatosiz (200), F.I.O. so\'raladi', async () => {
    const javob = page.waitForResponse((r) => r.url().includes('/mijozlar/qidirish/'))
    await page.getByLabel('Mijoz telefoni').fill(`+998 99 ${String(Date.now()).slice(-7, -4)} ${String(Date.now()).slice(-4, -2)} ${String(Date.now()).slice(-2)}`)
    expect((await javob).status()).toBe(200)
    await expect(page.getByLabel('Yangi mijoz — F.I.O.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Zakazni saqlash' })).toBeDisabled()
  })
  // zakaz saqlanmaydi: bo'limdan chiqilganda libos qulfi bo'shaydi
  await bolimga(page, 'Dashboard')
  expect(xatolar).toEqual([])
})

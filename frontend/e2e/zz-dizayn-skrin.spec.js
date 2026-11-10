// Dizayn ko'rigi uchun skrinshotlar (rahbar, 1440×900 to'liq sahifa va telefon). Oddiy `npm run e2e` da o'tkazib yuboriladi —
// faqat so'ralganda: `DIZAYN_SKRIN=1 npx playwright test zz-dizayn-skrin`.
// Natija: frontend/dizayn-skrin/<tartib>-<bo'lim>.png (gitignore'da; test-results emas — uni Playwright har yurishda tozalaydi).
// Eslatma: rasm mazmuni baza holatiga bog'liq — solishtirish uchun doim yakka (toza seed ustida) ishga tushiring.
import { expect, test } from '@playwright/test'
import { bolimga, kirish, xatolarniKuzat } from './yordam.js'

const BOLIMLAR = ['Dashboard', 'Zakazlar', 'Liboslar', 'Mijozlar', 'Kassa', 'Hisobotlar', 'Sozlama']
const CHIQ = 'dizayn-skrin'

test('dizayn skrinshotlari', async ({ page }) => {
  test.skip(!process.env.DIZAYN_SKRIN, "faqat DIZAYN_SKRIN=1 bilan")
  test.setTimeout(180_000)  // 7 bo'lim + telefon — 60 soniya yetmaydi
  const xatolar = xatolarniKuzat(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await kirish(page, 'Rahbar', '1111')
  let i = 1
  for (const nom of BOLIMLAR) {
    await bolimga(page, nom)
    await page.waitForLoadState('networkidle')
    await expect(page.locator('.ustki-nom h1')).toBeVisible()  // bo'lim haqiqatan chizildi
    await page.screenshot({ path: `${CHIQ}/${String(i).padStart(2, '0')}-${nom}.png`, fullPage: true, animations: 'disabled' })
    i++
  }
  await page.setViewportSize({ width: 390, height: 844 })
  // telefonda chap menyu yopiq — bosh sahifaga to'g'ridan-to'g'ri o'tiladi (sahifa to'liq qayta yuklanadi)
  await page.goto('/')
  await expect(page.getByRole('region', { name: 'Egasining savollari' })).toBeVisible()
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `${CHIQ}/99-telefon-bosh.png`, fullPage: true, animations: 'disabled' })
  expect(xatolar).toEqual([])
})

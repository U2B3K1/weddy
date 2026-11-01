// «Mijozlar»: ro'yxat (jadval panel) va mijoz kartasi (varaq: to'y kuni, raqamlar, o'lchamlar; tarix).
// Har ko'rinish keng ekranda va telefonda suratga olinadi (test-results/mijozlar/*.png).
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const iso = (kun) => { const t = new Date(); t.setDate(t.getDate() + kun); return t.toLocaleDateString('sv-SE') }
const TELEFON = { width: 390, height: 844 }
const KENG = { width: 1280, height: 860 }

async function suratlar(page, nom) {
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `test-results/mijozlar/${nom}-keng.png`, fullPage: true, animations: 'disabled' })
  await page.setViewportSize(TELEFON)
  await page.waitForTimeout(400)
  await page.screenshot({ path: `test-results/mijozlar/${nom}-telefon.png`, fullPage: true, animations: 'disabled' })
  const [kenglik, ekran] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth])
  expect(kenglik, `${nom}: telefonda sahifa gorizontal surilmasin`).toBeLessThanOrEqual(ekran)
  await page.setViewportSize(KENG)
}

test('mijozlar: ro\'yxat va mijoz varaqasi', async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await nav(page).getByRole('button', { name: 'Mijozlar', exact: true }).click()
  const qator = page.locator('.mijoz-jadval tbody tr', { hasText: 'Storno Mijoz' })
  await expect(qator).toBeVisible()
  await suratlar(page, '1-royxat')

  await qator.click()
  await expect(page.getByRole('heading', { name: 'Storno Mijoz' })).toBeVisible()
  await page.waitForLoadState('networkidle')  // dev (StrictMode) karta ikki marta yuklanadi — kech javob kiritilganni bosmasin
  await page.getByLabel("To'y sanasi").fill(iso(30))
  await page.getByLabel("Ko'krak").fill('88')
  await page.getByLabel('Bel').fill('64')
  await page.getByRole('button', { name: 'Saqlash', exact: true }).click()
  await expect(page.getByText('Saqlandi.')).toBeVisible()
  const varaq = page.locator('.mijoz-varaq')
  await expect(varaq).toContainText('30 kun qoldi')
  await expect(varaq.locator('.mijoz-olchamlar')).toContainText('88 sm')
  await expect(page.locator('.karta-tolovlar .tarix-qator').first()).toContainText('#1')
  await suratlar(page, '2-karta')

  await page.getByRole('button', { name: "Mijozlar ro'yxatiga qaytish" }).click()
  await page.getByRole('tab', { name: "Qora ro'yxat" }).click()
  await expect(page.getByText("Qora ro'yxatda hech kim yo'q.")).toBeVisible()
  expect(xatolar).toEqual([])
})

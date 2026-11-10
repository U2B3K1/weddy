// «Mijozlar»: ro'yxat (jadval panel) va mijoz kartasi (varaq: to'y kuni, raqamlar, o'lchamlar; tarix).
// Har ko'rinish keng ekranda va telefonda suratga olinadi (test-results/mijozlar/*.png).
import { expect, test } from '@playwright/test'
import { bolimga, kirish, xatolarniKuzat } from './yordam.js'

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
  await bolimga(page, 'Mijozlar')
  const qator = page.locator('.mijoz-jadval tbody tr', { hasText: 'Storno Mijoz' })
  await expect(qator).toBeVisible()
  await suratlar(page, '1-royxat')

  await qator.click()
  await expect(page.getByRole('heading', { name: 'Storno Mijoz' })).toBeVisible()
  await page.waitForLoadState('networkidle')  // dev (StrictMode) karta ikki marta yuklanadi — kech javob kiritilganni bosmasin
  await page.getByText("Ma'lumotlarni tahrirlash", { exact: true }).click()  // tahrir bloki yopiq turadi (B-33)
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
  // ko'rsatkich kartasi-filtr (maket uslubi): to'yi 30 kun ichida — hozirgina to'y sanasi kiritilgan mijoz shu ro'yxatda
  const kpi = page.getByRole('region', { name: "Mijozlar ko'rsatkichlari" })
  await expect(kpi.getByRole('button', { name: /^Jami mijozlar: [1-9]\d*$/ })).toHaveAttribute('aria-pressed', 'true')
  const toy = kpi.getByRole('button', { name: /^Yaqin to'ylar: [1-9]\d*$/ })
  const toySoni = Number((await toy.getAttribute('aria-label')).split(': ')[1])
  await toy.click()
  await expect(toy).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('heading', { name: "Yaqin to'ylar" })).toBeVisible()
  await expect(page.locator('.mijoz-jadval tbody tr')).toHaveCount(toySoni)  // ro'yxat — faqat shu filtr (kartadagi son bilan bir xil)
  await expect(page.locator('.mijoz-jadval tbody tr', { hasText: 'Storno Mijoz' })).toBeVisible()
  await suratlar(page, '3-yaqin-toylar')
  await toy.click()  // yana bosilsa — hammasi
  await expect(page.locator('.jadval-asboblar .panel-nom')).toHaveText('Mijozlar')
  await page.getByRole('tab', { name: "Qora ro'yxat" }).click()
  await expect(page.getByText("Qora ro'yxatda hech kim yo'q.")).toBeVisible()
  expect(xatolar).toEqual([])
})

// «Zakazlar» ro'yxati: holat tablari sonlari bilan, ijara sanasi va «qachon?» belgisi (N kun qoldi / kechikdi).
// Keng ekranda va telefonda suratga olinadi (test-results/zakazlar/*.png).
import { expect, test } from '@playwright/test'
import { kirish, xatolarniKuzat } from './yordam.js'

const nav = (page) => page.getByRole('navigation', { name: "Bo'limlar" })
const TELEFON = { width: 390, height: 844 }
const KENG = { width: 1280, height: 860 }

async function suratlar(page, nom) {
  await page.waitForLoadState('networkidle')
  await page.screenshot({ path: `test-results/zakazlar/${nom}-keng.png`, fullPage: true, animations: 'disabled' })
  await page.setViewportSize(TELEFON)
  await page.waitForTimeout(400)
  await page.screenshot({ path: `test-results/zakazlar/${nom}-telefon.png`, fullPage: true, animations: 'disabled' })
  const [kenglik, ekran] = await page.evaluate(() => [document.documentElement.scrollWidth, window.innerWidth])
  expect(kenglik, `${nom}: telefonda sahifa gorizontal surilmasin`).toBeLessThanOrEqual(ekran)
  await page.setViewportSize(KENG)
}

test("zakazlar: ro'yxat — sonli tablar, ijara sanasi va muddat", async ({ page }) => {
  const xatolar = xatolarniKuzat(page)
  await kirish(page, 'Rahbar', '1111')
  await nav(page).getByRole('button', { name: 'Zakazlar', exact: true }).click()
  const qatorlar = page.locator('.zakaz-jadval tbody tr')
  await expect(qatorlar.first()).toBeVisible()
  // «Hammasi» tabidagi son jadval qatorlari soniga teng
  const jami = await page.getByRole('tab', { name: /^Hammasi/ }).locator('.tab-son').innerText()
  await expect(qatorlar).toHaveCount(Number(jami))
  // bekor qilinmagan zakazda «qachon?» javobi bor
  await expect(page.locator('.zakaz-jadval .muddat').first()).toHaveText(/kun qoldi|olib ketadi|qaytaradi|kechikdi|mijozda/)
  await expect(page.locator('.ijara-sana').first()).toBeVisible()
  await suratlar(page, '1-royxat')

  await page.getByRole('tab', { name: /^Bekor/ }).click()
  await expect(qatorlar.first()).toContainText('Bekor')
  await expect(qatorlar.locator('.muddat')).toHaveCount(0)  // bekor zakazda muddat yo'q
  await page.locator('.jadval-qidiruv').fill('yoqmijoz')
  await expect(page.getByText("«yoqmijoz» bo'yicha zakaz topilmadi.")).toBeVisible()
  expect(xatolar).toEqual([])
})
